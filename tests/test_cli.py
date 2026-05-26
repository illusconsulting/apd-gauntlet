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
    assert "1.3.0.dev0" in result.output


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
