"""apd-gauntlet CLI entry point."""
from __future__ import annotations

import json as _stdjson
import pathlib

import click

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
from .validate import ValidationReport, run_cross_file_pass, run_schema_pass, run_semantic_pass


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
def init_run_cmd(run_id, inputs, domain, root, taxonomies) -> None:  # type: ignore[no-untyped-def]
    parsed = (
        [t.strip() for t in taxonomies.split(",") if t.strip()] if taxonomies else None
    )
    target = scaffold_run(run_id, inputs, domain, root, taxonomies=parsed)
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


if __name__ == "__main__":
    main()
