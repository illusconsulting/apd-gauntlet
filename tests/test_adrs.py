"""Tests pinning ADR-0010 (Task C-27).

These tests assert that the attack-path analysis ADR exists at the canonical
path, opens with the harmonized ``# ADR-NNNN: <Title>`` heading used by
ADR-0008 and ADR-0009, carries the standard metadata block, and contains
the four canonical sections (Context / Decision / Consequences /
Alternatives considered).

The body assertions check that the ADR substantively justifies the four key
design choices documented in the Phase C plan: partial-graph realism with
provenance and confidence, crown-jewel declaration required (no guessing),
bounded enumeration with honest output, and a D3FEND overlay on bottleneck
edges for highest-leverage defensive guidance.
"""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
ADR = REPO_ROOT / "docs" / "adrs" / "0010-attack-path-analysis-on-partial-graphs.md"


def test_adr_0010_exists() -> None:
    assert ADR.exists(), f"Expected ADR at {ADR}"


def test_adr_0010_has_required_sections() -> None:
    text = ADR.read_text()
    assert "# ADR-0010" in text
    assert "Status:" in text
    assert "Date:" in text
    assert "## Context" in text
    assert "## Decision" in text
    assert "## Consequences" in text
    assert "## Alternatives considered" in text


def test_adr_0010_justifies_partial_graph_approach() -> None:
    text = ADR.read_text().lower()
    assert "partial graph" in text
    assert "provenance" in text and "confidence" in text


def test_adr_0010_justifies_crown_jewel_required() -> None:
    text = ADR.read_text().lower()
    assert "crown jewel" in text
    assert "block" in text or "no guessing" in text


def test_adr_0010_justifies_bounded_enumeration() -> None:
    text = ADR.read_text().lower()
    assert "bounded" in text or "max_hop" in text


def test_adr_0010_justifies_d3fend_overlay() -> None:
    assert "D3FEND" in ADR.read_text()


def test_adr_0010_uses_harmonized_format_like_0008_0009() -> None:
    text = ADR.read_text().splitlines()[0]
    assert text.startswith("# ADR-0010:")  # matches 0008/0009 style


def test_adr_0010_is_substantively_sized() -> None:
    """An ADR shorter than 3 KB is almost certainly underspecified."""
    size = ADR.stat().st_size
    assert size >= 3000, (
        f"ADR is only {size} bytes; expected a substantive ADR of at "
        "least 3000 bytes."
    )
