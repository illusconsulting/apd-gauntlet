"""Meta block transform — derives the data.meta block."""
from __future__ import annotations

import pathlib

from apd_gauntlet.report.loader import load_run
from apd_gauntlet.report.transform import meta_block


def test_meta_includes_subject_and_run_id(legacy_example_run: pathlib.Path) -> None:
    artifacts = load_run(legacy_example_run)
    meta = meta_block(artifacts)
    assert meta["run_id"] == "apd-legacy-example-run"
    assert "LegacyExample" in meta["subject"]
    assert meta["framework_version"] == "1.4.0"
    assert meta["domain_pack"]["name"] == "pbm"


def test_meta_crown_jewels_and_attackers_from_inventory(legacy_example_run: pathlib.Path) -> None:
    artifacts = load_run(legacy_example_run)
    meta = meta_block(artifacts)
    assert isinstance(meta["crown_jewels"], list)
    assert isinstance(meta["attacker_positions"], list)
    assert len(meta["crown_jewels"]) >= 1
    assert len(meta["attacker_positions"]) >= 1


def test_meta_artifact_count_matches_inputs_dir(legacy_example_run: pathlib.Path) -> None:
    artifacts = load_run(legacy_example_run)
    meta = meta_block(artifacts, run_dir=legacy_example_run)
    expected = len(list((legacy_example_run / "inputs").iterdir()))
    assert meta["artifact_count"] == expected
