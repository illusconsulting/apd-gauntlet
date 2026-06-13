"""Unit tests for the shared version-pinned KB fetch helper.

fetch_pinned is the ONE place the Content-Length pre-check + post-read size cap
lives, factored out of the six refresh_*.py fetchers. Network is always stubbed;
no test touches a real socket.
"""
from __future__ import annotations

import hashlib
from unittest.mock import MagicMock, patch

import pytest
from apd_gauntlet.kb_fetch import (
    DEFAULT_MAX_BYTES,
    DEFAULT_TIMEOUT_SECONDS,
    fetch_pinned,
)

_BODY = b'{"hello": "world"}'


def _stub_response(headers: dict[str, str], body: bytes) -> MagicMock:
    response = MagicMock()
    response.headers = headers
    response.read.return_value = body
    return response


def test_default_constants() -> None:
    assert DEFAULT_TIMEOUT_SECONDS == 60
    assert DEFAULT_MAX_BYTES == 200 * 1024 * 1024


def test_returns_body_and_provenance_meta() -> None:
    with patch("apd_gauntlet.kb_fetch.urlopen") as mock:
        mock.return_value.__enter__.return_value = _stub_response(
            {"Content-Length": str(len(_BODY))}, _BODY
        )
        mock.return_value.__exit__.return_value = False
        body, meta = fetch_pinned(
            "https://example.test/x.json",
            max_bytes=DEFAULT_MAX_BYTES,
            timeout=DEFAULT_TIMEOUT_SECONDS,
        )
    assert body == _BODY
    assert meta["source"] == "https://example.test/x.json"
    assert meta["source_sha256"] == hashlib.sha256(_BODY).hexdigest()
    assert "fetched_at" in meta


def test_passes_timeout_to_urlopen() -> None:
    with patch("apd_gauntlet.kb_fetch.urlopen") as mock:
        mock.return_value.__enter__.return_value = _stub_response(
            {"Content-Length": str(len(_BODY))}, _BODY
        )
        mock.return_value.__exit__.return_value = False
        fetch_pinned("https://example.test/x", max_bytes=DEFAULT_MAX_BYTES, timeout=42)
        _, kwargs = mock.call_args
        assert kwargs.get("timeout") == 42


def test_rejects_oversize_content_length() -> None:
    with patch("apd_gauntlet.kb_fetch.urlopen") as mock:
        mock.return_value.__enter__.return_value = _stub_response(
            {"Content-Length": "999"}, _BODY
        )
        mock.return_value.__exit__.return_value = False
        with pytest.raises(ValueError, match="exceeds maximum"):
            fetch_pinned("https://example.test/x", max_bytes=10, timeout=60)


def test_rejects_oversize_post_read_when_header_missing() -> None:
    big = b"x" * 2048
    with patch("apd_gauntlet.kb_fetch.urlopen") as mock:
        mock.return_value.__enter__.return_value = _stub_response({}, big)
        mock.return_value.__exit__.return_value = False
        with pytest.raises(ValueError, match="exceeds maximum"):
            fetch_pinned("https://example.test/x", max_bytes=1024, timeout=60)


def test_rejects_oversize_post_read_when_header_lies() -> None:
    """Content-Length under-reports (passes the Stage-1 pre-check), but the body
    is oversize — the Stage-2 post-read length check must still reject it. This is
    the scenario that proves Stage 2 is independent of a (possibly lying) header."""
    big = b"x" * 2048
    with patch("apd_gauntlet.kb_fetch.urlopen") as mock:
        mock.return_value.__enter__.return_value = _stub_response(
            {"Content-Length": "5"}, big
        )
        mock.return_value.__exit__.return_value = False
        with pytest.raises(ValueError, match="exceeds maximum"):
            fetch_pinned("https://example.test/x", max_bytes=1024, timeout=60)


def test_tolerates_unparseable_content_length() -> None:
    with patch("apd_gauntlet.kb_fetch.urlopen") as mock:
        mock.return_value.__enter__.return_value = _stub_response(
            {"Content-Length": "not-a-number"}, _BODY
        )
        mock.return_value.__exit__.return_value = False
        body, _ = fetch_pinned(
            "https://example.test/x", max_bytes=DEFAULT_MAX_BYTES, timeout=60
        )
    assert body == _BODY


def test_sha256_is_stable_across_calls() -> None:
    digests = set()
    for _ in range(3):
        with patch("apd_gauntlet.kb_fetch.urlopen") as mock:
            mock.return_value.__enter__.return_value = _stub_response(
                {"Content-Length": str(len(_BODY))}, _BODY
            )
            mock.return_value.__exit__.return_value = False
            _, meta = fetch_pinned(
                "https://example.test/x", max_bytes=DEFAULT_MAX_BYTES, timeout=60
            )
            digests.add(meta["source_sha256"])
    assert len(digests) == 1
