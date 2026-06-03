"""Refresh the cached MITRE CWE reference data for the apd-gauntlet.

Fetches ``cwec_latest.xml.zip`` from cwe.mitre.org, projects every ``<Weakness>``
element to a compact JSON shape, and writes the result (with ``source_sha256``
and ``fetched_at`` metadata) to ``tools/apd_gauntlet/data/cwe.json``.

Security hardening mirrors :mod:`apd_gauntlet.refresh_mitre`:

* ``DEFAULT_TIMEOUT_SECONDS = 60`` — bounds time spent waiting for upstream.
* ``MAX_RESPONSE_BYTES = 200 MiB`` — bounds memory if upstream is compromised.
* Defense in depth: a ``Content-Length`` pre-check AND a post-read size check
  (the header may be missing, or it may lie).
"""

from __future__ import annotations

import hashlib
import io
import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.request import urlopen
from xml.etree import ElementTree as ET

CWE_XML_URL = "https://cwe.mitre.org/data/xml/cwec_latest.xml.zip"

# Hard cap on the fetched bundle size to bound memory use if the upstream is
# compromised or misbehaves. The legitimate ZIP is ~2 MB; 200 MiB leaves plenty
# of headroom for future growth while still being a useful guardrail.
MAX_RESPONSE_BYTES = 200 * 1024 * 1024  # 200 MiB
DEFAULT_TIMEOUT_SECONDS = 60

# CWE 4.x publishes against the cwe-7 schema namespace; this matches the
# ``xmlns`` declared in the live XML at the time of writing.
CWE_NAMESPACE = "http://cwe.mitre.org/cwe-7"
_NS = f"{{{CWE_NAMESPACE}}}"


def fetch_cwe_xml() -> bytes:
    """Fetch and unzip the latest CWE XML. Returns the raw XML bytes.

    Raises ``ValueError`` if the response exceeds :data:`MAX_RESPONSE_BYTES`
    (checked twice: once via ``Content-Length``, once after reading).
    """
    with urlopen(CWE_XML_URL, timeout=DEFAULT_TIMEOUT_SECONDS) as response:
        content_length = response.headers.get("Content-Length")
        if content_length is not None:
            try:
                advertised = int(content_length)
            except (TypeError, ValueError):
                advertised = None
            if advertised is not None and advertised > MAX_RESPONSE_BYTES:
                raise ValueError(
                    f"CWE XML response Content-Length ({advertised}) "
                    f"exceeds maximum ({MAX_RESPONSE_BYTES})"
                )
        zipped = response.read(MAX_RESPONSE_BYTES + 1)
    if len(zipped) > MAX_RESPONSE_BYTES:
        raise ValueError(
            f"CWE XML response body exceeds maximum ({MAX_RESPONSE_BYTES} bytes); "
            "refusing to load. Verify the upstream feed before retrying."
        )
    with zipfile.ZipFile(io.BytesIO(zipped)) as zf:
        xml_name = next(name for name in zf.namelist() if name.endswith(".xml"))
        return zf.read(xml_name)


def project_cwe_xml_to_json(xml_bytes: bytes) -> dict[str, Any]:
    """Project the CWE XML into a compact JSON-serialisable mapping.

    Each entry exposes the minimum surface area the gauntlet needs at runtime:
    id, name, abstraction, parents (``ChildOf`` relationships), and presence
    flags for demonstrative/observed examples.
    """
    root = ET.fromstring(xml_bytes)
    entries: list[dict[str, Any]] = []
    # Projects both <Weakness> and <Category> elements (see the Category loop
    # below). Categories are needed because some findings cite category CWEs
    # (e.g. CWE-840). <View> elements are intentionally not projected.
    for weakness in root.iter(f"{_NS}Weakness"):
        cwe_id = weakness.get("ID")
        if not cwe_id:
            continue
        name = weakness.get("Name") or ""
        abstraction = (weakness.get("Abstraction") or "").lower()
        seen_parents: set[str] = set()
        parents: list[str] = []
        for rel in weakness.iter(f"{_NS}Related_Weakness"):
            if rel.get("Nature") != "ChildOf":
                continue
            parent_id = rel.get("CWE_ID")
            if not parent_id:
                continue
            pid = f"CWE-{parent_id}"
            if pid not in seen_parents:
                seen_parents.add(pid)
                parents.append(pid)
        has_demo = weakness.find(f"{_NS}Demonstrative_Examples") is not None
        has_obs = weakness.find(f"{_NS}Observed_Examples") is not None
        entries.append(
            {
                "cwe_id": f"CWE-{cwe_id}",
                "name": name,
                "abstraction": abstraction,
                "parents": parents,
                "demonstrative_examples_present": has_demo,
                "observed_examples_present": has_obs,
            }
        )
    # Project <Category> elements too. Categories (e.g. CWE-840 "Business Logic
    # Errors") are cited by some findings; without them taxonomy_titles_resolve
    # would render a bare id. Categories have no Abstraction attr and no ChildOf
    # parents (they relate to members via Has_Member), so: abstraction="category",
    # parents=[].
    for category in root.iter(f"{_NS}Category"):
        cwe_id = category.get("ID")
        if not cwe_id:
            continue
        entries.append(
            {
                "cwe_id": f"CWE-{cwe_id}",
                "name": category.get("Name") or "",
                "abstraction": "category",
                "parents": [],
                "demonstrative_examples_present": False,
                "observed_examples_present": False,
            }
        )
    entries.sort(key=lambda e: int(str(e["cwe_id"]).removeprefix("CWE-")))
    return {
        "source_url": CWE_XML_URL,
        "source_sha256": hashlib.sha256(xml_bytes).hexdigest(),
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "entries": entries,
    }


def refresh_cwe(output_path: Path | None = None) -> Path:
    """Fetch, project, and write CWE reference data. Returns the output path."""
    if output_path is None:
        output_path = Path(__file__).parent / "data" / "cwe.json"
    xml_bytes = fetch_cwe_xml()
    projected = project_cwe_xml_to_json(xml_bytes)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(projected, indent=2, sort_keys=True), encoding="utf-8")
    return output_path


if __name__ == "__main__":
    written = refresh_cwe()
    print(f"Wrote {written}")
