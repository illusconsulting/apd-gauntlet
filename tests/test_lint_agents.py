"""Tests for the lint-agents command."""
from __future__ import annotations

import pathlib

import pytest
import yaml
from apd_gauntlet import lint_agents
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
    a.write_text(
        "---\nname: apd-x\ndescription: " + "x" * 161
        + "\ntools: Read\neffort: low\n---\n\n## Final message\n"
    )
    assert MAX_AGENT_DESCRIPTION_CHARS == 160
    assert lint_agent_file(a, tmp_path) == [
        f"{a}: description is 161 characters (max 160); it loads into every session "
        "with the plugin enabled — keep one line"
    ]


def test_lint_agents_one_line_error_text(tmp_path):
    a = tmp_path / "apd-x.md"
    a.write_text(
        "---\nname: apd-x\ndescription: |\n  a\n  b\ntools: Read\neffort: low\n---\n\n"
        "## Final message\n"
    )
    assert lint_agent_file(a, tmp_path) == [f"{a}: description must be one line"]


def test_lint_agents_accepts_a_description_at_the_cap(tmp_path):
    a = tmp_path / "apd-x.md"
    a.write_text(
        "---\nname: apd-x\ndescription: " + "x" * 160
        + "\ntools: Read\neffort: low\n---\n\n## Final message\n"
    )
    assert lint_agent_file(a, tmp_path) == []


@pytest.mark.parametrize("value", ["", ' ""'], ids=["null", "empty-string"])
def test_lint_agents_flags_an_empty_description_as_missing(tmp_path, value):
    # `description:` with no value parses to None; str(None) would pass both checks.
    a = tmp_path / "apd-x.md"
    a.write_text(f"---\nname: apd-x\ndescription:{value}\ntools: Read\neffort: low\n---\n\n"
                 "## Final message\n")
    assert lint_agent_file(a, tmp_path) == [f"{a}: frontmatter missing 'description'"]


def test_real_agents_lint_clean_with_22_agents():
    errors = lint_agents_dir(REPO / ".claude" / "agents", REPO)
    assert errors == [], errors
    assert len(list((REPO / ".claude" / "agents").glob("*.md"))) == 22


# --- WS3 Task 6a (N18): every agent sets `tools`, and each agent's tool set is pinned ---

READ_GLOB_GREP_WRITE = frozenset({"Read", "Glob", "Grep", "Write"})
CODEBASE_MEMORY_TOOLS = frozenset(f"mcp__codebase-memory-mcp__{tool}" for tool in (
    "index_status", "list_projects", "get_architecture", "search_graph", "trace_path",
    "get_code_snippet", "search_code", "query_graph", "index_repository"))
LENSES = ["confidentiality", "integrity", "availability", "distributed", "resilient",
          "ephemeral", "authenticity", "non-repudiation", "immutability"]

# The tools each agent may use; giving an agent another tool means changing this pin.
# apd-threat-model-recon, apd-threat-model-author, apd-attack-path-analyzer and
# apd-domain-auditor still hold Bash: Phase 10 removes it.
EXPECTED_TOOLS: dict[str, frozenset[str]] = {
    **{f"apd-{lens}": READ_GLOB_GREP_WRITE for lens in LENSES},
    "apd-intake": READ_GLOB_GREP_WRITE,
    "apd-code-recon": READ_GLOB_GREP_WRITE | CODEBASE_MEMORY_TOOLS,
    "apd-threat-model-evaluator": READ_GLOB_GREP_WRITE,
    "apd-synthesizer": READ_GLOB_GREP_WRITE,
    "apd-cli-runner": frozenset({"Bash"}),
    "apd-tier-repair": frozenset({"Read", "Edit"}),
    "apd-cluster-adjudicator": frozenset({"Read", "Write"}),
    "apd-report-writer": frozenset({"Read", "Write"}),
    "apd-report-auditor": frozenset({"Read", "Write"}),
    "apd-threat-model-recon": READ_GLOB_GREP_WRITE | {"Bash"},
    "apd-threat-model-author": READ_GLOB_GREP_WRITE | {"Bash"},
    "apd-attack-path-analyzer": READ_GLOB_GREP_WRITE | {"Bash"},
    "apd-domain-auditor": READ_GLOB_GREP_WRITE | {"Bash"},
}

MALFORMED_TOOLS = "tools must be a comma-separated string or a YAML list of tool names"


