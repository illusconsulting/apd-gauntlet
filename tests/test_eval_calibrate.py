"""eval.calibrate: value specs, threshold choice, labelled pairs and the thresholds writer."""
from __future__ import annotations

import math
import pathlib
import shutil

import pytest
import yaml
from apd_gauntlet import resources
from apd_gauntlet.eval import calibrate
from apd_gauntlet.eval.calibrate import (
    VALUE_SPECS,
    Calibration,
    CalibrationError,
    ValueSpec,
    choose_threshold,
    labelled_pairs,
    record_model,
    register_value,
    write_threshold,
)
from apd_gauntlet.eval.corpus import Labels, load_labels

FIXTURE = pathlib.Path(__file__).parent / "fixtures/eval/finding-qa.record.yaml"
RECORD_REL = "40-synthesis/decisions/finding-qa.10-trustworthiness.yaml"
GOLD = [True, True, True, False, True, False, False, False, True]

PAIRS = [
    (0.95, True), (0.9, True), (0.85, True), (0.8, False),
    (0.7, True), (0.6, False), (0.4, False), (0.2, False),
]


def test_max_recall_subject_to_precision():
    c = choose_threshold(PAIRS, direction="above", target_precision=0.75, min_support=1)
    assert (c.threshold, c.precision, c.recall, c.n, c.feasible) == (0.65, 0.8, 1.0, 8, True)


def test_higher_target_moves_cut_up():
    c = choose_threshold(PAIRS, direction="above", target_precision=0.9, min_support=1)
    assert c.threshold == 0.825


def test_below_mirrors_above():
    c = choose_threshold(
        [(1 - v, g) for v, g in PAIRS], direction="below", target_precision=0.75, min_support=1
    )
    assert c.threshold == 0.35 and c.recall == 1.0


def test_min_support_makes_it_infeasible():
    c = choose_threshold(PAIRS, direction="above", target_precision=0.75, min_support=6)
    assert not c.feasible and c.threshold is None and c.best_precision == pytest.approx(4 / 6)


def test_no_positive_labels_raise():
    with pytest.raises(CalibrationError):
        choose_threshold([(0.1, False), (0.2, False)], direction="above", target_precision=0.9)


def test_lens_drift_value_uses_finding_goal():
    item = {"answers": {"goal": {
        "type": "choice", "probabilities": {"confidentiality": 0.2, "authenticity": 0.8},
    }}}
    assert VALUE_SPECS["finding-qa.lens_drift"].value(item, {"apd_goal": "confidentiality"}) == 0.2


# --- beyond the plan's tests -------------------------------------------------------------


def _run(tmp_path, name="run", record=FIXTURE):
    """A run directory holding ``record`` at the finding-qa record path; returns the record."""
    target = tmp_path / name / RECORD_REL
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(record, target)
    return target


def _labels(path, records, task="finding-qa.unsupported", set_name="dev"):
    """A decisions labels file at ``path``; ``records`` is a list of (path, [(ref, gold)])."""
    doc = {
        "schema_version": 1, "kind": "decisions", "set": set_name, "task": task,
        "records": [
            {"path": str(p), "items": [{"ref": r, "gold": g} for r, g in items]}
            for p, items in records
        ],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(doc, sort_keys=False))
    return load_labels(path)


def _all_items(gold=GOLD):
    return [(f"conf-0000000{k}", g) for k, g in enumerate(gold, start=1)]


def _record_doc():
    return yaml.safe_load(FIXTURE.read_text())


def _write_record(tmp_path, doc, name="run"):
    target = tmp_path / name / RECORD_REL
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(yaml.safe_dump(doc, sort_keys=False))
    return target


def _findings(run, goals):
    """Write ``<run>/10-trustworthiness/x.findings.yaml`` with ``{id: apd_goal}``."""
    f = run / "10-trustworthiness/x.findings.yaml"
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(yaml.safe_dump(
        {"finding": [{"id": rid, "apd_goal": goal} for rid, goal in goals.items()]}
    ))


# choose_threshold


def test_best_precision_is_the_highest_supported_precision_when_feasible():
    c = choose_threshold(PAIRS, direction="above", target_precision=0.75, min_support=1)
    assert c.best_precision == 1.0


def test_infeasible_has_no_precision_or_recall():
    c = choose_threshold(PAIRS, direction="above", target_precision=0.75, min_support=6)
    assert (c.precision, c.recall, c.n) == (None, None, 8)


