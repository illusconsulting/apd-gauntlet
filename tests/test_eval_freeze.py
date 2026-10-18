"""eval.freeze: the tunables hash, ``eval/frozen.yaml`` and the held-out guard (ADR-0028)."""
from __future__ import annotations

import hashlib
import os
import pathlib
import re

import pytest
import yaml
from apd_gauntlet.cli import main
from apd_gauntlet.eval.freeze import (
    FROZEN_RELPATH,
    RESULTS_RELPATH,
    TUNABLE_GLOBS,
    FreezeError,
    check_frozen,
    freeze,
    heldout_uses,
    read_frozen,
    tunables,
    tunables_sha256,
)
from click.testing import CliRunner

THRESHOLDS = "tools/apd_gauntlet/data/decide/thresholds.yaml"
IAC_PARAMS = "tools/apd_gauntlet/data/iac/context-params.yaml"
CODEFLOW_PARAMS = "tools/apd_gauntlet/data/codeflow/context-params.yaml"


def root(tmp_path):
    for rel, text in {THRESHOLDS: "{}\n", IAC_PARAMS: "k: 20\n"}.items():
        (tmp_path / rel).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / rel).write_text(text)
    return tmp_path


def frozen(r):
    return yaml.safe_load((r / "eval/frozen.yaml").read_text())


def heldout_result(r, sha, name="heldout-20261011T000000Z.yaml", evaluator="findings"):
    res = r / "eval/results" / evaluator / name
    res.parent.mkdir(parents=True, exist_ok=True)
    res.write_text(yaml.safe_dump({"frozen_sha256": sha}))
    return res


def _sha(text):
    return hashlib.sha256(text.encode()).hexdigest()


# --- the plan's tests ---------------------------------------------------------------------


def test_tunables_found(tmp_path):
    assert list(tunables(root(tmp_path))) == [
        "tools/apd_gauntlet/data/decide/thresholds.yaml",
        "tools/apd_gauntlet/data/iac/context-params.yaml",
    ]


def test_missing_freeze(tmp_path):
    with pytest.raises(FreezeError, match="eval freeze"):
        check_frozen(root(tmp_path))


def test_freeze_then_edit(tmp_path):
    r = root(tmp_path)
    freeze(r)
    assert check_frozen(r) == yaml.safe_load(
        (r / "eval/frozen.yaml").read_text()
    )["tunables_sha256"]
    (r / "tools/apd_gauntlet/data/iac/context-params.yaml").write_text("k: 21\n")
    with pytest.raises(
        FreezeError, match="changed tools/apd_gauntlet/data/iac/context-params.yaml"
    ):
        check_frozen(r)


def test_added_tunable_counts(tmp_path):
    r = root(tmp_path)
    freeze(r)
    (r / "tools/apd_gauntlet/data/codeflow").mkdir()
    (r / "tools/apd_gauntlet/data/codeflow/context-params.yaml").write_text("k: 1\n")
    with pytest.raises(FreezeError, match="added"):
        check_frozen(r)


def test_refreeze_after_heldout_use_refused(tmp_path):
    r = root(tmp_path)
    freeze(r)
    sha = check_frozen(r)
    res = r / "eval/results/findings/heldout-20261011T000000Z.yaml"
    res.parent.mkdir(parents=True)
    res.write_text(yaml.safe_dump({"frozen_sha256": sha}))
    (r / "tools/apd_gauntlet/data/decide/thresholds.yaml").write_text("x: {}\n")
    with pytest.raises(FreezeError, match="new held-out set"):
        freeze(r)
    freeze(r, new_heldout_set=True)
    assert yaml.safe_load((r / "eval/frozen.yaml").read_text())["generation"] == 2


def test_refreeze_without_heldout_use_keeps_generation(tmp_path):
    r = root(tmp_path)
    freeze(r)
    first = frozen(r)["tunables_sha256"]
    (r / IAC_PARAMS).write_text("k: 21\n")
    freeze(r)
    data = frozen(r)
    assert data["generation"] == 1
    assert data["tunables_sha256"] != first
    assert check_frozen(r) == data["tunables_sha256"]


