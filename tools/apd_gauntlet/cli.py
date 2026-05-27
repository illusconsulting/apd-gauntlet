"""apd-gauntlet CLI entry point."""
from __future__ import annotations

import hashlib
import json as _stdjson
import pathlib
from pathlib import Path
from typing import TYPE_CHECKING, Any

import click
import yaml

if TYPE_CHECKING:
    from .attack_path.enumerate import EnumerationParams
    from .attack_path.enumerate import Path as APath
    from .attack_path.graph import Edge, Graph, Node

from . import __version__
from .build_domain_skill import build_domain_skill
from .init_run import scaffold_run
from .lint_agents import lint_agents_dir
from .linters import check_capability_id, check_finding_id
from .refresh_cwe import refresh_cwe
from .refresh_d3fend import refresh_d3fend
from .refresh_mitre import fetch_and_project
from .refresh_owasp import refresh_owasp
from .summary import render_summary, summarize_run
from .validate import (
    ValidationReport,
    build_registry,
    run_cross_file_pass,
    run_schema_pass,
    run_semantic_pass,
)


@click.group(
    name="apd-gauntlet",
    help="APD Gauntlet — validator and tooling for APD security architecture reviews.",
)
@click.version_option(__version__, prog_name="apd-gauntlet")
def main() -> None:
    """Root command group."""


@main.command(help="Validate all records under a run directory.")
@click.argument("run_dir", type=click.Path(exists=True, file_okay=False, path_type=pathlib.Path))
@click.option(
    "--schema-only",
    is_flag=True,
    help="Run schema validation only (skip semantic + cross-file passes).",
)
@click.option("--strict", is_flag=True, help="Treat warnings as errors.")
@click.option("--json", "as_json", is_flag=True, help="Emit JSON output for CI consumption.")
def validate(run_dir, schema_only, strict, as_json) -> None:  # type: ignore[no-untyped-def]
    schema_rep = run_schema_pass(run_dir)
    if schema_only:
        merged = schema_rep
    else:
        semantic_rep = run_semantic_pass(run_dir)
        cross_file_rep = run_cross_file_pass(run_dir)
        merged = ValidationReport(
            errors=schema_rep.errors + semantic_rep.errors + cross_file_rep.errors,
            warnings=schema_rep.warnings + semantic_rep.warnings + cross_file_rep.warnings,
            files_seen=max(
                schema_rep.files_seen, semantic_rep.files_seen, cross_file_rep.files_seen
            ),
            records_seen=schema_rep.records_seen,
        )
    if strict:
        merged.errors.extend(merged.warnings)
        merged.warnings = []
    if as_json:
        import json as _json

        from .validate import Violation as _Violation

        def _ser(v: _Violation) -> dict[str, object]:
            return {"file": str(v.file), "id": v.record_id, "message": v.message, "path": v.path}

        click.echo(
            _json.dumps(
                {
                    "errors": [_ser(v) for v in merged.errors],
                    "warnings": [_ser(v) for v in merged.warnings],
                    "records": merged.records_seen,
                    "files": merged.files_seen,
                },
                indent=2,
            )
        )
    else:
        click.echo(merged.render())
    raise SystemExit(0 if merged.is_clean else 1)


@main.command("build-domain-skill")
@click.argument("domain_name")
@click.option(
    "--domains-dir",
    type=click.Path(exists=True, file_okay=False, path_type=pathlib.Path),
    default=pathlib.Path("domains"),
)
@click.option(
    "--out",
    type=click.Path(file_okay=False, path_type=pathlib.Path),
    default=pathlib.Path(".claude/skills/apd-domain"),
)
@click.option("--framework-version", default=__version__)
def build_domain_skill_cmd(domain_name, domains_dir, out, framework_version) -> None:  # type: ignore[no-untyped-def]
    try:
        path = build_domain_skill(domain_name, domains_dir, out, framework_version)
    except (FileNotFoundError, ValueError) as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1) from None
    click.echo(f"Wrote {path}")


