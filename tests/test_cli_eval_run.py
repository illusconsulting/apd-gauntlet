"""eval.runner and ``eval run``: a registered evaluator over one set of a corpus."""
from __future__ import annotations

import hashlib
import json
import pathlib
import re
from datetime import datetime, timedelta, timezone

import pytest
import yaml
from apd_gauntlet import __version__
from apd_gauntlet.cli import main
from apd_gauntlet.eval import evaluators
from apd_gauntlet.eval.corpus import CorpusError
from apd_gauntlet.eval.evaluators import EvalResult
from apd_gauntlet.eval.findings_eval import label_template, metrics_from_counts
from apd_gauntlet.eval.freeze import FreezeError, check_frozen, freeze
from apd_gauntlet.eval.runner import ResultsWriteError, run_eval
from click.testing import CliRunner

REPO = pathlib.Path(__file__).resolve().parent.parent
THRESHOLDS = "tools/apd_gauntlet/data/decide/thresholds.yaml"
IAC_PARAMS = "tools/apd_gauntlet/data/iac/context-params.yaml"
NOW = datetime(2026, 10, 17, 12, 30, 45, tzinfo=timezone.utc)


def _tunables(root):
    for rel, text in {THRESHOLDS: "{}\n", IAC_PARAMS: "k: 20\n"}.items():
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_text(text)


def _labels(path, run, entry_id, **overrides):
    """A findings labels file for ``run``: every item true_positive, then ``overrides``."""
    data = label_template(run, entry_id)
    for item in data["items"]:
        item["verdict"] = "true_positive"
        item.update(overrides.get(item["id"], {}))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data))
    return data


def _manifest(path, entries, name="findings"):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump({"schema_version": 1, "name": name, "entries": entries}))
    return path


def setup_corpus(make_run, tmp_path, set_name):
    root = tmp_path / "repo"
    _tunables(root)  # tunables as in Task 10's root()
    run = make_run("r")
    labels = root / "eval/findings/labels/ceb.yaml"  # label_template, all true_positive
    _labels(labels, run, "ceb")
    m = _manifest(
        root / "eval/findings/corpus.yaml",
        [{"id": "ceb", "set": set_name, "run": str(run), "labels": "labels/ceb.yaml"}],
    )
    return root, m


def ev(root, m, s):
    return CliRunner().invoke(
        main, ["eval", "run", str(m), "--set", s, "--evaluator", "findings", "--root", str(root)]
    )


def test_dev_run_writes_results(make_run, tmp_path):
    root, m = setup_corpus(make_run, tmp_path, "dev")
    assert ev(root, m, "dev").exit_code == 0
    (res,) = (root / "eval/results/findings").glob("dev-*.yaml")
    data = yaml.safe_load(res.read_text())
    assert data["totals"]["metrics"]["precision.all"] == 1.0
    assert data["frozen_sha256"] is None


def test_heldout_without_freeze_exits_2(make_run, tmp_path):
    root, m = setup_corpus(make_run, tmp_path, "heldout")
    r = ev(root, m, "heldout")
    assert r.exit_code == 2 and "eval freeze" in r.output


def test_heldout_after_tunable_edit_exits_2(make_run, tmp_path):
    root, m = setup_corpus(make_run, tmp_path, "heldout")
    freeze(root)
    (root / "tools/apd_gauntlet/data/iac/context-params.yaml").write_text("k: 99\n")
    r = ev(root, m, "heldout")
    assert r.exit_code == 2 and "changed since freeze" in r.output


def test_heldout_records_frozen_hash_and_blocks_refreeze(make_run, tmp_path):
    root, m = setup_corpus(make_run, tmp_path, "heldout")
    freeze(root)
    assert ev(root, m, "heldout").exit_code == 0
    (res,) = (root / "eval/results/findings").glob("heldout-*.yaml")
    assert yaml.safe_load(res.read_text())["frozen_sha256"] == check_frozen(root)
    (root / "tools/apd_gauntlet/data/iac/context-params.yaml").write_text("k: 99\n")
    assert CliRunner().invoke(main, ["eval", "freeze", "--root", str(root)]).exit_code == 1


