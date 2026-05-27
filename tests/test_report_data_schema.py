"""Schema validation tests for report-data.yaml."""
from __future__ import annotations

import json
import pathlib

import pytest
import yaml
from jsonschema import Draft202012Validator

REPO = pathlib.Path(__file__).resolve().parent.parent
SCHEMA_PATH = REPO / "schemas" / "report-data.schema.json"
EXAMPLE_PATH = REPO / "tests" / "fixtures" / "report-data" / "example.report-data.yaml"


def _validator() -> Draft202012Validator:
    schema = json.loads(SCHEMA_PATH.read_text())
    return Draft202012Validator(schema)


def test_example_validates() -> None:
    data = yaml.safe_load(EXAMPLE_PATH.read_text())
    errors = list(_validator().iter_errors(data))
    assert errors == [], [e.message for e in errors]


@pytest.mark.parametrize("missing", [
    "schema_version", "exec_summary", "headline_findings",
    "strengths", "next_steps", "posture_summary",
])
def test_missing_top_level_field_fails(missing: str) -> None:
    data = yaml.safe_load(EXAMPLE_PATH.read_text())
    data.pop(missing)
    errors = list(_validator().iter_errors(data))
    assert errors, f"removing {missing} should have failed validation"


def test_schema_version_must_be_one() -> None:
    data = yaml.safe_load(EXAMPLE_PATH.read_text())
    data["schema_version"] = 2
    errors = list(_validator().iter_errors(data))
    # jsonschema Draft 2020-12 reports const failures as "1 was expected"
    assert any(
        "const" in e.message or "1 was expected" in e.message or "2" in e.message
        for e in errors
    )


def test_headline_rank_must_be_integer() -> None:
    data = yaml.safe_load(EXAMPLE_PATH.read_text())
    data["headline_findings"][0]["rank"] = "1"  # string, not int
    errors = list(_validator().iter_errors(data))
    assert errors


def test_posture_summary_requires_three_tiers() -> None:
    data = yaml.safe_load(EXAMPLE_PATH.read_text())
    data["posture_summary"].pop("scalability")
    errors = list(_validator().iter_errors(data))
    assert errors
