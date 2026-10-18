"""eval.metamorphic: the suite registry, the invariance runner and ``metamorphic run``."""
from __future__ import annotations

import json
import shutil
from dataclasses import replace
from pathlib import Path

import pytest
from apd_gauntlet.cli import main
from apd_gauntlet.eval.metamorphic import (
    BUILTIN_SUITE_MODULES,
    SUITES,
    CaseResult,
    MetamorphicError,
    Suite,
    get_suite,
    load_builtin_suites,
    register_suite,
    run_suite,
)
from click.testing import CliRunner

REPO = Path(__file__).resolve().parent.parent


def test_stride_suite_holds_end_to_end():
    r = CliRunner().invoke(
        main, ["metamorphic", "run", "--suite", "stride-table", "--root", str(REPO), "--json"]
    )
    assert r.exit_code == 0
    assert sorted((c["transform"], c["status"]) for c in json.loads(r.stdout)["cases"]) == [
        ("rename-elements", "holds"), ("reorder-columns", "holds"), ("reorder-rows", "holds")]


def drop_last_row(src, dst):
    shutil.copytree(src, dst, dirs_exist_ok=True)
    p = dst / "threat-model.md"
    p.write_text("\n".join(p.read_text().splitlines()[:-1]) + "\n")
    return {}


def test_violation_detected(tmp_path, monkeypatch):
    load_builtin_suites()
    base = SUITES["stride-table"]
    monkeypatch.setitem(
        SUITES, "t-drop", replace(base, name="t-drop", transforms={"drop-last-row": drop_last_row})
    )
    (case,) = run_suite(SUITES["t-drop"], REPO, tmp_path)
    assert case.status == "violated" and len(case.missing) == 1 and case.extra == ()
    assert case.missing[0][0] == "audit-log-writer"


def test_allowlisted_violation(tmp_path):
    load_builtin_suites()
    base = SUITES["stride-table"]
    suite = replace(
        base, name="t-drop", transforms={"drop-last-row": drop_last_row},
        known_non_invariant={("drop-last-row", base.fixtures[0]): "demo"},
    )
    (case,) = run_suite(suite, REPO, tmp_path)
    assert case.status == "allowlisted"


def test_stale_allowlist(tmp_path):
    load_builtin_suites()
    base = SUITES["stride-table"]
    suite = replace(base, known_non_invariant={("reorder-rows", base.fixtures[0]): "demo"})
    statuses = {c.transform: c.status for c in run_suite(suite, REPO, tmp_path)}
    assert statuses["reorder-rows"] == "stale_allowlist"


def test_unknown_suite_exits_2():
    r = CliRunner().invoke(main, ["metamorphic", "run", "--suite", "nope", "--root", str(REPO)])
    assert r.exit_code == 2 and "stride-table" in r.output


# --- beyond the plan ---------------------------------------------------------

FIXTURE = "tests/fixtures/metamorphic/stride-table/basic"


def _stride():
    load_builtin_suites()
    return SUITES["stride-table"]


def _suite(**changes):
    """The stride-table suite, named ``t-suite`` unless ``changes`` names it, with ``changes``."""
    changes.setdefault("name", "t-suite")
    return replace(_stride(), **changes)


def _invoke(*args):
    return CliRunner().invoke(main, ["metamorphic", "run", *args])


def _data_rows(path):
    lines = [ln for ln in path.read_text(encoding="utf-8").splitlines() if ln.startswith("|")]
    return [[c.strip() for c in ln.split("|")[1:-1]] for ln in lines[2:]]


def _header(path):
    line = next(ln for ln in path.read_text(encoding="utf-8").splitlines() if ln.startswith("|"))
    return [c.strip() for c in line.split("|")[1:-1]]


def test_fixture_is_a_byte_copy_of_the_sample_stride_table():
    sample = REPO / "tests/fixtures/threat_models/sample-stride-table.md"
    assert (REPO / FIXTURE / "threat-model.md").read_bytes() == sample.read_bytes()


def test_builtin_suite_registration():
    from apd_gauntlet.eval.suites import stride_table

    assert BUILTIN_SUITE_MODULES == ("apd_gauntlet.eval.suites.stride_table",)
    load_builtin_suites()
    load_builtin_suites()  # a second call changes nothing
    assert SUITES["stride-table"] is stride_table.SUITE
    suite = SUITES["stride-table"]
    assert suite.fixtures == (FIXTURE,)
    assert set(suite.transforms) == {"rename-elements", "reorder-columns", "reorder-rows"}
    assert dict(suite.known_non_invariant) == {}


