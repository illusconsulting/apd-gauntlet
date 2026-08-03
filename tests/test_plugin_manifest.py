"""Structural + drift guards for the Claude Code plugin and marketplace manifests."""
from __future__ import annotations

import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
PLUGIN = REPO / ".claude-plugin" / "plugin.json"
MARKET = REPO / ".claude-plugin" / "marketplace.json"


def _manifest() -> dict:
    return json.loads(PLUGIN.read_text(encoding="utf-8"))


def _norm(p: str) -> str:
    """Strip leading './' prefix without corrupting dotfile paths like .claude/."""
    return p[2:] if p.startswith("./") else p


def test_plugin_manifest_well_formed() -> None:
    m = _manifest()
    for k in ("name", "version", "description", "license", "agents", "skills"):
        assert m.get(k), f"missing/empty {k}"
    assert m["name"] == "apd-gauntlet"


def test_agents_array_matches_dir() -> None:
    """The explicit agents array must list EXACTLY the .claude/agents/*.md files (no drift)."""
    m = _manifest()
    listed = {_norm(p) for p in m["agents"]}
    actual = {str(p.relative_to(REPO)) for p in (REPO / ".claude" / "agents").glob("*.md")}
    assert listed == actual, (
        f"agents array out of sync with .claude/agents/.\n"
        f"  missing from manifest: {sorted(actual - listed)}\n"
        f"  stale in manifest: {sorted(listed - actual)}"
    )


def test_commands_array_matches_dir() -> None:
    """The explicit commands array must list EXACTLY the commands/*.md files (no drift)."""
    m = _manifest()
    listed = {_norm(p) for p in m.get("commands", [])}
    actual = {str(p.relative_to(REPO)) for p in (REPO / "commands").glob("*.md")}
    assert listed == actual, (
        f"commands array out of sync with commands/.\n"
        f"  missing from manifest: {sorted(actual - listed)}\n"
        f"  stale in manifest: {sorted(listed - actual)}"
    )


def test_skills_array_matches_dir() -> None:
    """Explicit skills array must list EXACTLY each .claude/skills/<name> directory (no drift).

    Claude Code requires each skills entry to be the directory that contains a
    SKILL.md, not the SKILL.md file itself; a file path fails to load with
    "path is a file; skills entries must be directories containing SKILL.md".
    """
    m = _manifest()
    listed = {_norm(p) for p in m["skills"]}
    actual = {
        str(d.relative_to(REPO))
        for d in (REPO / ".claude" / "skills").iterdir()
        if d.is_dir() and (d / "SKILL.md").is_file()
    }
    assert listed == actual, (
        f"skills array out of sync with .claude/skills/.\n"
        f"  missing from manifest: {sorted(actual - listed)}\n"
        f"  stale in manifest: {sorted(listed - actual)}"
    )


def test_skills_entries_are_directories_not_files() -> None:
    """Regression: every skills entry must resolve to a directory holding a SKILL.md.

    Guards against reintroducing the ".../SKILL.md" file-path form that Claude
    Code rejects at load time.
    """
    for rel in _manifest()["skills"]:
        skill_dir = REPO / _norm(rel)
        assert skill_dir.is_dir(), f"skills entry is not a directory: {rel}"
        assert (skill_dir / "SKILL.md").is_file(), f"missing SKILL.md in {rel}"


def test_commands_paths_exist() -> None:
    for rel in _manifest().get("commands", []):
        assert (REPO / _norm(rel)).is_file(), f"missing command file {rel}"


def test_marketplace_well_formed_and_versions_match() -> None:
    mk = json.loads(MARKET.read_text(encoding="utf-8"))
    assert mk["name"] == "apd-security"
    assert isinstance(mk.get("owner"), dict) and mk["owner"].get("name")
    entry = next(p for p in mk["plugins"] if p["name"] == "apd-gauntlet")
    assert entry["source"] == "./"
    assert entry["version"] == _manifest()["version"]


def _loader_contract_errors(m: dict) -> list[str]:
    """Assert each manifest array matches Claude Code's plugin-LOADER contract.

    Verified against https://code.claude.com/docs/en/plugins-reference and
    empirically (2026-07-14, re-verified 2026-08-02 on CLI 2.0.76):
    `claude plugin validate` exits 0 on the file-vs-directory skills error, so
    this filesystem-aware check — not the CLI — is the load-bearing guard.
    The skills branch deliberately overlaps
    test_skills_entries_are_directories_not_files above, which stays as the
    narrowly-labeled PR #8 regression guard; the new coverage here is the
    agents/commands path-form contract plus the non-vacuity fixtures.
    """
    errors: list[str] = []
    for rel in m.get("skills", []):
        d = REPO / _norm(rel)
        if not d.is_dir() or not (d / "SKILL.md").is_file():
            errors.append(f"skills entry must be a directory containing SKILL.md: {rel}")
    for rel in m.get("agents", []):
        p = REPO / _norm(rel)
        if not (rel.endswith(".md") and p.is_file()):
            errors.append(f"agents entry must be a .md file: {rel}")
    for rel in m.get("commands", []):
        p = REPO / _norm(rel)
        if not (rel.endswith(".md") and p.is_file()):
            errors.append(f"commands entry must be a .md file: {rel}")
    return errors


def test_manifest_satisfies_loader_contract() -> None:
    assert _loader_contract_errors(_manifest()) == []


def test_loader_contract_flags_file_form_skill() -> None:
    """Non-vacuous: the original PR #8 bug (skills -> SKILL.md file) is caught."""
    broken = dict(_manifest())
    broken["skills"] = ["./.claude/skills/apd-framework/SKILL.md"]
    errs = _loader_contract_errors(broken)
    assert any("directory containing SKILL.md" in e for e in errs)


def test_loader_contract_flags_directory_form_agent() -> None:
    """Non-vacuous: an agent entry pointing at a directory is caught."""
    broken = dict(_manifest())
    broken["agents"] = ["./.claude/agents"]
    errs = _loader_contract_errors(broken)
    assert any("agents entry must be a .md file" in e for e in errs)


def test_loader_contract_flags_directory_form_command() -> None:
    """Non-vacuous: a commands entry pointing at a directory is caught."""
    broken = dict(_manifest())
    broken["commands"] = ["./commands"]
    errs = _loader_contract_errors(broken)
    assert any("commands entry must be a .md file" in e for e in errs)
