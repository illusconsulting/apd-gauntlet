"""Tests for the refresh-cwe command (network mocked)."""
from __future__ import annotations

import hashlib
import io
import json
import zipfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from apd_gauntlet.refresh_cwe import (
    DEFAULT_TIMEOUT_SECONDS,
    MAX_RESPONSE_BYTES,
    fetch_cwe_xml,
    project_cwe_xml_to_json,
    refresh_cwe,
)

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "reference_data" / "cwe-sample.xml"


def _zip_bytes(xml_bytes: bytes, member_name: str = "cwec_v4.20-test.xml") -> bytes:
    """Pack the given XML bytes into an in-memory zip, matching MITRE's layout."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(member_name, xml_bytes)
    return buf.getvalue()


@pytest.fixture
def sample_cwe_xml_bytes() -> bytes:
    """Two-weakness fixture XML matching the CWE 4.x schema shape."""
    return FIXTURE_PATH.read_bytes()


@pytest.fixture
def sample_cwe_zip_bytes(sample_cwe_xml_bytes: bytes) -> bytes:
    """The fixture XML wrapped in a zip, mimicking the live MITRE download."""
    return _zip_bytes(sample_cwe_xml_bytes)


@pytest.fixture
def mock_urlopen(sample_cwe_zip_bytes: bytes):
    with patch("apd_gauntlet.refresh_cwe.urlopen") as mock:
        response = MagicMock()
        response.headers = {"Content-Length": str(len(sample_cwe_zip_bytes))}
        response.read.return_value = sample_cwe_zip_bytes
        mock.return_value.__enter__.return_value = response
        mock.return_value.__exit__.return_value = False
        yield mock


def test_refresh_cwe_timeout_constant_is_60s() -> None:
    assert DEFAULT_TIMEOUT_SECONDS == 60


def test_refresh_cwe_size_cap_is_200_mib() -> None:
    assert MAX_RESPONSE_BYTES == 200 * 1024 * 1024


def test_project_extracts_required_fields(sample_cwe_xml_bytes: bytes) -> None:
    """The fixture has 2 weaknesses with the fields the projection cares about."""
    projected = project_cwe_xml_to_json(sample_cwe_xml_bytes)
    assert "entries" in projected
    assert "source_sha256" in projected
    assert "fetched_at" in projected
    assert len(projected["entries"]) == 2

    entry = projected["entries"][0]
    assert set(entry.keys()) >= {
        "cwe_id",
        "name",
        "abstraction",
        "parents",
        "demonstrative_examples_present",
        "observed_examples_present",
    }
    # source_sha256 matches the raw fixture content.
    assert projected["source_sha256"] == hashlib.sha256(sample_cwe_xml_bytes).hexdigest()

    by_id = {e["cwe_id"]: e for e in projected["entries"]}
    assert "CWE-79" in by_id
    assert "CWE-89" in by_id
    cwe79 = by_id["CWE-79"]
    assert cwe79["abstraction"] == "base"
    # Only ChildOf relationships become parents.
    assert cwe79["parents"] == ["CWE-74"]
    assert cwe79["demonstrative_examples_present"] is True
    assert cwe79["observed_examples_present"] is True
    cwe89 = by_id["CWE-89"]
    assert cwe89["parents"] == ["CWE-74"]
    assert cwe89["demonstrative_examples_present"] is False
    assert cwe89["observed_examples_present"] is False


def test_fetch_cwe_xml_passes_timeout(mock_urlopen: MagicMock) -> None:
    fetch_cwe_xml()
    _, kwargs = mock_urlopen.call_args
    assert kwargs.get("timeout") == DEFAULT_TIMEOUT_SECONDS


def test_fetch_cwe_xml_rejects_oversize_response_content_length() -> None:
    """Content-Length pre-check rejects responses that advertise > 200 MiB."""
    with patch("apd_gauntlet.refresh_cwe.urlopen") as mock:
        response = MagicMock()
        response.headers = {"Content-Length": str(MAX_RESPONSE_BYTES + 1)}
        mock.return_value.__enter__.return_value = response
        mock.return_value.__exit__.return_value = False
        with pytest.raises(ValueError, match="exceeds maximum"):
            fetch_cwe_xml()


def test_fetch_cwe_xml_rejects_oversize_response_post_read(monkeypatch: pytest.MonkeyPatch) -> None:
    """Defense in depth: even with missing/false Content-Length, oversize body raises.

    We monkeypatch ``MAX_RESPONSE_BYTES`` down to a tiny value so the test does not
    actually allocate 200 MiB of memory.
    """
    monkeypatch.setattr("apd_gauntlet.refresh_cwe.MAX_RESPONSE_BYTES", 1024)
    fake_oversize_payload = b"x" * 2048
    with patch("apd_gauntlet.refresh_cwe.urlopen") as mock:
        response = MagicMock()
        response.headers = {}  # No Content-Length advertised.
        response.read.return_value = fake_oversize_payload
        mock.return_value.__enter__.return_value = response
        mock.return_value.__exit__.return_value = False
        with pytest.raises(ValueError, match="exceeds maximum"):
            fetch_cwe_xml()


def test_refresh_cwe_writes_to_data_dir(tmp_path: Path, sample_cwe_xml_bytes: bytes) -> None:
    """End-to-end: refresh_cwe writes a valid JSON file to the target path."""
    target = tmp_path / "cwe.json"
    with patch("apd_gauntlet.refresh_cwe.fetch_cwe_xml", return_value=sample_cwe_xml_bytes):
        refresh_cwe(output_path=target)
    assert target.exists()
    data = json.loads(target.read_text())
    assert data["source_sha256"] == hashlib.sha256(sample_cwe_xml_bytes).hexdigest()
    assert data["source_url"]
    assert "entries" in data and len(data["entries"]) == 2
