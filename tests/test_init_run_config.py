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


def test_run_config_schema_accepts_mas_taxonomies(tmp_path):
    """run-config taxonomy enum must accept masvs + maswe so a MAS run validates."""
    inputs = tmp_path / "in"
    inputs.mkdir()
    (inputs / "tech_plan.md").write_text("# Plan\n")

    run_dir = scaffold_run(
        "run-mas", inputs, ["pbm"], tmp_path / "runs",
        taxonomies=["masvs", "maswe"],
    )

    cfg = yaml.safe_load((run_dir / ".apd-run.yaml").read_text())
    assert cfg["taxonomies"] == ["masvs", "maswe"]
    errors = list(Draft202012Validator(RUN_CONFIG_SCHEMA).iter_errors(cfg))
    assert errors == [], [e.message for e in errors]


def test_domain_schema_accepts_taxonomies_field(tmp_path):
    """domain.schema.json must allow an optional top-level taxonomies array with the
    masvs/maswe enum values (additionalProperties is false, so it needs an explicit
    property)."""
    schema = json.loads((REPO / "schemas" / "domain.schema.json").read_text())
    meta = {
        "name": "x",
        "display_name": "X Domain",
        "version": "1.0.0",
        "framework_compat": ">=1.0.0,<2.0.0",
        "description": "A domain pack used only for this schema test, padded.",
        "includes": ["severity-rubric.md"],
        "regulatory_anchors": [],
        "taxonomies": ["masvs", "maswe"],
    }
    errors = list(Draft202012Validator(schema).iter_errors(meta))
    assert errors == [], [e.message for e in errors]


def test_mobile_pack_declares_mas_taxonomies():
    """The mobile pack must declare taxonomies: [masvs, maswe] so selecting it
    auto-seeds the run taxonomies; the file must still schema-validate."""
    import json
    schema = json.loads((REPO / "schemas" / "domain.schema.json").read_text())
    meta = yaml.safe_load(
        (REPO / "domains" / "mobile-applications" / "domain.yaml").read_text()
    )
    assert meta.get("taxonomies") == ["masvs", "maswe"]
    errors = list(Draft202012Validator(schema).iter_errors(meta))
    assert errors == [], [e.message for e in errors]


def test_scaffold_mobile_auto_seeds_mas_taxonomies(tmp_path):
    """Scaffolding with domain=mobile-applications and NO --taxonomies must still
    write taxonomies including masvs + maswe (auto-seeded from the pack)."""
    inputs = tmp_path / "in"
    inputs.mkdir()
    (inputs / "tech_plan.md").write_text("# Plan\n")

    run_dir = scaffold_run("run-mob", inputs, ["mobile-applications"], tmp_path / "runs")

    cfg = yaml.safe_load((run_dir / ".apd-run.yaml").read_text())
    assert "masvs" in cfg["taxonomies"]
    assert "maswe" in cfg["taxonomies"]
    errors = list(Draft202012Validator(RUN_CONFIG_SCHEMA).iter_errors(cfg))
    assert errors == [], [e.message for e in errors]


def test_scaffold_non_mobile_pack_seeds_no_taxonomies(tmp_path):
    """A pack without a taxonomies field (pbm) must not gain a taxonomies list."""
    inputs = tmp_path / "in"
    inputs.mkdir()
    (inputs / "tech_plan.md").write_text("# Plan\n")

    run_dir = scaffold_run("run-pbm", inputs, ["pbm"], tmp_path / "runs")

    cfg = yaml.safe_load((run_dir / ".apd-run.yaml").read_text())
    assert "taxonomies" not in cfg


def test_scaffold_operator_taxonomies_merge_with_pack(tmp_path):
    """Operator --taxonomies still merge with the pack-auto-seeded set, deduped,
    operator entries first, then any pack entry not already present."""
    inputs = tmp_path / "in"
    inputs.mkdir()
    (inputs / "tech_plan.md").write_text("# Plan\n")

    run_dir = scaffold_run(
        "run-merge", inputs, ["mobile-applications"], tmp_path / "runs",
        taxonomies=["cwe", "masvs"],
    )

    cfg = yaml.safe_load((run_dir / ".apd-run.yaml").read_text())
    tax = cfg["taxonomies"]
    assert tax[:2] == ["cwe", "masvs"]      # operator order preserved, masvs not duplicated
    assert "maswe" in tax                    # pack entry merged in
    assert tax.count("masvs") == 1           # dedupe held
    errors = list(Draft202012Validator(RUN_CONFIG_SCHEMA).iter_errors(cfg))
    assert errors == [], [e.message for e in errors]
