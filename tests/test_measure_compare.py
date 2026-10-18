"""measure.compare: the pairwise delta between two finished runs."""
from __future__ import annotations

import copy
import pathlib

import pytest
import yaml
from apd_gauntlet.measure.compare import (
    MATURITY_ORDER,
    SEVERITY_ORDER,
    blocked_rate_pct,
    compare_pair,
    unexcused_lost,
)
from apd_gauntlet.measure.runs import RunSnapshot, is_run_dir, load_run

REPO = pathlib.Path(__file__).parent.parent
CEB = REPO / "examples/apd-20260601-claim-event-bus/expected"
CONF_FINDINGS = "10-trustworthiness/confidentiality.findings.yaml"


def new_finding(rid, title, *, evidence):
    """A copy of ``conf-7aa376c5``'s record with ``id``, ``title`` and ``evidence`` replaced."""
    doc = yaml.safe_load((CEB / CONF_FINDINGS).read_text(encoding="utf-8"))
    (base,) = [r for r in doc["finding"] if r["id"] == "conf-7aa376c5"]
    record = copy.deepcopy(base)
    record.update(
        id=rid,
        title=title,
        evidence=[{"artifact": a, "locator": loc, "excerpt": "x"} for a, loc in evidence],
    )
    return record


def snapshot(findings=None, capabilities=None, headlines=None):
    return RunSnapshot(
        path=pathlib.Path("run"),
        findings=findings or {},
        capabilities=capabilities or {},
        graph_targets={},
        headlines=headlines,
        inputs_sha256=None,
    )


# The plan's tests (Task 2 Step 1).


def test_mutations_are_reported(make_run, edit):
    b, c = make_run("b"), make_run("c")
    edit.drop(c, "conf-7aa376c5")                                  # high, confidentiality
    edit.finding(c, "avail-ce35b2ed", severity="medium")
    edit.finding(c, "immut-067a7391", disposition="gap")
    edit.capability(c, "conf-cap-d0590471", maturity="tested")
    d = compare_pair(load_run(b), load_run(c))
    assert len(d.findings.matched) == 19
    assert d.findings.missing == ("conf-7aa376c5",) and d.findings.new == ()
    assert d.missing_by_severity == {"high": 1} and d.new_by_severity == {}
    assert d.severity_shifts == {"high->medium": 1}
    assert d.severity_agreement_pct == pytest.approx(1800 / 19)
    assert d.maturity_shifts == {"implemented->tested": 1}
    assert [(x.id, x.excuse) for x in d.lost_critical_high] == [("conf-7aa376c5", None)]
    assert d.headline_overlap_pct == pytest.approx(600 / 7)
    assert blocked_rate_pct(load_run(b)) == 15.0
    assert blocked_rate_pct(load_run(c)) == pytest.approx(200 / 19)


def test_operator_excuse(make_run, edit):
    b, c = make_run("b"), make_run("c")
    edit.drop(c, "conf-7aa376c5")
    d = compare_pair(load_run(b), load_run(c), excused=frozenset({"conf-7aa376c5"}))
    assert d.lost_critical_high[0].excuse == "operator" and unexcused_lost(d) == 0


def test_evidence_reassigned_excuse(make_run, edit):
    b, c = make_run("b"), make_run("c")
    edit.drop(c, "intg-42a3ebbd")                 # cites threat-model.md / Tampering paragraph 2
    edit.add_finding(c, "10-trustworthiness/confidentiality.findings.yaml", new_finding(
        "conf-0000beef", "Unsigned Kafka payloads allow claim tampering in transit",
        evidence=[("threat-model.md", "Tampering paragraph 2")]))
    d = compare_pair(load_run(b), load_run(c))
    assert d.lost_critical_high[0].excuse == "evidence_reassigned:conf-0000beef"


def test_shared_evidence_with_existing_capability_does_not_excuse(make_run, edit):
    b, c = make_run("b"), make_run("c")
    edit.drop(c, "conf-7aa376c5")             # conf-cap-d0590471 cites the same pair in both runs
    assert unexcused_lost(compare_pair(load_run(b), load_run(c))) == 1


# Further pins on the delta and on the conftest fixtures.


def test_orders_are_least_to_most():
    assert SEVERITY_ORDER == ("informational", "low", "medium", "high", "critical")
    assert MATURITY_ORDER == ("designed", "implemented", "tested", "operationalized")


def test_identical_runs_have_an_empty_delta(make_run):
    b, c = make_run("b"), make_run("c")
    d = compare_pair(load_run(b), load_run(c))
    assert d.baseline == b and d.candidate == c
    assert len(d.findings.matched) == 20 and len(d.capabilities.matched) == 10
    assert d.missing_by_severity == {} and d.new_by_severity == {}
    assert d.severity_shifts == {} and d.maturity_shifts == {}
    assert d.severity_agreement_pct == 100.0 and d.headline_overlap_pct == 100.0
    assert d.lost_critical_high == () and unexcused_lost(d) == 0


def test_new_findings_are_counted_by_severity(make_run, edit):
    b, c = make_run("b"), make_run("c")
    edit.add_finding(c, CONF_FINDINGS, new_finding(
        "conf-0000beef", "Unsigned Kafka payloads allow claim tampering in transit",
        evidence=[("tech_plan.md", "§9 paragraph 1")]))
    d = compare_pair(load_run(b), load_run(c))
    assert d.findings.new == ("conf-0000beef",) and d.new_by_severity == {"high": 1}


