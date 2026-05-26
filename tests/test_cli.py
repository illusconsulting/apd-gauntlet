"""Smoke tests for the apd-gauntlet CLI entry point."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import yaml
from apd_gauntlet.cli import main
from click.testing import CliRunner


def test_cli_shows_help():
    runner = CliRunner()
    result = runner.invoke(main, ["--help"])
    assert result.exit_code == 0
    assert "apd-gauntlet" in result.output.lower()


def test_cli_version():
    runner = CliRunner()
    result = runner.invoke(main, ["--version"])
    assert result.exit_code == 0
    assert "1.3.0" in result.output


def test_cli_refresh_cwe_invokes_refresh():
    runner = CliRunner()
    with patch("apd_gauntlet.cli.refresh_cwe") as mock:
        mock.return_value = Path("/tmp/cwe.json")
        result = runner.invoke(main, ["refresh-cwe"])
        assert result.exit_code == 0
        mock.assert_called_once()


def test_cli_refresh_owasp_invokes_refresh():
    runner = CliRunner()
    with patch("apd_gauntlet.cli.refresh_owasp") as mock:
        mock.return_value = {
            "top10": Path("/tmp/owasp_top10.json"),
            "api_top10": Path("/tmp/owasp_api_top10.json"),
            "llm_top10": Path("/tmp/owasp_llm_top10.json"),
        }
        result = runner.invoke(main, ["refresh-owasp"])
        assert result.exit_code == 0
        mock.assert_called_once()


def test_cli_refresh_d3fend_invokes_refresh():
    runner = CliRunner()
    with patch("apd_gauntlet.cli.refresh_d3fend") as mock:
        mock.return_value = Path("/tmp/d3fend.json")
        result = runner.invoke(main, ["refresh-d3fend"])
        assert result.exit_code == 0
        mock.assert_called_once()


def test_cli_init_run_accepts_taxonomies_flag(tmp_path):
    inputs = tmp_path / "src-inputs"
    inputs.mkdir()
    (inputs / "tech_plan.md").write_text("# stub")
    runner = CliRunner()
    result = runner.invoke(
        main,
        [
            "init-run", "run-tax-001",
            "--inputs", str(inputs),
            "--domain", "pbm",
            "--root", str(tmp_path / "runs"),
            "--taxonomies", "cwe,mitre_attack,d3fend",
        ],
    )
    assert result.exit_code == 0, result.output
    cfg_path = tmp_path / "runs" / "run-tax-001" / ".apd-run.yaml"
    cfg = yaml.safe_load(cfg_path.read_text())
    assert cfg["taxonomies"] == ["cwe", "mitre_attack", "d3fend"]


def test_cli_init_run_accepts_threat_model_and_methodology_hint(tmp_path):
    inputs = tmp_path / "src-inputs"
    inputs.mkdir()
    (inputs / "tech_plan.md").write_text("# stub")
    runner = CliRunner()
    result = runner.invoke(
        main,
        [
            "init-run", "run-tm-001",
            "--inputs", str(inputs),
            "--domain", "pbm",
            "--root", str(tmp_path / "runs"),
            "--threat-model", "threat-model.md",
            "--methodology-hint", "stride",
        ],
    )
    assert result.exit_code == 0, result.output
    cfg_path = tmp_path / "runs" / "run-tm-001" / ".apd-run.yaml"
    cfg = yaml.safe_load(cfg_path.read_text())
    assert cfg["threat_model"] == "threat-model.md"
    assert cfg["methodology_hint"] == "stride"


def test_cli_init_run_methodology_hint_validated_against_known_set(tmp_path):
    inputs = tmp_path / "src-inputs"
    inputs.mkdir()
    (inputs / "tech_plan.md").write_text("# stub")
    runner = CliRunner()
    result = runner.invoke(
        main,
        [
            "init-run", "run-tm-002",
            "--inputs", str(inputs),
            "--domain", "pbm",
            "--root", str(tmp_path / "runs"),
            "--methodology-hint", "invalid_hint",
        ],
    )
    assert result.exit_code != 0
    assert "invalid_hint" in result.output or "Invalid value" in result.output


# ---------------------------------------------------------------------------
# parse-threat-model subcommand tests (Task B-17)
# ---------------------------------------------------------------------------


def test_cli_parse_threat_model_stdout(tmp_path):
    runner = CliRunner()
    result = runner.invoke(main, [
        "parse-threat-model",
        "tests/fixtures/threat_models/sample-stride-table.md",
    ])
    assert result.exit_code == 0, result.output
    data = yaml.safe_load(result.output)
    assert data["methodology"] == "stride"
    assert data["entries"]


def test_cli_parse_threat_model_output_file(tmp_path):
    runner = CliRunner()
    output = tmp_path / "normalized.yaml"
    result = runner.invoke(main, [
        "parse-threat-model",
        "tests/fixtures/threat_models/sample-stride-table.md",
        "--output", str(output),
    ])
    assert result.exit_code == 0, result.output
    assert output.exists()
    data = yaml.safe_load(output.read_text())
    assert data["methodology"] == "stride"


def test_cli_parse_threat_model_validates_output_against_schema(tmp_path):
    """Default --validate=on; happy-path fixtures must validate cleanly."""
    runner = CliRunner()
    result = runner.invoke(main, [
        "parse-threat-model",
        "tests/fixtures/threat_models/sample-microsoft.tm7",
        "--output", str(tmp_path / "out.yaml"),
    ])
    assert result.exit_code == 0, result.output
    assert "ERROR" not in result.output


def test_cli_parse_threat_model_methodology_hint_override():
    runner = CliRunner()
    result = runner.invoke(main, [
        "parse-threat-model",
        "tests/fixtures/threat_models/sample-stride-table.md",
        "--methodology-hint", "linddun",
    ])
    assert result.exit_code == 0, result.output
    data = yaml.safe_load(result.output)
    assert data["methodology"] == "linddun"


def test_cli_parse_threat_model_rejects_unknown_hint():
    runner = CliRunner()
    result = runner.invoke(main, [
        "parse-threat-model",
        "tests/fixtures/threat_models/sample-stride-table.md",
        "--methodology-hint", "made_up",
    ])
    assert result.exit_code != 0
    assert "unknown methodology hint" in result.output


def test_cli_parse_threat_model_reports_invalid_json_path(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text("{ not valid json")
    runner = CliRunner()
    result = runner.invoke(main, ["parse-threat-model", str(bad)])
    assert result.exit_code != 0
    assert "invalid JSON" in result.output