def test_extract_reads_every_stride_entry():
    from apd_gauntlet.eval.suites.stride_table import extract

    rs = extract(REPO / FIXTURE)
    assert len(rs) == 10
    assert {t[0] for t in rs} == {"claim-ingress-API", "adjudication-service", "audit-log-writer"}
    assert {t[1] for t in rs} == set("STRIDE")
    assert all(len(t) == 4 and all(isinstance(x, str) and x for x in t) for t in rs)
    (audit,) = [t for t in rs if t[0] == "audit-log-writer"]
    assert audit[1] == "R" and audit[2].startswith("Audit entry deletion")


def test_normalise_maps_only_the_asset():
    from apd_gauntlet.eval.suites.stride_table import normalise

    rs = frozenset({("element-1", "S", "element-1 spoofed", "authenticity"), ("x", "T", "t", "")})
    assert normalise(rs, {"element-1": "api"}) == frozenset(
        {("api", "S", "element-1 spoofed", "authenticity"), ("x", "T", "t", "")})


def test_rename_elements_writes_numbered_elements(tmp_path):
    from apd_gauntlet.eval.suites.stride_table import extract, normalise, rename_elements

    src = REPO / FIXTURE
    rename = rename_elements(src, tmp_path)
    assert rename == {"element-1": "claim-ingress-API", "element-2": "adjudication-service",
                      "element-3": "audit-log-writer"}
    copy = tmp_path / "threat-model.md"
    assert [row[0] for row in _data_rows(copy)] == ["element-1", "element-2", "element-3"]
    original = _data_rows(src / "threat-model.md")
    assert [row[1:] for row in _data_rows(copy)] == [row[1:] for row in original]
    assert {t[0] for t in extract(tmp_path)} == {"element-1", "element-2", "element-3"}
    assert normalise(extract(tmp_path), rename) == extract(src)


def test_reorder_rows_reverses_the_data_rows(tmp_path):
    from apd_gauntlet.eval.suites.stride_table import reorder_rows

    src = REPO / FIXTURE / "threat-model.md"
    assert reorder_rows(REPO / FIXTURE, tmp_path) == {}
    copy = tmp_path / "threat-model.md"
    assert _data_rows(copy) == _data_rows(src)[::-1]
    assert _header(copy) == _header(src)
    original = src.read_text(encoding="utf-8").splitlines()
    assert copy.read_text(encoding="utf-8").splitlines()[:4] == original[:4]  # heading and header


def test_reorder_columns_reverses_the_stride_columns(tmp_path):
    from apd_gauntlet.eval.suites.stride_table import reorder_columns

    src = REPO / FIXTURE / "threat-model.md"
    assert reorder_columns(REPO / FIXTURE, tmp_path) == {}
    copy = tmp_path / "threat-model.md"
    assert _header(copy) == ["Element", "E", "D", "I", "R", "T", "S"]
    assert _data_rows(copy) == [[row[0], *row[:0:-1]] for row in _data_rows(src)]
    separator = copy.read_text(encoding="utf-8").splitlines()[3]
    assert separator == "|---------|---|---|---|---|---|---|"


def test_transforms_copy_every_file_and_leave_the_source_alone(tmp_path):
    src = tmp_path / "src"
    shutil.copytree(REPO / FIXTURE, src)
    (src / "notes").mkdir()
    (src / "notes" / "extra.txt").write_text("kept\n", encoding="utf-8")
    before = (src / "threat-model.md").read_bytes()
    for name, transform in sorted(_stride().transforms.items()):
        dst = tmp_path / name
        dst.mkdir()
        transform(src, dst)
        assert (dst / "notes" / "extra.txt").read_text(encoding="utf-8") == "kept\n"
        assert (dst / "threat-model.md").read_bytes() != before
    assert (src / "threat-model.md").read_bytes() == before


def test_transforms_keep_crlf_and_a_missing_final_newline(tmp_path):
    from apd_gauntlet.eval.suites.stride_table import extract

    src = tmp_path / "src"
    src.mkdir()
    text = (REPO / FIXTURE / "threat-model.md").read_text(encoding="utf-8")
    (src / "threat-model.md").write_bytes(text.rstrip("\n").replace("\n", "\r\n").encode())
    for name, transform in sorted(_stride().transforms.items()):
        dst = tmp_path / name
        dst.mkdir()
        transform(src, dst)
        data = (dst / "threat-model.md").read_bytes()
        assert data.count(b"\r\n") == text.count("\n") - 1 and not data.endswith(b"\n")
        assert len(extract(dst)) == 10


