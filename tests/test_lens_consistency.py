# tests/test_lens_consistency.py
"""Tests for check_lens_consistency — the lens record agent==apd_goal +
apd_tier==goal-tier semantic gate.

Closes a silent-noncompliance gap surfaced by the specialist-compliance audit:
the JSON schema validates agent / apd_goal / apd_tier independently against their
enums, so a lens agent could relabel its goal (cross-lens leakage) or mis-tier a
record and still pass schema validation.
"""
from __future__ import annotations

import pathlib
import shutil

from apd_gauntlet.cli import main
from apd_gauntlet.linters import check_lens_consistency
from click.testing import CliRunner

FIXTURES = pathlib.Path(__file__).parent / "fixtures" / "runs"


# ---------------------------------------------------------------------------
# Unit
# ---------------------------------------------------------------------------

def test_valid_lens_record_passes() -> None:
    assert check_lens_consistency(
        {"agent": "confidentiality", "apd_goal": "confidentiality", "apd_tier": "trustworthiness"}
    ) == []


def test_cross_lens_goal_relabel_flagged() -> None:
    errs = check_lens_consistency(
        {"agent": "confidentiality", "apd_goal": "authenticity", "apd_tier": "auditability"}
    )
    assert any("must equal apd_goal" in e for e in errs)


def test_wrong_tier_flagged() -> None:
    errs = check_lens_consistency(
        {"agent": "distributed", "apd_goal": "distributed", "apd_tier": "trustworthiness"}
    )
    assert any("does not match lens" in e for e in errs)
    assert any("expected 'scalability'" in e for e in errs)


def test_all_nine_lenses_consistent_when_self_labelled() -> None:
    tiers = {
        "confidentiality": "trustworthiness", "integrity": "trustworthiness",
        "availability": "trustworthiness", "distributed": "scalability",
        "resilient": "scalability", "ephemeral": "scalability",
        "authenticity": "auditability", "non_repudiation": "auditability",
        "immutability": "auditability",
    }
    for lens, tier in tiers.items():
        assert check_lens_consistency(
            {"agent": lens, "apd_goal": lens, "apd_tier": tier}
        ) == [], lens


def test_non_lens_agents_exempt() -> None:
    # synthesizer / tmeval / apath legitimately carry any goal+tier.
    for agent in ("synthesizer", "threat_model_evaluator", "attack_path_analyzer"):
        assert check_lens_consistency(
            {"agent": agent, "apd_goal": "confidentiality", "apd_tier": "scalability"}
        ) == [], agent


def test_applies_to_capability_shape_too() -> None:
    # capabilities carry the same agent/apd_goal/apd_tier triple.
    errs = check_lens_consistency(
        {"agent": "integrity", "apd_goal": "availability", "apd_tier": "trustworthiness"}
    )
    assert any("must equal apd_goal" in e for e in errs)


# ---------------------------------------------------------------------------
# CLI integration (clean-run fixture)
# ---------------------------------------------------------------------------

def _copy_clean_run(tmp_path):
    dst = tmp_path / "run"
    shutil.copytree(FIXTURES / "clean-run", dst)
    return dst


def test_clean_run_passes_lens_consistency(tmp_path):
    dst = _copy_clean_run(tmp_path)
    result = CliRunner().invoke(main, ["validate", str(dst)])
    assert result.exit_code == 0, result.output


def test_relabelled_goal_caught_by_validate(tmp_path):
    dst = _copy_clean_run(tmp_path)
    f = dst / "10-trustworthiness" / "confidentiality.findings.yaml"
    text = f.read_text()
    assert "apd_goal: confidentiality" in text
    # Relabel the goal to another lens while leaving agent: confidentiality.
    text = text.replace("apd_goal: confidentiality", "apd_goal: integrity", 1)
    f.write_text(text)
    result = CliRunner().invoke(main, ["validate", str(dst)])
    assert result.exit_code == 1
    assert "must equal apd_goal" in result.output
