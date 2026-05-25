"""Tests for the check-ids command."""
from __future__ import annotations
import pathlib
from click.testing import CliRunner
from apd_gauntlet.cli import main


def test_check_ids_on_clean_finding(tmp_path):
    runner = CliRunner()
    # The clean-run fixture's finding has a deterministic id, so this should pass.
    target = pathlib.Path("tests/fixtures/runs/clean-run/10-trustworthiness/confidentiality.findings.yaml")
    result = runner.invoke(main, ["check-ids", str(target)])
    assert result.exit_code == 0, result.output


def test_check_ids_catches_mismatch(tmp_path):
    f = tmp_path / "bad.yaml"
    f.write_text("""\
finding:
  schema_version: 1
  id: conf-deadbeef
  agent: confidentiality
  title: "Some title that does not hash to deadbeef"
  evidence:
    - artifact: tech_plan.md
      locator: "§1"
      excerpt: "stuff"
""")
    runner = CliRunner()
    result = runner.invoke(main, ["check-ids", str(f)])
    assert result.exit_code == 1
    assert "mismatch" in result.output.lower()