def test_cli_freeze(tmp_path):
    r = root(tmp_path)
    first = CliRunner().invoke(main, ["eval", "freeze", "--root", str(r)])
    assert first.exit_code == 0, first.output
    assert (r / "eval/frozen.yaml").is_file()
    assert f"wrote {r / 'eval/frozen.yaml'}" in first.output
    second = CliRunner().invoke(main, ["eval", "freeze", "--root", str(r)])
    assert second.exit_code == 0, second.output
    assert "unchanged" in second.output


# --- constants, the hash and the file -----------------------------------------------------


def test_constants():
    assert TUNABLE_GLOBS == (
        "tools/apd_gauntlet/data/decide/thresholds.yaml",
        "tools/apd_gauntlet/data/*/context-params.yaml",
    )
    assert isinstance(FROZEN_RELPATH, pathlib.Path)
    assert isinstance(RESULTS_RELPATH, pathlib.Path)
    assert FROZEN_RELPATH.as_posix() == "eval/frozen.yaml"
    assert RESULTS_RELPATH.as_posix() == "eval/results"


def test_tunables_hash_each_file_by_content(tmp_path):
    files = tunables(root(tmp_path))
    assert files == {THRESHOLDS: _sha("{}\n"), IAC_PARAMS: _sha("k: 20\n")}


def test_tunables_sha256_over_sorted_lines():
    files = {"b": "2" * 64, "a": "1" * 64}
    expected = _sha(f"a\0{'1' * 64}\nb\0{'2' * 64}\n")
    assert tunables_sha256(files) == expected
    assert tunables_sha256(dict(reversed(list(files.items())))) == expected


def test_tunables_sorted_across_globs(tmp_path):
    r = root(tmp_path)
    for name in ("zeta", "alpha"):
        p = r / f"tools/apd_gauntlet/data/{name}/context-params.yaml"
        p.parent.mkdir(parents=True)
        p.write_text("k: 1\n")
    assert list(tunables(r)) == sorted(tunables(r))
    assert "tools/apd_gauntlet/data/alpha/context-params.yaml" in tunables(r)


def test_only_matching_files_are_tunables(tmp_path):
    r = root(tmp_path)
    data = r / "tools/apd_gauntlet/data"
    (data / "iac/other.yaml").write_text("k: 1\n")
    (data / "decide/thresholds.yml").write_text("{}\n")
    (data / "loose.json").write_text("{}\n")
    (data / "iac/nested").mkdir()
    (data / "iac/nested/context-params.yaml").write_text("k: 1\n")
    (r / "context-params.yaml").write_text("k: 1\n")
    assert list(tunables(r)) == [THRESHOLDS, IAC_PARAMS]


def test_no_tunables_is_an_empty_set(tmp_path):
    assert tunables(tmp_path) == {}
    assert tunables_sha256({}) == hashlib.sha256(b"").hexdigest()


def test_empty_tunable_set_freezes(tmp_path):
    path = freeze(tmp_path)
    assert path == tmp_path / "eval/frozen.yaml"
    assert frozen(tmp_path)["files"] == {}
    assert check_frozen(tmp_path) == hashlib.sha256(b"").hexdigest()
    (tmp_path / THRESHOLDS).parent.mkdir(parents=True)
    (tmp_path / THRESHOLDS).write_text("{}\n")
    with pytest.raises(FreezeError, match=f"added {THRESHOLDS}"):
        check_frozen(tmp_path)


def test_frozen_file_layout(tmp_path):
    r = root(tmp_path)
    assert freeze(r) == r / "eval/frozen.yaml"
    data = frozen(r)
    assert list(data) == ["schema_version", "frozen_at", "generation", "tunables_sha256", "files"]
    assert data["schema_version"] == 1
    assert data["generation"] == 1
    assert re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ", data["frozen_at"])
    assert data["files"] == tunables(r)
    assert data["tunables_sha256"] == tunables_sha256(tunables(r))
    assert (r / "eval/frozen.yaml").read_text().startswith("# ")


