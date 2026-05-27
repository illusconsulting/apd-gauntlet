"""Pure-function transforms producing the window.APD_DATA shape the React
template expects. Each function takes a RunArtifacts and returns plain
Python (dict / list / str / int) suitable for json.dumps.
"""
from __future__ import annotations

import collections
import pathlib
from typing import Any

from .loader import RunArtifacts

TIER_GOALS: dict[str, list[str]] = {
    "trustworthiness": ["confidentiality", "integrity", "availability"],
    "scalability":     ["distributed", "resilient", "ephemeral"],
    "auditability":    ["authenticity", "non_repudiation", "immutability"],
}


def _crown_jewels_from_inventory(inventory: dict[str, Any]) -> list[str]:
    """Derive crown jewels from asset_inventory assets.

    Checks ``asset_type == 'crown_jewel'`` or ``kind == 'crown_jewel'``.
    Returns an empty list when inventory has no matching assets.
    """
    out: list[str] = []
    for asset in inventory.get("assets") or []:
        if not isinstance(asset, dict):
            continue
        if asset.get("asset_type") == "crown_jewel" or asset.get("kind") == "crown_jewel":
            out.append(asset.get("name", asset.get("asset_id", "")))
    return out


def _attacker_positions_from_inventory(inventory: dict[str, Any]) -> list[str]:
    """Derive attacker positions from asset_inventory assets."""
    out: list[str] = []
    for asset in inventory.get("assets") or []:
        if not isinstance(asset, dict):
            continue
        if asset.get("asset_type") == "attacker_position" or asset.get("kind") == "attacker_position":
            out.append(asset.get("name", asset.get("asset_id", "")))
    return out


def _resolve_crown_jewels(artifacts: RunArtifacts) -> list[str]:
    """Return crown jewels, preferring run_cfg source over inventory derivation.

    Priority:
    1. ``artifacts.run_crown_jewels`` (from .apd-run.yaml top-level list)
    2. ``asset_inventory.crown_jewels`` top-level array
    3. Assets with asset_type/kind == 'crown_jewel'
    """
    if artifacts.run_crown_jewels:
        return list(artifacts.run_crown_jewels)
    inventory = artifacts.asset_inventory
    if "crown_jewels" in inventory and isinstance(inventory["crown_jewels"], list):
        return [
            cj["name"] if isinstance(cj, dict) and "name" in cj else str(cj)
            for cj in inventory["crown_jewels"]
        ]
    return _crown_jewels_from_inventory(inventory)


def _resolve_attacker_positions(artifacts: RunArtifacts) -> list[str]:
    """Return attacker positions, preferring run_cfg source over inventory derivation.

    Priority:
    1. ``artifacts.run_attacker_positions`` (from .apd-run.yaml top-level list)
    2. ``asset_inventory.attacker_positions`` top-level array
    3. Assets with asset_type/kind == 'attacker_position'
    """
    if artifacts.run_attacker_positions:
        return list(artifacts.run_attacker_positions)
    inventory = artifacts.asset_inventory
    if "attacker_positions" in inventory and isinstance(inventory["attacker_positions"], list):
        return [
            ap["name"] if isinstance(ap, dict) and "name" in ap else str(ap)
            for ap in inventory["attacker_positions"]
        ]
    return _attacker_positions_from_inventory(inventory)


def _count_artifact_types(run_dir: pathlib.Path | None) -> tuple[int, list[str]]:
    if run_dir is None or not (run_dir / "inputs").exists():
        return 0, []
    entries = sorted((run_dir / "inputs").iterdir())
    suffixes = collections.Counter(p.suffix.lstrip(".") or "file" for p in entries)
    types = [
        f"{k}×{v}" if v > 1 else k
        for k, v in sorted(suffixes.items(), key=lambda kv: (-kv[1], kv[0]))
    ]
    return len(entries), types


def meta_block(
    artifacts: RunArtifacts,
    run_dir: pathlib.Path | None = None,
) -> dict[str, Any]:
    """Return the data.meta block for the HTML template."""
    artifact_count, artifact_types = _count_artifact_types(run_dir)
    subject = artifacts.subject or artifacts.run_id
    return {
        "framework_version": artifacts.framework_version,
        "domain_pack": {
            "name": artifacts.domain_pack_name,
            "version": artifacts.domain_pack_version,
        },
        "run_id": artifacts.run_id,
        "synthesizer_version": "1.0.0",  # NOTE: future enhancement — pull from advisory-report frontmatter
        "specialists_skipped": [],
        "subject": subject.split(" — ")[0] if " — " in subject else subject,
        "subject_tagline": subject.split(" — ", 1)[1] if " — " in subject else "",
        "date": artifacts.date,
        "artifact_count": artifact_count,
        "artifact_types": artifact_types,
        "crown_jewels": _resolve_crown_jewels(artifacts),
        "attacker_positions": _resolve_attacker_positions(artifacts),
    }
