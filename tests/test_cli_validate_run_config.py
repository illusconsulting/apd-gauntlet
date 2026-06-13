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


def test_validate_run_config_rejects_infra_traversal_glob():
    """A '..'/leading-'/' infra glob exits non-zero with a Schema error line."""
    runner = CliRunner()
    bad = FIXTURES / "invalid/run-config-infra-traversal-glob.yaml"
    result = runner.invoke(main, ["validate-run-config", str(bad)])
    assert result.exit_code != 0
    assert "Schema error:" in result.output


def test_validate_run_config_accepts_static_infrastructure():
    """A well-formed infrastructure.static block validates cleanly."""
    runner = CliRunner()
    good = FIXTURES / "valid/run-config-with-infrastructure.yaml"
    result = runner.invoke(main, ["validate-run-config", str(good)])
    assert result.exit_code == 0
    assert "OK" in result.output
