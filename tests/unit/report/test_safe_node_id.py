# tests/unit/report/test_safe_node_id.py
"""Regression tests for the _safe_node_id / _NODE_ID_OK helpers.

These helpers outlived the Mermaid renderer: _safe_node_id still produces
canvas-graph node ids for the Cytoscape threat-surface map (boundary +
asset ids), so its charset + collision-resistance contract must hold.
"""
from __future__ import annotations

from apd_gauntlet.report.transform import (
    _NODE_ID_OK,
    _safe_node_id,
)


def test_safe_node_id_passes_through_valid_id():
    assert _safe_node_id("valid_id_123") == "valid_id_123"


def test_safe_node_id_hashes_invalid_id():
    out = _safe_node_id("not valid has space")
    assert out.startswith("n_")
    assert len(out) == 10  # 'n_' + 8 hex chars


def test_safe_node_id_deterministic_for_same_raw():
    """Same raw + seed -> same synthetic id (essential for id stability)."""
    a = _safe_node_id("foo bar", fallback_seed="asset_graph")
    b = _safe_node_id("foo bar", fallback_seed="asset_graph")
    assert a == b


def test_safe_node_id_distinguishes_seeds():
    """Same raw under different seeds -> different synthetic ids."""
    a = _safe_node_id("foo bar", fallback_seed="asset_graph")
    b = _safe_node_id("foo bar", fallback_seed="path_focused")
    assert a != b


def test_safe_node_id_distinguishes_invalid_raw_ids():
    """Two different invalid raw ids must NOT collide on the synthetic."""
    a = _safe_node_id("foo bar")
    b = _safe_node_id("baz qux")
    assert a != b


def test_safe_node_id_empty_raw():
    out = _safe_node_id("")
    assert out.startswith("n_")


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
    assert _safe_node_id("chainguard.dev/app:web") == "chainguard.dev/app:web"
    assert _safe_node_id("k8s.io/pod-1") == "k8s.io/pod-1"
