"""Format detection + parser dispatch for threat models."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from . import attack_tree, linddun_table, microsoft_tmt, stride_table, threat_dragon
from .linddun_table import is_linddun_table

_SUPPORTED_HINTS: frozenset[str] = frozenset({
    "stride", "linddun", "attack_tree", "pasta", "vast", "trike", "free_form",
})


def dispatch_parser(path: Path, hint: str | None = None) -> dict[str, Any]:
    """Parse a threat model file. Returns the normalized envelope dict.

    Raises ValueError if `hint` is provided but unrecognized.
    Returns free-form-fallback envelope if the format cannot be auto-detected
    (or hint requests it explicitly) — the recon agent then does LLM extraction.
    """
    if hint is not None and hint not in _SUPPORTED_HINTS:
        raise ValueError(
            f"unknown methodology hint '{hint}'; expected one of {sorted(_SUPPORTED_HINTS)}"
        )

    if hint in ("pasta", "vast", "trike", "free_form"):
        return _free_form_envelope(path, methodology=hint)

    suffix = path.suffix.lower()
    # Special suffix handling for .adtool.xml (compound extension)
    name_lower = path.name.lower()
    if name_lower.endswith(".adtool.xml"):
        suffix = ".adtool.xml"

    methodology, parser_id, entries = _detect_and_parse(path, suffix, hint)

    envelope = {
        "schema_version": 1,
        "generated_by": "threat_model_recon",
        "source_artifact": str(path),
        "methodology": methodology,
        "extraction_summary": _summarize(entries, parser_id),
        "entries": entries,
    }
    return envelope


def _detect_and_parse(
    path: Path, suffix: str, hint: str | None
) -> tuple[str, str, list[dict[str, Any]]]:
    """Return (methodology, parser_id, entries) tuple."""
    # Hint disambiguates ambiguous extensions
    methodology = hint  # may be None; resolved below

    if suffix == ".tm7":
        return "stride", "microsoft_tmt", microsoft_tmt.parse_microsoft_tmt(path.read_bytes())

    if suffix == ".adtool.xml":
        return (
            "attack_tree",
            "attack_tree.adtool_xml",
            attack_tree.parse_adtool_xml(path.read_bytes()),
        )

    if suffix == ".xml":
        # Could be ADTool or something else; sniff for <adtree> root
        content = path.read_bytes()
        if b"<adtree" in content[:512]:
            return "attack_tree", "attack_tree.adtool_xml", attack_tree.parse_adtool_xml(content)
        # Unknown XML — fall back to free_form
        return "free_form", "none — unrecognized XML", []

    if suffix == ".json":
        data = json.loads(path.read_text(encoding="utf-8"))
        # Threat Dragon shape: {summary, detail: {diagrams}}
        detail = data.get("detail") or {}
        is_threat_dragon = (
            isinstance(data, dict)
            and "summary" in data
            and "detail" in data
            and "diagrams" in detail
        )
        if is_threat_dragon:
            return "stride", "threat_dragon", threat_dragon.parse_threat_dragon(data)
        # Attack-tree shape: {goal, children}
        if isinstance(data, dict) and "goal" in data and "children" in data:
            return "attack_tree", "attack_tree.json", attack_tree.parse_attack_tree_json(data)
        # Honor hint if provided; otherwise fall back to free_form
        if methodology == "stride":
            return "stride", "threat_dragon", threat_dragon.parse_threat_dragon(data)
        if methodology == "attack_tree":
            return "attack_tree", "attack_tree.json", attack_tree.parse_attack_tree_json(data)
        return "free_form", "none — unrecognized JSON shape", []

    if suffix in (".md", ".csv"):
        text = path.read_text(encoding="utf-8")
        # Sniff for LINDDUN first (more specific keywords)
        headers = _sniff_table_headers(text, suffix)
        if methodology == "linddun" or (methodology is None and is_linddun_table(headers)):
            parser_fn = (
                linddun_table.parse_linddun_markdown
                if suffix == ".md"
                else linddun_table.parse_linddun_csv
            )
            return "linddun", f"linddun_table.{suffix[1:]}", parser_fn(text)
        # Default to STRIDE
        parser_fn = (
            stride_table.parse_stride_markdown if suffix == ".md" else stride_table.parse_stride_csv
        )
        return "stride", f"stride_table.{suffix[1:]}", parser_fn(text)

    if suffix == ".txt":
        return (
            "attack_tree",
            "attack_tree.indented_prose",
            attack_tree.parse_indented_prose(path.read_text(encoding="utf-8")),
        )

    # Unknown extension
    return "free_form", "none — unrecognized extension", []


def _sniff_table_headers(text: str, suffix: str) -> list[str]:
    """Return the first non-blank table row's cells as a list, for methodology detection."""
    if suffix == ".csv":
        import csv
        import io
        reader = csv.reader(io.StringIO(text))
        for row in reader:
            if row and any(c.strip() for c in row):
                return row
        return []
    # Markdown
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("|") and stripped.endswith("|"):
            cells = [c.strip() for c in stripped.split("|")[1:-1]]
            # Skip separator row
            if all(set(c) <= set("-:") for c in cells if c):
                continue
            return cells
    return []


def _free_form_envelope(path: Path, methodology: str) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "generated_by": "threat_model_recon",
        "source_artifact": str(path),
        "methodology": methodology,
        "extraction_summary": {
            "entry_count": 0,
            "high_confidence_count": 0,
            "medium_confidence_count": 0,
            "low_confidence_count": 0,
            "parser_used": "none — LLM extraction required",
        },
        "entries": [],
    }


def _summarize(entries: list[dict[str, Any]], parser_id: str) -> dict[str, Any]:
    def count(level: str) -> int:
        return sum(1 for e in entries if e.get("extraction_confidence") == level)
    return {
        "entry_count": len(entries),
        "high_confidence_count": count("high"),
        "medium_confidence_count": count("medium"),
        "low_confidence_count": count("low"),
        "parser_used": parser_id,
    }
