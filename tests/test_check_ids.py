"""Tests for the check-ids command."""
from __future__ import annotations

import pathlib

import yaml
from apd_gauntlet.cli import main
from apd_gauntlet.linters import compute_id
from click.testing import CliRunner


def _write(path: pathlib.Path, doc) -> None:
    path.write_text(yaml.safe_dump(doc, sort_keys=False), encoding="utf-8")


def _record_with_wrong_id():
    return {
        "id": "conf-deadbeef",  # does NOT match compute_id -> a real mismatch
        "agent": "confidentiality",
        "title": "PHI in topic",
        "evidence": [{"artifact": "tech_plan.md", "locator": "§4.2", "excerpt": "q"}],
    }


def test_check_ids_on_clean_finding(tmp_path):
    runner = CliRunner()
    # The clean-run fixture's finding has a deterministic id, so this should pass.
    target = pathlib.Path(
        "tests/fixtures/runs/clean-run/10-trustworthiness/confidentiality.findings.yaml"
    )
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


# C2 / F1: check-ids is non-vacuous on plural-root and wrapped files.


def test_check_ids_catches_mismatch_under_plural_root(tmp_path):
    f = tmp_path / "confidentiality.findings.yaml"
    _write(f, {"findings": [_record_with_wrong_id()]})  # plural root
    result = CliRunner().invoke(main, ["check-ids", str(f)])
    assert result.exit_code == 1, result.output
    assert "id mismatch" in result.output


def test_check_ids_catches_mismatch_under_wrapper(tmp_path):
    f = tmp_path / "confidentiality.findings.yaml"
    _write(f, {"finding": [{"finding": _record_with_wrong_id()}]})  # wrapped
    result = CliRunner().invoke(main, ["check-ids", str(f)])
    assert result.exit_code == 1, result.output
    assert "id mismatch" in result.output


def test_check_ids_clean_on_canonical_correct_id(tmp_path):
    rec = _record_with_wrong_id()
    rec["id"] = compute_id("conf", "PHI in topic", "§4.2")
    f = tmp_path / "confidentiality.findings.yaml"
    _write(f, {"finding": [rec]})
    result = CliRunner().invoke(main, ["check-ids", str(f)])
    assert result.exit_code == 0, result.output
    assert "IDs OK" in result.output
