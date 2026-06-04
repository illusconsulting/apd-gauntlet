# tests/unit/report/test_overview_breakdown.py
"""The Overview headline-grid breakdown must include critical and info so it
reconciles with findings_total, and a count strip must render from data.summary."""
from __future__ import annotations

import pathlib

SRC = (pathlib.Path(__file__).resolve().parents[3]
       / "report-template" / "screens" / "Overview.jsx").read_text()


def test_breakdown_includes_critical_and_info():
    # Pin the headline-grid breakdown cell specifically — these exact spans
    # exist only in the new 5-bucket breakdown, not in the rail-card severity card.
    assert "<span>{s.bySeverity.critical} crit</span>" in SRC
    assert "<span>{s.bySeverity.info} info</span>" in SRC


def test_count_strip_present():
    assert "count-strip" in SRC
    assert "{s.findings_total}</strong> findings" in SRC
    assert "{s.bySeverity.critical} critical" in SRC
    assert "{s.bySeverity.info} info" in SRC