@main.command("init-run", help="Scaffold runs/<run-id>/ with subdirs and copy input artifacts.")
@click.argument("run_id")
@click.option(
    "--inputs",
    type=click.Path(exists=True, file_okay=False, path_type=pathlib.Path),
    required=True,
)
@click.option("--domain", default="pbm", show_default=True)
@click.option(
    "--root",
    type=click.Path(file_okay=False, path_type=pathlib.Path),
    default=pathlib.Path("runs"),
    show_default=True,
)
@click.option(
    "--taxonomies",
    default=None,
    help=(
        "Comma-separated taxonomies "
        "(cwe,mitre_attack,d3fend,owasp_top10,owasp_api_top10,owasp_llm_top10)."
    ),
)
@click.option(
    "--threat-model",
    default=None,
    help="Path (relative to --inputs) to a threat model file.",
)
@click.option(
    "--methodology-hint",
    type=click.Choice(
        ["stride", "linddun", "attack_tree", "pasta", "vast", "trike", "free_form"],
        case_sensitive=False,
    ),
    default=None,
    help="Methodology hint for threat model parsing.",
)
def init_run_cmd(run_id, inputs, domain, root, taxonomies, threat_model, methodology_hint) -> None:  # type: ignore[no-untyped-def]
    parsed = (
        [t.strip() for t in taxonomies.split(",") if t.strip()] if taxonomies else None
    )
    target = scaffold_run(
        run_id,
        inputs,
        domain,
        root,
        taxonomies=parsed,
        threat_model=threat_model,
        methodology_hint=methodology_hint,
    )
    click.echo(f"Run scaffolded at {target}")


@main.command("validate-domain")
@click.argument("domain_name")
@click.option(
    "--domains-dir",
    type=click.Path(exists=True, file_okay=False, path_type=pathlib.Path),
    default=pathlib.Path("domains"),
)
def validate_domain_cmd(domain_name, domains_dir) -> None:  # type: ignore[no-untyped-def]
    from jsonschema import Draft202012Validator

    schema_path = (
        pathlib.Path(__file__).resolve().parent.parent.parent / "schemas" / "domain.schema.json"
    )
    schema = _stdjson.loads(schema_path.read_text())
    pack_dir = domains_dir / domain_name
    meta_path = pack_dir / "domain.yaml"
    if not meta_path.exists():
        click.echo(f"Error: domain pack '{domain_name}' not found at {pack_dir}", err=True)
        raise SystemExit(1)
    import yaml as _yaml

    meta = _yaml.safe_load(meta_path.read_text())
    errors = list(Draft202012Validator(schema).iter_errors(meta))
    if errors:
        for e in errors:
            click.echo(f"Schema error: {e.message}", err=True)
        raise SystemExit(1)
    missing = []
    for include_glob in meta.get("includes", []):
        matches = list(pack_dir.glob(include_glob))
        if not matches:
            missing.append(include_glob)
    if missing:
        for m in missing:
            click.echo(f"Missing include: {m}", err=True)
        raise SystemExit(1)
    n = len(meta.get("includes", []))
    click.echo(f"Domain pack '{domain_name}' OK: schema valid, {n} include patterns all resolved.")


@main.command("validate-run-config")
@click.argument("config_path", type=click.Path(exists=True, dir_okay=False, path_type=pathlib.Path))
def validate_run_config_cmd(config_path) -> None:  # type: ignore[no-untyped-def]
    import yaml as _yaml
    from jsonschema import Draft202012Validator

    schema_path = (
        pathlib.Path(__file__).resolve().parent.parent.parent / "schemas" / "run-config.schema.json"
    )
    schema = _stdjson.loads(schema_path.read_text())
    data = _yaml.safe_load(config_path.read_text())
    errors = list(Draft202012Validator(schema).iter_errors(data))
    if errors:
        for e in errors:
            click.echo(f"Schema error: {e.message}", err=True)
        raise SystemExit(1)
    click.echo(f"Run config '{config_path}' OK.")


