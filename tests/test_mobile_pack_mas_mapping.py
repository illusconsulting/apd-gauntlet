"""The mobile pack must pair each pattern with its MASVS control (and, where
known, its MASWE weakness) explicitly, so a specialist can ground a structured
`control_mappings.masvs` / `.maswe` mapping in the pack prose.

The convention is a literal ``MAS mapping:`` marker carrying ``MASVS-...`` ids
(and optional ``MASWE-####`` ids). These greps are the contract the
apd-control-mappings 'ground every MAS ID in the pack prose' rule depends on.
"""

import re
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PACK = REPO / "domains" / "mobile-applications"
RUBRIC = PACK / "severity-rubric.md"

MASVS_ID = re.compile(
    r"MASVS-(STORAGE|CRYPTO|AUTH|NETWORK|PLATFORM|CODE|RESILIENCE|PRIVACY)-[1-9][0-9]*"
)
MASWE_ID = re.compile(r"MASWE-[0-9]{4}")


def test_rubric_documents_mas_mapping_convention() -> None:
    text = RUBRIC.read_text()
    assert "MAS mapping:" in text
    # The convention must be explained near the top, not only used inline.
    head = text[: text.find("## Critical")]
    assert "MAS mapping:" in head


def test_rubric_has_at_least_six_mas_mapping_lines() -> None:
    lines = [ln for ln in RUBRIC.read_text().splitlines() if "MAS mapping:" in ln]
    # one per Critical/High/Medium clause that names a MASVS control
    assert len(lines) >= 6, f"only {len(lines)} MAS mapping lines"


def test_every_mas_mapping_line_carries_a_valid_masvs_id() -> None:
    for ln in RUBRIC.read_text().splitlines():
        if "MAS mapping:" in ln:
            assert MASVS_ID.search(ln), f"no MASVS id on: {ln!r}"


def test_mas_mapping_ids_use_only_valid_categories() -> None:
    # No typo'd category outside the 8-category enum slips into a mapping line.
    bad = re.compile(r"MASVS-(?!STORAGE|CRYPTO|AUTH|NETWORK|PLATFORM|CODE|RESILIENCE|PRIVACY)\w+")
    for ln in RUBRIC.read_text().splitlines():
        if "MAS mapping:" in ln:
            assert not bad.search(ln), f"invalid MASVS category on: {ln!r}"


CONF = PACK / "common-patterns" / "confidentiality.md"


def test_confidentiality_patterns_carry_mas_mapping_lines() -> None:
    lines = [ln for ln in CONF.read_text().splitlines() if "MAS mapping:" in ln]
    # 8 finding patterns + 4 capability patterns name a MASVS control; the
    # generic blocked/uncertainty pattern does not. Expect at least 9 lines.
    assert len(lines) >= 9, f"only {len(lines)} MAS mapping lines in confidentiality.md"


def test_confidentiality_mas_mapping_ids_valid() -> None:
    for ln in CONF.read_text().splitlines():
        if "MAS mapping:" in ln:
            assert MASVS_ID.search(ln), f"no MASVS id on: {ln!r}"
            bad = re.compile(
                r"MASVS-(?!STORAGE|CRYPTO|AUTH|NETWORK|PLATFORM|CODE|RESILIENCE|PRIVACY)\w+"
            )
            assert not bad.search(ln), f"invalid MASVS category on: {ln!r}"


AUTH = PACK / "common-patterns" / "authenticity.md"


def test_authenticity_patterns_carry_mas_mapping_lines() -> None:
    lines = [ln for ln in AUTH.read_text().splitlines() if "MAS mapping:" in ln]
    # 6 finding patterns + 4 capability patterns name a MASVS control; the
    # generic blocked/uncertainty pattern does not. Expect at least 8 lines.
    assert len(lines) >= 8, f"only {len(lines)} MAS mapping lines in authenticity.md"


def test_authenticity_mas_mapping_ids_valid() -> None:
    bad = re.compile(r"MASVS-(?!STORAGE|CRYPTO|AUTH|NETWORK|PLATFORM|CODE|RESILIENCE|PRIVACY)\w+")
    for ln in AUTH.read_text().splitlines():
        if "MAS mapping:" in ln:
            assert MASVS_ID.search(ln), f"no MASVS id on: {ln!r}"
            assert not bad.search(ln), f"invalid MASVS category on: {ln!r}"


INTEG = PACK / "common-patterns" / "integrity.md"


def test_integrity_patterns_carry_mas_mapping_lines() -> None:
    lines = [ln for ln in INTEG.read_text().splitlines() if "MAS mapping:" in ln]
    # 8 finding patterns + 4 capability patterns name a MASVS control; the
    # generic blocked/uncertainty pattern does not. Expect at least 9 lines.
    assert len(lines) >= 9, f"only {len(lines)} MAS mapping lines in integrity.md"


def test_integrity_mas_mapping_ids_valid() -> None:
    bad = re.compile(r"MASVS-(?!STORAGE|CRYPTO|AUTH|NETWORK|PLATFORM|CODE|RESILIENCE|PRIVACY)\w+")
    for ln in INTEG.read_text().splitlines():
        if "MAS mapping:" in ln:
            assert MASVS_ID.search(ln), f"no MASVS id on: {ln!r}"
            assert not bad.search(ln), f"invalid MASVS category on: {ln!r}"
