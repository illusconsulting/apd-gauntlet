"""Tests for the refresh-mitre command (network mocked)."""
from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest
from apd_gauntlet.refresh_mitre import (
    DEFAULT_TIMEOUT_SECONDS,
    MAX_RESPONSE_BYTES,
    MOBILE_URL,
    fetch_and_project,
    fetch_mitre_bundle,
    merge_mobile_technique_titles,
    project_technique_titles,
)

FAKE_MOBILE_BUNDLE = {
    "objects": [
        {"id": "attack-pattern--m1", "type": "attack-pattern", "name": "Hide Artifacts",
         "external_references": [{"source_name": "mitre-attack", "external_id": "T1628"}]},
        {"id": "attack-pattern--m2", "type": "attack-pattern", "name": "Suppress Application Icon",
         "x_mitre_is_subtechnique": True,
         "external_references": [{"source_name": "mitre-attack", "external_id": "T1628.001"}]},
        {"id": "attack-pattern--m3", "type": "attack-pattern", "name": "Old Revoked Technique",
         "revoked": True,
         "external_references": [{"source_name": "mitre-attack", "external_id": "T1453"}]},
        # An id that ALSO exists in the enterprise catalog — Enterprise must win.
        {"id": "attack-pattern--m4", "type": "attack-pattern", "name": "Mobile Valid Accounts",
         "external_references": [{"source_name": "mitre-attack", "external_id": "T1078"}]},
    ],
}

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


def test_project_technique_titles_parent_prefix_and_revoked() -> None:
    titles = project_technique_titles(FAKE_MOBILE_BUNDLE)
    # Top-level technique: plain name.
    assert titles["T1628"] == "Hide Artifacts"
    # Sub-technique: prefixed with the parent's name.
    assert titles["T1628.001"] == "Hide Artifacts: Suppress Application Icon"
    # Revoked techniques are retained so legacy citations still resolve.
    assert titles["T1453"] == "Old Revoked Technique"


def test_merge_mobile_technique_titles_is_additive_and_idempotent(tmp_path) -> None:
    techniques = tmp_path / "mitre-attack-techniques.json"
    techniques.write_text(
        json.dumps(
            {
                "_meta": {"source": "enterprise", "notes": "base."},
                # Enterprise entry for T1078 must survive the merge unchanged.
                "techniques": {"T1078": "Valid Accounts"},
            },
            indent=2,
            sort_keys=False,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    body = json.dumps(FAKE_MOBILE_BUNDLE).encode()
    with patch("apd_gauntlet.refresh_mitre.fetch_mitre_bundle", return_value=body) as fetch:
        stats = merge_mobile_technique_titles(techniques, fetched_at="2026-06-02")
    # Fetched the Mobile matrix, not the enterprise one.
    fetch.assert_called_once_with(MOBILE_URL)
    data = json.loads(techniques.read_text(encoding="utf-8"))
    t = data["techniques"]
    # Enterprise entry preserved (Enterprise wins on the shared T1078 id).
    assert t["T1078"] == "Valid Accounts"
    # Mobile entries added.
    assert t["T1628"] == "Hide Artifacts"
    assert t["T1628.001"] == "Hide Artifacts: Suppress Application Icon"
    assert t["T1453"] == "Old Revoked Technique"
    # T1078 was NOT counted as added (already present).
    assert stats["added"] == 3
    assert stats["total"] == 4
    # Provenance recorded.
    assert data["_meta"]["mobile_source"] == MOBILE_URL
    assert data["_meta"]["mobile_fetched_at"] == "2026-06-02"
    # Idempotent: a second merge adds nothing and does not duplicate the note.
    with patch("apd_gauntlet.refresh_mitre.fetch_mitre_bundle", return_value=body):
        stats2 = merge_mobile_technique_titles(techniques, fetched_at="2026-06-02")
    assert stats2["added"] == 0
    data2 = json.loads(techniques.read_text(encoding="utf-8"))
    assert data2["_meta"]["notes"].count("merged additively") == 1


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