@main.command("check-ids")
@click.argument("yaml_file", type=click.Path(exists=True, dir_okay=False, path_type=pathlib.Path))
def check_ids_cmd(yaml_file) -> None:  # type: ignore[no-untyped-def]
    import yaml as _yaml

    data = _yaml.safe_load(yaml_file.read_text()) or {}
    payload = data.get("finding") or data.get("capability")
    records = payload if isinstance(payload, list) else ([payload] if payload else [])
    is_capability = "capability" in data and "finding" not in data
    found_issues = False
    for rec in records:
        if not isinstance(rec, dict):
            continue
        msgs = check_capability_id(rec) if is_capability else check_finding_id(rec)
        for msg in msgs:
            click.echo(f"{yaml_file} [{rec.get('id')}]: {msg}")
            found_issues = True
    if found_issues:
        raise SystemExit(1)
    click.echo(f"{yaml_file}: IDs OK.")


@main.command("lint-agents")
@click.option(
    "--agent-dir",
    type=click.Path(exists=True, file_okay=False, path_type=pathlib.Path),
    default=pathlib.Path(".claude/agents"),
    show_default=True,
)
def lint_agents_cmd(agent_dir) -> None:  # type: ignore[no-untyped-def]
    repo_root = pathlib.Path.cwd()
    errors = lint_agents_dir(agent_dir, repo_root)
    if errors:
        for e in errors:
            click.echo(e)
        raise SystemExit(1)
    click.echo(f"Lint clean: {len(list(agent_dir.glob('*.md')))} agents checked.")


@main.command("summarize")
@click.argument("run_dir", type=click.Path(exists=True, file_okay=False, path_type=pathlib.Path))
@click.option("--json", "as_json", is_flag=True)
def summarize_cmd(run_dir, as_json) -> None:  # type: ignore[no-untyped-def]
    stats = summarize_run(run_dir)
    if as_json:
        import json as _json

        click.echo(_json.dumps(stats, indent=2))
    else:
        click.echo(render_summary(stats))


@main.command("refresh-mitre")
@click.option(
    "--out",
    type=click.Path(dir_okay=False, path_type=pathlib.Path),
    default=pathlib.Path(__file__).resolve().parent / "data" / "mitre-mitigations.json",
    show_default=False,
)
def refresh_mitre_cmd(out) -> None:  # type: ignore[no-untyped-def]
    click.echo("Fetching MITRE ATT&CK bundle...")
    fetch_and_project(out)
    click.echo(f"Wrote {out}")


@main.command("refresh-cwe")
def refresh_cwe_cmd() -> None:
    """Refresh MITRE CWE reference data (writes to package data dir)."""
    path = refresh_cwe()
    click.echo(f"Wrote {path}")


@main.command("refresh-owasp")
def refresh_owasp_cmd() -> None:
    """Refresh OWASP Top 10 / API Top 10 / LLM Top 10 reference data."""
    for name, path in refresh_owasp().items():
        click.echo(f"Wrote {name}: {path}")


@main.command("refresh-d3fend")
def refresh_d3fend_cmd() -> None:
    """Refresh MITRE D3FEND reference data."""
    path = refresh_d3fend()
    click.echo(f"Wrote {path}")


