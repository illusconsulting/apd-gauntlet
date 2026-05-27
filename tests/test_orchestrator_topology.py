"""Tests for the apd-orchestrator agent's topology documentation (Task C-19).

Phase C / v1.4 introduces the `apd-attack-path-analyzer` as a third tier-4
agent. The orchestrator agent describes the run lifecycle and must therefore:

- Reference the analyzer by name in the tier-4 topology block.
- Bump the topology header from "v1.3+ — 15 agents" to "v1.4+ — 16 agents".
- Document a Phase 5.6 dispatch (or equivalent attack-path analysis phase)
  that mirrors Phase 5.5's activation-gated tier-4 pattern.
- Describe the crown_jewels-based activation gate.
- Reference the analyzer's expected output artifacts so a future reader knows
  what to look for in `40-synthesis/`.
- Acknowledge in Phase 1 (intake) that intake now conditionally emits
  `00-context/asset-inventory.yaml` when `crown_jewels` are declared.

These tests pin the agent body so the contract cannot regress silently.
"""
from __future__ import annotations

from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
AGENT = REPO / ".claude" / "agents" / "apd-orchestrator.md"


def test_orchestrator_documents_attack_path_analyzer() -> None:
    text = AGENT.read_text()
    assert "apd-attack-path-analyzer" in text


def test_orchestrator_topology_count_is_16() -> None:
    text = AGENT.read_text()
    assert "16 agents" in text
    assert "15 agents" not in text


def test_orchestrator_documents_phase_5_6_analyzer_dispatch() -> None:
    text = AGENT.read_text()
    assert (
        "Phase 5.6" in text
        or "Attack-Path Analysis" in text
        or "attack-path analysis" in text.lower()
    )


def test_orchestrator_documents_analyzer_activation_gate() -> None:
    text = AGENT.read_text()
    assert "crown_jewels" in text


def test_orchestrator_documents_analyzer_outputs() -> None:
    text = AGENT.read_text()
    expected_outputs = [
        "asset-graph.yaml",
        "attack-paths.yaml",
        "defense-graph.yaml",
        "attack-path.findings.yaml",
    ]
    assert any(out in text for out in expected_outputs)


def test_orchestrator_acknowledges_intake_asset_inventory() -> None:
    """Phase 1 (intake) description should acknowledge the conditional
    asset-inventory.yaml output added in Task C-18, so a reader following
    the orchestrator end-to-end knows where the analyzer's primary input
    originates."""
    text = AGENT.read_text()
    assert "asset-inventory.yaml" in text
