"""The ``compare-runs`` command: run sets, medians and the proposal gates."""
from __future__ import annotations

import json
import pathlib
import shutil

import pytest
from apd_gauntlet.cli import main
from apd_gauntlet.measure.attempts import write_attempts
from apd_gauntlet.measure.compare import (
    Comparison,
    MissingRuns,
    compare_sides,
    comparison_json,
    render_text,
    resolve_side,
)
from apd_gauntlet.measure.gates import (
    Check,
    Gate,
    GateOutcome,
    apply_excuses,
    evaluate,
    load_gates,
    overall,
    split_excuses,
)
from apd_gauntlet.measure.runs import load_run
from apd_gauntlet.measure.usage import write_usage
from click.testing import CliRunner

REPO = pathlib.Path(__file__).resolve().parent.parent
GOOD_ATTEMPTS = {
    "schema_version": 1,
    "recorded_by": "workflow",
    "lens_retries": {"integrity": 1, "availability": 0},
    "first_pass_invalid": [],
    "tier_gate_failures": [],
    "skipped": [],
    "audit_iterations": 2,
    "tier_repairs": {},
    "lens_reruns": {},
}

GATES = str(REPO / "eval/gates.yaml")


def cr(*args):
    return CliRunner().invoke(main, ["compare-runs", *map(str, args)])


def test_missing_baseline_exits_2(make_run, tmp_path):
    r = cr(tmp_path / "nope", make_run("c"), "--gates", GATES)
    assert r.exit_code == 2 and "baseline not found" in r.output and "-r1" in r.output


def test_same_run_exits_2(make_run):
    run = make_run("b")
    assert cr(run, run).exit_code == 2


def test_scaffold_baseline_exits_2(make_run, tmp_path):
    s = tmp_path / "scaffold"
    s.mkdir()
    (s / ".apd-run.yaml").write_text("run_id: scaffold\n")
    r = cr(s, make_run("c"))
    assert r.exit_code == 2 and "no findings" in r.output


def test_different_inputs_exit_2(make_run):
    b, c = make_run("b"), make_run("c")
    (c / "inputs/extra.md").write_text("x")
    r = cr(b, c)
    assert r.exit_code == 2 and "different inputs" in r.output


def test_identical_runs_pass_with_gaps(make_run):
    r = cr(make_run("b"), make_run("c"), "--gates", GATES, "--json")
    out = json.loads(r.stdout)
    assert r.exit_code == 0 and out["status"] == "pass_with_gaps"
    assert [g["status"] for g in out["gates"]] == [
        "pass", "pass", "pass", "not_available", "not_available"
    ]


def test_attempt_gates_not_available_on_1_7_runs(make_run):
    out = json.loads(cr(make_run("b"), make_run("c"), "--gates", GATES, "--json").stdout)
    assert "attempts.yaml" in out["gates"][3]["reason"]


def test_strict_fails_on_gaps(make_run):
    assert cr(make_run("b"), make_run("c"), "--gates", GATES, "--strict").exit_code == 1


def test_lost_high_fails_and_excuse_passes(make_run, edit):
    b, c = make_run("b"), make_run("c")
    edit.drop(c, "conf-7aa376c5")
    assert cr(b, c, "--gates", GATES).exit_code == 1
    assert cr(b, c, "--gates", GATES, "--excuse", "conf-7aa376c5").exit_code == 0


def test_gate_excuse_passes_and_is_recorded(make_run, edit):
    b, c = make_run("b"), make_run("c")
    edit.drop(c, "conf-7aa376c5")
    ex = "no_lost_critical_high:loss reviewed"
    out = json.loads(cr(b, c, "--gates", GATES, "--json", "--excuse", ex).stdout)
    assert out["gates"][0]["status"] == "excused" and out["gates"][0]["excuse"] == "loss reviewed"
    r = cr(b, c, "--gates", GATES, "--excuse", ex)
    assert r.exit_code == 0 and "EXCUSED (loss reviewed)" in r.output


