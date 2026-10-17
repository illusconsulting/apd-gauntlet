"""measure.runs: the RunSnapshot loader and the inputs digest."""
from __future__ import annotations

import hashlib
import os
import pathlib
import shutil

import pytest
from apd_gauntlet.measure.runs import RunLoadError, inputs_digest, is_run_dir, load_run

REPO = pathlib.Path(__file__).parent.parent
HA = REPO / "examples/apd-20260612-home-assistant/expected"
CEB = REPO / "examples/apd-20260601-claim-event-bus/expected"
CONF_FINDINGS = "10-trustworthiness/confidentiality.findings.yaml"
CONF_CAPABILITIES = "10-trustworthiness/confidentiality.capabilities.yaml"
ASSET_GRAPH = "40-synthesis/asset-graph.yaml"
REPORT_DATA = "40-synthesis/report-data.yaml"
DEDUPED = "40-synthesis/deduped-findings.yaml"


def test_load_run_home_assistant():
    s = load_run(HA)
    assert len(s.findings) == 94 and len(s.capabilities) == 28
    assert s.graph_targets["avail-4be2dd70"] == ["recorder_history_db"]
    assert len(s.headlines) == 10 and len(s.headlines[1]) == 8      # merged-1119b0be
    assert s.inputs_sha256 is None                                   # expected/ has no inputs/


def test_inputs_digest_changes_with_content(tmp_path):
    (tmp_path / "inputs").mkdir()
    (tmp_path / "inputs/a.md").write_text("x")
    d1 = inputs_digest(tmp_path)
    (tmp_path / "inputs/a.md").write_text("y")
    assert d1 != inputs_digest(tmp_path) and len(d1) == 64


# --- review fixes (Task 1) -------------------------------------------------


@pytest.fixture
def ceb(tmp_path):
    """A writable copy of the claim-event-bus example run."""
    run = tmp_path / "run"
    shutil.copytree(CEB, run, ignore=shutil.ignore_patterns("report-html"))
    return run


def _unreadable(path: pathlib.Path) -> None:
    """chmod ``path`` to 0, or skip when the user can still read it (root)."""
    path.chmod(0)
    if os.access(path, os.R_OK):
        path.chmod(0o755 if path.is_dir() else 0o644)
        pytest.skip("this user can read a mode-0 file")


def _load_error(run: pathlib.Path) -> str:
    with pytest.raises(RunLoadError) as info:
        load_run(run)
    return str(info.value)


def test_inputs_digest_is_the_planned_line_format(tmp_path):
    (tmp_path / "inputs/sub").mkdir(parents=True)
    (tmp_path / "inputs/b.md").write_bytes(b"y")
    (tmp_path / "inputs/sub/a.md").write_bytes(b"x")
    lines = sorted(
        f"{rel}\0{hashlib.sha256(data).hexdigest()}\n"
        for rel, data in (("b.md", b"y"), ("sub/a.md", b"x"))
    )
    assert inputs_digest(tmp_path) == hashlib.sha256("".join(lines).encode()).hexdigest()


def test_inputs_digest_depends_on_paths(tmp_path):
    (tmp_path / "inputs").mkdir()
    (tmp_path / "inputs/a.md").write_text("x")
    d1 = inputs_digest(tmp_path)
    (tmp_path / "inputs/a.md").rename(tmp_path / "inputs/b.md")
    assert d1 != inputs_digest(tmp_path)


def test_is_run_dir(tmp_path):
    assert not is_run_dir(tmp_path)
    (tmp_path / ".apd-run.yaml").mkdir()
    assert not is_run_dir(tmp_path)                                  # a directory is not a run file
    (tmp_path / ".apd-run.yaml").rmdir()
    (tmp_path / ".apd-run.yaml").write_text("run_id: x\n")
    assert is_run_dir(tmp_path)


@pytest.mark.parametrize("rel", [CONF_FINDINGS, CONF_CAPABILITIES])
def test_invalid_yaml_in_corpus_file_names_it(ceb, rel):
    (ceb / rel).write_text("finding: [unclosed\n")
    assert _load_error(ceb).startswith(f"{ceb / rel}: ")


