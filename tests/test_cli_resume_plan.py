"""Tests for the read-only ``resume-plan`` command (R1).

``resume-plan <run-dir> --json`` reports which agent steps of a run are already
complete, so the runner can skip them on resume. A step is complete only when
every file of one of its output sets is present AND valid; a half-written lens
(valid findings, truncated capabilities) must re-run.
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

import yaml
from apd_gauntlet import __version__
from apd_gauntlet.cli import main
from apd_gauntlet.resume_plan import RESUMABLE_STEPS
from apd_gauntlet.validate import run_schema_pass, schema_errors_for_file
from click.testing import CliRunner
from jsonschema import Draft202012Validator

FIX = Path(__file__).resolve().parent / "fixtures"


def _run(tmp_path, framework_version="1.7.1", *, clean=False) -> Path:
    run = tmp_path / "run"
    if clean:
        shutil.copytree(FIX / "runs" / "clean-run", run)
    else:
        run.mkdir()
    (run / ".apd-run.yaml").write_text(yaml.safe_dump(
        {"run_id": "run", "domains": ["pbm"], "framework_version": framework_version}))
    return run


def _plan(run):
    r = CliRunner().invoke(main, ["resume-plan", str(run), "--json"])
    assert r.exit_code == 0, r.output
    return json.loads(r.stdout)


def _step(plan, label):
    return next(s for s in plan["steps"] if s["label"] == label)


def test_fresh_run_lists_every_step_incomplete(tmp_path):
    plan = _plan(_run(tmp_path))
    assert plan["engine_version"] == __version__
    assert [s["label"] for s in plan["steps"]] == [s.label for s in RESUMABLE_STEPS]
    assert not any(s["complete"] for s in plan["steps"])
    assert _step(plan, "intake")["reason"] == "missing 00-context/context-brief.md"


def test_output_matches_receipt_schema(tmp_path):
    schema = json.loads((FIX.parent.parent / "schemas/agent-receipt.schema.json").read_text())
    Draft202012Validator(schema["properties"]["resume_plan"]).validate(
        _plan(_run(tmp_path, clean=True)))


def test_finished_lens_is_complete(tmp_path):
    assert _step(_plan(_run(tmp_path, clean=True)), "confidentiality") == {
        "label": "confidentiality", "complete": True, "reason": "outputs present and valid"}


def test_truncated_sibling_is_not_complete(tmp_path):  # Review Focus 2
    run = _run(tmp_path, clean=True)
    (run / "10-trustworthiness/confidentiality.capabilities.yaml").write_text(
        'capability:\n  - title: "unterminated\n')
    s = _step(_plan(run), "confidentiality")
    assert not s["complete"]
    assert s["reason"].startswith(
        "unparseable 10-trustworthiness/confidentiality.capabilities.yaml")


def test_missing_sibling_is_not_complete(tmp_path):  # Review Focus 2
    run = _run(tmp_path, clean=True)
    (run / "10-trustworthiness/confidentiality.capabilities.yaml").unlink()
    assert _step(_plan(run), "confidentiality")["reason"] == (
        "missing 10-trustworthiness/confidentiality.capabilities.yaml")


def test_schema_invalid_output_is_not_complete(tmp_path):
    run = _run(tmp_path, clean=True)
    (run / "10-trustworthiness/confidentiality.findings.yaml").write_text(
        "finding:\n  - agent: confidentiality\n")
    assert _step(_plan(run), "confidentiality")["reason"].startswith(
        "schema-invalid 10-trustworthiness/confidentiality.findings.yaml")


def test_empty_markdown_is_not_complete(tmp_path):
    run = _run(tmp_path, clean=True)
    shutil.copy(FIX / "valid/asset-inventory-valid.yaml", run / "00-context/asset-inventory.yaml")
    assert _step(_plan(run), "intake")["complete"] is True
    (run / "00-context/context-brief.md").write_text("")
    assert _step(_plan(run), "intake")["reason"] == "empty 00-context/context-brief.md"


def test_code_recon_skip_note_counts_as_complete(tmp_path):
    run = _run(tmp_path)
    (run / "00-context").mkdir()
    (run / "00-context/code-recon-skipped.md").write_text(
        "CBM not reachable; recon cannot complete\n")
    assert _step(_plan(run), "code-recon")["complete"] is True


def _snapshot(run):
    return {p: (p.stat().st_mtime_ns, p.read_bytes()) for p in run.rglob("*") if p.is_file()}


def test_writes_nothing(tmp_path):
    run = _run(tmp_path, clean=True)
    before = _snapshot(run)
    _plan(run)
    assert _snapshot(run) == before


def test_refuses_run_from_another_major(tmp_path):  # Review Focus 1
    r = CliRunner().invoke(main, ["resume-plan", str(_run(tmp_path, "2.0.0")), "--json"])
    assert r.exit_code == 3 and r.stdout == ""
    assert "2.0.0" in r.stderr and __version__ in r.stderr and "apd-gauntlet 2.x engine" in r.stderr


def _config_run(tmp_path, **config) -> Path:
    run = tmp_path / "run"
    run.mkdir()
    (run / ".apd-run.yaml").write_text(yaml.safe_dump(
        {"run_id": "run", "domains": ["pbm"], **config}))
    return run


def test_other_major_with_a_key_this_schema_lacks_exits_3(tmp_path):  # Review Focus 1
    run = _config_run(tmp_path, framework_version="2.0.0", key_added_in_2x={"x": 1})
    before = _snapshot(run)
    r = CliRunner().invoke(main, ["resume-plan", str(run), "--json"])
    assert r.exit_code == 3 and r.stdout == ""
    assert "2.0.0" in r.stderr and "apd-gauntlet 2.x engine" in r.stderr
    assert _snapshot(run) == before


def test_same_major_with_a_key_this_schema_lacks_exits_2(tmp_path):
    run = _config_run(tmp_path, framework_version="1.7.1", key_added_in_2x={"x": 1})
    r = CliRunner().invoke(main, ["resume-plan", str(run), "--json"])
    assert r.exit_code == 2 and r.stdout == ""
    assert "key_added_in_2x" in r.stderr


def test_accepts_older_run_on_same_major(tmp_path):
    assert _plan(_run(tmp_path, "1.6.0"))["engine_version"] == __version__


def test_missing_run_config_exits_2(tmp_path):
    r = CliRunner().invoke(main, ["resume-plan", str(tmp_path), "--json"])
    assert r.exit_code == 2 and "No .apd-run.yaml" in r.stderr


def test_unparseable_run_config_exits_2(tmp_path):
    (tmp_path / ".apd-run.yaml").write_text('run_id: "unterminated\n')
    r = CliRunner().invoke(main, ["resume-plan", str(tmp_path), "--json"])
    assert r.exit_code == 2 and r.stdout == ""
    assert ".apd-run.yaml" in r.stderr


def test_schema_invalid_run_config_exits_2(tmp_path):  # F-7
    (tmp_path / ".apd-run.yaml").write_text(
        yaml.safe_dump({"run_id": "run", "domains": [], "framework_version": "one.seven"}))
    r = CliRunner().invoke(main, ["resume-plan", str(tmp_path), "--json"])
    assert r.exit_code == 2 and r.stdout == ""
    assert ".apd-run.yaml" in r.stderr


def test_text_mode_lists_labels(tmp_path):
    r = CliRunner().invoke(main, ["resume-plan", str(_run(tmp_path))])
    assert r.exit_code == 0 and "intake" in r.stdout and "domain-auditor" in r.stdout


def test_text_mode_prints_engine_then_one_line_per_step(tmp_path):
    r = CliRunner().invoke(main, ["resume-plan", str(_run(tmp_path, clean=True))])
    lines = r.stdout.splitlines()
    assert lines[0] == f"engine {__version__}"
    assert len(lines) == 1 + len(RESUMABLE_STEPS)
    assert "complete  confidentiality  outputs present and valid" in lines
    assert "pending  integrity  missing 10-trustworthiness/integrity.findings.yaml" in lines


def test_json_is_one_line_on_stdout(tmp_path):
    r = CliRunner().invoke(main, ["resume-plan", str(_run(tmp_path)), "--json"])
    assert r.exit_code == 0 and len(r.stdout.splitlines()) == 1


def test_context_brief_without_frontmatter_is_not_complete(tmp_path):
    run = _run(tmp_path, clean=True)
    shutil.copy(FIX / "valid/asset-inventory-valid.yaml", run / "00-context/asset-inventory.yaml")
    (run / "00-context/context-brief.md").write_text("# a brief with no frontmatter\n")
    assert _step(_plan(run), "intake")["reason"] == "no frontmatter in 00-context/context-brief.md"


def test_code_recon_full_output_set_counts_as_complete(tmp_path):
    run = _run(tmp_path)
    (run / "00-context").mkdir()
    shutil.copy(FIX / "valid/code-evidence-index.yaml", run / "00-context/code-evidence-index.yaml")
    shutil.copy(FIX / "valid/c4-recon.yaml", run / "00-context/c4-recon.yaml")
    (run / "00-context/code-architecture-brief.md").write_text("# architecture\n")
    assert _step(_plan(run), "code-recon")["complete"] is True


def test_code_recon_reports_first_alternative_when_neither_is_complete(tmp_path):
    run = _run(tmp_path)
    (run / "00-context").mkdir()
    shutil.copy(FIX / "invalid/code-evidence-index-malformed.yaml",
                run / "00-context/code-evidence-index.yaml")
    s = _step(_plan(run), "code-recon")
    assert not s["complete"]
    assert s["reason"].startswith("schema-invalid 00-context/code-evidence-index.yaml")


def test_non_utf8_output_is_not_complete(tmp_path):
    run = _run(tmp_path, clean=True)
    caps = "10-trustworthiness/confidentiality.capabilities.yaml"
    (run / caps).write_bytes(b"capability:\n  - title: \xff\xfe\n")
    s = _step(_plan(run), "confidentiality")
    assert not s["complete"]
    assert s["reason"].startswith(f"unreadable {caps}")


# --- validate.schema_errors_for_file: the shared file -> schema lookup (F-14) -------------


def test_schema_errors_for_file_agrees_with_run_schema_pass(tmp_path):
    """The per-file verdict must equal what ``validate`` concludes for the same file."""
    run = _run(tmp_path, clean=True)
    (run / "00-context").mkdir(exist_ok=True)
    shutil.copy(FIX / "invalid/code-evidence-index-malformed.yaml",
                run / "00-context/code-evidence-index.yaml")
    shutil.copy(FIX / "invalid/c4-recon-malformed.yaml", run / "00-context/c4-recon.yaml")
    shutil.copy(FIX / "valid/asset-inventory-valid.yaml", run / "00-context/asset-inventory.yaml")
    (run / "40-synthesis/cluster-decisions.yaml").write_text("not_a_valid: document\n")
    (run / "40-synthesis/metrics.yaml").write_text("{}\n")
    (run / "20-scalability/resilient.findings.yaml").write_text(
        "finding:\n  - agent: resilient\n")
    flagged = {v.file.relative_to(run).as_posix() for v in run_schema_pass(run).errors}
    probes = [
        "00-context/code-evidence-index.yaml", "00-context/c4-recon.yaml",
        "00-context/asset-inventory.yaml", "40-synthesis/cluster-decisions.yaml",
        "40-synthesis/metrics.yaml", "20-scalability/resilient.findings.yaml",
        "10-trustworthiness/confidentiality.findings.yaml",
        "10-trustworthiness/confidentiality.capabilities.yaml",
    ]
    for rel in probes:
        assert bool(schema_errors_for_file(run, rel)) == (rel in flagged), rel
    assert flagged, "the probe set must include files validate rejects"


def test_schema_errors_for_file_is_empty_when_no_schema_applies(tmp_path):
    run = _run(tmp_path, clean=True)
    (run / "40-synthesis/not-a-known-rollup.yaml").write_text("anything: [goes\n")
    assert schema_errors_for_file(run, "40-synthesis/not-a-known-rollup.yaml") == []
    assert schema_errors_for_file(run, "00-context/context-brief.md") == []


def test_schema_errors_for_file_reports_yaml_parse_errors(tmp_path):
    run = _run(tmp_path, clean=True)
    findings = "10-trustworthiness/confidentiality.findings.yaml"
    (run / findings).write_text('finding:\n  - title: "unterminated\n')
    errors = schema_errors_for_file(run, findings)
    assert errors and errors[0].startswith("YAML parse error")


def test_schema_errors_for_file_flags_a_non_mapping_record_file(tmp_path):
    run = _run(tmp_path, clean=True)
    findings = "10-trustworthiness/confidentiality.findings.yaml"
    (run / findings).write_text("fin\n")
    assert schema_errors_for_file(run, findings)
