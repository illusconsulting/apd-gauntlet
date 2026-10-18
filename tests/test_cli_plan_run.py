"""Tests for the plan-run command.

plan-run emits the EXACT ordered phase->step list the
.claude/workflows/apd-gauntlet.js runner executes, honoring the run-config
gates, so operators can drive the gauntlet FOREGROUND in-session without the
background Workflow primitive (which can interrupt subagent dispatches and wipe
a run).
"""
from __future__ import annotations

import json
import pathlib
import re

import yaml
from apd_gauntlet.cli import main
from click.testing import CliRunner

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
WORKFLOW_JS = REPO_ROOT / ".claude" / "workflows" / "apd-gauntlet.js"

# Minimal, schema-valid run-config the synthesized-fixture tests start from.
BASE_CFG = {
    "run_id": "apd-test",
    "domains": ["agentic-ai"],
    "framework_version": "1.6.0",
}

# A fully-featured config exercising every gate (code_recon enabled, crown_jewels
# present, threat_model absent), synthesized into a tmp run dir so the tests do NOT
# depend on any gitignored runs/ directory (those are absent in CI). plan-run only
# reads the run dir's .apd-run.yaml, so a config-only scaffold is sufficient.
FULL_CFG = {
    "run_id": "apd-test-full",
    "domains": ["agentic-ai", "api-security"],
    "framework_version": "1.6.0",
    "code_recon": "enabled",
    "crown_jewels": ["tool_execution_capability", "pii_profile_store"],
}


def _write_run(tmp_path, cfg):
    """Scaffold a minimal run dir with a .apd-run.yaml and return its path."""
    run_dir = tmp_path / cfg["run_id"]
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / ".apd-run.yaml").write_text(yaml.safe_dump(cfg), encoding="utf-8")
    return run_dir


def test_plan_run_real_run_markdown(tmp_path):
    """A fully-featured run: code_recon enabled, crown_jewels present,
    threat_model absent."""
    run_dir = _write_run(tmp_path, FULL_CFG)
    runner = CliRunner()
    result = runner.invoke(main, ["plan-run", str(run_dir)])
    assert result.exit_code == 0, result.output
    out = result.output
    # header names the run + the foreground-drive intent
    assert "apd-test-full" in out
    assert "agentic-ai" in out and "api-security" in out
    assert "foreground drive order" in out
    # required steps present
    for needle in (
        "apd-intake",
        "apd-code-recon",
        "apd-attack-path-analyzer",
        "apd-threat-model-evaluator",
        "build-report",
        "audit-report",
    ):
        assert needle in out, f"missing step: {needle}"
    # threat_model absent -> recon ABSENT
    assert "apd-threat-model-recon" not in out
    # ordering (by string index): intake < tier-1 lenses < cluster < report
    i_intake = out.index("apd-intake")
    i_lens = out.index("apd-confidentiality")
    i_cluster = out.index("cluster-candidates")
    i_report = out.index("apd-report-writer")
    assert i_intake < i_lens < i_cluster < i_report


def test_plan_run_json(tmp_path):
    run_dir = _write_run(tmp_path, FULL_CFG)
    runner = CliRunner()
    result = runner.invoke(main, ["plan-run", "--json", str(run_dir)])
    assert result.exit_code == 0, result.output
    plan = json.loads(result.output)
    assert isinstance(plan, list)
    assert plan, "plan must be non-empty"
    for step in plan:
        assert isinstance(step, dict)
        assert set(step.keys()) == {"phase", "kind", "ref", "outputs", "gate"}
        assert step["kind"] in ("CLI", "AGENT")
    refs = [s["ref"] for s in plan]
    assert "apd-intake" in refs
    assert "apd-attack-path-analyzer" in refs
    assert "apd-threat-model-evaluator" in refs


def test_plan_run_code_recon_disabled_omits_code_recon(tmp_path):
    cfg = dict(BASE_CFG, code_recon="disabled")
    run_dir = _write_run(tmp_path, cfg)
    runner = CliRunner()
    result = runner.invoke(main, ["plan-run", str(run_dir)])
    assert result.exit_code == 0, result.output
    assert "apd-code-recon" not in result.output


def test_plan_run_no_crown_jewels_omits_apath(tmp_path):
    cfg = dict(BASE_CFG)  # no crown_jewels key
    run_dir = _write_run(tmp_path, cfg)
    runner = CliRunner()
    result = runner.invoke(main, ["plan-run", str(run_dir)])
    assert result.exit_code == 0, result.output
    out = result.output
    # apath step omitted...
    assert "apd-attack-path-analyzer" not in out
    # ...but annotated so the operator knows when it would run
    assert "crown" in out.lower()
    # tmeval ALWAYS present
    assert "apd-threat-model-evaluator" in out


