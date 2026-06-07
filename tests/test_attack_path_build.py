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


# ---------------------------------------------------------------------------
# #84: crown-jewel pattern-token wiring to controlled data_classifications,
# optional realizes_crown_jewels field, and zero-wire diagnostic
# ---------------------------------------------------------------------------


def _g_with_assets(*assets):
    """Build a graph holding only asset nodes for direct _add_crown_jewels tests.

    Each asset is (name, data_classifications, extra_kwargs).
    """
    g = Graph()
    for name, classes, extra in assets:
        g.add_node(
            Node(
                node_id=stable_id("asset", name),
                node_type="asset",
                name=name,
                provenance={"source": "asset_inventory"},
                confidence="high",
                data_classifications=tuple(classes),
                **extra,
            )
        )
    return g


def test_jewel_candidate_tokens_strips_generic_suffixes():
    from apd_gauntlet.attack_path.build import _jewel_candidate_tokens

    toks = _jewel_candidate_tokens("pii_profile_store")
    # full pattern + suffix-stripped semantic head + split-on-underscore parts
    assert "pii_profile_store" in toks
    assert "pii_profile" in toks  # _store suffix stripped
    assert "pii" in toks  # head split on _
    # a single-token classification like "pii" is reachable

    toks2 = _jewel_candidate_tokens("tool_execution_capability")
    assert "tool_execution_capability" in toks2
    assert "tool_execution" in toks2  # _capability stripped


def test_crown_jewel_semantic_token_wires_to_classification():
    from apd_gauntlet.attack_path.build import _add_crown_jewels

    # jewel pattern pii_profile_store -> semantic head "pii" via _store strip + split.
    g = _g_with_assets(("profile-db", ["pii"], {}))
    orphans = _add_crown_jewels(g, ["pii_profile_store"], {}, inventory={})
    jewel_id = stable_id("jewel", "pii_profile_store")
    asset_id = stable_id("asset", "profile-db")
    edges = [
        e
        for e in g._edges.values()
        if e.edge_type == "data_resides_on"
        and e.from_node == asset_id
        and e.to_node == jewel_id
    ]
    assert edges, "asset with pii classification should wire to pii_profile_store jewel"
    assert orphans == [], "jewel has an inbound edge, so it is not an orphan"


def test_realizes_crown_jewels_field_wires_explicitly():
    from apd_gauntlet.attack_path.build import _add_crown_jewels

    # The asset declares it realizes an abstract jewel token; no classification match.
    g = _g_with_assets(("agent-runtime", ["internal"], {}))
    inventory = {
        "assets": [
            {
                "asset_id": stable_id("asset", "agent-runtime"),
                "name": "agent-runtime",
                "realizes_crown_jewels": ["tool_execution_capability"],
            }
        ]
    }
    orphans = _add_crown_jewels(
        g, ["tool_execution_capability"], {}, inventory=inventory
    )
    jewel_id = stable_id("jewel", "tool_execution_capability")
    asset_id = stable_id("asset", "agent-runtime")
    edges = [
        e
        for e in g._edges.values()
        if e.edge_type == "data_resides_on"
        and e.from_node == asset_id
        and e.to_node == jewel_id
    ]
    assert edges, "realizes_crown_jewels should wire an explicit data_resides_on edge"
    assert orphans == []


def test_declared_jewel_with_no_match_is_orphan_diagnostic_not_crash():
    from apd_gauntlet.attack_path.build import _add_crown_jewels

    g = _g_with_assets(("billing-svc", ["internal"], {}))
    edges_before = len(g._edges)
    orphans = _add_crown_jewels(
        g, ["genome_sequence_vault"], {}, inventory={}
    )
    # No invented edges
    assert len(g._edges) == edges_before, "orphan jewel must not invent edges"
    assert "genome_sequence_vault" in orphans


def test_no_over_wiring_unrelated_classification():
    from apd_gauntlet.attack_path.build import _add_crown_jewels

    # asset classified "internal"; jewel pattern pii_profile_store -> tokens {pii,...}.
    g = _g_with_assets(("logs-bucket", ["internal"], {}))
    orphans = _add_crown_jewels(g, ["pii_profile_store"], {}, inventory={})
    data_edges = [e for e in g._edges.values() if e.edge_type == "data_resides_on"]
    assert data_edges == [], "unrelated classification must NOT wire to the jewel"
    assert "pii_profile_store" in orphans


def test_existing_name_realization_still_works():
    """Regression: an inventory asset whose NAME equals the jewel pattern still
    realizes that jewel via _wire_realized_crown_jewels — even when its
    data_classifications do NOT match the pattern's semantic tokens."""
    from apd_gauntlet.attack_path.build import _add_crown_jewels

    # Asset is named exactly "phi_store" but classified only "internal", so the
    # classification-alias path can NOT fire — only name realization can.
    g = _g_with_assets(("phi_store", ["internal"], {}))
    orphans = _add_crown_jewels(g, ["phi_store"], {}, inventory={})
    # _add_crown_jewels alone sees no classification match -> reports orphan...
    assert "phi_store" in orphans
    # ...but the downstream name-realization pass wires it.
    _wire_realized_crown_jewels(g)
    jewel_id = stable_id("jewel", "phi_store")
    asset_id = stable_id("asset", "phi_store")
    edges = [
        e
        for e in g._edges.values()
        if e.edge_type == "data_resides_on"
        and e.from_node == asset_id
        and e.to_node == jewel_id
    ]
    assert edges, "name-equals-jewel realization must still wire a data_resides_on edge"


def test_build_result_surfaces_orphan_crown_jewels(tmp_path: Path) -> None:
    """build_graph must expose orphan crown jewels (zero inbound edges) so the
    silent-orphan-sink condition is visible — without blocking the build."""
    run = tmp_path / "run"
    shutil.copytree(FIXTURE_ROOT, run)
    cfg = run / ".apd-run.yaml"
    # Add an unmatchable jewel alongside phi_store.
    cfg.write_text(
        cfg.read_text().replace(
            "crown_jewels:\n  - phi_store",
            "crown_jewels:\n  - phi_store\n  - unmatched_secret_vault",
        )
    )
    result = build_graph(run)
    assert "unmatched_secret_vault" in result.orphan_crown_jewels
    # phi_store wires to member-record-store (phi classification) -> not orphan
    assert "phi_store" not in result.orphan_crown_jewels


def test_minimal_run_phi_store_wires_via_classification_alias() -> None:
    """The minimal-run fixture's phi_store jewel must gain an inbound
    data_resides_on edge from member-record-store (data_classifications:[phi])
    purely via the classification-alias path (semantic head of phi_store == phi)."""
    graph = build_graph(FIXTURE_ROOT).graph
    jewel_id = stable_id("jewel", "phi_store")
    inbound = [e for e in graph._edges.values() if e.to_node == jewel_id]
    assert inbound, "phi_store should have at least one inbound data_resides_on edge"