def test_lost_findings_list_critical_first_and_skip_lower_severities(make_run, edit):
    b, c = make_run("b"), make_run("c")
    edit.finding(b, "nonrep-62124087", severity="critical")
    for rid in ("nonrep-62124087", "conf-7aa376c5", "auth-8d386c2f"):    # critical, high, medium
        edit.drop(c, rid)
    d = compare_pair(load_run(b), load_run(c))
    assert d.missing_by_severity == {"critical": 1, "high": 1, "medium": 1}
    assert list(d.missing_by_severity) == ["critical", "high", "medium"]
    assert [(x.id, x.severity) for x in d.lost_critical_high] == [
        ("nonrep-62124087", "critical"), ("conf-7aa376c5", "high")]
    assert d.lost_critical_high[1].title == (
        "PHI fields in Kafka claim-events topic lack envelope encryption")
    assert unexcused_lost(d) == 2


def test_operator_excuse_wins_over_reassigned_evidence(make_run, edit):
    b, c = make_run("b"), make_run("c")
    edit.drop(c, "intg-42a3ebbd")
    edit.add_finding(c, CONF_FINDINGS, new_finding(
        "conf-0000beef", "Unsigned Kafka payloads allow claim tampering in transit",
        evidence=[("threat-model.md", "Tampering paragraph 2")]))
    d = compare_pair(load_run(b), load_run(c), excused=frozenset({"intg-42a3ebbd"}))
    assert d.lost_critical_high[0].excuse == "operator"


def test_evidence_reassigned_to_a_new_capability(make_run, edit):
    b, c = make_run("b"), make_run("c")
    edit.drop(c, "intg-42a3ebbd")
    capability = {"id": "intg-cap-0000beef", "apd_goal": "integrity", "maturity": "designed",
                  "title": "Producers sign every claim event payload",
                  "evidence": [{"artifact": "./threat-model.md",           # normalised to match
                                "locator": " Tampering paragraph 2 ", "excerpt": "x"}]}
    (c / "10-trustworthiness/extra.capabilities.yaml").write_text(
        yaml.safe_dump({"capability": [capability]}, sort_keys=False), encoding="utf-8")
    d = compare_pair(load_run(b), load_run(c))
    assert d.findings.new == () and d.capabilities.new == ("intg-cap-0000beef",)
    assert d.lost_critical_high[0].excuse == "evidence_reassigned:intg-cap-0000beef"


def test_evidence_pointer_without_artifact_or_locator_does_not_excuse():
    lost = {"id": "conf-1", "apd_goal": "confidentiality", "severity": "high", "title": "Lost",
            "evidence": [{"excerpt": "x"}]}
    new = {"id": "intg-2", "apd_goal": "integrity", "severity": "low", "title": "New",
           "evidence": [{"excerpt": "y"}]}
    d = compare_pair(snapshot({"conf-1": lost}), snapshot({"intg-2": new}))
    assert [(x.id, x.excuse) for x in d.lost_critical_high] == [("conf-1", None)]


def test_a_missing_severity_counts_as_unknown_after_the_known_levels():
    lost = {f"conf-{n}": {"id": f"conf-{n}", "apd_goal": "confidentiality", "title": f"T{n}",
                          "evidence": [{"artifact": "a.md", "locator": f"#{n}"}]} for n in (1, 2)}
    lost["conf-2"]["severity"] = "low"
    d = compare_pair(snapshot(lost), snapshot())
    assert list(d.missing_by_severity.items()) == [("low", 1), ("unknown", 1)]
    assert d.lost_critical_high == ()


def test_no_matches_leave_agreement_undefined():
    d = compare_pair(snapshot(), snapshot())
    assert d.severity_agreement_pct is None and d.findings.matched == ()


def test_headline_overlap_undefined_without_headlines(make_run):
    b, c = make_run("b"), make_run("c")
    (c / "40-synthesis/report-data.yaml").unlink()
    assert compare_pair(load_run(b), load_run(c)).headline_overlap_pct is None
    assert compare_pair(snapshot(headlines=()), snapshot(headlines=())).headline_overlap_pct is None


def test_blocked_rate_undefined_without_findings():
    assert blocked_rate_pct(snapshot()) is None


def test_make_run_copies_the_example_with_its_inputs(make_run):
    b, c = make_run("b"), make_run("c")
    assert is_run_dir(b) and (b / "inputs/threat-model.md").is_file()
    assert load_run(b).inputs_sha256 is not None
    assert load_run(b).inputs_sha256 == load_run(c).inputs_sha256


def test_edit_accepts_a_single_mapping_root(make_run, edit):
    run = make_run("r")
    path = run / "20-scalability/single.findings.yaml"
    record = new_finding("dist-0000beef", "A single mapping root", evidence=[("a.md", "#x")])
    path.write_text(yaml.safe_dump({"finding": record}, sort_keys=False), encoding="utf-8")
    edit.finding(run, "dist-0000beef", severity="low")
    assert load_run(run).findings["dist-0000beef"]["severity"] == "low"
    edit.drop(run, "dist-0000beef")
    assert "dist-0000beef" not in load_run(run).findings


def test_edit_refuses_an_unknown_id(make_run, edit):
    run = make_run("r")
    with pytest.raises(LookupError, match="nope-00000000"):
        edit.drop(run, "nope-00000000")
    with pytest.raises(LookupError, match="conf-7aa376c5"):
        edit.capability(run, "conf-7aa376c5", maturity="tested")   # a finding id, not a capability
