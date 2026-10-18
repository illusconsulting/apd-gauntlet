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

``compare_sides`` compares two sets of runs, each side one run or the runs
``<name>-r1``, ``<name>-r2``, … that ``resolve_side`` finds. Pairwise metrics
are the median over every baseline-candidate pair; per-run metrics are the
median of each side, and a side median is ``None`` (with a reason) when any of
its runs lacks the value, so a gate never judges part of a side.
"""
from __future__ import annotations

from collections import Counter
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from statistics import median
from typing import Any

from .gates import GateOutcome
from .match import Match, MatchResult, evidence_pairs, match_records
from .runs import RunSnapshot, is_run_dir
from .usage import USAGE_RELPATH

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


# --- two sets of runs (compare-runs) -----------------------------------------------------

RUNBOOK = "docs/measuring-changes.md"

# Per-run metrics, in report order; each side's median is ``<side>_<metric>`` in values.
PER_RUN_METRICS: tuple[str, ...] = (
    "blocked_rate_pct",
    "first_pass_validator_errors",
    "lens_retries_total",
    "tier_repairs_total",
    "lens_reruns_total",
    "audit_iterations",
    "cost_usd",
    "cost_usd_all",  # agent plus decision-model cost (register A12.8)
)
# The gated attempts deltas (candidate median minus baseline median) and their metric.
ATTEMPT_DELTAS: dict[str, str] = {
    "first_pass_validator_errors_delta": "first_pass_validator_errors",
    "lens_retries_delta": "lens_retries_total",
    "tier_repairs_delta": "tier_repairs_total",  # register A9.4
    "lens_reruns_delta": "lens_reruns_total",  # register A9.4
    "audit_iterations_delta": "audit_iterations",
}
_SIDES = ("baseline", "candidate")
_LISTED_IDS = 5  # ids shown in a warning before "and N more"


class MissingRuns(Exception):
    """A side of a comparison names no run directory; the message says what was looked for."""


@dataclass(frozen=True)
class Comparison:
    baseline: tuple[RunSnapshot, ...]
    candidate: tuple[RunSnapshot, ...]
    pairs: tuple[PairDelta, ...]
    per_run: dict[str, dict[str, float | None]]
    values: dict[str, float | None]
    reasons: dict[str, str]
    warnings: tuple[str, ...]


def _is_run(path: Path) -> bool:
    try:
        return is_run_dir(path)
    except OSError as exc:  # e.g. a PermissionError from the stat call
        raise MissingRuns(f"{path}: cannot read: {exc.strerror or exc}") from exc


def resolve_side(path: Path) -> list[Path]:
    """The runs one side of a comparison names.

    ``[path]`` when ``path`` is a run directory; else ``<path>-r1``,
    ``<path>-r2``, … for as long as each is a run directory, so the first gap
    ends the list. With neither, ``MissingRuns`` names the convention and the
    runbook.
    """
    if _is_run(path):
        return [path]
    runs: list[Path] = []
    while _is_run(run := Path(f"{path}-r{len(runs) + 1}")):
        runs.append(run)
    if not runs:
        raise MissingRuns(
            f"{path} is not a run directory (no .apd-run.yaml) and {path}-r1 is not one "
            f"either; name a configuration's runs <name>-r1, <name>-r2 and pass <name> "
            f"({RUNBOOK})"
        )
    return runs


def _attempts_problem(run: RunSnapshot) -> str | None:
    if run.attempts is None:
        return (
            f"no .apd-state/attempts.yaml in {run.path} "
            "(1.7 runs and foreground drives record none)"
        )
    if run.attempts.skipped:
        return (
            f"{run.path} resumed: {len(run.attempts.skipped)} steps skipped, "
            "retries under-counted"
        )
    return None


def _problem(run: RunSnapshot, metric: str) -> str | None:
    """Why ``run`` gives no usable value for ``metric``; ``None`` when it gives one."""
    if metric == "blocked_rate_pct":
        return None if run.findings else f"{run.path} has no findings, so it has no blocked rate"
    if metric in ("cost_usd", "cost_usd_all"):
        if run.usage_totals is None:
            return f"no .apd-state/usage.yaml in {run.path} (run apd-gauntlet usage)"
        if metric not in run.usage_totals:
            return f"{run.path / USAGE_RELPATH} has no {metric}"
        return None
    return _attempts_problem(run)


def _run_values(run: RunSnapshot) -> dict[str, float | None]:
    a = run.attempts
    usage = run.usage_totals or {}
    return {
        "blocked_rate_pct": blocked_rate_pct(run),
        "first_pass_validator_errors": None if a is None else a.first_pass_validator_errors,
        "lens_retries_total": None if a is None else a.lens_retries_total,
        "tier_repairs_total": None if a is None else a.tier_repairs_total,
        "lens_reruns_total": None if a is None else a.lens_reruns_total,
        "audit_iterations": None if a is None else a.audit_iterations,
        "cost_usd": usage.get("cost_usd"),
        "cost_usd_all": usage.get("cost_usd_all"),
    }


def _joined(reasons: Iterable[str | None]) -> str:
    return "; ".join(dict.fromkeys(r for r in reasons if r))


def _listed(ids: Sequence[str]) -> str:
    shown = ", ".join(ids[:_LISTED_IDS])
    more = len(ids) - _LISTED_IDS
    return f"{shown} and {more} more" if more > 0 else shown


def _warnings(
    runs: Sequence[RunSnapshot], pairs: Sequence[PairDelta], excused: frozenset[str]
) -> list[str]:
    warnings: list[str] = []
    lost = {x.id for p in pairs for x in p.lost_critical_high}
    for rid in sorted(excused - lost):
        warnings.append(
            f"excused finding {rid} is not a lost critical or high finding in any pair; "
            "it excuses nothing"
        )
    for run in runs:
        odd = sorted(
            rid for rid, rec in run.findings.items()
            if _level(rec, "severity") not in SEVERITY_ORDER
        )
        if odd:
            warnings.append(
                f"{run.path}: {len(odd)} findings have a severity outside "
                f"{', '.join(SEVERITY_ORDER)} ({_listed(odd)}); a lost one never counts "
                "as a lost critical or high finding"
            )
    for run in runs:
        if run.inputs_sha256 is None:
            warnings.append(
                f"{run.path} has no inputs/, so it cannot be checked against the other "
                "runs' inputs"
            )
    return warnings


def compare_sides(
    baseline: Sequence[RunSnapshot],
    candidate: Sequence[RunSnapshot],
    *,
    excused: frozenset[str] = frozenset(),
) -> Comparison:
    """Compare every baseline run with every candidate run, and take the medians.

    ``unexcused_lost_critical_high`` and ``severity_agreement_pct`` are the
    median over all pairs (pairs without a value are dropped; ``None`` when no
    pair has one). Each per-run metric gets a median per side,
    ``baseline_<metric>`` and ``candidate_<metric>``, which is ``None`` when a
    run of that side has no usable value: no findings, no attempts file or a
    resumed run (attempts metrics), or no usage file. Then
    ``blocked_rate_abs_delta_pts`` is ``|candidate - baseline|`` and each of
    ``ATTEMPT_DELTAS`` is ``candidate - baseline``, ``None`` when either median
    is. ``reasons`` explains every ``None`` value, so ``evaluate`` can pass it
    on. ``excused`` holds finding ids whose loss the operator accepted. Each side
    needs at least one run and no run may be listed twice (``ValueError``);
    inputs and empty runs are the caller's checks.
    """
    runs = (*baseline, *candidate)
    if not baseline or not candidate:
        raise ValueError("each side of a comparison needs at least one run")
    seen: set[str] = set()
    for run in runs:
        if str(run.path) in seen:
            raise ValueError(f"run {run.path} is listed twice")
        seen.add(str(run.path))

    pairs = tuple(compare_pair(b, c, excused=excused) for b in baseline for c in candidate)
    per_run = {str(run.path): _run_values(run) for run in runs}
    sides = {"baseline": tuple(baseline), "candidate": tuple(candidate)}

    medians: dict[str, float | None] = {}
    reasons: dict[str, str] = {}
    for metric in PER_RUN_METRICS:
        for side in _SIDES:
            key = f"{side}_{metric}"
            problem = _joined(_problem(run, metric) for run in sides[side])
            if problem:
                medians[key] = None
                reasons[key] = problem
            else:
                found = [per_run[str(run.path)][metric] for run in sides[side]]
                medians[key] = float(median(v for v in found if v is not None))

    def delta(name: str, metric: str, fn: Callable[[float], float]) -> float | None:
        b, c = medians[f"baseline_{metric}"], medians[f"candidate_{metric}"]
        if b is None or c is None:
            reasons[name] = _joined(reasons.get(f"{side}_{metric}") for side in _SIDES)
            return None
        return fn(c - b)

    values: dict[str, float | None] = {
        "unexcused_lost_critical_high": float(median(unexcused_lost(p) for p in pairs)),
    }
    agreement = [p.severity_agreement_pct for p in pairs if p.severity_agreement_pct is not None]
    values["severity_agreement_pct"] = float(median(agreement)) if agreement else None
    if not agreement:
        reasons["severity_agreement_pct"] = "no pair has a matched finding"
    values["blocked_rate_abs_delta_pts"] = delta(
        "blocked_rate_abs_delta_pts", "blocked_rate_pct", abs
    )
    for name, metric in ATTEMPT_DELTAS.items():
        values[name] = delta(name, metric, lambda d: d)
    values.update(medians)

    return Comparison(
        baseline=tuple(baseline),
        candidate=tuple(candidate),
        pairs=pairs,
        per_run=per_run,
        values=values,
        reasons={k: reasons[k] for k in values if k in reasons},
        warnings=tuple(_warnings(runs, pairs, excused)),
    )


# --- rendering ---------------------------------------------------------------------------


def _match_json(m: MatchResult) -> dict[str, Any]:
    return {
        "matched": [
            {
                "baseline": x.baseline_id,
                "candidate": x.candidate_id,
                "title_similarity": x.title_similarity,
                "asset_similarity": x.asset_similarity,
            }
            for x in m.matched
        ],
        "missing": list(m.missing),
        "new": list(m.new),
    }


def _pair_json(p: PairDelta) -> dict[str, Any]:
    return {
        "baseline": str(p.baseline),
        "candidate": str(p.candidate),
        "findings": _match_json(p.findings),
        "capabilities": _match_json(p.capabilities),
        "missing_by_severity": dict(p.missing_by_severity),
        "new_by_severity": dict(p.new_by_severity),
        "severity_shifts": dict(p.severity_shifts),
        "severity_agreement_pct": p.severity_agreement_pct,
        "lost_critical_high": [
            {"id": x.id, "severity": x.severity, "title": x.title, "excuse": x.excuse}
            for x in p.lost_critical_high
        ],
        "unexcused_lost_critical_high": unexcused_lost(p),
        "maturity_shifts": dict(p.maturity_shifts),
        "headline_overlap_pct": p.headline_overlap_pct,
    }


def _gate_json(o: GateOutcome) -> dict[str, Any]:
    return {
        "id": o.gate.id,
        "text": o.gate.text,
        "status": o.status,
        "checks": [{"metric": c.metric, "op": c.op, "value": c.value} for c in o.gate.checks],
        "values": dict(o.values),
        "reason": o.reason,
        "excuse": o.excuse,
    }


def comparison_json(
    c: Comparison, outcomes: Sequence[GateOutcome] | None, status: str
) -> dict[str, Any]:
    """The comparison as JSON-ready data; ``runs`` is keyed by each run's path as given.

    ``gates`` is empty when no gates were applied (``status`` ``delta_only``).
    """
    return {
        "status": status,
        "baseline": [str(r.path) for r in c.baseline],
        "candidate": [str(r.path) for r in c.candidate],
        "pairs": [_pair_json(p) for p in c.pairs],
        "runs": {path: dict(values) for path, values in c.per_run.items()},
        "values": dict(c.values),
        "gates": [_gate_json(o) for o in outcomes or ()],
        "warnings": list(c.warnings),
    }


_STATUS_TEXT = {"pass": "PASS", "fail": "FAIL", "not_available": "NOT AVAILABLE"}


def _fmt(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.6g}"


def _counted(counts: Mapping[str, int]) -> str:
    return ", ".join(f"{level} {n}" for level, n in counts.items())


def _runs(n: int, side: str) -> str:
    return f"{n} {side} run" + ("" if n == 1 else "s")


def _pair_line(p: PairDelta) -> str:
    f, cap = p.findings, p.capabilities
    missing = f"{len(f.missing)} missing" + (
        f" ({_counted(p.missing_by_severity)})" if f.missing else ""
    )
    new = f"{len(f.new)} new" + (f" ({_counted(p.new_by_severity)})" if f.new else "")
    overlap = "n/a" if p.headline_overlap_pct is None else f"{p.headline_overlap_pct:.1f}%"
    return (
        f"  {p.baseline} -> {p.candidate}: findings {len(f.matched)} matched, {missing}, {new}; "
        f"severity shifts {_counted(p.severity_shifts) or 'none'}; "
        f"capabilities {len(cap.matched)} matched, {len(cap.missing)} missing, "
        f"{len(cap.new)} new; maturity shifts {_counted(p.maturity_shifts) or 'none'}; "
        f"headline overlap {overlap}"
    )


def _gate_line(o: GateOutcome) -> str:
    label = f"EXCUSED ({o.excuse})" if o.status == "excused" else _STATUS_TEXT[o.status]
    checks = ", ".join(
        f"{c.metric} {_fmt(o.values.get(c.metric))} {c.op} {c.value:g}" for c in o.gate.checks
    )
    line = f"  {label}  {o.gate.id}: {o.gate.text} [{checks}]"
    return f"{line}; {o.reason}" if o.reason else line


def _result_line(outcomes: Sequence[GateOutcome] | None, status: str) -> str:
    parts = []
    for word, kind in (("failed", "fail"), ("not available", "not_available"),
                       ("excused", "excused")):
        ids = [o.gate.id for o in outcomes or () if o.status == kind]
        if ids:
            parts.append(f"{word}: {', '.join(ids)}")
    return f"RESULT: {status}" + (f" ({'; '.join(parts)})" if parts else "")


def _missing_data(c: Comparison) -> list[str]:
    """Each distinct reason a value is ``None``, once: the pairwise one, then per run."""
    found = [c.reasons["severity_agreement_pct"]] if "severity_agreement_pct" in c.reasons else []
    for run in (*c.baseline, *c.candidate):
        found.extend(p for p in (_problem(run, m) for m in PER_RUN_METRICS) if p)
    return list(dict.fromkeys(found))


def render_text(c: Comparison, outcomes: Sequence[GateOutcome] | None, status: str) -> str:
    """The text report: runs, one line per pair with its lost findings, values, gates, result.

    Each distinct reason for a missing value is listed once under ``missing
    data``, and each unavailable gate repeats its own. The last line is
    ``RESULT: <status>``, followed by the failed, unavailable and excused gate
    ids when there are any.
    """
    lines = [
        f"compare-runs: {_runs(len(c.baseline), 'baseline')}, "
        f"{_runs(len(c.candidate), 'candidate')}"
    ]
    for side, runs in (("baseline", c.baseline), ("candidate", c.candidate)):
        lines.append(f"{side}:")
        for run in runs:
            v = c.per_run[str(run.path)]
            lines.append(
                f"  {run.path}: {len(run.findings)} findings, {len(run.capabilities)} "
                f"capabilities, blocked {_fmt(v['blocked_rate_pct'])}%, "
                f"cost_usd {_fmt(v['cost_usd'])}"
            )
    lines.append("pairs:")
    for p in c.pairs:
        lines.append(_pair_line(p))
        for x in p.lost_critical_high:
            excuse = "not excused" if x.excuse is None else f"excused: {x.excuse}"
            lines.append(f"    lost {x.severity} {x.id} ({excuse}): {x.title}")
    lines.append("values:")
    lines.extend(f"  {key}: {_fmt(value)}" for key, value in c.values.items())
    missing = _missing_data(c)
    if missing:
        lines.append("missing data:")
        lines.extend(f"  {m}" for m in missing)
    if outcomes is not None:
        lines.append("gates:")
        lines.extend(_gate_line(o) for o in outcomes)
    lines.extend(f"warning: {w}" for w in c.warnings)
    lines.append(_result_line(outcomes, status))
    return "\n".join(lines)
