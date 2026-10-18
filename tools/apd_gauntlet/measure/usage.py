"""Tokens and cost per agent and phase, from Claude Code's OpenTelemetry events.

Claude Code emits one ``claude_code.api_request`` log event per model request,
with the documented attributes ``model``, ``cost_usd``, ``cost_usd_micros``,
``input_tokens``, ``output_tokens``, ``cache_read_tokens``,
``cache_creation_tokens``, ``effort`` and ``agent.name``, plus ``event.name``,
``session.id`` and ``workflow.run_id``. ``usage`` reads an export of those events
and writes ``<run>/.apd-state/usage.yaml``: totals, ``by_agent`` and
``by_phase``, the decision-model spend recorded under ``40-synthesis/decisions/``
and the combined cost, ``cost_usd_all``.

The documentation fixes the attribute names but not the file format, so
``iter_api_requests`` accepts OTLP/JSON only: the proto3 JSON mapping of
``ExportLogsServiceRequest``, one document per line as the OpenTelemetry
Collector ``file`` exporter writes it (a single pretty-printed document also
reads). It is the only function that knows the format; its private helpers sit
directly above it. The console exporter's output is refused. Telemetry carries
no phase, so ``phase_for`` maps the agent name through ``AGENT_PHASES``.
"""
from __future__ import annotations

import contextlib
import hashlib
import json
import math
from collections.abc import Iterable, Iterator, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

USAGE_RELPATH = Path(".apd-state/usage.yaml")
DECISIONS_RELDIR = Path("40-synthesis/decisions")
RUNBOOK = "docs/measuring-changes.md"

AGENT_PHASES: dict[str, str] = {
    "apd-intake": "intake",
    "apd-code-recon": "code-recon",
    "apd-threat-model-author": "threat-model-author",
    "apd-threat-model-recon": "tm-recon",
    "apd-confidentiality": "tier-1",
    "apd-integrity": "tier-1",
    "apd-availability": "tier-1",
    "apd-distributed": "tier-2",
    "apd-resilient": "tier-2",
    "apd-ephemeral": "tier-2",
    "apd-authenticity": "tier-3",
    "apd-non-repudiation": "tier-3",
    "apd-immutability": "tier-3",
    "apd-cluster-adjudicator": "synthesis-adjudicate",
    "apd-synthesizer": "synthesis-fallback",
    "apd-threat-model-evaluator": "tmeval",
    "apd-attack-path-analyzer": "apath",
    "apd-report-writer": "synthesis-report",
    "apd-report-auditor": "synthesis-audit",
    "apd-domain-auditor": "domain-improvements",
    "apd-tier-repair": "canonicalize",  # WS1's tier-gate repair agent (register A9.2)
    "general-purpose": "cli-steps",  # every pyStep worker
    "main": "session",
}
# Phases that are not workflow phases: CLI steps, the launching session, and the rest.
PSEUDO_PHASES = frozenset({"cli-steps", "session", "unattributed"})
# What Claude Code reports for custom agents without OTEL_LOG_TOOL_DETAILS=1.
REDACTED_AGENTS = frozenset({"custom", "third-party"})

_TOKENS = ("input_tokens", "output_tokens", "cache_read_tokens", "cache_creation_tokens")
_COUNTERS = ("requests", *_TOKENS)
_DECISION_COUNTERS = ("calls", "input_tokens")


_SHOWN = 60  # characters of a bad value an error message quotes


class UsageParseError(Exception):
    """Telemetry or a decision record cannot be read as usage; the message names the file."""


def _shown(value: Any) -> str:
    """``repr(value)`` for an error message, cut to ``_SHOWN`` characters and ``...``."""
    text = repr(value)
    return text if len(text) <= _SHOWN else text[:_SHOWN] + "..."


@dataclass(frozen=True)
class ApiRequest:
    """One ``api_request`` event.

    ``cost_missing`` is set when the event carried neither ``cost_usd_micros``
    nor ``cost_usd`` (``cost_usd_micros`` is then 0); ``effort`` is the
    ``effort`` attribute (register A9.7).
    """

    agent: str
    model: str
    input_tokens: int
    output_tokens: int
    cache_read_tokens: int
    cache_creation_tokens: int
    cost_usd_micros: int
    session_id: str | None
    workflow_run_id: str | None
    cost_missing: bool = False
    effort: str | None = None


# --- OTLP/JSON: the private helpers of iter_api_requests ---------------------------------


def _otlp_value(any_value: Any) -> Any:
    """Decode an OTLP ``AnyValue``; a kind other than string, int, double or bool is ``None``."""
    if isinstance(any_value, dict):
        for kind in ("stringValue", "intValue", "doubleValue", "boolValue"):
            if kind in any_value:
                return any_value[kind]
    return None


