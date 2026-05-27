"""PBM domain pack contract — crown jewels, attacker positions, trust boundaries."""
from __future__ import annotations

import json
from pathlib import Path

import yaml
from apd_gauntlet.validate import build_registry
from jsonschema import Draft202012Validator

REPO = Path(__file__).resolve().parent.parent
DOMAIN_PATH = REPO / "domains" / "pbm" / "domain.yaml"
SCHEMA_PATH = REPO / "schemas" / "domain.schema.json"


def _load_pbm_domain() -> dict:
    return yaml.safe_load(DOMAIN_PATH.read_text())


def _validate_domain(doc: dict) -> list:
    schema = json.loads(SCHEMA_PATH.read_text())
    registry = build_registry()
    validator = Draft202012Validator(schema, registry=registry)
    return list(validator.iter_errors(doc))


def test_pbm_domain_declares_phi_store_crown_jewel() -> None:
    d = _load_pbm_domain()
    jewels = [j["pattern"] for j in d["crown_jewels"]]
    assert "phi_store" in jewels
    assert "pde_submission_pipeline" in jewels
    assert "claim_adjudication_engine" in jewels


def test_pbm_domain_declares_compromised_pharmacy_credential_attacker_position() -> None:
    d = _load_pbm_domain()
    positions = [p["position"] for p in d["attacker_positions"]]
    assert "compromised_pharmacy_credential" in positions
    assert "compromised_vendor_integration" in positions
    assert "insider_with_member_service_role" in positions
    assert "compromised_dev_workstation" in positions
    assert "external_internet" in positions


def test_pbm_domain_declares_pharmacy_ingress_trust_boundary() -> None:
    d = _load_pbm_domain()
    boundaries = [b["boundary"] for b in d["default_trust_boundaries"]]
    assert "pharmacy_submission_ingress" in boundaries
    assert "member_portal_ingress" in boundaries
    assert "internal_to_pde_submission" in boundaries


def test_pbm_domain_validates_clean() -> None:
    d = _load_pbm_domain()
    errors = _validate_domain(d)
    assert errors == [], [e.message for e in errors]
