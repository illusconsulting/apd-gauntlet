"""Refresh the cached MITRE CAPEC reference data for the apd-gauntlet.

CAPEC is the authoritative connective tissue between CWE weaknesses and MITRE
ATT&CK techniques: each attack pattern carries ``Related_Weaknesses`` (CWE) and,
for a subset of the catalog, an ATT&CK ``Taxonomy_Mapping``. The derived CAPEC
bridge (ADR-0022) uses exactly those two edges, so this projection keeps only
``{name, abstraction, related_cwe[], related_attack[]}`` per pattern.

Fetches ``capec_latest.xml`` (uncompressed, unlike CWE's zip) from
capec.mitre.org, projects every non-deprecated ``<Attack_Pattern>``, and writes
the result (with ``source_sha256`` and ``fetched_at``) to
``tools/apd_gauntlet/data/capec.json``.

Security hardening mirrors :mod:`apd_gauntlet.refresh_cwe`:

* ``DEFAULT_TIMEOUT_SECONDS = 60`` — bounds time spent waiting for upstream.
* ``MAX_RESPONSE_BYTES = 200 MiB`` — bounds memory if upstream is compromised.
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

from .kb_fetch import fetch_pinned

CAPEC_XML_URL = "https://capec.mitre.org/data/xml/capec_latest.xml"

# Hard cap on the fetched catalogue size to bound memory if upstream is
# compromised. The legitimate XML is ~4 MB; 200 MiB leaves ample headroom while
# still being a useful guardrail (mirrors refresh_cwe / refresh_mitre).
MAX_RESPONSE_BYTES = 200 * 1024 * 1024  # 200 MiB
DEFAULT_TIMEOUT_SECONDS = 60

# CAPEC 3.x publishes against the capec-3 schema namespace.
CAPEC_NAMESPACE = "http://capec.mitre.org/capec-3"
_NS = f"{{{CAPEC_NAMESPACE}}}"

# Attack patterns no longer in active use are not bridge material.
_SKIP_STATUS = {"Deprecated", "Obsolete"}

# ATT&CK enterprise technique ids are T#### or T####.### — the CAPEC Entry_ID
# carries the bare number (e.g. "1190" or "1574.010"). Guard against any
# non-technique taxonomy noise.
_ATTACK_ENTRY = re.compile(r"\d{4}(?:\.\d{3})?")


def fetch_capec_xml() -> bytes:
    """Fetch the latest CAPEC catalogue XML. Returns the raw XML bytes.

    Delegates the size-cap + timeout discipline to :func:`kb_fetch.fetch_pinned`.
    """
    data, _meta = fetch_pinned(
        CAPEC_XML_URL, max_bytes=MAX_RESPONSE_BYTES, timeout=DEFAULT_TIMEOUT_SECONDS
    )
    return data


def project_capec_xml_to_json(xml_bytes: bytes) -> dict[str, Any]:
    """Project the CAPEC XML into a compact ``{capec_id: {...}}`` mapping.

    Each entry exposes only what the bridge rollup needs: the pattern name, its
    abstraction, the CWE weaknesses it relates, and the ATT&CK techniques it maps
    to. Deprecated/obsolete patterns are dropped; CWE and technique lists are
    de-duplicated while preserving document order.
    """
    root = ET.fromstring(xml_bytes)
    patterns: dict[str, dict[str, Any]] = {}
    for ap in root.iter(f"{_NS}Attack_Pattern"):
        cid = ap.get("ID")
        if not cid:
            continue
        if (ap.get("Status") or "") in _SKIP_STATUS:
            continue

        related_cwe: list[str] = []
        seen_cwe: set[str] = set()
        for rw in ap.iter(f"{_NS}Related_Weakness"):
            raw = rw.get("CWE_ID")
            if not raw:
                continue
            wid = f"CWE-{raw}"
            if wid not in seen_cwe:
                seen_cwe.add(wid)
                related_cwe.append(wid)

        related_attack: list[str] = []
        seen_attack: set[str] = set()
        for tm in ap.iter(f"{_NS}Taxonomy_Mapping"):
            if tm.get("Taxonomy_Name") != "ATTACK":
                continue
            entry = tm.find(f"{_NS}Entry_ID")
            txt = (entry.text or "").strip() if entry is not None else ""
            if not _ATTACK_ENTRY.fullmatch(txt):
                continue
            tid = f"T{txt}"
            if tid not in seen_attack:
                seen_attack.add(tid)
                related_attack.append(tid)

        patterns[f"CAPEC-{cid}"] = {
            "name": ap.get("Name") or f"CAPEC-{cid}",
            "abstraction": (ap.get("Abstraction") or "").lower(),
            "related_cwe": related_cwe,
            "related_attack": related_attack,
        }

    return {
        "source_url": CAPEC_XML_URL,
        "source_sha256": hashlib.sha256(xml_bytes).hexdigest(),
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "attack_patterns": patterns,
    }


def refresh_capec(output_path: Path | None = None) -> Path:
    """Fetch, project, and write CAPEC reference data. Returns the output path."""
    if output_path is None:
        output_path = Path(__file__).parent / "data" / "capec.json"
    xml_bytes = fetch_capec_xml()
    projected = project_capec_xml_to_json(xml_bytes)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(projected, indent=2, sort_keys=True), encoding="utf-8")
    return output_path


if __name__ == "__main__":
    written = refresh_capec()
    print(f"Wrote {written}")
