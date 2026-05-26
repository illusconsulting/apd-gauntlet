"""Bounded DFS path enumeration with edge-set pruning.

Given a graph and (attacker, crown_jewel) pair, walks every distinct
acyclic path (cycles prevented by visited-edge-set, not visited-node-set —
so parallel edges between same nodes are valid alternate paths) up to
``max_hop`` depth. Sorts by ``(-severity_sum, hop_count, -feasibility_rank,
path_id)`` and truncates at ``max_paths_per_pair``.

Pure module: no I/O, no global state. Deterministic across runs given
identical inputs.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any, Literal

from .graph import Confidence, Graph

_CONFIDENCE_RANK: dict[str, int] = {"low": 0, "medium": 1, "high": 2}
_SEVERITY_SCORE: dict[str, int] = {
    "critical": 4,
    "high": 3,
    "medium": 2,
    "low": 1,
    "informational": 0,
}


@dataclass(frozen=True)
class EnumerationParams:
    """Bounds on path enumeration.

    - ``max_hop``: maximum number of edges in any returned path.
    - ``max_paths_per_pair``: cap on returned paths per (attacker, jewel) pair.
    - ``bottleneck_threshold``: edges appearing on at least this many paths
      qualify as bottlenecks (consumed by :func:`compute_bottleneck_edges`).
    """

    max_hop: int
    max_paths_per_pair: int
    bottleneck_threshold: int


@dataclass(frozen=True)
class Path:
    """A single enumerated attack path with derived metadata."""

    path_id: str
    attacker_position: str
    crown_jewel: str
    edges: tuple[str, ...]
    hop_count: int
    feasibility: Literal["high", "medium", "low"]
    severity_sum: int
    mitigation_count: int


def enumerate_paths(
    g: Graph,
    attacker_node_id: str,
    crown_jewel_node_id: str,
    params: EnumerationParams,
    *,
    findings_by_id: dict[str, dict[str, Any]] | None = None,
) -> list[Path]:
    """DFS from attacker to jewel; emits all acyclic paths up to ``max_hop``.

    Acyclicity is enforced via a visited-edge-set (not visited-node-set), so
    parallel edges between the same pair of nodes are explored as alternate
    paths. Self-loops are skipped. Results are sorted by
    ``(-severity_sum, hop_count, -feasibility_rank, path_id)`` and truncated
    at ``params.max_paths_per_pair``.
    """
    findings = findings_by_id or {}
    collector: list[Path] = []
    _dfs(
        g,
        attacker_node_id,
        crown_jewel_node_id,
        params.max_hop,
        visited_edges=set(),
        trail=[],
        collector=collector,
        findings_by_id=findings,
        attacker=attacker_node_id,
        jewel=crown_jewel_node_id,
    )
    collector.sort(
        key=lambda p: (
            -p.severity_sum,
            p.hop_count,
            -_CONFIDENCE_RANK[p.feasibility],
            p.path_id,
        )
    )
    return collector[: params.max_paths_per_pair]


def _dfs(
    g: Graph,
    current: str,
    target: str,
    depth: int,
    *,
    visited_edges: set[str],
    trail: list[str],
    collector: list[Path],
    findings_by_id: dict[str, dict[str, Any]],
    attacker: str,
    jewel: str,
) -> None:
    if depth <= 0:
        return
    for edge in g.outgoing(current):
        if edge.edge_id in visited_edges:
            continue
        if edge.from_node == edge.to_node:
            # Self-loops are never valid attack steps.
            continue
        trail.append(edge.edge_id)
        visited_edges.add(edge.edge_id)
        if edge.to_node == target:
            collector.append(
                _finalize_path(g, attacker, jewel, tuple(trail), findings_by_id)
            )
        else:
            _dfs(
                g,
                edge.to_node,
                target,
                depth - 1,
                visited_edges=visited_edges,
                trail=trail,
                collector=collector,
                findings_by_id=findings_by_id,
                attacker=attacker,
                jewel=jewel,
            )
        trail.pop()
        visited_edges.discard(edge.edge_id)


def _finalize_path(
    g: Graph,
    attacker: str,
    jewel: str,
    edge_ids: tuple[str, ...],
    findings_by_id: dict[str, dict[str, Any]],
) -> Path:
    edges = [g.get_edge(eid) for eid in edge_ids]
    confidences: list[Confidence] = [e.confidence for e in edges]
    feasibility: Literal["high", "medium", "low"] = min(
        confidences, key=lambda c: _CONFIDENCE_RANK[c]
    )
    severity_sum = sum(
        _SEVERITY_SCORE.get(
            findings_by_id.get(e.finding_id or "", {}).get("severity", "informational"),
            0,
        )
        for e in edges
        if e.edge_type == "compromisable_via_finding"
    )
    mitigation_count = sum(
        1 for e in edges if e.edge_type == "mitigated_by_capability"
    )
    digest = hashlib.sha256("|".join(edge_ids).encode("utf-8")).hexdigest()[:8]
    return Path(
        path_id=f"path-{digest}",
        attacker_position=attacker,
        crown_jewel=jewel,
        edges=edge_ids,
        hop_count=len(edge_ids),
        feasibility=feasibility,
        severity_sum=severity_sum,
        mitigation_count=mitigation_count,
    )


def compute_bottleneck_edges(
    paths: list[Path], threshold: int
) -> dict[str, list[str]]:
    """Return ``{edge_id: [path_id, ...]}`` for edges on ``threshold`` or more paths.

    Edges appearing on fewer than ``threshold`` paths are filtered out.
    """
    counts: dict[str, list[str]] = {}
    for p in paths:
        for eid in p.edges:
            counts.setdefault(eid, []).append(p.path_id)
    return {eid: pids for eid, pids in counts.items() if len(pids) >= threshold}
