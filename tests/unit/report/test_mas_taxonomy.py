"""MASVS/MASWE title loaders read the bundled masvs.json / maswe.json catalogs
(projection discipline mirrors atlas_titles / d3fend_titles)."""
from __future__ import annotations

import json
import os
import time

import pytest
from apd_gauntlet.report import taxonomy as tax
from apd_gauntlet.report.taxonomy import (
    invalidate_if_modified,
    masvs_titles,
    masvs_url,
    maswe_titles,
    maswe_url,
    reference_db_versions,
)


@pytest.fixture(autouse=True)
def _isolate():
    tax.invalidate_all()
    yield
    tax.invalidate_all()


def test_masvs_titles_resolves_bundled_controls() -> None:
    titles = masvs_titles()
    assert titles["MASVS-STORAGE-1"] == "The app securely stores sensitive data."
    # All 8 categories' first control ship in the bundled subset.
    assert "MASVS-PRIVACY-1" in titles
    assert len(titles) >= 8


def test_maswe_titles_resolves_bundled_weaknesses() -> None:
    titles = maswe_titles()
    assert "Logs" in titles["MASWE-0001"]
    assert "MASWE-0013" in titles  # a deprecated entry still carries a title


def test_masvs_titles_reads_monkeypatched_data(tmp_path, monkeypatch) -> None:
    p = tmp_path / "masvs.json"
    p.write_text(
        json.dumps(
            {
                "_meta": {},
                "controls": {
                    "MASVS-CODE-9": {
                        "title": "X",
                        "category": "MASVS-CODE",
                        "category_title": "Code Quality",
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(tax, "_DATA", tmp_path)
    tax.invalidate_all()
    assert masvs_titles() == {"MASVS-CODE-9": "X"}


def test_masvs_titles_missing_file_is_empty(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(tax, "_DATA", tmp_path)
    tax.invalidate_all()
    assert masvs_titles() == {}


def test_masvs_url_is_pure_regex_no_catalog() -> None:
    assert masvs_url("MASVS-STORAGE-1") == "https://mas.owasp.org/MASVS/controls/MASVS-STORAGE-1/"
    assert masvs_url("MASVS-CRYPTO-2") == "https://mas.owasp.org/MASVS/controls/MASVS-CRYPTO-2/"


def test_masvs_url_rejects_non_control_ids() -> None:
    assert masvs_url("MASVS-STORAGE") is None  # category, not control
    assert masvs_url("MASWE-0001") is None
    assert masvs_url("") is None
    assert masvs_url("MASVS-BOGUS-1") is None  # unknown category prefix


def test_maswe_url_reads_filing_category_from_catalog() -> None:
    # MASWE-0001 ships in the bundled maswe.json with category MASVS-STORAGE.
    assert maswe_url("MASWE-0001") == "https://mas.owasp.org/MASWE/MASVS-STORAGE/MASWE-0001/"


def test_maswe_url_unknown_category_returns_none() -> None:
    # A weakness id not present in the catalog has no resolvable category.
    assert maswe_url("MASWE-9999") is None
    assert maswe_url("") is None


def test_reference_db_versions_includes_masvs_and_maswe() -> None:
    versions = reference_db_versions()
    assert "masvs" in versions
    assert "maswe" in versions
    assert versions["masvs"]["count"] >= 8
    assert versions["masvs"]["source"]  # _meta.source surfaced
    assert versions["maswe"]["count"] >= 1


def test_invalidate_if_modified_clears_masvs_cache(tmp_path) -> None:
    p = tmp_path / "masvs.json"
    p.write_text('{"_meta": {}, "controls": {}}', encoding="utf-8")
    invalidate_if_modified(tmp_path)  # warmup
    future = time.time() + 5
    os.utime(p, (future, future))
    cleared = invalidate_if_modified(tmp_path)
    assert "masvs.json" in cleared


def test_invalidate_if_modified_clears_maswe_caches(tmp_path) -> None:
    p = tmp_path / "maswe.json"
    p.write_text('{"_meta": {}, "weaknesses": {}}', encoding="utf-8")
    invalidate_if_modified(tmp_path)  # warmup
    future = time.time() + 5
    os.utime(p, (future, future))
    cleared = invalidate_if_modified(tmp_path)
    assert "maswe.json" in cleared
    # Regression guard: the consistency-lint accessor maswe_masvs_parents reads
    # maswe.json and MUST be among the cleared loaders, else check_maswe_masvs_
    # consistency would grade against stale parent maps after a refresh.
    from apd_gauntlet.report import taxonomy as _tx
    _tx.maswe_masvs_parents()  # prime its lru_cache from the bundled catalog
    assert _tx.maswe_masvs_parents.cache_info().currsize == 1
    os.utime(p, (future + 2, future + 2))
    invalidate_if_modified(tmp_path)
    assert _tx.maswe_masvs_parents.cache_info().currsize == 0
