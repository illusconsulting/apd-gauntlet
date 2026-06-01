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


def compute_capability_id(prefix: str, title: str, first_locator: str) -> str:
    """Deterministic capability id: <prefix>-cap-<sha8(title|locator)>."""
    digest = hashlib.sha256(f"{title}|{first_locator}".encode()).hexdigest()[:8]
    return f"{prefix}-cap-{digest}"


def compute_improvement_id(
    improvement_type: str,
    target_pack: str,
    target_file: str,
    primary_ref: str,
) -> str:
    """Deterministic dimpr- id (§4.1). NOT compute_id: the key is the LOWERCASED,
    '|'-joined 4-tuple improvement_type|target_pack|target_file|evidence[0].ref,
    sha256[:8], 'dimpr-' prefix. The agent (§7.2 step 5) and the linter below both
    call this, so the at-capture id and the recomputed id are guaranteed to agree.
    """
    key = "|".join([improvement_type, target_pack, target_file, primary_ref]).lower()
    digest = hashlib.sha256(key.encode()).hexdigest()[:8]
    return f"dimpr-{digest}"


def check_domain_improvement_id(record: dict[str, Any]) -> list[str]:
    """Recompute the dimpr-<sha8> via compute_improvement_id and flag a mismatch.

    NOT a mirror of check_finding_id (which early-returns unless record['agent']
    is in _PREFIX_BY_AGENT — improvement records carry no 'agent' field). The
    primary ref is ALWAYS evidence[0].ref.
    """
    evidence = record.get("evidence") or []
    if not evidence:
        return []
    primary_ref = evidence[0].get("ref", "")
    expected = compute_improvement_id(
        record.get("improvement_type", ""),
        record.get("target_pack", ""),
        record.get("target_file", ""),
        primary_ref,
    )
    actual = record.get("id", "")
    if actual != expected:
        return [f"id mismatch: got {actual}, expected {expected} per dimpr- deterministic rule"]
    return []


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
    agent = record.get("agent") or ""
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
    agent = record.get("agent") or ""
    prefix = _PREFIX_BY_AGENT.get(agent, "")
    if not prefix:
        return []
    title = record.get("title", "")
    evidence = record.get("evidence") or []
    if not evidence:
        return []
    expected = compute_capability_id(prefix, title, evidence[0].get("locator", ""))
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
            unique = sorted({h.lower() for h in hits})
            warnings.append(f"mitre_attack[{i}].rationale uses hedge words: {unique}")
    return warnings


def check_d3fend_counters_attack(record: dict[str, Any]) -> list[str]:
    """Every d3fend.counters_attack ID on a capability must appear in the same
    capability's `mitre_attack[].technique` list — either exactly, or (for
    sub-technique IDs like ``T1110.001``) via its parent technique (``T1110``).

    The schema validates the format of `counters_attack` entries; this lint
    enforces the semantic intent: a D3FEND mapping that doesn't counter
    anything the capability itself claims to defend against is an
    evidence-discipline violation (D3FEND-by-name-similarity).

    Returns one error string per d3fend entry that has any unmatched
    `counters_attack` ID. Returns ``[]`` when no `d3fend` block is present.
    """
    errors: list[str] = []
    control_mappings = record.get("control_mappings") or {}
    d3fend_entries = control_mappings.get("d3fend") or []
    if not d3fend_entries:
        return errors
    declared_techniques: set[str] = {
        entry["technique"]
        for entry in (control_mappings.get("mitre_attack") or [])
        if isinstance(entry, dict) and "technique" in entry
    }
    for i, d3_entry in enumerate(d3fend_entries):
        if not isinstance(d3_entry, dict):
            continue
        unmatched: list[str] = []
        for counter_id in d3_entry.get("counters_attack", []) or []:
            if counter_id in declared_techniques:
                continue
            parent = counter_id.split(".", 1)[0] if "." in counter_id else None
            if parent and parent in declared_techniques:
                continue
            unmatched.append(counter_id)
        if unmatched:
            errors.append(
                f"control_mappings.d3fend[{i}] (technique="
                f"{d3_entry.get('technique')}) counters_attack {unmatched} "
                f"not in mitre_attack[].technique; D3FEND mappings require "
                f"the countered ATT&CK technique (or its parent) to also "
                f"appear in mitre_attack[]"
            )
    return errors


def _looks_like_tm_evidence(artifact: str) -> bool:
    """True if the evidence artifact field points at the normalized TM or a TM source file."""
    if artifact == "00-context/threat-model-normalized.yaml":
        return True
    tm_patterns = (
        ".tm7", ".adtool.xml", "threat-model.", "-threat-model.",
        "threat_model.",
    )
    lower = artifact.lower()
    return any(pat in lower for pat in tm_patterns)


def check_tmeval_evidence_pointer(record: dict[str, Any]) -> list[str]:
    """Every tmeval- finding must cite the normalized TM or the source artifact in evidence.

    Triggers only when ``record["id"]`` starts with ``"tmeval-"`` — non-tmeval
    findings are untouched by this check.
    """
    errors: list[str] = []
    record_id = record.get("id") or ""
    if not record_id.startswith("tmeval-"):
        return errors
    evidence = record.get("evidence") or []
    has_tm_evidence = any(
        _looks_like_tm_evidence(item.get("artifact") or "")
        for item in evidence
    )
    if not has_tm_evidence:
        errors.append(
            f"{record_id}: tmeval- findings must have at least one evidence entry "
            f"pointing at 00-context/threat-model-normalized.yaml or a recognized "
            f"threat-model artifact path. None found in {len(evidence)} evidence "
            f"entries. (missing tm evidence)"
        )
    return errors


def check_tmeval_contradiction_cross_reference(record: dict[str, Any]) -> list[str]:
    """Every tmeval- finding with disposition: risk must have non-empty cross_references.

    Per Rule 6 in apd-threat-model-methodologies: contradictions cross-reference
    the specialist finding they contradict; an empty list is structurally
    incomplete (contradiction without cross_references).
    """
    errors: list[str] = []
    record_id = record.get("id") or ""
    if not record_id.startswith("tmeval-"):
        return errors
    if record.get("disposition") != "risk":
        return errors
    cross_refs = record.get("cross_references") or []
    if not cross_refs:
        errors.append(
            f"{record_id}: tmeval- contradiction (disposition: risk) must have at "
            f"least one entry in cross_references pointing to the specialist finding "
            f"it contradicts. Empty cross_references is structurally incomplete per "
            f"apd-threat-model-methodologies Rule 6."
        )
    return errors


def check_capability_maturity_evidence(
    record: dict[str, Any], tech_plan_artifacts: set[str]
) -> list[str]:
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
