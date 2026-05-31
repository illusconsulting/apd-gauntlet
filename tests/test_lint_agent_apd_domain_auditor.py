"""Frontmatter + receipt-schema-conformance lint for the apd-domain-auditor agent (§7, §12)."""
from __future__ import annotations

import json
import pathlib
import re

import yaml
from jsonschema import Draft202012Validator

REPO = pathlib.Path(__file__).resolve().parent.parent
AGENT = REPO / ".claude" / "agents" / "apd-domain-auditor.md"
RECEIPT_SCHEMA = REPO / "schemas" / "agent-receipt.schema.json"
FRONTMATTER = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)


def _meta_and_body():
    text = AGENT.read_text(encoding="utf-8")
    m = FRONTMATTER.match(text)
    assert m, "apd-domain-auditor.md must start with a YAML frontmatter block"
    return yaml.safe_load(m.group(1)), text


def test_agent_file_exists():
    assert AGENT.is_file()


def test_frontmatter_fields_present():
    meta, _ = _meta_and_body()
    assert meta.get("name") == "apd-domain-auditor"
    assert meta.get("description")
    assert meta.get("tools")
    assert meta.get("model")


def test_required_reading_paths_resolve():
    """Every backticked `.claude/...md` reference ANYWHERE in the body must resolve
    (this scans the whole file, not just the Required-reading section). The body
    cites `.claude/skills/apd-domain/SKILL.md` in Inputs — that path is committed
    (verified: `git ls-files` tracks it, not gitignored), so it resolves at lint
    time. Keep all `.claude/...md` paths exact."""
    _, text = _meta_and_body()
    for ref in re.findall(r"`(\.claude/[^`]+\.md)`", text):
        assert (REPO / ref).exists(), f"required reading target not found: {ref}"


def test_documented_receipt_conforms_to_schema():
    """§12: the agent's documented final message CONFORMS TO agent-receipt.schema.json
    (status enum, outputs[].schema_valid, advisory counts: {}). Extract the fenced
    YAML receipt block under '## Final message', safe_load it, and validate it against
    the real schema — a string grep cannot catch a drifted key / missing required
    field. The documented block uses a single concrete `status: ok` so it is loadable."""
    _, text = _meta_and_body()
    after = text.split("## Final message", 1)
    assert len(after) == 2, "missing '## Final message' receipt section"
    m = re.search(r"```ya?ml\n(.*?)\n```", after[1], re.DOTALL)
    assert m, "receipt section must contain a fenced ```yaml block"
    receipt = yaml.safe_load(m.group(1))
    schema = json.loads(RECEIPT_SCHEMA.read_text(encoding="utf-8"))
    errors = list(Draft202012Validator(schema).iter_errors(receipt))
    assert errors == [], [e.message for e in errors]
    # And pin the B-specific receipt content.
    assert receipt["agent"] == "apd-domain-auditor"
    assert receipt["status"] == "ok"
    assert receipt["counts"] == {}
    assert any(
        o["path"] == "40-synthesis/domain-improvements.yaml" and o["schema_valid"] is True
        for o in receipt["outputs"]
    )


def test_lint_agents_dir_passes_on_new_agent():
    from apd_gauntlet.lint_agents import lint_agent_file
    errors = lint_agent_file(AGENT, REPO)
    assert errors == [], errors
