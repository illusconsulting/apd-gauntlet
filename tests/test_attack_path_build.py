"""Tests for the attack-path graph builder.

Builds a Graph from a minimal-run fixture and asserts the expected
nodes / edges / provenance markers per Task C-10.
"""
from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from apd_gauntlet.attack_path.build import (
    BuilderBlocked,
    _node_name_index,
    _wire_realized_crown_jewels,
    build_graph,
)
from apd_gauntlet.attack_path.graph import Graph, Node, stable_id

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


def test_authored_tm_edges_carry_inferred_provenance(tmp_path: Path) -> None:
    """A canonical TM emitted by the author agent (generated_by:
    threat_model_author) must NOT be presented as operator-DECLARED TM
    coverage. Its network_reachable edges carry provenance.source
    'threat_model_inferred', distinguishing them from a recon-parsed
    (operator-declared) TM which stays 'threat_model'."""
    run = tmp_path / "run"
    shutil.copytree(FIXTURE_ROOT, run)
    tm = run / "00-context" / "threat-model-normalized.yaml"
    tm.write_text(
        tm.read_text().replace(
            "generated_by: threat_model_recon",
            "generated_by: threat_model_author",
            1,
        )
    )
    graph = build_graph(run).graph
    inferred = [
        e for e in graph._edges.values()
        if e.provenance.get("source") == "threat_model_inferred"
    ]
    declared = [
        e for e in graph._edges.values()
        if e.provenance.get("source") == "threat_model"
    ]
    assert inferred, "authored TM must yield threat_model_inferred edges"
    assert not declared, "authored TM must NOT yield declared threat_model edges"


def test_recon_tm_edges_stay_declared_golden_unchanged() -> None:
    """Regression guard: the recon-parsed minimal-run fixture
    (generated_by: threat_model_recon) keeps declared 'threat_model'
    provenance — the author guard must not alter recon golden behavior."""
    graph = build_graph(FIXTURE_ROOT).graph
    declared = [
        e for e in graph._edges.values()
        if e.provenance.get("source") == "threat_model"
    ]
    inferred = [
        e for e in graph._edges.values()
        if e.provenance.get("source") == "threat_model_inferred"
    ]
    assert declared, "recon TM must keep declared threat_model provenance"
    assert not inferred, "recon TM must NOT be downgraded to inferred"


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


def test_builder_result_reports_all_sources_used() -> None:
    """`BuildResult.sources_used` must enumerate every artifact that
    contributed to the graph — downstream consumers (Task C-11, C-17 agent)
    rely on it for attribution.
    """
    result = build_graph(FIXTURE_ROOT)
    assert set(result.sources_used) >= {
        "asset_inventory",
        "findings",
        "capabilities",
        "threat_model_normalized",
        "code_evidence_index",
    }


def test_builder_raises_on_case_insensitive_node_name_collision(
    tmp_path: Path,
) -> None:
    """Two nodes whose names differ only in case make case-insensitive
    text matching ambiguous — the builder must raise rather than silently
    collapse them in `_node_name_index`.
    """
    run = tmp_path / "run"
    shutil.copytree(FIXTURE_ROOT, run)
    inv = run / "00-context" / "asset-inventory.yaml"
    inv.write_text(
        inv.read_text().replace(
            'name: "adjudication-service"',
            'name: "Claim-Ingress"',
            1,
        )
    )
    with pytest.raises(BuilderBlocked, match="case-insensitive"):
        build_graph(run)


