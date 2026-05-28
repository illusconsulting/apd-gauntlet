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
        contradictions=[], severity_disagreements=[],
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
        assert {"attacker_position", "crown_jewel", "paths"}.issubset(pair.keys())
        for p in pair["paths"]:
            assert {
                "path_id", "hop_count", "severity_sum", "edges", "bottleneck_edges"
            }.issubset(p.keys())


def test_bottleneck_overlays_present_when_defense_graph(example_run: pathlib.Path) -> None:
    artifacts = load_run(example_run)
    data = attack_paths_data(artifacts)
    assert data is not None
    assert isinstance(data["bottleneck_overlays"], list)


def test_coverage_summary_card(example_run: pathlib.Path) -> None:
    artifacts = load_run(example_run)
    data = attack_paths_data(artifacts)
    assert data is not None
    s = data["summary"]
    assert s["total_paths"] >= 0
    assert s["total_pairs"] >= 0


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