def test_infeasible_without_enough_support_has_no_best_precision():
    c = choose_threshold(PAIRS, direction="above", target_precision=0.75, min_support=8)
    assert not c.feasible and c.best_precision is None


def test_target_unreached_reports_the_best_precision():
    c = choose_threshold(
        [(0.9, True), (0.8, False), (0.7, True), (0.6, False)],
        direction="above", target_precision=0.99, min_support=2,
    )
    assert not c.feasible and c.best_precision == pytest.approx(2 / 3)


def test_equal_recall_takes_the_higher_precision():
    c = choose_threshold(
        [(0.9, True), (0.8, False), (0.1, False)],
        direction="above", target_precision=0.5, min_support=1,
    )
    assert (c.threshold, c.precision, c.recall) == (0.85, 1.0, 1.0)


def test_precision_equal_to_the_target_is_feasible():
    c = choose_threshold(PAIRS, direction="above", target_precision=0.8, min_support=5)
    assert (c.threshold, c.precision, c.feasible) == (0.65, 0.8, True)


def test_support_counts_predicted_positives():
    c = choose_threshold(PAIRS, direction="above", target_precision=0.75, min_support=5)
    assert (c.threshold, c.feasible) == (0.65, True)


def test_a_cut_whose_rounding_reaches_a_neighbour_is_kept_unrounded():
    lo, hi = 0.1234564, 0.1234566
    c = choose_threshold([(hi, True), (lo, False)], direction="above", target_precision=0.9,
                         min_support=1)
    assert c.threshold is not None and lo < c.threshold < hi
    assert c.threshold != round(c.threshold, 6)


def test_adjacent_floats_give_no_cut():
    lo = 1.0
    hi = math.nextafter(lo, 2.0)
    c = choose_threshold([(hi, True), (lo, False)], direction="above", target_precision=0.5,
                         min_support=1)
    assert not c.feasible and c.best_precision is None


def test_one_distinct_value_gives_no_cut():
    c = choose_threshold([(0.5, True), (0.5, False)], direction="above", target_precision=0.5,
                         min_support=1)
    assert not c.feasible and c.threshold is None and c.n == 2


def test_no_labelled_value_sits_on_the_cut():
    c = choose_threshold(PAIRS, direction="above", target_precision=0.75, min_support=1)
    assert all(v != c.threshold for v, _ in PAIRS)
    strict = sum(1 for v, _ in PAIRS if v > c.threshold)
    inclusive = sum(1 for v, _ in PAIRS if v >= c.threshold)
    assert strict == inclusive == 5


def test_empty_pairs_raise():
    with pytest.raises(CalibrationError, match="no gold positive"):
        choose_threshold([], direction="above", target_precision=0.9)


def test_default_min_support_is_ten():
    pairs = [(k / 100, k >= 50) for k in range(100)]
    c = choose_threshold(pairs, direction="above", target_precision=0.98)
    assert (c.threshold, c.precision, c.recall, c.n) == (0.495, 1.0, 1.0, 100)
    sparse = choose_threshold(pairs[:59], direction="above", target_precision=0.98)
    assert not sparse.feasible and sparse.best_precision == 0.9  # 9 of the 10 above 0.485


@pytest.mark.parametrize("kwargs, match", [
    ({"direction": "sideways"}, "direction"),
    ({"target_precision": 0.0}, "target_precision"),
    ({"target_precision": 1.5}, "target_precision"),
    ({"target_precision": math.nan}, "target_precision"),
    ({"min_support": 0}, "min_support"),
])
def test_bad_arguments_raise(kwargs, match):
    args = {"direction": "above", "target_precision": 0.75, "min_support": 1, **kwargs}
    with pytest.raises(ValueError, match=match):
        choose_threshold(PAIRS, **args)


@pytest.mark.parametrize("bad", [math.nan, math.inf, -math.inf])
def test_non_finite_values_raise(bad):
    with pytest.raises(ValueError, match="finite"):
        choose_threshold([*PAIRS, (bad, True)], direction="above", target_precision=0.75)


def test_target_precision_of_one_is_allowed():
    c = choose_threshold(PAIRS, direction="above", target_precision=1.0, min_support=1)
    assert (c.threshold, c.precision, c.recall) == (0.825, 1.0, 0.75)


# value specs


