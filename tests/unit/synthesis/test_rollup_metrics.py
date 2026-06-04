# tests/unit/synthesis/test_rollup_metrics.py
"""build_rollups emits 40-synthesis/metrics.yaml matching compute_metrics over deduped∪apath."""
from __future__ import annotations

import pathlib
import shutil

import yaml
from apd_gauntlet.synthesis.rollup import build_rollups

EXAMPLE = pathlib.Path(__file__).resolve().parents[3] / "examples" / \
    "apd-20260601-claim-event-bus" / "expected"


def test_build_rollups_emits_metrics_yaml(tmp_path: pathlib.Path):
    run = tmp_path / "run"
    shutil.copytree(EXAMPLE, run)
    # Remove any pre-existing metrics.yaml so we prove build_rollups writes it.
    (run / "40-synthesis" / "metrics.yaml").unlink(missing_ok=True)

    build_rollups(run)

    metrics = yaml.safe_load((run / "40-synthesis" / "metrics.yaml").read_text())
    assert metrics["schema_version"] == 1
    # Severity bucket sums reconcile to the total (internal consistency).
    assert sum(metrics["bySeverity"].values()) == metrics["findings_total"]
    assert sum(metrics["byTier"].values()) == metrics["findings_total"]
    assert metrics["findings_total"] >= 1
    assert metrics["contradictions"] == 1
    assert metrics["severity_disagreements"] == 1
    assert sum(metrics["capabilitiesByMaturity"].values()) == metrics["capabilities_total"]
