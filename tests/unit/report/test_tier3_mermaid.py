# tests/unit/report/test_tier3_mermaid.py
"""Regression tests for Mermaid renderer hardening (T3-B)."""
from __future__ import annotations

from apd_gauntlet.report.transform import (
    _PATH_FOCUSED_NODE_CAP,
    _build_mermaid,
    _build_mermaid_path_focused,
    _safe_node_id,
)


def test_safe_node_id_passes_through_valid_id():
    assert _safe_node_id("valid_id_123") == "valid_id_123"


def test_safe_node_id_hashes_invalid_id():
    out = _safe_node_id("not-valid:has-colon")
    assert out.startswith("n_")
    assert len(out) == 10  # 'n_' + 8 hex chars


def test_safe_node_id_deterministic_for_same_raw():
    """Same raw + seed → same synthetic id (essential for id_remap correctness)."""
    a = _safe_node_id("foo:bar", fallback_seed="asset_graph")
    b = _safe_node_id("foo:bar", fallback_seed="asset_graph")
    assert a == b


def test_safe_node_id_distinguishes_seeds():
    """Same raw under different seeds → different synthetic ids."""
    a = _safe_node_id("foo:bar", fallback_seed="asset_graph")
    b = _safe_node_id("foo:bar", fallback_seed="path_focused")
    assert a != b


def test_safe_node_id_distinguishes_invalid_raw_ids():
    """Two different invalid raw ids must NOT collide on the synthetic."""
    a = _safe_node_id("foo:bar")
    b = _safe_node_id("baz:qux")
    assert a != b


def test_safe_node_id_empty_raw():
    out = _safe_node_id("")
    assert out.startswith("n_")


def test_build_mermaid_handles_multiple_invalid_node_ids():
    """Two nodes with invalid raw ids must produce distinct safe ids
    (regression for the pre-T3-B fallback-counter collision)."""
    graph = {
        "nodes": [
            {"node_id": "host:web-1", "name": "web-1", "node_type": "service"},
            {"node_id": "host:db-1",  "name": "db-1",  "node_type": "data_store"},
        ],
        "edges": [{"from": "host:web-1", "to": "host:db-1", "edge_type": "trusts"}],
    }
    out = _build_mermaid(graph)
    # Two distinct synthetic ids should appear; the edge must reference both.
    assert "n_" in out
    lines = [ln.strip() for ln in out.split("\n")]
    node_lines = [ln for ln in lines if "[" in ln and not ln.startswith("graph")]
    # Should have exactly 2 node lines + 1 edge line.
    assert len(node_lines) == 2
    edge_line = [ln for ln in lines if "-->" in ln]
    assert len(edge_line) == 1


def test_build_mermaid_path_focused_caps_large_subgraph():
    """A path-focused subgraph with more than _PATH_FOCUSED_NODE_CAP nodes
    should render a summary node rather than an unmanageable diagram."""
    n_nodes = _PATH_FOCUSED_NODE_CAP + 5
    nodes = [
        {"node_id": f"node{i}", "name": f"n{i}", "node_type": "service"}
        for i in range(n_nodes)
    ]
    edges = [
        {"edge_id": f"e{i}", "from": f"node{i}", "to": f"node{i+1}",
         "edge_type": "trusts"}
        for i in range(n_nodes - 1)
    ]
    paths = [{"edges": [f"e{i}" for i in range(n_nodes - 1)]}]
    out = _build_mermaid_path_focused(
        {"nodes": nodes, "edges": edges}, paths,
    )
    assert "too_large" in out
    assert str(n_nodes) in out


def test_build_mermaid_path_focused_renders_small_subgraph():
    nodes = [
        {"node_id": "att", "name": "attacker", "node_type": "attacker_position"},
        {"node_id": "cj",  "name": "crown",    "node_type": "crown_jewel"},
    ]
    edges = [{"edge_id": "e0", "from": "att", "to": "cj",
              "edge_type": "compromisable_via_finding"}]
    paths = [{"edges": ["e0"]}]
    out = _build_mermaid_path_focused(
        {"nodes": nodes, "edges": edges}, paths,
    )
    assert "too_large" not in out
    assert "graph LR" in out


def test_build_mermaid_path_focused_returns_none_on_empty_paths():
    out = _build_mermaid_path_focused({"nodes": [], "edges": []}, [])
    assert out is None
