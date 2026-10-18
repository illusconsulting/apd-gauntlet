"""``apd-gauntlet calibrate``: a decision threshold from dev labels over decision records."""
from __future__ import annotations

import hashlib
import os
import pathlib
import shutil

import pytest
import yaml
from apd_gauntlet import resources
from apd_gauntlet.cli import main
from apd_gauntlet.eval import calibrate
from click.testing import CliRunner

FIXTURE = pathlib.Path(__file__).parent / "fixtures/eval/finding-qa.record.yaml"
RECORD_REL = "40-synthesis/decisions/finding-qa.10-trustworthiness.yaml"
GOLD = [True, True, True, False, True, False, False, False, True]
FREEZE_REMINDER = "re-run 'apd-gauntlet eval freeze' before any held-out run"


def _write_labels(path, records, *, task="finding-qa.unsupported", set_name="dev"):
    doc = {
        "schema_version": 1, "kind": "decisions", "set": set_name, "task": task,
        "records": [
            {"path": p, "items": [{"ref": r, "gold": g} for r, g in items]} for p, items in records
        ],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(doc, sort_keys=False))
    return path


def _items(gold=GOLD):
    return [(f"conf-0000000{k}", g) for k, g in enumerate(gold, start=1)]


@pytest.fixture
def decision_labels(tmp_path):
    """The fixture record in ``<tmp>/run`` and its dev labels under ``eval/local/decide/``."""
    record = tmp_path / "run" / RECORD_REL
    record.parent.mkdir(parents=True)
    shutil.copy(FIXTURE, record)
    labels = tmp_path / "eval/local/decide/finding-qa.unsupported.labels.yaml"
    return _write_labels(labels, [(f"../../../run/{RECORD_REL}", _items())])


def _relabel(path, **changes):
    doc = yaml.safe_load(path.read_text())
    doc.update(changes)
    path.write_text(yaml.safe_dump(doc, sort_keys=False))


def _calibrate(labels, th, *extra, task="finding-qa.unsupported"):
    return CliRunner().invoke(main, ["calibrate", task, "--labels", str(labels),
                                     "--target-precision", "0.75", "--thresholds", str(th),
                                     *extra])


def test_calibrate_writes_entry(decision_labels, tmp_path):
    th = tmp_path / "thresholds.yaml"
    th.write_text("{}\n")
    r = CliRunner().invoke(main, [
        "calibrate", "finding-qa.unsupported", "--labels", str(decision_labels),
        "--target-precision", "0.75", "--min-support", "1", "--thresholds", str(th),
    ])
    assert r.exit_code == 0
    assert yaml.safe_load(th.read_text())["finding-qa.unsupported"] == {
        "threshold": 0.35, "precision": 0.8, "recall": 1.0, "n": 8,
        "labels_sha256": hashlib.sha256(decision_labels.read_bytes()).hexdigest(),
        "provider": "cloudflare", "model": "clef", "weights_revision": None, "calibrated": True}


def test_min_support_refuses_tiny_sets(decision_labels, tmp_path):
    th = tmp_path / "thresholds.yaml"
    th.write_text("{}\n")
    before = th.read_bytes()
    r = CliRunner().invoke(main, [
        "calibrate", "finding-qa.unsupported", "--labels", str(decision_labels),
        "--target-precision", "0.75", "--thresholds", str(th),
    ])
    assert r.exit_code == 1 and "uncalibrated" in r.output and th.read_bytes() == before


def test_heldout_labels_refused(decision_labels, tmp_path):
    _relabel(decision_labels, set="heldout")
    th = tmp_path / "thresholds.yaml"
    th.write_text("{}\n")
    r = _calibrate(decision_labels, th, "--min-support", "1")
    assert r.exit_code == 2
    assert "calibrate on dev labels only; thresholds freeze before held-out runs" in r.output
    assert th.read_text() == "{}\n"


def test_task_mismatch_refused(decision_labels, tmp_path):
    th = tmp_path / "thresholds.yaml"
    th.write_text("{}\n")
    r = _calibrate(decision_labels, th, "--min-support", "1", task="finding-qa.lens_drift")
    assert r.exit_code == 2
    assert "finding-qa.unsupported" in r.output and "finding-qa.lens_drift" in r.output
    assert th.read_text() == "{}\n"


def test_unknown_ref_refused(decision_labels, tmp_path):
    _relabel(decision_labels, records=[
        {"path": f"../../../run/{RECORD_REL}", "items": [{"ref": "conf-0000000a", "gold": True}]}
    ])
    th = tmp_path / "thresholds.yaml"
    th.write_text("{}\n")
    r = _calibrate(decision_labels, th, "--min-support", "1")
    assert r.exit_code == 2 and "conf-0000000a" in r.output
    assert th.read_text() == "{}\n"


