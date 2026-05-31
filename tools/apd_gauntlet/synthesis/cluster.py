"""5a cluster-candidates — mechanical signal detection + union-find grouping.

Detects three signals (NEVER shared control mappings — that over-groups):
  1. evidence_locator_overlap — two records cite the same (artifact, locator).
  2. title_similarity — token Jaccard >= 0.5 over normalised titles.
  3. related_concerns — reciprocal cross-goal related_concerns (A in lens X cites
     Y, B in lens Y cites X) AND a shared evidence artifact.

Groups via union-find over the signal graph, then bounds group size so the
adjudicator's context stays small. Findings and capabilities cluster separately.
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .coverage_logic import extract_ids_from_mapping, normalize_nist_ids
from .loader import load_corpus

_TOKEN_STOP = {
    "the", "a", "an", "of", "in", "on", "for", "and", "or", "to", "is", "no", "not", "with"
}
_TOKEN_RE = re.compile(r"[a-z0-9]+")


@dataclass
class CandidateResult:
    groups: list[dict[str, Any]] = field(default_factory=list)


def _title_tokens(title: str) -> set[str]:
    return {t for t in _TOKEN_RE.findall(title.lower()) if t not in _TOKEN_STOP and len(t) > 2}


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def _first_evidence(rec: dict[str, Any]) -> dict[str, str]:
    ev = rec.get("evidence") or []
    if ev and isinstance(ev[0], dict):
        return {
            "artifact": str(ev[0].get("artifact", "")),
            "locator": str(ev[0].get("locator", "")),
            "excerpt": str(ev[0].get("excerpt", "")),
        }
    return {"artifact": "", "locator": "", "excerpt": ""}


class _UnionFind:
    def __init__(self, items: list[str]) -> None:
        self.parent = {i: i for i in items}

    def find(self, x: str) -> str:
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def union(self, a: str, b: str) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.parent[max(ra, rb)] = min(ra, rb)


def _signals_between(r1: dict[str, Any], r2: dict[str, Any]) -> set[str]:
    sigs: set[str] = set()
    e1, e2 = _first_evidence(r1), _first_evidence(r2)
    shared_artifact = bool(e1["artifact"]) and e1["artifact"] == e2["artifact"]
    if shared_artifact and e1["locator"] and e1["locator"] == e2["locator"]:
        sigs.add("evidence_locator_overlap")
    if _jaccard(_title_tokens(r1.get("title", "")), _title_tokens(r2.get("title", ""))) >= 0.5:
        sigs.add("title_similarity")
    g1, g2 = r1.get("apd_goal"), r2.get("apd_goal")
    rc1 = set(r1.get("related_concerns") or [])
    rc2 = set(r2.get("related_concerns") or [])
    if g1 and g2 and g2 in rc1 and g1 in rc2 and shared_artifact:
        sigs.add("related_concerns")
    return sigs


def _member_view(rec: dict[str, Any]) -> dict[str, Any]:
    cm = rec.get("control_mappings") or {}
    return {
        "id": rec["id"],
        "agent": rec.get("agent", ""),
        "apd_goal": rec.get("apd_goal", ""),
        "severity": rec.get("severity", "informational"),
        "title": rec.get("title", ""),
        "summary": rec.get("summary", "") or rec.get("description", ""),
        "first_evidence": _first_evidence(rec),
        "related_concerns": list(rec.get("related_concerns") or []),
        "mapping_ids": {
            "nist": normalize_nist_ids(extract_ids_from_mapping(cm.get("nist_800_53r5"))),
            "attack": extract_ids_from_mapping(cm.get("mitre_attack"), "technique"),
        },
    }


def _group_records(
    records: list[dict[str, Any]], kind: str, max_group_size: int
) -> list[dict[str, Any]]:
    ids = [r["id"] for r in records]
    by_id = {r["id"]: r for r in records}
    uf = _UnionFind(ids)
    edge_signals: dict[tuple[str, str], set[str]] = {}
    for i in range(len(ids)):
        for j in range(i + 1, len(ids)):
            sigs = _signals_between(by_id[ids[i]], by_id[ids[j]])
            if sigs:
                uf.union(ids[i], ids[j])
                edge_signals[(ids[i], ids[j])] = sigs
    clusters: dict[str, list[str]] = {}
    for rid in ids:
        clusters.setdefault(uf.find(rid), []).append(rid)
    groups: list[dict[str, Any]] = []
    for root in sorted(clusters):
        members = sorted(clusters[root])
        if len(members) < 2:
            continue
        # Bound group size: split into deterministic even-distribution chunks so
        # no chunk exceeds max_group_size and no chunk is a singleton.
        n = len(members)
        if n <= max_group_size:
            chunks = [members]
        else:
            num_chunks = math.ceil(n / max_group_size)
            base, rem = divmod(n, num_chunks)
            chunks = []
            start = 0
            for i in range(num_chunks):
                size = base + (1 if i < rem else 0)
                chunks.append(members[start:start + size])
                start += size
        for chunk in chunks:
            chunk_set = set(chunk)
            chunk_sigs: set[str] = set()
            for (a, b), s in edge_signals.items():
                if a in chunk_set and b in chunk_set:
                    chunk_sigs |= s
            groups.append({
                "kind": kind,
                "signals": sorted(chunk_sigs) or ["title_similarity"],
                "members": [_member_view(by_id[m]) for m in chunk],
            })
    return groups


def build_candidates(run_dir: Path, *, max_group_size: int = 8) -> CandidateResult:
    """Detect candidate clusters across findings and (separately) capabilities."""
    findings_by_id, capabilities = load_corpus(run_dir, include_attack_path=True)
    finding_groups = _group_records(list(findings_by_id.values()), "finding", max_group_size)
    cap_groups = _group_records(capabilities, "capability", max_group_size)
    all_groups = finding_groups + cap_groups
    # Assign deterministic sequential group_ids after the records are ordered.
    for idx, g in enumerate(all_groups, start=1):
        g["group_id"] = f"cluster-cand-{idx:04x}"
    # Reorder keys: group_id first, then kind/signals/members.
    ordered = [
        {
            "group_id": g["group_id"],
            "kind": g["kind"],
            "signals": g["signals"],
            "members": g["members"],
        }
        for g in sorted(all_groups, key=lambda g: g["group_id"])
    ]
    return CandidateResult(groups=ordered)
