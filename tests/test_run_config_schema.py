"""Schema tests for the .apd-run.yaml run-config."""
from __future__ import annotations

import json
import pathlib

import pytest
import yaml
from jsonschema import Draft202012Validator

REPO = pathlib.Path(__file__).resolve().parent.parent
SCHEMA = json.loads((REPO / "schemas" / "run-config.schema.json").read_text())
FIXTURES = REPO / "tests" / "fixtures"


def test_valid_run_config_passes():
    data = yaml.safe_load((FIXTURES / "valid/run-config.yaml").read_text())
    errors = list(Draft202012Validator(SCHEMA).iter_errors(data))
    assert errors == []


def test_invalid_run_config_fails():
    data = yaml.safe_load((FIXTURES / "invalid/run-config-traversal-and-bad-enum.yaml").read_text())
    errors = list(Draft202012Validator(SCHEMA).iter_errors(data))
    assert any("run_id" in str(e.path) for e in errors)
    assert any("code_recon" in str(e.path) for e in errors)


@pytest.mark.parametrize(
    "code_recon_value", ["enabled", "auto", "disabled"]
)
def test_all_code_recon_values_accepted(code_recon_value):
    data = {
        "run_id": "valid-run-id",
        "domain": "pbm",
        "framework_version": "1.1.0",
        "code_recon": code_recon_value,
    }
    errors = list(Draft202012Validator(SCHEMA).iter_errors(data))
    assert errors == []


def test_code_recon_optional_defaults_handled_by_validator():
    """Schema does NOT enforce default; init_run.py is responsible for writing
    'auto' when the field is absent. Test that omitting the field is legal."""
    data = {
        "run_id": "valid-run-id",
        "domain": "pbm",
        "framework_version": "1.1.0",
    }
    errors = list(Draft202012Validator(SCHEMA).iter_errors(data))
    assert errors == []


def test_run_config_accepts_taxonomies():
    """A run-config that declares a valid subset of framework taxonomies passes."""
    data = yaml.safe_load(
        (FIXTURES / "valid/run-config-with-taxonomies.yaml").read_text()
    )
    errors = list(Draft202012Validator(SCHEMA).iter_errors(data))
    assert errors == []


def test_run_config_rejects_unknown_taxonomy():
    """A run-config with an unrecognised taxonomy value must fail validation."""
    data = yaml.safe_load(
        (FIXTURES / "invalid/run-config-with-invalid-taxonomy.yaml").read_text()
    )
    errors = list(Draft202012Validator(SCHEMA).iter_errors(data))
    assert errors


def test_run_config_without_taxonomies_still_valid():
    """Omitting taxonomies entirely must remain valid (field is optional)."""
    data = yaml.safe_load((FIXTURES / "valid/run-config.yaml").read_text())
    errors = list(Draft202012Validator(SCHEMA).iter_errors(data))
    assert errors == []
