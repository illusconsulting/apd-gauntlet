"""Composite commands: ``prepare-run``, ``tier-gate``, ``post-tier4`` and ``closeout``.

Each composite runs existing ``apd-gauntlet`` commands in-process, in order, and writes one
status line per constituent to stderr (``<name>: <step> exit=<N>``), then ``<name>: ok`` or
``<name>: failed <steps>``. ``tier-gate`` exits with its ``validate`` code; the others exit
with the first failing constituent's code.
"""
from __future__ import annotations

import json
import pathlib
import shutil
import subprocess
import sys

import pytest
import yaml
from apd_gauntlet import FRAMEWORK_VERSION
from apd_gauntlet.cli import main
from apd_gauntlet.composite import (
    SubStep,
    closeout_steps,
    invoke,
    post_tier4_steps,
    prepare_run_steps,
    run_composite,
    tier_gate_steps,
)
from click.testing import CliRunner
from test_summarize import GOOD as GOOD_ATTEMPTS

REPO = pathlib.Path(__file__).parent.parent
CEB = REPO / "examples/apd-20260601-claim-event-bus/expected"
CLEAN_RUN = REPO / "tests/fixtures/runs/clean-run"
SKILL = ".claude/skills/apd-domain/SKILL.md"
CONF = "10-trustworthiness/confidentiality.findings.yaml"


@pytest.fixture
def ceb(tmp_path):
    """A writable copy of the claim-event-bus example: ``domains: [pbm]``, framework 1.4.0."""
    return shutil.copytree(CEB, tmp_path / "run")


@pytest.fixture
def bare(tmp_path):
    """A writable copy of clean-run: no ``.apd-run.yaml`` and no 40-synthesis deduped files."""
    return shutil.copytree(CLEAN_RUN, tmp_path / "run")


def _status(r, name):
    return [line for line in r.stderr.splitlines() if line.startswith(f"{name}: ")]


def _set_first_finding(path, **fields):
    doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    doc["finding"][0].update(fields)
    path.write_text(yaml.safe_dump(doc, sort_keys=False, allow_unicode=True), encoding="utf-8")


def _raise(exc):
    def raiser(*args, **kwargs):
        raise exc

    return raiser


def _codes(seq):
    """An ``invoke`` stub that returns the next code of ``seq`` on each call."""
    it = iter(seq)
    return lambda argv: next(it)


# --- prepare-run --------------------------------------------------------------


