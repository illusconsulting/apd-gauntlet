"""Tests for the validate-run-config CLI subcommand."""
import pathlib

from click.testing import CliRunner

from apd_gauntlet.cli import main

FIXTURES = pathlib.Path(__file__).resolve().parent / "fixtures"


def test_validate_run_config_accepts_valid_file():
    runner = CliRunner()
    result = runner.invoke(main, ["validate-run-config", str(FIXTURES / "valid/run-config.yaml")])
    assert result.exit_code == 0
    assert "OK" in result.output


def test_validate_run_config_rejects_invalid_file():
    runner = CliRunner()
    result = runner.invoke(main, ["validate-run-config", str(FIXTURES / "invalid/run-config-traversal-and-bad-enum.yaml")])
    assert result.exit_code != 0