def test_read_frozen(tmp_path):
    r = root(tmp_path)
    assert read_frozen(r) is None
    freeze(r)
    f = read_frozen(r)
    assert f is not None
    data = frozen(r)
    assert (f.generation, f.tunables_sha256, f.files, f.frozen_at) == (
        1, data["tunables_sha256"], data["files"], data["frozen_at"]
    )


def test_check_frozen_returns_the_current_hash(tmp_path):
    r = root(tmp_path)
    freeze(r)
    assert check_frozen(r) == tunables_sha256(tunables(r))


def test_missing_freeze_message(tmp_path):
    with pytest.raises(FreezeError) as exc:
        check_frozen(tmp_path)
    assert str(exc.value) == (
        f"{tmp_path / 'eval/frozen.yaml'} not found — tune on dev, then run "
        "'apd-gauntlet eval freeze'"
    )


def test_change_message_lists_every_difference_by_path(tmp_path):
    r = root(tmp_path)
    freeze(r)
    (r / THRESHOLDS).unlink()
    (r / IAC_PARAMS).write_text("k: 21\n")
    (r / CODEFLOW_PARAMS).parent.mkdir()
    (r / CODEFLOW_PARAMS).write_text("k: 1\n")
    with pytest.raises(FreezeError) as exc:
        check_frozen(r)
    assert str(exc.value) == (
        f"tunables changed since freeze: added {CODEFLOW_PARAMS}, removed {THRESHOLDS}, "
        f"changed {IAC_PARAMS}"
    )


def test_removed_tunable_detected(tmp_path):
    r = root(tmp_path)
    freeze(r)
    (r / THRESHOLDS).unlink()
    with pytest.raises(FreezeError, match=f"removed {THRESHOLDS}"):
        check_frozen(r)


def test_reverting_an_edit_matches_again(tmp_path):
    r = root(tmp_path)
    freeze(r)
    sha = check_frozen(r)
    (r / IAC_PARAMS).write_text("k: 21\n")
    with pytest.raises(FreezeError):
        check_frozen(r)
    (r / IAC_PARAMS).write_text("k: 20\n")
    assert check_frozen(r) == sha


def test_mtime_does_not_matter(tmp_path):
    r = root(tmp_path)
    freeze(r)
    sha = check_frozen(r)
    os.utime(r / IAC_PARAMS, (2_000_000_000, 2_000_000_000))  # newer than the freeze
    assert check_frozen(r) == sha
    os.utime(r / "eval/frozen.yaml", (1_000_000_000, 1_000_000_000))  # older than the tunables
    assert check_frozen(r) == sha


# --- freeze -------------------------------------------------------------------------------


def test_unchanged_freeze_writes_nothing(tmp_path):
    r = root(tmp_path)
    path = freeze(r)
    before = path.read_bytes()
    os.utime(path, (1_000_000_000, 1_000_000_000))
    assert freeze(r) == path
    assert freeze(r, new_heldout_set=True) == path
    assert path.read_bytes() == before
    assert path.stat().st_mtime == 1_000_000_000


def test_first_freeze_is_generation_1_even_with_the_flag(tmp_path):
    r = root(tmp_path)
    freeze(r, new_heldout_set=True)
    assert frozen(r)["generation"] == 1


def test_new_heldout_set_raises_the_generation_on_a_change(tmp_path):
    r = root(tmp_path)
    freeze(r)
    (r / IAC_PARAMS).write_text("k: 21\n")
    freeze(r, new_heldout_set=True)
    assert frozen(r)["generation"] == 2
    (r / IAC_PARAMS).write_text("k: 22\n")
    freeze(r)
    assert frozen(r)["generation"] == 2


