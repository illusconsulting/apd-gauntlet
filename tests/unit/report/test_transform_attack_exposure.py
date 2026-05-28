# tests/unit/report/test_transform_attack_exposure.py
from __future__ import annotations

import pathlib
from unittest.mock import MagicMock

from apd_gauntlet.report.loader import load_run
from apd_gauntlet.report.transform import attack_exposure_rows


def test_rows_one_per_technique(example_run: pathlib.Path) -> None:
    """Row count matches flattened technique count from the fixture.

    For the new-shape fixture (techniques dict + sub_techniques), the expected
    count equals the number of entries that have citing_findings (either parent
    or sub-technique rows emitted by the transform).
    """
    artifacts = load_run(example_run)
    rows = attack_exposure_rows(artifacts)
    # crAPI fixture uses the new techniques-dict shape; count is >0.
    assert len(rows) > 0
    # Each row must have required fields.
    for r in rows:
        assert "id" in r
        assert "name" in r
        assert "findings" in r
        assert "mitigations" in r
        assert "coverage" in r


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
    assert "T1078" in by_id, "T1078 should be present in crAPI fixture rows"
    assert by_id["T1078"]["coverage"] == "uncovered"


def test_rows_partial_when_both_findings_and_mitigations(
    example_run: pathlib.Path,
) -> None:
    """T1110.001 in the crAPI fixture has both findings and mitigations → partial."""
    artifacts = load_run(example_run)
    rows = attack_exposure_rows(artifacts)
    by_id = {r["id"]: r for r in rows}
    # T1110.001 has citing_findings=[...] and countering_capabilities=[...].
    assert "T1110.001" in by_id, "T1110.001 sub-technique should appear as its own row"
    assert by_id["T1110.001"]["coverage"] == "partial"
    assert len(by_id["T1110.001"]["mitigations"]) > 0


def test_rows_mitigations_is_list_of_capability_ids(example_run: pathlib.Path) -> None:
    artifacts = load_run(example_run)
    rows = attack_exposure_rows(artifacts)
    for r in rows:
        assert isinstance(r["mitigations"], list)
        for m in r["mitigations"]:
            assert isinstance(m, str)


def test_rows_old_shape_covered_technique() -> None:
    """Synthetic old-shape: technique with findings=0 and mitigations → covered."""
    old_shape = {
        "technique": [
            {
                "id": "T1040",
                "name": "Network Sniffing",
                "exposure_finding_count": 0,
                "mitigated_by_capabilities": [
                    {"capability_id": "cap-abc123", "mitigation_id": "M1031"},
                ],
            },
            {
                "id": "T1059",
                "name": "Command and Scripting Interpreter",
                "exposure_finding_count": 3,
                "mitigated_by_capabilities": [],
            },
            {
                "id": "T1078",
                "name": "Valid Accounts",
                "exposure_finding_count": 2,
                "mitigated_by_capabilities": [
                    {"capability_id": "cap-def456", "mitigation_id": "M1026"},
                ],
            },
        ]
    }
    artifacts = MagicMock()
    artifacts.attack_exposure = old_shape

    rows = attack_exposure_rows(artifacts)
    assert len(rows) == 3

    by_id = {r["id"]: r for r in rows}
    assert by_id["T1040"]["coverage"] == "covered"
    assert by_id["T1059"]["coverage"] == "uncovered"
    assert by_id["T1078"]["coverage"] == "partial"
    assert by_id["T1040"]["mitigations"] == ["cap-abc123"]