def test_unknown_evaluator_exits_2(make_run, tmp_path):
    root, m = setup_corpus(make_run, tmp_path, "dev")
    r = CliRunner().invoke(
        main, ["eval", "run", str(m), "--set", "dev", "--evaluator", "nope", "--root", str(root)]
    )
    assert r.exit_code == 2 and "findings" in r.output


def test_results_and_local_are_gitignored():
    lines = (REPO / ".gitignore").read_text().splitlines()
    assert "eval/results/" in lines and "eval/local/" in lines
    assert "telemetry/" in lines


# --- beyond the plan's tests -------------------------------------------------------------


def invoke(*args):
    return CliRunner().invoke(main, ["eval", "run", *map(str, args)])


def _results(root, evaluator="findings"):
    return sorted((root / "eval/results" / evaluator).glob("*.yaml"))


def _sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.fixture
def fake(monkeypatch):
    """Register ``fake`` evaluators for one test; returns ``add(name, fn)``."""

    def add(name, fn):
        monkeypatch.setitem(evaluators.EVALUATORS, name, fn)

    return add


def _fake_corpus(tmp_path, ids=("a", "b"), set_name="dev"):
    """A corpus of entries with empty findings labels, for fake evaluators."""
    root = tmp_path / "repo"
    _tunables(root)
    entries = []
    for i in ids:
        labels = root / f"eval/fake/labels/{i}.yaml"
        labels.parent.mkdir(parents=True, exist_ok=True)
        labels.write_text(
            yaml.safe_dump({"schema_version": 1, "kind": "findings", "entry": i, "items": []})
        )
        entries.append({
            "id": i,
            "set": set_name,
            "run": str(tmp_path / f"run-{i}"),
            "labels": f"labels/{i}.yaml",
        })
    return root, _manifest(root / "eval/fake/corpus.yaml", entries, name="fake")


def _counting(counts, *, derive=None, calls=None, notes=()):
    def fn(entry, labels):
        if calls is not None:
            calls.append((entry.id, labels.data["entry"]))
        return EvalResult(entry.id, dict(counts[entry.id]), {"m": 0.5}, notes, derive=derive)

    return fn


def test_results_file_layout(make_run, tmp_path):
    root, m = setup_corpus(make_run, tmp_path, "dev")
    path = run_eval(
        m, "dev", "findings", root=root, results_dir=root / "eval/results", now=NOW
    )
    assert path == root / "eval/results/findings/dev-20261017T123045Z.yaml"
    data = yaml.safe_load(path.read_text())
    assert list(data) == [
        "schema_version", "evaluator", "set", "corpus", "frozen_sha256", "engine_version",
        "generated_at", "entries", "totals",
    ]
    assert data["schema_version"] == 1 and data["evaluator"] == "findings"
    assert data["set"] == "dev" and data["engine_version"] == __version__
    assert data["corpus"] == {
        "name": "findings", "path": "eval/findings/corpus.yaml", "sha256": _sha(m),
    }
    assert data["generated_at"] == "2026-10-17T12:30:45Z"
    (entry,) = data["entries"]
    assert list(entry) == ["id", "counts", "metrics", "notes"]
    assert entry["id"] == "ceb" and entry["notes"] == []
    assert entry["counts"]["tp.confidentiality"] == 4 and entry["metrics"]["recall.all"] == 1.0
    assert list(data["totals"]) == ["counts", "metrics"]
    assert data["totals"]["counts"] == entry["counts"]
    assert data["totals"]["metrics"] == entry["metrics"]
    assert path.read_text().startswith("# ")


def test_corpus_outside_root_is_recorded_absolute(make_run, tmp_path):
    root, m = setup_corpus(make_run, tmp_path, "dev")
    outside = tmp_path / "elsewhere/corpus.yaml"
    outside.parent.mkdir()
    outside.write_text(
        m.read_text().replace("labels/ceb.yaml", str(m.parent / "labels/ceb.yaml"))
    )
    path = run_eval(outside, "dev", "findings", root=root, results_dir=tmp_path / "res")
    assert yaml.safe_load(path.read_text())["corpus"]["path"] == str(outside.resolve())


