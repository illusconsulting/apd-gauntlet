"""eval.findings_eval: the ``findings`` evaluator and ``eval label-template``."""
from __future__ import annotations

import copy
import errno
import importlib
import pathlib
import sys

import apd_gauntlet.eval as eval_pkg
import pytest
import yaml
from apd_gauntlet.cli import main
from apd_gauntlet.eval import evaluators, findings_eval
from apd_gauntlet.eval.corpus import CorpusEntry, load_labels
from apd_gauntlet.eval.evaluators import get, load_builtin_evaluators
from apd_gauntlet.eval.findings_eval import (
    GOALS,
    evaluate_findings,
    label_template,
    metrics_from_counts,
)
from apd_gauntlet.measure.runs import load_run
from apd_gauntlet.resources import read_schema
from click.testing import CliRunner


def labelled(make_run, tmp_path, **overrides):
    run = make_run("r")
    data = label_template(run, "ceb")
    for it in data["items"]:
        it["verdict"] = "true_positive"
        it.update(overrides.get(it["id"], {}))
    p = tmp_path / "labels.yaml"
    p.write_text(yaml.safe_dump(data))
    return CorpusEntry("ceb", "dev", run, None, p), load_labels(p)


def test_template_lists_every_finding_unreviewed(make_run):
    data = label_template(make_run("r"), "ceb")
    assert len(data["items"]) == 20
    assert {i["verdict"] for i in data["items"]} == {"unreviewed"}


def test_perfect_labels(make_run, tmp_path):
    m = evaluate_findings(*labelled(make_run, tmp_path)).metrics
    assert m["precision.all"] == m["recall.all"] == m["f1.all"] == m["severity_agreement"] == 1.0


def test_false_positive_label(make_run, tmp_path):
    m = evaluate_findings(
        *labelled(make_run, tmp_path, **{"conf-98a543cd": {"verdict": "false_positive"}})
    ).metrics
    assert m["precision.confidentiality"] == 0.75 and m["recall.confidentiality"] == 1.0


def test_severity_disagreement(make_run, tmp_path):
    m = evaluate_findings(
        *labelled(make_run, tmp_path, **{"avail-ce35b2ed": {"severity": "medium"}})
    ).metrics
    assert m["severity_agreement"] == 0.95


def test_unjudged_finding(make_run, tmp_path):
    entry, labels = labelled(make_run, tmp_path)
    labels.data["items"] = [i for i in labels.data["items"] if i["id"] != "dist-d697bb34"]
    m = evaluate_findings(entry, labels).metrics
    assert m["precision.distributed"] is None and m["precision_strict.distributed"] == 0.0
    assert m["precision.all"] == 1.0 and m["precision_strict.all"] == 0.95


def test_unreviewed_refused(make_run, tmp_path):
    run = make_run("r")
    p = tmp_path / "l.yaml"
    p.write_text(yaml.safe_dump(label_template(run, "ceb")))
    with pytest.raises(ValueError, match="20 unreviewed"):
        evaluate_findings(CorpusEntry("ceb", "dev", run, None, p), load_labels(p))


def test_cli_label_template(make_run, tmp_path):
    out = tmp_path / "l.yaml"
    args = ["eval", "label-template", str(make_run("r")), "--entry", "ceb", "--out", str(out)]
    assert CliRunner().invoke(main, args).exit_code == 0 and load_labels(out).kind == "findings"
    assert CliRunner().invoke(main, args).exit_code == 1


# --- beyond the plan ---------------------------------------------------------

SCOPES = (*GOALS, "all")


def write_labels(path, data):
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    return load_labels(path)


def reviewed(run, tmp_path, entry_id="ceb", **overrides):
    """A labels file for ``run`` with every item true_positive, then ``overrides`` by id."""
    data = label_template(run, entry_id)
    for it in data["items"]:
        it["verdict"] = "true_positive"
        it.update(overrides.get(it["id"], {}))
    return write_labels(tmp_path / f"{entry_id}-labels.yaml", data)


def entry_for(run, labels, entry_id="ceb"):
    return CorpusEntry(entry_id, "dev", run, None, labels.path)


def test_goals_are_the_schema_enum_in_order():
    enum = read_schema("_defs.schema.json")["$defs"]["apd_goal"]["enum"]
    assert tuple(enum) == GOALS
    assert len(GOALS) == 9
    assert GOALS[0] == "confidentiality" and GOALS[-1] == "immutability"


