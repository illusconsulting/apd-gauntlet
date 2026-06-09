"""Refresh the cached OWASP MASVS + MASWE reference catalogs.

Builds two JSONs bundled in ``tools/apd_gauntlet/data/``:

* ``masvs.json`` from ``OWASP_MASVS.yaml`` at a pinned ``master`` commit —
  the consolidated machine-readable YAML was committed to the repo AFTER the
  ``v2.1.0`` tag was cut, so it does NOT exist at that tag (it 404s). We pin an
  immutable master commit for reproducibility while keeping ``v2.1.0`` as the
  human display label (the content IS the v2.1.0 standard). Projected to
  ``{control_id: {title, category, category_title}}``.
* ``maswe.json`` from the ``OWASP/maswe`` repo at a pinned commit — each
  weakness is a markdown file with YAML front-matter (delimited by ``---``);
  we parse the front-matter only and ignore the prose body. A weakness's
  filing ``category`` is taken from its repo-path directory segment (e.g.
  ``weaknesses/MASVS-STORAGE/MASWE-0001.md`` -> ``MASVS-STORAGE``), falling
  back to the first ``mappings.masvs-v2`` control's prefix only when the path
  has no recognizable ``MASVS-*`` segment; ``covered_by`` is preserved for
  deprecated entries.

Security hardening mirrors :mod:`apd_gauntlet.refresh_atlas` /
:mod:`apd_gauntlet.refresh_d3fend`:

* ``DEFAULT_TIMEOUT_SECONDS = 60`` — bounds time spent waiting for upstream.
* ``MAX_RESPONSE_BYTES = 200 MiB`` — bounds memory if upstream is compromised.
* Defense in depth: a ``Content-Length`` pre-check AND a post-read size check.
"""

from __future__ import annotations

import datetime
import hashlib
import json
import pathlib
from typing import Any
from urllib.request import urlopen

import yaml

# ``v2.1.0`` is the human display label (the content IS the v2.1.0 standard),
# but OWASP_MASVS.yaml does not exist at that git tag — the consolidated
# machine-readable bundle was committed to ``master`` AFTER the tag was cut.
# Fetch from an IMMUTABLE master commit for reproducible refreshes.
MASVS_VERSION = "v2.1.0"
MASVS_COMMIT = "c0db792d48206186874b8b10818e117226eb1d68"
MASVS_URL = (
    "https://raw.githubusercontent.com/OWASP/masvs/"
    f"{MASVS_COMMIT}/OWASP_MASVS.yaml"
)
# MASWE is Beta — its IDs/URLs churn — so pin an IMMUTABLE 40-hex commit for
# reproducible refreshes (resolved from `git ls-remote https://github.com/OWASP/maswe.git HEAD`).
MASWE_COMMIT = "6799c10d662954a724d2a4b03b69f71c5debe3b1"
MASWE_REPO = "https://github.com/OWASP/maswe"

# The eight canonical MASVS v2 category prefixes; a MASWE filing directory must
# be one of these for the path-derived category to be trusted.
_MASVS_CATEGORIES = frozenset(
    {
        "MASVS-STORAGE",
        "MASVS-CRYPTO",
        "MASVS-AUTH",
        "MASVS-NETWORK",
        "MASVS-PLATFORM",
        "MASVS-CODE",
        "MASVS-RESILIENCE",
        "MASVS-PRIVACY",
    }
)

MAX_RESPONSE_BYTES = 200 * 1024 * 1024  # 200 MiB
DEFAULT_TIMEOUT_SECONDS = 60

_DATA = pathlib.Path(__file__).resolve().parent / "data"


def fetch_url(url: str) -> bytes:
    """Fetch ``url``. Returns the raw bytes.

    Raises ``ValueError`` if the response exceeds :data:`MAX_RESPONSE_BYTES`
    (checked twice: once via ``Content-Length``, once after reading).
    """
    with urlopen(url, timeout=DEFAULT_TIMEOUT_SECONDS) as response:
        content_length = response.headers.get("Content-Length")
        if content_length is not None:
            try:
                advertised = int(content_length)
            except (TypeError, ValueError):
                advertised = None
            if advertised is not None and advertised > MAX_RESPONSE_BYTES:
                raise ValueError(
                    f"MAS response Content-Length ({advertised}) "
                    f"exceeds maximum ({MAX_RESPONSE_BYTES})"
                )
        body: bytes = response.read(MAX_RESPONSE_BYTES + 1)
    if len(body) > MAX_RESPONSE_BYTES:
        raise ValueError(
            f"MAS response body exceeds maximum ({MAX_RESPONSE_BYTES} bytes); "
            "refusing to load. Verify the upstream feed before retrying."
        )
    return body


def project_masvs(yaml_bytes: bytes, *, fetched_at: str | None = None) -> dict[str, Any]:
    """Project the OWASP_MASVS.yaml bundle to the bundled masvs.json shape.

    Upstream shape: ``{groups: [{id, title, controls: [{id, statement}]}]}``.
    """
    doc = yaml.safe_load(yaml_bytes.decode("utf-8")) or {}
    controls: dict[str, dict[str, str]] = {}
    for group in doc.get("groups", []) or []:
        if not isinstance(group, dict):
            continue
        category = str(group.get("id") or "")
        category_title = str(group.get("title") or "")
        for control in group.get("controls", []) or []:
            if not isinstance(control, dict):
                continue
            cid = str(control.get("id") or "")
            statement = str(control.get("statement") or "")
            if not cid or not category:
                continue
            controls[cid] = {
                "title": statement,
                "category": category,
                "category_title": category_title,
            }
    return {
        "_meta": {
            "fetched_at": fetched_at or datetime.date.today().isoformat(),
            "source": MASVS_URL,
            "source_sha256": hashlib.sha256(yaml_bytes).hexdigest(),
            "version": MASVS_VERSION,
            "commit": MASVS_COMMIT,
            "count": len(controls),
        },
        "controls": dict(sorted(controls.items())),
    }


