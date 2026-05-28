# tests/unit/report/test_transform_attack_paths.py
from __future__ import annotations

import pathlib

from apd_gauntlet.report.loader import load_run
from apd_gauntlet.report.transform import attack_paths_data


def test_returns_none_when_artifacts_missing(tmp_path: pathlib.Path) -> None:
    # Build a minimal artifacts via load_run requires a full run; instead build one
    # by hand to exercise the missing-data branch.
    from apd_gauntlet.report.loader import RunArtifacts
    art = RunArtifacts(
        run_id="r", framework_version="1", domain_pack_name="p", domain_pack_version="1",
        subject="s", date="2026-01-01",
        asset_inventory={}, deduped_findings=[], deduped_capabilities=[],
        contradictions=[], contradictions_notes=None,
        severity_disagreements=[], severity_disagreements_notes=None,
        nist_coverage={}, attack_exposure={}, apd_coverage_matrix={},
        attack_paths=None, asset_graph=None, defense_graph=None,
        attack_path_findings=[], report_data=None,
    )
    assert attack_paths_data(art) is None


def test_returns_mermaid_string(example_run: pathlib.Path) -> None:
    artifacts = load_run(example_run)
    data = attack_paths_data(artifacts)
    assert data is not None
    assert isinstance(data["mermaid"], str)
    assert "graph" in data["mermaid"].lower()


def test_path_pairs_present(example_run: pathlib.Path) -> None:
    artifacts = load_run(example_run)
    data = attack_paths_data(artifacts)
    assert data is not None
    pairs = data["pairs"]
    # crAPI's attack-paths.yaml carries zero paths due to sparse asset→finding
    # edge connectivity; we assert structure not count.
    assert isinstance(pairs, list)
    for pair in pairs:
        assert {
            "attacker_position", "attacker_position_name",
            "crown_jewel", "crown_jewel_name",
            "paths",
        }.issubset(pair.keys())
        assert isinstance(pair["attacker_position_name"], str)
        assert isinstance(pair["crown_jewel_name"], str)
        for p in pair["paths"]:
            assert {
                "path_id", "hop_count", "severity_sum", "edges", "bottleneck_edges"
            }.issubset(p.keys())


def test_bottleneck_overlays_present_when_defense_graph(example_run: pathlib.Path) -> None:
    artifacts = load_run(example_run)
    data = attack_paths_data(artifacts)
    assert data is not None
    assert isinstance(data["bottleneck_overlays"], list)
    # bottleneck_threshold is passed through from enumeration_parameters (may be None)
    assert "bottleneck_threshold" in data
    # asset_graph_summary must be fully populated
    assert "asset_graph_summary" in data
    gs = data["asset_graph_summary"]
    for key in (
        "node_count", "edge_count", "attacker_position_count", "crown_jewel_count",
        "asset_count", "identity_count",
        "trust_boundary_edge_count", "finding_derived_edge_count", "capability_derived_edge_count",
    ):
        assert key in gs, f"asset_graph_summary missing key: {key}"
        assert isinstance(gs[key], int), f"asset_graph_summary[{key!r}] must be int"


def test_coverage_summary_card(example_run: pathlib.Path) -> None:
    artifacts = load_run(example_run)
    data = attack_paths_data(artifacts)
    assert data is not None
    s = data["summary"]
    assert s["total_paths"] >= 0
    assert s["total_pairs"] >= 0


def test_pairs_empty_explanation_present_when_pairs_empty(example_run: pathlib.Path) -> None:
    """crAPI fixture has 0 paths; transform must attach a pairs_empty_explanation."""
    artifacts = load_run(example_run)
    data = attack_paths_data(artifacts)
    assert data is not None
    # crAPI has an asset graph with nodes/edges but zero enumerated paths.
    if data["pairs"]:
        # If paths were added in a future fixture update, explanation must be absent/None.
        assert data.get("pairs_empty_explanation") is None
    else:
        assert "pairs_empty_explanation" in data
        expl = data["pairs_empty_explanation"]
        assert isinstance(expl, str) and len(expl) > 20
        # Explanation must mention the graph counts.
        assert data["asset_graph_summary"]["node_count"] > 0
        node_count = data["asset_graph_summary"]["node_count"]
        edge_count = data["asset_graph_summary"]["edge_count"]
        assert str(node_count) in expl
        assert str(edge_count) in expl


