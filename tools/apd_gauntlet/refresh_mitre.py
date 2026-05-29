"""Refresh the cached MITRE ATT&CK mitigation→technique crosswalk.

Fetches the MITRE CTI ``enterprise-attack.json`` bundle, walks every
``relationship`` of ``relationship_type == "mitigates"``, and writes a compact
mitigation→techniques crosswalk JSON (with ``source_sha256`` metadata) to
``tools/apd_gauntlet/data/mitre-mitigations.json``.

Security hardening mirrors :mod:`apd_gauntlet.refresh_cwe`,
:mod:`apd_gauntlet.refresh_owasp`, and :mod:`apd_gauntlet.refresh_d3fend`:

* ``DEFAULT_TIMEOUT_SECONDS = 60`` — bounds time spent waiting for upstream.
* ``MAX_RESPONSE_BYTES = 200 MiB`` — bounds memory if upstream is compromised.
* Defense in depth: a ``Content-Length`` pre-check AND a post-read size check
  (the header may be missing, or it may lie).
"""

from __future__ import annotations

import hashlib
import json
import pathlib
from urllib.request import urlopen

MITRE_URL = "https://raw.githubusercontent.com/mitre/cti/master/enterprise-attack/enterprise-attack.json"

# Hard cap on the fetched bundle size to bound memory use if the upstream is
# compromised or misbehaves. The legitimate bundle is ~50 MB and growing slowly.
MAX_RESPONSE_BYTES = 200 * 1024 * 1024  # 200 MiB
DEFAULT_TIMEOUT_SECONDS = 60


def fetch_mitre_bundle() -> bytes:
    """Fetch the MITRE ATT&CK enterprise bundle. Returns the raw JSON bytes.

    Raises ``ValueError`` if the response exceeds :data:`MAX_RESPONSE_BYTES`
    (checked twice: once via ``Content-Length``, once after reading).
    """
    with urlopen(MITRE_URL, timeout=DEFAULT_TIMEOUT_SECONDS) as response:
        content_length = response.headers.get("Content-Length")
        if content_length is not None:
            try:
                advertised = int(content_length)
            except (TypeError, ValueError):
                advertised = None
            if advertised is not None and advertised > MAX_RESPONSE_BYTES:
                raise ValueError(
                    f"MITRE bundle response Content-Length ({advertised}) "
                    f"exceeds maximum ({MAX_RESPONSE_BYTES})"
                )
        body: bytes = response.read(MAX_RESPONSE_BYTES + 1)
    if len(body) > MAX_RESPONSE_BYTES:
        raise ValueError(
            f"MITRE bundle response body exceeds maximum ({MAX_RESPONSE_BYTES} bytes); "
            "refusing to load. Verify the upstream feed before retrying."
        )
    return body


def fetch_and_project(out_path: pathlib.Path) -> None:
    raw = fetch_mitre_bundle()
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
    out_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
