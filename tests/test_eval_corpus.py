"""eval.corpus: corpus manifests (``eval-corpus``) and label files (``eval-labels``)."""
from __future__ import annotations

import hashlib
import pathlib

import pytest
import yaml
from apd_gauntlet.eval.corpus import (
    Corpus,
    CorpusEntry,
    CorpusError,
    Labels,
    RepoPin,
    load_corpus_manifest,
    load_labels,
)
from apd_gauntlet.resources import read_schema

SCHEMA_ID = "https://github.com/illusconsulting/apd-gauntlet/schemas/"
COMMIT = "a" * 40


def manifest(tmp_path, entries):
    p = tmp_path / "corpus.yaml"
    p.write_text(yaml.safe_dump({"schema_version": 1, "name": "t", "entries": entries}))
    return p


def test_valid_manifest_resolves_paths(tmp_path):
    c = load_corpus_manifest(manifest(tmp_path, [
        {"id": "a", "set": "dev", "run": "runs/a", "labels": "labels/a.yaml"},
        {"id": "b", "set": "heldout",
         "repo": {"url": "https://example.org/r.git", "commit": "a" * 40},
         "labels": "labels/b.yaml"}]))
    assert c.select("dev")[0].run_dir == tmp_path / "runs/a"
    assert c.select("heldout")[0].repo.commit == "a" * 40
    assert len(c.sha256) == 64


def test_same_run_in_both_sets_rejected(tmp_path):
    with pytest.raises(CorpusError, match="'a'.*'b'"):
        load_corpus_manifest(manifest(tmp_path, [
            {"id": "a", "set": "dev", "run": "runs/x", "labels": "l.yaml"},
            {"id": "b", "set": "heldout", "run": "./runs/x", "labels": "l.yaml"}]))


def test_duplicate_id_rejected(tmp_path):
    with pytest.raises(CorpusError, match="duplicate"):
        load_corpus_manifest(manifest(tmp_path, [
            {"id": "a", "set": "dev", "run": "runs/x", "labels": "l.yaml"},
            {"id": "a", "set": "dev", "run": "runs/y", "labels": "l.yaml"}]))


def test_short_commit_rejected(tmp_path):
    with pytest.raises(CorpusError, match="commit"):
        load_corpus_manifest(manifest(tmp_path, [
            {"id": "a", "set": "dev", "repo": {"url": "https://example.org/r.git", "commit": "abc"},
             "labels": "l.yaml"}]))


def test_entry_needs_run_or_repo(tmp_path):
    with pytest.raises(CorpusError, match="'run'.*'repo'"):
        load_corpus_manifest(manifest(tmp_path, [{"id": "a", "set": "dev", "labels": "l.yaml"}]))


def test_findings_labels_use_shared_vocab(tmp_path):
    p = tmp_path / "l.yaml"
    p.write_text(yaml.safe_dump({"schema_version": 1, "kind": "findings", "entry": "a", "items": [
        {"verdict": "true_positive", "apd_goal": "confidentiality", "severity": "info",
         "title": "t" * 10, "evidence": [{"artifact": "a.md", "locator": "#x"}]}]}))
    with pytest.raises(CorpusError, match="severity"):
        load_labels(p)                                    # "info" is the display token, not data


# --- beyond the plan: the manifest ------------------------------------------


def test_schema_ids():
    assert read_schema("eval-corpus.schema.json")["$id"] == SCHEMA_ID + "eval-corpus.schema.json"
    assert read_schema("eval-labels.schema.json")["$id"] == SCHEMA_ID + "eval-labels.schema.json"


def test_manifest_fields(tmp_path):
    p = manifest(tmp_path, [
        {"id": "a", "set": "dev", "run": "runs/a", "labels": "labels/a.yaml", "licence": "MIT"},
        {"id": "b", "set": "heldout",
         "repo": {"url": "https://example.org/r.git", "commit": COMMIT, "path": "examples/x"},
         "labels": "labels/b.yaml"},
        {"id": "c", "set": "dev", "run": "runs/c",
         "repo": {"url": "https://example.org/s.git", "commit": "b" * 40},
         "labels": "labels/c.yaml"},
    ])
    c = load_corpus_manifest(p)
    assert c == Corpus(
        name="t",
        path=p,
        sha256=hashlib.sha256(p.read_bytes()).hexdigest(),
        entries=(
            CorpusEntry("a", "dev", tmp_path / "runs/a", None, tmp_path / "labels/a.yaml"),
            CorpusEntry("b", "heldout", None,
                        RepoPin("https://example.org/r.git", COMMIT, "examples/x"),
                        tmp_path / "labels/b.yaml"),
            CorpusEntry("c", "dev", tmp_path / "runs/c",
                        RepoPin("https://example.org/s.git", "b" * 40, None),
                        tmp_path / "labels/c.yaml"),
        ),
    )