def test_builtin_specs():
    assert {"finding-qa.unsupported", "finding-qa.lens_drift"} <= set(VALUE_SPECS)
    for key in ("finding-qa.unsupported", "finding-qa.lens_drift"):
        assert VALUE_SPECS[key].task == "finding-qa"
        assert VALUE_SPECS[key].direction == "below"


def test_unsupported_value_reads_the_excerpt_answer():
    item = {"answers": {"excerpt_supports_claim": {"type": "noul", "p": 0.25}}}
    assert VALUE_SPECS["finding-qa.unsupported"].value(item, None) == 0.25


@pytest.mark.parametrize("item", [
    {},
    {"answers": None},
    {"answers": {"goal": {"type": "choice"}}},
    {"answers": {"excerpt_supports_claim": "0.2"}},
    {"answers": {"excerpt_supports_claim": {"type": "noul"}}},
    {"answers": {"excerpt_supports_claim": {"type": "noul", "p": "0.2"}}},
    {"answers": {"excerpt_supports_claim": {"type": "noul", "p": True}}},
    {"answers": {"excerpt_supports_claim": {"type": "noul", "p": math.nan}}},
])
def test_unsupported_value_is_none_without_a_probability(item):
    assert VALUE_SPECS["finding-qa.unsupported"].value(item, None) is None


@pytest.mark.parametrize("item, finding", [
    ({"answers": {"goal": {"probabilities": {"confidentiality": 0.2}}}}, None),
    ({"answers": {"goal": {"probabilities": {"confidentiality": 0.2}}}}, {}),
    ({"answers": {"goal": {"probabilities": {"confidentiality": 0.2}}}}, {"apd_goal": 7}),
    ({"answers": {"goal": {"probabilities": {"authenticity": 0.2}}}},
     {"apd_goal": "confidentiality"}),
    ({"answers": {"goal": {"probabilities": [0.2]}}}, {"apd_goal": "confidentiality"}),
    ({"answers": {}}, {"apd_goal": "confidentiality"}),
])
def test_lens_drift_value_is_none_without_the_goal_probability(item, finding):
    assert VALUE_SPECS["finding-qa.lens_drift"].value(item, finding) is None


def test_integer_probabilities_are_floats():
    item = {"answers": {"excerpt_supports_claim": {"type": "noul", "p": 1}}}
    value = VALUE_SPECS["finding-qa.unsupported"].value(item, None)
    assert value == 1.0 and isinstance(value, float)


def test_register_value_adds_a_spec():
    spec = ValueSpec("demo-task", "above", lambda item, _finding: item.get("score"))
    register_value("demo-task", spec)
    try:
        assert VALUE_SPECS["demo-task"] is spec
    finally:
        del VALUE_SPECS["demo-task"]


@pytest.mark.parametrize("key, spec, match", [
    ("finding-qa.unsupported", ValueSpec("finding-qa", "below", lambda i, f: None), "already"),
    ("Bad Key", ValueSpec("Bad Key", "below", lambda i, f: None), "does not match"),
    ("a.b.c", ValueSpec("a", "below", lambda i, f: None), "does not match"),
    ("other.flag", ValueSpec("finding-qa", "below", lambda i, f: None), "task"),
    ("demo", ValueSpec("demo", "sideways", lambda i, f: None), "direction"),
])
def test_register_value_refuses(key, spec, match):
    before = dict(VALUE_SPECS)
    with pytest.raises(ValueError, match=match):
        register_value(key, spec)
    assert before == VALUE_SPECS


# labelled_pairs


def test_labelled_pairs_from_the_fixture(tmp_path):
    record = _run(tmp_path)
    labels = _labels(tmp_path / "labels.yaml", [(record, _all_items())])
    pairs, skipped = labelled_pairs(labels, "finding-qa.unsupported")
    assert pairs == [
        (0.05, True), (0.1, True), (0.15, True), (0.2, False),
        (0.3, True), (0.4, False), (0.6, False), (0.8, False),
    ]
    assert skipped == 1


def test_record_paths_resolve_relative_to_the_labels_file(tmp_path):
    _run(tmp_path)
    labels = _labels(
        tmp_path / "eval/local/decide/finding-qa.unsupported.labels.yaml",
        [(pathlib.Path("../../..") / "run" / RECORD_REL, _all_items())],
    )
    pairs, skipped = labelled_pairs(labels, "finding-qa.unsupported")
    assert (len(pairs), skipped) == (8, 1)