def test_pair_convention_and_medians(make_run, edit, tmp_path):
    for n in ("x-base-r1", "x-base-r2", "x-cand-r1", "x-cand-r2"):
        make_run(n)
    edit.drop(tmp_path / "x-cand-r1", "conf-7aa376c5")
    out = json.loads(
        cr(tmp_path / "x-base", tmp_path / "x-cand", "--gates", GATES, "--json").stdout
    )
    assert len(out["baseline"]) == 2 and len(out["pairs"]) == 4
    assert out["values"]["unexcused_lost_critical_high"] == 0.5
    assert out["gates"][0]["status"] == "fail"


def test_attempt_medians(make_run, tmp_path):
    runs = {n: make_run(n) for n in ("y-base-r1", "y-base-r2", "y-cand-r1", "y-cand-r2")}
    for n, k in {"y-base-r1": 1, "y-base-r2": 1, "y-cand-r1": 0, "y-cand-r2": 2}.items():
        write_attempts(runs[n], {**GOOD_ATTEMPTS, "lens_retries": {"integrity": k}})
    out = json.loads(
        cr(tmp_path / "y-base", tmp_path / "y-cand", "--gates", GATES, "--json").stdout
    )
    assert out["values"]["lens_retries_delta"] == 0 and out["gates"][3]["status"] == "pass"


def test_resumed_run_attempts_not_available(make_run):
    b, c = make_run("b"), make_run("c")
    write_attempts(b, GOOD_ATTEMPTS)
    write_attempts(c, {**GOOD_ATTEMPTS, "skipped": ["integrity"]})
    out = json.loads(cr(b, c, "--gates", GATES, "--json").stdout)
    assert out["gates"][3]["status"] == "not_available" and "resumed" in out["gates"][3]["reason"]


def test_usage_cost_reported(make_run):
    b, c = make_run("b"), make_run("c")
    for run, cost in ((b, 2.0), (c, 1.5)):
        write_usage(run, {"schema_version": 1, "totals": {"requests": 1, "cost_usd": cost}})
    out = json.loads(cr(b, c, "--json").stdout)
    assert out["status"] == "delta_only" and out["runs"][str(c)]["cost_usd"] == 1.5


# --- beyond the plan's tests: side resolution ----------------------------------------------


def test_resolve_side_prefers_the_run_directory_itself(make_run, tmp_path):
    run = make_run("z")
    make_run("z-r1")
    assert resolve_side(run) == [run]


def test_resolve_side_stops_at_the_first_gap(make_run, tmp_path):
    for n in ("s-r1", "s-r2", "s-r4"):
        make_run(n)
    assert resolve_side(tmp_path / "s") == [tmp_path / "s-r1", tmp_path / "s-r2"]


def test_resolve_side_skips_a_directory_that_is_not_a_run(make_run, tmp_path):
    (tmp_path / "t").mkdir()  # no .apd-run.yaml
    make_run("t-r1")
    assert resolve_side(tmp_path / "t") == [tmp_path / "t-r1"]


def test_resolve_side_needs_r1(make_run, tmp_path):
    make_run("u-r2")
    with pytest.raises(MissingRuns) as info:
        resolve_side(tmp_path / "u")
    message = str(info.value)
    for s in (str(tmp_path / "u"), "-r1", "-r2", "docs/measuring-changes.md"):
        assert s in message


def test_missing_baseline_message_names_the_convention_and_the_runbook(make_run, tmp_path):
    r = cr(tmp_path / "nope", make_run("c"))
    assert r.exit_code == 2
    assert r.stderr.startswith("Error: baseline not found: ")
    for s in (str(tmp_path / "nope"), "-r2", "docs/measuring-changes.md"):
        assert s in r.stderr
    assert r.stdout == ""


def test_a_side_that_cannot_be_read_exits_2(make_run, tmp_path, monkeypatch):
    def unreadable(path):
        raise PermissionError(13, "Permission denied", str(path))

    monkeypatch.setattr("apd_gauntlet.measure.compare.is_run_dir", unreadable)
    with pytest.raises(MissingRuns, match="cannot read: Permission denied"):
        resolve_side(tmp_path / "x")
    r = cr(tmp_path / "x", tmp_path / "y")
    assert r.exit_code == 2
    assert r.stderr == (
        f"Error: baseline not found: {tmp_path / 'x'}: cannot read: Permission denied\n"
    )


