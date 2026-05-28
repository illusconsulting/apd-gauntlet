"""Pure-function transforms producing the window.APD_DATA shape the React
template expects. Each function takes a RunArtifacts and returns plain
Python (dict / list / str / int) suitable for json.dumps.
"""
from __future__ import annotations

import collections
import json as _json
import pathlib
import re
from typing import Any

from . import taxonomy as _taxonomy
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
            out.append(asset.get("name") or asset.get("asset_id") or "")
    return out


def _attacker_positions_from_inventory(inventory: dict[str, Any]) -> list[str]:
    """Derive attacker positions from asset_inventory assets."""
    out: list[str] = []
    for asset in inventory.get("assets") or []:
        if not isinstance(asset, dict):
            continue
        if (asset.get("asset_type") == "attacker_position"
                or asset.get("kind") == "attacker_position"):
            out.append(asset.get("name") or asset.get("asset_id") or "")
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
        # NOTE: future enhancement — pull from advisory-report frontmatter
        "synthesizer_version": "1.0.0",
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
        if c.get("merged") or (
            c.get("lens_perspectives") and c.get("id", "").startswith("cap-merged")
        )
    )
    linked_clusters = sum(
        1 for f in findings if f.get("linked_perspectives")
    )

    return {
        "findings_total": len(findings),
        # post-dedup view; pre/post unknown without specialist counts
        "findings_pre_dedup": len(findings),
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


def capability_grid(artifacts: RunArtifacts) -> list[dict[str, Any]]:
    """Map every deduped capability to the template's flat cap-grid entry shape."""
    out: list[dict[str, Any]] = []
    for c in artifacts.deduped_capabilities:
        entry: dict[str, Any] = {
            "id":       c.get("id"),
            "tier":     c.get("apd_tier"),
            "goal":     c.get("apd_goal"),
            "maturity": c.get("maturity", "implemented"),
            "title":    c.get("title", ""),
            "scope":    c.get("scope", ""),
        }
        lp_raw = c.get("lens_perspectives")
        is_merged = c.get("id", "").startswith("cap-merged") or bool(c.get("merged") or lp_raw)
        if is_merged and lp_raw:
            entry["merged"] = True
            # lens_perspectives may be a dict (key=lens name, value=dict with source_id)
            # or a list of dicts with an apd_goal/goal field.
            if isinstance(lp_raw, dict):
                cross_lens = list(lp_raw.keys())
            else:
                cross_lens = [
                    lp.get("apd_goal", lp.get("goal"))
                    for lp in lp_raw
                    if isinstance(lp, dict)
                ]
            if cross_lens:
                entry["cross_lens"] = cross_lens
        elif is_merged:
            entry["merged"] = True
            # No lens_perspectives but id starts with cap-merged — still flag merged
            entry["cross_lens"] = []
        out.append(entry)
    return out


_SEV_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3, "informational": 4, "info": 4}
_CONF_ORDER = {"high": 0, "medium": 1, "low": 2}


def _algorithmic_headline_ranks(findings: list[dict[str, Any]]) -> dict[str, int]:
    """Pick the top-10 findings by (severity, confidence, id). Returns id→rank."""
    ranked = sorted(
        findings,
        key=lambda f: (
            _SEV_ORDER.get(f.get("severity", "informational"), 9),
            _CONF_ORDER.get(f.get("confidence", "low"), 9),
            f.get("id", ""),
        ),
    )
    top = ranked[:10]
    return {f["id"]: idx + 1 for idx, f in enumerate(top) if "id" in f}


def _lens_perspective_source_ids(raw: Any) -> list[Any]:
    """Extract source_id values from lens_perspectives — tolerates list or dict shape.

    List shape (standard):  [{source_id: "x", ...}, ...]  → ["x", ...]
    Dict shape (legacy runs): {lens_name: {source_id: "x", ...}, ...} → ["x", ...]
    """
    if isinstance(raw, dict):
        return [v.get("source_id") for v in raw.values() if isinstance(v, dict)]
    if isinstance(raw, list):
        return [lp.get("source_id") for lp in raw if isinstance(lp, dict)]
    return []


