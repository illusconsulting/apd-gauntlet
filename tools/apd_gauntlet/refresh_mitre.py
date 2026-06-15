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
from datetime import datetime, timezone
from typing import Any

from .kb_fetch import fetch_pinned

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

    Pass :data:`MOBILE_URL` to fetch the Mobile matrix. Delegates the size-cap +
    timeout discipline to :func:`kb_fetch.fetch_pinned`.
    """
    body, _meta = fetch_pinned(
        url, max_bytes=MAX_RESPONSE_BYTES, timeout=DEFAULT_TIMEOUT_SECONDS
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


def project_detection(bundle: dict[str, Any]) -> dict[str, list[dict[str, str]]]:
    """Project a STIX ATT&CK bundle to ``{technique_id: [data component]}``.

    ATT&CK v17+ detection model: a ``detects`` relationship links an
    ``x-mitre-detection-strategy`` to a technique; the strategy's
    ``x_mitre_analytic_refs`` point at ``x-mitre-analytic`` objects whose
    ``x_mitre_log_source_references`` cite the ``x-mitre-data-component``
    (``DC####``) telemetry. This walks technique <- strategy -> analytic ->
    data-component to the sorted, de-duplicated list of
    ``{data_component_id, data_component_name}`` ATT&CK says is required to detect
    the technique (the detection overlay, ADR-0022). Pinned to data components,
    which are stable across the v17 detection-strategy restructure.
    """
    by_id = {obj.get("id"): obj for obj in bundle.get("objects", []) if obj.get("id")}
    out: dict[str, list[dict[str, str]]] = {}
    seen: dict[str, set[str]] = {}
    for obj in bundle.get("objects", []):
        if obj.get("type") != "relationship" or obj.get("relationship_type") != "detects":
            continue
        strat = by_id.get(obj.get("source_ref")) or {}
        tech = by_id.get(obj.get("target_ref")) or {}
        if strat.get("type") != "x-mitre-detection-strategy":
            continue
        tid = _attack_external_id(tech)
        if not tid:
            continue
        for aref in strat.get("x_mitre_analytic_refs", []) or []:
            analytic = by_id.get(aref) or {}
            for lsr in analytic.get("x_mitre_log_source_references", []) or []:
                dc = by_id.get(lsr.get("x_mitre_data_component_ref")) or {}
                dc_name = dc.get("name")
                if not dc_name:
                    continue
                dc_id = _attack_external_id(dc) or ""
                key = dc_id or dc_name
                if key in seen.setdefault(tid, set()):
                    continue
                seen[tid].add(key)
                out.setdefault(tid, []).append(
                    {"data_component_id": dc_id, "data_component_name": dc_name}
                )
    for tid in out:
        out[tid].sort(key=lambda c: c["data_component_name"])
    return out


def fetch_and_project_detection(out_path: pathlib.Path) -> None:
    """Fetch the enterprise bundle and write the detection overlay catalog."""
    raw = fetch_mitre_bundle()
    bundle = json.loads(raw.decode("utf-8"))
    payload = {
        "source_url": MITRE_URL,
        "source_sha256": hashlib.sha256(raw).hexdigest(),
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "attack_version": bundle.get("created", "unknown"),
        "detection": project_detection(bundle),
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


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


def merge_mobile_mitigations(
    mitigations_path: pathlib.Path,
    *,
    fetched_at: str | None = None,
) -> dict[str, int]:
    """Additively merge ATT&CK Mobile mitigation→technique mappings into the
    bundled crosswalk (``mitre-mitigations.json``).

    Mobile mitigation ids are disjoint from the Enterprise set except M1013
    (Application Developer Guidance), which is the same mitigation in both
    matrices, so a per-id union of technique lists is sound. Idempotent. Returns
    ``{"added_mitigations": n, "added_pairs": p, "total_mitigations": m}``.

    Re-serialized with the bundled crosswalk's options (``indent=2,
    sort_keys=True``) so the diff is the unioned/added entries plus the
    ``mobile_source_*`` provenance keys.
    """
    import datetime

    raw = fetch_mitre_bundle(MOBILE_URL)
    bundle = json.loads(raw.decode("utf-8"))
    by_id = {obj.get("id"): obj for obj in bundle.get("objects", []) if obj.get("id")}
    mobile_map: dict[str, set[str]] = {}
    for obj in bundle.get("objects", []):
        if obj.get("type") != "relationship" or obj.get("relationship_type") != "mitigates":
            continue
        mit = _attack_external_id(by_id.get(obj.get("source_ref")) or {})
        tech = _attack_external_id(by_id.get(obj.get("target_ref")) or {})
        if mit and tech:
            mobile_map.setdefault(mit, set()).add(tech)

    existing = json.loads(mitigations_path.read_text(encoding="utf-8"))
    mitigations: dict[str, list[str]] = existing.setdefault("mitigations", {})
    added_ids = 0
    added_pairs = 0
    for mid in sorted(mobile_map):
        current = set(mitigations.get(mid, []))
        if mid not in mitigations:
            added_ids += 1
        merged = current | mobile_map[mid]
        added_pairs += len(merged) - len(current)
        mitigations[mid] = sorted(merged)

    existing["mobile_source_url"] = MOBILE_URL
    existing["mobile_source_sha256"] = hashlib.sha256(raw).hexdigest()
    existing["mobile_fetched_at"] = fetched_at or datetime.date.today().isoformat()
    mitigations_path.write_text(
        json.dumps(existing, indent=2, sort_keys=True), encoding="utf-8"
    )
    return {
        "added_mitigations": added_ids,
        "added_pairs": added_pairs,
        "total_mitigations": len(mitigations),
    }
