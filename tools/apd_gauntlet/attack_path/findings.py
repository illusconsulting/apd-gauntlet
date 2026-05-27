"""Emit apath-* findings from enumeration results + D3FEND overlays.

Four flavors per design spec section 7.6:
  1. risk (severity critical|high) — high-feasibility path, no mitigation
  2. uncertainty — low-feasibility paths (capped at medium severity)
  3. gap — bottleneck edge with no D3FEND-backed capability
  4. blocked — emitted by the CLI/agent layer when BuilderBlocked is raised;
     this module does not need to emit blocked findings.

All emitted dicts conform to ``schemas/finding.schema.json``. The function
:func:`emit_findings` is keyword-only and returns a list sorted by ``id`` so
output is deterministic across runs.
"""

from __future__ import annotations

import hashlib
from typing import Any

from .enumerate import Path as APath
from .graph import Graph

_SEVERITY_FOR_RISK: dict[int, str] = {3: "high", 4: "critical", 5: "critical", 6: "critical"}
_UNCERTAINTY_SEVERITY = "low"
_TITLE_MAX = 200


def emit_findings(
    *,
    paths: list[APath],
    overlays: list[dict[str, Any]],
    graph: Graph,
    findings_by_id: dict[str, dict[str, Any]],
    capabilities: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Emit apath-* findings for enumerated paths and qualifying overlays.

    Yields one finding per path (risk or uncertainty disposition) and one
    additional finding per overlay whose ``net_new_d3fend`` is non-empty and
    whose ``existing_capability_backing`` is empty (gap disposition).

    The ``capabilities`` parameter is accepted for API symmetry with the
    analyze-attack-paths CLI; gap-finding eligibility is read directly from
    the overlay's pre-computed backing partitions.
    """
    del capabilities  # API symmetry; overlay carries pre-computed backing
    out: list[dict[str, Any]] = []
    for p in paths:
        out.append(_finding_from_path(p, graph, findings_by_id))
    for overlay in overlays:
        if overlay.get("net_new_d3fend") and not overlay.get("existing_capability_backing"):
            out.append(_finding_from_bottleneck(overlay, graph, findings_by_id))
    out.sort(key=lambda f: f["id"])
    return out


def _truncate_title(title: str) -> str:
    if len(title) <= _TITLE_MAX:
        return title
    return title[: _TITLE_MAX - 3] + "..."


def _finding_from_path(
    p: APath, g: Graph, findings_by_id: dict[str, dict[str, Any]]
) -> dict[str, Any]:
    low_feasibility = p.feasibility == "low"
    no_mitigation = p.mitigation_count == 0

    if low_feasibility:
        disposition = "uncertainty"
        severity = _UNCERTAINTY_SEVERITY
        confidence = "low"
        title_prefix = "Low-feasibility attack path"
    elif no_mitigation and p.severity_sum >= 3:
        disposition = "risk"
        severity = _SEVERITY_FOR_RISK.get(p.severity_sum, "high")
        confidence = p.feasibility
        title_prefix = "High-feasibility attack path with no capability coverage"
    else:
        disposition = "uncertainty"
        severity = "medium" if no_mitigation else "informational"
        confidence = p.feasibility
        title_prefix = "Attack path with partial mitigation"

    jewel_name = g.get_node(p.crown_jewel).name
    atk_name = g.get_node(p.attacker_position).name
    short_hash = hashlib.sha256(p.path_id.encode()).hexdigest()[:8]
    summary = (
        f"Path from {atk_name} to {jewel_name} in {p.hop_count} hop(s); "
        f"feasibility={p.feasibility}; severity_sum={p.severity_sum}; "
        f"mitigations on path={p.mitigation_count}."
    )

    detail_edges: list[str] = []
    for eid in p.edges:
        e = g.get_edge(eid)
        detail_edges.append(
            f"{g.get_node(e.from_node).name} --[{e.edge_type}/{e.confidence}]--> "
            f"{g.get_node(e.to_node).name}"
        )
    detail = (
        f"Path: {' -> '.join(detail_edges)}. "
        f"Feasibility floor = {p.feasibility}. "
        f"Severity sum = {p.severity_sum}. "
        f"Mitigations along path = {p.mitigation_count}."
    )

    cross_refs: list[str] = sorted({
        fid
        for fid in (
            g.get_edge(eid).finding_id
            for eid in p.edges
            if g.get_edge(eid).edge_type == "compromisable_via_finding"
        )
        if fid
    })

    title = _truncate_title(
        f"{title_prefix}: {atk_name} -> {jewel_name} in {p.hop_count} hop(s)"
    )

    return {
        "schema_version": 1,
        "id": f"apath-{short_hash}",
        "agent": "attack_path_analyzer",
        "apd_tier": _infer_tier(g, p, findings_by_id),
        "apd_goal": _infer_goal(g, p, findings_by_id),
        "disposition": disposition,
        "severity": severity,
        "confidence": confidence,
        "title": title,
        "summary": summary,
        "detail": detail,
        "evidence": [
            {
                "artifact": "40-synthesis/asset-graph.yaml",
                "locator": f"edges (path {p.path_id})",
                "excerpt": detail_edges[0] if detail_edges else "(no edges)",
            },
            {
                "artifact": "40-synthesis/attack-paths.yaml",
                "locator": p.path_id,
                "excerpt": summary,
            },
        ],
        "control_mappings": {
            "nist_800_53r5": _infer_nist_controls(g, p, findings_by_id),
        },
        "cross_references": cross_refs,
        "recommendation": {
            "posture": "required" if disposition == "risk" else "recommended",
            "summary": (
                "Reduce path feasibility by adding capability coverage on the "
                "highest-confidence edge or removing a low-confidence "
                "reachability assumption"
            ),
            "detail": (
                f"Path has {p.hop_count} hops with feasibility floor "
                f"{p.feasibility}. Adding a capability on any high-confidence "
                "compromisable edge or strengthening identity controls along "
                "this path closes the kill-chain."
            ),
        },
    }


def _finding_from_bottleneck(
    overlay: dict[str, Any], g: Graph, findings_by_id: dict[str, dict[str, Any]]
) -> dict[str, Any]:
    edge_id = overlay["edge_id"]
    edge = g.get_edge(edge_id)
    net_new: list[str] = list(overlay.get("net_new_d3fend", []))
    short_hash = hashlib.sha256(("bottleneck|" + edge_id).encode()).hexdigest()[:8]
    attack_techs = ", ".join(overlay.get("exposed_attack_techniques", []))
    d3fend_list = ", ".join(net_new)
    finding: dict[str, Any] = findings_by_id.get(edge.finding_id or "", {})
    paths_traversing = int(overlay.get("paths_traversing", 0))

    title = _truncate_title(
        f"Bottleneck edge {edge_id} exposes {attack_techs} with no "
        f"D3FEND-backed capability ({d3fend_list} would counter)"
    )

    return {
        "schema_version": 1,
        "id": f"apath-{short_hash}",
        "agent": "attack_path_analyzer",
        "apd_tier": finding.get("apd_tier", "trustworthiness"),
        "apd_goal": finding.get("apd_goal", "authenticity"),
        "disposition": "gap",
        "severity": "high" if paths_traversing >= 5 else "medium",
        "confidence": "high",
        "title": title,
        "summary": (
            f"Edge {edge_id} appears on {paths_traversing} enumerated paths and "
            f"exposes ATT&CK technique(s) {attack_techs}. D3FEND counters "
            f"{d3fend_list} are available but not implemented by any capability."
        ),
        "detail": (
            f"Bottleneck edge analysis: this edge sits on {paths_traversing} "
            f"distinct enumerated paths. Adding a capability that implements "
            f"any of {d3fend_list} breaks all of them. Existing capability "
            "backing for this technique: none."
        ),
        "evidence": [
            {
                "artifact": "40-synthesis/asset-graph.yaml",
                "locator": f"edges[{edge_id}]",
                "excerpt": f"{edge.from_node} -> {edge.to_node} via {edge.edge_type}",
            },
            {
                "artifact": "40-synthesis/defense-graph.yaml",
                "locator": f"bottleneck_overlays[{edge_id}]",
                "excerpt": f"net_new_d3fend: {net_new}",
            },
        ],
        "control_mappings": {
            "nist_800_53r5": _infer_nist_controls_from_finding(finding),
        },
        "cross_references": [edge.finding_id] if edge.finding_id else [],
        "recommendation": {
            "posture": "required",
            "summary": f"Implement one of {d3fend_list} on the bottleneck edge {edge_id}",
            "detail": (
                f"All {paths_traversing} enumerated paths through this edge "
                "share the same defensive opportunity. Single highest-leverage "
                f"investment: pick a D3FEND technique from {d3fend_list} and "
                "design a capability around it."
            ),
        },
    }


def _infer_tier(
    g: Graph, p: APath, findings_by_id: dict[str, dict[str, Any]]
) -> str:
    for eid in p.edges:
        e = g.get_edge(eid)
        if (
            e.edge_type == "compromisable_via_finding"
            and e.finding_id
            and e.finding_id in findings_by_id
        ):
            tier = findings_by_id[e.finding_id].get("apd_tier", "trustworthiness")
            return str(tier)
    return "trustworthiness"


def _infer_goal(
    g: Graph, p: APath, findings_by_id: dict[str, dict[str, Any]]
) -> str:
    for eid in p.edges:
        e = g.get_edge(eid)
        if (
            e.edge_type == "compromisable_via_finding"
            and e.finding_id
            and e.finding_id in findings_by_id
        ):
            goal = findings_by_id[e.finding_id].get("apd_goal", "authenticity")
            return str(goal)
    jewel = g.get_node(p.crown_jewel)
    if "phi" in (jewel.data_classifications or ()):
        return "confidentiality"
    return "authenticity"


def _infer_nist_controls(
    g: Graph, p: APath, findings_by_id: dict[str, dict[str, Any]]
) -> list[str]:
    controls: set[str] = set()
    for eid in p.edges:
        e = g.get_edge(eid)
        if (
            e.edge_type == "compromisable_via_finding"
            and e.finding_id
            and e.finding_id in findings_by_id
        ):
            for c in (
                findings_by_id[e.finding_id]
                .get("control_mappings", {})
                .get("nist_800_53r5", [])
            ):
                controls.add(c)
    if not controls:
        controls = {"CA-3", "SA-8"}
    return sorted(controls)


def _infer_nist_controls_from_finding(finding: dict[str, Any]) -> list[str]:
    controls = list(finding.get("control_mappings", {}).get("nist_800_53r5", []))
    return sorted(set(controls) | {"SA-8"})