def test_select_keeps_file_order(tmp_path):
    c = load_corpus_manifest(manifest(tmp_path, [
        {"id": "z", "set": "dev", "run": "runs/z", "labels": "l.yaml"},
        {"id": "h", "set": "heldout", "run": "runs/h", "labels": "l.yaml"},
        {"id": "a", "set": "dev", "run": "runs/a", "labels": "l.yaml"}]))
    assert [e.id for e in c.select("dev")] == ["z", "a"]
    assert [e.id for e in c.select("heldout")] == ["h"]
    assert isinstance(c.select("dev"), tuple)


def test_select_refuses_an_unknown_set(tmp_path):
    c = load_corpus_manifest(manifest(tmp_path, [
        {"id": "a", "set": "dev", "run": "runs/a", "labels": "l.yaml"}]))
    with pytest.raises(ValueError, match="'held-out'"):
        c.select("held-out")


def test_an_empty_corpus_loads(tmp_path):
    c = load_corpus_manifest(manifest(tmp_path, []))
    assert c.entries == () and c.select("dev") == () and c.select("heldout") == ()


def test_absolute_run_and_labels_paths_are_kept(tmp_path):
    run, labels = tmp_path / "elsewhere/run", tmp_path / "elsewhere/l.yaml"
    sub = tmp_path / "eval/area"
    sub.mkdir(parents=True)
    (e,) = load_corpus_manifest(manifest(sub, [
        {"id": "a", "set": "dev", "run": str(run), "labels": str(labels)}])).entries
    assert (e.run_dir, e.labels_path) == (run, labels)


def test_paths_resolve_against_the_manifest_directory_not_the_cwd(tmp_path, monkeypatch):
    sub = tmp_path / "eval/area"
    sub.mkdir(parents=True)
    p = manifest(sub, [{"id": "a", "set": "dev", "run": "../../runs/a", "labels": "labels/a.yaml"}])
    monkeypatch.chdir(tmp_path)
    (e,) = load_corpus_manifest(pathlib.Path("eval/area/corpus.yaml")).entries
    assert e.run_dir == pathlib.Path("eval/area/../../runs/a")
    assert e.labels_path == pathlib.Path("eval/area/labels/a.yaml")
    assert e.run_dir.resolve() == (tmp_path / "runs/a").resolve()
    assert load_corpus_manifest(p).entries[0].labels_path == sub / "labels/a.yaml"


def test_same_repo_commit_in_both_sets_rejected(tmp_path):
    repo = {"url": "https://example.org/r.git", "commit": COMMIT}
    with pytest.raises(CorpusError) as exc:
        load_corpus_manifest(manifest(tmp_path, [
            {"id": "a", "set": "heldout", "repo": repo, "labels": "l.yaml"},
            {"id": "b", "set": "dev", "repo": {**repo, "path": "sub"}, "labels": "l.yaml"}]))
    message = str(exc.value)
    assert "'a' (heldout)" in message and "'b' (dev)" in message
    assert f"https://example.org/r.git at {COMMIT}" in message


def test_same_repo_at_another_commit_is_allowed(tmp_path):
    c = load_corpus_manifest(manifest(tmp_path, [
        {"id": "a", "set": "dev", "repo": {"url": "https://example.org/r.git", "commit": COMMIT},
         "labels": "l.yaml"},
        {"id": "b", "set": "heldout",
         "repo": {"url": "https://example.org/r.git", "commit": "b" * 40}, "labels": "l.yaml"}]))
    assert [e.id for e in c.entries] == ["a", "b"]


def test_the_disjoint_rule_compares_sets_not_entries(tmp_path):
    repo = {"url": "https://example.org/r.git", "commit": COMMIT}
    c = load_corpus_manifest(manifest(tmp_path, [
        {"id": "a", "set": "dev", "run": "runs/x", "repo": repo, "labels": "l.yaml"},
        {"id": "b", "set": "dev", "run": "runs/x", "repo": repo, "labels": "l.yaml"}]))
    assert len(c.select("dev")) == 2


