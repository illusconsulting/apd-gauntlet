"""Static-source pin for the Start-here reading-guide screen.

The Start-here tab is static JSX in report-template/screens/StartHere.jsx; the
bundle-freshness gate separately guarantees the shipped app.js matches this
source, so pinning the source proves the guide's content cannot silently
regress. Mirrors test_annex_framework_reference.py.
"""
from __future__ import annotations

import pathlib

REPO = pathlib.Path(__file__).resolve().parents[3]
SCREEN = REPO / "report-template" / "screens" / "StartHere.jsx"


def _src() -> str:
    return SCREEN.read_text(encoding="utf-8")


def test_screen_registers_on_window() -> None:
    assert "window.StartHere = StartHere;" in _src()


def test_four_sections_present() -> None:
    src = _src()
    for label in ("Orientation", "Vocabulary", "How to use", "For your role"):
        assert label in src, f"missing section: {label}"


def test_glossary_uses_real_atoms() -> None:
    # The glossary renders the SAME atoms used elsewhere so it never drifts.
    src = _src()
    assert "<SeverityPill value=" in src
    assert "<DispositionMark value=" in src
    assert "<MaturityMark value=" in src


def test_decodes_core_vocabulary() -> None:
    src = _src()
    for term in ("Severity", "Disposition", "Confidence", "Maturity", "Coverage cells"):
        assert term in src, f"missing vocabulary term: {term}"
    # The "both is suspicious" insight must be present.
    assert "scope-clarity debt" in src


def test_framework_labels_are_constant_driven() -> None:
    # Pillars/goals come from the shared framework constants, not re-typed.
    src = _src()
    assert "TIER_GOALS" in src
    assert "TIER_LABELS" in src
    assert "GOAL_LABELS" in src


def test_is_contextual_on_run_data() -> None:
    src = _src()
    assert "data.meta" in src
    assert "summary" in src


def test_offline_no_network_calls() -> None:
    src = _src()
    for forbidden in ("fetch(", "XMLHttpRequest", "import(", "https://"):
        assert forbidden not in src, f"network/dynamic call not allowed: {forbidden}"


def test_present_tabs_mirror_app_tab_list() -> None:
    # The orientation "what each tab is for" map must track app.jsx BASE_TABS:
    # the threat-model tab is conditional on data.threat_model.present, and the
    # trailing tabs are attack_paths then annexes. The bundle-freshness gate
    # cannot see app.jsx<->StartHere divergence, so pin the mirror here.
    src = _src()
    assert "data.threat_model.present" in src
    assert 'presentTabs.push("attack_paths", "annexes")' in src


def test_html_report_doc_mentions_start_here_guide() -> None:
    doc = (REPO / "docs" / "html-report.md").read_text(encoding="utf-8")
    assert "start here" in doc.lower()
