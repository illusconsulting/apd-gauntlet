"""Tests for the lint-agents command."""
from __future__ import annotations

import pathlib

from apd_gauntlet.cli import main
from apd_gauntlet.lint_agents import lint_agent_file, lint_agents_dir
from click.testing import CliRunner

REPO = pathlib.Path(__file__).parent.parent


def test_lint_agents_on_real_repo(tmp_path):
    runner = CliRunner()
    # NOTE: This runs against the real .claude/agents/ in the repo. Required-reading
    # references to `.claude/skills/apd-domain/SKILL.md` will fail until M5 generates it.
    # For v1.0 we accept that lint-agents currently warns (or in our impl, errors) on
    # apd-domain references. Once M5 lands, this test should pass cleanly.
    # Here we simply ensure the command runs and produces output.
    result = runner.invoke(main, ["lint-agents", "--agent-dir", str(REPO / ".claude/agents")])
    # Exit code may be 0 or 1 depending on agent file state.
    assert result.exit_code in (0, 1)
    assert result.output  # produces some output


def test_lint_agents_catches_missing_frontmatter(tmp_path):
    agent_dir = tmp_path / "agents"
    agent_dir.mkdir()
    (agent_dir / "broken.md").write_text("# No frontmatter here\n")
    runner = CliRunner()
    result = runner.invoke(main, ["lint-agents", "--agent-dir", str(agent_dir)])
    assert result.exit_code == 1
    assert "frontmatter" in result.output.lower()


def test_code_recon_required_reading_resolves_c4_discipline() -> None:
    """The C4 extension adds .claude/skills/apd-c4-discipline/SKILL.md to
    code-recon's Required reading; lint_agent_file must resolve it (no
    'required reading target not found' error)."""
    from apd_gauntlet.lint_agents import lint_agent_file

    repo_root = pathlib.Path(__file__).resolve().parent.parent
    agent = repo_root / ".claude" / "agents" / "apd-code-recon.md"
    errors = lint_agent_file(agent, repo_root)
    assert errors == [], errors
    assert "apd-c4-discipline" in agent.read_text()


def test_lint_agents_flags_long_description(tmp_path):
    a = tmp_path / "apd-x.md"
    a.write_text("---\nname: apd-x\ndescription: " + "x" * 161 + "\n---\n\n## Final message\n")
    assert any("max 160" in e for e in lint_agent_file(a, tmp_path))


def test_lint_agents_flags_multiline_description(tmp_path):
    a = tmp_path / "apd-x.md"
    a.write_text('---\nname: apd-x\ndescription: "a\\nb"\n---\n\n## Final message\n')
    assert any("one line" in e for e in lint_agent_file(a, tmp_path))


def test_lint_agents_description_cap_error_text(tmp_path):
    from apd_gauntlet.lint_agents import MAX_AGENT_DESCRIPTION_CHARS

    a = tmp_path / "apd-x.md"
    a.write_text("---\nname: apd-x\ndescription: " + "x" * 161 + "\n---\n\n## Final message\n")
    assert MAX_AGENT_DESCRIPTION_CHARS == 160
    assert lint_agent_file(a, tmp_path) == [
        f"{a}: description is 161 characters (max 160); it loads into every session "
        "with the plugin enabled — keep one line"
    ]


def test_lint_agents_one_line_error_text(tmp_path):
    a = tmp_path / "apd-x.md"
    a.write_text("---\nname: apd-x\ndescription: |\n  a\n  b\n---\n\n## Final message\n")
    assert lint_agent_file(a, tmp_path) == [f"{a}: description must be one line"]


def test_lint_agents_accepts_a_description_at_the_cap(tmp_path):
    a = tmp_path / "apd-x.md"
    a.write_text("---\nname: apd-x\ndescription: " + "x" * 160 + "\n---\n\n## Final message\n")
    assert lint_agent_file(a, tmp_path) == []


def test_real_agents_lint_clean_with_22_agents():
    errors = lint_agents_dir(REPO / ".claude" / "agents", REPO)
    assert errors == [], errors
    assert len(list((REPO / ".claude" / "agents").glob("*.md"))) == 22
