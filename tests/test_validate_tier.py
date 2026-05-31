"""--tier: validate only one subdir; skip the cross-file pass; tolerate later tiers absent."""
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


def test_tier_scopes_to_subdir(tmp_path):
    dst = _copy_clean_run(tmp_path)

    # Unconditionally inject a schema-broken findings file into a tier that is
    # NOT being validated. If --tier scoping works, this file must be invisible
    # to the validator; if scoping regressed to whole-run scanning, this fails.
    out_of_scope_dir = dst / "20-scalability"
    out_of_scope_dir.mkdir(exist_ok=True)
    broken = out_of_scope_dir / "injected.findings.yaml"
    broken.write_text(
        "finding:\n  - id: FAKE-001\n    not_severity: critical\n",
        encoding="utf-8",
    )

    runner = CliRunner()
    result = runner.invoke(
        main, ["validate", str(dst), "--tier", "10-trustworthiness", "--errors-only"]
    )
    assert result.exit_code == 0, result.output
    assert result.output.strip() == ""


def test_tier_catches_error_in_scoped_dir(tmp_path):
    dst = _copy_clean_run(tmp_path)
    f1 = dst / "10-trustworthiness" / "confidentiality.findings.yaml"
    f1.write_text(f1.read_text().replace("severity:", "not_severity:", 1))
    runner = CliRunner()
    result = runner.invoke(main, ["validate", str(dst), "--tier", "10-trustworthiness"])
    assert result.exit_code == 1
    assert "ERROR" in result.output


def test_tier_missing_subdir_errors_cleanly(tmp_path):
    dst = _copy_clean_run(tmp_path)
    runner = CliRunner()
    result = runner.invoke(main, ["validate", str(dst), "--tier", "99-nope"])
    assert result.exit_code != 0
    assert "99-nope" in result.output
