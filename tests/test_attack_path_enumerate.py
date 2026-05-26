"""Tests for bounded DFS path enumeration with edge-set pruning."""
from __future__ import annotations

from apd_gauntlet.attack_path.enumerate import (
    EnumerationParams,
    compute_bottleneck_edges,
    enumerate_paths,
)
from apd_gauntlet.attack_path.graph import Edge, Graph, Node, stable_id


def _params(
    *, max_hop: int = 8, max_paths_per_pair: int = 50, bottleneck_threshold: int = 5
) -> EnumerationParams:
    return EnumerationParams(
        max_hop=max_hop,
        max_paths_per_pair=max_paths_per_pair,
        bottleneck_threshold=bottleneck_threshold,
    )


def _two_hop_graph() -> Graph:
    g = Graph()
    atk = Node("atk-aaaaaaaa", "attacker_position", "ext",
               {"source": "domain_default"}, "high")
    a1 = Node("asset-aaaaaaaa", "asset", "gateway",
              {"source": "artifact"}, "high")
    jwl = Node("jewel-aaaaaaaa", "crown_jewel", "phi",
               {"source": "domain_default"}, "high")
    for n in (atk, a1, jwl):
        g.add_node(n)
    g.add_edge(Edge("edge-aaaaaaaa", "network_reachable",
                    "atk-aaaaaaaa", "asset-aaaaaaaa",
                    {"source": "artifact"}, "high", 1))
    g.add_edge(Edge("edge-bbbbbbbb", "data_resides_on",
                    "asset-aaaaaaaa", "jewel-aaaaaaaa",
                    {"source": "artifact"}, "high", 1))
    return g


def _three_way_fan_graph() -> Graph:
    """Build a graph with three 2-hop paths whose sort-key fields are all
    identical except ``path_id`` — exercises the ``path_id`` tiebreak in
    the enumeration sort key.

    Layout: one attacker, three intermediate assets, one crown jewel. All
    edges are ``high`` confidence with ``traversal_cost=1`` and no finding
    or capability edges, so every resulting path has
    ``severity_sum=0``, ``hop_count=2``, and ``feasibility="high"``.
    """
    g = Graph()
    atk = Node("atk-aaaaaaaa", "attacker_position", "ext",
               {"source": "domain_default"}, "high")
    jwl = Node("jewel-aaaaaaaa", "crown_jewel", "phi",
               {"source": "domain_default"}, "high")
    g.add_node(atk)
    g.add_node(jwl)
    for i in range(3):
        mid_id = stable_id("asset", f"mid-{i}")
        g.add_node(Node(mid_id, "asset", f"mid-{i}",
                        {"source": "artifact"}, "high"))
        g.add_edge(Edge(stable_id("edge", f"atk-to-mid-{i}"),
                        "network_reachable",
                        "atk-aaaaaaaa", mid_id,
                        {"source": "artifact"}, "high", 1))
        g.add_edge(Edge(stable_id("edge", f"mid-{i}-to-jewel"),
                        "data_resides_on",
                        mid_id, "jewel-aaaaaaaa",
                        {"source": "artifact"}, "high", 1))
    return g


def test_enumerate_finds_simple_two_hop_path() -> None:
    g = _two_hop_graph()
    paths = enumerate_paths(
        g, "atk-aaaaaaaa", "jewel-aaaaaaaa", _params()
    )
    assert len(paths) == 1
    assert paths[0].hop_count == 2
    assert paths[0].edges == ("edge-aaaaaaaa", "edge-bbbbbbbb")


