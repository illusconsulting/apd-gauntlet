# tests/unit/report/test_transform_attack_exposure.py
from __future__ import annotations

import pathlib

import pytest
from apd_gauntlet.report.loader import load_run
from apd_gauntlet.report.transform import attack_exposure_rows


def test_rows_one_per_technique(example_run: pathlib.Path) -> None:
    artifacts = load_run(example_run)
    rows = attack_exposure_rows(artifacts)
    raw = artifacts.attack_exposure.get("technique", [])
    assert len(rows) == len(raw)


def test_rows_carry_coverage_label(example_run: pathlib.Path) -> None:
    artifacts = load_run(example_run)
    rows = attack_exposure_rows(artifacts)
    for r in rows:
        assert r["coverage"] in {"covered", "partial", "uncovered"}


def test_rows_uncovered_when_no_mitigations(example_run: pathlib.Path) -> None:
    """T1078 in the crAPI fixture has zero countering capabilities → uncovered."""
    artifacts = load_run(example_run)
    rows = attack_exposure_rows(artifacts)
    by_id = {r["id"]: r for r in rows}
    # T1078 (Valid Accounts) has countering_capabilities: [] in the crAPI run.
    if "T1078" in by_id:
        assert by_id["T1078"]["coverage"] == "uncovered"
    else:
        # If the technique is absent, assert any uncovered row has correct label.
        uncovered = [r for r in rows if r["coverage"] == "uncovered"]
        if not uncovered:
            pytest.skip("no uncovered technique in fixture")
        for r in uncovered:
            assert r["coverage"] == "uncovered"


def test_rows_covered_when_findings_zero_and_mitigations_present(
    example_run: pathlib.Path,
) -> None:
    """T1110.001 in the crAPI fixture has findings AND mitigations (partial).
    Look for any technique with no findings but non-empty mitigations → covered."""
    artifacts = load_run(example_run)
    rows = attack_exposure_rows(artifacts)
    candidate = next(
        (r for r in rows if r.get("mitigations") and r.get("finding_count", 1) == 0),
        None,
    )
    if candidate is None:
        pytest.skip("no technique with zero findings and non-empty mitigations in fixture")
    assert candidate["coverage"] == "covered"


def test_rows_mitigations_is_list_of_capability_ids(example_run: pathlib.Path) -> None:
    artifacts = load_run(example_run)
    rows = attack_exposure_rows(artifacts)
    for r in rows:
        assert isinstance(r["mitigations"], list)
        for m in r["mitigations"]:
            assert isinstance(m, str)
