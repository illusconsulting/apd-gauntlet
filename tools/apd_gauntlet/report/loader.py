"""Read every 40-synthesis artifact a run produced into typed containers.

The loader is the only module that touches YAML. Downstream transform.py
operates on plain dicts and dataclass fields; emit.py operates on the
transform output.

`load_run(run_dir)` returns a `RunArtifacts` dataclass. Required artifacts
(`.apd-run.yaml`, `asset-inventory.yaml`, the deduped findings/capabilities)
trigger `MissingArtifactError` when absent. Optional artifacts (attack-paths,
threat-model coverage, `report-data.yaml`) return `None` so the caller can
substitute algorithmic fallbacks.

Fixture-shape notes (apd-legacy-example-run):
  - `.apd-run.yaml` uses `domain: <name>` (a bare string) rather than the
    planned `domain_pack: {name: ..., version: ...}` block.  The loader
    accepts both forms: it checks `run_cfg["domain_pack"]` first, then falls
    back to `run_cfg["domain"]`.
  - `domain_pack_version` is absent from `.apd-run.yaml`; the loader reads it
    from the frontmatter of `deduped-findings.yaml` (`domain_pack.version`).
  - There is no `subject:` key in `.apd-run.yaml`; the loader falls back to
    `cbm_project` when present, otherwise an empty string.
"""
from __future__ import annotations

import hashlib
import pathlib
from dataclasses import dataclass, field
from typing import Any

import yaml


class MissingArtifactError(FileNotFoundError):
    """Raised when a required input file is absent from the run dir."""


@dataclass(frozen=True)
class RunArtifacts:
    run_id: str
    framework_version: str
    domain_pack_name: str
    domain_pack_version: str
    subject: str
    date: str
    asset_inventory: dict[str, Any]
    deduped_findings: list[dict[str, Any]]
    deduped_capabilities: list[dict[str, Any]]
    contradictions: list[dict[str, Any]]
    severity_disagreements: list[dict[str, Any]]
    nist_coverage: dict[str, Any]
    attack_exposure: dict[str, Any]
    apd_coverage_matrix: dict[str, Any]
    attack_paths: dict[str, Any] | None
    asset_graph: dict[str, Any] | None
    defense_graph: dict[str, Any] | None
    attack_path_findings: list[dict[str, Any]]
    report_data: dict[str, Any] | None
    source_hashes: dict[str, str] = field(default_factory=dict)


def _required(run_dir: pathlib.Path, rel: str) -> pathlib.Path:
    path = run_dir / rel
    if not path.exists():
        raise MissingArtifactError(f"required artifact missing: {path}")
    return path


def _yaml(path: pathlib.Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text()) or {}


def _records(path: pathlib.Path, root_key: str) -> list[dict[str, Any]]:
    """Return the list under root_key. Accepts both list and single-dict shape."""
    doc = _yaml(path)
    payload = doc.get(root_key)
    if isinstance(payload, list):
        return [r for r in payload if isinstance(r, dict)]
    if isinstance(payload, dict):
        return [payload]
    return []


def _hash(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:16]


def _extract_domain_pack_name(run_cfg: dict[str, Any]) -> str:
    """Extract domain pack name from run config.

    Accepts two shapes:
      - ``domain_pack: {name: pbm, version: 1.0.0}``  (planned schema)
      - ``domain: pbm``  (current fixture shape — bare string)
    """
    domain_pack = run_cfg.get("domain_pack")
    if isinstance(domain_pack, dict):
        return domain_pack.get("name", "")
    if isinstance(domain_pack, str):
        return domain_pack
    # Fall back to the bare `domain:` key used by current runs.
    return str(run_cfg.get("domain", ""))


def _extract_domain_pack_version(
    run_cfg: dict[str, Any],
    findings_doc: dict[str, Any],
) -> str:
    """Extract domain pack version.

    Current fixture stores this in deduped-findings.yaml frontmatter
    (``domain_pack.version``) rather than in `.apd-run.yaml`.
    """
    domain_pack = run_cfg.get("domain_pack")
    if isinstance(domain_pack, dict):
        version = domain_pack.get("version", "")
        if version:
            return str(version)
    # Fall back to deduped-findings.yaml frontmatter.
    findings_dp = findings_doc.get("domain_pack")
    if isinstance(findings_dp, dict):
        return str(findings_dp.get("version", ""))
    return ""