def test_only_labelled_items_count(tmp_path):
    record = _run(tmp_path)
    labels = _labels(tmp_path / "l.yaml", [(record, [("conf-00000002", True),
                                                     ("conf-00000007", False)])])
    assert labelled_pairs(labels, "finding-qa.unsupported") == ([(0.1, True), (0.6, False)], 0)


def test_pairs_follow_label_order_across_records(tmp_path):
    a = _run(tmp_path, "a")
    b = _run(tmp_path, "b")
    labels = _labels(tmp_path / "l.yaml", [(b, [("conf-00000008", False)]),
                                           (a, [("conf-00000001", True)])])
    assert labelled_pairs(labels, "finding-qa.unsupported")[0] == [(0.8, False), (0.05, True)]


def test_unknown_ref_names_it(tmp_path):
    record = _run(tmp_path)
    labels = _labels(tmp_path / "l.yaml", [(record, [("conf-0000000a", True)])])
    where = r"\$\.records\[0\]\.items\[0\]: ref 'conf-0000000a'"
    with pytest.raises(CalibrationError, match=where):
        labelled_pairs(labels, "finding-qa.unsupported")


def test_record_of_another_task_refused(tmp_path):
    doc = _record_doc()
    doc["task"] = "cluster-pairs"
    record = _write_record(tmp_path, doc)
    labels = _labels(tmp_path / "l.yaml", [(record, _all_items())])
    with pytest.raises(CalibrationError, match="cluster-pairs record, not finding-qa"):
        labelled_pairs(labels, "finding-qa.unsupported")


def test_duplicate_label_refused(tmp_path):
    record = _run(tmp_path)
    labels = _labels(tmp_path / "l.yaml", [(record, [("conf-00000001", True)]),
                                           (record, [("conf-00000001", False)])])
    with pytest.raises(CalibrationError, match=r"labelled twice.*\$\.records\[0\]\.items\[0\]"):
        labelled_pairs(labels, "finding-qa.unsupported")


def test_the_same_record_may_be_listed_twice_with_other_refs(tmp_path):
    record = _run(tmp_path)
    labels = _labels(tmp_path / "l.yaml", [(record, [("conf-00000001", True)]),
                                           (record, [("conf-00000002", False)])])
    assert labelled_pairs(labels, "finding-qa.unsupported") == ([(0.05, True), (0.1, False)], 0)


def test_duplicate_ref_in_a_record_refused(tmp_path):
    doc = _record_doc()
    doc["items"].append(dict(doc["items"][0]))
    record = _write_record(tmp_path, doc)
    labels = _labels(tmp_path / "l.yaml", [(record, [("conf-00000002", True)])])
    with pytest.raises(CalibrationError, match="conf-00000001.*twice"):
        labelled_pairs(labels, "finding-qa.unsupported")


@pytest.mark.parametrize("rel", ["finding-qa.yaml", "run/decisions/finding-qa.yaml",
                                 "run/40-synthesis/finding-qa.yaml"])
def test_record_outside_a_runs_decisions_directory_refused(tmp_path, rel):
    target = tmp_path / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(FIXTURE, target)
    labels = _labels(tmp_path / "l.yaml", [(target, _all_items())])
    with pytest.raises(CalibrationError, match="40-synthesis/decisions"):
        labelled_pairs(labels, "finding-qa.unsupported")


@pytest.mark.parametrize("text, match", [
    (None, "cannot read"),
    (b"\xff\xfe", "not UTF-8"),
    (b"items: [", "invalid YAML"),
    (b"- a\n", "not a mapping"),
    (b"task: finding-qa\nprovider: cloudflare\nmodel: clef\n", "items"),
    (b"task: finding-qa\nprovider: cloudflare\nmodel: clef\nitems: [3]\n", r"items\[0\]"),
    (b"task: finding-qa\nprovider: cloudflare\nmodel: clef\nitems: [{ref: 3}]\n", "ref"),
    (b"provider: cloudflare\nmodel: clef\nitems: []\n", "task"),
    (b"generated_at: 2026-02-30\n", "invalid YAML"),
    (b"[" * 5000, "invalid YAML"),
])
def test_unreadable_or_malformed_record_refused(tmp_path, text, match):
    target = tmp_path / "run" / RECORD_REL
    target.parent.mkdir(parents=True)
    if text is not None:
        target.write_bytes(text)
    labels = _labels(tmp_path / "l.yaml", [(target, [("conf-00000001", True)])])
    with pytest.raises(CalibrationError, match=match) as err:
        labelled_pairs(labels, "finding-qa.unsupported")
    assert str(target.resolve()) in str(err.value)


