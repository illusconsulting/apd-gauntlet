"""The CLI step runner: a Bash-only Haiku agent that runs one apd-gauntlet command.

Every pyStep() of the workflow dispatches it (registry R5). Its body holds the static
receipt contract that pyStep() used to repeat in every prompt, so each dispatch prompt
carries only the guard or always-run line, COMMAND:, RECEIPT AGENT: and the step's own
receipt lines.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import yaml
from apd_gauntlet.lint_agents import lint_agent_file

REPO = Path(__file__).resolve().parent.parent
AGENT = REPO / ".claude" / "agents" / "apd-cli-runner.md"


def _frontmatter(path: Path) -> dict[str, Any]:
    # A copy of _agent_frontmatter in tests/test_lint_agent_apd_threat_model_author.py.
    text = path.read_text()
    m = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    assert m is not None, "Agent file is missing YAML frontmatter"
    meta = yaml.safe_load(m.group(1))
    assert isinstance(meta, dict)
    return meta


def _body() -> str:
    return AGENT.read_text(encoding="utf-8").split("\n---\n", 1)[1]


def test_frontmatter_is_registry_r5():
    meta = _frontmatter(AGENT)
    assert (meta["name"], meta["tools"], meta["model"], meta["effort"]) == (
        "apd-cli-runner", "Bash", "haiku", "low")
    assert len(meta["description"]) <= 160 and "\n" not in meta["description"]


def test_frontmatter_is_exactly_the_planned_block():
    head = AGENT.read_text(encoding="utf-8").split("\n---\n", 1)[0] + "\n---\n"
    assert head == (
        "---\n"
        "name: apd-cli-runner\n"
        'description: "Runs one apd-gauntlet CLI command and returns its receipt; '
        'dispatched by the apd-gauntlet workflow only."\n'
        "tools: Bash\n"
        "model: haiku\n"
        "effort: low\n"
        "---\n"
    )


def test_body_contract():
    body = _body()
    for phrase in ("COMMAND:", "begin with `apd-gauntlet`", "refused: not an apd-gauntlet command",
                   "exit=<N>; <stderr-tail>", "schemas/agent-receipt.schema.json",
                   "`<cmd>: <step> exit=<N>`"):
        assert phrase in body, phrase


def test_body_carries_the_static_receipt_contract_pystep_dropped():
    # Register A9.8: the WORK COMMAND and short-circuited pins move from pyStep() to the
    # agent body, with the rest of the static receipt mapping.
    body = _body()
    for phrase in ("work command", "IDEMPOTENCY GUARD",
                   "Always run this command; this step has no idempotency check and no skip.",
                   "RECEIPT AGENT", "short-circuited", 'status: "ok" if exit==0, else "error"',
                   "counts: {} (or blocked: N if the command reported blocked findings)",
                   "never prose"):
        assert phrase in body, phrase


def test_body_sections_and_job_rules():
    body = _body()
    assert re.findall(r"^#+ .*$", body, re.MULTILINE) == [
        "# apd-cli-runner", "## Job", "## Final message (receipt only)"]
    job = body[body.index("## Job"):body.index("## Final message")]
    for phrase in ("exactly once", "from the current directory",
                   "Never create, edit or delete files.", "Never run any other command.",
                   "Never retry.", "`report_audit`", "`resume_plan`", "`errors`"):
        assert phrase in job, phrase
    assert body.rstrip().endswith("`schemas/agent-receipt.schema.json`.")
    assert body.endswith("\n") and not body.endswith("\n\n")


def test_composite_status_lines_become_one_error_per_failed_step():
    # WS3 Task 3: a composite writes `<cmd>: <step> exit=<N>` per constituent to stderr.
    # The receipt names each failed constituent, so the workflow can tell a rollup
    # failure from an assemble-c4 one; the JSON error mapping wins where the prompt has it.
    final = _body().split("## Final message (receipt only)", 1)[1]
    for phrase in ("`<cmd>: <step> exit=<N>`", "N is not 0",
                   '{path: "<step>", message: "exit=<N>; <stderr-tail>"}',
                   "in place of the single default entry", "JSON error mapping",
                   "takes precedence"):
        assert phrase in final, phrase


def test_lints_clean():
    assert lint_agent_file(AGENT, REPO) == []


def test_listed_in_the_plugin_manifest_after_availability():
    agents = json.loads((REPO / ".claude-plugin" / "plugin.json").read_text())["agents"]
    at = agents.index("./.claude/agents/apd-availability.md")
    assert agents[at + 1] == "./.claude/agents/apd-cli-runner.md"


def test_architecture_doc_counts_and_lists_the_cli_runner():
    text = (REPO / "docs" / "architecture.md").read_text(encoding="utf-8")
    assert ("| CLI step runner | `apd-cli-runner` | Runs one `apd-gauntlet` command per CLI step "
            "(Bash only, Haiku, low effort) and returns its receipt |") in text
    assert "## The 22 agents" in text and "The gauntlet ships 22 agents" in text
    assert "A twenty-third file, `apd-orchestrator.md`" in text and "among the 22." in text
    assert "21 agents" not in text and "among the 21" not in text and "twenty-second" not in text
