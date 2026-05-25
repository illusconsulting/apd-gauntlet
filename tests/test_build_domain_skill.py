"""Tests for the build-domain-skill command."""
from __future__ import annotations
from click.testing import CliRunner
from apd_gauntlet.cli import main


def test_build_domain_skill_emits_expected_file(tmp_path):
    runner = CliRunner()
    out = tmp_path / "apd-domain"
    result = runner.invoke(
        main,
        ["build-domain-skill", "sample",
         "--domains-dir", "tests/fixtures/domains",
         "--out", str(out),
         "--framework-version", "1.0.0"],
    )
    assert result.exit_code == 0, result.output
    skill = out / "SKILL.md"
    assert skill.exists()
    text = skill.read_text()
    assert "name: apd-domain" in text
    assert "pack: sample" in text
    assert "Sample severity rubric" in text
    assert "Confidentiality patterns (sample)" in text


def test_build_domain_skill_rejects_incompatible_framework(tmp_path):
    runner = CliRunner()
    result = runner.invoke(
        main,
        ["build-domain-skill", "sample",
         "--domains-dir", "tests/fixtures/domains",
         "--out", str(tmp_path / "apd-domain"),
         "--framework-version", "2.0.0"],
    )
    assert result.exit_code != 0
    assert "incompatible" in result.output.lower() or "framework_compat" in result.output.lower()
