"""Suite ``stride-table``: the demonstration suite over ``parse-threat-model``.

The fixture is a STRIDE-per-element Markdown table (``threat-model.md``). Its
results are the parsed entries as ``(asset, STRIDE letter, threat, goals)``.
Renaming the elements, reversing the data rows and reversing the six STRIDE
columns must leave those results unchanged, once each renamed element is mapped
back to its original name.
"""
from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path

from ...threat_model.dispatcher import dispatch_parser
from ..metamorphic import SUITES, MetamorphicError, RenameMap, ResultSet, Suite, register_suite

FIXTURES: tuple[str, ...] = ("tests/fixtures/metamorphic/stride-table/basic",)
THREAT_MODEL = "threat-model.md"
_CELLS = 7  # the Element cell and the six STRIDE cells


def extract(d: Path) -> ResultSet:
    """The entries ``parse-threat-model`` reads from ``d/threat-model.md``."""
    envelope = dispatch_parser(d / THREAT_MODEL)
    return frozenset(
        (
            e["asset"],
            e["framework_refs"]["stride_letter"],
            e["threat"],
            ",".join(e["inferred_apd_goals"]),
        )
        for e in envelope["entries"]
    )


def normalise(results: ResultSet, rename: RenameMap) -> ResultSet:
    """``results`` with each asset mapped through ``rename`` (transformed -> original)."""
    return frozenset((rename.get(t[0], t[0]), *t[1:]) for t in results)


@dataclass
class _Table:
    """The threat model's lines, split as ``parse_stride_markdown`` splits them.

    ``bodies`` holds each line without its line ending and ``endings`` the
    ending, so a row can move without joining two lines. ``header`` is the
    first table line that is not a separator row, and ``data`` every later one.
    """

    path: Path
    bodies: list[str]
    endings: list[str]
    header: int
    separators: list[int]
    data: list[int]

    def cells(self, i: int) -> list[str]:
        """Line ``i``'s cells with their padding."""
        return self.bodies[i].split("|")[1:-1]

    def set_cells(self, i: int, cells: list[str]) -> None:
        parts = self.bodies[i].split("|")
        self.bodies[i] = "|".join([parts[0], *cells, parts[-1]])

    def write(self) -> None:
        text = "".join(b + e for b, e in zip(self.bodies, self.endings, strict=True))
        self.path.write_bytes(text.encode("utf-8"))


def _is_separator(cells: list[str]) -> bool:
    return all(set(c) <= set("-:") for c in (c.strip() for c in cells) if c)


def _copy_and_read(src: Path, dst: Path) -> _Table:
    """Copy ``src`` into ``dst`` and read the copy's table; ``MetamorphicError`` if unusable."""
    shutil.copytree(src, dst, dirs_exist_ok=True)
    path = dst / THREAT_MODEL
    lines = path.read_bytes().decode("utf-8").splitlines(keepends=True)
    bodies = [line.splitlines()[0] for line in lines]
    endings = [ln[len(b):] for ln, b in zip(lines, bodies, strict=True)]
    table = _Table(path, bodies, endings, -1, [], [])
    for i, body in enumerate(bodies):
        stripped = body.strip()
        if not (stripped.startswith("|") and stripped.endswith("|")):
            continue
        cells = table.cells(i)
        if len(cells) != _CELLS:
            raise MetamorphicError(
                f"{path}: line {i + 1}: the stride-table transforms need an Element cell and "
                f"six STRIDE cells, found {len(cells)} cells"
            )
        if _is_separator(cells):
            table.separators.append(i)
        elif table.header < 0:
            table.header = i
        elif not cells[0].strip():
            raise MetamorphicError(f"{path}: line {i + 1}: the Element cell is empty")
        else:
            table.data.append(i)
    if not table.data:
        raise MetamorphicError(f"{path}: no STRIDE table with data rows")
    return table


def rename_elements(src: Path, dst: Path) -> RenameMap:
    """Rename each data row's element to ``element-<n>``, in row order."""
    table = _copy_and_read(src, dst)
    rename: RenameMap = {}
    for n, i in enumerate(table.data, start=1):
        cells = table.cells(i)
        cell = cells[0]
        original = cell.strip()
        new = f"element-{n}"
        lead = cell[: len(cell) - len(cell.lstrip())]
        trail = cell[len(cell.rstrip()):]
        cells[0] = lead + new + trail
        table.set_cells(i, cells)
        rename[new] = original
    table.write()
    return rename


def reorder_rows(src: Path, dst: Path) -> RenameMap:
    """Reverse the data rows; each line keeps the line ending of its position."""
    table = _copy_and_read(src, dst)
    rows = [table.bodies[i] for i in table.data]
    for i, body in zip(table.data, reversed(rows), strict=True):
        table.bodies[i] = body
    table.write()
    return {}


def reorder_columns(src: Path, dst: Path) -> RenameMap:
    """Reverse the six STRIDE columns in every table row; the Element column stays first."""
    table = _copy_and_read(src, dst)
    for i in sorted([table.header, *table.separators, *table.data]):
        cells = table.cells(i)
        table.set_cells(i, [cells[0], *reversed(cells[1:])])
    table.write()
    return {}


SUITE = Suite(
    name="stride-table",
    fixtures=FIXTURES,
    transforms={
        "rename-elements": rename_elements,
        "reorder-columns": reorder_columns,
        "reorder-rows": reorder_rows,
    },
    extract=extract,
    normalise=normalise,
)

if SUITE.name not in SUITES:
    register_suite(SUITE)
