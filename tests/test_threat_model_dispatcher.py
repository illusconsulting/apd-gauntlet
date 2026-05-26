"""Tests for the threat-model format dispatcher (Task B-17)."""
from __future__ import annotations

from pathlib import Path

import pytest
from apd_gauntlet.threat_model.dispatcher import dispatch_parser


def test_dispatch_threat_dragon_json_auto_detected():
    result = dispatch_parser(Path("tests/fixtures/threat_models/sample-threat-dragon.json"))
    assert result["methodology"] == "stride"
    assert result["extraction_summary"]["parser_used"] == "threat_dragon"
    assert result["extraction_summary"]["entry_count"] >= 4


def test_dispatch_microsoft_tmt_by_extension():
    result = dispatch_parser(Path("tests/fixtures/threat_models/sample-microsoft.tm7"))
    assert result["methodology"] == "stride"
    assert "microsoft_tmt" in result["extraction_summary"]["parser_used"]


def test_dispatch_linddun_table_auto_detected_via_header_keywords():
    result = dispatch_parser(Path("tests/fixtures/threat_models/sample-linddun-table.md"))
    assert result["methodology"] == "linddun"
    assert "linddun_table" in result["extraction_summary"]["parser_used"]


def test_dispatch_stride_table_default_when_no_linddun_signature():
    result = dispatch_parser(Path("tests/fixtures/threat_models/sample-stride-table.md"))
    assert result["methodology"] == "stride"
    assert "stride_table" in result["extraction_summary"]["parser_used"]


def test_dispatch_attack_tree_indented_prose_by_extension():
    result = dispatch_parser(Path("tests/fixtures/threat_models/sample-attack-tree.txt"))
    assert result["methodology"] == "attack_tree"


def test_dispatch_attack_tree_adtool_xml_by_compound_extension():
    result = dispatch_parser(Path("tests/fixtures/threat_models/sample-attack-tree.adtool.xml"))
    assert result["methodology"] == "attack_tree"
    assert "adtool_xml" in result["extraction_summary"]["parser_used"]


def test_dispatch_attack_tree_json_sniffed_via_goal_and_children_keys():
    result = dispatch_parser(Path("tests/fixtures/threat_models/sample-attack-tree.json"))
    assert result["methodology"] == "attack_tree"
    assert "attack_tree.json" in result["extraction_summary"]["parser_used"]


def test_hint_overrides_extension():
    # Force LINDDUN interpretation of a STRIDE-headered table
    result = dispatch_parser(
        Path("tests/fixtures/threat_models/sample-stride-table.md"),
        hint="linddun",
    )
    assert result["methodology"] == "linddun"


def test_hint_pasta_returns_free_form_envelope():
    result = dispatch_parser(
        Path("tests/fixtures/threat_models/sample-stride-table.md"),
        hint="pasta",
    )
    assert result["methodology"] == "pasta"
    assert result["entries"] == []
    assert "LLM extraction required" in result["extraction_summary"]["parser_used"]


def test_unknown_hint_raises_value_error():
    with pytest.raises(ValueError, match="unknown methodology hint"):
        dispatch_parser(
            Path("tests/fixtures/threat_models/sample-stride-table.md"), hint="bogus"
        )


def test_envelope_extraction_summary_counts_per_confidence_level():
    result = dispatch_parser(Path("tests/fixtures/threat_models/sample-attack-tree.json"))
    summary = result["extraction_summary"]
    assert summary["entry_count"] == (
        summary["high_confidence_count"]
        + summary["medium_confidence_count"]
        + summary["low_confidence_count"]
    )
