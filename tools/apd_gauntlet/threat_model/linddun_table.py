"""Parser for LINDDUN privacy threat-model tables (Markdown + CSV)."""

from __future__ import annotations

import csv
import hashlib
import io
from pathlib import Path
from typing import Any

from .mappings import linddun_letter_to_apd_goals

_POSITION_TO_COMPOUND: dict[int, str] = {
    1: "L",
    2: "I",
    3: "N_repudiation",
    4: "D_etectability",
    5: "D_isclosure",
    6: "U",
    7: "N_compliance",
}

_LINDDUN_FULLNAMES_TO_COMPOUND: dict[str, str] = {
    "LINKABILITY":               "L",
    "LINK":                      "L",
    "IDENTIFIABILITY":           "I",
    "IDENT":                     "I",
    "NON-REPUDIATION":           "N_repudiation",
    "NONREPUDIATION":            "N_repudiation",
    "NON_REPUDIATION":           "N_repudiation",
    "NONREP":                    "N_repudiation",
    "DETECTABILITY":             "D_etectability",
    "DETECT":                    "D_etectability",
    "DISCLOSURE OF INFORMATION": "D_isclosure",
    "DISCLOSURE":                "D_isclosure",
    "DISCLOSE":                  "D_isclosure",
    "UNAWARENESS":               "U",
    "UNAWARE":                   "U",
    "NON-COMPLIANCE":            "N_compliance",
    "NONCOMPLIANCE":             "N_compliance",
    "NONCOMPLY":                 "N_compliance",
}

_LINDDUN_DETECTOR_KEYWORDS: frozenset[str] = frozenset({
    "LINKABILITY", "IDENTIFIABILITY", "DETECTABILITY",
    "DISCLOSURE", "UNAWARENESS", "NON-COMPLIANCE", "NONCOMPLIANCE",
    "LINDDUN",
})

_EMPTY_CELL_VALUES: frozenset[str] = frozenset({
    "", "—", "-", "–", "N/A", "NONE",
})


def _is_empty_cell(cell: str) -> bool:
    return cell.strip().upper() in _EMPTY_CELL_VALUES


def _normalize_column_header(header: str, column_position: int) -> str | None:
    """Return the LINDDUN compound-key for this column, or None if not a LINDDUN column.

    For single-letter headers (``L``, ``I``, ``N``, ``D``, ``D``, ``U``, ``N``), uses
    column_position to disambiguate the duplicates. For full names, uses
    the name lookup table and ignores position.
    """
    if not header:
        return None
    cleaned = header.strip().upper()
    # Full-name match first (unambiguous)
    if cleaned in _LINDDUN_FULLNAMES_TO_COMPOUND:
        return _LINDDUN_FULLNAMES_TO_COMPOUND[cleaned]
    # Single-letter match: disambiguate via position
    if cleaned in {"L", "I", "N", "D", "U"}:
        return _POSITION_TO_COMPOUND.get(column_position)
    return None


def is_linddun_table(headers: list[str]) -> bool:
    """Heuristic: is this header row from a LINDDUN table?

    Returns True if any header matches a LINDDUN-specific keyword OR the
    headers (excluding the label column) form the canonical L-I-N-D-D-U-N
    pattern.
    """
    upper_headers = [h.strip().upper() for h in headers]
    if any(h in _LINDDUN_DETECTOR_KEYWORDS for h in upper_headers):
        return True
    # Canonical 7-letter pattern check (skip first column = label)
    letter_only = [h for h in upper_headers[1:] if h in {"L", "I", "N", "D", "U"}]
    return letter_only == ["L", "I", "N", "D", "D", "U", "N"]


def _stable_entry_id(asset: str, threat: str, locator: str) -> str:
    raw = f"{asset}|{threat}|{locator}".encode()
    return f"tm-{hashlib.sha256(raw).hexdigest()[:8]}"


def _row_to_entries(
    headers: list[str | None], row: list[str], row_index: int
) -> list[dict[str, Any]]:
    if not row:
        return []
    asset = row[0].strip() if row else ""
    if not asset:
        return []
    entries: list[dict[str, Any]] = []
    for col_idx, cell in enumerate(row[1:], start=1):
        if col_idx >= len(headers):
            break
        compound_key = headers[col_idx]
        if compound_key is None:
            continue
        if _is_empty_cell(cell):
            continue
        locator = f"row[{row_index}].column[{col_idx}]"
        entries.append({
            "entry_id": _stable_entry_id(asset, cell.strip(), locator),
            "asset": asset,
            "threat": cell.strip(),
            "mitigation": None,
            "methodology": "linddun",
            "source_locator": locator,
            "extraction_confidence": "high",
            "framework_refs": {
                "stride_letter": None,
                "linddun_letter": compound_key,
                "attack_tree_position": None,
                "mitre_attack": [],
            },
            "inferred_apd_goals": linddun_letter_to_apd_goals(compound_key),
        })
    return entries


def parse_linddun_markdown(text: str) -> list[dict[str, Any]]:
    """Parse a Markdown table into LINDDUN entries.

    Lenient parser: ignores non-table lines (prose, headings), skips the
    ``|---|---|`` separator row, treats any pipe-delimited row as data.
    """
    rows: list[list[str]] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped.startswith("|") or not stripped.endswith("|"):
            continue
        cells = [c.strip() for c in stripped.split("|")[1:-1]]
        if all(set(c) <= set("-:") for c in cells if c):
            continue
        rows.append(cells)
    if not rows:
        return []
    headers = [_normalize_column_header(h, i) for i, h in enumerate(rows[0])]
    entries: list[dict[str, Any]] = []
    for i, row in enumerate(rows[1:], start=1):
        entries.extend(_row_to_entries(headers, row, i))
    return entries


def parse_linddun_csv(text: str) -> list[dict[str, Any]]:
    """Parse a CSV file into LINDDUN entries (stdlib csv module)."""
    reader = csv.reader(io.StringIO(text))
    rows = list(reader)
    if not rows:
        return []
    headers = [_normalize_column_header(h, i) for i, h in enumerate(rows[0])]
    entries: list[dict[str, Any]] = []
    for i, row in enumerate(rows[1:], start=1):
        entries.extend(_row_to_entries(headers, row, i))
    return entries


def parse_linddun_table(path: Path) -> list[dict[str, Any]]:
    """Dispatch based on file extension."""
    suffix = path.suffix.lower()
    text = path.read_text(encoding="utf-8")
    if suffix == ".md":
        return parse_linddun_markdown(text)
    if suffix == ".csv":
        return parse_linddun_csv(text)
    raise ValueError(f"Unsupported LINDDUN table file extension: {suffix}")