def test_refused_refreeze_message_and_file_untouched(tmp_path):
    r = root(tmp_path)
    freeze(r)
    sha = check_frozen(r)
    res = heldout_result(r, sha)
    before = (r / "eval/frozen.yaml").read_bytes()
    (r / IAC_PARAMS).write_text("k: 21\n")
    with pytest.raises(FreezeError) as exc:
        freeze(r)
    assert str(exc.value) == (
        f"tunables frozen as {sha[:8]} were used on held-out data ({res}); changing them "
        "needs a new held-out set (IaC spec §13.2) — pass --new-heldout-set once you have one"
    )
    assert (r / "eval/frozen.yaml").read_bytes() == before


def test_refused_refreeze_counts_further_uses(tmp_path):
    r = root(tmp_path)
    freeze(r)
    sha = check_frozen(r)
    first = heldout_result(r, sha, "heldout-20261011T000000Z.yaml", "findings")
    heldout_result(r, sha, "heldout-20261012T000000Z.yaml", "iac-delta")
    (r / IAC_PARAMS).write_text("k: 21\n")
    with pytest.raises(FreezeError, match=re.escape(f"({first} and 1 more)")):
        freeze(r)


def test_dev_results_never_block_a_refreeze(tmp_path):
    r = root(tmp_path)
    freeze(r)
    heldout_result(r, check_frozen(r), "dev-20261011T000000Z.yaml")
    (r / IAC_PARAMS).write_text("k: 21\n")
    freeze(r)
    assert frozen(r)["generation"] == 1


def test_heldout_results_of_an_older_freeze_do_not_block(tmp_path):
    r = root(tmp_path)
    freeze(r)
    heldout_result(r, "0" * 64)
    (r / IAC_PARAMS).write_text("k: 21\n")
    freeze(r)
    assert frozen(r)["generation"] == 1


def test_frozen_at_recorded_on_each_write(tmp_path):
    r = root(tmp_path)
    freeze(r)
    (r / "eval/frozen.yaml").write_text(
        (r / "eval/frozen.yaml").read_text().replace(frozen(r)["frozen_at"], "2000-01-01T00:00:00Z")
    )
    (r / IAC_PARAMS).write_text("k: 21\n")
    freeze(r)
    assert frozen(r)["frozen_at"] != "2000-01-01T00:00:00Z"


def test_write_failure_raises_freeze_error(tmp_path):
    r = root(tmp_path)
    (r / "eval").write_text("not a directory\n")
    with pytest.raises(FreezeError, match="cannot write"):
        freeze(r)


# --- heldout_uses -------------------------------------------------------------------------


def test_heldout_uses(tmp_path):
    results = tmp_path / "eval/results"
    sha = "a" * 64
    hit2 = heldout_result(tmp_path, sha, "heldout-20261012T000000Z.yaml", "findings")
    hit1 = heldout_result(tmp_path, sha, "heldout-20261011T000000Z.yaml", "catalog-grounding")
    heldout_result(tmp_path, "b" * 64, "heldout-20261013T000000Z.yaml", "findings")
    heldout_result(tmp_path, sha, "dev-20261011T000000Z.yaml", "findings")
    heldout_result(tmp_path, sha, "heldout-20261011T000000Z.json", "findings")
    (results / "findings/heldout-empty.yaml").write_text("")
    (results / "findings/heldout-list.yaml").write_text("- 1\n")
    nested = results / "iac-delta/older/heldout-20261001T000000Z.yaml"
    nested.parent.mkdir(parents=True)
    nested.write_text(yaml.safe_dump({"frozen_sha256": sha}))
    assert heldout_uses(results, sha) == sorted([hit1, hit2, nested])


def test_heldout_uses_without_results(tmp_path):
    assert heldout_uses(tmp_path / "eval/results", "a" * 64) == []


