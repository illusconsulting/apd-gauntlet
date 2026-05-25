"""apd-gauntlet CLI entry point."""
from __future__ import annotations
import pathlib
import click
from . import __version__
from .validate import run_schema_pass, run_semantic_pass, ValidationReport


@click.group(
    name="apd-gauntlet",
    help="APD Gauntlet — validator and tooling for APD security architecture reviews.",
)
@click.version_option(__version__, prog_name="apd-gauntlet")
def main():
    """Root command group."""


@main.command(help="Validate all records under a run directory.")
@click.argument("run_dir", type=click.Path(exists=True, file_okay=False, path_type=pathlib.Path))
@click.option("--schema-only", is_flag=True, help="Run schema validation only (skip semantic + cross-file passes).")
@click.option("--strict", is_flag=True, help="Treat warnings as errors.")
@click.option("--json", "as_json", is_flag=True, help="Emit JSON output for CI consumption.")
def validate(run_dir, schema_only, strict, as_json):
    schema_rep = run_schema_pass(run_dir)
    if schema_only:
        merged = schema_rep
    else:
        semantic_rep = run_semantic_pass(run_dir)
        merged = ValidationReport(
            errors=schema_rep.errors + semantic_rep.errors,
            warnings=schema_rep.warnings + semantic_rep.warnings,
            files_seen=max(schema_rep.files_seen, semantic_rep.files_seen),
            records_seen=schema_rep.records_seen,
        )
    if strict:
        merged.errors.extend(merged.warnings)
        merged.warnings = []
    if as_json:
        import json as _json
        click.echo(_json.dumps({
            "errors":   [{"file": str(v.file), "id": v.record_id, "message": v.message, "path": v.path} for v in merged.errors],
            "warnings": [{"file": str(v.file), "id": v.record_id, "message": v.message, "path": v.path} for v in merged.warnings],
            "records":  merged.records_seen,
            "files":    merged.files_seen,
        }, indent=2))
    else:
        click.echo(merged.render())
    raise SystemExit(0 if merged.is_clean else 1)


if __name__ == "__main__":
    main()
