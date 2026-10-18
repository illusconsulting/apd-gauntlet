"""Decision thresholds calibrated on labelled decision records (registry R8).

A decision task writes one record per run under ``<run>/40-synthesis/decisions/``
with an answer per item. A *value spec* turns an item's answers, and the finding
the item is about, into one number, and says on which side of a threshold an
item falls in the selected class: ``below`` for finding-QA flags (a flag fires
when the value is below the threshold), ``above`` for auto-decisions. A dev
labels file (``eval-labels`` of kind ``decisions``) marks items ``gold: true``
when they belong to that class.

``choose_threshold`` places candidate cuts at the midpoints of consecutive
distinct values, so no labelled value sits on a cut and a strict and an
inclusive comparison classify the labelled set alike. It takes the cut with the
highest recall among those with at least ``min_support`` predicted positives and
precision at or above the target, then the highest precision. ``write_threshold``
records the result in ``thresholds.yaml`` with the labels' hash and the
provider, model and weights revision of the records, because a threshold holds
only for the model it was calibrated on (register A12.6).
"""
from __future__ import annotations

import itertools
import math
import os
import re
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal

import yaml

from .. import resources
from ..measure.runs import RunLoadError, _load_corpus
from .corpus import Labels

Direction = Literal["above", "below"]
DIRECTIONS: tuple[str, ...] = ("above", "below")
# A threshold key: a decision task, optionally with one flag (eval-labels.schema.json).
KEY_PATTERN = re.compile(r"[a-z][a-z0-9-]*(\.[a-z][a-z0-9_]*)?")
HEADER = (
    "# Decision thresholds (registry R8), read by the decision tasks. Keys are <task> or\n"
    "# <task>.<flag>. 'apd-gauntlet calibrate' writes each entry from dev labels: threshold,\n"
    "# precision, recall, n, labels_sha256, provider, model, weights_revision and\n"
    "# calibrated: true. Proposal entries ship as calibrated: false (amendment A1) and never\n"
    "# decide on their own. A changed entry is a changed tunable, so run\n"
    "# 'apd-gauntlet eval freeze' before any held-out run (ADR-0028).\n"
)
_DECISIONS_PARTS = ("40-synthesis", "decisions")


class CalibrationError(Exception):
    """Labels, records or a thresholds file cannot give a calibration; the message says why."""


@dataclass(frozen=True)
class ValueSpec:
    task: str
    direction: Direction
    value: Callable[[Mapping[str, Any], Mapping[str, Any] | None], float | None]


@dataclass(frozen=True)
class Calibration:
    threshold: float | None
    precision: float | None
    recall: float | None
    n: int
    feasible: bool
    best_precision: float | None


