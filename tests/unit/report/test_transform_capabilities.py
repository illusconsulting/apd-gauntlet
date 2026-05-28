# tests/unit/report/test_transform_capabilities.py
from __future__ import annotations

import pathlib

import pytest
from apd_gauntlet.report.loader import load_run
from apd_gauntlet.report.transform import capability_grid, strengths_section


def test_capability_grid_returns_list(example_run: pathlib.Path) -> None:
    artifacts = load_run(example_run)
    grid = capability_grid(artifacts)
    assert isinstance(grid, list)
    assert len(grid) == len(artifacts.deduped_capabilities)


def test_capability_grid_each_entry_carries_tier_goal_maturity(
    example_run: pathlib.Path,
) -> None:
    artifacts = load_run(example_run)
    grid = capability_grid(artifacts)
    for c in grid:
        assert {"id", "tier", "goal", "maturity", "title", "scope"}.issubset(c.keys())


def test_capability_grid_merged_flag_propagates(example_run: pathlib.Path) -> None:
    artifacts = load_run(example_run)
    grid = capability_grid(artifacts)
    # If any cross-lens-merged capabilities exist, each must carry a cross_lens key.
    merged = [c for c in grid if c.get("merged")]
    for m in merged:
        assert "cross_lens" in m


def test_strengths_section_resolves_titles(example_run: pathlib.Path) -> None:
    artifacts = load_run(example_run)
    # No supplement passed; strengths come from report_data if present,
    # but strengths_section with supplied_strengths=None returns [].
    s = strengths_section(artifacts, supplied_strengths=None)
    assert s == []


def test_strengths_section_with_supplement_joins_titles(example_run: pathlib.Path) -> None:
    artifacts = load_run(example_run)
    # conf-cap-c354ef8e has title "JWKS endpoint published over standard /.well-known/jwks.json path"
    supplement = [{"id": "conf-cap-c354ef8e", "caveats": ["A caveat long enough."]}]
    s = strengths_section(artifacts, supplied_strengths=supplement)
    assert len(s) == 1
    assert s[0]["id"] == "conf-cap-c354ef8e"
    assert "jwks" in s[0]["title"].lower()
    assert s[0]["caveats"] == ["A caveat long enough."]


def test_strengths_section_unknown_id_raises(example_run: pathlib.Path) -> None:
    artifacts = load_run(example_run)
    supplement = [{"id": "conf-cap-deadbeef", "caveats": ["x" * 20]}]
    with pytest.raises(ValueError) as exc:
        strengths_section(artifacts, supplied_strengths=supplement)
    assert "conf-cap-deadbeef" in str(exc.value)
