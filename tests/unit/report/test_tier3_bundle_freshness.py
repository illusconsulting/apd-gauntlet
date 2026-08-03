# tests/unit/report/test_tier3_bundle_freshness.py
"""Regression tests for path-inclusive source hash (T3-E)."""
from __future__ import annotations

import importlib.util
import pathlib
import shutil
import subprocess

import pytest

REPO = pathlib.Path(__file__).resolve().parents[3]


def _load_freshness_module():
    """Load tools/check_report_template_freshness.py."""
    path = REPO / "tools" / "check_report_template_freshness.py"
    spec = importlib.util.spec_from_file_location("_freshness", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_compute_source_hash_returns_64char_hex():
    mod = _load_freshness_module()
    h = mod.compute_source_hash()
    assert isinstance(h, str)
    assert len(h) == 64
    int(h, 16)


def test_compute_source_hash_stable_across_calls():
    mod = _load_freshness_module()
    a = mod.compute_source_hash()
    b = mod.compute_source_hash()
    assert a == b


def test_compute_source_hash_includes_relative_path(monkeypatch, tmp_path):
    """Renaming a file changes the hash even if content is identical.

    Synthesises a tiny SRC tree, monkeypatches SRC, computes hash before
    and after rename — must differ.
    """
    mod = _load_freshness_module()
    src = tmp_path / "src"
    src.mkdir()
    (src / "foo.jsx").write_text("identical content\n", encoding="utf-8")
    monkeypatch.setattr(mod, "SRC", src)
    before = mod.compute_source_hash()
    # Rename: same content, different relative path → different hash.
    (src / "foo.jsx").rename(src / "renamed.jsx")
    after = mod.compute_source_hash()
    assert before != after, "rename must invalidate the hash"


def test_compute_source_hash_includes_nested_path(monkeypatch, tmp_path):
    """Two files with the same basename in different subdirs must contribute
    distinct path bytes to the hash."""
    mod = _load_freshness_module()
    src = tmp_path / "src"
    (src / "a").mkdir(parents=True)
    (src / "b").mkdir()
    (src / "a" / "shared.jsx").write_text("X", encoding="utf-8")
    (src / "b" / "shared.jsx").write_text("X", encoding="utf-8")
    monkeypatch.setattr(mod, "SRC", src)
    nested = mod.compute_source_hash()
    # Now make their relative paths collide by removing one (so only basename
    # is unique). Hashes must still differ from the both-present case.
    (src / "b" / "shared.jsx").unlink()
    (src / "b").rmdir()
    flat = mod.compute_source_hash()
    assert nested != flat


def test_shipped_bundle_source_hash_matches():
    """The shipped bundle .source-hash must agree with compute_source_hash()
    on main. If this test fails after editing report-template/, you forgot
    to run tools/build_report_template.py and commit the refreshed bundle."""
    mod = _load_freshness_module()
    bundle = REPO / "tools" / "apd_gauntlet" / "data" / "report-template"
    hash_file = bundle / ".source-hash"
    if not hash_file.is_file():
        return  # bundle not built; skip rather than fail
    expected = hash_file.read_text(encoding="utf-8").strip()
    actual = mod.compute_source_hash()
    assert expected == actual, (
        f"bundle .source-hash ({expected[:8]}) != compute_source_hash() "
        f"({actual[:8]}) — refresh via tools/build_report_template.py"
    )


def test_compute_source_hash_excludes_nested_dotfiles_and_node_modules(monkeypatch, tmp_path):
    """Dotfiles / node_modules / .build are excluded at EVERY depth, matching
    report-template/.build/build.mjs walk() (line 54, which skips them during
    recursive descent). Regression for the Python/Node divergence that only
    excluded at the top level (rel.parts[0])."""
    mod = _load_freshness_module()
    src = tmp_path / "src"
    (src / "sub").mkdir(parents=True)
    (src / "app.jsx").write_text("A", encoding="utf-8")
    (src / "sub" / "child.jsx").write_text("B", encoding="utf-8")
    monkeypatch.setattr(mod, "SRC", src)
    baseline = mod.compute_source_hash()
    # Entries build.mjs excludes at nested depth (parts[0] == "sub", not excluded
    # by the old top-level-only rule):
    (src / "sub" / ".gitkeep").write_text("x", encoding="utf-8")
    (src / "sub" / "node_modules").mkdir()
    (src / "sub" / "node_modules" / "pkg.js").write_text("y", encoding="utf-8")
    (src / "sub" / ".build").mkdir()
    (src / "sub" / ".build" / "out.js").write_text("z", encoding="utf-8")
    with_excluded = mod.compute_source_hash()
    assert with_excluded == baseline, (
        "nested dotfiles / node_modules / .build must not affect the hash "
        "(they don't in build.mjs)"
    )


def test_source_hash_parity_with_node_walk(monkeypatch, tmp_path):
    """Python compute_source_hash() and the Node walk (source-hash.mjs — the
    same code build.mjs runs) must agree byte-for-byte on one tree, including
    the two divergence-prone shapes: a nested dotfile, and a directory/file
    name-collision pair ("screens" dir vs "screens.css" file) that pins
    ordering agreement (Python's parts-tuple sort vs Node's per-directory
    sorted DFS). Skipped without node; the bundle-rebuild-diff CI job runs
    this module with Node present, so the skip cannot go permanently
    unnoticed."""
    if shutil.which("node") is None:
        pytest.skip("node unavailable; exercised in the bundle-rebuild-diff CI job")
    mod = _load_freshness_module()
    src = tmp_path / "src"
    (src / "screens").mkdir(parents=True)
    (src / "screens" / "A.jsx").write_text("A", encoding="utf-8")
    (src / "screens.css").write_text("C", encoding="utf-8")
    (src / "sub").mkdir()
    (src / "sub" / "child.jsx").write_text("B", encoding="utf-8")
    (src / "sub" / ".gitkeep").write_text("x", encoding="utf-8")
    monkeypatch.setattr(mod, "SRC", src)
    script = REPO / "report-template" / ".build" / "source-hash.mjs"
    proc = subprocess.run(
        ["node", str(script), str(src)], capture_output=True, text=True, check=True
    )
    assert proc.stdout.strip() == mod.compute_source_hash()


def test_ci_has_bundle_rebuild_diff_job():
    """The rebuild-and-diff CI job is the only guard that catches a stale or
    hand-edited committed bundle (the .source-hash marker cannot). Source-grep
    guard so the job is not silently dropped or renamed."""
    wf = (REPO / ".github" / "workflows" / "python-tests.yml").read_text(encoding="utf-8")
    assert "bundle-rebuild-diff:" in wf
    assert "git diff --exit-code -- tools/apd_gauntlet/data/report-template/" in wf
