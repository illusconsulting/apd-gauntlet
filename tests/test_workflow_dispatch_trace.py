"""What the workflow runner dispatches, measured by running it under node.

tests/js/workflow_dispatch_trace.mjs runs the real .claude/workflows/apd-gauntlet.js
against stub Workflow globals and prints every dispatch as
{agentType, label, phase, guard, command}. The tests here count and order those
dispatches. They are skipped where node is absent, like test_c4_solve_routes_node_oracle;
the CI test job provisions Node 22 so they run there.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

import pytest
import yaml
from apd_gauntlet.composite import post_tier4_steps
from apd_gauntlet.plan_run import build_plan

REPO = Path(__file__).resolve().parent.parent
RUNNER = REPO / ".claude" / "workflows" / "apd-gauntlet.js"
HARNESS = REPO / "tests" / "js" / "workflow_dispatch_trace.mjs"
CI = REPO / ".github" / "workflows" / "python-tests.yml"

# An HA-shaped run config: code recon on, a crown jewel declared, no threat model.
HA_SHAPED: dict[str, Any] = {
    "run_id": "r", "domains": ["pbm"], "code_recon": "enabled", "crown_jewels": ["phi_store"],
}

# Every CLI dispatch of a clean HA-shaped run, in order. WS3 Task 3 runs the composites
# prepare-run, tier-gate, post-tier4 and closeout: 9 fewer than the 27 of the WS1 + WS2 base.
# WS3 Task 7 makes Phase 5h opt-in, and HA_SHAPED does not set domain_improvement_capture,
# so domain-coverage-delta is not dispatched.
CLI_LABELS = [
    # setup and intake
    "resume-plan", "prepare-run", "assemble-inventory", "intake-schema-gate",
    # context
    "canonicalize-code-evidence", "author-threat-model-floor", "canonicalize-threat-model",
    # tiers
    "tier-gate-10-trustworthiness", "tier-gate-20-scalability", "tier-gate-30-auditability",
    "validate-full-prephase5",
    # synthesis
    "cluster-candidates", "apply-clusters", "post-tier4",
    "build-report-attempt-0", "audit-report-attempt-0",
    # closeout
    "closeout",
]
# The composite dispatches, and the CLI dispatches that still carry the guard text.
COMPOSITES = {"prepare-run", "tier-gate-10-trustworthiness", "tier-gate-20-scalability",
              "tier-gate-30-auditability", "post-tier4", "closeout"}
GUARDED = {"author-threat-model-floor", "cluster-candidates", "apply-clusters",
           "build-report-attempt-0", "audit-report-attempt-0"}


def trace_raw(
    cfg: dict[str, Any], fail: dict[str, list[str]] | None = None, *, logs: bool = False
) -> subprocess.CompletedProcess[str]:
    """Run the harness on the runner with `cfg` as args; `fail` maps a label to the
    names of its failing steps (an empty list fails the label itself). With `logs`, the
    harness also prints the workflow's log() lines on stderr."""
    node = shutil.which("node")
    if node is None:
        pytest.skip("node not available")
    argv = [node, str(HARNESS), str(RUNNER), json.dumps(cfg)]
    if fail is not None:
        argv.append(json.dumps(fail))
    env = {k: v for k, v in os.environ.items() if k != "TRACE_LOGS"}
    if logs:
        env["TRACE_LOGS"] = "1"
    return subprocess.run(argv, capture_output=True, text=True, timeout=60, cwd=REPO, env=env)


def run_logs(cfg: dict[str, Any], fail: dict[str, list[str]] | None = None) -> list[str]:
    """The messages the workflow passed to log(), in order."""
    r = trace_raw(cfg, fail, logs=True)
    assert r.returncode == 0, r.stderr
    return [line[len("log: "):] for line in r.stderr.splitlines() if line.startswith("log: ")]


def trace(cfg: dict[str, Any], fail: dict[str, list[str]] | None = None) -> list[dict[str, Any]]:
    r = trace_raw(cfg, fail)
    assert r.returncode == 0, r.stderr
    dispatches: list[dict[str, Any]] = json.loads(r.stdout)
    return dispatches


