"""Lookup tables for taxonomy hover tooltips.

Loads from package data shipped by refresh-* CLI verbs:
- data/cwe.json
- data/mitre-attack-techniques.json
- data/mitre-mitigations.json
- data/d3fend.json
- data/nist-controls.json
- data/owasp_top10.json / owasp_api_top10.json / owasp_llm_top10.json

All loaders are defensively written: they inspect the actual shape of the
file before extracting data, and gracefully fall back (returning the id as
the title) when the shape is unexpected.
"""
from __future__ import annotations

import json
import pathlib
from collections.abc import Callable
from functools import lru_cache
from typing import Any

_PKG_DATA = pathlib.Path(__file__).resolve().parent.parent / "data"
_DATA = _PKG_DATA


_CACHED_LOADERS: tuple[Callable[[], dict[str, Any]], ...] = ()


def _register_cached(fn: Callable[[], dict[str, Any]]) -> Callable[[], dict[str, Any]]:
    """Register a @lru_cache'd loader so invalidate_all() can clear it.

    Decorator pattern: apply BEFORE @lru_cache so we register the cached form.
    """
    global _CACHED_LOADERS
    _CACHED_LOADERS = (*_CACHED_LOADERS, fn)
    return fn


@_register_cached
@lru_cache(maxsize=1)
def _cwe_catalog() -> dict[str, dict[str, str]]:
    """Single CWE loader: {CWE-NNN: {"title": ..., "abstraction": ...}}.

    The one place cwe.json is parsed; ``cwe_titles`` and ``cwe_abstractions``
    are thin projections of this so the title map and the abstraction map can
    never drift. ``abstraction`` is "" when the source carries none.

    Handles two shapes:
    - Flat dict: {"CWE-NNN": title_str, ...}
    - Flat dict: {"CWE-NNN": {"title": ..., "name": ..., "abstraction": ...}, ...}
    - Envelope: {"entries": [{cwe_id: "CWE-NNN", name: ..., abstraction: ...}], ...}
    """
    raw = json.loads((_PKG_DATA / "cwe.json").read_text(encoding="utf-8"))
    out: dict[str, dict[str, str]] = {}
    if isinstance(raw, dict):
        # Envelope shape: {"entries": [...], ...}
        entries = raw.get("entries")
        if isinstance(entries, list):
            for entry in entries:
                if not isinstance(entry, dict):
                    continue
                cid = entry.get("cwe_id", "")
                if not cid:
                    continue
                title = entry.get("name", entry.get("title", cid)) or cid
                out[cid] = {
                    "title": title,
                    "abstraction": str(entry.get("abstraction") or ""),
                }
            return out
        # Flat dict shape: {"CWE-NNN": str | dict, ...}
        for cid, v in raw.items():
            if not cid or not cid.startswith("CWE-"):
                continue
            if isinstance(v, dict):
                out[cid] = {
                    "title": v.get("title", v.get("name", cid)) or cid,
                    "abstraction": str(v.get("abstraction") or ""),
                }
            else:
                out[cid] = {"title": str(v), "abstraction": ""}
    return out


@_register_cached
@lru_cache(maxsize=1)
def cwe_titles() -> dict[str, str]:
    """Return {CWE-NNN: title} for all entries in cwe.json (projection of the
    single :func:`_cwe_catalog` loader). Kept lru-cached/registered so callers
    relying on ``cwe_titles.cache_clear()`` / ``invalidate_all`` still work."""
    return {cid: e["title"] for cid, e in _cwe_catalog().items()}


@_register_cached
@lru_cache(maxsize=1)
def cwe_abstractions() -> dict[str, str]:
    """Return {CWE-NNN: abstraction} for all entries in cwe.json.

    Abstraction is one of category/pillar/class/base/variant/compound (or "" when
    the source carries none). Projection of the single :func:`_cwe_catalog`
    loader so it cannot drift from :func:`cwe_titles`. Consumed by the G6
    CWE-resolves guardrail in ``linters.check_cwe_resolves``.
    """
    return {cid: e["abstraction"] for cid, e in _cwe_catalog().items()}


@_register_cached
@lru_cache(maxsize=1)
def attack_technique_titles() -> dict[str, str]:
    """Map ATT&CK technique id (T####[.###]) → name.

    Reads the bundled MITRE ATT&CK techniques catalog produced by
    ``apd-gauntlet refresh-mitre``. Returns an empty dict if the file is
    missing or unparseable so callers fall back to using the id as the
    display title.

    Supported shapes:
    - {"techniques": {"T1234": "Name", ...}, ...}
    - {"techniques": {"T1234": {"name": "Name"}, ...}, ...}
    """
    path = _DATA / "mitre-attack-techniques.json"
    try:
        with path.open(encoding="utf-8") as fh:
            raw = json.load(fh)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}
    out: dict[str, str] = {}
    if not isinstance(raw, dict):
        return out
    techniques = raw.get("techniques")
    if isinstance(techniques, dict):
        for tid, v in techniques.items():
            out[tid] = (
                v if isinstance(v, str)
                else (v.get("name") or tid) if isinstance(v, dict)
                else tid
            )
    return out


@_register_cached
@lru_cache(maxsize=1)
def nist_control_titles() -> dict[str, str]:
    """Return {control_id: title} from the bundled NIST 800-53r5 catalog."""
    path = _DATA / "nist-controls.json"
    try:
        with path.open(encoding="utf-8") as fh:
            doc = json.load(fh)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}
    return doc.get("controls") or {}