def test_enumerate_honors_max_hop_cap() -> None:
    # Build a 5-hop graph; ask for max_hop=3 -> no path reaches jewel
    g = Graph()
    atk = Node("atk-aaaaaaaa", "attacker_position", "ext",
               {"source": "domain_default"}, "high")
    a1 = Node("asset-aaaaaaa1", "asset", "n1", {"source": "artifact"}, "high")
    a2 = Node("asset-aaaaaaa2", "asset", "n2", {"source": "artifact"}, "high")
    a3 = Node("asset-aaaaaaa3", "asset", "n3", {"source": "artifact"}, "high")
    a4 = Node("asset-aaaaaaa4", "asset", "n4", {"source": "artifact"}, "high")
    jwl = Node("jewel-aaaaaaaa", "crown_jewel", "phi",
               {"source": "domain_default"}, "high")
    for n in (atk, a1, a2, a3, a4, jwl):
        g.add_node(n)
    g.add_edge(Edge("edge-aaaaaaa1", "network_reachable",
                    "atk-aaaaaaaa", "asset-aaaaaaa1",
                    {"source": "artifact"}, "high", 1))
    g.add_edge(Edge("edge-aaaaaaa2", "network_reachable",
                    "asset-aaaaaaa1", "asset-aaaaaaa2",
                    {"source": "artifact"}, "high", 1))
    g.add_edge(Edge("edge-aaaaaaa3", "network_reachable",
                    "asset-aaaaaaa2", "asset-aaaaaaa3",
                    {"source": "artifact"}, "high", 1))
    g.add_edge(Edge("edge-aaaaaaa4", "network_reachable",
                    "asset-aaaaaaa3", "asset-aaaaaaa4",
                    {"source": "artifact"}, "high", 1))
    g.add_edge(Edge("edge-aaaaaaa5", "data_resides_on",
                    "asset-aaaaaaa4", "jewel-aaaaaaaa",
                    {"source": "artifact"}, "high", 1))
    paths = enumerate_paths(
        g, "atk-aaaaaaaa", "jewel-aaaaaaaa", _params(max_hop=3)
    )
    assert paths == []


def test_enumerate_uses_edge_set_pruning_not_node_set() -> None:
    # Two parallel edges between the same nodes — enumeration must allow
    # both as alternate paths
    g = Graph()
    atk = Node("atk-aaaaaaaa", "attacker_position", "ext",
               {"source": "domain_default"}, "high")
    a1 = Node("asset-aaaaaaaa", "asset", "gateway",
              {"source": "artifact"}, "high")
    jwl = Node("jewel-aaaaaaaa", "crown_jewel", "phi",
               {"source": "domain_default"}, "high")
    for n in (atk, a1, jwl):
        g.add_node(n)
    # Two parallel network_reachable edges between atk and a1
    g.add_edge(Edge("edge-aaaaaaa1", "network_reachable",
                    "atk-aaaaaaaa", "asset-aaaaaaaa",
                    {"source": "artifact"}, "high", 1))
    g.add_edge(Edge("edge-aaaaaaa2", "network_reachable",
                    "atk-aaaaaaaa", "asset-aaaaaaaa",
                    {"source": "artifact"}, "high", 1))
    g.add_edge(Edge("edge-bbbbbbbb", "data_resides_on",
                    "asset-aaaaaaaa", "jewel-aaaaaaaa",
                    {"source": "artifact"}, "high", 1))
    paths = enumerate_paths(
        g, "atk-aaaaaaaa", "jewel-aaaaaaaa", _params()
    )
    assert len(paths) == 2
    first_edges = {p.edges[0] for p in paths}
    assert first_edges == {"edge-aaaaaaa1", "edge-aaaaaaa2"}
    # Each path must end on the shared final edge
    for p in paths:
        assert p.edges[1] == "edge-bbbbbbbb"


def test_enumerate_truncates_at_max_paths_per_pair() -> None:
    # Fan graph with 50+ distinct 2-hop paths; ask max=10 -> exactly 10
    g = Graph()
    atk = Node("atk-aaaaaaaa", "attacker_position", "ext",
               {"source": "domain_default"}, "high")
    jwl = Node("jewel-aaaaaaaa", "crown_jewel", "phi",
               {"source": "domain_default"}, "high")
    g.add_node(atk)
    g.add_node(jwl)
    fan_count = 60
    for i in range(fan_count):
        nid = stable_id("asset", f"hop-{i}")
        g.add_node(Node(nid, "asset", f"hop-{i}",
                        {"source": "artifact"}, "high"))
        g.add_edge(Edge(stable_id("edge", f"atk-to-{i}"),
                        "network_reachable",
                        "atk-aaaaaaaa", nid,
                        {"source": "artifact"}, "high", 1))
        g.add_edge(Edge(stable_id("edge", f"{i}-to-jewel"),
                        "data_resides_on",
                        nid, "jewel-aaaaaaaa",
                        {"source": "artifact"}, "high", 1))
    paths = enumerate_paths(
        g, "atk-aaaaaaaa", "jewel-aaaaaaaa",
        _params(max_paths_per_pair=10),
    )
    assert len(paths) == 10


