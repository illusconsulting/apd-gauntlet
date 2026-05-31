"""--errors-only: suppress warnings + the scan/clean summary line; print only ERROR lines."""
from __future__ import annotations

import pathlib
import shutil

from apd_gauntlet.cli import main
from click.testing import CliRunner

FIXTURES = pathlib.Path(__file__).parent / "fixtures" / "runs"


def _copy_clean_run(tmp_path):
    dst = tmp_path / "run"
    shutil.copytree(FIXTURES / "clean-run", dst)
    return dst


def test_errors_only_clean_run_is_silent(tmp_path):
    dst = _copy_clean_run(tmp_path)
    runner = CliRunner()
    result = runner.invoke(main, ["validate", str(dst), "--errors-only"])
    assert result.exit_code == 0
    # No "Files scanned" summary, no "Clean." line — completely quiet on success.
    assert result.output.strip() == ""


def test_errors_only_prints_errors_but_not_summary(tmp_path):
    dst = _copy_clean_run(tmp_path)
    # Inject a schema error: blank out a required field on a finding.
    f = dst / "10-trustworthiness" / "confidentiality.findings.yaml"
    text = f.read_text()
    text = text.replace("severity:", "not_severity:", 1)
    f.write_text(text)
    runner = CliRunner()
    result = runner.invoke(main, ["validate", str(dst), "--errors-only"])
    assert result.exit_code == 1
    assert "ERROR" in result.output
    assert "Files scanned" not in result.output
    assert "WARNING" not in result.output