def _category_from_path(path: str) -> str:
    """Return the MASVS filing category from a repo path's directory segments.

    e.g. ``weaknesses/MASVS-STORAGE/MASWE-0001.md`` -> ``MASVS-STORAGE``.
    Returns ``""`` when no segment is one of the eight canonical categories.
    """
    for segment in path.split("/"):
        if segment in _MASVS_CATEGORIES:
            return segment
    return ""


def _parse_front_matter(md_bytes: bytes) -> dict[str, Any]:
    """Return the YAML front-matter of a MASWE markdown file (between --- lines)."""
    text = md_bytes.decode("utf-8")
    if not text.lstrip().startswith("---"):
        return {}
    stripped = text.lstrip()
    rest = stripped[3:]  # drop the leading ---
    end = rest.find("\n---")
    if end == -1:
        return {}
    front = rest[:end]
    parsed = yaml.safe_load(front)
    return parsed if isinstance(parsed, dict) else {}


def project_maswe(
    files: dict[str, bytes],
    *,
    commit: str,
    fetched_at: str | None = None,
) -> dict[str, Any]:
    """Project a ``{repo_path: markdown_bytes}`` map to the bundled maswe.json shape.

    The filing ``category`` is derived from the file's repo-PATH directory
    segment (e.g. ``weaknesses/MASVS-STORAGE/MASWE-0001.md`` -> ``MASVS-STORAGE``),
    which is what the canonical ``mas.owasp.org/MASWE/{category}/{id}/`` deep-link
    requires. It falls back to the first ``mappings.masvs-v2`` control's prefix
    ONLY when the path has no recognizable ``MASVS-*`` segment (a mapped-control
    category can differ from the filing directory and would 404). ``covered_by``
    is preserved for deprecated weaknesses.
    """
    weaknesses: dict[str, dict[str, Any]] = {}
    for path, md_bytes in files.items():
        front = _parse_front_matter(md_bytes)
        wid = str(front.get("id") or "")
        if not wid.startswith("MASWE-"):
            continue
        mappings = front.get("mappings") or {}
        masvs_v2 = [str(m) for m in (mappings.get("masvs-v2") or [])]
        cwe = [int(c) for c in (mappings.get("cwe") or []) if str(c).isdigit()]
        category = _category_from_path(path)
        if not category:
            category = masvs_v2[0].rsplit("-", 1)[0] if masvs_v2 else ""
        entry: dict[str, Any] = {
            "title": str(front.get("title") or ""),
            "category": category,
            "status": str(front.get("status") or "new"),
            "masvs_v2": masvs_v2,
            "cwe": cwe,
        }
        covered_by = front.get("covered_by")
        if covered_by:
            entry["covered_by"] = [str(c) for c in covered_by]
        weaknesses[wid] = entry
    return {
        "_meta": {
            "fetched_at": fetched_at or datetime.date.today().isoformat(),
            "source": MASWE_REPO,
            "commit": commit,
            "count": len(weaknesses),
        },
        "weaknesses": dict(sorted(weaknesses.items())),
    }


def refresh_masvs(
    output_path: pathlib.Path | None = None,
    *,
    fetched_at: str | None = None,
) -> pathlib.Path:
    """Fetch + project MASVS and write ``data/masvs.json``. Returns the path."""
    out = output_path or (_DATA / "masvs.json")
    raw = fetch_url(MASVS_URL)
    payload = project_masvs(raw, fetched_at=fetched_at)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return out


def refresh_maswe(
    output_path: pathlib.Path | None = None,
    *,
    commit: str = MASWE_COMMIT,
    fetched_at: str | None = None,
) -> pathlib.Path:
    """Fetch the MASWE weakness markdown set @ ``commit`` and write ``data/maswe.json``.

    Walks the repo's ``weaknesses/`` tree via the GitHub trees API at the pinned
    commit, fetches each ``MASWE-*.md`` raw blob, and projects the front-matter.
    """
    out = output_path or (_DATA / "maswe.json")
    tree_url = (
        f"https://api.github.com/repos/OWASP/maswe/git/trees/{commit}?recursive=1"
    )
    tree = json.loads(fetch_url(tree_url).decode("utf-8"))
    files: dict[str, bytes] = {}
    for node in tree.get("tree", []) or []:
        path = node.get("path", "")
        if path.endswith(".md") and "MASWE-" in path:
            raw_url = (
                f"https://raw.githubusercontent.com/OWASP/maswe/{commit}/{path}"
            )
            files[path] = fetch_url(raw_url)
    payload = project_maswe(files, commit=commit, fetched_at=fetched_at)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return out


if __name__ == "__main__":
    print(f"Wrote {refresh_masvs()}")
    print(f"Wrote {refresh_maswe()}")
