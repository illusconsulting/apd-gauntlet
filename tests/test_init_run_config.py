"""Tests for scaffold_run's emission of .apd-run.yaml."""
from __future__ import annotations

import json
import pathlib

import pytest
import yaml
from apd_gauntlet import __version__
from apd_gauntlet.init_run import scaffold_run
from jsonschema import Draft202012Validator

REPO = pathlib.Path(__file__).resolve().parent.parent
RUN_CONFIG_SCHEMA = json.loads((REPO / "schemas" / "run-config.schema.json").read_text())


def test_scaffold_run_emits_valid_run_config(tmp_path):
    inputs = tmp_path / "in"
    inputs.mkdir()
    (inputs / "tech_plan.md").write_text("# Plan\n")
    root = tmp_path / "runs"

    run_dir = scaffold_run("run-001", inputs, ["pbm"], root)

    config_path = run_dir / ".apd-run.yaml"
    assert config_path.exists()
    data = yaml.safe_load(config_path.read_text())
    assert data["run_id"] == "run-001"
    assert data["domains"] == ["pbm"]
    assert data["framework_version"] == __version__
    assert data["code_recon"] == "auto"

    # Must also schema-validate.
    errors = list(Draft202012Validator(RUN_CONFIG_SCHEMA).iter_errors(data))
    assert errors == []


def test_scaffold_run_writes_live_framework_version(tmp_path):
    """scaffold_run must stamp the LIVE package __version__ into .apd-run.yaml, not a
    hardcoded literal. A stale literal (a) records the wrong version on every run and
    (b) spuriously fails build_domain_skill's framework_compat gate if any pack floor
    ever rises above it."""
    inputs = tmp_path / "in"
    inputs.mkdir()
    (inputs / "tech_plan.md").write_text("# Plan\n")

    run_dir = scaffold_run("run-fv", inputs, ["pbm"], tmp_path / "runs")

    cfg = yaml.safe_load((run_dir / ".apd-run.yaml").read_text())
    assert cfg["framework_version"] == __version__
    assert cfg["framework_version"] != "1.1.0", (
        "scaffold must not emit the stale hardcoded 1.1.0"
    )


def test_scaffold_run_rejects_traversal_run_id(tmp_path):
    inputs = tmp_path / "in"
    inputs.mkdir()
    with pytest.raises(ValueError, match="invalid run_id"):
        scaffold_run("../etc/passwd", inputs, ["pbm"], tmp_path / "runs")


def test_init_run_writes_taxonomies_to_config(tmp_path):
    inputs = tmp_path / "in"
    inputs.mkdir()
    (inputs / "tech_plan.md").write_text("# Plan\n")
    root = tmp_path / "runs"
    taxonomies = ["cwe", "mitre_attack", "d3fend", "owasp_api_top10"]

    run_dir = scaffold_run("run-002", inputs, ["pbm"], root, taxonomies=taxonomies)

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

    run_dir = scaffold_run("run-003", inputs, ["pbm"], root)

    cfg = yaml.safe_load((run_dir / ".apd-run.yaml").read_text())
    assert "taxonomies" not in cfg


def test_init_run_empty_taxonomies_omits_field(tmp_path):
    inputs = tmp_path / "in"
    inputs.mkdir()
    (inputs / "tech_plan.md").write_text("# Plan\n")
    root = tmp_path / "runs"

    run_dir = scaffold_run("run-004", inputs, ["pbm"], root, taxonomies=[])

    cfg = yaml.safe_load((run_dir / ".apd-run.yaml").read_text())
    assert "taxonomies" not in cfg


def test_scaffold_run_includes_threat_model_when_provided(tmp_path):
    inputs = tmp_path / "in"
    inputs.mkdir()
    (inputs / "tech_plan.md").write_text("# Plan\n")
    root = tmp_path / "runs"

    run_dir = scaffold_run("run-005", inputs, ["pbm"], root, threat_model="threat-model.md")

    cfg = yaml.safe_load((run_dir / ".apd-run.yaml").read_text())
    assert cfg["threat_model"] == "threat-model.md"

    # Must also schema-validate.
    errors = list(Draft202012Validator(RUN_CONFIG_SCHEMA).iter_errors(cfg))
    assert errors == []


def test_scaffold_run_includes_methodology_hint_when_provided(tmp_path):
    inputs = tmp_path / "in"
    inputs.mkdir()
    (inputs / "tech_plan.md").write_text("# Plan\n")
    root = tmp_path / "runs"

    run_dir = scaffold_run("run-006", inputs, ["pbm"], root, methodology_hint="stride")

    cfg = yaml.safe_load((run_dir / ".apd-run.yaml").read_text())
    assert cfg["methodology_hint"] == "stride"

    # Must also schema-validate.
    errors = list(Draft202012Validator(RUN_CONFIG_SCHEMA).iter_errors(cfg))
    assert errors == []


def test_scaffold_run_omits_threat_model_when_absent(tmp_path):
    inputs = tmp_path / "in"
    inputs.mkdir()
    (inputs / "tech_plan.md").write_text("# Plan\n")
    root = tmp_path / "runs"

    run_dir = scaffold_run("run-007", inputs, ["pbm"], root)

    cfg = yaml.safe_load((run_dir / ".apd-run.yaml").read_text())
    assert "threat_model" not in cfg


def test_scaffold_run_omits_methodology_hint_when_only_threat_model_provided(tmp_path):
    inputs = tmp_path / "in"
    inputs.mkdir()
    (inputs / "tech_plan.md").write_text("# Plan\n")
    root = tmp_path / "runs"

    run_dir = scaffold_run("run-008", inputs, ["pbm"], root, threat_model="threat-model.md")

    cfg = yaml.safe_load((run_dir / ".apd-run.yaml").read_text())
    assert "methodology_hint" not in cfg
    assert cfg["threat_model"] == "threat-model.md"
