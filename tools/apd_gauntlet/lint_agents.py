"""Lint agent files for valid frontmatter and resolved Required reading paths."""
from __future__ import annotations

import pathlib
import re

import yaml

FRONTMATTER_PATTERN = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)
REQUIRED_READING_PATTERN = re.compile(r"`([^`]+\.md)`")

RECEIPT_MARKER = "## Final message"
# Agents NOT dispatched as receipt-returning children of the run driver.
RECEIPT_EXEMPT = {"apd-orchestrator", "apd-synthesizer"}

BOUNDING_MARKER = "## Output bounding"
SPECIALIST_NAMES = {
    "apd-confidentiality", "apd-integrity", "apd-availability",
    "apd-distributed", "apd-resilient", "apd-ephemeral",
    "apd-authenticity", "apd-non-repudiation", "apd-immutability",
}


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
    if "description" not in meta:
        errors.append(f"{path}: frontmatter missing 'description'")

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
