"""Pass-3 tests: cross-file ID and artifact resolution."""
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


def test_unknown_artifact_caught(tmp_path):
    dst = _copy_clean_run(tmp_path)
    f = dst / "10-trustworthiness" / "confidentiality.findings.yaml"
    text = f.read_text()
    # Change artifact reference to one not in the intake brief.
    text = text.replace("artifact: tech_plan.md", "artifact: unknown_file.md")
    f.write_text(text)
    runner = CliRunner()
    result = runner.invoke(main, ["validate", str(dst)])
    assert result.exit_code == 1
    assert "not in intake brief" in result.output.lower()


def test_dangling_cross_reference_caught(tmp_path):
    dst = _copy_clean_run(tmp_path)
    f = dst / "10-trustworthiness" / "confidentiality.findings.yaml"
    text = f.read_text()
    # Append a cross_reference pointing nowhere.
    text = text.replace("evidence:", "cross_references:\n    - conf-deadbeef\n  evidence:")
    f.write_text(text)
    runner = CliRunner()
    result = runner.invoke(main, ["validate", str(dst)])
    assert result.exit_code == 1
    assert "cross_reference" in result.output.lower()
    assert "not found" in result.output.lower()
