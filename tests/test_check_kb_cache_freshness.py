"""Unit tests for the KB-cache freshness gate."""
from __future__ import annotations

import importlib.util
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
_SPEC = importlib.util.spec_from_file_location(
    "check_kb_cache_freshness", REPO_ROOT / "tools" / "check_kb_cache_freshness.py"
)
mod = importlib.util.module_from_spec(_SPEC)
assert _SPEC.loader is not None
_SPEC.loader.exec_module(mod)


def test_metadata_block_prefers_meta() -> None:
    assert mod.metadata_block({"_meta": {"source": "x"}, "k": 1}) == {"source": "x"}


def test_metadata_block_falls_back_to_top_level() -> None:
    top = {"source_url": "x", "source_sha256": "y", "fetched_at": "z", "entries": []}
    assert mod.metadata_block(top) is top


def test_check_one_accepts_meta_source_sha256_fetched_at() -> None:
    ok, why = mod.check_one("f.json", {"_meta": {
        "source": "u", "source_sha256": "h", "fetched_at": "2026-06-10"}})
    assert ok, why


def test_check_one_accepts_top_level_source_url_and_commit() -> None:
    ok, why = mod.check_one("f.json", {
        "source_url": "u", "commit": "abc", "fetched_at": "2026-06-10"})
    assert ok, why


def test_check_one_rejects_missing_hash() -> None:
    ok, why = mod.check_one("f.json", {"_meta": {
        "source": "u", "fetched_at": "2026-06-10"}})
    assert not ok
    assert "source_sha256" in why or "commit" in why


def test_check_one_rejects_missing_source() -> None:
    ok, why = mod.check_one("f.json", {"_meta": {
        "source_sha256": "h", "fetched_at": "2026-06-10"}})
    assert not ok


def test_main_passes_on_the_real_data_dir() -> None:
    assert mod.main() == 0


def test_covered_set_and_exempt_set_are_disjoint() -> None:
    assert not (set(mod.COVERED) & set(mod.EXEMPT))


def test_exempt_set_is_documented() -> None:
    for name in mod.EXEMPT:
        assert name in mod.EXEMPT_REASON
        assert mod.EXEMPT_REASON[name].strip()
