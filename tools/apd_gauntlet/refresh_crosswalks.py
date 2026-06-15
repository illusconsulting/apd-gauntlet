"""Ground the compliance-projection crosswalks against the authoritative NIST CPRT
exports (ADR-0022).

Context (from analysing the CPRT JSON exports):

* The **CSF 2.0** CPRT export maps each subcategory to 800-53 *families*
  (``external_reference`` relationships to the 800-53 doc — e.g. ``PR.AA-05 -> AC,
  IA``), not to specific controls. Family-level references are too coarse to
  project directly (a subcategory can reference 8-20 families).
* The **SP 800-66r2** (HIPAA) CPRT export has no control-level 800-53 mapping at
  all — r2 uses a "relevant publications" model (``pub_crosswalk`` points at *SP
  800-53* the document, not its controls). The control-level HIPAA<->800-53
  crosswalk lives only in SP 800-66 **r1** Appendix D.

So this is a GROUNDING tool, not a raw importer: it keeps the curated
control-level crosswalks below (the useful granularity) but VALIDATES that every
curated (target -> control) mapping is a subset of NIST's stated references,
drops any that exceed NIST's scope, enriches the target titles from the real
export, and records provenance. Run via ``apd-gauntlet refresh-crosswalks
--csf2-json <export> --hipaa-json <export>``.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Curated control-level selections (the human-maintained source of truth).
# CSF 2.0: grounded so each control's family is within the subcategory's CPRT
# 800-53 family references (validated by ground_csf2 on every refresh).
CSF2_CURATED: dict[str, list[str]] = {
    "PR.AA-01": ["IA-2"],
    "PR.AA-03": ["IA-2"],
    "PR.AA-05": ["AC-3", "AC-6"],
    "PR.DS-01": ["SC-28", "SC-13"],
    "PR.DS-02": ["SC-8"],
    "PR.DS-11": ["CP-9"],
    "PR.PS-04": ["AU-2", "AU-3", "AU-12"],
    "DE.CM-09": ["SI-7"],
}

# HIPAA Security Rule: {standard/imp-spec -> (fallback_title, [800-53 controls])},
# control selections from SP 800-66r1 Appendix D (r2 dropped the control-level
# crosswalk); titles are validated/enriched against the 800-66r2 CPRT export.
HIPAA_CURATED: dict[str, tuple[str, list[str]]] = {
    "164.308(a)(1)(ii)(D)": ("Information System Activity Review", ["AU-6"]),
    "164.308(a)(4)":        ("Information Access Management", ["AC-2", "AC-3"]),
    "164.308(a)(5)(ii)(C)": ("Log-in Monitoring", ["AU-6"]),
    "164.308(a)(7)(ii)(A)": ("Data Backup Plan", ["CP-9"]),
    "164.308(a)(7)(ii)(B)": ("Disaster Recovery Plan", ["CP-10"]),
    "164.310(d)(2)(iv)":    ("Data Backup and Storage", ["CP-9"]),
    "164.312(a)(1)":        ("Access Control", ["AC-3", "AC-6"]),
    "164.312(a)(2)(i)":     ("Unique User Identification", ["IA-2", "AC-2"]),
    "164.312(a)(2)(iii)":   ("Automatic Logoff", ["AC-11", "AC-12"]),
    "164.312(a)(2)(iv)":    ("Encryption and Decryption", ["SC-28", "SC-13"]),
    "164.312(b)":           ("Audit Controls", ["AU-2", "AU-3", "AU-12"]),
    "164.312(c)(1)":        ("Integrity", ["SI-7", "AU-9"]),
    "164.312(d)":           ("Person or Entity Authentication", ["IA-2"]),
    "164.312(e)(1)":        ("Transmission Security", ["SC-8"]),
    "164.312(e)(2)(i)":     ("Integrity Controls", ["SC-8"]),
    "164.312(e)(2)(ii)":    ("Encryption", ["SC-13"]),
}

# CSF informative references / HIPAA crosswalks are broad (a control intersects a
# requirement); render conservatively as STRM intersects_with -> "partial" fidelity.
_RELATIONSHIP = "intersects_with"


def load_cprt(path: Path) -> dict[str, Any]:
    """Load a CPRT JSON export (response.elements.{elements, relationships})."""
    data: dict[str, Any] = json.loads(Path(path).read_text(encoding="utf-8"))
    return data


def _elements(cprt: dict[str, Any]) -> list[dict[str, Any]]:
    return cprt.get("response", {}).get("elements", {}).get("elements", []) or []


def _relationships(cprt: dict[str, Any]) -> list[dict[str, Any]]:
    return cprt.get("response", {}).get("elements", {}).get("relationships", []) or []


def _family(control_id: str) -> str:
    return control_id.split("-", 1)[0]


def csf2_family_index(cprt: dict[str, Any]) -> dict[str, set[str]]:
    """Return {subcategory_id: {800-53 family, ...}} from the CSF 2.0 export's
    ``external_reference`` relationships into the 800-53 document."""
    idx: dict[str, set[str]] = {}
    for r in _relationships(cprt):
        if (r.get("relationship_identifier") == "external_reference"
                and str(r.get("dest_doc_identifier", "")).startswith("SP_800_53")):
            src, dest = r.get("source_element_identifier"), r.get("dest_element_identifier")
            if src and dest:
                idx.setdefault(src, set()).add(dest)
    return idx


def _titles(cprt: dict[str, Any]) -> dict[str, str]:
    """Return {element_identifier: best title} (title, else descriptive text)."""
    out: dict[str, str] = {}
    for e in _elements(cprt):
        eid = e.get("element_identifier")
        if eid:
            out[eid] = str(e.get("title") or e.get("text") or "")
    return out


def csf2_titles(cprt: dict[str, Any]) -> dict[str, str]:
    return _titles(cprt)


def hipaa_titles(cprt: dict[str, Any]) -> dict[str, str]:
    return _titles(cprt)


def ground_csf2(
    curated: dict[str, list[str]], cprt: dict[str, Any]
) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    """Validate curated (subcategory -> control) mappings against the CSF 2.0
    export. Keep a control only when its 800-53 family is within the
    subcategory's authoritative references; drop (and report) the rest."""
    idx = csf2_family_index(cprt)
    titles = csf2_titles(cprt)
    mappings: list[dict[str, str]] = []
    dropped: list[dict[str, str]] = []
    for sub in sorted(curated):
        auth = idx.get(sub, set())
        title = titles.get(sub, "")
        for ctrl in curated[sub]:
            if _family(ctrl) in auth:
                mappings.append({"target_id": sub, "target_title": title,
                                 "nist": ctrl, "relationship": _RELATIONSHIP})
            else:
                dropped.append({
                    "target_id": sub, "nist": ctrl,
                    "reason": f"family {_family(ctrl)} not in NIST CSF2 800-53 "
                              f"references {sorted(auth)}",
                })
    return mappings, dropped