@main.command("parse-threat-model")
@click.argument("path", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--methodology-hint",
    default=None,
    help="Force a methodology (stride/linddun/attack_tree/pasta/vast/trike/free_form).",
)
@click.option(
    "--output",
    default=None,
    type=click.Path(path_type=Path),
    help="Output path; if omitted, writes YAML to stdout.",
)
@click.option(
    "--validate/--no-validate",
    default=True,
    help="Validate output against threat-model-normalized.schema.json (default: on).",
)
def parse_threat_model_cmd(
    path: Path,
    methodology_hint: str | None,
    output: Path | None,
    validate: bool,
) -> None:
    """Parse a threat model file into a normalized YAML graph.

    Auto-detects the format from extension when --methodology-hint is absent.
    Validates the result against schemas/threat-model-normalized.schema.json
    unless --no-validate is passed.
    """
    import json

    import yaml
    from jsonschema import Draft202012Validator

    from .threat_model.dispatcher import dispatch_parser

    try:
        normalized = dispatch_parser(path, methodology_hint)
    except json.JSONDecodeError as e:
        raise click.UsageError(
            f"failed to parse {path}: invalid JSON at line {e.lineno} col {e.colno}"
        ) from e
    except ValueError as e:
        raise click.UsageError(str(e)) from e

    if validate:
        schema_path = (
            pathlib.Path(__file__).resolve().parent.parent.parent
            / "schemas"
            / "threat-model-normalized.schema.json"
        )
        schema = _stdjson.loads(schema_path.read_text())
        registry = build_registry()
        validator = Draft202012Validator(schema, registry=registry)
        errors = list(validator.iter_errors(normalized))
        if errors:
            click.echo(
                f"ERROR: parser output failed schema validation ({len(errors)} errors):",
                err=True,
            )
            for err in errors[:5]:
                click.echo(f"  - {err.message} at {list(err.absolute_path)}", err=True)
            raise click.Abort()

    text = yaml.safe_dump(normalized, sort_keys=False)
    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(text)
        click.echo(f"Wrote {output}", err=True)
        click.echo(f"  methodology: {normalized['methodology']}", err=True)
        click.echo(f"  entries:     {normalized['extraction_summary']['entry_count']}", err=True)
    else:
        click.echo(text)


@main.command("analyze-attack-paths")
@click.argument("run_dir", type=click.Path(exists=True, file_okay=False, path_type=Path))
def analyze_attack_paths(run_dir: Path) -> None:
    """Build the asset graph, enumerate attack paths, compute D3FEND overlay, emit findings.

    Reads ``run_dir/00-context/asset-inventory.yaml`` plus optional TM /
    code-evidence artifacts and all specialist findings/capabilities. Writes:

    - ``40-synthesis/asset-graph.yaml``
    - ``40-synthesis/attack-paths.yaml``
    - ``40-synthesis/defense-graph.yaml``
    - ``40-synthesis/attack-path.findings.yaml``

    Enumeration defaults (override via .apd-run.yaml#attack_path_analysis):
      max_hop=8, max_paths_per_pair=50, bottleneck_threshold=5
    """
    from .attack_path.build import BuilderBlocked, build_graph
    from .attack_path.d3fend_overlay import build_overlays, load_d3fend_data
    from .attack_path.enumerate import (
        EnumerationParams,
        compute_bottleneck_edges,
        enumerate_paths,
    )
    from .attack_path.findings import emit_findings

    synth = run_dir / "40-synthesis"
    synth.mkdir(parents=True, exist_ok=True)
    run_cfg_path = run_dir / ".apd-run.yaml"
    try:
        run_cfg: dict[str, Any] = (
            yaml.safe_load(run_cfg_path.read_text()) if run_cfg_path.exists() else {}
        ) or {}
    except yaml.YAMLError as exc:
        raise click.UsageError(f".apd-run.yaml is not valid YAML: {exc}") from exc
    tuning = run_cfg.get("attack_path_analysis", {}) or {}
    params = EnumerationParams(
        max_hop=int(tuning.get("max_hop", 8)),
        max_paths_per_pair=int(tuning.get("max_paths_per_pair", 50)),
        bottleneck_threshold=int(tuning.get("bottleneck_threshold", 5)),
    )

    try:
        result = build_graph(run_dir)
    except BuilderBlocked as exc:
        _write_blocked_finding(synth, reason=str(exc))
        click.echo(f"analyze-attack-paths: blocked - {exc}")
        return

    graph = result.graph
    attackers = graph.nodes_by_type("attacker_position")
    jewels = graph.nodes_by_type("crown_jewel")

    findings_by_id, capabilities = _load_records(run_dir)

    all_paths: list[APath] = []
    truncated_pairs = 0
    for atk in attackers:
        for jwl in jewels:
            raw = enumerate_paths(
                graph,
                atk.node_id,
                jwl.node_id,
                params,
                findings_by_id=findings_by_id,
            )
            if len(raw) == params.max_paths_per_pair:
                truncated_pairs += 1
            all_paths.extend(raw)

    bottleneck_edges = compute_bottleneck_edges(all_paths, params.bottleneck_threshold)
    d3fend_data = load_d3fend_data()
    overlays = build_overlays(
        paths=all_paths,
        bottleneck_edges=bottleneck_edges,
        graph=graph,
        findings_by_id=findings_by_id,
        capabilities=capabilities,
        d3fend_data=d3fend_data,
    )
    findings = emit_findings(
        paths=all_paths,
        overlays=overlays,
        graph=graph,
        findings_by_id=findings_by_id,
        capabilities=capabilities,
    )

    _write_asset_graph(synth / "asset-graph.yaml", graph, result.sources_used)
    _write_attack_paths(
        synth / "attack-paths.yaml", all_paths, params, truncated_pairs, bottleneck_edges
    )
    _write_defense_graph(synth / "defense-graph.yaml", overlays)
    _write_findings(synth / "attack-path.findings.yaml", findings)

    click.echo(
        f"analyze-attack-paths: wrote {len(all_paths)} paths, "
        f"{len(bottleneck_edges)} bottlenecks, {len(findings)} findings"
    )