def test_path_feasibility_is_floor_of_edge_confidences() -> None:
    # Graph with high -> medium -> low -> high edges -> feasibility low
    g = Graph()
    atk = Node("atk-aaaaaaaa", "attacker_position", "ext",
               {"source": "domain_default"}, "high")
    a1 = Node("asset-aaaaaaa1", "asset", "n1", {"source": "artifact"}, "high")
    a2 = Node("asset-aaaaaaa2", "asset", "n2", {"source": "artifact"}, "high")
    a3 = Node("asset-aaaaaaa3", "asset", "n3", {"source": "artifact"}, "high")
    jwl = Node("jewel-aaaaaaaa", "crown_jewel", "phi",
               {"source": "domain_default"}, "high")
    for n in (atk, a1, a2, a3, jwl):
        g.add_node(n)
    g.add_edge(Edge("edge-aaaaaaa1", "network_reachable",
                    "atk-aaaaaaaa", "asset-aaaaaaa1",
                    {"source": "artifact"}, "high", 1))
    g.add_edge(Edge("edge-aaaaaaa2", "network_reachable",
                    "asset-aaaaaaa1", "asset-aaaaaaa2",
                    {"source": "artifact"}, "medium", 1))
    g.add_edge(Edge("edge-aaaaaaa3", "network_reachable",
                    "asset-aaaaaaa2", "asset-aaaaaaa3",
                    {"source": "artifact"}, "low", 1))
    g.add_edge(Edge("edge-aaaaaaa4", "data_resides_on",
                    "asset-aaaaaaa3", "jewel-aaaaaaaa",
                    {"source": "artifact"}, "high", 1))
    paths = enumerate_paths(
        g, "atk-aaaaaaaa", "jewel-aaaaaaaa", _params()
    )
    assert len(paths) == 1
    assert paths[0].feasibility == "low"


def test_path_severity_sum_aggregates_compromisable_edges() -> None:
    # Two compromisable_via_finding edges (critical, high) -> severity_sum 7 (4+3)
    g = Graph()
    atk = Node("atk-aaaaaaaa", "attacker_position", "ext",
               {"source": "domain_default"}, "high")
    a1 = Node("asset-aaaaaaa1", "asset", "n1", {"source": "artifact"}, "high")
    a2 = Node("asset-aaaaaaa2", "asset", "n2", {"source": "artifact"}, "high")
    jwl = Node("jewel-aaaaaaaa", "crown_jewel", "phi",
               {"source": "domain_default"}, "high")
    for n in (atk, a1, a2, jwl):
        g.add_node(n)
    g.add_edge(Edge("edge-aaaaaaa1", "compromisable_via_finding",
                    "atk-aaaaaaaa", "asset-aaaaaaa1",
                    {"source": "artifact"}, "high", 1,
                    finding_id="F-crit"))
    g.add_edge(Edge("edge-aaaaaaa2", "compromisable_via_finding",
                    "asset-aaaaaaa1", "asset-aaaaaaa2",
                    {"source": "artifact"}, "high", 1,
                    finding_id="F-high"))
    g.add_edge(Edge("edge-aaaaaaa3", "data_resides_on",
                    "asset-aaaaaaa2", "jewel-aaaaaaaa",
                    {"source": "artifact"}, "high", 1))
    findings_by_id = {
        "F-crit": {"severity": "critical"},
        "F-high": {"severity": "high"},
    }
    paths = enumerate_paths(
        g, "atk-aaaaaaaa", "jewel-aaaaaaaa", _params(),
        findings_by_id=findings_by_id,
    )
    assert len(paths) == 1
    assert paths[0].severity_sum == 7


