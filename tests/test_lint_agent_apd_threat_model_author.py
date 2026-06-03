"""Structural tests for the apd-threat-model-author tier-0 agent (C2).

The agent's body is the source-of-truth for tier, always-on activation,
inputs/outputs, the CLI floor it drives, and its required-reading set. These
tests pin the invariants the workflow runner and `lint-agents` rely on.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml
from apd_gauntlet.cli import main
from apd_gauntlet.lint_agents import RECEIPT_MARKER, lint_agent_file
from click.testing import CliRunner

REPO_ROOT = Path(__file__).resolve().parent.parent
AGENT = REPO_ROOT / ".claude" / "agents" / "apd-threat-model-author.md"


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


def test_agent_name_matches_file() -> None:
    meta = _agent_frontmatter()
    assert meta["name"] == "apd-threat-model-author"


def test_agent_declares_tier_0_always_on() -> None:
    text = AGENT.read_text().lower()
    assert "tier-0" in text
    assert "always-on" in text or "always on" in text


def test_agent_invokes_cli_floor() -> None:
    assert "author-threat-model" in AGENT.read_text()


def test_agent_emits_canonical_and_human_outputs() -> None:
    text = AGENT.read_text()
    assert "00-context/threat-model-normalized.yaml" in text
    assert "00-context/threat-model-authored.md" in text
    assert "threat_model_author" in text


def test_agent_required_reading_set() -> None:
    text = AGENT.read_text()
    for skill in (
        "apd-framework",
        "apd-threat-model-methodologies",
        "apd-evidence-discipline",
    ):
        assert skill in text, f"required reading must include {skill}"
    assert "apd-finding-schema" not in text, (
        "the author emits no findings; apd-finding-schema must NOT be "
        "required reading (spec C2)"
    )


def test_agent_carries_receipt_contract() -> None:
    text = AGENT.read_text()
    assert RECEIPT_MARKER in text, "missing receipt contract section"
    assert "schemas/agent-receipt.schema.json" in text


def test_agent_ends_with_single_trailing_newline() -> None:
    text = AGENT.read_text()
    assert text.endswith("\n") and not text.endswith("\n\n"), (
        "agent file must end with one trailing newline (MD047)"
    )


def test_agent_lints_clean() -> None:
    runner = CliRunner()
    agent_dir = REPO_ROOT / ".claude" / "agents"
    result = runner.invoke(main, ["lint-agents", "--agent-dir", str(agent_dir)])
    assert result.exit_code == 0, result.output
    assert lint_agent_file(AGENT, REPO_ROOT) == []
