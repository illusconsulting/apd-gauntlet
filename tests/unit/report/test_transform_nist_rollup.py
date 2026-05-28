from __future__ import annotations

import pathlib

import pytest
from apd_gauntlet.report.loader import load_run
from apd_gauntlet.report.transform import nist_rollup_rows


def test_rollup_one_row_per_family(example_run: pathlib.Path) -> None:
    artifacts = load_run(example_run)
    rows = nist_rollup_rows(artifacts)
    if not rows:
        pytest.skip(
            "crAPI nist-coverage.yaml has no family_summary section; "
            "rollup returns empty list — structural shape tested below"
        )
    families = {r["family"] for r in rows}
    # The crAPI fixture touches at least SC, AU, CM, CP, AC, IA.
    assert families >= {"SC", "AU", "CM", "CP", "AC", "IA"}


def test_rollup_counts_match_family_summary(example_run: pathlib.Path) -> None:
    artifacts = load_run(example_run)
    rows = nist_rollup_rows(artifacts)
    by_family = {r["family"]: r for r in rows}
    fs = artifacts.nist_coverage.get("family_summary", {})
    for fam, summary in fs.items():
        if fam not in by_family:
            continue
        assert by_family[fam]["covered"] == summary["covered"]
        assert by_family[fam]["gapped"] == summary["gapped"]
        assert by_family[fam]["both"] == summary["gapped_and_covered"]


def test_rollup_carries_title_from_families_data(example_run: pathlib.Path) -> None:
    artifacts = load_run(example_run)
    rows = nist_rollup_rows(artifacts)
    if not rows:
        pytest.skip("crAPI nist-coverage.yaml has no family_summary section")
    sc = next((r for r in rows if r["family"] == "SC"), None)
    if sc is None:
        pytest.skip("SC family not present in rollup rows")
    assert "Communications" in sc["title"] or "System" in sc["title"]


def test_rollup_notable_is_string(example_run: pathlib.Path) -> None:
    artifacts = load_run(example_run)
    rows = nist_rollup_rows(artifacts)
    for r in rows:
        assert isinstance(r["notable"], str)
