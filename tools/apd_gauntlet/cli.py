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
from .threat_model.author import build_skeleton_from_inventory_file
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
@click.option(
    "--errors-only",
    is_flag=True,
    help="Print only ERROR lines; suppress warnings and the scan/clean summary line.",
)
@click.option(
    "--tier",
    default=None,
    help=(
        "Validate only this run subdir (e.g. 10-trustworthiness); "
        "skips the cross-file pass and 00-context/40-synthesis rollup checks."
    ),
)
def validate(run_dir, schema_only, strict, as_json, errors_only, tier) -> None:  # type: ignore[no-untyped-def]
    target = run_dir / tier if tier else run_dir
    if tier and not target.is_dir():
        raise click.ClickException(f"--tier subdir not found: {target}")

    schema_rep = run_schema_pass(target)
    if schema_only:
        merged = schema_rep
    elif tier:
        semantic_rep = run_semantic_pass(target)
        merged = ValidationReport(
            errors=schema_rep.errors + semantic_rep.errors,
            warnings=schema_rep.warnings + semantic_rep.warnings,
            files_seen=max(schema_rep.files_seen, semantic_rep.files_seen),
            records_seen=schema_rep.records_seen,
        )
    else:
        semantic_rep = run_semantic_pass(target)
        cross_file_rep = run_cross_file_pass(target)
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
    elif errors_only:
        if merged.errors:
            click.echo("\n".join(f"ERROR   {v.render()}" for v in merged.errors))
    else:
        click.echo(merged.render())
    raise SystemExit(0 if merged.is_clean else 1)


@main.command("build-domain-skill")
@click.argument("domain_names", nargs=-1, required=True)
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
@click.option(
    "--full-only",
    is_flag=True,
    default=False,
    help="Write only the full cross-goal SKILL.md; skip the per-goal by-goal/ "
    "sidecars (which lens agents read to bound context on multi-domain runs).",
)
def build_domain_skill_cmd(domain_names, domains_dir, out, framework_version, full_only) -> None:  # type: ignore[no-untyped-def]
    try:
        path = build_domain_skill(
            list(domain_names), domains_dir, out, framework_version,
            emit_sidecars=not full_only,
        )
    except (FileNotFoundError, ValueError) as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1) from None
    click.echo(f"Wrote {path}")
    if not full_only:
        by_goal = path.parent / "by-goal"
        n = sum(1 for _ in by_goal.glob("*.md")) if by_goal.is_dir() else 0
        click.echo(f"Wrote {n} per-goal sidecars to {by_goal}")


@main.command("init-run", help="Scaffold runs/<run-id>/ with subdirs and copy input artifacts.")
@click.argument("run_id")
@click.option(
    "--inputs",
    type=click.Path(exists=True, file_okay=False, path_type=pathlib.Path),
    required=True,
)
@click.option(
    "--domain",
    "domains",
    multiple=True,
    default=("pbm",),
    show_default=True,
    help=(
        "Domain pack for the run; repeat the flag for multiple"
        " (e.g. --domain pbm --domain api-security)."
    ),
)
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
        "(cwe,mitre_attack,d3fend,owasp_top10,owasp_api_top10,owasp_llm_top10,"
        "mitre_atlas,masvs,maswe). "
        "Selected packs may auto-seed taxonomies (e.g. mobile-applications -> "
        "masvs,maswe); these merge with any supplied here."
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
        ["stride", "linddun", "attack_tree", "pasta", "vast", "trike", "maestro", "free_form"],
        case_sensitive=False,
    ),
    default=None,
    help="Methodology hint for threat model parsing.",
)
def init_run_cmd(run_id, inputs, domains, root, taxonomies, threat_model, methodology_hint) -> None:  # type: ignore[no-untyped-def]
    parsed = (
        [t.strip() for t in taxonomies.split(",") if t.strip()] if taxonomies else None
    )
    target = scaffold_run(
        run_id,
        inputs,
        list(domains),
        root,
        taxonomies=parsed,
        threat_model=threat_model,
        methodology_hint=methodology_hint,
    )
    click.echo(f"Run scaffolded at {target}")


