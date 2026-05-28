# tests/unit/report/test_transform_taxonomy.py
from __future__ import annotations

import pathlib

from apd_gauntlet.report.loader import load_run
from apd_gauntlet.report.transform import taxonomy_dict


def test_taxonomy_contains_referenced_nist(example_run: pathlib.Path) -> None:
    artifacts = load_run(example_run)
    tax = taxonomy_dict(artifacts)
    # SC-8 appears in crAPI findings (vehicle-location BOLA, plaintext in-cluster, etc.).
    assert "SC-8" in tax
    assert tax["SC-8"]["family"] == "NIST 800-53r5"
    assert tax["SC-8"]["title"]


def test_taxonomy_contains_referenced_attack_technique(example_run: pathlib.Path) -> None:
    artifacts = load_run(example_run)
    tax = taxonomy_dict(artifacts)
    # T1499 (Endpoint DoS) appears in crAPI attack-exposure via merged-514507e6.
    assert "T1499" in tax


def test_taxonomy_no_unreferenced_entries(example_run: pathlib.Path) -> None:
    """We only include IDs actually used in the run — keeps data.js small."""
    artifacts = load_run(example_run)
    tax = taxonomy_dict(artifacts)
    # SC-44 is not referenced in the crAPI run.
    assert "SC-44" not in tax