def test_registered_as_findings_by_load_builtin_evaluators():
    load_builtin_evaluators()
    assert get("findings") is evaluate_findings
    assert evaluators._BUILTIN_MODULES == ("apd_gauntlet.eval.findings_eval",)


def test_a_second_import_does_not_raise(monkeypatch):
    load_builtin_evaluators()
    registered = get("findings")
    monkeypatch.delitem(sys.modules, "apd_gauntlet.eval.findings_eval")
    monkeypatch.setattr(eval_pkg, "findings_eval", findings_eval)
    fresh = importlib.import_module("apd_gauntlet.eval.findings_eval")
    assert fresh is not findings_eval
    assert get("findings") is registered


def test_counts_keys_and_values_for_perfect_labels(make_run, tmp_path):
    run = make_run("r")
    labels = reviewed(run, tmp_path)
    result = evaluate_findings(entry_for(run, labels), labels)
    expected = [f"{k}.{g}" for k in ("tp", "fp", "fn", "unjudged") for g in GOALS]
    assert list(result.counts) == [*expected, "severity_agree"]
    assert sum(result.counts[f"tp.{g}"] for g in GOALS) == 20
    assert result.counts["tp.confidentiality"] == 4 and result.counts["tp.authenticity"] == 4
    assert all(result.counts[f"{k}.{g}"] == 0 for k in ("fp", "fn", "unjudged") for g in GOALS)
    assert result.counts["severity_agree"] == 20
    assert result.entry_id == "ceb" and result.notes == ()


def test_result_derives_its_metrics_from_its_counts(make_run, tmp_path):
    entry, labels = labelled(make_run, tmp_path, **{"conf-98a543cd": {"verdict": "false_positive"}})
    result = evaluate_findings(entry, labels)
    assert result.derive is metrics_from_counts
    assert result.derive(result.counts) == result.metrics


def test_metric_keys_in_order():
    m = metrics_from_counts({})
    kinds = ("precision", "precision_strict", "recall", "f1")
    expected = [f"{k}.{s}" for k in kinds for s in SCOPES]
    assert list(m) == [*expected, "severity_agreement"]
    assert set(m.values()) == {None}


def test_metrics_from_counts_values():
    m = metrics_from_counts({
        "tp.integrity": 3, "fp.integrity": 1, "fn.integrity": 1, "unjudged.integrity": 1,
        "tp.availability": 1, "fn.availability": 3, "severity_agree": 2,
    })
    assert m["precision.integrity"] == 0.75 and m["recall.integrity"] == 0.75
    assert m["precision_strict.integrity"] == 0.6 and m["f1.integrity"] == 0.75
    assert m["precision.availability"] == 1.0 and m["recall.availability"] == 0.25
    assert m["f1.availability"] == pytest.approx(0.4)
    # all: TP 4, FP 1, FN 4, unjudged 1
    assert m["precision.all"] == 0.8 and m["recall.all"] == 0.5
    assert m["precision_strict.all"] == pytest.approx(4 / 6)
    assert m["f1.all"] == pytest.approx(2 * 0.8 * 0.5 / 1.3)
    assert m["severity_agreement"] == 0.5
    assert m["precision.confidentiality"] is None and m["f1.confidentiality"] is None


def test_f1_is_zero_when_precision_and_recall_are_zero():
    m = metrics_from_counts({"fp.ephemeral": 2, "fn.ephemeral": 1})
    assert m["precision.ephemeral"] == 0.0 and m["recall.ephemeral"] == 0.0
    assert m["f1.ephemeral"] == 0.0 and m["severity_agreement"] is None


def test_f1_needs_both_precision_and_recall():
    only_fp = metrics_from_counts({"fp.resilient": 2})
    assert only_fp["precision.resilient"] == 0.0 and only_fp["recall.resilient"] is None
    assert only_fp["f1.resilient"] is None
    only_fn = metrics_from_counts({"fn.resilient": 2})
    assert only_fn["recall.resilient"] == 0.0 and only_fn["precision.resilient"] is None
    assert only_fn["f1.resilient"] is None


def test_metrics_ignore_keys_outside_the_goals():
    m = metrics_from_counts({"tp.integrity": 1, "tp.other": 5, "fp.all": 5, "x": 9})
    assert m["precision.all"] == 1.0 and m["recall.all"] == 1.0


