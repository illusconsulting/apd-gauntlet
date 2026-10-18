"""The pairwise delta between a baseline run and a candidate run.

Findings and capabilities are matched one to one with ``match_records`` (same goal,
a shared derived asset, title Jaccard of at least 0.5). The delta counts what went
missing and what is new by severity, the severity and maturity shifts across matched
records, how often matched findings agree on severity, which critical or high
findings were lost and whether each loss is excused, and how many baseline report
headlines the candidate kept.

A lost critical or high finding is excused as ``operator`` when its id is in
``excused``, else as ``evidence_reassigned:<id>`` when an unmatched candidate
finding or capability (one in ``findings.new`` or ``capabilities.new``) cites one of
its evidence pointers. A pointer shared with a matched record does not excuse: that
record exists in both runs, so the loss did not move anywhere.
"""
from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .match import Match, MatchResult, evidence_pairs, match_records
from .runs import RunSnapshot

SEVERITY_ORDER: tuple[str, ...] = ("informational", "low", "medium", "high", "critical")
MATURITY_ORDER: tuple[str, ...] = ("designed", "implemented", "tested", "operationalized")

_LOST_SEVERITIES = frozenset({"critical", "high"})
# The level reported for a record whose severity or maturity is missing or not a string.
_UNKNOWN = "unknown"


@dataclass(frozen=True)
class LostFinding:
    id: str
    severity: str
    title: str
    excuse: str | None  # None, "operator" or "evidence_reassigned:<candidate id>"


@dataclass(frozen=True)
class PairDelta:
    baseline: Path
    candidate: Path
    findings: MatchResult
    capabilities: MatchResult
    missing_by_severity: dict[str, int]
    new_by_severity: dict[str, int]
    severity_shifts: dict[str, int]
    severity_agreement_pct: float | None
    lost_critical_high: tuple[LostFinding, ...]
    maturity_shifts: dict[str, int]
    headline_overlap_pct: float | None


def _level(record: Mapping[str, Any], key: str) -> str:
    value = record.get(key)
    return value if isinstance(value, str) else _UNKNOWN


def _rank(order: tuple[str, ...], level: str) -> tuple[int, int, str]:
    """Sort key: the highest level of ``order`` first, levels outside it last by name."""
    if level in order:
        return (0, -order.index(level), "")
    return (1, 0, level)


def _counts(levels: Iterable[str], order: tuple[str, ...]) -> dict[str, int]:
    counts = Counter(levels)
    return {lv: counts[lv] for lv in sorted(counts, key=lambda lv: _rank(order, lv))}


def _shifts(pairs: Iterable[tuple[str, str]], order: tuple[str, ...]) -> dict[str, int]:
    """``"<from>-><to>"`` counts over the pairs whose levels differ."""
    counts = Counter((a, b) for a, b in pairs if a != b)
    keys = sorted(counts, key=lambda p: (_rank(order, p[0]), _rank(order, p[1])))
    return {f"{a}->{b}": counts[(a, b)] for a, b in keys}


def _level_pairs(
    matched: Iterable[Match],
    baseline: Mapping[str, Mapping[str, Any]],
    candidate: Mapping[str, Mapping[str, Any]],
    key: str,
) -> list[tuple[str, str]]:
    return [
        (_level(baseline[m.baseline_id], key), _level(candidate[m.candidate_id], key))
        for m in matched
    ]


def _pointers(record: Mapping[str, Any]) -> frozenset[tuple[str, str]]:
    """The record's evidence pairs that name both an artifact and a locator.

    A pair with either part empty points at nothing (the finding schema requires
    both), so it never excuses a loss.
    """
    return frozenset((a, loc) for a, loc in evidence_pairs(record) if a and loc)


def _excuse(
    rid: str,
    record: Mapping[str, Any],
    excused: frozenset[str],
    new_pointers: list[tuple[str, frozenset[tuple[str, str]]]],
) -> str | None:
    if rid in excused:
        return "operator"
    lost = _pointers(record)
    for new_id, pointers in new_pointers:
        if lost & pointers:
            return f"evidence_reassigned:{new_id}"
    return None


