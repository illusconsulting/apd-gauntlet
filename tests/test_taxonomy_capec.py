"""CAPEC title/URL resolution in report.taxonomy (ADR-0022 derived bridge)."""
from __future__ import annotations

from apd_gauntlet.report.taxonomy import capec_titles, capec_url, reference_db_versions


def test_capec_titles_resolve_real_anchor():
    titles = capec_titles()
    # CAPEC-2 is a known anchor in the bundled catalog.
    assert titles.get("CAPEC-2") == "Inducing Account Lockout"
    assert all(isinstance(v, str) and v for v in titles.values())


def test_capec_url_is_pure_regex():
    assert capec_url("CAPEC-66") == "https://capec.mitre.org/data/definitions/66.html"
    assert capec_url("CAPEC-2") == "https://capec.mitre.org/data/definitions/2.html"
    # Not a CAPEC id -> no fabricated link.
    assert capec_url("not-a-capec") is None
    assert capec_url("T1190") is None
    assert capec_url("CWE-89") is None


def test_capec_registered_in_reference_db_versions():
    dbs = reference_db_versions()
    assert "capec" in dbs
    assert dbs["capec"]["count"] >= 100  # 558 patterns in the bundled catalog