def test_run_and_repo_are_checked_separately(tmp_path):
    repo = {"url": "https://example.org/r.git", "commit": COMMIT}
    with pytest.raises(CorpusError, match=r"'a' \(dev\) and 'b' \(heldout\) both pin"):
        load_corpus_manifest(manifest(tmp_path, [
            {"id": "a", "set": "dev", "run": "runs/a", "repo": repo, "labels": "l.yaml"},
            {"id": "b", "set": "heldout", "run": "runs/b", "repo": repo, "labels": "l.yaml"}]))


def test_run_paths_are_compared_after_resolving(tmp_path):
    (tmp_path / "runs/x").mkdir(parents=True)
    (tmp_path / "link").symlink_to(tmp_path / "runs/x", target_is_directory=True)
    for other in ("other/../runs/x", "link", str(tmp_path / "runs/x")):
        with pytest.raises(CorpusError) as exc:
            load_corpus_manifest(manifest(tmp_path, [
                {"id": "a", "set": "dev", "run": "runs/x", "labels": "l.yaml"},
                {"id": "b", "set": "heldout", "run": other, "labels": "l.yaml"}]))
        assert f"both use run {(tmp_path / 'runs/x').resolve()}" in str(exc.value)


def test_a_run_that_cannot_be_resolved_is_refused(tmp_path):
    (tmp_path / "loop").symlink_to("loop")
    try:
        (tmp_path / "loop").resolve()
    except RuntimeError:
        pass
    else:
        pytest.skip("this Python resolves a link loop without raising")
    p = manifest(tmp_path, [{"id": "a", "set": "dev", "run": "loop", "labels": "l.yaml"}])
    with pytest.raises(CorpusError) as exc:
        load_corpus_manifest(p)
    assert str(exc.value).startswith(f"{p}: $.entries[0].run: cannot resolve {tmp_path / 'loop'}: ")

def test_disjoint_message_names_the_file_and_the_rule(tmp_path):
    p = manifest(tmp_path, [
        {"id": "a", "set": "dev", "run": "runs/x", "labels": "l.yaml"},
        {"id": "b", "set": "heldout", "run": "runs/x", "labels": "l.yaml"}])
    with pytest.raises(CorpusError) as exc:
        load_corpus_manifest(p)
    assert str(exc.value).startswith(f"{p}: entries 'a' (dev) and 'b' (heldout) both use run ")
    assert "disjoint" in str(exc.value)


def test_duplicate_id_message_names_both_entries(tmp_path):
    p = manifest(tmp_path, [
        {"id": "a", "set": "dev", "run": "runs/x", "labels": "l.yaml"},
        {"id": "b", "set": "dev", "run": "runs/y", "labels": "l.yaml"},
        {"id": "a", "set": "heldout", "run": "runs/z", "labels": "l.yaml"}])
    with pytest.raises(CorpusError) as exc:
        load_corpus_manifest(p)
    assert str(exc.value) == f"{p}: duplicate entry id 'a' ($.entries[0] and $.entries[2])"


def test_schema_messages_carry_the_file_and_json_path(tmp_path):
    p = manifest(tmp_path, [
        {"id": "a", "set": "dev", "repo": {"url": "https://example.org/r.git", "commit": "abc"},
         "labels": "l.yaml"}])
    with pytest.raises(CorpusError) as exc:
        load_corpus_manifest(p)
    assert str(exc.value) == (
        f"{p}: invalid corpus manifest: $.entries[0].repo.commit: "
        "'abc' does not match '^[0-9a-f]{40}$'"
    )


def test_every_schema_message_is_listed(tmp_path):
    p = manifest(tmp_path, [
        {"id": "A", "set": "dev", "run": "r", "labels": "l.yaml"},
        {"id": "b", "set": "test", "run": "r", "labels": "l.yaml"}])
    with pytest.raises(CorpusError) as exc:
        load_corpus_manifest(p)
    assert "$.entries[0].id: " in str(exc.value) and "$.entries[1].set: " in str(exc.value)


def _entry(**changes):
    entry = {"id": "a", "set": "dev", "run": "runs/a", "labels": "l.yaml"}
    entry.update(changes)
    return {k: v for k, v in entry.items() if v is not None}