def cli(t: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [d for d in t if d["agentType"] == "apd-cli-runner"]


def llm(t: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [d for d in t if d["agentType"] != "apd-cli-runner"]


def test_every_clean_run_dispatch_names_an_agent():
    assert all(d["agentType"] for d in trace(HA_SHAPED))


def test_cli_steps_go_to_cli_runner():
    steps = cli(trace(HA_SHAPED))
    assert [d["label"] for d in steps] == CLI_LABELS
    assert all(d["command"].startswith("apd-gauntlet ") for d in steps)


def test_llm_dispatch_count_unchanged():
    assert len(llm(trace(HA_SHAPED))) == 17


@pytest.mark.parametrize("patch", [{"run_id": "r; touch x"}, {"domains": ["pbm", "$(id)"]},
                                   {"framework_version": "1.7.0 && id"}])
def test_trace_rejects_shell_metacharacters(patch):
    r = trace_raw({**HA_SHAPED, **patch})
    assert r.returncode == 3 and "run-config.schema.json" in r.stderr


# --- WS3 Task 3: the workflow runs the composite commands ------------------------------


def _labels(fail: dict[str, list[str]] | None = None) -> list[str]:
    return [d["label"] for d in trace(HA_SHAPED, fail)]


def test_guard_text_only_on_mutating_cli_steps():
    t = cli(trace(HA_SHAPED))
    assert {d["label"] for d in t if d["guard"]} == GUARDED and not COMPOSITES & GUARDED


def test_composite_commands_and_phase():
    t = {d["label"]: d for d in trace(HA_SHAPED)}
    assert t["prepare-run"]["command"] == "apd-gauntlet prepare-run runs/r --domain pbm"
    assert t["tier-gate-20-scalability"]["command"] == (
        "apd-gauntlet tier-gate runs/r --tier 20-scalability --json")
    assert t["tier-gate-20-scalability"]["phase"] == "tier-2"
    assert t["post-tier4"]["command"] == "apd-gauntlet post-tier4 runs/r"
    assert t["closeout"]["command"].startswith("apd-gauntlet closeout runs/r --record-attempts '")


def test_rollup_fallback_keys_on_rollup_step():
    only_c4 = _labels({"post-tier4": ["assemble-c4"]})
    assert "post-tier4-retry-1" not in only_c4 and "synthesizer-fallback-rollup" not in only_c4
    rollup = _labels({"post-tier4": ["rollup"], "post-tier4-retry-1": ["rollup"]})
    i = rollup.index("post-tier4")
    assert rollup[i:i + 3] == ["post-tier4", "post-tier4-retry-1", "synthesizer-fallback-rollup"]
    assert "synthesizer-fallback-rollup" in _labels({"post-tier4": [], "post-tier4-retry-1": []})


# WS1's failingFiles needs a record-file path.
BAD = "runs/r/10-trustworthiness/integrity.findings.yaml"


def test_repair_loop_regates_through_tier_gate():
    labels = _labels({"tier-gate-10-trustworthiness": [BAD]})
    assert labels.index("tier-gate-10-trustworthiness") < labels.index(
        "tier-gate-10-trustworthiness-after-repair")
    assert not any(label.startswith("canonicalize-10-trustworthiness") for label in labels)


def test_plan_run_matches_workflow_dispatch_sequence():
    cfg = {"run_id": "apd-test-full", "domains": ["agentic-ai", "api-security"],
           "code_recon": "enabled", "crown_jewels": ["a"]}
    wf = [("CLI", d["command"].split()[1]) if d["agentType"] == "apd-cli-runner"
          else ("AGENT", d["agentType"]) for d in trace(cfg)]
    assert [(s["kind"], s["ref"].split()[0]) for s in build_plan(cfg)] == wf


# --- beyond the plan's Task 3 tests ----------------------------------------------------


def test_dispatch_totals_after_the_composites():
    # The plan's "After Task 7, default" column: 17 CLI and 17 LLM dispatches on a clean
    # run ("After Task 3" was 18 and 18; Phase 5h is now opt-in).
    t = trace(HA_SHAPED)
    assert (len(cli(t)), len(llm(t)), len(t)) == (17, 17, 34)


def test_composites_always_run():
    by_label = {d["label"]: d for d in cli(trace(HA_SHAPED))}
    assert all(by_label[label]["guard"] is False for label in COMPOSITES)


def test_post_tier4_steps_constant_matches_the_composite():
    # stepFailed() reads a receipt error's path as a post-tier4 constituent name.
    m = re.search(r"const POST_TIER4_STEPS = \[([^\]]*)\];", RUNNER.read_text(encoding="utf-8"))
    assert m, "POST_TIER4_STEPS not found"
    names = re.findall(r"'([^']+)'", m.group(1))
    assert names == [s.name for s in post_tier4_steps(Path("runs/r"))] == [
        "assemble-c4", "canonicalize", "rollup"]


def test_rollup_failure_retry_carries_the_same_command():
    t = trace(HA_SHAPED, {"post-tier4": ["rollup"]})
    by_label = {d["label"]: d for d in t}
    assert by_label["post-tier4-retry-1"]["command"] == "apd-gauntlet post-tier4 runs/r"
    assert by_label["post-tier4-retry-1"]["phase"] == "synthesis-rollup"
    # The retry always runs, like the composite it repeats: a guard could skip it on
    # coverage files a previous run left behind, and the synthesizer would never fire.
    assert by_label["post-tier4-retry-1"]["guard"] is False
    assert "synthesizer-fallback-rollup" not in by_label  # the retry succeeded


ADVISORY = " failed — advisory; the run continues."


def _post_tier4_logs(fail: dict[str, list[str]]) -> list[str]:
    return [m for m in run_logs(HA_SHAPED, fail) if m.startswith("post-tier4: ")]


@pytest.mark.parametrize(("fail", "steps"), [
    ({"post-tier4": ["assemble-c4"]}, "assemble-c4"),
    ({"post-tier4": ["canonicalize", "assemble-c4"]}, "assemble-c4, canonicalize"),
    # The retry fixed rollup, but canonicalize still failed on it.
    ({"post-tier4": ["rollup"], "post-tier4-retry-1": ["canonicalize"]}, "canonicalize"),
    # Rollup failed twice, and assemble-c4 with it: the synthesizer runs, and the
    # advisory failure is still named.
    ({"post-tier4": ["rollup"], "post-tier4-retry-1": ["rollup", "assemble-c4"]}, "assemble-c4"),
])
def test_advisory_post_tier4_failures_are_logged(fail, steps):
    assert _post_tier4_logs(fail) == ["post-tier4: " + steps + ADVISORY]


@pytest.mark.parametrize("fail", [
    {},
    {"post-tier4": ["rollup"]},
    {"post-tier4": ["rollup", "assemble-c4"]},  # the retry passed every step
    {"post-tier4": [], "post-tier4-retry-1": []},  # failed receipts that name no step
    {"post-tier4": ["rollup"], "post-tier4-retry-1": ["rollup"]},
])
def test_no_advisory_log_without_a_named_advisory_failure(fail):
    assert _post_tier4_logs(fail) == []


def test_runner_logs_name_no_workstream():
    # Operators read these lines; a plan's workstream name means nothing to them.
    for fail in ({}, {"post-tier4": ["assemble-c4"]},
                 {"post-tier4": ["rollup"], "post-tier4-retry-1": ["rollup"]}):
        lines = run_logs(HA_SHAPED, fail)
        assert lines and not [m for m in lines if re.search(r"\bWS\d", m)], lines


def test_canonicalize_failure_alone_is_advisory():
    labels = _labels({"post-tier4": ["canonicalize"]})
    assert "post-tier4-retry-1" not in labels and "synthesizer-fallback-rollup" not in labels
    assert labels[labels.index("post-tier4") + 1] == "report-writer-attempt-0"


def test_rollup_named_among_several_failures_triggers_the_retry():
    labels = _labels({"post-tier4": ["assemble-c4", "rollup"]})
    assert labels[labels.index("post-tier4") + 1] == "post-tier4-retry-1"


def test_repair_regates_after_rerun_through_tier_gate():
    labels = _labels({"tier-gate-10-trustworthiness": [BAD],
                      "tier-gate-10-trustworthiness-after-repair": [BAD]})
    at = labels.index("tier-gate-10-trustworthiness")
    assert labels[at:at + 5] == [
        "tier-gate-10-trustworthiness", "repair-10-trustworthiness-integrity.findings.yaml",
        "tier-gate-10-trustworthiness-after-repair", "integrity-rerun",
        "tier-gate-10-trustworthiness-after-rerun"]
    by_label = {d["label"]: d for d in trace(HA_SHAPED, {"tier-gate-10-trustworthiness": [BAD]})}
    assert by_label["tier-gate-10-trustworthiness-after-repair"]["command"] == (
        "apd-gauntlet tier-gate runs/r --tier 10-trustworthiness --json")
    assert by_label["tier-gate-10-trustworthiness-after-repair"]["phase"] == "tier-1"


def test_prepare_run_reads_framework_version_from_the_run_config():
    # args is the run's .apd-run.yaml, which prepare-run reads itself: no CLI command
    # carries the flag, whether or not the key is set.
    for cfg in (HA_SHAPED, {**HA_SHAPED, "framework_version": "1.7.1"}):
        assert not any("--framework-version" in d["command"] for d in cli(trace(cfg)))


# --- beyond the plan's tests -------------------------------------------------------------


@pytest.mark.parametrize(("patch", "key"), [
    ({"run_id": "r; touch x"}, "args.run_id"),
    ({"run_id": "r/../../x"}, "args.run_id"),
    ({"run_id": "-r"}, "args.run_id"),
    ({"domains": ["pbm", "$(id)"]}, "args.domains[1]"),
    ({"domains": ["PBM"]}, "args.domains[0]"),
    ({"domains": ["pbm", 7]}, "args.domains[1]"),
    ({"framework_version": "1.7.0 && id"}, "args.framework_version"),
    ({"framework_version": "1.7"}, "args.framework_version"),
    ({"framework_version": ""}, "args.framework_version"),
])
def test_refusal_names_the_key_and_comes_before_any_dispatch(patch, key):
    r = trace_raw({**HA_SHAPED, **patch})
    assert r.returncode == 3, r.stderr
    assert r.stderr.startswith("apd-gauntlet: " + key + " "), r.stderr
    assert r.stderr.endswith(
        "does not match run-config.schema.json; refusing to build a shell command from it."
    ), r.stderr
    assert json.loads(r.stdout) == [], "the runner dispatched before refusing the run config"


def test_schema_valid_identifiers_are_accepted():
    cfg = {**HA_SHAPED, "run_id": "apd-20260601_claim.event-bus", "domains": ["pbm", "fhir-r4"],
           "framework_version": "1.7.1"}
    commands = {d["label"]: d["command"] for d in cli(trace(cfg))}
    assert commands["resume-plan"] == (
        "apd-gauntlet resume-plan runs/apd-20260601_claim.event-bus --json")
    assert commands["prepare-run"] == (
        "apd-gauntlet prepare-run runs/apd-20260601_claim.event-bus --domain pbm --domain fhir-r4")


def test_trace_records_phase_and_guard():
    by_label = {d["label"]: d for d in trace(HA_SHAPED)}
    assert by_label["tier-gate-10-trustworthiness"]["phase"] == "tier-1"
    assert by_label["tier-gate-10-trustworthiness"]["guard"] is False  # alwaysRun
    assert by_label["cluster-candidates"]["guard"] is True
    assert by_label["intake"] == {"agentType": "apd-intake", "label": "intake",
                                  "phase": "intake", "guard": False, "command": None}


def test_failure_branch_retries_also_go_to_cli_runner():
    t = trace(HA_SHAPED, {"cluster-candidates": []})
    labels = [d["label"] for d in t]
    at = labels.index("cluster-candidates")
    assert labels[at + 1] == "cluster-candidates-retry-1"
    retry = t[at + 1]
    assert retry["agentType"] == "apd-cli-runner"
    assert retry["command"] == "apd-gauntlet cluster-candidates runs/r"


def test_ci_test_job_provisions_node_22():
    # Register A9.20: without node on the runner these tests skip in CI.
    steps = yaml.safe_load(CI.read_text(encoding="utf-8"))["jobs"]["test"]["steps"]
    nodes = [i for i, s in enumerate(steps)
             if str(s.get("uses", "")).startswith("actions/setup-node@")]
    assert len(nodes) == 1, steps
    step = steps[nodes[0]]
    assert re.fullmatch(r"actions/setup-node@[0-9a-f]{40}", step["uses"]), step["uses"]
    assert str(step["with"]["node-version"]) == "22"
    pytest_at = next(i for i, s in enumerate(steps) if str(s.get("run", "")).startswith("pytest"))
    assert nodes[0] < pytest_at


# --- WS3 Task 4: the repair dispatch goes to apd-tier-repair ----------------------------


def test_repair_dispatches_tier_repair_agent():
    t = trace(HA_SHAPED, {"tier-gate-10-trustworthiness": [BAD]})
    repair = [d for d in t if d["label"].startswith("repair-10-trustworthiness-")]
    assert [d["agentType"] for d in repair] == ["apd-tier-repair"]


# --- WS3 Task 7: Phase 5h runs only when domain_improvement_capture is true -------------


def test_domain_capture_default_off_and_opt_in():
    off, on = trace(HA_SHAPED), trace({**HA_SHAPED, "domain_improvement_capture": True})
    assert not {"domain-coverage-delta", "domain-auditor"} & {d["label"] for d in off}
    assert {"domain-coverage-delta", "domain-auditor"} <= {d["label"] for d in on}
    assert (len(cli(off)), len(llm(off)), len(cli(on)), len(llm(on))) == (17, 17, 18, 18)
    assert trace_raw({**HA_SHAPED, "domain_improvement_capture": "true"}).returncode == 3


# --- beyond the plan's Task 7 tests ------------------------------------------------------

CAPTURE_REFUSAL_END = (
    "is not a boolean; write true or false, unquoted, in .apd-run.yaml, or leave the key "
    "out (run-config.schema.json).")


def test_explicit_false_is_the_default():
    assert trace({**HA_SHAPED, "domain_improvement_capture": False}) == trace(HA_SHAPED)


def test_opted_in_phase_5h_runs_between_the_audit_and_closeout():
    t = trace({**HA_SHAPED, "domain_improvement_capture": True})
    labels = [d["label"] for d in t]
    at = labels.index("domain-coverage-delta")
    assert labels[at - 1:at + 3] == [
        "auditor-attempt-0", "domain-coverage-delta", "domain-auditor", "closeout"]
    delta, auditor = t[at], t[at + 1]
    assert delta["agentType"] == "apd-cli-runner" and delta["guard"] is True
    assert delta["command"] == "apd-gauntlet domain-coverage-delta runs/r"
    assert delta["phase"] == "domain-coverage-delta"
    assert auditor["agentType"] == "apd-domain-auditor"
    assert auditor["phase"] == "domain-improvements"
    # Everything else is the default run's sequence.
    assert [x for x in labels if x not in {"domain-coverage-delta", "domain-auditor"}] == [
        d["label"] for d in trace(HA_SHAPED)]


def test_opted_in_cli_labels_and_guard_text():
    t = cli(trace({**HA_SHAPED, "domain_improvement_capture": True}))
    assert [d["label"] for d in t] == CLI_LABELS[:-1] + ["domain-coverage-delta", "closeout"]
    assert {d["label"] for d in t if d["guard"]} == GUARDED | {"domain-coverage-delta"}


@pytest.mark.parametrize("capture", [None, False])
def test_skipped_phase_5h_logs_both_skips(capture):
    cfg = HA_SHAPED if capture is None else {**HA_SHAPED, "domain_improvement_capture": capture}
    skips = [m for m in run_logs(cfg) if ": skipped (" in m]
    reason = " (domain_improvement_capture is not true in .apd-run.yaml)"
    assert skips == ["domain-coverage-delta: skipped" + reason,
                     "domain-improvements: skipped" + reason]


def test_opted_in_phase_5h_logs_no_skip():
    logs = run_logs({**HA_SHAPED, "domain_improvement_capture": True})
    assert not [m for m in logs if ": skipped (" in m], logs


def test_advisory_phase_5h_failures_do_not_halt_the_run():
    t = trace({**HA_SHAPED, "domain_improvement_capture": True},
              {"domain-coverage-delta": [], "domain-auditor": []})
    assert [d["label"] for d in t][-3:] == ["domain-coverage-delta", "domain-auditor", "closeout"]


@pytest.mark.parametrize("value", ["true", "false", 1, 0, None, [], {}])
def test_non_boolean_capture_is_refused_before_any_dispatch(value):
    r = trace_raw({**HA_SHAPED, "domain_improvement_capture": value})
    assert r.returncode == 3, r.stderr
    assert r.stderr == (
        "apd-gauntlet: args.domain_improvement_capture " + json.dumps(value) + " "
        + CAPTURE_REFUSAL_END), r.stderr
    assert json.loads(r.stdout) == [], "the runner dispatched before refusing the run config"


def test_plan_run_matches_workflow_dispatch_sequence_with_capture():
    cfg = {"run_id": "apd-test-full", "domains": ["agentic-ai", "api-security"],
           "code_recon": "enabled", "crown_jewels": ["a"], "domain_improvement_capture": True}
    wf = [("CLI", d["command"].split()[1]) if d["agentType"] == "apd-cli-runner"
          else ("AGENT", d["agentType"]) for d in trace(cfg)]
    assert [(s["kind"], s["ref"].split()[0]) for s in build_plan(cfg)] == wf
    assert ("AGENT", "apd-domain-auditor") in wf
