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

_UNCERTAINTY_SEVERITY = "low"
_TITLE_MAX = 200

# Feasibility rank for the bounded-selection tiebreak (higher = more feasible).
_FEASIBILITY_RANK: dict[str, int] = {"low": 0, "medium": 1, "high": 2}

# Priority order for inferring apd_goal across multiple finding-edges on a
# path. Highest-impact category appears first so that, given a path that
# crosses several findings of different goals, the emitted finding is labeled
# by the worst-case category (e.g. PHI exposure dominates an upstream
# authenticity weakness).
_GOAL_PRIORITY: tuple[str, ...] = (
    "confidentiality",
    "integrity",
    "non_repudiation",
    "availability",
    "authenticity",
    "ephemeral",
    "immutability",
    "resilient",
    "distributed",
)

# Priority order for inferring apd_tier across multiple finding-edges. The
# three tiers form a dependency chain (trustworthiness underpins
# scalability underpins auditability); when a path mixes tiers we report the
# foundational one because a break there invalidates the layers above.
_TIER_PRIORITY: tuple[str, ...] = (
    "trustworthiness",
    "scalability",
    "auditability",
)


def severity_for_risk(severity_sum: int) -> str:
    """Map ``severity_sum`` (sum of ``_SEVERITY_SCORE`` over compromisable
    edges) to a severity label for the risk-disposition branch.

    Eligible only when ``severity_sum >= 3`` (enforced by caller).

    - ``sum == 3``: ``"high"`` (a single high-severity finding on the path).
    - ``sum >= 4``: ``"critical"`` (one critical finding OR two-or-more high
      findings OR any worse combination). Saturates at critical — multi-hop
      worst-case paths must not be silently downgraded.
    """
    return "critical" if severity_sum >= 4 else "high"


