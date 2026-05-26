"""Tests for the attack-path graph builder.

Builds a Graph from a minimal-run fixture and asserts the expected
nodes / edges / provenance markers per Task C-10.
"""
from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from apd_gauntlet.attack_path.build import BuilderBlocked, build_graph

FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "attack_path" / "minimal-run"


def test_builder_emits_attacker_position_and_crown_jewel_nodes() -> None:
    graph = build_graph(FIXTURE_ROOT).graph
    assert any(
        n.node_type == "attacker_position" and n.name == "external"
        for n in graph.nodes_by_type("attacker_position")
    )
    assert any(
        n.node_type == "crown_jewel" and n.name == "phi_store"
        for n in graph.nodes_by_type("crown_jewel")
    )


def test_builder_emits_asset_nodes_from_inventory() -> None:
    graph = build_graph(FIXTURE_ROOT).graph
    assets = graph.nodes_by_type("asset")
    assert len(assets) >= 3


def test_builder_emits_compromisable_edges_from_findings() -> None:
    graph = build_graph(FIXTURE_ROOT).graph
    comp_edges = [
        e for e in graph._edges.values() if e.edge_type == "compromisable_via_finding"
    ]
    assert comp_edges
    assert all(e.finding_id for e in comp_edges)


def test_builder_emits_capability_edges_from_capabilities() -> None:
    graph = build_graph(FIXTURE_ROOT).graph
    mit_edges = [
        e for e in graph._edges.values() if e.edge_type == "mitigated_by_capability"
    ]
    assert mit_edges
    assert all(e.capability_id for e in mit_edges)


def test_builder_threat_model_edges_carry_threat_model_provenance() -> None:
    graph = build_graph(FIXTURE_ROOT).graph
    tm_provenance_edges = [
        e for e in graph._edges.values() if e.provenance.get("source") == "threat_model"
    ]
    assert tm_provenance_edges, (
        "threat-model entries should produce at least one edge with threat_model provenance"
    )


def test_builder_skips_when_no_crown_jewels_declared(tmp_path: Path) -> None:
    run = tmp_path / "run"
    shutil.copytree(FIXTURE_ROOT, run)
    cfg = run / ".apd-run.yaml"
    cfg.write_text(
        cfg.read_text().replace("crown_jewels:\n  - phi_store", "crown_jewels: []")
    )
    dom = run / "domains" / "pbm.yaml"
    dom.write_text(dom.read_text().replace("phi_store", "REMOVED"))
    with pytest.raises(BuilderBlocked, match="no crown jewels"):
        build_graph(run)


def test_builder_skips_when_no_attacker_positions_declared(tmp_path: Path) -> None:
    run = tmp_path / "run"
    shutil.copytree(FIXTURE_ROOT, run)
    cfg = run / ".apd-run.yaml"
    cfg.write_text(
        cfg.read_text().replace(
            "attacker_positions:\n  - external", "attacker_positions: []"
        )
    )
    dom = run / "domains" / "pbm.yaml"
    dom.write_text(dom.read_text().replace("- position: external", "# (removed)"))
    with pytest.raises(BuilderBlocked, match="no attacker positions"):
        build_graph(run)
