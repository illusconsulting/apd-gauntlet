"""Structural lint for the apd-c4-discipline skill. Mirrors how the other
discipline skills are shaped (YAML frontmatter + numbered ### hard rules) and
guards that each never-invent/honesty rule heading is actually present, so the
skill can't silently drop a load-bearing rule.
"""
from __future__ import annotations

import pathlib
import re

REPO = pathlib.Path(__file__).resolve().parent.parent
SKILL = REPO / ".claude" / "skills" / "apd-c4-discipline" / "SKILL.md"

REQUIRED_RULE_HEADINGS = [
    "Never invent containers or components",
    "Never invent containment (parent) or uses edges",
    "L3 component grouping is blocked by default",
    "Confidence floor on render",
    "Diagram-size cap",
    "not_analyzed is not zero findings",
]


def test_skill_file_exists():
    assert SKILL.exists(), f"missing {SKILL}"


def test_frontmatter_name_and_description():
    text = SKILL.read_text()
    m = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    assert m, "SKILL.md must open with a YAML frontmatter block"
    fm = m.group(1)
    assert re.search(r"^name:\s*apd-c4-discipline\s*$", fm, re.MULTILINE)
    assert re.search(r"^description:\s*\S", fm, re.MULTILINE)


def test_has_hard_rules_section():
    assert "## Hard rules" in SKILL.read_text()


def test_all_required_rule_headings_present():
    text = SKILL.read_text()
    for heading in REQUIRED_RULE_HEADINGS:
        assert "### " in text and heading in text, f"missing rule heading: {heading!r}"
        # each heading must appear on a level-3 markdown heading line
        assert re.search(rf"^### \d+\. .*{re.escape(heading)}", text, re.MULTILINE), \
            f"{heading!r} is not a numbered ### rule heading"


def test_machine_extracted_vs_hand_read_distinction_documented():
    text = SKILL.read_text()
    assert "machine_extracted" in text
    assert "hand_read" in text or "hand-read" in text


def test_names_not_ids_ownership_rule_documented():
    """ADR-0020 ownership: agents emit names; the assembler mints ids/badges."""
    text = SKILL.read_text()
    assert "ADR-0020" in text or "assembler" in text.lower()
    assert "c4-" in text  # references the id scheme it must NOT mint
