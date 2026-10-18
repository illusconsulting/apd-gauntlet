"""The ``findings`` evaluator: a run's findings scored against reviewed labels.

``eval label-template`` writes one ``unreviewed`` item per finding of a run. A
reviewer sets each verdict: ``true_positive`` for a real finding (correcting its
goal or severity where the run got them wrong) or ``false_positive``, and may add
true positives the run missed.

Scoring takes two passes of ``match_records``, the matcher ``compare-runs`` uses.
Pass 1 matches the true positives (gold) to the run's findings: a matched pair is
a TP, counted under the gold goal (matching requires the run goal to equal it),
and an unmatched gold item is an FN. Pass 2 matches the false positives to the
findings pass 1 left: a matched finding is an FP, and the rest are ``unjudged``.
Each item is keyed by its ``id`` when it has one, else ``label-<index>``, so on a
tie a label copied from a finding takes that same finding.
"""
from __future__ import annotations

import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from ..measure.match import match_records
from ..measure.runs import RunLoadError, RunSnapshot, is_run_dir, load_run
from ..resources import read_schema
from .corpus import CORPUS_SCHEMA, LABELS_SCHEMA, CorpusEntry, Labels, _order, _validator
from .evaluators import EVALUATORS, EvalResult, register

NAME = "findings"
# The nine apd_goal values, in _defs.schema.json order.
GOALS: tuple[str, ...] = tuple(
    str(goal) for goal in read_schema("_defs.schema.json")["$defs"]["apd_goal"]["enum"]
)
COUNT_KINDS: tuple[str, ...] = ("tp", "fp", "fn", "unjudged")
# A labels file's entry must be a usable corpus entry id (eval-corpus.schema.json).
_ENTRY_ID = re.compile(read_schema(CORPUS_SCHEMA)["$defs"]["slug"]["pattern"])


def _ratio(numerator: int, denominator: int) -> float | None:
    return numerator / denominator if denominator else None


def _f1(precision: float | None, recall: float | None) -> float | None:
    """The harmonic mean; ``None`` unless both are defined, 0.0 when both are 0."""
    if precision is None or recall is None:
        return None
    if precision + recall == 0:
        return 0.0
    return 2 * precision * recall / (precision + recall)


def metrics_from_counts(counts: Mapping[str, int]) -> dict[str, float | None]:
    """Precision, strict precision, recall and F1 per goal and for ``all``, then agreement.

    ``precision`` is TP/(TP+FP), ``precision_strict`` TP/(TP+FP+unjudged), ``recall``
    TP/(TP+FN), and ``severity_agreement`` ``severity_agree``/TP over all goals; a zero
    denominator gives ``None``. ``f1`` is the harmonic mean of precision and recall:
    ``None`` unless both are defined, and 0.0 when both are 0. ``all`` sums the nine
    goals; a missing count is 0 and keys outside ``<kind>.<goal>`` are ignored, so
    summed counts give corpus metrics.
    """
    rows: dict[str, tuple[int, ...]] = {
        goal: tuple(counts.get(f"{kind}.{goal}", 0) for kind in COUNT_KINDS) for goal in GOALS
    }
    rows["all"] = tuple(sum(row[i] for row in rows.values()) for i in range(len(COUNT_KINDS)))
    metrics: dict[str, float | None] = {}
    for scope, (tp, fp, _, _) in rows.items():
        metrics[f"precision.{scope}"] = _ratio(tp, tp + fp)
    for scope, (tp, fp, _, unjudged) in rows.items():
        metrics[f"precision_strict.{scope}"] = _ratio(tp, tp + fp + unjudged)
    for scope, (tp, _, fn, _) in rows.items():
        metrics[f"recall.{scope}"] = _ratio(tp, tp + fn)
    for scope in rows:
        metrics[f"f1.{scope}"] = _f1(metrics[f"precision.{scope}"], metrics[f"recall.{scope}"])
    metrics["severity_agreement"] = _ratio(counts.get("severity_agree", 0), rows["all"][0])
    return metrics


def _snapshot(run_dir: Path) -> RunSnapshot:
    """``load_run`` for a run directory; every problem is a ``ValueError`` naming it."""
    try:
        if not is_run_dir(run_dir):
            raise ValueError(f"{run_dir} is not a run directory (no .apd-run.yaml)")
        return load_run(run_dir)
    except RunLoadError as exc:
        raise ValueError(f"cannot load run {run_dir}: {exc}") from exc
    except OSError as exc:
        where = exc.filename if exc.filename is not None else run_dir
        raise ValueError(
            f"cannot load run {run_dir}: {where}: cannot read: {exc.strerror or exc}"
        ) from exc


def _keyed(labels: Labels) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    """The true- and false-positive items by key (``id``, else ``label-<index>``)."""
    gold: dict[str, dict[str, Any]] = {}
    false_positives: dict[str, dict[str, Any]] = {}
    first: dict[str, int] = {}
    for index, item in enumerate(labels.data["items"]):
        key = item.get("id", f"label-{index}")
        if key in first:
            raise ValueError(
                f"{labels.path}: duplicate label key {key!r}"
                f" ($.items[{first[key]}] and $.items[{index}])"
            )
        first[key] = index
        if item["verdict"] == "true_positive":
            gold[key] = item
        elif item["verdict"] == "false_positive":
            false_positives[key] = item
    return gold, false_positives


