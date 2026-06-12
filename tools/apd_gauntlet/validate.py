"""Validation engine — Pass 1 (schema), Pass 2 (semantic lints), Pass 3 (cross-file)."""
from __future__ import annotations

import json
import pathlib
from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Any

import yaml
from jsonschema import Draft202012Validator
from referencing import Registry, Resource

from . import linters
from .report import taxonomy as _taxonomy

REPO = pathlib.Path(__file__).resolve().parent.parent.parent
SCHEMAS_DIR = REPO / "schemas"

# Map record kind → (schema filename, root key in YAML, filename glob)
RECORD_KINDS: dict[str, tuple[str, str, str]] = {
    "finding":    ("finding.schema.json",    "finding",    "*.findings.yaml"),
    "capability": ("capability.schema.json", "capability", "*.capabilities.yaml"),
}

# Correct plural root keys. `root_key + "s"` is WRONG for "capability"
# ("capabilitys"); agents emit "capabilities". Keep this the single source.
_PLURAL_ROOT: dict[str, str] = {"finding": "findings", "capability": "capabilities"}


@dataclass
class Violation:
    file: pathlib.Path
    record_id: str | None
    message: str
    path: str = ""

    def render(self) -> str:
        loc = str(self.file)
        if self.record_id:
            loc += f" [{self.record_id}]"
        if self.path:
            loc += f" {self.path}"
        return f"{loc}: {self.message}"


@dataclass
class ValidationReport:
    errors:   list[Violation] = field(default_factory=list)
    warnings: list[Violation] = field(default_factory=list)
    files_seen:   int = 0
    records_seen: int = 0

    @property
    def is_clean(self) -> bool:
        return not self.errors

    def render(self) -> str:
        lines = [f"Files scanned: {self.files_seen}  Records: {self.records_seen}"]
        for v in self.errors:
            lines.append(f"ERROR   {v.render()}")
        for v in self.warnings:
            lines.append(f"WARNING {v.render()}")
        if self.is_clean and not self.warnings:
            lines.append("Clean.")
        return "\n".join(lines)


def build_registry() -> Registry:
    """Build a referencing Registry covering every schema in schemas/.

    Each schema is registered under its declared ``$id``. This lets cross-schema
    ``$ref`` resolve — notably the shared patterns in ``_defs.schema.json``.
    """
    resources: list[tuple[str, Resource[Any]]] = []
    for schema_path in sorted(SCHEMAS_DIR.glob("*.schema.json")):
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        schema_id = schema.get("$id")
        if not schema_id:
            continue
        resources.append((schema_id, Resource.from_contents(schema)))
    return Registry().with_resources(resources)


def extract_records(doc: dict[str, Any], root_key: str) -> list[dict[str, Any]]:
    """Return the bare record dicts from a findings/capabilities document.

    The single shared extraction rule used by canonicalize, ``_iter_records``,
    ``check-ids``, and the synthesis loader — so they cannot drift. Accepts:

    - the canonical singular root key (``finding`` / ``capability``) whose value
      is a list of bare records (or a single bare record), AND
    - the legacy plural root key (``findings`` / ``capabilities``), AND
    - per-record wrappers of the form ``{<root_key>: {...}}`` (unwrapped here).

    Non-dict items are dropped. This is extraction only; it does not validate.
    """
    raw = doc.get(root_key)
    if raw is None:
        raw = doc.get(_PLURAL_ROOT.get(root_key, root_key + "s"))
    items = raw if isinstance(raw, list) else ([raw] if isinstance(raw, dict) else [])
    out: list[dict[str, Any]] = []
    for item in items:
        if (
            isinstance(item, dict)
            and set(item.keys()) == {root_key}
            and isinstance(item[root_key], dict)
        ):
            item = item[root_key]  # unwrap a per-record {finding: {...}} wrapper
        if isinstance(item, dict):
            out.append(item)
    return out


def _iter_records(run_dir: pathlib.Path) -> Iterable[tuple[pathlib.Path, str, dict[str, Any]]]:
    """Yield (file_path, kind, record_dict) for every YAML record in the run.

    Uses the shared ``extract_records`` extraction (singular-or-plural root key,
    per-record unwrap) so per-record checks run even on non-canonical files —
    no vacuous pass. The non-canonical envelope itself is flagged separately by
    ``_check_envelopes``.
    """
    for kind, (_schema, root_key, glob) in RECORD_KINDS.items():
        for path in sorted(run_dir.rglob(glob)):
            try:
                data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            except yaml.YAMLError as e:
                yield path, kind, {"_parse_error": str(e)}
                continue
            if not isinstance(data, dict):
                continue
            for record in extract_records(data, root_key):
                yield path, kind, record


