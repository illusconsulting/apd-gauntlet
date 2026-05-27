# tests/unit/report/test_transform_attack_exposure.py
from __future__ import annotations

import pathlib

from apd_gauntlet.report.loader import load_run
from apd_gauntlet.report.transform import attack_exposure_rows


def test_rows_one_per_technique(legacy_example_run: pathlib.Path) -> None:
    artifacts = load_run(legacy_example_run)
    rows = attack_exposure_rows(artifacts)
    raw = artifacts.attack_exposure.get("technique", [])
    assert len(rows) == len(raw)


def test_rows_carry_coverage_label(legacy_example_run: pathlib.Path) -> None:
    artifacts = load_run(legacy_example_run)
    rows = attack_exposure_rows(artifacts)
    for r in rows:
        assert r["coverage"] in {"covered", "partial", "uncovered"}


def test_rows_uncovered_when_no_mitigations(legacy_example_run: pathlib.Path) -> None:
    """T1070.002 in legacy_example has zero mitigations → uncovered."""
    artifacts = load_run(legacy_example_run)
    rows = attack_exposure_rows(artifacts)
    by_id = {r["id"]: r for r in rows}
    if "T1070.002" in by_id:
        assert by_id["T1070.002"]["coverage"] == "uncovered"


def test_rows_covered_when_findings_zero_and_mitigations_present(
    legacy_example_run: pathlib.Path,
) -> None:
    """T1530 in legacy_example has zero findings, some mitigations → covered."""
    artifacts = load_run(legacy_example_run)
    rows = attack_exposure_rows(artifacts)
    by_id = {r["id"]: r for r in rows}
    if "T1530" in by_id:
        assert by_id["T1530"]["coverage"] == "covered"


def test_rows_mitigations_is_list_of_capability_ids(legacy_example_run: pathlib.Path) -> None:
    artifacts = load_run(legacy_example_run)
    rows = attack_exposure_rows(artifacts)
    for r in rows:
        assert isinstance(r["mitigations"], list)
        for m in r["mitigations"]:
            assert isinstance(m, str)