def test_totals_sum_counts_and_derive_from_the_sums(make_run, tmp_path):
    root = tmp_path / "repo"
    _tunables(root)
    r1, r2 = make_run("r1"), make_run("r2")
    _labels(root / "eval/findings/labels/one.yaml", r1, "one")
    two = _labels(root / "eval/findings/labels/two.yaml", r2, "two")
    # Entry two: ten findings left unlabelled (unjudged) and one false positive.
    kept = two["items"][10:]
    kept[0]["verdict"] = "false_positive"
    two["items"] = kept
    (root / "eval/findings/labels/two.yaml").write_text(yaml.safe_dump(two))
    m = _manifest(root / "eval/findings/corpus.yaml", [
        {"id": "one", "set": "dev", "run": str(r1), "labels": "labels/one.yaml"},
        {"id": "two", "set": "dev", "run": str(r2), "labels": "labels/two.yaml"},
    ])
    data = yaml.safe_load(
        run_eval(m, "dev", "findings", root=root, results_dir=root / "eval/results").read_text()
    )
    first, second = data["entries"]
    assert [first["id"], second["id"]] == ["one", "two"]
    assert first["metrics"]["precision.all"] == 1.0 and second["metrics"]["precision.all"] == 0.9
    totals = data["totals"]
    summed = {k: first["counts"][k] + second["counts"][k] for k in first["counts"]}
    assert totals["counts"] == summed
    assert totals["metrics"] == metrics_from_counts(totals["counts"])
    assert totals["metrics"]["precision.all"] == pytest.approx(29 / 30)  # pooled, not the mean


def test_totals_union_of_count_keys_and_no_derive(tmp_path, fake):
    root, m = _fake_corpus(tmp_path)
    fake("fake", _counting({"a": {"x": 1, "y": 2}, "b": {"y": 3, "z": 4}}))
    data = yaml.safe_load(
        run_eval(m, "dev", "fake", root=root, results_dir=root / "eval/results").read_text()
    )
    assert data["totals"] == {"counts": {"x": 1, "y": 5, "z": 4}, "metrics": {}}
    assert [e["metrics"] for e in data["entries"]] == [{"m": 0.5}, {"m": 0.5}]


def test_totals_metrics_use_the_first_entry_derive(tmp_path, fake):
    root, m = _fake_corpus(tmp_path)

    def derive(counts):
        return {"total_x": float(counts.get("x", 0))}

    fake("fake", _counting({"a": {"x": 1}, "b": {"x": 2}}, derive=derive))
    data = yaml.safe_load(
        run_eval(m, "dev", "fake", root=root, results_dir=root / "eval/results").read_text()
    )
    assert data["totals"]["metrics"] == {"total_x": 3.0}


def test_entries_follow_the_manifest_and_only_the_set(tmp_path, fake):
    root, m = _fake_corpus(tmp_path, ids=("c", "a", "b"))
    doc = yaml.safe_load(m.read_text())
    doc["entries"][2]["set"] = "heldout"
    m.write_text(yaml.safe_dump(doc))
    calls: list[tuple[str, str]] = []
    fake("fake", _counting({"c": {}, "a": {}, "b": {}}, calls=calls, notes=("n1", "n2")))
    data = yaml.safe_load(
        run_eval(m, "dev", "fake", root=root, results_dir=root / "eval/results").read_text()
    )
    assert calls == [("c", "c"), ("a", "a")]
    assert [e["id"] for e in data["entries"]] == ["c", "a"]
    assert data["entries"][0]["notes"] == ["n1", "n2"]


def test_dev_records_the_frozen_hash_when_frozen(make_run, tmp_path):
    root, m = setup_corpus(make_run, tmp_path, "dev")
    freeze(root)
    assert ev(root, m, "dev").exit_code == 0
    (res,) = _results(root)
    assert yaml.safe_load(res.read_text())["frozen_sha256"] == check_frozen(root)


def test_dev_after_tunable_edit_records_null(make_run, tmp_path):
    root, m = setup_corpus(make_run, tmp_path, "dev")
    freeze(root)
    (root / IAC_PARAMS).write_text("k: 99\n")
    result = ev(root, m, "dev")
    assert result.exit_code == 0, result.output
    (res,) = _results(root)
    assert yaml.safe_load(res.read_text())["frozen_sha256"] is None
    assert "not frozen" in result.output


