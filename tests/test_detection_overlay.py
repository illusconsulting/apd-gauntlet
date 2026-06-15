"""ATT&CK detection overlay — derived technique -> required-telemetry view (ADR-0022).

For each ATT&CK technique a finding exposes, the synthesizer attaches the data
components ATT&CK says are required to detect it. v1 surfaces detection
*requirements*; absence of detection data is silent.
"""
from __future__ import annotations

import json
import pathlib

import yaml
from apd_gauntlet.synthesis.rollup import RollupResult, _detection_rollup, build_rollups
from apd_gauntlet.validate import build_registry
from jsonschema import Draft202012Validator

REPO = pathlib.Path(__file__).parent.parent
SCHEMA_DIR = REPO / "schemas"

CATALOG = {
    "T1530": [{"data_component_id": "DC0025", "data_component_name": "Cloud Storage Access"},
              {"data_component_id": "DC0085", "data_component_name": "Network Traffic Content"}],
    "T1059": [{"data_component_id": "DC0031", "data_component_name": "Command Execution"}],
}


def _finding(fid, techniques):
    return {"id": fid, "control_mappings": {"mitre_attack": [{"technique": t} for t in techniques]}}


def test_rollup_result_has_detection_field():
    assert RollupResult().detection is None


def test_detection_rollup_attaches_required_data_components():
    doc = _detection_rollup([_finding("conf-1", ["T1530"])], CATALOG)
    assert doc["schema_version"] == 1
    assert doc["generated_by"] == "synthesizer"
    entry = {e["technique"]: e for e in doc["entries"]}["T1530"]
    assert entry["exposure_finding_count"] == 1
    assert entry["telemetry"] == "required"
    names = [c["data_component_name"] for c in entry["required_data_components"]]
    assert names == ["Cloud Storage Access", "Network Traffic Content"]


def test_detection_rollup_sub_technique_falls_back_to_parent():
    doc = _detection_rollup([_finding("conf-2", ["T1059.007"])], CATALOG)
    entry = doc["entries"][0]
    assert entry["technique"] == "T1059.007"
    assert entry["required_data_components"][0]["data_component_id"] == "DC0031"


def test_detection_rollup_silent_when_no_detection_data():
    # T9999 is not in the catalog and has no parent entry -> no row (silence).
    doc = _detection_rollup([_finding("conf-3", ["T9999"])], CATALOG)
    assert doc["entries"] == []


def test_detection_rollup_orders_by_exposure_then_id():
    findings = [_finding("a", ["T1059"]), _finding("b", ["T1530"]), _finding("c", ["T1530"])]
    doc = _detection_rollup(findings, CATALOG)
    # T1530 exposed by 2 findings -> first; T1059 by 1 -> second.
    assert [e["technique"] for e in doc["entries"]] == ["T1530", "T1059"]


# ---- build_rollups gating against the real bundled catalog ----

def _run(tmp_path, run_yaml, findings_yaml):
    run_dir = tmp_path / "run"
    (run_dir / "40-synthesis").mkdir(parents=True)
    (run_dir / "00-context").mkdir(parents=True)
    (run_dir / ".apd-run.yaml").write_text(run_yaml, encoding="utf-8")
    (run_dir / "40-synthesis" / "deduped-findings.yaml").write_text(findings_yaml, encoding="utf-8")
    (run_dir / "40-synthesis" / "deduped-capabilities.yaml").write_text(
        "capability: []\n", encoding="utf-8")
    (run_dir / "00-context" / "asset-inventory.yaml").write_text("assets: []\n", encoding="utf-8")
    return run_dir


# T1530 is a real technique with detection data in the bundled catalog.
_T1530_FINDING = (
    "finding:\n"
    "  - schema_version: 1\n"
    "    id: conf-aabbccdd\n"
    "    apd_goal: confidentiality\n"
    "    disposition: gap\n"
    "    control_mappings:\n"
    "      mitre_attack:\n"
    "        - technique: T1530\n"
    "          tactic: TA0010\n"
)


def test_build_rollups_skips_detection_when_attack_not_declared(tmp_path):
    run_dir = _run(tmp_path, "run_id: t\ndomain: pbm\ntaxonomies: [cwe]\n", _T1530_FINDING)
    assert build_rollups(run_dir).detection is None
    assert not (run_dir / "40-synthesis" / "detection-coverage.yaml").exists()


def test_build_rollups_emits_detection_when_attack_declared(tmp_path):
    run_dir = _run(tmp_path, "run_id: t\ndomain: pbm\ntaxonomies: [mitre_attack]\n", _T1530_FINDING)
    result = build_rollups(run_dir)
    assert result.detection is not None
    by_t = {e["technique"]: e for e in result.detection["entries"]}
    assert "T1530" in by_t
    assert by_t["T1530"]["required_data_components"]  # non-empty
    doc = yaml.safe_load((run_dir / "40-synthesis" / "detection-coverage.yaml").read_text())
    schema = json.loads((SCHEMA_DIR / "detection-coverage.schema.json").read_text())
    assert list(Draft202012Validator(schema, registry=build_registry()).iter_errors(doc)) == []
