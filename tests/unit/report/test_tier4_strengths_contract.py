"""Regression tests for PR-T4-D — strengths_section error contract.

Before T4-D, ``strengths_section`` raised ``ValueError`` on an unknown
capability id while sibling supplements (``headline_findings``,
``next_steps``) failed silently. T4-D normalizes the contract:
strengths_section now warn-and-skip's unknown ids, matching siblings, and
records each occurrence in ``data.meta.warnings`` when build_apd_data runs.

These tests pin the new contract so a future refactor cannot accidentally
re-introduce the raise path or drop the warning surface.
"""
from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

from apd_gauntlet.report.transform import build_apd_data, strengths_section


def _make_minimal_artifacts() -> MagicMock:
    """Build a RunArtifacts-shaped mock with every field populated to a
    benign default. Mirrors the helper used by ``test_tier2_isolation.py``.

    Tests here override only ``deduped_capabilities`` and ``report_data``
    because strengths_section + the surrounding build_apd_data plumbing
    are the only paths under test.
    """
    a = MagicMock()
    a.run_id = "test-run"
    a.subject = "test"
    a.date = "2026-05-29"
    a.framework_version = "1.5.0"
    a.domain_pack_name = "pbm"
    a.domain_pack_version = "1.0.0"
    a.run_crown_jewels = []
    a.run_attacker_positions = []
    a.asset_inventory = {}
    a.report_data = {}
    a.deduped_findings = []
    a.attack_path_findings = []
    a.deduped_capabilities = []
    a.nist_coverage = {}
    a.attack_exposure = {}
    a.apd_coverage_matrix = {}
    a.contradictions = []
    a.contradictions_notes = None
    a.severity_disagreements = []
    a.severity_disagreements_notes = None
    a.attack_paths = None
    a.asset_graph = None
    a.defense_graph = None
    return a


def _cap(cid: str, title: str = "Some capability", goal: str = "confidentiality",
         maturity: str = "implemented") -> dict[str, Any]:
    return {
        "id":       cid,
        "title":    title,
        "apd_goal": goal,
        "maturity": maturity,
    }


# ---------------------------------------------------------------------------
# Direct helper-level tests
# ---------------------------------------------------------------------------


def test_strengths_section_unknown_id_now_warns_instead_of_raising() -> None:
    """An unknown id must drop the entry, append a warning, and never raise."""
    artifacts = _make_minimal_artifacts()
    artifacts.deduped_capabilities = []  # no caps at all => every id is unknown
    warnings: list[dict[str, str]] = []
    supplied = [{"id": "cap-ghost", "caveats": ["a caveat long enough"]}]

    # No exception should escape — the pre-T4-D ValueError path is gone.
    result = strengths_section(
        artifacts, supplied_strengths=supplied, warnings=warnings,
    )

    assert result == []
    assert warnings == [{
        "section": "strengths",
        "issue":   "unknown_capability_id",
        "id":      "cap-ghost",
    }]


def test_strengths_section_known_id_emits_normally() -> None:
    """Regression: known ids must still emit the full (id/title/goal/...) entry."""
    artifacts = _make_minimal_artifacts()
    artifacts.deduped_capabilities = [
        _cap("cap-001", title="JWKS publication", goal="authenticity",
             maturity="implemented"),
    ]
    warnings: list[dict[str, str]] = []
    supplied = [{"id": "cap-001", "caveats": ["caveat one is long enough"]}]

    result = strengths_section(
        artifacts, supplied_strengths=supplied, warnings=warnings,
    )

    assert warnings == []
    assert result == [{
        "id":       "cap-001",
        "title":    "JWKS publication",
        "goal":     "authenticity",
        "maturity": "implemented",
        "caveats":  ["caveat one is long enough"],
    }]


def test_strengths_section_warnings_kwarg_optional() -> None:
    """Omitting the warnings kwarg must still short-circuit unknown ids
    silently (matches sibling supplement helpers when callers don't capture).
    """
    artifacts = _make_minimal_artifacts()
    artifacts.deduped_capabilities = []
    supplied = [{"id": "cap-ghost", "caveats": ["caveat long enough"]}]

    # No exception; no warnings list passed; return is still empty list.
    result = strengths_section(artifacts, supplied_strengths=supplied)

    assert result == []


