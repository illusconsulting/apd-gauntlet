from __future__ import annotations

import pathlib
from unittest.mock import MagicMock

import yaml
from apd_gauntlet.report.loader import load_run
from apd_gauntlet.report.transform import nist_rollup_rows

LEGACY_NIST = (
    pathlib.Path(__file__).resolve().parents[3]
    / "tests" / "fixtures" / "legacy-coverage-shapes" / "40-synthesis" / "nist-coverage.yaml"
)


def test_rollup_one_row_per_family(example_run: pathlib.Path) -> None:
    artifacts = load_run(example_run)
    rows = nist_rollup_rows(artifacts)
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
    sc = next((r for r in rows if r["family"] == "SC"), None)
    assert sc is not None, "SC family expected in rollup rows"
    assert "Communications" in sc["title"] or "System" in sc["title"]


def test_rollup_notable_is_string(example_run: pathlib.Path) -> None:
    artifacts = load_run(example_run)
    rows = nist_rollup_rows(artifacts)
    for r in rows:
        assert isinstance(r["notable"], str)


def test_rollup_new_shape_counts_are_nonzero() -> None:
    """Loader tolerance: the FROZEN legacy coverage_by_family doc cross-walks to nonzero rows."""
    legacy = yaml.safe_load(LEGACY_NIST.read_text(encoding="utf-8"))
    assert legacy.get("coverage_by_family") is not None, \
        "Frozen fixture should use the legacy coverage_by_family shape"
    artifacts = MagicMock()
    artifacts.nist_coverage = legacy
    artifacts.deduped_capabilities = []
    rows = nist_rollup_rows(artifacts)
    total = sum(r["covered"] + r["gapped"] + r["both"] for r in rows)
    assert total > 0, "Expected non-zero control counts from coverage_by_family cross-walk"


def test_rollup_old_shape_uses_family_summary() -> None:
    """Synthetic old-shape input: family_summary + control list are used directly."""
    old_shape_nist = {
        "family_summary": {
            "AC": {"covered": 2, "gapped": 3, "gapped_and_covered": 1},
            "AU": {"covered": 0, "gapped": 4, "gapped_and_covered": 0},
        },
        "control": [
            {"id": "AC-2", "family": "AC", "title": "Account Management", "posture": "covered"},
            {"id": "AC-3", "family": "AC", "title": "Access Enforcement", "posture": "gapped"},
            {"id": "AU-2", "family": "AU", "title": "Event Logging", "posture": "gapped"},
        ],
    }
    artifacts = MagicMock()
    artifacts.nist_coverage = old_shape_nist
    artifacts.deduped_capabilities = []

    rows = nist_rollup_rows(artifacts)
    by_fam = {r["family"]: r for r in rows}

    assert set(by_fam) == {"AC", "AU"}
    assert by_fam["AC"]["covered"] == 2
    assert by_fam["AC"]["gapped"] == 3
    assert by_fam["AC"]["both"] == 1
    assert by_fam["AU"]["gapped"] == 4
    # AU has more total (4) than AC (6)... wait, AC=6, AU=4; AC first in sorted order
    assert rows[0]["family"] == "AC"
    # Notable should mention AC-2 strong and AC-3 gapped (from control list)
    assert "AC-2" in rows[0]["notable"]