@_register_cached
@lru_cache(maxsize=1)
def d3fend_titles() -> dict[str, str]:
    """Map D3FEND technique id → name.

    Supported shapes:
    - {"techniques": {"D3-AA": "Name", ...}, ...}
    - {"techniques": {"D3-AA": {"name": "Name"}, ...}, ...}
    - {"entries": [{"d3fend_id": "D3-AA", "name": "...", ...}, ...], ...}
    """
    raw = json.loads((_PKG_DATA / "d3fend.json").read_text(encoding="utf-8"))
    out: dict[str, str] = {}
    if not isinstance(raw, dict):
        return out
    # Try "entries" list shape first (actual shape as of refresh).
    entries = raw.get("entries")
    if isinstance(entries, list):
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            did = entry.get("d3fend_id", "")
            name = entry.get("name") or did
            if did:
                out[did] = name
        return out
    # Try "techniques" dict shape.
    techniques = raw.get("techniques")
    if isinstance(techniques, dict):
        for did, v in techniques.items():
            out[did] = (
                v if isinstance(v, str)
                else (v.get("name") or did) if isinstance(v, dict)
                else did
            )
    return out


@_register_cached
@lru_cache(maxsize=1)
def atlas_titles() -> dict[str, str]:
    """Map MITRE ATLAS technique id (AML.T####[.###]) → name.

    Reads the bundled ATLAS catalog produced by ``apd-gauntlet refresh-atlas``.
    Returns an empty dict if the file is missing or unparseable so callers fall
    back to using the id as the display title. Same ``techniques`` dict shape as
    :func:`attack_technique_titles`.

    Supported shapes:
    - {"techniques": {"AML.T0051": "Name", ...}, ...}
    - {"techniques": {"AML.T0051": {"name": "Name"}, ...}, ...}
    """
    path = _DATA / "atlas-techniques.json"
    try:
        with path.open(encoding="utf-8") as fh:
            raw = json.load(fh)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}
    out: dict[str, str] = {}
    if not isinstance(raw, dict):
        return out
    techniques = raw.get("techniques")
    if isinstance(techniques, dict):
        for tid, v in techniques.items():
            out[tid] = (
                v if isinstance(v, str)
                else (v.get("name") or tid) if isinstance(v, dict)
                else tid
            )
    return out


def reference_db_versions() -> dict[str, dict[str, Any]]:
    """Return {family: {fetched_at, count, source}} for each shipped reference DB.

    Used by transform.meta_block to surface freshness state to the report
    so the UI can warn when a catalog is stale (>180 days) or empty (load
    failure).
    """
    out: dict[str, dict[str, Any]] = {}
    for family, fn, path_name in (
        ("nist",   nist_control_titles,     "nist-controls.json"),
        ("attack", attack_technique_titles, "mitre-attack-techniques.json"),
        ("cwe",    cwe_titles,              "cwe.json"),
        ("d3fend", d3fend_titles,           "d3fend.json"),
        ("atlas",  atlas_titles,            "atlas-techniques.json"),
    ):
        path = _DATA / path_name
        meta: dict[str, Any] = {}
        if path.is_file():
            try:
                with path.open(encoding="utf-8") as fh:
                    doc = json.load(fh)
                meta = doc.get("_meta") or {}
            except (json.JSONDecodeError, OSError):
                pass
        out[family] = {
            "fetched_at": meta.get("fetched_at"),
            "source":     meta.get("source"),
            "count":      len(fn()),
        }
    return out


def invalidate_all() -> None:
    """Invalidate every reference-data LRU cache.

    Call when the underlying data files have changed and the process must
    pick up the refreshed values without restarting (e.g. a SaaS variant
    receiving a refresh-mitre webhook, or a hot-reload workflow).
    """
    for fn in _CACHED_LOADERS:
        fn.cache_clear()  # type: ignore[attr-defined]


_LAST_SEEN_MTIMES: dict[pathlib.Path, float] = {}


def invalidate_if_modified(
    catalog_dir: pathlib.Path | None = None,
) -> list[str]:
    """Clear caches whose source JSON file mtime has changed since last call.

    Returns the list of catalog filenames whose caches were cleared. On the
    first call this populates the mtime registry but does NOT clear anything
    (idempotent warm-up).
    """
    target = catalog_dir or _DATA
    cleared: list[str] = []
    # Mapping of catalog filename -> loader(s) to invalidate. cwe.json backs three
    # caches (_cwe_catalog parse + the cwe_titles / cwe_abstractions projections);
    # clear all three so a projection cannot survive a refreshed source.
    catalog_to_loaders: dict[str, tuple[Callable[[], dict[str, Any]], ...]] = {
        "nist-controls.json":            (nist_control_titles,),
        "mitre-attack-techniques.json":  (attack_technique_titles,),
        "cwe.json":                      (_cwe_catalog, cwe_titles, cwe_abstractions),
        "d3fend.json":                   (d3fend_titles,),
        "atlas-techniques.json":         (atlas_titles,),
    }
    for filename, loaders in catalog_to_loaders.items():
        path = target / filename
        if not path.is_file():
            continue
        try:
            current = path.stat().st_mtime
        except OSError:
            continue
        previous = _LAST_SEEN_MTIMES.get(path)
        if previous is None:
            _LAST_SEEN_MTIMES[path] = current
            continue  # warm-up
        if current != previous:
            for loader in loaders:
                loader.cache_clear()  # type: ignore[attr-defined]
            _LAST_SEEN_MTIMES[path] = current
            cleared.append(filename)
    return cleared