def emit_findings(
    *,
    paths: list[APath],
    overlays: list[dict[str, Any]],
    graph: Graph,
    findings_by_id: dict[str, dict[str, Any]],
    capabilities: list[dict[str, Any]],
    bound: bool = True,
    max_risk_per_pair: int = 1,
) -> list[dict[str, Any]]:
    """Emit apath-* findings for enumerated paths and qualifying overlays.

    Builds one finding per path (risk or uncertainty disposition) and one
    additional finding per overlay whose ``net_new_d3fend`` is non-empty and
    whose ``existing_capability_backing`` is empty (gap disposition).

    When ``bound`` is True (the DEFAULT for all runs) the full per-path stream
    is then passed through :func:`select_bounded`, which keeps every gap finding,
    keeps the worst ``max_risk_per_pair`` risk findings per (attacker,
    crown_jewel) pair, and collapses the suppressed remainder into ONE aggregate
    uncertainty finding. Set ``bound=False`` to restore the legacy
    one-finding-per-path behavior. Note that ``attack-paths.yaml`` always keeps
    every enumerated path as an artifact of record — only the findings file is
    bounded.

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
    if bound:
        out, _stats = select_bounded(
            out, paths, max_risk_per_pair=max_risk_per_pair
        )
    out.sort(key=lambda f: f["id"])
    return out


def _apath_id_for_path(path_id: str) -> str:
    """Reproduce the emitter's own apath id scheme for a path: the same
    ``apath-<sha8(path_id)>`` derived in :func:`_finding_from_path`."""
    return "apath-" + hashlib.sha256(path_id.encode()).hexdigest()[:8]


def select_bounded(
    all_findings: list[dict[str, Any]],
    paths: list[APath],
    *,
    max_risk_per_pair: int = 1,
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    """Bound the per-path finding stream to the worst N risks per pair.

    Discipline (ported as the default for every run):

    * keep ALL gap-disposition findings untouched;
    * a path is *risk-eligible* when ``feasibility != 'low'`` AND
      ``severity_sum >= 3`` AND ``mitigation_count == 0``. Risk-eligible paths
      are grouped by ``(attacker_position, crown_jewel)``; within each group the
      top ``max_risk_per_pair`` are kept, ranked by ``(severity_sum desc,
      hop_count asc, feasibility desc, path_id)``. The kept paths' findings are
      located via the emitter's own id scheme (``apath-<sha8(path_id)>``);
    * everything else (risk-eligible paths beyond the per-pair cap, plus every
      non-risk per-path finding such as low-feasibility uncertainties and
      partial-mitigation findings) is the *suppressed remainder*. It collapses
      into ONE aggregate uncertainty finding (disposition ``uncertainty``,
      severity ``low``, confidence ``low``, posture ``consider``) disclosing the
      suppressed count, the total path count, and the per-pair cap. The
      aggregate is omitted only when nothing is suppressed.

    Findings whose id maps to no enumerated path (defensive — e.g. a stray
    record not produced by ``_finding_from_path``) are kept so nothing is
    silently lost.

    Returns ``(selected, stats)`` where ``stats`` has keys ``gap``,
    ``risk_pairs``, ``risk_findings``, ``suppressed_into_aggregate``, and
    ``selected_total``.
    """
    findings_by_apath_id = {f.get("id"): f for f in all_findings}

    gap_findings = [f for f in all_findings if f.get("disposition") == "gap"]

    # All apath ids that originate from an enumerated path (the per-path stream).
    path_finding_ids = {_apath_id_for_path(p.path_id) for p in paths}

    # Group risk-eligible paths by (attacker, jewel).
    pairs: dict[tuple[str, str], list[APath]] = {}
    for p in paths:
        if p.feasibility != "low" and p.severity_sum >= 3 and p.mitigation_count == 0:
            pairs.setdefault((p.attacker_position, p.crown_jewel), []).append(p)

    kept_risk_ids: list[str] = []
    for _pair, group in pairs.items():
        group.sort(
            key=lambda p: (
                -p.severity_sum,
                p.hop_count,
                -_FEASIBILITY_RANK[p.feasibility],
                p.path_id,
            )
        )
        for p in group[:max_risk_per_pair]:
            fid = _apath_id_for_path(p.path_id)
            if fid in findings_by_apath_id and fid not in kept_risk_ids:
                kept_risk_ids.append(fid)

    kept_ids: set[str | None] = {f.get("id") for f in gap_findings}
    kept_ids.update(kept_risk_ids)

    selected: list[dict[str, Any]] = list(gap_findings)
    for rid in kept_risk_ids:
        selected.append(findings_by_apath_id[rid])

    # Defensive: keep any finding that is neither a gap, a kept risk, nor a
    # per-path finding (so an unexpected stray record is never silently lost).
    for f in all_findings:
        sid = f.get("id")
        if sid not in kept_ids and sid not in path_finding_ids:
            selected.append(f)
            kept_ids.add(sid)

    # Suppressed remainder = every per-path finding that was not kept.
    suppressed = sum(1 for pid in path_finding_ids if pid not in kept_ids)

    if suppressed > 0:
        selected.append(
            _aggregate_uncertainty_finding(
                suppressed=suppressed,
                total_paths=len(paths),
                max_risk_per_pair=max_risk_per_pair,
            )
        )

    stats = {
        "gap": len(gap_findings),
        "risk_pairs": len(pairs),
        "risk_findings": len(kept_risk_ids),
        "suppressed_into_aggregate": suppressed,
        "selected_total": len(selected),
    }
    return selected, stats


def _aggregate_uncertainty_finding(
    *, suppressed: int, total_paths: int, max_risk_per_pair: int
) -> dict[str, Any]:
    """Build the single aggregate uncertainty finding that stands in for all
    suppressed risk paths. Its id is deterministic in the disclosed counts so
    re-runs over the same input are stable.

    Schema-valid: low severity, low confidence, posture ``consider`` (which the
    schema allows to omit recommendation ``detail``), one evidence pointer at
    ``attack-paths.yaml`` (the artifact of record that retains every path).
    """
    short_hash = hashlib.sha256(
        f"aggregate|{suppressed}|{total_paths}|{max_risk_per_pair}".encode()
    ).hexdigest()[:8]
    summary = (
        f"{suppressed} additional risk-eligible attack path(s) of {total_paths} "
        f"enumerated were suppressed from the findings file (per-pair cap = "
        f"{max_risk_per_pair} risk finding(s) per attacker x crown-jewel pair). "
        "Only the worst path per pair is surfaced as a discrete risk finding."
    )
    detail = (
        f"To keep the advisory signal focused, the analyzer bounds risk findings "
        f"to the worst {max_risk_per_pair} path(s) per (attacker_position, "
        f"crown_jewel) pair. {suppressed} lower-ranked risk-eligible path(s) "
        f"(of {total_paths} total enumerated paths) are collapsed into this "
        "single aggregate. Every enumerated path — suppressed or not — is "
        "retained verbatim in 40-synthesis/attack-paths.yaml, the artifact of "
        "record; consult it to inspect the full set."
    )
    return {
        "schema_version": 1,
        "id": f"apath-{short_hash}",
        "agent": "attack_path_analyzer",
        "apd_tier": "trustworthiness",
        "apd_goal": "authenticity",
        "disposition": "uncertainty",
        "severity": "low",
        "confidence": "low",
        "title": "Suppressed risk attack paths collapsed into one aggregate",
        "summary": summary,
        "detail": detail,
        "evidence": [
            {
                "artifact": "40-synthesis/attack-paths.yaml",
                "locator": "paths",
                "excerpt": (
                    f"{suppressed} of {total_paths} enumerated paths suppressed "
                    f"from findings (per-pair cap={max_risk_per_pair})"
                ),
            }
        ],
        "control_mappings": {"nist_800_53r5": ["CA-3", "SA-8"]},
        "cross_references": [],
        "recommendation": {
            "posture": "consider",
            "summary": (
                "Review 40-synthesis/attack-paths.yaml for the full path set; "
                "raise max_risk_findings_per_pair if more per-pair detail is wanted."
            ),
        },
    }


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
        severity = severity_for_risk(p.severity_sum)
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
    """Pick the apd_tier label for a path's finding.

    Collects tiers from every ``compromisable_via_finding`` edge on the path
    (not just the first) and returns the highest-priority entry in
    ``_TIER_PRIORITY``. ``trustworthiness`` outranks ``scalability`` which
    outranks ``auditability`` because the tiers stack as a dependency chain
    — a break in the foundational tier invalidates the layers above, so the
    finding should be labeled by the foundational tier when a path crosses
    multiple. Falls back to ``"trustworthiness"`` when no finding-edges
    contribute a tier.
    """
    collected: set[str] = set()
    for eid in p.edges:
        e = g.get_edge(eid)
        if (
            e.edge_type == "compromisable_via_finding"
            and e.finding_id
            and e.finding_id in findings_by_id
        ):
            tier = findings_by_id[e.finding_id].get("apd_tier")
            if isinstance(tier, str):
                collected.add(tier)
    for candidate in _TIER_PRIORITY:
        if candidate in collected:
            return candidate
    return "trustworthiness"


def _infer_goal(
    g: Graph, p: APath, findings_by_id: dict[str, dict[str, Any]]
) -> str:
    """Pick the apd_goal label for a path's finding.

    Collects goals from every ``compromisable_via_finding`` edge on the path
    and returns the highest-priority entry in ``_GOAL_PRIORITY``. Ordering
    reflects worst-case impact: a path that crosses a ``confidentiality``
    finding adjacent to the crown jewel dominates an upstream
    ``authenticity`` finding, so the emitted finding is labeled
    ``confidentiality``. When no finding-edges contribute a goal, falls
    back to the PHI-classification heuristic on the crown-jewel node, then
    to ``"authenticity"``.
    """
    collected: set[str] = set()
    for eid in p.edges:
        e = g.get_edge(eid)
        if (
            e.edge_type == "compromisable_via_finding"
            and e.finding_id
            and e.finding_id in findings_by_id
        ):
            goal = findings_by_id[e.finding_id].get("apd_goal")
            if isinstance(goal, str):
                collected.add(goal)
    for candidate in _GOAL_PRIORITY:
        if candidate in collected:
            return candidate
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
