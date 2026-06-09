"""5d rollup — pure aggregation over deduped records into canonical coverage YAMLs.

Reproduces the example-golden list shapes (NOT the divergent runs/ shapes):
  nist-coverage.yaml      controls: [ {id, family, title, finding_count, finding_ids,
                                       capability_count, capability_ids, posture} ]
  attack-exposure.yaml    techniques: [ {id, sub_technique, tactic, name,
                                         exposure_finding_count, exposure_finding_ids,
                                         mitigated_by_capabilities} ]
  apd-coverage-matrix.yaml components: [
                              {name, cells: {<9 goals>: {findings, capabilities, posture}}} ]
  cwe/owasp/d3fend-coverage.yaml — only when the run declares those taxonomies.

Deterministic: controls/techniques sorted by first-appearance over deduped
record order then by id; cells emit all 9 goals in canonical GOAL_SHORT order.
Roll up ONLY what records cite; never synthesize from reference data.

EQUIVALENCE SCOPE (I1): nist-coverage / attack-exposure reproduce the golden's
per-row finding/capability membership + posture. The apd-coverage-matrix
reproduces the golden SHAPE and per-cell posture SEMANTICS, but its component
LABELS are NOT a golden-equivalence target — the golden labels components by
editorial logical-asset names that no deterministic rule reproduces (see
_matrix_rollup). The matrix is excluded from the Task 8 equivalence projection.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from ..report.taxonomy import atlas_titles, attack_technique_titles, d3fend_titles
from . import coverage_logic as cl
from .loader import load_corpus
from .metrics import compute_metrics

_PKG_DATA = Path(__file__).resolve().parent.parent / "data"

# Import-cycle note: report.taxonomy imports only stdlib (no synthesis import),
# and synthesis.rollup is never imported by report.*, so this synthesis->report
# edge does NOT close the report->synthesis cycle that coverage_logic broke
# (report.transform->synthesis.coverage_logic is the only report->synthesis edge,
# and it does not touch rollup or taxonomy).


@dataclass
class RollupResult:
    nist: list[dict[str, Any]] = field(default_factory=list)
    attack: list[dict[str, Any]] = field(default_factory=list)
    matrix: list[dict[str, Any]] = field(default_factory=list)
    cwe: dict[str, Any] | None = None
    owasp: dict[str, Any] | None = None
    d3fend: dict[str, Any] | None = None
    atlas: dict[str, Any] | None = None
    masvs: dict[str, Any] | None = None
    maswe: dict[str, Any] | None = None
    metrics: dict[str, Any] = field(default_factory=dict)


def _nist_titles() -> dict[str, str]:
    path = _PKG_DATA / "nist-controls.json"
    if not path.is_file():
        return {}
    raw = json.loads(path.read_text(encoding="utf-8"))
    return raw.get("controls", raw) if isinstance(raw, dict) else {}


def _family_titles() -> dict[str, str]:
    path = _PKG_DATA / "nist-families.json"
    if not path.is_file():
        return {}
    raw: Any = json.loads(path.read_text(encoding="utf-8"))
    return raw if isinstance(raw, dict) else {}


def _load_deduped(run_dir: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    synth = run_dir / "40-synthesis"
    fdoc = yaml.safe_load((synth / "deduped-findings.yaml").read_text(encoding="utf-8")) or {}
    cdoc = yaml.safe_load((synth / "deduped-capabilities.yaml").read_text(encoding="utf-8")) or {}
    findings = [f for f in (fdoc.get("finding") or []) if isinstance(f, dict)]
    caps = [c for c in (cdoc.get("capability") or []) if isinstance(c, dict)]
    # Union the tier-4 findings into the finding corpus so nist/attack/matrix
    # coverage + metrics reflect them (spec Steps 2/8). F1: this now unions BOTH
    # apath-* (attack-path analyzer) AND tmeval-* (threat-model evaluator) —
    # previously only apath-*, which silently dropped tmeval-* from coverage and
    # the report. load_corpus(include_attack_path=True) already indexes both the
    # 40-synthesis/attack-path.findings.yaml and 40-threat-model/threat-model.findings.yaml.
    tier4_by_id, _ = load_corpus(run_dir, include_attack_path=True)
    seen = {f.get("id") for f in findings}
    for fid, rec in tier4_by_id.items():
        if (fid.startswith("apath-") or fid.startswith("tmeval-")) and fid not in seen:
            findings.append(rec)
    return findings, caps


def _nist_rollup(
    findings: list[dict[str, Any]],
    caps: list[dict[str, Any]],
    titles: dict[str, str],
    fam_titles: dict[str, str],
) -> list[dict[str, Any]]:
    order: list[str] = []
    fmap: dict[str, list[str]] = {}
    for f in findings:
        for cid in cl.normalize_nist_ids(
            cl.extract_ids_from_mapping((f.get("control_mappings") or {}).get("nist_800_53r5"))
        ):
            if cid not in fmap:
                fmap[cid] = []
                order.append(cid)
            if f["id"] not in fmap[cid]:
                fmap[cid].append(f["id"])
    cap_index = cl.build_cap_controls_index(caps)
    rows: list[dict[str, Any]] = []
    all_ids = set(order) | set(cap_index)
    order_index = {c: i for i, c in enumerate(order)}
    for cid in sorted(all_ids, key=lambda c: (order_index.get(c, 1_000_000), c)):
        fids = sorted(fmap.get(cid, []))
        cids = sorted(cap_index.get(cid, set()))
        fam = cl.nist_family_of(cid)
        rows.append({
            "id": cid, "family": fam,
            "title": titles.get(cid) or fam_titles.get(fam) or f"{fam} family controls",
            "finding_count": len(fids), "finding_ids": fids,
            "capability_count": len(cids), "capability_ids": cids,
            "posture": cl.posture(has_findings=bool(fids), has_caps=bool(cids)),
        })
    return rows


def _attack_rollup(
    findings: list[dict[str, Any]],
    caps: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    mit_path = _PKG_DATA / "mitre-mitigations.json"
    mitigations = json.loads(mit_path.read_text(encoding="utf-8")).get("mitigations", {})
    # C4: attack-exposure.schema.json requires name minLength:3 — name:"" FAILS
    # validation and contradicts the golden (which carries real technique names
    # like "Data from Cloud Storage"). Look up the title from the bundled
    # ATT&CK catalog (report.taxonomy.attack_technique_titles returns {tid: name}),
    # falling back to the id (always >= 3 chars: "T####") so name is never "".
    titles = attack_technique_titles()
    order: list[str] = []
    tech: dict[str, dict[str, Any]] = {}
    for f in findings:
        for m in (f.get("control_mappings") or {}).get("mitre_attack") or []:
            if not isinstance(m, dict) or not m.get("technique"):
                continue
            tid = m["technique"]
            if tid not in tech:
                tech[tid] = {"tactic": m.get("tactic"), "sub_technique": m.get("sub_technique"),
                             "finding_ids": []}
                order.append(tid)
            if f["id"] not in tech[tid]["finding_ids"]:
                tech[tid]["finding_ids"].append(f["id"])
    rows: list[dict[str, Any]] = []
    order_index = {t: i for i, t in enumerate(order)}
    for tid in sorted(order, key=lambda t: (order_index[t], t)):
        fids = sorted(tech[tid]["finding_ids"])
        mits: list[dict[str, str]] = []
        for cap in caps:
            for m in (cap.get("control_mappings") or {}).get("mitre_attack_mitigations") or []:
                mid = m.get("id") if isinstance(m, dict) else None
                if mid and tid in mitigations.get(mid, []):
                    mits.append({"capability_id": cap["id"], "mitigation_id": mid})
        mits.sort(key=lambda x: (x["capability_id"], x["mitigation_id"]))
        rows.append({
            "id": tid, "sub_technique": tech[tid]["sub_technique"], "tactic": tech[tid]["tactic"],
            "name": titles.get(tid, tid), "exposure_finding_count": len(fids),
            "exposure_finding_ids": fids, "mitigated_by_capabilities": mits,
        })
    return rows


def _matrix_rollup(
    findings: list[dict[str, Any]],
    caps: list[dict[str, Any]],
    inventory: dict[str, Any],
) -> list[dict[str, Any]]:
    # I1 — DIVERGENCE (grounded against the golden, not a defect to "fix"):
    # the example golden apd-coverage-matrix.yaml keys components by LOGICAL
    # ASSET LABELS ("Kafka claim-events topic", "RDS audit_log table") and
    # attributes the SAME finding id to MULTIPLE components (e.g. intg-42a3ebbd
    # — whose only evidence artifact is threat-model.md — appears under BOTH
    # the Kafka and RDS components; immut-067a7391 appears under Kafka.immut AND
    # RDS.availability). asset-inventory.yaml asset names are
    # "claim-ingress-api"/"audit-log-store"/... — they match NEITHER the golden
    # labels NOR a single evidence-artifact filename. The golden component
    # attribution is therefore an EDITORIAL (LLM/synthesizer) judgement about
    # which logical assets a finding touches, NOT a function any deterministic
    # one-component-per-record _label() can reproduce. Consequently:
    #   * the COMPONENT LABEL is explicitly NOT a golden-equivalence target;
    #   * only the per-cell posture SEMANTICS (gapped/covered/both/silent given
    #     a component's finding+capability membership, all 9 goals present) are
    #     a reproducible contract — and those ARE tested below;
    #   * the rollup keys deterministically by the first-evidence ARTIFACT label
    #     (one component per record), which is a faithful, reproducible matrix —
    #     it just won't byte-match the golden's editorial logical-asset labels.
    # The Task 8 equivalence test does NOT project the matrix for this reason
    # (it projects nist only). Plan 3 may add an optional LLM matrix-labeling
    # pass if logical-asset attribution becomes a requirement.
    components = [a.get("name", "") for a in (inventory.get("assets") or [])
                 if isinstance(a, dict) and a.get("name")]
    # Index findings/caps by (component-artifact-label, goal).
    def _label(rec: dict[str, Any]) -> str:
        ev = rec.get("evidence") or []
        return str(ev[0].get("artifact")) if ev and isinstance(ev[0], dict) else "(unattributed)"
    comp_goal_f: dict[str, dict[str, list[str]]] = {}
    comp_goal_c: dict[str, dict[str, list[str]]] = {}
    for f in findings:
        g = f.get("apd_goal")
        if g in cl.GOAL_SHORT:
            comp_goal_f.setdefault(_label(f), {}).setdefault(g, []).append(f["id"])
    for c in caps:
        g = c.get("apd_goal")
        if g in cl.GOAL_SHORT:
            comp_goal_c.setdefault(_label(c), {}).setdefault(g, []).append(c["id"])
    names = sorted(set(components) | set(comp_goal_f) | set(comp_goal_c))
    rows: list[dict[str, Any]] = []
    for name in names:
        cells: dict[str, Any] = {}
        for goal in cl.GOAL_SHORT:
            fids = sorted(comp_goal_f.get(name, {}).get(goal, []))
            cids = sorted(comp_goal_c.get(name, {}).get(goal, []))
            cells[goal] = {"findings": fids, "capabilities": cids,
                           "posture": cl.posture(has_findings=bool(fids), has_caps=bool(cids))}
        rows.append({"name": name, "cells": cells})
    return rows


def _declared_taxonomies(run_cfg: dict[str, Any]) -> set[str]:
    raw = run_cfg.get("taxonomies") or []
    return {str(t).strip() for t in raw} if isinstance(raw, list) else set()


def _read_records(path: Path, *keys: str) -> list[dict[str, Any]]:
    """Key-tolerant record reader matching loader.load_run's fallbacks so the
    metrics counts equal the transform's view of the same files."""
    if not path.is_file():
        return []
    doc = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(doc, dict):
        return []
    for key in keys:
        value = doc.get(key)
        if isinstance(value, list):
            return [r for r in value if isinstance(r, dict)]
        if isinstance(value, dict):
            return [value]
    return []


