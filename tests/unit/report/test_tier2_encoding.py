# tests/unit/report/test_tier2_encoding.py
"""Regression tests for explicit UTF-8 encoding in the report pipeline.

These tests pin the pipeline against locale variance — without explicit
encoding, a `LC_ALL=C` shell or Windows cp1252 default would raise
UnicodeDecodeError on any fixture containing UTF-8 content.
"""
from __future__ import annotations

import json

from apd_gauntlet.report.loader import _yaml


def test_yaml_loader_handles_utf8_under_c_locale(tmp_path, monkeypatch):
    """YAML containing UTF-8 chars must parse even with LC_ALL=C set."""
    fixture = tmp_path / "test.yaml"
    fixture.write_text(
        "title: « Curly » — accents éñç\n"
        "rationale: \"Smart 'quotes' and em-dashes —\"\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("LC_ALL", "C")
    monkeypatch.setenv("LANG", "C")
    doc = _yaml(fixture)
    assert "Curly" in doc["title"]
    assert "éñç" in doc["title"]


def test_data_js_round_trips_utf8(tmp_path, monkeypatch):
    """emit.write_data_js / read_text round-trip must preserve UTF-8."""
    from apd_gauntlet.report.emit import write_data_js
    monkeypatch.setenv("LC_ALL", "C")
    monkeypatch.setenv("LANG", "C")
    payload = {"subject": "PBM — Adjudication ❤", "note": "éñç"}
    target = tmp_path / "data.js"
    write_data_js(payload, target)
    body = target.read_text(encoding="utf-8")
    data = json.loads(body[body.find("{"):body.rfind("}") + 1])
    assert data["subject"] == "PBM — Adjudication ❤"
    assert data["note"] == "éñç"


def test_taxonomy_loaders_handle_utf8_data_files(monkeypatch):
    """The bundled JSON catalogs may contain UTF-8 names; loaders must work
    under a C locale."""
    from apd_gauntlet.report.taxonomy import (
        attack_technique_titles,
        cwe_titles,
        d3fend_titles,
        nist_control_titles,
    )
    # Bust the lru_cache so the loader runs under the patched env.
    for fn in (attack_technique_titles, cwe_titles, d3fend_titles, nist_control_titles):
        fn.cache_clear()
    monkeypatch.setenv("LC_ALL", "C")
    monkeypatch.setenv("LANG", "C")
    # If any loader implicitly used the system encoding, this would raise.
    assert isinstance(nist_control_titles(), dict)
    assert isinstance(attack_technique_titles(), dict)
    assert isinstance(cwe_titles(), dict)
    assert isinstance(d3fend_titles(), dict)