def test_summed_counts_give_corpus_metrics(make_run, tmp_path):
    entry, labels = labelled(make_run, tmp_path, **{"conf-98a543cd": {"verdict": "false_positive"}})
    one = evaluate_findings(entry, labels).counts
    summed = {k: 2 * v for k, v in one.items()}
    assert metrics_from_counts(summed) == metrics_from_counts(one)


def test_missing_finding_is_a_false_negative(make_run, edit, tmp_path):
    run = make_run("r")
    labels = reviewed(run, tmp_path)
    edit.drop(run, "conf-98a543cd")
    result = evaluate_findings(entry_for(run, labels), labels)
    assert result.counts["fn.confidentiality"] == 1 and result.counts["tp.confidentiality"] == 3
    m = result.metrics
    assert m["recall.confidentiality"] == 0.75 and m["precision.confidentiality"] == 1.0
    assert m["recall.all"] == 0.95 and m["severity_agreement"] == 1.0


def test_added_gold_item_the_run_missed(make_run, tmp_path):
    run = make_run("r")
    data = label_template(run, "ceb")
    for it in data["items"]:
        it["verdict"] = "true_positive"
    data["items"].append({
        "verdict": "true_positive", "apd_goal": "integrity", "severity": "high",
        "title": "Claim adjudication results are not signed",
        "evidence": [{"artifact": "tech_plan.md", "locator": "§9 paragraph 1"}],
    })
    labels = write_labels(tmp_path / "l.yaml", data)
    result = evaluate_findings(entry_for(run, labels), labels)
    assert result.counts["fn.integrity"] == 1 and result.metrics["recall.integrity"] == 0.5


def test_items_without_ids_match_by_content(make_run, tmp_path):
    run = make_run("r")
    data = label_template(run, "ceb")
    for it in data["items"]:
        it["verdict"] = "true_positive"
        del it["id"]
    labels = write_labels(tmp_path / "l.yaml", data)
    m = evaluate_findings(entry_for(run, labels), labels).metrics
    assert m["precision.all"] == m["recall.all"] == m["severity_agreement"] == 1.0


def test_wrong_goal_label_is_a_miss_and_leaves_the_finding_unjudged(make_run, tmp_path):
    entry, labels = labelled(make_run, tmp_path, **{"intg-42a3ebbd": {"apd_goal": "authenticity"}})
    result = evaluate_findings(entry, labels)
    assert result.counts["fn.authenticity"] == 1 and result.counts["unjudged.integrity"] == 1
    assert result.counts["tp.integrity"] == 0
    assert result.metrics["precision.integrity"] is None
    assert result.metrics["precision_strict.integrity"] == 0.0


def test_a_label_copied_from_a_finding_prefers_that_finding(make_run, edit, tmp_path):
    run = make_run("r")
    original = load_run(run).findings["conf-98a543cd"]
    twin = {**copy.deepcopy(original), "id": "conf-00000000", "severity": "low"}
    edit.add_finding(run, "10-trustworthiness/twin.findings.yaml", twin)
    labels = reviewed(run, tmp_path, **{"conf-00000000": {"verdict": "false_positive"}})
    result = evaluate_findings(entry_for(run, labels), labels)
    # Gold conf-98a543cd (high) takes the run's conf-98a543cd (high), not its twin (low),
    # though the twin's id sorts first; the false_positive label then takes the twin.
    assert result.counts["tp.confidentiality"] == 4 and result.counts["fp.confidentiality"] == 1
    assert result.counts["severity_agree"] == 20