@pytest.mark.parametrize(
    ("doc", "where"),
    [
        ({"schema_version": 2, "name": "t", "entries": []}, "$.schema_version"),
        ({"schema_version": True, "name": "t", "entries": []}, "$.schema_version"),
        ({"schema_version": 1, "name": "T", "entries": []}, "$.name"),
        ({"schema_version": 1, "name": "-t", "entries": []}, "$.name"),
        ({"schema_version": 1, "name": "t"}, "$"),
        ({"schema_version": 1, "entries": []}, "$"),
        ({"schema_version": 1, "name": "t", "entries": [], "extra": 1}, "$"),
        ({"schema_version": 1, "name": "t", "entries": {}}, "$.entries"),
        ({"schema_version": 1, "name": "t", "entries": [], "description": 5}, "$.description"),
        ({"schema_version": 1, "name": "t", "entries": [_entry(id="a_b")]}, "$.entries[0].id"),
        ({"schema_version": 1, "name": "t", "entries": [_entry(set="test")]}, "$.entries[0].set"),
        ({"schema_version": 1, "name": "t", "entries": [_entry(run="")]}, "$.entries[0].run"),
        ({"schema_version": 1, "name": "t", "entries": [_entry(labels="")]},
         "$.entries[0].labels"),
        ({"schema_version": 1, "name": "t", "entries": [_entry(labels=None)]}, "$.entries[0]"),
        ({"schema_version": 1, "name": "t", "entries": [_entry(licence="")]},
         "$.entries[0].licence"),
        ({"schema_version": 1, "name": "t", "entries": [_entry(extra="x")]}, "$.entries[0]"),
        ({"schema_version": 1, "name": "t", "entries": [_entry(repo={"commit": COMMIT})]},
         "$.entries[0].repo"),
        ({"schema_version": 1, "name": "t",
          "entries": [_entry(repo={"url": "u", "commit": "A" * 40})]},
         "$.entries[0].repo.commit"),
        ({"schema_version": 1, "name": "t",
          "entries": [_entry(repo={"url": "u", "commit": COMMIT, "branch": "main"})]},
         "$.entries[0].repo"),
        ({"schema_version": 1, "name": "t",
          "entries": [_entry(repo={"url": "u", "commit": COMMIT, "path": ""})]},
         "$.entries[0].repo.path"),
        ([], "$"),
        (None, "$"),
    ],
    ids=[
        "schema-version-2", "schema-version-true", "name-upper", "name-leading-dash",
        "no-entries", "no-name", "extra-top-key", "entries-mapping", "description-number",
        "id-underscore", "set-unknown", "run-empty", "labels-empty", "labels-missing",
        "licence-empty", "extra-entry-key", "repo-no-url", "commit-upper", "extra-repo-key",
        "repo-path-empty", "top-level-list", "empty-file",
    ],
)
def test_invalid_manifests_are_refused(tmp_path, doc, where):
    p = tmp_path / "corpus.yaml"
    p.write_text(yaml.safe_dump(doc))
    with pytest.raises(CorpusError) as exc:
        load_corpus_manifest(p)
    assert str(exc.value).startswith(f"{p}: invalid corpus manifest: {where}: ")


@pytest.mark.parametrize(
    ("content", "problem"),
    [
        (b"schema_version: 1\nentries: [\n", "invalid YAML"),
        (b"schema_version: 2026-02-30\n", "invalid YAML"),
        (b"[" * 5000, "invalid YAML: nested too deeply to parse"),
        (b"\xff\xfeschema_version: 1\n", "not UTF-8 text"),
    ],
    ids=["unclosed", "impossible-date", "deep-nesting", "not-utf8"],
)
def test_unparseable_files_are_refused(tmp_path, content, problem):
    p = tmp_path / "f.yaml"
    p.write_bytes(content)
    for load in (load_corpus_manifest, load_labels):
        with pytest.raises(CorpusError) as exc:
            load(p)
        assert str(exc.value).startswith(f"{p}: {problem}")


@pytest.mark.parametrize(
    "make", [lambda d: d / "missing.yaml", lambda d: d], ids=["missing", "directory"]
)
def test_unreadable_files_are_refused(tmp_path, make):
    p = make(tmp_path)
    for load in (load_corpus_manifest, load_labels):
        with pytest.raises(CorpusError) as exc:
            load(p)
        assert str(exc.value).startswith(f"{p}: cannot read: ")


# --- beyond the plan: labels -------------------------------------------------