@main.command("validate-domain")
@click.argument("domain_names", nargs=-1, required=True)
@click.option(
    "--domains-dir",
    type=click.Path(exists=True, file_okay=False, path_type=pathlib.Path),
    default=pathlib.Path("domains"),
)
def validate_domain_cmd(domain_names, domains_dir) -> None:  # type: ignore[no-untyped-def]
    from jsonschema import Draft202012Validator

    schema_path = (
        pathlib.Path(__file__).resolve().parent.parent.parent / "schemas" / "domain.schema.json"
    )
    schema = _stdjson.loads(schema_path.read_text(encoding="utf-8"))
    import yaml as _yaml

    for domain_name in domain_names:
        pack_dir = domains_dir / domain_name
        meta_path = pack_dir / "domain.yaml"
        if not meta_path.exists():
            click.echo(f"Error: domain pack '{domain_name}' not found at {pack_dir}", err=True)
            raise SystemExit(1)
        meta = _yaml.safe_load(meta_path.read_text(encoding="utf-8"))
        errors = list(Draft202012Validator(schema).iter_errors(meta))
        if errors:
            for e in errors:
                click.echo(f"Schema error in '{domain_name}': {e.message}", err=True)
            raise SystemExit(1)
        missing = [g for g in meta.get("includes", []) if not list(pack_dir.glob(g))]
        if missing:
            for m in missing:
                click.echo(f"Missing include in '{domain_name}': {m}", err=True)
            raise SystemExit(1)
        n = len(meta.get("includes", []))
        click.echo(
            f"Domain pack '{domain_name}' OK: schema valid, {n} include patterns all resolved."
        )