def findings_array(
    artifacts: RunArtifacts,
    *,
    headline_supplement: list[dict[str, Any]] | None,
) -> list[dict[str, Any]]:
    """Map deduped findings + attack-path findings to the template's flat array.

    Headline rank: if supplement is supplied, use it (silently dropping ids that
    don't match a finding). Otherwise compute algorithmically (top-10 by severity
    desc, confidence desc, id asc).
    """
    all_findings = artifacts.deduped_findings + artifacts.attack_path_findings
    if headline_supplement is not None:
        valid_ids = {f.get("id") for f in all_findings}
        headline_ranks = {
            entry["id"]: entry["rank"]
            for entry in headline_supplement
            if entry.get("id") in valid_ids
        }
    else:
        headline_ranks = _algorithmic_headline_ranks(all_findings)

    out: list[dict[str, Any]] = []
    for f in all_findings:
        fid = f.get("id")
        entry: dict[str, Any] = {
            "id":           fid,
            "title":        f.get("title", ""),
            "goal":         f.get("apd_goal"),
            "tier":         f.get("apd_tier"),
            "severity":     f.get("severity", "informational"),
            "confidence":   f.get("confidence", "low"),
            "disposition":  f.get("disposition", "gap"),
            "summary":      f.get("summary", ""),
            "detail":       f.get("detail", ""),
            "rubric_clause": f.get("rubric_clause"),
            "evidence":     f.get("evidence", []),
            "recommendation": f.get("recommendation"),
            "mappings": {
                "nist":      (f.get("control_mappings") or {}).get("nist_800_53r5", []),
                "attack":    _extract_ids_from_mapping(
                    (f.get("control_mappings") or {}).get("mitre_attack"), "technique"
                ),
                "cwe":       (f.get("control_mappings") or {}).get("cwe", []),
                "owasp_api": (f.get("control_mappings") or {}).get("owasp_api_top10", []),
                "owasp":     (f.get("control_mappings") or {}).get("owasp_top10", []),
                "d3fend":    _extract_ids_from_mapping(
                    (f.get("control_mappings") or {}).get("d3fend")
                ),
            },
            "lens_perspectives": _lens_perspective_source_ids(f.get("lens_perspectives")),
            "prerequisite_evidence": f.get("prerequisite_evidence", []),
        }
        if fid in headline_ranks:
            entry["headline"] = True
            entry["headline_rank"] = headline_ranks[fid]
        out.append(entry)
    return out


def strengths_section(
    artifacts: RunArtifacts,
    *,
    supplied_strengths: list[dict[str, Any]] | None,
) -> list[dict[str, Any]]:
    """Join supplied strengths (id + caveats) with capability titles.

    Raises ValueError if a supplied id does not resolve to a capability — this
    is a synthesizer authoring error caught by the validator's cross-file pass,
    but we double-check here so build-time misuse fails loudly.
    """
    if not supplied_strengths:
        return []
    by_id = {c.get("id"): c for c in artifacts.deduped_capabilities}
    out: list[dict[str, Any]] = []
    for s in supplied_strengths:
        cid = s.get("id")
        cap = by_id.get(cid)
        if cap is None:
            raise ValueError(
                f"strengths references unknown capability {cid!r}"
            )
        out.append({
            "id":       cid,
            "title":    cap.get("title", ""),
            "goal":     cap.get("apd_goal"),
            "maturity": cap.get("maturity", "implemented"),
            "caveats":  list(s.get("caveats") or []),
        })
    return out


_PKG_DATA = pathlib.Path(__file__).resolve().parent.parent / "data"


def _nist_family_titles() -> dict[str, str]:
    result: dict[str, str] = _json.loads((_PKG_DATA / "nist-families.json").read_text())
    return result


def _notable_for_family(
    family: str,
    controls: list[dict[str, Any]],
) -> str:
    """Build a one-liner naming the strongest and weakest control in the family."""
    in_family = [c for c in controls if c.get("family") == family]
    if not in_family:
        return ""
    covered = [c for c in in_family if c.get("posture") == "covered"]
    gapped = [c for c in in_family if c.get("posture") == "gapped"]
    bits: list[str] = []
    if covered[:3]:
        bits.append(", ".join(c["id"] for c in covered[:3]) + " strong")
    if gapped[:3]:
        bits.append(", ".join(c["id"] for c in gapped[:3]) + " gapped")
    return "; ".join(bits) if bits else "mixed posture"


def _notable_for_family_new(
    family: str,
    family_controls: dict[str, list[str]],
) -> str:
    """Build a notable one-liner from a coverage_by_family family dict.

    Returns up to 3 of the most-cited control IDs (by finding-citation count).
    """
    if not family_controls:
        return ""
    sorted_controls = sorted(
        family_controls.items(),
        key=lambda kv: (-len(kv[1]), kv[0]),
    )
    top = [ctrl_id for ctrl_id, _ in sorted_controls[:3]]
    return ", ".join(top) + " cited" if top else ""


