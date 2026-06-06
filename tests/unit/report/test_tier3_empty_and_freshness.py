# tests/unit/report/test_tier3_empty_and_freshness.py
"""Regression tests for meta.is_empty_run + meta.reference_db_versions (T3-C)."""
from __future__ import annotations

import pathlib
from unittest.mock import MagicMock

from apd_gauntlet.report.loader import load_run
from apd_gauntlet.report.taxonomy import reference_db_versions
from apd_gauntlet.report.transform import meta_block

REPO = pathlib.Path(__file__).resolve().parents[3]


def _minimal_artifacts():
    a = MagicMock()
    a.run_id = "test"
    a.subject = "test"
    a.date = "2026-05-29"
    a.framework_version = "1.5.0"
    a.domain_pack_name = "pbm"
    a.domain_pack_version = "1.0.0"
    a.run_crown_jewels = []
    a.run_attacker_positions = []
    a.asset_inventory = {}
    a.deduped_findings = []
    a.attack_path_findings = []
    a.threat_model_findings = []
    a.deduped_capabilities = []
    return a


def test_is_empty_run_flag_true_when_no_input():
    artifacts = _minimal_artifacts()
    meta = meta_block(artifacts)
    assert meta["is_empty_run"] is True


def test_is_empty_run_flag_false_with_findings():
    artifacts = _minimal_artifacts()
    artifacts.deduped_findings = [{"id": "f1"}]
    meta = meta_block(artifacts)
    assert meta["is_empty_run"] is False


def test_is_empty_run_flag_false_with_capabilities():
    artifacts = _minimal_artifacts()
    artifacts.deduped_capabilities = [{"id": "cap-1"}]
    meta = meta_block(artifacts)
    assert meta["is_empty_run"] is False


def test_is_empty_run_flag_false_with_attack_path_findings():
    artifacts = _minimal_artifacts()
    artifacts.attack_path_findings = [{"id": "apath-1"}]
    artifacts.threat_model_findings = []
    meta = meta_block(artifacts)
    assert meta["is_empty_run"] is False


def test_reference_db_versions_returns_5_families():
    versions = reference_db_versions()
    assert set(versions.keys()) == {"nist", "attack", "cwe", "d3fend", "atlas"}


def test_reference_db_versions_carries_fetched_at_and_count():
    versions = reference_db_versions()
    for _family, entry in versions.items():
        assert "fetched_at" in entry
        assert "count" in entry
        assert isinstance(entry["count"], int)


def test_reference_db_versions_nist_count_positive():
    versions = reference_db_versions()
    assert versions["nist"]["count"] >= 100, \
        "nist-controls.json should ship hundreds of controls"


def test_reference_db_versions_attack_count_positive():
    versions = reference_db_versions()
    assert versions["attack"]["count"] >= 50, \
        "mitre-attack-techniques.json should ship at least 50 techniques"


def test_reference_db_versions_atlas_count_positive():
    versions = reference_db_versions()
    assert versions["atlas"]["count"] >= 50, \
        "atlas-techniques.json should ship at least 50 techniques"


def test_meta_block_carries_reference_db_versions():
    artifacts = _minimal_artifacts()
    meta = meta_block(artifacts)
    assert "reference_db_versions" in meta
    assert set(meta["reference_db_versions"].keys()) == {"nist", "attack", "cwe", "d3fend", "atlas"}


def test_canonical_example_renders_with_is_empty_run_false():
    for run_path in (
        "examples/apd-20260601-claim-event-bus/expected",
    ):
        artifacts = load_run(REPO / run_path)
        meta = meta_block(artifacts)
        assert meta["is_empty_run"] is False, f"{run_path}: unexpected empty"
        assert meta["reference_db_versions"]["nist"]["count"] > 0
        assert meta["reference_db_versions"]["attack"]["count"] > 0