def _non_canonical_envelope_reason(doc: dict[str, Any], root_key: str) -> str | None:
    """Return a human reason if doc's envelope is non-canonical, else None."""
    plural = _PLURAL_ROOT.get(root_key, root_key + "s")
    if root_key not in doc and plural in doc:
        return f"plural root key '{plural}'"
    raw = doc.get(root_key)
    items = raw if isinstance(raw, list) else ([raw] if isinstance(raw, dict) else [])
    for item in items:
        if (
            isinstance(item, dict)
            and set(item.keys()) == {root_key}
            and isinstance(item[root_key], dict)
        ):
            return f"per-record '{root_key}:' wrapper"
    return None


def _check_envelopes(run_dir: pathlib.Path, report: ValidationReport) -> None:
    """Hard ERROR when a lens findings/capabilities file uses a plural root key
    or wraps any record in a per-record ``{<kind>: {...}}`` wrapper. canonicalize
    is the normalizer; validate refuses to silently accept non-canonical input."""
    for _kind, (_schema, root_key, glob) in RECORD_KINDS.items():
        for path in sorted(run_dir.rglob(glob)):
            try:
                # NOTE: intentional second parse — run_schema_pass already iterated
                # records, but the raw doc is discarded; re-reading here keeps the
                # envelope check independent of the per-record pass.
                doc = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            except yaml.YAMLError:
                continue  # parse errors are reported by the schema pass
            if not isinstance(doc, dict):
                continue
            reason = _non_canonical_envelope_reason(doc, root_key)
            if reason:
                report.errors.append(
                    Violation(
                        path,
                        None,
                        f"non-canonical envelope ({reason}): use singular root key "
                        f"'{root_key}' with bare records (run 'apd-gauntlet canonicalize')",
                    )
                )


# G7: every *.findings.yaml / *.capabilities.yaml must live DIRECTLY under one of
# these canonical run subdirs. The three tier dirs mirror the runTier tier names
# (trustworthiness / scalability / auditability), plus the two tier-4 output dirs
# (40-synthesis for the synthesizer + attack-path analyzer; 40-threat-model for the
# threat-model evaluator). A record file anywhere else (e.g. a phantom
# 20-findings/40-threat-model/ path) is rejected by run_cross_file_pass.
CANONICAL_RECORD_DIRS: frozenset[str] = frozenset({
    "10-trustworthiness",
    "20-scalability",
    "30-auditability",
    "40-synthesis",
    "40-threat-model",
})


CODE_EVIDENCE_INDEX_FILENAME = "code-evidence-index.yaml"

# Issue #86: tier-4 analyzers legitimately cite their own derived synthesis
# outputs as evidence (paths relative to the run root, exactly as the agents
# emit them). These are always-known artifacts and must not be flagged as
# "not in intake brief". Keep this set narrow — do NOT broaden the artifact
# check beyond these specific analyzer-derived files.
ANALYZER_DERIVED_ARTIFACTS: frozenset[str] = frozenset({
    "40-synthesis/asset-graph.yaml",          # attack-path analyzer
    "40-synthesis/attack-paths.yaml",         # attack-path analyzer
    "40-synthesis/defense-graph.yaml",        # attack-path analyzer
    "40-synthesis/deduped-findings.yaml",     # threat-model evaluator + attack-path analyzer
    "40-synthesis/deduped-capabilities.yaml",  # threat-model evaluator + attack-path analyzer
})

# FW-3: 00-context generated run-context artifacts. Specialists — especially
# the tier-4 threat-model evaluator (which MUST cite the normalized threat
# model) and attack-path analyzer — legitimately cite these derived context
# files as evidence and must not be flagged "not in intake brief". Each is
# allow-listed ONLY when it actually exists on disk (mirrors the
# code-evidence-index existence guard below — never grant an implicit pass to a
# context file the run did not produce). Both the bare basename and the
# ``00-context/``-prefixed form agents emit are accepted. Excluded by design:
# context-brief.md (cite the underlying artifact, not the brief's summary) and
# code-evidence-index.yaml (handled by its own existence guard in
# run_cross_file_pass).
CONTEXT_DERIVED_STEMS: tuple[str, ...] = (
    "threat-model-normalized.yaml",
    "threat-model-authored.md",
    "threat-model-skeleton.yaml",
    "threat-model-supplied-normalized.yaml",
    "asset-inventory.yaml",
    "code-architecture-brief.md",
)