def test_mixed_models_refused(decision_labels, tmp_path):
    doc = yaml.safe_load(FIXTURE.read_text())
    doc["model"] = "clef-flash"
    second = tmp_path / "run2" / RECORD_REL
    second.parent.mkdir(parents=True)
    second.write_text(yaml.safe_dump(doc, sort_keys=False))
    labels = yaml.safe_load(decision_labels.read_text())
    labels["records"].append({"path": f"../../../run2/{RECORD_REL}",
                              "items": [{"ref": "conf-00000001", "gold": True}]})
    decision_labels.write_text(yaml.safe_dump(labels, sort_keys=False))
    th = tmp_path / "thresholds.yaml"
    th.write_text("{}\n")
    before = th.read_bytes()
    r = _calibrate(decision_labels, th, "--min-support", "1")
    assert r.exit_code == 2 and "clef-flash" in r.output and "mix models" in r.output
    assert th.read_bytes() == before


def test_unknown_task_lists_keys(decision_labels, tmp_path):
    th = tmp_path / "thresholds.yaml"
    th.write_text("{}\n")
    r = _calibrate(decision_labels, th, task="nope")
    assert r.exit_code == 2 and "finding-qa.unsupported" in r.output
    assert "finding-qa.lens_drift" in r.output
    assert th.read_text() == "{}\n"


def test_packaged_thresholds_file_exists():
    assert (resources.data_dir() / "decide/thresholds.yaml").is_file()


# --- beyond the plan's tests -------------------------------------------------------------


def test_success_prints_the_entry_and_the_freeze_reminder(decision_labels, tmp_path):
    th = tmp_path / "thresholds.yaml"
    th.write_text("{}\n")
    r = _calibrate(decision_labels, th, "--min-support", "1")
    assert r.exit_code == 0, r.output
    assert f"wrote {th}: finding-qa.unsupported" in r.output
    assert "threshold: 0.35" in r.output and "calibrated: true" in r.output
    assert "provider: cloudflare" in r.output and "model: clef" in r.output
    assert "skipped 1 labelled item (outcome error or no value)" in r.output
    assert r.output.rstrip().endswith(FREEZE_REMINDER)


def test_no_skipped_line_when_nothing_is_skipped(decision_labels, tmp_path):
    _relabel(decision_labels, records=[
        {"path": f"../../../run/{RECORD_REL}", "items": [{"ref": r, "gold": g}
                                                        for r, g in _items()[:8]]}
    ])
    th = tmp_path / "thresholds.yaml"
    th.write_text("{}\n")
    r = _calibrate(decision_labels, th, "--min-support", "1")
    assert r.exit_code == 0, r.output
    assert "labelled item" not in r.output  # the tmp path holds the word "skipped"


def test_written_file_has_the_header(decision_labels, tmp_path):
    th = tmp_path / "thresholds.yaml"
    th.write_text(calibrate.HEADER + "{}\n")
    assert _calibrate(decision_labels, th, "--min-support", "1").exit_code == 0
    assert th.read_text().startswith(calibrate.HEADER)


def test_other_entries_are_kept(decision_labels, tmp_path):
    th = tmp_path / "thresholds.yaml"
    th.write_text("finding-qa.lens_drift: {threshold: 0.5, calibrated: false}\n")
    assert _calibrate(decision_labels, th, "--min-support", "1").exit_code == 0
    doc = yaml.safe_load(th.read_text())
    assert doc["finding-qa.lens_drift"] == {"threshold": 0.5, "calibrated": False}
    assert doc["finding-qa.unsupported"]["calibrated"] is True


def test_infeasible_message(decision_labels, tmp_path):
    th = tmp_path / "thresholds.yaml"
    th.write_text("{}\n")
    r = _calibrate(decision_labels, th)
    assert r.exit_code == 1
    assert (
        "no threshold reaches precision ≥ 0.75 with at least 10 predicted positives (best: none);"
        " finding-qa.unsupported stays uncalibrated"
    ) in r.output
    r = _calibrate(decision_labels, th, "--min-support", "6")
    assert r.exit_code == 1
    assert "at least 6 predicted positives (best: 0.6667)" in r.output
    assert th.read_text() == "{}\n"


def test_lens_drift_end_to_end(decision_labels, tmp_path):
    findings = tmp_path / "run/10-trustworthiness/x.findings.yaml"
    findings.parent.mkdir(parents=True)
    findings.write_text(yaml.safe_dump({"finding": [
        {"id": f"conf-0000000{k}", "apd_goal": "confidentiality"} for k in range(1, 8)
    ]}))
    _relabel(decision_labels, task="finding-qa.lens_drift")
    th = tmp_path / "thresholds.yaml"
    th.write_text("{}\n")
    r = _calibrate(decision_labels, th, "--min-support", "1", task="finding-qa.lens_drift")
    assert r.exit_code == 0, r.output
    entry = yaml.safe_load(th.read_text())["finding-qa.lens_drift"]
    assert (entry["threshold"], entry["precision"], entry["recall"], entry["n"]) == (
        0.175, 0.8, 1.0, 7)
    assert "skipped 2 labelled items" in r.output