def _count_unresolved_merges(path: Path) -> int:
    """Count unresolved authored-merge groups from rejected-records.yaml.

    apply-clusters logs exactly one "fewer than 2 resolvable members" group row
    per merge decision it could not apply (members absent or mixed kinds), so
    counting those rows yields the unresolved-merge count without re-plumbing
    ApplyResult through the rollup.
    """
    rows = _read_records(path, "rejected")
    return sum(
        1 for r in rows
        if "fewer than 2 resolvable members" in str(r.get("reason", ""))
    )


def build_rollups(run_dir: Path) -> RollupResult:
    findings, caps = _load_deduped(run_dir)
    inventory = yaml.safe_load(
        (run_dir / "00-context" / "asset-inventory.yaml").read_text(encoding="utf-8")
    ) or {}
    run_cfg = yaml.safe_load(
        (run_dir / ".apd-run.yaml").read_text(encoding="utf-8")
    ) if (run_dir / ".apd-run.yaml").is_file() else {}
    run_cfg = run_cfg or {}

    result = RollupResult()
    result.nist = _nist_rollup(findings, caps, _nist_titles(), _family_titles())
    result.attack = _attack_rollup(findings, caps)
    result.matrix = _matrix_rollup(findings, caps, inventory)

    declared = _declared_taxonomies(run_cfg)
    if "cwe" in declared:
        result.cwe = _cwe_rollup(findings)
    if declared & {"owasp_top10", "owasp_api_top10", "owasp_llm_top10"}:
        result.owasp = _owasp_rollup(findings, declared)
    if "d3fend" in declared:
        result.d3fend = _d3fend_rollup(findings, caps)
    if "mitre_atlas" in declared:
        result.atlas = _atlas_rollup(findings)
    if "masvs" in declared:
        result.masvs = _masvs_rollup(findings, caps)
    if "maswe" in declared:
        result.maswe = _maswe_rollup(findings)

    synth = run_dir / "40-synthesis"
    contradictions = _read_records(
        synth / "contradictions.yaml", "contradictions", "contradiction")
    sev_dis = _read_records(
        synth / "severity-disagreements.yaml",
        "severity_disagreements", "disagreements", "severity_disagreement")
    # PR3: surface apply-clusters' unresolved authored merges (non-blocking + loud).
    # Counted from rejected-records.yaml: each dropped merge group logs one
    # "fewer than 2 resolvable members" group row, so that string is the count.
    unresolved = _count_unresolved_merges(synth / "rejected-records.yaml")
    # findings already UNION apath-* (via _load_deduped); compute_metrics is the
    # single canonical report summary block.
    result.metrics = compute_metrics(
        findings, caps, contradictions, sev_dis,
        unresolved_authored_merges=unresolved,
    )

    _write(run_dir, result)
    return result