@main.command("validate-run-config")
@click.argument("config_path", type=click.Path(exists=True, dir_okay=False, path_type=pathlib.Path))
def validate_run_config_cmd(config_path) -> None:  # type: ignore[no-untyped-def]
    import yaml as _yaml
    from jsonschema import Draft202012Validator

    schema_path = (
        pathlib.Path(__file__).resolve().parent.parent.parent / "schemas" / "run-config.schema.json"
    )
    schema = _stdjson.loads(schema_path.read_text(encoding="utf-8"))
    data = _yaml.safe_load(config_path.read_text(encoding="utf-8"))
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

    from .validate import extract_records

    data = _yaml.safe_load(yaml_file.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        click.echo(f"{yaml_file}: IDs OK.")
        return
    # root_key is the SINGULAR key; extract_records resolves the plural variant
    # ("findings"/"capabilities") internally. A single file is one kind by the
    # *.findings.yaml / *.capabilities.yaml naming invariant, so first-match wins.
    if "finding" in data or "findings" in data:
        kind, root_key = "finding", "finding"
    elif "capability" in data or "capabilities" in data:
        kind, root_key = "capability", "capability"
    else:
        click.echo(f"{yaml_file}: IDs OK.")
        return
    records = extract_records(data, root_key)
    found_issues = False
    for rec in records:
        msgs = check_capability_id(rec) if kind == "capability" else check_finding_id(rec)
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


@main.command("plan-run")
@click.argument("run_dir", type=click.Path(exists=True, file_okay=False, path_type=pathlib.Path))
@click.option("--json", "as_json", is_flag=True, help="Emit the plan as a JSON list of steps.")
def plan_run_cmd(run_dir, as_json) -> None:  # type: ignore[no-untyped-def]
    """Emit the deterministic FOREGROUND drive-checklist for a run.

    Reads RUN_DIR/.apd-run.yaml, validates it against run-config.schema.json, and
    prints the exact ordered phase->step list the apd-gauntlet.js runner executes
    (honoring the run-config gates) so operators can drive each step in-session.
    """
    from jsonschema import Draft202012Validator

    from .plan_run import build_plan, render_markdown

    config_path = run_dir / ".apd-run.yaml"
    if not config_path.is_file():
        click.echo(f"No .apd-run.yaml under {run_dir}", err=True)
        raise SystemExit(1)

    schema_path = (
        pathlib.Path(__file__).resolve().parent.parent.parent / "schemas" / "run-config.schema.json"
    )
    schema = _stdjson.loads(schema_path.read_text(encoding="utf-8"))
    cfg = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    errors = list(Draft202012Validator(schema).iter_errors(cfg))
    if errors:
        for e in errors:
            click.echo(f"Schema error: {e.message}", err=True)
        raise SystemExit(1)

    plan = build_plan(cfg)
    if as_json:
        click.echo(_stdjson.dumps(plan, indent=2))
    else:
        click.echo(render_markdown(plan, cfg))


@main.command("refresh-mitre")
@click.option(
    "--out",
    type=click.Path(dir_okay=False, path_type=pathlib.Path),
    default=pathlib.Path(__file__).resolve().parent / "data" / "mitre-mitigations.json",
    show_default=False,
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Fetch the upstream bundle and report its byte size without writing.",
)
def refresh_mitre_cmd(out, dry_run) -> None:  # type: ignore[no-untyped-def]
    if dry_run:
        from .refresh_mitre import fetch_mitre_bundle

        click.echo("Fetching MITRE ATT&CK bundle (dry-run)...")
        body = fetch_mitre_bundle()
        click.echo(
            f"Would write {out} ({len(body)} bytes fetched from upstream)."
        )
        return
    click.echo("Fetching MITRE ATT&CK bundle...")
    fetch_and_project(out)
    click.echo(f"Wrote {out}")


@main.command("refresh-mitre-mobile")
@click.option(
    "--techniques-out",
    type=click.Path(dir_okay=False, path_type=pathlib.Path),
    default=pathlib.Path(__file__).resolve().parent / "data" / "mitre-attack-techniques.json",
    show_default=False,
)
@click.option(
    "--mitigations-out",
    type=click.Path(dir_okay=False, path_type=pathlib.Path),
    default=pathlib.Path(__file__).resolve().parent / "data" / "mitre-mitigations.json",
    show_default=False,
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Fetch the Mobile bundle and report its byte size without writing.",
)
def refresh_mitre_mobile_cmd(techniques_out, mitigations_out, dry_run) -> None:  # type: ignore[no-untyped-def]
    """Additively merge the ATT&CK Mobile matrix into the bundled catalogs.

    Adds Mobile technique titles (so Mobile-pack findings render names, not bare
    ids) and Mobile mitigation→technique mappings. Enterprise entries are
    preserved; only Mobile ids not already present are added (the lone shared id,
    M1013, is unioned). Idempotent.
    """
    from .refresh_mitre import (
        MOBILE_URL,
        fetch_mitre_bundle,
        merge_mobile_mitigations,
        merge_mobile_technique_titles,
    )

    if dry_run:
        click.echo("Fetching MITRE ATT&CK Mobile bundle (dry-run)...")
        body = fetch_mitre_bundle(MOBILE_URL)
        click.echo(
            f"Would merge Mobile titles into {techniques_out} and mitigations into "
            f"{mitigations_out} ({len(body)} bytes fetched)."
        )
        return
    click.echo("Fetching MITRE ATT&CK Mobile bundle and merging titles + mitigations...")
    t = merge_mobile_technique_titles(techniques_out)
    m = merge_mobile_mitigations(mitigations_out)
    click.echo(
        f"Merged Mobile ATT&CK into bundled catalogs: titles +{t['added']} "
        f"({t['total']} total); mitigations +{m['added_mitigations']} ids / "
        f"+{m['added_pairs']} pairs ({m['total_mitigations']} total)."
    )


# Upstream OSCAL 800-53r5 catalog. Stable enough that refresh-nist defaults to
# the same source the bundled nist-controls.json was projected from.
NIST_OSCAL_URL = (
    "https://github.com/usnistgov/oscal-content/raw/main/nist.gov/SP800-53/rev5/"
    "json/NIST_SP-800-53_rev5_catalog-min.json"
)


@main.command("refresh-nist")
@click.option(
    "--out",
    type=click.Path(dir_okay=False, path_type=pathlib.Path),
    default=pathlib.Path(__file__).resolve().parent / "data" / "nist-controls.json",
    show_default=False,
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Fetch the upstream OSCAL catalog and report its byte size without writing.",
)
def refresh_nist_cmd(out, dry_run) -> None:  # type: ignore[no-untyped-def]
    """Refresh the bundled NIST 800-53r5 control catalog from the OSCAL source.

    Downloads the upstream OSCAL JSON, projects it to the compact
    ``{control_id: title}`` shape the report taxonomy loader expects, and
    writes it to the package data directory. Mirrors the security hardening
    used by other ``refresh-*`` commands (bounded response size, defensive
    Content-Length check).
    """
    from urllib.request import urlopen

    MAX_RESPONSE_BYTES = 200 * 1024 * 1024  # 200 MiB
    DEFAULT_TIMEOUT_SECONDS = 60

    click.echo(f"Fetching NIST 800-53r5 OSCAL catalog from {NIST_OSCAL_URL} ...")
    try:
        with urlopen(NIST_OSCAL_URL, timeout=DEFAULT_TIMEOUT_SECONDS) as resp:
            content_length = resp.headers.get("Content-Length")
            if content_length is not None:
                try:
                    advertised = int(content_length)
                except (TypeError, ValueError):
                    advertised = None
                if advertised is not None and advertised > MAX_RESPONSE_BYTES:
                    raise click.ClickException(
                        f"OSCAL response Content-Length ({advertised}) exceeds "
                        f"maximum ({MAX_RESPONSE_BYTES} bytes); refusing to load."
                    )
            body = resp.read(MAX_RESPONSE_BYTES + 1)
    except OSError as exc:
        # Network failure or upstream unavailable. Tell the operator what would
        # happen so they can fall back to the bundled artifact in the meantime.
        raise click.ClickException(
            f"Could not reach OSCAL catalog at {NIST_OSCAL_URL}: {exc}. "
            f"refresh-nist would normally download the OSCAL JSON, extract every "
            f"control id + title, and write the projected catalog to {out}."
        ) from exc
    if len(body) > MAX_RESPONSE_BYTES:
        raise click.ClickException(
            f"OSCAL response body exceeds maximum ({MAX_RESPONSE_BYTES} bytes); "
            "refusing to load. Verify the upstream feed before retrying."
        )

    if dry_run:
        click.echo(
            f"Would write {out} ({len(body)} bytes fetched from upstream)."
        )
        return

    catalog = _stdjson.loads(body.decode("utf-8"))
    controls: dict[str, str] = {}

    def _walk_groups(groups: list[Any]) -> None:
        for group in groups:
            if not isinstance(group, dict):
                continue
            for ctrl in group.get("controls") or []:
                _walk_control(ctrl)
            sub_groups = group.get("groups")
            if isinstance(sub_groups, list):
                _walk_groups(sub_groups)

    def _walk_control(ctrl: dict[str, Any]) -> None:
        if not isinstance(ctrl, dict):
            return
        cid = ctrl.get("id")
        title = ctrl.get("title")
        if isinstance(cid, str) and isinstance(title, str):
            controls[cid.upper()] = title
        for nested in ctrl.get("controls") or []:
            _walk_control(nested)

    root = catalog.get("catalog") or catalog
    groups = root.get("groups") if isinstance(root, dict) else None
    if isinstance(groups, list):
        _walk_groups(groups)

    if not controls:
        raise click.ClickException(
            "OSCAL catalog parsed but no controls were extracted; aborting "
            "rather than overwriting the bundled artifact with an empty file."
        )

    payload = {
        "_meta": {
            "source": NIST_OSCAL_URL,
            "schema_version": 1,
            "control_count": len(controls),
        },
        "controls": controls,
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(_stdjson.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    click.echo(f"Wrote {out} ({len(controls)} controls).")


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


@main.command("refresh-atlas")
def refresh_atlas_cmd() -> None:
    """Refresh MITRE ATLAS technique-title reference data."""
    from .refresh_atlas import refresh_atlas

    path = refresh_atlas()
    click.echo(f"Wrote {path}")


@main.command("refresh-mas")
def refresh_mas_cmd() -> None:
    """Refresh OWASP MASVS v2.1.0 + MASWE mobile reference catalogs."""
    from .refresh_mas import refresh_masvs, refresh_maswe

    click.echo(f"Wrote {refresh_masvs()}")
    click.echo(f"Wrote {refresh_maswe()}")


@main.command("parse-threat-model")
@click.argument("path", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--methodology-hint",
    default=None,
    help="Force a methodology (stride/linddun/attack_tree/pasta/vast/trike/maestro/free_form).",
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
        schema = _stdjson.loads(schema_path.read_text(encoding="utf-8"))
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
        output.write_text(text, encoding="utf-8")
        click.echo(f"Wrote {output}", err=True)
        click.echo(f"  methodology: {normalized['methodology']}", err=True)
        click.echo(f"  entries:     {normalized['extraction_summary']['entry_count']}", err=True)
    else:
        click.echo(text)


@main.command("author-threat-model")
@click.argument("run_dir", type=click.Path(exists=True, file_okay=False, path_type=Path))
def author_threat_model_cmd(run_dir: Path) -> None:
    """Build the deterministic threat-model skeleton from the asset inventory.

    Reads ``run_dir/00-context/asset-inventory.yaml`` and writes one
    normalized-TM skeleton entry per (surface, applicable-STRIDE) cell to
    ``run_dir/00-context/threat-model-skeleton.yaml``. Pure + idempotent;
    never emits a surface absent from the inventory. The apd-threat-model-author
    agent enriches/blocks each cell and emits the canonical normalized TM.
    """
    inventory_path = run_dir / "00-context" / "asset-inventory.yaml"
    if not inventory_path.exists():
        raise click.ClickException(
            f"asset-inventory.yaml not found at {inventory_path}; run intake first."
        )
    envelope = build_skeleton_from_inventory_file(inventory_path)
    out_path = run_dir / "00-context" / "threat-model-skeleton.yaml"
    out_path.write_text(yaml.safe_dump(envelope, sort_keys=False), encoding="utf-8")
    click.echo(
        f"author-threat-model: wrote {envelope['extraction_summary']['entry_count']} "
        f"skeleton entries to {out_path}"
    )


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
            yaml.safe_load(run_cfg_path.read_text(encoding="utf-8"))
            if run_cfg_path.exists()
            else {}
        ) or {}
    except yaml.YAMLError as exc:
        raise click.UsageError(f".apd-run.yaml is not valid YAML: {exc}") from exc
    tuning = run_cfg.get("attack_path_analysis", {}) or {}
    params = EnumerationParams(
        max_hop=int(tuning.get("max_hop", 8)),
        max_paths_per_pair=int(tuning.get("max_paths_per_pair", 50)),
        bottleneck_threshold=int(tuning.get("bottleneck_threshold", 5)),
    )
    # Findings are bounded by default for every run: at most
    # max_risk_findings_per_pair (default 1) risk findings per (attacker,
    # crown_jewel) pair, with the suppressed remainder collapsed into one
    # aggregate uncertainty finding. attack-paths.yaml keeps every path.
    max_risk_per_pair = int(tuning.get("max_risk_findings_per_pair", 1))
    fan_out_warn = int(tuning.get("fan_out_warn_threshold", 500))

    try:
        result = build_graph(run_dir)
    except BuilderBlocked as exc:
        _write_blocked_finding(synth, reason=str(exc))
        click.echo(f"analyze-attack-paths: blocked - {exc}")
        return

    graph = result.graph
    if result.orphan_crown_jewels:
        click.echo(
            "analyze-attack-paths: WARNING - crown jewels with no inbound edges "
            "(no asset realizes them; they will enumerate 0 paths): "
            + ", ".join(result.orphan_crown_jewels)
        )
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
        bound=True,
        max_risk_per_pair=max_risk_per_pair,
    )

    # Density warning (no hard ceiling): a large raw path count signals a
    # dense graph whose findings are now bounded but whose enumeration may be
    # worth tuning. attack-paths.yaml still retains every path.
    if len(all_paths) > fan_out_warn:
        click.echo(
            "analyze-attack-paths: WARNING - high path fan-out "
            f"({len(all_paths)} paths > {fan_out_warn}); findings are bounded "
            "to max_risk_findings_per_pair, but consider lowering max_hop / "
            "max_paths_per_pair if enumeration is slow."
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
    (synth / "attack-path.findings.yaml").write_text(
        yaml.safe_dump(doc, sort_keys=False),
        encoding="utf-8",
    )


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
        doc = yaml.safe_load(f.read_text(encoding="utf-8")) or {}
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
        doc = yaml.safe_load(f.read_text(encoding="utf-8")) or {}
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
    path.write_text(yaml.safe_dump(doc, sort_keys=False), encoding="utf-8")


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
    path.write_text(yaml.safe_dump(doc, sort_keys=False), encoding="utf-8")


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
    path.write_text(yaml.safe_dump(doc, sort_keys=False), encoding="utf-8")


def _write_findings(path: Path, findings: list[dict[str, Any]]) -> None:
    """Emit a ``*.findings.yaml`` doc with the singular ``finding:`` root key
    (per ``validate.RECORD_KINDS``). The internal Python variable stays
    plural — only the YAML root key is singular.
    """
    doc = {"schema_version": 1, "finding": findings}
    path.write_text(yaml.safe_dump(doc, sort_keys=False), encoding="utf-8")


@main.command("build-report",
              help="Generate the HTML advisory report for a completed run.")
@click.argument("run_dir", type=click.Path(exists=True, file_okay=False, path_type=pathlib.Path))
@click.option("--out", "out_dir", type=click.Path(path_type=pathlib.Path), default=None,
              help="Override output directory. Default: <run_dir>/40-synthesis/report-html/")
@click.option("--quiet", is_flag=True, help="Suppress per-file progress messages.")
def build_report_cmd(run_dir, out_dir, quiet) -> None:  # type: ignore[no-untyped-def]
    from .report.build import BundleFreshnessError, ReportBuildError, build_report
    from .report.emit import BundleMissingError
    from .report.loader import MalformedArtifactError, MissingArtifactError
    try:
        target, data = build_report(run_dir, out_dir, quiet=quiet)
    except (
        MissingArtifactError,
        MalformedArtifactError,
        BundleMissingError,
        BundleFreshnessError,
        ReportBuildError,
    ) as exc:
        click.echo(f"Error: {exc}", err=True)
        raise SystemExit(1) from None
    # Surface per-section failures so CI can grep for them and operators see
    # which sections rendered with placeholders. The report itself still emits
    # successfully — see data.meta.section_errors in data.js.
    section_errors = (data.get("meta") or {}).get("section_errors") or {}
    for name, err in section_errors.items():
        click.echo(f"warning: section '{name}' failed: {err}", err=True)
    if not quiet:
        click.echo(f"HTML report at {target}")


@main.command("canonicalize")
@click.argument("run_dir", type=click.Path(exists=True, file_okay=False, path_type=Path))
def canonicalize_cmd(run_dir: Path) -> None:
    """Structurally canonicalize specialist findings/capabilities in place.

    Idempotent, whole-run: normalizes the record envelope (singular root key,
    unwraps per-record wrappers, injects schema_version), recomputes every
    deterministic id (tooling is authoritative), and rewrites cross_references.
    Structural only — never edits titles, excerpts, or evidence.
    """
    from .canonicalize import CanonicalizeCollision, canonicalize_run

    try:
        result = canonicalize_run(run_dir)
    except CanonicalizeCollision as exc:
        click.echo(f"canonicalize: blocked - {exc}", err=True)
        raise SystemExit(1) from None
    for path, msg in result.parse_errors:
        click.echo(f"canonicalize: SKIPPED unparseable file {path}: {msg}", err=True)
    click.echo(
        f"canonicalize: {result.records_canonicalized} records recanonicalized, "
        f"{result.cross_refs_rewritten} cross-refs rewritten"
        + (
            f", {len(result.parse_errors)} files skipped (unparseable)"
            if result.parse_errors
            else ""
        )
    )
    # FW-1: an unparseable specialist file must be a HARD signal, not a quiet
    # note buried in a zero-exit summary. The pass still canonicalizes every
    # parseable file first (the malformed one is skipped, not aborted), then we
    # exit nonzero so standalone/CI callers and the runner surface it at the
    # canonicalize step rather than as a confusing downstream tier-gate error.
    if result.parse_errors:
        raise SystemExit(1)


@main.command("cluster-candidates")
@click.argument("run_dir", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option(
    "--max-group-size",
    default=8,
    show_default=True,
    help="Maximum members per candidate group; larger clusters are split.",
)
def cluster_candidates_cmd(run_dir: Path, max_group_size: int) -> None:
    """5a: mechanically detect cluster candidates; emit cluster-candidates.yaml."""
    from .synthesis.cluster import build_candidates

    synth = run_dir / "40-synthesis"
    synth.mkdir(parents=True, exist_ok=True)
    run_cfg_path = run_dir / ".apd-run.yaml"
    try:
        run_cfg: dict[str, Any] = (
            yaml.safe_load(run_cfg_path.read_text(encoding="utf-8"))
            if run_cfg_path.exists()
            else {}
        ) or {}
    except yaml.YAMLError as exc:
        raise click.UsageError(f".apd-run.yaml is not valid YAML: {exc}") from exc
    cap = int(run_cfg.get("max_candidate_group_size", max_group_size))
    result = build_candidates(run_dir, max_group_size=cap)
    doc = {"schema_version": 1, "generated_by": "apd-gauntlet", "groups": result.groups}
    (synth / "cluster-candidates.yaml").write_text(
        yaml.safe_dump(doc, sort_keys=False), encoding="utf-8"
    )
    click.echo(f"cluster-candidates: wrote {len(result.groups)} candidate groups")


@main.command("apply-clusters")
@click.argument("run_dir", type=click.Path(exists=True, file_okay=False, path_type=Path))
def apply_clusters_cmd(run_dir: Path) -> None:
    """5c: apply cluster-decisions.yaml; emit deduped + severity-disagreements + rejected."""
    from .synthesis.apply import AdjudicationMissing, apply_clusters

    try:
        result = apply_clusters(run_dir)
    except AdjudicationMissing as exc:
        click.echo(f"apply-clusters: blocked - {exc}", err=True)
        raise SystemExit(2) from None
    if result.unresolved_authored_merges:
        click.echo(
            f"apply-clusters: WARNING - {result.unresolved_authored_merges} authored "
            "merge decision(s) could not be applied (members absent or mixed kinds); "
            "the source records are logged in 40-synthesis/rejected-records.yaml",
            err=True,
        )
    click.echo(
        f"apply-clusters: wrote {len(result.findings)} findings, "
        f"{len(result.capabilities)} capabilities, "
        f"{len(result.contradictions)} contradictions, "
        f"{len(result.rejected)} rejected"
    )


@main.command("rollup")
@click.argument("run_dir", type=click.Path(exists=True, file_okay=False, path_type=Path))
def rollup_cmd(run_dir: Path) -> None:
    """5d: aggregate deduped records into the canonical coverage YAMLs."""
    from .synthesis.rollup import build_rollups

    result = build_rollups(run_dir)
    taxonomies = sum(x is not None for x in (result.cwe, result.owasp, result.d3fend))
    click.echo(
        f"rollup: wrote {len(result.nist)} controls, {len(result.attack)} techniques, "
        f"{len(result.matrix)} components, {taxonomies} extra coverage files"
    )


@main.command("domain-coverage-delta")
@click.argument("run_dir", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option(
    "--domains-dir",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=Path("domains"),
)
def domain_coverage_delta_cmd(run_dir: Path, domains_dir: Path) -> None:
    """5h-i: deterministic coverage-delta pre-pass; emit domain-coverage-delta.yaml."""
    from .synthesis.coverage_delta import build_coverage_delta

    path = build_coverage_delta(run_dir, domains_dir)
    doc = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    click.echo(f"domain-coverage-delta: wrote {len(doc.get('candidates') or [])} candidates")


@main.command("draft-domain-improvements")
@click.argument("run_dir", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option(
    "--domains-dir",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=Path("domains"),
)
@click.option("--out", "out", type=click.Path(path_type=Path), default=None,
              help="Patch output path. Default: <run_dir>/40-synthesis/domain-improvements.patch")
@click.option("--id", "ids", multiple=True, help="Only draft these dimpr- ids (repeatable).")
@click.option("--type", "types", multiple=True, help="Filter by improvement_type (repeatable).")
@click.option("--target-pack", "packs", multiple=True, help="Filter by target_pack (repeatable).")
def draft_domain_improvements_cmd(run_dir, domains_dir, out, ids, types, packs) -> None:  # type: ignore[no-untyped-def]
    """On-demand: insert chosen draft_snippets into a temp copy, gate, emit a diff."""
    from .synthesis.draft import DraftError, draft_domain_improvements

    out_path = out or (run_dir / "40-synthesis" / "domain-improvements.patch")
    try:
        res = draft_domain_improvements(
            run_dir, domains_dir, out_path, ids=ids, types=types, packs=packs
        )
    except DraftError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1) from None

    if not res.drafted and not res.dropped:
        click.echo("0 opportunities selected; nothing to draft")
        return
    click.echo(f"{len(res.drafted)} drafted, {len(res.dropped)} dropped")
    for dimpr_id, tfile, reason in res.dropped:
        click.echo(f"  DROPPED {dimpr_id} ({tfile}): {reason}")
    for dimpr_id, note in res.retargeted:
        click.echo(f"  RETARGETED {dimpr_id}: {note}")
    if res.patch_written:
        click.echo(f"Wrote patch to {out_path}")


@main.command("mint-improvement-id")
@click.option("--type", "improvement_type", required=True, help="improvement_type")
@click.option("--target-pack", "target_pack", required=True, help="target_pack name")
@click.option("--target-file", "target_file", required=True, help="target_file within the pack")
@click.option("--ref", "primary_ref", required=True, help="evidence[0].ref (the primary ref)")
def mint_improvement_id_cmd(  # type: ignore[no-untyped-def]
    improvement_type, target_pack, target_file, primary_ref
) -> None:
    """Print the canonical dimpr-<sha8> id for a domain-improvement record.

    FW-5: the apd-domain-auditor is an execution-light (Read/Glob/Grep/Write)
    judgment agent that cannot hand-compute the sha256 the validator recomputes.
    This wraps the SAME ``compute_improvement_id`` the linter uses, so the
    at-capture id is GUARANTEED to match the gate — the auditor calls it once it
    has chosen the 4-tuple (improvement_type|target_pack|target_file|evidence[0].ref).
    """
    from .linters import compute_improvement_id

    click.echo(
        compute_improvement_id(improvement_type, target_pack, target_file, primary_ref)
    )


@main.command("audit-report")
@click.argument("run_dir", type=click.Path(exists=True, file_okay=False, path_type=Path))
def audit_report_cmd(run_dir: Path) -> None:
    """5g: structurally cross-check data.js against the authoritative YAMLs."""
    from .synthesis.audit import audit_report

    result = audit_report(run_dir)
    failed = [c for c in result.checks if c["status"] == "fail"]
    structural_failed = sum(1 for c in failed if c.get("klass", "structural") == "structural")
    editorial_failed = sum(1 for c in failed if c.get("klass") == "editorial")
    click.echo(
        f"audit-report: {result.status} ({len(result.checks)} checks, {len(failed)} failed; "
        f"structural_failed={structural_failed} editorial_failed={editorial_failed})"
    )
    for c in failed:
        klass = c.get("klass", "structural")
        click.echo(f"  FAIL [{klass}]: {c['name']} — {c.get('detail', '')}", err=True)
    if result.status == "fail":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
