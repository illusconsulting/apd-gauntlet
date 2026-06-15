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
import re
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


class SerializationIntegrityError(Exception):
    """Raised when a schema-string field holds a non-str value or a value that
    matches a Python-repr signature (dict/list coerced to text) at the single
    emit point. Loud/blocking defense-in-depth so a poisoned record never
    reaches disk."""


@dataclass
class ApplyResult:
    findings: list[dict[str, Any]] = field(default_factory=list)
    capabilities: list[dict[str, Any]] = field(default_factory=list)
    severity_disagreements: list[dict[str, Any]] = field(default_factory=list)
    contradictions: list[dict[str, Any]] = field(default_factory=list)
    rejected: list[dict[str, Any]] = field(default_factory=list)
    # PR3: authored merge decisions that resolved to <2 members in EITHER index
    # (member ids absent, or a mixed finding+capability cluster). Non-blocking +
    # LOUD — the source records are still written to rejected-records.yaml; this
    # counter exists so the drop is countable rather than silent.
    unresolved_authored_merges: int = 0


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


def _max_maturity(records: list[dict[str, Any]]) -> str:
    """Return the HIGHEST maturity across ``records`` by _MATURITY_RANK.

    A capability confirmed at a higher maturity by any lens is itself at that
    maturity (mirrors the merged-finding "highest severity/confidence wins"
    rule). Falls back to ``implemented`` for unknown values.
    """
    ranks = [_MATURITY_RANK.get(str(r.get("maturity", "implemented")), 1) for r in records]
    return _MATURITY_BY_RANK[max(ranks)] if ranks else "implemented"


def _union_objs(
    records: list[dict[str, Any]], mapping_key: str, dedup_key: str
) -> list[dict[str, Any]]:
    """Union object-array control mappings (``mitre_attack_mitigations``,
    ``d3fend``) across sources, de-duped by ``dedup_key`` and sorted by it.
    Keeps the first source object per key so its rationale survives.
    """
    seen: dict[str, dict[str, Any]] = {}
    for r in sorted(records, key=lambda x: x["id"]):
        for item in (r.get("control_mappings") or {}).get(mapping_key) or []:
            if isinstance(item, dict) and item.get(dedup_key):
                seen.setdefault(item[dedup_key], item)
    return [seen[k] for k in sorted(seen)]


def _merge_capabilities(
    decision: dict[str, Any],
    c_src: list[dict[str, Any]],
    members: list[str],
    result: ApplyResult,
) -> dict[str, Any]:
    """Build ONE merged capability from a cross-lens CAPABILITY cluster.

    Mirrors the finding-merge contract but for the capability schema:
      * id   = "cap-merged-" + sha8(merged_title | primary first-locator)
      * primary = sorted-first source by id (deterministic regardless of order)
      * maturity = HIGHEST of sources (a capability confirmed at a higher level
        by any lens is itself at that level)
      * scope  = "; ".join of the unique, non-empty source scopes (the schema
        requires a non-empty scope string)
      * evidence = de-duped union over sources, sorted by id
      * control_mappings unions ONLY the capability-allowed keys.
    """
    primary = min(c_src, key=lambda r: r["id"])
    title = decision.get("merged_title", "")
    description = (
        decision.get("merged_summary")
        or decision.get("merged_detail")
        or primary.get("description", "")
    )
    # Unique, order-preserving (by source id) non-empty STRING scopes.
    # W0: a non-string scope is a schema violation (capability.schema.json
    # requires scope: string). Skip it and log a failed_validation reject row
    # instead of str()-coercing a dict into "{'components': ...}" repr-poison.
    scopes: list[str] = []
    for s in sorted(c_src, key=lambda r: r["id"]):
        raw_scope = s.get("scope", "")
        if not isinstance(raw_scope, str):
            result.rejected.append({
                "id": s.get("id", "unknown"),
                "category": "failed_validation",
                "reason": (
                    f"capability scope is {type(raw_scope).__name__}, not str; "
                    "skipped during capability merge to avoid repr-poisoning "
                    "(capability.schema.json requires scope: string)"
                ),
            })
            continue
        sc = raw_scope.strip()
        if sc and sc not in scopes:
            scopes.append(sc)
    scope = "; ".join(scopes)
    evidence: list[dict[str, Any]] = []
    for s in sorted(c_src, key=lambda r: r["id"]):
        for ev in s.get("evidence") or []:
            if ev not in evidence:
                evidence.append(ev)
    control_mappings: dict[str, Any] = {
        "nist_800_53r5": _sorted_union(c_src, ("control_mappings", "nist_800_53r5")),
    }
    attack = _union_attack(c_src)
    if attack:
        control_mappings["mitre_attack"] = attack
    # mitre_attack_mitigations + d3fend are object arrays keyed by id/technique;
    # union by that key, keeping the first source object so rationale survives.
    mits = _union_objs(c_src, "mitre_attack_mitigations", "id")
    if mits:
        control_mappings["mitre_attack_mitigations"] = mits
    d3 = _union_objs(c_src, "d3fend", "technique")
    if d3:
        control_mappings["d3fend"] = d3
    return {
        "schema_version": 1,
        "id": "cap-merged-" + _sha8(title, _first_locator(primary)),
        "agent": "synthesizer",
        "apd_tier": primary.get("apd_tier"),
        "apd_goal": primary.get("apd_goal"),
        "title": title,
        "description": description,
        "maturity": _max_maturity(c_src),
        "scope": scope,
        "evidence": evidence,
        "merged_from": sorted(members),
        "lens_perspectives": decision.get("lens_perspectives", {}),
        "control_mappings": control_mappings,
    }


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
    consumed_caps: set[str] = set()
    merged_caps: list[dict[str, Any]] = []
    cross_refs: dict[str, list[str]] = {}

    for decision in doc.get("decisions") or []:
        disp = decision.get("decision")
        members = _members_for(doc, decision)
        if disp == "merge":
            # PR3: resolve members against BOTH indexes so authored CAPABILITY
            # merges are no longer silently dropped (only findings_by_id was
            # consulted before, so every kind:capability cluster failed).
            f_src = [findings_by_id[m] for m in members if m in findings_by_id]
            c_src = [caps_by_id[m] for m in members if m in caps_by_id]
            if len(c_src) >= 2 and not f_src:
                # CAPABILITY merge.
                consumed_caps.update(members)
                merged_caps.append(_merge_capabilities(decision, c_src, members, result))
                continue
            if not (len(f_src) >= 2 and not c_src):
                # UNRESOLVED: mixed kinds, or <2 resolvable in either index.
                # Keep the existing reject rows AND make the drop countable
                # (non-blocking + loud — never raise).
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
                result.unresolved_authored_merges += 1
                continue
            # FINDING merge (logic unchanged below).
            sources = f_src
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
    # attaching reciprocal cross_references for linked records. A linked record
    # ALSO gets a ``linked_perspectives`` marker (the metric marker) so the
    # rollup can count linked clusters.
    for rec in _ordered_records(findings_by_id):
        if rec["id"] in consumed:
            continue
        out = dict(rec)
        refs = sorted(set(cross_refs.get(rec["id"], [])))
        if refs:
            out["cross_references"] = sorted(set(out.get("cross_references", [])) | set(refs))
            out["linked_perspectives"] = refs
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

    # Emit capabilities: (a) skip the ones consumed by a CAPABILITY merge,
    # (b) preserve the stale-downgrade mutations above, (c) attach reciprocal
    # cross_references + the linked_perspectives marker for linked caps,
    # (d) append the merged capabilities. Deterministic order (by id).
    emitted_caps: list[dict[str, Any]] = []
    for cid in sorted(caps_by_id):
        if cid in consumed_caps:
            continue
        cap = dict(caps_by_id[cid])
        refs = sorted(set(cross_refs.get(cid, [])))
        if refs:
            cap["cross_references"] = sorted(set(cap.get("cross_references", [])) | set(refs))
            cap["linked_perspectives"] = refs
        emitted_caps.append(cap)
    emitted_caps.extend(merged_caps)
    result.capabilities = emitted_caps

    _write_outputs(run_dir, result)
    return result


