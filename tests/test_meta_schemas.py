"""Verify every schema under schemas/ is itself a valid JSON Schema draft 2020-12 document."""
from __future__ import annotations

import json
import pathlib

import pytest
from jsonschema import Draft202012Validator

REPO = pathlib.Path(__file__).parent.parent
SCHEMA_DIR = REPO / "schemas"


@pytest.mark.parametrize("schema_path", sorted(SCHEMA_DIR.glob("*.schema.json")))
def test_schema_is_valid_meta(schema_path):
    schema = json.loads(schema_path.read_text())
    Draft202012Validator.check_schema(schema)
