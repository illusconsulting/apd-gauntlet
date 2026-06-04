"""Regression tests for informational-severity rendering in the HTML report.

The finding schema's canonical severity for the lowest tier is the full word
``informational`` (schemas/finding.schema.json), but the report template keys on
the short token ``info`` — its CSS classes (``.sev--info`` / ``.finding-row--info``),
its findings-screen severity sort map (``{...,info:4}``), and ``summary_rollup``'s
``bySeverity.info`` all use ``info``. Before the fix, ``findings_array`` emitted the
full word verbatim, so a finding with ``severity: informational`` reached the
template as ``"informational"``: it had no CSS rule (unstyled pill + neutral rail)
and ``sevOrder["informational"]`` was ``undefined`` (NaN comparator → mis-sorted
the whole Findings list).

This pins the data-side normalization (``_display_severity``) that maps the
finding's display severity to the template token so informational findings sort,
style, and filter correctly. The mobile-applications domain pack is the first to
realistically emit informational findings, but the fix is pack-agnostic.
"""
from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

from apd_gauntlet.report.transform import (
    _display_severity,
    findings_array,
    summary_rollup,
)

EMPTY_METRICS = {
    "schema_version": 1,
    "findings_total": 0, "findings_pre_dedup": 0,
    "cross_lens_merged_clusters": 0, "linked_clusters": 0,
    "bySeverity": {"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0},
    "byDisposition": {"gap": 0, "blocked": 0, "risk": 0, "uncertainty": 0, "ok": 0},
    "byTier": {"trustworthiness": 0, "scalability": 0, "auditability": 0},
    "capabilities_total": 0, "capabilities_pre_dedup": 0,
    "capabilitiesByMaturity": {"designed": 0, "implemented": 0, "tested": 0, "operationalized": 0},
    "contradictions": 0, "severity_disagreements": 0,
}


def _make_minimal_artifacts() -> MagicMock:
    a = MagicMock()
    a.run_id = "test-run"
    a.subject = "test"
    a.date = "2026-06-02"
    a.framework_version = "1.5.0"
    a.domain_pack_name = "mobile-applications"
    a.domain_pack_version = "1.0.0"
    a.run_crown_jewels = []
    a.run_attacker_positions = []
    a.asset_inventory = {}
    a.report_data = {}
    a.deduped_findings = []
    a.attack_path_findings = []
    a.deduped_capabilities = []
    a.nist_coverage = {}
    a.attack_exposure = {}
    a.apd_coverage_matrix = {}
    a.contradictions = []
    a.contradictions_notes = None
    a.severity_disagreements = []
    a.severity_disagreements_notes = None
    a.attack_paths = None
    a.asset_graph = None
    a.defense_graph = None
    a.metrics = EMPTY_METRICS
    return a


def _finding(fid: str, severity: str) -> dict[str, Any]:
    return {
        "id":          fid,
        "title":       "A mobile finding with an informational tier",
        "apd_goal":    "confidentiality",
        "apd_tier":    "trustworthiness",
        "severity":    severity,
        "confidence":  "high",
        "disposition": "gap",
        "summary":     "summary",
        "detail":      "detail",
        "control_mappings": {"nist_800_53r5": ["SC-28"]},
        "recommendation": {"posture": "consider", "summary": "do a thing"},
    }


def test_display_severity_maps_informational_to_info() -> None:
    assert _display_severity("informational") == "info"


def test_display_severity_passes_through_graded_severities() -> None:
    for sev in ("critical", "high", "medium", "low", "info"):
        assert _display_severity(sev) == sev


def test_display_severity_defaults_missing_to_info() -> None:
    # A finding with no severity defaults to the informational tier, mapped to "info".
    assert _display_severity(None) == "info"


def test_findings_array_emits_info_token_for_informational_finding() -> None:
    """An informational finding must reach the template as 'info' (its canonical
    token), not the full word 'informational' (which has no CSS rule / sort key)."""
    artifacts = _make_minimal_artifacts()
    artifacts.deduped_findings = [_finding("conf-00000001", "informational")]
    rows = findings_array(artifacts, headline_supplement=None)
    assert len(rows) == 1
    assert rows[0]["severity"] == "info"
    assert rows[0]["id"] == "conf-00000001"


def test_findings_array_preserves_graded_severities() -> None:
    artifacts = _make_minimal_artifacts()
    artifacts.deduped_findings = [
        _finding("conf-00000002", "critical"),
        _finding("conf-00000003", "low"),
    ]
    rows = findings_array(artifacts, headline_supplement=None)
    sev_by_id = {r["id"]: r["severity"] for r in rows}
    assert sev_by_id["conf-00000002"] == "critical"
    assert sev_by_id["conf-00000003"] == "low"


def test_summary_rollup_passthrough_returns_metrics_bysev() -> None:
    """summary_rollup now passes through artifacts.metrics; the informational->info
    bucketing itself is covered by tests/unit/synthesis/test_metrics.py."""
    artifacts = _make_minimal_artifacts()
    artifacts.metrics = {**EMPTY_METRICS,
                         "findings_total": 1,
                         "bySeverity": {"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 1}}
    summary = summary_rollup(artifacts)
    assert summary["bySeverity"]["info"] == 1
    assert "schema_version" not in summary


def test_findings_array_defaults_missing_tier_to_trustworthiness() -> None:
    """A finding lacking apd_tier renders tier='trustworthiness' (matching
    compute_metrics' tier default), so §2 tier-posture reconciles with byTier."""
    artifacts = _make_minimal_artifacts()
    artifacts.deduped_findings = [{"id": "conf-00000099", "severity": "high"}]  # no apd_tier
    rows = findings_array(artifacts, headline_supplement=None)
    assert len(rows) == 1
    assert rows[0]["tier"] == "trustworthiness"