# Whole-document rollup files in 40-synthesis/ that get schema-validated by the
# CLI. Each entry maps the on-disk filename to the schema in schemas/.
# Note: attack-path.findings.yaml is NOT listed here — post-C-20 it matches the
# ``*.findings.yaml`` glob in RECORD_KINDS and is validated per-record.
SYNTHESIS_ROLLUPS: dict[str, str] = {
    "cwe-coverage.yaml":           "cwe-coverage.schema.json",
    "owasp-coverage.yaml":         "owasp-coverage.schema.json",
    "d3fend-coverage.yaml":        "d3fend-coverage.schema.json",
    "atlas-coverage.yaml":         "atlas-coverage.schema.json",
    # v1.7 — OWASP MAS (mobile) coverage rollups. Single-file convention like
    # cwe-coverage (no -doc wrapper); registered directly here.
    "masvs-coverage.yaml":         "masvs-coverage.schema.json",
    "maswe-coverage.yaml":         "maswe-coverage.schema.json",
    "threat-model-coverage.yaml":  "threat-model-coverage.schema.json",
    # C-21: Phase C synthesis artifacts
    "asset-graph.yaml":            "asset-graph.schema.json",
    "attack-paths.yaml":           "attack-path.schema.json",
    "defense-graph.yaml":          "defense-graph.schema.json",
    # D: HTML report input
    "report-data.yaml":            "report-data.schema.json",
    # The canonical report summary block (unified-metrics-model).
    "metrics.yaml":                "metrics.schema.json",
    # Plan 2 — synthesis decomposition artifacts.
    "cluster-candidates.yaml":     "cluster-candidates.schema.json",
    "cluster-decisions.yaml":      "cluster-decisions.schema.json",
    "rejected-records.yaml":       "rejected-records.schema.json",
    "report-audit.yaml":           "report-audit.schema.json",
    # Plan 3 — the three coverage rollups, now wired globally against their
    # array-shaped *-doc wrapper schemas. The legacy runs/ were regenerated to
    # the array shape via `apd-gauntlet rollup` (Plan 3 Task B), so this no
    # longer breaks validate on the committed runs. The matrix doc schema is
    # named coverage-matrix-doc.schema.json (NOT apd-coverage-matrix-doc); all
    # three map to the DOC wrappers (array-of-$ref), never the per-row schemas.
    "nist-coverage.yaml":          "nist-coverage-doc.schema.json",
    "attack-exposure.yaml":        "attack-exposure-doc.schema.json",
    "apd-coverage-matrix.yaml":    "coverage-matrix-doc.schema.json",
    # Plan 2 (I5) — apply-clusters annex outputs, previously unwired so a
    # malformed annex slipped past validate --schema-only. Wrap the existing
    # per-row severity-disagreement / contradiction schemas.
    "severity-disagreements.yaml": "severity-disagreements-doc.schema.json",
    "contradictions.yaml":         "contradictions-doc.schema.json",
    # Subsystem B — domain-improvement capture artifacts. The doc wrapper's
    # improvements[].items.$ref is the absolute $id of domain-improvement.schema.json,
    # which build_registry() indexes, so each record validates against the record
    # schema with no further wiring. Neither file is a *.findings.yaml, so neither
    # enters _iter_records / the semantic pass / cross-file finding-id resolution.
    "domain-coverage-delta.yaml":  "domain-coverage-delta-doc.schema.json",
    "domain-improvements.yaml":    "domain-improvements-doc.schema.json",
}

# Whole-document rollup files in 00-context/ that get schema-validated by the
# CLI. Each entry maps the on-disk filename to the schema in schemas/.
CONTEXT_ROLLUPS: dict[str, str] = {
    "threat-model-normalized.yaml": "threat-model-normalized.schema.json",
    # The supplied-TM sibling parsed by recon when a TM is supplied. It shares
    # the normalized-TM schema (the authoring effort widened that schema's
    # generated_by enum to include threat_model_author); the sibling itself is
    # recon output, so it carries generated_by: threat_model_recon. Wiring it
    # here ensures a malformed sibling is caught the same way the canonical
    # baseline is.
    "threat-model-supplied-normalized.yaml": "threat-model-normalized.schema.json",
    # C-21: Phase C intake artifact (emitted by the intake step).
    "asset-inventory.yaml":         "asset-inventory.schema.json",
}


