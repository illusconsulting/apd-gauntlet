"""Tests for the Phase C attack-path templates (Task C-22).

The `apd-attack-path-analyzer` agent (tier-4) authors four artifacts:

- `30-graph/asset-graph.yaml`   — asset graph (asset-graph.schema.json)
- `30-graph/attack-paths.yaml`  — enumerated paths (attack-path.schema.json)
- `30-graph/defense-graph.yaml` — D3FEND overlay (defense-graph.schema.json)
- `40-synthesis/attack-path-report.md` — narrative + Mermaid diagrams

These tests pin the four template files so the analyzer agent's
forward-references stay valid and the templates do not silently rot.
"""
from __future__ import annotations

from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parent.parent
TPL = REPO / "templates"


def test_asset_graph_template_has_yaml_skeleton() -> None:
    text = (TPL / "asset-graph.template.md").read_text()
    assert "schema_version: 1" in text
    assert "generated_by: attack_path_analyzer" in text
    assert "nodes:" in text and "edges:" in text


def test_attack_paths_template_has_enumeration_parameters() -> None:
    text = (TPL / "attack-paths.template.md").read_text()
    assert "enumeration_parameters:" in text
    assert "max_hop" in text and "max_paths_per_pair" in text


def test_defense_graph_template_documents_overlay_shape() -> None:
    text = (TPL / "defense-graph.template.md").read_text()
    assert "bottleneck_overlays" in text
    assert "candidate_d3fend" in text
    assert "net_new_d3fend" in text


def test_attack_path_report_template_has_mermaid_block_placeholder() -> None:
    text = (TPL / "attack-path-report.template.md").read_text()
    assert "```mermaid" in text
    assert "flowchart LR" in text
    assert "## Crown jewels" in text or "Crown jewels" in text


def test_attack_path_report_template_documents_50_node_cap() -> None:
    text = (TPL / "attack-path-report.template.md").read_text().lower()
    assert "50 node" in text or "50-node" in text or "50 nodes" in text


def test_data_templates_yaml_skeletons_parse() -> None:
    """The fenced YAML inside each data template must be parseable.

    Bonus contract check: extract the first fenced ```yaml block from each
    data template, run `yaml.safe_load`, and assert the top-level keys
    cover the schema's required keys. This prevents the skeleton from
    silently drifting out of sync with the schema.
    """
    cases: list[tuple[str, set[str]]] = [
        (
            "asset-graph.template.md",
            {"schema_version", "generated_by", "nodes", "edges"},
        ),
        (
            "attack-paths.template.md",
            {
                "schema_version",
                "generated_by",
                "enumeration_parameters",
                "paths",
                "summary",
            },
        ),
        (
            "defense-graph.template.md",
            {
                "schema_version",
                "generated_by",
                "bottleneck_overlays",
                "summary",
            },
        ),
    ]
    for name, required_keys in cases:
        text = (TPL / name).read_text()
        assert "```yaml" in text, f"{name} missing fenced yaml block"
        block = text.split("```yaml", 1)[1].split("```", 1)[0]
        doc = yaml.safe_load(block)
        assert isinstance(doc, dict), f"{name} yaml skeleton did not parse to a mapping"
        missing = required_keys - doc.keys()
        assert not missing, f"{name} missing keys: {missing}"
