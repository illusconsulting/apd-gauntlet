"""Tests for the lint-skills command and lint_skills helpers."""
from __future__ import annotations

import pathlib

from apd_gauntlet.cli import main
from apd_gauntlet.lint_skills import lint_skill_dir, lint_skills_dir
from click.testing import CliRunner

REPO = pathlib.Path(__file__).resolve().parent.parent


def test_lint_skills_clean_on_real_repo() -> None:
    errors = lint_skills_dir(REPO / ".claude" / "skills")
    assert errors == [], errors


def _write_skill(root: pathlib.Path, dirname: str, frontmatter: str) -> pathlib.Path:
    d = root / dirname
    d.mkdir(parents=True)
    (d / "SKILL.md").write_text(f"---\n{frontmatter}\n---\nbody\n", encoding="utf-8")
    return d


def test_lint_skills_flags_missing_skill_md(tmp_path) -> None:
    (tmp_path / "foo").mkdir()
    errors = lint_skill_dir(tmp_path / "foo")
    assert any("missing SKILL.md" in e for e in errors)


def test_lint_skills_flags_missing_description(tmp_path) -> None:
    d = _write_skill(tmp_path, "foo", "name: foo")
    errors = lint_skill_dir(d)
    assert any("missing 'description'" in e for e in errors)


def test_lint_skills_flags_name_dir_mismatch(tmp_path) -> None:
    d = _write_skill(tmp_path, "foo", "name: bar\ndescription: x")
    errors = lint_skill_dir(d)
    assert any("!= directory" in e for e in errors)


def test_lint_skills_cli_exit_zero_on_real_repo() -> None:
    result = CliRunner().invoke(main, ["lint-skills", "--skill-dir", str(REPO / ".claude/skills")])
    assert result.exit_code == 0, result.output
    assert "Lint clean" in result.output