def _write_blocked_finding(synth: Path, *, reason: str) -> None:
    """Emit a single ``disposition: blocked`` apath finding to
    ``attack-path.findings.yaml``. Conforms to ``finding.schema.json``
    (including the ``allOf`` rule requiring ``prerequisite_evidence`` when
    ``disposition == "blocked"``).
    """
    short_hash = hashlib.sha256(reason.encode()).hexdigest()[:8]
    doc = {
        "schema_version": 1,
        "finding": [
            {
                "schema_version": 1,
                "id": f"apath-{short_hash}",
                "agent": "attack_path_analyzer",
                "apd_tier": "trustworthiness",
                "apd_goal": "authenticity",
                "disposition": "blocked",
                "severity": "informational",
                "confidence": "high",
                "title": f"Attack-path analysis blocked: {reason}",
                "summary": (
                    f"The analyzer could not run because {reason}. Declare "
                    "crown_jewels[] in the domain pack or .apd-run.yaml to "
                    "enable attack-path analysis."
                ),
                # TODO: reference ADR-0010 once C-27 lands
                "detail": (
                    "Attack-path analysis requires at least one "
                    "(attacker_position, crown_jewel) pair declared in either "
                    "the domain pack's crown_jewels[] / attacker_positions[] "
                    "fields or the run-config. See "
                    "docs/attack-path-analysis.md for configuration patterns."
                ),
                "evidence": [
                    {
                        "artifact": ".apd-run.yaml",
                        "locator": "crown_jewels",
                        "excerpt": "(absent or empty)",
                    }
                ],
                "prerequisite_evidence": [
                    "domain pack or run-config must declare crown_jewels[] "
                    "and attacker_positions[]"
                ],
                "control_mappings": {"nist_800_53r5": ["SA-8"]},
                "recommendation": {
                    "posture": "required",
                    "summary": (
                        "Declare crown jewels and attacker positions in the "
                        "domain pack or run-config"
                    ),
                    "detail": (
                        "The PBM domain pack ships defaults (phi_store, "
                        "pde_submission_pipeline, claim_adjudication_engine); "
                        "see docs/attack-path-analysis.md for declaration "
                        "patterns in other domains."
                    ),
                },
            }
        ],
    }
    (synth / "attack-path.findings.yaml").write_text(yaml.safe_dump(doc, sort_keys=False))