def test_dev_with_an_invalid_frozen_file_records_null(make_run, tmp_path):
    root, m = setup_corpus(make_run, tmp_path, "dev")
    (root / "eval/frozen.yaml").write_text("schema_version: 2\n")
    assert ev(root, m, "dev").exit_code == 0
    (res,) = _results(root)
    assert yaml.safe_load(res.read_text())["frozen_sha256"] is None


def test_heldout_freeze_checked_before_any_evaluator(tmp_path, fake):
    root, m = _fake_corpus(tmp_path, set_name="heldout")
    calls: list[tuple[str, str]] = []
    fake("fake", _counting({"a": {}, "b": {}}, calls=calls))
    with pytest.raises(FreezeError, match="eval freeze"):
        run_eval(m, "heldout", "fake", root=root, results_dir=root / "eval/results")
    assert calls == [] and not (root / "eval/results").exists()


def test_heldout_freeze_checked_before_the_manifest(tmp_path):
    root = tmp_path / "repo"
    _tunables(root)
    r = invoke(tmp_path / "missing.yaml", "--set", "heldout", "--evaluator", "findings",
               "--root", root)
    assert r.exit_code == 2 and "eval freeze" in r.output


def test_tunables_changed_during_a_heldout_run_write_nothing(tmp_path, fake):
    root, m = _fake_corpus(tmp_path, set_name="heldout")
    freeze(root)

    def edits(entry, labels):
        (root / IAC_PARAMS).write_text("k: 21\n")
        return EvalResult(entry.id, {}, {})

    fake("edits", edits)
    with pytest.raises(FreezeError, match="changed since freeze"):
        run_eval(m, "heldout", "edits", root=root, results_dir=root / "eval/results")
    assert not (root / "eval/results").exists()


def test_refrozen_during_a_heldout_run_writes_nothing(tmp_path, fake):
    root, m = _fake_corpus(tmp_path, set_name="heldout")
    freeze(root)

    def refreezes(entry, labels):
        if entry.id == "a":
            (root / IAC_PARAMS).write_text("k: 21\n")
            freeze(root)
        return EvalResult(entry.id, {}, {})

    fake("refreezes", refreezes)
    with pytest.raises(FreezeError, match="re-frozen during the held-out run"):
        run_eval(m, "heldout", "refreezes", root=root, results_dir=root / "eval/results")
    assert not (root / "eval/results").exists()


def test_heldout_result_name_and_cli_line(make_run, tmp_path):
    root, m = setup_corpus(make_run, tmp_path, "heldout")
    freeze(root)
    result = ev(root, m, "heldout")
    assert result.exit_code == 0, result.output
    (res,) = _results(root)
    assert re.fullmatch(r"heldout-\d{8}T\d{6}Z\.yaml", res.name)
    sha = check_frozen(root)
    assert f"wrote {res}" in result.output and f"frozen {sha[:8]}" in result.output
    assert "1 heldout entry" in result.output


def test_results_dir_option(make_run, tmp_path):
    root, m = setup_corpus(make_run, tmp_path, "dev")
    out = tmp_path / "out"
    r = invoke(m, "--set", "dev", "--evaluator", "findings", "--root", root, "--results-dir", out)
    assert r.exit_code == 0, r.output
    assert len(list((out / "findings").glob("dev-*.yaml"))) == 1
    assert not (root / "eval/results").exists()


def test_heldout_results_outside_root_warn(make_run, tmp_path):
    root, m = setup_corpus(make_run, tmp_path, "heldout")
    freeze(root)
    out = tmp_path / "out"
    r = invoke(m, "--set", "heldout", "--evaluator", "findings", "--root", root,
               "--results-dir", out)
    assert r.exit_code == 0, r.output
    assert "warning:" in r.output and "eval freeze" in r.output and str(root) in r.output
    r = invoke(m, "--set", "heldout", "--evaluator", "findings", "--root", root, "--json",
               "--results-dir", tmp_path / "out2")
    out_json = json.loads(r.stdout)
    assert len(out_json["warnings"]) == 1 and "eval freeze" in out_json["warnings"][0]


