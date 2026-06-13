"""Deterministic manual-audit-prompts generator (no LLM).

Reads a run's ``40-synthesis/deduped-findings.yaml``, filters records with
``disposition: blocked``, and renders ``40-synthesis/manual-audit-prompts.md``
pairing each blocked finding with copy-paste audit commands drawn from a small
keyword -> command-template table. Output is byte-stable: input record order is
preserved, keyword lookup is order-deterministic, and there is no timestamp.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

# Ordered keyword -> command-template table. A finding's title+summary is scanned
# (lowercased) for each keyword in declared order; every matching template is
# emitted, deduped, in table order. Keep this table small and ordered so output
# is deterministic.
KEYWORD_COMMANDS: list[tuple[str, str]] = [
    ("networkpolicy", "kubectl get networkpolicies -A"),
    ("network policy", "kubectl get networkpolicies -A"),
    ("peerauthentication", "kubectl get peerauthentications.security.istio.io -A"),
    ("mtls", "kubectl get peerauthentications.security.istio.io -A"),
    ("istio", "istioctl proxy-config secret -n production"),
    # "secret" is intentionally broad — any finding mentioning a secret routes to
    # the istio cert inspection. False positives are low-stakes for a prompt hint.
    ("secret", "istioctl proxy-config secret -n production"),
]


def commands_for(finding: dict[str, Any]) -> list[str]:
    """Return the deduped, table-ordered command templates a finding triggers."""
    haystack = (
        str(finding.get("title", "")) + " " + str(finding.get("summary", ""))
    ).lower()
    out: list[str] = []
    for keyword, command in KEYWORD_COMMANDS:
        if keyword in haystack and command not in out:
            out.append(command)
    return out


def render_prompts(findings: list[dict[str, Any]]) -> str:
    """Render the manual-audit-prompts markdown for the blocked findings.

    Only ``disposition: blocked`` records are included; input order is preserved.
    """
    blocked = [
        f
        for f in findings
        if isinstance(f, dict) and f.get("disposition") == "blocked"
    ]
    lines: list[str] = [
        "# Manual audit prompts",
        "",
        (
            "Each blocked finding below needs a runtime signal a static review "
            "cannot provide. Run the paired command(s) against the live system "
            "and attach the output as the prerequisite evidence."
        ),
        "",
    ]
    if not blocked:
        lines.append("No blocked findings — nothing to audit manually.")
        lines.append("")
        return "\n".join(lines)

    for f in blocked:
        fid = str(f.get("id", "unknown"))
        title = str(f.get("title", "(untitled)"))
        lines.append(f"## {fid} — {title}")
        lines.append("")
        prereqs = [str(p) for p in (f.get("prerequisite_evidence") or [])]
        if prereqs:
            lines.append("**Prerequisite evidence:**")
            lines.append("")
            for p in prereqs:
                lines.append(f"- {p}")
            lines.append("")
        commands = commands_for(f)
        if commands:
            lines.append("**Suggested audit commands:**")
            lines.append("")
            lines.append("```bash")
            lines.extend(commands)
            lines.append("```")
            lines.append("")
        else:
            lines.append(
                "No infrastructure command template matched; review manually "
                "against the prerequisite evidence above."
            )
            lines.append("")
    return "\n".join(lines)


def write_prompts(run_dir: Path) -> tuple[Path, int]:
    """Read deduped-findings.yaml, render, and write manual-audit-prompts.md.

    Returns ``(output_path, blocked_count)``. Raises ``FileNotFoundError`` when
    the deduped-findings file is absent.
    """
    synth = run_dir / "40-synthesis"
    deduped = synth / "deduped-findings.yaml"
    if not deduped.is_file():
        raise FileNotFoundError(str(deduped))
    doc = yaml.safe_load(deduped.read_text(encoding="utf-8")) or {}
    findings = [f for f in (doc.get("finding") or []) if isinstance(f, dict)]
    text = render_prompts(findings)
    out_path = synth / "manual-audit-prompts.md"
    out_path.write_text(text, encoding="utf-8")
    blocked_count = sum(1 for f in findings if f.get("disposition") == "blocked")
    return out_path, blocked_count
