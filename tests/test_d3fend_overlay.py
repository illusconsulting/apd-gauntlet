"""Tests for D3FEND defensive overlay computation (Task C-12).

Validates the pure data transformation that, given bottleneck edges plus
findings (for ATT&CK technique extraction) plus capabilities (for existing
D3FEND backing), produces the ``bottleneck_overlays[]`` array conforming
to ``defense-graph.schema.json``.
"""
from __future__ import annotations

from apd_gauntlet.attack_path.d3fend_overlay import (
    _lookup_d3fend_counters,
    build_overlays,
)
from apd_gauntlet.attack_path.graph import Edge, Graph, Node

# NOTE: D3FEND data shape matches tools/apd_gauntlet/data/d3fend.json —
# top-level key is "entries", inner field is "d3fend_id" (NOT
# "techniques"/"id" as the original plan skeleton suggested).
D3FEND_DATA = {
    "entries": [
        {
            "d3fend_id": "D3-NTSA",
            "name": "Network Traffic Signature Analysis",
            "counters_attack": ["T1078", "T1190"],
        },
        {
            "d3fend_id": "D3-IBCA",
            "name": "Inbound Session Volume Analysis",
            "counters_attack": ["T1078"],
        },
        {
            "d3fend_id": "D3-MFA",
            "name": "Multi-factor Authentication",
            "counters_attack": ["T1078", "T1110"],
        },
    ]
}


# ---------------------------------------------------------------------------
# _lookup_d3fend_counters unit tests
# ---------------------------------------------------------------------------

def test_lookup_d3fend_counters_returns_only_techniques_that_counter_input() -> None:
    counters = _lookup_d3fend_counters(["T1078"], D3FEND_DATA)
    ids = {c["d3fend_id"] for c in counters}
    assert ids == {"D3-NTSA", "D3-IBCA", "D3-MFA"}


def test_lookup_d3fend_counters_filters_by_intersection() -> None:
    counters = _lookup_d3fend_counters(["T1190"], D3FEND_DATA)
    ids = {c["d3fend_id"] for c in counters}
    assert ids == {"D3-NTSA"}


def test_lookup_d3fend_counters_handles_empty() -> None:
    assert _lookup_d3fend_counters([], D3FEND_DATA) == []


# ---------------------------------------------------------------------------
# build_overlays integration tests
# ---------------------------------------------------------------------------

def _bottleneck_graph() -> tuple[Graph, str]:
    """Build a minimal graph with one ``compromisable_via_finding`` edge.

    Returns the graph and the edge_id of the finding-edge so each test can
    construct ``bottleneck_edges`` against it.
    """
    g = Graph()
    atk = Node(
        "atk-aaaaaaaa", "attacker_position", "external",
        {"source": "domain_default"}, "high",
    )
    jwl = Node(
        "jewel-aaaaaaaa", "crown_jewel", "phi-store",
        {"source": "domain_default"}, "high",
    )
    g.add_node(atk)
    g.add_node(jwl)
    g.add_edge(Edge(
        "edge-aaaaaaaa", "compromisable_via_finding",
        "atk-aaaaaaaa", "jewel-aaaaaaaa",
        {"source": "finding"}, "high", 1,
        finding_id="finding-deadbeef",
    ))
    return g, "edge-aaaaaaaa"


def test_build_overlays_extracts_attack_techniques_from_compromisable_edges() -> None:
    """A finding-edge with two ATT&CK techniques produces an overlay whose
    ``exposed_attack_techniques`` is the sorted union of those techniques.
    """
    g, edge_id = _bottleneck_graph()
    findings_by_id = {
        "finding-deadbeef": {
            "id": "finding-deadbeef",
            "control_mappings": {
                "mitre_attack": [
                    {"technique": "T1078"},
                    {"technique": "T1110"},
                ],
            },
        },
    }
    bottleneck_edges = {edge_id: ["path-aaaaaaaa", "path-bbbbbbbb"]}

    overlays = build_overlays(
        paths=[],
        bottleneck_edges=bottleneck_edges,
        graph=g,
        findings_by_id=findings_by_id,
        capabilities=[],
        d3fend_data=D3FEND_DATA,
    )

    assert len(overlays) == 1
    overlay = overlays[0]
    assert overlay["edge_id"] == edge_id
    assert overlay["paths_traversing"] == 2
    assert overlay["exposed_attack_techniques"] == ["T1078", "T1110"]


def test_build_overlays_marks_existing_capability_backing() -> None:
    """A capability whose D3FEND mapping intersects the candidate list moves
    that D3FEND id from ``net_new_d3fend`` to ``existing_capability_backing``.
    """
    g, edge_id = _bottleneck_graph()
    findings_by_id = {
        "finding-deadbeef": {
            "id": "finding-deadbeef",
            "control_mappings": {
                "mitre_attack": [{"technique": "T1078"}],
            },
        },
    }
    capabilities = [
        {
            "id": "cap-12345678",
            "control_mappings": {
                "d3fend": [
                    {
                        "technique": "D3-MFA",
                        "counters_attack": ["T1078"],
                        "rationale": "MFA blocks valid-account abuse",
                    },
                ],
            },
        },
    ]
    bottleneck_edges = {edge_id: ["path-aaaaaaaa", "path-bbbbbbbb"]}

    overlays = build_overlays(
        paths=[],
        bottleneck_edges=bottleneck_edges,
        graph=g,
        findings_by_id=findings_by_id,
        capabilities=capabilities,
        d3fend_data=D3FEND_DATA,
    )

    assert len(overlays) == 1
    overlay = overlays[0]
    assert {"d3fend_id": "D3-MFA", "capability_ids": ["cap-12345678"]} \
        in overlay["existing_capability_backing"]
    assert "D3-MFA" not in overlay["net_new_d3fend"]


def test_build_overlays_net_new_d3fend_excludes_already_backed() -> None:
    """Bottleneck exposes T1078; all three D3FEND techniques counter T1078;
    one capability provides D3-MFA → ``net_new == [D3-IBCA, D3-NTSA]`` (sorted).
    """
    g, edge_id = _bottleneck_graph()
    findings_by_id = {
        "finding-deadbeef": {
            "id": "finding-deadbeef",
            "control_mappings": {
                "mitre_attack": [{"technique": "T1078"}],
            },
        },
    }
    capabilities = [
        {
            "id": "cap-12345678",
            "control_mappings": {
                "d3fend": [
                    {
                        "technique": "D3-MFA",
                        "counters_attack": ["T1078"],
                        "rationale": "MFA blocks valid-account abuse",
                    },
                ],
            },
        },
    ]
    bottleneck_edges = {edge_id: ["path-aaaaaaaa", "path-bbbbbbbb"]}

    overlays = build_overlays(
        paths=[],
        bottleneck_edges=bottleneck_edges,
        graph=g,
        findings_by_id=findings_by_id,
        capabilities=capabilities,
        d3fend_data=D3FEND_DATA,
    )

    assert len(overlays) == 1
    overlay = overlays[0]
    assert overlay["net_new_d3fend"] == ["D3-IBCA", "D3-NTSA"]
    backing_ids = {b["d3fend_id"] for b in overlay["existing_capability_backing"]}
    assert backing_ids == {"D3-MFA"}