def _headline_overlap(
    baseline: RunSnapshot, candidate: RunSnapshot, matched: Iterable[Match]
) -> float | None:
    """Percent of baseline headlines whose matched candidate ids meet a candidate headline."""
    if not baseline.headlines or not candidate.headlines:
        return None
    to_candidate = {m.baseline_id: m.candidate_id for m in matched}
    retained = 0
    for headline in baseline.headlines:
        mapped = {to_candidate[i] for i in headline if i in to_candidate}
        if any(mapped & expanded for expanded in candidate.headlines):
            retained += 1
    return 100 * retained / len(baseline.headlines)


def compare_pair(
    baseline: RunSnapshot,
    candidate: RunSnapshot,
    *,
    excused: frozenset[str] = frozenset(),
) -> PairDelta:
    """Compute the delta from ``baseline`` to ``candidate``.

    ``excused`` holds baseline finding ids whose loss the operator has accepted.
    """
    findings = match_records(
        baseline.findings,
        candidate.findings,
        baseline_targets=baseline.graph_targets,
        candidate_targets=candidate.graph_targets,
    )
    capabilities = match_records(
        baseline.capabilities,
        candidate.capabilities,
        baseline_targets=baseline.graph_targets,
        candidate_targets=candidate.graph_targets,
    )

    severities = _level_pairs(findings.matched, baseline.findings, candidate.findings, "severity")
    agreeing = sum(1 for a, b in severities if a == b)
    agreement = 100 * agreeing / len(severities) if severities else None

    # Unmatched candidate records, findings before capabilities, each in id order, so
    # the first one citing a lost finding's evidence is the same on every run.
    new_pointers = [(rid, _pointers(candidate.findings[rid])) for rid in findings.new] + [
        (rid, _pointers(candidate.capabilities[rid])) for rid in capabilities.new
    ]
    lost: list[LostFinding] = []
    for rid in findings.missing:
        record = baseline.findings[rid]
        severity = _level(record, "severity")
        if severity not in _LOST_SEVERITIES:
            continue
        title = record.get("title")
        lost.append(
            LostFinding(
                id=rid,
                severity=severity,
                title=title if isinstance(title, str) else "",
                excuse=_excuse(rid, record, excused, new_pointers),
            )
        )
    lost.sort(key=lambda x: (_rank(SEVERITY_ORDER, x.severity), x.id))

    return PairDelta(
        baseline=baseline.path,
        candidate=candidate.path,
        findings=findings,
        capabilities=capabilities,
        missing_by_severity=_counts(
            (_level(baseline.findings[rid], "severity") for rid in findings.missing),
            SEVERITY_ORDER,
        ),
        new_by_severity=_counts(
            (_level(candidate.findings[rid], "severity") for rid in findings.new),
            SEVERITY_ORDER,
        ),
        severity_shifts=_shifts(severities, SEVERITY_ORDER),
        severity_agreement_pct=agreement,
        lost_critical_high=tuple(lost),
        maturity_shifts=_shifts(
            _level_pairs(
                capabilities.matched, baseline.capabilities, candidate.capabilities, "maturity"
            ),
            MATURITY_ORDER,
        ),
        headline_overlap_pct=_headline_overlap(baseline, candidate, findings.matched),
    )


def blocked_rate_pct(run: RunSnapshot) -> float | None:
    """Percent of the run's findings whose disposition is ``blocked``; ``None`` with none."""
    if not run.findings:
        return None
    blocked = sum(1 for r in run.findings.values() if r.get("disposition") == "blocked")
    return 100 * blocked / len(run.findings)


def unexcused_lost(delta: PairDelta) -> int:
    """The number of lost critical or high findings with no excuse."""
    return sum(1 for x in delta.lost_critical_high if x.excuse is None)
