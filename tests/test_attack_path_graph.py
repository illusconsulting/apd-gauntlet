"""Tests for attack-path graph primitives."""
from __future__ import annotations

import pytest
from apd_gauntlet.attack_path.graph import Edge, Graph, Node, stable_id


def test_node_requires_provenance_and_confidence():
    n = Node(node_id="asset-aaaaaaaa", node_type="asset", name="API",
             provenance={"source": "artifact", "artifact": "intake-brief.md", "locator": "L42"},
             confidence="high")
    assert n.node_id == "asset-aaaaaaaa"


def test_node_rejects_malformed_id():
    with pytest.raises(ValueError, match="node_id"):
        Node(node_id="bad-id", node_type="asset", name="X",
             provenance={"source": "artifact"}, confidence="high")


def test_node_id_prefix_matches_node_type():
    with pytest.raises(ValueError, match="prefix"):
        Node(node_id="asset-aaaaaaaa", node_type="identity", name="X",
             provenance={"source": "artifact"}, confidence="high")


def test_node_rejects_invalid_confidence():
    with pytest.raises(ValueError, match="confidence"):
        Node(node_id="asset-aaaaaaaa", node_type="asset", name="X",
             provenance={"source": "artifact"}, confidence="very-high")


def test_node_requires_provenance_source():
    with pytest.raises(ValueError, match="source"):
        Node(node_id="asset-aaaaaaaa", node_type="asset", name="X",
             provenance={"artifact": "x.md"}, confidence="high")


def test_edge_requires_from_to_provenance_confidence_cost():
    e = Edge(edge_id="edge-aaaaaaaa", edge_type="network_reachable",
             from_node="asset-bbbbbbbb", to_node="asset-cccccccc",
             provenance={"source": "artifact"}, confidence="high", traversal_cost=1)
    assert e.edge_type == "network_reachable"


def test_compromisable_via_finding_edge_requires_finding_id():
    with pytest.raises(ValueError, match="finding_id"):
        Edge(edge_id="edge-aaaaaaaa", edge_type="compromisable_via_finding",
             from_node="asset-bbbbbbbb", to_node="asset-cccccccc",
             provenance={"source": "artifact"}, confidence="high", traversal_cost=1)


def test_mitigated_by_capability_edge_requires_capability_id():
    with pytest.raises(ValueError, match="capability_id"):
        Edge(edge_id="edge-aaaaaaaa", edge_type="mitigated_by_capability",
             from_node="asset-bbbbbbbb", to_node="asset-cccccccc",
             provenance={"source": "artifact"}, confidence="high", traversal_cost=1)


def test_edge_traversal_cost_out_of_range():
    with pytest.raises(ValueError, match="traversal_cost"):
        Edge(edge_id="edge-aaaaaaaa", edge_type="network_reachable",
             from_node="asset-bbbbbbbb", to_node="asset-cccccccc",
             provenance={"source": "artifact"}, confidence="high", traversal_cost=0)
    with pytest.raises(ValueError, match="traversal_cost"):
        Edge(edge_id="edge-aaaaaaaa", edge_type="network_reachable",
             from_node="asset-bbbbbbbb", to_node="asset-cccccccc",
             provenance={"source": "artifact"}, confidence="high", traversal_cost=101)


def test_graph_add_node_and_lookup():
    g = Graph()
    g.add_node(Node("asset-aaaaaaaa", "asset", "API",
                    {"source": "artifact"}, "high"))
    assert g.get_node("asset-aaaaaaaa").name == "API"


def test_graph_add_duplicate_node_raises():
    g = Graph()
    n1 = Node("asset-aaaaaaaa", "asset", "A", {"source": "artifact"}, "high")
    g.add_node(n1)
    with pytest.raises(ValueError, match="duplicate"):
        g.add_node(n1)


def test_graph_add_edge_requires_both_endpoints_present():
    g = Graph()
    with pytest.raises(ValueError, match="unknown node"):
        g.add_edge(Edge("edge-aaaaaaaa", "network_reachable",
                         "asset-bbbbbbbb", "asset-cccccccc",
                         {"source": "artifact"}, "high", 1))


def test_graph_outgoing_edges_for_node():
    g = Graph()
    n1 = Node("asset-aaaaaaaa", "asset", "A", {"source": "artifact"}, "high")
    n2 = Node("asset-bbbbbbbb", "asset", "B", {"source": "artifact"}, "high")
    g.add_node(n1)
    g.add_node(n2)
    e = Edge("edge-aaaaaaaa", "network_reachable",
             "asset-aaaaaaaa", "asset-bbbbbbbb",
             {"source": "artifact"}, "high", 1)
    g.add_edge(e)
    outs = g.outgoing("asset-aaaaaaaa")
    assert len(outs) == 1 and outs[0].edge_id == "edge-aaaaaaaa"


def test_graph_nodes_by_type():
    g = Graph()
    g.add_node(Node("asset-aaaaaaaa", "asset", "A", {"source": "artifact"}, "high"))
    g.add_node(
        Node("atk-bbbbbbbb", "attacker_position", "ext", {"source": "domain_default"}, "high")
    )
    g.add_node(Node("jewel-cccccccc", "crown_jewel", "phi", {"source": "domain_default"}, "high"))
    assert len(g.nodes_by_type("asset")) == 1
    assert len(g.nodes_by_type("attacker_position")) == 1
    assert len(g.nodes_by_type("crown_jewel")) == 1


def test_stable_id_deterministic():
    id1 = stable_id("asset", "API", "intake-brief.md#L42")
    id2 = stable_id("asset", "API", "intake-brief.md#L42")
    id3 = stable_id("asset", "API", "intake-brief.md#L43")
    assert id1 == id2
    assert id1 != id3
    assert id1.startswith("asset-")


def test_stable_id_for_all_node_kinds_and_edge():
    for kind in ("asset", "idn", "atk", "jewel", "edge"):
        result = stable_id(kind, "x", "y")
        if kind == "edge":
            assert result.startswith("edge-")
        elif kind == "idn":
            assert result.startswith("idn-")
        else:
            assert result.startswith(f"{kind}-")
        # Hash digest is 8 hex chars
        assert len(result.split("-", 1)[1]) == 8
