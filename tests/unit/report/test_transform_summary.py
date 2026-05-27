# tests/unit/report/test_transform_summary.py
"""Summary roll-up — bySeverity, byDisposition, byTier, capabilitiesByMaturity."""
from __future__ import annotations

import pathlib

from apd_gauntlet.report.loader import load_run
from apd_gauntlet.report.transform import summary_rollup


def test_summary_severity_counts(legacy_example_run: pathlib.Path) -> None:
    artifacts = load_run(legacy_example_run)
    s = summary_rollup(artifacts)
    assert s["bySeverity"]["high"] >= 1
    assert sum(s["bySeverity"].values()) == s["findings_total"]


def test_summary_disposition_counts(legacy_example_run: pathlib.Path) -> None:
    artifacts = load_run(legacy_example_run)
    s = summary_rollup(artifacts)
    assert set(s["byDisposition"].keys()) >= {"gap", "blocked", "risk"}
    assert sum(s["byDisposition"].values()) == s["findings_total"]


def test_summary_tier_counts_sum_to_total(legacy_example_run: pathlib.Path) -> None:
    artifacts = load_run(legacy_example_run)
    s = summary_rollup(artifacts)
    assert set(s["byTier"].keys()) == {"trustworthiness", "scalability", "auditability"}
    assert sum(s["byTier"].values()) == s["findings_total"]


def test_summary_capabilities_by_maturity(legacy_example_run: pathlib.Path) -> None:
    artifacts = load_run(legacy_example_run)
    s = summary_rollup(artifacts)
    assert "implemented" in s["capabilitiesByMaturity"]
    assert sum(s["capabilitiesByMaturity"].values()) == s["capabilities_total"]


def test_summary_contradictions_and_disagreements(legacy_example_run: pathlib.Path) -> None:
    artifacts = load_run(legacy_example_run)
    s = summary_rollup(artifacts)
    assert s["contradictions"] == len(artifacts.contradictions)
    assert s["severity_disagreements"] == len(artifacts.severity_disagreements)
