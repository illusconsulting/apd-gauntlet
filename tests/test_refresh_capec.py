"""Tests for the refresh-capec command (network mocked).

CAPEC is the derived CWE <-> ATT&CK bridge catalog (ADR-0022). The projection
keeps only the edges the bridge rollup needs: each attack pattern's
Related_Weaknesses (CWE) and its ATT&CK Taxonomy_Mapping techniques.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from apd_gauntlet.refresh_capec import (
    DEFAULT_TIMEOUT_SECONDS,
    MAX_RESPONSE_BYTES,
    fetch_capec_xml,
    project_capec_xml_to_json,
    refresh_capec,
)

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "reference_data" / "capec-sample.xml"


@pytest.fixture
def sample_capec_xml_bytes() -> bytes:
    return FIXTURE_PATH.read_bytes()


def test_refresh_capec_timeout_constant_is_60s() -> None:
    assert DEFAULT_TIMEOUT_SECONDS == 60


def test_refresh_capec_size_cap_is_200_mib() -> None:
    assert MAX_RESPONSE_BYTES == 200 * 1024 * 1024


def test_project_extracts_cwe_and_attack_edges(sample_capec_xml_bytes: bytes) -> None:
    projected = project_capec_xml_to_json(sample_capec_xml_bytes)
    assert "attack_patterns" in projected
    assert projected["source_sha256"] == hashlib.sha256(sample_capec_xml_bytes).hexdigest()
    assert "fetched_at" in projected and "source_url" in projected

    patterns = projected["attack_patterns"]
    # SQL Injection: both CWE edges (deduped) + the ATT&CK technique; the WASC
    # taxonomy mapping is ignored (only ATTACK is projected).
    sqli = patterns["CAPEC-66"]
    assert sqli["name"] == "SQL Injection"
    assert sqli["related_cwe"] == ["CWE-89", "CWE-1286"]
    assert sqli["related_attack"] == ["T1190"]


def test_project_keeps_sub_technique_id_format(sample_capec_xml_bytes: bytes) -> None:
    patterns = project_capec_xml_to_json(sample_capec_xml_bytes)["attack_patterns"]
    xss = patterns["CAPEC-63"]
    assert xss["related_cwe"] == ["CWE-79"]
    # Entry_ID 1059.007 -> T1059.007 (sub-technique form preserved).
    assert xss["related_attack"] == ["T1059.007"]


def test_project_keeps_cwe_only_pattern_with_empty_attack(sample_capec_xml_bytes: bytes) -> None:
    patterns = project_capec_xml_to_json(sample_capec_xml_bytes)["attack_patterns"]
    info = patterns["CAPEC-200"]
    assert info["related_cwe"] == ["CWE-200"]
    assert info["related_attack"] == []


def test_project_skips_deprecated_patterns(sample_capec_xml_bytes: bytes) -> None:
    patterns = project_capec_xml_to_json(sample_capec_xml_bytes)["attack_patterns"]
    # CAPEC-999 is Status="Deprecated" -> must not be projected.
    assert "CAPEC-999" not in patterns
    assert set(patterns) == {"CAPEC-66", "CAPEC-63", "CAPEC-200"}


def test_fetch_capec_xml_passes_timeout() -> None:
    with patch("apd_gauntlet.kb_fetch.urlopen") as mock:
        response = MagicMock()
        response.headers = {"Content-Length": "100"}
        response.read.return_value = b"<Attack_Pattern_Catalog/>"
        mock.return_value.__enter__.return_value = response
        mock.return_value.__exit__.return_value = False
        fetch_capec_xml()
        _, kwargs = mock.call_args
        assert kwargs.get("timeout") == DEFAULT_TIMEOUT_SECONDS


def test_refresh_capec_writes_to_target(tmp_path: Path, sample_capec_xml_bytes: bytes) -> None:
    target = tmp_path / "capec.json"
    with patch("apd_gauntlet.refresh_capec.fetch_capec_xml", return_value=sample_capec_xml_bytes):
        refresh_capec(output_path=target)
    assert target.exists()
    data = json.loads(target.read_text())
    assert data["source_sha256"] == hashlib.sha256(sample_capec_xml_bytes).hexdigest()
    assert data["source_url"]
    assert set(data["attack_patterns"]) == {"CAPEC-66", "CAPEC-63", "CAPEC-200"}