def test_findings_labels_refused(tmp_path):
    labels = tmp_path / "l.yaml"
    labels.write_text(yaml.safe_dump({"schema_version": 1, "kind": "findings", "entry": "x",
                                      "items": []}))
    th = tmp_path / "thresholds.yaml"
    th.write_text("{}\n")
    r = _calibrate(labels, th)
    assert r.exit_code == 2 and "decisions" in r.output


@pytest.mark.parametrize("content", [None, "kind: [\n", "schema_version: 1\nkind: decisions\n"])
def test_missing_or_invalid_labels_refused(tmp_path, content):
    labels = tmp_path / "l.yaml"
    if content is not None:
        labels.write_text(content)
    th = tmp_path / "thresholds.yaml"
    th.write_text("{}\n")
    r = _calibrate(labels, th)
    assert r.exit_code == 2 and str(labels) in r.output
    assert th.read_text() == "{}\n"


def test_no_gold_positive_refused(decision_labels, tmp_path):
    _relabel(decision_labels, records=[
        {"path": f"../../../run/{RECORD_REL}", "items": [{"ref": r, "gold": False}
                                                        for r, _ in _items()]}
    ])
    th = tmp_path / "thresholds.yaml"
    th.write_text("{}\n")
    r = _calibrate(decision_labels, th, "--min-support", "1")
    assert r.exit_code == 2 and "no gold positive" in r.output


@pytest.mark.parametrize("value", ["0", "-0.1", "1.01", "x"])
def test_target_precision_range(decision_labels, tmp_path, value):
    th = tmp_path / "thresholds.yaml"
    th.write_text("{}\n")
    r = CliRunner().invoke(main, ["calibrate", "finding-qa.unsupported", "--labels",
                                  str(decision_labels), "--target-precision", value,
                                  "--thresholds", str(th)])
    assert r.exit_code == 2 and "--target-precision" in r.output


def test_target_precision_of_one_is_accepted(decision_labels, tmp_path):
    th = tmp_path / "thresholds.yaml"
    th.write_text("{}\n")
    r = CliRunner().invoke(main, ["calibrate", "finding-qa.unsupported", "--labels",
                                  str(decision_labels), "--target-precision", "1",
                                  "--min-support", "1", "--thresholds", str(th)])
    assert r.exit_code == 0, r.output
    assert yaml.safe_load(th.read_text())["finding-qa.unsupported"]["threshold"] == 0.175


def test_min_support_must_be_positive(decision_labels, tmp_path):
    th = tmp_path / "thresholds.yaml"
    th.write_text("{}\n")
    r = _calibrate(decision_labels, th, "--min-support", "0")
    assert r.exit_code == 2 and "--min-support" in r.output


def test_invalid_thresholds_file_refused_and_left(decision_labels, tmp_path):
    th = tmp_path / "thresholds.yaml"
    th.write_text("- not a mapping\n")
    r = _calibrate(decision_labels, th, "--min-support", "1")
    assert r.exit_code == 2 and str(th) in r.output
    assert th.read_text() == "- not a mapping\n"


@pytest.mark.skipif(os.geteuid() == 0, reason="root ignores directory permissions")
def test_unwritable_thresholds_exits_1(decision_labels, tmp_path):
    d = tmp_path / "ro"
    d.mkdir()
    th = d / "thresholds.yaml"
    th.write_text("{}\n")
    d.chmod(0o500)
    try:
        r = _calibrate(decision_labels, th, "--min-support", "1")
    finally:
        d.chmod(0o700)
    assert r.exit_code == 1 and f"{th}: cannot write" in r.output
    assert th.read_text() == "{}\n" and list(d.iterdir()) == [th]


def test_default_thresholds_path(decision_labels, tmp_path, monkeypatch):
    th = tmp_path / "packaged/thresholds.yaml"
    th.parent.mkdir()
    th.write_text("{}\n")
    monkeypatch.setattr(calibrate, "_thresholds_path", lambda: th)
    r = CliRunner().invoke(main, ["calibrate", "finding-qa.unsupported", "--labels",
                                  str(decision_labels), "--target-precision", "0.75",
                                  "--min-support", "1"])
    assert r.exit_code == 0, r.output
    assert yaml.safe_load(th.read_text())["finding-qa.unsupported"]["calibrated"] is True


def test_help_lists_the_exit_codes():
    r = CliRunner().invoke(main, ["calibrate", "--help"])
    assert r.exit_code == 0
    text = " ".join(r.output.split())
    for s in ("Exits 0", "1 when", "2 when", "--min-support", "--thresholds", "eval freeze"):
        assert s in text, s
