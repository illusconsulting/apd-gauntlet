"""Tests for the `## Authoring discipline` section added to the
apd-threat-model-methodologies skill (spec C4)."""

from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SKILL = REPO / ".claude" / "skills" / "apd-threat-model-methodologies" / "SKILL.md"


def _authoring_section() -> str:
    """Return only the `## Authoring discipline` section body.

    Section-anchored so the test cannot be satisfied by an unrelated phrase
    elsewhere in the file.
    """
    text = SKILL.read_text()
    start = text.index("## Authoring discipline")
    rest = text[start + len("## Authoring discipline"):]
    end = rest.find("\n## ")
    return rest if end == -1 else rest[:end]


def test_authoring_section_present() -> None:
    assert "## Authoring discipline" in SKILL.read_text()


def test_authoring_has_six_numbered_rules() -> None:
    section = _authoring_section()
    for n in range(1, 7):
        assert f"{n}." in section, f"authoring rule {n} missing"


def test_authoring_rules_cover_the_six_topics() -> None:
    section = _authoring_section().lower()
    assert "never invent surfaces" in section          # rule 1
    assert "reason about" in section or "reason ABOUT".lower() in section  # rule 2
    assert "weakest grounding source" in section        # rule 3
    assert "block-on-ambiguity" in section              # rule 4
    assert "prerequisite_evidence" in section
    assert "input trust boundary" in section            # rule 5
    assert "self-check" in section                      # rule 6


def test_authoring_section_names_grounding_sources() -> None:
    section = _authoring_section()
    assert "asset-inventory.yaml" in section
    assert "code-evidence-index.yaml" in section
    assert "domain-pack" in section.lower() or "domain pack" in section.lower()


def test_authoring_references_entry_id_recompute() -> None:
    section = _authoring_section()
    assert "entry_id" in section
    assert "source_locator" in section


def test_never_invent_threats_rule_has_scoping_clause() -> None:
    """The existing Rule 1 must scope itself to the recon+evaluator path so it
    does not contradict the author's proactive-completeness mandate."""
    text = SKILL.read_text().lower()
    assert "never invent threats" in text
    assert "authoring discipline" in text
    # The scoping clause must name the parse/grade path it binds.
    assert "parsing/grading" in text or "parse/grade" in text


def test_mapping_tables_single_sourced_pointer() -> None:
    assert "tools/apd_gauntlet/threat_model/mappings.py" in SKILL.read_text()