def test_record_path_that_cannot_resolve_refused(tmp_path):
    loop = tmp_path / "loop"
    loop.symlink_to(loop)
    labels = _labels(tmp_path / "l.yaml", [(pathlib.Path("loop") / RECORD_REL, _all_items())])
    with pytest.raises(CalibrationError, match="loop"):
        labelled_pairs(labels, "finding-qa.unsupported")


def test_labels_for_another_key_refused(tmp_path):
    record = _run(tmp_path)
    labels = _labels(tmp_path / "l.yaml", [(record, _all_items())], task="finding-qa.lens_drift")
    with pytest.raises(CalibrationError, match="labels for finding-qa.lens_drift, not "
                                               "finding-qa.unsupported"):
        labelled_pairs(labels, "finding-qa.unsupported")


def test_labels_without_records_refused(tmp_path):
    labels = Labels(kind="decisions", path=tmp_path / "l.yaml", sha256="0" * 64, data={
        "schema_version": 1, "kind": "decisions", "set": "dev",
        "task": "finding-qa.unsupported", "records": [],
    })
    with pytest.raises(CalibrationError, match="no records"):
        record_model(labels)
    assert labelled_pairs(labels, "finding-qa.unsupported") == ([], 0)


def test_lens_drift_reads_the_runs_findings(tmp_path):
    record = _run(tmp_path)
    _findings(tmp_path / "run", {f"conf-0000000{k}": "confidentiality" for k in range(1, 8)})
    labels = _labels(tmp_path / "l.yaml", [(record, _all_items())], task="finding-qa.lens_drift")
    pairs, skipped = labelled_pairs(labels, "finding-qa.lens_drift")
    assert pairs == [
        (0.025, True), (0.05, True), (0.075, True), (0.1, False),
        (0.15, True), (0.2, False), (0.3, False),
    ]
    assert skipped == 2  # item 8 has no finding; item 9 is an error


def test_findings_are_loaded_once_per_run(tmp_path, monkeypatch):
    a = _run(tmp_path, "a")
    b = _run(tmp_path, "b")
    calls = []
    real = calibrate._run_findings

    def counting(run_dir):
        calls.append(run_dir)
        return real(run_dir)

    monkeypatch.setattr(calibrate, "_run_findings", counting)
    labels = _labels(tmp_path / "l.yaml", [(a, [("conf-00000001", True)]),
                                           (b, [("conf-00000002", True)]),
                                           (a, [("conf-00000003", True)])])
    labelled_pairs(labels, "finding-qa.unsupported")
    assert calls == [(tmp_path / "a").resolve(), (tmp_path / "b").resolve()]


def test_a_run_whose_findings_cannot_load_refused(tmp_path):
    record = _run(tmp_path)
    bad = tmp_path / "run/10-trustworthiness/x.findings.yaml"
    bad.parent.mkdir(parents=True)
    bad.write_text("finding: [")
    labels = _labels(tmp_path / "l.yaml", [(record, [("conf-00000001", True)])])
    with pytest.raises(CalibrationError, match="x.findings.yaml"):
        labelled_pairs(labels, "finding-qa.unsupported")


def test_a_run_that_cannot_be_read_refused(tmp_path, monkeypatch):
    record = _run(tmp_path)

    def fail(run_dir):
        raise PermissionError(13, "Permission denied", str(run_dir / "10-trustworthiness"))

    monkeypatch.setattr(calibrate, "_load_corpus", fail)
    labels = _labels(tmp_path / "l.yaml", [(record, [("conf-00000001", True)])])
    with pytest.raises(CalibrationError, match="10-trustworthiness: Permission denied"):
        labelled_pairs(labels, "finding-qa.unsupported")


def test_value_spec_returning_a_non_number_refused(tmp_path):
    register_value("finding-qa.odd", ValueSpec("finding-qa", "above", lambda i, f: "high"))
    try:
        record = _run(tmp_path)
        labels = _labels(tmp_path / "l.yaml", [(record, [("conf-00000001", True)])],
                         task="finding-qa.odd")
        with pytest.raises(CalibrationError, match="conf-00000001.*'high'"):
            labelled_pairs(labels, "finding-qa.odd")
    finally:
        del VALUE_SPECS["finding-qa.odd"]


