"""Tests for the refresh-owasp command (network mocked)."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from apd_gauntlet.refresh_owasp import (
    DEFAULT_TIMEOUT_SECONDS,
    MAX_RESPONSE_BYTES,
    _fetch_json,
    _write_projected,
    fetch_owasp_api_top10,
    fetch_owasp_llm_top10,
    fetch_owasp_top10,
    refresh_owasp,
)


def test_owasp_timeout_constant_is_60s() -> None:
    assert DEFAULT_TIMEOUT_SECONDS == 60


def test_owasp_size_cap_is_200_mib() -> None:
    assert MAX_RESPONSE_BYTES == 200 * 1024 * 1024


def _make_fetch_json_side_effect(
    payloads: list[dict[str, Any]],
) -> Any:
    """Return a side_effect for _fetch_json that yields (raw_bytes, parsed) per call."""
    responses = [
        (json.dumps(p).encode("utf-8"), p) for p in payloads
    ]
    calls: list[int] = [0]

    def _side_effect(url: str) -> tuple[bytes, Any]:  # noqa: ARG001
        idx = calls[0]
        calls[0] += 1
        return responses[idx]

    return _side_effect


def test_refresh_owasp_writes_three_files(tmp_path: Path) -> None:
    """End-to-end: refresh_owasp writes all three projected JSON files with metadata."""
    fake_payloads = [
        {"categories": [
            {"id": "A03:2021", "title": "Injection"},
            {"id": "A05:2021", "title": "Security Misconfiguration"},
        ]},
        {"categories": [
            {"id": "API3:2023", "title": "Broken Object Property Level Authorization"},
        ]},
        {"categories": [{"id": "LLM01", "title": "Prompt Injection"}]},
    ]
    with patch(
        "apd_gauntlet.refresh_owasp._fetch_json",
        side_effect=_make_fetch_json_side_effect(fake_payloads),
    ):
        paths = refresh_owasp(output_dir=tmp_path)

    assert (tmp_path / "owasp_top10.json").exists()
    assert (tmp_path / "owasp_api_top10.json").exists()
    assert (tmp_path / "owasp_llm_top10.json").exists()
    assert paths["top10"] == tmp_path / "owasp_top10.json"
    assert paths["api_top10"] == tmp_path / "owasp_api_top10.json"
    assert paths["llm_top10"] == tmp_path / "owasp_llm_top10.json"

    for name in ("owasp_top10.json", "owasp_api_top10.json", "owasp_llm_top10.json"):
        data = json.loads((tmp_path / name).read_text())
        assert "source_sha256" in data
        assert "fetched_at" in data
        assert "source_url" in data
        assert "entries" in data

    top10 = json.loads((tmp_path / "owasp_top10.json").read_text())
    assert top10["entries"][0]["category_id"] == "A03:2021"


def test_refresh_owasp_preserves_edition_in_category_id(tmp_path: Path) -> None:
    """A finding mapped to A03:2021 stays A03:2021 — the year is part of the id."""
    fake_payloads = [
        {"categories": [{"id": "A03:2021", "title": "Injection"}]},
        {"categories": []},
        {"categories": []},
    ]
    with patch(
        "apd_gauntlet.refresh_owasp._fetch_json",
        side_effect=_make_fetch_json_side_effect(fake_payloads),
    ):
        refresh_owasp(output_dir=tmp_path)
    data = json.loads((tmp_path / "owasp_top10.json").read_text())
    assert data["entries"][0]["category_id"] == "A03:2021"


def test_fetch_owasp_top10_passes_timeout() -> None:
    """The URL fetch must use DEFAULT_TIMEOUT_SECONDS."""
    payload = json.dumps({"categories": [{"id": "A03:2021", "title": "Injection"}]}).encode()
    with patch("apd_gauntlet.refresh_owasp.urlopen") as mock:
        response = MagicMock()
        response.headers = {"Content-Length": str(len(payload))}
        response.read.return_value = payload
        mock.return_value.__enter__.return_value = response
        mock.return_value.__exit__.return_value = False
        fetch_owasp_top10()
        _, kwargs = mock.call_args
        assert kwargs.get("timeout") == DEFAULT_TIMEOUT_SECONDS


def test_fetch_json_rejects_oversize_response_content_length() -> None:
    """Content-Length pre-check rejects responses that advertise > 200 MiB."""
    with patch("apd_gauntlet.refresh_owasp.urlopen") as mock:
        response = MagicMock()
        response.headers = {"Content-Length": str(MAX_RESPONSE_BYTES + 1)}
        mock.return_value.__enter__.return_value = response
        mock.return_value.__exit__.return_value = False
        with pytest.raises(ValueError, match="exceeds maximum"):
            _fetch_json("https://example.invalid/owasp.json")


def test_fetch_json_rejects_oversize_response_post_read(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Defense in depth: even with missing/false Content-Length, oversize body raises.

    Monkeypatch MAX_RESPONSE_BYTES down so the test does not allocate 200 MiB.
    """
    monkeypatch.setattr("apd_gauntlet.refresh_owasp.MAX_RESPONSE_BYTES", 1024)
    fake_oversize_payload = b"x" * 2048
    with patch("apd_gauntlet.refresh_owasp.urlopen") as mock:
        response = MagicMock()
        response.headers = {}  # No Content-Length advertised.
        response.read.return_value = fake_oversize_payload
        mock.return_value.__enter__.return_value = response
        mock.return_value.__exit__.return_value = False
        with pytest.raises(ValueError, match="exceeds maximum"):
            _fetch_json("https://example.invalid/owasp.json")