def _cwe_rollup(findings: list[dict[str, Any]]) -> dict[str, Any]:
    cwe_data = json.loads((_PKG_DATA / "cwe.json").read_text(encoding="utf-8"))
    by_id = {e["cwe_id"]: e for e in cwe_data.get("entries", []) if isinstance(e, dict)}
    order: list[str] = []
    grouped: dict[str, dict[str, Any]] = {}
    for f in findings:
        for cid in cl.extract_ids_from_mapping((f.get("control_mappings") or {}).get("cwe")):
            if cid not in grouped:
                grouped[cid] = {"finding_ids": [], "surfaces": set()}
                order.append(cid)
            if f["id"] not in grouped[cid]["finding_ids"]:
                grouped[cid]["finding_ids"].append(f["id"])
            for ev in f.get("evidence") or []:
                if isinstance(ev, dict) and ev.get("locator"):
                    grouped[cid]["surfaces"].add(str(ev["locator"]))
    entries = []
    for cid in sorted(order, key=lambda c: (order.index(c), c)):
        ref = by_id.get(cid, {})
        parents = ref.get("parents") or []
        entries.append({
            "cwe_id": cid, "name": ref.get("name", cid),
            "abstraction": ref.get("abstraction", "base"),
            "parent_pillar": parents[0] if parents else None,
            "finding_count": len(grouped[cid]["finding_ids"]),
            "finding_ids": sorted(grouped[cid]["finding_ids"]),
            "surfaces": sorted(grouped[cid]["surfaces"]),
        })
    return {"schema_version": 1, "generated_by": "synthesizer", "entries": entries}