def test_matching_uses_the_runs_asset_graph(make_run, edit, tmp_path):
    run = make_run("r")
    base = load_run(run).findings["conf-98a543cd"]
    near = {**copy.deepcopy(base), "id": "conf-aaaa0001", "severity": "low"}
    far = {**copy.deepcopy(base), "id": "conf-bbbb0002", "severity": "high"}
    for twin in (near, far):
        edit.add_finding(run, "10-trustworthiness/twins.findings.yaml", twin)
    edit.drop(run, "conf-98a543cd")
    graph_file = run / "40-synthesis/asset-graph.yaml"
    graph = yaml.safe_load(graph_file.read_text(encoding="utf-8"))
    graph["edges"].append({**graph["edges"][0], "edge_id": "edge-00000001",
                           "finding_id": "conf-aaaa0001"})
    graph_file.write_text(yaml.safe_dump(graph, sort_keys=False), encoding="utf-8")
    data = label_template(run, "ceb")
    for it in data["items"]:
        it["verdict"] = "true_positive"
    data["items"] = [i for i in data["items"] if i["id"] not in ("conf-aaaa0001", "conf-bbbb0002")]
    data["items"].append({k: v for k, v in base.items() if k in ("apd_goal", "title")} | {
        "verdict": "true_positive", "severity": "high",
        "evidence": [{"artifact": "tech_plan.md", "locator": "§3 paragraph 4"}],
    })
    labels = write_labels(tmp_path / "l.yaml", data)
    result = evaluate_findings(entry_for(run, labels), labels)
    # The edge gives conf-aaaa0001 a graph: asset key the label lacks, so conf-bbbb0002
    # shares more of the label's assets and is taken although its id sorts second.
    assert result.counts["tp.confidentiality"] == 4 and result.counts["severity_agree"] == 20
    assert result.counts["unjudged.confidentiality"] == 1


def test_false_positive_matching_uses_the_runs_asset_graph(make_run, edit, tmp_path):
    run = make_run("r")
    base = load_run(run).findings["conf-98a543cd"]
    near = {**copy.deepcopy(base), "id": "conf-aaaa0001",
            "title": "Envelope keys never rotate offline"}
    far = {**copy.deepcopy(base), "id": "conf-bbbb0002",
           "title": "Envelope keys never rotate quarterly"}
    for twin in (near, far):
        edit.add_finding(run, "10-trustworthiness/twins.findings.yaml", twin)
    edit.drop(run, "conf-98a543cd")
    graph_file = run / "40-synthesis/asset-graph.yaml"
    graph = yaml.safe_load(graph_file.read_text(encoding="utf-8"))
    graph["edges"].append({**graph["edges"][0], "edge_id": "edge-00000001",
                           "finding_id": "conf-aaaa0001"})
    graph_file.write_text(yaml.safe_dump(graph, sort_keys=False), encoding="utf-8")
    data = label_template(run, "ceb")
    for it in data["items"]:
        it["verdict"] = "true_positive"
    data["items"] = [i for i in data["items"] if i["id"] not in ("conf-aaaa0001", "conf-bbbb0002")]
    for title in ("Envelope keys never rotate", "Envelope keys offline plaintext"):
        data["items"].append({
            "verdict": "false_positive", "apd_goal": "confidentiality", "severity": "high",
            "title": title, "evidence": [{"artifact": "tech_plan.md", "locator": "§3 paragraph 4"}],
        })
    labels = write_labels(tmp_path / "l.yaml", data)
    result = evaluate_findings(entry_for(run, labels), labels)
    # The first label's title matches both twins equally (0.8); the second matches only
    # conf-aaaa0001 (0.5). The edge gives conf-aaaa0001 a graph: asset key the labels
    # lack, so the first label takes conf-bbbb0002 although its id sorts second, and the
    # second label is left conf-aaaa0001.
    assert result.counts["fp.confidentiality"] == 2
    assert result.counts["unjudged.confidentiality"] == 0 and result.notes == ()


def test_false_positive_labels_count_under_the_run_goal(make_run, tmp_path):
    overrides = {rid: {"verdict": "false_positive"} for rid in ("auth-8d386c2f", "nonrep-62124087")}
    entry, labels = labelled(make_run, tmp_path, **overrides)
    c = evaluate_findings(entry, labels).counts
    assert c["fp.authenticity"] == 1 and c["fp.non_repudiation"] == 1
    assert c["tp.authenticity"] == 3 and c["tp.non_repudiation"] == 2


def test_a_finding_judged_false_positive_is_not_unjudged(make_run, tmp_path):
    entry, labels = labelled(make_run, tmp_path, **{"conf-98a543cd": {"verdict": "false_positive"}})
    result = evaluate_findings(entry, labels)
    c = result.counts
    assert c["fp.confidentiality"] == 1 and c["unjudged.confidentiality"] == 0
    assert sum(c[f"unjudged.{g}"] for g in GOALS) == 0
    assert result.metrics["precision_strict.confidentiality"] == 0.75
    assert result.metrics["precision_strict.all"] == 0.95