def test_plan_run_empty_crown_jewels_omits_apath(tmp_path):
    cfg = dict(BASE_CFG, crown_jewels=[])
    run_dir = _write_run(tmp_path, cfg)
    runner = CliRunner()
    result = runner.invoke(main, ["plan-run", str(run_dir)])
    assert result.exit_code == 0, result.output
    assert "apd-attack-path-analyzer" not in result.output


def test_plan_run_threat_model_present_includes_recon(tmp_path):
    cfg = dict(BASE_CFG, threat_model="inputs/tm.md")
    run_dir = _write_run(tmp_path, cfg)
    runner = CliRunner()
    result = runner.invoke(main, ["plan-run", str(run_dir)])
    assert result.exit_code == 0, result.output
    assert "apd-threat-model-recon" in result.output


def test_plan_run_invalid_config_exits_1(tmp_path):
    # framework_version pattern violation (not X.Y.Z) -> schema error
    cfg = dict(BASE_CFG, framework_version="not-a-version")
    run_dir = _write_run(tmp_path, cfg)
    runner = CliRunner()
    result = runner.invoke(main, ["plan-run", str(run_dir)])
    assert result.exit_code == 1
    assert "Schema error" in result.output


def test_plan_run_phase_names_consistent_with_workflow(tmp_path):
    """CONSISTENCY: the emitted phase-name set must not silently drift from the
    runner's meta.phases. Parse meta.phases out of the workflow JS and assert the
    plan's phase names are a subset (modulo dynamic tier phase aliasing)."""
    js = WORKFLOW_JS.read_text(encoding="utf-8")
    m = re.search(r"phases:\s*\[(.*?)\]", js, re.DOTALL)
    assert m, "could not locate meta.phases in the workflow JS"
    workflow_phases = set(re.findall(r"'([^']+)'", m.group(1)))

    run_dir = _write_run(tmp_path, FULL_CFG)
    runner = CliRunner()
    result = runner.invoke(main, ["plan-run", "--json", str(run_dir)])
    assert result.exit_code == 0, result.output
    plan = json.loads(result.output)
    plan_phases = {s["phase"] for s in plan}

    # plan-run expands the runner's three abstract tier phases (tier-1/2/3) into
    # the concrete tier-dir phase names the runner ACTUALLY validates against.
    tier_aliases = {"10-trustworthiness", "20-scalability", "30-auditability"}
    # everything else in the plan must be a real runner phase.
    leftover = plan_phases - workflow_phases - tier_aliases
    assert not leftover, f"plan emitted phases not in the runner: {leftover}"

    workflow_cmds = set(re.findall(r"pyStep\('([a-z][a-z0-9-]+)'", js))
    plan_cmds = {s["ref"].split()[0] for s in plan if s["kind"] == "CLI"}
    assert plan_cmds <= workflow_cmds, (
        f"plan-run CLI steps the runner never runs: {plan_cmds - workflow_cmds}"
    )
    assert "resume-plan" in plan_cmds & workflow_cmds
    # Both run the same commands: every command the runner runs has a plan-run row.
    assert {s["ref"].split()[0] for s in plan if s["kind"] == "CLI"} == workflow_cmds


def test_plan_run_code_recon_step_mentions_cross_repo(tmp_path):
    """The code-recon step outputs string names the multi-repo cross-repo pass
    so an operator driving foreground knows it can span repos[]."""
    run_dir = _write_run(tmp_path, FULL_CFG)
    runner = CliRunner()
    result = runner.invoke(main, ["plan-run", "--json", str(run_dir)])
    assert result.exit_code == 0, result.output
    plan = json.loads(result.output)
    recon = [s for s in plan if s["ref"] == "apd-code-recon"]
    assert recon, "code-recon step must be present"
    assert "cross-repo" in recon[0]["outputs"], recon[0]["outputs"]


def test_plan_run_starts_with_resume_plan(tmp_path):
    plan = json.loads(
        CliRunner().invoke(main, ["plan-run", "--json", str(_write_run(tmp_path, FULL_CFG))]).output
    )
    assert plan[0]["ref"] == "resume-plan runs/apd-test-full --json"
    assert plan[0]["phase"] == "setup"


