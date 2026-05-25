"""Tests for the refresh-mitre command (network mocked)."""
from __future__ import annotations
import json
from unittest.mock import patch, MagicMock
from apd_gauntlet.refresh_mitre import fetch_and_project


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


def test_fetch_and_project(tmp_path):
    out = tmp_path / "out.json"
    fake_response = MagicMock()
    fake_response.__enter__ = MagicMock(return_value=fake_response)
    fake_response.__exit__ = MagicMock(return_value=False)
    fake_response.read = MagicMock(return_value=json.dumps(FAKE_BUNDLE).encode())
    with patch("urllib.request.urlopen", return_value=fake_response):
        fetch_and_project(out)
    data = json.loads(out.read_text())
    assert data["mitigations"]["M1041"] == ["T1530"]
