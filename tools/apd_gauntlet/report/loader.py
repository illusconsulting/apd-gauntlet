"""Read every 40-synthesis artifact a run produced into typed containers.

The loader is the only module that touches YAML. Downstream transform.py
operates on plain dicts and dataclass fields; emit.py operates on the
transform output.

`load_run(run_dir)` returns a `RunArtifacts` dataclass. Required artifacts
(`.apd-run.yaml`, `asset-inventory.yaml`, the deduped findings/capabilities)
trigger `MissingArtifactError` when absent. Optional artifacts (attack-paths,
threat-model coverage, `report-data.yaml`) return `None` so the caller can
substitute algorithmic fallbacks.

Fixture-shape notes (apd-20260527-crapi-owasp-api-top10 and earlier runs):
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


class MalformedArtifactError(ValueError):
    """An artifact exists but does not parse to the expected shape."""

    def __init__(self, path: pathlib.Path, expected: str, got: type) -> None:
        super().__init__(
            f"{path}: expected {expected}, got {got.__name__}"
        )
        self.path = path
        self.expected = expected
        self.got = got


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
    contradictions_notes: str | None
    severity_disagreements: list[dict[str, Any]]
    severity_disagreements_notes: str | None
    nist_coverage: dict[str, Any]
    attack_exposure: dict[str, Any]
    apd_coverage_matrix: dict[str, Any]
    attack_paths: dict[str, Any] | None
    asset_graph: dict[str, Any] | None
    defense_graph: dict[str, Any] | None
    attack_path_findings: list[dict[str, Any]]
    report_data: dict[str, Any] | None
    source_hashes: dict[str, str] = field(default_factory=dict)
    # Crown jewels and attacker positions sourced from .apd-run.yaml (run_cfg).
    # These override / supplement the asset_inventory-derived lists in meta_block.
    run_crown_jewels: list[str] = field(default_factory=list)
    run_attacker_positions: list[str] = field(default_factory=list)


def _required(run_dir: pathlib.Path, rel: str) -> pathlib.Path:
    path = run_dir / rel
    if not path.is_file():
        if path.is_dir():
            raise MissingArtifactError(
                f"required artifact is a directory, not a file: {path}"
            )
        raise MissingArtifactError(f"required artifact missing: {path}")
    return path


def _yaml_with_hash(path: pathlib.Path) -> tuple[dict[str, Any], str]:
    """Read *path* once, returning the parsed mapping and a short content hash.

    The bytes are read a single time and both YAML parsing and the SHA-256
    digest are computed from that buffer. This eliminates the TOCTOU window
    that exists when a separate ``_hash(path)`` follows ``_yaml(path)``: if
    the file is replaced between the two reads, the parsed contents and the
    recorded hash would diverge, and an OS error on the second read would
    abort an otherwise successful load.

    Returns a ``(doc, hash_str)`` tuple. ``hash_str`` is the first 16 hex
    characters of the SHA-256 digest — identical to the format produced by
    ``_hash`` so callers comparing against shipped hashes are unaffected.
    Empty or whitespace-only YAML resolves to an empty dict (matching
    ``_yaml``'s prior behavior); a non-mapping top level raises
    :class:`MalformedArtifactError`.
    """
    raw = path.read_bytes()
    doc = yaml.safe_load(raw.decode("utf-8"))
    hash_str = hashlib.sha256(raw).hexdigest()[:16]
    if doc is None:
        return {}, hash_str
    if not isinstance(doc, dict):
        raise MalformedArtifactError(path, "mapping (dict)", type(doc))
    return doc, hash_str


def _yaml(path: pathlib.Path) -> dict[str, Any]:
    """Return the parsed YAML mapping at *path*.

    Thin wrapper around :func:`_yaml_with_hash` preserved as a stable
    public-ish helper for callers that do not need the content hash
    (the common case across the loader and tests).
    """
    doc, _hash_str = _yaml_with_hash(path)
    return doc


def _yaml_optional(path: pathlib.Path) -> dict[str, Any] | None:
    """Return _yaml(path) if the file exists and parses; else None.

    On yaml.YAMLError emit a click.echo warning to stderr and return None
    so the caller treats the artifact as absent rather than aborting.
    """
    if not path.is_file():
        return None
    try:
        return _yaml(path)
    except yaml.YAMLError as e:
        # Best-effort warning; do not crash the build for an optional artifact.
        try:
            import click  # noqa: PLC0415 — intentional lazy import
            click.echo(
                f"warning: {path}: malformed YAML, skipping ({e})",
                err=True,
            )
        except ImportError:
            pass
        return None


def _records_from_doc(
    doc: dict[str, Any],
    root_key: str,
    *fallback_keys: str,
) -> list[dict[str, Any]]:
    """Pluck the list under root_key (or fallback_keys) from an already-parsed doc.

    Same semantics as :func:`_records` but operates on an in-memory dict,
    which lets callers reuse a single YAML read instead of re-reading the
    file. Required by ``load_run`` to eliminate the double-read pattern.
    """
    for key in (root_key, *fallback_keys):
        payload = doc.get(key)
        if payload is None:
            continue
        if isinstance(payload, list):
            return [r for r in payload if isinstance(r, dict)]
        if isinstance(payload, dict):
            return [payload]
    return []


def _records(
    path: pathlib.Path,
    root_key: str,
    *fallback_keys: str,
) -> list[dict[str, Any]]:
    """Return the list under root_key (or any fallback_key). Accepts both
    list and single-dict shape under any of the candidate keys.

    Synthesizers across fixtures use different top-level keys for the same
    record class — e.g. contradictions.yaml uses ``contradictions:`` (plural)
    in shipped runs but the planned schema named the key ``contradiction:``
    (singular). Passing both keys lets the loader stay agnostic.
    """
    return _records_from_doc(_yaml(path), root_key, *fallback_keys)


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
        return str(domain_pack.get("name", ""))
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


def _is_path_slug(value: str) -> bool:
    """Return True if *value* looks like a filesystem path slug.

    Patterns detected:
    - Contains ``-Documents-GitHub-`` (macOS home-dir CBM project slugs)
    - Starts with ``Users-`` (absolute path slugged with hyphens)
    """
    import re  # noqa: PLC0415 — intentional lazy import
    return bool(re.search(r"-Documents-GitHub-|-Documents-|-Users-", value))


def _humanise_slug(slug: str) -> str:
    """Extract a human-readable name from a filesystem path slug.

    ``Users-alice-Documents-GitHub-MyProject`` -> ``MyProject``
    """
    # Last hyphen-separated segment that starts with a capital letter, or just last segment.
    parts = slug.split("-")
    for part in reversed(parts):
        if part and part[0].isupper():
            return part
    return parts[-1] if parts else slug


def _extract_subject(run_cfg: dict[str, Any]) -> str:
    """Extract subject string.

    Priority order:
    1. ``subject:`` key in run_cfg (explicit, human-authored)
    2. ``cbm_project`` if it doesn't look like a path slug
    3. Humanised last segment of ``cbm_project`` when it is a path slug
    4. Empty string
    """
    subject = run_cfg.get("subject", "")
    if subject:
        return str(subject)
    cbm = str(run_cfg.get("cbm_project", ""))
    if not cbm:
        return ""
    if _is_path_slug(cbm):
        return _humanise_slug(cbm)
    return cbm


def _extract_str_list(run_cfg: dict[str, Any], key: str) -> list[str]:
    """Extract a list of strings from run_cfg[key].

    Handles both ``[str, ...]`` and ``[{name: str, ...}, ...]`` shapes.
    Returns an empty list when key is absent or value is not a list.
    """
    raw = run_cfg.get(key)
    if not isinstance(raw, list):
        return []
    out: list[str] = []
    for item in raw:
        if isinstance(item, str):
            out.append(item)
        elif isinstance(item, dict):
            out.append(item.get("name") or item.get("id") or str(item))
    return out


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

    # Read required artifacts once each, collecting hashes inline. Reading
    # bytes + hashing in one pass closes the TOCTOU window that a separate
    # post-parse hashing loop would open if the file were replaced after the
    # initial read.
    source_hashes: dict[str, str] = {}
    run_cfg, source_hashes[".apd-run.yaml"] = _yaml_with_hash(run_cfg_path)
    inventory, source_hashes["asset-inventory.yaml"] = _yaml_with_hash(
        asset_inventory_path,
    )
    findings_doc, source_hashes["deduped-findings.yaml"] = _yaml_with_hash(
        deduped_findings_path,
    )
    caps_doc, source_hashes["deduped-capabilities.yaml"] = _yaml_with_hash(
        deduped_caps_path,
    )
    nist_doc, source_hashes["nist-coverage.yaml"] = _yaml_with_hash(nist_path)
    attack_exposure_doc, source_hashes["attack-exposure.yaml"] = (
        _yaml_with_hash(attack_exposure_path)
    )
    apd_matrix_doc, source_hashes["apd-coverage-matrix.yaml"] = (
        _yaml_with_hash(apd_matrix_path)
    )

    # Optional artifacts.
    synth = run_dir / "40-synthesis"
    contradictions_notes: str | None = None
    _contra_doc = _yaml_optional(synth / "contradictions.yaml")
    if _contra_doc is not None:
        # Plural ``contradictions`` is the shipped-fixture key; singular
        # ``contradiction`` is the planned-schema key. Accept both.
        contradictions = _records(
            synth / "contradictions.yaml", "contradictions", "contradiction",
        )
        # ``notes`` (plural) and ``note`` (caldera's singular variant).
        contradictions_notes = (
            _contra_doc.get("notes") or _contra_doc.get("note") or None
        )
    else:
        contradictions = []
    sev_dis_notes: str | None = None
    _sevdis_doc = _yaml_optional(synth / "severity-disagreements.yaml")
    if _sevdis_doc is not None:
        # crapi/example use ``severity_disagreements``; caldera/authentik
        # use the abbreviated ``disagreements``; the planned schema named
        # the singular ``severity_disagreement``. Accept all three.
        sev_dis = _records(
            synth / "severity-disagreements.yaml",
            "severity_disagreements",
            "disagreements",
            "severity_disagreement",
        )
        sev_dis_notes = (
            _sevdis_doc.get("notes") or _sevdis_doc.get("note") or None
        )
    else:
        sev_dis = []
    attack_paths = _yaml_optional(synth / "attack-paths.yaml")
    asset_graph = _yaml_optional(synth / "asset-graph.yaml")
    defense_graph = _yaml_optional(synth / "defense-graph.yaml")
    apath_findings = (
        _records(synth / "attack-path.findings.yaml", "finding")
        if (synth / "attack-path.findings.yaml").is_file()
        else []
    )
    report_data = _yaml_optional(synth / "report-data.yaml")

    # Optional artifacts are hashed via the existing single-read helper:
    # they are already loaded above and we tolerate the second read here
    # because (a) the file is known to exist (loaded successfully) and
    # (b) the optional-artifact set is small. The required-artifact set
    # — the actual TOCTOU hotspot, since it would abort an otherwise
    # successful load — is hashed inline in the read pass above.
    if attack_paths is not None:
        source_hashes["attack-paths.yaml"] = _hash(synth / "attack-paths.yaml")
    if asset_graph is not None:
        source_hashes["asset-graph.yaml"] = _hash(synth / "asset-graph.yaml")
    if defense_graph is not None:
        source_hashes["defense-graph.yaml"] = _hash(synth / "defense-graph.yaml")
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
        deduped_findings=_records_from_doc(findings_doc, "finding"),
        deduped_capabilities=_records_from_doc(caps_doc, "capability"),
        contradictions=contradictions,
        contradictions_notes=contradictions_notes,
        severity_disagreements=sev_dis,
        severity_disagreements_notes=sev_dis_notes,
        nist_coverage=nist_doc,
        attack_exposure=attack_exposure_doc,
        apd_coverage_matrix=apd_matrix_doc,
        attack_paths=attack_paths,
        asset_graph=asset_graph,
        defense_graph=defense_graph,
        attack_path_findings=apath_findings,
        report_data=report_data,
        source_hashes=source_hashes,
        run_crown_jewels=_extract_str_list(run_cfg, "crown_jewels"),
        run_attacker_positions=_extract_str_list(run_cfg, "attacker_positions"),
    )
