"""The three new LLM agents carry the receipt contract and lint clean."""
from __future__ import annotations

import pathlib

from apd_gauntlet.lint_agents import RECEIPT_MARKER, lint_agent_file

REPO = pathlib.Path(__file__).parent.parent
AGENTS = REPO / ".claude" / "agents"

NEW_AGENTS = ["apd-cluster-adjudicator", "apd-report-writer", "apd-report-auditor"]


def test_new_agents_carry_receipt_contract():
    for name in NEW_AGENTS:
        text = (AGENTS / f"{name}.md").read_text()
        assert RECEIPT_MARKER in text, f"{name}.md missing receipt contract"
        assert "schemas/agent-receipt.schema.json" in text, (
            f"{name}.md must reference the receipt schema"
        )


def test_new_agents_end_with_trailing_newline():
    for name in NEW_AGENTS:
        text = (AGENTS / f"{name}.md").read_text()
        assert text.endswith("\n") and not text.endswith("\n\n"), (
            f"{name}.md must end with one trailing newline (MD047)"
        )


def test_new_agents_lint_clean():
    for name in NEW_AGENTS:
        errors = lint_agent_file(AGENTS / f"{name}.md", REPO)
        assert errors == [], f"{name}.md lint errors: {errors}"