def _build_cap_controls_index(capabilities: list[dict[str, Any]]) -> dict[str, set[str]]:
    """Return {control_id: {cap_id, ...}} for all capabilities with NIST mappings."""
    index: dict[str, set[str]] = {}
    for cap in capabilities:
        cap_id = cap.get("id", "")
        cm = cap.get("control_mappings") or {}
        nist_controls = cm.get("nist_800_53r5") or []
        for ctrl in _extract_ids_from_mapping(nist_controls):
            # Strip enhancements to base control for family derivation, but keep
            # the full control id in the index so we match exact keys.
            index.setdefault(ctrl, set()).add(cap_id)
    return index


def nist_rollup_rows(artifacts: RunArtifacts) -> list[dict[str, Any]]:
    """Return rows for the NIST coverage table: one per family with counts +
    notable one-liner. Order: descending by (covered + gapped + both).

    Tolerates two synthesizer output shapes:

    Old shape — ``family_summary`` + ``control`` list present:
      Uses the pre-computed counts and posture fields directly.

    New shape — ``coverage_by_family`` present (no ``family_summary``):
      Derives counts by cross-walking capabilities via
      ``deduped_capabilities[].control_mappings.nist_800_53r5``.
      - covered: controls with ≥1 capability but 0 findings
      - gapped:  controls with ≥1 finding but 0 capabilities
      - both:    controls with both findings and ≥1 capability
    """
    family_summary = artifacts.nist_coverage.get("family_summary") or {}
    control_list = artifacts.nist_coverage.get("control") or []
    titles = _nist_family_titles()
    rows: list[dict[str, Any]] = []

    if family_summary:
        # Old shape path.
        for fam, summary in sorted(family_summary.items()):
            rows.append({
                "family":  fam,
                "title":   titles.get(fam, fam),
                "covered": summary.get("covered", 0),
                "gapped":  summary.get("gapped", 0),
                "both":    summary.get("gapped_and_covered", 0),
                "notable": _notable_for_family(fam, control_list),
            })
    else:
        # New shape path — derive from coverage_by_family + capability cross-walk.
        coverage_by_family = artifacts.nist_coverage.get("coverage_by_family") or {}
        cap_controls = _build_cap_controls_index(artifacts.deduped_capabilities)
        for fam in sorted(coverage_by_family.keys()):
            family_controls: dict[str, list[str]] = coverage_by_family[fam] or {}
            covered = gapped = both = 0
            for ctrl_id, finding_ids in family_controls.items():
                has_findings = bool(finding_ids)
                has_caps = bool(cap_controls.get(ctrl_id))
                if has_findings and has_caps:
                    both += 1
                elif has_findings:
                    gapped += 1
                elif has_caps:
                    covered += 1
                # else: silent — neither findings nor capabilities cite it; skip
            rows.append({
                "family":  fam,
                "title":   titles.get(fam, fam),
                "covered": covered,
                "gapped":  gapped,
                "both":    both,
                "notable": _notable_for_family_new(fam, family_controls),
            })

    rows.sort(key=lambda r: -(r["covered"] + r["gapped"] + r["both"]))
    return rows


def _attack_coverage_label(mits: list[str], findings: int) -> str:
    """Return coverage string from mitigations list and finding count."""
    if not mits:
        return "uncovered"
    if findings == 0:
        return "covered"
    return "partial"


