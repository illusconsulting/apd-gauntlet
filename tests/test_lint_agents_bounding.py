"""The nine specialists must declare output bounding (soft cap + no-silent-truncation)."""
from __future__ import annotations

import pathlib

from apd_gauntlet.lint_agents import (
    BOUNDING_MARKER,
    SPECIALIST_NAMES,
    lint_agent_file,
)

REPO = pathlib.Path(__file__).parent.parent
AGENTS = REPO / ".claude" / "agents"


def test_all_specialists_carry_output_bounding():
    for name in sorted(SPECIALIST_NAMES):
        text = (AGENTS / f"{name}.md").read_text()
        assert BOUNDING_MARKER in text, f"{name}.md missing output-bounding section"


def test_specialist_missing_bounding_is_flagged(tmp_path):
    # A specialist file lacking the bounding section must be flagged by the linter.
    agent = tmp_path / "apd-confidentiality.md"
    agent.write_text(
        "---\nname: apd-confidentiality\ndescription: x\n---\n\n"
        "# Conf\n\n## Final message\n\nreceipt only\n"
    )
    errors = lint_agent_file(agent, tmp_path)
    assert any("bounding" in e.lower() for e in errors)
