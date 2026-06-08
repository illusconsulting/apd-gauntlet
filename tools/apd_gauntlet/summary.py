"""Run summary statistics."""
from __future__ import annotations

import pathlib
from collections import Counter
from typing import Any

import yaml

from .validate import _iter_records


def _summarize_from_metrics(metrics: dict[str, Any]) -> dict[str, Any]:
    """Build the count block from the authoritative deduped metrics.yaml.

    metrics.yaml is the single source of truth post-synthesis (deduped
    specialist findings unioned with tmeval + apath). Its ``bySeverity`` uses
    the key ``info``; the summary renders ``informational``, so we remap.
    """
    severity = dict(metrics.get("bySeverity") or {})
    if "info" in severity and "informational" not in severity:
        severity["informational"] = severity.pop("info")
    return {
        "findings": int(metrics.get("findings_total") or 0),
        "severity": severity,
        "disposition": dict(metrics.get("byDisposition") or {}),
        "capabilities": int(metrics.get("capabilities_total") or 0),
        "maturity": dict(metrics.get("capabilitiesByMaturity") or {}),
        "contradictions": int(metrics.get("contradictions") or 0),
        "severity_disagreements": int(metrics.get("severity_disagreements") or 0),
    }


def summarize_run(run_dir: pathlib.Path) -> dict[str, Any]:
    # FW-6: prefer the authoritative deduped counts in metrics.yaml when the run
    # has reached synthesis. The raw _iter_records tally counts pre-dedup
    # per-lens records and over-reports relative to the report; only fall back to
    # it (clearly labelled) when metrics.yaml is absent (pre-synthesis).
    metrics_path = run_dir / "40-synthesis" / "metrics.yaml"
    metrics: Any = None
    if metrics_path.exists():
        try:
            metrics = yaml.safe_load(metrics_path.read_text(encoding="utf-8"))
        except yaml.YAMLError:
            metrics = None

    if isinstance(metrics, dict) and metrics.get("findings_total") is not None:
        block = _summarize_from_metrics(metrics)
        source = "metrics"
    else:
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
        block = {
            "findings": findings,
            "severity": dict(severity_counts),
            "disposition": dict(disposition_counts),
            "capabilities": capabilities,
            "maturity": dict(maturity_counts),
            "contradictions": 0,
            "severity_disagreements": 0,
        }
        source = "raw"

    # The contradictions / severity-disagreements annex files are authoritative
    # when present; use them to confirm the count regardless of source.
    contradictions_path = run_dir / "40-synthesis" / "contradictions.yaml"
    severity_disagreements_path = run_dir / "40-synthesis" / "severity-disagreements.yaml"
    if contradictions_path.exists():
        data = yaml.safe_load(contradictions_path.read_text(encoding="utf-8")) or {}
        block["contradictions"] = len(data.get("contradictions") or [])
    if severity_disagreements_path.exists():
        data = yaml.safe_load(severity_disagreements_path.read_text(encoding="utf-8")) or {}
        block["severity_disagreements"] = len(data.get("severity_disagreements") or [])

    domain_improvements_path = run_dir / "40-synthesis" / "domain-improvements.yaml"
    domain_improvements: int | None = None
    if domain_improvements_path.exists():
        di = yaml.safe_load(domain_improvements_path.read_text(encoding="utf-8")) or {}
        domain_improvements = len(di.get("improvements") or [])

    return {**block, "source": source, "domain_improvements": domain_improvements}


def render_summary(stats: dict[str, Any]) -> str:
    lines = []
    # FW-6: make the count provenance explicit so the deduped report total and
    # the pre-synthesis raw tally are never confused.
    if stats.get("source") == "raw":
        lines.append("(raw pre-dedup tally — metrics.yaml not yet generated)")
    elif stats.get("source") == "metrics":
        lines.append("(authoritative deduped counts — source: 40-synthesis/metrics.yaml)")
    lines.append(f"Findings: {stats['findings']}")
    for sev in ("critical", "high", "medium", "low", "informational"):
        lines.append(f"  {sev}: {stats['severity'].get(sev, 0)}")
    lines.append(f"  blocked-on-evidence: {stats['disposition'].get('blocked', 0)}")
    lines.append(f"Capabilities: {stats['capabilities']}")
    for m in ("designed", "implemented", "tested", "operationalized"):
        lines.append(f"  {m}: {stats['maturity'].get(m, 0)}")
    lines.append(f"Contradictions: {stats['contradictions']}")
    lines.append(f"Severity disagreements: {stats['severity_disagreements']}")
    n = stats.get("domain_improvements")
    if n is not None:
        if n:
            lines.append(
                f"{n} domain-improvement opportunities captured; run apd-gauntlet "
                "draft-domain-improvements <run> to draft pack edits."
            )
        else:
            lines.append("0 domain-improvement opportunities captured.")
    return "\n".join(lines)