def _code_evidence_index_path(run_dir: pathlib.Path) -> pathlib.Path:
    return run_dir / "00-context" / CODE_EVIDENCE_INDEX_FILENAME


def _validate_code_evidence_index(
    run_dir: pathlib.Path, report: ValidationReport, registry: Registry
) -> None:
    """If code-evidence-index.yaml exists, schema-validate it. Errors append to report."""
    path = _code_evidence_index_path(run_dir)
    if not path.exists():
        return
    schema = json.loads(
        (SCHEMAS_DIR / "code-evidence-index.schema.json").read_text(encoding="utf-8")
    )
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as e:
        report.errors.append(Violation(path, None, f"YAML parse error: {e}"))
        return
    validator = Draft202012Validator(schema, registry=registry)
    for err in validator.iter_errors(data):
        report.errors.append(Violation(path, None, err.message, "/".join(map(str, err.path))))


def _validate_synthesis_rollups(
    run_dir: pathlib.Path,
    report: ValidationReport,
    registry: Registry,
    seen_files: set[pathlib.Path],
) -> None:
    """Schema-validate each present coverage rollup under 40-synthesis/.

    Walks ``SYNTHESIS_ROLLUPS`` so the validator catches malformed CWE / OWASP /
    D3FEND coverage rollups the same way it catches malformed findings. Missing
    rollups are silent (these files are optional). Discovered files are added
    to ``seen_files`` so ``files_seen`` reflects them.
    """
    synthesis_dir = run_dir / "40-synthesis"
    if not synthesis_dir.exists():
        return
    for filename, schema_name in SYNTHESIS_ROLLUPS.items():
        path = synthesis_dir / filename
        if not path.exists():
            continue
        seen_files.add(path)
        schema = json.loads((SCHEMAS_DIR / schema_name).read_text(encoding="utf-8"))
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        except yaml.YAMLError as e:
            report.errors.append(Violation(path, None, f"YAML parse error: {e}"))
            continue
        validator = Draft202012Validator(schema, registry=registry)
        for err in validator.iter_errors(data):
            report.errors.append(
                Violation(path, None, err.message, "/".join(map(str, err.path)))
            )


def _validate_context_rollups(
    run_dir: pathlib.Path,
    report: ValidationReport,
    registry: Registry,
    seen_files: set[pathlib.Path],
) -> None:
    """Schema-validate each present rollup under 00-context/.

    Walks ``CONTEXT_ROLLUPS`` so the validator catches malformed threat-model
    rollups the same way it catches malformed findings. Missing rollups are
    silent (these files are optional). Discovered files are added to
    ``seen_files`` so ``files_seen`` reflects them.
    """
    context_dir = run_dir / "00-context"
    if not context_dir.exists():
        return
    for filename, schema_name in CONTEXT_ROLLUPS.items():
        path = context_dir / filename
        if not path.exists():
            continue
        seen_files.add(path)
        schema = json.loads((SCHEMAS_DIR / schema_name).read_text(encoding="utf-8"))
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        except yaml.YAMLError as e:
            report.errors.append(Violation(path, None, f"YAML parse error: {e}"))
            continue
        validator = Draft202012Validator(schema, registry=registry)
        for err in validator.iter_errors(data):
            report.errors.append(
                Violation(path, None, err.message, "/".join(map(str, err.path)))
            )


def run_schema_pass(run_dir: pathlib.Path) -> ValidationReport:
    """Pass 1: validate every record against its JSON Schema."""
    registry = build_registry()
    report = ValidationReport()
    validators = {
        kind: Draft202012Validator(
            json.loads((SCHEMAS_DIR / schema).read_text(encoding="utf-8")),
            registry=registry,
        )
        for kind, (schema, _, _) in RECORD_KINDS.items()
    }
    seen_files: set[pathlib.Path] = set()
    for path, kind, record in _iter_records(run_dir):
        seen_files.add(path)
        if "_parse_error" in record:
            report.errors.append(
                Violation(path, None, f"YAML parse error: {record['_parse_error']}")
            )
            continue
        report.records_seen += 1
        validator = validators[kind]
        rid = record.get("id")
        for err in validator.iter_errors(record):
            report.errors.append(Violation(path, rid, err.message, "/".join(map(str, err.path))))
    _validate_code_evidence_index(run_dir, report, registry)
    _validate_context_rollups(run_dir, report, registry, seen_files)
    _validate_synthesis_rollups(run_dir, report, registry, seen_files)
    _check_envelopes(run_dir, report)
    report.files_seen = len(seen_files)
    return report


