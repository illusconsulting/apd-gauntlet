"""Lint skill directories for valid frontmatter and name/directory agreement."""
from __future__ import annotations

import pathlib
import re

import yaml

FRONTMATTER_PATTERN = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)


def lint_skill_dir(skill_dir: pathlib.Path) -> list[str]:
    """Lint one skill directory. Return error strings; empty list means clean."""
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.is_file():
        return [f"{skill_dir}: missing SKILL.md"]
    text = skill_md.read_text(encoding="utf-8")
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
    if not meta.get("description"):
        errors.append(f"{skill_md}: frontmatter missing 'description'")
    return errors


def lint_skills_dir(skills_dir: pathlib.Path) -> list[str]:
    out: list[str] = []
    for path in sorted(skills_dir.iterdir()):
        if path.is_dir():
            out.extend(lint_skill_dir(path))
    return out