def test_default_root_is_the_working_directory(make_run, tmp_path, monkeypatch):
    root, m = setup_corpus(make_run, tmp_path, "dev")
    monkeypatch.chdir(root)
    r = invoke("eval/findings/corpus.yaml", "--set", "dev", "--evaluator", "findings")
    assert r.exit_code == 0, r.output
    (res,) = _results(root)
    assert yaml.safe_load(res.read_text())["corpus"]["path"] == "eval/findings/corpus.yaml"


def test_json_output(make_run, tmp_path):
    root, m = setup_corpus(make_run, tmp_path, "dev")
    r = invoke(m, "--set", "dev", "--evaluator", "findings", "--root", root, "--json")
    assert r.exit_code == 0, r.output
    out = json.loads(r.stdout)
    (res,) = _results(root)
    assert out["path"] == str(res) and out["warnings"] == []
    assert out["result"] == yaml.safe_load(res.read_text())


def test_empty_set_exits_2_and_writes_nothing(make_run, tmp_path):
    root, m = setup_corpus(make_run, tmp_path, "dev")
    r = invoke(m, "--set", "heldout", "--evaluator", "findings", "--root", root)
    assert r.exit_code == 2  # the freeze check comes first
    freeze(root)
    r = invoke(m, "--set", "heldout", "--evaluator", "findings", "--root", root)
    assert r.exit_code == 2 and "no heldout entries" in r.output
    assert not (root / "eval/results").exists()


def test_invalid_manifest_exits_2(make_run, tmp_path):
    root, m = setup_corpus(make_run, tmp_path, "dev")
    m.write_text("schema_version: 1\nname: findings\n")
    r = ev(root, m, "dev")
    assert r.exit_code == 2 and "invalid corpus manifest" in r.output
    r = invoke(tmp_path / "nope.yaml", "--set", "dev", "--evaluator", "findings", "--root", root)
    assert r.exit_code == 2 and "cannot read" in r.output
    assert not (root / "eval/results").exists()


def test_invalid_labels_exit_2(make_run, tmp_path):
    root, m = setup_corpus(make_run, tmp_path, "dev")
    (root / "eval/findings/labels/ceb.yaml").write_text("schema_version: 1\nkind: findings\n")
    r = ev(root, m, "dev")
    assert r.exit_code == 2 and "invalid labels" in r.output
    assert not (root / "eval/results").exists()


def test_labels_checked_before_any_evaluator(tmp_path, fake):
    root, m = _fake_corpus(tmp_path)
    (root / "eval/fake/labels/b.yaml").write_text("kind: nope\n")
    calls: list[tuple[str, str]] = []
    fake("fake", _counting({"a": {}, "b": {}}, calls=calls))
    with pytest.raises(CorpusError, match="b.yaml"):
        run_eval(m, "dev", "fake", root=root, results_dir=root / "eval/results")
    assert calls == []


def test_evaluator_value_error_exits_2_and_writes_nothing(make_run, tmp_path):
    root, m = setup_corpus(make_run, tmp_path, "dev")
    labels = root / "eval/findings/labels/ceb.yaml"
    labels.write_text(labels.read_text().replace("true_positive", "unreviewed", 1))
    r = ev(root, m, "dev")
    assert r.exit_code == 2 and "1 unreviewed item" in r.output
    assert not (root / "eval/results").exists()


def test_a_later_entry_failing_writes_nothing(tmp_path, fake):
    root, m = _fake_corpus(tmp_path)

    def fails_on_b(entry, labels):
        if entry.id == "b":
            raise ValueError("b is broken")
        return EvalResult(entry.id, {"x": 1}, {})

    fake("fails", fails_on_b)
    r = invoke(m, "--set", "dev", "--evaluator", "fails", "--root", root)
    assert r.exit_code == 2 and "b is broken" in r.output
    assert not (root / "eval/results").exists()


