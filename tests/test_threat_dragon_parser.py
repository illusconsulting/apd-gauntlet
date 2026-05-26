"""Tests for the OWASP Threat Dragon JSON parser."""
from __future__ import annotations

import json
from pathlib import Path

from apd_gauntlet.threat_model.threat_dragon import (
    _stride_letter_from_threat_type,
    parse_threat_dragon,
)

FIXTURE = Path(__file__).parent / "fixtures" / "threat_models" / "sample-threat-dragon.json"


def _load_fixture() -> dict:
    return json.loads(FIXTURE.read_text())


def test_parser_extracts_entries_from_threat_dragon():
    entries = parse_threat_dragon(_load_fixture())
    assert len(entries) >= 4
    for entry in entries:
        assert entry["asset"]
        assert entry["threat"]
        assert entry["methodology"] == "stride"
        assert entry["extraction_confidence"] == "high"
        assert entry["framework_refs"]["stride_letter"] in {"S", "T", "R", "I", "D", "E"}


def test_parser_handles_threat_without_mitigation():
    entries = parse_threat_dragon(_load_fixture())
    nulls = [e for e in entries if e["mitigation"] is None]
    assert nulls, "fixture should have at least one threat without a mitigation"


def test_parser_emits_mitigation_string_when_present():
    entries = parse_threat_dragon(_load_fixture())
    with_mit = [e for e in entries if e["mitigation"]]
    assert with_mit, "fixture should have at least one mitigated threat"
    for entry in with_mit:
        assert isinstance(entry["mitigation"], str)
        assert len(entry["mitigation"]) > 0


def test_parser_generates_stable_entry_ids():
    """Same input → same entry IDs across runs."""
    a = parse_threat_dragon(_load_fixture())
    b = parse_threat_dragon(_load_fixture())
    a_ids = sorted(e["entry_id"] for e in a)
    b_ids = sorted(e["entry_id"] for e in b)
    assert a_ids == b_ids


def test_parser_entry_ids_match_schema_pattern():
    """entry_id matches ^tm-[0-9a-f]{8}$ from threat-model-normalized schema."""
    import re

    entries = parse_threat_dragon(_load_fixture())
    pattern = re.compile(r"^tm-[0-9a-f]{8}$")
    for entry in entries:
        assert pattern.match(entry["entry_id"]), entry["entry_id"]


def test_parser_inferred_apd_goals_come_from_canonical_mapping():
    """Each entry's inferred_apd_goals is the canonical STRIDE→APD mapping."""
    from apd_gauntlet.threat_model.mappings import stride_letter_to_apd_goals

    entries = parse_threat_dragon(_load_fixture())
    for entry in entries:
        letter = entry["framework_refs"]["stride_letter"]
        assert entry["inferred_apd_goals"] == stride_letter_to_apd_goals(letter)


def test_parser_source_locator_is_diagram_path():
    """source_locator references the diagrams[i].cells[j].threats[k] path."""
    entries = parse_threat_dragon(_load_fixture())
    for entry in entries:
        loc = entry["source_locator"]
        assert loc.startswith("diagrams[")
        assert ".threats[" in loc


def test_parser_prefers_data_name_over_label_text():
    """When cell.data.name and cell.attrs.label.text differ, parser uses data.name."""
    # Construct a tiny inline doc with the divergence
    doc = {
        "detail": {
            "diagrams": [
                {
                    "id": 0,
                    "cells": [
                        {
                            "attrs": {"label": {"text": "Label Text"}},
                            "data": {
                                "name": "Data Name",
                                "threats": [
                                    {
                                        "title": "Test threat",
                                        "type": "Spoofing",
                                    }
                                ],
                            },
                        }
                    ],
                }
            ]
        }
    }
    entries = parse_threat_dragon(doc)
    assert entries[0]["asset"] == "Data Name"


def test_parser_returns_empty_list_for_doc_without_diagrams():
    """Defensive: empty / minimal doc returns []."""
    assert parse_threat_dragon({}) == []
    assert parse_threat_dragon({"detail": {}}) == []
    assert parse_threat_dragon({"detail": {"diagrams": []}}) == []


def test_stride_letter_from_threat_type_canonical():
    assert _stride_letter_from_threat_type("Spoofing") == "S"
    assert _stride_letter_from_threat_type("Tampering") == "T"
    assert _stride_letter_from_threat_type("Repudiation") == "R"
    assert _stride_letter_from_threat_type("Information disclosure") == "I"
    assert _stride_letter_from_threat_type("Denial of service") == "D"
    assert _stride_letter_from_threat_type("Elevation of privilege") == "E"


def test_stride_letter_from_threat_type_case_insensitive():
    assert _stride_letter_from_threat_type("SPOOFING") == "S"
    assert _stride_letter_from_threat_type("spoofing") == "S"


def test_stride_letter_from_threat_type_unknown_returns_none():
    assert _stride_letter_from_threat_type("Made-up category") is None
