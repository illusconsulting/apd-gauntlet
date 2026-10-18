"""docs/measuring-changes.md: the operator runbook for before-and-after measurement."""
from __future__ import annotations

import pathlib

from apd_gauntlet.measure.usage import AGENT_PHASES

REPO = pathlib.Path(__file__).resolve().parent.parent


def test_runbook_covers_baseline_capture():
    t = (REPO / "docs/measuring-changes.md").read_text()
    for s in ("CLAUDE_CODE_ENABLE_TELEMETRY=1", "OTEL_LOGS_EXPORTER=otlp",
              "OTEL_EXPORTER_OTLP_PROTOCOL=http/json", "OTEL_LOG_TOOL_DETAILS=1", "2.1.273",
              "-baseline-r1", "-baseline-r2", "apd-gauntlet usage"):
        assert s in t


# --- beyond the plan's tests -------------------------------------------------------------


def test_runbook_sections_and_collector():
    t = (REPO / "docs/measuring-changes.md").read_text()
    for heading in ("## Why measure", "## Capture a baseline", "## Telemetry", "## Usage"):
        assert heading in t
    for s in ("OTEL_EXPORTER_OTLP_ENDPOINT=http://127.0.0.1:4318", "telemetry/<run-id>.otlp.jsonl",
              "apd-gauntlet validate", "ADR-0017", "--workflow-run"):
        assert s in t


def test_runbook_phase_table_matches_agent_phases():
    t = (REPO / "docs/measuring-changes.md").read_text()
    for agent, phase in AGENT_PHASES.items():
        assert f"| `{agent}` | `{phase}` |" in t, agent


def test_running_guide_links_the_runbook():
    t = (REPO / "docs/running-the-gauntlet.md").read_text()
    section = t.split("## Local accuracy benchmark (out-of-band)", 1)[1].split("\n## ", 1)[0]
    assert "(measuring-changes.md)" in section
