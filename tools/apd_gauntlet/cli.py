"""apd-gauntlet CLI entry point."""
from __future__ import annotations

import hashlib
import json as _stdjson
import math
import pathlib
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal, NoReturn

import click
import yaml

if TYPE_CHECKING:
    from .attack_path.enumerate import EnumerationParams
    from .attack_path.enumerate import Path as APath
    from .attack_path.graph import Edge, Graph, Node

from . import FRAMEWORK_VERSION, __version__
from . import resources as _resources
from .build_domain_skill import build_domain_skill
from .init_run import UnsafeInputsError, scaffold_run
from .lint_agents import lint_agents_dir
from .lint_skills import lint_skills_dir
from .linters import check_capability_id, check_finding_id
from .manual_audit import write_prompts
from .refresh_cwe import refresh_cwe
from .refresh_d3fend import refresh_d3fend
from .refresh_mitre import fetch_and_project
from .refresh_owasp import refresh_owasp
from .summary import render_summary, summarize_run
from .threat_model.author import build_skeleton_from_inventory_file
from .validate import (
    ValidationReport,
    add_excerpt_violations,
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
@click.option(
    "--strict-excerpts",
    is_flag=True,
    help=(
        "Make an evidence excerpt that is not verbatim in its cited inputs/ file an "
        "ERROR (a WARNING by default). Ignored with --schema-only."
    ),
)
def validate(  # type: ignore[no-untyped-def]
    run_dir, schema_only, strict, as_json, errors_only, tier, strict_excerpts
) -> None:
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
        add_excerpt_violations(
            merged, run_dir, records_dir=target, strict_excerpts=strict_excerpts
        )
    else:
        semantic_rep = run_semantic_pass(target)
        cross_file_rep = run_cross_file_pass(target, strict_excerpts=strict_excerpts)
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
    default=None,
)
@click.option(
    "--out",
    type=click.Path(file_okay=False, path_type=pathlib.Path),
    default=pathlib.Path(".claude/skills/apd-domain"),
)
@click.option("--framework-version", default=FRAMEWORK_VERSION)
@click.option(
    "--full-only",
    is_flag=True,
    default=False,
    help="Write only the full cross-goal SKILL.md; skip the per-goal by-goal/ "
    "sidecars (which lens agents read to bound context on multi-domain runs).",
)
def build_domain_skill_cmd(domain_names, domains_dir, out, framework_version, full_only) -> None:  # type: ignore[no-untyped-def]
    if domains_dir is None:
        domains_dir = _resources.domains_dir()
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
    try:
        target = scaffold_run(
            run_id,
            inputs,
            list(domains),
            root,
            taxonomies=parsed,
            threat_model=threat_model,
            methodology_hint=methodology_hint,
        )
    except UnsafeInputsError as e:
        click.echo(f"init-run: {e}", err=True)
        raise SystemExit(1) from None
    click.echo(f"Run scaffolded at {target}")


@main.command("validate-domain")
@click.argument("domain_names", nargs=-1, required=True)
@click.option(
    "--domains-dir",
    type=click.Path(exists=True, file_okay=False, path_type=pathlib.Path),
    default=None,
)
def validate_domain_cmd(domain_names, domains_dir) -> None:  # type: ignore[no-untyped-def]
    from jsonschema import Draft202012Validator

    if domains_dir is None:
        domains_dir = _resources.domains_dir()
    schema = _resources.read_schema("domain.schema.json")
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

    schema = _resources.read_schema("run-config.schema.json")
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


@main.command("lint-skills")
@click.option(
    "--skill-dir",
    type=click.Path(exists=True, file_okay=False, path_type=pathlib.Path),
    default=pathlib.Path(".claude/skills"),
    show_default=True,
)
def lint_skills_cmd(skill_dir) -> None:  # type: ignore[no-untyped-def]
    errors = lint_skills_dir(skill_dir)
    if errors:
        for e in errors:
            click.echo(e)
        raise SystemExit(1)
    n = sum(1 for p in skill_dir.iterdir() if p.is_dir())
    click.echo(f"Lint clean: {n} skills checked.")


@main.command("summarize")
@click.argument("run_dir", type=click.Path(exists=True, file_okay=False, path_type=pathlib.Path))
@click.option("--json", "as_json", is_flag=True)
@click.option(
    "--record-attempts",
    "attempts_json",
    metavar="JSON",
    help=(
        "Before summarising, validate this run-attempts object (run-attempts.schema.json) and "
        "write it to RUN_DIR/.apd-state/attempts.yaml. Exits 2 when it is not JSON, and 1 when "
        "it does not match the schema or cannot be written; a rejected object writes nothing."
    ),
)
def summarize_cmd(run_dir, as_json, attempts_json) -> None:  # type: ignore[no-untyped-def]
    if attempts_json is not None:
        from .measure.attempts import AttemptsError, write_attempts

        try:
            attempts = _stdjson.loads(attempts_json)
        except (ValueError, RecursionError) as exc:
            raise click.BadParameter(
                f"not valid JSON: {exc}", param_hint="'--record-attempts'"
            ) from exc
        try:
            recorded = write_attempts(run_dir, attempts)
        except AttemptsError as exc:
            click.echo(f"Error: {exc}", err=True)
            raise SystemExit(1) from exc
        click.echo(f"Recorded attempts -> {recorded}", err=True)
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

    schema = _resources.read_schema("run-config.schema.json")
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