def test_missing_candidate_exits_2(make_run, tmp_path):
    r = cr(make_run("b"), tmp_path / "nope", "--gates", GATES)
    assert r.exit_code == 2 and "candidate not found" in r.stderr and "-r1" in r.stderr


# --- beyond the plan's tests: the other refusals -------------------------------------------


def test_same_directory_through_a_link_exits_2(make_run, tmp_path):
    run = make_run("b")
    link = tmp_path / "link"
    link.symlink_to(run, target_is_directory=True)
    r = cr(run, link)
    assert r.exit_code == 2 and "same run directory" in r.stderr


def test_a_side_whose_sets_share_a_run_exits_2(make_run, tmp_path):
    make_run("v-r1")
    (tmp_path / "w-r1").symlink_to(tmp_path / "v-r1", target_is_directory=True)
    r = cr(tmp_path / "v", tmp_path / "w")
    assert r.exit_code == 2 and "same run directory" in r.stderr


def test_different_inputs_within_one_side_exit_2(make_run, tmp_path):
    for n in ("d-base-r1", "d-base-r2", "d-cand-r1"):
        make_run(n)
    (tmp_path / "d-base-r2/inputs/extra.md").write_text("x")
    r = cr(tmp_path / "d-base", tmp_path / "d-cand")
    assert r.exit_code == 2 and "different inputs" in r.stderr
    assert str(tmp_path / "d-base-r2") in r.stderr


def test_scaffold_candidate_is_compared(make_run, tmp_path):
    s = tmp_path / "scaffold"
    s.mkdir()
    (s / ".apd-run.yaml").write_text("run_id: scaffold\n")
    out = json.loads(cr(make_run("b"), s, "--gates", GATES, "--json").stdout)
    assert out["status"] == "fail" and out["gates"][0]["status"] == "fail"
    assert out["gates"][2]["status"] == "not_available"
    assert out["gates"][2]["reason"] == f"{s} has no findings, so it has no blocked rate"


def test_run_that_fails_to_load_exits_2(make_run):
    b, c = make_run("b"), make_run("c")
    bad = c / "10-trustworthiness/confidentiality.findings.yaml"
    bad.write_text("finding: [\n")
    r = cr(b, c, "--gates", GATES)
    assert r.exit_code == 2 and str(bad) in r.stderr and r.stdout == ""


def test_os_error_while_loading_exits_2(make_run, monkeypatch):
    b, c = make_run("b"), make_run("c")

    def unreadable(path):
        raise PermissionError(13, "Permission denied", str(path / "40-synthesis"))

    monkeypatch.setattr("apd_gauntlet.measure.runs.load_run", unreadable)
    r = cr(b, c)
    assert r.exit_code == 2
    assert f"{b / '40-synthesis'}: cannot read: Permission denied" in r.stderr


@pytest.mark.parametrize("content", [None, "schema_version: 1\ngates: []\n"])
def test_unreadable_gates_exit_2(make_run, tmp_path, content):
    gates = tmp_path / "gates.yaml"
    if content is not None:
        gates.write_text(content)
    r = cr(make_run("b"), make_run("c"), "--gates", gates)
    assert r.exit_code == 2 and str(gates) in r.stderr and r.stdout == ""


def test_gate_excuse_without_a_reason_exits_2(make_run):
    r = cr(make_run("b"), make_run("c"), "--gates", GATES, "--excuse", "blocked_rate: ")
    assert r.exit_code == 2 and "--excuse" in r.output and "needs a reason" in r.output


# --- beyond the plan's tests: statuses, excuses and warnings -------------------------------


def test_lost_high_without_gates_is_delta_only(make_run, edit):
    b, c = make_run("b"), make_run("c")
    edit.drop(c, "conf-7aa376c5")
    r = cr(b, c, "--json")
    out = json.loads(r.stdout)
    assert r.exit_code == 0 and out["status"] == "delta_only" and out["gates"] == []
    assert out["values"]["unexcused_lost_critical_high"] == 1.0


