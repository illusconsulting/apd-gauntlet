# tests/unit/report/test_transform_apd_matrix.py
from __future__ import annotations

import pathlib
from unittest.mock import MagicMock

from apd_gauntlet.report.loader import load_run
from apd_gauntlet.report.transform import apd_matrix


def test_matrix_returns_goals_and_rows(example_run: pathlib.Path) -> None:
    artifacts = load_run(example_run)
    m = apd_matrix(artifacts)
    assert set(m["goals"]) == {
        "conf", "intg", "avail", "dist", "resil", "ephem", "auth", "nonrep", "immut"
    }
    assert "goalLabels" in m
    # crAPI fixture uses the new coverage-dict shape → rows derived from findings.
    # Expect at least one row (at minimum the most-cited artifact).
    assert len(m["rows"]) > 0


def test_matrix_cells_use_short_posture_keys(example_run: pathlib.Path) -> None:
    artifacts = load_run(example_run)
    m = apd_matrix(artifacts)
    for row in m["rows"]:
        for g in m["goals"]:
            v = row["cells"][g]
            assert v in {"covered", "gapped", "both", "silent"}


def test_matrix_new_shape_produces_artifact_component_rows(
    example_run: pathlib.Path,
) -> None:
    """crAPI fixture uses goal-keyed coverage; row components should be artifact names."""
    artifacts = load_run(example_run)
    assert artifacts.apd_coverage_matrix.get("coverage") is not None, \
        "Fixture should use the goal-keyed coverage shape"
    m = apd_matrix(artifacts)
    component_names = {r["component"] for r in m["rows"]}
    # tech_plan.md is by far the most cited artifact in the fixture.
    assert "tech_plan.md" in component_names


def test_matrix_posture_gapped_and_covered_becomes_both(example_run: pathlib.Path) -> None:
    """For the crAPI fixture, at least one cell should be 'both' (findings + capabilities)."""
    artifacts = load_run(example_run)
    m = apd_matrix(artifacts)
    assert any(
        v == "both" for r in m["rows"] for v in r["cells"].values()
    ), "expected at least one 'both' cell across all rows"


def test_matrix_old_shape_component_rows() -> None:
    """Synthetic old-shape input: component list is used directly."""
    def _cell(posture: str) -> dict:
        return {"posture": posture, "findings": [], "capabilities": []}

    old_shape = {
        "component": [
            {
                "name": "api-gateway",
                "cells": {
                    "confidentiality": _cell("gapped_and_covered"),
                    "integrity":       _cell("gapped"),
                    "availability":    _cell("covered"),
                    "distributed":     _cell("silent"),
                    "resilient":       _cell("silent"),
                    "ephemeral":       _cell("silent"),
                    "authenticity":    _cell("silent"),
                    "non_repudiation": _cell("silent"),
                    "immutability":    _cell("silent"),
                },
            },
        ]
    }
    artifacts = MagicMock()
    artifacts.apd_coverage_matrix = old_shape
    artifacts.deduped_findings = []
    artifacts.attack_path_findings = []

    m = apd_matrix(artifacts)
    assert len(m["rows"]) == 1
    row = m["rows"][0]
    assert row["component"] == "api-gateway"
    assert row["cells"]["conf"] == "both"
    assert row["cells"]["intg"] == "gapped"
    assert row["cells"]["avail"] == "covered"
    assert row["cells"]["dist"] == "silent"
