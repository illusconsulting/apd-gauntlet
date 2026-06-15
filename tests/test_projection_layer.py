"""Compliance projection layer — derive HIPAA + CSF 2.0 from 800-53r5 coverage (ADR-0022).

A pure projection of the existing nist-coverage rollup through a published
crosswalk. Each projected target row inherits the contributing controls' posture
and provenance, carries the STRM relationship, and is flagged exact|partial — a
coverage view in another vocabulary, never a compliance attestation.
"""
from __future__ import annotations

import json
import pathlib

import yaml
from apd_gauntlet.synthesis.rollup import (
    RollupResult,
    _framework_projection_rollup,
    build_rollups,
)
from apd_gauntlet.validate import build_registry
from jsonschema import Draft202012Validator

REPO = pathlib.Path(__file__).parent.parent
SCHEMA_DIR = REPO / "schemas"

# Synthetic nist-coverage rows (the _nist_rollup output shape).
NIST_ROWS = [
    {"id": "AC-3", "finding_ids": ["conf-1"], "capability_ids": [], "posture": "gapped"},
    {"id": "SC-28", "finding_ids": [], "capability_ids": ["cap-1"], "posture": "covered"},
    {"id": "SC-8(1)", "finding_ids": ["conf-2"], "capability_ids": ["cap-2"],
     "posture": "gapped_and_covered"},
]
CROSSWALK = [
    {"target_id": "164.312(a)(1)", "target_title": "Access Control", "nist": "AC-3",
     "relationship": "intersects_with"},
    {"target_id": "164.312(a)(2)(iv)", "target_title": "Encryption", "nist": "SC-28",
     "relationship": "equal_to"},
    {"target_id": "164.312(e)(1)", "target_title": "Transmission Security", "nist": "SC-8",
     "relationship": "intersects_with"},
]


def test_rollup_result_has_projection_fields():
    rr = RollupResult()
    assert rr.hipaa is None and rr.csf2 is None


def test_projection_aggregates_controls_into_targets():
    doc = _framework_projection_rollup(NIST_ROWS, CROSSWALK, "hipaa")
    assert doc["schema_version"] == 1
    assert doc["target"] == "hipaa"
    by_t = {e["target_id"]: e for e in doc["entries"]}
    assert by_t["164.312(a)(1)"]["finding_ids"] == ["conf-1"]
    assert by_t["164.312(a)(1)"]["posture"] == "gapped"
    assert by_t["164.312(a)(2)(iv)"]["capability_ids"] == ["cap-1"]
    assert by_t["164.312(a)(2)(iv)"]["posture"] == "covered"


def test_projection_folds_control_enhancements_to_base():
    # SC-8(1) must match the crosswalk's base SC-8 mapping.
    doc = _framework_projection_rollup(NIST_ROWS, CROSSWALK, "hipaa")
    by_t = {e["target_id"]: e for e in doc["entries"]}
    entry = by_t["164.312(e)(1)"]
    assert entry["finding_ids"] == ["conf-2"]
    assert entry["capability_ids"] == ["cap-2"]
    assert entry["posture"] == "gapped_and_covered"
    # The actual cited control id (with the enhancement) is recorded as the source.
    assert entry["source_controls"] == [{"id": "SC-8(1)", "relationship": "intersects_with"}]


def test_projection_fidelity_exact_only_when_all_relationships_exact():
    doc = _framework_projection_rollup(NIST_ROWS, CROSSWALK, "hipaa")
    by_t = {e["target_id"]: e for e in doc["entries"]}
    # equal_to -> exact; intersects_with -> partial.
    assert by_t["164.312(a)(2)(iv)"]["fidelity"] == "exact"
    assert by_t["164.312(a)(1)"]["fidelity"] == "partial"


# ---- build_rollups gating against the real bundled seed crosswalks ----

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


_AC3_FINDING = (
    "finding:\n"
    "  - schema_version: 1\n"
    "    id: conf-aabbccdd\n"
    "    apd_goal: confidentiality\n"
    "    disposition: gap\n"
    "    control_mappings:\n"
    "      nist_800_53r5: [AC-3]\n"
)


def test_build_rollups_skips_projections_unless_declared(tmp_path):
    run_dir = _run(tmp_path, "run_id: t\ndomain: pbm\n", _AC3_FINDING)
    result = build_rollups(run_dir)
    assert result.hipaa is None and result.csf2 is None
    assert not (run_dir / "40-synthesis" / "hipaa-coverage.yaml").exists()


def test_build_rollups_emits_projections_when_declared(tmp_path):
    run_dir = _run(
        tmp_path, "run_id: t\ndomain: pbm\nprojections: [hipaa, csf2]\n", _AC3_FINDING)
    result = build_rollups(run_dir)
    assert result.hipaa is not None and result.csf2 is not None
    # AC-3 projects to HIPAA 164.312(a)(1) Access Control + CSF2 PR.AA-05.
    h_targets = {e["target_id"] for e in result.hipaa["entries"]}
    assert "164.312(a)(1)" in h_targets
    c_targets = {e["target_id"] for e in result.csf2["entries"]}
    assert "PR.AA-05" in c_targets
    for fname, schema in (("hipaa-coverage.yaml", "framework-coverage.schema.json"),
                          ("csf2-coverage.yaml", "framework-coverage.schema.json")):
        doc = yaml.safe_load((run_dir / "40-synthesis" / fname).read_text())
        s = json.loads((SCHEMA_DIR / schema).read_text())
        assert list(Draft202012Validator(s, registry=build_registry()).iter_errors(doc)) == []
