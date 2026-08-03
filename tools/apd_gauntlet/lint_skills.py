"""Lint skill directories for valid frontmatter and name/directory agreement."""
from __future__ import annotations

import pathlib
import re

import yaml

from .lint_agents import FRONTMATTER_PATTERN


def lint_skill_dir(skill_dir: pathlib.Path) -> list[str]:
    """Lint one skill directory. Return error strings; empty list means clean."""
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.is_file():
        return [f"{skill_dir}: missing SKILL.md"]
    text = skill_md.read_text(encoding="utf-8").replace("\r\n", "\n")
    m = FRONTMATTER_PATTERN.match(text)
    if not m:
        return [f"{skill_md}: no YAML frontmatter (missing '---' block at top)"]
    try:
        meta = yaml.safe_load(m.group(1))
    except yaml.YAMLError as e:
        return [f"{skill_md}: frontmatter parse error: {e}"]
    if not isinstance(meta, dict):
        return [f"{skill_md}: frontmatter is not a mapping"]
    errors: list[str] = []
    name = meta.get("name")
    if not name:
        errors.append(f"{skill_md}: frontmatter missing 'name'")
    elif name != skill_dir.name:
        errors.append(
            f"{skill_md}: frontmatter name '{name}' != directory '{skill_dir.name}'"
        )
    if name and not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", str(name)):
        errors.append(
            f"{skill_md}: name '{name}' is not lowercase-hyphen form (Agent Skills standard)"
        )
    if name and len(str(name)) > 64:
        errors.append(f"{skill_md}: name exceeds 64 characters (Agent Skills standard)")
    desc = meta.get("description")
    if not desc:
        errors.append(f"{skill_md}: frontmatter missing 'description'")
    elif len(str(desc)) > 1536:
        errors.append(
            f"{skill_md}: description exceeds 1536 characters — Claude Code truncates "
            "the skill listing there (code.claude.com/docs/en/skills), silently "
            "degrading automatic invocation"
        )
    return errors


def lint_skills_dir(skills_dir: pathlib.Path) -> list[str]:
    out: list[str] = []
    for path in sorted(skills_dir.iterdir()):
        if path.is_dir():
            out.extend(lint_skill_dir(path))
    return out