def attack_exposure_rows(artifacts: RunArtifacts) -> list[dict[str, Any]]:
    """Return rows for the ATT&CK exposure table.

    coverage:
      - 'uncovered' if mitigations list is empty
      - 'covered'   if mitigations present and exposure_finding_count == 0
      - 'partial'   if both findings and mitigations are present

    Tolerates two synthesizer output shapes:

    Old shape — ``technique`` (singular) list present:
      Each entry has ``id``, ``name``, ``exposure_finding_count``,
      ``mitigated_by_capabilities`` (list of dicts with ``capability_id``).

    New shape — ``techniques`` (plural) dict present:
      Top-level entries may have ``citing_findings`` / ``countering_capabilities``.
      Sub-techniques are nested under ``sub_techniques`` dict.
      Parent entries lacking ``citing_findings`` are skipped when they only
      carry ``sub_techniques``; both parent and sub-technique rows are emitted
      when the parent also has its own ``citing_findings``.
    """
    rows: list[dict[str, Any]] = []

    technique_list = artifacts.attack_exposure.get("technique")
    if technique_list is not None:
        # Old shape path.
        for t in technique_list:
            mits = [
                m.get("capability_id")
                for m in (t.get("mitigated_by_capabilities") or [])
                if m.get("capability_id")
            ]
            findings = t.get("exposure_finding_count", 0)
            rows.append({
                "id":          t.get("id"),
                "name":        t.get("name", ""),
                "findings":    findings,
                "mitigations": mits,
                "coverage":    _attack_coverage_label(mits, findings),
                "note":        "",
            })
    else:
        # New shape path — techniques dict with optional sub_techniques.
        techniques_dict = artifacts.attack_exposure.get("techniques") or {}
        for tech_id in sorted(techniques_dict.keys()):
            entry = techniques_dict[tech_id]
            if not isinstance(entry, dict):
                continue
            sub_techniques = entry.get("sub_techniques") or {}
            parent_citing = entry.get("citing_findings")

            if parent_citing is not None:
                # Parent entry has its own findings — emit it.
                mits = list(entry.get("countering_capabilities") or [])
                findings = len(parent_citing)
                rows.append({
                    "id":          tech_id,
                    "name":        entry.get("name", ""),
                    "findings":    findings,
                    "mitigations": mits,
                    "coverage":    _attack_coverage_label(mits, findings),
                    "note":        "",
                })
            # Emit sub-technique rows (sorted for determinism).
            for sub_id in sorted(sub_techniques.keys()):
                sub = sub_techniques[sub_id]
                if not isinstance(sub, dict):
                    continue
                mits = list(sub.get("countering_capabilities") or [])
                findings = len(sub.get("citing_findings") or [])
                rows.append({
                    "id":          sub_id,
                    "name":        sub.get("name", ""),
                    "findings":    findings,
                    "mitigations": mits,
                    "coverage":    _attack_coverage_label(mits, findings),
                    "note":        "",
                })

    rows.sort(key=lambda r: (-r["findings"], r["id"] or ""))
    return rows


_GOAL_SHORT = {
    "confidentiality": "conf",
    "integrity":       "intg",
    "availability":    "avail",
    "distributed":     "dist",
    "resilient":       "resil",
    "ephemeral":       "ephem",
    "authenticity":    "auth",
    "non_repudiation": "nonrep",
    "immutability":    "immut",
}
_GOAL_LABEL_SHORT = {
    "conf":   "Conf",   "intg":  "Intg",   "avail":  "Avail",
    "dist":   "Dist",   "resil": "Resil",  "ephem":  "Ephem",
    "auth":   "Auth",   "nonrep": "NonRep", "immut": "Immut",
}
_POSTURE_TO_CELL = {
    "silent": "silent",
    "covered": "covered",
    "gapped": "gapped",
    "gapped_and_covered": "both",
}


def _artifact_label(finding: dict[str, Any]) -> str:
    """Extract the primary artifact label from a finding's evidence list.

    Returns the ``artifact`` field of the first evidence entry, or
    ``"(unattributed)"`` when no evidence is available.
    """
    evidence = finding.get("evidence") or []
    if evidence and isinstance(evidence[0], dict):
        label = evidence[0].get("artifact") or evidence[0].get("locator")
        if label:
            return str(label)
    return "(unattributed)"