@pytest.mark.parametrize(
    "raw",
    [b"frozen_sha256: [\n", b"\xff\xfe not utf-8", b"date: 2026-02-30\n"],
    ids=["yaml", "utf8", "date"],
)
def test_heldout_result_that_cannot_be_read_refuses(tmp_path, raw):
    res = tmp_path / "eval/results/findings/heldout-20261011T000000Z.yaml"
    res.parent.mkdir(parents=True)
    res.write_bytes(raw)
    with pytest.raises(FreezeError, match=re.escape(str(res))):
        heldout_uses(tmp_path / "eval/results", "a" * 64)


def test_refreeze_refused_when_a_heldout_result_cannot_be_read(tmp_path):
    r = root(tmp_path)
    freeze(r)
    res = r / "eval/results/findings/heldout-20261011T000000Z.yaml"
    res.parent.mkdir(parents=True)
    res.write_text("frozen_sha256: [\n")
    (r / IAC_PARAMS).write_text("k: 21\n")
    with pytest.raises(FreezeError, match=re.escape(str(res))):
        freeze(r)


# --- invalid frozen files -----------------------------------------------------------------


def _valid_frozen():
    files = {THRESHOLDS: "1" * 64}
    return {
        "schema_version": 1,
        "frozen_at": "2026-10-17T00:00:00Z",
        "generation": 1,
        "tunables_sha256": tunables_sha256(files),
        "files": files,
    }


def _bad(**changes):
    doc = _valid_frozen()
    for key, value in changes.items():
        if value is KeyError:
            del doc[key]
        else:
            doc[key] = value
    return yaml.safe_dump(doc)


BAD_FROZEN = {
    "not-yaml": ("schema_version: [\n", "invalid YAML"),
    "not-mapping": ("- 1\n", "not a mapping"),
    "version": (_bad(schema_version=2), "schema_version"),
    "version-bool": (_bad(schema_version=True), "schema_version"),
    "no-generation": (_bad(generation=KeyError), "generation"),
    "generation-0": (_bad(generation=0), "generation"),
    "generation-bool": (_bad(generation=True), "generation"),
    "frozen-at": (_bad(frozen_at=""), "frozen_at"),
    "sha": (_bad(tunables_sha256="abc"), "tunables_sha256"),
    "files": (_bad(files=["x"]), "files"),
    "file-sha": (_bad(files={THRESHOLDS: "x"}), "files"),
    "inconsistent": (_bad(tunables_sha256="0" * 64), "does not match its files"),
}


@pytest.mark.parametrize("text,message", BAD_FROZEN.values(), ids=BAD_FROZEN.keys())
def test_invalid_frozen_file_refused(tmp_path, text, message):
    r = root(tmp_path)
    path = r / "eval/frozen.yaml"
    path.parent.mkdir()
    path.write_text(text)
    for call in (check_frozen, freeze, read_frozen):
        with pytest.raises(FreezeError, match=re.escape(str(path))) as exc:
            call(r)
        assert message in str(exc.value)
    assert path.read_text() == text


def test_frozen_file_that_is_not_utf8_refused(tmp_path):
    path = tmp_path / "eval/frozen.yaml"
    path.parent.mkdir()
    path.write_bytes(b"\xff\xfe")
    with pytest.raises(FreezeError, match="not UTF-8"):
        check_frozen(tmp_path)


# --- files that cannot be read ------------------------------------------------------------

needs_permissions = pytest.mark.skipif(
    not hasattr(os, "geteuid") or os.geteuid() == 0, reason="root ignores file modes"
)


@needs_permissions
def test_unreadable_tunable_refused(tmp_path):
    r = root(tmp_path)
    target = r / IAC_PARAMS
    target.chmod(0)
    try:
        with pytest.raises(FreezeError, match=re.escape(f"{target}: cannot read")):
            tunables(r)
    finally:
        target.chmod(0o644)