@pytest.mark.parametrize(
    ("result", "message"),
    [
        (EvalResult("other", {}, {}), "returned a result for entry 'other'"),
        (EvalResult("a", {"x": True}, {}), "count 'x'"),
        (EvalResult("a", {"x": 1.5}, {}), "count 'x'"),
        (EvalResult("a", {"x": -1}, {}), "count 'x'"),
        (EvalResult("a", {1: 1}, {}), "count 1"),
        (EvalResult("a", {}, {"m": "high"}), "metric 'm'"),
        (EvalResult("a", {}, {"m": True}), "metric 'm'"),
        (EvalResult("a", {}, {"m": float("nan")}), "metric 'm' is nan, not a finite number"),
        (EvalResult("a", {}, {"m": float("inf")}), "metric 'm' is inf"),
        (EvalResult("a", {}, {"m": 10**400}), "metric 'm' is " + "1" + "0" * 59 + "..., not"),
        (EvalResult("a", {}, {2: 0.5}), "metric 2 is not keyed by name"),
        (EvalResult("a", {}, {}, derive=lambda c: {"t": "x"}), "total metric 't' is 'x'"),
        (EvalResult("a", {}, {}, derive=lambda c: {3: 1.0}), "total metric 3 is not keyed"),
    ],
)
def test_malformed_evaluator_results_refused(tmp_path, fake, result, message):
    root, m = _fake_corpus(tmp_path, ids=("a",))
    fake("bad", lambda entry, labels: result)
    with pytest.raises(ValueError, match=re.escape(message)):
        run_eval(m, "dev", "bad", root=root, results_dir=root / "eval/results")
    assert not (root / "eval/results").exists()


def test_integer_metrics_and_none_are_kept(tmp_path, fake):
    root, m = _fake_corpus(tmp_path, ids=("a",))
    fake("ok", lambda entry, labels: EvalResult("a", {}, {"n": 3, "p": None, "q": 0.25}))
    data = yaml.safe_load(
        run_eval(m, "dev", "ok", root=root, results_dir=root / "eval/results").read_text()
    )
    assert data["entries"][0]["metrics"] == {"n": 3.0, "p": None, "q": 0.25}


def test_unknown_evaluator_from_the_api(make_run, tmp_path):
    root, m = setup_corpus(make_run, tmp_path, "dev")
    with pytest.raises(KeyError, match="registered: .*findings"):
        run_eval(m, "dev", "nope", root=root, results_dir=root / "eval/results")


def test_unknown_set_from_the_api(make_run, tmp_path):
    root, m = setup_corpus(make_run, tmp_path, "dev")
    with pytest.raises(ValueError, match="unknown set"):
        run_eval(m, "test", "findings", root=root, results_dir=root / "eval/results")


def test_unknown_set_on_the_command_line(make_run, tmp_path):
    root, m = setup_corpus(make_run, tmp_path, "dev")
    r = invoke(m, "--set", "test", "--evaluator", "findings", "--root", root)
    assert r.exit_code == 2 and "'dev'" in r.output and "'heldout'" in r.output


def test_an_existing_results_file_is_never_overwritten(make_run, tmp_path):
    root, m = setup_corpus(make_run, tmp_path, "dev")
    results = root / "eval/results"
    path = run_eval(m, "dev", "findings", root=root, results_dir=results, now=NOW)
    before = path.read_bytes()
    with pytest.raises(ResultsWriteError, match="exists; not overwritten"):
        run_eval(m, "dev", "findings", root=root, results_dir=results, now=NOW)
    assert path.read_bytes() == before
    later = run_eval(
        m, "dev", "findings", root=root, results_dir=results, now=NOW + timedelta(seconds=1)
    )
    assert later.name == "dev-20261017T123046Z.yaml"


def test_cli_existing_results_file_exits_1(make_run, tmp_path, monkeypatch):
    root, m = setup_corpus(make_run, tmp_path, "dev")
    import apd_gauntlet.eval.runner as runner

    real = runner.run_eval

    def at_now(*args, **kwargs):
        return real(*args, **{**kwargs, "now": NOW})

    monkeypatch.setattr(runner, "run_eval", at_now)
    assert ev(root, m, "dev").exit_code == 0
    r = ev(root, m, "dev")
    assert r.exit_code == 1 and "exists; not overwritten" in r.output


