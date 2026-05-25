"""Semantic lints — checks JSON Schema cannot express."""
from __future__ import annotations
import hashlib
import re
from typing import Any

HEDGE_WORDS = re.compile(r"\b(could|may|potentially)\b", re.IGNORECASE)

_PREFIX_BY_AGENT = {
    "confidentiality": "conf", "integrity": "intg", "availability": "avail",
    "distributed": "dist", "resilient": "resil", "ephemeral": "ephem",
    "authenticity": "auth", "non_repudiation": "nonrep", "immutability": "immut",
    "synthesizer": "merged",
}


def compute_id(prefix: str, title: str, first_locator: str) -> str:
    """Deterministic id: first 8 hex chars of SHA-256 over title + '|' + locator."""
    payload = f"{title}|{first_locator}".encode()
    digest = hashlib.sha256(payload).hexdigest()[:8]
    return f"{prefix}-{digest}"


def check_excerpt_length(record: dict[str, Any]) -> list[str]:
    """Each excerpt must be <= 25 whitespace-separated tokens."""
    errors: list[str] = []
    for i, ev in enumerate(record.get("evidence", [])):
        excerpt = ev.get("excerpt", "")
        n = len(excerpt.split())
        if n > 25:
            errors.append(f"evidence[{i}].excerpt has {n} tokens (max 25)")
    return errors


def check_finding_id(record: dict[str, Any]) -> list[str]:
    """Finding ID must equal sha8(title + '|' + first_evidence_locator)."""
    agent = record.get("agent")
    prefix = _PREFIX_BY_AGENT.get(agent, "")
    if not prefix:
        return []
    title = record.get("title", "")
    evidence = record.get("evidence") or []
    if not evidence:
        return []
    expected = compute_id(prefix, title, evidence[0].get("locator", ""))
    actual = record.get("id", "")
    if actual != expected:
        return [f"id mismatch: got {actual}, expected {expected} per deterministic rule"]
    return []


def check_capability_id(record: dict[str, Any]) -> list[str]:
    """Capability ID must equal sha8(...) with -cap- infix."""
    agent = record.get("agent")
    prefix = _PREFIX_BY_AGENT.get(agent, "")
    if not prefix:
        return []
    title = record.get("title", "")
    evidence = record.get("evidence") or []
    if not evidence:
        return []
    payload = f"{title}|{evidence[0].get('locator', '')}".encode()
    digest = hashlib.sha256(payload).hexdigest()[:8]
    expected = f"{prefix}-cap-{digest}"
    actual = record.get("id", "")
    if actual != expected:
        return [f"id mismatch: got {actual}, expected {expected} per deterministic rule"]
    return []


def check_hedge_words_in_attack_rationale(record: dict[str, Any]) -> list[str]:
    """WARNING-level: rationale shouldn't contain hedge words."""
    warnings: list[str] = []
    for i, entry in enumerate(record.get("control_mappings", {}).get("mitre_attack", [])):
        rationale = entry.get("rationale", "")
        hits = HEDGE_WORDS.findall(rationale)
        if hits:
            warnings.append(f"mitre_attack[{i}].rationale uses hedge words: {sorted(set(h.lower() for h in hits))}")
    return warnings


def check_capability_maturity_evidence(record: dict[str, Any], tech_plan_artifacts: set[str]) -> list[str]:
    """Capability maturity >= implemented requires at least one non-tech-plan evidence entry."""
    if record.get("maturity") not in {"implemented", "tested", "operationalized"}:
        return []
    if not tech_plan_artifacts:
        return []
    non_tech_plan = [
        ev for ev in record.get("evidence", [])
        if ev.get("artifact") not in tech_plan_artifacts
    ]
    if not non_tech_plan:
        return [f"maturity={record['maturity']} requires non-tech-plan evidence; "
                f"only tech-plan artifacts present"]
    return []