def test_pairs_empty_explanation_absent_when_pairs_non_empty() -> None:
    """When paths exist, pairs_empty_explanation must not be set."""
    from apd_gauntlet.report.loader import RunArtifacts
    art = RunArtifacts(
        run_id="r", framework_version="1", domain_pack_name="p", domain_pack_version="1",
        subject="s", date="2026-01-01",
        asset_inventory={}, deduped_findings=[], deduped_capabilities=[],
        contradictions=[], contradictions_notes=None,
        severity_disagreements=[], severity_disagreements_notes=None,
        nist_coverage={}, attack_exposure={}, apd_coverage_matrix={},
        attack_paths={
            "paths": [
                {
                    "attacker_position": "internet",
                    "crown_jewel": "db",
                    "path_id": "p1",
                    "hop_count": 1,
                    "feasibility": "high",
                    "severity_sum": 8,
                    "mitigation_count": 0,
                    "edges": ["e1"],
                    "bottleneck_edges": [],
                }
            ]
        },
        asset_graph={
            "nodes": [
                {"node_id": "internet", "name": "Internet", "node_type": "attacker_position"},
                {"node_id": "db", "name": "DB", "node_type": "crown_jewel"},
            ],
            "edges": [{"from": "internet", "to": "db"}],
        },
        defense_graph=None,
        attack_path_findings=[], report_data=None,
    )
    data = attack_paths_data(art)
    assert data is not None
    assert len(data["pairs"]) == 1
    assert data.get("pairs_empty_explanation") is None


def test_asset_graph_summary_always_present(example_run: pathlib.Path) -> None:
    """asset_graph_summary must be present whenever attack_paths_data returns non-None."""
    artifacts = load_run(example_run)
    data = attack_paths_data(artifacts)
    assert data is not None
    assert "asset_graph_summary" in data
    gs = data["asset_graph_summary"]
    assert isinstance(gs["node_count"], int)
    assert isinstance(gs["edge_count"], int)


def test_edges_detailed_carries_node_names_and_edge_type() -> None:
    """edges_detailed must carry from_name, to_name, edge_type, and finding_id
    when the edge is compromisable_via_finding."""
    from apd_gauntlet.report.loader import RunArtifacts

    art = RunArtifacts(
        run_id="r", framework_version="1", domain_pack_name="p", domain_pack_version="1",
        subject="s", date="2026-01-01",
        asset_inventory={}, deduped_findings=[], deduped_capabilities=[],
        contradictions=[], contradictions_notes=None,
        severity_disagreements=[], severity_disagreements_notes=None,
        nist_coverage={}, attack_exposure={}, apd_coverage_matrix={},
        attack_paths={
            "enumeration_parameters": {"bottleneck_threshold": 5},
            "paths": [
                {
                    "attacker_position": "atk-001",
                    "crown_jewel": "jewel-001",
                    "path_id": "p-001",
                    "hop_count": 1,
                    "feasibility": "high",
                    "severity_sum": 8,
                    "mitigation_count": 0,
                    "edges": ["edge-001"],
                    "bottleneck_edges": [],
                }
            ],
        },
        asset_graph={
            "nodes": [
                {
                    "node_id": "atk-001", "name": "Compromised Admin",
                    "node_type": "attacker_position",
                },
                {
                    "node_id": "jewel-001", "name": "Secret Key Store",
                    "node_type": "crown_jewel",
                },
            ],
            "edges": [
                {
                    "edge_id": "edge-001",
                    "edge_type": "compromisable_via_finding",
                    "from": "atk-001",
                    "to": "jewel-001",
                    "finding_id": "conf-abc123",
                    "confidence": "high",
                }
            ],
        },
        defense_graph=None,
        attack_path_findings=[], report_data=None,
    )
    data = attack_paths_data(art)
    assert data is not None
    assert len(data["pairs"]) == 1
    pair = data["pairs"][0]
    assert pair["attacker_position_name"] == "Compromised Admin"
    assert pair["crown_jewel_name"] == "Secret Key Store"
    assert len(pair["paths"]) == 1
    path = pair["paths"][0]
    assert "edges_detailed" in path
    assert len(path["edges_detailed"]) == 1
    ed = path["edges_detailed"][0]
    assert ed["from_name"] == "Compromised Admin"
    assert ed["to_name"] == "Secret Key Store"
    assert ed["edge_type"] == "compromisable_via_finding"
    assert ed["finding_id"] == "conf-abc123"
    assert ed["capability_id"] is None
    assert ed["is_bottleneck"] is False


