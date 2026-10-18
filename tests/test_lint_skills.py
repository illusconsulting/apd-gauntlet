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


def test_lint_skills_flags_bad_name_format(tmp_path) -> None:
    d = _write_skill(tmp_path, "Foo_Bar", "name: Foo_Bar\ndescription: x")
    errors = lint_skill_dir(d)
    assert any("lowercase-hyphen" in e for e in errors)


def test_lint_skills_flags_overlong_description(tmp_path) -> None:
    d = _write_skill(tmp_path, "foo", "name: foo\ndescription: " + "x" * 1600)
    errors = lint_skill_dir(d)
    assert any("1536" in e for e in errors)


def test_lint_skills_accepts_crlf_frontmatter(tmp_path) -> None:
    d = tmp_path / "foo"
    d.mkdir()
    (d / "SKILL.md").write_bytes(b"---\r\nname: foo\r\ndescription: x\r\n---\r\nbody\r\n")
    assert lint_skill_dir(d) == []


def test_lint_skills_flags_description_over_budget(tmp_path) -> None:
    d = _write_skill(tmp_path, "foo", "name: foo\ndescription: " + "x" * 201)
    assert any("max 200" in e for e in lint_skill_dir(d))


def test_lint_skills_description_cap_error_text(tmp_path) -> None:
    from apd_gauntlet.lint_skills import MAX_SKILL_DESCRIPTION_CHARS

    d = _write_skill(tmp_path, "foo", "name: foo\ndescription: " + "x" * 201)
    assert MAX_SKILL_DESCRIPTION_CHARS == 200
    assert lint_skill_dir(d) == [
        f"{d / 'SKILL.md'}: description is 201 characters (max 200); it loads into every "
        "session with the plugin enabled — keep one line"
    ]


def test_lint_skills_flags_multiline_description(tmp_path) -> None:
    d = _write_skill(tmp_path, "foo", "name: foo\ndescription: |\n  a\n  b")
    assert lint_skill_dir(d) == [f"{d / 'SKILL.md'}: description must be one line"]


def test_lint_skills_accepts_a_description_at_the_cap(tmp_path) -> None:
    d = _write_skill(tmp_path, "foo", "name: foo\ndescription: " + "x" * 200)
    assert lint_skill_dir(d) == []
