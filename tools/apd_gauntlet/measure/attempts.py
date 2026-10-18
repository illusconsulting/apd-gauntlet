"""Read and write a run's retry and repair counts, ``<run>/.apd-state/attempts.yaml``.

In 1.7 runs none of these numbers is persisted: lens retries, first-pass
receipts and tier-gate results live only in the workflow's JavaScript, and
``40-synthesis/report-audit.yaml`` is overwritten on each audit attempt. This
file is their only record. The workflow writes it at closeout through
``apd-gauntlet summarize --record-attempts``, and a local runner calls
``write_attempts``. The shape is ``run-attempts.schema.json``.
"""
from __future__ import annotations

import contextlib
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator

from ..resources import read_schema
from ..validate import build_registry

SCHEMA = "run-attempts.schema.json"
ATTEMPTS_RELPATH = Path(".apd-state/attempts.yaml")


class AttemptsError(Exception):
    """Attempts data is invalid, or the file cannot be read or written; the message says why."""


@dataclass(frozen=True)
class Attempts:
    recorded_by: str
    lens_retries: dict[str, int]
    first_pass_invalid: tuple[str, ...]
    tier_gate_failures: tuple[str, ...]
    skipped: tuple[str, ...]
    audit_iterations: int
    tier_repairs: dict[str, int]
    lens_reruns: dict[str, int]

    @property
    def first_pass_validator_errors(self) -> int:
        """Lenses invalid on the first pass plus tier gates that failed before repair."""
        return len(self.first_pass_invalid) + len(self.tier_gate_failures)

    @property
    def lens_retries_total(self) -> int:
        return sum(self.lens_retries.values())

    @property
    def tier_repairs_total(self) -> int:
        return sum(self.tier_repairs.values())

    @property
    def lens_reruns_total(self) -> int:
        return sum(self.lens_reruns.values())


def _problems(data: Any) -> list[str]:
    """Every schema message as ``"<path>: <message>"``, sorted; empty when ``data`` is valid."""
    validator = Draft202012Validator(read_schema(SCHEMA), registry=build_registry())
    return sorted(
        f"{'/'.join(map(str, err.absolute_path)) or '<root>'}: {err.message}"
        for err in validator.iter_errors(data)
    )


def _counts(raw: Mapping[str, Any]) -> dict[str, int]:
    # The schema's "integer" admits 2.0; store and report it as 2.
    return {name: int(n) for name, n in raw.items()}


def _attempts(data: Any, context: str) -> Attempts:
    """Validate ``data`` and build ``Attempts``; ``AttemptsError`` lists every schema message."""
    if isinstance(data, Mapping):
        data = dict(data)
    problems = _problems(data)
    if problems:
        raise AttemptsError(f"{context}: " + "; ".join(problems))
    return Attempts(
        recorded_by=data["recorded_by"],
        lens_retries=_counts(data["lens_retries"]),
        first_pass_invalid=tuple(data["first_pass_invalid"]),
        tier_gate_failures=tuple(data["tier_gate_failures"]),
        skipped=tuple(data["skipped"]),
        audit_iterations=int(data["audit_iterations"]),
        tier_repairs=_counts(data["tier_repairs"]),
        lens_reruns=_counts(data["lens_reruns"]),
    )


def _document(a: Attempts) -> dict[str, Any]:
    """The file's contents, in the schema's key order."""
    return {
        "schema_version": 1,
        "recorded_by": a.recorded_by,
        "lens_retries": dict(a.lens_retries),
        "first_pass_invalid": list(a.first_pass_invalid),
        "tier_gate_failures": list(a.tier_gate_failures),
        "skipped": list(a.skipped),
        "audit_iterations": a.audit_iterations,
        "tier_repairs": dict(a.tier_repairs),
        "lens_reruns": dict(a.lens_reruns),
    }


def write_attempts(run_dir: Path, data: Mapping[str, Any]) -> Path:
    """Validate ``data`` and write it to ``<run_dir>/.apd-state/attempts.yaml``.

    Creates ``.apd-state/`` (``run_dir`` itself must exist) and replaces any
    earlier file. Nothing is created when ``data`` is invalid: ``AttemptsError``
    lists every schema message. A write that fails part-way leaves any earlier
    file intact, because the new text is written beside it and then moved into
    place. Returns the path written.
    """
    text = yaml.safe_dump(
        _document(_attempts(data, "invalid attempts")), sort_keys=False, allow_unicode=True
    )
    path = run_dir / ATTEMPTS_RELPATH
    partial = path.with_name(path.name + ".tmp")
    try:
        path.parent.mkdir(exist_ok=True)
        partial.write_text(text, encoding="utf-8")
        partial.replace(path)
    except OSError as exc:
        with contextlib.suppress(OSError):  # e.g. .apd-state is a file
            partial.unlink(missing_ok=True)
        raise AttemptsError(f"{path}: cannot write: {exc.strerror or exc}") from exc
    return path


def read_attempts(run_dir: Path) -> Attempts | None:
    """Read ``<run_dir>/.apd-state/attempts.yaml``; ``None`` when the file does not exist.

    A file that cannot be read, is not UTF-8, is not valid YAML or does not
    match the schema raises ``AttemptsError`` naming it.
    """
    path = run_dir / ATTEMPTS_RELPATH
    try:
        raw = path.read_bytes()
    except FileNotFoundError:
        return None
    except OSError as exc:
        raise AttemptsError(f"{path}: cannot read: {exc.strerror or exc}") from exc
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise AttemptsError(f"{path}: not UTF-8 text: {exc}") from exc
    try:
        doc = yaml.safe_load(text)
    except (yaml.YAMLError, ValueError) as exc:  # ValueError: e.g. an impossible date
        raise AttemptsError(f"{path}: invalid YAML: {exc}") from exc
    except RecursionError as exc:
        raise AttemptsError(f"{path}: invalid YAML: nested too deeply to parse") from exc
    return _attempts(doc, f"{path}: invalid attempts")
