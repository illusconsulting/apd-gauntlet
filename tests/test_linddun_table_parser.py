from pathlib import Path

import pytest
from apd_gauntlet.threat_model.linddun_table import (
    _is_empty_cell,
    _normalize_column_header,
    is_linddun_table,
    parse_linddun_csv,
    parse_linddun_markdown,
    parse_linddun_table,
)

MD_FIXTURE = Path("tests/fixtures/threat_models/sample-linddun-table.md")
CSV_FIXTURE = Path("tests/fixtures/threat_models/sample-linddun-table.csv")
FULLNAMES_FIXTURE = Path("tests/fixtures/threat_models/sample-linddun-table-fullnames.md")


def test_linddun_parser_extracts_entries_with_disambiguated_letters():
    entries = parse_linddun_markdown(MD_FIXTURE.read_text())
    # Member login row has all 7 columns populated
    login_entries = [e for e in entries if e["asset"] == "Member login flow"]
    assert len(login_entries) == 7
    letters = sorted(e["framework_refs"]["linddun_letter"] for e in login_entries)
    assert letters == [
        "D_etectability", "D_isclosure", "I", "L", "N_compliance", "N_repudiation", "U",
    ]


def test_linddun_n_repudiation_maps_to_apd_non_repudiation():
    entries = parse_linddun_markdown(MD_FIXTURE.read_text())
    n_rep_entries = [e for e in entries if e["framework_refs"]["linddun_letter"] == "N_repudiation"]
    assert n_rep_entries
    for entry in n_rep_entries:
        assert "non_repudiation" in entry["inferred_apd_goals"]


def test_linddun_n_compliance_maps_to_apd_non_repudiation_domain_specific():
    entries = parse_linddun_markdown(MD_FIXTURE.read_text())
    n_compl_entries = [
        e for e in entries if e["framework_refs"]["linddun_letter"] == "N_compliance"
    ]
    assert n_compl_entries
    # Domain-specific override happens at evaluator time; here just check the base mapping
    for entry in n_compl_entries:
        assert "non_repudiation" in entry["inferred_apd_goals"]


def test_linddun_d_etectability_vs_d_isclosure_are_distinct():
    entries = parse_linddun_markdown(MD_FIXTURE.read_text())
    d_etc = {
        e["threat"] for e in entries if e["framework_refs"]["linddun_letter"] == "D_etectability"
    }
    d_isc = {
        e["threat"] for e in entries if e["framework_refs"]["linddun_letter"] == "D_isclosure"
    }
    assert d_etc & d_isc == set()  # no threat appears in both


def test_linddun_parser_handles_fullname_headers():
    entries = parse_linddun_markdown(FULLNAMES_FIXTURE.read_text())
    # Same logical content → same entry count + same letter distribution
    login_letters = sorted(
        e["framework_refs"]["linddun_letter"]
        for e in entries if e["asset"] == "Member login flow"
    )
    assert login_letters == [
        "D_etectability", "D_isclosure", "I", "L", "N_compliance", "N_repudiation", "U",
    ]


def test_is_linddun_table_detector_returns_true_for_linddun_headers():
    headers = ["Data Flow", "L", "I", "N", "D", "D", "U", "N"]
    assert is_linddun_table(headers)

    headers_fullnames = [
        "Data Flow", "Linkability", "Identifiability", "Non-repudiation",
        "Detectability", "Disclosure of information", "Unawareness", "Non-compliance",
    ]
    assert is_linddun_table(headers_fullnames)


def test_is_linddun_table_detector_returns_false_for_stride_headers():
    headers = ["Element", "S", "T", "R", "I", "D", "E"]
    assert not is_linddun_table(headers)


def test_markdown_parser_extracts_ten_entries():
    # login: 7, claim-history: 2, pharmacy: 1 → total 10
    entries = parse_linddun_markdown(MD_FIXTURE.read_text())
    assert len(entries) == 10


def test_csv_parser_extracts_ten_entries():
    entries = parse_linddun_csv(CSV_FIXTURE.read_text())
    assert len(entries) == 10


