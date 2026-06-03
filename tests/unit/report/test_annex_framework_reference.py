"""Static-source pin for the §11 APD framework-reference annex.

The §11 section is static JSX in report-template/screens/Annexes.jsx; the
bundle-freshness gate (test_tier3_bundle_freshness) separately guarantees the
shipped app.js matches this source, so pinning the source is sufficient to
prove the educational content cannot silently regress.
"""
from __future__ import annotations

import pathlib

REPO = pathlib.Path(__file__).resolve().parents[3]
ANNEXES = REPO / "report-template" / "screens" / "Annexes.jsx"
HTML_DOC = REPO / "docs" / "html-report.md"


def _src() -> str:
    return ANNEXES.read_text(encoding="utf-8")


def test_section_heading_and_numbering_present() -> None:
    src = _src()
    assert "§ 11 — APD framework reference" in src
    assert "Three pillars, nine goals" in src


def test_structure_is_constant_driven() -> None:
    # Labels must come from the framework constants, not re-typed strings,
    # so the annex can never drift from the framework definition.
    src = _src()
    assert "TIER_GOALS" in src
    assert "TIER_LABELS" in src
    assert "GOAL_LABELS" in src
    assert "APD_TIER_ORDER" in src


def test_all_nine_goal_details_present() -> None:
    src = _src()
    for goal_key in (
        "confidentiality", "integrity", "availability",
        "distributed", "resilient", "ephemeral",
        "authenticity", "non_repudiation", "immutability",
    ):
        assert f"{goal_key}:" in src, f"missing goal detail entry: {goal_key}"
    # Every goal block shows its lens question.
    assert src.count("lens:") == 9


def test_per_goal_nist_family_anchors_present() -> None:
    src = _src()
    for anchor in (
        "NIST 800-53r5 · SC, AC, MP",   # confidentiality
        "NIST 800-53r5 · SI, SC, CM",   # integrity
        "NIST 800-53r5 · CP, SC, SI",   # availability
        "NIST 800-53r5 · SC, CP, CM",   # distributed
        "NIST 800-53r5 · SI, CP, SC",   # resilient
        "NIST 800-53r5 · IA, AC, SA",   # ephemeral
        "NIST 800-53r5 · IA, SC, SR",   # authenticity
        "NIST 800-53r5 · AU-10, IA",    # non-repudiation
        "NIST 800-53r5 · AU, CM, MP",   # immutability
    ):
        assert anchor in src, f"missing NIST anchor: {anchor}"


def test_acronym_caveat_present() -> None:
    # APD must NOT be asserted as a documented expansion.
    src = _src()
    assert "informal editorial gloss" in src
    assert "not the framework's documented expansion" in src


def test_sources_and_enforcement_note_present() -> None:
    src = _src()
    # Distinctive Sources bodies (the user-named bodies + a couple unique ones).
    for body in (
        "NIST Cybersecurity Framework (CSF) 2.0",
        "ISO/IEC 27001:2022",
        "OWASP ASVS",
        "The Open Group Open FAIR",
        "CSA Cloud Controls Matrix",
        "IHE ATNA",
    ):
        assert body in src, f"missing Sources body: {body}"
    # The honest enforcement note, with the default-on vs opt-in nuance.
    assert "What the gauntlet actually enforces" in src
    assert "opt-in per run" in src
    assert "not a statement that the gauntlet measures the system's compliance" in src


def test_report_cross_reference_line_present() -> None:
    src = _src()
    assert "drive the Findings filters" in src
    assert "Coverage → APD matrix" in src


def test_html_report_doc_mentions_framework_annex() -> None:
    doc = HTML_DOC.read_text(encoding="utf-8")
    assert "three pillars" in doc.lower() and "nine goals" in doc.lower()
