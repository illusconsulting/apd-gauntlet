"""Tests for Mermaid flowchart rendering of attack paths.

Covers both single-diagram rendering (``render_path_diagram``) and the
50-node-capped, attacker-partitioned form (``render_partitioned_diagrams``).
"""
from __future__ import annotations

import re

from apd_gauntlet.attack_path.enumerate import Path as APath
from apd_gauntlet.attack_path.graph import Edge, Graph, Node, stable_id
from apd_gauntlet.attack_path.mermaid import (
    render_partitioned_diagrams,
    render_path_diagram,
)

# --- helpers ---------------------------------------------------------------


def _sanitize(node_id: str) -> str:
    """Mirror the renderer's sanitization for test comparisons.

    Mermaid identifiers cannot contain hyphens; the renderer maps `-` to `_`.
    Tests that assert on raw node IDs must sanitize first (Option A).
    """
    return node_id.replace("-", "_")


def _sample_graph() -> Graph:
    """Small 3-node graph: attacker -> asset -> crown_jewel via 2 hops."""
    g = Graph()
    atk = Node(
        "atk-aaaaaaaa", "attacker_position", "ext",
        {"source": "domain_default"}, "high",
    )
    asset = Node(
        "asset-a1b2c3d4", "asset", "gateway",
        {"source": "artifact"}, "high",
    )
    jewel = Node(
        "jewel-aaaaaaaa", "crown_jewel", "phi",
        {"source": "domain_default"}, "high",
    )
    for n in (atk, asset, jewel):
        g.add_node(n)
    g.add_edge(Edge(
        "edge-aaaaaaa1", "network_reachable",
        "atk-aaaaaaaa", "asset-a1b2c3d4",
        {"source": "artifact"}, "high", 1,
    ))
    g.add_edge(Edge(
        "edge-aaaaaaa2", "data_resides_on",
        "asset-a1b2c3d4", "jewel-aaaaaaaa",
        {"source": "artifact"}, "high", 1,
    ))
    return g


def _sample_path() -> APath:
    """A single 2-hop path over ``_sample_graph()``."""
    return APath(
        path_id="path-aaaaaaa1",
        attacker_position="atk-aaaaaaaa",
        crown_jewel="jewel-aaaaaaaa",
        edges=("edge-aaaaaaa1", "edge-aaaaaaa2"),
        hop_count=2,
        feasibility="high",
        severity_sum=0,
        mitigation_count=0,
    )


def _path_nodes(graph: Graph, path: APath) -> list[str]:
    """Return sanitized node IDs that appear in ``path``, in order."""
    seen: set[str] = set()
    out: list[str] = []
    for eid in path.edges:
        e = graph.get_edge(eid)
        for nid in (e.from_node, e.to_node):
            if nid not in seen:
                seen.add(nid)
                out.append(_sanitize(nid))
    return out


def _large_graph() -> Graph:
    """Build a 94-node graph spread across 3 attacker positions.

    Layout:
      - 3 attackers (``atk-aaaaaaa1``..``atk-aaaaaaa3``)
      - 1 shared crown jewel (``jewel-aaaaaaaa``)
      - For each attacker: 30 unique intermediate assets, each with a
        2-hop path atk -> asset -> jewel.
    Total distinct nodes = 3 + 1 + 90 = 94 (well above the 50-node cap).
    """
    g = Graph()
    jewel = Node(
        "jewel-aaaaaaaa", "crown_jewel", "phi",
        {"source": "domain_default"}, "high",
    )
    g.add_node(jewel)
    for atk_idx in (1, 2, 3):
        atk_id = f"atk-aaaaaaa{atk_idx}"
        g.add_node(Node(
            atk_id, "attacker_position", f"ext-{atk_idx}",
            {"source": "domain_default"}, "high",
        ))
        for mid_idx in range(30):
            asset_id = stable_id("asset", f"a{atk_idx}-m{mid_idx}")
            g.add_node(Node(
                asset_id, "asset", f"mid-{atk_idx}-{mid_idx}",
                {"source": "artifact"}, "high",
            ))
            g.add_edge(Edge(
                stable_id("edge", f"atk{atk_idx}-to-m{mid_idx}"),
                "network_reachable",
                atk_id, asset_id,
                {"source": "artifact"}, "high", 1,
            ))
            g.add_edge(Edge(
                stable_id("edge", f"m{atk_idx}-{mid_idx}-to-jewel"),
                "data_resides_on",
                asset_id, "jewel-aaaaaaaa",
                {"source": "artifact"}, "high", 1,
            ))
    return g


def _many_paths() -> list[APath]:
    """Build the 90 paths corresponding to ``_large_graph()``."""
    paths: list[APath] = []
    for atk_idx in (1, 2, 3):
        atk_id = f"atk-aaaaaaa{atk_idx}"
        for mid_idx in range(30):
            e1 = stable_id("edge", f"atk{atk_idx}-to-m{mid_idx}")
            e2 = stable_id("edge", f"m{atk_idx}-{mid_idx}-to-jewel")
            paths.append(APath(
                path_id=stable_id("edge", f"path-{atk_idx}-{mid_idx}"),
                attacker_position=atk_id,
                crown_jewel="jewel-aaaaaaaa",
                edges=(e1, e2),
                hop_count=2,
                feasibility="high",
                severity_sum=0,
                mitigation_count=0,
            ))
    return paths


# --- tests -----------------------------------------------------------------


def test_render_path_diagram_emits_flowchart_lr() -> None:
    output = render_path_diagram(paths=[_sample_path()], graph=_sample_graph())
    assert output.startswith("flowchart LR\n")


def test_render_path_diagram_includes_all_path_nodes() -> None:
    g = _sample_graph()
    p = _sample_path()
    output = render_path_diagram(paths=[p], graph=g)
    for node_id in _path_nodes(g, p):
        assert node_id in output


def test_render_path_diagram_labels_edges_with_edge_type() -> None:
    output = render_path_diagram(paths=[_sample_path()], graph=_sample_graph())
    assert "compromisable_via_finding" in output or "network_reachable" in output


def test_render_partitioned_diagrams_partitions_when_node_cap_exceeded() -> None:
    diagrams = render_partitioned_diagrams(
        paths=_many_paths(), graph=_large_graph()
    )
    assert len(diagrams) >= 3  # one per attacker partition
    for d in diagrams:
        node_lines = [
            line for line in d.splitlines()
            if "[" in line and line.strip() and line.strip()[0].isalpha()
        ]
        assert len(node_lines) <= 50


def test_render_partitioned_diagrams_single_diagram_when_below_cap() -> None:
    diagrams = render_partitioned_diagrams(
        paths=[_sample_path()], graph=_sample_graph()
    )
    assert len(diagrams) == 1


def test_mermaid_output_is_valid_against_basic_syntax_pattern() -> None:
    output = render_path_diagram(paths=[_sample_path()], graph=_sample_graph())
    lines = [line for line in output.splitlines()[1:] if line.strip()]
    node_pat = re.compile(r"^\s*[A-Za-z_][\w-]*(\[.*\])?$")
    edge_pat = re.compile(
        r"^\s*[A-Za-z_][\w-]*\s*--.*-->\s*[A-Za-z_][\w-]*$"
    )
    for line in lines:
        assert node_pat.match(line) or edge_pat.match(line), (
            f"unrecognized mermaid syntax: {line!r}"
        )