def test_unmatched_false_positive_label_is_a_note(make_run, edit, tmp_path):
    run = make_run("r")
    labels = reviewed(run, tmp_path, **{"conf-98a543cd": {"verdict": "false_positive"}})
    edit.drop(run, "conf-98a543cd")
    result = evaluate_findings(entry_for(run, labels), labels)
    assert result.counts["fp.confidentiality"] == 0
    assert result.metrics["precision.confidentiality"] == 1.0
    assert result.notes == (
        "1 false_positive label matches no run finding left after the true positives: "
        "conf-98a543cd",
    )


def test_unjudged_counts_under_the_run_goal(make_run, tmp_path):
    entry, labels = labelled(make_run, tmp_path)
    drop = {"dist-d697bb34", "ephem-bff0e958", "ephem-eb51a236"}
    labels.data["items"] = [i for i in labels.data["items"] if i["id"] not in drop]
    c = evaluate_findings(entry, labels).counts
    assert c["unjudged.distributed"] == 1 and c["unjudged.ephemeral"] == 2
    assert sum(c[f"unjudged.{g}"] for g in GOALS) == 3


def test_entry_without_run_refused(make_run, tmp_path):
    _, labels = labelled(make_run, tmp_path)
    entry = CorpusEntry("ceb", "heldout", None, None, labels.path)
    with pytest.raises(ValueError, match="entry 'ceb' has no run directory"):
        evaluate_findings(entry, labels)


def test_decision_labels_refused(make_run, tmp_path):
    run = make_run("r")
    labels = write_labels(tmp_path / "d.yaml", {
        "schema_version": 1, "kind": "decisions", "set": "dev", "task": "dedup",
        "records": [{"path": "r.yaml", "items": [{"ref": "x", "gold": True}]}],
    })
    with pytest.raises(ValueError, match="labels of kind 'decisions'"):
        evaluate_findings(CorpusEntry("ceb", "dev", run, None, labels.path), labels)


def test_labels_for_another_entry_refused(make_run, tmp_path):
    run = make_run("r")
    labels = reviewed(run, tmp_path, entry_id="other")
    with pytest.raises(ValueError, match="labels are for entry 'other', not 'ceb'"):
        evaluate_findings(CorpusEntry("ceb", "dev", run, None, labels.path), labels)


def test_one_unreviewed_item_refused(make_run, tmp_path):
    entry, labels = labelled(make_run, tmp_path, **{"conf-98a543cd": {"verdict": "unreviewed"}})
    with pytest.raises(ValueError, match=r"labels\.yaml: 1 unreviewed item;"):
        evaluate_findings(entry, labels)


def test_duplicate_label_keys_refused(make_run, tmp_path):
    entry, labels = labelled(make_run, tmp_path)
    items = labels.data["items"]
    items[5]["id"] = items[2]["id"]
    message = r"duplicate label key '.+' \(\$\.items\[2\] and \$\.items\[5\]\)"
    with pytest.raises(ValueError, match=message):
        evaluate_findings(entry, labels)


def test_an_id_equal_to_another_items_index_key_refused(make_run, tmp_path):
    entry, labels = labelled(make_run, tmp_path)
    items = labels.data["items"]
    del items[0]["id"]
    items[3]["id"] = "label-0"
    with pytest.raises(ValueError, match=r"duplicate label key 'label-0'"):
        evaluate_findings(entry, labels)


def test_not_a_run_directory_refused(make_run, tmp_path):
    entry, labels = labelled(make_run, tmp_path)
    (entry.run_dir / ".apd-run.yaml").unlink()
    with pytest.raises(ValueError, match=r"is not a run directory \(no \.apd-run\.yaml\)"):
        evaluate_findings(entry, labels)


def test_missing_run_directory_refused(make_run, tmp_path):
    _, labels = labelled(make_run, tmp_path)
    entry = CorpusEntry("ceb", "dev", tmp_path / "gone", None, labels.path)
    with pytest.raises(ValueError, match="gone is not a run directory"):
        evaluate_findings(entry, labels)


def test_run_that_fails_to_load_refused(make_run, tmp_path):
    entry, labels = labelled(make_run, tmp_path)
    bad = entry.run_dir / "10-trustworthiness/broken.findings.yaml"
    bad.write_text("finding: [unclosed\n")
    with pytest.raises(ValueError, match=r"cannot load run .*broken\.findings\.yaml"):
        evaluate_findings(entry, labels)


