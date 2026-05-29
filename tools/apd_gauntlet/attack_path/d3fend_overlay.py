"""D3FEND defensive overlay computation.

For each bottleneck edge, collect the ATT&CK techniques exposed (from the
finding(s) backing the edge), look up D3FEND techniques that counter those,
and partition the candidates by existing-capability-backing vs net-new.

Pure data transformation: no I/O beyond :func:`load_d3fend_data`, no global
state. Output conforms to ``schemas/defense-graph.schema.json``'s
``bottleneck_overlays[]`` array.

The D3FEND data file at ``tools/apd_gauntlet/data/d3fend.json`` uses the shape
``{"entries": [{"d3fend_id": ..., "name": ..., "counters_attack": [...]}, ...]}``.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .enumerate import Path as APath
from .graph import Graph

_D3FEND_DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "d3fend.json"


def load_d3fend_data() -> dict[str, Any]:
    """Load the bundled D3FEND attack-counter mapping from disk.

    Public API for callers (e.g. the analyze-attack-paths CLI). Unit tests
    pass an in-memory fixture directly to :func:`build_overlays` instead.
    """
    return json.loads(_D3FEND_DATA_PATH.read_text(encoding="utf-8"))  # type: ignore[no-any-return]


def lookup_d3fend_counters(
    attack_technique_ids: list[str],
    d3fend: dict[str, Any],
) -> list[dict[str, Any]]:
    """Return D3FEND entries that counter at least one input ATT&CK technique.

    Each returned dict has ``d3fend_id``, ``counters`` (sorted list of the
    intersection with the input), and ``rationale`` (>=20 chars, satisfying
    ``defense-graph.schema.json`` ``candidate_d3fend[].rationale``). The
    returned list is sorted by ``d3fend_id`` for deterministic output.
    """
    wanted = set(attack_technique_ids)
    hits: list[dict[str, Any]] = []
    for entry in d3fend.get("entries", []):
        covered = set(entry.get("counters_attack", [])) & wanted
        if not covered:
            continue
        d3fend_id = entry["d3fend_id"]
        name = entry.get("name", "")
        hits.append({
            "d3fend_id": d3fend_id,
            "counters": sorted(covered),
            "rationale": (
                f"D3FEND {d3fend_id} ({name}) counters ATT&CK "
                f"{', '.join(sorted(covered))} per MITRE D3FEND "
                "attack-counter mapping"
            ),
        })
    return sorted(hits, key=lambda h: h["d3fend_id"])


def build_overlays(
    *,
    paths: list[APath],
    bottleneck_edges: dict[str, list[str]],
    graph: Graph,
    findings_by_id: dict[str, dict[str, Any]],
    capabilities: list[dict[str, Any]],
    d3fend_data: dict[str, Any],
) -> list[dict[str, Any]]:
    """Build ``bottleneck_overlays[]`` entries for ``defense-graph.schema.json``.

    Iterates ``bottleneck_edges`` (output of
    :func:`apd_gauntlet.attack_path.enumerate.compute_bottleneck_edges`),
    skips non-``compromisable_via_finding`` edges (they expose no ATT&CK
    techniques), extracts the finding's ``mitre_attack`` techniques, looks
    up D3FEND counters, and partitions them by existing-capability-backing
    vs net-new.

    The ``paths`` parameter is accepted for symmetry with the call site
    but is not consulted; the bottleneck_edges dict already carries
    ``edge_id → [path_id, ...]``.
    """
    del paths  # accepted for API symmetry; unused

    overlays: list[dict[str, Any]] = []

    # Index capabilities by the D3FEND technique they implement.
    # capability schema: control_mappings.d3fend = [{technique, counters_attack, rationale}, ...]
    cap_by_d3fend: dict[str, list[str]] = {}
    for cap in capabilities:
        d3fend_entries = (cap.get("control_mappings") or {}).get("d3fend") or []
        for entry in d3fend_entries:
            cap_by_d3fend.setdefault(entry["technique"], []).append(cap["id"])

    for edge_id, traversing_path_ids in sorted(bottleneck_edges.items()):
        edge = graph.get_edge(edge_id)
        # Bottleneck overlays are only meaningful for compromisable_via_finding
        # edges; other edge types have no ATT&CK techniques to counter.
        if edge.edge_type != "compromisable_via_finding":
            continue
        finding_id = edge.finding_id
        if finding_id is None:
            continue
        finding = findings_by_id.get(finding_id)
        if not finding:
            continue
        attack_techs = sorted({
            e["technique"]
            for e in ((finding.get("control_mappings") or {}).get("mitre_attack") or [])
        })
        if not attack_techs:
            continue
        candidate = lookup_d3fend_counters(attack_techs, d3fend_data)

        existing_backing: list[dict[str, Any]] = []
        net_new: list[str] = []
        for cand in candidate:
            backers = cap_by_d3fend.get(cand["d3fend_id"], [])
            if backers:
                existing_backing.append({
                    "d3fend_id": cand["d3fend_id"],
                    "capability_ids": sorted(backers),
                })
            else:
                net_new.append(cand["d3fend_id"])

        overlays.append({
            "edge_id": edge_id,
            "paths_traversing": len(traversing_path_ids),
            "exposed_attack_techniques": attack_techs,
            "candidate_d3fend": candidate,
            "existing_capability_backing": existing_backing,
            "net_new_d3fend": sorted(net_new),
        })

    return overlays