@pytest.mark.parametrize("bad", [
    "# no table here\n",
    "| Element | S | T | R | I | D | E |\n|---|---|---|---|---|---|---|\n",
    "| Element | S | T |\n|---|---|---|\n| api | x | y |\n",
    "| Element | S | T | R | I | D | E |\n|---|---|---|---|---|---|---|\n"
    "|  | a | — | — | — | — | — |\n",
])
def test_transforms_refuse_a_table_they_cannot_transform(tmp_path, bad):
    src = tmp_path / "src"
    src.mkdir()
    (src / "threat-model.md").write_text(bad, encoding="utf-8")
    for name, transform in sorted(_stride().transforms.items()):
        dst = tmp_path / name
        dst.mkdir()
        with pytest.raises(MetamorphicError, match="threat-model.md"):
            transform(src, dst)


def test_holding_cases_in_transform_order_with_the_workdir_layout(tmp_path):
    cases = run_suite(_stride(), REPO, tmp_path)
    assert cases == [
        CaseResult(FIXTURE, name, "holds", (), (), None)
        for name in ("rename-elements", "reorder-columns", "reorder-rows")
    ]
    for name in ("rename-elements", "reorder-columns", "reorder-rows"):
        assert (tmp_path / "basic" / name / "threat-model.md").is_file()


def test_untouched_fixture_is_extracted_once_from_root(tmp_path):
    seen = []
    base = _stride()

    def extract(d):
        seen.append(d)
        return base.extract(d)

    run_suite(_suite(extract=extract), REPO, tmp_path)
    assert seen[0] == REPO / FIXTURE
    assert seen[1:] == [tmp_path / "basic" / n
                        for n in ("rename-elements", "reorder-columns", "reorder-rows")]


def add_row(src, dst):
    shutil.copytree(src, dst, dirs_exist_ok=True)
    p = dst / "threat-model.md"
    p.write_text(p.read_text() + "| new-asset | spoofed | — | — | — | — | — |\n")
    return {}


def rename_without_map(src, dst):
    shutil.copytree(src, dst, dirs_exist_ok=True)
    p = dst / "threat-model.md"
    p.write_text(p.read_text().replace("audit-log-writer", "audit-writer"))
    return {}


def test_extra_entries_are_a_violation(tmp_path):
    (case,) = run_suite(_suite(transforms={"add-row": add_row}), REPO, tmp_path)
    assert case.status == "violated" and case.missing == () and case.reason is None
    assert [t[:2] for t in case.extra] == [("new-asset", "S")]


def test_a_rename_needs_its_map(tmp_path):
    (case,) = run_suite(_suite(transforms={"rename": rename_without_map}), REPO, tmp_path)
    assert case.status == "violated"
    assert [t[0] for t in case.missing] == ["audit-log-writer"]
    assert [t[0] for t in case.extra] == ["audit-writer"]

    def with_map(src, dst):
        rename_without_map(src, dst)
        return {"audit-writer": "audit-log-writer"}

    (case,) = run_suite(_suite(transforms={"rename": with_map}), REPO, tmp_path / "w2")
    assert case.status == "holds"


def test_missing_and_extra_are_sorted(tmp_path):
    def drop_two_rows(src, dst):
        shutil.copytree(src, dst, dirs_exist_ok=True)
        p = dst / "threat-model.md"
        p.write_text("\n".join(p.read_text().splitlines()[:-2]) + "\n")
        return {}

    (case,) = run_suite(_suite(transforms={"drop": drop_two_rows}), REPO, tmp_path)
    assert len(case.missing) == 5
    assert list(case.missing) == sorted(case.missing)


def test_allowlist_reason_is_reported(tmp_path):
    suite = _suite(transforms={"drop-last-row": drop_last_row},
                   known_non_invariant={("drop-last-row", FIXTURE): "drops a row on purpose"})
    (case,) = run_suite(suite, REPO, tmp_path)
    assert (case.status, case.reason) == ("allowlisted", "drops a row on purpose")
    assert len(case.missing) == 1  # what differs is still shown
    stale = replace(_stride(), known_non_invariant={("reorder-rows", FIXTURE): "was flaky"})
    cases = {c.transform: c for c in run_suite(stale, REPO, tmp_path / "w2")}
    assert (cases["reorder-rows"].status, cases["reorder-rows"].reason) == (
        "stale_allowlist", "was flaky")
    assert cases["rename-elements"].reason is None


