"""Meta block transform — derives the data.meta block."""
from __future__ import annotations

import pathlib

from apd_gauntlet.report.loader import load_run
from apd_gauntlet.report.transform import meta_block


def test_meta_includes_subject_and_run_id(example_run: pathlib.Path) -> None:
    artifacts = load_run(example_run)
    meta = meta_block(artifacts)
    assert meta["run_id"] == "apd-20260601-claim-event-bus"
    # The example declares no explicit subject, so it falls back to the run_id.
    assert "claim-event-bus" in meta["subject"]
    assert meta["framework_version"] == "1.4.0"
    assert meta["domain_pack"]["name"] == "pbm"


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
    inputs_dir = example_run / "inputs"
    # meta_block counts the run's inputs/ dir; the example ships an output-only
    # snapshot with no inputs/, so the count is 0 — and meta_block must not crash.
    expected = len(list(inputs_dir.iterdir())) if inputs_dir.is_dir() else 0
    assert meta["artifact_count"] == expected
