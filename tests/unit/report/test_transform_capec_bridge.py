# tests/unit/report/test_transform_capec_bridge.py
"""Report wiring for the derived CAPEC bridge (ADR-0022)."""
from __future__ import annotations

import pathlib
import shutil

import yaml
from apd_gauntlet.report.loader import RunArtifacts, load_run
from apd_gauntlet.report.transform import (
    build_apd_data,
    capec_bridge_view,
    taxonomy_dict,
)

EMPTY_METRICS = {"schema_version": 1, "findings_total": 0}
EXAMPLE = pathlib.Path(__file__).resolve().parents[3] / "examples" / \
    "apd-20260601-claim-event-bus" / "expected"

_CAPEC = {
    "schema_version": 1, "generated_by": "synthesizer",
    "bridges": [{"finding_id": "intg-1", "capec_id": "CAPEC-2",
                 "capec_name": "Inducing Account Lockout",
                 "cwe": ["CWE-645"], "attack": ["T1531"]}],
    "suggestions": [{"finding_id": "conf-1", "direction": "cwe_to_attack",
                     "via_capec": ["CAPEC-66"], "suggested": ["T1190"]}],
}


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


def test_capec_bridge_view_from_artifact() -> None:
    view = capec_bridge_view(_artifacts(capec_bridge=_CAPEC))
    assert view["bridges"][0]["capec_id"] == "CAPEC-2"
    assert view["bridges"][0]["cwe"] == ["CWE-645"]
    assert view["suggestions"][0]["direction"] == "cwe_to_attack"


def test_capec_bridge_view_empty_when_absent() -> None:
    view = capec_bridge_view(_artifacts(capec_bridge=None))
    assert view == {"bridges": [], "suggestions": []}


def test_build_apd_data_includes_capec_bridge_scene() -> None:
    data = build_apd_data(_artifacts(capec_bridge=_CAPEC))
    assert data["capec_bridge"]["bridges"][0]["capec_id"] == "CAPEC-2"
    assert data["capec_bridge"]["suggestions"][0]["via_capec"] == ["CAPEC-66"]


def test_build_apd_data_capec_bridge_empty_on_example() -> None:
    data = build_apd_data(load_run(EXAMPLE))
    assert data["capec_bridge"] == {"bridges": [], "suggestions": []}


def test_taxonomy_dict_has_capec_branch_with_url_and_cross_ids() -> None:
    tax = taxonomy_dict(_artifacts(capec_bridge=_CAPEC))
    assert tax["CAPEC-2"]["family"] == "MITRE CAPEC"
    assert tax["CAPEC-2"]["url"] == "https://capec.mitre.org/data/definitions/2.html"
    assert tax["CAPEC-2"]["title"] == "Inducing Account Lockout"
    # CAPEC suggested via_capec also resolves.
    assert tax["CAPEC-66"]["family"] == "MITRE CAPEC"
    # The CWE + ATT&CK ids the bridge references resolve too (so chips render).
    assert "CWE-645" in tax
    assert "T1531" in tax
    # The suggested technique resolves.
    assert "T1190" in tax


def test_loader_capec_bridge_absent_on_example() -> None:
    assert load_run(EXAMPLE).capec_bridge is None


def test_loader_loads_capec_bridge(tmp_path: pathlib.Path) -> None:
    dst = tmp_path / "run"
    shutil.copytree(EXAMPLE, dst)
    (dst / "40-synthesis" / "capec-bridge.yaml").write_text(
        yaml.safe_dump(_CAPEC), encoding="utf-8")
    art = load_run(dst)
    assert art.capec_bridge is not None
    assert art.capec_bridge["bridges"][0]["capec_id"] == "CAPEC-2"
    assert "capec-bridge.yaml" in art.source_hashes