def test_excusing_the_unavailable_gates_passes_under_strict(make_run):
    r = cr(make_run("b"), make_run("c"), "--gates", GATES, "--strict", "--json",
           "--excuse", "first_pass_and_retries:1.7.1 baseline records no attempts",
           "--excuse", "audit_iterations:1.7.1 baseline records no attempts")
    out = json.loads(r.stdout)
    assert r.exit_code == 0 and out["status"] == "pass"
    assert [g["status"] for g in out["gates"]] == [
        "pass", "pass", "pass", "excused", "excused"
    ]
    assert out["gates"][3]["reason"].startswith("no .apd-state/attempts.yaml in ")


def test_severity_disagreement_fails_gate_2(make_run, edit):
    b, c = make_run("b"), make_run("c")
    for rid in ("avail-ce35b2ed", "avail-4e08f6d8", "intg-42a3ebbd"):
        edit.finding(c, rid, severity="medium")
    r = cr(b, c, "--gates", GATES, "--json")
    out = json.loads(r.stdout)
    assert r.exit_code == 1 and out["status"] == "fail"
    assert out["values"]["severity_agreement_pct"] == 85.0
    assert out["gates"][1]["status"] == "fail"
    assert out["pairs"][0]["severity_shifts"] == {"high->medium": 3}


def test_blocked_rate_move_fails_gate_3(make_run, edit):
    b, c = make_run("b"), make_run("c")
    for rid in ("avail-ce35b2ed", "intg-42a3ebbd"):
        edit.finding(c, rid, disposition="blocked")
    out = json.loads(cr(b, c, "--gates", GATES, "--json").stdout)
    assert out["values"]["baseline_blocked_rate_pct"] == 15.0
    assert out["values"]["candidate_blocked_rate_pct"] == 25.0
    assert out["values"]["blocked_rate_abs_delta_pts"] == 10.0
    assert out["gates"][2]["status"] == "fail"


def test_attempts_on_one_side_only_name_the_run_without(make_run):
    b, c = make_run("b"), make_run("c")
    write_attempts(c, GOOD_ATTEMPTS)
    out = json.loads(cr(b, c, "--gates", GATES, "--json").stdout)
    reason = (
        f"no .apd-state/attempts.yaml in {b} (1.7 runs and foreground drives record none)"
    )
    assert out["gates"][3]["reason"] == reason and out["gates"][4]["reason"] == reason
    assert out["runs"][str(c)]["lens_retries_total"] == 1
    assert out["runs"][str(b)]["lens_retries_total"] is None


def test_resumed_reason_text(make_run):
    b, c = make_run("b"), make_run("c")
    write_attempts(b, GOOD_ATTEMPTS)
    write_attempts(c, {**GOOD_ATTEMPTS, "skipped": ["integrity", "availability"]})
    out = json.loads(cr(b, c, "--gates", GATES, "--json").stdout)
    assert out["gates"][4]["reason"] == f"{c} resumed: 2 steps skipped, retries under-counted"
    assert out["values"]["audit_iterations_delta"] is None
    assert out["runs"][str(c)]["audit_iterations"] == 2


def test_attempt_deltas_are_candidate_minus_baseline(make_run):
    b, c = make_run("b"), make_run("c")
    write_attempts(b, {**GOOD_ATTEMPTS, "audit_iterations": 3, "lens_reruns": {"integrity": 1}})
    write_attempts(c, {
        **GOOD_ATTEMPTS,
        "first_pass_invalid": ["integrity"],
        "tier_gate_failures": ["20-scalability"],
        "tier_repairs": {"20-scalability": 2},
    })
    out = json.loads(cr(b, c, "--gates", GATES, "--json").stdout)
    values = out["values"]
    assert values["first_pass_validator_errors_delta"] == 2
    assert values["tier_repairs_delta"] == 2
    assert values["lens_reruns_delta"] == -1
    assert values["audit_iterations_delta"] == -1
    assert [g["status"] for g in out["gates"][3:]] == ["fail", "pass"]


