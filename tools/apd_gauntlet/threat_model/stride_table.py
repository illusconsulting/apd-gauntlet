"""Parser for STRIDE-per-element threat-model tables (Markdown + CSV)."""

from __future__ import annotations

import csv
import hashlib
import io
from pathlib import Path
from typing import Any

from .mappings import stride_letter_to_apd_goals

_STRIDE_HEADER_TO_LETTER: dict[str, str] = {
    "S": "S", "SPOOFING": "S", "SPOOF": "S",
    "T": "T", "TAMPERING": "T", "TAMPER": "T",
    "R": "R", "REPUDIATION": "R", "REPUD": "R",
    "I": "I", "INFORMATION DISCLOSURE": "I", "INFO DISC": "I", "INFODISC": "I", "DISCLOSURE": "I",
    "D": "D", "DENIAL OF SERVICE": "D", "DOS": "D", "DENIAL": "D",
    "E": "E", "ELEVATION OF PRIVILEGE": "E", "EOP": "E", "ELEVATION": "E",
}

_EMPTY_CELL_VALUES: frozenset[str] = frozenset({
    "", "—", "-", "–", "N/A", "NONE",
})


def _normalize_column_header(header: str) -> str | None:
    """Map a column header string to a STRIDE letter, or None if not a STRIDE column."""
    if not header:
        return None
    return _STRIDE_HEADER_TO_LETTER.get(header.strip().upper())


def _is_empty_cell(cell: str) -> bool:
    """True if the cell represents 'no threat in this STRIDE category for this element'."""
    return cell.strip().upper() in _EMPTY_CELL_VALUES


def _stable_entry_id(asset: str, threat: str, locator: str) -> str:
    raw = f"{asset}|{threat}|{locator}".encode()
    return f"tm-{hashlib.sha256(raw).hexdigest()[:8]}"


def _row_to_entries(
    headers: list[str | None],
    row: list[str],
    row_index: int,
) -> list[dict[str, Any]]:
    """Convert one data row to zero-or-more STRIDE entries.

    `headers[0]` is None (the label column); subsequent items are STRIDE letters.
    """
    if not row:
        return []
    asset = row[0].strip() if row else ""
    if not asset:
        return []
    entries: list[dict[str, Any]] = []
    for col_idx, cell in enumerate(row[1:], start=1):
        if col_idx >= len(headers):
            break
        letter = headers[col_idx]
        if letter is None:
            continue  # column header wasn't a STRIDE letter
        if _is_empty_cell(cell):
            continue
        locator = f"row[{row_index}].column[{col_idx}]"
        entries.append({
            "entry_id": _stable_entry_id(asset, cell.strip(), locator),
            "asset": asset,
            "threat": cell.strip(),
            "mitigation": None,  # table format has no mitigation column by convention
            "methodology": "stride",
            "source_locator": locator,
            "extraction_confidence": "high",
            "framework_refs": {
                "stride_letter": letter,
                "linddun_letter": None,
                "attack_tree_position": None,
                "mitre_attack": [],
            },
            "inferred_apd_goals": stride_letter_to_apd_goals(letter),
        })
    return entries


def parse_stride_markdown(text: str) -> list[dict[str, Any]]:
    """Parse a Markdown table into STRIDE entries.

    Lenient parser: ignores non-table lines (prose, headings), skips the
    `|---|---|` separator row, treats any pipe-delimited row as data.
    """
    rows: list[list[str]] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped.startswith("|") or not stripped.endswith("|"):
            continue
        # Split on |, strip the leading/trailing empty cells from |...|
        cells = [c.strip() for c in stripped.split("|")[1:-1]]
        # Skip separator rows (cells are all dashes/colons)
        if all(set(c) <= set("-:") for c in cells if c):
            continue
        rows.append(cells)
    if not rows:
        return []
    headers = [_normalize_column_header(h) for h in rows[0]]
    entries: list[dict[str, Any]] = []
    for i, row in enumerate(rows[1:], start=1):
        entries.extend(_row_to_entries(headers, row, i))
    return entries


def parse_stride_csv(text: str) -> list[dict[str, Any]]:
    """Parse a CSV file into STRIDE entries (stdlib csv module)."""
    reader = csv.reader(io.StringIO(text))
    rows = list(reader)
    if not rows:
        return []
    headers = [_normalize_column_header(h) for h in rows[0]]
    entries: list[dict[str, Any]] = []
    for i, row in enumerate(rows[1:], start=1):
        entries.extend(_row_to_entries(headers, row, i))
    return entries


def parse_stride_table(path: Path) -> list[dict[str, Any]]:
    """Dispatch based on file extension."""
    suffix = path.suffix.lower()
    text = path.read_text(encoding="utf-8")
    if suffix == ".md":
        return parse_stride_markdown(text)
    if suffix == ".csv":
        return parse_stride_csv(text)
    raise ValueError(f"Unsupported STRIDE table file extension: {suffix}")
