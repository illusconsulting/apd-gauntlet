# tests/unit/report/test_tier4_mermaid_identity.py
"""Regression tests for Mermaid identity prefix + broadened node-id charset (T4-B)."""
from __future__ import annotations

from apd_gauntlet.report.transform import (
    _NODE_ID_OK,
    _build_mermaid,
    _build_mermaid_path_focused,
    _safe_node_id,
)


def test_node_id_ok_accepts_dot():
    assert _NODE_ID_OK.match("foo.bar")


def test_node_id_ok_accepts_colon():
    assert _NODE_ID_OK.match("foo:bar")


def test_node_id_ok_accepts_slash():
    assert _NODE_ID_OK.match("foo/bar")


def test_node_id_ok_accepts_combined():
    assert _NODE_ID_OK.match("chainguard.dev/app:web")


def test_node_id_ok_still_rejects_spaces():
    assert not _NODE_ID_OK.match("foo bar")


def test_node_id_ok_still_rejects_special_chars():
    assert not _NODE_ID_OK.match("foo<bar")
    assert not _NODE_ID_OK.match("foo[bar")


def test_safe_node_id_passes_dot_colon_slash_through():
    """Pre-T4-B these would route through the hash-fallback path."""
    assert _safe_node_id("chainguard.dev/app:web") == "chainguard.dev/app:web"
    assert _safe_node_id("k8s.io/pod-1") == "k8s.io/pod-1"


def test_build_mermaid_identity_node_uses_asymmetric_shape():
    graph = {
        "nodes": [
            {"node_id": "u1", "name": "user-1", "node_type": "identity"},
            {"node_id": "s1", "name": "svc",    "node_type": "service"},
        ],
        "edges": [{"from": "u1", "to": "s1", "edge_type": "trusts"}],
    }
    out = _build_mermaid(graph)
    # Identity node should render with the asymmetric flag shape '>...]'.
    assert ">\"user-1\"]" in out
    # Service node stays as rectangle '[...]'.
    assert "[\"svc\"]" in out


def test_build_mermaid_distinguishes_identity_from_asset():
    """Pre-T4-B both rendered as generic rectangles; now they're visually distinct."""
    graph = {
        "nodes": [
            {"node_id": "u1", "name": "user", "node_type": "identity"},
            {"node_id": "a1", "name": "asset","node_type": "asset"},
        ],
        "edges": [],
    }
    out = _build_mermaid(graph)
    lines = [ln.strip() for ln in out.split("\n") if ln.strip()]
    u_line = next(ln for ln in lines if "user" in ln)
    a_line = next(ln for ln in lines if "asset" in ln)
    # Different open/close characters → different shapes.
    assert u_line.startswith("u1>") and u_line.endswith("]")
    assert a_line.startswith("a1[") and a_line.endswith("]")
    assert u_line != a_line.replace("asset", "user").replace("a1", "u1")


def test_build_mermaid_path_focused_identity_node_uses_asymmetric_shape():
    nodes = [
        {"node_id": "u1", "name": "user", "node_type": "identity"},
        {"node_id": "cj", "name": "cj",   "node_type": "crown_jewel"},
    ]
    edges = [{"edge_id": "e0", "from": "u1", "to": "cj",
              "edge_type": "compromisable_via_finding"}]
    paths = [{"edges": ["e0"]}]
    out = _build_mermaid_path_focused({"nodes": nodes, "edges": edges}, paths)
    assert ">\"user\"]" in out


def test_build_mermaid_preserves_dot_colon_slash_in_node_id():
    graph = {
        "nodes": [
            {"node_id": "chainguard.dev/app:web", "name": "web",
             "node_type": "service"},
        ],
        "edges": [],
    }
    out = _build_mermaid(graph)
    # The raw ID survives untouched (no hash-fallback).
    assert "chainguard.dev/app:web[" in out