def _extract_subject(run_cfg: dict[str, Any]) -> str:
    """Extract subject string.

    Current fixture has no ``subject:`` key; fall back to ``cbm_project``
    when present.
    """
    subject = run_cfg.get("subject", "")
    if subject:
        return str(subject)
    return str(run_cfg.get("cbm_project", ""))


def load_run(run_dir: pathlib.Path) -> RunArtifacts:
    """Read every 40-synthesis artifact a run produced. Raises MissingArtifactError
    when any required input is absent.
    """
    run_cfg_path = _required(run_dir, ".apd-run.yaml")
    asset_inventory_path = _required(run_dir, "00-context/asset-inventory.yaml")
    deduped_findings_path = _required(run_dir, "40-synthesis/deduped-findings.yaml")
    deduped_caps_path = _required(run_dir, "40-synthesis/deduped-capabilities.yaml")
    nist_path = _required(run_dir, "40-synthesis/nist-coverage.yaml")
    attack_exposure_path = _required(run_dir, "40-synthesis/attack-exposure.yaml")
    apd_matrix_path = _required(run_dir, "40-synthesis/apd-coverage-matrix.yaml")

    run_cfg = _yaml(run_cfg_path)
    inventory = _yaml(asset_inventory_path)
    findings_doc = _yaml(deduped_findings_path)

    # Optional artifacts.
    synth = run_dir / "40-synthesis"
    contradictions = _records(synth / "contradictions.yaml", "contradiction") \
        if (synth / "contradictions.yaml").exists() else []
    sev_dis = _records(synth / "severity-disagreements.yaml", "severity_disagreement") \
        if (synth / "severity-disagreements.yaml").exists() else []
    attack_paths = _yaml(synth / "attack-paths.yaml") \
        if (synth / "attack-paths.yaml").exists() else None
    asset_graph = _yaml(synth / "asset-graph.yaml") \
        if (synth / "asset-graph.yaml").exists() else None
    defense_graph = _yaml(synth / "defense-graph.yaml") \
        if (synth / "defense-graph.yaml").exists() else None
    apath_findings = _records(synth / "attack-path.findings.yaml", "finding") \
        if (synth / "attack-path.findings.yaml").exists() else []
    report_data = _yaml(synth / "report-data.yaml") \
        if (synth / "report-data.yaml").exists() else None

    source_hashes = {
        ".apd-run.yaml": _hash(run_cfg_path),
        "asset-inventory.yaml": _hash(asset_inventory_path),
        "deduped-findings.yaml": _hash(deduped_findings_path),
        "deduped-capabilities.yaml": _hash(deduped_caps_path),
        "nist-coverage.yaml": _hash(nist_path),
        "attack-exposure.yaml": _hash(attack_exposure_path),
        "apd-coverage-matrix.yaml": _hash(apd_matrix_path),
    }
    if attack_paths is not None:
        source_hashes["attack-paths.yaml"] = _hash(synth / "attack-paths.yaml")
    if report_data is not None:
        source_hashes["report-data.yaml"] = _hash(synth / "report-data.yaml")

    return RunArtifacts(
        run_id=run_cfg.get("run_id", run_dir.name),
        framework_version=str(
            run_cfg.get("framework_version")
            or findings_doc.get("framework_version", "")
        ),
        domain_pack_name=_extract_domain_pack_name(run_cfg),
        domain_pack_version=_extract_domain_pack_version(run_cfg, findings_doc),
        subject=_extract_subject(run_cfg),
        date=str(run_cfg.get("date", "")),
        asset_inventory=inventory,
        deduped_findings=_records(deduped_findings_path, "finding"),
        deduped_capabilities=_records(deduped_caps_path, "capability"),
        contradictions=contradictions,
        severity_disagreements=sev_dis,
        nist_coverage=_yaml(nist_path),
        attack_exposure=_yaml(attack_exposure_path),
        apd_coverage_matrix=_yaml(apd_matrix_path),
        attack_paths=attack_paths,
        asset_graph=asset_graph,
        defense_graph=defense_graph,
        attack_path_findings=apath_findings,
        report_data=report_data,
        source_hashes=source_hashes,
    )
