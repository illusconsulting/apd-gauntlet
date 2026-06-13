"""Refresh the cached MITRE ATLAS technique-title catalog.

Fetches the MITRE ATLAS data bundle (``dist/ATLAS.yaml`` from
``mitre-atlas/atlas-data``), projects every technique to a ``{AML.T####: name}``
map, and writes ``tools/apd_gauntlet/data/atlas-techniques.json``. The catalog
backs the report's ATLAS tooltip titles and the ``atlas-coverage`` rollup name
resolution — exactly as ``mitre-attack-techniques.json`` backs ATT&CK.

Security hardening mirrors :mod:`apd_gauntlet.refresh_mitre` and
:mod:`apd_gauntlet.refresh_d3fend`:

* ``DEFAULT_TIMEOUT_SECONDS = 60`` — bounds time spent waiting for upstream.
* ``MAX_RESPONSE_BYTES = 200 MiB`` — bounds memory if upstream is compromised.
* Defense in depth: a ``Content-Length`` pre-check AND a post-read size check.

The ATLAS source is YAML (not JSON like the ATT&CK / CWE / OWASP sources), so
this module ``yaml.safe_load``s it (PyYAML is already a project dependency).
"""

from __future__ import annotations

import datetime
import hashlib
import json
import pathlib
from typing import Any

import yaml

from .kb_fetch import fetch_pinned

ATLAS_URL = "https://raw.githubusercontent.com/mitre-atlas/atlas-data/main/dist/ATLAS.yaml"

MAX_RESPONSE_BYTES = 200 * 1024 * 1024  # 200 MiB
DEFAULT_TIMEOUT_SECONDS = 60

_DATA = pathlib.Path(__file__).resolve().parent / "data"


def fetch_atlas(url: str = ATLAS_URL) -> bytes:
    """Fetch the MITRE ATLAS YAML bundle. Returns the raw bytes.

    Delegates the size-cap + timeout discipline to :func:`kb_fetch.fetch_pinned`.
    Raises ``ValueError`` if the response exceeds :data:`MAX_RESPONSE_BYTES`.
    """
    body, _meta = fetch_pinned(
        url, max_bytes=MAX_RESPONSE_BYTES, timeout=DEFAULT_TIMEOUT_SECONDS
    )
    return body


def project_atlas(bundle: dict[str, Any]) -> dict[str, str]:
    """Project a parsed ATLAS bundle to a ``{technique_id: name}`` map.

    Reads ``matrices[0].techniques`` (each ``{id: AML.T####[.###], name, ...}``).
    Sub-technique names (``AML.T####.###``) are prefixed with their parent's name
    (``Parent: Leaf``) for tooltip clarity, mirroring the ATT&CK catalog
    convention.
    """
    matrices = bundle.get("matrices") or []
    techniques = matrices[0].get("techniques", []) if matrices else []
    base: dict[str, str] = {}
    for t in techniques:
        if not isinstance(t, dict):
            continue
        tid = t.get("id")
        name = t.get("name")
        if isinstance(tid, str) and tid and isinstance(name, str) and name:
            base[tid] = name
    titles: dict[str, str] = {}
    for tid in sorted(base):
        name = base[tid]
        # ATLAS IDs are dotted (``AML.T0000``); a sub-technique (``AML.T0000.000``)
        # is one whose parent ID — everything before the LAST dot — is itself a
        # known base technique. ``rsplit`` (not ``split``) gets the right parent.
        parent_id = tid.rsplit(".", 1)[0]
        parent = base.get(parent_id)
        if parent is not None and parent_id != tid:
            titles[tid] = f"{parent}: {name}"
        else:
            titles[tid] = name
    return titles


def refresh_atlas(
    output_path: pathlib.Path | None = None,
    *,
    fetched_at: str | None = None,
) -> pathlib.Path:
    """Fetch + project ATLAS and write ``data/atlas-techniques.json``.

    Returns the written path. Shape: ``{_meta: {...}, techniques: {id: name}}``,
    mirroring ``mitre-attack-techniques.json`` so ``atlas_titles()`` is a direct
    analog of ``attack_technique_titles()``.
    """
    out = output_path or (_DATA / "atlas-techniques.json")
    raw = fetch_atlas()
    bundle = yaml.safe_load(raw.decode("utf-8"))
    titles = project_atlas(bundle)
    payload = {
        "_meta": {
            "source": ATLAS_URL,
            "source_sha256": hashlib.sha256(raw).hexdigest(),
            "version": str(bundle.get("version", "unknown")),
            "fetched_at": fetched_at or datetime.date.today().isoformat(),
            "notes": (
                "MITRE ATLAS techniques projected to {id: name}; sub-technique "
                "names are parent-prefixed (Parent: Leaf) for tooltip clarity."
            ),
        },
        "techniques": titles,
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return out
