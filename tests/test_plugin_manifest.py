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


def test_skills_array_matches_dir() -> None:
    """Explicit skills array must list EXACTLY each .claude/skills/<name>/SKILL.md (no drift)."""
    m = _manifest()
    listed = {_norm(p) for p in m["skills"]}
    actual = {
        str((d / "SKILL.md").relative_to(REPO))
        for d in (REPO / ".claude" / "skills").iterdir()
        if d.is_dir() and (d / "SKILL.md").is_file()
    }
    assert listed == actual, (
        f"skills array out of sync with .claude/skills/.\n"
        f"  missing from manifest: {sorted(actual - listed)}\n"
        f"  stale in manifest: {sorted(listed - actual)}"
    )


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
