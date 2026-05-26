"""Tests for the Microsoft Threat Modeling Tool .tm7 parser."""

from __future__ import annotations

import re
from pathlib import Path

from apd_gauntlet.threat_model.microsoft_tmt import (
    _category_to_stride_letter,
    parse_microsoft_tmt,
)

FIXTURE = Path(__file__).parent / "fixtures" / "threat_models" / "sample-microsoft.tm7"


def test_parser_extracts_all_threats() -> None:
    entries = parse_microsoft_tmt(FIXTURE.read_bytes())
    assert len(entries) == 5  # matches fixture


def test_parser_emits_methodology_stride_and_high_confidence_for_known_categories() -> None:
    entries = parse_microsoft_tmt(FIXTURE.read_bytes())
    for entry in entries:
        assert entry["methodology"] == "stride"
    # At least the recognized-category threats should be high confidence
    known = [e for e in entries if e["framework_refs"]["stride_letter"] is not None]
    assert known
    for e in known:
        assert e["extraction_confidence"] == "high"


def test_parser_extracts_asset_name_via_source_guid_lookup() -> None:
    entries = parse_microsoft_tmt(FIXTURE.read_bytes())
    assets = {e["asset"] for e in entries}
    # At least one of the known element names from the fixture should appear
    assert assets & {"Web Server", "User Database", "SQL traffic"}


def test_parser_extracts_mitigation_when_present() -> None:
    entries = parse_microsoft_tmt(FIXTURE.read_bytes())
    with_mit = [e for e in entries if e["mitigation"] is not None]
    assert with_mit, "fixture has at least one mitigated threat"


def test_parser_emits_null_mitigation_when_absent() -> None:
    entries = parse_microsoft_tmt(FIXTURE.read_bytes())
    without_mit = [e for e in entries if e["mitigation"] is None]
    assert without_mit, "fixture has at least one unmitigated threat"


def test_category_to_stride_letter_exact_match() -> None:
    assert _category_to_stride_letter("Spoofing") == "S"
    assert _category_to_stride_letter("Tampering") == "T"
    assert _category_to_stride_letter("Repudiation") == "R"
    assert _category_to_stride_letter("Information Disclosure") == "I"
    assert _category_to_stride_letter("Denial of Service") == "D"
    assert _category_to_stride_letter("Elevation of Privilege") == "E"


def test_category_to_stride_letter_prefix_fallback() -> None:
    """TMT custom templates emit non-canonical category strings; first-word prefix wins."""
    assert _category_to_stride_letter("Spoofing the External Entity") == "S"
    assert _category_to_stride_letter("Tampering with Data Flow") == "T"
    assert _category_to_stride_letter("Information Disclosure of Data Store") == "I"


def test_category_to_stride_letter_unknown_returns_none() -> None:
    assert _category_to_stride_letter("Custom Threat Type") is None
    assert _category_to_stride_letter("") is None


def test_parser_handles_malformed_xml_via_recover_mode() -> None:
    """Truncate the fixture mid-element; lxml recover=True returns whatever parsed."""
    raw = FIXTURE.read_bytes()
    truncated = raw[: len(raw) // 2]
    entries = parse_microsoft_tmt(truncated)  # must not raise
    # Don't assert count — partial parse is best-effort
    assert isinstance(entries, list)


def test_parser_returns_empty_list_for_empty_bytes() -> None:
    assert parse_microsoft_tmt(b"") == []


def test_parser_extraction_confidence_drops_to_medium_for_unknown_category() -> None:
    """Threats whose Category we can't map still emit, but with extraction_confidence='medium'."""
    inline_xml = (
        b"<?xml version=\"1.0\" encoding=\"utf-8\"?>"
        b"<ThreatModel"
        b' xmlns="http://schemas.datacontract.org/2004/07/ThreatModeling.Model">'
        b"<ThreatInstances>"
        b"<KeyValueOfstringThreatpc_X>"
        b"<Key>{abc12345-1234-1234-1234-123456789abc}</Key>"
        b"<Value>"
        b"<Title>A made-up threat with an unknown category</Title>"
        b"<Properties>"
        b"<KeyValueOfstringstring>"
        b"<Key>Title</Key>"
        b"<Value>A made-up threat with an unknown category</Value>"
        b"</KeyValueOfstringstring>"
        b"<KeyValueOfstringstring>"
        b"<Key>Category</Key>"
        b"<Value>Custom Threat Type</Value>"
        b"</KeyValueOfstringstring>"
        b"</Properties>"
        b"</Value>"
        b"</KeyValueOfstringThreatpc_X>"
        b"</ThreatInstances>"
        b"</ThreatModel>"
    )
    entries = parse_microsoft_tmt(inline_xml)
    assert len(entries) == 1
    assert entries[0]["framework_refs"]["stride_letter"] is None
    assert entries[0]["extraction_confidence"] == "medium"


def test_parser_xxe_safe_against_external_entity_payload() -> None:
    """XXE: DOCTYPE attempting external entity resolution must not crash or read files."""
    xxe_payload = b"""<?xml version="1.0"?>
<!DOCTYPE foo [<!ENTITY xxe SYSTEM "file:///etc/passwd">]>
<ThreatModel xmlns="http://schemas.datacontract.org/2004/07/ThreatModeling.Model">&xxe;</ThreatModel>"""
    entries = parse_microsoft_tmt(xxe_payload)
    # Should return empty list (no threats parseable); no file read; no crash
    assert entries == []


def test_parser_all_entries_have_stable_ids_matching_schema_pattern() -> None:
    entries = parse_microsoft_tmt(FIXTURE.read_bytes())
    pattern = re.compile(r"^tm-[0-9a-f]{8}$")
    for entry in entries:
        assert pattern.match(entry["entry_id"]), entry["entry_id"]


def test_parser_emits_required_normalized_schema_fields() -> None:
    entries = parse_microsoft_tmt(FIXTURE.read_bytes())
    required_keys = {
        "entry_id",
        "asset",
        "threat",
        "mitigation",
        "methodology",
        "source_locator",
        "extraction_confidence",
        "framework_refs",
        "inferred_apd_goals",
    }
    for entry in entries:
        assert required_keys <= set(entry.keys())
        fr = entry["framework_refs"]
        assert {"stride_letter", "linddun_letter", "attack_tree_position", "mitre_attack"} <= set(
            fr.keys()
        )
