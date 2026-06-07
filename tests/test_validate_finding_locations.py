"""G7 — canonical finding/capability file location.

Every ``*.findings.yaml`` / ``*.capabilities.yaml`` must live directly under a
canonical run subdir: one of the three tier dirs (10-trustworthiness,
20-scalability, 30-auditability), or 40-synthesis/, or 40-threat-model/.
A phantom path like ``20-findings/40-threat-model/`` is an ERROR.

Also folds in the G1/G2/G3 regression assertions (confirm-only) that the
existing gates still fire: title>200 (schema), excerpt>25 tokens (linters),
capability maturity>=implemented without non-tech-plan evidence.
"""
from __future__ import annotations

import pathlib
import shutil

from apd_gauntlet import validate as v
from apd_gauntlet.cli import main
from click.testing import CliRunner

FIXTURES = pathlib.Path(__file__).parent / "fixtures" / "runs"


def _copy_clean_run(tmp_path: pathlib.Path) -> pathlib.Path:
    dst = tmp_path / "run"
    shutil.copytree(FIXTURES / "clean-run", dst)
    return dst


# ---------------------------------------------------------------------------
# G7 — canonical location
# ---------------------------------------------------------------------------


def test_canonical_dir_set_is_named_constant() -> None:
    """The allowed dir set is a named constant covering tiers + tier-4 dirs."""
    allowed = v.CANONICAL_RECORD_DIRS
    assert "10-trustworthiness" in allowed
    assert "20-scalability" in allowed
    assert "30-auditability" in allowed
    assert "40-synthesis" in allowed
    assert "40-threat-model" in allowed


def test_phantom_path_errors(tmp_path: pathlib.Path) -> None:
    """A *.findings.yaml under a phantom dir (20-findings/40-threat-model/) errors."""
    dst = _copy_clean_run(tmp_path)
    phantom = dst / "20-findings" / "40-threat-model"
    phantom.mkdir(parents=True)
    src = dst / "10-trustworthiness" / "confidentiality.findings.yaml"
    shutil.copy(src, phantom / "rogue.findings.yaml")
    runner = CliRunner()
    result = runner.invoke(main, ["validate", str(dst)])
    assert result.exit_code == 1
    out = result.output.lower()
    assert "20-findings" in result.output or "canonical" in out


def test_canonical_tier_dir_ok(tmp_path: pathlib.Path) -> None:
    """A *.findings.yaml under 30-auditability/ is in a canonical location."""
    dst = _copy_clean_run(tmp_path)
    runner = CliRunner()
    result = runner.invoke(main, ["validate", str(dst)])
    # Clean run is clean; specifically, no canonical-location error fires.
    assert "canonical" not in result.output.lower()
    assert result.exit_code == 0, result.output


def test_threat_model_dir_ok(tmp_path: pathlib.Path) -> None:
    """A *.findings.yaml under 40-threat-model/ is canonical (no location error)."""
    dst = _copy_clean_run(tmp_path)
    tm = dst / "40-threat-model"
    tm.mkdir(parents=True, exist_ok=True)
    src = dst / "10-trustworthiness" / "confidentiality.findings.yaml"
    shutil.copy(src, tm / "threat-model.findings.yaml")
    rep = v.run_cross_file_pass(dst)
    location_errs = [e for e in rep.errors if "canonical" in e.message.lower()]
    assert location_errs == [], [e.render() for e in location_errs]


def test_check_runs_in_cross_file_pass(tmp_path: pathlib.Path) -> None:
    """G7 is a Pass-3 (cross-file) check, mirroring the task placement."""
    dst = _copy_clean_run(tmp_path)
    phantom = dst / "20-findings"
    phantom.mkdir(parents=True)
    src = dst / "10-trustworthiness" / "confidentiality.findings.yaml"
    shutil.copy(src, phantom / "rogue.findings.yaml")
    rep = v.run_cross_file_pass(dst)
    assert any("canonical" in e.message.lower() for e in rep.errors)


def test_capabilities_file_location_checked(tmp_path: pathlib.Path) -> None:
    """*.capabilities.yaml is subject to the same canonical-location rule."""
    dst = _copy_clean_run(tmp_path)
    phantom = dst / "99-bogus"
    phantom.mkdir(parents=True)
    src = dst / "10-trustworthiness" / "confidentiality.capabilities.yaml"
    shutil.copy(src, phantom / "rogue.capabilities.yaml")
    rep = v.run_cross_file_pass(dst)
    assert any("canonical" in e.message.lower() for e in rep.errors)


# ---------------------------------------------------------------------------
# G1/G2/G3 regression — confirm-only (existing gates still fire)
# ---------------------------------------------------------------------------


def test_g1_title_over_200_caught(tmp_path: pathlib.Path) -> None:
    """G1: a finding title >200 chars is rejected by the schema pass."""
    dst = _copy_clean_run(tmp_path)
    f = dst / "10-trustworthiness" / "confidentiality.findings.yaml"
    text = f.read_text()
    long_title = "A" * 201
    text = text.replace(
        'title: "PHI fields in Kafka claim-events topic lack envelope encryption"',
        f'title: "{long_title}"',
    )
    f.write_text(text)
    runner = CliRunner()
    result = runner.invoke(main, ["validate", str(dst)])
    assert result.exit_code == 1


def test_g2_excerpt_over_25_tokens_caught(tmp_path: pathlib.Path) -> None:
    """G2: an excerpt >25 whitespace tokens is rejected by the linter."""
    dst = _copy_clean_run(tmp_path)
    f = dst / "10-trustworthiness" / "confidentiality.findings.yaml"
    text = f.read_text()
    long_excerpt = " ".join(["word"] * 30)
    text = text.replace(
        'excerpt: "All Kafka topics use AES-256 at-rest encryption via broker-managed keys"',
        f'excerpt: "{long_excerpt}"',
    )
    f.write_text(text)
    runner = CliRunner()
    result = runner.invoke(main, ["validate", str(dst)])
    assert result.exit_code == 1
    assert "excerpt" in result.output.lower()
    assert "25" in result.output


def test_g3_capability_maturity_without_evidence_caught(
    tmp_path: pathlib.Path,
) -> None:
    """G3: maturity>=implemented with only tech-plan evidence is rejected."""
    from apd_gauntlet import linters

    record = {
        "maturity": "implemented",
        "evidence": [{"artifact": "tech_plan.md", "locator": "§1"}],
    }
    errors = linters.check_capability_maturity_evidence(record, {"tech_plan.md"})
    assert errors != []
    assert "non-tech-plan evidence" in errors[0]