def test_attack_paths_max_edge_traversal_count_is_int() -> None:
    """max_edge_traversal_count must be an int at top level of attack_paths_data."""
    from apd_gauntlet.report.loader import RunArtifacts

    # Zero-path case.
    art_empty = RunArtifacts(
        run_id="r", framework_version="1", domain_pack_name="p", domain_pack_version="1",
        subject="s", date="2026-01-01",
        asset_inventory={}, deduped_findings=[], deduped_capabilities=[],
        contradictions=[], contradictions_notes=None,
        severity_disagreements=[], severity_disagreements_notes=None,
        nist_coverage={}, attack_exposure={}, apd_coverage_matrix={},
        attack_paths={"paths": []},
        asset_graph={"nodes": [], "edges": []},
        defense_graph=None,
        attack_path_findings=[], report_data=None,
    )
    data_empty = attack_paths_data(art_empty)
    assert data_empty is not None
    assert isinstance(data_empty["max_edge_traversal_count"], int)
    assert data_empty["max_edge_traversal_count"] == 0

    # Single-path case — the one edge is traversed once.
    art_one = RunArtifacts(
        run_id="r", framework_version="1", domain_pack_name="p", domain_pack_version="1",
        subject="s", date="2026-01-01",
        asset_inventory={}, deduped_findings=[], deduped_capabilities=[],
        contradictions=[], contradictions_notes=None,
        severity_disagreements=[], severity_disagreements_notes=None,
        nist_coverage={}, attack_exposure={}, apd_coverage_matrix={},
        attack_paths={
            "paths": [
                {
                    "attacker_position": "atk-x",
                    "crown_jewel": "jewel-x",
                    "path_id": "p-x",
                    "hop_count": 1,
                    "feasibility": "high",
                    "severity_sum": 4,
                    "mitigation_count": 0,
                    "edges": ["edge-x"],
                    "bottleneck_edges": [],
                }
            ]
        },
        asset_graph={
            "nodes": [
                {"node_id": "atk-x", "name": "Attacker", "node_type": "attacker_position"},
                {"node_id": "jewel-x", "name": "Jewel", "node_type": "crown_jewel"},
            ],
            "edges": [{
                "edge_id": "edge-x",
                "edge_type": "compromisable_via_finding",
                "from": "atk-x",
                "to": "jewel-x",
                "confidence": "high",
            }],
        },
        defense_graph=None,
        attack_path_findings=[], report_data=None,
    )
    data_one = attack_paths_data(art_one)
    assert data_one is not None
    assert isinstance(data_one["max_edge_traversal_count"], int)
    assert data_one["max_edge_traversal_count"] == 1


def test_mermaid_sanitizes_adversarial_labels() -> None:
    """Asset names with <script>, brackets, newlines must not appear raw
    in the mermaid source — adopter-controlled inputs cannot inject syntax."""
    from apd_gauntlet.report.transform import _build_mermaid

    graph = {
        "nodes": [
            {"node_id": "n1", "name": "<script>alert(1)</script>", "node_type": "service"},
            {"node_id": "n2", "name": "Valkey\nINJECT", "node_type": "data_store"},
            {"node_id": "../etc", "name": "bad id", "node_type": "service"},
        ],
        "edges": [{"from": "n1", "to": "n2"}],
    }
    src = _build_mermaid(graph)
    assert "<script>" not in src
    assert "alert" not in src.lower() or "alert" in "(unnamed)"  # only if accidentally allowed
    assert "\n  ../etc" not in src  # bad id must have been remapped
    assert "n1" in src and "n2" in src


