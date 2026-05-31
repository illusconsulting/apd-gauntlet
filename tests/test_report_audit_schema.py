"""report-audit schema: compact structural audit output."""
from __future__ import annotations

import json
import pathlib

from jsonschema import Draft202012Validator

REPO = pathlib.Path(__file__).parent.parent
SCHEMA = REPO / "schemas" / "report-audit.schema.json"


def _validator():
    return Draft202012Validator(json.loads(SCHEMA.read_text()))


def test_minimal_pass_audit():
    doc = {
        "schema_version": 1,
        "generated_by": "apd-gauntlet",
        "status": "pass",
        "checks": [{"name": "id_coverage_findings", "status": "pass", "detail": "90/90"}],
        "counts": {
            "deduped_findings_yaml": 15, "apath_findings_yaml": 75, "findings_data_js": 90,
            "capabilities_yaml": 10, "capabilities_data_js": 10,
            "nist_controls_yaml": 10, "nist_ids_in_taxonomy": 10,
            "attack_techniques_yaml": 4, "attack_techniques_data_js": 4,
        },
        "drift": [],
    }
    assert list(_validator().iter_errors(doc)) == []


def test_rejects_bad_status():
    doc = {"schema_version": 1, "generated_by": "apd-gauntlet", "status": "warn",
           "checks": [], "counts": {}, "drift": []}
    assert list(_validator().iter_errors(doc))
