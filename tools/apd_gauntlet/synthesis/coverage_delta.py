"""Deterministic domain-coverage-delta pre-pass (Subsystem B, spec §5.1).

Pure Python, no LLM. Computes mechanical coverage deltas between the run's
asset-inventory and the union of the selected packs' declarations, and writes
``40-synthesis/domain-coverage-delta.yaml`` — the candidate-signal file the
``apd-domain-auditor`` agent reads. Candidate signals only: no snippets, no
``dimpr-`` ids, no ``domain-improvements.yaml``.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

_NONALNUM = re.compile(r"[^a-z0-9]+")


def _normalize(text: str) -> str:
    """Lowercase, non-alphanumeric -> '_', collapse repeats, strip edges."""
    return _NONALNUM.sub("_", str(text).lower()).strip("_")


def _load_pack(domains_dir: Path, name: str) -> dict[str, Any]:
    meta_path = domains_dir / name / "domain.yaml"
    if not meta_path.exists():
        return {}
    data = yaml.safe_load(meta_path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {}


def _declared_union(domains_dir: Path, domains: list[str]) -> dict[str, set[str]]:
    union: dict[str, set[str]] = {
        "crown_jewels": set(),
        "attacker_positions": set(),
        "trust_boundaries": set(),
    }
    specs = [
        ("crown_jewels", "pattern", "crown_jewels"),
        ("attacker_positions", "position", "attacker_positions"),
        ("default_trust_boundaries", "boundary", "trust_boundaries"),
    ]
    for name in domains:
        meta = _load_pack(domains_dir, name)
        for field, key, bucket in specs:
            for item in meta.get(field, []) or []:
                if isinstance(item, dict) and item.get(key):
                    union[bucket].add(_normalize(item[key]))
    return union


def _candidates(
    inventory: dict[str, Any],
    union: dict[str, set[str]],
    primary_pack: str,
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    # Crown-jewel delta: artifact/threat_model/code_evidence assets only.
    for asset in inventory.get("assets", []) or []:
        if not isinstance(asset, dict):
            continue
        if not asset.get("asset_id"):
            continue
        prov = (asset.get("provenance") or {}).get("source")
        if prov == "domain_default":
            continue
        key = _normalize(asset.get("name", ""))
        if not key or key in union["crown_jewels"]:
            continue
        cand: dict[str, Any] = {
            "improvement_type": "missing_crown_jewel",
            "source": "deterministic",
            "default_target_pack": primary_pack,
            "priority": "high" if prov == "artifact" else "medium",
            "asset_name": asset.get("name", ""),
            "evidence": [{"kind": "asset_inventory", "ref": asset["asset_id"]}],
        }
        classes = asset.get("data_classifications")
        if classes:
            cand["data_classifications"] = list(classes)
        out.append(cand)
    # Attacker-position delta: non-domain_default identities (external_party).
    # Note: the union dedup only suppresses pack positions declared as
    # `external_<name>`; most pack positions (compromised_*, authenticated_*)
    # are not suppressed here by design — the agent auditor makes the final
    # keep/drop decision.
    for ident in inventory.get("identities", []) or []:
        if not isinstance(ident, dict):
            continue
        if not ident.get("identity_id"):
            continue
        if (ident.get("provenance") or {}).get("source") == "domain_default":
            continue
        if ident.get("identity_type") != "external_party":
            continue
        key = _normalize("external_" + str(ident.get("name", "")))
        if key in union["attacker_positions"]:
            continue
        out.append({
            "improvement_type": "missing_attacker_position",
            "source": "deterministic",
            "default_target_pack": primary_pack,
            "priority": "medium",
            "asset_name": ident.get("name", ""),
            "evidence": [{"kind": "asset_inventory", "ref": ident["identity_id"]}],
        })
    # Trust-boundary delta: non-domain_default boundaries.
    for bnd in inventory.get("trust_boundaries", []) or []:
        if not isinstance(bnd, dict):
            continue
        if not bnd.get("boundary_id"):
            continue
        if (bnd.get("provenance") or {}).get("source") == "domain_default":
            continue
        key = _normalize(bnd.get("name", ""))
        if not key or key in union["trust_boundaries"]:
            continue
        out.append({
            "improvement_type": "missing_trust_boundary",
            "source": "deterministic",
            "default_target_pack": primary_pack,
            "priority": "medium",
            "asset_name": bnd.get("name", ""),
            "crosses": list(bnd.get("crosses", []) or []),
            "evidence": [{"kind": "asset_inventory", "ref": bnd["boundary_id"]}],
        })
    return out


def build_coverage_delta(run_dir: Path, domains_dir: Path) -> Path:
    """Compute the coverage delta and write domain-coverage-delta.yaml. Returns
    the written path. Best-effort: a missing/empty inventory yields empty
    candidates and exits cleanly."""
    run_cfg_path = run_dir / ".apd-run.yaml"
    run_cfg: dict[str, Any] = (
        yaml.safe_load(run_cfg_path.read_text(encoding="utf-8")) or {}
        if run_cfg_path.exists()
        else {}
    )
    domains: list[str] = [str(d) for d in (run_cfg.get("domains") or [])]
    primary_pack = domains[0] if domains else ""

    inv_path = run_dir / "00-context" / "asset-inventory.yaml"
    inventory: dict[str, Any] = (
        yaml.safe_load(inv_path.read_text(encoding="utf-8")) or {}
        if inv_path.exists()
        else {}
    )

    union = _declared_union(domains_dir, domains)
    candidates = _candidates(inventory, union, primary_pack)

    doc = {
        "schema_version": 1,
        "generated_by": "coverage-delta",
        "examined_domains": domains,
        "declared_union": {
            "crown_jewels": sorted(union["crown_jewels"]),
            "attacker_positions": sorted(union["attacker_positions"]),
            "trust_boundaries": sorted(union["trust_boundaries"]),
        },
        "candidates": candidates,
    }
    synth = run_dir / "40-synthesis"
    synth.mkdir(parents=True, exist_ok=True)
    out_path = synth / "domain-coverage-delta.yaml"
    out_path.write_text(
        yaml.safe_dump(doc, sort_keys=False, default_flow_style=False, allow_unicode=True),
        encoding="utf-8",
    )
    return out_path
