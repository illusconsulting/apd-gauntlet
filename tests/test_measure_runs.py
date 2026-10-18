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


# --- review fixes (Task 1, second round) ------------------------------------


@pytest.mark.parametrize("new", ["id: 12345", "id: [a, b]"])
@pytest.mark.parametrize(
    ("rel", "singular", "plural", "old"),
    [
        (CONF_FINDINGS, "finding:\n", "findings:\n", "id: conf-7aa376c5"),
        (CONF_CAPABILITIES, "capability:\n", "capabilities:\n", "id: conf-cap-89e19793"),
    ],
)
def test_non_string_record_id_under_a_plural_root_names_the_file(
    ceb, rel, singular, plural, old, new
):
    text = (ceb / rel).read_text(encoding="utf-8")
    assert text.startswith(singular) and old in text
    text = plural + text[len(singular):]
    (ceb / rel).write_text(text.replace(old, new, 1), encoding="utf-8")
    assert _load_error(ceb).startswith(f"{ceb / rel}: ")


@pytest.mark.parametrize("rel", [CONF_FINDINGS, ASSET_GRAPH, REPORT_DATA])
def test_yaml_nested_too_deeply_names_the_file(ceb, rel):
    (ceb / rel).write_text("[" * 5000)
    assert _load_error(ceb).startswith(f"{ceb / rel}: ")


def test_headlines_rank_order_puts_unranked_and_boolean_ranks_last(tmp_path):
    synth = tmp_path / "40-synthesis"
    synth.mkdir()
    (synth / "report-data.yaml").write_text(
        "headline_findings:\n"
        "  - {id: conf-0000000u}\n"
        "  - {id: conf-0000000t, rank: true}\n"
        "  - {id: conf-00000002, rank: 2}\n"
        "  - {id: conf-00000001, rank: 1}\n"
    )
    (synth / "deduped-findings.yaml").write_text("finding: []\n")
    assert load_run(tmp_path).headlines == (
        frozenset({"conf-00000001"}),
        frozenset({"conf-00000002"}),
        frozenset({"conf-0000000u"}),                                # unranked, in file order
        frozenset({"conf-0000000t"}),                                # rank: true is not a rank
    )


def test_inputs_digest_records_where_a_directory_link_points(tmp_path):
    inputs = tmp_path / "inputs"
    for sub, data in (("v1", b"x"), ("v2", b"y")):
        (inputs / sub).mkdir(parents=True)
        (inputs / sub / "a.md").write_bytes(data)
    (inputs / "docs").symlink_to("v1", target_is_directory=True)
    d1 = inputs_digest(tmp_path)
    (inputs / "docs").unlink()
    (inputs / "docs").symlink_to("v2", target_is_directory=True)
    assert d1 != inputs_digest(tmp_path)


def test_inputs_digest_records_a_dangling_link(tmp_path):
    (tmp_path / "inputs").mkdir()
    (tmp_path / "inputs/a.md").write_bytes(b"x")
    d1 = inputs_digest(tmp_path)
    (tmp_path / "inputs/gone.md").symlink_to("missing.md")
    assert d1 != inputs_digest(tmp_path)


def test_inputs_digest_link_line_format(tmp_path):
    # "docs\0link:v1\n" + "v1/a.md\0<sha256 of b'x'>\n", sorted, then hashed.
    (tmp_path / "inputs/v1").mkdir(parents=True)
    (tmp_path / "inputs/v1/a.md").write_bytes(b"x")
    (tmp_path / "inputs/docs").symlink_to("v1", target_is_directory=True)
    assert inputs_digest(tmp_path) == (
        "fd2a8f3754e4007c59c93aa945d52a2e1ed4cda578d367db5fd04afaa9951033"
    )


def test_inputs_digest_hashes_a_file_link_by_its_content(tmp_path):
    # A link to a file is a file under inputs/: "b.md\0<sha256 of b'x'>\n", as for a.md.
    (tmp_path / "inputs").mkdir()
    (tmp_path / "inputs/a.md").write_bytes(b"x")
    (tmp_path / "inputs/b.md").symlink_to("a.md")
    assert inputs_digest(tmp_path) == (
        "07633a50b835c0c1596c85c8e9ed691c854de637a40e991282948b6f107f4ac4"
    )


def test_inputs_digest_sorts_its_lines(tmp_path):
    # os.walk yields z.md before a/x.md; sorted order is a/x.md first.
    (tmp_path / "inputs/a").mkdir(parents=True)
    (tmp_path / "inputs/z.md").write_bytes(b"y")
    (tmp_path / "inputs/a/x.md").write_bytes(b"x")
    assert inputs_digest(tmp_path) == (
        "272b831d626f8e48773c85ace36212bac6514e8247756e43d693aa9177329799"
    )


def test_inputs_digest_counts_dotfiles(tmp_path):
    (tmp_path / "inputs").mkdir()
    (tmp_path / "inputs/a.md").write_bytes(b"x")
    d1 = inputs_digest(tmp_path)
    (tmp_path / "inputs/.terraform.lock.hcl").write_bytes(b"x")
    assert d1 != inputs_digest(tmp_path)


@pytest.mark.parametrize("rel", [REPORT_DATA, DEDUPED])
def test_headlines_are_none_without_report_data_or_deduped_findings(ceb, rel):
    assert len(load_run(ceb).headlines) == 7
    (ceb / rel).unlink()
    assert load_run(ceb).headlines is None


def test_graph_targets_are_empty_without_an_asset_graph(ceb):
    assert load_run(ceb).graph_targets
    (ceb / ASSET_GRAPH).unlink()
    assert load_run(ceb).graph_targets == {}


@pytest.mark.parametrize(("rel", "field", "empty"), [
    (REPORT_DATA, "headlines", ()),          # both files exist, no headline: empty, not None
    (ASSET_GRAPH, "graph_targets", {}),
])
def test_empty_synthesis_file_reads_as_empty(ceb, rel, field, empty):
    (ceb / rel).write_text("")
    assert getattr(load_run(ceb), field) == empty


def test_load_run_maps_capability_edges():
    assert load_run(HA).graph_targets["intg-cap-7a54b1a7"] == ["user_credentials_store"]


def test_graph_targets_list_each_node_once_in_edge_order(tmp_path):
    synth = tmp_path / "40-synthesis"
    synth.mkdir()
    (synth / "asset-graph.yaml").write_text(
        "nodes:\n"
        "  - {node_id: n1, name: token_store}\n"
        "  - {node_id: n2, name: audit_log}\n"
        "edges:\n"
        "  - {from: x, to: n2, finding_id: conf-00000001}\n"
        "  - {from: x, to: n1, finding_id: conf-00000001}\n"
        "  - {from: y, to: n2, finding_id: conf-00000001}\n"
        "  - {from: y, to: n1, capability_id: conf-cap-00000001}\n"
    )
    assert load_run(tmp_path).graph_targets == {
        "conf-00000001": ["audit_log", "token_store"],
        "conf-cap-00000001": ["token_store"],
    }


def test_load_corpus_failure_with_no_file_at_fault_is_re_raised(ceb, monkeypatch):
    def boom(*_args, **_kwargs):
        raise OSError("disk went away")

    monkeypatch.setattr("apd_gauntlet.measure.runs.load_corpus", boom)
    with pytest.raises(OSError, match="disk went away"):
        load_run(ceb)