def apd_matrix(artifacts: RunArtifacts) -> dict[str, Any]:
    """Return the data.apd_matrix block: goals[], goalLabels{}, rows[{component, cells}].

    Tolerates two synthesizer output shapes:

    Old shape — ``component`` list present:
      Each component entry has ``name`` and ``cells`` keyed by full goal name,
      each cell containing ``findings``, ``capabilities``, and ``posture``.

    New shape — ``coverage`` goal-keyed dict present:
      Synthesises per-component rows by grouping findings under each goal by
      their ``evidence[0].artifact`` string (Option B from spec).
      Capabilities for a goal are taken from the goal's ``capabilities`` list.
      Posture per (component, goal) cell:
        - ``'both'``    if the component has findings and the goal has capabilities
        - ``'gapped'``  if findings but no capabilities under the goal
        - ``'covered'`` if no findings for this component but capabilities exist
        - ``'silent'``  otherwise
    """
    goals = list(_GOAL_LABEL_SHORT.keys())
    rows: list[dict[str, Any]] = []

    component_list = artifacts.apd_coverage_matrix.get("component")
    if component_list is not None:
        # Old shape path.
        for comp in component_list:
            cells_in = comp.get("cells") or {}
            cells_out: dict[str, str] = {}
            for full_goal, short in _GOAL_SHORT.items():
                cell = cells_in.get(full_goal) or {}
                posture = cell.get("posture", "silent")
                cells_out[short] = _POSTURE_TO_CELL.get(posture, "silent")
            rows.append({"component": comp.get("name", ""), "cells": cells_out})
    else:
        # New shape path — synthesise rows from goal-keyed coverage dict.
        coverage = artifacts.apd_coverage_matrix.get("coverage") or {}

        # Build a lookup: finding_id → finding record (for evidence[0].artifact).
        all_findings = artifacts.deduped_findings + artifacts.attack_path_findings
        finding_by_id: dict[str, dict[str, Any]] = {
            f["id"]: f for f in all_findings if f.get("id")
        }

        # Collect all artifact labels across all goals.
        all_artifacts: set[str] = set()
        for full_goal in _GOAL_SHORT:
            goal_data = coverage.get(full_goal) or {}
            for tier_key in ("critical", "high", "medium", "low", "informational",
                             "blocked", "uncertainty"):
                for fid in (goal_data.get(tier_key) or []):
                    f = finding_by_id.get(fid)
                    if f:
                        all_artifacts.add(_artifact_label(f))
                    # IDs with no loaded finding get attributed to (unattributed).

        # For each artifact, build its row.
        for artifact_name in sorted(all_artifacts):
            row_cells: dict[str, str] = {}
            for full_goal, short in _GOAL_SHORT.items():
                goal_data = coverage.get(full_goal) or {}
                has_caps = bool(goal_data.get("capabilities"))
                # Gather findings under this goal attributed to this artifact.
                goal_finding_ids: list[str] = []
                for tier_key in ("critical", "high", "medium", "low", "informational",
                                 "blocked", "uncertainty"):
                    for fid in (goal_data.get(tier_key) or []):
                        f = finding_by_id.get(fid)
                        label = _artifact_label(f) if f else "(unattributed)"
                        if label == artifact_name:
                            goal_finding_ids.append(fid)
                has_findings = bool(goal_finding_ids)
                if has_findings and has_caps:
                    posture = "both"
                elif has_findings:
                    posture = "gapped"
                elif has_caps:
                    posture = "covered"
                else:
                    posture = "silent"
                row_cells[short] = posture
            rows.append({"component": artifact_name, "cells": row_cells})

    return {
        "goals":      goals,
        "goalLabels": _GOAL_LABEL_SHORT,
        "rows":       rows,
    }


_NODE_ID_OK = re.compile(r"^[A-Za-z0-9_-]+$")
_LABEL_STRIP = re.compile(r"[^A-Za-z0-9 _./:()-]")
# HTML tag pattern: reject the entire label if angle-bracket tags are present.
_HTML_TAG = re.compile(r"<[^>]*>")


def _safe_node_id(raw: str, fallback: str) -> str:
    """Mermaid node ids must be plain identifiers. Drop anything that could
    inject syntax (newlines, brackets, html); fall back if nothing left.
    """
    return raw if _NODE_ID_OK.match(raw or "") else fallback


def _safe_label(raw: str) -> str:
    """Mermaid node labels are quoted strings; we additionally strip
    metacharacters that confuse the parser or compose into XSS payloads when
    mermaid renders to SVG (#, [, ], <, >, &, etc.). Truncated to 60 chars
    so adversarial asset names cannot blow up graph layout.

    Defense-in-depth: if the raw label contains HTML-tag patterns (<…>), the
    entire label is discarded and replaced with "(unnamed)" — partial stripping
    of a tag payload (e.g. keeping "alert" from "<script>alert(1)</script>")
    is still an information leak from an adversarial asset name.
    """
    if _HTML_TAG.search(raw or ""):
        return "(unnamed)"
    cleaned = _LABEL_STRIP.sub(" ", raw or "")
    cleaned = " ".join(cleaned.split())  # collapse whitespace
    return cleaned[:60] or "(unnamed)"


def _build_mermaid(asset_graph: dict[str, Any]) -> str:
    """Render the asset graph as a small Mermaid graph TD definition.

    Sanitization discipline: every node id and label is constrained to a safe
    character set before interpolation. Asset-graph YAML is adopter-controlled
    so unsafe characters MUST be filtered here, not at render time. Combined
    with mermaid securityLevel='strict' on the JS side, this gives defense in
    depth against label-based SVG/XSS payloads.

    Mermaid handles ~100-node graphs comfortably. Larger graphs render a
    summary string so the page still loads.
    """
    nodes = asset_graph.get("nodes") or []
    edges = asset_graph.get("edges") or []
    if len(nodes) > 100:
        return f"graph TD\n  too_large[\"Graph has {len(nodes)} nodes; see asset-graph.yaml\"]"
    lines = ["graph TD"]
    id_remap: dict[str, str] = {}
    for idx, n in enumerate(nodes):
        raw_id = str(n.get("node_id", f"n{idx}"))
        safe_id = _safe_node_id(raw_id, f"n{idx}")
        id_remap[raw_id] = safe_id
        label = _safe_label(str(n.get("name") or raw_id))
        ntype = n.get("node_type", "")
        prefix = {
            "attacker_position": "((", "crown_jewel": "{{", "service": "[",
            "data_store": "[(", "secret_store": "[(",
        }.get(ntype, "[")
        suffix = {"((": "))", "{{": "}}", "[": "]", "[(": ")]"}[prefix]
        lines.append(f"  {safe_id}{prefix}\"{label}\"{suffix}")
    for e in edges:
        src = id_remap.get(str(e.get("from", "")))
        dst = id_remap.get(str(e.get("to", "")))
        if src and dst:
            lines.append(f"  {src} --> {dst}")
    return "\n".join(lines)