def test_path_mitigation_count_aggregates_capability_edges() -> None:
    # Two mitigated_by_capability edges along path -> mitigation_count 2
    g = Graph()
    atk = Node("atk-aaaaaaaa", "attacker_position", "ext",
               {"source": "domain_default"}, "high")
    a1 = Node("asset-aaaaaaa1", "asset", "n1", {"source": "artifact"}, "high")
    a2 = Node("asset-aaaaaaa2", "asset", "n2", {"source": "artifact"}, "high")
    jwl = Node("jewel-aaaaaaaa", "crown_jewel", "phi",
               {"source": "domain_default"}, "high")
    for n in (atk, a1, a2, jwl):
        g.add_node(n)
    g.add_edge(Edge("edge-aaaaaaa1", "mitigated_by_capability",
                    "atk-aaaaaaaa", "asset-aaaaaaa1",
                    {"source": "artifact"}, "high", 1,
                    capability_id="CAP-1"))
    g.add_edge(Edge("edge-aaaaaaa2", "mitigated_by_capability",
                    "asset-aaaaaaa1", "asset-aaaaaaa2",
                    {"source": "artifact"}, "high", 1,
                    capability_id="CAP-2"))
    g.add_edge(Edge("edge-aaaaaaa3", "data_resides_on",
                    "asset-aaaaaaa2", "jewel-aaaaaaaa",
                    {"source": "artifact"}, "high", 1))
    paths = enumerate_paths(
        g, "atk-aaaaaaaa", "jewel-aaaaaaaa", _params()
    )
    assert len(paths) == 1
    assert paths[0].mitigation_count == 2


