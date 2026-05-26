from pathlib import Path

import pytest
from apd_gauntlet.threat_model.stride_table import (
    _is_empty_cell,
    _normalize_column_header,
    parse_stride_csv,
    parse_stride_markdown,
    parse_stride_table,
)

MD_FIXTURE = Path("tests/fixtures/threat_models/sample-stride-table.md")
CSV_FIXTURE = Path("tests/fixtures/threat_models/sample-stride-table.csv")


def test_markdown_parser_extracts_eight_entries():
    # The fixture has 10 populated STRIDE cells across 3 rows:
    # claim-ingress-API: S,T,I,D,E (5); adjudication-service: S,T,I,D (4); audit-log-writer: R (1)
    entries = parse_stride_markdown(MD_FIXTURE.read_text())
    assert len(entries) == 10

def test_csv_parser_extracts_eight_entries():
    entries = parse_stride_csv(CSV_FIXTURE.read_text())
    assert len(entries) == 10

def test_markdown_and_csv_produce_equivalent_entries():
    md_entries = parse_stride_markdown(MD_FIXTURE.read_text())
    csv_entries = parse_stride_csv(CSV_FIXTURE.read_text())
    # Same assets, same STRIDE letters, same threat text
    assert {(e["asset"], e["framework_refs"]["stride_letter"]) for e in md_entries} == \
           {(e["asset"], e["framework_refs"]["stride_letter"]) for e in csv_entries}

def test_all_entries_emit_methodology_stride_and_high_confidence():
    entries = parse_stride_markdown(MD_FIXTURE.read_text())
    for entry in entries:
        assert entry["methodology"] == "stride"
        assert entry["extraction_confidence"] == "high"

def test_stride_letters_correctly_mapped_from_column_position():
    entries = parse_stride_markdown(MD_FIXTURE.read_text())
    # claim-ingress-API row has populated cells in S, T, I, D, E (not R)
    claim_letters = sorted({
        e["framework_refs"]["stride_letter"]
        for e in entries if e["asset"] == "claim-ingress-API"
    })
    assert claim_letters == ["D", "E", "I", "S", "T"]

def test_empty_cells_dash_and_blank_are_skipped():
    entries = parse_stride_markdown(MD_FIXTURE.read_text())
    # audit-log-writer row has only R populated; the other 5 are skipped
    audit_entries = [e for e in entries if e["asset"] == "audit-log-writer"]
    assert len(audit_entries) == 1
    assert audit_entries[0]["framework_refs"]["stride_letter"] == "R"

def test_inferred_apd_goals_populated_from_mapping_table():
    entries = parse_stride_markdown(MD_FIXTURE.read_text())
    # An "E" (Elevation of Privilege) entry → both authenticity AND integrity
    e_entries = [e for e in entries if e["framework_refs"]["stride_letter"] == "E"]
    assert e_entries
    assert sorted(e_entries[0]["inferred_apd_goals"]) == ["authenticity", "integrity"]

def test_mitigation_is_null_for_table_format():
    # STRIDE-per-element tables don't have a mitigation column by convention
    entries = parse_stride_markdown(MD_FIXTURE.read_text())
    for entry in entries:
        assert entry["mitigation"] is None

def test_normalize_column_header_handles_letters_and_full_names():
    assert _normalize_column_header("S") == "S"
    assert _normalize_column_header("Spoofing") == "S"
    assert _normalize_column_header("Spoof") == "S"
    assert _normalize_column_header("Information Disclosure") == "I"
    assert _normalize_column_header("Info Disc") == "I"
    assert _normalize_column_header("Element") is None  # not a STRIDE column

@pytest.mark.parametrize("cell,expected", [
    ("", True), ("   ", True), ("—", True), ("-", True), ("–", True),
    ("N/A", True), ("n/a", True), ("None", True), ("none", True),
    ("real threat", False), ("0", False), (" data ", False),
])
def test_is_empty_cell(cell, expected):
    assert _is_empty_cell(cell) is expected

def test_dispatcher_routes_by_extension():
    """parse_stride_table reads the file path and routes by suffix."""
    entries_md = parse_stride_table(MD_FIXTURE)
    entries_csv = parse_stride_table(CSV_FIXTURE)
    assert len(entries_md) == 10
    assert len(entries_csv) == 10

def test_malformed_markdown_table_no_separator_row_still_parses():
    """A 'table' that lacks the |---| separator row still parses (lenient)."""
    text = "| Element | S | T |\n| api | spoof | tamper |\n"
    entries = parse_stride_markdown(text)
    assert len(entries) == 2  # spoof + tamper