@main.command("resume-plan")
@click.argument("run_dir", type=click.Path(exists=True, file_okay=False, path_type=pathlib.Path))
@click.option("--json", "as_json", is_flag=True, help="Emit the plan as one line of JSON.")
def resume_plan_cmd(run_dir: pathlib.Path, as_json: bool) -> None:
    """Report which agent steps of a run are already complete (read-only).

    A step is complete when every file of one of its output sets is present, non-empty
    and schema-valid; the runner resumes from this and skips the complete steps. Writes
    nothing. Exits 2 when RUN_DIR/.apd-run.yaml is missing, unparseable or invalid, and 3
    when the run was created by a different framework major than this engine.
    """
    from .resume_plan import (
        EngineMismatch,
        RunConfigError,
        build_resume_plan,
        check_engine_compat,
    )

    try:
        check_engine_compat(run_dir)
    except RunConfigError as e:
        click.echo(str(e), err=True)
        raise SystemExit(2) from e
    except EngineMismatch as e:
        click.echo(str(e), err=True)
        raise SystemExit(3) from e

    plan = build_resume_plan(run_dir)
    if as_json:
        click.echo(_stdjson.dumps(plan))
        return
    click.echo(f"engine {plan['engine_version']}")
    for step in plan["steps"]:
        state = "complete" if step["complete"] else "pending"
        click.echo(f"{state}  {step['label']}  {step['reason']}")


@main.command("manual-audit-prompts")
@click.argument("run_dir", type=click.Path(exists=True, file_okay=False, path_type=pathlib.Path))
def manual_audit_prompts_cmd(run_dir) -> None:  # type: ignore[no-untyped-def]
    """Render 40-synthesis/manual-audit-prompts.md from blocked deduped findings.

    Reads RUN_DIR/40-synthesis/deduped-findings.yaml, filters disposition:blocked
    records, and writes copy-paste audit commands (kubectl/istioctl) keyed off a
    small keyword->template table. Deterministic, LLM-free, byte-stable.
    """
    try:
        out_path, blocked = write_prompts(run_dir)
    except FileNotFoundError as e:
        click.echo(f"No deduped-findings.yaml under {run_dir} (looked at {e})", err=True)
        raise SystemExit(1) from e
    click.echo(f"manual-audit-prompts: wrote {out_path} ({blocked} blocked findings)")


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
    # ADR-0022 — also refresh the derived detection overlay catalog from the same
    # bundle (technique -> required data components). Written alongside the
    # mitigations crosswalk so a single refresh-mitre keeps both current.
    from .refresh_mitre import fetch_and_project_detection

    detection_out = out.parent / "mitre-attack-detection.json"
    fetch_and_project_detection(detection_out)
    click.echo(f"Wrote {detection_out}")


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


@main.command("refresh-capec")
def refresh_capec_cmd() -> None:
    """Refresh MITRE CAPEC reference data (the derived CWE<->ATT&CK bridge catalog)."""
    from .refresh_capec import refresh_capec

    path = refresh_capec()
    click.echo(f"Wrote {path}")


@main.command("refresh-crosswalks")
@click.option("--csf2-json", required=True,
              type=click.Path(exists=True, dir_okay=False, path_type=pathlib.Path),
              help="NIST CSF 2.0 CPRT JSON export (download from csrc.nist.gov/projects/cprt).")
@click.option("--hipaa-json", required=True,
              type=click.Path(exists=True, dir_okay=False, path_type=pathlib.Path),
              help="NIST SP 800-66r2 CPRT JSON export.")
def refresh_crosswalks_cmd(csf2_json, hipaa_json) -> None:  # type: ignore[no-untyped-def]
    """Ground the HIPAA + CSF 2.0 compliance crosswalks against NIST CPRT exports."""
    from .refresh_crosswalks import refresh_crosswalks

    report = refresh_crosswalks(csf2_json, hipaa_json)
    click.echo(f"CSF2: {report['csf2']['kept']} mappings grounded "
               f"({len(report['csf2']['dropped'])} dropped as out-of-scope)")
    for d in report["csf2"]["dropped"]:
        click.echo(f"  DROPPED {d['target_id']} -> {d['nist']}: {d['reason']}")
    click.echo(f"HIPAA: {report['hipaa']['kept']} mappings; "
               f"unmatched ids (curated title kept): {report['hipaa']['unmatched']}")


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
        schema = _resources.read_schema("threat-model-normalized.schema.json")
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
                # Per docs/adrs/0010-attack-path-analysis-on-partial-graphs.md
                # (decision rule 2), a missing crown-jewel declaration yields
                # this single blocked finding instead of an enumeration or a
                # guessed target. The builder applies the same rule to missing
                # attacker positions and ambiguous node names. The ADR's
                # apath-blocked- id prefix is not used; the id is apath-<hash>.
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


