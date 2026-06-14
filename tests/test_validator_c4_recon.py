"""Validator integration tests for 00-context/c4-recon.yaml (Milestone 3)."""
from __future__ import annotations

import pathlib

from apd_gauntlet.validate import run_schema_pass

FIXTURES = pathlib.Path(__file__).resolve().parent / "fixtures"


def _make_run(tmp_path, valid: bool):
    (tmp_path / "00-context").mkdir(parents=True)
    (tmp_path / "00-context" / "context-brief.md").write_text(
        "---\n"
        "framework_version: 1.1.0\n"
        "run_id: t\n"
        "domain_pack: { name: pbm, version: 1.0.0 }\n"
        "artifacts:\n"
        "  - { filename: tech_plan.md, type: tech_plan }\n"
        "---\n"
        "# brief\n"
    )
    src = "valid/c4-recon.yaml" if valid else "invalid/c4-recon-malformed.yaml"
    (tmp_path / "00-context" / "c4-recon.yaml").write_text((FIXTURES / src).read_text())
    return tmp_path


def test_schema_pass_accepts_valid_c4_recon(tmp_path):
    run_dir = _make_run(tmp_path, valid=True)
    report = run_schema_pass(run_dir)
    errors = [v for v in report.errors if "c4-recon" in str(v.file)]
    assert errors == [], [v.message for v in errors]


def test_schema_pass_flags_malformed_c4_recon(tmp_path):
    run_dir = _make_run(tmp_path, valid=False)
    report = run_schema_pass(run_dir)
    assert any("c4-recon" in str(v.file) for v in report.errors), (
        "malformed c4-recon.yaml must be flagged by run_schema_pass"
    )


def test_absent_c4_recon_is_silent(tmp_path):
    """c4-recon.yaml is OPTIONAL: an absent file produces no validation error."""
    (tmp_path / "00-context").mkdir(parents=True)
    (tmp_path / "00-context" / "context-brief.md").write_text(
        "---\nframework_version: 1.1.0\nrun_id: t\n"
        "domain_pack: { name: pbm, version: 1.0.0 }\n"
        "artifacts:\n  - { filename: tech_plan.md, type: tech_plan }\n---\n# brief\n"
    )
    report = run_schema_pass(tmp_path)
    assert not any("c4-recon" in str(v.file) for v in report.errors)