def test_plan_run_tier_gates_name_the_repair_path(tmp_path):
    plan = json.loads(
        CliRunner().invoke(main, ["plan-run", "--json", str(_write_run(tmp_path, FULL_CFG))]).output
    )
    gates = [s for s in plan if s["ref"].startswith("tier-gate ")]
    assert len(gates) == 3 and all("repair.md" in s["gate"] and "halt" in s["gate"] for s in gates)
    # The row text is the command the workflow runs (register A8.9), and the gate text
    # leads with it.
    assert [s["ref"] for s in gates] == [
        f"tier-gate runs/apd-test-full --tier {d} --json"
        for d in ("10-trustworthiness", "20-scalability", "30-auditability")]
    assert all(s["gate"].startswith(s["ref"] + "; on failure repair ") for s in gates)
    assert [s["phase"] for s in gates] == [
        "10-trustworthiness", "20-scalability", "30-auditability"]


def _plan(tmp_path, cfg):
    run_dir = _write_run(tmp_path, cfg)
    return json.loads(CliRunner().invoke(main, ["plan-run", "--json", str(run_dir)]).output)


def test_plan_run_mints_context_ids_before_tier_1(tmp_path):
    plan = _plan(tmp_path, FULL_CFG)
    canon = [i for i, s in enumerate(plan) if s["phase"] == "canonicalize"]
    first_lens = next(i for i, s in enumerate(plan) if s["ref"] == "apd-confidentiality")
    assert len(canon) == 2 and max(canon) < first_lens


def test_plan_run_without_code_recon_mints_tm_ids_only(tmp_path):
    plan = _plan(tmp_path, dict(BASE_CFG, code_recon="disabled"))
    assert sum(1 for s in plan if s["phase"] == "canonicalize") == 1


def test_plan_run_context_canonicalize_rows_follow_their_producers(tmp_path):
    plan = _plan(tmp_path, dict(FULL_CFG, threat_model="inputs/tm.md"))
    refs = [s["ref"] for s in plan]
    rows = [i for i, s in enumerate(plan) if s["phase"] == "canonicalize"]
    assert [plan[i]["ref"] for i in rows] == ["canonicalize runs/apd-test-full"] * 2
    assert refs.index("apd-code-recon") + 1 == rows[0]
    assert rows[0] < refs.index("author-threat-model runs/apd-test-full")
    assert refs.index("apd-threat-model-recon") + 1 == rows[1]
    plan = _plan(tmp_path, FULL_CFG)  # no supplied TM: the row follows the author
    refs = [s["ref"] for s in plan]
    last = max(i for i, s in enumerate(plan) if s["phase"] == "canonicalize")
    assert refs.index("apd-threat-model-author") + 1 == last


def test_plan_run_cli_rows_use_composites(tmp_path):
    cli = [s["ref"] for s in _plan(tmp_path, FULL_CFG) if s["kind"] == "CLI"]
    assert [r.split()[0] for r in cli] == [
        "resume-plan", "prepare-run", "assemble-inventory", "validate",
        "canonicalize", "author-threat-model", "canonicalize", "tier-gate", "tier-gate",
        "tier-gate", "validate", "cluster-candidates", "apply-clusters", "post-tier4",
        "build-report", "audit-report", "domain-coverage-delta", "closeout"]
    assert cli[1] == "prepare-run runs/apd-test-full --domain agentic-ai --domain api-security"


# --- beyond the plan's Task 3 tests --------------------------------------------------------


def test_plan_run_composite_rows(tmp_path):
    plan = _plan(tmp_path, FULL_CFG)
    rows = {s["ref"].split()[0]: s for s in plan if s["kind"] == "CLI"}
    assert rows["prepare-run"]["phase"] == "setup"
    assert rows["assemble-inventory"] == {
        "phase": "intake", "kind": "CLI", "ref": "assemble-inventory runs/apd-test-full",
        "outputs": "00-context/asset-inventory.yaml (asset-/idn-/tb- ids minted; crosses wired)",
        "gate": ""}
    refs = [s["ref"] for s in plan]
    assert refs.index("apd-intake") + 1 == refs.index("assemble-inventory runs/apd-test-full")
    assert rows["post-tier4"]["ref"] == "post-tier4 runs/apd-test-full"
    assert rows["post-tier4"]["phase"] == "synthesis-rollup"
    assert "c4-model.yaml" in rows["post-tier4"]["outputs"]
    assert "metrics.yaml" in rows["post-tier4"]["outputs"]
    assert rows["closeout"]["ref"] == "closeout runs/apd-test-full"
    assert rows["closeout"]["phase"] == "closeout"
    assert plan[-1] is rows["closeout"]
    for gone in ("build-domain-skill", "validate-domain", "rollup", "summarize"):
        assert gone not in rows, gone
