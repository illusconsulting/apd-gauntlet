"""Static-source test: the threat-model-evaluator agent must carry the
anti-tautology carve-out and the supplied-vs-authored comparator instructions
introduced by the threat-model-authoring effort.

The evaluator is a pure-LLM agent (no deterministic rollup under
tools/apd_gauntlet/ drives it), so the contract is enforced structurally on
the agent markdown the same way lint-agents enforces required-reading paths.
"""
from __future__ import annotations

import pathlib

AGENT = (
    pathlib.Path(__file__).resolve().parent.parent
    / ".claude"
    / "agents"
    / "apd-threat-model-evaluator.md"
)


def _text() -> str:
    return AGENT.read_text(encoding="utf-8")


def test_agent_keys_carveout_on_authored_baseline() -> None:
    text = _text()
    assert "threat_model_author" in text
    assert "Anti-tautology" in text


def test_carveout_disables_coverage_and_silence_on_authored_only() -> None:
    text = _text()
    assert "do not run the coverage-gap" in text.lower() or (
        "skip step 3" in text.lower() and "skip step 5" in text.lower()
    )


def test_carveout_keeps_contradiction_and_corroboration() -> None:
    text = _text()
    assert "contradiction pass" in text.lower()
    assert "corroborat" in text.lower()


def test_blocked_placeholder_never_counts_as_coverage() -> None:
    text = _text()
    assert "prerequisite_evidence" in text
    assert "never count" in text.lower() or "not counted" in text.lower()


def test_comparator_emits_omission_findings_and_delta() -> None:
    text = _text()
    assert "threat-model-supplied-normalized.yaml" in text
    assert "supplied_vs_authored" in text
    assert "baseline_only_threats" in text
    assert "supplied_omissions_emitted" in text


def test_comparator_omission_finding_is_gap_disposition() -> None:
    text = _text()
    assert "omission" in text.lower()
    assert "disposition: gap" in text