FINDING_ITEM = {
    "id": "conf-98a543cd", "verdict": "true_positive", "apd_goal": "confidentiality",
    "severity": "high", "title": "Tokens are logged",
    "evidence": [{"artifact": "inputs/a.md", "locator": "#x", "excerpt": "tokens"}],
    "note": "seen in the log",
}
FINDINGS = {"schema_version": 1, "kind": "findings", "entry": "ceb", "items": [FINDING_ITEM]}
DECISIONS = {
    "schema_version": 1, "kind": "decisions", "set": "dev", "task": "finding-qa.unsupported",
    "records": [{"path": "run/40-synthesis/decisions/finding-qa.10-trustworthiness.yaml",
                 "items": [{"ref": "conf-00000001", "gold": True},
                           {"ref": "conf-00000002", "gold": False}]}],
}


def write(tmp_path, doc):
    p = tmp_path / "labels.yaml"
    p.write_text(yaml.safe_dump(doc, sort_keys=False))
    return p


@pytest.mark.parametrize("doc", [FINDINGS, DECISIONS], ids=["findings", "decisions"])
def test_labels_load(tmp_path, doc):
    p = write(tmp_path, doc)
    assert load_labels(p) == Labels(
        kind=doc["kind"], path=p, sha256=hashlib.sha256(p.read_bytes()).hexdigest(), data=doc
    )


def test_minimal_findings_labels_load(tmp_path):
    item = {"verdict": "unreviewed", "apd_goal": "non_repudiation", "severity": "informational",
            "title": "t", "evidence": [{"artifact": "a", "locator": "b"}]}
    labels = load_labels(write(tmp_path, {**FINDINGS, "items": [item]}))
    assert labels.data["items"] == [item]                 # unreviewed is the evaluator's refusal
    assert load_labels(write(tmp_path, {**FINDINGS, "items": []})).data["items"] == []


@pytest.mark.parametrize("task", ["finding-qa", "finding-qa.lens_drift", "cluster-pairs", "a.b2_c"])
def test_decision_task_names_accepted(tmp_path, task):
    assert load_labels(write(tmp_path, {**DECISIONS, "task": task})).data["task"] == task


def test_a_bad_item_reports_its_own_path(tmp_path):
    bad = {**FINDING_ITEM, "severity": "info"}
    p = write(tmp_path, {**FINDINGS, "items": [FINDING_ITEM, FINDING_ITEM, bad]})
    with pytest.raises(CorpusError) as exc:
        load_labels(p)
    assert str(exc.value).startswith(f"{p}: invalid labels: $.items[2].severity: 'info' is not one")
    assert "is not valid under" not in str(exc.value)


def test_label_vocabularies_come_from_defs():
    item = read_schema("eval-labels.schema.json")["$defs"]["finding_label"]["properties"]
    assert item["apd_goal"] == {"$ref": "_defs.schema.json#/$defs/apd_goal"}
    assert item["severity"] == {"$ref": "_defs.schema.json#/$defs/severity"}


def _item(**changes):
    item = dict(FINDING_ITEM)
    item.update(changes)
    return {k: v for k, v in item.items() if v is not None}


def _record(**changes):
    record = dict(DECISIONS["records"][0])
    record.update(changes)
    return record


