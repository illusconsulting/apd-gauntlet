"""The ``usage`` command: OTLP/JSON telemetry into ``<run>/.apd-state/usage.yaml``."""
from __future__ import annotations

import json
import pathlib
import sys

import pytest
import yaml
from apd_gauntlet.cli import main
from apd_gauntlet.measure.runs import load_run
from click.testing import CliRunner

FIXTURES = pathlib.Path(__file__).resolve().parent / "fixtures"
OTEL = FIXTURES / "otel/claude-code-logs.otlp.jsonl"


def test_usage_writes_state_file(make_run):
    run = make_run("r")
    r = CliRunner().invoke(main, ["usage", str(run), "--otel", str(OTEL)])
    assert r.exit_code == 0
    assert yaml.safe_load((run / ".apd-state/usage.yaml").read_text())["totals"]["requests"] == 5


def test_console_export_refused(make_run):
    r = CliRunner().invoke(
        main, ["usage", str(make_run("r")), "--otel", str(FIXTURES / "otel/console-export.txt")]
    )
    assert r.exit_code == 2 and "OTLP/JSON" in r.output


def test_no_events_exits_1(make_run, tmp_path):
    empty = tmp_path / "e.jsonl"
    empty.write_text('{"resourceLogs": []}\n')
    run = make_run("r")
    assert CliRunner().invoke(main, ["usage", str(run), "--otel", str(empty)]).exit_code == 1
    assert not (run / ".apd-state/usage.yaml").exists()


# --- beyond the plan's tests -------------------------------------------------------------


def _usage(run):
    return yaml.safe_load((run / ".apd-state/usage.yaml").read_text(encoding="utf-8"))


def test_usage_file_keys_and_combined_cost_without_decisions(make_run):
    run = make_run("r")
    assert CliRunner().invoke(main, ["usage", str(run), "--otel", str(OTEL)]).exit_code == 0
    doc = _usage(run)
    assert list(doc) == [
        "schema_version", "generated_by", "source", "filter", "totals", "by_agent", "by_phase",
        "decision_models", "cost_usd_all", "warnings",
    ]
    assert doc["decision_models"] == {
        "totals": {"calls": 0, "input_tokens": 0, "cost_usd": 0.0},
        "by_task": {},
        "by_cost_basis": {},
    }
    assert doc["cost_usd_all"] == doc["totals"]["cost_usd"] == 0.763


def test_decision_model_spend_is_added(make_run):
    run = make_run("r")
    folder = run / "40-synthesis/decisions"
    folder.mkdir(parents=True)
    (folder / "finding-qa.all.yaml").write_text(
        "task: finding-qa\nusage: {calls: 3, input_tokens: 4210, cost_usd: 0.00101, "
        "cost_basis: estimated}\n",
        encoding="utf-8",
    )
    assert CliRunner().invoke(main, ["usage", str(run), "--otel", str(OTEL)]).exit_code == 0
    doc = _usage(run)
    assert doc["decision_models"]["totals"] == {"calls": 3, "input_tokens": 4210,
                                                "cost_usd": 0.00101}
    assert doc["decision_models"]["by_task"] == {
        "finding-qa": {"calls": 3, "input_tokens": 4210, "cost_usd": 0.00101}
    }
    assert doc["cost_usd_all"] == 0.76401
    snapshot = load_run(run)
    assert snapshot.usage_totals is not None
    assert snapshot.usage_totals["cost_usd"] == 0.763
    assert snapshot.usage_totals["cost_usd_all"] == 0.76401


def test_json_output_is_the_written_file(make_run):
    run = make_run("r")
    r = CliRunner().invoke(main, ["usage", str(run), "--otel", str(OTEL), "--json"])
    assert r.exit_code == 0
    assert json.loads(r.stdout) == _usage(run)