def parse_intake_brief(brief_path: pathlib.Path) -> dict[str, Any]:
    """Extract the YAML frontmatter block from context-brief.md."""
    if not brief_path.exists():
        return {}
    text = brief_path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return {}
    end = text.find("\n---\n", 4)
    if end < 0:
        return {}
    return yaml.safe_load(text[4:end]) or {}


def run_semantic_pass(
    run_dir: pathlib.Path,
    tech_plan_artifacts: set[str] | None = None,
) -> ValidationReport:
    """Pass 2: semantic lints that JSON Schema cannot express."""
    tech_plan_artifacts = tech_plan_artifacts or set()
    report = ValidationReport()
    seen_files: set[pathlib.Path] = set()
    # G6: build the {cwe_id: abstraction} index once from the single bundled-catalog
    # loader, then enforce concrete-CWE resolution per finding (reachable here at the
    # tier gate, not only the late report-audit).
    cwe_index = _taxonomy.cwe_abstractions()
    maswe_parents = _taxonomy.maswe_masvs_parents()
    for path, kind, record in _iter_records(run_dir):
        if "_parse_error" in record:
            continue
        seen_files.add(path)
        rid = record.get("id")
        report.records_seen += 1
        if kind == "finding":
            for msg in linters.check_excerpt_length(record):
                report.errors.append(Violation(path, rid, msg))
            for msg in linters.check_cwe_resolves(record, cwe_index):
                report.errors.append(Violation(path, rid, msg))
            for msg in linters.check_finding_id(record):
                report.errors.append(Violation(path, rid, msg))
            for msg in linters.check_id_present(record):
                report.errors.append(Violation(path, rid, msg))
            for msg in linters.check_lens_consistency(record):
                report.errors.append(Violation(path, rid, msg))
            for msg in linters.check_hedge_words_in_attack_rationale(record):
                report.warnings.append(Violation(path, rid, msg))
            for msg in linters.check_maswe_masvs_consistency(record, maswe_parents):
                report.warnings.append(Violation(path, rid, msg))
            for msg in linters.check_tmeval_evidence_pointer(record):
                report.errors.append(Violation(path, rid, msg))
            for msg in linters.check_tmeval_contradiction_cross_reference(record):
                report.errors.append(Violation(path, rid, msg))
            for msg in linters.check_tmeval_id(record):
                report.errors.append(Violation(path, rid, msg))
        elif kind == "capability":
            for msg in linters.check_excerpt_length(record):
                report.errors.append(Violation(path, rid, msg))
            for msg in linters.check_capability_id(record):
                report.errors.append(Violation(path, rid, msg))
            for msg in linters.check_id_present(record):
                report.errors.append(Violation(path, rid, msg))
            for msg in linters.check_lens_consistency(record):
                report.errors.append(Violation(path, rid, msg))
            for msg in linters.check_capability_maturity_evidence(record, tech_plan_artifacts):
                report.errors.append(Violation(path, rid, msg))
            for msg in linters.check_d3fend_counters_attack(record):
                report.errors.append(Violation(path, rid, msg))
    report.files_seen = len(seen_files)
    return report


