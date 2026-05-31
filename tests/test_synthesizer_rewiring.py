"""The synthesizer no longer triggers build-report; the build is a workflow phase (Plan 3)."""
from __future__ import annotations

import pathlib

REPO = pathlib.Path(__file__).parent.parent
SYNTH = REPO / ".claude" / "agents" / "apd-synthesizer.md"


def test_synthesizer_does_not_trigger_build_report():
    text = SYNTH.read_text()
    assert "## Trailing HTML build" not in text, "synthesizer must not own the trailing HTML build"
    # The synthesizer must not instruct invoking build-report itself anymore.
    assert "apd-gauntlet build-report" not in text


def test_synthesizer_documents_build_is_a_workflow_phase():
    text = SYNTH.read_text()
    # A short note explaining the re-wiring (so a reader knows where the build went).
    assert "build-report" in text  # referenced in prose, not as a trigger
    assert "workflow" in text.lower()
