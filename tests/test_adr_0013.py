"""Tests pinning ADR-0013 (spec C8).

ADR-0013 records the reversal of the Phase-B reviewer-only posture: the
gauntlet now AUTHORS a grounded baseline threat model. The tests assert the
canonical path, the harmonized heading/metadata used by 0008-0012, the four
canonical sections, and that the body substantively records the four design
choices the spec requires: supersedes-vs-preserves, the anti-tautology
carve-out, the CLI-floor mitigation, and the weakest-source confidence floor.
"""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
ADR = REPO_ROOT / "docs" / "adrs" / "0013-author-grounded-baseline-threat-model.md"
ADR0009 = (
    REPO_ROOT / "docs" / "adrs"
    / "0009-methodology-aware-threat-model-evaluator.md"
)


def test_adr_0013_exists() -> None:
    assert ADR.exists(), f"Expected ADR at {ADR}"


def test_adr_0013_has_required_sections() -> None:
    text = ADR.read_text()
    assert "# ADR-0013" in text
    assert "Status:" in text
    assert "Date:" in text
    assert "## Context" in text
    assert "## Decision" in text
    assert "## Consequences" in text
    assert "## Alternatives considered" in text


def test_adr_0013_uses_harmonized_heading() -> None:
    first = ADR.read_text().splitlines()[0]
    assert first.startswith("# ADR-0013:")


def test_adr_0013_records_supersedes_and_preserves() -> None:
    text = ADR.read_text().lower()
    assert "supersede" in text
    assert "preserv" in text
    assert "0009" in text  # supersedes the methodology-aware-evaluator posture


def test_adr_0013_records_anti_tautology_carve_out() -> None:
    text = ADR.read_text().lower()
    assert "tautolog" in text
    assert "corroborat" in text or "contradiction" in text


def test_adr_0013_records_cli_floor_and_confidence_mitigations() -> None:
    text = ADR.read_text().lower()
    assert "cli floor" in text or "author-threat-model" in text
    assert "weakest" in text and "confidence" in text


def test_adr_0013_is_substantively_sized() -> None:
    size = ADR.stat().st_size
    assert size >= 3000, (
        f"ADR is only {size} bytes; expected a substantive ADR of at least "
        "3000 bytes."
    )


def test_adr_0009_back_references_0013() -> None:
    text = ADR0009.read_text()
    assert "0013" in text, "ADR-0009 should record that ADR-0013 supersedes it"
