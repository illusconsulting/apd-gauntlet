"""Meta block transform — derives the data.meta block."""
from __future__ import annotations

import pathlib

from apd_gauntlet.report.loader import load_run
from apd_gauntlet.report.transform import meta_block


def test_meta_includes_subject_and_run_id(example_run: pathlib.Path) -> None:
    artifacts = load_run(example_run)
    meta = meta_block(artifacts)
    assert meta["run_id"] == "apd-20260527-crapi-owasp-api-top10"
    assert "crAPI" in meta["subject"] or "OWASP" in meta["subject"]
    assert meta["framework_version"] == "1.5.0"
    assert meta["domain_pack"]["name"] == "api-security"


def test_meta_crown_jewels_and_attackers_from_inventory(example_run: pathlib.Path) -> None:
    artifacts = load_run(example_run)
    meta = meta_block(artifacts)
    assert isinstance(meta["crown_jewels"], list)
    assert isinstance(meta["attacker_positions"], list)
    assert len(meta["crown_jewels"]) >= 1
    assert len(meta["attacker_positions"]) >= 1


def test_meta_artifact_count_matches_inputs_dir(example_run: pathlib.Path) -> None:
    artifacts = load_run(example_run)
    meta = meta_block(artifacts, run_dir=example_run)
    expected = len(list((example_run / "inputs").iterdir()))
    assert meta["artifact_count"] == expected
