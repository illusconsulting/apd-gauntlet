"""Tests for the validate-run-config CLI subcommand."""
import pathlib

from apd_gauntlet.cli import main
from click.testing import CliRunner

FIXTURES = pathlib.Path(__file__).resolve().parent / "fixtures"


def test_validate_run_config_accepts_valid_file():
    runner = CliRunner()
    result = runner.invoke(main, ["validate-run-config", str(FIXTURES / "valid/run-config.yaml")])
    assert result.exit_code == 0
    assert "OK" in result.output


def test_validate_run_config_rejects_invalid_file():
    runner = CliRunner()
    invalid_path = FIXTURES / "invalid/run-config-traversal-and-bad-enum.yaml"
    result = runner.invoke(main, ["validate-run-config", str(invalid_path)])
    assert result.exit_code != 0
