"""Tests for scaffold_run's emission of .apd-run.yaml."""
from __future__ import annotations

import json
import pathlib

import pytest
import yaml
from apd_gauntlet.init_run import scaffold_run
from jsonschema import Draft202012Validator

REPO = pathlib.Path(__file__).resolve().parent.parent
RUN_CONFIG_SCHEMA = json.loads((REPO / "schemas" / "run-config.schema.json").read_text())


def test_scaffold_run_emits_valid_run_config(tmp_path):
    inputs = tmp_path / "in"
    inputs.mkdir()
    (inputs / "tech_plan.md").write_text("# Plan\n")
    root = tmp_path / "runs"

    run_dir = scaffold_run("run-001", inputs, "pbm", root)

    config_path = run_dir / ".apd-run.yaml"
    assert config_path.exists()
    data = yaml.safe_load(config_path.read_text())
    assert data["run_id"] == "run-001"
    assert data["domain"] == "pbm"
    assert data["framework_version"] == "1.1.0"
    assert data["code_recon"] == "auto"

    # Must also schema-validate.
    errors = list(Draft202012Validator(RUN_CONFIG_SCHEMA).iter_errors(data))
    assert errors == []


def test_scaffold_run_rejects_traversal_run_id(tmp_path):
    inputs = tmp_path / "in"
    inputs.mkdir()
    with pytest.raises(ValueError, match="invalid run_id"):
        scaffold_run("../etc/passwd", inputs, "pbm", tmp_path / "runs")


def test_init_run_writes_taxonomies_to_config(tmp_path):
    inputs = tmp_path / "in"
    inputs.mkdir()
    (inputs / "tech_plan.md").write_text("# Plan\n")
    root = tmp_path / "runs"
    taxonomies = ["cwe", "mitre_attack", "d3fend", "owasp_api_top10"]

    run_dir = scaffold_run("run-002", inputs, "pbm", root, taxonomies=taxonomies)

    cfg = yaml.safe_load((run_dir / ".apd-run.yaml").read_text())
    assert cfg["taxonomies"] == taxonomies

    # Must also schema-validate.
    errors = list(Draft202012Validator(RUN_CONFIG_SCHEMA).iter_errors(cfg))
    assert errors == []


def test_init_run_without_taxonomies_omits_field(tmp_path):
    inputs = tmp_path / "in"
    inputs.mkdir()
    (inputs / "tech_plan.md").write_text("# Plan\n")
    root = tmp_path / "runs"

    run_dir = scaffold_run("run-003", inputs, "pbm", root)

    cfg = yaml.safe_load((run_dir / ".apd-run.yaml").read_text())
    assert "taxonomies" not in cfg


def test_init_run_empty_taxonomies_omits_field(tmp_path):
    inputs = tmp_path / "in"
    inputs.mkdir()
    (inputs / "tech_plan.md").write_text("# Plan\n")
    root = tmp_path / "runs"

    run_dir = scaffold_run("run-004", inputs, "pbm", root, taxonomies=[])

    cfg = yaml.safe_load((run_dir / ".apd-run.yaml").read_text())
    assert "taxonomies" not in cfg
