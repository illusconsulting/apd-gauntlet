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


def summary_rollup(artifacts: RunArtifacts) -> dict[str, Any]:
    """Return the data.summary block — totals and tier/sev/disposition rollups."""
    findings = artifacts.deduped_findings + artifacts.attack_path_findings
    caps = artifacts.deduped_capabilities

    by_sev = collections.Counter(f.get("severity", "informational") for f in findings)
    by_disp = collections.Counter(f.get("disposition", "gap") for f in findings)
    by_tier = collections.Counter(f.get("apd_tier", "trustworthiness") for f in findings)
    by_mat = collections.Counter(c.get("maturity", "implemented") for c in caps)

    cross_lens_merged = sum(
        1 for c in caps
        if c.get("merged") or (c.get("lens_perspectives") and c.get("id", "").startswith("cap-merged"))
    )
    linked_clusters = sum(
        1 for f in findings if f.get("linked_perspectives")
    )

    return {
        "findings_total": len(findings),
        "findings_pre_dedup": len(findings),  # post-dedup view; pre/post unknown without specialist counts
        "cross_lens_merged_clusters": cross_lens_merged,
        "linked_clusters": linked_clusters,
        "bySeverity": {
            "critical":      by_sev.get("critical", 0),
            "high":          by_sev.get("high", 0),
            "medium":        by_sev.get("medium", 0),
            "low":           by_sev.get("low", 0),
            "info":          by_sev.get("informational", 0),
        },
        "byDisposition": {
            "gap":         by_disp.get("gap", 0),
            "blocked":     by_disp.get("blocked", 0),
            "risk":        by_disp.get("risk", 0),
            "uncertainty": by_disp.get("uncertainty", 0),
            "ok":          0,  # ok is a capability-side concept; kept for template parity
        },
        "byTier": {
            "trustworthiness": by_tier.get("trustworthiness", 0),
            "scalability":     by_tier.get("scalability", 0),
            "auditability":    by_tier.get("auditability", 0),
        },
        "capabilities_total":    len(caps),
        "capabilities_pre_dedup": len(caps),
        "capabilitiesByMaturity": {
            "designed":         by_mat.get("designed", 0),
            "implemented":      by_mat.get("implemented", 0),
            "tested":           by_mat.get("tested", 0),
            "operationalized":  by_mat.get("operationalized", 0),
        },
        "contradictions": len(artifacts.contradictions),
        "severity_disagreements": len(artifacts.severity_disagreements),
    }