@main.command("assemble-inventory")
@click.argument("run_dir", type=click.Path(exists=True, file_okay=False, path_type=Path))
def assemble_inventory_cmd(run_dir: Path) -> None:
    """Mint deterministic asset-/idn-/tb- ids and wire trust-boundary crosses (by name)."""
    from .assemble_inventory import assemble_inventory

    changed = assemble_inventory(run_dir)
    click.echo(
        f"assemble-inventory: {changed} asset id(s) (re)minted under {run_dir}/00-context/"
    )


@main.command("assemble-c4")
@click.argument("run_dir", type=click.Path(exists=True, file_okay=False, path_type=Path))
def assemble_c4_cmd(run_dir: Path) -> None:
    """Assemble the grounded C4 architecture model -> 40-synthesis/c4-model.yaml.

    Gated on 40-synthesis/asset-graph.yaml; the code tiers (L3/L4) are populated
    only when 00-context/code-evidence-index.yaml exists. Mints all c4-/c4e- ids
    and the per-node finding/capability badges (the SOLE minter; ADR-0020).
    """
    from .assemble_c4 import assemble_c4

    summary = assemble_c4(run_dir)
    if not summary:
        click.echo(
            f"assemble-c4: no asset-graph.yaml under {run_dir}/40-synthesis/ - skipped"
        )
        return
    click.echo(
        "assemble-c4: wrote 40-synthesis/c4-model.yaml "
        f"({summary['node_count']} nodes = "
        f"{summary['system_count']} system / {summary['person_count']} person / "
        f"{summary['external_system_count']} external_system / "
        f"{summary['container_count']} container / "
        f"{summary['component_count']} component / {summary['code_count']} code; "
        f"{summary['uses_edge_count']} uses edges; "
        f"{summary['not_analyzed_container_count']} not_analyzed container(s); "
        f"{summary['unlocalized_finding_count']} unlocalized finding(s))"
    )