def attack_paths_data(artifacts: RunArtifacts) -> dict[str, Any] | None:
    """Return the data.attack_paths block, or None when v1.4 artifacts are absent."""
    if artifacts.attack_paths is None or artifacts.asset_graph is None:
        return None
    paths = artifacts.attack_paths.get("paths") or []

    # Group paths by (attacker_position, crown_jewel).
    pairs_by_key: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for p in paths:
        key = (p.get("attacker_position", ""), p.get("crown_jewel", ""))
        pairs_by_key.setdefault(key, []).append({
            "path_id":          p.get("path_id"),
            "hop_count":        p.get("hop_count"),
            "feasibility":      p.get("feasibility"),
            "severity_sum":     p.get("severity_sum"),
            "mitigation_count": p.get("mitigation_count"),
            "edges":            p.get("edges", []),
            "bottleneck_edges": p.get("bottleneck_edges", []),
        })
    pairs = [
        {"attacker_position": k[0], "crown_jewel": k[1], "paths": v}
        for k, v in sorted(pairs_by_key.items())
    ]

    overlays: list[Any] = []
    if artifacts.defense_graph is not None:
        overlays = artifacts.defense_graph.get("bottleneck_overlays") or []

    node_count = len(artifacts.asset_graph.get("nodes") or [])
    edge_count = len(artifacts.asset_graph.get("edges") or [])

    # Build a helpful explanation when no paths were enumerated but the graph exists.
    pairs_empty_explanation: str | None = None
    if not pairs and (node_count > 0 or edge_count > 0):
        pairs_empty_explanation = (
            f"No (attacker, crown-jewel) paths were enumerated for this run. "
            f"The asset graph has {node_count} node{'s' if node_count != 1 else ''} / "
            f"{edge_count} edge{'s' if edge_count != 1 else ''} but those edges don't form "
            f"a chain from any declared attacker position to any declared crown jewel. "
            f"This is common for runs where finding evidence references documents "
            f"(e.g., tech_plan.md) rather than specific asset names — the analyzer "
            f"can't synthesize edges from prose. To enable path enumeration, enrich "
            f"00-context/asset-inventory.yaml with explicit trust boundaries connecting "
            f"attacker positions to crown jewels, OR have specialists tag finding evidence "
            f"with the asset_id of the affected component."
        )

    result: dict[str, Any] = {
        "mermaid": _build_mermaid(artifacts.asset_graph),
        "pairs":   pairs,
        "bottleneck_overlays": overlays,
        "summary": {
            "total_paths":  len(paths),
            "total_pairs":  len(pairs),
            "bottleneck_count": (
                len(overlays)
                if artifacts.defense_graph is not None else 0
            ),
        },
        "asset_graph_summary": {
            "node_count": node_count,
            "edge_count": edge_count,
        },
    }
    if pairs_empty_explanation is not None:
        result["pairs_empty_explanation"] = pairs_empty_explanation
    return result


# ---------------------------------------------------------------------------
# Contradictions + severity-disagreements + next_steps + posture passthrough
# ---------------------------------------------------------------------------


def contradictions_section(artifacts: RunArtifacts) -> list[dict[str, Any]]:
    """Return contradictions in the React template's shape:
       [{id, finding{id, assertion}, capability{id, assertion}, comparison, resolution}]
    """
    out: list[dict[str, Any]] = []
    for c in artifacts.contradictions:
        # capability_ids may be a list — the template shows one; join with " + " if many.
        cap_ids = c.get("capability_ids") or (
            [c.get("capability_id")] if c.get("capability_id") else []
        )
        out.append({
            "id": c.get("id"),
            "finding": {
                "id": c.get("finding_id"),
                "assertion": (c.get("finding_assertion") or "").strip(),
            },
            "capability": {
                "id": " + ".join(filter(None, cap_ids)) or None,
                "assertion": (c.get("capability_assertion") or "").strip(),
            },
            "comparison": (c.get("evidence_comparison") or c.get("comparison") or "").strip(),
            "resolution": (c.get("recommended_resolution") or c.get("resolution") or "").strip(),
        })
    return out


