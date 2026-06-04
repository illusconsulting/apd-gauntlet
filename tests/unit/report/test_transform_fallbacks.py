# tests/unit/report/test_transform_fallbacks.py
from __future__ import annotations

import pathlib

from apd_gauntlet.report.loader import RunArtifacts, load_run
from apd_gauntlet.report.transform import (
    build_apd_data,
    contradictions_section,
    next_steps_section,
    posture_summary_section,
    severity_disagreements_section,
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


def _artifacts_with_notes(
    *, contradictions_notes: str | None = None, severity_notes: str | None = None,
) -> RunArtifacts:
    """Minimal RunArtifacts carrying only the note fields under test, so the
    note-passthrough wiring is verified without depending on a fixture run's
    specific contradictions/severity content."""
    return RunArtifacts(
        run_id="r", framework_version="1.0.0", domain_pack_name="p",
        domain_pack_version="1", subject="s", date="2026-01-01",
        asset_inventory={}, deduped_findings=[], deduped_capabilities=[],
        contradictions=[], contradictions_notes=contradictions_notes,
        severity_disagreements=[], severity_disagreements_notes=severity_notes,
        nist_coverage={}, attack_exposure={}, apd_coverage_matrix={},
        attack_paths=None, asset_graph=None, defense_graph=None,
        attack_path_findings=[], report_data=None,
        metrics=EMPTY_METRICS,
    )


def test_contradictions_section_shape(example_run: pathlib.Path) -> None:
    artifacts = load_run(example_run)
    out = contradictions_section(artifacts)
    for c in out:
        assert {"id", "finding", "capability", "comparison", "resolution"}.issubset(c.keys())
        assert {"id", "assertion"}.issubset(c["finding"].keys())
        assert {"id", "assertion"}.issubset(c["capability"].keys())


def test_severity_disagreements_section_shape(example_run: pathlib.Path) -> None:
    artifacts = load_run(example_run)
    out = severity_disagreements_section(artifacts)
    for d in out:
        assert {"id", "agents", "chosen", "rationale"}.issubset(d.keys())
        for a in d["agents"]:
            assert {"lens", "severity"}.issubset(a.keys())


def test_next_steps_supplied_passes_through(example_run: pathlib.Path) -> None:
    supplement = [{"rank": 1, "text": "Do the thing.", "refs": ["merged-7c2a4f91"]}]
    assert next_steps_section(supplement) == supplement


def test_next_steps_absent_returns_empty(example_run: pathlib.Path) -> None:
    assert next_steps_section(None) == []


def test_posture_summary_supplied(example_run: pathlib.Path) -> None:
    supplied = {"trustworthiness": "T", "scalability": "S", "auditability": "A"}
    assert posture_summary_section(supplied) == supplied


def test_posture_summary_absent_returns_placeholders(example_run: pathlib.Path) -> None:
    out = posture_summary_section(None)
    assert set(out.keys()) == {"trustworthiness", "scalability", "auditability"}
    for v in out.values():
        assert isinstance(v, str) and v


def test_build_apd_data_assembles_full_window_object(example_run: pathlib.Path) -> None:
    artifacts = load_run(example_run)
    data = build_apd_data(artifacts, run_dir=example_run)
    # Spot-check the top-level keys the React template expects.
    for key in (
        "meta", "summary", "capabilities", "strengths", "findings",
        "contradictions", "contradictions_notes",
        "severity_disagreements", "severity_disagreements_notes",
        "nist_rollup", "attack_exposure", "apd_matrix",
        "attack_paths", "next_steps", "taxonomy",
    ):
        assert key in data, f"missing key {key}"


def test_contradictions_notes_pulled_from_yaml() -> None:
    """contradictions_notes loaded from the yaml must surface in build_apd_data."""
    note = "Scope clarification: these reflect language an out-of-context reviewer over-read."
    artifacts = _artifacts_with_notes(contradictions_notes=note)
    data = build_apd_data(artifacts)
    assert data["contradictions"] == []
    assert data["contradictions_notes"] == note


def test_severity_disagreements_notes_pulled_from_yaml() -> None:
    """severity_disagreements_notes loaded from the yaml must surface in build_apd_data."""
    note = "Severity deltas here are calibration differences, not unresolved disputes."
    artifacts = _artifacts_with_notes(severity_notes=note)
    data = build_apd_data(artifacts)
    assert data["severity_disagreements"] == []
    assert data["severity_disagreements_notes"] == note
