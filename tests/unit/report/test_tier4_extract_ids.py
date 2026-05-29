# tests/unit/report/test_tier4_extract_ids.py
"""Regression tests for PR-T4-C: ``_extract_ids_from_mapping`` last-resort
name fallback and ``data.meta.warnings`` aggregation.

The helper previously dropped dict items lacking both ``id`` and any supplied
fallback key — partial signal lost silently. Tier-4-C adds a final ``name``
fallback so the human-readable label still propagates, plus a structured
warnings aggregator that surfaces the issue in ``data.meta.warnings``.
"""
from __future__ import annotations

import pathlib

from apd_gauntlet.report.loader import load_run
from apd_gauntlet.report.transform import (
    _extract_ids_from_mapping,
    build_apd_data,
)

# ---------------------------------------------------------------------------
# _extract_ids_from_mapping unit tests
# ---------------------------------------------------------------------------


def test_extract_ids_name_fallback_when_no_id_no_fallback_key() -> None:
    """Dict item with no id / fallback_key but a usable name appends the name
    so partial signal is not silently lost."""
    warnings: list[dict[str, str]] = []
    out = _extract_ids_from_mapping(
        [{"name": "Spoofing the customer", "rationale": "weak auth"}],
        warnings=warnings,
    )
    assert out == ["Spoofing the customer"]
    assert warnings == [{
        "issue": "mapping_id_missing_using_name",
        "name":  "Spoofing the customer",
    }]


def test_extract_ids_warns_when_no_id_no_name() -> None:
    """Dict item with no id / fallback_key / name is skipped and a structured
    warning is emitted carrying the dict shape."""
    warnings: list[dict[str, str]] = []
    out = _extract_ids_from_mapping(
        [{"rationale": "y", "confidence": "low"}],
        warnings=warnings,
    )
    assert out == []
    assert warnings == [{
        "issue": "mapping_item_no_id_no_name",
        "shape": "confidence,rationale",
    }]


def test_extract_ids_no_warnings_on_clean_input() -> None:
    """Well-formed input must not emit any warnings."""
    warnings: list[dict[str, str]] = []
    out = _extract_ids_from_mapping(
        [
            "AC-3",
            {"id": "AC-6", "rationale": "least privilege"},
            {"technique": "T1078", "rationale": "valid accounts"},
        ],
        "technique",
        warnings=warnings,
    )
    assert out == ["AC-3", "AC-6", "T1078"]
    assert warnings == []


def test_extract_ids_uses_fallback_key_before_name() -> None:
    """``fallback_keys`` must take precedence over ``name`` so legitimate
    schema variants (e.g. mitre_attack's ``technique`` field) keep emitting
    the canonical id, not the human-readable label."""
    warnings: list[dict[str, str]] = []
    out = _extract_ids_from_mapping(
        [{"technique": "T1110", "name": "Brute Force", "rationale": "ok"}],
        "technique",
        warnings=warnings,
    )
    assert out == ["T1110"]
    assert warnings == []


def test_extract_ids_warnings_kwarg_optional() -> None:
    """Existing callers that omit ``warnings`` must keep working — the
    last-resort name fallback still fires silently so partial signal is not
    dropped, but no warning is recorded anywhere."""
    out = _extract_ids_from_mapping(
        [
            "AC-3",
            {"id": "AC-6"},
            {"name": "label only"},
            {"rationale": "no id, no name"},
        ]
    )
    # AC-3 + AC-6 + last-resort name fallback; the shapeless dict is skipped.
    assert out == ["AC-3", "AC-6", "label only"]


# ---------------------------------------------------------------------------
# build_apd_data integration: data.meta.warnings field
# ---------------------------------------------------------------------------


REPO = pathlib.Path(__file__).resolve().parents[3]


def test_build_apd_data_emits_empty_warnings_on_clean_input() -> None:
    """The shipped crAPI run uses well-formed control_mappings everywhere, so
    data.meta.warnings exists and is an empty list."""
    artifacts = load_run(REPO / "runs" / "apd-20260527-crapi-owasp-api-top10")
    data = build_apd_data(artifacts)
    assert "warnings" in data["meta"]
    assert data["meta"]["warnings"] == []


def test_build_apd_data_aggregates_warnings_from_findings() -> None:
    """A finding whose control_mappings.mitre_attack carries a name-only
    entry must surface a ``mapping_id_missing_using_name`` warning on
    data.meta.warnings — confirming the warnings list is threaded through
    findings_array → _extract_ids_from_mapping correctly."""
    artifacts = load_run(REPO / "runs" / "apd-20260527-crapi-owasp-api-top10")
    # Inject one synthetic finding with a name-only mitre_attack entry. The
    # deduped_findings list on RunArtifacts is mutable (a plain list), so this
    # surgical mutation exercises the production code path end-to-end.
    artifacts.deduped_findings.append({
        "id": "tier4-c-synthetic",
        "title": "synthetic finding for tier4-c regression",
        "severity": "low",
        "confidence": "low",
        "disposition": "gap",
        "apd_goal": "confidentiality",
        "apd_tier": "assure_trustworthiness",
        "control_mappings": {
            "mitre_attack": [
                {"name": "Phantom Technique", "rationale": "ok"},
            ],
        },
    })
    data = build_apd_data(artifacts)
    issues = [w for w in data["meta"]["warnings"]
              if w.get("issue") == "mapping_id_missing_using_name"]
    assert issues, (
        "expected at least one mapping_id_missing_using_name warning, "
        f"got {data['meta']['warnings']!r}"
    )
    assert any(w.get("name") == "Phantom Technique" for w in issues)