def test_mermaid_path_focused_present_when_pairs_nonempty() -> None:
    """mermaid_path_focused must be a non-empty string when paths are present."""
    from apd_gauntlet.report.loader import RunArtifacts

    art = RunArtifacts(
        run_id="r", framework_version="1", domain_pack_name="p", domain_pack_version="1",
        subject="s", date="2026-01-01",
        asset_inventory={}, deduped_findings=[], deduped_capabilities=[],
        contradictions=[], contradictions_notes=None,
        severity_disagreements=[], severity_disagreements_notes=None,
        nist_coverage={}, attack_exposure={}, apd_coverage_matrix={},
        attack_paths={
            "paths": [
                {
                    "attacker_position": "atk-9dadadaa",
                    "crown_jewel": "jewel-3e9a8535",
                    "path_id": "path-abc",
                    "hop_count": 1,
                    "feasibility": "high",
                    "severity_sum": 4,
                    "mitigation_count": 0,
                    "edges": ["edge-0e2085ac"],
                    "bottleneck_edges": [],
                }
            ]
        },
        asset_graph={
            "nodes": [
                {
                    "node_id": "atk-9dadadaa", "name": "compromised_admin_account",
                    "node_type": "attacker_position",
                },
                {
                    "node_id": "jewel-3e9a8535", "name": "service_account_credential_store",
                    "node_type": "crown_jewel",
                },
            ],
            "edges": [
                {
                    "edge_id": "edge-0e2085ac",
                    "edge_type": "compromisable_via_finding",
                    "from": "atk-9dadadaa",
                    "to": "jewel-3e9a8535",
                    "finding_id": "conf-477ff8a1",
                    "confidence": "high",
                }
            ],
        },
        defense_graph=None,
        attack_path_findings=[], report_data=None,
    )
    data = attack_paths_data(art)
    assert data is not None
    focused = data.get("mermaid_path_focused")
    assert isinstance(focused, str), "mermaid_path_focused must be a string when pairs non-empty"
    assert len(focused) > 0


def test_mermaid_path_focused_is_none_when_no_pairs() -> None:
    """mermaid_path_focused must be None when no paths are enumerated."""
    from apd_gauntlet.report.loader import RunArtifacts

    art = RunArtifacts(
        run_id="r", framework_version="1", domain_pack_name="p", domain_pack_version="1",
        subject="s", date="2026-01-01",
        asset_inventory={}, deduped_findings=[], deduped_capabilities=[],
        contradictions=[], contradictions_notes=None,
        severity_disagreements=[], severity_disagreements_notes=None,
        nist_coverage={}, attack_exposure={}, apd_coverage_matrix={},
        attack_paths={"paths": []},
        asset_graph={"nodes": [], "edges": []},
        defense_graph=None,
        attack_path_findings=[], report_data=None,
    )
    data = attack_paths_data(art)
    assert data is not None
    assert data.get("mermaid_path_focused") is None, (
        "mermaid_path_focused must be None when paths list is empty"
    )


def test_mermaid_path_focused_uses_LR_direction() -> None:
    """The focused subgraph must use `graph LR` so attacker → crown-jewel reads left-to-right."""
    from apd_gauntlet.report.loader import RunArtifacts

    art = RunArtifacts(
        run_id="r", framework_version="1", domain_pack_name="p", domain_pack_version="1",
        subject="s", date="2026-01-01",
        asset_inventory={}, deduped_findings=[], deduped_capabilities=[],
        contradictions=[], contradictions_notes=None,
        severity_disagreements=[], severity_disagreements_notes=None,
        nist_coverage={}, attack_exposure={}, apd_coverage_matrix={},
        attack_paths={
            "paths": [
                {
                    "attacker_position": "internet",
                    "crown_jewel": "db",
                    "path_id": "p1",
                    "hop_count": 1,
                    "feasibility": "high",
                    "severity_sum": 8,
                    "mitigation_count": 0,
                    "edges": ["e1"],
                    "bottleneck_edges": [],
                }
            ]
        },
        asset_graph={
            "nodes": [
                {"node_id": "internet", "name": "Internet", "node_type": "attacker_position"},
                {"node_id": "db", "name": "DB", "node_type": "crown_jewel"},
            ],
            "edges": [
                {
                    "edge_id": "e1",
                    "edge_type": "compromisable_via_finding",
                    "from": "internet",
                    "to": "db",
                }
            ],
        },
        defense_graph=None,
        attack_path_findings=[], report_data=None,
    )
    data = attack_paths_data(art)
    assert data is not None
    focused = data.get("mermaid_path_focused")
    assert isinstance(focused, str)
    assert "graph LR" in focused, "Focused subgraph must use `graph LR` direction"
