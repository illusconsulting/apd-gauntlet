"""C6: the finding-schema skill must state the canonical singular-bare envelope."""
from __future__ import annotations

import pathlib

SKILL = (
    pathlib.Path(__file__).parent.parent
    / ".claude" / "skills" / "apd-finding-schema" / "SKILL.md"
)


def test_skill_states_singular_bare_envelope():
    text = SKILL.read_text(encoding="utf-8")
    assert "Output envelope (canonical)" in text
    # explicitly forbids the two drift shapes
    assert "never the plural" in text
    assert "tooling-canonicalized" in text