def test_markdown_and_csv_produce_equivalent_entries():
    md_entries = parse_linddun_markdown(MD_FIXTURE.read_text())
    csv_entries = parse_linddun_csv(CSV_FIXTURE.read_text())
    assert {(e["asset"], e["framework_refs"]["linddun_letter"]) for e in md_entries} == \
           {(e["asset"], e["framework_refs"]["linddun_letter"]) for e in csv_entries}


def test_all_entries_emit_methodology_linddun_and_high_confidence():
    entries = parse_linddun_markdown(MD_FIXTURE.read_text())
    for entry in entries:
        assert entry["methodology"] == "linddun"
        assert entry["extraction_confidence"] == "high"


def test_mitigation_is_null_for_table_format():
    entries = parse_linddun_markdown(MD_FIXTURE.read_text())
    for entry in entries:
        assert entry["mitigation"] is None


def test_normalize_column_header_single_letters_use_position():
    # Position 3 → N_repudiation; position 7 → N_compliance
    assert _normalize_column_header("N", 3) == "N_repudiation"
    assert _normalize_column_header("N", 7) == "N_compliance"
    # Position 4 → D_etectability; position 5 → D_isclosure
    assert _normalize_column_header("D", 4) == "D_etectability"
    assert _normalize_column_header("D", 5) == "D_isclosure"
    # Unambiguous single letters
    assert _normalize_column_header("L", 1) == "L"
    assert _normalize_column_header("I", 2) == "I"
    assert _normalize_column_header("U", 6) == "U"


def test_normalize_column_header_fullnames_ignore_position():
    assert _normalize_column_header("Linkability", 0) == "L"
    assert _normalize_column_header("Identifiability", 99) == "I"
    assert _normalize_column_header("Non-repudiation", 0) == "N_repudiation"
    assert _normalize_column_header("Detectability", 0) == "D_etectability"
    assert _normalize_column_header("Disclosure of information", 0) == "D_isclosure"
    assert _normalize_column_header("Unawareness", 0) == "U"
    assert _normalize_column_header("Non-compliance", 0) == "N_compliance"
    assert _normalize_column_header("Data Flow", 0) is None


def test_dispatcher_routes_by_extension():
    entries_md = parse_linddun_table(MD_FIXTURE)
    entries_csv = parse_linddun_table(CSV_FIXTURE)
    assert len(entries_md) == 10
    assert len(entries_csv) == 10


def test_dispatcher_raises_on_unknown_extension(tmp_path: Path):
    f = tmp_path / "threat.xml"
    f.write_text("<xml/>")
    with pytest.raises(ValueError, match="Unsupported"):
        parse_linddun_table(f)


def test_empty_cells_various_forms_are_skipped():
    # Pharmacy row has only L populated; all others are "—" or empty
    entries = parse_linddun_markdown(MD_FIXTURE.read_text())
    pharmacy_entries = [e for e in entries if e["asset"] == "Pharmacy lookup search"]
    assert len(pharmacy_entries) == 1
    assert pharmacy_entries[0]["framework_refs"]["linddun_letter"] == "L"


@pytest.mark.parametrize("cell,expected", [
    ("", True), ("   ", True), ("—", True), ("-", True), ("–", True),
    ("N/A", True), ("n/a", True), ("None", True), ("none", True),
    ("real threat", False), ("0", False), (" data ", False),
])
def test_is_empty_cell(cell: str, expected: bool) -> None:
    assert _is_empty_cell(cell) is expected


def test_malformed_markdown_no_separator_row_still_parses():
    """Lenient parser: missing |---| separator row should still work."""
    text = "| Data Flow | L | I |\n| api gateway | link threat | id threat |\n"
    entries = parse_linddun_markdown(text)
    assert len(entries) == 2


def test_fullnames_and_single_letter_fixtures_have_same_total_entry_count():
    md_entries = parse_linddun_markdown(MD_FIXTURE.read_text())
    full_entries = parse_linddun_markdown(FULLNAMES_FIXTURE.read_text())
    assert len(md_entries) == len(full_entries)