def _validate_report_data_cross_refs(
    run_dir: pathlib.Path,
    report: ValidationReport,
) -> None:
    """Verify report-data.yaml references point at real findings / capabilities."""
    path = run_dir / "40-synthesis" / "report-data.yaml"
    if not path.exists():
        return
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError:
        return  # schema pass already complained
    finding_ids: set[str] = set()
    capability_ids: set[str] = set()
    for _p, kind, rec in _iter_records(run_dir):
        if "_parse_error" in rec or "id" not in rec:
            continue
        (finding_ids if kind == "finding" else capability_ids).add(rec["id"])
    # Union in the DEDUPED corpus the report-writer actually ranks from. A
    # multi-member cluster minted by apply.py gets a 'merged-<sha8>' id that
    # exists ONLY in 40-synthesis/deduped-{findings,capabilities}.yaml — whose
    # filenames do NOT match the *.findings.yaml / *.capabilities.yaml globs, so
    # _iter_records never sees them. The report legitimately headlines such a
    # merged-* id, so it must resolve (mirrors _validate_domain_improvements_cross_refs).
    for fname, idset in (
        ("deduped-findings.yaml", finding_ids),
        ("deduped-capabilities.yaml", capability_ids),
    ):
        deduped_path = run_dir / "40-synthesis" / fname
        if not deduped_path.exists():
            continue
        try:
            deduped = yaml.safe_load(deduped_path.read_text(encoding="utf-8")) or {}
        except yaml.YAMLError:
            continue  # the schema pass already complained
        root_key = "finding" if "findings" in fname else "capability"
        for rec in deduped.get(root_key) or []:
            if isinstance(rec, dict) and rec.get("id"):
                idset.add(rec["id"])

    for entry in data.get("headline_findings") or []:
        rid = entry.get("id")
        if rid and rid not in finding_ids:
            report.errors.append(Violation(
                path, rid,
                f"headline_findings references unknown finding {rid!r}",
            ))
    for entry in data.get("strengths") or []:
        rid = entry.get("id")
        if rid and rid not in capability_ids:
            report.errors.append(Violation(
                path, rid,
                f"strengths references unknown capability {rid!r}",
            ))
    for entry in data.get("next_steps") or []:
        for rid in entry.get("refs") or []:
            if rid not in finding_ids and rid not in capability_ids:
                report.errors.append(Violation(
                    path, rid,
                    f"next_steps refs include unknown id {rid!r} "
                    "(must match a finding or capability)",
                ))


def _validate_domain_improvements_cross_refs(
    run_dir: pathlib.Path,
    report: ValidationReport,
) -> None:
    """Subsystem B (§4.3): resolve every domain-improvement evidence[].ref and
    recompute each dimpr- id. This is the ONE pass that walks the improvements
    doc — it is not a *.findings.yaml, so it never enters _iter_records / the
    semantic pass. Both checks live here.
    """
    path = run_dir / "40-synthesis" / "domain-improvements.yaml"
    if not path.exists():
        return
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError:
        return  # the schema pass already complained

    # Real finding ids in the SETTLED corpus the agent actually reads. Two sources,
    # unioned:
    #   (a) _iter_records — globs *.findings.yaml (the per-lens / attack-path /
    #       (legacy) merged.findings.yaml files), the synthesizer-fallback path.
    #   (b) 40-synthesis/deduped-findings.yaml (root key 'finding') — the DEDUPED
    #       corpus. Its filename does NOT match the *.findings.yaml glob, so
    #       _iter_records never sees it; yet a multi-member cluster minted by
    #       apply.py gets a 'merged-<sha8>' id that exists ONLY here in a decomposed
    #       run (the decomposed apply path writes no merged.findings.yaml). The
    #       auditor legitimately cites such a merged-* id as evidence, so it must
    #       resolve. Union (b) in so a real merged-* ref is not a false positive.
    finding_ids: set[str] = set()
    for _p, kind, rec in _iter_records(run_dir):
        if "_parse_error" in rec or "id" not in rec:
            continue
        if kind == "finding":
            finding_ids.add(rec["id"])
    deduped_path = run_dir / "40-synthesis" / "deduped-findings.yaml"
    if deduped_path.exists():
        try:
            deduped = yaml.safe_load(deduped_path.read_text(encoding="utf-8")) or {}
        except yaml.YAMLError:
            deduped = {}
        for rec in deduped.get("finding") or []:
            if isinstance(rec, dict) and rec.get("id"):
                finding_ids.add(rec["id"])

    # Real asset/identity/boundary ids in the inventory.
    inv_path = run_dir / "00-context" / "asset-inventory.yaml"
    inventory_ids: set[str] = set()
    if inv_path.exists():
        try:
            inv = yaml.safe_load(inv_path.read_text(encoding="utf-8")) or {}
        except yaml.YAMLError:
            inv = {}
        for a in inv.get("assets") or []:
            if isinstance(a, dict) and a.get("asset_id"):
                inventory_ids.add(a["asset_id"])
        for i in inv.get("identities") or []:
            if isinstance(i, dict) and i.get("identity_id"):
                inventory_ids.add(i["identity_id"])
        for b in inv.get("trust_boundaries") or []:
            if isinstance(b, dict) and b.get("boundary_id"):
                inventory_ids.add(b["boundary_id"])

    for imp in data.get("improvements") or []:
        if not isinstance(imp, dict):
            continue
        rid = imp.get("id")
        for j, ev in enumerate(imp.get("evidence") or []):
            kind = ev.get("kind")
            ref = ev.get("ref")
            if kind == "finding" and ref not in finding_ids:
                report.errors.append(Violation(
                    path, rid,
                    f"evidence[{j}].ref {ref!r} (kind: finding) not found in run corpus",
                ))
            elif kind == "asset_inventory" and ref not in inventory_ids:
                report.errors.append(Violation(
                    path, rid,
                    f"evidence[{j}].ref {ref!r} (kind: asset_inventory) not found in "
                    "00-context/asset-inventory.yaml",
                ))
        for msg in linters.check_domain_improvement_id(imp):
            report.errors.append(Violation(path, rid, msg))


