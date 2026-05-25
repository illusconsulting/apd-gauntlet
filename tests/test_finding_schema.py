"""Schema validation tests for finding records."""
from __future__ import annotations

import json
import pathlib

import pytest
import yaml
from jsonschema import Draft202012Validator

REPO = pathlib.Path(__file__).parent.parent
SCHEMA_PATH = REPO / "schemas" / "finding.schema.json"
FIXTURES = REPO / "tests" / "fixtures"


def _load_schema():
    return json.loads(SCHEMA_PATH.read_text())


def _load_yaml(path):
    with open(path) as f:
        return yaml.safe_load(f)


@pytest.mark.parametrize(
    "fixture",
    [p.name for p in (FIXTURES / "valid").glob("finding-*.yaml")],
)
def test_valid_finding_fixtures_pass(fixture):
    schema = _load_schema()
    data = _load_yaml(FIXTURES / "valid" / fixture)
    validator = Draft202012Validator(schema)
    errors = list(validator.iter_errors(data["finding"]))
    assert errors == [], f"Unexpected errors: {[e.message for e in errors]}"


@pytest.mark.parametrize(
    "fixture",
    [p.name for p in (FIXTURES / "invalid").glob("finding-*.yaml")],
)
def test_invalid_finding_fixtures_fail(fixture):
    schema = _load_schema()
    data = _load_yaml(FIXTURES / "invalid" / fixture)
    validator = Draft202012Validator(schema)
    errors = list(validator.iter_errors(data["finding"]))
    assert errors, f"Expected validation errors for {fixture}, got none"
