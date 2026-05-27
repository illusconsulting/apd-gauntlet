"""Assert the synthesizer test harness fixture produces a valid report-data.yaml.

This test is permissive: it checks that *if* report-data.yaml is present in the
legacy_example fixture (it will be once the synthesizer agent has been re-run), the
schema and cross-file validation passes. If the file isn't present yet, the
test skips.
"""
from __future__ import annotations

import pathlib

import pytest
from apd_gauntlet.validate import run_cross_file_pass, run_schema_pass

REPO = pathlib.Path(__file__).resolve().parents[3]
FIXTURE = REPO / "runs" / "apd-legacy-example-run"
REPORT_DATA = FIXTURE / "40-synthesis" / "report-data.yaml"


@pytest.mark.skipif(not REPORT_DATA.exists(), reason="report-data.yaml not yet emitted on fixture")
def test_legacy_example_report_data_schema_valid() -> None:
    rep = run_schema_pass(FIXTURE)
    errors_for_file = [v for v in rep.errors if v.file == REPORT_DATA]
    assert not errors_for_file, [v.render() for v in errors_for_file]


@pytest.mark.skipif(not REPORT_DATA.exists(), reason="report-data.yaml not yet emitted on fixture")
def test_legacy_example_report_data_refs_resolve() -> None:
    rep = run_cross_file_pass(FIXTURE)
    errors_for_file = [v for v in rep.errors if v.file == REPORT_DATA]
    assert not errors_for_file, [v.render() for v in errors_for_file]