def _atlas_rollup(findings: list[dict[str, Any]]) -> dict[str, Any]:
    # Mirrors _cwe_rollup: ATLAS is a flat technique-id list on
    # control_mappings.atlas (AML.T####[.###]). Names resolve from the bundled
    # ATLAS catalog (report.taxonomy.atlas_titles → {id: name}), falling back to
    # the id on miss. First-appearance order over the deduped finding order.
    names = atlas_titles()
    order: list[str] = []
    grouped: dict[str, dict[str, Any]] = {}
    for f in findings:
        for aid in cl.extract_ids_from_mapping((f.get("control_mappings") or {}).get("atlas")):
            if aid not in grouped:
                grouped[aid] = {"finding_ids": [], "surfaces": set()}
                order.append(aid)
            if f["id"] not in grouped[aid]["finding_ids"]:
                grouped[aid]["finding_ids"].append(f["id"])
            for ev in f.get("evidence") or []:
                if isinstance(ev, dict) and ev.get("locator"):
                    grouped[aid]["surfaces"].add(str(ev["locator"]))
    entries = []
    for aid in sorted(order, key=lambda a: (order.index(a), a)):
        entries.append({
            "atlas_id": aid, "name": names.get(aid, aid),
            "finding_count": len(grouped[aid]["finding_ids"]),
            "finding_ids": sorted(grouped[aid]["finding_ids"]),
            "surfaces": sorted(grouped[aid]["surfaces"]),
        })
    return {"schema_version": 1, "generated_by": "synthesizer", "entries": entries}


