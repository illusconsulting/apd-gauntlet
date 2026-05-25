"""Tests for the init-run command."""
from __future__ import annotations
import pathlib
from click.testing import CliRunner
from apd_gauntlet.cli import main


def test_init_run_creates_expected_directories(tmp_path):
    inputs = tmp_path / "src-inputs"
    inputs.mkdir()
    (inputs / "tech_plan.md").write_text("# stub")
    runner = CliRunner()
    result = runner.invoke(
        main,
        ["init-run", "test-001", "--inputs", str(inputs), "--domain", "pbm",
         "--root", str(tmp_path / "runs")],
    )
    assert result.exit_code == 0, result.output
    run_dir = tmp_path / "runs" / "test-001"
    for sub in ("inputs", "00-context", "10-trustworthiness", "20-scalability", "30-auditability", "40-synthesis"):
        assert (run_dir / sub).is_dir()
    assert (run_dir / "inputs" / "tech_plan.md").exists()
    assert (run_dir / ".apd-run.yaml").exists()
