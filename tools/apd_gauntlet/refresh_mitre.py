"""Refresh the cached MITRE ATT&CK mitigation→technique crosswalk."""
from __future__ import annotations

import json
import pathlib
import urllib.request

MITRE_URL = "https://raw.githubusercontent.com/mitre/cti/master/enterprise-attack/enterprise-attack.json"


def fetch_and_project(out_path: pathlib.Path) -> None:
    with urllib.request.urlopen(MITRE_URL) as resp:
        bundle = json.loads(resp.read().decode("utf-8"))
    mit_to_techs: dict[str, list[str]] = {}
    by_id = {obj.get("id"): obj for obj in bundle.get("objects", []) if obj.get("id")}
    for obj in bundle.get("objects", []):
        if obj.get("type") != "relationship":
            continue
        if obj.get("relationship_type") != "mitigates":
            continue
        src = by_id.get(obj.get("source_ref")) or {}
        tgt = by_id.get(obj.get("target_ref")) or {}
        mit_id = next(
            (
                r["external_id"]
                for r in src.get("external_references", [])
                if r.get("source_name") == "mitre-attack"
            ),
            None,
        )
        tech_id = next(
            (
                r["external_id"]
                for r in tgt.get("external_references", [])
                if r.get("source_name") == "mitre-attack"
            ),
            None,
        )
        if mit_id and tech_id:
            mit_to_techs.setdefault(mit_id, []).append(tech_id)
    payload = {
        "version": bundle.get("created", "unknown"),
        "mitigations": {k: sorted(set(v)) for k, v in mit_to_techs.items()},
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2, sort_keys=True))
