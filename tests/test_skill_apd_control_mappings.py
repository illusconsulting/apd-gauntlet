"""Tests for the apd-control-mappings project skill.

Body-anchored assertions guard against the trap where the frontmatter
``description:`` field happens to contain a phrase the test is looking for.
The allowed-keys list and the MASVS/MASWE discipline subsection are the
contract the mobile pack grounds its structured mappings against.
"""

from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SKILL = REPO / ".claude" / "skills" / "apd-control-mappings" / "SKILL.md"


def _body() -> str:
    """Return SKILL.md content after the closing ``---`` of the frontmatter."""
    text = SKILL.read_text()
    parts = text.split("---", 2)
    return parts[2] if len(parts) >= 3 else text


def _allowed_keys_paragraph() -> str:
    """Return the 'Allowed keys:' structural-rule paragraph."""
    for line in _body().splitlines():
        if "Allowed keys:" in line:
            return line
    return ""


def test_skill_exists() -> None:
    assert SKILL.exists()


def test_allowed_keys_paragraph_lists_masvs_and_maswe() -> None:
    para = _allowed_keys_paragraph()
    assert para, "the 'Allowed keys:' structural-rule line is missing"
    assert "`masvs`" in para
    assert "`maswe`" in para


def test_allowed_keys_marks_maswe_as_findings_only() -> None:
    para = _allowed_keys_paragraph()
    # maswe is findings-ONLY; masvs is on BOTH findings and capabilities.
    assert "findings-only" in para.lower() or "findings only" in para.lower()


def test_owasp_mas_subsection_present() -> None:
    body = _body()
    assert "### OWASP MAS (mobile — MASVS on findings + capabilities, MASWE on findings, optional)" in body  # noqa: E501


def test_owasp_mas_subsection_codifies_emit_only_when_declared() -> None:
    body = _body().lower()
    # Emit ONLY when the run declares masvs/maswe (mobile pack active).
    assert "only emit" in body
    assert "mobile-applications" in body


def test_owasp_mas_subsection_states_masvs_on_capability_means_satisfied() -> None:
    body = _body()
    # masvs on a capability = control SATISFIED; on a finding = control VIOLATED.
    assert "control satisfied" in body.lower()
    assert "control violated" in body.lower()


def test_owasp_mas_subsection_carries_maswe_beta_caveat() -> None:
    assert "MASWE-Beta" in _body()


def test_owasp_mas_subsection_grounds_ids_in_pack_prose() -> None:
    body = _body().lower()
    # Every id must be grounded in the mobile pack prose (rubric / patterns).
    assert "ground" in body
    assert "severity-rubric" in body or "common-patterns" in body


def test_owasp_mas_subsection_is_flat_list_no_rationale() -> None:
    body = _body().lower()
    # MAS ids are flat ID strings with no rationale field (like cwe / atlas).
    assert "no rationale field" in body


def test_high_confidence_rule_covers_mas() -> None:
    # The existing high-confidence-only rule must explicitly extend to MAS.
    body = _body()
    idx = body.find("## High-confidence-only rule")
    assert idx != -1
    tail = body[idx:]
    assert "MASVS" in tail or "MASWE" in tail
