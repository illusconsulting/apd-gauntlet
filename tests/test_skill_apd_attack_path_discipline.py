"""Tests for the apd-attack-path-discipline project skill.

The analyzer agent (Task C-17) is not yet present, so the cross-reference test
from the original plan stubs is intentionally deferred to that task. The seven
tests below validate only the skill file and its reference doc.
"""

import re
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SKILL = REPO / ".claude" / "skills" / "apd-attack-path-discipline" / "SKILL.md"
REF = (
    REPO
    / ".claude"
    / "skills"
    / "apd-attack-path-discipline"
    / "references"
    / "d3fend-mapping-pattern.md"
)


def _body() -> str:
    """Return SKILL.md content after the closing ``---`` of the frontmatter.

    Body-anchored assertions guard against the trap where the frontmatter
    ``description:`` field happens to contain a phrase the test is looking
    for — which would let a body-only deletion pass undetected.
    """
    text = SKILL.read_text()
    parts = text.split("---", 2)
    # parts[0] is empty (before opening ---), parts[1] is frontmatter,
    # parts[2] is body.
    return parts[2] if len(parts) >= 3 else text


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
    body = _body().lower()
    assert "confidence" in body
    assert "floor" in body
    assert "severity" in body


def test_skill_codifies_block_on_missing_crown_jewels() -> None:
    body = _body().lower()
    assert "block" in body
    assert "crown jewel" in body


def test_skill_codifies_bounded_enumeration() -> None:
    text = SKILL.read_text()
    assert "max_hop" in text or "bounded" in text.lower()
