"""Static-text regression test for the D3FEND overlay rendering in
report-template/screens/AttackPaths.jsx (no JS test runner in this repo)."""
from __future__ import annotations

import pathlib

REPO = pathlib.Path(__file__).resolve().parents[3]
SRC = REPO / "report-template" / "screens" / "AttackPaths.jsx"


def test_d3fend_tags_normalize_string_or_object_id() -> None:
    """net_new_d3fend items are bare id STRINGS; candidate_d3fend items are
    {d3fend_id,...} OBJECTS. Both rows must normalize the id so net-new tags are
    never rendered with id=undefined (the empty-tag bug)."""
    src = SRC.read_text(encoding="utf-8")
    assert "o.candidate_d3fend" in src and "o.net_new_d3fend" in src
    # the broken object-access-on-every-item pattern is gone
    assert "key={d.d3fend_id} id={d.d3fend_id}" not in src
    # the string-safe normalizer is present (applied to both rows)
    assert src.count('typeof d === "string" ? d : d.d3fend_id') >= 2
