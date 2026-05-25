"""Tests for the summarize command."""
from __future__ import annotations

import pathlib

from apd_gauntlet.cli import main
from click.testing import CliRunner

FIXTURES = pathlib.Path(__file__).parent / "fixtures" / "runs"


def test_summarize_clean_run(tmp_path):
    runner = CliRunner()
    result = runner.invoke(main, ["summarize", str(FIXTURES / "clean-run")])
    assert result.exit_code == 0
    assert "Findings:" in result.output
    assert "Capabilities:" in result.output


def test_summarize_json(tmp_path):
    runner = CliRunner()
    result = runner.invoke(main, ["summarize", "--json", str(FIXTURES / "clean-run")])
    assert result.exit_code == 0
    import json
    data = json.loads(result.output)
    assert "findings" in data
    assert "capabilities" in data