def _frontmatter(path: pathlib.Path) -> dict:
    m = lint_agents.FRONTMATTER_PATTERN.match(path.read_text(encoding="utf-8"))
    assert m is not None, f"{path.name} has no YAML frontmatter"
    meta = yaml.safe_load(m.group(1))
    assert isinstance(meta, dict), path.name
    return meta


def _agent(tmp_path: pathlib.Path, tools_line: str) -> pathlib.Path:
    a = tmp_path / "apd-x.md"
    a.write_text("---\nname: apd-x\ndescription: x\n" + tools_line
                 + "effort: low\n---\n\n## Final message\n")
    return a


def test_every_agent_tool_set_is_pinned():
    # The pin reads each file with the linter's own parser, so both forms count the same.
    files = sorted((REPO / ".claude" / "agents").glob("*.md"))
    assert {f.stem for f in files} == set(EXPECTED_TOOLS)
    for f in files:
        assert lint_agents.parse_tools(_frontmatter(f)["tools"]) == EXPECTED_TOOLS[f.stem], f.name


def test_bash_holders_are_the_cli_runner_and_the_four_recorded_agents():
    assert {name for name, tools in EXPECTED_TOOLS.items() if "Bash" in tools} == {
        "apd-cli-runner", "apd-threat-model-recon", "apd-threat-model-author",
        "apd-attack-path-analyzer", "apd-domain-auditor"}


@pytest.mark.parametrize("tools_line", ["", "tools:\n", 'tools: ""\n', "tools: []\n"],
                         ids=["absent", "null", "empty-string", "empty-list"])
def test_missing_tools_is_an_error(tmp_path, tools_line):
    # Without `tools`, Claude Code gives the agent every tool of the session.
    a = _agent(tmp_path, tools_line)
    assert lint_agent_file(a, tmp_path) == [f"{a}: frontmatter missing 'tools'"]


@pytest.mark.parametrize(("tools_line", "expected"), [
    ("tools: Read, Glob, Grep, Write\n", {"Read", "Glob", "Grep", "Write"}),
    ("tools: Read,Write\n", {"Read", "Write"}),
    ("tools: Bash\n", {"Bash"}),
    ("tools: [Read, Glob, Grep, Write]\n", {"Read", "Glob", "Grep", "Write"}),
    ("tools:\n  - Read\n  - Bash    # a comment\n", {"Read", "Bash"}),
    # A comma inside parentheses does not separate two names.
    ("tools: Agent(worker, researcher), Read, Bash\n",
     {"Agent(worker, researcher)", "Read", "Bash"}),
], ids=["comma", "comma-no-space", "one-name", "flow-list", "block-list", "parentheses"])
def test_both_tools_forms_parse_and_lint_clean(tmp_path, tools_line, expected):
    a = _agent(tmp_path, tools_line)
    assert lint_agent_file(a, tmp_path) == []
    assert lint_agents.parse_tools(_frontmatter(a)["tools"]) == frozenset(expected)


@pytest.mark.parametrize("tools_line", [
    "tools: Read,, Write\n",        # an empty name
    "tools: Read,\n",               # a trailing comma
    "tools: '  '\n",                # blank
    "tools: [Read, '']\n",
    "tools: [Read, 3]\n",           # not a string
    "tools: [[Read]]\n",
    "tools: {Read: true}\n",        # a mapping
    "tools: 3\n",
    "tools: true\n",
])
def test_malformed_tools_is_an_error(tmp_path, tools_line):
    a = _agent(tmp_path, tools_line)
    assert lint_agent_file(a, tmp_path) == [f"{a}: {MALFORMED_TOOLS}"]


@pytest.mark.parametrize("value", [None, "", [], 3, True, {"Read": True}, ["Read", 3],
                                   ["Read", " "], "Read,,Write"])
def test_parse_tools_returns_none_when_no_name_is_given_or_the_value_is_malformed(value):
    assert lint_agents.parse_tools(value) is None


def test_tools_error_comes_after_description_and_before_effort(tmp_path):
    a = tmp_path / "apd-x.md"
    a.write_text("---\nname: apd-x\ndescription: |\n  a\n  b\n---\n\n## Final message\n")
    assert lint_agent_file(a, tmp_path) == [
        f"{a}: description must be one line",
        f"{a}: frontmatter missing 'tools'",
        f"{a}: frontmatter missing 'effort'",
    ]
