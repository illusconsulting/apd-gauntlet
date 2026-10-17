"""Tests for the apd-attack-path-analyzer tier-4 agent file (Task C-17).

The agent's body is the source-of-truth for tier, activation, inputs/outputs,
and CLI delegation. These tests pin the structural invariants the orchestrator
and the lint-agents command rely on.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml
from apd_gauntlet.cli import main
from click.testing import CliRunner

REPO_ROOT = Path(__file__).resolve().parent.parent
AGENT = REPO_ROOT / ".claude" / "agents" / "apd-attack-path-analyzer.md"


def _agent_frontmatter() -> dict[str, Any]:
    text = AGENT.read_text()
    m = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    assert m is not None, "Agent file is missing YAML frontmatter"
    meta = yaml.safe_load(m.group(1))
    assert isinstance(meta, dict)
    return meta


def test_agent_file_exists() -> None:
    assert AGENT.exists(), f"Agent file missing: {AGENT}"


def test_agent_has_required_frontmatter() -> None:
    text = AGENT.read_text()
    assert text.startswith("---\n")
    for field in ("name:", "description:", "tools:", "model:"):
        assert field in text, f"Frontmatter missing '{field}'"


def test_agent_tools_are_expected_set() -> None:
    meta = _agent_frontmatter()
    assert set(meta["tools"]) == {"Read", "Glob", "Grep", "Write", "Bash"}


def test_agent_model_is_opus() -> None:
    meta = _agent_frontmatter()
    assert meta["model"] == "opus"


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


def test_agent_has_no_obsolete_template_hedge() -> None:
    text = AGENT.read_text()
    assert "does not yet exist" not in text and "Task C-22" not in text
    assert "templates/attack-path-report.template.md" in text
    assert (REPO_ROOT / "templates" / "attack-path-report.template.md").is_file()


def test_agent_has_no_manual_schema_check_passage() -> None:
    text = AGENT.read_text()
    for stale in ("Task C-21", "direct schema check", "vacuously"):
        assert stale not in text
    assert "apd-gauntlet validate" in text


def test_validate_step_is_scoped_to_the_four_attack_path_files() -> None:
    """The analyzer runs in parallel with the threat-model evaluator, whose records
    have no ids yet, so whole-run validation errors from tmeval are not its to fix."""
    text = AGENT.read_text()
    step = text.split("6. **Validate.**", 1)[1].split("\n## ", 1)[0]
    for name in (
        "asset-graph.yaml",
        "attack-paths.yaml",
        "defense-graph.yaml",
        "attack-path.findings.yaml",
    ):
        assert name in step
    assert "apd-threat-model-evaluator" in step and "not yours to fix" in step
