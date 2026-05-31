"""5g audit-report — structural data.js<->YAML cross-check.

Parses data.js back to a dict, RECOMPUTES the expected data via
report.loader.load_run + report.transform.build_apd_data, and runs structural
checks. Emits compact report-audit.yaml (the LLM auditor reads this, never
data.js). Status fail -> CLI exits 1 so the workflow gate branches.
"""
from __future__ import annotations

import collections
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

_INFORMATIONAL_TO_INFO = {"informational": "info"}


@dataclass
class AuditResult:
    status: str = "pass"
    checks: list[dict[str, str]] = field(default_factory=list)
    counts: dict[str, int] = field(default_factory=dict)
    drift: list[dict[str, str]] = field(default_factory=list)


def parse_data_js(path: Path) -> dict[str, Any]:
    """Parse 'window.APD_DATA = {...};' back into a dict.

    Strips the prefix + trailing ';', reverses the '</' -> '<\\/' escaping that
    emit.write_data_js applies, then json.loads.
    """
    text = path.read_text(encoding="utf-8-sig").strip()
    prefix = "window.APD_DATA = "
    if text.startswith(prefix):
        text = text[len(prefix):]
    text = text.rstrip()
    if text.endswith(";"):
        text = text[:-1]
    text = text.replace("<\\/", "</")
    result: dict[str, Any] = json.loads(text)
    return result


def _yaml_records(path: Path, key: str) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    doc = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return [r for r in (doc.get(key) or []) if isinstance(r, dict)]


def _recompute_nist_rollup(run_dir: Path) -> list[dict[str, Any]]:
    """Recompute the family-aggregated nist_rollup the report renderer produces.

    Isolated so the audit's parity check can be monkeypatched in tests and so a
    transform exception is caught at one call site.
    """
    from ..report.loader import load_run
    from ..report.transform import build_apd_data

    data = build_apd_data(load_run(run_dir), run_dir=run_dir)
    rollup = data.get("nist_rollup") or []
    return [r for r in rollup if isinstance(r, dict)]


def _check(result: AuditResult, name: str, ok: bool, detail: str) -> None:
    result.checks.append({"name": name, "status": "pass" if ok else "fail", "detail": detail})
    if not ok:
        result.status = "fail"


