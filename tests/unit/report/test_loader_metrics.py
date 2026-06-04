# tests/unit/report/test_loader_metrics.py
"""load_run reads 40-synthesis/metrics.yaml; absence is a hard MissingArtifactError."""
from __future__ import annotations

import pathlib
import shutil

import pytest
from apd_gauntlet.report.loader import MissingArtifactError, load_run

EXAMPLE = pathlib.Path(__file__).resolve().parents[3] / "examples" / \
    "apd-20260601-claim-event-bus" / "expected"


def test_load_run_reads_metrics(tmp_path):
    run = tmp_path / "run"
    shutil.copytree(EXAMPLE, run)
    artifacts = load_run(run)
    assert artifacts.metrics["schema_version"] == 1
    assert "bySeverity" in artifacts.metrics
    assert "metrics.yaml" in artifacts.source_hashes


def test_load_run_missing_metrics_raises(tmp_path):
    run = tmp_path / "run"
    shutil.copytree(EXAMPLE, run)
    (run / "40-synthesis" / "metrics.yaml").unlink()
    with pytest.raises(MissingArtifactError):
        load_run(run)
