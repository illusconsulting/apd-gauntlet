"""Shared fixtures: scratch run directories built from a committed example, and edits to them.

``make_run(name)`` copies ``examples/apd-20260601-claim-event-bus/expected`` to
``tmp_path/name`` and that example's ``inputs/`` to ``<run>/inputs``, so two runs made
from it share an inputs digest. ``edit`` changes records in such a copy by rewriting
the corpus file that holds them (``**/*.findings.yaml`` or ``**/*.capabilities.yaml``,
the files ``load_corpus`` reads); report and synthesis files are left as they are.
"""
from __future__ import annotations

import pathlib
import shutil
from collections.abc import Callable
from typing import Any

import pytest
import yaml

REPO = pathlib.Path(__file__).parent.parent
CLAIM_EVENT_BUS = REPO / "examples/apd-20260601-claim-event-bus"

# Record kind -> (corpus glob, legacy plural root key that load_corpus also accepts).
_KINDS = {
    "finding": ("**/*.findings.yaml", "findings"),
    "capability": ("**/*.capabilities.yaml", "capabilities"),
}


@pytest.fixture
def make_run(tmp_path: pathlib.Path) -> Callable[[str], pathlib.Path]:
    """Return ``make(name)``, which builds a copy of the claim-event-bus run in ``tmp_path``."""

    def make(name: str) -> pathlib.Path:
        run = tmp_path / name
        shutil.copytree(CLAIM_EVENT_BUS / "expected", run)
        shutil.copytree(CLAIM_EVENT_BUS / "inputs", run / "inputs")
        return run

    return make


def _root_key(doc: dict[str, Any], kind: str) -> str:
    plural = _KINDS[kind][1]
    return plural if kind not in doc and plural in doc else kind


def _read(path: pathlib.Path, kind: str) -> tuple[dict[str, Any], str, list[Any]]:
    """The document, its root key, and its records as a list (a single mapping is one)."""
    doc = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    key = _root_key(doc, kind)
    raw = doc.get(key)
    records = raw if isinstance(raw, list) else ([] if raw is None else [raw])
    return doc, key, records


def _write(path: pathlib.Path, doc: dict[str, Any], key: str, records: list[Any]) -> None:
    doc[key] = records
    path.write_text(
        yaml.safe_dump(doc, sort_keys=False, allow_unicode=True, width=1000), encoding="utf-8"
    )


class RunEditor:
    """Edits records in a scratch run; an id that no corpus file holds raises ``LookupError``."""

    def finding(self, run: pathlib.Path, rid: str, **fields: Any) -> None:
        self._update(run, "finding", rid, fields)

    def capability(self, run: pathlib.Path, rid: str, **fields: Any) -> None:
        self._update(run, "capability", rid, fields)

    def drop(self, run: pathlib.Path, rid: str) -> None:
        """Remove the finding or capability ``rid``."""
        for kind in _KINDS:
            located = self._find(run, kind, rid)
            if located is not None:
                path, doc, key, records, index = located
                del records[index]
                _write(path, doc, key, records)
                return
        raise LookupError(f"no finding or capability {rid} in {run}")

    def add_finding(self, run: pathlib.Path, rel_path: str, record: dict[str, Any]) -> None:
        """Append ``record`` to the findings file ``rel_path``, creating it if needed."""
        path = run / rel_path
        if path.exists():
            doc, key, records = _read(path, "finding")
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            doc, key, records = {}, "finding", []
        records.append(record)
        _write(path, doc, key, records)

    def _update(self, run: pathlib.Path, kind: str, rid: str, fields: dict[str, Any]) -> None:
        located = self._find(run, kind, rid)
        if located is None:
            raise LookupError(f"no {kind} {rid} in {run}")
        path, doc, key, records, index = located
        records[index] = {**records[index], **fields}
        _write(path, doc, key, records)

    @staticmethod
    def _find(
        run: pathlib.Path, kind: str, rid: str
    ) -> tuple[pathlib.Path, dict[str, Any], str, list[Any], int] | None:
        hits = []
        for path in sorted(run.glob(_KINDS[kind][0])):
            doc, key, records = _read(path, kind)
            for index, record in enumerate(records):
                if isinstance(record, dict) and record.get("id") == rid:
                    hits.append((path, doc, key, records, index))
        if len(hits) > 1:
            raise LookupError(f"{kind} {rid} is in more than one file: {[h[0] for h in hits]}")
        return hits[0] if hits else None


@pytest.fixture
def edit() -> RunEditor:
    """Return a ``RunEditor`` (``.finding``, ``.capability``, ``.drop``, ``.add_finding``)."""
    return RunEditor()