def test_single_run_warning_only_with_gates(make_run, tmp_path):
    b, c = make_run("b"), make_run("c")
    warning = "gates applied to a single run per side; run each configuration twice"
    assert warning in json.loads(cr(b, c, "--gates", GATES, "--json").stdout)["warnings"]
    assert warning not in json.loads(cr(b, c, "--json").stdout)["warnings"]
    for n in ("p-base-r1", "p-base-r2", "p-cand-r1", "p-cand-r2"):
        make_run(n)
    r = cr(tmp_path / "p-base", tmp_path / "p-cand", "--gates", GATES, "--json")
    assert warning not in json.loads(r.stdout)["warnings"]


def test_strict_without_gates_warns(make_run):
    r = cr(make_run("b"), make_run("c"), "--strict", "--json")
    assert r.exit_code == 0
    assert "--strict has no effect without --gates" in json.loads(r.stdout)["warnings"]


def test_excuse_that_matches_no_lost_finding_warns(make_run):
    out = json.loads(cr(make_run("b"), make_run("c"), "--gates", GATES, "--json",
                        "--excuse", "no_such_gate:typo").stdout)
    assert (
        "excused finding no_such_gate:typo is not a lost critical or high finding in any pair; "
        "it excuses nothing"
    ) in out["warnings"]
    assert all(g["status"] != "excused" for g in out["gates"])


def test_missing_inputs_warn(make_run):
    b, c = make_run("b"), make_run("c")
    shutil.rmtree(c / "inputs")
    r = cr(b, c, "--json")
    assert r.exit_code == 0
    assert (
        f"{c} has no inputs/, so it cannot be checked against the other runs' inputs"
    ) in json.loads(r.stdout)["warnings"]


def test_severity_outside_the_scale_warns(make_run, edit):
    b, c = make_run("b"), make_run("c")
    edit.finding(c, "conf-7aa376c5", severity="High")
    out = json.loads(cr(b, c, "--json").stdout)
    assert (
        f"{c}: 1 findings have a severity outside informational, low, medium, high, critical "
        "(conf-7aa376c5); a lost one never counts as a lost critical or high finding"
    ) in out["warnings"]


# --- beyond the plan's tests: output -------------------------------------------------------


def test_json_keys_and_runs_keyed_by_the_path_as_given(make_run, tmp_path, monkeypatch):
    make_run("b")
    make_run("c")
    monkeypatch.chdir(tmp_path)
    out = json.loads(cr("b", "c", "--gates", GATES, "--json").stdout)
    assert list(out) == [
        "status", "baseline", "candidate", "pairs", "runs", "values", "gates", "warnings"
    ]
    assert out["baseline"] == ["b"] and out["candidate"] == ["c"]
    assert list(out["runs"]) == ["b", "c"]
    assert list(out["runs"]["b"]) == [
        "blocked_rate_pct", "first_pass_validator_errors", "lens_retries_total",
        "tier_repairs_total", "lens_reruns_total", "audit_iterations", "cost_usd",
        "cost_usd_all",
    ]
    assert out["runs"]["b"]["blocked_rate_pct"] == 15.0
    assert list(out["pairs"][0]) == [
        "baseline", "candidate", "findings", "capabilities", "missing_by_severity",
        "new_by_severity", "severity_shifts", "severity_agreement_pct", "lost_critical_high",
        "unexcused_lost_critical_high", "maturity_shifts", "headline_overlap_pct",
    ]
    assert list(out["gates"][0]) == [
        "id", "text", "status", "checks", "values", "reason", "excuse"
    ]


def test_json_values_order_and_side_medians(make_run):
    b, c = make_run("b"), make_run("c")
    out = json.loads(cr(b, c, "--json").stdout)
    gate_metrics = [
        "unexcused_lost_critical_high", "severity_agreement_pct", "blocked_rate_abs_delta_pts",
        "first_pass_validator_errors_delta", "lens_retries_delta", "tier_repairs_delta",
        "lens_reruns_delta", "audit_iterations_delta",
    ]
    assert list(out["values"])[:8] == gate_metrics
    per_run = list(out["runs"][str(b)])
    assert list(out["values"])[8:] == [
        f"{side}_{m}" for m in per_run for side in ("baseline", "candidate")
    ]
    assert out["values"]["severity_agreement_pct"] == 100.0
    assert out["values"]["blocked_rate_abs_delta_pts"] == 0.0


