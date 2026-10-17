"""Read a finished run directory into a ``RunSnapshot`` for comparison.

The snapshot holds what a before-and-after comparison needs: findings and
capabilities by id (the whole corpus, attack-path and threat-model findings
included), the asset-graph node names each record's edges target, the report
headlines expanded through ``merged_from``, and a digest of ``inputs/`` so runs
over different inputs are never compared.
"""
from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from ..synthesis.loader import load_corpus

_CHUNK = 1 << 20


class RunLoadError(Exception):
    """A run directory could not be read; the message names the file."""


@dataclass(frozen=True)
class RunSnapshot:
    path: Path
    findings: dict[str, dict[str, Any]]
    capabilities: dict[str, dict[str, Any]]
    graph_targets: dict[str, list[str]]
    headlines: tuple[frozenset[str], ...] | None
    inputs_sha256: str | None


def is_run_dir(path: Path) -> bool:
    """A run directory is one that holds ``.apd-run.yaml``."""
    return (path / ".apd-run.yaml").is_file()


def _unreadable(path: object, exc: OSError) -> RunLoadError:
    return RunLoadError(f"{path}: cannot read: {exc.strerror or exc}")


def _walk_error(exc: OSError) -> None:
    raise _unreadable(exc.filename, exc) from exc


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as fh:
            for chunk in iter(lambda: fh.read(_CHUNK), b""):
                digest.update(chunk)
    except OSError as exc:
        raise _unreadable(path, exc) from exc
    return digest.hexdigest()


def inputs_digest(run_dir: Path) -> str | None:
    """SHA-256 over every file under ``<run>/inputs/``; ``None`` when it is absent.

    Each file contributes the line ``"<posix path relative to inputs/>\\0<sha256>\\n"``;
    the lines are sorted before hashing, so the digest depends only on paths and bytes.
    Dotfiles count like any other file. A file or directory that cannot be read
    raises ``RunLoadError`` naming it, so no file is silently left out.
    """
    inputs = run_dir / "inputs"
    if not inputs.is_dir():
        return None
    lines: list[str] = []
    for root, _dirs, files in os.walk(inputs, onerror=_walk_error):
        for name in files:
            p = Path(root, name)
            if p.is_file():
                lines.append(f"{p.relative_to(inputs).as_posix()}\0{_file_sha256(p)}\n")
    lines.sort()
    return hashlib.sha256("".join(lines).encode("utf-8", "surrogateescape")).hexdigest()


def _parse(path: Path) -> Any:
    """Parse one YAML file; any read or parse failure becomes ``RunLoadError``."""
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise RunLoadError(f"{path}: not UTF-8 text: {exc}") from exc
    except OSError as exc:
        raise _unreadable(path, exc) from exc
    try:
        return yaml.safe_load(text)
    except (yaml.YAMLError, ValueError) as exc:  # ValueError: e.g. an impossible date
        raise RunLoadError(f"{path}: invalid YAML: {exc}") from exc


def _not_a_mapping(path: Path, doc: Any) -> RunLoadError:
    return RunLoadError(f"{path}: top level is a {type(doc).__name__}, not a mapping")


def _parse_mapping(path: Path) -> dict[str, Any]:
    """``_parse`` a file whose top level must be a mapping; an empty file is ``{}``."""
    doc = _parse(path)
    if doc is None:
        return {}
    if not isinstance(doc, dict):
        raise _not_a_mapping(path, doc)
    return doc


def _corpus_files(run_dir: Path) -> list[Path]:
    """The files ``load_corpus`` reads, in the order it reads them."""
    return sorted(run_dir.glob("**/*.findings.yaml")) + sorted(
        run_dir.glob("**/*.capabilities.yaml")
    )


def _records(doc: dict[str, Any], key: str) -> list[dict[str, Any]]:
    raw = doc.get(key)
    if raw is None:
        raw = doc.get(key + "s")
    items = raw if isinstance(raw, list) else [raw]
    return [r for r in items if isinstance(r, dict)]


def _corpus_problem(run_dir: Path) -> RunLoadError | None:
    """The error for the first corpus file ``load_corpus`` cannot use, if any.

    A file fails when it cannot be read or parsed, when its top level is not a
    mapping (``load_corpus`` reads every falsy document as empty), or when a
    record's ``id`` is not a string.
    """
    for f in _corpus_files(run_dir):
        try:
            doc = _parse(f) or {}
        except RunLoadError as exc:
            return exc
        if not isinstance(doc, dict):
            return _not_a_mapping(f, doc)
        key = "finding" if f.name.endswith(".findings.yaml") else "capability"
        for rec in _records(doc, key):
            rid = rec.get("id", "")
            if not isinstance(rid, str):
                return RunLoadError(f"{f}: a {key} id is a {type(rid).__name__}, not a string")
    return None