def test_cli_unwritable_results_exits_1(make_run, tmp_path):
    root, m = setup_corpus(make_run, tmp_path, "dev")
    blocker = tmp_path / "blocker"
    blocker.write_text("a file, not a directory\n")
    r = invoke(m, "--set", "dev", "--evaluator", "findings", "--root", root,
               "--results-dir", blocker / "sub")
    assert r.exit_code == 1 and "cannot write" in r.output


def test_a_file_in_place_of_the_evaluator_directory_cannot_be_written(make_run, tmp_path):
    root, m = setup_corpus(make_run, tmp_path, "dev")
    results = root / "eval/results"
    results.mkdir(parents=True)
    (results / "findings").write_text("not a directory\n")
    with pytest.raises(ResultsWriteError, match="cannot write: Not a directory"):
        run_eval(m, "dev", "findings", root=root, results_dir=results)


def test_a_failed_write_leaves_no_partial_file(make_run, tmp_path, monkeypatch):
    root, m = setup_corpus(make_run, tmp_path, "dev")
    real_open = pathlib.Path.open

    class Full:
        def __init__(self, handle):
            self.handle = handle

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            self.handle.close()

        def write(self, text):
            self.handle.write(text[:10])
            raise OSError(28, "No space left on device")

    def open_(self, mode="r", *args, **kwargs):
        handle = real_open(self, mode, *args, **kwargs)
        return Full(handle) if mode == "x" else handle

    monkeypatch.setattr(pathlib.Path, "open", open_)
    with pytest.raises(ResultsWriteError, match="cannot write: No space left on device"):
        run_eval(m, "dev", "findings", root=root, results_dir=root / "eval/results", now=NOW)
    assert list((root / "eval/results/findings").iterdir()) == []


def test_now_is_written_in_utc(make_run, tmp_path):
    root, m = setup_corpus(make_run, tmp_path, "dev")
    results = root / "eval/results"
    plus2 = datetime(2026, 10, 17, 14, 0, 0, tzinfo=timezone(timedelta(hours=2)))
    path = run_eval(m, "dev", "findings", root=root, results_dir=results, now=plus2)
    assert path.name == "dev-20261017T120000Z.yaml"
    assert yaml.safe_load(path.read_text())["generated_at"] == "2026-10-17T12:00:00Z"
    naive = run_eval(
        m, "dev", "findings", root=root, results_dir=results, now=datetime(2026, 1, 2, 3, 4, 5)
    )
    assert naive.name == "dev-20260102T030405Z.yaml"  # a naive time is taken as UTC


def test_text_output_lists_totals_and_notes(make_run, tmp_path):
    root, m = setup_corpus(make_run, tmp_path, "dev")
    labels = root / "eval/findings/labels/ceb.yaml"
    data = yaml.safe_load(labels.read_text())
    data["items"].append({**data["items"][0], "id": "extra-fp", "verdict": "false_positive"})
    labels.write_text(yaml.safe_dump(data))
    r = ev(root, m, "dev")
    assert r.exit_code == 0, r.output
    assert "1 dev entry" in r.output and "not frozen" in r.output
    assert "  precision.all: 1.0000" in r.output
    assert "note (ceb): 1 false_positive label matches no run finding" in r.output


def test_text_output_reads_n_a_for_a_missing_metric(tmp_path, fake):
    root, m = _fake_corpus(tmp_path, ids=("a",))

    def derive(counts):
        return {"p": None, "q": 0.125}

    fake("ok", lambda entry, labels: EvalResult("a", {}, {}, derive=derive))
    r = invoke(m, "--set", "dev", "--evaluator", "ok", "--root", root)
    assert r.exit_code == 0, r.output
    assert "  p: n/a\n  q: 0.1250\n" in r.output


def test_help_lists_the_exit_codes():
    r = CliRunner().invoke(main, ["eval", "run", "--help"])
    assert r.exit_code == 0
    for text in ("--set", "--evaluator", "--root", "--results-dir", "--json", "eval freeze",
                 "Exits 0", "1 when", "2 when"):
        assert text in r.output, text
