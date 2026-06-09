# tests/unit/report/test_transform_mas_coverage.py
from __future__ import annotations

import pathlib

from apd_gauntlet.report.loader import RunArtifacts, load_run
from apd_gauntlet.report.transform import (
    build_apd_data,
    masvs_coverage_rows,
    maswe_coverage_rows,
)

EMPTY_METRICS = {"schema_version": 1, "findings_total": 0}


def _artifacts(**overrides) -> RunArtifacts:
    base = {
        "run_id": "r", "framework_version": "1", "domain_pack_name": "mobile-applications",
        "domain_pack_version": "1", "subject": "s", "date": "2026-01-01",
        "asset_inventory": {}, "deduped_findings": [], "deduped_capabilities": [],
        "contradictions": [], "contradictions_notes": None,
        "severity_disagreements": [], "severity_disagreements_notes": None,
        "nist_coverage": {}, "attack_exposure": {}, "apd_coverage_matrix": {},
        "attack_paths": None, "asset_graph": None, "defense_graph": None,
        "attack_path_findings": [], "report_data": None, "metrics": EMPTY_METRICS,
    }
    base.update(overrides)
    return RunArtifacts(**base)


def test_masvs_coverage_rows_from_rollup() -> None:
    art = _artifacts(masvs_coverage={
        "schema_version": 1, "generated_by": "synthesizer",
        "controls": [
            {"masvs_id": "MASVS-STORAGE-1", "name": "Store secrets securely",
             "category": "MASVS-STORAGE", "category_title": "Storage",
             "finding_count": 2, "finding_ids": ["rslv-1", "rslv-2"],
             "surfaces": ["local-db"], "capability_count": 0,
             "capability_ids": [], "posture": "gapped"},
            {"masvs_id": "MASVS-CRYPTO-2", "name": "Use strong crypto",
             "category": "MASVS-CRYPTO", "category_title": "Cryptography",
             "finding_count": 0, "finding_ids": [], "surfaces": [],
             "capability_count": 1, "capability_ids": ["cap-1"],
             "posture": "covered"},
        ],
    })
    rows = masvs_coverage_rows(art)
    assert len(rows) == 2
    by_id = {r["masvs_id"]: r for r in rows}
    assert by_id["MASVS-STORAGE-1"]["finding_count"] == 2
    assert by_id["MASVS-STORAGE-1"]["posture"] == "gapped"
    assert by_id["MASVS-STORAGE-1"]["category_title"] == "Storage"
    assert by_id["MASVS-CRYPTO-2"]["capability_count"] == 1


def test_masvs_coverage_rows_empty_when_absent() -> None:
    art = _artifacts(masvs_coverage=None)
    assert masvs_coverage_rows(art) == []


def test_maswe_coverage_rows_from_rollup() -> None:
    art = _artifacts(maswe_coverage={
        "schema_version": 1, "generated_by": "synthesizer",
        "entries": [
            {"maswe_id": "MASWE-0001", "name": "Insecure data storage",
             "category": "MASVS-STORAGE", "status": "new",
             "parent_masvs": ["MASVS-STORAGE-2"], "finding_count": 3,
             "finding_ids": ["rslv-1", "rslv-2", "rslv-3"],
             "surfaces": ["local-db"]},
            {"maswe_id": "MASWE-0002", "name": "Weak crypto",
             "category": "MASVS-CRYPTO", "status": "draft",
             "parent_masvs": [], "finding_count": 1,
             "finding_ids": ["rslv-4"], "surfaces": []},
        ],
    })
    rows = maswe_coverage_rows(art)
    assert len(rows) == 2
    by_id = {r["maswe_id"]: r for r in rows}
    assert by_id["MASWE-0001"]["finding_count"] == 3
    assert by_id["MASWE-0001"]["status"] == "new"
    assert by_id["MASWE-0001"]["parent_masvs"] == ["MASVS-STORAGE-2"]
    assert by_id["MASWE-0002"]["category"] == "MASVS-CRYPTO"
    # ordered most-cited-first
    assert rows[0]["maswe_id"] == "MASWE-0001"


def test_maswe_coverage_rows_empty_when_absent() -> None:
    art = _artifacts(maswe_coverage=None)
    assert maswe_coverage_rows(art) == []


def test_build_apd_data_includes_mas_coverage_scenes() -> None:
    art = _artifacts(
        masvs_coverage={"controls": [
            {"masvs_id": "MASVS-STORAGE-1", "finding_count": 1, "posture": "gapped"},
        ]},
        maswe_coverage={"entries": [
            {"maswe_id": "MASWE-0001", "finding_count": 1, "status": "new"},
        ]},
    )
    data = build_apd_data(art)
    assert data["masvs_coverage"][0]["masvs_id"] == "MASVS-STORAGE-1"
    assert data["maswe_coverage"][0]["maswe_id"] == "MASWE-0001"


def test_build_apd_data_mas_scenes_empty_on_non_mobile(example_run: pathlib.Path) -> None:
    # the example run ships no MAS coverage rollups
    art = load_run(example_run)
    data = build_apd_data(art)
    assert data["masvs_coverage"] == []
    assert data["maswe_coverage"] == []