def test_invalid_yaml_in_asset_graph_names_it(ceb):
    (ceb / ASSET_GRAPH).write_text("nodes: [unclosed\n")
    assert _load_error(ceb).startswith(f"{ceb / ASSET_GRAPH}: ")


@pytest.mark.parametrize("body", ["- id: conf-00000001\n", "just a string\n", "42\n"])
def test_corpus_file_without_a_mapping_names_it(ceb, body):
    (ceb / CONF_FINDINGS).write_text(body)
    assert _load_error(ceb).startswith(f"{ceb / CONF_FINDINGS}: ")


@pytest.mark.parametrize("rel", [CONF_FINDINGS, ASSET_GRAPH, REPORT_DATA, DEDUPED])
def test_top_level_list_names_the_file(ceb, rel):
    (ceb / rel).write_text("- a\n- b\n")
    assert _load_error(ceb).startswith(f"{ceb / rel}: ")


@pytest.mark.parametrize("rel", [CONF_FINDINGS, ASSET_GRAPH, REPORT_DATA])
def test_non_utf8_file_names_it(ceb, rel):
    (ceb / rel).write_bytes("title: café\n".encode("latin-1"))
    assert _load_error(ceb).startswith(f"{ceb / rel}: ")


@pytest.mark.parametrize("rel", [CONF_FINDINGS, ASSET_GRAPH])
def test_value_error_from_yaml_names_the_file(ceb, rel):
    (ceb / rel).write_text("reviewed: 2026-02-30\n")             # an impossible date
    assert _load_error(ceb).startswith(f"{ceb / rel}: ")


@pytest.mark.parametrize("rel", [CONF_FINDINGS, ASSET_GRAPH])
def test_unreadable_yaml_names_it(ceb, rel):
    _unreadable(ceb / rel)
    assert _load_error(ceb).startswith(f"{ceb / rel}: ")


def test_unreadable_input_file_names_it(ceb):
    (ceb / "inputs").mkdir()
    (ceb / "inputs/a.md").write_text("x")
    _unreadable(ceb / "inputs/a.md")
    assert _load_error(ceb).startswith(f"{ceb / 'inputs/a.md'}: ")


def test_unreadable_input_directory_names_it(ceb):
    (ceb / "inputs/sub").mkdir(parents=True)
    (ceb / "inputs/sub/a.md").write_text("x")
    _unreadable(ceb / "inputs/sub")
    try:
        assert _load_error(ceb).startswith(f"{ceb / 'inputs/sub'}: ")
    finally:
        (ceb / "inputs/sub").chmod(0o755)                            # let tmp_path clean up


@pytest.mark.parametrize(
    ("rel", "old", "new"),
    [
        (CONF_FINDINGS, "id: conf-7aa376c5", "id: 12345"),
        (CONF_FINDINGS, "id: conf-7aa376c5", "id: [a, b]"),
        (CONF_CAPABILITIES, "id: conf-cap-89e19793", "id: 12345"),
        (CONF_CAPABILITIES, "id: conf-cap-89e19793", "id: [a, b]"),
    ],
)
def test_non_string_record_id_names_the_file(ceb, rel, old, new):
    text = (ceb / rel).read_text(encoding="utf-8")
    assert old in text
    (ceb / rel).write_text(text.replace(old, new, 1), encoding="utf-8")
    assert _load_error(ceb).startswith(f"{ceb / rel}: ")


def test_headline_expansion_keeps_only_string_members(tmp_path):
    synth = tmp_path / "40-synthesis"
    synth.mkdir()
    (synth / "report-data.yaml").write_text(
        "headline_findings:\n"
        "  - {id: merged-00000001, rank: 1}\n"
        "  - {id: merged-00000002, rank: 2}\n"
    )
    (synth / "deduped-findings.yaml").write_text(
        "finding:\n"
        "  - {id: merged-00000001, merged_from: [conf-00000001, null, {a: 1}, 7]}\n"
        "  - {id: merged-00000002, merged_from: [null]}\n"
    )
    assert load_run(tmp_path).headlines == (
        frozenset({"conf-00000001"}),
        frozenset({"merged-00000002"}),                              # no string member: itself
    )
