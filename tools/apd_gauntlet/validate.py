"""Validation engine — Pass 1 (schema), Pass 2 (semantic lints), Pass 3 (cross-file)."""
from __future__ import annotations
import json
import pathlib
from dataclasses import dataclass, field
from typing import Any, Iterable
import yaml
from jsonschema import Draft202012Validator
from referencing import Registry, Resource
from . import linters

REPO = pathlib.Path(__file__).resolve().parent.parent.parent
SCHEMAS_DIR = REPO / "schemas"

# Map record kind → (schema filename, root key in YAML, filename glob)
RECORD_KINDS: dict[str, tuple[str, str, str]] = {
    "finding":    ("finding.schema.json",    "finding",    "*.findings.yaml"),
    "capability": ("capability.schema.json", "capability", "*.capabilities.yaml"),
}


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


def _build_registry() -> Registry:
    finding    = Resource.from_contents(json.loads((SCHEMAS_DIR / "finding.schema.json").read_text()))
    capability = Resource.from_contents(json.loads((SCHEMAS_DIR / "capability.schema.json").read_text()))
    return Registry().with_resources([
        ("https://github.com/shoveleejoe/apd-gauntlet/schemas/finding.schema.json",    finding),
        ("https://github.com/shoveleejoe/apd-gauntlet/schemas/capability.schema.json", capability),
    ])


def _iter_records(run_dir: pathlib.Path) -> Iterable[tuple[pathlib.Path, str, dict[str, Any]]]:
    """Yield (file_path, kind, record_dict) for every YAML record in the run."""
    for kind, (_schema, root_key, glob) in RECORD_KINDS.items():
        for path in sorted(run_dir.rglob(glob)):
            try:
                data = yaml.safe_load(path.read_text()) or {}
            except yaml.YAMLError as e:
                yield path, kind, {"_parse_error": str(e)}
                continue
            payload = data.get(root_key)
            if isinstance(payload, list):
                for item in payload:
                    yield path, kind, item
            elif isinstance(payload, dict):
                yield path, kind, payload


def run_schema_pass(run_dir: pathlib.Path) -> ValidationReport:
    """Pass 1: validate every record against its JSON Schema."""
    registry = _build_registry()
    report = ValidationReport()
    validators = {
        kind: Draft202012Validator(
            json.loads((SCHEMAS_DIR / schema).read_text()),
            registry=registry,
        )
        for kind, (schema, _, _) in RECORD_KINDS.items()
    }
    seen_files: set[pathlib.Path] = set()
    for path, kind, record in _iter_records(run_dir):
        seen_files.add(path)
        if "_parse_error" in record:
            report.errors.append(Violation(path, None, f"YAML parse error: {record['_parse_error']}"))
            continue
        report.records_seen += 1
        validator = validators[kind]
        rid = record.get("id")
        for err in validator.iter_errors(record):
            report.errors.append(Violation(path, rid, err.message, "/".join(map(str, err.path))))
    report.files_seen = len(seen_files)
    return report


def parse_intake_brief(brief_path: pathlib.Path) -> dict[str, Any]:
    """Extract the YAML frontmatter block from context-brief.md."""
    if not brief_path.exists():
        return {}
    text = brief_path.read_text()
    if not text.startswith("---\n"):
        return {}
    end = text.find("\n---\n", 4)
    if end < 0:
        return {}
    return yaml.safe_load(text[4:end]) or {}


def run_semantic_pass(run_dir: pathlib.Path, tech_plan_artifacts: set[str] | None = None) -> ValidationReport:
    """Pass 2: semantic lints that JSON Schema cannot express."""
    tech_plan_artifacts = tech_plan_artifacts or set()
    report = ValidationReport()
    seen_files: set[pathlib.Path] = set()
    for path, kind, record in _iter_records(run_dir):
        if "_parse_error" in record:
            continue
        seen_files.add(path)
        rid = record.get("id")
        report.records_seen += 1
        if kind == "finding":
            for msg in linters.check_excerpt_length(record):
                report.errors.append(Violation(path, rid, msg))
            for msg in linters.check_finding_id(record):
                report.errors.append(Violation(path, rid, msg))
            for msg in linters.check_hedge_words_in_attack_rationale(record):
                report.warnings.append(Violation(path, rid, msg))
        elif kind == "capability":
            for msg in linters.check_excerpt_length(record):
                report.errors.append(Violation(path, rid, msg))
            for msg in linters.check_capability_id(record):
                report.errors.append(Violation(path, rid, msg))
            for msg in linters.check_capability_maturity_evidence(record, tech_plan_artifacts):
                report.errors.append(Violation(path, rid, msg))
    report.files_seen = len(seen_files)
    return report


def run_cross_file_pass(run_dir: pathlib.Path) -> ValidationReport:
    """Pass 3: cross-file ID and artifact resolution."""
    report = ValidationReport()
    brief = parse_intake_brief(run_dir / "00-context" / "context-brief.md")
    artifacts_meta = brief.get("artifacts") or []
    known_artifacts:    set[str] = {a["filename"] for a in artifacts_meta if "filename" in a}
    tech_plan_artifacts: set[str] = {a["filename"] for a in artifacts_meta if a.get("type") == "tech_plan"}

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
                report.errors.append(Violation(path, rid, f"evidence[{i}].artifact '{art}' not in intake brief"))
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

    # Contradictions reference real IDs.
    contradictions_path = run_dir / "40-synthesis" / "contradictions.yaml"
    if contradictions_path.exists():
        data = yaml.safe_load(contradictions_path.read_text()) or {}
        for entry in (data.get("contradictions") or []):
            fid = entry.get("finding_id")
            cid = entry.get("capability_id")
            if fid and fid not in finding_ids:
                report.errors.append(Violation(contradictions_path, entry.get("id"), f"finding_id {fid} not found"))
            if cid and cid not in capability_ids:
                report.errors.append(Violation(contradictions_path, entry.get("id"), f"capability_id {cid} not found"))

    report.files_seen = len(seen_files)
    return report
