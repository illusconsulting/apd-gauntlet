"""Shared version-pinned knowledge-base fetch helper.

``fetch_pinned`` is the single implementation of the network-fetch + size-cap
discipline that the six ``refresh_*.py`` fetchers previously copy-pasted. It uses
only the standard library (``urllib``) — no third-party HTTP client — and returns
the raw bytes plus a provenance ``meta`` block so callers can record
``source``/``source_sha256``/``fetched_at`` without re-hashing.

Reproducibility: callers pin to ``meta["source_sha256"]`` and never fetch at
gauntlet runtime.
"""
from __future__ import annotations

import datetime
import hashlib
from typing import Any
from urllib.request import urlopen

DEFAULT_TIMEOUT_SECONDS = 60
DEFAULT_MAX_BYTES = 200 * 1024 * 1024  # 200 MiB


def fetch_pinned(
    url: str,
    *,
    max_bytes: int = DEFAULT_MAX_BYTES,
    timeout: int = DEFAULT_TIMEOUT_SECONDS,
) -> tuple[bytes, dict[str, Any]]:
    """Fetch ``url`` with a bounded response size. Returns ``(body, meta)``.

    ``meta`` is ``{source, source_sha256, fetched_at}`` computed over the exact
    bytes received (hash before any parsing). Raises ``ValueError`` if the
    response exceeds ``max_bytes`` — checked twice: once via ``Content-Length``
    (the header may be missing or may lie), once after reading.
    """
    with urlopen(url, timeout=timeout) as response:
        content_length = response.headers.get("Content-Length")
        if content_length is not None:
            try:
                advertised: int | None = int(content_length)
            except (TypeError, ValueError):
                advertised = None
            if advertised is not None and advertised > max_bytes:
                raise ValueError(
                    f"Response from {url} Content-Length ({advertised}) "
                    f"exceeds maximum ({max_bytes})"
                )
        body: bytes = response.read(max_bytes + 1)
    if len(body) > max_bytes:
        raise ValueError(
            f"Response from {url} body exceeds maximum ({max_bytes} bytes); "
            "refusing to load. Verify the upstream feed before retrying."
        )
    meta = {
        "source": url,
        "source_sha256": hashlib.sha256(body).hexdigest(),
        "fetched_at": datetime.date.today().isoformat(),
    }
    return body, meta