def ground_hipaa(
    curated: dict[str, tuple[str, list[str]]], cprt: dict[str, Any]
) -> tuple[list[dict[str, str]], list[str]]:
    """Validate curated HIPAA target ids + enrich titles against the 800-66r2
    export. Control selections (800-66r1 App D) are kept as-is — r2 has no
    control-level mapping to validate against. Returns (mappings, unmatched_ids)."""
    titles = hipaa_titles(cprt)
    mappings: list[dict[str, str]] = []
    unmatched: list[str] = []
    for tid in sorted(curated):
        fallback_title, ctrls = curated[tid]
        if tid in titles:
            title = titles[tid] or fallback_title
        else:
            title = fallback_title
            unmatched.append(tid)
        for ctrl in ctrls:
            mappings.append({"target_id": tid, "target_title": title,
                             "nist": ctrl, "relationship": _RELATIONSHIP})
    return mappings, unmatched


def _write_crosswalk(
    out_path: Path, mappings: list[dict[str, str]], *, source: str,
    source_sha256: str, note: str,
) -> None:
    payload = {
        "_meta": {
            "source": source,
            "source_sha256": source_sha256,
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "note": note,
        },
        "mappings": mappings,
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2, sort_keys=False) + "\n", encoding="utf-8")


def refresh_crosswalks(
    csf2_json: Path, hipaa_json: Path, *, data_dir: Path | None = None,
) -> dict[str, Any]:
    """Ground both crosswalks against the CPRT exports and write the data files.

    Returns a report {csf2: {kept, dropped}, hipaa: {kept, unmatched}}.
    """
    if data_dir is None:
        data_dir = Path(__file__).parent / "data"
    csf2_cprt = load_cprt(csf2_json)
    hipaa_cprt = load_cprt(hipaa_json)
    csf2_map, csf2_dropped = ground_csf2(CSF2_CURATED, csf2_cprt)
    hipaa_map, hipaa_unmatched = ground_hipaa(HIPAA_CURATED, hipaa_cprt)

    _write_crosswalk(
        data_dir / "csf2-800-53-crosswalk.json", csf2_map,
        source=f"NIST CSF 2.0 CPRT export ({Path(csf2_json).name})",
        source_sha256=hashlib.sha256(Path(csf2_json).read_bytes()).hexdigest(),
        note="Control selections validated against the CSF 2.0 CPRT family-level "
             "800-53 references (each control's family is within NIST's stated refs); "
             "titles from the export. Relationship intersects_with -> partial fidelity.",
    )
    _write_crosswalk(
        data_dir / "hipaa-800-53-crosswalk.json", hipaa_map,
        source=f"NIST SP 800-66r2 CPRT export ({Path(hipaa_json).name})",
        source_sha256=hashlib.sha256(Path(hipaa_json).read_bytes()).hexdigest(),
        note="Standard ids/titles validated/enriched against the 800-66r2 CPRT "
             "export; control selections from SP 800-66r1 Appendix D (r2 has no "
             "control-level 800-53 crosswalk). intersects_with -> partial fidelity.",
    )
    return {
        "csf2": {"kept": len(csf2_map), "dropped": csf2_dropped},
        "hipaa": {"kept": len(hipaa_map), "unmatched": hipaa_unmatched},
    }