def _number(value: Any) -> float | None:
    """``value`` as a float when it is a finite real number (not a bool), else ``None``."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    result = float(value)
    return result if math.isfinite(result) else None


def _answer(item: Mapping[str, Any], question: str) -> Mapping[str, Any] | None:
    answers = item.get("answers")
    answer = answers.get(question) if isinstance(answers, Mapping) else None
    return answer if isinstance(answer, Mapping) else None


def _unsupported(item: Mapping[str, Any], _finding: Mapping[str, Any] | None) -> float | None:
    """P(the cited excerpts support the claim): ``answers.excerpt_supports_claim.p``."""
    answer = _answer(item, "excerpt_supports_claim")
    return None if answer is None else _number(answer.get("p"))


def _lens_drift(item: Mapping[str, Any], finding: Mapping[str, Any] | None) -> float | None:
    """P(the finding's own goal): ``answers.goal.probabilities[finding.apd_goal]``."""
    answer = _answer(item, "goal")
    goal = finding.get("apd_goal") if finding is not None else None
    probabilities = answer.get("probabilities") if answer is not None else None
    if not isinstance(goal, str) or not isinstance(probabilities, Mapping):
        return None
    return _number(probabilities.get(goal))


# finding-qa.severity_delta depends on LA1's score scale, so LA1 registers it.
VALUE_SPECS: dict[str, ValueSpec] = {
    "finding-qa.unsupported": ValueSpec("finding-qa", "below", _unsupported),
    "finding-qa.lens_drift": ValueSpec("finding-qa", "below", _lens_drift),
}


def register_value(key: str, spec: ValueSpec) -> None:
    """Register ``spec`` under ``key`` (``<task>`` or ``<task>.<flag>``).

    ``ValueError`` when the key is taken or malformed, its task part is not
    ``spec.task``, or the direction is neither ``above`` nor ``below``.
    """
    if not KEY_PATTERN.fullmatch(key):
        raise ValueError(f"value key {key!r} does not match {KEY_PATTERN.pattern}")
    if key.split(".", 1)[0] != spec.task:
        raise ValueError(f"value key {key!r} is not a key of task {spec.task!r}")
    if spec.direction not in DIRECTIONS:
        raise ValueError(f"direction {spec.direction!r} is neither above nor below")
    if key in VALUE_SPECS:
        raise ValueError(f"value key {key!r} is already registered")
    VALUE_SPECS[key] = spec


def _known_keys() -> str:
    return ", ".join(sorted(VALUE_SPECS)) or "none"


def unknown_key_message(key: str) -> str:
    return f"no value spec for {key!r}; known keys: {_known_keys()}"


def choose_threshold(
    pairs: Sequence[tuple[float, bool]],
    *,
    direction: Direction,
    target_precision: float,
    min_support: int = 10,
) -> Calibration:
    """The threshold over ``(value, gold)`` pairs that maximises recall at the target precision.

    See the module docstring for the cuts and the choice. ``n`` is the number of
    pairs. ``best_precision`` is the highest precision among cuts with at least
    ``min_support`` predicted positives, or ``None`` when no cut has that many.
    Without a feasible cut, ``threshold``, ``precision`` and ``recall`` are
    ``None``. ``CalibrationError`` when no pair is a gold positive; ``ValueError``
    for a bad argument or a value that is not a finite number.
    """
    if direction not in DIRECTIONS:
        raise ValueError(f"direction {direction!r} is neither above nor below")
    if not 0 < target_precision <= 1:  # NaN fails too
        raise ValueError(f"target_precision {target_precision!r} is not in (0, 1]")
    if min_support < 1:
        raise ValueError(f"min_support {min_support!r} is below 1")
    if not all(math.isfinite(v) for v, _ in pairs):
        raise ValueError("every value must be a finite number")
    gold_total = sum(1 for _, gold in pairs if gold)
    if gold_total == 0:
        raise CalibrationError("no gold positive among the labelled items, so recall is undefined")
    values = sorted({v for v, _ in pairs})
    best: tuple[float, float, float] | None = None  # (recall, precision, threshold)
    best_precision: float | None = None
    for lo, hi in itertools.pairwise(values):
        cut = lo + (hi - lo) / 2
        if not lo < cut < hi:  # adjacent floats: no cut separates them
            continue
        chosen = [gold for v, gold in pairs if (v > cut if direction == "above" else v < cut)]
        if len(chosen) < min_support:
            continue
        precision = sum(chosen) / len(chosen)
        recall = sum(chosen) / gold_total
        best_precision = precision if best_precision is None else max(best_precision, precision)
        if precision >= target_precision:
            rounded = round(cut, 6)
            threshold = rounded if lo < rounded < hi else cut
            if best is None or (recall, precision) > best[:2]:
                best = (recall, precision, threshold)
    if best is None:
        return Calibration(None, None, None, len(pairs), False, best_precision)
    recall, precision, threshold = best
    return Calibration(threshold, precision, recall, len(pairs), True, best_precision)


def _decisions(labels: Labels) -> None:
    if labels.kind != "decisions":
        raise CalibrationError(f"{labels.path}: labels of kind {labels.kind}, not decisions")


def _resolve(labels: Labels, index: int, raw: str) -> Path:
    try:
        return (labels.path.parent / raw).resolve()
    except (OSError, RuntimeError) as exc:  # RuntimeError: a link loop before 3.13
        raise CalibrationError(
            f"{labels.path}: $.records[{index}].path: cannot resolve {raw}: {exc}"
        ) from exc


def _read_record(path: Path) -> dict[str, Any]:
    """Parse a decision record; it must be a mapping. Problems name the file."""
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise CalibrationError(f"{path}: not UTF-8 text: {exc}") from exc
    except OSError as exc:
        raise CalibrationError(f"{path}: cannot read: {exc.strerror or exc}") from exc
    try:
        doc = yaml.safe_load(text)
    except (yaml.YAMLError, ValueError) as exc:  # ValueError: e.g. an impossible date
        raise CalibrationError(f"{path}: invalid YAML: {exc}") from exc
    except RecursionError as exc:
        raise CalibrationError(f"{path}: invalid YAML: nested too deeply to parse") from exc
    if not isinstance(doc, dict):
        raise CalibrationError(f"{path}: top level is a {type(doc).__name__}, not a mapping")
    return doc


@dataclass(frozen=True)
class _Record:
    path: Path
    doc: dict[str, Any]


def _records(labels: Labels) -> list[tuple[int, _Record]]:
    """Each ``records[]`` entry of ``labels`` with its parsed record, read once per file."""
    _decisions(labels)
    cache: dict[Path, _Record] = {}
    out: list[tuple[int, _Record]] = []
    for index, entry in enumerate(labels.data["records"]):
        path = _resolve(labels, index, entry["path"])
        if path not in cache:
            cache[path] = _Record(path, _read_record(path))
        out.append((index, cache[path]))
    return out


def _model_field(record: _Record, field: str) -> str:
    value = record.doc.get(field)
    if not isinstance(value, str) or not value:
        raise CalibrationError(
            f"{record.path}: {field} must be a non-empty string to key a threshold,"
            f" not {_short(value)}"
        )
    return value


def _weights_revision(record: _Record) -> str | None:
    value = record.doc.get("weights_revision")
    if value is not None and (not isinstance(value, str) or not value):
        raise CalibrationError(
            f"{record.path}: weights_revision must be a non-empty string or null,"
            f" not {_short(value)}"
        )
    return value


def _describe(model: tuple[str, str, str | None]) -> str:
    provider, name, revision = model
    return f"{provider}/{name}" + (f" (weights_revision {revision})" if revision else "")


def record_model(labels: Labels) -> tuple[str, str, str | None]:
    """The ``(provider, model, weights_revision)`` every labelled record shares.

    ``weights_revision`` is ``None`` for a record without one. ``CalibrationError``
    when a record lacks a provider or model, or when the records mix models
    (register A12.6); the message names a record for each model.
    """
    first: dict[tuple[str, str, str | None], Path] = {}
    for _, record in _records(labels):
        model = (
            _model_field(record, "provider"),
            _model_field(record, "model"),
            _weights_revision(record),
        )
        first.setdefault(model, record.path)
    if len(first) > 1:
        listed = "; ".join(f"{_describe(m)} in {path}" for m, path in first.items())
        raise CalibrationError(
            f"labelled records mix models: {listed}; calibrate each model on its own labels"
        )
    if not first:  # the labels schema requires at least one record
        raise CalibrationError(f"{labels.path}: no records")
    return next(iter(first))


def _run_dir(record: _Record) -> Path:
    """``<run>`` for a record at ``<run>/40-synthesis/decisions/<file>``."""
    parents = record.path.parents
    if len(parents) < 3 or (parents[1].name, parents[0].name) != _DECISIONS_PARTS:
        raise CalibrationError(
            f"{record.path}: not a decision record of a run "
            "(expected <run>/40-synthesis/decisions/<file>)"
        )
    return parents[2]


def _run_findings(run_dir: Path) -> dict[str, dict[str, Any]]:
    """The run's findings by id: ``load_corpus(run_dir, include_attack_path=True)``."""
    try:
        findings, _ = _load_corpus(run_dir)
    except RunLoadError as exc:
        raise CalibrationError(f"cannot load the findings of run {run_dir}: {exc}") from exc
    except OSError as exc:
        raise CalibrationError(
            f"cannot load the findings of run {run_dir}: {exc.filename or run_dir}: "
            f"{exc.strerror or exc}"
        ) from exc
    return findings


def _items_by_ref(record: _Record, task: str) -> dict[str, Mapping[str, Any]]:
    record_task = record.doc.get("task")
    if not isinstance(record_task, str):
        raise CalibrationError(f"{record.path}: no task, so it is not a {task} record")
    if record_task != task:
        raise CalibrationError(f"{record.path}: a {record_task} record, not {task}")
    items = record.doc.get("items")
    if not isinstance(items, list):
        raise CalibrationError(f"{record.path}: items is not a list")
    by_ref: dict[str, Mapping[str, Any]] = {}
    first: dict[str, int] = {}
    for index, item in enumerate(items):
        if not isinstance(item, Mapping):
            raise CalibrationError(f"{record.path}: $.items[{index}] is not a mapping")
        ref = item.get("ref")
        if not isinstance(ref, str):
            raise CalibrationError(f"{record.path}: $.items[{index}].ref is not a string")
        if ref in first:
            raise CalibrationError(
                f"{record.path}: $.items[{index}]: ref {ref!r} appears twice"
                f" ($.items[{first[ref]}] and $.items[{index}])"
            )
        first[ref] = index
        by_ref[ref] = item
    return by_ref


def _short(value: Any) -> str:
    text = repr(value)
    return text if len(text) <= 60 else text[:60] + "..."


def labelled_pairs(labels: Labels, key: str) -> tuple[list[tuple[float, bool]], int]:
    """``(value, gold)`` for each labelled item, in label order, and the number skipped.

    Record paths are relative to the labels file. Each record's ``task`` must be
    the part of ``key`` before the first ``.``, and every labelled ``ref`` must be
    one of its items. An item with ``outcome: error`` or no value is skipped. The
    finding passed to the value spec comes from the record's run, loaded once per
    run. ``CalibrationError`` names the file and JSON path of any problem: an
    unknown key, labels for another kind or key, a record that cannot be read or
    is not ``<run>/40-synthesis/decisions/<file>``, an unknown or twice-labelled
    ref, or a value that is not a finite number.
    """
    spec = VALUE_SPECS.get(key)
    if spec is None:
        raise CalibrationError(unknown_key_message(key))
    _decisions(labels)
    if labels.data["task"] != key:
        raise CalibrationError(f"{labels.path}: labels for {labels.data['task']}, not {key}")
    task = key.split(".", 1)[0]
    findings: dict[Path, dict[str, dict[str, Any]]] = {}
    indexed: dict[Path, dict[str, Mapping[str, Any]]] = {}
    seen: dict[tuple[Path, str], str] = {}
    pairs: list[tuple[float, bool]] = []
    skipped = 0
    for index, record in _records(labels):
        run_dir = _run_dir(record)
        if record.path not in indexed:
            indexed[record.path] = _items_by_ref(record, task)
        if run_dir not in findings:
            findings[run_dir] = _run_findings(run_dir)
        for j, label in enumerate(labels.data["records"][index]["items"]):
            ref, where = label["ref"], f"$.records[{index}].items[{j}]"
            if (record.path, ref) in seen:
                raise CalibrationError(
                    f"{labels.path}: {where}: ref {ref!r} of {record.path} is labelled twice"
                    f" (first at {seen[(record.path, ref)]})"
                )
            seen[(record.path, ref)] = where
            item = indexed[record.path].get(ref)
            if item is None:
                raise CalibrationError(
                    f"{labels.path}: {where}: ref {ref!r} is not an item of {record.path}"
                )
            if item.get("outcome") == "error":
                skipped += 1
                continue
            value = spec.value(item, findings[run_dir].get(ref))
            if value is None:
                skipped += 1
                continue
            number = _number(value)
            if number is None:
                raise CalibrationError(
                    f"{record.path}: item {ref!r}: the {key} value is {_short(value)},"
                    " not a finite number"
                )
            pairs.append((number, label["gold"]))
    return pairs, skipped


def _thresholds_path() -> Path:
    return resources.data_dir() / "decide" / "thresholds.yaml"


if TYPE_CHECKING:
    THRESHOLDS_PATH: Path
else:

    def __getattr__(name: str) -> Any:
        """``THRESHOLDS_PATH`` is resolved on first use, like every packaged resource."""
        if name == "THRESHOLDS_PATH":
            return _thresholds_path()
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def _read_thresholds(path: Path) -> dict[str, Any]:
    """The entries of ``path``; ``{}`` when it is missing or holds only comments."""
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return {}
    except UnicodeDecodeError as exc:
        raise CalibrationError(f"{path}: not UTF-8 text: {exc}") from exc
    except OSError as exc:
        raise CalibrationError(f"{path}: cannot read: {exc.strerror or exc}") from exc
    try:
        doc = yaml.safe_load(text)
    except (yaml.YAMLError, ValueError) as exc:
        raise CalibrationError(f"{path}: invalid YAML: {exc}") from exc
    except RecursionError as exc:
        raise CalibrationError(f"{path}: invalid YAML: nested too deeply to parse") from exc
    if doc is None:
        return {}
    if not isinstance(doc, dict):
        raise CalibrationError(f"{path}: top level is a {type(doc).__name__}, not a mapping")
    for name in doc:
        if not isinstance(name, str):
            raise CalibrationError(f"{path}: key {name!r} is not a string")
    return doc


def threshold_entry(
    cal: Calibration,
    labels_sha256: str,
    *,
    provider: str,
    model: str,
    weights_revision: str | None,
) -> dict[str, Any]:
    """The ``thresholds.yaml`` entry for a feasible calibration (precision and recall to 4 dp).

    ``ValueError`` for an infeasible calibration, which is never written.
    """
    if not cal.feasible or cal.threshold is None or cal.precision is None or cal.recall is None:
        raise ValueError("an infeasible calibration is never written")
    return {
        "threshold": cal.threshold,
        "precision": round(cal.precision, 4),
        "recall": round(cal.recall, 4),
        "n": cal.n,
        "labels_sha256": labels_sha256,
        "provider": provider,
        "model": model,
        "weights_revision": weights_revision,
        "calibrated": True,
    }


def write_threshold(
    path: Path,
    key: str,
    cal: Calibration,
    labels_sha256: str,
    *,
    provider: str,
    model: str,
    weights_revision: str | None,
) -> None:
    """Set ``key`` in ``path`` to the calibrated entry, keeping every other entry.

    The file is rewritten as ``HEADER`` plus the entries with sorted keys, via a
    temporary file and a rename. ``CalibrationError`` names the file when the
    existing one cannot be read or is not a mapping of string keys (it is left as
    it is); an ``OSError`` from the write propagates and leaves the file unchanged.
    ``ValueError`` for an infeasible calibration.
    """
    entry = threshold_entry(
        cal, labels_sha256, provider=provider, model=model, weights_revision=weights_revision
    )
    doc = _read_thresholds(path)
    doc[key] = entry
    text = HEADER + yaml.safe_dump(doc, sort_keys=True)
    tmp = path.with_name(path.name + ".tmp")
    try:
        tmp.write_text(text, encoding="utf-8")
        os.replace(tmp, path)
    except OSError:
        tmp.unlink(missing_ok=True)
        raise
