"""Assemble 00-context/asset-inventory.yaml: mint deterministic asset-/idn-/tb-
ids from name+provenance and wire trust_boundaries.crosses (authored by asset
NAME) to the minted asset ids. Idempotent; no-op when the file is absent.

Runs in the intake phase, BEFORE specialists cite inventory ids in evidence, so
the ids are stable for the remainder of the run.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from .linters import compute_asset_id, compute_boundary_id, compute_identity_id


def _loc(rec: dict[str, Any]) -> str:
    prov = rec.get("provenance") or {}
    return str(prov.get("locator") or "")


def assemble_inventory(run_dir: Path) -> int:
    """Mint inventory ids + wire crosses by name. Returns asset ids (re)minted."""
    path = run_dir / "00-context" / "asset-inventory.yaml"
    if not path.exists():
        return 0
    inv = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(inv, dict):
        return 0

    name_to_asset_id: dict[str, str] = {}
    changed = 0
    for a in inv.get("assets") or []:
        new_id = compute_asset_id(a.get("name", ""), _loc(a))
        if a.get("asset_id") != new_id:
            changed += 1
        a["asset_id"] = new_id
        name_to_asset_id[a.get("name", "")] = new_id
    for i in inv.get("identities") or []:
        i["identity_id"] = compute_identity_id(i.get("name", ""), _loc(i))
    for b in inv.get("trust_boundaries") or []:
        b["boundary_id"] = compute_boundary_id(b.get("name", ""), _loc(b))
        # crosses authored by asset NAME -> rewrite to the minted asset id; pass
        # through values already in asset-id form so the pass is idempotent.
        b["crosses"] = [name_to_asset_id.get(c, c) for c in (b.get("crosses") or [])]

    path.write_text(
        yaml.safe_dump(inv, sort_keys=False, allow_unicode=True, width=4096),
        encoding="utf-8",
    )
    return changed
