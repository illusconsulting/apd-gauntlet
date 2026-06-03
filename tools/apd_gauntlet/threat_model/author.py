"""Deterministic threat-model skeleton builder (apd-gauntlet author-threat-model).

Pure, idempotent, never-invent: reads an intake asset-inventory document and
emits one normalized-TM skeleton entry per (surface, applicable-STRIDE) cell.
Every surface traces to an inventory record — the builder NEVER manufactures a
surface absent from the inventory. STRIDE applicability follows the
Shostack/Microsoft element-type matrix; APD-goal inference is single-sourced
from ``threat_model.mappings``.

This is the C1 "deterministic CLI floor": it grounds nothing and blocks nothing
(``extraction_confidence: low`` stubs with empty ``prerequisite_evidence``); the
apd-threat-model-author agent enriches/blocks each cell downstream.
"""
from __future__ import annotations

import hashlib
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import yaml

from .mappings import stride_letter_to_apd_goals

# Element-type -> applicable STRIDE categories (canonical Shostack matrix).
APPLICABLE_STRIDE: Mapping[str, tuple[str, ...]] = {
    "external_entity": ("S", "R"),
    "process": ("S", "T", "R", "I", "D", "E"),
    "data_store": ("T", "R", "I", "D"),
    "data_flow": ("T", "I", "D"),
}

# Inventory asset_type -> matrix element type. Synonyms collapse so future
# inventory vocabularies (api/gateway/database/topic) bind to the same cell-set.
_ASSET_TYPE_TO_ELEMENT: Mapping[str, str] = {
    "service": "process",
    "process": "process",
    "api": "process",
    "gateway": "process",
    "compute": "process",
    "external_dependency": "process",
    "data_store": "data_store",
    "database": "data_store",
    "queue": "data_store",
    "topic": "data_store",
    "secret_store": "data_store",
    "network": "data_store",
}


def _sha8(*parts: str) -> str:
    """sha256 of the concatenated parts, truncated to 8 hex chars."""
    return hashlib.sha256("".join(parts).encode("utf-8")).hexdigest()[:8]


def entry_id_for(asset: str, threat: str, source_locator: str) -> str:
    """entry_id = 'tm-' + sha8(asset + threat + source_locator)."""
    return "tm-" + _sha8(asset, threat, source_locator)


def _locator_of(record: dict[str, Any]) -> str:
    """Return a non-empty source_locator from the record's provenance.

    Prefers the explicit ``locator``, then ``artifact``, then the provenance
    ``source`` enum value — guaranteeing the skeleton entry's source_locator is
    never empty (the authoring-discipline self-check requires it).
    """
    prov = record.get("provenance") or {}
    return str(prov.get("locator") or prov.get("artifact") or prov.get("source") or "inventory")


def _skeleton_entry(*, asset: str, letter: str, source_locator: str) -> dict[str, Any]:
    threat = f"({letter} on {asset}: to be grounded)"
    return {
        "entry_id": entry_id_for(asset, threat, source_locator),
        "asset": asset,
        "threat": threat,
        "mitigation": None,
        "methodology": "stride",
        "source_locator": source_locator,
        "extraction_confidence": "low",
        "framework_refs": {"stride_letter": letter},
        "inferred_apd_goals": stride_letter_to_apd_goals(letter),
        "prerequisite_evidence": [],
    }


def build_skeleton(inventory: dict[str, Any], *, source_artifact: str) -> dict[str, Any]:
    """Build the normalized-TM skeleton envelope from an asset inventory.

    Pure + idempotent: same inventory in => byte-identical envelope out. One
    entry per (surface, applicable-STRIDE) cell. Surfaces come ONLY from the
    inventory's ``assets[]`` (mapped via the element matrix) and ``identities[]``
    (external entities). Records with an unknown ``asset_type`` are skipped (no
    fabricated cells). Entries are emitted in a deterministic order: identities
    then assets, each in inventory order, STRIDE letters in matrix order.
    """
    entries: list[dict[str, Any]] = []

    for ident in inventory.get("identities") or []:
        asset = str(ident.get("name") or "")
        if not asset:
            continue
        locator = _locator_of(ident)
        for letter in APPLICABLE_STRIDE["external_entity"]:
            entries.append(_skeleton_entry(asset=asset, letter=letter, source_locator=locator))

    for rec in inventory.get("assets") or []:
        asset = str(rec.get("name") or "")
        element = _ASSET_TYPE_TO_ELEMENT.get(str(rec.get("asset_type") or ""))
        if not asset or element is None:
            continue
        locator = _locator_of(rec)
        for letter in APPLICABLE_STRIDE[element]:
            entries.append(_skeleton_entry(asset=asset, letter=letter, source_locator=locator))

    return {
        "schema_version": 1,
        "generated_by": "threat_model_author",
        "source_artifact": source_artifact,
        "methodology": "stride",
        "extraction_summary": {
            "entry_count": len(entries),
            "high_confidence_count": 0,
            "medium_confidence_count": 0,
            "low_confidence_count": len(entries),
            "parser_used": "author-threat-model (deterministic skeleton)",
        },
        "entries": entries,
    }


def build_skeleton_from_inventory_file(inventory_path: Path) -> dict[str, Any]:
    """Load an asset-inventory YAML and build the skeleton.

    ``source_artifact`` is the inventory path itself (the primary grounding
    artifact for an authored baseline, per the schema's relaxed description).
    """
    inventory = yaml.safe_load(inventory_path.read_text(encoding="utf-8")) or {}
    return build_skeleton(inventory, source_artifact=str(inventory_path))
