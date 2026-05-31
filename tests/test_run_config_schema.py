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
        "domains": ["pbm"],
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
        "domains": ["pbm"],
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


def test_run_config_accepts_threat_model_path_and_methodology_hint():
    data = yaml.safe_load(
        (FIXTURES / "valid/run-config-with-threat-model.yaml").read_text()
    )
    errors = list(Draft202012Validator(SCHEMA).iter_errors(data))
    assert errors == []


def test_run_config_rejects_unknown_methodology_hint():
    data = yaml.safe_load(
        (FIXTURES / "invalid/run-config-with-bad-methodology-hint.yaml").read_text()
    )
    errors = list(Draft202012Validator(SCHEMA).iter_errors(data))
    assert errors  # truthy: rejected by the enum


def test_run_config_accepts_crown_jewels_and_attacker_positions():
    """A run-config with crown_jewels and attacker_positions passes."""
    data = yaml.safe_load(
        (FIXTURES / "valid/run-config-with-attack-path.yaml").read_text()
    )
    errors = list(Draft202012Validator(SCHEMA).iter_errors(data))
    assert errors == []
    assert data["crown_jewels"] == ["phi_store", "pde_submission_pipeline"]
    assert "compromised_pharmacy_credential" in data["attacker_positions"]


def test_run_config_accepts_attack_path_analysis_tuning_block():
    """A run-config with attack_path_analysis tuning passes."""
    data = yaml.safe_load(
        (FIXTURES / "valid/run-config-with-attack-path.yaml").read_text()
    )
    errors = list(Draft202012Validator(SCHEMA).iter_errors(data))
    assert errors == []
    assert data["attack_path_analysis"]["max_hop"] == 6
    assert data["attack_path_analysis"]["max_paths_per_pair"] == 25
    assert data["attack_path_analysis"]["bottleneck_threshold"] == 4


def test_run_config_rejects_max_hop_above_cap():
    """max_hop=20 should violate maximum=12."""
    data = yaml.safe_load(
        (FIXTURES / "invalid/run-config-with-bad-max-hop.yaml").read_text()
    )
    errors = list(Draft202012Validator(SCHEMA).iter_errors(data))
    assert errors, "max_hop=20 should violate maximum=12"


def test_run_config_rejects_max_paths_per_pair_above_cap():
    """max_paths_per_pair=500 should violate maximum=200."""
    data = {
        "run_id": "test-run",
        "domains": ["pbm"],
        "framework_version": "1.4.0",
        "attack_path_analysis": {"max_paths_per_pair": 500},
    }
    errors = list(Draft202012Validator(SCHEMA).iter_errors(data))
    assert errors, "max_paths_per_pair=500 should violate maximum=200"


def test_run_config_requires_domains_list():
    """domains is required and must be a non-empty array."""
    data = {"run_id": "r", "framework_version": "1.1.0"}
    errors = list(Draft202012Validator(SCHEMA).iter_errors(data))
    assert any("domains" in e.message for e in errors)


def test_run_config_accepts_multiple_domains():
    """domains may contain more than one pack name."""
    data = {"run_id": "r", "domains": ["pbm", "api-security"], "framework_version": "1.1.0"}
    errors = list(Draft202012Validator(SCHEMA).iter_errors(data))
    assert errors == []


def test_run_config_rejects_empty_domains():
    data = {"run_id": "r", "domains": [], "framework_version": "1.1.0"}
    errors = list(Draft202012Validator(SCHEMA).iter_errors(data))
    assert errors, "empty domains must violate minItems:1"


def test_run_config_rejects_legacy_domain_key():
    """Hard cutover: the singular `domain` key is no longer a known property."""
    data = {"run_id": "r", "domain": "pbm", "framework_version": "1.1.0"}
    errors = list(Draft202012Validator(SCHEMA).iter_errors(data))
    assert errors, "legacy singular `domain` must be rejected (additionalProperties:false)"
