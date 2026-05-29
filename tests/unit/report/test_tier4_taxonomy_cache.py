"""Regression tests for taxonomy cache invalidation (T4-A)."""
from __future__ import annotations

import time

from apd_gauntlet.report.taxonomy import (
    attack_technique_titles,
    cwe_titles,
    d3fend_titles,
    invalidate_all,
    invalidate_if_modified,
    nist_control_titles,
)


def test_invalidate_all_clears_every_cached_loader():
    # Prime caches.
    nist_control_titles()
    attack_technique_titles()
    cwe_titles()
    d3fend_titles()
    # All have a cached result now.
    info_before = nist_control_titles.cache_info()
    assert info_before.currsize == 1
    invalidate_all()
    info_after = nist_control_titles.cache_info()
    assert info_after.currsize == 0
    # Reload works.
    out = nist_control_titles()
    assert "AC-3" in out


def test_invalidate_all_is_idempotent():
    invalidate_all()
    invalidate_all()  # second call must not raise
    nist_control_titles()


def test_invalidate_if_modified_warmup_clears_nothing(tmp_path):
    # First call against a fresh dir is warmup.
    (tmp_path / "nist-controls.json").write_text(
        '{"controls": {"X-1": "x"}}', encoding="utf-8"
    )
    cleared = invalidate_if_modified(tmp_path)
    assert cleared == []


def test_invalidate_if_modified_clears_after_mtime_change(tmp_path):
    p = tmp_path / "nist-controls.json"
    p.write_text('{"controls": {"X-1": "x"}}', encoding="utf-8")
    # Warmup.
    invalidate_if_modified(tmp_path)
    # Touch the file with a future mtime.
    future = time.time() + 5
    import os
    os.utime(p, (future, future))
    cleared = invalidate_if_modified(tmp_path)
    assert "nist-controls.json" in cleared


def test_invalidate_if_modified_no_change_clears_nothing(tmp_path):
    p = tmp_path / "nist-controls.json"
    p.write_text('{"controls": {"X-1": "x"}}', encoding="utf-8")
    invalidate_if_modified(tmp_path)  # warmup
    cleared = invalidate_if_modified(tmp_path)  # no mtime change
    assert cleared == []


def test_reload_after_invalidate_picks_up_new_content(tmp_path, monkeypatch):
    """After invalidate_all, the loader rereads the source file."""
    from apd_gauntlet.report import taxonomy as tax
    p = tmp_path / "nist-controls.json"
    p.write_text(
        '{"controls": {"AC-3": "Original Title"}}', encoding="utf-8"
    )
    monkeypatch.setattr(tax, "_DATA", tmp_path)
    invalidate_all()
    out1 = nist_control_titles()
    assert out1["AC-3"] == "Original Title"
    p.write_text('{"controls": {"AC-3": "New Title"}}', encoding="utf-8")
    invalidate_all()
    out2 = nist_control_titles()
    assert out2["AC-3"] == "New Title"