def _load_records(
    run_dir: Path,
) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:
    """Index findings by ``id`` and collect capabilities, recursively scanning
    ``run_dir`` for ``*.findings.yaml`` / ``*.capabilities.yaml``.

    Specialist agents emit into the per-goal tier directories
    (``10-trustworthiness/``, ``20-scalability/``, ``30-auditability/``) per
    the apd-synthesizer's input convention; test fixtures may use flatter
    layouts. A recursive glob handles both shapes uniformly.

    The analyzer's own ``40-synthesis/attack-path.findings.yaml`` is skipped
    so repeated runs do not ingest the previous run's apath-* findings as
    "specialist findings."
    """
    findings_by_id: dict[str, dict[str, Any]] = {}
    capabilities: list[dict[str, Any]] = []
    for f in sorted(run_dir.glob("**/*.findings.yaml")):
        if "40-synthesis" in f.parts and f.name == "attack-path.findings.yaml":
            continue
        doc = yaml.safe_load(f.read_text()) or {}
        # Canonical root key is singular (`finding`), per validate.RECORD_KINDS.
        # Accept legacy plural (`findings`) defensively so older or hand-rolled
        # fixtures still load — writers always emit singular.
        raw = doc.get("finding")
        if raw is None:
            raw = doc.get("findings")
        records = raw if isinstance(raw, list) else ([raw] if isinstance(raw, dict) else [])
        for idx, rec in enumerate(records):
            if not isinstance(rec, dict):
                click.echo(
                    f"WARNING: {f}: finding[{idx}] is not a dict; skipping",
                    err=True,
                )
                continue
            if "id" not in rec:
                click.echo(
                    f"WARNING: {f}: finding[{idx}] missing 'id'; skipping",
                    err=True,
                )
                continue
            findings_by_id[rec["id"]] = rec
    for f in sorted(run_dir.glob("**/*.capabilities.yaml")):
        doc = yaml.safe_load(f.read_text()) or {}
        # Singular canonical; accept legacy plural defensively (see above).
        raw = doc.get("capability")
        if raw is None:
            raw = doc.get("capabilities")
        records = raw if isinstance(raw, list) else ([raw] if isinstance(raw, dict) else [])
        for idx, rec in enumerate(records):
            if not isinstance(rec, dict):
                click.echo(
                    f"WARNING: {f}: capability[{idx}] is not a dict; skipping",
                    err=True,
                )
                continue
            capabilities.append(rec)
    return findings_by_id, capabilities


def _write_asset_graph(path: Path, graph: Graph, sources_used: list[str]) -> None:
    doc = {
        "schema_version": 1,
        "generated_by": "attack_path_analyzer",
        "nodes": [
            _serialize_node(n)
            for n in sorted(graph._nodes.values(), key=lambda n: n.node_id)
        ],
        "edges": [
            _serialize_edge(e)
            for e in sorted(graph._edges.values(), key=lambda e: e.edge_id)
        ],
        "build_summary": {
            "node_count": graph.node_count,
            "edge_count": graph.edge_count,
            "attacker_position_count": len(graph.nodes_by_type("attacker_position")),
            "crown_jewel_count": len(graph.nodes_by_type("crown_jewel")),
            "finding_edges_count": sum(
                1
                for e in graph._edges.values()
                if e.edge_type == "compromisable_via_finding"
            ),
            "capability_edges_count": sum(
                1
                for e in graph._edges.values()
                if e.edge_type == "mitigated_by_capability"
            ),
            "sources_used": sources_used,
        },
    }
    path.write_text(yaml.safe_dump(doc, sort_keys=False))


def _serialize_node(n: Node) -> dict[str, Any]:
    out: dict[str, Any] = {
        "node_id": n.node_id,
        "node_type": n.node_type,
        "name": n.name,
        "provenance": dict(n.provenance),
        "confidence": n.confidence,
    }
    if n.asset_type:
        out["asset_type"] = n.asset_type
    if n.data_classifications:
        out["data_classifications"] = list(n.data_classifications)
    return out