def test_missing_fixture_raises_before_any_case(tmp_path):
    calls = []

    def transform(src, dst):
        calls.append(src)
        return {}

    suite = _suite(fixtures=(FIXTURE, "tests/fixtures/metamorphic/nope"),
                   transforms={"t": transform})
    with pytest.raises(MetamorphicError, match="tests/fixtures/metamorphic/nope"):
        run_suite(suite, REPO, tmp_path)
    assert calls == []


def test_workdir_must_be_empty(tmp_path):
    (tmp_path / "basic" / "reorder-rows").mkdir(parents=True)
    (tmp_path / "basic" / "reorder-rows" / "left-over").write_text("x", encoding="utf-8")
    with pytest.raises(MetamorphicError, match="not empty"):
        run_suite(_stride(), REPO, tmp_path)


@pytest.mark.parametrize("result, match", [
    ([("a",)], "set of tuples"),
    (frozenset({"abc"}), "set of tuples"),
    (frozenset({("a", 1)}), "set of tuples"),
])
def test_malformed_result_sets_are_refused(tmp_path, result, match):
    with pytest.raises(MetamorphicError, match=match):
        run_suite(_suite(extract=lambda d: result), REPO, tmp_path)


@pytest.mark.parametrize("rename", [None, [("a", "b")], {"a": 1}, {2: "b"}])
def test_malformed_rename_maps_are_refused(tmp_path, rename):
    def transform(src, dst):
        shutil.copytree(src, dst, dirs_exist_ok=True)
        return rename

    with pytest.raises(MetamorphicError, match="rename map"):
        run_suite(_suite(transforms={"t": transform}), REPO, tmp_path)


def test_an_os_error_names_the_case(tmp_path):
    def transform(src, dst):
        raise PermissionError(13, "Permission denied", str(dst))

    with pytest.raises(MetamorphicError, match=r"t-suite.*basic.*broken.*Permission denied"):
        run_suite(_suite(transforms={"broken": transform}), REPO, tmp_path)


def test_register_suite_refuses_duplicates_and_bad_definitions():
    base = _suite(name="t-reg")
    register_suite(base)
    try:
        assert get_suite("t-reg") is base
        with pytest.raises(ValueError, match="already registered"):
            register_suite(base)
    finally:
        SUITES.pop("t-reg")
    bad = [
        (replace(base, name="Bad Name"), "does not match"),
        (replace(base, fixtures=()), "no fixtures"),
        (replace(base, transforms={}), "no transforms"),
        (replace(base, fixtures=(FIXTURE, "other/basic")), "share the directory name"),
        (replace(base, fixtures=(".",)), "no directory name"),
        (replace(base, transforms={"../up": drop_last_row}), "transform name"),
        (replace(base, known_non_invariant={("nope", FIXTURE): "r"}), "names no case"),
        (replace(base, known_non_invariant={("reorder-rows", "x/basic"): "r"}), "names no case"),
        (replace(base, known_non_invariant={("reorder-rows", FIXTURE): "  "}), "reason"),
    ]
    for suite, match in bad:
        with pytest.raises(ValueError, match=match):
            register_suite(suite)
        assert "t-reg" not in SUITES


def test_get_suite_lists_registered_names(monkeypatch):
    load_builtin_suites()
    with pytest.raises(KeyError, match="unknown suite 'nope'; registered: .*stride-table"):
        get_suite("nope")
    monkeypatch.setattr("apd_gauntlet.eval.metamorphic.SUITES", {})
    with pytest.raises(KeyError, match="registered: none"):
        get_suite("nope")


def test_suite_is_frozen():
    with pytest.raises(AttributeError):
        _stride().name = "x"
    assert Suite.__dataclass_params__.frozen


def test_cli_text_report_passes():
    r = _invoke("--suite", "stride-table", "--root", str(REPO))
    assert r.exit_code == 0, r.output
    lines = r.output.splitlines()
    assert lines[0] == "suite stride-table: 1 fixture, 3 transforms, 3 cases"
    assert f"holds: rename-elements on {FIXTURE}" in lines
    assert lines[-1] == "RESULT: pass (3 holds)"


