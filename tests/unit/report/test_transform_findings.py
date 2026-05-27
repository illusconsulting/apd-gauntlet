# tests/unit/report/test_transform_findings.py
from __future__ import annotations

import pathlib

from apd_gauntlet.report.loader import load_run
from apd_gauntlet.report.transform import findings_array


def test_findings_array_includes_attack_path_findings(legacy_example_run: pathlib.Path) -> None:
    artifacts = load_run(legacy_example_run)
    arr = findings_array(artifacts, headline_supplement=None)
    assert len(arr) == len(artifacts.deduped_findings) + len(artifacts.attack_path_findings)


def test_findings_array_carries_required_fields(legacy_example_run: pathlib.Path) -> None:
    artifacts = load_run(legacy_example_run)
    arr = findings_array(artifacts, headline_supplement=None)
    for f in arr:
        assert {"id", "title", "goal", "tier", "severity", "confidence", "disposition"}.issubset(f.keys())


def test_findings_array_supplied_headlines_set_rank(legacy_example_run: pathlib.Path) -> None:
    artifacts = load_run(legacy_example_run)
    arr = findings_array(
        artifacts,
        headline_supplement=[
            {"id": "merged-7c2a4f91", "rank": 1},
            {"id": "merged-9c1f8d62", "rank": 2},
        ],
    )
    headlined = [f for f in arr if f.get("headline")]
    assert len(headlined) == 2
    ranks = sorted(f["headline_rank"] for f in headlined)
    assert ranks == [1, 2]


def test_findings_array_fallback_picks_top_10_by_sev_then_conf(legacy_example_run: pathlib.Path) -> None:
    """No supplement: algorithmic top-10 by (severity desc, confidence desc, id asc)."""
    _SEV_RANK = {"critical": 0, "high": 1, "medium": 2, "low": 3, "informational": 4, "info": 4}
    artifacts = load_run(legacy_example_run)
    arr = findings_array(artifacts, headline_supplement=None)
    headlined = sorted(
        [f for f in arr if f.get("headline")],
        key=lambda f: f["headline_rank"],
    )
    assert len(headlined) <= 10
    # Headline #1 must be the highest severity present in the full array.
    best_sev = min(arr, key=lambda f: _SEV_RANK.get(f["severity"], 9))["severity"]
    assert headlined[0]["severity"] == best_sev


def test_findings_array_unknown_supplement_id_dropped_silently(legacy_example_run: pathlib.Path) -> None:
    """Schema validator catches unknown ids; transform tolerates them so a stale
    report-data.yaml doesn't break the HTML render."""
    artifacts = load_run(legacy_example_run)
    arr = findings_array(
        artifacts,
        headline_supplement=[{"id": "conf-deadbeef", "rank": 1}],
    )
    headlined = [f for f in arr if f.get("headline")]
    assert headlined == []