def _check(entry: CorpusEntry, labels: Labels) -> Path:
    """Refuse an entry or labels the evaluator cannot score; return the run directory."""
    if entry.run_dir is None:
        raise ValueError(
            f"entry {entry.id!r} has no run directory; the findings evaluator scores a run"
        )
    if labels.kind != "findings":
        raise ValueError(
            f"{labels.path}: labels of kind {labels.kind!r}; the findings evaluator needs "
            "kind 'findings'"
        )
    if labels.data["entry"] != entry.id:
        raise ValueError(
            f"{labels.path}: labels are for entry {labels.data['entry']!r}, not {entry.id!r}"
        )
    unreviewed = sum(1 for item in labels.data["items"] if item["verdict"] == "unreviewed")
    if unreviewed:
        noun = "item" if unreviewed == 1 else "items"
        raise ValueError(
            f"{labels.path}: {unreviewed} unreviewed {noun}; set each verdict to "
            "true_positive or false_positive before evaluating"
        )
    return entry.run_dir


def evaluate_findings(entry: CorpusEntry, labels: Labels) -> EvalResult:
    """Score the findings of ``entry``'s run against ``labels``; see the module docstring.

    ``ValueError`` for an entry with no run directory, labels of another kind or for
    another entry, any ``unreviewed`` item (the message gives the count), two items
    with one key, a run that is missing or fails to load, and a run finding whose
    ``apd_goal`` is not one of ``GOALS``.
    """
    run_dir = _check(entry, labels)
    gold, false_positives = _keyed(labels)
    run = _snapshot(run_dir)
    off_goal = sorted(
        f"{rid} ({finding.get('apd_goal')!r})"
        for rid, finding in run.findings.items()
        if finding.get("apd_goal") not in GOALS
    )
    if off_goal:
        raise ValueError(
            f"{run_dir}: findings with an apd_goal outside the nine goals: {', '.join(off_goal)}"
        )

    counts = {f"{kind}.{goal}": 0 for kind in COUNT_KINDS for goal in GOALS}
    counts["severity_agree"] = 0
    first = match_records(gold, run.findings, candidate_targets=run.graph_targets)
    for pair in first.matched:
        item = gold[pair.baseline_id]
        counts[f"tp.{item['apd_goal']}"] += 1
        if run.findings[pair.candidate_id].get("severity") == item["severity"]:
            counts["severity_agree"] += 1
    for key in first.missing:
        counts[f"fn.{gold[key]['apd_goal']}"] += 1

    rest = {rid: run.findings[rid] for rid in first.new}
    second = match_records(false_positives, rest, candidate_targets=run.graph_targets)
    for pair in second.matched:
        counts[f"fp.{rest[pair.candidate_id]['apd_goal']}"] += 1
    for rid in second.new:
        counts[f"unjudged.{rest[rid]['apd_goal']}"] += 1

    notes: tuple[str, ...] = ()
    if second.missing:
        n = len(second.missing)
        what = "label matches" if n == 1 else "labels match"
        notes = (
            f"{n} false_positive {what} no run finding left after the true positives: "
            + ", ".join(second.missing),
        )
    return EvalResult(
        entry.id, counts, metrics_from_counts(counts), notes, derive=metrics_from_counts
    )


def _pointer(ev: Any) -> Any:
    """An evidence item's ``artifact`` and ``locator``; a non-mapping is kept for the check."""
    if isinstance(ev, Mapping):
        return {"artifact": ev.get("artifact"), "locator": ev.get("locator")}
    return ev


def _template_item(rid: str, finding: Mapping[str, Any]) -> dict[str, Any]:
    raw = finding.get("evidence")
    return {
        "id": rid,
        "verdict": "unreviewed",
        "apd_goal": finding.get("apd_goal"),
        "severity": finding.get("severity"),
        "title": finding.get("title"),
        # Evidence that is not a list of mappings is copied as it is, so the schema
        # check names it rather than the template dropping it.
        "evidence": [_pointer(ev) for ev in raw] if isinstance(raw, list) else raw,
    }


def label_template(run_dir: Path, entry_id: str) -> dict[str, Any]:
    """A findings labels document for ``run_dir``: one ``unreviewed`` item per finding.

    Items are in id order and copy the finding's id, ``apd_goal``, ``severity``,
    title and evidence pointers (``artifact`` and ``locator``, no excerpt).
    ``ValueError`` when ``entry_id`` is not a corpus entry id, the run is missing
    or fails to load, or a finding cannot become a valid labels item (evidence that
    is not a list of mappings included).
    """
    if not _ENTRY_ID.fullmatch(entry_id):
        raise ValueError(
            f"entry id {entry_id!r} does not match {_ENTRY_ID.pattern} (a corpus entry id)"
        )
    run = _snapshot(run_dir)
    items = [_template_item(rid, run.findings[rid]) for rid in sorted(run.findings)]
    doc: dict[str, Any] = {
        "schema_version": 1, "kind": "findings", "entry": entry_id, "items": items,
    }
    errors = sorted(
        _validator(LABELS_SCHEMA).iter_errors(doc), key=lambda e: (_order(e), e.message)
    )
    problems: dict[str, None] = {}
    for err in errors:
        path = list(err.absolute_path)
        in_item = len(path) > 1 and path[0] == "items" and isinstance(path[1], int)
        where = f"finding {items[path[1]]['id']}: " if in_item else ""
        problems[f"{where}{err.json_path}: {err.message}"] = None
    if problems:
        raise ValueError(f"{run_dir}: findings that cannot be labelled: " + "; ".join(problems))
    return doc


if NAME not in EVALUATORS:  # a second import of this module registers nothing
    register(NAME, evaluate_findings)
