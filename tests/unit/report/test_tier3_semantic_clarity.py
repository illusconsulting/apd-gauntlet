# tests/unit/report/test_tier3_semantic_clarity.py
"""Regression tests for three semantic clarifications (T3-D)."""
from __future__ import annotations

from unittest.mock import MagicMock

from apd_gauntlet.report.transform import (
    _normalize_nist_id,
    attack_exposure_rows,
    capability_grid,
    findings_array,
)

# ---------------------------------------------------------------------------
# D1 — NIST id normalisation
# ---------------------------------------------------------------------------


def test_normalize_nist_id_uppercases():
    assert _normalize_nist_id("ac-3") == "AC-3"


def test_normalize_nist_id_strips_whitespace():
    assert _normalize_nist_id(" AC-3 ") == "AC-3"


def test_normalize_nist_id_passes_canonical():
    assert _normalize_nist_id("AC-3") == "AC-3"
    assert _normalize_nist_id("AC-2(13)") == "AC-2(13)"
    assert _normalize_nist_id("SC-7(5)") == "SC-7(5)"


def test_normalize_nist_id_rejects_junk():
    assert _normalize_nist_id("AC2(2)") is None  # missing dash
    assert _normalize_nist_id("123") is None
    assert _normalize_nist_id("") is None
    assert _normalize_nist_id(None) is None
    assert _normalize_nist_id(123) is None


def test_findings_array_normalises_nist_case():
    """A finding emitting 'ac-3' and a different finding emitting 'AC-3'
    should both contribute to the same taxonomy entry, not split."""
    artifacts = MagicMock()
    artifacts.deduped_findings = [
        {"id": "f1", "control_mappings": {"nist_800_53r5": ["ac-3"]}},
        {"id": "f2", "control_mappings": {"nist_800_53r5": ["AC-3"]}},
    ]
    artifacts.attack_path_findings = []
    out = findings_array(artifacts, headline_supplement=None)
    assert out[0]["mappings"]["nist"] == ["AC-3"]
    assert out[1]["mappings"]["nist"] == ["AC-3"]


# ---------------------------------------------------------------------------
# D2 — lens_perspectives dict-shape extraction
# ---------------------------------------------------------------------------


def test_capability_grid_dict_shape_pulls_apd_goals_from_values():
    """Pre-T3-D, dict-shape returned lens NAMES (keys); now it must
    return APD goals (extracted from values)."""
    artifacts = MagicMock()
    artifacts.deduped_capabilities = [
        {
            "id": "cap-merged-001",
            "merged": True,
            "lens_perspectives": {
                "oauth_lens": {"apd_goal": "confidentiality", "source_id": "x"},
                "k8s_lens":   {"apd_goal": "integrity",      "source_id": "y"},
            },
        },
    ]
    grid = capability_grid(artifacts)
    assert grid[0]["cross_lens"] == ["confidentiality", "integrity"]


def test_capability_grid_list_shape_unchanged():
    """List shape behavior preserved (regression: don't break the working path)."""
    artifacts = MagicMock()
    artifacts.deduped_capabilities = [
        {
            "id": "cap-merged-002",
            "merged": True,
            "lens_perspectives": [
                {"apd_goal": "availability", "source_id": "a"},
                {"goal":     "resilient",    "source_id": "b"},
            ],
        },
    ]
    grid = capability_grid(artifacts)
    assert grid[0]["cross_lens"] == ["availability", "resilient"]


# ---------------------------------------------------------------------------
# D3 — ATT&CK Shape-B parent vs grouping distinction
# ---------------------------------------------------------------------------


def test_attack_exposure_skips_grouping_only_parent():
    """A parent with citing_findings: [] AND non-empty sub_techniques
    should NOT emit a parent row; only the sub-technique rows."""
    artifacts = MagicMock()
    artifacts.attack_exposure = {
        "techniques": {
            "T1110": {
                "name": "Brute Force",
                "citing_findings": [],
                "sub_techniques": {
                    "T1110.001": {"name": "Password Guessing", "citing_findings": ["f1"]},
                    "T1110.003": {"name": "Password Spraying", "citing_findings": ["f2"]},
                },
            },
        },
    }
    rows = attack_exposure_rows(artifacts)
    ids = [r["id"] for r in rows]
    assert "T1110" not in ids, "parent grouping node should not emit a row"
    assert "T1110.001" in ids
    assert "T1110.003" in ids


def test_attack_exposure_emits_parent_with_own_findings():
    """A parent with its own citing_findings (non-empty) still emits a row,
    alongside the sub-technique rows."""
    artifacts = MagicMock()
    artifacts.attack_exposure = {
        "techniques": {
            "T1078": {
                "name": "Valid Accounts",
                "citing_findings": ["f1", "f2"],
                "sub_techniques": {
                    "T1078.004": {"name": "Cloud Accounts", "citing_findings": ["f3"]},
                },
            },
        },
    }
    rows = attack_exposure_rows(artifacts)
    ids = [r["id"] for r in rows]
    assert "T1078" in ids
    assert "T1078.004" in ids