def _check_record_file_locations(
    run_dir: pathlib.Path, report: ValidationReport
) -> None:
    """G7: every *.findings.yaml / *.capabilities.yaml must live DIRECTLY under a
    canonical run subdir (``CANONICAL_RECORD_DIRS``). A record file at any other
    relative location — e.g. a phantom ``20-findings/40-threat-model/`` path, or a
    file nested one level too deep — is an ERROR. The synthesizer-fallback
    ``merged.findings.yaml`` and the per-lens / attack-path / threat-model files all
    live directly under a canonical dir, so canonical runs are unaffected.
    """
    for _kind, (_schema, _root_key, glob) in RECORD_KINDS.items():
        for path in sorted(run_dir.rglob(glob)):
            rel = path.relative_to(run_dir)
            parent = rel.parent.as_posix()  # the single dir the file sits in
            if parent not in CANONICAL_RECORD_DIRS:
                report.errors.append(
                    Violation(
                        path,
                        None,
                        f"non-canonical location {parent!r}: {glob} files must live "
                        f"directly under one of "
                        f"{sorted(CANONICAL_RECORD_DIRS)}",
                    )
                )


def run_cross_file_pass(run_dir: pathlib.Path) -> ValidationReport:
    """Pass 3: cross-file ID and artifact resolution."""
    report = ValidationReport()
    _check_record_file_locations(run_dir, report)
    brief = parse_intake_brief(run_dir / "00-context" / "context-brief.md")
    artifacts_meta = brief.get("artifacts") or []
    known_artifacts: set[str] = {a["filename"] for a in artifacts_meta if "filename" in a}
    if _code_evidence_index_path(run_dir).exists():
        known_artifacts.add(CODE_EVIDENCE_INDEX_FILENAME)
    # Issue #86: allow tier-4 analyzers to cite their own synthesis outputs as
    # evidence. Only union them when the artifact check is actually active
    # (known_artifacts non-empty); adding them when no brief/artifacts are
    # declared would resurrect the check that the no-brief path intentionally
    # skips (see the `if known_artifacts` guard below).
    if known_artifacts:
        known_artifacts |= ANALYZER_DERIVED_ARTIFACTS
        ctx_dir = run_dir / "00-context"
        for stem in CONTEXT_DERIVED_STEMS:
            if (ctx_dir / stem).exists():
                known_artifacts.add(stem)
                known_artifacts.add(f"00-context/{stem}")
    tech_plan_artifacts: set[str] = {
        a["filename"] for a in artifacts_meta if a.get("type") == "tech_plan"
    }

    # Collect all finding/capability IDs.
    finding_ids:    set[str] = set()
    capability_ids: set[str] = set()
    for _path, kind, record in _iter_records(run_dir):
        if "_parse_error" in record:
            continue
        rid = record.get("id")
        if not rid:
            continue
        if kind == "finding":
            finding_ids.add(rid)
        else:
            capability_ids.add(rid)

    # FW-3: tier-4 findings (tmeval/apath) cross-reference MERGED finding ids
    # that exist only in the post-synthesis deduped corpus — whose filename
    # (deduped-findings.yaml, a hyphen) is deliberately NOT matched by the
    # ``*.findings.yaml`` record glob. Fold those ids into the resolution
    # universe when the deduped file is present so a post-synthesis whole-run
    # validate does not falsely flag a legitimate merged cross-reference.
    # Pre-synthesis the file is absent, so this is a no-op and the raw-set gate
    # is unchanged. (Resolution-only: these records are not schema-validated
    # here, and adding ids can only clear false "not found" errors.)
    deduped_findings_path = run_dir / "40-synthesis" / "deduped-findings.yaml"
    if deduped_findings_path.exists():
        try:
            deduped_doc = yaml.safe_load(
                deduped_findings_path.read_text(encoding="utf-8")
            ) or {}
        except yaml.YAMLError:
            deduped_doc = {}
        deduped_recs = deduped_doc.get("finding") or deduped_doc.get("findings") or []
        for rec in deduped_recs:
            if isinstance(rec, dict) and rec.get("id"):
                finding_ids.add(rec["id"])

    # Verify cross_references, merged_from, and evidence artifacts.
    seen_files: set[pathlib.Path] = set()
    for path, _kind, record in _iter_records(run_dir):
        if "_parse_error" in record:
            continue
        seen_files.add(path)
        rid = record.get("id")
        for i, ev in enumerate(record.get("evidence", [])):
            art = ev.get("artifact")
            if known_artifacts and art not in known_artifacts:
                report.errors.append(
                    Violation(path, rid, f"evidence[{i}].artifact '{art}' not in intake brief")
                )
        for ref in record.get("cross_references", []):
            if ref not in finding_ids:
                report.errors.append(Violation(path, rid, f"cross_reference {ref} not found"))
        for ref in record.get("merged_from", []):
            if ref not in finding_ids:
                report.errors.append(Violation(path, rid, f"merged_from {ref} not found"))

    # Re-run the maturity-vs-evidence lint with the real tech-plan set.
    if tech_plan_artifacts:
        sem = run_semantic_pass(run_dir, tech_plan_artifacts=tech_plan_artifacts)
        for v in sem.errors:
            if "non-tech-plan evidence" in v.message:
                report.errors.append(v)

    # Asset-graph edge integrity (C-21).
    # If the run has a 40-synthesis/asset-graph.yaml, verify:
    #   (a) every edge's ``from``/``to`` references a node_id present in nodes
    #   (b) compromisable_via_finding edges reference a known finding_id
    #   (c) mitigated_by_capability edges reference a known capability_id
    # The per-document schema already enforces shape; this is the cross-file pass.
    asset_graph_path = run_dir / "40-synthesis" / "asset-graph.yaml"
    if asset_graph_path.exists():
        try:
            ag = yaml.safe_load(asset_graph_path.read_text(encoding="utf-8")) or {}
        except yaml.YAMLError as e:
            report.errors.append(
                Violation(asset_graph_path, None, f"YAML parse error: {e}")
            )
        else:
            node_ids = {
                n.get("node_id")
                for n in (ag.get("nodes") or [])
                if isinstance(n, dict) and n.get("node_id")
            }
            for i, edge in enumerate(ag.get("edges") or []):
                if not isinstance(edge, dict):
                    continue
                eid = edge.get("edge_id")
                for endpoint in ("from", "to"):
                    node_ref = edge.get(endpoint)
                    if node_ref and node_ref not in node_ids:
                        report.errors.append(
                            Violation(
                                asset_graph_path, eid,
                                f"edges[{i}].{endpoint} '{node_ref}' not in nodes list",
                            )
                        )
                if edge.get("edge_type") == "compromisable_via_finding":
                    fid = edge.get("finding_id")
                    if fid and fid not in finding_ids:
                        report.errors.append(
                            Violation(
                                asset_graph_path, eid,
                                f"edges[{i}].finding_id '{fid}' not found in any "
                                "specialist or tier-4 finding file",
                            )
                        )
                if edge.get("edge_type") == "mitigated_by_capability":
                    cid = edge.get("capability_id")
                    if cid and cid not in capability_ids:
                        report.errors.append(
                            Violation(
                                asset_graph_path, eid,
                                f"edges[{i}].capability_id '{cid}' not found in any "
                                "specialist capability file",
                            )
                        )

    # Contradictions reference real IDs.
    contradictions_path = run_dir / "40-synthesis" / "contradictions.yaml"
    if contradictions_path.exists():
        data = yaml.safe_load(contradictions_path.read_text(encoding="utf-8")) or {}
        for entry in (data.get("contradictions") or []):
            fid = entry.get("finding_id")
            cid = entry.get("capability_id")
            if fid and fid not in finding_ids:
                report.errors.append(
                    Violation(contradictions_path, entry.get("id"), f"finding_id {fid} not found")
                )
            if cid and cid not in capability_ids:
                report.errors.append(
                    Violation(
                        contradictions_path, entry.get("id"), f"capability_id {cid} not found"
                    )
                )

    _validate_report_data_cross_refs(run_dir, report)
    _validate_domain_improvements_cross_refs(run_dir, report)
    report.files_seen = len(seen_files)
    return report
