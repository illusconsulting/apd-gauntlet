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
from typing import Any
from urllib.request import urlopen

MITRE_URL = "https://raw.githubusercontent.com/mitre/cti/master/enterprise-attack/enterprise-attack.json"
# The ATT&CK Mobile matrix. Mobile-pack runs emit Mobile technique IDs (e.g.
# T1634); their titles are merged into the bundled catalog additively so they
# render as names rather than bare IDs. See ``merge_mobile_technique_titles``.
MOBILE_URL = "https://raw.githubusercontent.com/mitre/cti/master/mobile-attack/mobile-attack.json"

# Hard cap on the fetched bundle size to bound memory use if the upstream is
# compromised or misbehaves. The legitimate bundle is ~50 MB and growing slowly.
MAX_RESPONSE_BYTES = 200 * 1024 * 1024  # 200 MiB
DEFAULT_TIMEOUT_SECONDS = 60


def fetch_mitre_bundle(url: str = MITRE_URL) -> bytes:
    """Fetch a MITRE ATT&CK STIX bundle (enterprise by default). Returns raw JSON bytes.

    Pass :data:`MOBILE_URL` to fetch the Mobile matrix. Raises ``ValueError`` if
    the response exceeds :data:`MAX_RESPONSE_BYTES` (checked twice: once via
    ``Content-Length``, once after reading).
    """
    with urlopen(url, timeout=DEFAULT_TIMEOUT_SECONDS) as response:
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


def _attack_external_id(obj: dict[str, Any]) -> str | None:
    """Return an object's mitre-attack external_id (e.g. ``T1634``), or None."""
    for ref in obj.get("external_references", []) or []:
        if ref.get("source_name") == "mitre-attack":
            external_id = ref.get("external_id")
            if isinstance(external_id, str) and external_id:
                return external_id
    return None


def project_technique_titles(bundle: dict[str, Any]) -> dict[str, str]:
    """Project a STIX ATT&CK bundle to a ``{technique_id: name}`` map.

    Matches the bundled enterprise catalog's conventions: sub-technique names are
    prefixed with their parent technique's name (``Parent: Leaf``) for tooltip
    clarity, and revoked techniques are retained so legacy citations still
    resolve (a non-revoked object wins over a revoked one for the same id).
    """
    base: dict[str, tuple[str, bool]] = {}
    for obj in bundle.get("objects", []):
        if obj.get("type") != "attack-pattern":
            continue
        tid = _attack_external_id(obj)
        name = obj.get("name")
        if not tid or not name:
            continue
        revoked = bool(obj.get("revoked")) or bool(obj.get("x_mitre_deprecated"))
        prev = base.get(tid)
        if prev is None or (prev[1] and not revoked):
            base[tid] = (name, revoked)
    titles: dict[str, str] = {}
    for tid in sorted(base):
        name = base[tid][0]
        if "." in tid:
            parent = base.get(tid.split(".", 1)[0])
            titles[tid] = f"{parent[0]}: {name}" if parent else name
        else:
            titles[tid] = name
    return titles


def merge_mobile_technique_titles(
    techniques_path: pathlib.Path,
    *,
    fetched_at: str | None = None,
) -> dict[str, int]:
    """Additively merge ATT&CK Mobile technique titles into the bundled catalog.

    Fetches the :data:`MOBILE_URL` bundle and adds a title for every Mobile
    technique id not already present in ``techniques_path``; Enterprise entries
    are preserved byte-for-byte (Enterprise wins on any shared id). Idempotent —
    re-running adds nothing new. Returns ``{"added": n, "total": m}``.

    The file is re-serialized with the same options as the bundled catalog
    (``indent=2, sort_keys=False, ensure_ascii=False`` + trailing newline) so the
    only diff is the appended Mobile block plus the ``_meta`` provenance update.
    """
    import datetime

    raw = fetch_mitre_bundle(MOBILE_URL)
    bundle = json.loads(raw.decode("utf-8"))
    mobile_titles = project_technique_titles(bundle)

    existing = json.loads(techniques_path.read_text(encoding="utf-8"))
    techniques: dict[str, str] = existing.setdefault("techniques", {})
    added = 0
    for tid in sorted(mobile_titles):
        if tid not in techniques:  # Enterprise priority on shared ids.
            techniques[tid] = mobile_titles[tid]
            added += 1

    meta = existing.setdefault("_meta", {})
    meta["mobile_source"] = MOBILE_URL
    meta["mobile_source_sha256"] = hashlib.sha256(raw).hexdigest()
    meta["mobile_fetched_at"] = fetched_at or datetime.date.today().isoformat()
    note = (
        "ATT&CK Mobile technique titles merged additively "
        "(Enterprise entries unchanged; Enterprise wins on shared ids)."
    )
    if note not in meta.get("notes", ""):
        meta["notes"] = (meta.get("notes", "").rstrip() + " " + note).strip()

    techniques_path.write_text(
        json.dumps(existing, indent=2, sort_keys=False, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return {"added": added, "total": len(techniques)}