def test_strengths_section_partial_success() -> None:
    """A mix of known + unknown ids: knowns emit, each unknown contributes
    exactly one warning. Per-entry behaviour is independent.
    """
    artifacts = _make_minimal_artifacts()
    artifacts.deduped_capabilities = [
        _cap("cap-known-1", title="MFA enforced", goal="authenticity"),
        _cap("cap-known-2", title="Audit log retention", goal="auditability"),
    ]
    warnings: list[dict[str, str]] = []
    supplied = [
        {"id": "cap-known-1", "caveats": ["caveat for one is long enough"]},
        {"id": "cap-ghost-a", "caveats": ["caveat for ghost-a is long enough"]},
        {"id": "cap-known-2", "caveats": ["caveat for two is long enough"]},
        {"id": "cap-ghost-b", "caveats": ["caveat for ghost-b is long enough"]},
    ]

    result = strengths_section(
        artifacts, supplied_strengths=supplied, warnings=warnings,
    )

    emitted_ids = [entry["id"] for entry in result]
    assert emitted_ids == ["cap-known-1", "cap-known-2"]

    assert warnings == [
        {"section": "strengths", "issue": "unknown_capability_id",
         "id": "cap-ghost-a"},
        {"section": "strengths", "issue": "unknown_capability_id",
         "id": "cap-ghost-b"},
    ]


def test_strengths_section_missing_id_uses_placeholder_marker() -> None:
    """A strengths entry with no ``id`` key (or an empty/non-string id) is
    still a synthesizer authoring error — but it must surface as a warning
    with id ``"(missing)"`` rather than crash the report.
    """
    artifacts = _make_minimal_artifacts()
    artifacts.deduped_capabilities = []
    warnings: list[dict[str, str]] = []
    supplied = [
        {"caveats": ["caveat long enough"]},        # no id at all
        {"id": "", "caveats": ["another caveat"]},   # empty id
    ]

    result = strengths_section(
        artifacts, supplied_strengths=supplied, warnings=warnings,
    )

    assert result == []
    assert warnings == [
        {"section": "strengths", "issue": "unknown_capability_id",
         "id": "(missing)"},
        {"section": "strengths", "issue": "unknown_capability_id",
         "id": "(missing)"},
    ]


# ---------------------------------------------------------------------------
# End-to-end via build_apd_data
# ---------------------------------------------------------------------------


def test_strengths_section_warning_recorded_in_meta() -> None:
    """build_apd_data must thread its shared warnings list into the strengths
    thunk so the warning lands in ``data.meta.warnings`` — additive to and
    independent of ``data.meta.section_errors``.
    """
    artifacts = _make_minimal_artifacts()
    artifacts.deduped_capabilities = []
    artifacts.report_data = {
        "strengths": [
            {"id": "cap-not-there", "caveats": ["caveat long enough"]},
        ],
    }

    data = build_apd_data(artifacts)

    assert data["meta"]["section_errors"] == {}
    assert {
        "section": "strengths",
        "issue":   "unknown_capability_id",
        "id":      "cap-not-there",
    } in data["meta"]["warnings"]


def test_build_apd_data_succeeds_with_unknown_strengths_id() -> None:
    """End-to-end: pre-T4-D this raised ValueError out of the strengths thunk
    and was caught by per-section isolation (ending up in section_errors).
    Post-T4-D the thunk no longer raises — strengths is an empty list,
    section_errors stays empty, and meta.warnings carries the issue.
    """
    artifacts = _make_minimal_artifacts()
    artifacts.deduped_capabilities = [
        _cap("cap-real-1", title="TLS everywhere", goal="confidentiality"),
    ]
    artifacts.report_data = {
        "strengths": [
            {"id": "cap-real-1", "caveats": ["a known caveat long enough"]},
            {"id": "cap-phantom", "caveats": ["caveat for phantom long enough"]},
        ],
    }

    data = build_apd_data(artifacts)

    # Section did not error out.
    assert data["meta"]["section_errors"] == {}
    # Known id still emits.
    assert [s["id"] for s in data["strengths"]] == ["cap-real-1"]
    # Warning recorded for the unknown id.
    assert {
        "section": "strengths",
        "issue":   "unknown_capability_id",
        "id":      "cap-phantom",
    } in data["meta"]["warnings"]


def test_build_apd_data_meta_warnings_empty_on_clean_input() -> None:
    """Baseline contract: a clean run produces an empty warnings list, not a
    missing key. Downstream consumers can iterate ``data.meta.warnings``
    unconditionally.
    """
    artifacts = _make_minimal_artifacts()
    artifacts.deduped_capabilities = [
        _cap("cap-real-1", title="TLS everywhere", goal="confidentiality"),
    ]
    artifacts.report_data = {
        "strengths": [
            {"id": "cap-real-1", "caveats": ["a known caveat long enough"]},
        ],
    }

    data = build_apd_data(artifacts)

    assert data["meta"]["section_errors"] == {}
    assert data["meta"]["warnings"] == []
