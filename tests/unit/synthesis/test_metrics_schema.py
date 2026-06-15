# tests/unit/synthesis/test_metrics_schema.py
"""metrics.yaml validates against metrics.schema.json; compute_metrics output is valid."""
from __future__ import annotations

import jsonschema
import pytest
from apd_gauntlet.synthesis.metrics import compute_metrics
from apd_gauntlet.validate import build_registry


def _validator():
    reg = build_registry()
    schema = reg.contents(
        "https://github.com/illusconsulting/apd-gauntlet/schemas/metrics.schema.json"
    )
    return jsonschema.Draft202012Validator(schema, registry=reg)


def test_compute_metrics_output_validates():
    doc = compute_metrics([{"id": "a", "severity": "high"}], [], [], [])
    _validator().validate(doc)  # raises on failure


def test_missing_required_key_fails():
    doc = compute_metrics([], [], [], [])
    del doc["bySeverity"]
    with pytest.raises(jsonschema.ValidationError):
        _validator().validate(doc)


def test_negative_count_fails():
    doc = compute_metrics([], [], [], [])
    doc["findings_total"] = -1
    with pytest.raises(jsonschema.ValidationError):
        _validator().validate(doc)
