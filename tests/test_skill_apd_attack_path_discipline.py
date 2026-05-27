"""Tests for the apd-attack-path-discipline project skill.

The analyzer agent (Task C-17) is not yet present, so the cross-reference test
from the original plan stubs is intentionally deferred to that task. The seven
tests below validate only the skill file and its reference doc.
"""

import re
from pathlib import Path

SKILL = Path(".claude/skills/apd-attack-path-discipline/SKILL.md")
REF = Path(".claude/skills/apd-attack-path-discipline/references/d3fend-mapping-pattern.md")


def test_skill_exists() -> None:
    assert SKILL.exists()
    assert REF.exists()


def test_skill_has_frontmatter_with_name_and_description() -> None:
    content = SKILL.read_text()
    assert content.startswith("---\n")
    m = re.search(r"^name:\s*apd-attack-path-discipline\s*$", content, re.M)
    assert m
    assert re.search(r"^description:\s*\S", content, re.M)


def test_skill_codifies_never_invent_nodes_rule() -> None:
    assert "never invent nodes" in SKILL.read_text().lower()


def test_skill_codifies_never_invent_edges_rule() -> None:
    assert "never invent edges" in SKILL.read_text().lower()


def test_skill_codifies_confidence_floors_severity_rule() -> None:
    text = SKILL.read_text().lower()
    assert "confidence" in text and "floor" in text and "severity" in text


def test_skill_codifies_block_on_missing_crown_jewels() -> None:
    text = SKILL.read_text().lower()
    assert "block" in text and "crown jewel" in text


def test_skill_codifies_bounded_enumeration() -> None:
    text = SKILL.read_text()
    assert "max_hop" in text or "bounded" in text.lower()
