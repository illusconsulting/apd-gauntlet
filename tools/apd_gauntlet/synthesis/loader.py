"""Shared corpus loader for the synthesis decomposition commands.

Based on ``cli._load_records`` but adds an ``include_attack_path`` flag so
``cluster-candidates`` and ``rollup`` can pull the tier-4 corpus —
``40-synthesis/attack-path.findings.yaml`` (apath-*) and
``40-threat-model/threat-model.findings.yaml`` (tmeval-*) — which
``cli._load_records`` SKIPS to avoid re-ingestion during attack-path analysis.

Same discipline as ``cli._load_records``: singular root key ``finding`` /
``capability`` (legacy plural accepted defensively), warn-on-malformed via
``click.echo(err=True)``, skip records missing ``id``.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import click
import yaml


def _records(raw: Any) -> list[dict[str, Any]]:
    return raw if isinstance(raw, list) else ([raw] if isinstance(raw, dict) else [])


def load_corpus(
    run_dir: Path,
    *,
    include_attack_path: bool = False,
) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:
    """Index findings by ``id`` and collect capabilities across the run.

    With ``include_attack_path=False`` (default) the analyzer's own
    ``40-synthesis/attack-path.findings.yaml`` is excluded (matching
    ``cli._load_records``). With ``include_attack_path=True`` it IS included,
    along with ``40-threat-model/threat-model.findings.yaml`` — both required
    by the rollup matrix/nist steps and the clustering corpus per spec
    Steps 2/8.
    """
    findings_by_id: dict[str, dict[str, Any]] = {}
    capabilities: list[dict[str, Any]] = []
    for f in sorted(run_dir.glob("**/*.findings.yaml")):
        is_apath = "40-synthesis" in f.parts and f.name == "attack-path.findings.yaml"
        if is_apath and not include_attack_path:
            continue
        doc = yaml.safe_load(f.read_text(encoding="utf-8")) or {}
        raw = doc.get("finding")
        if raw is None:
            raw = doc.get("findings")
        for idx, rec in enumerate(_records(raw)):
            if not isinstance(rec, dict):
                click.echo(f"WARNING: {f}: finding[{idx}] is not a dict; skipping", err=True)
                continue
            if "id" not in rec:
                click.echo(f"WARNING: {f}: finding[{idx}] missing 'id'; skipping", err=True)
                continue
            findings_by_id[rec["id"]] = rec
    for f in sorted(run_dir.glob("**/*.capabilities.yaml")):
        doc = yaml.safe_load(f.read_text(encoding="utf-8")) or {}
        raw = doc.get("capability")
        if raw is None:
            raw = doc.get("capabilities")
        for idx, rec in enumerate(_records(raw)):
            if not isinstance(rec, dict):
                click.echo(f"WARNING: {f}: capability[{idx}] is not a dict; skipping", err=True)
                continue
            if "id" not in rec:
                click.echo(f"WARNING: {f}: capability[{idx}] missing 'id'; skipping", err=True)
                continue
            capabilities.append(rec)
    return findings_by_id, capabilities
