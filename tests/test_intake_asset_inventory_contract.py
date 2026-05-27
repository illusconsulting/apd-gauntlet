"""Tests for the apd-intake agent's asset-inventory contract (Task C-18).

The intake agent must emit a machine-readable `00-context/asset-inventory.yaml`
in addition to the existing markdown context-brief. The analyzer (Task C-17)
consumes the inventory; intake produces it. These tests pin the agent body
and template skeleton so the contract cannot regress silently.
"""
from __future__ import annotations

from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
AGENT = REPO / ".claude" / "agents" / "apd-intake.md"
TEMPLATE = REPO / "templates" / "asset-inventory.template.md"


def test_intake_agent_emits_asset_inventory() -> None:
    text = AGENT.read_text()
    assert "asset-inventory.yaml" in text
    assert "00-context/asset-inventory.yaml" in text


def test_intake_agent_references_asset_inventory_template() -> None:
    text = AGENT.read_text()
    assert "asset-inventory.template.md" in text


def test_intake_agent_documents_asset_types() -> None:
    text = AGENT.read_text().lower()
    for kind in (
        "service",
        "data_store",
        "secret_store",
        "queue",
        "network",
        "external_dependency",
        "compute",
    ):
        assert kind in text, f"asset_type {kind} should appear in intake instructions"


def test_intake_agent_documents_identity_types() -> None:
    text = AGENT.read_text().lower()
    for kind in (
        "human_role",
        "service_account",
        "workload_identity",
        "external_party",
    ):
        assert kind in text


def test_asset_inventory_template_exists() -> None:
    assert TEMPLATE.exists()


def test_asset_inventory_template_has_yaml_skeleton() -> None:
    text = TEMPLATE.read_text()
    assert "schema_version: 1" in text
    assert "generated_by: intake" in text
    assert "assets:" in text
    assert "identities:" in text
    assert "trust_boundaries:" in text
    assert "extraction_summary:" in text
