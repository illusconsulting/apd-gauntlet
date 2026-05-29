"""Pure-function transforms producing the window.APD_DATA shape the React
template expects. Each function takes a RunArtifacts and returns plain
Python (dict / list / str / int) suitable for json.dumps.
"""
from __future__ import annotations

import collections
import hashlib
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
    # Defensive sizing: any of the three collections may be a misshapen object
    # supplied by an adversarial fixture (see test_tier2_isolation). Per the
    # build_apd_data contract, the meta layer must not raise for per-section
    # data faults — those are isolated downstream. Default to "not empty" when
    # we cannot measure so the empty-run banner does not falsely trigger.
    def _safe_len(obj: Any) -> int:
        try:
            return len(obj)
        except Exception:  # noqa: BLE001 — defensive against any container fault
            return -1
    findings_len = _safe_len(artifacts.deduped_findings)
    attack_paths_len = _safe_len(artifacts.attack_path_findings)
    caps_len = _safe_len(artifacts.deduped_capabilities)
    if findings_len < 0 or attack_paths_len < 0 or caps_len < 0:
        is_empty_run = False
    else:
        is_empty_run = (
            (findings_len + attack_paths_len == 0) and (caps_len == 0)
        )
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
        "is_empty_run": is_empty_run,
        "reference_db_versions": _taxonomy.reference_db_versions(),
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


def _goal_to_tier(goal: str | None) -> str | None:
    """Reverse lookup: APD goal → APD tier. Used as a fallback when a capability
    record carries apd_goal but no apd_tier (a schema-non-conformance found in
    caldera/authentik fixtures)."""
    if not goal:
        return None
    for tier, goals in TIER_GOALS.items():
        if goal in goals:
            return tier
    return None