@main.command("canonicalize")
@click.argument("run_dir", type=click.Path(exists=True, file_okay=False, path_type=Path))
def canonicalize_cmd(run_dir: Path) -> None:
    """Structurally canonicalize specialist findings/capabilities in place.

    Idempotent, whole-run: normalizes the record envelope (singular root key,
    unwraps per-record wrappers, injects schema_version), recomputes every
    deterministic id (tooling is authoritative), and rewrites cross_references.
    Also mints the 00-context ids agents no longer emit (cev- on code-evidence-index
    entries; tm- on normalized threat-model entries, plus an absent
    inferred_apd_goals), only where absent: an existing value is never rewritten.
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
            f", {result.context_ids_minted} context ids minted"
            if result.context_ids_minted
            else ""
        )
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
    from .synthesis.apply import AdjudicationMissing, SerializationIntegrityError, apply_clusters

    try:
        result = apply_clusters(run_dir)
    except AdjudicationMissing as exc:
        click.echo(f"apply-clusters: blocked - {exc}", err=True)
        raise SystemExit(2) from None
    except SerializationIntegrityError as exc:
        click.echo(
            f"apply-clusters: serialization integrity error - {exc}; "
            "a schema-string field held a non-string or repr-poisoned value "
            "and was NOT written. Inspect the source records and re-run.",
            err=True,
        )
        raise SystemExit(3) from None
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
    default=None,
)
def domain_coverage_delta_cmd(run_dir: Path, domains_dir: Path | None) -> None:
    """5h-i: deterministic coverage-delta pre-pass; emit domain-coverage-delta.yaml."""
    from .synthesis.coverage_delta import build_coverage_delta

    if domains_dir is None:
        domains_dir = _resources.domains_dir()
    path = build_coverage_delta(run_dir, domains_dir)
    doc = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    click.echo(f"domain-coverage-delta: wrote {len(doc.get('candidates') or [])} candidates")


@main.command("draft-domain-improvements")
@click.argument("run_dir", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option(
    "--domains-dir",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=None,
)
@click.option("--out", "out", type=click.Path(path_type=Path), default=None,
              help="Patch output path. Default: <run_dir>/40-synthesis/domain-improvements.patch")
@click.option("--id", "ids", multiple=True, help="Only draft these dimpr- ids (repeatable).")
@click.option("--type", "types", multiple=True, help="Filter by improvement_type (repeatable).")
@click.option("--target-pack", "packs", multiple=True, help="Filter by target_pack (repeatable).")
def draft_domain_improvements_cmd(run_dir, domains_dir, out, ids, types, packs) -> None:  # type: ignore[no-untyped-def]
    """On-demand: insert chosen draft_snippets into a temp copy, gate, emit a diff."""
    from .synthesis.draft import DraftError, draft_domain_improvements

    if domains_dir is None:
        domains_dir = _resources.domains_dir()
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


@main.command("usage")
@click.argument("run_dir", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option(
    "--otel",
    "otel_file",
    required=True,
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help=(
        "OpenTelemetry logs export in OTLP/JSON (the Collector file exporter's output). "
        "The console exporter's output is refused; see docs/measuring-changes.md."
    ),
)
@click.option(
    "--workflow-run",
    "workflow_run",
    metavar="ID",
    default=None,
    help="Count only api_request events whose workflow.run_id is ID.",
)
@click.option("--json", "as_json", is_flag=True, help="Print the written summary as JSON.")
def usage_cmd(run_dir: Path, otel_file: Path, workflow_run: str | None, as_json: bool) -> None:
    """Summarise tokens and cost per agent and phase into RUN_DIR/.apd-state/usage.yaml.

    Reads Claude Code's claude_code.api_request events from the export, adds the
    decision-model spend under 40-synthesis/decisions/, and writes the summary.
    Exits 0 when written, 1 when no api_request event is left after filtering
    (nothing is written) or usage.yaml cannot be written, and 2 when the export
    or a decision record cannot be read.
    """
    from .measure.runs import is_run_dir
    from .measure.usage import (
        USAGE_RELPATH,
        UsageParseError,
        iter_api_requests,
        summarize_decisions,
        summarize_usage,
        write_usage,
    )

    if not is_run_dir(run_dir):
        raise click.BadParameter(
            f"{run_dir} is not a run directory (no .apd-run.yaml)", param_hint="'RUN_DIR'"
        )
    try:
        summary = summarize_usage(
            iter_api_requests(otel_file), source=otel_file, workflow_run=workflow_run
        )
        if summary["totals"]["requests"] == 0:
            message = f"no api_request events in {otel_file}"
            if workflow_run is not None:
                runs = ", ".join(summary["source"]["workflow_runs"]) or "none"
                message += f" for workflow run {workflow_run} (workflow runs in the file: {runs})"
            click.echo(f"Error: {message}; nothing written", err=True)
            raise SystemExit(1)
        decisions = summarize_decisions(run_dir)
    except UsageParseError as exc:
        click.echo(f"Error: {exc}", err=True)
        raise SystemExit(2) from exc
    warnings = summary.pop("warnings")
    summary["decision_models"] = decisions
    summary["cost_usd_all"] = round(
        summary["totals"]["cost_usd"] + decisions["totals"]["cost_usd"], 9
    )
    summary["warnings"] = warnings
    try:
        written = write_usage(run_dir, summary)
    except OSError as exc:
        click.echo(
            f"Error: {run_dir / USAGE_RELPATH}: cannot write: {exc.strerror or exc}",
            err=True,
        )
        raise SystemExit(1) from exc
    for warning in warnings:
        click.echo(f"warning: {warning}", err=True)
    if as_json:
        click.echo(_stdjson.dumps(summary, indent=2))
        return
    totals = summary["totals"]
    click.echo(
        f"usage: {totals['requests']} api_request events, cost_usd {totals['cost_usd']:.6f} "
        f"(with decision models {summary['cost_usd_all']:.6f}) -> {written}"
    )
    for phase, row in summary["by_phase"].items():
        tokens = sum(row[k] for k in (
            "input_tokens", "output_tokens", "cache_read_tokens", "cache_creation_tokens"
        ))
        click.echo(
            f"  {phase}: {row['requests']} requests, {tokens} tokens, "
            f"cost_usd {row['cost_usd']:.6f}"
        )


_SINGLE_RUN_WARNING = "gates applied to a single run per side; run each configuration twice"


def _refuse(message: str) -> NoReturn:
    """Print ``Error: <message>`` on stderr and exit 2 (a usage error)."""
    click.echo(f"Error: {message}", err=True)
    raise SystemExit(2)


@main.command("compare-runs")
@click.argument("baseline", type=click.Path(path_type=Path))
@click.argument("candidate", type=click.Path(path_type=Path))
@click.option("--json", "as_json", is_flag=True, help="Print the comparison as JSON.")
@click.option(
    "--gates",
    "gates_file",
    type=click.Path(path_type=Path),
    default=None,
    help="Evaluate the gates in this file (the proposals are in eval/gates.yaml).",
)
@click.option(
    "--excuse",
    "excuses",
    multiple=True,
    metavar="VALUE",
    help=(
        "Repeatable. '<gate-id>:<reason>' excuses that gate; any other value is a "
        "finding id whose loss is accepted."
    ),
)
@click.option(
    "--strict", is_flag=True, help="Exit 1 when a gate is not available (pass_with_gaps)."
)
def compare_runs_cmd(
    baseline: Path,
    candidate: Path,
    as_json: bool,
    gates_file: Path | None,
    excuses: tuple[str, ...],
    strict: bool,
) -> None:
    """Compare a CANDIDATE run, or run set, with a BASELINE and apply the comparison gates.

    Each side is a run directory, or a name whose runs are NAME-r1, NAME-r2, ...
    (see docs/measuring-changes.md). Every baseline run is compared with every
    candidate run, and the gates judge the medians. Exits 0 when no gate fails
    (or without --gates), 1 when a gate fails or, under --strict, when a gate is
    not available, and 2 when a side does not resolve, both sides share a run,
    a baseline run has no findings, the runs have different inputs, a run
    fails to load, or the gates file cannot be read.
    """
    from dataclasses import replace

    from .measure.compare import (
        MissingRuns,
        compare_sides,
        comparison_json,
        render_text,
        resolve_side,
    )
    from .measure.gates import (
        GatesError,
        apply_excuses,
        evaluate,
        load_gates,
        overall,
        split_excuses,
    )
    from .measure.runs import RunLoadError, RunSnapshot, load_run

    gates = None
    if gates_file is not None:
        try:
            gates = load_gates(gates_file)
        except GatesError as exc:
            _refuse(str(exc))
    try:
        gate_excuses, finding_excuses = split_excuses(
            excuses, [g.id for g in gates or ()]
        )
    except ValueError as exc:
        raise click.BadParameter(str(exc), param_hint="'--excuse'") from exc

    sides: dict[str, list[Path]] = {}
    for side, path in (("baseline", baseline), ("candidate", candidate)):
        try:
            sides[side] = resolve_side(path)
        except MissingRuns as exc:
            _refuse(f"{side} not found: {exc}")

    seen: dict[Path, tuple[str, Path]] = {}
    for side, paths in sides.items():
        for path in paths:
            real = path.resolve()  # each path is a run directory, so no link loop
            if real in seen:
                other_side, other = seen[real]
                _refuse(
                    f"{other_side} run {other} and {side} run {path} are the same run "
                    f"directory ({real})"
                )
            seen[real] = (side, path)

    snapshots: dict[str, list[RunSnapshot]] = {}
    for side, paths in sides.items():
        snapshots[side] = []
        for path in paths:
            try:
                snapshots[side].append(load_run(path))
            except RunLoadError as exc:
                _refuse(f"cannot load {side} run {path}: {exc}")
            except OSError as exc:
                where = exc.filename if exc.filename is not None else path
                _refuse(f"cannot load {side} run {path}: {where}: cannot read: "
                        f"{exc.strerror or exc}")

    for run in snapshots["baseline"]:
        if not run.findings:
            _refuse(
                f"baseline run {run.path} has no findings; a scaffold or unfinished run "
                "is no baseline (docs/measuring-changes.md)"
            )
    digests = [
        (r.path, r.inputs_sha256)
        for r in (*snapshots["baseline"], *snapshots["candidate"])
        if r.inputs_sha256 is not None
    ]
    for path, digest in digests[1:]:
        first, first_digest = digests[0]
        if digest != first_digest:
            _refuse(
                f"runs over different inputs: {first} and {path} have different inputs/ "
                f"(sha256 {first_digest[:12]}… and {digest[:12]}…)"
            )

    comparison = compare_sides(
        snapshots["baseline"], snapshots["candidate"], excused=finding_excuses
    )
    outcomes = None
    status: str = "delta_only"
    extra: list[str] = []
    if gates is not None:
        evaluated = evaluate(gates, comparison.values, comparison.reasons)
        outcomes = apply_excuses(evaluated, gate_excuses)
        status = overall(outcomes)
        if min(len(comparison.baseline), len(comparison.candidate)) == 1:
            extra.append(_SINGLE_RUN_WARNING)
        # apply_excuses leaves a gate that passed as it is; say that its excuse did nothing.
        extra.extend(
            f"excused gate {o.gate.id} passed; it excuses nothing "
            f"(reason given: {gate_excuses[o.gate.id]})"
            for o in evaluated
            if o.status == "pass" and o.gate.id in gate_excuses
        )
    elif strict:
        extra.append("--strict has no effect without --gates")
    if extra:
        comparison = replace(comparison, warnings=(*extra, *comparison.warnings))

    if as_json:
        click.echo(_stdjson.dumps(comparison_json(comparison, outcomes, status), indent=2))
    else:
        click.echo(render_text(comparison, outcomes, status))
    if status == "fail" or (strict and status == "pass_with_gaps"):
        raise SystemExit(1)


@main.group("eval")
def eval_group() -> None:
    """Evaluate runs against hand-reviewed labels (docs/measuring-changes.md)."""


_LABELS_HEADER = (
    "# Findings labels for corpus entry {entry}. Set each verdict to true_positive or\n"
    "# false_positive, correct apd_goal or severity where the run got them wrong, and\n"
    "# add true positives the run missed. Evaluators refuse unreviewed items.\n"
)


def _cannot_write(out_file: Path, exc: OSError) -> NoReturn:
    click.echo(f"Error: {out_file}: cannot write: {exc.strerror or exc}", err=True)
    raise SystemExit(1)


@eval_group.command("label-template")
@click.argument("run_dir", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option(
    "--entry",
    "entry_id",
    required=True,
    metavar="ID",
    help="The corpus entry id the labels are for.",
)
@click.option(
    "--out",
    "out_file",
    required=True,
    type=click.Path(path_type=Path),
    help="The labels file to write; an existing file is never overwritten.",
)
def eval_label_template_cmd(run_dir: Path, entry_id: str, out_file: Path) -> None:
    """Write a findings labels file for RUN_DIR: one unreviewed item per finding.

    Each item copies the finding's id, goal, severity, title and evidence
    pointers. Review every verdict before 'eval run' scores the run. Exits 0
    when written, 1 when the file exists (it is never overwritten) or cannot be
    written, and 2 when ID is not a corpus entry id, RUN_DIR is not a run or
    fails to load, or a finding cannot become a valid labels item.
    """
    from .eval.findings_eval import label_template

    try:
        doc = label_template(run_dir, entry_id)
    except ValueError as exc:
        _refuse(str(exc))
    text = _LABELS_HEADER.format(entry=entry_id) + yaml.safe_dump(
        doc, sort_keys=False, allow_unicode=True, width=1000
    )
    try:
        out_file.parent.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        _cannot_write(out_file, exc)
    try:
        handle = out_file.open("x", encoding="utf-8")  # exclusive: never through a link
    except FileExistsError:
        click.echo(f"Error: {out_file} exists; not overwritten", err=True)
        raise SystemExit(1) from None
    except OSError as exc:
        _cannot_write(out_file, exc)
    try:
        with handle:
            handle.write(text)
    except OSError as exc:
        out_file.unlink(missing_ok=True)
        _cannot_write(out_file, exc)
    click.echo(f"wrote {out_file}: {len(doc['items'])} items to review (verdict unreviewed)")


@eval_group.command("freeze")
@click.option(
    "--root",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=Path("."),
    show_default=True,
    help="The repository whose tunables are frozen.",
)
@click.option(
    "--new-heldout-set",
    is_flag=True,
    help=(
        "Re-freeze after a held-out run used the frozen tunables. Give it only once "
        "you have a new held-out set; the generation goes up by one."
    ),
)
def eval_freeze_cmd(root: Path, new_heldout_set: bool) -> None:
    """Freeze the tunables: record their SHA-256 in ROOT/eval/frozen.yaml.

    The tunables are the decision thresholds and every context-params.yaml under
    tools/apd_gauntlet/data/. Tune them on the dev set, freeze, then run the
    held-out set: 'eval run --set heldout' refuses when a tunables file changed
    after the freeze. Exits 0 when the file is written or unchanged, and 1 when
    the tunables changed after a held-out run used them (pass --new-heldout-set
    once you have a new held-out set, ADR-0028), a held-out result or the
    frozen file cannot be read, or the file cannot be written.
    """
    from .eval.freeze import FreezeError, freeze, read_frozen

    try:
        before = read_frozen(root)
        path = freeze(root, new_heldout_set=new_heldout_set)
        after = read_frozen(root)
    except FreezeError as exc:
        click.echo(f"Error: {exc}", err=True)
        raise SystemExit(1) from None
    if after is None:  # freeze always leaves the file in place
        raise click.ClickException(f"{path} missing after freeze")
    state = f"generation {after.generation}, tunables {after.tunables_sha256[:8]}, " + (
        f"{len(after.files)} files"
    )
    if after == before:
        click.echo(f"{path} unchanged: {state}")
        return
    click.echo(f"wrote {path}: {state}")
    for name in after.files:
        click.echo(f"  {name}")


def _same_directory(a: Path, b: Path) -> bool:
    try:
        return a.resolve() == b.resolve()
    except (OSError, RuntimeError):  # RuntimeError: a link loop before 3.13
        return a.absolute() == b.absolute()


@eval_group.command("run")
@click.argument("corpus", type=click.Path(path_type=Path))
@click.option(
    "--set",
    "set_name",
    required=True,
    type=click.Choice(["dev", "heldout"]),
    help="The set of CORPUS to score; heldout needs 'eval freeze' first.",
)
@click.option(
    "--evaluator",
    required=True,
    metavar="NAME",
    help="A registered evaluator, for example findings.",
)
@click.option(
    "--root",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=Path("."),
    show_default=True,
    help="The repository whose eval/frozen.yaml and tunables are checked.",
)
@click.option(
    "--results-dir",
    type=click.Path(file_okay=False, path_type=Path),
    default=None,
    help="Where the results go.  [default: ROOT/eval/results]",
)
@click.option(
    "--json",
    "as_json",
    is_flag=True,
    help="Print the results, the file's path and any warnings as JSON.",
)
def eval_run_cmd(
    corpus: Path,
    set_name: Literal["dev", "heldout"],
    evaluator: str,
    root: Path,
    results_dir: Path | None,
    as_json: bool,
) -> None:
    """Score the dev or heldout entries of CORPUS with a registered evaluator.

    Writes RESULTS_DIR/<evaluator>/<set>-<UTC time>.yaml: each entry's counts,
    metrics and notes, and the totals over the set. --set heldout needs the
    tunables frozen with 'eval freeze' and unchanged since; its results record
    the frozen hash, so re-freezing changed tunables then needs
    --new-heldout-set. A dev run records the frozen hash when the tunables
    match the freeze, and null otherwise. Exits 0 when written, 1 when the
    results file exists (it is never overwritten) or cannot be written, and 2
    when CORPUS or a labels file is invalid, the tunables are not frozen or
    changed since the freeze (heldout), the evaluator is unknown or refuses an
    entry, or the set has no entries.
    """
    from .eval.corpus import CorpusError
    from .eval.evaluators import get, load_builtin_evaluators
    from .eval.freeze import RESULTS_RELPATH, FreezeError
    from .eval.runner import ResultsWriteError, run_eval

    load_builtin_evaluators()
    try:
        get(evaluator)
    except KeyError as exc:
        _refuse(str(exc.args[0]))
    default_results = root / RESULTS_RELPATH
    target = results_dir if results_dir is not None else default_results
    warnings: list[str] = []
    if set_name == "heldout" and not _same_directory(target, default_results):
        warnings.append(
            f"held-out results outside {default_results} are not seen by 'eval freeze', so a "
            "re-freeze of changed tunables will not know this run used them"
        )
    try:
        path = run_eval(corpus, set_name, evaluator, root=root, results_dir=target)
    except (CorpusError, FreezeError, ValueError) as exc:
        _refuse(str(exc))
    except ResultsWriteError as exc:
        click.echo(f"Error: {exc}", err=True)
        raise SystemExit(1) from None
    doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    if as_json:
        click.echo(_stdjson.dumps(
            {"path": str(path), "result": doc, "warnings": warnings}, indent=2
        ))
        return
    n = len(doc["entries"])
    frozen = doc["frozen_sha256"]
    click.echo(
        f"wrote {path}: {evaluator} on {n} {set_name} {'entry' if n == 1 else 'entries'} "
        f"of corpus {doc['corpus']['name']}, "
        + (f"frozen {frozen[:8]}" if frozen else "not frozen")
    )
    if doc["totals"]["metrics"]:
        click.echo("totals:")
        for key, value in doc["totals"]["metrics"].items():
            click.echo(f"  {key}: " + ("n/a" if value is None else f"{value:.4f}"))
    for entry in doc["entries"]:
        for note in entry["notes"]:
            click.echo(f"note ({entry['id']}): {note}")
    for warning in warnings:
        click.echo(f"warning: {warning}", err=True)


_HELDOUT_LABELS = "calibrate on dev labels only; thresholds freeze before held-out runs"
_FREEZE_REMINDER = "re-run 'apd-gauntlet eval freeze' before any held-out run"


def _not_nan(ctx: click.Context, param: click.Parameter, value: float) -> float:
    """Refuse NaN, which passes ``click.FloatRange`` because it fails both bound checks."""
    if math.isnan(value):
        raise click.BadParameter(f"{value} is not in the range 0<x<=1.")
    return value


@main.command("calibrate")
@click.argument("task")
@click.option(
    "--labels",
    "labels_file",
    required=True,
    type=click.Path(path_type=Path),
    metavar="FILE",
    help="Dev labels of kind decisions for TASK (eval-labels.schema.json).",
)
@click.option(
    "--target-precision",
    required=True,
    type=click.FloatRange(0, 1, min_open=True),
    callback=_not_nan,
    metavar="P",
    help="The precision the threshold must reach on the labels, for example 0.98.",
)
@click.option(
    "--min-support",
    type=click.IntRange(min=1),
    default=10,
    show_default=True,
    metavar="N",
    help="The fewest predicted positives a threshold may rest on.",
)
@click.option(
    "--thresholds",
    "thresholds_file",
    type=click.Path(dir_okay=False, path_type=Path),
    default=None,
    metavar="PATH",
    help="The thresholds file to update.  [default: the packaged data/decide/thresholds.yaml]",
)
def calibrate_cmd(
    task: str,
    labels_file: Path,
    target_precision: float,
    min_support: int,
    thresholds_file: Path | None,
) -> None:
    """Calibrate the decision threshold TASK (<task> or <task>.<flag>) on dev labels.

    Reads the decision records the labels name, takes the threshold with the
    highest recall whose precision on the labelled items is at least P with at
    least N predicted positives, and writes it to the thresholds file with the
    labels' SHA-256 and the records' provider, model and weights revision
    (calibrated: true). A changed threshold is a changed tunable, so run
    'apd-gauntlet eval freeze' before any held-out run. Exits 0 when written, 1
    when no threshold qualifies or the file cannot be written (it is left as it
    was), and 2 when TASK has no value spec, the labels are invalid, of another
    kind or task, or held-out, or the records cannot be used (an unknown ref, a
    record of another task, records that mix models, no gold positive).
    """
    from .eval import calibrate as cal
    from .eval.corpus import CorpusError, load_labels

    spec = cal.VALUE_SPECS.get(task)
    if spec is None:
        _refuse(cal.unknown_key_message(task))
    try:
        labels = load_labels(labels_file)
    except CorpusError as exc:
        _refuse(str(exc))
    if labels.kind != "decisions":
        _refuse(f"{labels_file}: labels of kind {labels.kind}; calibrate needs kind decisions")
    if labels.data["task"] != task:
        _refuse(f"{labels_file}: labels for {labels.data['task']}, not {task}")
    if labels.data["set"] == "heldout":
        _refuse(f"{labels_file}: set: heldout; {_HELDOUT_LABELS}")
    try:
        provider, model, weights_revision = cal.record_model(labels)
        pairs, skipped = cal.labelled_pairs(labels, task)
        result = cal.choose_threshold(
            pairs, direction=spec.direction, target_precision=target_precision,
            min_support=min_support,
        )
    except cal.CalibrationError as exc:
        _refuse(str(exc))
    if skipped:
        click.echo(
            f"skipped {skipped} labelled item{'' if skipped == 1 else 's'}"
            " (outcome error or no value)"
        )
    if not result.feasible:
        best = "none" if result.best_precision is None else f"{result.best_precision:.4f}"
        click.echo(
            f"no threshold reaches precision ≥ {target_precision!r} with at least "
            f"{min_support} predicted positives (best: {best}); {task} stays uncalibrated"
        )
        raise SystemExit(1)
    path = thresholds_file if thresholds_file is not None else cal.THRESHOLDS_PATH
    try:
        cal.write_threshold(
            path, task, result, labels.sha256,
            provider=provider, model=model, weights_revision=weights_revision,
        )
    except cal.CalibrationError as exc:
        _refuse(str(exc))
    except OSError as exc:
        _cannot_write(path, exc)
    entry = cal.threshold_entry(
        result, labels.sha256, provider=provider, model=model, weights_revision=weights_revision
    )
    click.echo(f"wrote {path}: {task}, selecting values {spec.direction} the threshold")
    for line in yaml.safe_dump(entry, sort_keys=True).splitlines():
        click.echo(f"  {line}")
    click.echo(_FREEZE_REMINDER)


@main.group("metamorphic")
def metamorphic_group() -> None:
    """Check that behaviour-preserving changes to inputs leave results unchanged."""


@metamorphic_group.command("run")
@click.option(
    "--suite",
    "suite_name",
    required=True,
    metavar="NAME",
    help="A registered suite, for example stride-table.",
)
@click.option(
    "--root",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=Path("."),
    show_default=True,
    help="The directory the suite's fixtures are relative to.",
)
@click.option(
    "--json",
    "as_json",
    is_flag=True,
    help="Print the suite name and every case as JSON.",
)
def metamorphic_run_cmd(suite_name: str, root: Path, as_json: bool) -> None:
    """Apply each transformation of the suite NAME to each of its fixtures and compare.

    A transformation writes a changed copy of a fixture (renamed elements,
    reordered rows) that must give the same results, once renamed names are
    mapped back. Each case holds, is violated, is allowlisted (the suite lists
    it as a known non-invariance, with a reason) or is a stale allowlist entry
    (listed, but it holds). The copies go to a temporary directory that is
    removed afterwards. Exits 0 when every case holds or is allowlisted, 1 when
    a case is violated or an allowlist entry is stale, and 2 when NAME is not a
    registered suite or a fixture is missing under ROOT, or the suite cannot
    run (for example, a tool it needs is missing).
    """
    import dataclasses
    import tempfile

    from .eval.metamorphic import (
        FAILING,
        MetamorphicError,
        get_suite,
        load_builtin_suites,
        render_text,
        run_suite,
    )

    load_builtin_suites()
    try:
        suite = get_suite(suite_name)
    except KeyError as exc:
        _refuse(str(exc.args[0]))
    with tempfile.TemporaryDirectory(prefix="apd-metamorphic-") as workdir:
        try:
            cases = run_suite(suite, root, Path(workdir))
        except MetamorphicError as exc:
            _refuse(str(exc))
    if as_json:
        click.echo(_stdjson.dumps(
            {"suite": suite.name, "cases": [dataclasses.asdict(c) for c in cases]}, indent=2
        ))
    else:
        click.echo(render_text(suite, cases))
    if any(c.status in FAILING for c in cases):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
