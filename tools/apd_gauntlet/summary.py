"""Run summary statistics."""
from __future__ import annotations

import pathlib
from collections import Counter
from typing import Any

import yaml

from .validate import _iter_records


def summarize_run(run_dir: pathlib.Path) -> dict[str, Any]:
    severity_counts: Counter[str] = Counter()
    maturity_counts: Counter[str] = Counter()
    disposition_counts: Counter[str] = Counter()
    findings = 0
    capabilities = 0
    for _path, kind, record in _iter_records(run_dir):
        if "_parse_error" in record:
            continue
        if kind == "finding":
            findings += 1
            severity_counts[record.get("severity", "unknown")] += 1
            disposition_counts[record.get("disposition", "unknown")] += 1
        else:
            capabilities += 1
            maturity_counts[record.get("maturity", "unknown")] += 1

    contradictions_path = run_dir / "40-synthesis" / "contradictions.yaml"
    severity_disagreements_path = run_dir / "40-synthesis" / "severity-disagreements.yaml"
    contradictions = 0
    severity_disagreements = 0
    if contradictions_path.exists():
        data = yaml.safe_load(contradictions_path.read_text(encoding="utf-8")) or {}
        contradictions = len(data.get("contradictions") or [])
    if severity_disagreements_path.exists():
        data = yaml.safe_load(severity_disagreements_path.read_text(encoding="utf-8")) or {}
        severity_disagreements = len(data.get("severity_disagreements") or [])

    return {
        "findings": findings,
        "severity": dict(severity_counts),
        "disposition": dict(disposition_counts),
        "capabilities": capabilities,
        "maturity": dict(maturity_counts),
        "contradictions": contradictions,
        "severity_disagreements": severity_disagreements,
    }


def render_summary(stats: dict[str, Any]) -> str:
    lines = []
    lines.append(f"Findings: {stats['findings']}")
    for sev in ("critical", "high", "medium", "low", "informational"):
        lines.append(f"  {sev}: {stats['severity'].get(sev, 0)}")
    lines.append(f"  blocked-on-evidence: {stats['disposition'].get('blocked', 0)}")
    lines.append(f"Capabilities: {stats['capabilities']}")
    for m in ("designed", "implemented", "tested", "operationalized"):
        lines.append(f"  {m}: {stats['maturity'].get(m, 0)}")
    lines.append(f"Contradictions: {stats['contradictions']}")
    lines.append(f"Severity disagreements: {stats['severity_disagreements']}")
    return "\n".join(lines)
