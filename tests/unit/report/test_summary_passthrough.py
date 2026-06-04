# tests/unit/report/test_summary_passthrough.py
"""summary_rollup is a pure passthrough of artifacts.metrics (schema_version stripped)."""
from __future__ import annotations

from unittest.mock import MagicMock

from apd_gauntlet.report.transform import summary_rollup


def test_summary_rollup_returns_metrics_without_schema_version():
    a = MagicMock()
    a.metrics = {
        "schema_version": 1, "findings_total": 3,
        "bySeverity": {"critical": 1, "high": 1, "medium": 0, "low": 0, "info": 1},
    }
    s = summary_rollup(a)
    assert "schema_version" not in s
    assert s["findings_total"] == 3
    assert s["bySeverity"]["critical"] == 1


def test_summary_rollup_does_not_recompute_from_findings():
    a = MagicMock()
    a.metrics = {"findings_total": 99}
    a.deduped_findings = [{"id": "x", "severity": "high"}]   # ignored by passthrough
    a.attack_path_findings = []
    assert summary_rollup(a)["findings_total"] == 99
