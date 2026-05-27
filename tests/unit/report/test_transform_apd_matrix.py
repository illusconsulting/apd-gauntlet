# tests/unit/report/test_transform_apd_matrix.py
from __future__ import annotations

import pathlib

from apd_gauntlet.report.loader import load_run
from apd_gauntlet.report.transform import apd_matrix


def test_matrix_returns_goals_and_rows(legacy_example_run: pathlib.Path) -> None:
    artifacts = load_run(legacy_example_run)
    m = apd_matrix(artifacts)
    assert set(m["goals"]) == {
        "conf", "intg", "avail", "dist", "resil", "ephem", "auth", "nonrep", "immut"
    }
    assert "goalLabels" in m
    assert len(m["rows"]) == len(artifacts.apd_coverage_matrix.get("component", []))


def test_matrix_cells_use_short_posture_keys(legacy_example_run: pathlib.Path) -> None:
    artifacts = load_run(legacy_example_run)
    m = apd_matrix(artifacts)
    for row in m["rows"]:
        for g in m["goals"]:
            v = row["cells"][g]
            assert v in {"covered", "gapped", "both", "silent"}


def test_matrix_posture_gapped_and_covered_becomes_both(legacy_example_run: pathlib.Path) -> None:
    artifacts = load_run(legacy_example_run)
    m = apd_matrix(artifacts)
    # Go sidecar process is gapped_and_covered across many goals in legacy_example.
    sidecar = next((r for r in m["rows"] if "sidecar" in r["component"].lower()), None)
    assert sidecar is not None
    # At least one cell becomes 'both'.
    assert any(v == "both" for v in sidecar["cells"].values())
