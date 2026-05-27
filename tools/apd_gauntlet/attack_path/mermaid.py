"""Mermaid flowchart rendering for attack-path diagrams.

Constraints:
  - 50-node cap per diagram
  - When the path-set spans more than 50 nodes, partition by ``attacker_position``
  - Mermaid uses ``flowchart LR`` (left-to-right) for readable kill-chains
  - Node IDs must be sanitized for Mermaid (no hyphens in identifiers — replace with underscore)
  - Edge labels are pipe-escaped to avoid breaking Mermaid syntax

Pure module: no I/O, no global state. Output is deterministic for any
ordered ``paths`` input (path order, in turn, comes from the C-11
enumeration sort).
"""

from __future__ import annotations

from collections import defaultdict

from .enumerate import Path as APath
from .graph import Graph

_MAX_NODES_PER_DIAGRAM = 50

_NODE_TYPE_ICON: dict[str, str] = {
    "asset": "S",
    "identity": "I",
    "attacker_position": "X",
    "crown_jewel": "J",
}


def _sanitize(node_id: str) -> str:
    """Replace hyphens with underscores for Mermaid identifier compatibility."""
    return node_id.replace("-", "_")


def _node_label(graph: Graph, node_id: str) -> str:
    """Render a single Mermaid node declaration: ``id["icon: name"]``."""
    n = graph.get_node(node_id)
    icon = _NODE_TYPE_ICON[n.node_type]
    safe_name = n.name.replace("|", "/").replace("[", "(").replace("]", ")")
    return f'{_sanitize(node_id)}["{icon}: {safe_name}"]'


def _edge_label(graph: Graph, edge_id: str) -> str:
    """Render a single Mermaid labeled edge: ``from --|label|--> to``."""
    e = graph.get_edge(edge_id)
    label = f"{e.edge_type}/{e.confidence}"
    if e.edge_type == "compromisable_via_finding" and e.finding_id:
        label += f" ({e.finding_id})"
    elif e.edge_type == "mitigated_by_capability" and e.capability_id:
        label += f" ({e.capability_id})"
    label = label.replace("|", "/")
    return f"{_sanitize(e.from_node)} --|{label}|--> {_sanitize(e.to_node)}"


def render_path_diagram(*, paths: list[APath], graph: Graph) -> str:
    """Render the union of ``paths`` as a single ``flowchart LR`` diagram.

    Visits edges in the order they appear across ``paths`` (deduped), so the
    output is deterministic given a deterministic ``paths`` ordering.
    Node declarations precede edge declarations.
    """
    node_ids: list[str] = []
    seen_nodes: set[str] = set()
    edge_ids: list[str] = []
    seen_edges: set[str] = set()
    for p in paths:
        for eid in p.edges:
            if eid in seen_edges:
                continue
            seen_edges.add(eid)
            edge_ids.append(eid)
            e = graph.get_edge(eid)
            for nid in (e.from_node, e.to_node):
                if nid not in seen_nodes:
                    seen_nodes.add(nid)
                    node_ids.append(nid)

    lines: list[str] = ["flowchart LR"]
    lines.extend(_node_label(graph, nid) for nid in node_ids)
    lines.extend(_edge_label(graph, eid) for eid in edge_ids)
    return "\n".join(lines) + "\n"


def render_partitioned_diagrams(
    *, paths: list[APath], graph: Graph
) -> list[str]:
    """Render ``paths`` as one or more diagrams, each capped at 50 nodes.

    If the union of all path nodes is at or below the cap, returns a single
    diagram. Otherwise partitions ``paths`` by ``attacker_position`` (sorted
    by attacker node_id for determinism) and emits one diagram per attacker.
    Within each partition, paths are added greedily in their original order.
    Paths that would push the node count over ``_MAX_NODES_PER_DIAGRAM`` are
    skipped; subsequent paths that fit within the cap are still included.
    """
    all_nodes: set[str] = set()
    for p in paths:
        for eid in p.edges:
            e = graph.get_edge(eid)
            all_nodes.add(e.from_node)
            all_nodes.add(e.to_node)

    if len(all_nodes) <= _MAX_NODES_PER_DIAGRAM:
        return [render_path_diagram(paths=paths, graph=graph)]

    by_attacker: dict[str, list[APath]] = defaultdict(list)
    for p in paths:
        by_attacker[p.attacker_position].append(p)

    diagrams: list[str] = []
    for _atk, ps in sorted(by_attacker.items()):
        subset: list[APath] = []
        subset_nodes: set[str] = set()
        for p in ps:
            candidate_nodes = set(subset_nodes)
            for eid in p.edges:
                e = graph.get_edge(eid)
                candidate_nodes.add(e.from_node)
                candidate_nodes.add(e.to_node)
            if len(candidate_nodes) > _MAX_NODES_PER_DIAGRAM:
                continue
            subset_nodes = candidate_nodes
            subset.append(p)
        if subset:
            diagrams.append(render_path_diagram(paths=subset, graph=graph))
    return diagrams
