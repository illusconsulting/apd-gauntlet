# tests/unit/report/test_transform_taxonomy.py
from __future__ import annotations

import pathlib

from apd_gauntlet.report.loader import load_run
from apd_gauntlet.report.transform import taxonomy_dict


def test_taxonomy_contains_referenced_nist(legacy_example_run: pathlib.Path) -> None:
    artifacts = load_run(legacy_example_run)
    tax = taxonomy_dict(artifacts)
    # SC-8 appears in legacy_example findings.
    assert "SC-8" in tax
    assert tax["SC-8"]["family"] == "NIST 800-53r5"
    assert tax["SC-8"]["title"]


def test_taxonomy_contains_referenced_attack_technique(legacy_example_run: pathlib.Path) -> None:
    artifacts = load_run(legacy_example_run)
    tax = taxonomy_dict(artifacts)
    # T1499 appears in legacy_example attack-exposure.
    assert "T1499" in tax


def test_taxonomy_no_unreferenced_entries(legacy_example_run: pathlib.Path) -> None:
    """We only include IDs actually used in the run — keeps data.js small."""
    artifacts = load_run(legacy_example_run)
    tax = taxonomy_dict(artifacts)
    # Unrelated control SC-44 (not used in legacy_example) must not appear.
    assert "SC-44" not in tax
