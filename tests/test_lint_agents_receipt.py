"""Every dispatched agent must declare the receipt contract; orchestrator/synthesizer exempt."""
from __future__ import annotations

import pathlib

from apd_gauntlet.lint_agents import RECEIPT_MARKER, lint_agent_file

REPO = pathlib.Path(__file__).parent.parent
AGENTS = REPO / ".claude" / "agents"


def test_specialist_missing_receipt_is_flagged(tmp_path):
    agent = tmp_path / "apd-fake-specialist.md"
    agent.write_text(
        "---\nname: apd-fake-specialist\ndescription: x\n---\n\n"
        "# Fake\n\n## Output\n\nWrites foo.findings.yaml\n"
    )
    errors = lint_agent_file(agent, tmp_path)
    assert any("receipt" in e.lower() or "final message" in e.lower() for e in errors)


def test_orchestrator_is_exempt(tmp_path):
    agent = tmp_path / "apd-orchestrator.md"
    agent.write_text("---\nname: apd-orchestrator\ndescription: x\n---\n\n# Orchestrator\n")
    errors = lint_agent_file(agent, tmp_path)
    assert not any("receipt" in e.lower() or "final message" in e.lower() for e in errors)


def test_real_dispatched_agents_all_carry_receipt_contract():
    dispatched = [
        "apd-intake", "apd-code-recon", "apd-threat-model-recon",
        "apd-confidentiality", "apd-integrity", "apd-availability",
        "apd-distributed", "apd-resilient", "apd-ephemeral",
        "apd-authenticity", "apd-non-repudiation", "apd-immutability",
        "apd-attack-path-analyzer", "apd-threat-model-evaluator",
    ]
    for name in dispatched:
        text = (AGENTS / f"{name}.md").read_text()
        assert RECEIPT_MARKER in text, f"{name}.md missing receipt contract section"
