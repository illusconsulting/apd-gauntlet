"""``eval run``: a registered evaluator over one set of a corpus, written as a results file.

``run_eval`` scores every entry of the ``dev`` or ``heldout`` set of a corpus
manifest with one evaluator and writes
``<results_dir>/<evaluator>/<set>-<UTC time>.yaml``. A held-out run checks the
freeze first (``check_frozen``), before the manifest is read, and again after
the last entry, so a tunables file edited, or a re-freeze, while the
evaluators ran also refuses. Its results file records the frozen hash, which
is what makes ``eval freeze`` refuse to re-freeze changed tunables. A dev run
records the frozen hash when the tunables match the freeze, and ``null``
otherwise.

Nothing is written until every entry is scored: the manifest and every labels
file are loaded before the first evaluator runs, and an error from any entry
leaves no results file. An existing results file is never overwritten.
Results stay local (ADR-0028).
"""
from __future__ import annotations

import errno
import math
from collections.abc import Mapping
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

import yaml

from .. import __version__
from .corpus import SETS, CorpusEntry, Labels, load_corpus_manifest, load_labels
from .evaluators import EvalResult, get, load_builtin_evaluators
from .freeze import FreezeError, check_frozen

SCHEMA_VERSION = 1
_HEADER = (
    "# Written by 'apd-gauntlet eval run'. Results stay local and are never committed "
    "(ADR-0028).\n"
)


class ResultsWriteError(Exception):
    """The results file exists (it is never overwritten) or cannot be written."""


def _utc(now: datetime | None) -> datetime:
    """``now`` in UTC, to the second; a naive time is taken as UTC already."""
    if now is None:
        now = datetime.now(timezone.utc)
    elif now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    return now.astimezone(timezone.utc).replace(microsecond=0)


def _display_path(path: Path, root: Path) -> str:
    """``path`` relative to ``root`` in posix form when it is inside it, else absolute."""
    resolved = path.resolve()
    try:
        return resolved.relative_to(root.resolve()).as_posix()
    except ValueError:
        return str(resolved)


def _short(value: Any) -> str:
    """``repr(value)``, cut to 60 characters, so a long bad value is not echoed in full."""
    text = repr(value)
    return text if len(text) <= 60 else text[:60] + "..."