def test_text_output_and_warnings_on_stderr(make_run):
    run = make_run("r")
    r = CliRunner().invoke(main, ["usage", str(run), "--otel", str(OTEL)])
    assert r.exit_code == 0
    assert str(run / ".apd-state/usage.yaml") in r.stdout
    assert "5 api_request events" in r.stdout and "0.763" in r.stdout
    assert "tier-1" in r.stdout and "OTEL_LOG_TOOL_DETAILS" not in r.stdout
    assert "warning: agent names redacted on 1 requests" in r.stderr
    assert "warning: multiple workflow runs in this file (wf_1, wf_2)" in r.stderr


def test_workflow_run_option_filters(make_run):
    run = make_run("r")
    r = CliRunner().invoke(main, ["usage", str(run), "--otel", str(OTEL), "--workflow-run", "wf_1"])
    assert r.exit_code == 0
    doc = _usage(run)
    assert doc["totals"]["requests"] == 3 and doc["totals"]["cost_usd"] == 0.76
    assert doc["filter"] == {"workflow_run": "wf_1"} and doc["warnings"] == []
    assert r.stderr == ""


def test_unknown_workflow_run_exits_1_and_names_it(make_run):
    run = make_run("r")
    r = CliRunner().invoke(main, ["usage", str(run), "--otel", str(OTEL), "--workflow-run", "wf_9"])
    assert r.exit_code == 1
    assert "workflow run wf_9" in r.stderr and "wf_1, wf_2" in r.stderr
    assert not (run / ".apd-state").exists()


def test_no_events_message_names_the_file(make_run, tmp_path):
    empty = tmp_path / "e.jsonl"
    empty.write_text('{"resourceLogs": []}\n')
    r = CliRunner().invoke(main, ["usage", str(make_run("r")), "--otel", str(empty)])
    assert r.exit_code == 1 and f"no api_request events in {empty}" in r.stderr


def test_console_export_writes_nothing(make_run):
    run = make_run("r")
    r = CliRunner().invoke(
        main, ["usage", str(run), "--otel", str(FIXTURES / "otel/console-export.txt")]
    )
    assert r.exit_code == 2 and "docs/measuring-changes.md" in r.stderr
    assert not (run / ".apd-state").exists()


def test_unusable_decision_record_exits_2(make_run):
    run = make_run("r")
    folder = run / "40-synthesis/decisions"
    folder.mkdir(parents=True)
    (folder / "finding-qa.all.yaml").write_text("task: [unclosed\n", encoding="utf-8")
    r = CliRunner().invoke(main, ["usage", str(run), "--otel", str(OTEL)])
    assert r.exit_code == 2 and "finding-qa.all.yaml" in r.stderr
    assert not (run / ".apd-state/usage.yaml").exists()


def test_not_a_run_directory_exits_2(tmp_path):
    r = CliRunner().invoke(main, ["usage", str(tmp_path), "--otel", str(OTEL)])
    assert r.exit_code == 2 and ".apd-run.yaml" in r.output
    assert not (tmp_path / ".apd-state").exists()


def test_missing_otel_file_exits_2(make_run, tmp_path):
    r = CliRunner().invoke(
        main, ["usage", str(make_run("r")), "--otel", str(tmp_path / "missing.jsonl")]
    )
    assert r.exit_code == 2


def test_unwritable_state_exits_1(make_run):
    run = make_run("r")
    (run / ".apd-state").write_text("not a directory", encoding="utf-8")
    r = CliRunner().invoke(main, ["usage", str(run), "--otel", str(OTEL)])
    assert r.exit_code == 1
    assert f"Error: {run / '.apd-state/usage.yaml'}: cannot write" in r.stderr


def test_integer_too_long_to_convert_exits_2(make_run, tmp_path):
    limit = getattr(sys, "get_int_max_str_digits", lambda: 0)()
    if not limit:
        pytest.skip("this Python has no limit on integer string conversion")
    export = tmp_path / "t.jsonl"
    export.write_text('{"resourceLogs": [], "n": ' + "9" * (limit + 1) + "}\n", encoding="utf-8")
    run = make_run("r")
    r = CliRunner().invoke(main, ["usage", str(run), "--otel", str(export)])
    assert r.exit_code == 2 and "line 1: cannot parse a JSON value" in r.stderr
    assert r.exception is None or isinstance(r.exception, SystemExit)
    assert not (run / ".apd-state").exists()
