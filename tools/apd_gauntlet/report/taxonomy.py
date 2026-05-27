"""Lookup tables for taxonomy hover tooltips.

Loads from package data shipped by refresh-* CLI verbs:
- data/cwe.json
- data/mitre-mitigations.json
- data/d3fend.json
- data/owasp_top10.json / owasp_api_top10.json / owasp_llm_top10.json

All loaders are defensively written: they inspect the actual shape of the
file before extracting data, and gracefully fall back (returning the id as
the title) when the shape is unexpected.
"""
from __future__ import annotations

import json
import pathlib
from functools import lru_cache

_PKG_DATA = pathlib.Path(__file__).resolve().parent.parent / "data"


@lru_cache(maxsize=1)
def cwe_titles() -> dict[str, str]:
    """Return {CWE-NNN: title} for all entries in cwe.json.

    Handles two shapes:
    - Flat dict: {"CWE-NNN": title_str, ...}
    - Flat dict: {"CWE-NNN": {"title": ..., "name": ..., ...}, ...}
    - Envelope: {"entries": [{cwe_id: "CWE-NNN", name: "...", ...}, ...], ...}
    """
    raw = json.loads((_PKG_DATA / "cwe.json").read_text())
    out: dict[str, str] = {}
    if isinstance(raw, dict):
        # Envelope shape: {"entries": [...], ...}
        entries = raw.get("entries")
        if isinstance(entries, list):
            for entry in entries:
                if not isinstance(entry, dict):
                    continue
                cid = entry.get("cwe_id", "")
                title = entry.get("name", entry.get("title", cid))
                if cid:
                    out[cid] = title
            return out
        # Flat dict shape: {"CWE-NNN": str | dict, ...}
        for cid, v in raw.items():
            if not cid or not cid.startswith("CWE-"):
                continue
            if isinstance(v, dict):
                out[cid] = v.get("title", v.get("name", cid))
            else:
                out[cid] = str(v)
    return out


@lru_cache(maxsize=1)
def attack_technique_titles() -> dict[str, str]:
    """Map ATT&CK technique id (T####[.###]) → name.

    mitre-mitigations.json carries mitigation rows but may also embed
    technique titles. We try every shape we know about; if none yield
    technique titles the returned dict is empty and callers fall back
    to using the id as the display title.

    Supported shapes:
    - {"techniques": {"T1234": "Name", ...}, ...}
    - {"techniques": {"T1234": {"name": "Name"}, ...}, ...}
    - {"mitigations": {"M1013": ["T1234", ...], ...}, ...} — no technique names; empty return
    """
    raw = json.loads((_PKG_DATA / "mitre-mitigations.json").read_text())
    out: dict[str, str] = {}
    if not isinstance(raw, dict):
        return out
    techniques = raw.get("techniques")
    if isinstance(techniques, dict):
        for tid, v in techniques.items():
            out[tid] = v if isinstance(v, str) else v.get("name", tid) if isinstance(v, dict) else tid
    # No "techniques" key (e.g. mitigations-only shape) → return empty dict;
    # callers use the id as the title.
    return out


@lru_cache(maxsize=1)
def d3fend_titles() -> dict[str, str]:
    """Map D3FEND technique id → name.

    Supported shapes:
    - {"techniques": {"D3-AA": "Name", ...}, ...}
    - {"techniques": {"D3-AA": {"name": "Name"}, ...}, ...}
    - {"entries": [{"d3fend_id": "D3-AA", "name": "...", ...}, ...], ...}
    """
    raw = json.loads((_PKG_DATA / "d3fend.json").read_text())
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
            name = entry.get("name", did)
            if did:
                out[did] = name
        return out
    # Try "techniques" dict shape.
    techniques = raw.get("techniques")
    if isinstance(techniques, dict):
        for did, v in techniques.items():
            out[did] = v if isinstance(v, str) else v.get("name", did) if isinstance(v, dict) else did
    return out