def test_os_error_while_loading_is_a_value_error(make_run, tmp_path, monkeypatch):
    entry, labels = labelled(make_run, tmp_path)

    def denied(path):
        raise PermissionError(13, "Permission denied", str(path / "40-synthesis"))

    monkeypatch.setattr(findings_eval, "load_run", denied)
    with pytest.raises(ValueError, match=r"40-synthesis: cannot read: Permission denied"):
        evaluate_findings(entry, labels)


def test_run_finding_outside_the_nine_goals_refused(make_run, edit, tmp_path):
    entry, labels = labelled(make_run, tmp_path)
    edit.finding(entry.run_dir, "resil-0173b90b", apd_goal="resilience")
    with pytest.raises(ValueError, match=r"resil-0173b90b \('resilience'\)"):
        evaluate_findings(entry, labels)


def test_template_document(make_run):
    data = label_template(make_run("r"), "ceb")
    assert list(data) == ["schema_version", "kind", "entry", "items"]
    assert (data["schema_version"], data["kind"], data["entry"]) == (1, "findings", "ceb")
    ids = [i["id"] for i in data["items"]]
    assert ids == sorted(ids) and {"apath-d066312b", "tmeval-6e33edd4"} <= set(ids)
    first = data["items"][0]
    assert first == {
        "id": "apath-d066312b",
        "verdict": "unreviewed",
        "apd_goal": "authenticity",
        "severity": "low",
        "title": "Suppressed risk attack paths collapsed into one aggregate",
        "evidence": [{"artifact": "40-synthesis/attack-paths.yaml", "locator": "paths"}],
    }


def test_template_copies_every_evidence_pointer_without_excerpts(make_run, edit):
    run = make_run("r")
    edit.finding(run, "conf-98a543cd", evidence=[
        {"artifact": "tech_plan.md", "locator": "§3 paragraph 4", "excerpt": "DEKs rotate"},
        {"artifact": "iac/kms.tf", "locator": "resource aws_kms_key"},
    ])
    (item,) = (i for i in label_template(run, "ceb")["items"] if i["id"] == "conf-98a543cd")
    assert item["evidence"] == [
        {"artifact": "tech_plan.md", "locator": "§3 paragraph 4"},
        {"artifact": "iac/kms.tf", "locator": "resource aws_kms_key"},
    ]


def test_template_is_deterministic(make_run):
    run = make_run("r")
    assert label_template(run, "ceb") == label_template(run, "ceb")


@pytest.mark.parametrize("entry_id", ["", "Ceb", "-ceb", "c_b", "a/b", "ceb\n"])
def test_template_refuses_an_invalid_entry_id(make_run, entry_id):
    with pytest.raises(ValueError, match="entry id"):
        label_template(make_run("r"), entry_id)


def test_template_refuses_a_directory_that_is_not_a_run(tmp_path):
    with pytest.raises(ValueError, match="is not a run directory"):
        label_template(tmp_path, "ceb")


def test_template_refuses_a_finding_that_cannot_be_a_label(make_run, edit):
    run = make_run("r")
    edit.finding(run, "conf-98a543cd", severity="info")
    edit.finding(run, "avail-ce35b2ed", evidence=[])
    with pytest.raises(ValueError) as exc:
        label_template(run, "ceb")
    message = str(exc.value)
    assert "cannot be labelled" in message
    assert "finding avail-ce35b2ed: $.items[4].evidence: [] should be non-empty" in message
    assert "finding conf-98a543cd: $.items[6].severity: 'info' is not one of" in message
    assert message.index("avail-ce35b2ed") < message.index("conf-98a543cd")


@pytest.mark.parametrize(("evidence", "problem"), [
    (
        ["tech_plan.md §3 paragraph 4", {"artifact": "iac/kms.tf", "locator": "resource k"}],
        "$.items[6].evidence[0]: 'tech_plan.md §3 paragraph 4' is not of type 'object'",
    ),
    ("tech_plan.md §3 paragraph 4", "$.items[6].evidence: 'tech_plan.md §3 paragraph 4' "
                                    "is not of type 'array'"),
])
def test_template_refuses_evidence_that_is_not_a_pointer(make_run, edit, evidence, problem):
    run = make_run("r")
    edit.finding(run, "conf-98a543cd", evidence=evidence)
    with pytest.raises(ValueError) as exc:
        label_template(run, "ceb")
    assert f"finding conf-98a543cd: {problem}" in str(exc.value)