def _normalise_agent_severities(d: dict[str, Any]) -> list[dict[str, Any]]:
    """Normalise the various severity-agent shapes into [{lens, severity}].

    Accepted input shapes:
    1. ``agents: [{lens: "x", severity: "high"}, ...]``  (planned schema)
    2. ``lens_severities: [{lens: "x", severity: "high"}, ...]``  (alternate key)
    3. ``agent_severities: {lens_name: "severity", ...}``  (legacy fixture shape)
    """
    # Shape 1 & 2: list under agents / lens_severities
    agents_raw = d.get("agents") or d.get("lens_severities")
    if agents_raw and isinstance(agents_raw, list):
        return [
            {"lens": a.get("lens") or a.get("agent"), "severity": a.get("severity")}
            for a in agents_raw
            if isinstance(a, dict)
        ]
    # Shape 3: dict under agent_severities
    agent_sev = d.get("agent_severities")
    if isinstance(agent_sev, dict):
        return [
            {"lens": lens, "severity": sev}
            for lens, sev in agent_sev.items()
        ]
    return []


def severity_disagreements_section(artifacts: RunArtifacts) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for d in artifacts.severity_disagreements:
        out.append({
            "id":     d.get("finding_id") or d.get("id"),
            "agents": _normalise_agent_severities(d),
            "chosen":    d.get("chosen_severity") or d.get("chosen"),
            "rationale": (d.get("rationale") or "").strip(),
        })
    return out


def next_steps_section(
    supplement: list[dict[str, Any]] | None,
) -> list[dict[str, Any]]:
    if not supplement:
        return []
    return [
        {"rank": e["rank"], "text": e["text"], "refs": list(e.get("refs") or [])}
        for e in sorted(supplement, key=lambda x: x.get("rank", 9999))
    ]


def posture_summary_section(
    supplement: dict[str, Any] | None,
) -> dict[str, str]:
    if supplement:
        return {
            "trustworthiness": supplement.get("trustworthiness", ""),
            "scalability":     supplement.get("scalability", ""),
            "auditability":    supplement.get("auditability", ""),
        }
    return {
        "trustworthiness": "Posture statement not provided by synthesizer.",
        "scalability":     "Posture statement not provided by synthesizer.",
        "auditability":    "Posture statement not provided by synthesizer.",
    }


def build_apd_data(
    artifacts: RunArtifacts,
    *,
    run_dir: pathlib.Path | None = None,
) -> dict[str, Any]:
    """Assemble the full window.APD_DATA dict from a RunArtifacts."""
    supplement = artifacts.report_data or {}
    return {
        "meta":     meta_block(artifacts, run_dir=run_dir),
        "summary":  summary_rollup(artifacts),
        "exec_summary": (supplement.get("exec_summary") or {}).get(
            "paragraphs", ["Run summary not provided by synthesizer."]
        ),
        "posture_summary": posture_summary_section(supplement.get("posture_summary")),
        "capabilities":  capability_grid(artifacts),
        "strengths":     strengths_section(
            artifacts, supplied_strengths=supplement.get("strengths"),
        ),
        "findings":      findings_array(
            artifacts, headline_supplement=supplement.get("headline_findings"),
        ),
        "contradictions":              contradictions_section(artifacts),
        "contradictions_notes":        artifacts.contradictions_notes,
        "severity_disagreements":      severity_disagreements_section(artifacts),
        "severity_disagreements_notes": artifacts.severity_disagreements_notes,
        "nist_rollup":      nist_rollup_rows(artifacts),
        "attack_exposure":  attack_exposure_rows(artifacts),
        "apd_matrix":       apd_matrix(artifacts),
        "attack_paths":     attack_paths_data(artifacts),
        "next_steps":       next_steps_section(supplement.get("next_steps")),
        "taxonomy":         taxonomy_dict(artifacts),
    }


# ---------------------------------------------------------------------------
# Taxonomy hover dictionary
# ---------------------------------------------------------------------------

_NIST_FAMILY_DISPLAY = "NIST 800-53r5"
_ATTACK_FAMILY_DISPLAY = "MITRE ATT&CK"
_CWE_FAMILY_DISPLAY = "CWE"
_D3FEND_FAMILY_DISPLAY = "MITRE D3FEND"


