"""Read every 40-synthesis artifact a run produced into typed containers.

The loader is the only module that touches YAML. Downstream transform.py
operates on plain dicts and dataclass fields; emit.py operates on the
transform output.

`load_run(run_dir)` returns a `RunArtifacts` dataclass. Required artifacts
(`.apd-run.yaml`, `asset-inventory.yaml`, the deduped findings/capabilities)
trigger `MissingArtifactError` when absent. Optional artifacts (attack-paths,
threat-model coverage, `report-data.yaml`) return `None` so the caller can
substitute algorithmic fallbacks.

Fixture-shape notes (apd-20260527-crapi-owasp-api-top10 and later runs):
  - `.apd-run.yaml` uses a `domains: [<name>, ...]` list (current schema)
    rather than the planned `domain_pack: {name: ..., version: ...}` block.
    The loader is forgiving: it checks `run_cfg["domain_pack"]` first, then a
    legacy bare `run_cfg["domain"]`, then the first entry of the
    `run_cfg["domains"]` list.
  - `domain_pack_version` is absent from `.apd-run.yaml`; the loader reads it
    from the frontmatter of `deduped-findings.yaml` (`domain_pack.version`).
  - There is no `subject:` key in `.apd-run.yaml`; the loader falls back to
    `cbm_project` when present, otherwise an empty string.

Manifest schema (the keys populated on the returned RunArtifacts dataclass)
-------------------------------------------------------------------------

Required artifacts (raise MissingArtifactError when absent):
  - ``.apd-run.yaml``                          → ``run_cfg`` (run-level config)
  - ``00-context/asset-inventory.yaml``         → ``asset_inventory``
  - ``40-synthesis/deduped-findings.yaml``      → ``deduped_findings``
  - ``40-synthesis/deduped-capabilities.yaml``  → ``deduped_capabilities``
  - ``40-synthesis/nist-coverage.yaml``         → ``nist_coverage``
  - ``40-synthesis/attack-exposure.yaml``       → ``attack_exposure``
  - ``40-synthesis/apd-coverage-matrix.yaml``   → ``apd_coverage_matrix``
  - ``40-synthesis/metrics.yaml``               → ``metrics``

Optional artifacts (default to ``None`` / ``[]`` when absent):
  - ``40-synthesis/contradictions.yaml``        → ``contradictions`` / notes
  - ``40-synthesis/severity-disagreements.yaml``→ ``severity_disagreements`` / notes
  - ``40-synthesis/attack-paths.yaml``          → ``attack_paths``
  - ``40-synthesis/asset-graph.yaml``           → ``asset_graph``
  - ``40-synthesis/defense-graph.yaml``         → ``defense_graph``
  - ``40-synthesis/attack-path.findings.yaml``  → ``attack_path_findings``
  - ``40-synthesis/report-data.yaml``           → ``report_data``

Source-of-truth + fallback chain for each manifest field:
  - ``run_id`` — ``run_cfg.run_id``; falls back to ``run_dir.name``.
  - ``framework_version`` — ``run_cfg.framework_version``; falls back to
    ``deduped-findings.yaml`` top-level ``framework_version``; final empty
    string is treated downstream (transform.meta_block) as a warning case
    and substituted with ``"unknown"``.
  - ``domain_pack_name`` — ``run_cfg.domain_pack.name`` if dict-shaped;
    accepts ``run_cfg.domain_pack`` as a bare string; falls back to a legacy
    ``run_cfg.domain`` string, then to the first entry of ``run_cfg.domains``
    (current multi-domain list shape).
  - ``domain_pack_version`` — ``run_cfg.domain_pack.version``; falls back to
    ``run_cfg.domain_pack_version``; then to
    ``deduped-findings.yaml._meta.domain_pack_version``; then to
    ``deduped-findings.yaml.domain_pack.version`` (legacy frontmatter
    shape); final fallback ``"unknown"``.
  - ``subject`` — ``run_cfg.subject``; falls back to a humanised
    ``run_cfg.cbm_project`` when the latter is not a filesystem-path slug.
  - ``date`` — ``run_cfg.date``; falls back to
    ``nist_coverage.generated_at`` (date portion); then to
    ``attack_exposure.generated_at`` (date portion); final fallback is
    today's ISO date (build-time stamp).
"""
from __future__ import annotations

