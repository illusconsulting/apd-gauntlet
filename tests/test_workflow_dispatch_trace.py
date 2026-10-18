"""What the workflow runner dispatches, measured by running it under node.

tests/js/workflow_dispatch_trace.mjs runs the real .claude/workflows/apd-gauntlet.js
against stub Workflow globals and prints every dispatch as
{agentType, label, phase, guard, command}. The tests here count and order those
dispatches. They are skipped where node is absent, like test_c4_solve_routes_node_oracle;
the CI test job provisions Node 22 so they run there.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

import pytest
import yaml

REPO = Path(__file__).resolve().parent.parent
RUNNER = REPO / ".claude" / "workflows" / "apd-gauntlet.js"
HARNESS = REPO / "tests" / "js" / "workflow_dispatch_trace.mjs"
CI = REPO / ".github" / "workflows" / "python-tests.yml"

# An HA-shaped run config: code recon on, a crown jewel declared, no threat model.
HA_SHAPED: dict[str, Any] = {
    "run_id": "r", "domains": ["pbm"], "code_recon": "enabled", "crown_jewels": ["phi_store"],
}

# Every CLI dispatch of a clean HA-shaped run on the WS1 + WS2 base, in order.
CLI_LABELS = [
    # setup and intake
    "resume-plan", "validate-scaffold", "build-domain-skill", "validate-domain",
    "assemble-inventory", "intake-schema-gate",
    # context
    "canonicalize-code-evidence", "author-threat-model-floor", "canonicalize-threat-model",
    # tiers
    "canonicalize-10-trustworthiness", "validate-10-trustworthiness",
    "canonicalize-20-scalability", "validate-20-scalability",
    "canonicalize-30-auditability", "validate-30-auditability", "validate-full-prephase5",
    # synthesis
    "cluster-candidates", "apply-clusters", "assemble-c4", "canonicalize-tmeval", "rollup",
    "build-report-attempt-0", "audit-report-attempt-0",
    # Phase 5h and closeout
    "domain-coverage-delta", "canonicalize-dimpr", "summarize", "validate-final",
]


def trace_raw(
    cfg: dict[str, Any], fail: dict[str, list[str]] | None = None
) -> subprocess.CompletedProcess[str]:
    """Run the harness on the runner with `cfg` as args; `fail` maps a label to the
    names of its failing steps (an empty list fails the label itself)."""
    node = shutil.which("node")
    if node is None:
        pytest.skip("node not available")
    argv = [node, str(HARNESS), str(RUNNER), json.dumps(cfg)]
    if fail is not None:
        argv.append(json.dumps(fail))
    return subprocess.run(argv, capture_output=True, text=True, timeout=60, cwd=REPO)


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
    assert len(llm(trace(HA_SHAPED))) == 18


@pytest.mark.parametrize("patch", [{"run_id": "r; touch x"}, {"domains": ["pbm", "$(id)"]},
                                   {"framework_version": "1.7.0 && id"}])
def test_trace_rejects_shell_metacharacters(patch):
    r = trace_raw({**HA_SHAPED, **patch})
    assert r.returncode == 3 and "run-config.schema.json" in r.stderr


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
    assert commands["build-domain-skill"] == (
        "apd-gauntlet build-domain-skill pbm fhir-r4 --framework-version 1.7.1")


def test_absent_framework_version_omits_the_flag():
    commands = {d["label"]: d["command"] for d in cli(trace(HA_SHAPED))}
    assert commands["build-domain-skill"] == "apd-gauntlet build-domain-skill pbm"


def test_trace_records_phase_and_guard():
    by_label = {d["label"]: d for d in trace(HA_SHAPED)}
    assert by_label["validate-10-trustworthiness"]["phase"] == "tier-1"
    assert by_label["validate-10-trustworthiness"]["guard"] is False  # alwaysRun
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