def _otlp_object(value: Any, where: str) -> dict[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise UsageParseError(f"{where} is not an object")
    return value


def _otlp_list(obj: dict[str, Any], key: str, where: str) -> list[Any]:
    value = obj.get(key)
    if value is None:  # proto3 JSON omits empty repeated fields
        return []
    if not isinstance(value, list):
        raise UsageParseError(f"{where}{key} is not a list")
    return value


def _otlp_attributes(obj: dict[str, Any], where: str) -> dict[str, Any]:
    attrs: dict[str, Any] = {}
    for kv in _otlp_list(obj, "attributes", where):
        if isinstance(kv, dict) and isinstance(kv.get("key"), str):
            attrs[kv["key"]] = _otlp_value(kv.get("value"))
    return attrs


def _otlp_int(attrs: dict[str, Any], name: str, where: str) -> int:
    value = attrs.get(name)
    if value is None:
        return 0
    try:
        if isinstance(value, bool):
            raise TypeError(name)
        return int(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise UsageParseError(f"{where}: {name} is not an integer: {_shown(value)}") from exc


def _otlp_micros(attrs: dict[str, Any], where: str) -> int | None:
    """``cost_usd_micros`` when present, else ``round(cost_usd * 1e6)``, else ``None``."""
    if attrs.get("cost_usd_micros") is not None:
        return _otlp_int(attrs, "cost_usd_micros", where)
    value = attrs.get("cost_usd")
    if value is None:
        return None
    try:
        if isinstance(value, bool):
            raise TypeError("cost_usd")
        micros = float(value) * 1e6
        if not math.isfinite(micros):
            raise ValueError(value)
    except (TypeError, ValueError) as exc:
        raise UsageParseError(
            f"{where}: cost_usd is not a finite number: {_shown(value)}"
        ) from exc
    return round(micros)


def _otlp_str(attrs: dict[str, Any], name: str) -> str | None:
    value = attrs.get(name)
    return None if value is None else str(value)


def _otlp_documents(text: str, path: Path) -> Iterator[tuple[int, Any]]:
    """Each JSON document in ``text`` with the line it starts on."""
    decoder = json.JSONDecoder()
    pos, line, counted = 0, 1, 0
    while True:
        while pos < len(text) and text[pos] in " \t\r\n":
            pos += 1
        if pos == len(text):
            return
        line += text.count("\n", counted, pos)
        counted = pos
        try:
            doc, pos = decoder.raw_decode(text, pos)
        except json.JSONDecodeError as exc:
            raise UsageParseError(
                f"{path}: line {exc.lineno}: not JSON ({exc.msg}). usage reads OTLP/JSON only, "
                "one ExportLogsServiceRequest per line as the OpenTelemetry Collector file "
                f"exporter writes it; the console exporter's output is not parsed. See {RUNBOOK}."
            ) from exc
        except ValueError as exc:  # e.g. an integer longer than int() converts
            raise UsageParseError(f"{path}: line {line}: cannot parse a JSON value: {exc}") from exc
        except RecursionError as exc:
            raise UsageParseError(f"{path}: line {line}: nested too deeply to parse") from exc
        yield line, doc


def iter_api_requests(path: Path) -> Iterator[ApiRequest]:
    """Yield every ``api_request`` event in the OTLP/JSON export at ``path``, in file order.

    A log record counts when attribute ``event.name`` is ``api_request`` or its
    body's ``stringValue`` is ``claude_code.api_request``. Record attributes
    override resource attributes; a missing (or empty) ``agent.name`` is
    ``main``. Documents without ``resourceLogs`` (metrics or traces in the same
    file) are skipped. Text that is not JSON, a JSON value that cannot be
    converted (an integer longer than ``int()`` accepts), a malformed document,
    a token count that is not an integer and a cost that is not a finite number
    raise ``UsageParseError`` naming the file and line; a bad value is quoted
    cut to 60 characters.
    """
    try:
        text = path.read_bytes().decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise UsageParseError(f"{path}: not UTF-8 text, so not OTLP/JSON: {exc}") from exc
    except OSError as exc:
        raise UsageParseError(f"{path}: cannot read: {exc.strerror or exc}") from exc
    for line, doc in _otlp_documents(text, path):
        if not isinstance(doc, dict) or "resourceLogs" not in doc:
            continue
        where = f"{path}: line {line}"
        for i, rl in enumerate(_otlp_list(doc, "resourceLogs", f"{where}: ")):
            at = f"resourceLogs[{i}]"
            rl = _otlp_object(rl, f"{where}: {at}")
            resource = _otlp_object(rl.get("resource"), f"{where}: {at}.resource")
            base = _otlp_attributes(resource, f"{where}: {at}.resource.")
            for j, sl in enumerate(_otlp_list(rl, "scopeLogs", f"{where}: {at}.")):
                at_sl = f"{at}.scopeLogs[{j}]"
                sl = _otlp_object(sl, f"{where}: {at_sl}")
                for k, rec in enumerate(_otlp_list(sl, "logRecords", f"{where}: {at_sl}.")):
                    at_rec = f"{at_sl}.logRecords[{k}]"
                    rec = _otlp_object(rec, f"{where}: {at_rec}")
                    attrs = {**base, **_otlp_attributes(rec, f"{where}: {at_rec}.")}
                    body = rec.get("body")
                    is_request = attrs.get("event.name") == "api_request" or (
                        isinstance(body, dict)
                        and body.get("stringValue") == "claude_code.api_request"
                    )
                    if not is_request:
                        continue
                    micros = _otlp_micros(attrs, where)
                    yield ApiRequest(
                        agent=_otlp_str(attrs, "agent.name") or "main",
                        model=_otlp_str(attrs, "model") or "",
                        input_tokens=_otlp_int(attrs, "input_tokens", where),
                        output_tokens=_otlp_int(attrs, "output_tokens", where),
                        cache_read_tokens=_otlp_int(attrs, "cache_read_tokens", where),
                        cache_creation_tokens=_otlp_int(attrs, "cache_creation_tokens", where),
                        cost_usd_micros=0 if micros is None else micros,
                        session_id=_otlp_str(attrs, "session.id"),
                        workflow_run_id=_otlp_str(attrs, "workflow.run_id"),
                        cost_missing=micros is None,
                        effort=_otlp_str(attrs, "effort"),
                    )


# --- phases and the summary --------------------------------------------------------------


def phase_for(agent: str) -> str:
    """The phase an agent's requests count under; any ``<plugin>:`` prefix is ignored."""
    return AGENT_PHASES.get(agent.rpartition(":")[2], "unattributed")


class _Tally:
    def __init__(self) -> None:
        self.counts = dict.fromkeys(_COUNTERS, 0)
        self.micros = 0

    def add(self, r: ApiRequest) -> None:
        self.counts["requests"] += 1
        for name in _TOKENS:
            self.counts[name] += getattr(r, name)
        self.micros += r.cost_usd_micros

    def render(self) -> dict[str, Any]:
        return {**self.counts, "cost_usd": self.micros / 1e6}


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as fh:
            for chunk in iter(lambda: fh.read(1 << 20), b""):
                digest.update(chunk)
    except OSError as exc:
        raise UsageParseError(f"{path}: cannot read: {exc.strerror or exc}") from exc
    return digest.hexdigest()


def summarize_usage(
    requests: Iterable[ApiRequest], *, source: Path, workflow_run: str | None = None
) -> dict[str, Any]:
    """The ``usage.yaml`` summary of ``requests`` (read from ``source``).

    With ``workflow_run`` only requests whose ``workflow.run_id`` equals it
    count; ``source`` still describes the whole file. ``cost_usd`` is micros /
    1e6. ``decision_models`` and ``cost_usd_all`` are added by the command,
    from ``summarize_decisions``.
    """
    every = list(requests)
    runs = sorted({r.workflow_run_id for r in every if r.workflow_run_id is not None})
    chosen = [r for r in every if workflow_run is None or r.workflow_run_id == workflow_run]
    totals = _Tally()
    agents: dict[str, _Tally] = {}
    phases: dict[str, _Tally] = {}
    for r in chosen:
        totals.add(r)
        agents.setdefault(r.agent, _Tally()).add(r)
        phases.setdefault(phase_for(r.agent), _Tally()).add(r)
    warnings: list[str] = []
    redacted = sum(1 for r in chosen if r.agent.rpartition(":")[2] in REDACTED_AGENTS)
    if redacted:
        warnings.append(
            f"agent names redacted on {redacted} requests ('custom'/'third-party'): set "
            "OTEL_LOG_TOOL_DETAILS=1 and use Claude Code 2.1.273 or later"
        )
    if workflow_run is None and len(runs) > 1:
        warnings.append(
            f"multiple workflow runs in this file ({', '.join(runs)}): pass --workflow-run"
        )
    missing = sum(1 for r in chosen if r.cost_missing)
    if missing:
        warnings.append(f"{missing} requests carried no cost attribute")
    return {
        "schema_version": 1,
        "generated_by": "apd-gauntlet usage",
        "source": {
            "file": str(source),
            "sha256": _file_sha256(source),
            "api_requests": len(every),
            "sessions": sorted({r.session_id for r in every if r.session_id is not None}),
            "workflow_runs": runs,
        },
        "filter": {"workflow_run": workflow_run},
        "totals": totals.render(),
        "by_agent": {
            agent: {"phase": phase_for(agent), **agents[agent].render()}
            for agent in sorted(agents)
        },
        "by_phase": {phase: phases[phase].render() for phase in sorted(phases)},
        "warnings": warnings,
    }


def write_usage(run_dir: Path, summary: Mapping[str, Any]) -> Path:
    """Write ``summary`` to ``<run_dir>/.apd-state/usage.yaml`` and return the path.

    Creates ``.apd-state/`` (``run_dir`` itself must exist) and replaces any
    earlier file; the text is written beside it and then moved into place, so a
    failed write leaves the earlier file intact. Raises ``OSError`` on failure.
    """
    text = yaml.safe_dump(dict(summary), sort_keys=False, allow_unicode=True)
    path = run_dir / USAGE_RELPATH
    partial = path.with_name(path.name + ".tmp")
    try:
        path.parent.mkdir(exist_ok=True)
        partial.write_text(text, encoding="utf-8")
        partial.replace(path)
    except OSError:
        with contextlib.suppress(OSError):  # e.g. .apd-state is a file
            partial.unlink(missing_ok=True)
        raise
    return path


# --- decision-model spend (register A12.8) ------------------------------------------------


def _decision_usage(path: Path) -> tuple[str, str, dict[str, int], float]:
    """``(task, cost_basis, {calls, input_tokens}, cost_usd)`` of one decision record."""
    try:
        doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    except UnicodeDecodeError as exc:
        raise UsageParseError(f"{path}: not UTF-8 text: {exc}") from exc
    except OSError as exc:
        raise UsageParseError(f"{path}: cannot read: {exc.strerror or exc}") from exc
    except (yaml.YAMLError, ValueError) as exc:  # ValueError: e.g. an impossible date
        raise UsageParseError(f"{path}: invalid YAML: {exc}") from exc
    except RecursionError as exc:
        raise UsageParseError(f"{path}: invalid YAML: nested too deeply to parse") from exc
    if not isinstance(doc, dict):
        raise UsageParseError(f"{path}: top level is not a mapping")
    usage = doc.get("usage")
    if usage is None:
        usage = {}
    if not isinstance(usage, dict):
        raise UsageParseError(f"{path}: usage is not a mapping")
    counts: dict[str, int] = {}
    for name in _DECISION_COUNTERS:
        value = usage.get(name)
        if value is not None and (isinstance(value, bool) or not isinstance(value, int)):
            raise UsageParseError(
                f"{path}: usage.{name} is not a whole number: {_shown(value)}"
            )
        counts[name] = value or 0
    cost = usage.get("cost_usd")
    if cost is not None and (
        isinstance(cost, bool) or not isinstance(cost, (int, float)) or not math.isfinite(cost)
    ):
        raise UsageParseError(f"{path}: usage.cost_usd is not a number: {_shown(cost)}")
    task, basis = doc.get("task"), usage.get("cost_basis")
    return (
        task if isinstance(task, str) else "unknown",
        basis if isinstance(basis, str) else "unknown",
        counts,
        float(cost or 0.0),
    )


def _decision_bucket() -> dict[str, Any]:
    return {"calls": 0, "input_tokens": 0, "cost_usd": 0.0}


def summarize_decisions(run_dir: Path) -> dict[str, Any]:
    """The ``decision_models`` block of ``usage.yaml`` (register A12.8).

    Totals of ``calls``, ``input_tokens`` and ``cost_usd`` over the ``usage``
    block of every ``<run>/40-synthesis/decisions/*.yaml`` record, and the same
    counters ``by_task`` and ``by_cost_basis``. With no records the totals are
    zero and both mappings are empty. A missing ``input_tokens`` or
    ``cost_usd`` counts as 0, so ``by_cost_basis.unknown`` shows the calls
    whose cost is not known. A record that cannot be read or whose ``usage`` is
    malformed raises ``UsageParseError`` naming it.
    """
    folder = run_dir / DECISIONS_RELDIR
    try:
        files = sorted(p for p in folder.iterdir() if p.name.endswith(".yaml"))
    except FileNotFoundError:
        files = []
    except OSError as exc:
        raise UsageParseError(f"{folder}: cannot read: {exc.strerror or exc}") from exc
    totals = _decision_bucket()
    by_task: dict[str, dict[str, Any]] = {}
    by_basis: dict[str, dict[str, Any]] = {}
    for path in files:
        task, basis, counts, cost = _decision_usage(path)
        for bucket in (totals, by_task.setdefault(task, _decision_bucket()),
                       by_basis.setdefault(basis, _decision_bucket())):
            for name, n in counts.items():
                bucket[name] += n
            bucket["cost_usd"] += cost
    for bucket in (totals, *by_task.values(), *by_basis.values()):
        bucket["cost_usd"] = round(bucket["cost_usd"], 9)
    return {
        "totals": totals,
        "by_task": {k: by_task[k] for k in sorted(by_task)},
        "by_cost_basis": {k: by_basis[k] for k in sorted(by_basis)},
    }