def _extract_ids_from_mapping(raw: Any, *fallback_keys: str) -> list[str]:
    """Extract string IDs from a control-mapping field that may be:

    - A list of strings: ["ID1", "ID2"]
    - A list of dicts: [{"id": "ID1", ...}, {"technique": "T1040", ...}, ...]
    - None / missing → []

    ``fallback_keys`` is the ordered list of dict keys to try when "id" is absent.
    E.g. for mitre_attack: fallback_keys=("technique",)
    """
    if not raw:
        return []
    ids: list[str] = []
    for item in raw:
        if isinstance(item, str):
            ids.append(item)
        elif isinstance(item, dict):
            # Try "id" first, then each fallback key in order.
            found = item.get("id")
            if not found:
                for key in fallback_keys:
                    found = item.get(key)
                    if found:
                        break
            if found and isinstance(found, str):
                ids.append(found)
    return ids


def _collect_referenced_ids(artifacts: RunArtifacts) -> dict[str, set[str]]:
    """Return {family: {ids}} across all findings + capabilities + coverage rows."""
    out: dict[str, set[str]] = {
        "nist": set(), "attack": set(), "cwe": set(), "d3fend": set(),
    }
    for rec in artifacts.deduped_findings + artifacts.attack_path_findings:
        cm = rec.get("control_mappings") or {}
        out["nist"].update(cm.get("nist_800_53r5") or [])
        out["attack"].update(_extract_ids_from_mapping(cm.get("mitre_attack"), "technique"))
        out["cwe"].update(_extract_ids_from_mapping(cm.get("cwe")))
        out["d3fend"].update(_extract_ids_from_mapping(cm.get("d3fend")))
    for rec in artifacts.deduped_capabilities:
        cm = rec.get("control_mappings") or {}
        out["nist"].update(cm.get("nist_800_53r5") or [])
        out["attack"].update(_extract_ids_from_mapping(cm.get("mitre_attack"), "technique"))
        out["cwe"].update(_extract_ids_from_mapping(cm.get("cwe")))
        out["d3fend"].update(_extract_ids_from_mapping(cm.get("d3fend")))
    # Coverage rollups — handle both old and new shapes.
    # Old shape: nist_coverage has a "control" list with id fields.
    for c in artifacts.nist_coverage.get("control") or []:
        out["nist"].add(c.get("id", ""))
    # New shape: nist_coverage has "coverage_by_family" dict.
    for _fam, fam_controls in (artifacts.nist_coverage.get("coverage_by_family") or {}).items():
        out["nist"].update(fam_controls.keys() if isinstance(fam_controls, dict) else [])
    # Old shape: attack_exposure has a "technique" list with id fields.
    for t in artifacts.attack_exposure.get("technique") or []:
        out["attack"].add(t.get("id", ""))
    # New shape: attack_exposure has "techniques" dict (with optional sub_techniques).
    for tech_id, entry in (artifacts.attack_exposure.get("techniques") or {}).items():
        out["attack"].add(tech_id)
        if isinstance(entry, dict):
            for sub_id in (entry.get("sub_techniques") or {}):
                out["attack"].add(sub_id)
    return out


def taxonomy_dict(artifacts: RunArtifacts) -> dict[str, dict[str, str]]:
    """Return {id: {family, title}} for every taxonomy ID referenced in the run.

    Only IDs actually present in findings, capabilities, or coverage rollups are
    included — this keeps data.js small for runs with large reference databases.
    """
    refs = _collect_referenced_ids(artifacts)
    out: dict[str, dict[str, str]] = {}

    # NIST 800-53r5: titles come from the nist-coverage artifact (already loaded).
    nist_titles = {
        c.get("id"): c.get("title", "")
        for c in (artifacts.nist_coverage.get("control") or [])
    }
    for cid in sorted(refs["nist"]):
        if not cid:
            continue
        out[cid] = {
            "family": _NIST_FAMILY_DISPLAY,
            "title":  nist_titles.get(cid, cid),
        }

    # ATT&CK techniques: titles from taxonomy module; fall back to id if absent.
    attack = _taxonomy.attack_technique_titles()
    for tid in sorted(refs["attack"]):
        if not tid:
            continue
        out[tid] = {"family": _ATTACK_FAMILY_DISPLAY, "title": attack.get(tid, tid)}

    # CWE: titles from taxonomy module; fall back to id if absent.
    cwe = _taxonomy.cwe_titles()
    for cid in sorted(refs["cwe"]):
        if not cid:
            continue
        out[cid] = {"family": _CWE_FAMILY_DISPLAY, "title": cwe.get(cid, cid)}

    # D3FEND: titles from taxonomy module; fall back to id if absent.
    d3 = _taxonomy.d3fend_titles()
    for did in sorted(refs["d3fend"]):
        if not did:
            continue
        out[did] = {"family": _D3FEND_FAMILY_DISPLAY, "title": d3.get(did, did)}

    return out
