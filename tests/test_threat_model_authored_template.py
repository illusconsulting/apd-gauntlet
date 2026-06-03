"""Structural test for the authored-threat-model doc template.

The template documents the render contract for
00-context/threat-model-authored.md (emitted by apd-threat-model-author).
It is illustrative markdown — these assertions pin the sections the agent
and the report renderer rely on so the contract cannot silently drift.
"""
from __future__ import annotations

import pathlib

TEMPLATE = (
    pathlib.Path(__file__).resolve().parent.parent
    / "templates"
    / "threat-model-authored.template.md"
)


def _text() -> str:
    return TEMPLATE.read_text(encoding="utf-8")


def test_template_exists() -> None:
    assert TEMPLATE.is_file()


def test_template_names_the_author_and_generated_by() -> None:
    text = _text()
    assert "apd-threat-model-author" in text
    assert "threat_model_author" in text


def test_template_documents_blocked_placeholder_visibility() -> None:
    # Blocked placeholders (non-empty prerequisite_evidence) must be a visible,
    # distinct section so reviewers see thin-evidence surfaces as gaps.
    text = _text()
    assert "prerequisite_evidence" in text
    assert "Blocked" in text


def test_template_documents_supplied_vs_authored_delta() -> None:
    # The comparator delta section is rendered only when a supplied TM exists.
    text = _text()
    assert "Supplied-vs-authored" in text
    assert "baseline_only" in text


def test_template_companion_artifact_is_the_normalized_yaml() -> None:
    assert "threat-model-normalized.yaml" in _text()
