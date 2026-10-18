"""The comparison gates in ``eval/gates.yaml``, and their evaluation.

Each gate holds one or more checks, and each check bounds one metric that
``compare-runs`` computes: ``le`` (at most the value) or ``ge`` (at least the
value), both inclusive. A gate fails when any check whose metric has a value
fails. If none fails but a value is missing, the gate is ``not_available``,
because 1.7 runs record no attempts and a resumed run under-counts them. Only
when every value is known and every check holds does the gate pass. A
``not_available`` gate never counts as passed: ``overall`` then reads
``pass_with_gaps``.

``load_gates`` reads only the ``gates`` list and ignores other top-level keys,
so a file can carry other sections next to it.
"""
from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import yaml

METRICS = frozenset({
    "unexcused_lost_critical_high",
    "severity_agreement_pct",
    "blocked_rate_abs_delta_pts",
    "first_pass_validator_errors_delta",
    "lens_retries_delta",
    "tier_repairs_delta",  # WS1's repair loop (register A9.4)
    "lens_reruns_delta",  # WS1's repair loop (register A9.4)
    "audit_iterations_delta",
})
SCHEMA_VERSION = 1
_OPS = ("le", "ge")
_GATE_KEYS = ("id", "text", "checks")
_CHECK_KEYS = ("metric", "op", "value")


class GatesError(Exception):
    """The gates file cannot be read or is malformed; the message names the file and the problem."""


class _Malformed(Exception):
    """A problem in the parsed document; ``load_gates`` prefixes the file name."""


@dataclass(frozen=True)
class Check:
    metric: str
    op: Literal["le", "ge"]
    value: float


@dataclass(frozen=True)
class Gate:
    id: str
    text: str
    checks: tuple[Check, ...]


@dataclass(frozen=True)
class GateOutcome:
    gate: Gate
    status: Literal["pass", "fail", "not_available"]
    values: dict[str, float | None]
    reason: str | None


def _read(path: Path) -> Any:
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:  # a ValueError, not an OSError
        raise GatesError(f"{path}: not UTF-8 text: {exc}") from exc
    except OSError as exc:
        raise GatesError(f"{path}: cannot read: {exc.strerror or exc}") from exc
    try:
        return yaml.safe_load(text)
    except (yaml.YAMLError, ValueError) as exc:  # ValueError: e.g. an impossible date
        raise GatesError(f"{path}: invalid YAML: {exc}") from exc
    except RecursionError as exc:
        raise GatesError(f"{path}: invalid YAML: nested too deeply to parse") from exc


def _mapping(raw: Any, where: str, keys: tuple[str, ...]) -> dict[Any, Any]:
    """``raw`` when it is a mapping with exactly ``keys``; else ``_Malformed`` naming the key."""
    if not isinstance(raw, dict):
        raise _Malformed(f"{where} is not a mapping")
    for key in keys:
        if key not in raw:
            raise _Malformed(f"{where}: missing key {key!r}")
    unknown = sorted(str(key) for key in raw if key not in keys)
    if unknown:
        raise _Malformed(f"{where}: unknown key {unknown[0]!r}")
    return raw


def _number(raw: Any) -> float | None:
    """``raw`` as a finite float, or ``None`` when it is not a finite number (booleans included)."""
    if isinstance(raw, bool) or not isinstance(raw, (int, float)):
        return None
    try:
        number = float(raw)
    except OverflowError:  # an integer too large for a float
        return None
    return number if math.isfinite(number) else None


def _text(raw: Any) -> bool:
    return isinstance(raw, str) and bool(raw.strip())


def _check(raw: Any, where: str) -> Check:
    raw = _mapping(raw, where, _CHECK_KEYS)
    metric, op = raw["metric"], raw["op"]
    if not isinstance(metric, str) or metric not in METRICS:
        raise _Malformed(f"{where}: unknown metric {metric!r}")
    if not isinstance(op, str) or op not in _OPS:
        raise _Malformed(f"{where}: unknown op {op!r}")
    value = _number(raw["value"])
    if value is None:
        raise _Malformed(f"{where}: value is not a finite number: {raw['value']!r}")
    return Check(metric=metric, op="le" if op == "le" else "ge", value=value)


