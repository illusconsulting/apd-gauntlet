# tests/unit/report/test_tier2_bundle.py
"""Regression tests for copy_bundle prune-orphans behaviour."""
from __future__ import annotations

import pathlib

from apd_gauntlet.report.emit import copy_bundle


def _populate_src(path: pathlib.Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    (path / "app.js").write_text("new app", encoding="utf-8")
    (path / "index.html").write_text("<html />", encoding="utf-8")
    (path / "screens.css").write_text("body {}", encoding="utf-8")
    (path / "fonts").mkdir()
    (path / "fonts" / "x.woff2").write_text("font-bytes", encoding="utf-8")


def test_copy_bundle_copies_source_into_target(tmp_path):
    src = tmp_path / "src"
    dst = tmp_path / "dst"
    _populate_src(src)
    copy_bundle(src, dst)
    assert (dst / "app.js").read_text(encoding="utf-8") == "new app"
    assert (dst / "index.html").is_file()
    assert (dst / "fonts" / "x.woff2").is_file()


def test_copy_bundle_prunes_orphan_top_level_files(tmp_path):
    src = tmp_path / "src"
    dst = tmp_path / "dst"
    _populate_src(src)
    # Pre-populate dst with an orphan from a hypothetical prior bundle.
    dst.mkdir()
    (dst / "old-asset.js").write_text("stale", encoding="utf-8")
    copy_bundle(src, dst)
    assert not (dst / "old-asset.js").exists(), "orphan top-level file must be pruned"
    assert (dst / "app.js").read_text(encoding="utf-8") == "new app"


def test_copy_bundle_prunes_orphan_nested_files(tmp_path):
    src = tmp_path / "src"
    dst = tmp_path / "dst"
    _populate_src(src)
    dst.mkdir()
    (dst / "old").mkdir()
    (dst / "old" / "stale.js").write_text("stale", encoding="utf-8")
    copy_bundle(src, dst)
    assert not (dst / "old" / "stale.js").exists()
    # Now-empty directory removed.
    assert not (dst / "old").exists()


def test_copy_bundle_preserves_data_js_and_manifest(tmp_path):
    src = tmp_path / "src"
    dst = tmp_path / "dst"
    _populate_src(src)
    dst.mkdir()
    (dst / "data.js").write_text("window.APD_DATA = {}", encoding="utf-8")
    (dst / "build-manifest.txt").write_text("framework_version=1.0.0", encoding="utf-8")
    copy_bundle(src, dst)
    assert (dst / "data.js").read_text(encoding="utf-8") == "window.APD_DATA = {}"
    assert (dst / "build-manifest.txt").read_text(encoding="utf-8") == "framework_version=1.0.0"


def test_copy_bundle_overwrites_collisions(tmp_path):
    src = tmp_path / "src"
    dst = tmp_path / "dst"
    _populate_src(src)
    dst.mkdir()
    (dst / "app.js").write_text("old app", encoding="utf-8")
    copy_bundle(src, dst)
    assert (dst / "app.js").read_text(encoding="utf-8") == "new app"


def test_copy_bundle_handles_empty_destination(tmp_path):
    src = tmp_path / "src"
    dst = tmp_path / "dst"
    _populate_src(src)
    # dst does not exist
    assert not dst.exists()
    copy_bundle(src, dst)
    assert (dst / "app.js").is_file()
