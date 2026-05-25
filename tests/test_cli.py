"""Smoke tests for the apd-gauntlet CLI entry point."""
from __future__ import annotations

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
    assert "1.0.0" in result.output
