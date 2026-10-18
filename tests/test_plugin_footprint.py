"""The always-on footprint: every agent and skill description loads into each session.

Claude Code puts the description of every agent and skill the plugin lists into
each session that has the plugin enabled. The workflow names every `agentType`
it dispatches, so a description only steers delegation; keep each to one line.
"""
from __future__ import annotations

import json
import pathlib

import pytest
import yaml
from apd_gauntlet import lint_agents
from apd_gauntlet.lint_agents import FRONTMATTER_PATTERN
from test_plugin_manifest import PLUGIN, REPO, _norm

AGENT_ENDING = "; dispatched by the apd-gauntlet workflow only."
SKILL_ENDING = " Read through the agent's Required reading."

LENSES = {
    "apd-confidentiality": (1, "Confidentiality"),
    "apd-integrity": (1, "Integrity"),
    "apd-availability": (1, "Availability"),
    "apd-distributed": (2, "Distributed"),
    "apd-resilient": (2, "Resilient"),
    "apd-ephemeral": (2, "Ephemeral"),
    "apd-authenticity": (3, "Authenticity"),
    "apd-non-repudiation": (3, "Non-Repudiation"),
    "apd-immutability": (3, "Immutability"),
}

AGENTS = {
    "apd-attack-path-analyzer": (
        "APD gauntlet tier-4 attack-path analysis: asset graph, paths to crown jewels, "
        "D3FEND counters"
    ),
    "apd-cluster-adjudicator": (
        "APD gauntlet synthesis 5b: merge, link or separate candidate clusters"
    ),
    "apd-code-recon": (
        "APD gauntlet optional code reconnaissance via codebase-memory-mcp "
        "(code evidence index, C4 recon)"
    ),
    "apd-domain-auditor": "APD gauntlet advisory domain-pack improvement capture",
    "apd-intake": "APD gauntlet intake: context brief and asset inventory from the run inputs",
    "apd-report-auditor": (
        "APD gauntlet synthesis 5g: judges the advisory report's faithfulness to the findings"
    ),
    "apd-report-writer": (
        "APD gauntlet synthesis 5e: writes the advisory report prose and report-data.yaml"
    ),
    "apd-synthesizer": (
        "APD gauntlet synthesis fallback, used when the decomposed pipeline fails"
    ),
    "apd-threat-model-author": "APD gauntlet tier-0: authors the grounded baseline threat model",
    "apd-threat-model-evaluator": (
        "APD gauntlet tier-4: checks findings against the threat model "
        "(gaps, contradictions, silences)"
    ),
    "apd-threat-model-recon": (
        "APD gauntlet tier-0: parses a supplied threat model into normalized YAML"
    ),
}

SKILLS = {
    "apd-attack-path-discipline": (
        "Discipline rules for apd-attack-path-analyzer: never-invent nodes and edges, "
        "bounded enumeration, D3FEND counters."
    ),
    "apd-c4-discipline": (
        "Discipline rules for apd-code-recon when it writes 00-context/c4-recon.yaml."
    ),
    "apd-control-mappings": (
        "NIST 800-53r5 and MITRE ATT&CK mapping rules for APD gauntlet findings and "
        "capabilities."
    ),
    "apd-evidence-discipline": (
        "Evidence, blocking, lens and severity discipline for APD gauntlet specialists."
    ),
    "apd-finding-schema": "YAML contracts for APD gauntlet finding and capability records.",
    "apd-framework": (
        "The APD framework: three tiers, nine security goals and the boundary rules "
        "between goals."
    ),
    "apd-threat-model-methodologies": (
        "STRIDE and LINDDUN to APD mappings and rules for the threat-model recon and "
        "evaluator agents."
    ),
}


def _description(path: pathlib.Path) -> str:
    text = path.read_text(encoding="utf-8").replace("\r\n", "\n")
    m = FRONTMATTER_PATTERN.match(text)
    assert m, f"{path}: no YAML frontmatter"
    return str(yaml.safe_load(m.group(1))["description"])


def _expected() -> dict[pathlib.Path, str]:
    agents = REPO / ".claude" / "agents"
    skills = REPO / ".claude" / "skills"
    out = {
        agents / f"{name}.md": f"APD gauntlet tier-{n} {goal} lens specialist{AGENT_ENDING}"
        for name, (n, goal) in LENSES.items()
    }
    out.update({agents / f"{name}.md": text + AGENT_ENDING for name, text in AGENTS.items()})
    out.update({skills / name / "SKILL.md": text + SKILL_ENDING for name, text in SKILLS.items()})
    return out


def test_always_on_description_budget():
    m = json.loads(PLUGIN.read_text(encoding="utf-8"))
    files = [REPO / _norm(p) for p in m["agents"]]
    files += [REPO / _norm(d) / "SKILL.md" for d in m["skills"]]
    assert sum(len(_description(f).encode("utf-8")) for f in files) <= 4096


def test_orchestrator_removed():
    assert not (REPO / ".claude/agents/apd-orchestrator.md").exists()
    agents = json.loads(PLUGIN.read_text(encoding="utf-8"))["agents"]
    assert not any("apd-orchestrator" in p for p in agents)


def test_only_the_synthesizer_is_receipt_exempt():
    exempt = set(lint_agents.RECEIPT_EXEMPT)
    assert exempt == {"apd-synthesizer"}


def test_no_agent_or_skill_names_the_orchestrator():
    paths = sorted((REPO / ".claude" / "agents").glob("*.md"))
    paths += sorted((REPO / ".claude" / "skills").glob("*/SKILL.md"))
    named = [p.name for p in paths if "apd-orchestrator" in p.read_text(encoding="utf-8")]
    assert named == []


def test_the_planned_set_is_every_listed_agent_and_skill_but_three():
    m = json.loads(PLUGIN.read_text(encoding="utf-8"))
    listed = {REPO / _norm(p) for p in m["agents"]}
    listed |= {REPO / _norm(d) / "SKILL.md" for d in m["skills"]}
    untouched = {
        REPO / ".claude/agents/apd-cli-runner.md",
        REPO / ".claude/agents/apd-tier-repair.md",
        REPO / ".claude/skills/apd-domain/SKILL.md",
    }
    assert listed - untouched == set(_expected())
    assert len(_expected()) == 27


@pytest.mark.parametrize(
    "path", sorted(_expected()), ids=lambda p: p.stem if p.stem != "SKILL" else p.parent.name
)
def test_description_is_the_planned_one_line(path: pathlib.Path) -> None:
    want = _expected()[path]
    assert _description(path) == want
    m = FRONTMATTER_PATTERN.match(path.read_text(encoding="utf-8"))
    assert m
    # Double-quoted, because several contain a colon followed by a space.
    assert f'description: "{want}"' in m.group(1).splitlines()