def test_fetch_owasp_api_top10_projects_categories() -> None:
    """Projection extracts id+title pairs from the upstream categories[] shape."""
    payload = json.dumps(
        {
            "categories": [
                {"id": "API1:2023", "title": "Broken Object Level Authorization"},
                {"id": "API2:2023", "title": "Broken Authentication"},
            ]
        }
    ).encode()
    with patch("apd_gauntlet.refresh_owasp.urlopen") as mock:
        response = MagicMock()
        response.headers = {"Content-Length": str(len(payload))}
        response.read.return_value = payload
        mock.return_value.__enter__.return_value = response
        mock.return_value.__exit__.return_value = False
        entries = fetch_owasp_api_top10()
    assert entries == [
        {"category_id": "API1:2023", "name": "Broken Object Level Authorization"},
        {"category_id": "API2:2023", "name": "Broken Authentication"},
    ]


def test_fetch_owasp_llm_top10_projects_categories() -> None:
    payload = json.dumps(
        {"categories": [{"id": "LLM01", "title": "Prompt Injection"}]}
    ).encode()
    with patch("apd_gauntlet.refresh_owasp.urlopen") as mock:
        response = MagicMock()
        response.headers = {"Content-Length": str(len(payload))}
        response.read.return_value = payload
        mock.return_value.__enter__.return_value = response
        mock.return_value.__exit__.return_value = False
        entries = fetch_owasp_llm_top10()
    assert entries == [{"category_id": "LLM01", "name": "Prompt Injection"}]


def test_refresh_owasp_writes_three_files_to_explicit_dir(
    tmp_path: Path,
) -> None:
    """refresh_owasp with an explicit output_dir writes all files under that directory."""
    fake_payloads = [
        {"categories": [{"id": "A01:2021", "title": "Broken Access Control"}]},
        {"categories": []},
        {"categories": []},
    ]
    target_dir = tmp_path / "pkg" / "data"
    with patch(
        "apd_gauntlet.refresh_owasp._fetch_json",
        side_effect=_make_fetch_json_side_effect(fake_payloads),
    ):
        paths = refresh_owasp(output_dir=target_dir)
    assert paths["top10"].exists()
    assert paths["top10"].parent == target_dir


def test_write_projected_hashes_raw_bytes_when_provided(tmp_path: Path) -> None:
    """source_sha256 equals sha256(raw_bytes) when raw_bytes are passed in.

    This verifies the contract described in _fetch_json's docstring: callers can
    pass the exact upstream bytes to _write_projected and the stored hash will
    reflect those bytes, not a re-serialised projection.
    """
    raw = b'{"categories":[{"id":"A01:2021","title":"Broken Access Control"}]}'
    entries = [{"category_id": "A01:2021", "name": "Broken Access Control"}]
    out = tmp_path / "test.json"
    _write_projected(entries, "https://example.invalid/", out, raw_bytes=raw)
    data = json.loads(out.read_text())
    assert data["source_sha256"] == hashlib.sha256(raw).hexdigest()


def test_write_projected_falls_back_to_entries_hash_when_no_raw_bytes(
    tmp_path: Path,
) -> None:
    """source_sha256 is a stable hash of projected entries when raw_bytes is None (seed mode)."""
    entries = [{"category_id": "A01:2021", "name": "Broken Access Control"}]
    out = tmp_path / "test.json"
    _write_projected(entries, "seed_only", out, raw_bytes=None)
    data = json.loads(out.read_text())
    expected = hashlib.sha256(
        json.dumps(entries, sort_keys=True).encode("utf-8")
    ).hexdigest()
    assert data["source_sha256"] == expected
