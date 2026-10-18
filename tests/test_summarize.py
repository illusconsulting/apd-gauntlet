"""Tests for the summarize command."""
from __future__ import annotations

import json
import pathlib
import shutil

import yaml
from apd_gauntlet.cli import main
from click.testing import CliRunner

FIXTURES = pathlib.Path(__file__).parent / "fixtures" / "runs"

GOOD = {
    "schema_version": 1,
    "recorded_by": "workflow",
    "lens_retries": {"integrity": 1, "availability": 0},
    "first_pass_invalid": ["integrity"],
    "tier_gate_failures": ["20-scalability"],
    "skipped": [],
    "audit_iterations": 2,
    "tier_repairs": {"20-scalability": 1},
    "lens_reruns": {},
}


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
    data = json.loads(result.output)
    assert "findings" in data
    assert "capabilities" in data


def test_summarize_records_attempts(tmp_path):
    run = shutil.copytree(FIXTURES / "clean-run", tmp_path / "run")
    r = CliRunner().invoke(main, ["summarize", str(run), "--record-attempts", json.dumps(GOOD)])
    assert r.exit_code == 0 and (run / ".apd-state/attempts.yaml").exists()
    assert "Findings:" in r.output


def test_summarize_bad_attempts_json_exits_2(tmp_path):
    run = shutil.copytree(FIXTURES / "clean-run", tmp_path / "run")
    assert (
        CliRunner().invoke(main, ["summarize", str(run), "--record-attempts", "{nope"]).exit_code
        == 2
    )


def test_summarize_invalid_attempts_exits_1(tmp_path):
    run = shutil.copytree(FIXTURES / "clean-run", tmp_path / "run")
    r = CliRunner().invoke(
        main,
        ["summarize", str(run), "--record-attempts", json.dumps({**GOOD, "audit_iterations": 0})],
    )
    assert r.exit_code == 1 and not (run / ".apd-state").exists()


# --- beyond the plan's tests -------------------------------------------------


def test_summarize_reports_the_recorded_path_on_stderr(tmp_path):
    run = shutil.copytree(FIXTURES / "clean-run", tmp_path / "run")
    r = CliRunner().invoke(main, ["summarize", str(run), "--record-attempts", json.dumps(GOOD)])
    assert r.exit_code == 0
    assert r.stderr == f"Recorded attempts -> {run / '.apd-state/attempts.yaml'}\n"
    assert "Recorded attempts" not in r.stdout
    written = yaml.safe_load((run / ".apd-state/attempts.yaml").read_text(encoding="utf-8"))
    assert written == GOOD


def test_summarize_json_stdout_stays_json_when_recording(tmp_path):
    run = shutil.copytree(FIXTURES / "clean-run", tmp_path / "run")
    r = CliRunner().invoke(
        main, ["summarize", str(run), "--json", "--record-attempts", json.dumps(GOOD)]
    )
    assert r.exit_code == 0
    assert "findings" in json.loads(r.stdout)


def test_summarize_bad_attempts_json_names_the_option_and_writes_nothing(tmp_path):
    run = shutil.copytree(FIXTURES / "clean-run", tmp_path / "run")
    r = CliRunner().invoke(main, ["summarize", str(run), "--record-attempts", "{nope"])
    assert r.exit_code == 2 and "--record-attempts" in r.stderr
    assert not (run / ".apd-state").exists()


def test_summarize_invalid_attempts_prints_the_schema_message(tmp_path):
    run = shutil.copytree(FIXTURES / "clean-run", tmp_path / "run")
    r = CliRunner().invoke(
        main,
        ["summarize", str(run), "--record-attempts", json.dumps({**GOOD, "audit_iterations": 0})],
    )
    assert "audit_iterations: 0 is less than the minimum of 1" in r.stderr
    assert "Findings:" not in r.stdout


def test_summarize_non_object_attempts_exits_1(tmp_path):
    run = shutil.copytree(FIXTURES / "clean-run", tmp_path / "run")
    r = CliRunner().invoke(main, ["summarize", str(run), "--record-attempts", "[]"])
    assert r.exit_code == 1 and not (run / ".apd-state").exists()
