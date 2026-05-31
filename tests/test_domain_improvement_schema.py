"""Schema validation tests for the domain-improvement record + doc + delta-doc."""
from __future__ import annotations

import json
import pathlib

import pytest
import yaml
from jsonschema import Draft202012Validator
from referencing import Registry, Resource

REPO = pathlib.Path(__file__).parent.parent
SCHEMA_DIR = REPO / "schemas"
FIXTURES = REPO / "tests" / "fixtures"


def _build_registry() -> Registry:
    resources = []
    for schema_path in sorted(SCHEMA_DIR.glob("*.schema.json")):
        schema = json.loads(schema_path.read_text())
        sid = schema.get("$id")
        if sid:
            resources.append((sid, Resource.from_contents(schema)))
    return Registry().with_resources(resources)


def _validator(schema_name: str) -> Draft202012Validator:
    schema = json.loads((SCHEMA_DIR / schema_name).read_text())
    return Draft202012Validator(schema, registry=_build_registry())


# (fixture file, schema file) for fixtures that MUST validate clean.
# All fixtures use the dimpr- prefix so they never collide with the domain-*.yaml
# glob in tests/test_other_schemas.py (which validates against the PACK schema).
VALID = [
    ("valid/dimpr-record.yaml", "domain-improvement.schema.json"),
    ("valid/dimpr-common-pattern.yaml", "domain-improvement.schema.json"),
    ("valid/dimpr-nonrep-pattern.yaml", "domain-improvement.schema.json"),
    ("valid/dimpr-doc.yaml", "domain-improvements-doc.schema.json"),
    ("valid/dimpr-doc-empty.yaml", "domain-improvements-doc.schema.json"),
    ("valid/dimpr-coverage-delta-doc.yaml", "domain-coverage-delta-doc.schema.json"),
]

# (fixture file, schema file) for fixtures that MUST be rejected.
INVALID = [
    ("invalid/dimpr-bad-id.yaml", "domain-improvement.schema.json"),
    ("invalid/dimpr-bad-type.yaml", "domain-improvement.schema.json"),
    ("invalid/dimpr-bad-target-file.yaml", "domain-improvement.schema.json"),
    ("invalid/dimpr-empty-evidence.yaml", "domain-improvement.schema.json"),
    ("invalid/dimpr-no-snippet.yaml", "domain-improvement.schema.json"),
    ("invalid/dimpr-common-pattern-no-goal.yaml", "domain-improvement.schema.json"),
    ("invalid/dimpr-common-pattern-mismatch.yaml", "domain-improvement.schema.json"),
    ("invalid/dimpr-bad-pack-traversal.yaml", "domain-improvement.schema.json"),
    ("invalid/dimpr-uppercase-pack.yaml", "domain-improvement.schema.json"),
    ("invalid/dimpr-doc-no-examined.yaml", "domain-improvements-doc.schema.json"),
    ("invalid/dimpr-doc-empty-examined-domains.yaml", "domain-improvements-doc.schema.json"),
    ("invalid/dimpr-coverage-delta-doc-bad-genby.yaml", "domain-coverage-delta-doc.schema.json"),
]


@pytest.mark.parametrize(("fixture", "schema"), VALID)
def test_valid_fixtures_pass(fixture, schema):
    errors = list(_validator(schema).iter_errors(yaml.safe_load((FIXTURES / fixture).read_text())))
    assert errors == [], f"Unexpected errors in {fixture}: {[e.message for e in errors]}"


@pytest.mark.parametrize(("fixture", "schema"), INVALID)
def test_invalid_fixtures_rejected(fixture, schema):
    errors = list(_validator(schema).iter_errors(yaml.safe_load((FIXTURES / fixture).read_text())))
    assert errors, f"Expected {fixture} to be rejected by {schema}, but it validated clean"


def test_doc_ref_resolves_record_schema():
    """A doc with one real record exercises the absolute-$id $ref into the record schema."""
    doc = yaml.safe_load((FIXTURES / "valid/dimpr-doc.yaml").read_text())
    assert doc["improvements"], "doc fixture must carry >=1 record to exercise the $ref"
    errors = list(_validator("domain-improvements-doc.schema.json").iter_errors(doc))
    assert errors == []
