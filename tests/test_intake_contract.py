"""Contract test: apd-intake agent must delegate id minting to the assembler."""
import pathlib

INTAKE = pathlib.Path(__file__).resolve().parent.parent / ".claude" / "agents" / "apd-intake.md"


def test_intake_does_not_fabricate_inventory_ids():
    t = INTAKE.read_text(encoding="utf-8")
    assert "deterministic ID from name" not in t
    assert "assembler" in t.lower()


def test_intake_authors_crosses_by_name():
    t = INTAKE.read_text(encoding="utf-8")
    # the canonical directive bullet must be present — a phrase unique to the
    # crosses-by-name instruction, so the test cannot pass on unrelated prose.
    assert "crosses[]" in t
    assert "list of asset **names**" in t
