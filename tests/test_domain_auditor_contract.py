import pathlib

AGENT = (
    pathlib.Path(__file__).resolve().parent.parent
    / ".claude" / "agents" / "apd-domain-auditor.md"
)


def test_domain_auditor_does_not_imperatively_mint_id():
    text = AGENT.read_text(encoding="utf-8")
    # the old imperative ("Compute the dimpr- id with the deterministic CLI") is gone
    assert "Compute the dimpr- id with the deterministic CLI" not in text


def test_domain_auditor_states_assembler_owns_dimpr_id():
    text = AGENT.read_text(encoding="utf-8")
    assert "do NOT emit" in text
    assert "assembler" in text.lower()