def test_enumerate_orders_paths_descending_severity_then_ascending_hops_then_descending_feasibility() -> None:  # noqa: E501
    # 3 paths with distinguishable metadata (max per-edge severity is critical=4,
    # so two compromisable edges give a max severity_sum of 8):
    #   Path A: severity_sum=8, hop=2, feasibility=high  -> sorts first
    #   Path B: severity_sum=8, hop=3, feasibility=high  -> sorts second (more hops)
    #   Path C: severity_sum=4, hop=2, feasibility=high  -> sorts last (lower severity)
    g = Graph()
    atk = Node("atk-aaaaaaaa", "attacker_position", "ext",
               {"source": "domain_default"}, "high")
    jwl = Node("jewel-aaaaaaaa", "crown_jewel", "phi",
               {"source": "domain_default"}, "high")
    # Intermediate nodes for the three independent paths
    a_mid = Node("asset-aaaaaaaa", "asset", "a-mid",
                 {"source": "artifact"}, "high")
    b_mid1 = Node("asset-bbbbbbb1", "asset", "b-mid1",
                  {"source": "artifact"}, "high")
    b_mid2 = Node("asset-bbbbbbb2", "asset", "b-mid2",
                  {"source": "artifact"}, "high")
    c_mid = Node("asset-cccccccc", "asset", "c-mid",
                 {"source": "artifact"}, "high")
    for n in (atk, jwl, a_mid, b_mid1, b_mid2, c_mid):
        g.add_node(n)
    # Path A: atk -> a_mid -> jwl (2 hops, both compromisable, critical+critical=8)
    g.add_edge(Edge("edge-aaaaaaa1", "compromisable_via_finding",
                    "atk-aaaaaaaa", "asset-aaaaaaaa",
                    {"source": "artifact"}, "high", 1, finding_id="F-A1"))
    g.add_edge(Edge("edge-aaaaaaa2", "compromisable_via_finding",
                    "asset-aaaaaaaa", "jewel-aaaaaaaa",
                    {"source": "artifact"}, "high", 1, finding_id="F-A2"))
    # Path B: atk -> b_mid1 -> b_mid2 -> jwl (3 hops, last two compromisable, critical+critical=8)
    g.add_edge(Edge("edge-bbbbbbb1", "network_reachable",
                    "atk-aaaaaaaa", "asset-bbbbbbb1",
                    {"source": "artifact"}, "high", 1))
    g.add_edge(Edge("edge-bbbbbbb2", "compromisable_via_finding",
                    "asset-bbbbbbb1", "asset-bbbbbbb2",
                    {"source": "artifact"}, "high", 1, finding_id="F-B1"))
    g.add_edge(Edge("edge-bbbbbbb3", "compromisable_via_finding",
                    "asset-bbbbbbb2", "jewel-aaaaaaaa",
                    {"source": "artifact"}, "high", 1, finding_id="F-B2"))
    # Path C: atk -> c_mid -> jwl (2 hops, one compromisable critical=4)
    g.add_edge(Edge("edge-ccccccc1", "compromisable_via_finding",
                    "atk-aaaaaaaa", "asset-cccccccc",
                    {"source": "artifact"}, "high", 1, finding_id="F-C1"))
    g.add_edge(Edge("edge-ccccccc2", "network_reachable",
                    "asset-cccccccc", "jewel-aaaaaaaa",
                    {"source": "artifact"}, "high", 1))
    # Severity scoring via findings_by_id (critical=4, high=3, medium=2, low=1).
    # A: critical + critical = 8
    # B: critical + critical = 8 (3 hops, ties A's severity)
    # C: critical only       = 4 (path C has 1 compromisable edge)
    findings_by_id = {
        "F-A1": {"severity": "critical"},
        "F-A2": {"severity": "critical"},
        "F-B1": {"severity": "critical"},
        "F-B2": {"severity": "critical"},
        "F-C1": {"severity": "critical"},
    }
    paths = enumerate_paths(
        g, "atk-aaaaaaaa", "jewel-aaaaaaaa", _params(),
        findings_by_id=findings_by_id,
    )
    assert len(paths) == 3
    # Map result paths to which "logical path" they are by first edge prefix.
    by_label = {}
    for p in paths:
        label = p.edges[0][:8]  # "edge-aaa", "edge-bbb", "edge-ccc"
        by_label[label] = p
    # Expected severities:
    assert by_label["edge-aaa"].severity_sum == 8
    assert by_label["edge-bbb"].severity_sum == 8
    assert by_label["edge-ccc"].severity_sum == 4
    # Expected order: A (sev=8, hop=2), B (sev=8, hop=3), C (sev=4, hop=2)
    assert paths[0].edges[0].startswith("edge-aaa")
    assert paths[1].edges[0].startswith("edge-bbb")
    assert paths[2].edges[0].startswith("edge-ccc")


def test_enumerate_self_loop_skipped() -> None:
    # Self-loop edge must never be traversed.
    g = Graph()
    atk = Node("atk-aaaaaaaa", "attacker_position", "ext",
               {"source": "domain_default"}, "high")
    a1 = Node("asset-aaaaaaaa", "asset", "n1",
              {"source": "artifact"}, "high")
    jwl = Node("jewel-aaaaaaaa", "crown_jewel", "phi",
               {"source": "domain_default"}, "high")
    for n in (atk, a1, jwl):
        g.add_node(n)
    g.add_edge(Edge("edge-aaaaaaa1", "network_reachable",
                    "atk-aaaaaaaa", "asset-aaaaaaaa",
                    {"source": "artifact"}, "high", 1))
    # Self-loop on the intermediate asset
    g.add_edge(Edge("edge-10010010", "network_reachable",
                    "asset-aaaaaaaa", "asset-aaaaaaaa",
                    {"source": "artifact"}, "high", 1))
    g.add_edge(Edge("edge-bbbbbbbb", "data_resides_on",
                    "asset-aaaaaaaa", "jewel-aaaaaaaa",
                    {"source": "artifact"}, "high", 1))
    paths = enumerate_paths(
        g, "atk-aaaaaaaa", "jewel-aaaaaaaa", _params()
    )
    assert len(paths) == 1
    assert paths[0].edges == ("edge-aaaaaaa1", "edge-bbbbbbbb")
    # The self-loop edge_id must not appear on any path
    for p in paths:
        assert "edge-10010010" not in p.edges


