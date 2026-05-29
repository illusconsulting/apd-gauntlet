# tests/unit/report/test_tier4_manifest_fallbacks.py
"""Regression tests for PR-T4-G: manifest schema fallbacks.

Three defects closed:
  1. ``framework_version`` silently empty when run_cfg is sparse — now
     substituted with ``"unknown"`` and a stderr warning is emitted.
  2. ``domain_pack_version`` and ``date`` empty for all three live runs —
     now fall back through deduped-findings ``_meta`` and coverage-yaml
     ``generated_at`` respectively, then to a build-time stamp.
  3. The loader module now carries a docstring enumerating manifest
     schema source-of-truth + fallback chain for each field. (Documented
     change; not exercised by a test.)
"""
from __future__ import annotations

import datetime
from typing import Any

import pytest
from apd_gauntlet.report.loader import (
    RunArtifacts,
    _extract_domain_pack_version,
    _resolve_date,
)
from apd_gauntlet.report.transform import meta_block

# ---------------------------------------------------------------------------
# _extract_domain_pack_version
# ---------------------------------------------------------------------------


def test_extract_domain_pack_version_uses_run_cfg() -> None:
    """Canonical path: run_cfg.domain_pack.version wins."""
    run_cfg = {"domain_pack": {"name": "pbm", "version": "1.2.3"}}
    findings_doc = {"_meta": {"domain_pack_version": "0.0.1"}}
    assert _extract_domain_pack_version(run_cfg, findings_doc) == "1.2.3"


def test_extract_domain_pack_version_falls_back_to_findings_meta() -> None:
    """When run_cfg.domain_pack lacks a version, _meta.domain_pack_version
    in the findings doc fills in."""
    run_cfg = {"domain_pack": {"name": "pbm"}}
    findings_doc = {"_meta": {"domain_pack_version": "2026.05.01"}}
    assert (
        _extract_domain_pack_version(run_cfg, findings_doc) == "2026.05.01"
    )


def test_extract_domain_pack_version_falls_back_to_findings_meta_when_dp_is_string() -> None:
    """Bare-string domain_pack still defers to findings _meta for version."""
    run_cfg = {"domain_pack": "pbm"}
    findings_doc = {"_meta": {"domain_pack_version": "9.9.9"}}
    assert _extract_domain_pack_version(run_cfg, findings_doc) == "9.9.9"


def test_extract_domain_pack_version_unknown_when_no_source() -> None:
    """No version anywhere → 'unknown' (not empty string) so the rendered
    report shows a usable value."""
    assert _extract_domain_pack_version({}, {}) == "unknown"
    assert _extract_domain_pack_version({}, None) == "unknown"
    assert _extract_domain_pack_version({"domain_pack": {}}, {"_meta": {}}) == "unknown"


def test_extract_domain_pack_version_signature_backwards_compatible() -> None:
    """The findings_doc kwarg is optional — single-arg callers still work."""
    run_cfg = {"domain_pack": {"version": "3.0.0"}}
    assert _extract_domain_pack_version(run_cfg) == "3.0.0"
    assert _extract_domain_pack_version({}) == "unknown"


# ---------------------------------------------------------------------------
# _resolve_date
# ---------------------------------------------------------------------------


def test_resolve_date_uses_run_cfg() -> None:
    """Canonical path: run_cfg.date wins."""
    run_cfg = {"date": "2026-05-27"}
    nist_doc = {"generated_at": "2024-01-01T00:00:00Z"}
    attack_doc = {"generated_at": "2023-12-31T00:00:00Z"}
    assert _resolve_date(run_cfg, nist_doc, attack_doc) == "2026-05-27"


def test_resolve_date_falls_back_to_nist_generated_at() -> None:
    """Sparse run_cfg → nist coverage generated_at (date portion only)."""
    run_cfg: dict[str, Any] = {}
    nist_doc = {"generated_at": "2026-05-27T12:34:56Z"}
    attack_doc = {"generated_at": "2026-04-01T00:00:00Z"}
    assert _resolve_date(run_cfg, nist_doc, attack_doc) == "2026-05-27"


def test_resolve_date_falls_back_to_attack_generated_at() -> None:
    """Sparse run_cfg + sparse nist → attack-exposure generated_at."""
    run_cfg: dict[str, Any] = {}
    nist_doc: dict[str, Any] = {}
    attack_doc = {"generated_at": "2026-05-28T01:02:03Z"}
    assert _resolve_date(run_cfg, nist_doc, attack_doc) == "2026-05-28"


def test_resolve_date_falls_back_to_today_iso() -> None:
    """No source → today's ISO date as a build-time stamp."""
    run_cfg: dict[str, Any] = {}
    today = datetime.date.today().isoformat()
    assert _resolve_date(run_cfg, None, None) == today
    assert _resolve_date(run_cfg, {}, {}) == today


def test_resolve_date_handles_bare_date_without_time() -> None:
    """generated_at may be a bare date without a 'T' separator."""
    run_cfg: dict[str, Any] = {}
    nist_doc = {"generated_at": "2026-05-27"}
    assert _resolve_date(run_cfg, nist_doc, None) == "2026-05-27"


# ---------------------------------------------------------------------------
# meta_block framework_version substitution + warning
# ---------------------------------------------------------------------------


def _empty_artifacts(framework_version: str = "") -> RunArtifacts:
    """Construct a RunArtifacts with the minimum non-collection fields set."""
    return RunArtifacts(
        run_id="apd-test-run",
        framework_version=framework_version,
        domain_pack_name="pbm",
        domain_pack_version="1.0.0",
        subject="Test Subject",
        date="2026-05-27",
        asset_inventory={},
        deduped_findings=[],
        deduped_capabilities=[],
        contradictions=[],
        contradictions_notes=None,
        severity_disagreements=[],
        severity_disagreements_notes=None,
        nist_coverage={},
        attack_exposure={},
        apd_coverage_matrix={},
        attack_paths=None,
        asset_graph=None,
        defense_graph=None,
        attack_path_findings=[],
        report_data=None,
    )


def test_meta_block_substitutes_unknown_for_empty_framework_version(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Empty framework_version → 'unknown' + stderr warning."""
    artifacts = _empty_artifacts(framework_version="")
    meta = meta_block(artifacts)
    assert meta["framework_version"] == "unknown"
    captured = capsys.readouterr()
    assert "framework_version is empty" in captured.err
    assert "unknown" in captured.err


def test_meta_block_preserves_existing_framework_version(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Non-empty framework_version flows through unchanged; no warning."""
    artifacts = _empty_artifacts(framework_version="1.5.0")
    meta = meta_block(artifacts)
    assert meta["framework_version"] == "1.5.0"
    captured = capsys.readouterr()
    assert "framework_version is empty" not in captured.err
