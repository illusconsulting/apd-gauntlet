# tests/unit/report/test_transform_derived_views.py
"""Report wiring for the derived detection overlay + compliance projections (ADR-0022)."""
from __future__ import annotations

from apd_gauntlet.report.loader import RunArtifacts
from apd_gauntlet.report.transform import (
    build_apd_data,
    compliance_projection_view,
    detection_coverage_view,
)

EMPTY_METRICS = {"schema_version": 1, "findings_total": 0}


def _artifacts(**overrides) -> RunArtifacts:
    base = {
        "run_id": "r", "framework_version": "1", "domain_pack_name": "pbm",
        "domain_pack_version": "1", "subject": "s", "date": "2026-01-01",
        "asset_inventory": {}, "deduped_findings": [], "deduped_capabilities": [],
        "contradictions": [], "contradictions_notes": None,
        "severity_disagreements": [], "severity_disagreements_notes": None,
        "nist_coverage": {}, "attack_exposure": {}, "apd_coverage_matrix": {},
        "attack_paths": None, "asset_graph": None, "defense_graph": None,
        "attack_path_findings": [], "report_data": None, "metrics": EMPTY_METRICS,
    }
    base.update(overrides)
    return RunArtifacts(**base)


_DETECTION = {"schema_version": 1, "generated_by": "synthesizer", "entries": [
    {"technique": "T1530", "technique_name": "Data from Cloud Storage",
     "exposure_finding_count": 1, "exposure_finding_ids": ["conf-1"],
     "required_data_components": [{"data_component_id": "DC0025",
                                   "data_component_name": "Cloud Storage Access"}],
     "telemetry": "required"}]}

_HIPAA = {"schema_version": 1, "generated_by": "synthesizer", "target": "hipaa", "entries": [
    {"target_id": "164.312(a)(1)", "target_title": "Access Control",
     "source_controls": [{"id": "AC-3", "relationship": "intersects_with"}],
     "finding_count": 1, "finding_ids": ["conf-1"], "capability_count": 0,
     "capability_ids": [], "posture": "gapped", "fidelity": "partial"}]}


def test_detection_coverage_view_from_artifact() -> None:
    rows = detection_coverage_view(_artifacts(detection_coverage=_DETECTION))
    assert rows[0]["technique"] == "T1530"
    assert rows[0]["required_data_components"][0]["data_component_id"] == "DC0025"


def test_detection_coverage_view_empty_when_absent() -> None:
    assert detection_coverage_view(_artifacts(detection_coverage=None)) == []


def test_compliance_projection_view_from_artifacts() -> None:
    view = compliance_projection_view(_artifacts(hipaa_coverage=_HIPAA))
    assert view["hipaa"][0]["target_id"] == "164.312(a)(1)"
    assert view["hipaa"][0]["fidelity"] == "partial"
    assert view["csf2"] == []


def test_compliance_projection_view_empty_when_absent() -> None:
    assert compliance_projection_view(_artifacts()) == {"hipaa": [], "csf2": []}


def test_build_apd_data_includes_derived_view_scenes() -> None:
    data = build_apd_data(_artifacts(detection_coverage=_DETECTION, hipaa_coverage=_HIPAA))
    assert data["detection_coverage"][0]["technique"] == "T1530"
    assert data["compliance_projection"]["hipaa"][0]["target_id"] == "164.312(a)(1)"


def test_build_apd_data_derived_scenes_empty_by_default() -> None:
    data = build_apd_data(_artifacts())
    assert data["detection_coverage"] == []
    assert data["compliance_projection"] == {"hipaa": [], "csf2": []}