@pytest.mark.parametrize(
    ("doc", "where"),
    [
        ({**FINDINGS, "schema_version": 2}, "$.schema_version"),
        ({**FINDINGS, "kind": "iac"}, "$.kind"),
        ({k: v for k, v in FINDINGS.items() if k != "kind"}, "$"),
        ({k: v for k, v in FINDINGS.items() if k != "entry"}, "$"),
        ({**FINDINGS, "entry": ""}, "$.entry"),
        ({**FINDINGS, "set": "dev"}, "$"),
        ({**FINDINGS, "items": {}}, "$.items"),
        ({**FINDINGS, "items": [_item(verdict="maybe")]}, "$.items[0].verdict"),
        ({**FINDINGS, "items": [_item(apd_goal="privacy")]}, "$.items[0].apd_goal"),
        ({**FINDINGS, "items": [_item(title="")]}, "$.items[0].title"),
        ({**FINDINGS, "items": [_item(title=None)]}, "$.items[0]"),
        ({**FINDINGS, "items": [_item(id="")]}, "$.items[0].id"),
        ({**FINDINGS, "items": [_item(evidence=[])]}, "$.items[0].evidence"),
        ({**FINDINGS, "items": [_item(evidence=[{"artifact": "a"}])]},
         "$.items[0].evidence[0]"),
        ({**FINDINGS, "items": [_item(evidence=[{"artifact": "a", "locator": ""}])]},
         "$.items[0].evidence[0].locator"),
        ({**FINDINGS, "items": [_item(evidence=[{"artifact": "a", "locator": "b", "x": 1}])]},
         "$.items[0].evidence[0]"),
        ({**FINDINGS, "items": [_item(confidence="high")]}, "$.items[0]"),
        ({**FINDINGS, "items": [_item(note=3)]}, "$.items[0].note"),
        ({**DECISIONS, "set": "test"}, "$.set"),
        ({k: v for k, v in DECISIONS.items() if k != "set"}, "$"),
        ({**DECISIONS, "task": "Finding-QA"}, "$.task"),
        ({**DECISIONS, "task": "finding-qa."}, "$.task"),
        ({**DECISIONS, "task": "finding-qa.a.b"}, "$.task"),
        ({**DECISIONS, "task": "finding-qa.lens-drift"}, "$.task"),
        ({**DECISIONS, "records": []}, "$.records"),
        ({**DECISIONS, "entry": "ceb"}, "$"),
        ({**DECISIONS, "records": [_record(items=[])]}, "$.records[0].items"),
        ({**DECISIONS, "records": [_record(path="")]}, "$.records[0].path"),
        ({**DECISIONS, "records": [_record(extra=1)]}, "$.records[0]"),
        ({**DECISIONS, "records": [_record(items=[{"ref": "x", "gold": "yes"}])]},
         "$.records[0].items[0].gold"),
        ({**DECISIONS, "records": [_record(items=[{"ref": "", "gold": True}])]},
         "$.records[0].items[0].ref"),
        ({**DECISIONS, "records": [_record(items=[{"ref": "x"}])]}, "$.records[0].items[0]"),
        ({**DECISIONS, "records": [_record(items=[{"ref": "x", "gold": True, "p": 0.5}])]},
         "$.records[0].items[0]"),
        ([], "$"),
        (None, "$"),
    ],
    ids=[
        "schema-version-2", "kind-unknown", "kind-missing", "entry-missing", "entry-empty",
        "findings-with-set", "items-mapping", "verdict-unknown", "goal-unknown", "title-empty",
        "title-missing", "id-empty", "evidence-empty", "evidence-no-locator",
        "evidence-locator-empty", "evidence-extra-key", "item-extra-key", "note-number",
        "set-unknown", "set-missing", "task-upper", "task-trailing-dot", "task-two-dots",
        "task-dash-after-dot", "records-empty", "decisions-with-entry", "record-items-empty",
        "record-path-empty", "record-extra-key", "gold-string", "ref-empty", "gold-missing",
        "decision-item-extra-key", "top-level-list", "empty-file",
    ],
)
def test_invalid_labels_are_refused(tmp_path, doc, where):
    p = write(tmp_path, doc)
    with pytest.raises(CorpusError) as exc:
        load_labels(p)
    assert str(exc.value).startswith(f"{p}: invalid labels: {where}: ")


def test_messages_follow_document_order(tmp_path):
    bad = {**FINDING_ITEM, "verdict": "maybe"}
    items = [FINDING_ITEM] * 11
    items[2], items[10] = bad, bad
    with pytest.raises(CorpusError) as exc:
        load_labels(write(tmp_path, {**FINDINGS, "items": items}))
    message = str(exc.value)
    assert message.index("$.items[2].verdict") < message.index("$.items[10].verdict")


def test_a_message_is_listed_once(tmp_path):
    p = write(tmp_path, [])
    with pytest.raises(CorpusError) as exc:
        load_labels(p)
    assert str(exc.value) == f"{p}: invalid labels: $: [] is not of type 'object'"


def test_the_first_entry_of_a_set_is_named(tmp_path):
    with pytest.raises(CorpusError, match=r"entries 'a' \(dev\) and 'c' \(heldout\)"):
        load_corpus_manifest(manifest(tmp_path, [
            {"id": "a", "set": "dev", "run": "runs/x", "labels": "l.yaml"},
            {"id": "b", "set": "dev", "run": "runs/x", "labels": "l.yaml"},
            {"id": "c", "set": "heldout", "run": "runs/x", "labels": "l.yaml"}]))
