"""Read a finished run directory into a ``RunSnapshot`` for comparison.

The snapshot holds what a before-and-after comparison needs: findings and
capabilities by id (the whole corpus, attack-path and threat-model findings
included), the asset-graph node names each record's edges target, the report
headlines expanded through ``merged_from``, and a digest of ``inputs/`` so runs
over different inputs are never compared.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from ..synthesis.loader import load_corpus


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


def inputs_digest(run_dir: Path) -> str | None:
    """SHA-256 over every file under ``<run>/inputs/``; ``None`` when it is absent.

    Each file contributes the line ``"<posix path relative to inputs/>\\0<sha256>\\n"``;
    the lines are sorted before hashing, so the digest depends only on paths and bytes.
    """
    inputs = run_dir / "inputs"
    if not inputs.is_dir():
        return None
    lines = sorted(
        f"{p.relative_to(inputs).as_posix()}\0{hashlib.sha256(p.read_bytes()).hexdigest()}\n"
        for p in inputs.rglob("*")
        if p.is_file()
    )
    return hashlib.sha256("".join(lines).encode("utf-8", "surrogateescape")).hexdigest()


def _parse(path: Path) -> Any:
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise RunLoadError(f"{path}: invalid YAML: {exc}") from exc


def _corpus_files(run_dir: Path) -> list[Path]:
    """The files ``load_corpus`` reads, in the order it reads them."""
    return sorted(run_dir.glob("**/*.findings.yaml")) + sorted(
        run_dir.glob("**/*.capabilities.yaml")
    )


def _load_corpus(
    run_dir: Path,
) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    try:
        findings, capabilities = load_corpus(run_dir, include_attack_path=True)
    except yaml.YAMLError as exc:
        for f in _corpus_files(run_dir):
            _parse(f)  # raises RunLoadError naming the first unreadable file
        raise RunLoadError(f"{run_dir}: invalid YAML: {exc}") from exc
    return findings, {c["id"]: c for c in capabilities}


def _records(doc: Any, key: str) -> list[dict[str, Any]]:
    if not isinstance(doc, dict):
        return []
    raw = doc.get(key)
    if raw is None:
        raw = doc.get(key + "s")
    items = raw if isinstance(raw, list) else [raw]
    return [r for r in items if isinstance(r, dict)]


def _graph_targets(graph: Any) -> dict[str, list[str]]:
    """Map each ``finding_id``/``capability_id`` on an edge to its ``to`` node's name."""
    if not isinstance(graph, dict):
        return {}
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


def _headlines(report_data: Any, deduped: Any) -> tuple[frozenset[str], ...]:
    """Headline ids in ``rank`` order, each expanded through ``merged_from``."""
    merged: dict[str, frozenset[str]] = {}
    for rec in _records(deduped, "finding"):
        rid, members = rec.get("id"), rec.get("merged_from")
        if isinstance(rid, str) and isinstance(members, list) and members:
            merged[rid] = frozenset(str(m) for m in members)
    raw = report_data.get("headline_findings") if isinstance(report_data, dict) else None
    entries = [
        h for h in (raw if isinstance(raw, list) else [])
        if isinstance(h, dict) and isinstance(h.get("id"), str)
    ]
    entries.sort(key=_rank)
    return tuple(merged.get(h["id"], frozenset({h["id"]})) for h in entries)


def load_run(path: Path) -> RunSnapshot:
    """Read the run directory at ``path``.

    A ``yaml.YAMLError`` in any file read becomes ``RunLoadError`` naming that file.
    ``headlines`` is ``None`` when ``report-data.yaml`` or ``deduped-findings.yaml``
    is missing; ``inputs_sha256`` is ``None`` when the run has no ``inputs/``.
    """
    findings, capabilities = _load_corpus(path)
    synth = path / "40-synthesis"
    graph_file = synth / "asset-graph.yaml"
    graph_targets = _graph_targets(_parse(graph_file)) if graph_file.is_file() else {}
    report_file = synth / "report-data.yaml"
    deduped_file = synth / "deduped-findings.yaml"
    headlines = (
        _headlines(_parse(report_file), _parse(deduped_file))
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