@needs_permissions
def test_unsearchable_data_directory_refused(tmp_path):
    r = root(tmp_path)
    data = r / "tools/apd_gauntlet/data"
    data.chmod(0)
    try:
        with pytest.raises(FreezeError, match=re.escape(str(data))):
            tunables(r)
    finally:
        data.chmod(0o755)


@needs_permissions
def test_unlistable_data_directory_refused(tmp_path):
    # Execute only: thresholds.yaml can still be reached by name, but the
    # context-params.yaml pattern cannot list data/. Path.glob would skip it silently.
    r = root(tmp_path)
    data = r / "tools/apd_gauntlet/data"
    data.chmod(0o100)
    try:
        with pytest.raises(FreezeError, match=re.escape(f"{data}: cannot list")):
            tunables(r)
    finally:
        data.chmod(0o755)


@needs_permissions
def test_unlistable_results_directory_refused(tmp_path):
    results = tmp_path / "eval/results"
    sub = results / "findings"
    sub.mkdir(parents=True)
    sub.chmod(0)
    try:
        with pytest.raises(FreezeError, match=re.escape(str(sub))):
            heldout_uses(results, "a" * 64)
    finally:
        sub.chmod(0o755)


def test_tunable_that_is_a_directory_refused(tmp_path):
    r = root(tmp_path)
    (r / "tools/apd_gauntlet/data/bad/context-params.yaml").mkdir(parents=True)
    with pytest.raises(FreezeError, match="bad/context-params.yaml: cannot read"):
        tunables(r)


# --- the command --------------------------------------------------------------------------


def invoke(*args):
    return CliRunner().invoke(main, ["eval", "freeze", *args])


def test_cli_freeze_lists_the_files(tmp_path):
    r = root(tmp_path)
    result = invoke("--root", str(r))
    assert result.exit_code == 0, result.output
    sha = frozen(r)["tunables_sha256"]
    assert f"generation 1, tunables {sha[:8]}, 2 files" in result.output
    assert THRESHOLDS in result.output and IAC_PARAMS in result.output


def test_cli_refused_refreeze_exits_1(tmp_path):
    r = root(tmp_path)
    assert invoke("--root", str(r)).exit_code == 0
    heldout_result(r, check_frozen(r))
    (r / IAC_PARAMS).write_text("k: 21\n")
    before = (r / "eval/frozen.yaml").read_bytes()
    refused = invoke("--root", str(r))
    assert refused.exit_code == 1
    assert "--new-heldout-set" in refused.output
    assert "Traceback" not in refused.output
    assert (r / "eval/frozen.yaml").read_bytes() == before
    accepted = invoke("--root", str(r), "--new-heldout-set")
    assert accepted.exit_code == 0, accepted.output
    assert "generation 2" in accepted.output
    assert frozen(r)["generation"] == 2


def test_cli_invalid_frozen_file_exits_1(tmp_path):
    r = root(tmp_path)
    (r / "eval").mkdir()
    (r / "eval/frozen.yaml").write_text("- 1\n")
    result = invoke("--root", str(r))
    assert result.exit_code == 1
    assert "not a mapping" in result.output


def test_cli_write_failure_exits_1(tmp_path):
    r = root(tmp_path)
    (r / "eval").write_text("not a directory\n")
    result = invoke("--root", str(r))
    assert result.exit_code == 1
    assert "cannot write" in result.output
    assert "Traceback" not in result.output


def test_cli_root_must_be_a_directory(tmp_path):
    assert invoke("--root", str(tmp_path / "missing")).exit_code == 2


def test_cli_root_defaults_to_the_working_directory(tmp_path, monkeypatch):
    r = root(tmp_path)
    monkeypatch.chdir(r)
    result = invoke()
    assert result.exit_code == 0, result.output
    assert (r / "eval/frozen.yaml").is_file()
    assert "wrote eval/frozen.yaml" in result.output


def test_cli_help():
    result = invoke("--help")
    assert result.exit_code == 0
    for text in ("--root", "--new-heldout-set", "eval/frozen.yaml", "held-out"):
        assert text in result.output
