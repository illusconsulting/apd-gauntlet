"""Corpus manifests and their label files (``eval-corpus`` and ``eval-labels``).

A manifest lists the entries an evaluator scores. Each entry is in the ``dev``
set, where tunables and thresholds are tuned, or the ``heldout`` set, which is
run only after ``eval freeze``. An entry names a finished run directory, a
repository pinned by commit, or both, and its labels file. ``run`` and
``labels`` are relative to the manifest's directory.

The two sets must be disjoint, as in GRAML's cross-dataset deduplication: a
run directory (compared after resolving links and ``..``) or a ``(repo.url,
repo.commit)`` pair that appears in both sets is refused, and so is a duplicate
entry id. Every problem raises ``CorpusError`` naming the file: one that cannot
be read, is not UTF-8 or is not valid YAML, and every schema message with its
JSON path.
"""
from __future__ import annotations

import functools
import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import yaml
from jsonschema import Draft202012Validator, ValidationError

from ..resources import read_schema
from ..validate import build_registry

CORPUS_SCHEMA = "eval-corpus.schema.json"
LABELS_SCHEMA = "eval-labels.schema.json"
SETS = ("dev", "heldout")


class CorpusError(Exception):
    """A manifest or labels file cannot be read or is invalid; the message names the file."""


@dataclass(frozen=True)
class RepoPin:
    url: str
    commit: str
    path: str | None


@dataclass(frozen=True)
class CorpusEntry:
    id: str
    set: Literal["dev", "heldout"]
    run_dir: Path | None
    repo: RepoPin | None
    labels_path: Path


@dataclass(frozen=True)
class Corpus:
    name: str
    path: Path
    sha256: str  # of the manifest's bytes
    entries: tuple[CorpusEntry, ...]

    def select(self, set_name: str) -> tuple[CorpusEntry, ...]:
        """The entries of one set, in file order; ``ValueError`` for a name not in ``SETS``."""
        if set_name not in SETS:
            raise ValueError(f"unknown set {set_name!r}; expected dev or heldout")
        return tuple(e for e in self.entries if e.set == set_name)


@dataclass(frozen=True)
class Labels:
    kind: Literal["findings", "decisions"]
    path: Path
    sha256: str  # of the file's bytes
    data: dict[str, Any]


def _read(path: Path) -> tuple[str, Any]:
    """The SHA-256 of ``path``'s bytes and its parsed YAML."""
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise CorpusError(f"{path}: cannot read: {exc.strerror or exc}") from exc
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise CorpusError(f"{path}: not UTF-8 text: {exc}") from exc
    try:
        doc = yaml.safe_load(text)
    except (yaml.YAMLError, ValueError) as exc:  # ValueError: e.g. an impossible date
        raise CorpusError(f"{path}: invalid YAML: {exc}") from exc
    except RecursionError as exc:
        raise CorpusError(f"{path}: invalid YAML: nested too deeply to parse") from exc
    return hashlib.sha256(raw).hexdigest(), doc


@functools.cache
def _validator(schema: str) -> Draft202012Validator:
    return Draft202012Validator(read_schema(schema), registry=build_registry())


def _order(err: ValidationError) -> tuple[tuple[int, int, str], ...]:
    """Document order: list indexes as numbers, so ``[10]`` sorts after ``[2]``."""
    return tuple(
        (0, part, "") if isinstance(part, int) else (1, 0, str(part))
        for part in err.absolute_path
    )


def _message(err: ValidationError) -> str:
    if err.validator == "anyOf" and err.context:  # an entry with neither run nor repo
        return " or ".join(dict.fromkeys(sub.message for sub in err.context))
    return err.message


def _validate(doc: Any, schema: str, context: str) -> None:
    """Raise ``CorpusError`` listing every schema message as ``<JSON path>: <message>``."""
    errors = sorted(_validator(schema).iter_errors(doc), key=lambda e: (_order(e), e.message))
    problems = dict.fromkeys(f"{err.json_path}: {_message(err)}" for err in errors)
    if problems:
        raise CorpusError(f"{context}: " + "; ".join(problems))


def _entry(raw: dict[str, Any], base: Path) -> CorpusEntry:
    repo = raw.get("repo")
    return CorpusEntry(
        id=raw["id"],
        set=raw["set"],
        run_dir=base / raw["run"] if "run" in raw else None,
        repo=RepoPin(repo["url"], repo["commit"], repo.get("path")) if repo else None,
        labels_path=base / raw["labels"],
    )


def _sources(path: Path, index: int, entry: CorpusEntry) -> list[tuple[tuple[str, ...], str]]:
    """What the entry evaluates, as (key, description) pairs the two sets must not share."""
    sources: list[tuple[tuple[str, ...], str]] = []
    if entry.run_dir is not None:
        try:
            resolved = entry.run_dir.resolve()
        except (OSError, RuntimeError) as exc:  # RuntimeError: a link loop before 3.13
            raise CorpusError(
                f"{path}: $.entries[{index}].run: cannot resolve {entry.run_dir}: {exc}"
            ) from exc
        sources.append((("run", str(resolved)), f"use run {resolved}"))
    if entry.repo is not None:
        key = ("repo", entry.repo.url, entry.repo.commit)
        sources.append((key, f"pin {entry.repo.url} at {entry.repo.commit}"))
    return sources


def _check_disjoint(path: Path, entries: list[CorpusEntry]) -> None:
    seen: dict[tuple[str, tuple[str, ...]], CorpusEntry] = {}
    for index, entry in enumerate(entries):
        for key, what in _sources(path, index, entry):
            other_set = "heldout" if entry.set == "dev" else "dev"
            first = seen.get((other_set, key))
            if first is not None:
                raise CorpusError(
                    f"{path}: entries {first.id!r} ({first.set}) and {entry.id!r} ({entry.set})"
                    f" both {what}; the dev and heldout sets must be disjoint"
                )
            seen.setdefault((entry.set, key), entry)


def load_corpus_manifest(path: Path) -> Corpus:
    """Read and check the manifest at ``path``; see the module docstring for the rules."""
    sha256, doc = _read(path)
    _validate(doc, CORPUS_SCHEMA, f"{path}: invalid corpus manifest")
    entries: list[CorpusEntry] = []
    first_index: dict[str, int] = {}
    for index, raw in enumerate(doc["entries"]):
        if raw["id"] in first_index:
            raise CorpusError(
                f"{path}: duplicate entry id {raw['id']!r}"
                f" ($.entries[{first_index[raw['id']]}] and $.entries[{index}])"
            )
        first_index[raw["id"]] = index
        entries.append(_entry(raw, path.parent))
    _check_disjoint(path, entries)
    return Corpus(name=doc["name"], path=path, sha256=sha256, entries=tuple(entries))


def load_labels(path: Path) -> Labels:
    """Read the labels file at ``path`` and check it against ``eval-labels.schema.json``.

    Only the schema is checked: an ``unreviewed`` item loads, and an evaluator
    refuses it.
    """
    sha256, doc = _read(path)
    _validate(doc, LABELS_SCHEMA, f"{path}: invalid labels")
    return Labels(kind=doc["kind"], path=path, sha256=sha256, data=doc)
