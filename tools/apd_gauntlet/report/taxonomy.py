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
from functools import lru_cache
from typing import Any

_PKG_DATA = pathlib.Path(__file__).resolve().parent.parent / "data"
_DATA = _PKG_DATA


@lru_cache(maxsize=1)
def cwe_titles() -> dict[str, str]:
    """Return {CWE-NNN: title} for all entries in cwe.json.

    Handles two shapes:
    - Flat dict: {"CWE-NNN": title_str, ...}
    - Flat dict: {"CWE-NNN": {"title": ..., "name": ..., ...}, ...}
    - Envelope: {"entries": [{cwe_id: "CWE-NNN", name: "...", ...}, ...], ...}
    """
    raw = json.loads((_PKG_DATA / "cwe.json").read_text(encoding="utf-8"))
    out: dict[str, str] = {}
    if isinstance(raw, dict):
        # Envelope shape: {"entries": [...], ...}
        entries = raw.get("entries")
        if isinstance(entries, list):
            for entry in entries:
                if not isinstance(entry, dict):
                    continue
                cid = entry.get("cwe_id", "")
                title = entry.get("name", entry.get("title", cid)) or cid
                if cid:
                    out[cid] = title
            return out
        # Flat dict shape: {"CWE-NNN": str | dict, ...}
        for cid, v in raw.items():
            if not cid or not cid.startswith("CWE-"):
                continue
            if isinstance(v, dict):
                out[cid] = v.get("title", v.get("name", cid)) or cid
            else:
                out[cid] = str(v)
    return out


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