def test_unknown_key_refused(tmp_path):
    record = _run(tmp_path)
    labels = _labels(tmp_path / "l.yaml", [(record, _all_items())])
    with pytest.raises(CalibrationError, match="finding-qa.unsupported"):
        labelled_pairs(labels, "nope")


def test_findings_labels_refused(tmp_path):
    path = tmp_path / "f.yaml"
    path.write_text(yaml.safe_dump({"schema_version": 1, "kind": "findings", "entry": "x",
                                    "items": []}))
    with pytest.raises(CalibrationError, match="decisions"):
        labelled_pairs(load_labels(path), "finding-qa.unsupported")
    with pytest.raises(CalibrationError, match="decisions"):
        record_model(load_labels(path))


# record_model


def test_record_model_of_the_fixture(tmp_path):
    record = _run(tmp_path)
    labels = _labels(tmp_path / "l.yaml", [(record, _all_items())])
    assert record_model(labels) == ("cloudflare", "clef", None)


def test_record_model_carries_the_weights_revision(tmp_path):
    doc = _record_doc()
    doc["weights_revision"] = "rev-7"
    record = _write_record(tmp_path, doc)
    labels = _labels(tmp_path / "l.yaml", [(record, _all_items())])
    assert record_model(labels) == ("cloudflare", "clef", "rev-7")


@pytest.mark.parametrize("field, value", [
    ("model", "clef-flash"), ("provider", "typesafe"), ("weights_revision", "rev-8"),
])
def test_mixed_models_refused_naming_both_records(tmp_path, field, value):
    a = _run(tmp_path, "a")
    doc = _record_doc()
    doc[field] = value
    b = _write_record(tmp_path, doc, name="b")
    labels = _labels(tmp_path / "l.yaml", [(a, [("conf-00000001", True)]),
                                           (b, [("conf-00000002", True)])])
    with pytest.raises(CalibrationError, match="mix models") as err:
        record_model(labels)
    assert str(a.resolve()) in str(err.value) and str(b.resolve()) in str(err.value)
    assert value in str(err.value)


@pytest.mark.parametrize("field, value, match", [
    ("provider", None, "provider"),
    ("model", "", "model"),
    ("model", 3, "model"),
    ("weights_revision", 3, "weights_revision"),
    ("weights_revision", "", "weights_revision"),
])
def test_record_without_a_usable_model_refused(tmp_path, field, value, match):
    doc = _record_doc()
    doc[field] = value
    record = _write_record(tmp_path, doc)
    labels = _labels(tmp_path / "l.yaml", [(record, _all_items())])
    with pytest.raises(CalibrationError, match=match):
        record_model(labels)


# write_threshold

CAL = Calibration(threshold=0.35, precision=0.812345, recall=0.987654, n=8, feasible=True,
                  best_precision=1.0)
SHA = "a" * 64


def test_write_threshold_entry_and_header(tmp_path):
    th = tmp_path / "thresholds.yaml"
    th.write_text(calibrate.HEADER + "{}\n")
    write_threshold(th, "finding-qa.unsupported", CAL, SHA, provider="cloudflare", model="clef",
                    weights_revision=None)
    text = th.read_text()
    assert text.startswith(calibrate.HEADER)
    assert yaml.safe_load(text) == {"finding-qa.unsupported": {
        "threshold": 0.35, "precision": 0.8123, "recall": 0.9877, "n": 8, "labels_sha256": SHA,
        "provider": "cloudflare", "model": "clef", "weights_revision": None, "calibrated": True,
    }}
    body = text[len(calibrate.HEADER):]
    assert body == yaml.safe_dump(yaml.safe_load(text), sort_keys=True)


def test_write_threshold_keeps_other_entries_and_replaces_its_own(tmp_path):
    th = tmp_path / "thresholds.yaml"
    th.write_text("# old header\nzeta: {threshold: 0.9, calibrated: false}\n"
                  "finding-qa.unsupported: {threshold: 0.3, calibrated: false, extra: 1}\n")
    write_threshold(th, "finding-qa.unsupported", CAL, SHA, provider="cloudflare", model="clef",
                    weights_revision="rev-7")
    doc = yaml.safe_load(th.read_text())
    assert list(doc) == ["finding-qa.unsupported", "zeta"]
    assert doc["zeta"] == {"threshold": 0.9, "calibrated": False}
    assert "extra" not in doc["finding-qa.unsupported"]
    assert doc["finding-qa.unsupported"]["weights_revision"] == "rev-7"
    assert th.read_text().startswith(calibrate.HEADER) and "old header" not in th.read_text()


