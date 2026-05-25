"""Pass-1 tests: schema validation of records in a run directory."""
from __future__ import annotations
import pathlib
import shutil
from click.testing import CliRunner
from apd_gauntlet.cli import main

FIXTURES = pathlib.Path(__file__).parent / "fixtures" / "runs"


def test_validate_clean_run_returns_zero():
    runner = CliRunner()
    result = runner.invoke(main, ["validate", str(FIXTURES / "clean-run")])
    assert result.exit_code == 0, result.output


def test_validate_run_with_bad_record_returns_one(tmp_path):
    src = FIXTURES / "clean-run"
    dst = tmp_path / "run"
    shutil.copytree(src, dst)
    # Corrupt the finding by deleting required `severity:` line.
    finding_file = dst / "10-trustworthiness" / "confidentiality.findings.yaml"
    text = finding_file.read_text()
    finding_file.write_text(text.replace("  severity: high\n", ""))
    runner = CliRunner()
    result = runner.invoke(main, ["validate", str(dst)])
    assert result.exit_code == 1
    assert "severity" in result.output.lower()
