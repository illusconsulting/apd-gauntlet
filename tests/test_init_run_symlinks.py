"""init-run refuses input links that point outside the inputs folder (N1)."""
from __future__ import annotations

import os
import pathlib

from apd_gauntlet.cli import main
from apd_gauntlet.init_run import scaffold_run
from click.testing import CliRunner


def _outside(tmp_path: pathlib.Path) -> pathlib.Path:
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "id_rsa").write_text("SECRET")
    return outside


def _inputs(tmp_path: pathlib.Path) -> pathlib.Path:
    inputs = tmp_path / "in"
    inputs.mkdir()
    (inputs / "plan.md").write_text("x")
    return inputs


def _init_run(inputs: pathlib.Path, root: pathlib.Path):  # type: ignore[no-untyped-def]
    return CliRunner().invoke(
        main, ["init-run", "r1", "--inputs", str(inputs), "--root", str(root)]
    )


def test_escaping_dir_link_refused(tmp_path):
    outside = _outside(tmp_path)
    inputs = _inputs(tmp_path)
    (inputs / "keys").symlink_to(outside, target_is_directory=True)

    r = _init_run(inputs, tmp_path / "runs")

    assert r.exit_code == 1
    assert f"keys -> {outside}" in r.output
    assert not (tmp_path / "runs" / "r1").exists()


def test_escaping_file_link_refused(tmp_path):
    outside = _outside(tmp_path)
    inputs = _inputs(tmp_path)
    (inputs / "key-file").symlink_to(outside / "id_rsa")

    r = _init_run(inputs, tmp_path / "runs")

    assert r.exit_code == 1
    assert "key-file" in r.output
    assert not (tmp_path / "runs" / "r1").exists()
    runs = tmp_path / "runs"
    copied = [p for p in runs.rglob("*") if p.is_file()] if runs.exists() else []
    assert not any("SECRET" in p.read_text() for p in copied)


def test_nested_escaping_link_refused(tmp_path):
    outside = _outside(tmp_path)
    inputs = _inputs(tmp_path)
    (inputs / "docs").mkdir()
    (inputs / "docs" / "deep").symlink_to(outside, target_is_directory=True)

    r = _init_run(inputs, tmp_path / "runs")

    assert r.exit_code == 1
    assert "docs/deep" in r.output
    assert not (tmp_path / "runs" / "r1").exists()


def test_relative_escaping_link_refused(tmp_path):
    _outside(tmp_path)
    inputs = _inputs(tmp_path)
    (inputs / "up").symlink_to(pathlib.Path("..") / "outside" / "id_rsa")

    r = _init_run(inputs, tmp_path / "runs")

    assert r.exit_code == 1
    assert "up -> ../outside/id_rsa" in r.output
    assert not (tmp_path / "runs" / "r1").exists()


def test_dangling_outside_link_refused(tmp_path):
    inputs = _inputs(tmp_path)
    (inputs / "gone").symlink_to(tmp_path / "missing" / "file")

    r = _init_run(inputs, tmp_path / "runs")

    assert r.exit_code == 1
    assert "gone" in r.output
    assert not (tmp_path / "runs" / "r1").exists()


def test_internal_link_kept_relative(tmp_path):
    inputs = _inputs(tmp_path)
    (inputs / "docs").mkdir()
    (inputs / "docs" / "notes.md").write_text("n")
    (inputs / "alias.md").symlink_to(inputs / "plan.md")
    (inputs / "docs" / "alias.md").symlink_to(inputs / "plan.md")
    (inputs / "docs-link").symlink_to(inputs / "docs", target_is_directory=True)

    run = scaffold_run("r2", inputs, ["pbm"], tmp_path / "runs")

    copied = run / "inputs"
    assert os.readlink(copied / "alias.md") == "plan.md"
    assert os.readlink(copied / "docs" / "alias.md") == os.path.join("..", "plan.md")
    assert os.readlink(copied / "docs-link") == "docs"
    assert (copied / "alias.md").read_text() == "x"
    assert (copied / "docs-link" / "notes.md").read_text() == "n"


def test_find_escaping_links_sorted_relative(tmp_path):
    from apd_gauntlet.init_run import find_escaping_links

    outside = _outside(tmp_path)
    inputs = _inputs(tmp_path)
    (inputs / "keys").symlink_to(outside, target_is_directory=True)
    (inputs / "b").mkdir()
    (inputs / "b" / "link").symlink_to(outside / "id_rsa")
    (inputs / "inside").symlink_to(inputs / "plan.md")

    assert find_escaping_links(inputs) == ["b/link", "keys"]