def test_prepare_run_runs_three_steps(ceb, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    r = CliRunner().invoke(main, ["prepare-run", str(ceb)])
    assert r.exit_code == 0, r.output
    assert _status(r, "prepare-run") == [
        "prepare-run: validate exit=0", "prepare-run: build-domain-skill exit=0",
        "prepare-run: validate-domain exit=0", "prepare-run: ok"]
    assert "framework_version: 1.4.0" in (tmp_path / SKILL).read_text()


def test_prepare_run_bad_domain_runs_all_and_keeps_code(ceb, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    r = CliRunner().invoke(main, ["prepare-run", str(ceb), "--domain", "nope"])
    assert r.exit_code == 1
    assert _status(r, "prepare-run")[-1] == "prepare-run: failed build-domain-skill,validate-domain"


def test_prepare_run_without_framework_version_uses_default(bare, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (bare / ".apd-run.yaml").write_text("run_id: run\ndomains: [pbm]\n")
    assert CliRunner().invoke(main, ["prepare-run", str(bare)]).exit_code == 0
    assert f"framework_version: {FRAMEWORK_VERSION}" in (tmp_path / SKILL).read_text()


def test_prepare_run_without_domains_is_usage_error(bare):
    r = CliRunner().invoke(main, ["prepare-run", str(bare)])
    assert r.exit_code == 2 and "--domain" in r.output


def test_prepare_run_unparseable_config_is_usage_error(bare, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (bare / ".apd-run.yaml").write_text("domains: [pbm\n")
    r = CliRunner().invoke(main, ["prepare-run", str(bare), "--domain", "pbm"])
    assert r.exit_code == 2 and ".apd-run.yaml is not valid YAML" in r.output
    assert not (tmp_path / SKILL).exists()


@pytest.mark.parametrize(
    ("config", "flags", "key"),
    [
        ("domains: ['--out=elsewhere']\n", [], "domains"),
        ("domains: pbm\n", [], "domains"),
        ("domains: [pbm]\nframework_version: 1.4\n", [], "framework_version"),
        ("domains: [pbm]\nframework_version: '--full-only'\n", [], "framework_version"),
        ("", ["--domain", "-x"], "--domain"),
    ],
)
def test_prepare_run_refuses_a_value_that_is_not_an_identifier(
    bare, tmp_path, monkeypatch, config, flags, key
):
    # The values become argv of in-process commands: a leading "-" would parse as an option.
    monkeypatch.chdir(tmp_path)
    (bare / ".apd-run.yaml").write_text(config)
    r = CliRunner().invoke(main, ["prepare-run", str(bare), *flags])
    assert r.exit_code == 2 and key in r.output and _status(r, "prepare-run") == []
    assert not (tmp_path / SKILL).exists()


# --- tier-gate -----------------------------------------------------------------


def test_tier_gate_clean_then_schema_error(ceb):
    gate = ["tier-gate", str(ceb), "--tier", "10-trustworthiness"]
    assert CliRunner().invoke(main, gate).exit_code == 0
    _set_first_finding(ceb / CONF, severity="catastrophic")
    r = CliRunner().invoke(main, gate)
    assert r.exit_code == 1 and "ERROR" in r.stdout
    assert "tier-gate: validate exit=1" in _status(r, "tier-gate")


def test_tier_gate_json_stdout_is_validate_json(ceb):
    _set_first_finding(ceb / CONF, severity="catastrophic")
    r = CliRunner().invoke(main, ["tier-gate", str(ceb), "--tier", "10-trustworthiness", "--json"])
    errors = json.loads(r.stdout)["errors"]
    assert r.exit_code == 1 and errors
    assert errors[0]["file"].endswith("confidentiality.findings.yaml")


def test_tier_gate_json_stdout_is_pure_in_a_subprocess(ceb):
    # The runner reads a real process's stdout, where canonicalize's summary line goes too
    # unless the composite redirects it.
    p = subprocess.run(
        [sys.executable, "-m", "apd_gauntlet.cli", "tier-gate", str(ceb),
         "--tier", "10-trustworthiness", "--json"],
        capture_output=True, text=True, timeout=120,
    )
    assert p.returncode == 0, p.stderr
    assert json.loads(p.stdout)["errors"] == []
    assert "canonicalize: 0 records recanonicalized" in p.stderr
    assert p.stderr.splitlines()[-1] == "tier-gate: ok"


def test_tier_gate_exit_is_the_validate_gate(ceb, monkeypatch):
    from apd_gauntlet.canonicalize import CanonicalizeCollision

    monkeypatch.setattr(
        "apd_gauntlet.canonicalize.canonicalize_run", _raise(CanonicalizeCollision("dup"))
    )
    r = CliRunner().invoke(main, ["tier-gate", str(ceb), "--tier", "10-trustworthiness"])
    assert r.exit_code == 0 and "tier-gate: canonicalize exit=1" in _status(r, "tier-gate")
    assert _status(r, "tier-gate")[-1] == "tier-gate: failed canonicalize"


def test_tier_gate_missing_tier_dir(ceb):
    r = CliRunner().invoke(main, ["tier-gate", str(ceb), "--tier", "99-nope"])
    assert r.exit_code == 1 and "--tier subdir not found" in r.output


# --- post-tier4 ----------------------------------------------------------------


def test_post_tier4_order(ceb):
    r = CliRunner().invoke(main, ["post-tier4", str(ceb)])
    assert [line.split()[1] for line in _status(r, "post-tier4")[:3]] == [
        "assemble-c4", "canonicalize", "rollup"]
    assert r.exit_code == 0 and (ceb / "40-synthesis/c4-model.yaml").is_file()
    assert _status(r, "post-tier4")[-1] == "post-tier4: ok"


def test_post_tier4_rollup_failure_is_named(bare):
    r = CliRunner().invoke(main, ["post-tier4", str(bare)])
    assert r.exit_code == 1 and "post-tier4: rollup exit=1" in _status(r, "post-tier4")
    assert "post-tier4: assemble-c4 exit=0" in _status(r, "post-tier4")


def test_post_tier4_assemble_failure_still_runs_rollup(ceb, monkeypatch):
    monkeypatch.setattr("apd_gauntlet.assemble_c4.assemble_c4", _raise(RuntimeError("boom")))
    r = CliRunner().invoke(main, ["post-tier4", str(ceb)])
    assert r.exit_code == 1
    assert {"post-tier4: assemble-c4 exit=1", "post-tier4: rollup exit=0"} <= set(
        _status(r, "post-tier4")
    )
    assert "RuntimeError: boom" in r.stderr
    assert _status(r, "post-tier4")[-1] == "post-tier4: failed assemble-c4"


# --- closeout --------------------------------------------------------------------


def test_closeout_order_and_attempts(ceb):
    attempts = json.dumps(GOOD_ATTEMPTS)
    r = CliRunner().invoke(main, ["closeout", str(ceb), "--record-attempts", attempts])
    assert r.exit_code == 0 and (ceb / ".apd-state/attempts.yaml").is_file()
    assert [line.split()[1] for line in _status(r, "closeout")[:3]] == [
        "canonicalize", "summarize", "validate"]


def test_closeout_bad_attempts_keeps_the_summarize_code(ceb):
    r = CliRunner().invoke(main, ["closeout", str(ceb), "--record-attempts", "{nope"])
    assert r.exit_code == 2 and "closeout: validate exit=0" in _status(r, "closeout")
    assert _status(r, "closeout")[-1] == "closeout: failed summarize"


# --- step builders, run_composite and invoke ------------------------------------------


def test_step_builders_pass_the_run_dir_in_every_argv(tmp_path):
    run = tmp_path / "r"
    assert prepare_run_steps(run, ["pbm", "api-security"], "1.4.0") == [
        SubStep("validate", ("validate", str(run), "--schema-only", "--errors-only")),
        SubStep("build-domain-skill",
                ("build-domain-skill", "pbm", "api-security", "--framework-version", "1.4.0")),
        SubStep("validate-domain", ("validate-domain", "pbm", "api-security")),
    ]
    assert prepare_run_steps(run, ["pbm"], None)[1].argv == ("build-domain-skill", "pbm")
    assert tier_gate_steps(run, "20-scalability", json_output=True) == [
        SubStep("canonicalize", ("canonicalize", str(run)), stdout_to_stderr=True),
        SubStep("validate", ("validate", str(run), "--tier", "20-scalability", "--json")),
    ]
    assert tier_gate_steps(run, "20-scalability")[1].argv[-1] == "--errors-only"
    assert not tier_gate_steps(run, "20-scalability")[0].stdout_to_stderr
    assert [s.argv for s in post_tier4_steps(run)] == [
        ("assemble-c4", str(run)), ("canonicalize", str(run)), ("rollup", str(run))]
    assert [s.argv for s in closeout_steps(run, '{"a": 1}')] == [
        ("canonicalize", str(run)), ("summarize", str(run), "--record-attempts", '{"a": 1}'),
        ("validate", str(run), "--errors-only")]
    assert closeout_steps(run)[1].argv == ("summarize", str(run))


def test_run_composite_exit_rules():
    steps = [SubStep(n, ()) for n in ("a", "b", "c")]
    assert run_composite("x", steps, invoke=_codes([0, 3, 1])) == 3
    assert run_composite("x", steps, gate="c", invoke=_codes([1, 0, 0])) == 0


def test_run_composite_writes_one_status_line_per_step(capsys):
    steps = [SubStep(n, ()) for n in ("a", "b", "c")]
    run_composite("x", steps, invoke=_codes([0, 3, 1]))
    out, err = capsys.readouterr()
    assert out == ""
    assert err.splitlines() == ["x: a exit=0", "x: b exit=3", "x: c exit=1", "x: failed b,c"]
    run_composite("x", steps, invoke=_codes([0, 0, 0]))
    assert capsys.readouterr().err.splitlines()[-1] == "x: ok"


def test_run_composite_redirects_stdout_only_for_the_flagged_step(capsys):
    def speak(argv):
        print(f"said {argv[0]}")
        return 0

    steps = [SubStep("quiet", ("one",), stdout_to_stderr=True), SubStep("loud", ("two",))]
    assert run_composite("x", steps, invoke=speak) == 0
    out, err = capsys.readouterr()
    assert out == "said two\n"
    assert err.splitlines() == ["said one", "x: quiet exit=0", "x: loud exit=0", "x: ok"]


def test_run_composite_refuses_an_unknown_gate():
    with pytest.raises(ValueError, match="nope"):
        run_composite("x", [SubStep("a", ())], gate="nope", invoke=_codes([0]))


def test_invoke_returns_the_standalone_exit_code(capsys):
    assert invoke(["--version"]) == 0
    assert invoke(["no-such-command"]) == 2
    assert "No such command" in capsys.readouterr().err
    assert invoke(["validate", "/no/such/run"]) == 2