def _maswe_rollup(findings: list[dict[str, Any]]) -> dict[str, Any]:
    # Mirrors _cwe_rollup: MASWE is a flat weakness-id list on
    # control_mappings.maswe (MASWE-####). name/category/status/parent_masvs
    # resolve from the bundled OWASP MAS catalog (data/maswe.json, weaknesses
    # map), falling back to the id (name) / None (category, status) / [] on miss.
    # First-appearance order over the deduped finding order, then by id.
    maswe_data = json.loads((_PKG_DATA / "maswe.json").read_text(encoding="utf-8"))
    by_id = maswe_data.get("weaknesses", {})
    order: list[str] = []
    grouped: dict[str, dict[str, Any]] = {}
    for f in findings:
        for wid in cl.extract_ids_from_mapping((f.get("control_mappings") or {}).get("maswe")):
            if wid not in grouped:
                grouped[wid] = {"finding_ids": [], "surfaces": set()}
                order.append(wid)
            if f["id"] not in grouped[wid]["finding_ids"]:
                grouped[wid]["finding_ids"].append(f["id"])
            for ev in f.get("evidence") or []:
                if isinstance(ev, dict) and ev.get("locator"):
                    grouped[wid]["surfaces"].add(str(ev["locator"]))
    entries = []
    for wid in sorted(order, key=lambda w: (order.index(w), w)):
        ref = by_id.get(wid, {})
        entries.append({
            "maswe_id": wid, "name": ref.get("title") or wid,
            "category": ref.get("category"),
            "status": ref.get("status"),
            "parent_masvs": list(ref.get("masvs_v2") or []),
            "finding_count": len(grouped[wid]["finding_ids"]),
            "finding_ids": sorted(grouped[wid]["finding_ids"]),
            "surfaces": sorted(grouped[wid]["surfaces"]),
        })
    return {"schema_version": 1, "generated_by": "synthesizer", "entries": entries}


def _masvs_catalog() -> dict[str, dict[str, Any]]:
    """Return {masvs_id: {title, category, category_title}} from data/masvs.json."""
    raw = json.loads((_PKG_DATA / "masvs.json").read_text(encoding="utf-8"))
    controls = raw.get("controls", {})
    return controls if isinstance(controls, dict) else {}


def _masvs_cap_index(caps: list[dict[str, Any]]) -> dict[str, set[str]]:
    """Return {masvs_id: {cap_id, ...}} for capabilities citing control_mappings.masvs."""
    index: dict[str, set[str]] = {}
    for cap in caps:
        cap_id = cap.get("id", "")
        cm = cap.get("control_mappings") or {}
        for mid in cl.extract_ids_from_mapping(cm.get("masvs")):
            index.setdefault(mid, set()).add(cap_id)
    return index


