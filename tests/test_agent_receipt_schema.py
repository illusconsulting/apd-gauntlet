"""The agent-receipt schema accepts a minimal valid receipt and rejects prose/extra keys."""
from __future__ import annotations

import json
import pathlib

from jsonschema import Draft202012Validator

REPO = pathlib.Path(__file__).parent.parent
SCHEMA = REPO / "schemas" / "agent-receipt.schema.json"


def _validator():
    return Draft202012Validator(json.loads(SCHEMA.read_text()))


def test_minimal_valid_receipt():
    receipt = {
        "agent": "apd-confidentiality",
        "status": "ok",
        "outputs": [
            {"path": "10-trustworthiness/confidentiality.findings.yaml", "schema_valid": True}
        ],
        "counts": {"findings_by_severity": {"high": 2}, "blocked": 0},
    }
    assert list(_validator().iter_errors(receipt)) == []


def test_rejects_unknown_top_level_key():
    receipt = {
        "agent": "apd-confidentiality",
        "status": "ok",
        "outputs": [],
        "counts": {},
        "summary_prose": "Here is a long narrative the driver should never receive.",
    }
    assert list(_validator().iter_errors(receipt))  # additionalProperties: false


def test_rejects_bad_status():
    receipt = {"agent": "x", "status": "done", "outputs": [], "counts": {}}
    assert list(_validator().iter_errors(receipt))


def test_rejects_prose_value_in_counts_submap():
    receipt = {
        "agent": "apd-confidentiality",
        "status": "ok",
        "outputs": [],
        "counts": {"findings_by_severity": {"high": "see attached analysis for reasoning"}},
    }
    assert list(_validator().iter_errors(receipt))  # values must be non-negative integers


def test_rejects_unknown_key_in_outputs_item():
    receipt = {
        "agent": "apd-confidentiality",
        "status": "ok",
        "outputs": [{"path": "x.findings.yaml", "schema_valid": True, "prose": "narrative"}],
        "counts": {},
    }
    assert list(_validator().iter_errors(receipt))  # outputs items: additionalProperties false
