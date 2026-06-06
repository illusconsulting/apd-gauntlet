"""5c apply-clusters — mechanically apply cluster-decisions.yaml.

Builds the authoritative deduped-findings.yaml / deduped-capabilities.yaml
(bare singular-root-key lists; no generated_at so output is reproducible),
plus severity-disagreements.yaml, contradictions.yaml, and
rejected-records.yaml. Raises AdjudicationMissing (mirrors
attack_path.BuilderBlocked) when the decisions file is absent or malformed so
the workflow can fall back to the synthesizer.

Contradictions (C5/I3): the adjudicator JUDGES finding-vs-capability conflicts
in cluster-decisions.yaml's ``contradictions`` block (with a ``classification``:
compatible|contradicted|stale). apply-clusters is the MECHANICAL PRODUCER of
40-synthesis/contradictions.yaml — it strips the adjudicator's ``classification``
(an adjudicator-only field, NOT part of the on-disk contradiction.schema.json
row) and emits a ``contra-<sha8>`` id + the per-row shape that the existing
schemas/contradiction.schema.json and validate.run_cross_file_pass enforce.

Stale-capability downgrade (I4): for each adjudicator contradiction classified
``stale``, the named capability's maturity is downgraded ONE notch via
_MATURITY_RANK and a ``stale_capability_downgrade`` record is logged to
rejected-records.yaml — implementing design §7.1-5c's "downgrades stale
capabilities".
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from .loader import load_corpus

_SEV_RANK = {"critical": 0, "high": 1, "medium": 2, "low": 3, "informational": 4}
_MATURITY_RANK = {"designed": 0, "implemented": 1, "tested": 2, "operationalized": 3}
_MATURITY_BY_RANK = {v: k for k, v in _MATURITY_RANK.items()}


class AdjudicationMissing(Exception):
    """Raised when cluster-decisions.yaml is absent or malformed."""


@dataclass
class ApplyResult:
    findings: list[dict[str, Any]] = field(default_factory=list)
    capabilities: list[dict[str, Any]] = field(default_factory=list)
    severity_disagreements: list[dict[str, Any]] = field(default_factory=list)
    contradictions: list[dict[str, Any]] = field(default_factory=list)
    rejected: list[dict[str, Any]] = field(default_factory=list)


def _sha8(title: str, first_locator: str) -> str:
    return hashlib.sha256(f"{title}|{first_locator}".encode()).hexdigest()[:8]


def _downgrade_maturity(current: str) -> str | None:
    """Return the maturity one notch below ``current`` (None if already lowest)."""
    rank = _MATURITY_RANK.get(current)
    if rank is None or rank == 0:
        return None
    return _MATURITY_BY_RANK[rank - 1]


def _first_locator(rec: dict[str, Any]) -> str:
    ev = rec.get("evidence") or []
    if ev and isinstance(ev[0], dict):
        return str(ev[0].get("locator", ""))
    return ""


def _max_severity(records: list[dict[str, Any]]) -> str:
    sevs = [str(r.get("severity", "informational")) for r in records]
    return min(sevs, key=lambda s: _SEV_RANK.get(s, 9))


def _sorted_union(records: list[dict[str, Any]], path: tuple[str, ...]) -> list[str]:
    out: set[str] = set()
    for r in records:
        node: Any = r
        for key in path:
            node = (node or {}).get(key) if isinstance(node, dict) else None
        for item in node or []:
            if isinstance(item, str):
                out.add(item)
    return sorted(out)


def _union_attack(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: dict[str, dict[str, Any]] = {}
    for r in records:
        for m in (r.get("control_mappings") or {}).get("mitre_attack") or []:
            if isinstance(m, dict) and m.get("technique"):
                seen.setdefault(m["technique"], m)
    return [seen[k] for k in sorted(seen)]


def _load_decisions(run_dir: Path) -> dict[str, Any]:
    path = run_dir / "40-synthesis" / "cluster-decisions.yaml"
    if not path.is_file():
        raise AdjudicationMissing(f"cluster-decisions.yaml absent at {path}")
    try:
        doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise AdjudicationMissing(f"cluster-decisions.yaml malformed: {exc}") from exc
    if not isinstance(doc, dict) or "decisions" not in doc:
        raise AdjudicationMissing("cluster-decisions.yaml missing 'decisions'")
    return doc


def _members_for(doc: dict[str, Any], decision: dict[str, Any]) -> list[str]:
    """Resolve the member ids for a decision.

    The adjudicator carries member ids in the optional ``_members`` map keyed by
    group_id (mirrors cluster-candidates.yaml group membership). Tests and the
    workflow supply it; if absent for a merge, the decision is treated as a
    rejected record rather than silently dropped.
    """
    return list((doc.get("_members") or {}).get(decision.get("group_id"), []))


def apply_clusters(run_dir: Path) -> ApplyResult:
    doc = _load_decisions(run_dir)
    # F4: apply-clusters runs BEFORE tier-4 (tmeval/apath). Exclude the tier-4
    # corpus so a stale 40-synthesis/attack-path.findings.yaml or
    # 40-threat-model/threat-model.findings.yaml left by a prior partial run is
    # NOT folded into deduped-findings.yaml on a recovery re-run. apath-*/tmeval-*
    # are unioned downstream by the rollup (_load_deduped) and the report loader,
    # so including them here would only risk double-rendering them.
    findings_by_id, capabilities = load_corpus(run_dir, include_attack_path=False)
    caps_by_id = {c["id"]: c for c in capabilities if "id" in c}

    result = ApplyResult()
    consumed: set[str] = set()
    cross_refs: dict[str, list[str]] = {}

    for decision in doc.get("decisions") or []:
        disp = decision.get("disposition")
        members = _members_for(doc, decision)
        if disp == "merge":
            sources = [findings_by_id[m] for m in members if m in findings_by_id]
            if len(sources) < 2:
                for m in members:
                    result.rejected.append({
                        "id": m, "category": "failed_validation",
                        "reason": "merge member not found in corpus during apply-clusters",
                    })
                group_id = decision.get("group_id", "unknown")
                result.rejected.append({
                    "id": group_id, "category": "failed_validation",
                    "reason": (
                        f"merge group {group_id} had fewer than 2 resolvable members; skipped"
                    ),
                })
                continue
            consumed.update(members)
            title = decision.get("merged_title", "")
            # primary = sorted-first member by id, so the merged record is deterministic
            # regardless of _members list order.
            primary = sorted(sources, key=lambda r: r["id"])[0]
            first_locator = _first_locator(primary)
            cluster_max = _max_severity(sources)
            chosen = decision.get("chosen_severity")
            severity = chosen or cluster_max
            evidence: list[dict[str, Any]] = []
            for s in sorted(sources, key=lambda r: r["id"]):
                for ev in s.get("evidence") or []:
                    if ev not in evidence:
                        evidence.append(ev)
            merged = {
                "schema_version": 1,
                "id": "merged-" + _sha8(title, first_locator),
                "agent": "synthesizer",
                "apd_tier": primary.get("apd_tier"),
                "apd_goal": primary.get("apd_goal"),
                "disposition": "gap",
                "severity": severity,
                # Merged confidence = HIGHEST of sources: a gap confirmed by any confident lens
                # is itself confident (deliberate; no golden impact).
                "confidence": min(
                    (s.get("confidence", "low") for s in sources),
                    key=lambda c: {"high": 0, "medium": 1, "low": 2}.get(c, 9),
                ),
                "title": title,
                "summary": decision.get("merged_summary", ""),
                "detail": decision.get("merged_detail", ""),
                "evidence": evidence,
                "merged_from": sorted(members),
                "lens_perspectives": decision.get("lens_perspectives", {}),
                "control_mappings": {
                    "nist_800_53r5": _sorted_union(
                        sources, ("control_mappings", "nist_800_53r5")
                    ),
                },
                "recommendation": decision.get("merged_recommendation", {}),
            }
            attack = _union_attack(sources)
            if attack:
                merged["control_mappings"]["mitre_attack"] = attack
            related = sorted({c for s in sources for c in (s.get("related_concerns") or [])})
            if related:
                merged["related_concerns"] = related
            result.findings.append(merged)
            # Emit a severity-disagreement when lens severities differ OR the
            # adjudicator elevated above the cluster max.
            lens_sevs = {s.get("apd_goal"): s.get("severity") for s in sources}
            if len(set(lens_sevs.values())) > 1 or (chosen and chosen != cluster_max):
                # severity-disagreement.schema.json requires rationale minLength
                # 30; the >=30-char default fires only when the adjudicator
                # omitted a rationale (rare — it supplies one on any elevation).
                result.severity_disagreements.append({
                    "finding_id": merged["id"],
                    "agent_severities": lens_sevs,
                    "chosen_severity": severity,
                    "rationale": decision.get("severity_rationale")
                    or "Highest-severity-wins across the merged lens severities; "
                       "no adjudicator rationale was supplied for this cluster.",
                })
        elif disp == "link":
            for link in decision.get("links") or []:
                a, b = link.get("from"), link.get("to")
                if a and b:
                    cross_refs.setdefault(a, []).append(b)
                    cross_refs.setdefault(b, []).append(a)
        # separate: no-op; both records flow through unchanged below.

    # Emit all non-consumed findings unchanged (tier order then id within tier),
    # attaching reciprocal cross_references for linked records.
    for rec in _ordered_records(findings_by_id):
        if rec["id"] in consumed:
            continue
        out = dict(rec)
        refs = sorted(set(cross_refs.get(rec["id"], [])))
        if refs:
            out["cross_references"] = sorted(set(out.get("cross_references", [])) | set(refs))
        result.findings.append(out)

    # Contradictions (C5/I3) + stale-capability downgrade (I4).
    # The adjudicator's contradiction rows carry a ``classification`` that is an
    # adjudicator-only field; the on-disk contradiction.schema.json row does NOT
    # include it, so it is stripped here. The id is a deterministic
    # ``contra-<sha8(finding_id|capability_id)>`` so output is reproducible.
    caps_by_id = {c["id"]: dict(c) for c in caps_by_id.values()}  # mutable copies
    for raw in doc.get("contradictions") or []:
        fid = raw.get("finding_id")
        cid = raw.get("capability_id")
        if not fid or not cid:
            continue
        contra_id = "contra-" + hashlib.sha256(f"{fid}|{cid}".encode()).hexdigest()[:8]
        result.contradictions.append({
            "id": contra_id,
            "finding_id": fid,
            "capability_id": cid,
            "finding_assertion": raw.get("finding_assertion", ""),
            "capability_assertion": raw.get("capability_assertion", ""),
            "evidence_comparison": raw.get("evidence_comparison", ""),
            "recommended_resolution": raw.get("recommended_resolution", ""),
        })
        # I4: stale → downgrade the named capability one maturity notch.
        if raw.get("classification") == "stale" and cid in caps_by_id:
            cap = caps_by_id[cid]
            current = cap.get("maturity", "implemented")
            new_maturity = _downgrade_maturity(current)
            if new_maturity is not None:
                cap["maturity"] = new_maturity
                result.rejected.append({
                    "id": cid,
                    "category": "stale_capability_downgrade",
                    "reason": (raw.get("recommended_resolution")
                               or "Adjudicator classified the capability as stale "
                                  "relative to the finding evidence."),
                    "from_maturity": current,
                    "to_maturity": new_maturity,
                })

    result.capabilities = list(caps_by_id.values())

    _write_outputs(run_dir, result)
    return result


_TIER_ORDER = {"trustworthiness": 0, "scalability": 1, "auditability": 2}


def _ordered_records(by_id: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        by_id.values(),
        key=lambda r: (_TIER_ORDER.get(r.get("apd_tier", ""), 9), r["id"]),
    )


def _write_outputs(run_dir: Path, result: ApplyResult) -> None:
    synth = run_dir / "40-synthesis"
    synth.mkdir(parents=True, exist_ok=True)
    # Merged records sort last (id starts 'merged-'); keep tier order for the rest.
    findings_sorted = sorted(
        result.findings,
        key=lambda r: (
            0 if r["id"].startswith("merged-") else -1,
            _TIER_ORDER.get(r.get("apd_tier", ""), 9),
            r["id"],
        ),
    )
    (synth / "deduped-findings.yaml").write_text(
        yaml.safe_dump({"finding": findings_sorted}, sort_keys=False), encoding="utf-8")
    (synth / "deduped-capabilities.yaml").write_text(
        yaml.safe_dump({"capability": sorted(result.capabilities, key=lambda c: c.get("id", ""))},
                       sort_keys=False), encoding="utf-8")
    (synth / "severity-disagreements.yaml").write_text(
        yaml.safe_dump({"severity_disagreements": sorted(
            result.severity_disagreements, key=lambda r: r["finding_id"])}, sort_keys=False),
        encoding="utf-8")
    # C5/I3: apply-clusters is the producer of contradictions.yaml. Bare
    # {contradictions: [...]} per-row shape, matching the EXISTING
    # contradiction.schema.json + validate.run_cross_file_pass cross-ref.
    (synth / "contradictions.yaml").write_text(
        yaml.safe_dump({"contradictions": sorted(
            result.contradictions, key=lambda r: r["id"])}, sort_keys=False),
        encoding="utf-8")
    (synth / "rejected-records.yaml").write_text(
        yaml.safe_dump({"schema_version": 1, "generated_by": "synthesizer",
                        "rejected": sorted(result.rejected, key=lambda r: r["id"])},
                       sort_keys=False), encoding="utf-8")