def test_load_domain_unions_multidomain_defaults(tmp_path: Path) -> None:
    from apd_gauntlet.attack_path.build import _load_domain
    for name, jewel in (("alpha", "alpha_store"), ("beta", "beta_store")):
        d = tmp_path / "domains" / name
        d.mkdir(parents=True)
        (d / "domain.yaml").write_text(
            f"name: {name}\n"
            "crown_jewels:\n"
            f"  - pattern: {jewel}\n    description: x\n"
            "  - pattern: shared_store\n    description: shared\n"
            "attacker_positions:\n"
            f"  - position: {name}_attacker\n    description: y\n"
        )
    dom = _load_domain(tmp_path, {"domains": ["alpha", "beta"]})
    assert [j["pattern"] for j in dom["crown_jewels"]] == [
        "alpha_store", "shared_store", "beta_store"
    ]
    assert [p["position"] for p in dom["attacker_positions"]] == ["alpha_attacker", "beta_attacker"]
    assert dom["name"] == "alpha+beta"


def test_builder_skips_prior_attack_path_findings_on_recursive_scan(
    tmp_path: Path,
) -> None:
    """The recursive ``**/*.findings.yaml`` glob will also match
    ``40-synthesis/attack-path.findings.yaml`` from a previous run. The
    builder must skip that file so re-runs do not ingest their own output
    as a "specialist finding."
    """
    run = tmp_path / "run"
    shutil.copytree(FIXTURE_ROOT, run)
    synth = run / "40-synthesis"
    synth.mkdir(parents=True, exist_ok=True)
    # A poison record that, if ingested, would attach to a `compromisable_via_finding`
    # edge — we assert that no edge with this id appears in the graph.
    (synth / "attack-path.findings.yaml").write_text(
        "finding:\n"
        "  - id: apath-poison\n"
        "    detail: 'adjudication-service to member-record-store'\n"
        "    severity: high\n"
        "    confidence: high\n"
    )
    graph = build_graph(run).graph
    for e in graph._edges.values():
        assert e.finding_id != "apath-poison", (
            "builder must not ingest 40-synthesis/attack-path.findings.yaml"
        )


# ---------------------------------------------------------------------------
# F5 / C5: crown_jewel <-> asset name collision resolution
# ---------------------------------------------------------------------------


def _g_with_jewel_asset_collision():
    g = Graph()
    g.add_node(Node(node_id=stable_id("asset", "phi_store"), node_type="asset",
                    name="phi_store", provenance={"source": "asset_inventory"},
                    confidence="high"))
    g.add_node(Node(node_id=stable_id("jewel", "phi_store"), node_type="crown_jewel",
                    name="phi_store", provenance={"source": "domain_default"},
                    confidence="high"))
    return g


def test_node_name_index_resolves_jewel_asset_collision_to_asset():
    g = _g_with_jewel_asset_collision()
    index = _node_name_index(g)  # must NOT raise
    assert index["phi_store"] == stable_id("asset", "phi_store")


def test_node_name_index_still_blocks_same_type_collision():
    g = Graph()
    g.add_node(Node(node_id=stable_id("asset", "a"), node_type="asset", name="dup",
                    provenance={"source": "asset_inventory"}, confidence="high"))
    g.add_node(Node(node_id=stable_id("asset", "b"), node_type="asset", name="DUP",
                    provenance={"source": "asset_inventory"}, confidence="high"))
    with pytest.raises(BuilderBlocked):
        _node_name_index(g)


def test_wire_realized_crown_jewels_emits_data_resides_on_edge():
    g = _g_with_jewel_asset_collision()
    _wire_realized_crown_jewels(g)
    edges = [e for e in g._edges.values() if e.edge_type == "data_resides_on"]
    assert edges, "expected a data_resides_on edge linking the asset to its jewel"
    e = edges[0]
    assert e.from_node == stable_id("asset", "phi_store")
    assert e.to_node == stable_id("jewel", "phi_store")


def test_wire_realized_crown_jewels_is_idempotent():
    g = _g_with_jewel_asset_collision()
    _wire_realized_crown_jewels(g)
    _wire_realized_crown_jewels(g)  # second call must not raise on duplicate edge
    edges = [e for e in g._edges.values() if e.edge_type == "data_resides_on"]
    assert len(edges) == 1
