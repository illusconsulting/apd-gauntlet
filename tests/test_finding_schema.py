"""Schema validation tests for finding records."""
from __future__ import annotations

import json
import pathlib

import pytest
import yaml
from jsonschema import Draft202012Validator
from referencing import Registry, Resource

REPO = pathlib.Path(__file__).parent.parent
SCHEMA_DIR = REPO / "schemas"
SCHEMA_PATH = SCHEMA_DIR / "finding.schema.json"
FIXTURES = REPO / "tests" / "fixtures"


def _load_schema():
    return json.loads(SCHEMA_PATH.read_text())


def _build_registry():
    resources = []
    for schema_path in sorted(SCHEMA_DIR.glob("*.schema.json")):
        schema = json.loads(schema_path.read_text())
        sid = schema.get("$id")
        if sid:
            resources.append((sid, Resource.from_contents(schema)))
    return Registry().with_resources(resources)


def _build_validator(schema):
    return Draft202012Validator(schema, registry=_build_registry())


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
    validator = _build_validator(schema)
    errors = list(validator.iter_errors(data["finding"]))
    assert errors == [], f"Unexpected errors: {[e.message for e in errors]}"


@pytest.mark.parametrize(
    "fixture",
    [p.name for p in (FIXTURES / "invalid").glob("finding-*.yaml")],
)
def test_invalid_finding_fixtures_fail(fixture):
    schema = _load_schema()
    data = _load_yaml(FIXTURES / "invalid" / fixture)
    validator = _build_validator(schema)
    errors = list(validator.iter_errors(data["finding"]))
    assert errors, f"Expected validation errors for {fixture}, got none"


def test_finding_accepts_optional_cwe():
    schema = _load_schema()
    data = _load_yaml(FIXTURES / "valid" / "finding-with-cwe.yaml")
    validator = _build_validator(schema)
    errors = list(validator.iter_errors(data["finding"]))
    assert errors == [], f"Unexpected errors: {[e.message for e in errors]}"


def test_finding_accepts_optional_owasp_taxonomies():
    schema = _load_schema()
    data = _load_yaml(FIXTURES / "valid" / "finding-with-owasp.yaml")
    validator = _build_validator(schema)
    errors = list(validator.iter_errors(data["finding"]))
    assert errors == [], f"Unexpected errors: {[e.message for e in errors]}"


def test_finding_rejects_invalid_cwe_format():
    schema = _load_schema()
    data = _load_yaml(FIXTURES / "invalid" / "finding-with-invalid-cwe.yaml")
    validator = _build_validator(schema)
    errors = list(validator.iter_errors(data["finding"]))
    assert errors, "Expected validation errors for invalid CWE format, got none"


def test_finding_rejects_owasp_llm_top10_outside_published_range():
    schema = _load_schema()
    data = _load_yaml(FIXTURES / "invalid" / "finding-with-invalid-owasp-llm.yaml")
    validator = _build_validator(schema)
    errors = list(validator.iter_errors(data["finding"]))
    assert errors, "Expected validation errors for owasp_llm_top10 outside LLM01..LLM10"


def test_finding_without_new_taxonomies_still_valid():
    schema = _load_schema()
    data = _load_yaml(FIXTURES / "valid" / "finding-minimal.yaml")
    validator = _build_validator(schema)
    errors = list(validator.iter_errors(data["finding"]))
    assert errors == [], f"Unexpected errors: {[e.message for e in errors]}"
