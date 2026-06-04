# tests/unit/report/test_tier4_shape_c_and_matrix.py
"""Regression tests for PR-T4-E: two related transform.py cleanup defects.

1. Caldera Shape-C ``sub_techniques`` formerly emitted a duplicate row when a
   ``sub_id`` was also a top-level key in ``technique_to_findings``. The fix
   tracks emitted IDs in a set and prefers the top-level row (which carries
   the actual findings list) over the degenerate sub-row.
2. ``_matrix_rows_from_dedup`` formerly dropped findings whose ``apd_goal``
   was ``None`` or unknown. The fix surfaces a synthetic ``"(no goal)"`` row
   when any such findings exist AND, when a ``warnings`` aggregator is
   supplied, appends a structured ``{section: "apd_matrix", issue:
   "findings_with_unknown_goal", count: <n>}`` entry so the loss-of-signal is
   visible in ``data.meta.warnings``.
"""
from __future__ import annotations

from typing import Any

from apd_gauntlet.report.loader import RunArtifacts
from apd_gauntlet.report.transform import (
    _matrix_rows_from_dedup,
    attack_exposure_rows,
    build_apd_data,
)

EMPTY_METRICS = {
    "schema_version": 1,
    "findings_total": 0, "findings_pre_dedup": 0,
    "cross_lens_merged_clusters": 0, "linked_clusters": 0,
    "bySeverity": {"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0},
    "byDisposition": {"gap": 0, "blocked": 0, "risk": 0, "uncertainty": 0, "ok": 0},
    "byTier": {"trustworthiness": 0, "scalability": 0, "auditability": 0},
    "capabilities_total": 0, "capabilities_pre_dedup": 0,
    "capabilitiesByMaturity": {"designed": 0, "implemented": 0, "tested": 0, "operationalized": 0},
    "contradictions": 0, "severity_disagreements": 0,
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_artifacts(
    *,
    deduped_findings: list[dict[str, Any]] | None = None,
    deduped_capabilities: list[dict[str, Any]] | None = None,
    attack_exposure: dict[str, Any] | None = None,
    apd_coverage_matrix: dict[str, Any] | None = None,
    attack_path_findings: list[dict[str, Any]] | None = None,
) -> RunArtifacts:
    """Construct a minimal RunArtifacts for transform-level unit tests."""
    return RunArtifacts(
        run_id="r",
        framework_version="1",
        domain_pack_name="p",
        domain_pack_version="1",
        subject="s",
        date="2026-01-01",
        asset_inventory={},
        deduped_findings=deduped_findings or [],
        deduped_capabilities=deduped_capabilities or [],
        contradictions=[],
        contradictions_notes=None,
        severity_disagreements=[],
        severity_disagreements_notes=None,
        nist_coverage={},
        attack_exposure=attack_exposure or {},
        apd_coverage_matrix=apd_coverage_matrix or {},
        attack_paths=None,
        asset_graph=None,
        defense_graph=None,
        attack_path_findings=attack_path_findings or [],
        report_data=None,
        metrics=EMPTY_METRICS,
    )


# ---------------------------------------------------------------------------
# Defect 1 — Shape-C sub_technique dedup
# ---------------------------------------------------------------------------


def test_shape_c_no_duplicate_when_sub_id_is_also_top_level() -> None:
    """When a sub_id appears under a parent's sub_techniques list AND as its
    own top-level key in technique_to_findings, the row must be emitted only
    once. The top-level entry wins because it carries actual findings."""
    art = _make_artifacts(
        attack_exposure={
            "technique_to_findings": {
                "T1078": {
                    "description": "Valid Accounts",
                    "findings": ["f-1"],
                    "sub_techniques": ["T1078.004"],
                },
                "T1078.004": {
                    "description": "Cloud Accounts",
                    "findings": ["f-2", "f-3"],
                },
            },
        },
    )
    rows = attack_exposure_rows(art)
    ids = [r["id"] for r in rows]
    # T1078.004 must appear exactly once — driven by its top-level entry,
    # not by T1078's sub_techniques list.
    assert ids.count("T1078.004") == 1, (
        f"expected exactly one T1078.004 row, got {ids}"
    )
    # The surviving T1078.004 row must be the findings-bearing one (the
    # top-level row), not the degenerate findings=0 sub-row.
    sub_row = next(r for r in rows if r["id"] == "T1078.004")
    assert sub_row["findings"] == 2
    assert sub_row["name"] == "Cloud Accounts"


def test_shape_c_emits_sub_techniques_normally_when_no_overlap() -> None:
    """Regression check: when a sub_id has no corresponding top-level entry,
    the sub-row is emitted as before (with findings=0 and empty name)."""
    art = _make_artifacts(
        attack_exposure={
            "technique_to_findings": {
                "T1059": {
                    "description": "Command and Scripting Interpreter",
                    "findings": ["f-1"],
                    "sub_techniques": ["T1059.001", "T1059.003"],
                },
            },
        },
    )
    rows = attack_exposure_rows(art)
    ids = [r["id"] for r in rows]
    # Parent row + both sub-rows.
    assert "T1059" in ids
    assert "T1059.001" in ids
    assert "T1059.003" in ids
    # Sub-rows carry the synthetic findings=0 / empty-name shape.
    sub_one = next(r for r in rows if r["id"] == "T1059.001")
    assert sub_one["findings"] == 0
    assert sub_one["name"] == ""


def test_shape_c_no_duplicate_when_two_parents_share_sub_id() -> None:
    """Edge case: two parents both list the same sub_id under their
    sub_techniques. Without dedup the sub-row would be emitted twice."""
    art = _make_artifacts(
        attack_exposure={
            "technique_to_findings": {
                "T1078": {
                    "description": "Valid Accounts",
                    "findings": ["f-1"],
                    "sub_techniques": ["T1078.999"],
                },
                "T1110": {
                    "description": "Brute Force",
                    "findings": ["f-2"],
                    "sub_techniques": ["T1078.999"],
                },
            },
        },
    )
    rows = attack_exposure_rows(art)
    ids = [r["id"] for r in rows]
    assert ids.count("T1078.999") == 1


# ---------------------------------------------------------------------------
# Defect 2 — _matrix_rows_from_dedup no-goal surface
# ---------------------------------------------------------------------------


def test_matrix_rows_from_dedup_no_goal_bucket_when_present() -> None:
    """A finding with apd_goal=None must contribute to a synthetic
    "(no goal)" row instead of being silently dropped."""
    art = _make_artifacts(
        deduped_findings=[
            {
                "id": "f-1",
                "apd_goal": "confidentiality",
                "evidence": [{"artifact": "svc-a"}],
            },
            {
                "id": "f-2",
                "apd_goal": None,
                "evidence": [{"artifact": "svc-b"}],
            },
        ],
    )
    rows = _matrix_rows_from_dedup(art)
    components = [r["component"] for r in rows]
    assert "svc-a" in components
    assert "(no goal)" in components
    # The "(no goal)" row's cells are all "silent" — we cannot attribute the
    # finding to a particular goal column.
    no_goal_row = next(r for r in rows if r["component"] == "(no goal)")
    assert set(no_goal_row["cells"].values()) == {"silent"}


def test_matrix_rows_from_dedup_unknown_goal_treated_as_no_goal() -> None:
    """Findings with an apd_goal NOT in the canonical _GOAL_SHORT list are
    treated identically to None — they land in the (no goal) bucket."""
    art = _make_artifacts(
        deduped_findings=[
            {
                "id": "f-1",
                "apd_goal": "not_a_real_goal",
                "evidence": [{"artifact": "svc-a"}],
            },
        ],
    )
    rows = _matrix_rows_from_dedup(art)
    components = [r["component"] for r in rows]
    assert "(no goal)" in components


def test_matrix_rows_from_dedup_warning_recorded() -> None:
    """When no-goal findings are present AND a warnings list is supplied, a
    structured warning is appended."""
    art = _make_artifacts(
        deduped_findings=[
            {"id": "f-1", "apd_goal": None, "evidence": [{"artifact": "svc-a"}]},
            {"id": "f-2", "apd_goal": None, "evidence": [{"artifact": "svc-b"}]},
        ],
    )
    warnings: list[dict[str, str]] = []
    _matrix_rows_from_dedup(art, warnings=warnings)
    no_goal_warnings = [
        w for w in warnings
        if w.get("section") == "apd_matrix"
        and w.get("issue") == "findings_with_unknown_goal"
    ]
    assert len(no_goal_warnings) == 1
    assert no_goal_warnings[0]["count"] == "2"


def test_matrix_rows_from_dedup_no_synthetic_row_on_clean_input() -> None:
    """When every finding has a recognized apd_goal, no "(no goal)" row and
    no warning are emitted."""
    art = _make_artifacts(
        deduped_findings=[
            {
                "id": "f-1",
                "apd_goal": "confidentiality",
                "evidence": [{"artifact": "svc-a"}],
            },
            {
                "id": "f-2",
                "apd_goal": "integrity",
                "evidence": [{"artifact": "svc-b"}],
            },
        ],
    )
    warnings: list[dict[str, str]] = []
    rows = _matrix_rows_from_dedup(art, warnings=warnings)
    components = [r["component"] for r in rows]
    assert "(no goal)" not in components
    assert warnings == []


def test_matrix_rows_from_dedup_warnings_kwarg_optional() -> None:
    """Omitting the warnings kwarg must keep working — the synthetic row
    still appears so partial signal is preserved on the data side, but no
    warning recording happens (callers that don't care don't pay)."""
    art = _make_artifacts(
        deduped_findings=[
            {"id": "f-1", "apd_goal": None, "evidence": [{"artifact": "svc-a"}]},
        ],
    )
    # No warnings kwarg — must not raise.
    rows = _matrix_rows_from_dedup(art)
    components = [r["component"] for r in rows]
    assert "(no goal)" in components


def test_matrix_rows_from_dedup_no_goal_findings_only() -> None:
    """When ALL findings are no-goal, the only emitted row is the synthetic
    "(no goal)" row."""
    art = _make_artifacts(
        deduped_findings=[
            {"id": "f-1", "apd_goal": None, "evidence": [{"artifact": "svc-a"}]},
        ],
    )
    rows = _matrix_rows_from_dedup(art)
    assert len(rows) == 1
    assert rows[0]["component"] == "(no goal)"


# ---------------------------------------------------------------------------
# End-to-end: build_apd_data threads warnings through apd_matrix
# ---------------------------------------------------------------------------


def test_build_apd_data_aggregates_apd_matrix_warnings() -> None:
    """End-to-end: a Shape-D run (matrix-keyed apd_coverage_matrix) with a
    no-goal finding must produce a data.meta.warnings entry whose
    section=apd_matrix."""
    art = _make_artifacts(
        deduped_findings=[
            {
                "id": "f-1",
                "title": "no-goal finding",
                "severity": "low",
                "confidence": "low",
                "disposition": "gap",
                "apd_goal": None,
                "apd_tier": "assure_trustworthiness",
                "evidence": [{"artifact": "svc-a"}],
            },
        ],
        apd_coverage_matrix={
            # Shape D — caldera-era matrix-keyed counts.
            "matrix": {
                "confidentiality": {
                    "findings_total": 0,
                    "capabilities_total": 0,
                },
            },
        },
    )
    data = build_apd_data(art)
    matrix_warnings = [
        w for w in data["meta"]["warnings"]
        if w.get("section") == "apd_matrix"
        and w.get("issue") == "findings_with_unknown_goal"
    ]
    assert matrix_warnings, (
        "expected an apd_matrix findings_with_unknown_goal warning, "
        f"got {data['meta']['warnings']!r}"
    )
    assert matrix_warnings[0]["count"] == "1"
    # The synthetic row must also show up in the rendered matrix.
    components = [r["component"] for r in data["apd_matrix"]["rows"]]
    assert "(no goal)" in components