def test_cli_violation_exits_1(monkeypatch):
    monkeypatch.setitem(SUITES, "t-drop", _suite(name="t-drop",
                                                transforms={"drop-last-row": drop_last_row}))
    r = _invoke("--suite", "t-drop", "--root", str(REPO))
    assert r.exit_code == 1
    assert f"violated: drop-last-row on {FIXTURE}" in r.output
    assert '  missing: ["audit-log-writer", "R", ' in r.output
    assert r.output.splitlines()[-1] == "RESULT: fail (1 violated)"
    r = _invoke("--suite", "t-drop", "--root", str(REPO), "--json")
    assert r.exit_code == 1
    doc = json.loads(r.stdout)
    assert doc["suite"] == "t-drop"
    (case,) = doc["cases"]
    assert set(case) == {"fixture", "transform", "status", "missing", "extra", "reason"}
    assert case["missing"][0][0] == "audit-log-writer" and case["extra"] == []


def test_cli_allowlisted_passes_and_stale_fails(monkeypatch):
    monkeypatch.setitem(SUITES, "t-allow", _suite(
        name="t-allow", transforms={"drop-last-row": drop_last_row},
        known_non_invariant={("drop-last-row", FIXTURE): "demo"}))
    r = _invoke("--suite", "t-allow", "--root", str(REPO))
    assert r.exit_code == 0, r.output
    assert f"allowlisted: drop-last-row on {FIXTURE} (demo)" in r.output
    assert r.output.splitlines()[-1] == "RESULT: pass (1 allowlisted)"
    monkeypatch.setitem(SUITES, "t-stale", _suite(
        name="t-stale", known_non_invariant={("reorder-rows", FIXTURE): "demo"}))
    r = _invoke("--suite", "t-stale", "--root", str(REPO))
    assert r.exit_code == 1
    assert (f"stale_allowlist: reorder-rows on {FIXTURE} (demo): the case holds; "
            "remove its allowlist entry") in r.output
    assert r.output.splitlines()[-1] == "RESULT: fail (2 holds, 1 stale_allowlist)"


def test_cli_missing_fixture_exits_2(tmp_path):
    r = _invoke("--suite", "stride-table", "--root", str(tmp_path))
    assert r.exit_code == 2
    assert FIXTURE in r.output


def test_cli_metamorphic_error_exits_2(monkeypatch):
    def extract(d):
        raise MetamorphicError("suite t-tool needs a-tool on PATH")

    monkeypatch.setitem(SUITES, "t-tool", _suite(name="t-tool", extract=extract))
    r = _invoke("--suite", "t-tool", "--root", str(REPO), "--json")
    assert r.exit_code == 2
    assert "suite t-tool needs a-tool on PATH" in r.output


def test_cli_workdir_is_temporary(monkeypatch):
    dirs = []

    def transform(src, dst):
        dirs.append(dst)
        shutil.copytree(src, dst, dirs_exist_ok=True)
        return {}

    monkeypatch.setitem(SUITES, "t-tmp", _suite(name="t-tmp", transforms={"copy": transform}))
    r = _invoke("--suite", "t-tmp", "--root", str(REPO))
    assert r.exit_code == 0, r.output
    (dst,) = dirs
    assert not REPO.joinpath("basic").exists()
    assert REPO not in dst.parents and not dst.exists()


def test_cli_text_escapes_control_characters(monkeypatch):
    def extract(d):
        return frozenset() if d.name == "inject" else frozenset({("a\x1b[31m", "x\nRESULT: pass")})

    monkeypatch.setitem(SUITES, "t-esc", _suite(name="t-esc", extract=extract,
                                               transforms={"inject": drop_last_row}))
    r = _invoke("--suite", "t-esc", "--root", str(REPO))
    assert r.exit_code == 1
    assert "\x1b" not in r.output
    assert [ln for ln in r.output.splitlines() if ln.startswith("RESULT:")] == [
        "RESULT: fail (1 violated)"]
    assert '  missing: ["a\\u001b[31m", "x\\nRESULT: pass"]' in r.output


def test_a_fixture_that_cannot_be_checked_counts_as_missing(tmp_path, monkeypatch):
    real = Path.is_dir

    def is_dir(self):
        if self.name == "basic":
            raise PermissionError(13, "Permission denied", str(self))
        return real(self)

    monkeypatch.setattr(Path, "is_dir", is_dir)
    with pytest.raises(MetamorphicError, match=f"no fixture directory {FIXTURE} under"):
        run_suite(_stride(), REPO, tmp_path)