def test_enumerate_returns_empty_when_no_path_exists() -> None:
    # Disconnected attacker and jewel -> []
    g = Graph()
    atk = Node("atk-aaaaaaaa", "attacker_position", "ext",
               {"source": "domain_default"}, "high")
    jwl = Node("jewel-aaaaaaaa", "crown_jewel", "phi",
               {"source": "domain_default"}, "high")
    g.add_node(atk)
    g.add_node(jwl)
    paths = enumerate_paths(
        g, "atk-aaaaaaaa", "jewel-aaaaaaaa", _params()
    )
    assert paths == []


def test_enumerate_deterministic_across_runs() -> None:
    # Smoke check: trivial single-path graph -> identical path_id sequence.
    g = _two_hop_graph()
    params = _params()
    p1 = enumerate_paths(g, "atk-aaaaaaaa", "jewel-aaaaaaaa", params)
    p2 = enumerate_paths(g, "atk-aaaaaaaa", "jewel-aaaaaaaa", params)
    assert [p.path_id for p in p1] == [p.path_id for p in p2]


def test_enumerate_deterministic_when_sort_key_components_tie() -> None:
    # Stronger guard: when ``-severity_sum``, ``hop_count`` and
    # ``-CONFIDENCE_RANK[feasibility]`` all tie across multiple paths, the
    # ``path_id`` component of the sort key determines order. This test
    # fails if ``path_id`` is removed from the sort tuple.
    g = _three_way_fan_graph()
    params = _params()
    p1 = enumerate_paths(g, "atk-aaaaaaaa", "jewel-aaaaaaaa", params)
    p2 = enumerate_paths(g, "atk-aaaaaaaa", "jewel-aaaaaaaa", params)
    assert len(p1) == 3
    # All non-path_id sort-key components are identical across the 3 paths.
    assert {p.severity_sum for p in p1} == {0}
    assert {p.hop_count for p in p1} == {2}
    assert {p.feasibility for p in p1} == {"high"}
    # Run-to-run determinism.
    assert [p.path_id for p in p1] == [p.path_id for p in p2]
    # Ordering is determined by ``path_id`` ascending (the 4th sort key).
    ids = [p.path_id for p in p1]
    assert ids == sorted(ids)


def test_compute_bottleneck_edges_returns_edges_meeting_threshold() -> None:
    # Sanity check on the bottleneck helper: an edge shared by >= threshold
    # paths is returned; an edge appearing only once is filtered.
    g = Graph()
    atk = Node("atk-aaaaaaaa", "attacker_position", "ext",
               {"source": "domain_default"}, "high")
    a1 = Node("asset-aaaaaaaa", "asset", "choke",
              {"source": "artifact"}, "high")
    jwl = Node("jewel-aaaaaaaa", "crown_jewel", "phi",
               {"source": "domain_default"}, "high")
    for n in (atk, a1, jwl):
        g.add_node(n)
    # Two parallel first-hop edges, single shared second-hop edge
    g.add_edge(Edge("edge-f1110000", "network_reachable",
                    "atk-aaaaaaaa", "asset-aaaaaaaa",
                    {"source": "artifact"}, "high", 1))
    g.add_edge(Edge("edge-f2220000", "network_reachable",
                    "atk-aaaaaaaa", "asset-aaaaaaaa",
                    {"source": "artifact"}, "high", 1))
    g.add_edge(Edge("edge-c0c0c0c0", "data_resides_on",
                    "asset-aaaaaaaa", "jewel-aaaaaaaa",
                    {"source": "artifact"}, "high", 1))
    paths = enumerate_paths(
        g, "atk-aaaaaaaa", "jewel-aaaaaaaa", _params()
    )
    assert len(paths) == 2
    bottlenecks = compute_bottleneck_edges(paths, threshold=2)
    assert "edge-c0c0c0c0" in bottlenecks
    assert len(bottlenecks["edge-c0c0c0c0"]) == 2
    # First-hop edges appear on exactly one path each -> filtered out
    assert "edge-f1110000" not in bottlenecks
    assert "edge-f2220000" not in bottlenecks
