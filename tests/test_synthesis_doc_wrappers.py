"""The doc-wrapper schemas validate the example golden rollups; reject-path + notes tests."""
from __future__ import annotations

import json
import pathlib

import pytest
import yaml
from apd_gauntlet.validate import SYNTHESIS_ROLLUPS, build_registry
from jsonschema import Draft202012Validator

REPO = pathlib.Path(__file__).parent.parent
SCHEMA_DIR = REPO / "schemas"
EXAMPLE_SYNTH = REPO / "examples" / "apd-20260601-claim-event-bus" / "expected" / "40-synthesis"

WRAPPERS = {
    "nist-coverage.yaml": "nist-coverage-doc.schema.json",
    "attack-exposure.yaml": "attack-exposure-doc.schema.json",
    "apd-coverage-matrix.yaml": "coverage-matrix-doc.schema.json",
    # I5 — the apply-clusters annex outputs (both present in the example golden).
    "severity-disagreements.yaml": "severity-disagreements-doc.schema.json",
    "contradictions.yaml": "contradictions-doc.schema.json",
}

# Plan 3 wires ALL five wrappers globally into SYNTHESIS_ROLLUPS.
WIRED_WRAPPERS = {
    "nist-coverage.yaml": "nist-coverage-doc.schema.json",
    "attack-exposure.yaml": "attack-exposure-doc.schema.json",
    "apd-coverage-matrix.yaml": "coverage-matrix-doc.schema.json",
    "severity-disagreements.yaml": "severity-disagreements-doc.schema.json",
    "contradictions.yaml": "contradictions-doc.schema.json",
}


def _validator(schema_name):
    schema = json.loads((SCHEMA_DIR / schema_name).read_text())
    return Draft202012Validator(schema, registry=build_registry())


def test_wrappers_validate_example_rollups():
    for filename, schema_name in WRAPPERS.items():
        doc = yaml.safe_load((EXAMPLE_SYNTH / filename).read_text())
        errors = list(_validator(schema_name).iter_errors(doc))
        assert errors == [], f"{filename}: {[e.message for e in errors]}"


def test_wired_wrappers_in_synthesis_rollups():
    """All five doc wrappers (nist/attack/matrix + sev-dis/contradictions) are wired (Plan 3)."""
    for filename, schema_name in WIRED_WRAPPERS.items():
        assert SYNTHESIS_ROLLUPS.get(filename) == schema_name, (
            f"{filename} should be wired to {schema_name} in SYNTHESIS_ROLLUPS"
        )


def test_new_artifacts_wired_into_synthesis_rollups():
    assert SYNTHESIS_ROLLUPS["cluster-candidates.yaml"] == "cluster-candidates.schema.json"
    assert SYNTHESIS_ROLLUPS["cluster-decisions.yaml"] == "cluster-decisions.schema.json"
    assert SYNTHESIS_ROLLUPS["rejected-records.yaml"] == "rejected-records.schema.json"
    assert SYNTHESIS_ROLLUPS["report-audit.yaml"] == "report-audit.schema.json"


# ---------------------------------------------------------------------------
# Reject-path tests — one per wrapper schema
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("schema_name,bad_doc,description", [
    (
        "nist-coverage-doc.schema.json",
        {"controls": "not-an-array"},
        "controls must be an array",
    ),
    (
        "nist-coverage-doc.schema.json",
        {"unexpected_key": []},
        "missing required root key 'controls'",
    ),
    (
        "attack-exposure-doc.schema.json",
        {"techniques": "not-an-array"},
        "techniques must be an array",
    ),
    (
        "attack-exposure-doc.schema.json",
        {"unexpected_key": []},
        "missing required root key 'techniques'",
    ),
    (
        "coverage-matrix-doc.schema.json",
        {"components": "not-an-array"},
        "components must be an array",
    ),
    (
        "coverage-matrix-doc.schema.json",
        {"unexpected_key": []},
        "missing required root key 'components'",
    ),
    (
        "severity-disagreements-doc.schema.json",
        {"severity_disagreements": "not-an-array"},
        "severity_disagreements must be an array",
    ),
    (
        "severity-disagreements-doc.schema.json",
        {"unexpected_key": [], "severity_disagreements": []},
        "unexpected top-level key rejected by additionalProperties:false",
    ),
    (
        "contradictions-doc.schema.json",
        {"contradictions": "not-an-array"},
        "contradictions must be an array",
    ),
    (
        "contradictions-doc.schema.json",
        {"unexpected_key": [], "contradictions": []},
        "unexpected top-level key rejected by additionalProperties:false",
    ),
])
def test_wrapper_reject_path(schema_name, bad_doc, description):
    errors = list(_validator(schema_name).iter_errors(bad_doc))
    assert errors, (
        f"{schema_name} should REJECT {description!r} but produced no errors"
    )


# ---------------------------------------------------------------------------
# Accept tests — notes field allowed on annex wrappers (Fix 2)
# ---------------------------------------------------------------------------

def test_severity_disagreements_accepts_notes():
    """A doc with severity_disagreements=[] and notes=str validates (legacy-run compat)."""
    doc = {"severity_disagreements": [], "notes": "No disagreements this run."}
    errors = list(_validator("severity-disagreements-doc.schema.json").iter_errors(doc))
    assert errors == [], f"Unexpected errors: {[e.message for e in errors]}"


def test_contradictions_accepts_notes():
    """A doc with contradictions=[] and notes=str validates (legacy-run compat)."""
    doc = {"contradictions": [], "notes": "No contradictions this run."}
    errors = list(_validator("contradictions-doc.schema.json").iter_errors(doc))
    assert errors == [], f"Unexpected errors: {[e.message for e in errors]}"
