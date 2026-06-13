"""Refresh the cached OWASP Top 10 reference data for the apd-gauntlet.

This module fetches three published OWASP Top 10 lists — web, API, and
LLM-application — projects each to a compact JSON shape, and writes them to
``tools/apd_gauntlet/data/owasp_top10.json``, ``owasp_api_top10.json``, and
``owasp_llm_top10.json`` respectively. Each projected file carries
``source_sha256``, ``fetched_at``, and ``source_url`` metadata so downstream
consumers can audit provenance.

**Edition versioning is preserved.** A finding mapped to ``A03:2021`` keeps
that identifier even after a new edition ships — the year is part of the id.
The LLM Top 10 follows the editionless ``LLM01``..``LLM10`` convention used by
the OWASP project.

Security hardening mirrors :mod:`apd_gauntlet.refresh_cwe`:

* ``DEFAULT_TIMEOUT_SECONDS = 60`` — bounds time spent waiting for upstream.
* ``MAX_RESPONSE_BYTES = 200 MiB`` — bounds memory if upstream is compromised.
* Defense in depth: a ``Content-Length`` pre-check AND a post-read size check
  (the header may be missing, or it may lie).

The constants ``OWASP_*_URL`` document the upstream sources we *would* fetch
when the OWASP project publishes machine-readable category lists at stable
URLs. The OWASP project has historically reorganised its repos, so operators
running ``python -m apd_gauntlet.refresh_owasp`` should expect to verify the
URLs are still live and update them when necessary. The data files shipped
with the package may be hand-seeded; in that case the file's ``source_url``
metadata records ``"seed_only"`` so consumers can tell.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .kb_fetch import fetch_pinned

# Hard cap on the fetched payload size to bound memory use if the upstream is
# compromised or misbehaves. OWASP category lists are kilobytes; 200 MiB leaves
# plenty of headroom for future growth while still being a useful guardrail.
MAX_RESPONSE_BYTES = 200 * 1024 * 1024  # 200 MiB
DEFAULT_TIMEOUT_SECONDS = 60

# Engineer: verify these URLs at execution time before running a live refresh.
# The OWASP project has historically reorganised its repos and renamed files;
# the live refresh path expects each URL to return a JSON document with a
# top-level ``categories`` array of ``{id, title}`` objects. If a refresh
# returns 404 or a wildly different shape, hand-seed the data file instead and
# record ``"seed_only"`` in its ``source_url``.
OWASP_TOP10_URL = (
    "https://raw.githubusercontent.com/OWASP/Top10/master/2021/docs/categories.json"
)
OWASP_API_TOP10_URL = (
    "https://raw.githubusercontent.com/OWASP/API-Security/master/editions/2023/en/categories.json"
)
OWASP_LLM_TOP10_URL = (
    "https://raw.githubusercontent.com/OWASP/"
    "www-project-top-10-for-large-language-model-applications/main/categories.json"
)


def _fetch_json(url: str) -> tuple[bytes, Any]:
    """Fetch a JSON document with the standard timeout + size cap.

    Returns ``(raw_body_bytes, parsed_json)`` so callers can compute a
    ``source_sha256`` over the *exact* bytes received, before parsing. Delegates
    the size-cap + timeout discipline to :func:`kb_fetch.fetch_pinned`.
    """
    body, _meta = fetch_pinned(
        url, max_bytes=MAX_RESPONSE_BYTES, timeout=DEFAULT_TIMEOUT_SECONDS
    )
    return body, json.loads(body)


def _project_categories(payload: Any) -> list[dict[str, Any]]:
    """Project a ``{categories: [{id, title}, ...]}`` payload into our shape.

    Defensive: missing ``categories`` returns an empty list rather than raising,
    and any entry lacking ``id`` is skipped. This lets the script tolerate
    minor upstream-format drift without blowing up.
    """
    categories = payload.get("categories", []) if isinstance(payload, dict) else []
    entries: list[dict[str, Any]] = []
    for raw in categories:
        if not isinstance(raw, dict):
            continue
        category_id = raw.get("id")
        if not category_id:
            continue
        entries.append(
            {
                "category_id": str(category_id),
                "name": str(raw.get("title") or raw.get("name") or ""),
            }
        )
    return entries


def fetch_owasp_top10() -> list[dict[str, Any]]:
    """Fetch OWASP Top 10 (web). Returns a list of ``{category_id, name}``."""
    _, payload = _fetch_json(OWASP_TOP10_URL)
    return _project_categories(payload)


def fetch_owasp_api_top10() -> list[dict[str, Any]]:
    """Fetch OWASP API Top 10. Returns a list of ``{category_id, name}``."""
    _, payload = _fetch_json(OWASP_API_TOP10_URL)
    return _project_categories(payload)


def fetch_owasp_llm_top10() -> list[dict[str, Any]]:
    """Fetch OWASP LLM Top 10. Returns a list of ``{category_id, name}``."""
    _, payload = _fetch_json(OWASP_LLM_TOP10_URL)
    return _project_categories(payload)


def _write_projected(
    entries: list[dict[str, Any]],
    url: str,
    output_path: Path,
    raw_bytes: bytes | None = None,
) -> None:
    """Serialize entries with provenance metadata and write to ``output_path``.

    When ``raw_bytes`` is provided (live fetch), ``source_sha256`` is computed
    over the exact upstream bytes received — matching the promise in
    :func:`_fetch_json`'s docstring.  When ``raw_bytes`` is ``None`` (seed mode
    or other cases where no upstream response is available), the hash falls back
    to a canonical ``sort_keys`` JSON dump of the projected entries so the field
    is always populated.
    """
    if raw_bytes is not None:
        sha = hashlib.sha256(raw_bytes).hexdigest()
    else:
        # Seed mode: no upstream response available; hash the projected entries
        # so the field is stable and deterministic.
        sha = hashlib.sha256(
            json.dumps(entries, sort_keys=True).encode("utf-8")
        ).hexdigest()
    projected = {
        "source_url": url,
        "source_sha256": sha,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "entries": entries,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(projected, indent=2, sort_keys=True), encoding="utf-8")


def refresh_owasp(output_dir: Path | None = None) -> dict[str, Path]:
    """Fetch all three OWASP lists; write to ``data/owasp_*.json``.

    Returns a mapping ``{"top10": Path, "api_top10": Path, "llm_top10": Path}``
    of the written file paths.

    Raw upstream bytes are passed directly to :func:`_write_projected` so that
    ``source_sha256`` is computed over the exact bytes received from the server,
    fulfilling the contract described in :func:`_fetch_json`'s docstring.
    """
    if output_dir is None:
        output_dir = Path(__file__).parent / "data"
    paths = {
        "top10": output_dir / "owasp_top10.json",
        "api_top10": output_dir / "owasp_api_top10.json",
        "llm_top10": output_dir / "owasp_llm_top10.json",
    }
    top10_body, top10_payload = _fetch_json(OWASP_TOP10_URL)
    _write_projected(
        _project_categories(top10_payload),
        OWASP_TOP10_URL,
        paths["top10"],
        raw_bytes=top10_body,
    )
    api_body, api_payload = _fetch_json(OWASP_API_TOP10_URL)
    _write_projected(
        _project_categories(api_payload),
        OWASP_API_TOP10_URL,
        paths["api_top10"],
        raw_bytes=api_body,
    )
    llm_body, llm_payload = _fetch_json(OWASP_LLM_TOP10_URL)
    _write_projected(
        _project_categories(llm_payload),
        OWASP_LLM_TOP10_URL,
        paths["llm_top10"],
        raw_bytes=llm_body,
    )
    return paths


if __name__ == "__main__":
    for name, path in refresh_owasp().items():
        print(f"Wrote {name}: {path}")