def test_json_pair_detail(make_run, edit):
    b, c = make_run("b"), make_run("c")
    edit.drop(c, "conf-7aa376c5")
    pair = json.loads(cr(b, c, "--json", "--excuse", "conf-7aa376c5").stdout)["pairs"][0]
    assert pair["baseline"] == str(b) and pair["candidate"] == str(c)
    assert pair["findings"]["missing"] == ["conf-7aa376c5"] and pair["findings"]["new"] == []
    assert len(pair["findings"]["matched"]) == 19
    assert set(pair["findings"]["matched"][0]) == {
        "baseline", "candidate", "title_similarity", "asset_similarity"
    }
    assert pair["missing_by_severity"] == {"high": 1}
    assert pair["lost_critical_high"] == [{
        "id": "conf-7aa376c5",
        "severity": "high",
        "title": "PHI fields in Kafka claim-events topic lack envelope encryption",
        "excuse": "operator",
    }]
    assert pair["unexcused_lost_critical_high"] == 0


def test_usage_cost_medians_and_combined_cost(make_run, tmp_path):
    runs = [make_run(n) for n in ("q-base-r1", "q-base-r2", "q-cand-r1", "q-cand-r2")]
    for run, cost in zip(runs, (2.0, 3.0, 1.0, 1.5), strict=True):
        write_usage(run, {
            "schema_version": 1,
            "totals": {"requests": 1, "cost_usd": cost},
            "cost_usd_all": cost + 0.25,
        })
    out = json.loads(cr(tmp_path / "q-base", tmp_path / "q-cand", "--json").stdout)
    values = out["values"]
    assert values["baseline_cost_usd"] == 2.5 and values["candidate_cost_usd"] == 1.25
    assert values["baseline_cost_usd_all"] == 2.75 and values["candidate_cost_usd_all"] == 1.5
    assert out["runs"][str(runs[3])]["cost_usd_all"] == 1.75


def test_text_report(make_run, edit):
    b, c = make_run("b"), make_run("c")
    edit.drop(c, "conf-7aa376c5")
    r = cr(b, c, "--gates", GATES)
    assert r.exit_code == 1
    lines = r.stdout.splitlines()
    assert lines[0] == "compare-runs: 1 baseline run, 1 candidate run"
    assert f"  {b}: 20 findings, 10 capabilities, blocked 15%, cost_usd n/a" in lines
    pair = next(line for line in lines if line.startswith(f"  {b} -> {c}: "))
    for s in ("findings 19 matched, 1 missing (high 1), 0 new", "severity shifts none",
              "capabilities 10 matched, 0 missing, 0 new", "maturity shifts none",
              "headline overlap"):
        assert s in pair
    assert (
        "    lost high conf-7aa376c5 (not excused): "
        "PHI fields in Kafka claim-events topic lack envelope encryption"
    ) in lines
    assert any(line.startswith("  FAIL  no_lost_critical_high: ") for line in lines)
    assert any(line.startswith("  PASS  severity_agreement: ") for line in lines)
    unavailable = next(
        line for line in lines if line.startswith("  NOT AVAILABLE  first_pass_and_retries: ")
    )
    assert f"no .apd-state/attempts.yaml in {b}" in unavailable
    assert "warning: gates applied to a single run per side; run each configuration twice" in lines
    assert lines[-1] == (
        "RESULT: fail (failed: no_lost_critical_high; "
        "not available: first_pass_and_retries, audit_iterations)"
    )


