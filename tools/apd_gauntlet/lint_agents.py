"""Lint agent files for valid frontmatter and resolved Required reading paths."""
from __future__ import annotations

import pathlib
import re

import yaml

FRONTMATTER_PATTERN = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)
REQUIRED_READING_PATTERN = re.compile(r"`([^`]+\.md)`")

RECEIPT_MARKER = "## Final message"
# Agents NOT dispatched as receipt-returning children of the run driver.
RECEIPT_EXEMPT = {"apd-synthesizer"}

# Claude Code loads every agent's description into each session that has the
# plugin enabled, so the description stays one short line.
MAX_AGENT_DESCRIPTION_CHARS = 160

# Claude Code subagent frontmatter values. Every agent sets `effort`; `model` stays
# optional until WS5 Task 23, and an omitted `model` differs from `inherit` when
# CLAUDE_CODE_SUBAGENT_MODEL is set.
ALLOWED_EFFORT = ("low", "medium", "high", "xhigh", "max")
MODEL_ALIASES = ("sonnet", "opus", "haiku", "fable", "inherit")
FULL_MODEL_ID = re.compile(r"^claude-[a-z0-9.-]+$")

# Every agent sets `tools`: without it, Claude Code gives the agent every tool of the
# session. A comma inside parentheses, as in `Agent(worker, researcher)`, does not
# separate two tool names.
TOOLS_SEPARATOR = re.compile(r",(?![^()]*\))")

BOUNDING_MARKER = "## Output bounding"
SPECIALIST_NAMES = {
    "apd-confidentiality", "apd-integrity", "apd-availability",
    "apd-distributed", "apd-resilient", "apd-ephemeral",
    "apd-authenticity", "apd-non-repudiation", "apd-immutability",
}


def description_errors(path: pathlib.Path, description: object, max_chars: int) -> list[str]:
    """Return the always-on footprint errors for one agent or skill description."""
    text = str(description)
    errors: list[str] = []
    if "\n" in text:
        errors.append(f"{path}: description must be one line")
    if len(text) > max_chars:
        errors.append(
            f"{path}: description is {len(text)} characters (max {max_chars}); it loads "
            "into every session with the plugin enabled — keep one line"
        )
    return errors


def parse_tools(value: object) -> frozenset[str] | None:
    """Return the tool names of an agent's `tools` value.

    The value is a comma-separated string or a YAML list of names. Returns None when it
    names no tool, holds an empty name, or is neither form.
    """
    if isinstance(value, str):
        names = [part.strip() for part in TOOLS_SEPARATOR.split(value)]
    elif isinstance(value, list):
        names = [item.strip() for item in value if isinstance(item, str)]
        if len(names) != len(value):
            return None
    else:
        return None
    if not names or not all(names):
        return None
    return frozenset(names)


def tools_errors(path: pathlib.Path, meta: dict[object, object]) -> list[str]:
    """Return the errors for an agent's `tools` (required, either form)."""
    tools = meta.get("tools")
    if tools is None or tools == "" or tools == []:
        return [f"{path}: frontmatter missing 'tools'"]
    if parse_tools(tools) is None:
        return [f"{path}: tools must be a comma-separated string or a YAML list of tool names"]
    return []


def model_effort_errors(path: pathlib.Path, meta: dict[object, object]) -> list[str]:
    """Return the errors for an agent's `effort` (required) and `model` (optional)."""
    errors: list[str] = []
    effort = meta.get("effort")
    if effort is None or effort == "":
        errors.append(f"{path}: frontmatter missing 'effort'")
    elif not (isinstance(effort, str) and effort in ALLOWED_EFFORT):
        errors.append(f"{path}: effort '{effort}' is not one of {', '.join(ALLOWED_EFFORT)}")
    if "model" in meta:
        model = meta["model"]
        if not (isinstance(model, str)
                and (model in MODEL_ALIASES or FULL_MODEL_ID.fullmatch(model))):
            errors.append(f"{path}: model '{model}' is not an alias or full model id")
    return errors


def lint_agent_file(path: pathlib.Path, repo_root: pathlib.Path) -> list[str]:
    """Return a list of error strings; empty list means clean."""
    errors: list[str] = []
    text = path.read_text(encoding="utf-8").replace("\r\n", "\n")
    m = FRONTMATTER_PATTERN.match(text)
    if not m:
        return [f"{path}: no YAML frontmatter (missing '---' block at top)"]
    try:
        meta = yaml.safe_load(m.group(1))
    except yaml.YAMLError as e:
        return [f"{path}: frontmatter parse error: {e}"]
    if not isinstance(meta, dict):
        return [f"{path}: frontmatter is not a mapping"]
    if "name" not in meta:
        errors.append(f"{path}: frontmatter missing 'name'")
    description = meta.get("description")
    if not description:
        errors.append(f"{path}: frontmatter missing 'description'")
    else:
        errors.extend(description_errors(path, description, MAX_AGENT_DESCRIPTION_CHARS))
    errors.extend(tools_errors(path, meta))
    errors.extend(model_effort_errors(path, meta))

    name = meta.get("name") or path.stem
    if name not in RECEIPT_EXEMPT and RECEIPT_MARKER not in text:
        errors.append(
            f"{path}: missing receipt contract section (expected a '{RECEIPT_MARKER}' heading)"
        )

    if name in SPECIALIST_NAMES and BOUNDING_MARKER not in text:
        errors.append(
            f"{path}: specialist missing output-bounding section "
            f"(expected a '{BOUNDING_MARKER}' heading)"
        )

    # Check Required reading paths.
    body = text[m.end():]
    # Look for the "Required reading" section header and the bulleted list after it.
    rr_section = re.search(r"(?ms)^##+\s*Required reading.*?(?=^##|\Z)", body)
    if rr_section:
        for ref in REQUIRED_READING_PATTERN.findall(rr_section.group(0)):
            # Only check repo-relative paths (starting with `.claude/` or similar).
            if ref.startswith(".claude/"):
                target = repo_root / ref
                if not target.exists():
                    errors.append(f"{path}: required reading target not found: {ref}")
    return errors


def lint_agents_dir(agent_dir: pathlib.Path, repo_root: pathlib.Path) -> list[str]:
    out: list[str] = []
    for path in sorted(agent_dir.glob("*.md")):
        out.extend(lint_agent_file(path, repo_root))
    return out
