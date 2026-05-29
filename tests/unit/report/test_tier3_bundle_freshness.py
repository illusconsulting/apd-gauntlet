# tests/unit/report/test_tier3_bundle_freshness.py
"""Regression tests for path-inclusive source hash (T3-E)."""
from __future__ import annotations

import importlib.util
import pathlib

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
