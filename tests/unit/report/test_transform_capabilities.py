# tests/unit/report/test_transform_capabilities.py
from __future__ import annotations

import pathlib

import pytest
from apd_gauntlet.report.loader import load_run
from apd_gauntlet.report.transform import capability_grid, strengths_section


def test_capability_grid_returns_list(legacy_example_run: pathlib.Path) -> None:
    artifacts = load_run(legacy_example_run)
    grid = capability_grid(artifacts)
    assert isinstance(grid, list)
    assert len(grid) == len(artifacts.deduped_capabilities)


def test_capability_grid_each_entry_carries_tier_goal_maturity(
    legacy_example_run: pathlib.Path,
) -> None:
    artifacts = load_run(legacy_example_run)
    grid = capability_grid(artifacts)
    for c in grid:
        assert {"id", "tier", "goal", "maturity", "title", "scope"}.issubset(c.keys())


def test_capability_grid_merged_flag_propagates(legacy_example_run: pathlib.Path) -> None:
    artifacts = load_run(legacy_example_run)
    grid = capability_grid(artifacts)
    merged = [c for c in grid if c.get("merged")]
    assert merged, "legacy_example fixture has at least one cross-lens-merged capability"
    for m in merged:
        assert "cross_lens" in m


def test_strengths_section_resolves_titles(legacy_example_run: pathlib.Path) -> None:
    artifacts = load_run(legacy_example_run)
    # No report-data.yaml on the fixture; pass an empty supplement and expect [].
    s = strengths_section(artifacts, supplied_strengths=None)
    assert s == []


def test_strengths_section_with_supplement_joins_titles(legacy_example_run: pathlib.Path) -> None:
    artifacts = load_run(legacy_example_run)
    supplement = [{"id": "conf-cap-3f6176f9", "caveats": ["A caveat long enough."]}]
    s = strengths_section(artifacts, supplied_strengths=supplement)
    assert len(s) == 1
    assert s[0]["id"] == "conf-cap-3f6176f9"
    assert "envelope" in s[0]["title"].lower()
    assert s[0]["caveats"] == ["A caveat long enough."]


def test_strengths_section_unknown_id_raises(legacy_example_run: pathlib.Path) -> None:
    artifacts = load_run(legacy_example_run)
    supplement = [{"id": "conf-cap-deadbeef", "caveats": ["x" * 20]}]
    with pytest.raises(ValueError) as exc:
        strengths_section(artifacts, supplied_strengths=supplement)
    assert "conf-cap-deadbeef" in str(exc.value)