def test_write_threshold_creates_a_missing_file(tmp_path):
    th = tmp_path / "thresholds.yaml"
    write_threshold(th, "k", CAL, SHA, provider="p", model="m", weights_revision=None)
    assert yaml.safe_load(th.read_text())["k"]["calibrated"] is True
    assert list(tmp_path.iterdir()) == [th]


def test_write_threshold_reads_a_comment_only_file_as_empty(tmp_path):
    th = tmp_path / "thresholds.yaml"
    th.write_text("# nothing yet\n")
    write_threshold(th, "k", CAL, SHA, provider="p", model="m", weights_revision=None)
    assert list(yaml.safe_load(th.read_text())) == ["k"]


@pytest.mark.parametrize("text, match", [
    (b"a: [", "invalid YAML"),
    (b"- 1\n", "not a mapping"),
    (b"\xff", "not UTF-8"),
    (b"1: {threshold: 0.5}\n", "key"),
    (b"k: 2026-02-30\n", "invalid YAML"),
    (b"[" * 5000, "invalid YAML"),
])
def test_write_threshold_refuses_an_invalid_file_and_leaves_it(tmp_path, text, match):
    th = tmp_path / "thresholds.yaml"
    th.write_bytes(text)
    with pytest.raises(CalibrationError, match=match) as err:
        write_threshold(th, "k", CAL, SHA, provider="p", model="m", weights_revision=None)
    assert str(th) in str(err.value)
    assert th.read_bytes() == text and list(tmp_path.iterdir()) == [th]


def test_write_threshold_refuses_an_unreadable_file(tmp_path):
    th = tmp_path / "thresholds.yaml"
    th.mkdir()
    with pytest.raises(CalibrationError, match="cannot read"):
        write_threshold(th, "k", CAL, SHA, provider="p", model="m", weights_revision=None)


def test_write_threshold_refuses_an_infeasible_calibration(tmp_path):
    th = tmp_path / "thresholds.yaml"
    th.write_text("{}\n")
    bad = Calibration(None, None, None, 8, False, 0.5)
    with pytest.raises(ValueError, match="infeasible"):
        write_threshold(th, "k", bad, SHA, provider="p", model="m", weights_revision=None)
    assert th.read_text() == "{}\n"


def test_write_threshold_raises_oserror_and_leaves_the_file(tmp_path, monkeypatch):
    th = tmp_path / "thresholds.yaml"
    th.write_text("{}\n")

    def fail(*_args, **_kwargs):
        raise OSError(28, "No space left on device")

    monkeypatch.setattr(calibrate.os, "replace", fail)
    with pytest.raises(OSError):
        write_threshold(th, "k", CAL, SHA, provider="p", model="m", weights_revision=None)
    assert th.read_text() == "{}\n" and list(tmp_path.iterdir()) == [th]


# the data file


def test_thresholds_path_is_the_packaged_file():
    assert resources.data_dir() / "decide" / "thresholds.yaml" == calibrate.THRESHOLDS_PATH


def test_other_module_attributes_still_raise():
    with pytest.raises(AttributeError):
        calibrate.NOT_A_NAME  # noqa: B018


def test_shipped_thresholds_file_is_the_header_and_an_empty_mapping():
    text = (resources.data_dir() / "decide/thresholds.yaml").read_text(encoding="utf-8")
    assert text == calibrate.HEADER + "{}\n"
    assert yaml.safe_load(text) == {}
    for s in ("R8", "<task>.<flag>", "calibrate", "calibrated: false", "eval freeze"):
        assert s in calibrate.HEADER, s


def test_fixture_follows_the_plan():
    doc = yaml.safe_load(FIXTURE.read_text())
    assert (doc["task"], doc["scope"], doc["provider"], doc["model"]) == (
        "finding-qa", "10-trustworthiness", "cloudflare", "clef")
    assert [i["ref"] for i in doc["items"]] == [f"conf-0000000{k}" for k in range(1, 10)]
    assert [i["outcome"] for i in doc["items"]] == ["pass"] * 8 + ["error"]
    ps = [i["answers"]["excerpt_supports_claim"]["p"] for i in doc["items"][:8]]
    assert ps == [0.05, 0.1, 0.15, 0.2, 0.3, 0.4, 0.6, 0.8]