def _gate(raw: Any, where: str) -> Gate:
    raw = _mapping(raw, where, _GATE_KEYS)
    for key in ("id", "text"):
        if not _text(raw[key]):
            raise _Malformed(f"{where}: {key} is not a non-empty string")
    checks = raw["checks"]
    if not isinstance(checks, list) or not checks:
        raise _Malformed(f"{where}: checks is not a non-empty list")
    return Gate(
        id=raw["id"],
        text=raw["text"],
        checks=tuple(_check(c, f"{where}.checks[{j}]") for j, c in enumerate(checks)),
    )


def _gates(doc: Any) -> tuple[Gate, ...]:
    if not isinstance(doc, dict):
        raise _Malformed("top level is not a mapping")
    for key in ("schema_version", "gates"):
        if key not in doc:
            raise _Malformed(f"missing key {key!r}")
    version = doc["schema_version"]
    if isinstance(version, bool) or version != SCHEMA_VERSION:
        raise _Malformed(f"unsupported schema_version {version!r}")
    items = doc["gates"]
    if not isinstance(items, list) or not items:
        raise _Malformed("gates is not a non-empty list")
    gates: list[Gate] = []
    for i, item in enumerate(items):
        gate = _gate(item, f"gates[{i}]")
        if any(g.id == gate.id for g in gates):
            raise _Malformed(f"gates[{i}]: duplicate id {gate.id!r}")
        gates.append(gate)
    return tuple(gates)


def load_gates(path: Path) -> tuple[Gate, ...]:
    """The gates in ``path``, in file order.

    ``GatesError`` names the file and the first problem: a file that cannot be
    read or parsed, a missing or unknown key, an unknown metric or op, a
    duplicate gate id, a ``schema_version`` other than 1, an empty list, or a
    value that is not a finite number.
    """
    doc = _read(path)
    try:
        return _gates(doc)
    except _Malformed as exc:
        raise GatesError(f"{path}: {exc}") from None


def _holds(check: Check, value: float) -> bool:
    # A NaN satisfies neither comparison, so it fails rather than passes.
    return value <= check.value if check.op == "le" else value >= check.value


def evaluate(
    gates: Sequence[Gate],
    values: Mapping[str, float | None],
    reasons: Mapping[str, str],
) -> list[GateOutcome]:
    """One outcome per gate, in order.

    ``fail`` when any check whose metric has a value fails; else
    ``not_available`` when a metric's value is ``None`` or absent from
    ``values``; else ``pass``. A ``not_available`` reason joins the distinct
    ``reasons`` of the missing metrics in check order (``"no value for
    <metric>"`` when ``reasons`` has none); ``pass`` and ``fail`` carry no
    reason.
    """
    outcomes: list[GateOutcome] = []
    for gate in gates:
        own = {c.metric: values.get(c.metric) for c in gate.checks}
        missing: list[str] = []
        failed = False
        for check in gate.checks:
            value = own[check.metric]
            if value is None:
                missing.append(check.metric)
            elif not _holds(check, value):
                failed = True
        if failed:
            outcomes.append(GateOutcome(gate=gate, status="fail", values=own, reason=None))
        elif missing:
            texts = (reasons.get(m, f"no value for {m}") for m in missing)
            reason = "; ".join(dict.fromkeys(texts))
            outcomes.append(
                GateOutcome(gate=gate, status="not_available", values=own, reason=reason)
            )
        else:
            outcomes.append(GateOutcome(gate=gate, status="pass", values=own, reason=None))
    return outcomes


def overall(outcomes: Sequence[GateOutcome]) -> Literal["pass", "pass_with_gaps", "fail"]:
    """``fail`` when any gate fails; else ``pass_with_gaps`` when any is ``not_available``."""
    statuses = {o.status for o in outcomes}
    if "fail" in statuses:
        return "fail"
    if "not_available" in statuses:
        return "pass_with_gaps"
    return "pass"
