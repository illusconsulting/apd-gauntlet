"""Schema validation tests for contradiction, severity-disagreement, coverage-matrix,
nist-coverage, attack-exposure, and domain records."""
from __future__ import annotations

import json
import pathlib

import pytest
import yaml
from jsonschema import Draft202012Validator

REPO = pathlib.Path(__file__).parent.parent
SCHEMA_DIR = REPO / "schemas"
FIXTURES = REPO / "tests" / "fixtures"

# Map prefix → (schema filename, root key in fixture YAML)
KINDS = {
    "contradiction":         ("contradiction.schema.json",         "contradiction"),
    "severity-disagreement": ("severity-disagreement.schema.json", "severity_disagreement"),
    "coverage-matrix":       ("coverage-matrix.schema.json",       "component"),
    "nist-coverage":         ("nist-coverage.schema.json",         "control"),
    "attack-exposure":       ("attack-exposure.schema.json",       "technique"),
    "domain": ("domain.schema.json", None),  # root-level, no wrapping key
}


def _validator_for(kind):
    schema = json.loads((SCHEMA_DIR / KINDS[kind][0]).read_text())
    return Draft202012Validator(schema)


def _record(kind, fixture):
    data = yaml.safe_load((FIXTURES / fixture).read_text())
    root_key = KINDS[kind][1]
    return data if root_key is None else data[root_key]


def _valid_fixtures():
    out = []
    for kind in KINDS:
        for p in sorted((FIXTURES / "valid").glob(f"{kind}-*.yaml")):
            out.append((kind, f"valid/{p.name}"))
    return out


def _invalid_fixtures():
    out = []
    for kind in KINDS:
        for p in sorted((FIXTURES / "invalid").glob(f"{kind}-*.yaml")):
            out.append((kind, f"invalid/{p.name}"))
    return out


@pytest.mark.parametrize(("kind", "fixture"), _valid_fixtures())
def test_valid_fixtures_pass(kind, fixture):
    validator = _validator_for(kind)
    errors = list(validator.iter_errors(_record(kind, fixture)))
    assert errors == [], f"Unexpected errors in {fixture}: {[e.message for e in errors]}"


@pytest.mark.parametrize(("kind", "fixture"), _invalid_fixtures())
def test_invalid_fixtures_fail(kind, fixture):
    validator = _validator_for(kind)
    errors = list(validator.iter_errors(_record(kind, fixture)))
    assert errors, f"Expected validation errors for {fixture}, got none"


def test_cwe_coverage_schema_validates():
    """CWE coverage rollup is a whole-document schema, not a per-record schema."""
    rollup = yaml.safe_load(
        (FIXTURES / "valid" / "cwe-coverage-valid.yaml").read_text()
    )
    schema = json.loads((SCHEMA_DIR / "cwe-coverage.schema.json").read_text())
    errors = list(Draft202012Validator(schema).iter_errors(rollup))
    assert errors == [], [e.message for e in errors]


def test_owasp_coverage_schema_validates():
    """OWASP coverage rollup is a whole-document schema covering Top 10, API Top 10, LLM Top 10."""
    rollup = yaml.safe_load(
        (FIXTURES / "valid" / "owasp-coverage-valid.yaml").read_text()
    )
    schema = json.loads((SCHEMA_DIR / "owasp-coverage.schema.json").read_text())
    errors = list(Draft202012Validator(schema).iter_errors(rollup))
    assert errors == [], [e.message for e in errors]
