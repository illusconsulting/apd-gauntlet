"""Deterministic coverage helpers shared by report.transform and synthesis.rollup.

Extracted from report/transform.py so both modules import one source of truth
without a report→synthesis import cycle (this module imports nothing from
report). The 4-shape tolerance in transform.py is unaffected — only these leaf
helpers were factored out.
"""
from __future__ import annotations

import re
from typing import Any

# Canonical APD goal order (used by the 9xN matrix and goal iteration).
GOAL_SHORT: dict[str, str] = {
    "confidentiality": "conf",
    "integrity":       "intg",
    "availability":    "avail",
    "distributed":     "dist",
    "resilient":       "resil",
    "ephemeral":       "ephem",
    "authenticity":    "auth",
    "non_repudiation": "nonrep",
    "immutability":    "immut",
}

_NIST_ID_CANONICAL = re.compile(r"[A-Z]{2,3}-\d+(\([\dA-Z]+\))?")


def normalize_nist_id(raw: str | None) -> str | None:
    """Normalise a NIST 800-53r5 control id to canonical form (e.g. 'ac-3' -> 'AC-3').

    Returns None for input that cannot be normalised so callers drop the entry.
    """
    if not isinstance(raw, str):
        return None
    norm = raw.strip().upper()
    if not norm:
        return None
    if not _NIST_ID_CANONICAL.fullmatch(norm):
        return None
    return norm


def normalize_nist_ids(ids: list[str]) -> list[str]:
    """Apply normalize_nist_id over a list, dropping invalid entries; preserve order."""
    return [n for n in (normalize_nist_id(x) for x in ids) if n]


def nist_family_of(control_id: str) -> str:
    """Return the NIST family prefix of a control id (e.g. 'AC-2(2)' -> 'AC')."""
    return control_id.split("-", 1)[0] if "-" in control_id else control_id


def posture(*, has_findings: bool, has_caps: bool) -> str:
    """Return the canonical coverage posture enum used in the rollup YAMLs."""
    if has_findings and has_caps:
        return "gapped_and_covered"
    if has_findings:
        return "gapped"
    if has_caps:
        return "covered"
    return "silent"


def extract_ids_from_mapping(raw: Any, *fallback_keys: str) -> list[str]:
    """Extract string IDs from a control-mapping field (list of str or list of dicts).

    Tries 'id' then each fallback key. Items with no usable id are skipped.
    Deliberately the silent variant (no warnings aggregator) — rollup wants
    only the clean ids; the report keeps the warnings-aware copy in transform.py.
    """
    if not raw:
        return []
    ids: list[str] = []
    for item in raw:
        if isinstance(item, str):
            ids.append(item)
            continue
        if not isinstance(item, dict):
            continue
        found = item.get("id")
        if not found:
            for key in fallback_keys:
                found = item.get(key)
                if found:
                    break
        if isinstance(found, str) and found:
            ids.append(found)
    return ids


def build_cap_controls_index(capabilities: list[dict[str, Any]]) -> dict[str, set[str]]:
    """Return {control_id: {cap_id, ...}} for capabilities with NIST mappings (normalised)."""
    index: dict[str, set[str]] = {}
    for cap in capabilities:
        cap_id = cap.get("id", "")
        cm = cap.get("control_mappings") or {}
        for ctrl in normalize_nist_ids(extract_ids_from_mapping(cm.get("nist_800_53r5"))):
            index.setdefault(ctrl, set()).add(cap_id)
    return index


def build_cap_attack_index(capabilities: list[dict[str, Any]]) -> dict[str, set[str]]:
    """Return {attack_id: {cap_id, ...}} for capabilities with MITRE ATT&CK mappings."""
    index: dict[str, set[str]] = {}
    for cap in capabilities:
        cap_id = cap.get("id", "")
        cm = cap.get("control_mappings") or {}
        for tech in extract_ids_from_mapping(cm.get("mitre_attack"), "technique"):
            index.setdefault(tech, set()).add(cap_id)
    return index
