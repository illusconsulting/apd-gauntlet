"""Staleness + completeness guards for the domain-pack authoring docs (sub-project 2)."""
from __future__ import annotations

import pathlib

REPO = pathlib.Path(__file__).resolve().parent.parent
DOCS = REPO / "docs"

# Top-level user-facing docs only (NOT docs/superpowers/** historical artifacts).
USER_DOCS = sorted(DOCS.glob("*.md")) + [REPO / "README.md"]

# The exact improvement_type enum from schemas/domain-improvement.schema.json.
IMPROVEMENT_TYPES = [
    "missing_severity_clause", "missing_crown_jewel", "missing_attacker_position",
    "missing_trust_boundary", "missing_consequential_action", "missing_immutability_class",
    "missing_data_class", "missing_common_pattern", "missing_regulatory_anchor",
]


def test_no_apd_orchestrator_in_user_docs():
    for doc in USER_DOCS:
        assert "apd-orchestrator" not in doc.read_text(encoding="utf-8"), (
            f"{doc.name} still references the retired apd-orchestrator"
        )


def test_running_guide_cli_reference_lists_draft_command():
    text = (DOCS / "running-the-gauntlet.md").read_text(encoding="utf-8")
    assert "draft-domain-improvements" in text, (
        "running-the-gauntlet.md CLI reference must list draft-domain-improvements"
    )


def test_adapting_guide_dissects_agentic_ai_pack():
    text = (DOCS / "adapting-to-other-domains.md").read_text(encoding="utf-8")
    assert "agentic-ai" in text, "the authoring guide must use the agentic-ai pack"


def test_improving_guide_enumerates_all_improvement_types():
    text = (DOCS / "improving-domain-packs.md").read_text(encoding="utf-8")
    missing = [t for t in IMPROVEMENT_TYPES if t not in text]
    assert not missing, f"improving guide missing improvement_types: {missing}"
