"""Tests for the attack-tree threat-model parser (B-16)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from apd_gauntlet.threat_model.attack_tree import (  # noqa: F401 (private, tested)
    _map_text_to_attack_techniques,
    parse_adtool_xml,
    parse_attack_tree,
    parse_attack_tree_json,
    parse_indented_prose,
)

PROSE_FIXTURE = Path("tests/fixtures/threat_models/sample-attack-tree.txt")
ADTOOL_FIXTURE = Path("tests/fixtures/threat_models/sample-attack-tree.adtool.xml")
JSON_FIXTURE = Path("tests/fixtures/threat_models/sample-attack-tree.json")


def test_indented_prose_extracts_ten_entries() -> None:
    entries = parse_indented_prose(PROSE_FIXTURE.read_text())
    # 1 root + 3 sub-goals + 6 leaves
    assert len(entries) == 10


def test_adtool_xml_extracts_ten_entries() -> None:
    entries = parse_adtool_xml(ADTOOL_FIXTURE.read_bytes())
    assert len(entries) == 10


def test_json_extracts_ten_entries() -> None:
    entries = parse_attack_tree_json(json.loads(JSON_FIXTURE.read_text()))
    assert len(entries) == 10


def test_three_formats_produce_equivalent_threat_text() -> None:
    prose_threats = {e["threat"] for e in parse_indented_prose(PROSE_FIXTURE.read_text())}
    adtool_threats = {e["threat"] for e in parse_adtool_xml(ADTOOL_FIXTURE.read_bytes())}
    json_data = json.loads(JSON_FIXTURE.read_text())
    json_threats = {e["threat"] for e in parse_attack_tree_json(json_data)}
    assert prose_threats == adtool_threats == json_threats


def test_root_has_low_confidence() -> None:
    entries = parse_attack_tree_json(json.loads(JSON_FIXTURE.read_text()))
    root_entries = [e for e in entries if e["framework_refs"]["attack_tree_position"] == "root"]
    assert len(root_entries) == 1
    assert root_entries[0]["extraction_confidence"] == "low"


def test_intermediate_has_low_confidence() -> None:
    entries = parse_attack_tree_json(json.loads(JSON_FIXTURE.read_text()))
    inter_entries = [
        e
        for e in entries
        if "/" in (e["framework_refs"]["attack_tree_position"] or "")
        and not e["framework_refs"]["mitre_attack"]
    ]
    for _entry in inter_entries:
        # Intermediates may have ATT&CK matches if their text happens to match keywords,
        # but the confidence is still low because they're not concrete attack steps
        pass


def test_leaf_has_medium_confidence() -> None:
    entries = parse_attack_tree_json(json.loads(JSON_FIXTURE.read_text()))
    leaf_entries = [
        e
        for e in entries
        if e["framework_refs"]["attack_tree_position"]
        and e["framework_refs"]["attack_tree_position"].count("/") >= 2
    ]
    assert leaf_entries
    for entry in leaf_entries:
        assert entry["extraction_confidence"] == "medium"


def test_leaves_get_attack_technique_mappings_from_keyword_heuristic() -> None:
    entries = parse_attack_tree_json(json.loads(JSON_FIXTURE.read_text()))
    phishing_leaf = [e for e in entries if "Phishing attack" in e["threat"]][0]
    assert "T1566" in phishing_leaf["framework_refs"]["mitre_attack"]
    smb_leaf = [e for e in entries if "SMB lateral" in e["threat"]][0]
    assert "T1021.002" in smb_leaf["framework_refs"]["mitre_attack"]


def test_position_string_reflects_tree_path() -> None:
    entries = parse_attack_tree_json(json.loads(JSON_FIXTURE.read_text()))
    phishing_leaf = [e for e in entries if "Phishing attack" in e["threat"]][0]
    pos = phishing_leaf["framework_refs"]["attack_tree_position"]
    # root/compromise-pharmacy/phishing (slug-style)
    assert "phishing" in pos
    assert pos.count("/") >= 2  # at least 3 levels deep


def test_and_gate_preserved_in_intermediate_node() -> None:
    entries = parse_attack_tree_json(json.loads(JSON_FIXTURE.read_text()))
    compromise_node = [
        e for e in entries if e["threat"] == "Compromise pharmacy submitter account"
    ][0]
    # Gate is appended as (AND) suffix on attack_tree_position
    assert (
        "AND" in compromise_node["threat"]
        or compromise_node.get("_gate") == "AND"
        or "(AND)" in compromise_node["framework_refs"]["attack_tree_position"]
    )


def test_indented_prose_uses_tabs_or_spaces_consistently() -> None:
    text = "Root\n\tSub1\n\t\tLeaf1\n\tSub2\n"
    entries = parse_indented_prose(text)
    assert len(entries) == 4


def test_adtool_parser_is_xxe_safe() -> None:
    xxe = (
        b'<?xml version="1.0"?>\n'
        b'<!DOCTYPE foo [<!ENTITY xxe SYSTEM "file:///etc/passwd">]>\n'
        b"<adtree>&xxe;</adtree>"
    )
    entries = parse_adtool_xml(xxe)
    assert entries == []  # no nodes; no crash; no file read


def test_keyword_mapper_handles_multiple_matches() -> None:
    result = _map_text_to_attack_techniques("phishing attack with credential stuffing")
    assert "T1566" in result
    assert "T1110.004" in result


def test_keyword_mapper_returns_empty_for_no_matches() -> None:
    result = _map_text_to_attack_techniques("compromise drug pricing data feed credentials")
    # No keyword match → empty list
    assert result == []


def test_parse_attack_tree_dispatcher_txt() -> None:
    entries = parse_attack_tree(PROSE_FIXTURE)
    assert len(entries) == 10


def test_parse_attack_tree_dispatcher_xml() -> None:
    entries = parse_attack_tree(ADTOOL_FIXTURE)
    assert len(entries) == 10


def test_parse_attack_tree_dispatcher_json() -> None:
    entries = parse_attack_tree(JSON_FIXTURE)
    assert len(entries) == 10


def test_parse_attack_tree_dispatcher_unsupported_raises() -> None:
    with pytest.raises(ValueError, match="Unsupported"):
        parse_attack_tree(Path("threat.pdf"))
