"""Tests for the apd-code-recon agent file — C4 emission extension (Milestone 3).

The agent body is the source-of-truth for what code-recon emits and which
disciplines it reads. These tests pin the structural invariants the assembler
(assemble-c4) and the lint-agents command rely on after the C4 extension.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml
from apd_gauntlet.cli import main
from click.testing import CliRunner

REPO_ROOT = Path(__file__).resolve().parent.parent
AGENT = REPO_ROOT / ".claude" / "agents" / "apd-code-recon.md"


def _agent_frontmatter() -> dict[str, Any]:
    text = AGENT.read_text()
    m = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    assert m is not None, "Agent file is missing YAML frontmatter"
    meta = yaml.safe_load(m.group(1))
    assert isinstance(meta, dict)
    return meta


def test_agent_file_exists() -> None:
    assert AGENT.exists(), f"Agent file missing: {AGENT}"


def test_agent_name_unchanged() -> None:
    assert _agent_frontmatter()["name"] == "apd-code-recon"


def test_required_reading_lists_c4_discipline() -> None:
    text = AGENT.read_text()
    rr = re.search(r"(?ms)^##+\s*Required reading.*?(?=^##|\Z)", text)
    assert rr is not None, "no Required reading section"
    assert "apd-c4-discipline" in rr.group(0), (
        "Required reading must list the apd-c4-discipline skill"
    )


def test_required_reading_c4_path_resolves() -> None:
    """The cited c4-discipline SKILL.md must exist on disk (lint enforces this)."""
    target = REPO_ROOT / ".claude" / "skills" / "apd-c4-discipline" / "SKILL.md"
    assert target.exists(), f"discipline skill missing: {target}"


def test_agent_declares_c4_recon_output() -> None:
    text = AGENT.read_text()
    assert "00-context/c4-recon.yaml" in text
    assert "generated_by: code_recon" in text


def test_agent_has_c4_emission_section() -> None:
    assert "## C4 architecture emission" in AGENT.read_text()


def test_agent_documents_c4_index_tags() -> None:
    text = AGENT.read_text()
    for tag in ("c4_container", "c4_component", "c4_level"):
        assert tag in text, f"missing c4 index tag doc: {tag}"


def test_agent_documents_l3_block_and_machine_extracted_flag() -> None:
    text = AGENT.read_text().lower()
    assert "machine_extracted" in text
    # L3 components default-OMIT rule must be stated.
    assert "components: []" in AGENT.read_text() or "l3 is blocked" in text


def test_agent_does_not_mint_ids() -> None:
    """Agent emits names only; the assembler (assemble-c4) mints c4-/c4e- ids."""
    text = AGENT.read_text()
    assert "assemble-c4" in text or "assemble_c4" in text
    assert "by name" in text.lower()


def test_agent_lints_clean() -> None:
    runner = CliRunner()
    agent_dir = REPO_ROOT / ".claude" / "agents"
    result = runner.invoke(main, ["lint-agents", "--agent-dir", str(agent_dir)])
    assert result.exit_code == 0, result.output
    assert "apd-code-recon.md" in {p.name for p in agent_dir.glob("*.md")}
