from __future__ import annotations

import pathlib

from apd_gauntlet.report.loader import load_run
from apd_gauntlet.report.transform import nist_rollup_rows


def test_rollup_one_row_per_family(legacy_example_run: pathlib.Path) -> None:
    artifacts = load_run(legacy_example_run)
    rows = nist_rollup_rows(artifacts)
    families = {r["family"] for r in rows}
    # The legacy_example fixture touches at least SC, SI, AU, CM, CP, AC, IA, SR, SA.
    assert families >= {"SC", "SI", "AU", "CM", "CP", "AC", "IA", "SR"}


def test_rollup_counts_match_family_summary(legacy_example_run: pathlib.Path) -> None:
    artifacts = load_run(legacy_example_run)
    rows = nist_rollup_rows(artifacts)
    by_family = {r["family"]: r for r in rows}
    fs = artifacts.nist_coverage.get("family_summary", {})
    for fam, summary in fs.items():
        if fam not in by_family:
            continue
        assert by_family[fam]["covered"] == summary["covered"]
        assert by_family[fam]["gapped"] == summary["gapped"]
        assert by_family[fam]["both"] == summary["gapped_and_covered"]


def test_rollup_carries_title_from_families_data(legacy_example_run: pathlib.Path) -> None:
    artifacts = load_run(legacy_example_run)
    rows = nist_rollup_rows(artifacts)
    sc = next(r for r in rows if r["family"] == "SC")
    assert "Communications" in sc["title"] or "System" in sc["title"]


def test_rollup_notable_is_string(legacy_example_run: pathlib.Path) -> None:
    artifacts = load_run(legacy_example_run)
    rows = nist_rollup_rows(artifacts)
    for r in rows:
        assert isinstance(r["notable"], str)