def _is_count(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def _metric(value: Any) -> float | None:
    """A metric as a finite float, or ``None``; ``TypeError`` for anything else."""
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError
    try:
        number = float(value)
    except OverflowError:  # an int too large for a float
        raise TypeError from None
    if not math.isfinite(number):
        raise TypeError
    return number


def _checked(evaluator: str, entry: CorpusEntry, result: EvalResult) -> dict[str, Any]:
    """The results-file row for ``result``; ``ValueError`` when it is malformed."""
    where = f"evaluator {evaluator!r}, entry {entry.id!r}"
    if result.entry_id != entry.id:
        raise ValueError(
            f"evaluator {evaluator!r} returned a result for entry {_short(result.entry_id)}, "
            f"not {entry.id!r}"
        )
    for key, count in result.counts.items():
        if not isinstance(key, str) or not _is_count(count):
            raise ValueError(
                f"{where}: count {_short(key)} is {_short(count)}; counts are integers of at "
                "least 0 keyed by name"
            )
    metrics: dict[str, float | None] = {}
    for key, value in result.metrics.items():
        if not isinstance(key, str):
            raise ValueError(f"{where}: metric {_short(key)} is not keyed by name")
        try:
            metrics[key] = _metric(value)
        except TypeError:
            raise ValueError(
                f"{where}: metric {key!r} is {_short(value)}, not a finite number or null"
            ) from None
    return {
        "id": entry.id,
        "counts": dict(result.counts),
        "metrics": metrics,
        "notes": [str(note) for note in result.notes],
    }


def _sum(rows: list[dict[str, Any]]) -> dict[str, int]:
    """Every count summed over ``rows``; keys in first-seen order, a missing count is 0."""
    totals: dict[str, int] = {}
    for row in rows:
        for key, value in row["counts"].items():
            totals[key] = totals.get(key, 0) + value
    return totals


def _derived(evaluator: str, result: EvalResult, counts: Mapping[str, int]) -> dict[str, Any]:
    if result.derive is None:
        return {}
    metrics: dict[str, float | None] = {}
    for key, value in result.derive(counts).items():
        if not isinstance(key, str):
            raise ValueError(
                f"evaluator {evaluator!r}: total metric {_short(key)} is not keyed by name"
            )
        try:
            metrics[key] = _metric(value)
        except TypeError:
            raise ValueError(
                f"evaluator {evaluator!r}: total metric {key!r} is {_short(value)}, "
                "not a finite number or null"
            ) from None
    return metrics


def _frozen_for(set_name: str, root: Path) -> str | None:
    """The frozen hash a run records; a held-out run raises ``FreezeError`` without one."""
    if set_name == "heldout":
        return check_frozen(root)
    try:
        return check_frozen(root)
    except FreezeError:
        return None


def _write(path: Path, doc: Mapping[str, Any]) -> None:
    """Write ``doc`` to the new file ``path``; ``FileExistsError`` when it exists.

    A partly written file is removed.
    """
    text = _HEADER + yaml.safe_dump(dict(doc), sort_keys=False, allow_unicode=True, width=1000)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
    except FileExistsError as exc:  # a file where a directory belongs
        raise NotADirectoryError(errno.ENOTDIR, "Not a directory", str(exc.filename)) from exc
    handle = path.open("x", encoding="utf-8")  # exclusive: never overwrite, never via a link
    try:
        with handle:
            handle.write(text)
    except BaseException:
        path.unlink(missing_ok=True)
        raise


def run_eval(
    manifest: Path,
    set_name: Literal["dev", "heldout"],
    evaluator: str,
    *,
    root: Path,
    results_dir: Path,
    now: datetime | None = None,
) -> Path:
    """Score the ``set_name`` entries of ``manifest`` with ``evaluator``; returns the file.

    The file is ``<results_dir>/<evaluator>/<set>-<now:%Y%m%dT%H%M%SZ>.yaml`` with
    ``schema_version``, ``evaluator``, ``set``, ``corpus`` (``name``, ``path``
    relative to ``root`` when inside it, ``sha256`` of the manifest's bytes),
    ``frozen_sha256``, ``engine_version``, ``generated_at``, ``entries`` (``id``,
    ``counts``, ``metrics``, ``notes``) and ``totals``: the summed counts and the
    first entry's ``derive`` over them (``{}`` without one). ``now`` defaults to
    the current time; a naive ``now`` is taken as UTC.

    Raises ``KeyError`` for an unknown evaluator, ``ValueError`` for an unknown
    set, a set with no entries, an evaluator's own ``ValueError`` or a malformed
    result, ``FreezeError`` when a held-out run finds the tunables not frozen or
    changed (before the manifest is read, or after the last entry),
    ``CorpusError`` for the manifest or a labels file, and ``ResultsWriteError``
    when the results file exists or cannot be written.
    """
    if set_name not in SETS:
        raise ValueError(f"unknown set {set_name!r}; expected dev or heldout")
    load_builtin_evaluators()
    fn = get(evaluator)
    frozen = _frozen_for(set_name, root)
    corpus = load_corpus_manifest(manifest)
    entries = corpus.select(set_name)
    if not entries:
        raise ValueError(f"{manifest}: no {set_name} entries in corpus {corpus.name!r}")
    labelled: list[tuple[CorpusEntry, Labels]] = [
        (entry, load_labels(entry.labels_path)) for entry in entries
    ]
    results = [(entry, fn(entry, labels)) for entry, labels in labelled]
    rows = [_checked(evaluator, entry, result) for entry, result in results]
    counts = _sum(rows)
    totals = {"counts": counts, "metrics": _derived(evaluator, results[0][1], counts)}
    if frozen is not None and set_name == "heldout":
        after = check_frozen(root)
        if after != frozen:
            raise FreezeError(
                f"tunables re-frozen during the held-out run (frozen as {frozen[:8]} when it "
                f"started, {after[:8]} now); nothing written — run it again"
            )
    stamp = _utc(now)
    doc: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "evaluator": evaluator,
        "set": set_name,
        "corpus": {
            "name": corpus.name,
            "path": _display_path(manifest, root),
            "sha256": corpus.sha256,
        },
        "frozen_sha256": frozen,
        "engine_version": __version__,
        "generated_at": stamp.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "entries": rows,
        "totals": totals,
    }
    path = results_dir / evaluator / f"{set_name}-{stamp:%Y%m%dT%H%M%SZ}.yaml"
    try:
        _write(path, doc)
    except FileExistsError as exc:
        raise ResultsWriteError(f"{path} exists; not overwritten") from exc
    except OSError as exc:
        raise ResultsWriteError(f"{path}: cannot write: {exc.strerror or exc}") from exc
    return path