_TIER_ORDER = {"trustworthiness": 0, "scalability": 1, "auditability": 2}


def _ordered_records(by_id: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        by_id.values(),
        key=lambda r: (_TIER_ORDER.get(r.get("apd_tier", ""), 9), r["id"]),
    )


# Anchored Python-repr signature: a string whose entire value is a dict/list
# literal of strings (e.g. "{'components': ...}" or "['a', 'b']") — the
# fingerprint of a str()-coerced structured field. A quote is required right
# after the opening bracket so legitimate prose like "[N/A]" or "[redacted]" is
# NOT flagged; Python str() of a dict or list-of-strings always quotes its
# keys/elements, so real repr-poison is still caught.
_REPR_SIGNATURE = re.compile(r"^\s*[\{\[][\"'].*[\}\]]\s*$", re.DOTALL)

# Schema-string scalar fields per record kind that must never hold a non-str
# value or a repr signature. Kept narrow (the emitted-scalar fields) — nested
# object/array fields are guarded by the schema gate, not this string check.
_FINDING_STRING_FIELDS = ("title", "summary", "detail")
_CAPABILITY_STRING_FIELDS = ("title", "description", "scope")


def _repr_signature_check(records: list[dict[str, Any]], fields: tuple[str, ...]) -> None:
    """Raise SerializationIntegrityError if any named field on any record is a
    non-str or matches an anchored Python-repr signature."""
    for rec in records:
        rid = rec.get("id", "<no-id>")
        for fld in fields:
            if fld not in rec:
                continue
            val = rec[fld]
            if not isinstance(val, str):
                raise SerializationIntegrityError(
                    f"record {rid}: field '{fld}' is {type(val).__name__}, not str"
                )
            if _REPR_SIGNATURE.match(val):
                raise SerializationIntegrityError(
                    f"record {rid}: field '{fld}' matches a Python-repr signature "
                    f"(coerced structured value): {val[:80]!r}"
                )


def _write_outputs(run_dir: Path, result: ApplyResult) -> None:
    synth = run_dir / "40-synthesis"
    synth.mkdir(parents=True, exist_ok=True)
    # W0: pre-write integrity guard — never emit a repr-poisoned schema-string
    # field. Loud/blocking defense-in-depth around the type-respecting accessor.
    _repr_signature_check(result.findings, _FINDING_STRING_FIELDS)
    _repr_signature_check(result.capabilities, _CAPABILITY_STRING_FIELDS)
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