def capability_grid(artifacts: RunArtifacts) -> list[dict[str, Any]]:
    """Map every deduped capability to the template's flat cap-grid entry shape.

    Schema-tolerance: when a capability record lacks ``apd_goal`` (caldera fixture),
    fall back to its ``agent`` field which carries the lens name. When it lacks
    ``apd_tier`` (caldera + authentik fixtures), derive it from the goal via
    ``_goal_to_tier`` rather than emitting None and collapsing the tier dimension.
    """
    out: list[dict[str, Any]] = []
    for c in artifacts.deduped_capabilities:
        goal = c.get("apd_goal") or c.get("agent")
        tier = c.get("apd_tier") or _goal_to_tier(goal)
        entry: dict[str, Any] = {
            "id":       c.get("id"),
            "tier":     tier,
            "goal":     goal,
            "maturity": c.get("maturity", "implemented"),
            "title":    c.get("title", ""),
            "scope":    c.get("scope", ""),
        }
        lp_raw = c.get("lens_perspectives")
        is_merged = c.get("id", "").startswith("cap-merged") or bool(c.get("merged") or lp_raw)
        if is_merged and lp_raw:
            entry["merged"] = True
            # lens_perspectives may be a dict (key=lens name, value=dict with source_id)
            # or a list of dicts with an apd_goal/goal field. Either way, the
            # cross_lens entry must carry APD goals, not lens names: the dict
            # shape extracts apd_goal/goal from the VALUES so it matches the
            # list-shape semantics. None goals are filtered out so the rendered
            # list stays clean.
            if isinstance(lp_raw, dict):
                cross_lens = [
                    v.get("apd_goal", v.get("goal"))
                    for v in lp_raw.values()
                    if isinstance(v, dict)
                ]
            else:
                cross_lens = [
                    lp.get("apd_goal", lp.get("goal"))
                    for lp in lp_raw
                    if isinstance(lp, dict)
                ]
            cross_lens = [g for g in cross_lens if g]
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
    warnings: list[dict[str, str]] | None = None,
) -> list[dict[str, Any]]:
    """Map deduped findings + attack-path findings to the template's flat array.

    Headline rank: if supplement is supplied, use it (silently dropping ids that
    don't match a finding). Otherwise compute algorithmically (top-10 by severity
    desc, confidence desc, id asc).

    ``warnings`` is an optional aggregator list threaded into
    ``_extract_ids_from_mapping`` calls so soft mapping issues (id-missing
    name-only entries, completely shapeless dicts) surface as structured
    ``data.meta.warnings`` records instead of being silently dropped.
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
                "nist":      _normalize_nist_ids(_extract_ids_from_mapping(
                    (f.get("control_mappings") or {}).get("nist_800_53r5"),
                    warnings=warnings,
                )),
                "attack":    _extract_ids_from_mapping(
                    (f.get("control_mappings") or {}).get("mitre_attack"),
                    "technique",
                    warnings=warnings,
                ),
                "cwe":       _extract_ids_from_mapping(
                    (f.get("control_mappings") or {}).get("cwe"),
                    warnings=warnings,
                ),
                "owasp_api": _extract_ids_from_mapping(
                    (f.get("control_mappings") or {}).get("owasp_api_top10"),
                    warnings=warnings,
                ),
                "owasp":     _extract_ids_from_mapping(
                    (f.get("control_mappings") or {}).get("owasp_top10"),
                    warnings=warnings,
                ),
                "d3fend":    _extract_ids_from_mapping(
                    (f.get("control_mappings") or {}).get("d3fend"),
                    warnings=warnings,
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
    warnings: list[dict[str, str]] | None = None,
) -> list[dict[str, Any]]:
    """Join supplied strengths (id + caveats) with capability titles.

    Unknown capability ids used to raise ``ValueError`` here. As of PR-T4-D
    they are normalized to a warn-and-skip contract that matches sibling
    supplements (``headline_findings``, ``next_steps``): the unknown entry is
    dropped and a structured record is appended to the optional ``warnings``
    list. Callers that want to surface the warning should pass the shared
    list owned by :func:`build_apd_data` (it lands in ``data.meta.warnings``).

    Backwards-compatible: when ``warnings`` is omitted the function still
    silently skips unknown ids — matching the existing behaviour of the
    sibling supplement helpers when their callers do not capture warnings.
    """
    if not supplied_strengths:
        return []
    by_id = {c.get("id"): c for c in artifacts.deduped_capabilities}
    out: list[dict[str, Any]] = []
    for s in supplied_strengths:
        cid = s.get("id")
        cap = by_id.get(cid)
        if cap is None:
            if warnings is not None:
                warnings.append({
                    "section": "strengths",
                    "issue":   "unknown_capability_id",
                    "id":      cid if isinstance(cid, str) and cid else "(missing)",
                })
            continue
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
    result: dict[str, str] = _json.loads(
        (_PKG_DATA / "nist-families.json").read_text(encoding="utf-8")
    )
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
    """Return {control_id: {cap_id, ...}} for all capabilities with NIST mappings.

    Control IDs are normalised to canonical form (e.g. 'ac-3' → 'AC-3') so the
    index matches exactly against the normalised IDs used by the family
    cross-walk; non-canonical IDs are dropped rather than emitted as junk keys.
    """
    index: dict[str, set[str]] = {}
    for cap in capabilities:
        cap_id = cap.get("id", "")
        cm = cap.get("control_mappings") or {}
        nist_controls = cm.get("nist_800_53r5") or []
        for ctrl in _normalize_nist_ids(_extract_ids_from_mapping(nist_controls)):
            # Strip enhancements to base control for family derivation, but keep
            # the full control id in the index so we match exact keys.
            index.setdefault(ctrl, set()).add(cap_id)
    return index


def _build_cap_attack_index(capabilities: list[dict[str, Any]]) -> dict[str, set[str]]:
    """Return {attack_id: {cap_id, ...}} for all capabilities with MITRE ATT&CK mappings."""
    index: dict[str, set[str]] = {}
    for cap in capabilities:
        cap_id = cap.get("id", "")
        cm = cap.get("control_mappings") or {}
        for tech in _extract_ids_from_mapping(cm.get("mitre_attack"), "technique"):
            index.setdefault(tech, set()).add(cap_id)
    return index


def _nist_family_of(control_id: str) -> str:
    """Return the NIST family prefix of a control id (e.g., 'AC-2(2)' → 'AC')."""
    return control_id.split("-", 1)[0] if "-" in control_id else control_id


_NIST_ID_CANONICAL = re.compile(r"[A-Z]{2,3}-\d+(\([\dA-Z]+\))?")


def _normalize_nist_id(raw: str | None) -> str | None:
    """Normalise a NIST 800-53r5 control id to canonical form.

    Uppercases, strips whitespace, and validates the result has the
    canonical 'FAM-N' or 'FAM-N(N)' shape. Returns None for input
    that cannot be normalised so callers can drop the entry rather
    than emit junk.

    Canonical pattern: 2-3 letter family prefix, dash, digits, optional
    parenthesised enhancement. Examples: AC-3, AC-2(13), SC-7(5).
    """
    if not isinstance(raw, str):
        return None
    norm = raw.strip().upper()
    if not norm:
        return None
    if not _NIST_ID_CANONICAL.fullmatch(norm):
        return None
    return norm


def _normalize_nist_ids(ids: list[str]) -> list[str]:
    """Apply ``_normalize_nist_id`` to a list of raw ids, dropping invalid entries.

    Preserves order; deduplication is not performed here (call sites that need
    deduped output already use set semantics)."""
    return [n for n in (_normalize_nist_id(x) for x in ids) if n]


def _family_row(
    fam: str,
    titles: dict[str, str],
    family_controls: dict[str, list[str]],
    cap_controls: dict[str, set[str]],
) -> dict[str, Any]:
    """Build a NIST rollup row from a per-family {control_id: [finding_ids]} map and
    a {control_id: {cap_ids}} index. Used by both the coverage_by_family branch
    and the caldera control_to_findings branch.
    """
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
    return {
        "family":  fam,
        "title":   titles.get(fam, fam),
        "covered": covered,
        "gapped":  gapped,
        "both":    both,
        "notable": _notable_for_family_new(fam, family_controls),
    }


def nist_rollup_rows(artifacts: RunArtifacts) -> list[dict[str, Any]]:
    """Return rows for the NIST coverage table: one per family with counts +
    notable one-liner. Order: descending by (covered + gapped + both).

    Tolerates four synthesizer output shapes (plus a Shape-A variant):

    Shape A — ``family_summary`` + ``control`` list (chainguard-era):
      Uses the pre-computed counts and posture fields directly.

    Shape A' — flat ``control`` / ``controls`` list of dicts (canonical example):
      No ``family_summary`` pre-computation; each entry is a dict carrying
      ``id``, ``family``, ``posture``, and ``finding_count`` /
      ``capability_count``. Family counts are derived from the per-control
      ``posture`` field. Treated as a degraded Shape A.

    Shape B — ``coverage_by_family`` (crAPI-era):
      Per-family {control_id: [finding_ids]} dict. Cross-walks capabilities
      via ``deduped_capabilities[].control_mappings.nist_800_53r5`` to derive
      covered/gapped/both counts.

    Shape C — ``controls`` map (authentik-era):
      Per-control dict with explicit ``findings:`` and ``capabilities:`` lists.
      Counts read directly; no cross-walk needed.

    Shape D — ``control_to_findings`` map (caldera-era):
      Flat {control_id: [finding_ids]} dict (no family grouping). Family is
      derived from control_id prefix; capability presence comes from
      ``_build_cap_controls_index``.

    Posture semantics (B/C/D):
      - covered: controls with ≥1 capability but 0 findings
      - gapped:  controls with ≥1 finding but 0 capabilities
      - both:    controls with both findings and ≥1 capability
    """
    family_summary = artifacts.nist_coverage.get("family_summary") or {}
    # Accept both singular ``control`` (chainguard) and plural ``controls``
    # (canonical example) — but ONLY when ``controls`` is a list, not a dict.
    # The plural ``controls`` MAY also be a {control_id: data} map (authentik
    # Shape C); that is handled by the dedicated ``controls_map`` branch below.
    raw_controls = artifacts.nist_coverage.get("controls")
    if isinstance(raw_controls, list):
        control_list = list(raw_controls)
        controls_map = None
    else:
        control_list = list(artifacts.nist_coverage.get("control") or [])
        controls_map = raw_controls if isinstance(raw_controls, dict) else None
    titles = _nist_family_titles()
    rows: list[dict[str, Any]] = []

    coverage_by_family = artifacts.nist_coverage.get("coverage_by_family")
    control_to_findings = artifacts.nist_coverage.get("control_to_findings")

    if family_summary:
        # Shape A — pre-computed family_summary.
        for fam, summary in sorted(family_summary.items()):
            rows.append({
                "family":  fam,
                "title":   titles.get(fam, fam),
                "covered": summary.get("covered", 0),
                "gapped":  summary.get("gapped", 0),
                "both":    summary.get("gapped_and_covered", 0),
                "notable": _notable_for_family(fam, control_list),
            })
    elif control_list:
        # Shape A' — flat list of control dicts (canonical example). Derive
        # family counts from per-control ``posture``.
        family_counts: dict[str, dict[str, int]] = {}
        for c in control_list:
            if not isinstance(c, dict):
                continue
            fam = c.get("family") or _nist_family_of(str(c.get("id") or ""))
            if not fam:
                continue
            posture = c.get("posture") or "silent"
            bucket = family_counts.setdefault(
                fam, {"covered": 0, "gapped": 0, "both": 0},
            )
            if posture == "gapped_and_covered":
                bucket["both"] += 1
            elif posture in bucket:
                bucket[posture] += 1
        for fam in sorted(family_counts.keys()):
            counts = family_counts[fam]
            rows.append({
                "family":  fam,
                "title":   titles.get(fam, fam),
                "covered": counts["covered"],
                "gapped":  counts["gapped"],
                "both":    counts["both"],
                "notable": _notable_for_family(fam, control_list),
            })
    elif coverage_by_family:
        # Shape B.
        cap_controls = _build_cap_controls_index(artifacts.deduped_capabilities)
        for fam in sorted(coverage_by_family.keys()):
            family_controls: dict[str, list[str]] = coverage_by_family[fam] or {}
            rows.append(_family_row(fam, titles, family_controls, cap_controls))
    elif controls_map:
        # Shape C — authentik. Group by family; counts come from the per-control
        # explicit findings/capabilities lists.
        family_to_controls: dict[str, dict[str, list[str]]] = {}
        cap_presence: dict[str, set[str]] = {}
        for ctrl_id, ctrl_data in controls_map.items():
            if not isinstance(ctrl_data, dict):
                continue
            fam = _nist_family_of(ctrl_id)
            findings = list(ctrl_data.get("findings") or [])
            caps = list(ctrl_data.get("capabilities") or [])
            family_to_controls.setdefault(fam, {})[ctrl_id] = findings
            if caps:
                cap_presence[ctrl_id] = set(caps)
        for fam in sorted(family_to_controls.keys()):
            rows.append(_family_row(
                fam, titles, family_to_controls[fam], cap_presence,
            ))
    elif control_to_findings:
        # Shape D — caldera. Group the flat control map by family, then
        # cross-walk capabilities for has_caps.
        cap_controls = _build_cap_controls_index(artifacts.deduped_capabilities)
        family_to_controls_d: dict[str, dict[str, list[str]]] = {}
        for ctrl_id, finding_ids in control_to_findings.items():
            fam = _nist_family_of(ctrl_id)
            family_to_controls_d.setdefault(fam, {})[ctrl_id] = list(finding_ids or [])
        for fam in sorted(family_to_controls_d.keys()):
            rows.append(_family_row(
                fam, titles, family_to_controls_d[fam], cap_controls,
            ))

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
      - 'covered'   if mitigations present and findings count == 0
      - 'partial'   if both findings and mitigations are present

    Tolerates four synthesizer output shapes:

    Shape A — ``technique`` (singular) list (chainguard-era):
      Each entry has ``id``, ``name``, ``exposure_finding_count``,
      ``mitigated_by_capabilities`` (list of dicts with ``capability_id``).

    Shape B — ``techniques`` (plural) dict (crAPI- and authentik-era):
      Top-level entries may have ``citing_findings`` / ``countering_capabilities``
      (crAPI) or ``findings`` / ``capabilities_with_mitigation`` (authentik) — we
      accept either pair. Sub-techniques nested under ``sub_techniques``.

    Shape C — ``technique_to_findings`` dict (caldera-era):
      Each entry has ``description``, ``tactic``, ``findings`` and optional
      ``sub_techniques`` (a list of IDs, not nested dicts). Mitigations are
      derived by cross-walking ``deduped_capabilities`` ATT&CK mappings.
    """
    rows: list[dict[str, Any]] = []

    technique_list = artifacts.attack_exposure.get("technique")
    # Accept ``techniques`` as plural-form Shape-A list (canonical example)
    # in addition to its established Shape-B dict form.
    raw_techniques = artifacts.attack_exposure.get("techniques")
    if technique_list is None and isinstance(raw_techniques, list):
        technique_list = raw_techniques
        techniques_dict = None
    else:
        techniques_dict = raw_techniques if isinstance(raw_techniques, dict) else None
    technique_to_findings = artifacts.attack_exposure.get("technique_to_findings")

    if technique_list is not None:
        # Shape A — list of per-technique dicts.
        for t in technique_list:
            if not isinstance(t, dict):
                continue
            mits: list[str] = []
            for m in (t.get("mitigated_by_capabilities") or []):
                if isinstance(m, dict):
                    cap_id = m.get("capability_id")
                    if isinstance(cap_id, str) and cap_id:
                        mits.append(cap_id)
            findings = t.get("exposure_finding_count", 0)
            rows.append({
                "id":          t.get("id"),
                "name":        t.get("name", ""),
                "findings":    findings,
                "mitigations": mits,
                "coverage":    _attack_coverage_label(mits, findings),
                "note":        "",
            })
    elif techniques_dict is not None:
        # Shape B — handles both crAPI key names and authentik key names.
        for tech_id in sorted(techniques_dict.keys()):
            entry = techniques_dict[tech_id]
            if not isinstance(entry, dict):
                continue
            sub_techniques = entry.get("sub_techniques") or {}
            parent_findings = entry.get("citing_findings")
            if parent_findings is None:
                parent_findings = entry.get("findings")

            # Distinguish a finding-bearing parent from a grouping-only parent:
            #   - parent_findings truthy (non-empty list) → emit a row.
            #   - parent_findings is [] AND sub_techniques present → parent is
            #     a grouping node; skip its row and let the sub-technique loop
            #     below emit the individual technique rows.
            #   - parent_findings is None AND no sub_techniques → nothing to
            #     emit (the entry carries no actionable data).
            #   - parent_findings is None AND sub_techniques present → same;
            #     defer to the sub-technique loop.
            if parent_findings:
                mits = list(
                    entry.get("countering_capabilities")
                    or entry.get("capabilities_with_mitigation")
                    or []
                )
                findings = len(parent_findings)
                rows.append({
                    "id":          tech_id,
                    "name":        entry.get("name", ""),
                    "findings":    findings,
                    "mitigations": mits,
                    "coverage":    _attack_coverage_label(mits, findings),
                    "note":        str(entry.get("notes", "") or ""),
                })
            # sub_techniques may be a dict (crAPI) — emit per-sub rows. authentik's
            # sub-technique rows appear as top-level keys (e.g., "T1110.002"),
            # which we'll catch in the outer sort already.
            if isinstance(sub_techniques, dict):
                for sub_id in sorted(sub_techniques.keys()):
                    sub = sub_techniques[sub_id]
                    if not isinstance(sub, dict):
                        continue
                    mits = list(
                        sub.get("countering_capabilities")
                        or sub.get("capabilities_with_mitigation")
                        or []
                    )
                    sub_findings = sub.get("citing_findings")
                    if sub_findings is None:
                        sub_findings = sub.get("findings") or []
                    findings = len(sub_findings)
                    rows.append({
                        "id":          sub_id,
                        "name":        sub.get("name", ""),
                        "findings":    findings,
                        "mitigations": mits,
                        "coverage":    _attack_coverage_label(mits, findings),
                        "note":        str(sub.get("notes", "") or ""),
                    })
    elif technique_to_findings is not None:
        # Shape C — caldera. Mitigations come from capability ATT&CK cross-walk.
        cap_attack = _build_cap_attack_index(artifacts.deduped_capabilities)
        for tech_id in sorted(technique_to_findings.keys()):
            entry = technique_to_findings[tech_id]
            if not isinstance(entry, dict):
                continue
            findings = len(entry.get("findings") or [])
            mits = sorted(cap_attack.get(tech_id, set()))
            rows.append({
                "id":          tech_id,
                "name":        entry.get("description", "") or "",
                "findings":    findings,
                "mitigations": mits,
                "coverage":    _attack_coverage_label(mits, findings),
                "note":        "",
            })
            # Caldera sub_techniques is a list of IDs — emit each as its own
            # row with no parent-supplied name. Findings/mitigations are
            # derived from the cap index only (no per-sub finding bucket
            # exists in this shape, so findings=0 by construction).
            for sub_id in (entry.get("sub_techniques") or []):
                if not isinstance(sub_id, str):
                    continue
                sub_mits = sorted(cap_attack.get(sub_id, set()))
                rows.append({
                    "id":          sub_id,
                    "name":        "",
                    "findings":    0,
                    "mitigations": sub_mits,
                    "coverage":    _attack_coverage_label(sub_mits, 0),
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


def _posture(has_findings: bool, has_caps: bool) -> str:
    if has_findings and has_caps:
        return "both"
    if has_findings:
        return "gapped"
    if has_caps:
        return "covered"
    return "silent"


def _matrix_rows_from_dedup(
    artifacts: RunArtifacts,
    goal_has_caps: dict[str, bool] | None = None,
) -> list[dict[str, Any]]:
    """Synthesise (component, goal) rows by reading deduped findings + caps
    directly. Used for the caldera ``matrix`` shape (which only carries counts)
    and as a graceful default when no recognized matrix shape is present.

    ``goal_has_caps`` may be pre-supplied; otherwise it's derived from
    deduped_capabilities.apd_goal.
    """
    all_findings = artifacts.deduped_findings + artifacts.attack_path_findings

    if goal_has_caps is None:
        goal_has_caps = {}
        for c in artifacts.deduped_capabilities:
            g = c.get("apd_goal")
            if g:
                goal_has_caps[g] = True

    # artifact_label → set of goals with findings under it.
    artifact_goal_findings: dict[str, set[str]] = {}
    for f in all_findings:
        g = f.get("apd_goal")
        if not g:
            continue
        label = _artifact_label(f)
        artifact_goal_findings.setdefault(label, set()).add(g)

    rows: list[dict[str, Any]] = []
    for artifact_name in sorted(artifact_goal_findings.keys()):
        goals_with_findings = artifact_goal_findings[artifact_name]
        cells: dict[str, str] = {}
        for full_goal, short in _GOAL_SHORT.items():
            cells[short] = _posture(
                full_goal in goals_with_findings,
                goal_has_caps.get(full_goal, False),
            )
        rows.append({"component": artifact_name, "cells": cells})
    return rows


def apd_matrix(artifacts: RunArtifacts) -> dict[str, Any]:
    """Return the data.apd_matrix block: goals[], goalLabels{}, rows[{component, cells}].

    Tolerates four synthesizer output shapes:

    Shape A — ``component`` list (chainguard-era):
      Each component entry has ``name`` and ``cells`` keyed by full goal name,
      each cell containing ``findings``, ``capabilities``, and ``posture``.

    Shape B — ``coverage`` goal-keyed dict (crAPI-era):
      Per-goal tier-keyed finding ID lists + ``capabilities`` list. Rows
      synthesised by grouping findings under each goal by their
      ``evidence[0].artifact`` (component-by-artifact).

    Shape C — ``goals`` goal-keyed dict (authentik-era):
      Per-goal explicit ``findings: [{id, severity, disposition}]`` +
      ``capabilities: [{id, maturity}]`` lists. Component rows synthesised the
      same way as shape B.

    Shape D — ``matrix`` goal-keyed counts (caldera-era):
      Only per-goal totals + per-taxonomy counts; no finding IDs. Falls back
      to deriving rows from deduped findings/capabilities directly.

    Posture per (component, goal) cell:
      - ``'both'``    findings present and goal has capabilities
      - ``'gapped'``  findings present but no capabilities under the goal
      - ``'covered'`` no findings for this component but capabilities exist
      - ``'silent'``  otherwise
    """
    goals = list(_GOAL_LABEL_SHORT.keys())
    rows: list[dict[str, Any]] = []

    # Accept either singular ``component`` or plural ``components`` as the
    # Shape-A container. The plural key is used by the canonical example.
    component_list = (
        artifacts.apd_coverage_matrix.get("component")
        or artifacts.apd_coverage_matrix.get("components")
    )
    coverage = artifacts.apd_coverage_matrix.get("coverage")
    goals_map = artifacts.apd_coverage_matrix.get("goals")
    matrix_map = artifacts.apd_coverage_matrix.get("matrix")

    if component_list is not None:
        # Shape A — list of {name, cells} entries.
        for comp in component_list:
            # Guard against shorthand authoring (e.g. ``components: [svc-a]``
            # as a list of bare strings) so a single bad entry does not abort
            # the whole render.
            if not isinstance(comp, dict):
                continue
            cells_in = comp.get("cells") or {}
            cells_out: dict[str, str] = {}
            for full_goal, short in _GOAL_SHORT.items():
                cell = cells_in.get(full_goal) or {}
                posture = cell.get("posture", "silent")
                cells_out[short] = _POSTURE_TO_CELL.get(posture, "silent")
            rows.append({"component": comp.get("name", ""), "cells": cells_out})
    elif coverage is not None:
        # Shape B — synthesise rows from goal-keyed tier-bucketed finding ID lists.
        all_findings = artifacts.deduped_findings + artifacts.attack_path_findings
        finding_by_id: dict[str, dict[str, Any]] = {
            f["id"]: f for f in all_findings if f.get("id")
        }

        tier_keys = ("critical", "high", "medium", "low", "informational",
                     "blocked", "uncertainty")

        all_artifacts: set[str] = set()
        for full_goal in _GOAL_SHORT:
            goal_data = coverage.get(full_goal) or {}
            for tier_key in tier_keys:
                for fid in (goal_data.get(tier_key) or []):
                    f = finding_by_id.get(fid)
                    if f:
                        all_artifacts.add(_artifact_label(f))

        for artifact_name in sorted(all_artifacts):
            row_cells: dict[str, str] = {}
            for full_goal, short in _GOAL_SHORT.items():
                goal_data = coverage.get(full_goal) or {}
                has_caps = bool(goal_data.get("capabilities"))
                goal_finding_ids: list[str] = []
                for tier_key in tier_keys:
                    for fid in (goal_data.get(tier_key) or []):
                        f = finding_by_id.get(fid)
                        label = _artifact_label(f) if f else "(unattributed)"
                        if label == artifact_name:
                            goal_finding_ids.append(fid)
                row_cells[short] = _posture(
                    bool(goal_finding_ids), has_caps,
                )
            rows.append({"component": artifact_name, "cells": row_cells})
    elif goals_map is not None:
        # Shape C — authentik. Goal entries carry explicit finding {id,...} lists.
        all_findings_c = artifacts.deduped_findings + artifacts.attack_path_findings
        finding_by_id_c: dict[str, dict[str, Any]] = {
            f["id"]: f for f in all_findings_c if f.get("id")
        }

        # Per goal: artifact_label → list of finding ids.
        goal_to_artifact: dict[str, set[str]] = {}
        goal_has_caps_c: dict[str, bool] = {}
        all_artifacts_c: set[str] = set()
        for full_goal in _GOAL_SHORT:
            goal_data = goals_map.get(full_goal) or {}
            goal_has_caps_c[full_goal] = bool(goal_data.get("capabilities"))
            per_goal_artifacts: set[str] = set()
            for f_rec in (goal_data.get("findings") or []):
                fid = f_rec.get("id") if isinstance(f_rec, dict) else None
                f = finding_by_id_c.get(fid) if fid else None
                label = _artifact_label(f) if f else "(unattributed)"
                per_goal_artifacts.add(label)
                all_artifacts_c.add(label)
            goal_to_artifact[full_goal] = per_goal_artifacts

        for artifact_name in sorted(all_artifacts_c):
            cells: dict[str, str] = {}
            for full_goal, short in _GOAL_SHORT.items():
                cells[short] = _posture(
                    artifact_name in goal_to_artifact.get(full_goal, set()),
                    goal_has_caps_c.get(full_goal, False),
                )
            rows.append({"component": artifact_name, "cells": cells})
    elif matrix_map is not None:
        # Shape D — caldera. The ``matrix`` map carries only totals, so derive
        # the per-component rows from deduped findings directly. Goal capability
        # presence is signalled by ``capabilities_total > 0`` in matrix_map when
        # available; otherwise fall back to deduped_capabilities.apd_goal.
        goal_has_caps_d: dict[str, bool] = {}
        for full_goal in _GOAL_SHORT:
            entry = matrix_map.get(full_goal) or {}
            if "capabilities_total" in entry:
                goal_has_caps_d[full_goal] = (entry.get("capabilities_total") or 0) > 0
        # Fill remaining gaps from deduped_capabilities.
        for c in artifacts.deduped_capabilities:
            g = c.get("apd_goal")
            if g and g not in goal_has_caps_d:
                goal_has_caps_d[g] = True
        rows = _matrix_rows_from_dedup(artifacts, goal_has_caps=goal_has_caps_d)

    return {
        "goals":      goals,
        "goalLabels": _GOAL_LABEL_SHORT,
        "rows":       rows,
    }


_NODE_ID_OK = re.compile(r"^[A-Za-z0-9_\-./:]+$")
_LABEL_STRIP = re.compile(r"[^A-Za-z0-9 _./:()-]")
# HTML tag pattern: reject the entire label if angle-bracket tags are present.
_HTML_TAG = re.compile(r"<[^>]*>")

# Tighter than the full-graph 100-cap because path-focused subgraphs are meant
# to be human-readable storytelling artifacts, not exhaustive inventories.
_PATH_FOCUSED_NODE_CAP = 60


def _safe_node_id(raw: str, fallback_seed: str = "") -> str:
    """Return a Mermaid-safe node id. When raw is invalid, derive a stable
    hash-based id so two nodes with distinct raw ids cannot collide on the
    synthetic fallback. The optional fallback_seed namespaces ids across
    rendering contexts (full asset graph vs path-focused subgraph)."""
    if _NODE_ID_OK.match(raw or ""):
        return raw
    digest = hashlib.sha256(((raw or "") + "::" + fallback_seed).encode("utf-8")).hexdigest()
    return f"n_{digest[:8]}"


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
        safe_id = _safe_node_id(raw_id, fallback_seed="asset_graph")
        existing = next((r for r, s in id_remap.items() if s == safe_id), None)
        if existing is not None and existing != raw_id:
            raise RuntimeError(
                f"_safe_node_id collision: {existing!r} and {raw_id!r} both → {safe_id!r}"
            )
        id_remap[raw_id] = safe_id
        label = _safe_label(str(n.get("name") or raw_id))
        ntype = n.get("node_type", "")
        prefix = {
            "attacker_position": "((", "crown_jewel": "{{", "service": "[",
            "data_store": "[(", "secret_store": "[(",
            "identity": ">",
        }.get(ntype, "[")
        suffix = {"((": "))", "{{": "}}", "[": "]", "[(": ")]", ">": "]"}[prefix]
        lines.append(f"  {safe_id}{prefix}\"{label}\"{suffix}")
    for e in edges:
        src = id_remap.get(str(e.get("from", "")))
        dst = id_remap.get(str(e.get("to", "")))
        if src and dst:
            lines.append(f"  {src} --> {dst}")
    return "\n".join(lines)


def _build_mermaid_path_focused(
    asset_graph: dict[str, Any],
    paths: list[dict[str, Any]],
) -> str | None:
    """Build a focused Mermaid graph LR showing only nodes/edges in enumerated paths.

    Returns None when ``paths`` is empty (nothing to focus on).

    The focused subgraph:
    - Uses ``graph LR`` so attacker → ... → crown_jewel reads left-to-right.
    - Includes only nodes touched by path edges.
    - Includes only edges that appear in enumerated paths.
    - Labels edges with the edge_type short label for context.
    """
    if not paths:
        return None

    raw_nodes: list[dict[str, Any]] = asset_graph.get("nodes") or []
    raw_edges: list[dict[str, Any]] = asset_graph.get("edges") or []

    node_by_id: dict[str, dict[str, Any]] = {
        str(n.get("node_id", "")): n for n in raw_nodes if isinstance(n, dict)
    }
    edge_by_id: dict[str, dict[str, Any]] = {
        str(e.get("edge_id", "")): e for e in raw_edges if isinstance(e, dict)
    }

    # Collect the edge IDs referenced by all paths.
    path_edge_ids: list[str] = []
    seen_edge_ids: set[str] = set()
    for p in paths:
        for eid in (p.get("edges") or []):
            if eid not in seen_edge_ids:
                path_edge_ids.append(eid)
                seen_edge_ids.add(eid)

    # Collect node IDs touched by those edges.
    touched_node_ids: set[str] = set()
    for eid in path_edge_ids:
        e = edge_by_id.get(eid, {})
        touched_node_ids.add(str(e.get("from", "")))
        touched_node_ids.add(str(e.get("to", "")))
    touched_node_ids.discard("")

    if not touched_node_ids:
        return None

    if len(touched_node_ids) > _PATH_FOCUSED_NODE_CAP:
        return (
            f"graph LR\n  too_large[\"Path-focused subgraph has "
            f"{len(touched_node_ids)} nodes; see attack-paths.yaml\"]"
        )

    # Edge type → short label for edge annotation.
    _EDGE_LABEL: dict[str, str] = {
        "compromisable_via_finding": "finding",
        "finding": "finding",
        "mitigated_by_capability": "capability",
        "capability": "capability",
        "trust_boundary": "trust",
        "trusts": "trust",
    }

    lines = ["graph LR"]

    # Emit only the touched nodes, preserving node_type shapes.
    id_remap: dict[str, str] = {}
    for raw_id in sorted(touched_node_ids):
        n = node_by_id.get(raw_id, {})
        safe_id = _safe_node_id(raw_id, fallback_seed="path_focused")
        existing = next((r for r, s in id_remap.items() if s == safe_id), None)
        if existing is not None and existing != raw_id:
            raise RuntimeError(
                f"_safe_node_id collision: {existing!r} and {raw_id!r} both → {safe_id!r}"
            )
        id_remap[raw_id] = safe_id
        label = _safe_label(str(n.get("name") or raw_id))
        ntype = n.get("node_type", "")
        prefix = {
            "attacker_position": "((",
            "crown_jewel": "{{",
            "service": "[",
            "data_store": "[(",
            "secret_store": "[(",
            "identity": ">",
        }.get(ntype, "[")
        suffix = {"((": "))", "{{": "}}", "[": "]", "[(": ")]", ">": "]"}[prefix]
        lines.append(f"  {safe_id}{prefix}\"{label}\"{suffix}")

    # Emit only path edges, annotated with edge_type label.
    for eid in path_edge_ids:
        e = edge_by_id.get(eid, {})
        src_raw = str(e.get("from", ""))
        dst_raw = str(e.get("to", ""))
        src = id_remap.get(src_raw)
        dst = id_remap.get(dst_raw)
        if src and dst:
            raw_type = str(e.get("edge_type", ""))
            edge_label = _EDGE_LABEL.get(raw_type, raw_type or "edge")
            lines.append(f"  {src} -->|{edge_label}| {dst}")

    return "\n".join(lines)


def attack_paths_data(artifacts: RunArtifacts) -> dict[str, Any] | None:
    """Return the data.attack_paths block, or None when v1.4 artifacts are absent."""
    if artifacts.attack_paths is None or artifacts.asset_graph is None:
        return None
    paths = artifacts.attack_paths.get("paths") or []

    # Build lookup maps for nodes and edges.
    raw_nodes = artifacts.asset_graph.get("nodes") or []
    raw_edges = artifacts.asset_graph.get("edges") or []
    node_by_id: dict[str, dict[str, Any]] = {
        str(n.get("node_id", "")): n for n in raw_nodes if isinstance(n, dict)
    }
    edge_by_id: dict[str, dict[str, Any]] = {
        str(e.get("edge_id", "")): e for e in raw_edges if isinstance(e, dict)
    }

    def _node_name(node_id: str) -> str:
        node = node_by_id.get(node_id)
        if node:
            return str(node.get("name") or node_id)
        return node_id

    def _edges_detailed(
        edge_ids: list[str],
        bottleneck_edge_ids: list[str],
    ) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        bottleneck_set = set(bottleneck_edge_ids)
        for eid in edge_ids:
            e = edge_by_id.get(eid, {})
            from_id = str(e.get("from", ""))
            to_id = str(e.get("to", ""))
            raw_type = str(e.get("edge_type", ""))
            # Normalise edge_type to the three canonical values.
            if raw_type == "trusts":
                edge_type = "trust_boundary"
            elif raw_type in ("compromisable_via_finding", "finding"):
                edge_type = "compromisable_via_finding"
            elif raw_type in ("mitigated_by_capability", "capability"):
                edge_type = "mitigated_by_capability"
            else:
                edge_type = raw_type or "trust_boundary"
            out.append({
                "edge_id":       eid,
                "from_id":       from_id,
                "from_name":     _node_name(from_id),
                "to_id":         to_id,
                "to_name":       _node_name(to_id),
                "edge_type":     edge_type,
                "finding_id":    (
                    e.get("finding_id") if edge_type == "compromisable_via_finding" else None
                ),
                "capability_id": (
                    e.get("capability_id") if edge_type == "mitigated_by_capability" else None
                ),
                "confidence":    str(e.get("confidence", "")),
                "is_bottleneck": eid in bottleneck_set,
            })
        return out

    # Group paths by (attacker_position, crown_jewel).
    pairs_by_key: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for p in paths:
        key = (p.get("attacker_position", ""), p.get("crown_jewel", ""))
        edge_ids = p.get("edges", [])
        bottleneck_ids = p.get("bottleneck_edges", [])
        pairs_by_key.setdefault(key, []).append({
            "path_id":          p.get("path_id"),
            "hop_count":        p.get("hop_count"),
            "feasibility":      p.get("feasibility"),
            "severity_sum":     p.get("severity_sum"),
            "mitigation_count": p.get("mitigation_count"),
            "edges":            edge_ids,
            "bottleneck_edges": bottleneck_ids,
            "edges_detailed":   _edges_detailed(edge_ids, bottleneck_ids),
        })
    pairs = [
        {
            "attacker_position":      k[0],
            "attacker_position_name": _node_name(k[0]),
            "crown_jewel":            k[1],
            "crown_jewel_name":       _node_name(k[1]),
            "paths":                  v,
        }
        for k, v in sorted(pairs_by_key.items())
    ]

    overlays: list[Any] = []
    if artifacts.defense_graph is not None:
        overlays = artifacts.defense_graph.get("bottleneck_overlays") or []

    # Pull bottleneck_threshold from enumeration_parameters.
    enum_params = artifacts.attack_paths.get("enumeration_parameters") or {}
    bottleneck_threshold: int | None = enum_params.get("bottleneck_threshold")

    # Compute max_edge_traversal_count: max number of paths that include any single edge.
    edge_path_counts: dict[str, int] = {}
    for p in paths:
        for eid in (p.get("edges") or []):
            edge_path_counts[eid] = edge_path_counts.get(eid, 0) + 1
    max_edge_traversal_count: int = max(edge_path_counts.values(), default=0)

    # Build asset_graph_summary with full breakdown.
    node_type_counts: dict[str, int] = {}
    for n in raw_nodes:
        ntype = str(n.get("node_type", "other"))
        node_type_counts[ntype] = node_type_counts.get(ntype, 0) + 1

    edge_type_counts: dict[str, int] = {}
    for e in raw_edges:
        raw_type = str(e.get("edge_type", ""))
        if raw_type == "trusts":
            cat = "trust_boundary"
        elif raw_type in ("compromisable_via_finding", "finding"):
            cat = "finding_derived"
        elif raw_type in ("mitigated_by_capability", "capability"):
            cat = "capability_derived"
        else:
            cat = "other"
        edge_type_counts[cat] = edge_type_counts.get(cat, 0) + 1

    node_count = len(raw_nodes)
    edge_count = len(raw_edges)

    asset_graph_summary: dict[str, Any] = {
        "node_count":               node_count,
        "edge_count":               edge_count,
        "attacker_position_count":  node_type_counts.get("attacker_position", 0),
        "crown_jewel_count":        node_type_counts.get("crown_jewel", 0),
        "asset_count":              node_type_counts.get("asset", 0),
        "identity_count":           node_type_counts.get("identity", 0),
        "trust_boundary_edge_count":    edge_type_counts.get("trust_boundary", 0),
        "finding_derived_edge_count":   edge_type_counts.get("finding_derived", 0),
        "capability_derived_edge_count": edge_type_counts.get("capability_derived", 0),
    }

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
        "mermaid_path_focused": _build_mermaid_path_focused(artifacts.asset_graph, paths),
        "pairs":   pairs,
        "bottleneck_overlays": overlays,
        "bottleneck_threshold": bottleneck_threshold,
        "max_edge_traversal_count": max_edge_traversal_count,
        "summary": {
            "total_paths":  len(paths),
            "total_pairs":  len(pairs),
            "bottleneck_count": (
                len(overlays)
                if artifacts.defense_graph is not None else 0
            ),
        },
        "asset_graph_summary": asset_graph_summary,
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
    """Assemble the full ``window.APD_DATA`` dict from a ``RunArtifacts``.

    Per-section isolation: each top-level section call runs inside a try/except.
    If a section transformer raises, the section is filled with a safe
    placeholder (empty list / dict / None) and the failure is recorded in
    ``data["meta"]["section_errors"]`` as ``{section_name: "ErrType: message"}``.
    One bad finding, one corrupt asset graph, or one misshapen capability
    cannot block the entire report — the orchestrator either completes with
    section_errors populated, or raises ``ReportBuildError`` when the meta
    layer itself cannot be assembled (a fatal authoring problem).
    """
    supplement = artifacts.report_data or {}
    section_errors: dict[str, str] = {}
    # Shared aggregator threaded into transformers that surface soft warnings:
    # unknown ids in supplements (T4-D), name-fallback usage in mappings (T4-C),
    # findings_with_unknown_goal (T4-E). Appended in-place by callees and
    # copied onto out["meta"]["warnings"] at the end. Additive to
    # section_errors; warnings never imply the section failed.
    warnings: list[dict[str, str]] = []
    out: dict[str, Any] = {"meta": meta_block(artifacts, run_dir=run_dir)}

    # Per-section work units. Each tuple is ``(name, thunk, placeholder)``.
    # The thunks capture artifacts/supplement by closure so the loop body
    # stays uniform. Placeholder shapes match what the React template expects
    # when a section is empty (an empty list for the array sections, an empty
    # dict for the keyed sections, ``None`` for ``attack_paths`` which the
    # template treats as "v1.4 artifacts absent").
    sections: list[tuple[str, Any, Any]] = [
        ("summary",
         lambda: summary_rollup(artifacts),
         {}),
        ("exec_summary",
         lambda: (supplement.get("exec_summary") or {}).get(
             "paragraphs", ["Run summary not provided by synthesizer."],
         ),
         ["Run summary not provided by synthesizer."]),
        ("posture_summary",
         lambda: posture_summary_section(supplement.get("posture_summary")),
         {}),
        ("capabilities",
         lambda: capability_grid(artifacts),
         []),
        ("strengths",
         lambda: strengths_section(
             artifacts,
             supplied_strengths=supplement.get("strengths"),
             warnings=warnings,
         ),
         []),
        ("findings",
         lambda: findings_array(
             artifacts,
             headline_supplement=supplement.get("headline_findings"),
             warnings=warnings,
         ),
         []),
        ("contradictions",
         lambda: contradictions_section(artifacts),
         []),
        ("severity_disagreements",
         lambda: severity_disagreements_section(artifacts),
         []),
        ("nist_rollup",
         lambda: nist_rollup_rows(artifacts),
         []),
        ("attack_exposure",
         lambda: attack_exposure_rows(artifacts),
         []),
        ("apd_matrix",
         lambda: apd_matrix(artifacts),
         {"goals": [], "goalLabels": {}, "rows": []}),
        ("attack_paths",
         lambda: attack_paths_data(artifacts),
         None),
        ("next_steps",
         lambda: next_steps_section(supplement.get("next_steps")),
         []),
        ("taxonomy",
         lambda: taxonomy_dict(artifacts),
         {}),
    ]

    # Passthrough fields are spliced in right after their related section to
    # preserve the field ordering callers (golden tests, downstream consumers)
    # expect from data.js. They come straight off the RunArtifacts so they
    # cannot fail at this layer (loader-level failures bubble up before we
    # reach build_apd_data).
    passthrough_after: dict[str, list[tuple[str, Any]]] = {
        "contradictions": [
            ("contradictions_notes", artifacts.contradictions_notes),
        ],
        "severity_disagreements": [
            ("severity_disagreements_notes", artifacts.severity_disagreements_notes),
        ],
    }

    for name, thunk, placeholder in sections:
        try:
            value = thunk()
        except Exception as exc:  # noqa: BLE001 — wide catch is the point
            value = placeholder
            section_errors[name] = f"{type(exc).__name__}: {exc}"
        out[name] = value
        for pt_name, pt_value in passthrough_after.get(name, ()):
            out[pt_name] = pt_value

    out["meta"]["section_errors"] = section_errors
    out["meta"]["warnings"] = warnings
    return out


# ---------------------------------------------------------------------------
# Taxonomy hover dictionary
# ---------------------------------------------------------------------------

_NIST_FAMILY_DISPLAY = "NIST 800-53r5"
_ATTACK_FAMILY_DISPLAY = "MITRE ATT&CK"
_CWE_FAMILY_DISPLAY = "CWE"
_D3FEND_FAMILY_DISPLAY = "MITRE D3FEND"


def _extract_ids_from_mapping(
    raw: Any,
    *fallback_keys: str,
    warnings: list[dict[str, str]] | None = None,
) -> list[str]:
    """Extract string IDs from a control-mapping field that may be:

    - A list of strings: ["ID1", "ID2"]
    - A list of dicts: [{"id": "ID1", ...}, {"technique": "T1040", ...}, ...]
    - None / missing → []

    ``fallback_keys`` is the ordered list of dict keys to try when "id" is absent.
    E.g. for mitre_attack: fallback_keys=("technique",)

    ``warnings`` is an optional aggregator list. When supplied:
    - Dict items lacking ``id`` and every fallback key but carrying a usable
      ``name`` string emit ``{"issue": "mapping_id_missing_using_name",
      "name": <name>}`` and the name is appended as a last-resort label so
      partial signal is not silently dropped.
    - Dict items lacking ``id``, every fallback key, AND any usable name emit
      ``{"issue": "mapping_item_no_id_no_name", "shape": <comma-joined sorted
      dict keys>}`` and the item is skipped.

    When ``warnings`` is ``None`` (the default for existing callers) the
    last-resort name fallback still fires silently — backwards-compatible
    callers continue to recover partial signal without observing structured
    warnings. Dict items with no name and no id are skipped, matching prior
    behaviour.
    """
    if not raw:
        return []
    ids: list[str] = []
    for item in raw:
        if isinstance(item, str):
            ids.append(item)
            continue
        if not isinstance(item, dict):
            continue
        # Try "id" first, then each fallback key in order.
        found = item.get("id")
        if not found:
            for key in fallback_keys:
                found = item.get(key)
                if found:
                    break
        if not found:
            # Last-resort: emit the human-readable name so partial signal is
            # not silently lost. Aggregate a structured warning when caller
            # supplied the warnings list.
            name = item.get("name")
            if isinstance(name, str) and name:
                if warnings is not None:
                    warnings.append({
                        "issue": "mapping_id_missing_using_name",
                        "name":  name,
                    })
                ids.append(name)
                continue
            if warnings is not None:
                warnings.append({
                    "issue": "mapping_item_no_id_no_name",
                    "shape": ",".join(sorted(item.keys())),
                })
            continue
        if isinstance(found, str):
            ids.append(found)
    return ids


def _collect_referenced_ids(
    artifacts: RunArtifacts,
    *,
    warnings: list[dict[str, str]] | None = None,
) -> dict[str, set[str]]:
    """Return {family: {ids}} across all findings + capabilities + coverage rows.

    ``warnings`` is an optional aggregator threaded into the underlying
    ``_extract_ids_from_mapping`` calls so soft mapping issues surface in
    ``data.meta.warnings`` rather than being silently dropped.
    """
    out: dict[str, set[str]] = {
        "nist": set(), "attack": set(), "cwe": set(), "d3fend": set(),
    }
    for rec in artifacts.deduped_findings + artifacts.attack_path_findings:
        cm = rec.get("control_mappings") or {}
        # nist_800_53r5 may be a list of bare ID strings OR a list of dicts
        # per apd-control-mappings discipline. Use the helper for both.
        out["nist"].update(
            _normalize_nist_ids(_extract_ids_from_mapping(
                cm.get("nist_800_53r5"), warnings=warnings,
            ))
        )
        out["attack"].update(_extract_ids_from_mapping(
            cm.get("mitre_attack"), "technique", warnings=warnings,
        ))
        out["cwe"].update(_extract_ids_from_mapping(
            cm.get("cwe"), warnings=warnings,
        ))
        out["d3fend"].update(_extract_ids_from_mapping(
            cm.get("d3fend"), warnings=warnings,
        ))
    for rec in artifacts.deduped_capabilities:
        cm = rec.get("control_mappings") or {}
        out["nist"].update(
            _normalize_nist_ids(_extract_ids_from_mapping(
                cm.get("nist_800_53r5"), warnings=warnings,
            ))
        )
        out["attack"].update(_extract_ids_from_mapping(
            cm.get("mitre_attack"), "technique", warnings=warnings,
        ))
        out["cwe"].update(_extract_ids_from_mapping(
            cm.get("cwe"), warnings=warnings,
        ))
        out["d3fend"].update(_extract_ids_from_mapping(
            cm.get("d3fend"), warnings=warnings,
        ))
    # Coverage rollups — handle all four shapes. Every NIST id is normalised
    # at ingest so 'ac-3' and 'AC-3' collapse to one taxonomy entry and junk
    # ids (e.g. 'AC2(2)' missing the dash) are dropped rather than rendered.
    # Shape A: nist_coverage has a "control" / "controls" list with id fields.
    for c in (artifacts.nist_coverage.get("control")
              or (artifacts.nist_coverage.get("controls")
                  if isinstance(artifacts.nist_coverage.get("controls"), list)
                  else None)
              or []):
        if isinstance(c, dict):
            norm = _normalize_nist_id(c.get("id"))
            if norm:
                out["nist"].add(norm)
    # Shape B: nist_coverage has "coverage_by_family" dict.
    for _fam, fam_controls in (artifacts.nist_coverage.get("coverage_by_family") or {}).items():
        if isinstance(fam_controls, dict):
            out["nist"].update(_normalize_nist_ids(list(fam_controls.keys())))
    # Shape C: nist_coverage has "controls" map (authentik) — dict form only;
    # the list form is handled by the Shape-A branch above.
    raw_ctrls = artifacts.nist_coverage.get("controls")
    if isinstance(raw_ctrls, dict):
        out["nist"].update(_normalize_nist_ids(list(raw_ctrls.keys())))
    # Shape D: nist_coverage has "control_to_findings" flat dict (caldera).
    out["nist"].update(_normalize_nist_ids(
        list((artifacts.nist_coverage.get("control_to_findings") or {}).keys())
    ))

    # Shape A: attack_exposure has a "technique" / "techniques" list with id fields.
    raw_techs = artifacts.attack_exposure.get("technique")
    if raw_techs is None and isinstance(artifacts.attack_exposure.get("techniques"), list):
        raw_techs = artifacts.attack_exposure.get("techniques")
    for t in raw_techs or []:
        if isinstance(t, dict):
            out["attack"].add(t.get("id", ""))
    # Shape B: attack_exposure has "techniques" dict (with optional sub_techniques
    # nested as a dict for crAPI). Authentik-era sub-techniques are top-level keys.
    raw_techs_dict = artifacts.attack_exposure.get("techniques")
    if isinstance(raw_techs_dict, dict):
        for tech_id, entry in raw_techs_dict.items():
            out["attack"].add(tech_id)
            if isinstance(entry, dict):
                subs = entry.get("sub_techniques") or {}
                if isinstance(subs, dict):
                    for sub_id in subs:
                        out["attack"].add(sub_id)
    # Shape C: attack_exposure has "technique_to_findings" dict (caldera).
    # Caldera sub_techniques is a list of IDs, not nested dicts.
    for tech_id, entry in (artifacts.attack_exposure.get("technique_to_findings") or {}).items():
        out["attack"].add(tech_id)
        if isinstance(entry, dict):
            for sub_id in (entry.get("sub_techniques") or []):
                if isinstance(sub_id, str):
                    out["attack"].add(sub_id)
    return out


def taxonomy_dict(artifacts: RunArtifacts) -> dict[str, dict[str, str]]:
    """Return {id: {family, title}} for every taxonomy ID referenced in the run.

    Only IDs actually present in findings, capabilities, or coverage rollups are
    included — this keeps data.js small for runs with large reference databases.
    """
    refs = _collect_referenced_ids(artifacts)
    out: dict[str, dict[str, str]] = {}

    # NIST 800-53r5: titles come from the nist-coverage artifact when present
    # (Shape A inline title), otherwise fall back to the bundled OSCAL catalog.
    # Keys are normalised so a Shape-A 'ac-3' inline title still resolves the
    # canonical 'AC-3' lookup emitted by ``_collect_referenced_ids``.
    inline_titles: dict[str, str] = {}
    for c in (artifacts.nist_coverage.get("control") or []):
        if not isinstance(c, dict):
            continue
        norm = _normalize_nist_id(c.get("id"))
        if norm:
            inline_titles[norm] = c.get("title", "")
    catalog_titles = _taxonomy.nist_control_titles()
    for cid in sorted(refs["nist"]):
        if not cid:
            continue
        title = inline_titles.get(cid) or catalog_titles.get(cid, cid)
        out[cid] = {
            "family": _NIST_FAMILY_DISPLAY,
            "title":  title,
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
