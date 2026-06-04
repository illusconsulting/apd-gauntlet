# tests/unit/report/test_transform_capabilities.py
from __future__ import annotations

import pathlib

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
    # conf-cap-d0590471 title: "MSK cluster with KMS-managed at-rest encryption".
    supplement = [{"id": "conf-cap-d0590471", "caveats": ["A caveat long enough."]}]
    s = strengths_section(artifacts, supplied_strengths=supplement)
    assert len(s) == 1
    assert s[0]["id"] == "conf-cap-d0590471"
    assert "kms" in s[0]["title"].lower()
    assert s[0]["caveats"] == ["A caveat long enough."]


def test_strengths_section_unknown_id_warns_not_raises(
    example_run: pathlib.Path,
) -> None:
    """Post-PR-T4-D: unknown capability ids are warn-and-skip, not fatal.

    Sibling supplements (``headline_findings``, ``next_steps``) already
    fail silently on unknown ids. The strengths helper now matches that
    contract — an unknown id is dropped from the output and (when the caller
    supplies a warnings list) a structured record is appended so the issue
    surfaces in ``data.meta.warnings`` without aborting the whole report.
    """
    artifacts = load_run(example_run)
    supplement = [{"id": "conf-cap-deadbeef", "caveats": ["x" * 20]}]
    warnings: list[dict[str, str]] = []
    # No exception is raised any more.
    result = strengths_section(
        artifacts, supplied_strengths=supplement, warnings=warnings,
    )
    assert result == []
    assert warnings == [{
        "section": "strengths",
        "issue":   "unknown_capability_id",
        "id":      "conf-cap-deadbeef",
    }]
