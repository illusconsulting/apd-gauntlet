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


def snapshot(findings=None, capabilities=None, headlines=None, graph_targets=None):
    return RunSnapshot(
        path=pathlib.Path("run"),
        findings=findings or {},
        capabilities=capabilities or {},
        graph_targets=graph_targets or {},
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


def test_shared_evidence_with_existing_finding_does_not_excuse(make_run, edit):
    b, c = make_run("b"), make_run("c")
    shared = new_finding(
        "conf-0000beef", "Unsigned Kafka payloads allow claim tampering in transit",
        evidence=[("threat-model.md", "Tampering paragraph 2")])     # intg-42a3ebbd's only pair
    edit.add_finding(b, CONF_FINDINGS, copy.deepcopy(shared))
    edit.add_finding(c, CONF_FINDINGS, shared)
    edit.drop(c, "intg-42a3ebbd")
    d = compare_pair(load_run(b), load_run(c))
    assert d.findings.missing == ("intg-42a3ebbd",) and d.findings.new == ()
    assert ("conf-0000beef", "conf-0000beef") in {
        (m.baseline_id, m.candidate_id) for m in d.findings.matched}
    assert [(x.id, x.excuse) for x in d.lost_critical_high] == [("intg-42a3ebbd", None)]
    assert unexcused_lost(d) == 1


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


def test_the_first_new_finding_citing_the_pointer_names_the_excuse(make_run, edit):
    # New findings come first, each kind in id order, so the capability (whose id sorts
    # first) and the later finding both lose to conf-0000beef.
    b, c = make_run("b"), make_run("c")
    edit.drop(c, "intg-42a3ebbd")                                  # cites Tampering paragraph 2
    for rid, title in (("conf-0000cafe", "Claim producers hold no payload signing keys"),
                       ("conf-0000beef", "Unsigned Kafka payloads allow claim tampering")):
        edit.add_finding(c, CONF_FINDINGS, new_finding(
            rid, title, evidence=[("threat-model.md", "Tampering paragraph 2")]))
    capability = {"id": "auth-cap-0000beef", "apd_goal": "authenticity", "maturity": "designed",
                  "title": "Producers sign every claim event payload",
                  "evidence": [{"artifact": "threat-model.md",
                                "locator": "Tampering paragraph 2", "excerpt": "x"}]}
    (c / "10-trustworthiness/extra.capabilities.yaml").write_text(
        yaml.safe_dump({"capability": [capability]}, sort_keys=False), encoding="utf-8")
    d = compare_pair(load_run(b), load_run(c))
    assert d.findings.new == ("conf-0000beef", "conf-0000cafe")
    assert d.capabilities.new == ("auth-cap-0000beef",)
    assert [(x.id, x.excuse) for x in d.lost_critical_high] == [
        ("intg-42a3ebbd", "evidence_reassigned:conf-0000beef")]


@pytest.mark.parametrize(
    "pointer",
    [
        {},                                         # neither part
        {"artifact": "a.md"},                       # no locator
        {"artifact": "a.md", "locator": "   "},     # a locator that strips to nothing
        {"locator": "§1"},                          # no artifact
        {"artifact": " ./ ", "locator": "§1"},      # an artifact that normalises to nothing
    ],
)
def test_evidence_pointer_without_artifact_or_locator_does_not_excuse(pointer):
    lost = {"id": "conf-1", "apd_goal": "confidentiality", "severity": "high", "title": "Lost",
            "evidence": [{**pointer, "excerpt": "x"}]}
    new = {"id": "intg-2", "apd_goal": "integrity", "severity": "low", "title": "New",
           "evidence": [{**pointer, "excerpt": "y"}]}
    d = compare_pair(snapshot({"conf-1": lost}), snapshot({"intg-2": new}))
    assert d.findings.new == ("intg-2",)
    assert [(x.id, x.excuse) for x in d.lost_critical_high] == [("conf-1", None)]


def test_each_runs_graph_targets_join_findings_and_capabilities():
    # Same goal and title, disjoint evidence artifacts: only the asset-graph node is shared.
    finding_title = "PHI in the claim topic lacks envelope encryption"
    capability_title = "KMS encrypts the claim topic at rest"

    def record(rid, title, artifact, **level):
        return {"id": rid, "apd_goal": "confidentiality", "title": title,
                "evidence": [{"artifact": artifact, "locator": "§1", "excerpt": "x"}], **level}

    baseline = snapshot(
        {"conf-1": record("conf-1", finding_title, "a.md", severity="high")},
        {"conf-cap-1": record("conf-cap-1", capability_title, "a.md", maturity="implemented")},
        graph_targets={"conf-1": ["Claim events topic"], "conf-cap-1": ["Claim events topic"]},
    )
    candidate = snapshot(
        {"conf-2": record("conf-2", finding_title, "b.md", severity="high")},
        {"conf-cap-2": record("conf-cap-2", capability_title, "b.md", maturity="implemented")},
        graph_targets={"conf-2": ["claim  events TOPIC"], "conf-cap-2": ["Claim events topic"]},
    )
    d = compare_pair(baseline, candidate)
    assert [(m.baseline_id, m.candidate_id) for m in d.findings.matched] == [("conf-1", "conf-2")]
    assert d.findings.missing == () and d.findings.new == ()
    assert [(m.baseline_id, m.candidate_id) for m in d.capabilities.matched] == [
        ("conf-cap-1", "conf-cap-2")]
    assert d.capabilities.missing == () and d.capabilities.new == ()


def test_a_missing_severity_counts_as_unknown_after_the_known_levels():
    lost = {f"conf-{n}": {"id": f"conf-{n}", "apd_goal": "confidentiality", "title": f"T{n}",
                          "evidence": [{"artifact": "a.md", "locator": f"#{n}"}]} for n in (1, 2)}
    lost["conf-2"]["severity"] = "low"
    d = compare_pair(snapshot(lost), snapshot())
    assert list(d.missing_by_severity.items()) == [("low", 1), ("unknown", 1)]
    assert d.lost_critical_high == ()


def test_shifts_list_the_higher_from_level_first_then_the_higher_to_level():
    def leveled(prefix, key, levels):
        """One record per title, each with its own level; ``None`` leaves ``key`` out."""
        return {f"{prefix}-{title}": {
            "id": f"{prefix}-{title}", "apd_goal": "confidentiality", "title": title,
            "evidence": [{"artifact": "a.md", "locator": "§1"}],
            **({} if level is None else {key: level})} for title, level in levels}

    severities = [("alpha", "low", "high"), ("bravo", "medium", "low"),
                  ("charlie", "critical", "low"), ("delta", "critical", "medium"),
                  ("echo", None, "high"), ("foxtrot", "high", None)]
    maturities = [("golf", "designed", "implemented"), ("hotel", "operationalized", "tested"),
                  ("india", "tested", "designed")]
    baseline = snapshot(leveled("conf", "severity", [(t, a) for t, a, _ in severities]),
                        leveled("conf-cap", "maturity", [(t, a) for t, a, _ in maturities]))
    candidate = snapshot(leveled("conf", "severity", [(t, z) for t, _, z in severities]),
                         leveled("conf-cap", "maturity", [(t, z) for t, _, z in maturities]))
    d = compare_pair(baseline, candidate)
    assert len(d.findings.matched) == 6 and len(d.capabilities.matched) == 3
    assert list(d.severity_shifts.items()) == [
        ("critical->medium", 1), ("critical->low", 1), ("high->unknown", 1),
        ("medium->low", 1), ("low->high", 1), ("unknown->high", 1)]
    assert list(d.maturity_shifts.items()) == [
        ("operationalized->tested", 1), ("tested->designed", 1), ("designed->implemented", 1)]
    assert d.severity_agreement_pct == 0.0


def test_no_matches_leave_agreement_undefined():
    d = compare_pair(snapshot(), snapshot())
    assert d.severity_agreement_pct is None and d.findings.matched == ()


def test_headline_overlap_counts_only_headlines_the_candidate_keeps(make_run):
    b, c = make_run("b"), make_run("c")
    report = c / "40-synthesis/report-data.yaml"
    doc = yaml.safe_load(report.read_text(encoding="utf-8"))
    doc["headline_findings"] = doc["headline_findings"][:3]
    assert [h["id"] for h in doc["headline_findings"]] == [
        "merged-4dd83f6a", "auth-dbba3dea", "avail-4e08f6d8"]
    report.write_text(yaml.safe_dump(doc, sort_keys=False), encoding="utf-8")
    d = compare_pair(load_run(b), load_run(c))      # the corpus is unchanged: all 20 match
    assert len(d.findings.matched) == 20
    assert d.headline_overlap_pct == pytest.approx(300 / 7)


def test_headline_overlap_follows_the_match_to_a_reworded_id():
    # Ids are sha8(title + first locator), so a reworded headline finding gets a new id
    # but still matches: the overlap compares the candidate id it matched, not its own id.
    def record(rid, title):
        return {"id": rid, "apd_goal": "confidentiality", "severity": "high", "title": title,
                "evidence": [{"artifact": "tech_plan.md", "locator": "§4.2 paragraph 3"}]}

    baseline = snapshot(
        {"conf-aaaa1111": record(
            "conf-aaaa1111", "PHI fields in Kafka claim-events topic lack envelope encryption")},
        headlines=(frozenset({"conf-aaaa1111"}),),
    )
    candidate = snapshot(
        {"conf-bbbb2222": record(
            "conf-bbbb2222",
            "PHI fields in the Kafka claim-events topic lack envelope encryption at rest")},
        headlines=(frozenset({"conf-bbbb2222"}),),
    )
    d = compare_pair(baseline, candidate)
    assert [(m.baseline_id, m.candidate_id) for m in d.findings.matched] == [
        ("conf-aaaa1111", "conf-bbbb2222")]
    assert d.headline_overlap_pct == 100.0


def test_headline_overlap_undefined_without_headlines(make_run):
    b, c = make_run("b"), make_run("c")
    (c / "40-synthesis/report-data.yaml").unlink()
    assert compare_pair(load_run(b), load_run(c)).headline_overlap_pct is None
    assert compare_pair(load_run(c), load_run(b)).headline_overlap_pct is None   # baseline side
    some = (frozenset({"conf-1"}),)
    for empty in ((), None):
        assert compare_pair(
            snapshot(headlines=empty), snapshot(headlines=some)).headline_overlap_pct is None
        assert compare_pair(
            snapshot(headlines=some), snapshot(headlines=empty)).headline_overlap_pct is None
    assert compare_pair(snapshot(headlines=()), snapshot(headlines=())).headline_overlap_pct is None


# Whole-branch review: one shared member keeps a headline, and one shared pointer excuses.


def test_headline_overlap_keeps_a_merged_headline_that_lost_one_member(make_run, edit):
    # merged-4dd83f6a expands to {immut-e09e4945, nonrep-62124087} in both runs; the
    # candidate's corpus no longer has nonrep-62124087, so only immut-e09e4945 maps across.
    b, c = make_run("b"), make_run("c")
    edit.drop(c, "nonrep-62124087")
    assert compare_pair(load_run(b), load_run(c)).headline_overlap_pct == 100.0


def test_headline_overlap_keeps_a_headline_the_candidate_narrowed():
    def record(rid, title, artifact):
        return {"id": rid, "apd_goal": "ephemeral", "severity": "high", "title": title,
                "evidence": [{"artifact": artifact, "locator": "#x"}]}

    findings = {"a": record("a", "Refresh tokens never rotate", "a.md"),
                "b": record("b", "Session cookie lacks secure flag", "b.md")}
    d = compare_pair(snapshot(findings, headlines=(frozenset({"a", "b"}),)),
                     snapshot(findings, headlines=(frozenset({"a"}),)))
    assert d.headline_overlap_pct == 100.0


def test_a_lost_finding_whose_second_pointer_is_shared_is_reassigned():
    lost = {"id": "conf-1", "apd_goal": "confidentiality", "severity": "high",
            "title": "Lost one",
            "evidence": [{"artifact": "a.md", "locator": "#1"},
                         {"artifact": "b.md", "locator": "#2"}]}
    new = {"id": "intg-2", "apd_goal": "integrity", "severity": "low",
           "title": "Something else",
           "evidence": [{"artifact": "b.md", "locator": "#2"},
                        {"artifact": "c.md", "locator": "#3"}]}
    d = compare_pair(snapshot({"conf-1": lost}), snapshot({"intg-2": new}))
    assert [(x.id, x.excuse) for x in d.lost_critical_high] == [
        ("conf-1", "evidence_reassigned:intg-2")]
    assert unexcused_lost(d) == 0


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