def audit_report(run_dir: Path) -> AuditResult:
    from ..report.loader import load_run
    from ..report.transform import build_apd_data

    synth = run_dir / "40-synthesis"
    result = AuditResult()

    data_js_path = synth / "report-html" / "data.js"
    if not data_js_path.is_file():
        _check(result, "data_js_present", False, f"missing {data_js_path}")
        _write(run_dir, result)
        return result
    try:
        parsed = parse_data_js(data_js_path)
    except (json.JSONDecodeError, ValueError, OSError) as exc:
        _check(result, "data_js_parse", False, f"data.js parse failed: {exc}")
        _write(run_dir, result)
        return result

    # Authoritative YAML record sets.
    deduped_f = _yaml_records(synth / "deduped-findings.yaml", "finding")
    deduped_c = _yaml_records(synth / "deduped-capabilities.yaml", "capability")
    apath_f = _yaml_records(synth / "attack-path.findings.yaml", "finding")
    nist = _yaml_records(synth / "nist-coverage.yaml", "controls")
    attack = _yaml_records(synth / "attack-exposure.yaml", "techniques")

    # ID coverage (findings): deduped UNION apath == data.findings ids.
    yaml_fids = {f.get("id") for f in deduped_f} | {f.get("id") for f in apath_f}
    data_fids = {f.get("id") for f in parsed.get("findings", [])}
    missing_fids = sorted(str(x) for x in yaml_fids - data_fids)[:5]
    _check(result, "id_coverage_findings", yaml_fids == data_fids,
           f"yaml={len(yaml_fids)} data.js={len(data_fids)} missing={missing_fids}")

    # ID coverage (capabilities).
    yaml_cids = {c.get("id") for c in deduped_c}
    data_cids = {c.get("id") for c in parsed.get("capabilities", [])}
    _check(result, "id_coverage_capabilities", yaml_cids == data_cids,
           f"yaml={len(yaml_cids)} data.js={len(data_cids)}")

    # NIST per-control vs taxonomy keys (nist_rollup is family-aggregated).
    # Subset check (yaml_ids ⊆ taxonomy keys): taxonomy carries the full reference catalog,
    # so only "every cited id is present" is required, not equality.
    taxonomy = parsed.get("taxonomy", {})
    nist_ids = {row.get("id") for row in nist}
    missing_nist = {cid for cid in nist_ids if cid not in taxonomy}
    missing_nist_sample = sorted(str(x) for x in missing_nist)[:5]
    _check(result, "id_coverage_nist", not missing_nist,
           f"controls={len(nist_ids)} missing_from_taxonomy={missing_nist_sample}")

    # NIST rendered-rollup parity (Plan 3): recompute the family-aggregated
    # nist_rollup and compare family-level {covered, gapped, both} + row count
    # against the data.js parsed['nist_rollup']. Hard FAIL on mismatch (drives
    # the remediate loop); soft (non-blocking pass) on a transform exception.
    parsed_rollup = [r for r in (parsed.get("nist_rollup") or []) if isinstance(r, dict)]
    try:
        expected_rollup = _recompute_nist_rollup(run_dir)
    except Exception as exc:  # noqa: BLE001 — recompute is best-effort
        _check(result, "nist_rollup_parity", True,
               f"skipped (recompute exception, non-blocking): {exc}")
    else:
        def _fam_counts(rows: list[dict[str, Any]]) -> dict[str, tuple[int, int, int]]:
            return {
                str(r.get("family")): (
                    int(r.get("covered", 0)), int(r.get("gapped", 0)), int(r.get("both", 0))
                )
                for r in rows
            }
        expected_counts = _fam_counts(expected_rollup)
        parsed_counts = _fam_counts(parsed_rollup)
        rows_ok = len(expected_rollup) == len(parsed_rollup)
        counts_ok = expected_counts == parsed_counts
        mismatched = sorted(
            fam for fam in set(expected_counts) | set(parsed_counts)
            if expected_counts.get(fam) != parsed_counts.get(fam)
        )[:5]
        _check(result, "nist_rollup_parity", rows_ok and counts_ok,
               f"recompute_rows={len(expected_rollup)} data.js_rows={len(parsed_rollup)} "
               f"mismatched_families={mismatched}")

    # ATT&CK per-technique (data.attack_exposure is 1:1).
    # Subset check (yaml_ids ⊆ data_attack_ids): attack_exposure carries the full reference catalog
    # (more keys than the run cites), so only "every cited id is present" is required, not equality.
    attack_ids = {row.get("id") for row in attack}
    data_attack_ids = {row.get("id") for row in parsed.get("attack_exposure", [])}
    _check(result, "id_coverage_attack", attack_ids <= data_attack_ids,
           f"yaml={len(attack_ids)} data.js={len(data_attack_ids)}")

    # Count parity (severity): recompute from deduped+apath, normalizing
    # 'informational'->'info'. NOT against summarize_run (which omits apath).
    def _norm_sev(f: dict[str, Any]) -> str:
        s = str(f.get("severity", "informational"))
        return _INFORMATIONAL_TO_INFO.get(s, s)

    by_sev = collections.Counter(_norm_sev(f) for f in deduped_f + apath_f)
    data_by_sev = parsed.get("summary", {}).get("bySeverity", {})
    sev_ok = all(data_by_sev.get(k, 0) == by_sev.get(k, 0)
                 for k in ("critical", "high", "medium", "low", "info"))
    _check(result, "count_parity_severity", sev_ok,
           f"recomputed={dict(by_sev)} data.js={data_by_sev}")

    # Count parity (totals).
    total_ok = parsed.get("summary", {}).get("findings_total") == len(deduped_f) + len(apath_f)
    data_total = parsed.get("summary", {}).get("findings_total")
    yaml_total = len(deduped_f) + len(apath_f)
    _check(result, "count_parity_totals", total_ok,
           f"data.js={data_total} yaml={yaml_total}")

    # data.js <-> recomputed drift.
    try:
        recomputed = build_apd_data(load_run(run_dir), run_dir=run_dir)
        recomputed_fids = {f.get("id") for f in recomputed.get("findings", [])}
        drift_ok = recomputed_fids == data_fids
        _check(result, "data_js_recompute_drift", drift_ok,
               f"recompute_findings={len(recomputed_fids)} data.js={len(data_fids)}")
    except Exception as exc:  # noqa: BLE001 — recompute is best-effort
        _check(result, "data_js_recompute_drift", False, f"recompute failed: {exc}")

    # section_errors gate.
    section_errors = (parsed.get("meta") or {}).get("section_errors") or {}
    _check(result, "section_errors_empty", not section_errors,
           f"section_errors={list(section_errors)}")

    result.counts = {
        # deduped + apath = findings_data_js (the total that id_coverage_findings checks).
        "deduped_findings_yaml": len(deduped_f), "apath_findings_yaml": len(apath_f),
        "findings_data_js": len(data_fids),
        "capabilities_yaml": len(deduped_c), "capabilities_data_js": len(data_cids),
        "nist_controls_yaml": len(nist_ids),
        "nist_ids_in_taxonomy": len(nist_ids - missing_nist),
        "attack_techniques_yaml": len(attack_ids),
        "attack_techniques_data_js": len(data_attack_ids),
    }
    _source_hash_drift(run_dir, result)
    _write(run_dir, result)
    return result


def _source_hash_drift(run_dir: Path, result: AuditResult) -> None:
    from ..report.loader import _yaml_with_hash

    manifest = run_dir / "40-synthesis" / "report-html" / "build-manifest.txt"
    if not manifest.is_file():
        return
    recorded: dict[str, str] = {}
    for line in manifest.read_text(encoding="utf-8").splitlines():
        if "=" in line:
            k, v = line.split("=", 1)
            recorded[k] = v
    for filename in ("deduped-findings.yaml", "deduped-capabilities.yaml",
                     "nist-coverage.yaml", "attack-exposure.yaml", "apd-coverage-matrix.yaml"):
        path = run_dir / "40-synthesis" / filename
        if not path.is_file() or filename not in recorded:
            continue
        _doc, current = _yaml_with_hash(path)
        if current != recorded[filename]:
            result.drift.append({"file": filename, "manifest_hash": recorded[filename],
                                  "current_hash": current})
    if result.drift:
        _check(result, "source_hash_drift", False,
               f"stale: {[d['file'] for d in result.drift]}")


def _write(run_dir: Path, result: AuditResult) -> None:
    synth = run_dir / "40-synthesis"
    synth.mkdir(parents=True, exist_ok=True)
    doc = {
        "schema_version": 1, "generated_by": "apd-gauntlet", "status": result.status,
        "checks": result.checks, "counts": result.counts, "drift": result.drift,
    }
    (synth / "report-audit.yaml").write_text(yaml.safe_dump(doc, sort_keys=False), encoding="utf-8")