def _load_corpus(
    run_dir: Path,
) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    try:
        findings, capabilities = load_corpus(run_dir, include_attack_path=True)
    except (yaml.YAMLError, ValueError, OSError, AttributeError, TypeError) as exc:
        problem = _corpus_problem(run_dir)
        if problem is None:
            raise
        raise problem from exc
    if not all(isinstance(rid, str) for rid in findings) or not all(
        isinstance(c["id"], str) for c in capabilities
    ):
        raise _corpus_problem(run_dir) or RunLoadError(f"{run_dir}: a record id is not a string")
    return findings, {c["id"]: c for c in capabilities}


def _graph_targets(graph: dict[str, Any]) -> dict[str, list[str]]:
    """Map each ``finding_id``/``capability_id`` on an edge to its ``to`` node's name."""
    nodes = graph.get("nodes")
    edges = graph.get("edges")
    names: dict[str, str] = {}
    for node in nodes if isinstance(nodes, list) else []:
        if isinstance(node, dict):
            node_id, name = node.get("node_id"), node.get("name")
            if isinstance(node_id, str) and isinstance(name, str):
                names[node_id] = name
    targets: dict[str, list[str]] = {}
    for edge in edges if isinstance(edges, list) else []:
        if not isinstance(edge, dict):
            continue
        to = edge.get("to")
        name = names.get(to) if isinstance(to, str) else None
        if name is None:
            continue
        for key in ("finding_id", "capability_id"):
            rid = edge.get(key)
            if isinstance(rid, str):
                listed = targets.setdefault(rid, [])
                if name not in listed:
                    listed.append(name)
    return targets


def _rank(entry: dict[str, Any]) -> tuple[int, int]:
    rank = entry.get("rank")
    return (0, rank) if isinstance(rank, int) else (1, 0)


def _headlines(
    report_data: dict[str, Any], deduped: dict[str, Any]
) -> tuple[frozenset[str], ...]:
    """Headline ids in ``rank`` order, each expanded through ``merged_from``.

    Only string members count; an id with none expands to itself.
    """
    merged: dict[str, frozenset[str]] = {}
    for rec in _records(deduped, "finding"):
        rid, members = rec.get("id"), rec.get("merged_from")
        if isinstance(rid, str) and isinstance(members, list):
            ids = frozenset(m for m in members if isinstance(m, str))
            if ids:
                merged[rid] = ids
    raw = report_data.get("headline_findings")
    entries = [
        h for h in (raw if isinstance(raw, list) else [])
        if isinstance(h, dict) and isinstance(h.get("id"), str)
    ]
    entries.sort(key=_rank)
    return tuple(merged.get(h["id"], frozenset({h["id"]})) for h in entries)


def load_run(path: Path) -> RunSnapshot:
    """Read the run directory at ``path``.

    Any file that cannot be read or parsed (``yaml.YAMLError``, a ``ValueError``
    from PyYAML, text that is not UTF-8, an ``OSError``), or whose top level is
    not a mapping, becomes ``RunLoadError`` naming that file; so does a corpus
    record whose ``id`` is not a string. ``headlines`` is ``None`` when
    ``report-data.yaml`` or ``deduped-findings.yaml`` is missing;
    ``inputs_sha256`` is ``None`` when the run has no ``inputs/``.
    """
    findings, capabilities = _load_corpus(path)
    synth = path / "40-synthesis"
    graph_file = synth / "asset-graph.yaml"
    graph_targets = _graph_targets(_parse_mapping(graph_file)) if graph_file.is_file() else {}
    report_file = synth / "report-data.yaml"
    deduped_file = synth / "deduped-findings.yaml"
    headlines = (
        _headlines(_parse_mapping(report_file), _parse_mapping(deduped_file))
        if report_file.is_file() and deduped_file.is_file()
        else None
    )
    return RunSnapshot(
        path=path,
        findings=findings,
        capabilities=capabilities,
        graph_targets=graph_targets,
        headlines=headlines,
        inputs_sha256=inputs_digest(path),
    )