def _masvs_rollup(
    findings: list[dict[str, Any]],
    caps: list[dict[str, Any]],
) -> dict[str, Any]:
    # Mirrors _nist_rollup: per-control union of finding_ids + capability_ids,
    # posture from coverage_logic.posture(), name/category/category_title from
    # the bundled OWASP MAS catalog (data/masvs.json). First-appearance order
    # over the deduped finding order, with cap-only controls sorted in by id.
    catalog = _masvs_catalog()
    order: list[str] = []
    fmap: dict[str, list[str]] = {}
    surfaces: dict[str, set[str]] = {}
    for f in findings:
        for mid in cl.extract_ids_from_mapping((f.get("control_mappings") or {}).get("masvs")):
            if mid not in fmap:
                fmap[mid] = []
                surfaces[mid] = set()
                order.append(mid)
            if f["id"] not in fmap[mid]:
                fmap[mid].append(f["id"])
            for ev in f.get("evidence") or []:
                if isinstance(ev, dict) and ev.get("locator"):
                    surfaces[mid].add(str(ev["locator"]))
    cap_index = _masvs_cap_index(caps)
    all_ids = set(order) | set(cap_index)
    order_index = {c: i for i, c in enumerate(order)}
    controls: list[dict[str, Any]] = []
    for mid in sorted(all_ids, key=lambda c: (order_index.get(c, 1_000_000), c)):
        fids = sorted(fmap.get(mid, []))
        cids = sorted(cap_index.get(mid, set()))
        ref = catalog.get(mid, {})
        controls.append({
            "masvs_id": mid,
            "name": ref.get("title") or mid,
            "category": ref.get("category"),
            "category_title": ref.get("category_title"),
            "finding_count": len(fids), "finding_ids": fids,
            "surfaces": sorted(surfaces.get(mid, set())),
            "capability_count": len(cids), "capability_ids": cids,
            "posture": cl.posture(has_findings=bool(fids), has_caps=bool(cids)),
        })
    return {"schema_version": 1, "generated_by": "synthesizer", "controls": controls}


def _owasp_names(tax_key: str) -> dict[str, str]:
    """Return {category_id: name} from the bundled owasp_*.json catalog (I2).

    The data files are {"entries": [{category_id, name}, ...]}; the golden
    owasp-coverage carries real names (e.g. "Broken Authentication"), so a
    raw-id name diverges. Falls back to {} (callers use category_id) on miss.
    """
    path = _PKG_DATA / f"{tax_key}.json"
    if not path.is_file():
        return {}
    raw = json.loads(path.read_text(encoding="utf-8"))
    out: dict[str, str] = {}
    for entry in (raw.get("entries") or []) if isinstance(raw, dict) else []:
        if isinstance(entry, dict) and entry.get("category_id"):
            out[entry["category_id"]] = entry.get("name") or entry["category_id"]
    return out


def _owasp_rollup(findings: list[dict[str, Any]], declared: set[str]) -> dict[str, Any]:
    entries = []
    for tax_key, field_key in (("owasp_top10", "owasp_top10"),
                               ("owasp_api_top10", "owasp_api_top10"),
                               ("owasp_llm_top10", "owasp_llm_top10")):
        if tax_key not in declared:
            continue
        names = _owasp_names(tax_key)
        grouped: dict[str, dict[str, Any]] = {}
        order: list[str] = []
        for f in findings:
            mappings = (f.get("control_mappings") or {}).get(field_key)
            for cat in cl.extract_ids_from_mapping(mappings):
                if cat not in grouped:
                    grouped[cat] = {"finding_ids": [], "surfaces": set()}
                    order.append(cat)
                grouped[cat]["finding_ids"].append(f["id"])
                for ev in f.get("evidence") or []:
                    if isinstance(ev, dict) and ev.get("locator"):
                        grouped[cat]["surfaces"].add(str(ev["locator"]))
        for cat in sorted(order, key=lambda c: (order.index(c), c)):
            entries.append({
                "taxonomy": tax_key, "category_id": cat, "name": names.get(cat, cat),
                "finding_count": len(grouped[cat]["finding_ids"]),
                "finding_ids": sorted(grouped[cat]["finding_ids"]),
                "surfaces": sorted(grouped[cat]["surfaces"]), "silent": False,
            })
    return {"schema_version": 1, "generated_by": "synthesizer", "entries": entries}