def test_template_round_trips_through_load_labels(make_run, tmp_path):
    data = label_template(make_run("r"), "ceb")
    labels = write_labels(tmp_path / "t.yaml", data)
    assert labels.kind == "findings" and labels.data == data


def test_cli_writes_the_template(make_run, tmp_path):
    run = make_run("r")
    out = tmp_path / "eval/local/findings/labels/ceb.yaml"
    args = ["eval", "label-template", str(run), "--entry", "ceb", "--out", str(out)]
    r = CliRunner().invoke(main, args)
    assert r.exit_code == 0, r.output
    assert f"wrote {out}: 20 items to review" in r.output
    text = out.read_text(encoding="utf-8")
    assert text.startswith("# Findings labels for corpus entry ceb.")
    assert str(run) not in text
    assert load_labels(out).data == label_template(run, "ceb")


def test_cli_never_overwrites(make_run, tmp_path):
    out = tmp_path / "l.yaml"
    out.write_text("keep me\n")
    args = ["eval", "label-template", str(make_run("r")), "--entry", "ceb", "--out", str(out)]
    r = CliRunner().invoke(main, args)
    assert r.exit_code == 1 and f"{out} exists; not overwritten" in r.output
    assert out.read_text() == "keep me\n"


def test_cli_never_writes_through_a_link(make_run, tmp_path):
    target = tmp_path / "target.yaml"
    out = tmp_path / "l.yaml"
    out.symlink_to(target)
    args = ["eval", "label-template", str(make_run("r")), "--entry", "ceb", "--out", str(out)]
    assert CliRunner().invoke(main, args).exit_code == 1
    assert not target.exists()


def test_cli_unwritable_parent_exits_1(make_run, tmp_path):
    blocker = tmp_path / "file"
    blocker.write_text("")
    out = blocker / "l.yaml"
    args = ["eval", "label-template", str(make_run("r")), "--entry", "ceb", "--out", str(out)]
    r = CliRunner().invoke(main, args)
    assert r.exit_code == 1 and "cannot write" in r.output
    assert "Traceback" not in r.output


def test_cli_removes_a_partly_written_file(make_run, tmp_path, monkeypatch):
    real_open = pathlib.Path.open

    class Full:
        """A file handle that writes a few characters, then runs out of space."""

        def __init__(self, handle):
            self.handle = handle

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            self.handle.close()

        def write(self, text):
            self.handle.write(text[:20])
            self.handle.flush()
            raise OSError(errno.ENOSPC, "No space left on device")

    def open_(self, mode="r", *args, **kwargs):
        handle = real_open(self, mode, *args, **kwargs)
        return Full(handle) if mode == "x" else handle

    out = tmp_path / "l.yaml"
    args = ["eval", "label-template", str(make_run("r")), "--entry", "ceb", "--out", str(out)]
    monkeypatch.setattr(pathlib.Path, "open", open_)
    r = CliRunner().invoke(main, args)
    assert r.exit_code == 1 and f"{out}: cannot write: No space left on device" in r.output
    assert not out.exists()


def test_cli_invalid_entry_exits_2(make_run, tmp_path):
    out = tmp_path / "l.yaml"
    args = ["eval", "label-template", str(make_run("r")), "--entry", "Bad Id", "--out", str(out)]
    r = CliRunner().invoke(main, args)
    assert r.exit_code == 2 and "entry id 'Bad Id'" in r.output
    assert not out.exists()


def test_cli_not_a_run_exits_2(tmp_path):
    out = tmp_path / "l.yaml"
    args = ["eval", "label-template", str(tmp_path), "--entry", "ceb", "--out", str(out)]
    r = CliRunner().invoke(main, args)
    assert r.exit_code == 2 and "is not a run directory" in r.output
    assert not out.exists()


def test_cli_finding_that_cannot_be_a_label_exits_2(make_run, edit, tmp_path):
    run = make_run("r")
    edit.finding(run, "conf-98a543cd", severity="info")
    out = tmp_path / "l.yaml"
    args = ["eval", "label-template", str(run), "--entry", "ceb", "--out", str(out)]
    r = CliRunner().invoke(main, args)
    assert r.exit_code == 2 and "finding conf-98a543cd" in r.output
    assert not out.exists()


def test_cli_eval_group_lists_label_template():
    r = CliRunner().invoke(main, ["eval", "--help"])
    assert r.exit_code == 0 and "label-template" in r.output