def _serialize_edge(e: Edge) -> dict[str, Any]:
    out: dict[str, Any] = {
        "edge_id": e.edge_id,
        "edge_type": e.edge_type,
        "from": e.from_node,
        "to": e.to_node,
        "provenance": dict(e.provenance),
        "confidence": e.confidence,
        "traversal_cost": e.traversal_cost,
    }
    if e.finding_id:
        out["finding_id"] = e.finding_id
    if e.capability_id:
        out["capability_id"] = e.capability_id
    return out


def _write_attack_paths(
    path: Path,
    paths: list[APath],
    params: EnumerationParams,
    truncated: int,
    bottleneck_edges: dict[str, list[str]],
) -> None:
    """Write ``attack-paths.yaml``. Each path's ``bottleneck_edges`` field is
    computed as the intersection of the path's ``edges`` tuple with the
    keys of the run-wide ``bottleneck_edges`` dict.
    """
    doc = {
        "schema_version": 1,
        "generated_by": "attack_path_analyzer",
        "enumeration_parameters": {
            "max_hop": params.max_hop,
            "max_paths_per_pair": params.max_paths_per_pair,
            "bottleneck_threshold": params.bottleneck_threshold,
        },
        "paths": [
            {
                "path_id": p.path_id,
                "attacker_position": p.attacker_position,
                "crown_jewel": p.crown_jewel,
                "edges": list(p.edges),
                "hop_count": p.hop_count,
                "feasibility": p.feasibility,
                "severity_sum": p.severity_sum,
                "mitigation_count": p.mitigation_count,
                "bottleneck_edges": [eid for eid in p.edges if eid in bottleneck_edges],
            }
            for p in paths
        ],
        "summary": {
            "pairs_enumerated": len(
                {(p.attacker_position, p.crown_jewel) for p in paths}
            ),
            "total_paths": len(paths),
            "truncated_pairs": truncated,
            "bottleneck_edge_count": len(bottleneck_edges),
        },
    }
    path.write_text(yaml.safe_dump(doc, sort_keys=False))


def _write_defense_graph(path: Path, overlays: list[dict[str, Any]]) -> None:
    doc = {
        "schema_version": 1,
        "generated_by": "attack_path_analyzer",
        "bottleneck_overlays": overlays,
        "summary": {
            "bottleneck_edge_count": len(overlays),
            "total_candidate_d3fend": sum(
                len(o.get("candidate_d3fend", [])) for o in overlays
            ),
            "total_net_new_d3fend": sum(
                len(o.get("net_new_d3fend", [])) for o in overlays
            ),
        },
    }
    path.write_text(yaml.safe_dump(doc, sort_keys=False))


def _write_findings(path: Path, findings: list[dict[str, Any]]) -> None:
    """Emit a ``*.findings.yaml`` doc with the singular ``finding:`` root key
    (per ``validate.RECORD_KINDS``). The internal Python variable stays
    plural — only the YAML root key is singular.
    """
    doc = {"schema_version": 1, "finding": findings}
    path.write_text(yaml.safe_dump(doc, sort_keys=False))


@main.command("build-report",
              help="Generate the HTML advisory report for a completed run.")
@click.argument("run_dir", type=click.Path(exists=True, file_okay=False, path_type=pathlib.Path))
@click.option("--out", "out_dir", type=click.Path(path_type=pathlib.Path), default=None,
              help="Override output directory. Default: <run_dir>/40-synthesis/report-html/")
@click.option("--quiet", is_flag=True, help="Suppress per-file progress messages.")
def build_report_cmd(run_dir, out_dir, quiet) -> None:  # type: ignore[no-untyped-def]
    from .report.build import build_report
    from .report.emit import BundleMissingError
    from .report.loader import MissingArtifactError
    try:
        target = build_report(run_dir, out_dir, quiet=quiet)
    except (MissingArtifactError, BundleMissingError) as exc:
        click.echo(f"Error: {exc}", err=True)
        raise SystemExit(1) from None
    if not quiet:
        click.echo(f"HTML report at {target}")


if __name__ == "__main__":
    main()
