# tests/test_report_writer_qualitative.py
"""The report-writer is told metrics render structurally; prose stays qualitative,
and metrics.yaml + attack-path findings are declared inputs on both surfaces."""
from __future__ import annotations

import pathlib

REPO = pathlib.Path(__file__).resolve().parents[1]
AGENT = (REPO / ".claude" / "agents" / "apd-report-writer.md").read_text()
ADVISORY_TMPL = (REPO / "templates" / "advisory-report.template.md").read_text()


def test_agent_declares_metrics_and_apath_inputs():
    assert "metrics.yaml" in AGENT
    assert "attack-path.findings.yaml" in AGENT


def test_agent_instructs_qualitative_prose():
    lowered = AGENT.lower()
    assert "do not restate" in lowered or "do not author" in lowered
    assert "qualitative" in lowered


def test_advisory_template_drops_literal_count_prompts():
    # The old §1 prompted "<n> critical, <n> high, <n> medium, <n> low, <n> informational".
    assert "<n> critical, <n> high, <n> medium, <n> low" not in ADVISORY_TMPL
    # New qualitative contract markers are present:
    assert "hand-type counts" in ADVISORY_TMPL
    assert "hand-type maturity counts" in ADVISORY_TMPL
    # No severity/maturity count-prompt survives inside §1 (tolerates the legitimate
    # "<n> artifacts" header above §1).
    import re as _re
    m = _re.search(r"## 1\. Executive Summary(.*?)## 2\.", ADVISORY_TMPL, _re.S)
    assert m, "could not locate §1 section"
    section = m.group(1)
    assert not _re.search(r"<n>\s+(critical|high|medium|low|capabilit)", section, _re.I)
