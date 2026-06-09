"""Schema validation tests for capability records."""
from __future__ import annotations

import json
import pathlib

import pytest
import yaml
from jsonschema import Draft202012Validator
from referencing import Registry, Resource

REPO = pathlib.Path(__file__).parent.parent
FIXTURES = REPO / "tests" / "fixtures"


def _build_validator():
    schema_dir = REPO / "schemas"
    capability_schema = json.loads((schema_dir / "capability.schema.json").read_text())
    resources = []
    for schema_path in sorted(schema_dir.glob("*.schema.json")):
        schema = json.loads(schema_path.read_text())
        sid = schema.get("$id")
        if sid:
            resources.append((sid, Resource.from_contents(schema)))
    registry = Registry().with_resources(resources)
    return Draft202012Validator(capability_schema, registry=registry)


def _load_yaml(path):
    with open(path) as f:
        return yaml.safe_load(f)


@pytest.mark.parametrize(
    "fixture",
    [p.name for p in (FIXTURES / "valid").glob("capability-*.yaml")],
)
def test_valid_capability_fixtures_pass(fixture):
    validator = _build_validator()
    data = _load_yaml(FIXTURES / "valid" / fixture)
    errors = list(validator.iter_errors(data["capability"]))
    assert errors == [], f"Unexpected errors: {[e.message for e in errors]}"


@pytest.mark.parametrize(
    "fixture",
    [p.name for p in (FIXTURES / "invalid").glob("capability-*.yaml")],
)
def test_invalid_capability_fixtures_fail(fixture):
    validator = _build_validator()
    data = _load_yaml(FIXTURES / "invalid" / fixture)
    errors = list(validator.iter_errors(data["capability"]))
    assert errors, f"Expected validation errors for {fixture}, got none"


def test_capability_accepts_optional_d3fend():
    validator = _build_validator()
    data = _load_yaml(FIXTURES / "valid" / "capability-with-d3fend.yaml")
    errors = list(validator.iter_errors(data["capability"]))
    assert errors == [], f"Unexpected errors: {[e.message for e in errors]}"


def test_capability_rejects_d3fend_without_counters_attack():
    validator = _build_validator()
    data = _load_yaml(FIXTURES / "invalid" / "capability-with-malformed-d3fend.yaml")
    errors = list(validator.iter_errors(data["capability"]))
    assert errors, "Expected validation errors for missing counters_attack, got none"


def test_capability_without_d3fend_still_valid():
    validator = _build_validator()
    data = _load_yaml(FIXTURES / "valid" / "capability-designed.yaml")
    errors = list(validator.iter_errors(data["capability"]))
    assert errors == [], f"Unexpected errors: {[e.message for e in errors]}"


def test_capability_accepts_optional_mitre_attack():
    validator = _build_validator()
    data = _load_yaml(FIXTURES / "valid" / "capability-with-mitre-attack.yaml")
    errors = list(validator.iter_errors(data["capability"]))
    assert errors == [], f"Unexpected errors: {[e.message for e in errors]}"


def test_capability_rejects_mitre_attack_entry_missing_required_field():
    validator = _build_validator()
    data = _load_yaml(FIXTURES / "invalid" / "capability-with-malformed-mitre-attack.yaml")
    errors = list(validator.iter_errors(data["capability"]))
    assert errors, "Expected validation errors for missing tactic and rationale, got none"


def test_capability_accepts_optional_masvs():
    validator = _build_validator()
    data = _load_yaml(FIXTURES / "valid" / "capability-with-masvs.yaml")
    errors = list(validator.iter_errors(data["capability"]))
    assert errors == [], f"Unexpected errors: {[e.message for e in errors]}"


def test_capability_rejects_invalid_masvs_format():
    validator = _build_validator()
    data = _load_yaml(FIXTURES / "invalid" / "capability-with-invalid-masvs.yaml")
    errors = list(validator.iter_errors(data["capability"]))
    assert errors, "Expected validation errors for malformed MASVS control id, got none"


def test_capability_control_mappings_has_no_maswe_property():
    """maswe is findings-only; capability control_mappings must not declare it."""
    import json
    schema = json.loads((REPO / "schemas" / "capability.schema.json").read_text())
    props = schema["properties"]["control_mappings"]["properties"]
    assert "masvs" in props
    assert "maswe" not in props
