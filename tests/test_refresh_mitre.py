"""Tests for the refresh-mitre command (network mocked)."""
from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest
from apd_gauntlet.refresh_mitre import (
    DEFAULT_TIMEOUT_SECONDS,
    MAX_RESPONSE_BYTES,
    fetch_and_project,
    fetch_mitre_bundle,
)

FAKE_BUNDLE = {
    "created": "2026-01-01",
    "objects": [
        {"id": "course-of-action--1", "type": "course-of-action",
         "external_references": [{"source_name": "mitre-attack", "external_id": "M1041"}]},
        {"id": "attack-pattern--1", "type": "attack-pattern",
         "external_references": [{"source_name": "mitre-attack", "external_id": "T1530"}]},
        {"type": "relationship", "relationship_type": "mitigates",
         "source_ref": "course-of-action--1", "target_ref": "attack-pattern--1"},
    ],
}


def _mock_response(body: bytes, content_length: str | None = None) -> MagicMock:
    response = MagicMock()
    response.headers = {"Content-Length": content_length} if content_length else {}
    response.read.return_value = body
    return response


def test_refresh_mitre_timeout_constant_is_60s() -> None:
    assert DEFAULT_TIMEOUT_SECONDS == 60


def test_refresh_mitre_size_cap_is_200_mib() -> None:
    assert MAX_RESPONSE_BYTES == 200 * 1024 * 1024


def test_fetch_and_project(tmp_path):
    out = tmp_path / "out.json"
    body = json.dumps(FAKE_BUNDLE).encode()
    with patch("apd_gauntlet.refresh_mitre.urlopen") as mock:
        mock.return_value.__enter__.return_value = _mock_response(body, str(len(body)))
        mock.return_value.__exit__.return_value = False
        fetch_and_project(out)
    data = json.loads(out.read_text())
    assert data["mitigations"]["M1041"] == ["T1530"]


def test_fetch_mitre_bundle_passes_timeout() -> None:
    body = json.dumps(FAKE_BUNDLE).encode()
    with patch("apd_gauntlet.refresh_mitre.urlopen") as mock:
        mock.return_value.__enter__.return_value = _mock_response(body, str(len(body)))
        mock.return_value.__exit__.return_value = False
        fetch_mitre_bundle()
    _, kwargs = mock.call_args
    assert kwargs.get("timeout") == DEFAULT_TIMEOUT_SECONDS


def test_fetch_mitre_bundle_rejects_oversize_response_content_length() -> None:
    """Content-Length pre-check rejects responses that advertise > 200 MiB."""
    with patch("apd_gauntlet.refresh_mitre.urlopen") as mock:
        response = MagicMock()
        response.headers = {"Content-Length": str(MAX_RESPONSE_BYTES + 1)}
        mock.return_value.__enter__.return_value = response
        mock.return_value.__exit__.return_value = False
        with pytest.raises(ValueError, match="exceeds maximum"):
            fetch_mitre_bundle()


def test_fetch_mitre_bundle_rejects_oversize_response_post_read(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Defense in depth: even with missing/false Content-Length, oversize body raises.

    Monkeypatches ``MAX_RESPONSE_BYTES`` down to a tiny value so the test does not
    actually allocate 200 MiB of memory.
    """
    monkeypatch.setattr("apd_gauntlet.refresh_mitre.MAX_RESPONSE_BYTES", 1024)
    oversize = b"x" * 2048
    with patch("apd_gauntlet.refresh_mitre.urlopen") as mock:
        response = MagicMock()
        response.headers = {}  # No Content-Length advertised.
        response.read.return_value = oversize
        mock.return_value.__enter__.return_value = response
        mock.return_value.__exit__.return_value = False
        with pytest.raises(ValueError, match="exceeds maximum"):
            fetch_mitre_bundle()