def test_text_report_without_missing_data(make_run):
    b, c = make_run("b"), make_run("c")
    for run in (b, c):
        write_attempts(run, GOOD_ATTEMPTS)
        write_usage(run, {"schema_version": 1, "totals": {"cost_usd": 1.0}, "cost_usd_all": 1.0})
    r = cr(b, c, "--gates", GATES, "--strict")
    assert r.exit_code == 0 and "missing data:" not in r.stdout
    assert r.stdout.splitlines()[-2:] == [
        "warning: gates applied to a single run per side; run each configuration twice",
        "RESULT: pass",
    ]


def test_text_report_result_lines(make_run, edit):
    b, c = make_run("b"), make_run("c")
    assert cr(b, c).stdout.splitlines()[-1] == "RESULT: delta_only"
    lines = cr(b, c, "--gates", GATES).stdout.splitlines()
    assert lines[-1] == (
        "RESULT: pass_with_gaps (not available: first_pass_and_retries, audit_iterations)"
    )
    edit.drop(c, "conf-7aa376c5")
    r = cr(b, c, "--gates", GATES, "--excuse", "conf-7aa376c5",
           "--excuse", "audit_iterations:reviewed")
    assert "    lost high conf-7aa376c5 (excused: operator): " in r.stdout
    assert r.stdout.splitlines()[-1] == (
        "RESULT: pass_with_gaps (not available: first_pass_and_retries; "
        "excused: audit_iterations)"
    )


# --- beyond the plan's tests: the library functions ----------------------------------------


def _gate(gate_id, metric="lens_retries_delta"):
    return Gate(id=gate_id, text=gate_id, checks=(Check(metric=metric, op="le", value=0.0),))


def test_split_excuses():
    gates, findings = split_excuses(
        ["a:one", "conf-1", "a:two", "a:one", "zz:x", "b: spaced "], ["a", "b"]
    )
    assert gates == {"a": "one; two", "b": "spaced"}
    assert findings == frozenset({"conf-1", "zz:x"})
    with pytest.raises(ValueError, match="needs a reason"):
        split_excuses(["a:"], ["a"])


def test_apply_excuses_keeps_values_and_reason():
    out = evaluate([_gate("a"), _gate("b")], {"lens_retries_delta": None}, {
        "lens_retries_delta": "why"
    })
    excused = apply_excuses(out, {"a": "reviewed"})
    assert excused[0] == GateOutcome(
        gate=_gate("a"), status="excused", values={"lens_retries_delta": None}, reason="why",
        excuse="reviewed",
    )
    assert excused[1] == out[1] and out[1].excuse is None
    assert overall(excused) == "pass_with_gaps"
    assert overall(apply_excuses(out, {"a": "r", "b": "r"})) == "pass"


def test_compare_sides_needs_a_run_on_each_side(make_run):
    run = load_run(make_run("b"))
    with pytest.raises(ValueError, match="at least one run"):
        compare_sides([run], [])
    with pytest.raises(ValueError, match="listed twice"):
        compare_sides([run], [run])


def test_compare_sides_reasons_feed_evaluate(make_run):
    b, c = load_run(make_run("b")), load_run(make_run("c"))
    comparison = compare_sides([b], [c])
    assert isinstance(comparison, Comparison)
    assert len(comparison.pairs) == 1 and comparison.baseline == (b,)
    assert comparison.reasons["baseline_cost_usd"] == (
        f"no .apd-state/usage.yaml in {b.path} (run apd-gauntlet usage)"
    )
    outcomes = evaluate(load_gates(REPO / "eval/gates.yaml"), comparison.values,
                        comparison.reasons)
    assert overall(outcomes) == "pass_with_gaps"
    lines = render_text(comparison, None, "delta_only").splitlines()
    assert "  baseline_cost_usd: n/a" in lines
    missing = lines[lines.index("missing data:") + 1:-1]
    assert missing == [
        f"  no .apd-state/attempts.yaml in {b.path} (1.7 runs and foreground drives record none)",
        f"  no .apd-state/usage.yaml in {b.path} (run apd-gauntlet usage)",
        f"  no .apd-state/attempts.yaml in {c.path} (1.7 runs and foreground drives record none)",
        f"  no .apd-state/usage.yaml in {c.path} (run apd-gauntlet usage)",
    ]
    assert comparison_json(comparison, None, "delta_only")["gates"] == []