import datetime
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
    metrics: dict[str, Any]
    source_hashes: dict[str, str] = field(default_factory=dict)

    # These override / supplement the asset_inventory-derived lists in meta_block.
    run_crown_jewels: list[str] = field(default_factory=list)
    run_attacker_positions: list[str] = field(default_factory=list)
    # The canonical normalized threat model (authored baseline or recon-parsed)
    # and the supplied-TM sibling, when present. Both optional; used by the
    # transform to expose the authored-vs-supplied comparator. None when absent.
    threat_model_normalized: dict[str, Any] | None = None
    threat_model_supplied: dict[str, Any] | None = None
    # The evaluator's per-surface STRIDE coverage artifact
    # (40-synthesis/threat-model-coverage.yaml). Optional; None when the
    # evaluator did not run. Consumed by the transform's threat-model scene.
    threat_model_coverage: dict[str, Any] | None = None
    # F1: the threat-model evaluator's tmeval-* finding records
    # (40-threat-model/threat-model.findings.yaml). First-class finding source —
    # unioned into the report findings list, metrics, and coverage rollups,
    # mirroring attack_path_findings. Empty when the evaluator emitted none.
    threat_model_findings: list[dict[str, Any]] = field(default_factory=list)
    # OWASP MAS (mobile) coverage rollups, loaded from 40-synthesis/ when the
    # synthesizer emitted them (mobile-applications pack runs declaring the
    # masvs / maswe taxonomies). Optional — None on non-mobile runs. Consumed by
    # the transform's masvs_coverage / maswe_coverage scenes and harvested into
    # the taxonomy dict so MASVS/MASWE ids resolve clickable titles + URLs.
    masvs_coverage: dict[str, Any] | None = None
    maswe_coverage: dict[str, Any] | None = None
    # The run-config ``taxonomies`` list, lifted verbatim so the transform can
    # emit data.meta.active_taxonomies (drives which taxonomy chips the report
    # advertises). Empty when the run declared no taxonomies key.
    active_taxonomies: list[str] = field(default_factory=list)


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

    Accepts three shapes:
      - ``domain_pack: {name: pbm, version: 1.0.0}``  (planned schema)
      - ``domain: pbm``  (legacy fixture shape — bare string)
      - ``domains: [pbm, ...]``  (current multi-domain list; first entry used)
    """
    domain_pack = run_cfg.get("domain_pack")
    if isinstance(domain_pack, dict):
        return str(domain_pack.get("name", ""))
    if isinstance(domain_pack, str):
        return domain_pack
    # Fall back to the bare `domain:` key used by legacy fixtures.
    legacy = run_cfg.get("domain", "")
    if legacy:
        return str(legacy)
    # Current shape: `domains:` list — join all selected packs so a multi-domain
    # run names every contributing pack (a single-domain run is unchanged).
    domains = run_cfg.get("domains")
    if isinstance(domains, list) and domains:
        return " + ".join(str(d) for d in domains)
    return ""


# Repo-root ``domains/`` directory, relative to this module
# (tools/apd_gauntlet/report/loader.py → repo_root/domains). Used as the
# default source for domain-pack versions when the run uses the multi-domain
# ``domains: [...]`` list shape (which carries no inline version).
_DOMAINS_DIR = pathlib.Path(__file__).resolve().parents[3] / "domains"


def _pack_versions_from_domains(
    run_cfg: dict[str, Any],
    domains_dir: pathlib.Path,
) -> str:
    """Combine the declared domains' pack versions, read from
    ``<domains_dir>/<name>/domain.yaml`` and joined with ``+`` in declared
    order (e.g. ``1.0.0+1.0.0`` for ``[agentic-ai, api-security]``).

    Returns ``""`` when there are no declared domains or any pack file is
    missing / versionless, so the caller falls through to ``"unknown"``.
    """
    names = _extract_str_list(run_cfg, "domains")
    if not names:
        return ""
    versions: list[str] = []
    for name in names:
        try:
            meta = yaml.safe_load(
                (domains_dir / name / "domain.yaml").read_text(encoding="utf-8")
            )
        except (OSError, yaml.YAMLError):
            return ""
        version = meta.get("version") if isinstance(meta, dict) else None
        if not version:
            return ""
        versions.append(str(version))
    return "+".join(versions)


def _extract_domain_pack_version(
    run_cfg: dict[str, Any],
    findings_doc: dict[str, Any] | None = None,
    domains_dir: pathlib.Path | None = None,
) -> str:
    """Extract domain pack version with cascading fallbacks.

    Fallback chain:
      1. ``run_cfg.domain_pack.version`` (planned schema)
      2. ``run_cfg.domain_pack_version`` (flat alternate shape)
      3. ``findings_doc._meta.domain_pack_version`` (PR-T4-G addition —
         synthesizer-emitted metadata)
      4. ``findings_doc.domain_pack.version`` (legacy frontmatter shape)
      5. ``<domains_dir>/<name>/domain.yaml`` versions for the run's
         ``domains: [...]`` list, joined with ``+`` (only when *domains_dir*
         is provided — the live build passes the repo ``domains/`` dir)
      6. ``"unknown"`` (final build-time fallback so the rendered report
         never shows an empty version string)
    """
    domain_pack = run_cfg.get("domain_pack")
    if isinstance(domain_pack, dict):
        version = domain_pack.get("version", "")
        if version:
            return str(version)
    flat_version = run_cfg.get("domain_pack_version")
    if flat_version:
        return str(flat_version)
    if findings_doc:
        meta = findings_doc.get("_meta")
        if isinstance(meta, dict):
            meta_version = meta.get("domain_pack_version")
            if meta_version:
                return str(meta_version)
        # Legacy frontmatter shape.
        findings_dp = findings_doc.get("domain_pack")
        if isinstance(findings_dp, dict):
            legacy_version = findings_dp.get("version", "")
            if legacy_version:
                return str(legacy_version)
    if domains_dir is not None:
        from_packs = _pack_versions_from_domains(run_cfg, domains_dir)
        if from_packs:
            return from_packs
    return "unknown"


def _resolve_date(
    run_cfg: dict[str, Any],
    nist_doc: dict[str, Any] | None = None,
    attack_doc: dict[str, Any] | None = None,
) -> str:
    """Resolve the manifest ``date`` field with cascading fallbacks.

    Fallback chain:
      1. ``run_cfg.date`` (canonical, run-config supplied)
      2. ``nist_doc.generated_at`` (date portion before any "T")
      3. ``attack_doc.generated_at`` (date portion before any "T")
      4. ``datetime.date.today().isoformat()`` (build-time stamp)
    """
    date = run_cfg.get("date") or ""
    if not date and nist_doc:
        date = str(nist_doc.get("generated_at") or "").split("T")[0]
    if not date and attack_doc:
        date = str(attack_doc.get("generated_at") or "").split("T")[0]
    if not date:
        date = datetime.date.today().isoformat()
    return str(date)


def _is_path_slug(value: str) -> bool:
    """Return True if *value* looks like a filesystem path slug.

    Patterns detected:
    - Contains ``-Documents-GitHub-`` (macOS home-dir CBM project slugs)
    - Starts with ``Users-`` (absolute path slugged with hyphens)
    """
    import re  # noqa: PLC0415 — intentional lazy import
    return bool(re.search(r"-Documents-GitHub-|-Documents-|-Users-", value))


# Directory names that commonly PARENT a repository inside a slugged CBM
# project path. The repo name is whatever follows the LAST of these segments.
# Matched case-insensitively against the hyphen-split slug.
_DEV_CONTAINER_DIRS = frozenset({
    "github", "gitlab", "bitbucket", "gitea", "sourcehut",
    "documents", "desktop", "src", "source", "repos", "repositories",
    "projects", "project", "code", "workspace", "workspaces", "dev",
})


def _prettify_repo_name(name: str) -> str:
    """Turn a repo directory name into a display title.

    ``open-notebook`` -> ``Open Notebook``; ``data-formulator`` ->
    ``Data Formulator``; ``MyProject`` -> ``MyProject`` and ``ChainGuard`` ->
    ``ChainGuard`` (existing CamelCase is preserved, lowercase words are
    capitalised).
    """
    segs = [s for s in name.replace("_", "-").split("-") if s]
    if not segs:
        return name
    return " ".join(s[:1].upper() + s[1:] if s.islower() else s for s in segs)


def _humanise_slug(slug: str) -> str:
    """Extract a human-readable project name from a filesystem path slug.

    The CBM project slug joins every path component with hyphens, e.g.
    ``Users-alice-Documents-GitHub-open-notebook``. The repository name is
    everything AFTER the last well-known repo-parent directory (GitHub,
    Documents, src, repos, …), rejoined and prettified — which correctly
    recovers multi-word lowercase repo names that the old "last capitalised
    segment" heuristic mis-resolved to the parent dir (e.g. ``GitHub``):

    ``Users-alice-Documents-GitHub-open-notebook`` -> ``Open Notebook``
    ``Users-alice-Documents-GitHub-MyProject``     -> ``MyProject``

    Falls back to the prettified last segment when no known parent dir is
    present.
    """
    parts = [p for p in slug.split("-") if p]
    if not parts:
        return slug
    last_container = -1
    for i, part in enumerate(parts):
        if part.lower() in _DEV_CONTAINER_DIRS:
            last_container = i
    repo_parts = parts[last_container + 1:] if last_container >= 0 else []
    if not repo_parts:
        repo_parts = [parts[-1]]
    return _prettify_repo_name("-".join(repo_parts))


def _extract_subject(run_cfg: dict[str, Any]) -> str:
    """Extract subject string.

    Priority order:
    1. ``subject:`` key in run_cfg (explicit, human-authored)
    2. ``cbm_project`` if it doesn't look like a path slug
    3. Humanised last segment of ``cbm_project`` when it is a path slug
    4. The primary (or first) ``repos[].cbm_project`` in multi-repo mode
    5. Empty string
    """
    subject = run_cfg.get("subject", "")
    if subject:
        return str(subject)
    cbm = str(run_cfg.get("cbm_project", ""))
    if cbm:
        if _is_path_slug(cbm):
            return _humanise_slug(cbm)
        return cbm
    # Multi-repo back-stop: no subject and no single cbm_project, but a repos[]
    # array is declared. Prefer the entry tagged role: primary, else the first.
    repos = run_cfg.get("repos")
    if isinstance(repos, list) and repos:
        primary = next(
            (r for r in repos if isinstance(r, dict) and r.get("role") == "primary"),
            repos[0],
        )
        if isinstance(primary, dict):
            name = str(primary.get("cbm_project", ""))
            if name:
                return _humanise_slug(name) if _is_path_slug(name) else name
    return ""


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
    metrics_path = _required(run_dir, "40-synthesis/metrics.yaml")

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
    metrics_doc, source_hashes["metrics.yaml"] = _yaml_with_hash(metrics_path)

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
    # F1: tmeval-* findings live under 40-threat-model/ (the evaluator's output),
    # a sibling of synth. Optional — empty when the evaluator emitted no findings.
    tm_findings_path = run_dir / "40-threat-model" / "threat-model.findings.yaml"
    tm_findings = (
        _records(tm_findings_path, "finding") if tm_findings_path.is_file() else []
    )
    report_data = _yaml_optional(synth / "report-data.yaml")
    context = run_dir / "00-context"
    tm_normalized = _yaml_optional(context / "threat-model-normalized.yaml")
    tm_supplied = _yaml_optional(context / "threat-model-supplied-normalized.yaml")
    # The evaluator's coverage artifact lives under 40-synthesis (the synth dir).
    tm_coverage = _yaml_optional(synth / "threat-model-coverage.yaml")
    # OWASP MAS (mobile) coverage rollups — present only on mobile-applications
    # pack runs that declared the masvs / maswe taxonomies. Tolerant: absent on
    # every non-mobile run, so _yaml_optional returns None and the transform
    # omits the MAS scenes/meta gracefully.
    masvs_coverage = _yaml_optional(synth / "masvs-coverage.yaml")
    maswe_coverage = _yaml_optional(synth / "maswe-coverage.yaml")

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
    if masvs_coverage is not None:
        source_hashes["masvs-coverage.yaml"] = _hash(synth / "masvs-coverage.yaml")
    if maswe_coverage is not None:
        source_hashes["maswe-coverage.yaml"] = _hash(synth / "maswe-coverage.yaml")

    return RunArtifacts(
        run_id=run_cfg.get("run_id", run_dir.name),
        framework_version=str(
            run_cfg.get("framework_version")
            or findings_doc.get("framework_version", "")
        ),
        domain_pack_name=_extract_domain_pack_name(run_cfg),
        domain_pack_version=_extract_domain_pack_version(
            run_cfg, findings_doc, domains_dir=_DOMAINS_DIR
        ),
        subject=_extract_subject(run_cfg),
        # Use T4-F's cached docs (nist_doc + attack_exposure_doc) to feed
        # T4-G's _resolve_date fallback chain — no third read needed.
        date=_resolve_date(run_cfg, nist_doc, attack_exposure_doc),
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
        metrics=metrics_doc,
        source_hashes=source_hashes,
        run_crown_jewels=_extract_str_list(run_cfg, "crown_jewels"),
        run_attacker_positions=_extract_str_list(run_cfg, "attacker_positions"),
        threat_model_normalized=tm_normalized,
        threat_model_supplied=tm_supplied,
        threat_model_coverage=tm_coverage,
        threat_model_findings=tm_findings,
        masvs_coverage=masvs_coverage,
        maswe_coverage=maswe_coverage,
        active_taxonomies=_extract_str_list(run_cfg, "taxonomies"),
    )
