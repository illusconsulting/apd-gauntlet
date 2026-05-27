"""Schema validation tests for contradiction, severity-disagreement, coverage-matrix,
nist-coverage, attack-exposure, and domain records."""
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

# Map prefix → (schema filename, root key in fixture YAML)
KINDS = {
    "contradiction":         ("contradiction.schema.json",         "contradiction"),
    "severity-disagreement": ("severity-disagreement.schema.json", "severity_disagreement"),
    "coverage-matrix":       ("coverage-matrix.schema.json",       "component"),
    "nist-coverage":         ("nist-coverage.schema.json",         "control"),
    "attack-exposure":       ("attack-exposure.schema.json",       "technique"),
    "domain": ("domain.schema.json", None),  # root-level, no wrapping key
}


def _build_registry():
    resources = []
    for schema_path in sorted(SCHEMA_DIR.glob("*.schema.json")):
        schema = json.loads(schema_path.read_text())
        sid = schema.get("$id")
        if sid:
            resources.append((sid, Resource.from_contents(schema)))
    return Registry().with_resources(resources)


def _validator_for(kind):
    schema = json.loads((SCHEMA_DIR / KINDS[kind][0]).read_text())
    return Draft202012Validator(schema, registry=_build_registry())


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


def _validate_whole_doc_schema(fixture_name: str, schema_name: str) -> list:
    """Validate a whole-document YAML fixture against a top-level schema.

    Returns the list of jsonschema errors (empty if valid). Used for rollup
    schemas (cwe-coverage, owasp-coverage, d3fend-coverage) that validate
    the whole document rather than a record extracted by a root key (those
    use the KINDS parametrized pattern instead).
    """
    fixture_path = FIXTURES / "valid" / fixture_name
    schema_path = SCHEMA_DIR / schema_name
    data = yaml.safe_load(fixture_path.read_text())
    schema = json.loads(schema_path.read_text())
    return list(Draft202012Validator(schema, registry=_build_registry()).iter_errors(data))


def test_cwe_coverage_schema_validates() -> None:
    errors = _validate_whole_doc_schema("cwe-coverage-valid.yaml", "cwe-coverage.schema.json")
    assert errors == [], errors


def test_owasp_coverage_schema_validates() -> None:
    errors = _validate_whole_doc_schema("owasp-coverage-valid.yaml", "owasp-coverage.schema.json")
    assert errors == [], errors


def test_d3fend_coverage_schema_validates() -> None:
    errors = _validate_whole_doc_schema("d3fend-coverage-valid.yaml", "d3fend-coverage.schema.json")
    assert errors == [], errors


def test_threat_model_normalized_schema_validates() -> None:
    errors = _validate_whole_doc_schema(
        "threat-model-normalized-valid.yaml",
        "threat-model-normalized.schema.json",
    )
    assert errors == [], errors


def test_threat_model_coverage_schema_validates() -> None:
    errors = _validate_whole_doc_schema(
        "threat-model-coverage-valid.yaml",
        "threat-model-coverage.schema.json",
    )
    assert errors == [], errors


def test_asset_inventory_valid_fixture_validates() -> None:
    errors = _validate_whole_doc_schema(
        "asset-inventory-valid.yaml",
        "asset-inventory.schema.json",
    )
    assert errors == [], errors


def test_asset_graph_valid_fixture_validates() -> None:
    errors = _validate_whole_doc_schema(
        "asset-graph-valid.yaml",
        "asset-graph.schema.json",
    )
    assert errors == [], errors


def test_domain_accepts_crown_jewels_and_attacker_positions():
    """Domain with all three attack-path arrays should validate."""
    validator = _validator_for("domain")
    d = _record("domain", "valid/domain-with-attack-path.yaml")
    errors = list(validator.iter_errors(d))
    assert errors == [], f"Unexpected errors: {[e.message for e in errors]}"
    jewels = [j["pattern"] for j in d["crown_jewels"]]
    assert "phi_store" in jewels


def test_domain_crown_jewel_requires_pattern_and_description():
    """Crown jewel without description should fail."""
    validator = _validator_for("domain")
    bad = {
        "name": "test",
        "display_name": "Test",
        "version": "1.0.0",
        "framework_compat": ">=1.0.0",
        "description": "Test domain for validation",
        "includes": ["test.md"],
        "regulatory_anchors": [],
        "crown_jewels": [{"pattern": "foo"}],  # missing description
    }
    errors = list(validator.iter_errors(bad))
    assert errors, "Expected validation error for missing description"


def test_domain_attacker_position_requires_position_and_description():
    """Attacker position without description should fail."""
    validator = _validator_for("domain")
    bad = {
        "name": "test",
        "display_name": "Test",
        "version": "1.0.0",
        "framework_compat": ">=1.0.0",
        "description": "Test domain for validation",
        "includes": ["test.md"],
        "regulatory_anchors": [],
        "attacker_positions": [{"position": "foo"}],  # missing description
    }
    errors = list(validator.iter_errors(bad))
    assert errors, "Expected validation error for missing description"


def test_domain_default_trust_boundary_requires_boundary_and_description():
    """Trust boundary without description should fail."""
    validator = _validator_for("domain")
    bad = {
        "name": "test",
        "display_name": "Test",
        "version": "1.0.0",
        "framework_compat": ">=1.0.0",
        "description": "Test domain for validation",
        "includes": ["test.md"],
        "regulatory_anchors": [],
        "default_trust_boundaries": [{"boundary": "foo"}],  # missing description
    }
    errors = list(validator.iter_errors(bad))
    assert errors, "Expected validation error for missing description"


def test_attack_path_valid_fixture_validates() -> None:
    errors = _validate_whole_doc_schema(
        "attack-paths-valid.yaml",
        "attack-path.schema.json",
    )
    assert errors == [], errors


def test_defense_graph_valid_fixture_validates() -> None:
    errors = _validate_whole_doc_schema(
        "defense-graph-valid.yaml",
        "defense-graph.schema.json",
    )
    assert errors == [], errors
