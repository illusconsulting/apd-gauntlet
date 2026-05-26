"""Parser for OWASP Threat Dragon JSON exports.

Threat Dragon (https://owasp.org/www-project-threat-dragon/) is one of the
most widely-used OSS threat-modeling tools. Its export format places
threats on diagram cells; each threat carries a STRIDE category string
that we map to a single-letter STRIDE code.
"""

from __future__ import annotations

import hashlib
from typing import Any

from .mappings import stride_letter_to_apd_goals

# Maps Threat Dragon's threat.type strings to single-letter STRIDE codes.
# Lookup is case-insensitive (see _stride_letter_from_threat_type).
_THREAT_TYPE_TO_STRIDE: dict[str, str] = {
    "spoofing":               "S",
    "tampering":              "T",
    "repudiation":            "R",
    "information disclosure": "I",
    "denial of service":      "D",
    "elevation of privilege": "E",
}


def _stride_letter_from_threat_type(threat_type: str) -> str | None:
    """Map a Threat Dragon threat-type string to a single-letter STRIDE code.

    Returns None when the type string is not a recognized STRIDE category.
    Case-insensitive matching.
    """
    if not threat_type:
        return None
    return _THREAT_TYPE_TO_STRIDE.get(threat_type.strip().lower())


def _stable_entry_id(*, asset: str, threat: str, locator: str) -> str:
    """Deterministic 8-hex-char ID, stable across runs for the same input."""
    raw = f"{asset}|{threat}|{locator}".encode()
    return f"tm-{hashlib.sha256(raw).hexdigest()[:8]}"


def _cell_asset_name(cell: dict[str, Any]) -> str:
    """Asset name preference: cell.data.name > cell.attrs.label.text > '(unnamed cell)'."""
    data = cell.get("data") or {}
    if isinstance(data, dict) and data.get("name"):
        return str(data["name"])
    attrs = cell.get("attrs") or {}
    label = attrs.get("label") if isinstance(attrs, dict) else None
    if isinstance(label, dict) and label.get("text"):
        return str(label["text"])
    return "(unnamed cell)"


def parse_threat_dragon(doc: dict[str, Any]) -> list[dict[str, Any]]:
    """Parse a Threat Dragon JSON document into normalized threat entries.

    Walks ``detail.diagrams[].cells[].data.threats[]``. Each threat emits one
    normalized entry with fields matching the threat-model-normalized schema.
    Missing/malformed sections are tolerated (parser returns an empty list
    rather than raising).
    """
    detail = doc.get("detail") or {}
    diagrams = detail.get("diagrams") or []
    if not isinstance(diagrams, list):
        return []
    entries: list[dict[str, Any]] = []
    for i, diagram in enumerate(diagrams):
        if not isinstance(diagram, dict):
            continue
        cells = diagram.get("cells") or []
        if not isinstance(cells, list):
            continue
        for j, cell in enumerate(cells):
            if not isinstance(cell, dict):
                continue
            data = cell.get("data") or {}
            threats = data.get("threats") if isinstance(data, dict) else None
            if not isinstance(threats, list):
                continue
            asset = _cell_asset_name(cell)
            for k, threat in enumerate(threats):
                if not isinstance(threat, dict):
                    continue
                title = threat.get("title") or threat.get("description") or "(unnamed threat)"
                mitigation = threat.get("mitigation") or None  # empty string → None
                letter = _stride_letter_from_threat_type(str(threat.get("type") or ""))
                locator = f"diagrams[{i}].cells[{j}].threats[{k}]"
                entries.append({
                    "entry_id": _stable_entry_id(asset=asset, threat=title, locator=locator),
                    "asset": asset,
                    "threat": title,
                    "mitigation": mitigation,
                    "methodology": "stride",
                    "source_locator": locator,
                    "extraction_confidence": "high",
                    "framework_refs": {
                        "stride_letter": letter,
                        "linddun_letter": None,
                        "attack_tree_position": None,
                        "mitre_attack": [],
                    },
                    "inferred_apd_goals": stride_letter_to_apd_goals(letter) if letter else [],
                })
    return entries
