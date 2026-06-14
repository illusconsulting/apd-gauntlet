# tests/test_adr_0021.py
"""Structural lint for ADR-0021. Matches the 0019/0020 ADR format (numbered
H1 title, Status/Date metadata, Context/Decision/Consequences/Alternatives
sections) and guards that the load-bearing decisions (grounded-from-code-recon,
L3-block-by-default, reuse-Cytoscape/adopt-nothing) are actually stated, plus
that 0021 is a unique, sequential ADR number on disk.
"""
from __future__ import annotations

import pathlib
import re

REPO = pathlib.Path(__file__).resolve().parent.parent
ADRS = REPO / "docs" / "adrs"
ADR = ADRS / "0021-grounded-c4-architecture-view.md"


def test_adr_file_exists():
    assert ADR.exists(), f"missing {ADR}"


def test_adr_header_format():
    text = ADR.read_text()
    assert text.startswith("# ADR-0021: "), "ADR must open with '# ADR-0021: <title>'"
    assert re.search(r"^\*\*Status:\*\*\s+\w", text, re.MULTILINE)
    assert re.search(r"^\*\*Date:\*\*\s+\d{4}-\d{2}-\d{2}", text, re.MULTILINE)


def test_required_sections_present():
    text = ADR.read_text()
    for section in ("## Context", "## Decision", "## Consequences", "## Alternatives considered"):
        assert section in text, f"missing section: {section}"


def test_load_bearing_decisions_stated():
    text = ADR.read_text().lower()
    assert "c4" in text
    assert "code_recon" in text or "code reconnaissance" in text
    assert "assemble_c4" in text or "assembler" in text
    assert "l3" in text and "block" in text          # L3-block-by-default
    assert "cytoscape" in text                        # reuse-Cytoscape
    assert "build-vs-adopt" in text or "build vs adopt" in text or "adopt" in text


def test_adr_number_is_unique_and_sequential():
    existing = sorted(p.name[:4] for p in ADRS.glob("[0-9][0-9][0-9][0-9]-*.md"))
    assert existing.count("0021") == 1, "exactly one ADR-0021 file must exist"
    assert "0020" in existing, "0021 must follow an existing 0020"


def test_no_unresolved_placeholders():
    text = ADR.read_text()
    for bad in ("TODO", "TBD", "FIXME", "XXX", "<placeholder>"):
        assert bad not in text, f"unresolved placeholder {bad!r} in ADR"