def _d3fend_rollup(
    findings: list[dict[str, Any]],
    caps: list[dict[str, Any]],
) -> dict[str, Any]:
    # I2: the golden d3fend-coverage carries real names (e.g. "Agent
    # Authentication"); name=d["technique"] (the raw id) diverges. Look up from
    # the bundled D3FEND catalog (report.taxonomy.d3fend_titles → {id: name}),
    # falling back to the id on miss.
    d3_names = d3fend_titles()
    # Fix 2: group by d3fend_id so two caps citing the same technique → one row.
    def_order: list[str] = []
    def_grouped: dict[str, dict[str, Any]] = {}
    for cap in caps:
        for d in (cap.get("control_mappings") or {}).get("d3fend") or []:
            if isinstance(d, dict) and d.get("technique"):
                did = d["technique"]
                if did not in def_grouped:
                    def_grouped[did] = {
                        "cap_ids": [],
                        "counters_attack": set(),
                    }
                    def_order.append(did)
                if cap["id"] not in def_grouped[did]["cap_ids"]:
                    def_grouped[did]["cap_ids"].append(cap["id"])
                for atk in (d.get("counters_attack") or []):
                    def_grouped[did]["counters_attack"].add(atk)
    defensive = []
    for did in sorted(def_order):
        grp = def_grouped[did]
        cap_ids = sorted(grp["cap_ids"])
        defensive.append({
            "d3fend_id": did, "name": d3_names.get(did, did),
            "capability_count": len(cap_ids), "capability_ids": cap_ids,
            "counters_attack": sorted(grp["counters_attack"]),
        })
    # Fix 3: group counter_coverage by attack_technique — one row per technique.
    ctr_order: list[str] = []
    ctr_grouped: dict[str, dict[str, Any]] = {}
    for f in findings:
        for m in (f.get("control_mappings") or {}).get("mitre_attack") or []:
            tid = m.get("technique") if isinstance(m, dict) else None
            if tid:
                if tid not in ctr_grouped:
                    ctr_grouped[tid] = {"finding_ids": []}
                    ctr_order.append(tid)
                if f["id"] not in ctr_grouped[tid]["finding_ids"]:
                    ctr_grouped[tid]["finding_ids"].append(f["id"])
    counter = []
    for tid in sorted(ctr_order):
        fids = sorted(ctr_grouped[tid]["finding_ids"])
        counter.append({
            "attack_technique": tid, "exposed_by_finding_count": len(fids),
            "exposed_by_finding_ids": fids,
            "countered_by_d3fend": [], "countered_by_capability_ids": [],
            "has_capability_coverage": False,
        })
    return {"schema_version": 1, "generated_by": "synthesizer",
            "defensive_entries": defensive, "counter_coverage": counter}


def _write(run_dir: Path, result: RollupResult) -> None:
    synth = run_dir / "40-synthesis"
    synth.mkdir(parents=True, exist_ok=True)
    (synth / "nist-coverage.yaml").write_text(
        yaml.safe_dump({"controls": result.nist}, sort_keys=False), encoding="utf-8")
    (synth / "attack-exposure.yaml").write_text(
        yaml.safe_dump({"techniques": result.attack}, sort_keys=False), encoding="utf-8")
    (synth / "apd-coverage-matrix.yaml").write_text(
        yaml.safe_dump({"components": result.matrix}, sort_keys=False), encoding="utf-8")
    (synth / "metrics.yaml").write_text(
        yaml.safe_dump(result.metrics, sort_keys=False), encoding="utf-8")
    if result.cwe is not None:
        (synth / "cwe-coverage.yaml").write_text(
            yaml.safe_dump(result.cwe, sort_keys=False), encoding="utf-8")
    if result.owasp is not None:
        (synth / "owasp-coverage.yaml").write_text(
            yaml.safe_dump(result.owasp, sort_keys=False), encoding="utf-8")
    if result.d3fend is not None:
        (synth / "d3fend-coverage.yaml").write_text(
            yaml.safe_dump(result.d3fend, sort_keys=False), encoding="utf-8")
    if result.atlas is not None:
        (synth / "atlas-coverage.yaml").write_text(
            yaml.safe_dump(result.atlas, sort_keys=False), encoding="utf-8")
    if result.masvs is not None:
        (synth / "masvs-coverage.yaml").write_text(
            yaml.safe_dump(result.masvs, sort_keys=False), encoding="utf-8")
    if result.maswe is not None:
        (synth / "maswe-coverage.yaml").write_text(
            yaml.safe_dump(result.maswe, sort_keys=False), encoding="utf-8")
