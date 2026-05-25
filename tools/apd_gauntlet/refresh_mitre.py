"""Refresh the cached MITRE ATT&CK mitigation→technique crosswalk."""
from __future__ import annotations

import hashlib
import json
import pathlib
import urllib.request

MITRE_URL = "https://raw.githubusercontent.com/mitre/cti/master/enterprise-attack/enterprise-attack.json"

# Hard cap on the fetched bundle size to bound memory use if the upstream is
# compromised or misbehaves. The legitimate bundle is ~50 MB and growing slowly.
MAX_BUNDLE_BYTES = 200 * 1024 * 1024  # 200 MiB
FETCH_TIMEOUT_SECONDS = 60


def fetch_and_project(out_path: pathlib.Path) -> None:
    with urllib.request.urlopen(MITRE_URL, timeout=FETCH_TIMEOUT_SECONDS) as resp:
        raw = resp.read(MAX_BUNDLE_BYTES + 1)
    if len(raw) > MAX_BUNDLE_BYTES:
        raise ValueError(
            f"MITRE bundle exceeds {MAX_BUNDLE_BYTES} bytes; refusing to load. "
            "Verify the upstream feed before retrying."
        )
    source_sha256 = hashlib.sha256(raw).hexdigest()
    bundle = json.loads(raw.decode("utf-8"))
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
        "source_url": MITRE_URL,
        "source_sha256": source_sha256,
        "mitigations": {k: sorted(set(v)) for k, v in mit_to_techs.items()},
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2, sort_keys=True))
