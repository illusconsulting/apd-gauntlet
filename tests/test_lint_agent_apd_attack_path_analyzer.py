"""Tests for the apd-attack-path-analyzer tier-4 agent file (Task C-17).

The agent's body is the source-of-truth for tier, activation, inputs/outputs,
and CLI delegation. These tests pin the structural invariants the orchestrator
and the lint-agents command rely on.
"""
from __future__ import annotations

from pathlib import Path

from apd_gauntlet.cli import main
from click.testing import CliRunner

REPO_ROOT = Path(__file__).resolve().parent.parent
AGENT = REPO_ROOT / ".claude" / "agents" / "apd-attack-path-analyzer.md"


def test_agent_file_exists() -> None:
    assert AGENT.exists(), f"Agent file missing: {AGENT}"


def test_agent_has_required_frontmatter() -> None:
    text = AGENT.read_text()
    assert text.startswith("---\n")
    for field in ("name:", "description:", "tools:", "model:"):
        assert field in text, f"Frontmatter missing '{field}'"


def test_agent_declares_tier_4() -> None:
    assert "tier-4" in AGENT.read_text().lower()


def test_agent_activation_gated_on_crown_jewels() -> None:
    text = AGENT.read_text()
    assert "crown_jewels" in text or "crown jewels" in text.lower()


def test_agent_invokes_cli_subcommand() -> None:
    assert "analyze-attack-paths" in AGENT.read_text()


def test_agent_consumes_dedup_findings_from_synthesizer() -> None:
    text = AGENT.read_text().lower()
    assert "synthesizer" in text or "dedup" in text


def test_agent_references_attack_path_discipline_skill() -> None:
    assert "apd-attack-path-discipline" in AGENT.read_text()


def test_agent_lints_clean() -> None:
    """apd-gauntlet lint-agents must include this agent and pass.

    The lint-agents command's clean message reports the total count rather
    than enumerating each agent, so we assert the agent file is on disk in
    the directory the linter scanned (it will be lint-checked along with
    its peers) AND the linter exited 0.
    """
    runner = CliRunner()
    agent_dir = REPO_ROOT / ".claude" / "agents"
    result = runner.invoke(main, ["lint-agents", "--agent-dir", str(agent_dir)])
    assert result.exit_code == 0, result.output
    assert AGENT.exists()
    agent_names = {p.name for p in agent_dir.glob("*.md")}
    assert "apd-attack-path-analyzer.md" in agent_names
