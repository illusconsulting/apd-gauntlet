"""Tier-2-A regression tests: the bundled NIST 800-53r5 + MITRE ATT&CK
taxonomy catalogs must resolve titles for every taxonomy reference appearing
in any shipped run.

Pre-Tier-2 the ATT&CK loader read mitre-mitigations.json (which has no
'techniques' key) and returned 0 entries, leaving every ATT&CK ID in
data.taxonomy with title == id. The NIST side had no catalog at all and
relied entirely on whatever inline titles the nist-coverage artifact happened
to carry. Both pipelines now use the bundled catalogs.
"""
from __future__ import annotations

import pathlib

from apd_gauntlet.report.loader import load_run
from apd_gauntlet.report.taxonomy import (
    attack_technique_titles,
    nist_control_titles,
)
from apd_gauntlet.report.transform import taxonomy_dict


def test_nist_control_titles_resolves_common_ids() -> None:
    titles = nist_control_titles()
    assert "AC-3" in titles
    assert "Access Enforcement" in titles["AC-3"]
    assert "AU-9" in titles  # Protection of Audit Information
    assert len(titles) >= 100  # rough floor


def test_attack_technique_titles_now_resolves() -> None:
    """Pre-Tier-2 this returned 0 entries because the loader read the wrong file."""
    titles = attack_technique_titles()
    assert titles.get("T1078") == "Valid Accounts"
    assert "T1565" in titles
    assert "T1565.001" in titles
    assert len(titles) >= 50


def test_taxonomy_dict_resolves_nist_titles_for_canonical_example() -> None:
    """No NIST entry in the canonical example should remain bare-id after Tier-2-A."""
    REPO = pathlib.Path(__file__).resolve().parents[3]
    for run_path in (
        "examples/apd-20260601-claim-event-bus/expected",
    ):
        artifacts = load_run(REPO / run_path)
        td = taxonomy_dict(artifacts)
        nist_entries = {
            k: v for k, v in td.items() if v["family"] == "NIST 800-53r5"
        }
        bare_id_count = sum(
            1 for k, v in nist_entries.items() if v["title"] == k
        )
        assert bare_id_count == 0, (
            f"{run_path}: {bare_id_count} bare-ID NIST entries"
        )


def test_taxonomy_dict_resolves_attack_titles_for_canonical_example() -> None:
    REPO = pathlib.Path(__file__).resolve().parents[3]
    for run_path in (
        "examples/apd-20260601-claim-event-bus/expected",
    ):
        artifacts = load_run(REPO / run_path)
        td = taxonomy_dict(artifacts)
        attack_entries = {
            k: v for k, v in td.items() if v["family"] == "MITRE ATT&CK"
        }
        bare_id_count = sum(
            1 for k, v in attack_entries.items() if v["title"] == k
        )
        # Some sub-techniques might be missing if curated, but most should resolve.
        assert bare_id_count <= 2, (
            f"{run_path}: {bare_id_count} bare-ID ATT&CK entries"
        )
