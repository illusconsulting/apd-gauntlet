"""Tests for the apd-code-recon agent file — C4 emission extension (Milestone 3).

The agent body is the source-of-truth for what code-recon emits and which
disciplines it reads. These tests pin the structural invariants the assembler
(assemble-c4) and the lint-agents command rely on after the C4 extension.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import yaml
from apd_gauntlet.cli import main
from click.testing import CliRunner
from jsonschema import Draft202012Validator

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


def test_agent_emits_no_cev_ids() -> None:
    text = AGENT.read_text()
    assert "Do NOT emit `id`" in text and "cev-0a000001" not in text


def test_brief_template_cites_code_locators_not_ids() -> None:
    template = (REPO_ROOT / "templates/code-architecture-brief.template.md").read_text()
    assert "cev-" not in template
    assert "Code anchors (`qualified_name:Lx-Ly`)" in template


def _section(start: str, end: str) -> str:
    return AGENT.read_text().split(start, 1)[1].split(end, 1)[0]


def _c4_recon_example() -> dict[str, Any]:
    section = _section("### `c4-recon.yaml` shape", "### Emission discipline")
    block = re.search(r"```yaml\n(.*?)\n```", section, re.DOTALL)
    assert block is not None, "c4-recon.yaml shape has no yaml example"
    doc = yaml.safe_load(block.group(1))
    assert isinstance(doc, dict)
    return doc


def test_c4_section_cites_no_evidence_id_that_does_not_exist_yet() -> None:
    # c4-recon.yaml is written before canonicalize mints the evidence index ids.
    assert "cev-" not in _section("## C4 architecture emission", "### Step 7")


def test_c4_recon_example_validates_against_the_schema() -> None:
    schema = json.loads((REPO_ROOT / "schemas" / "c4-recon.schema.json").read_text())
    errors = [e.message for e in Draft202012Validator(schema).iter_errors(_c4_recon_example())]
    assert errors == []


def test_c4_recon_example_edge_uses_the_hand_read_citation_format() -> None:
    # apd-c4-discipline: a hand_read edge cites a concrete file_path:Lstart-Lend.
    edge = _c4_recon_example()["uses_edges"][0]
    assert edge["machine_extracted"] is False
    assert edge["provenance"]["source"] == "code_evidence"
    assert re.fullmatch(r"[^\s:]+:L\d+-L\d+", edge["provenance"]["locator"])


def test_c4_edge_rule_names_both_grounded_citation_forms() -> None:
    rules = _section("### Emission discipline", "### Tag the evidence index")
    assert "file_path:Lstart-Lend" in rules and "<caller_qn> -> <callee_qn>" in rules


def test_self_check_requires_entries_without_ids() -> None:
    check = _section("## Self-check before exit", "## Final message")
    assert "carry an `id`" in check and "apd-gauntlet canonicalize" in check


def test_agent_records_provenance_in_fields_not_yaml_comments() -> None:
    # canonicalize rewrites code-evidence-index.yaml and drops YAML comments.
    shape = _section("### `code-evidence-index.yaml` structure", "## Process")
    assert "drops YAML comments" in shape and "`notes:`" in shape
