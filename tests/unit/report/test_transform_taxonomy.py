# tests/unit/report/test_transform_taxonomy.py
from __future__ import annotations

import pathlib
from typing import Any

from apd_gauntlet.report import transform as _t
from apd_gauntlet.report.loader import RunArtifacts, load_run
from apd_gauntlet.report.transform import _collect_referenced_ids, taxonomy_dict

EMPTY_METRICS = {
    "schema_version": 1,
    "findings_total": 0, "findings_pre_dedup": 0,
    "cross_lens_merged_clusters": 0, "linked_clusters": 0,
    "bySeverity": {"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0},
    "byDisposition": {"gap": 0, "blocked": 0, "risk": 0, "uncertainty": 0, "ok": 0},
    "byTier": {"trustworthiness": 0, "scalability": 0, "auditability": 0},
    "capabilities_total": 0, "capabilities_pre_dedup": 0,
    "capabilitiesByMaturity": {"designed": 0, "implemented": 0, "tested": 0, "operationalized": 0},
    "contradictions": 0, "severity_disagreements": 0,
}


def _artifacts_with_findings(findings: list[dict[str, Any]]) -> RunArtifacts:
    return RunArtifacts(
        run_id="r", framework_version="1", domain_pack_name="p",
        domain_pack_version="1", subject="s", date="2026-01-01",
        asset_inventory={}, deduped_findings=findings, deduped_capabilities=[],
        contradictions=[], contradictions_notes=None,
        severity_disagreements=[], severity_disagreements_notes=None,
        nist_coverage={}, attack_exposure={}, apd_coverage_matrix={},
        attack_paths=None, asset_graph=None, defense_graph=None,
        attack_path_findings=[], report_data=None,
        metrics=EMPTY_METRICS,
    )


def test_taxonomy_contains_referenced_nist(example_run: pathlib.Path) -> None:
    artifacts = load_run(example_run)
    tax = taxonomy_dict(artifacts)
    # SC-8 appears in the example findings (transport confidentiality/integrity).
    assert "SC-8" in tax
    assert tax["SC-8"]["family"] == "NIST 800-53r5"
    assert tax["SC-8"]["title"]


def test_taxonomy_contains_referenced_attack_technique(example_run: pathlib.Path) -> None:
    artifacts = load_run(example_run)
    tax = taxonomy_dict(artifacts)
    # T1530 (Data from Cloud Storage) appears in the example attack-exposure.
    assert "T1530" in tax


def test_taxonomy_no_unreferenced_entries(example_run: pathlib.Path) -> None:
    """We only include IDs actually used in the run — keeps data.js small."""
    artifacts = load_run(example_run)
    tax = taxonomy_dict(artifacts)
    # SC-44 is not referenced in the example run.
    assert "SC-44" not in tax


def test_taxonomy_resolves_referenced_atlas_technique() -> None:
    """A finding citing an ATLAS technique gets a MITRE ATLAS taxonomy entry
    with a resolved title from the bundled atlas-techniques.json catalog."""
    artifacts = _artifacts_with_findings([
        {
            "id": "intg-00000001",
            "control_mappings": {
                "nist_800_53r5": ["SI-10"],
                "atlas": ["AML.T0051", "AML.T0051.000"],
            },
            "evidence": [{"artifact": "plan.md", "locator": "§3"}],
        }
    ])
    tax = taxonomy_dict(artifacts)
    assert tax["AML.T0051"]["family"] == "MITRE ATLAS"
    # Title resolves from the shipped catalog (not the bare id).
    assert tax["AML.T0051"]["title"] == "LLM Prompt Injection"
    # Sub-technique resolves with the parent-prefixed title.
    assert tax["AML.T0051.000"]["family"] == "MITRE ATLAS"
    assert ":" in tax["AML.T0051.000"]["title"]


def _artifacts_with_defense_graph(overlays: list[dict[str, Any]]) -> RunArtifacts:
    return RunArtifacts(
        run_id="r", framework_version="1", domain_pack_name="p",
        domain_pack_version="1", subject="s", date="2026-01-01",
        asset_inventory={}, deduped_findings=[], deduped_capabilities=[],
        contradictions=[], contradictions_notes=None,
        severity_disagreements=[], severity_disagreements_notes=None,
        nist_coverage={}, attack_exposure={}, apd_coverage_matrix={},
        attack_paths=None, asset_graph=None,
        defense_graph={"bottleneck_overlays": overlays},
        attack_path_findings=[], report_data=None,
        metrics=EMPTY_METRICS,
    )


def test_taxonomy_resolves_d3fend_from_attack_path_overlays() -> None:
    """D3FEND ids appear ONLY in attack-path overlays (candidate_d3fend objects +
    net_new_d3fend strings), not in finding control_mappings. The taxonomy dict
    must still resolve their titles so the report's hover tooltips work the way
    ATT&CK technique tooltips do."""
    artifacts = _artifacts_with_defense_graph([
        {
            "edge_id": "edge-x",
            "exposed_attack_techniques": ["T1555"],
            "candidate_d3fend": [
                {"d3fend_id": "D3-CF", "counters": ["T1555"], "rationale": "x"},
            ],
            "net_new_d3fend": ["D3-CF"],  # net_new items are STRINGS
        },
    ])
    tax = taxonomy_dict(artifacts)
    assert "D3-CF" in tax, "D3FEND id from overlay must be in the taxonomy dict"
    assert tax["D3-CF"]["family"] == "MITRE D3FEND"
    assert tax["D3-CF"]["title"] == "Content Filtering"
    # the overlay's exposed ATT&CK technique resolves too
    assert tax.get("T1555", {}).get("family") == "MITRE ATT&CK"


def test_attack_taxonomy_entries_carry_authoritative_url() -> None:
    """ATT&CK technique + sub-technique tags deep-link to attack.mitre.org; other
    families (e.g. CWE) are left unlinked (feature scope: ATT&CK + D3FEND)."""
    artifacts = _artifacts_with_findings([
        {
            "id": "conf-00000001",
            "control_mappings": {
                "mitre_attack": [{"technique": "T1555"}, {"technique": "T1555.004"}],
                "cwe": ["CWE-79"],
            },
            "evidence": [{"artifact": "plan.md", "locator": "§1"}],
        }
    ])
    tax = taxonomy_dict(artifacts)
    assert tax["T1555"]["url"] == "https://attack.mitre.org/techniques/T1555/"
    assert tax["T1555.004"]["url"] == "https://attack.mitre.org/techniques/T1555/004/"
    assert "url" not in tax.get("CWE-79", {})  # CWE not linked (scope)


def test_d3fend_taxonomy_entries_carry_authoritative_url() -> None:
    """D3FEND tags deep-link via the AUTHORITATIVE ontology IRI local name
    (d3f_local) — hyphens + acronym casing preserved, NOT a PascalCase strip."""
    artifacts = _artifacts_with_defense_graph([
        {"edge_id": "e",
         "candidate_d3fend": [
             {"d3fend_id": "D3-CF", "counters": ["T1555"], "rationale": "x"},
             {"d3fend_id": "D3-PHDURA", "counters": ["T1020"], "rationale": "y"},
         ],
         "net_new_d3fend": ["D3-CF"]},
    ])
    tax = taxonomy_dict(artifacts)
    assert tax["D3-CF"]["url"] == "https://d3fend.mitre.org/technique/d3f:ContentFiltering/"
    # hyphenated local name preserved (authoritative IRI, NOT name-PascalCase)
    assert tax["D3-PHDURA"]["url"] == (
        "https://d3fend.mitre.org/technique/d3f:PerHostDownload-UploadRatioAnalysis/"
    )


def test_mas_family_display_constants() -> None:
    assert _t._MASVS_FAMILY_DISPLAY == "OWASP MASVS"
    assert _t._MASWE_FAMILY_DISPLAY == "OWASP MASWE"


def _mas_artifacts(**overrides) -> RunArtifacts:
    base = {
        "run_id": "r", "framework_version": "1", "domain_pack_name": "p",
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


def test_collect_referenced_harvests_mas_from_findings_and_caps() -> None:
    art = _mas_artifacts(
        deduped_findings=[{
            "id": "rslv-00000001",
            "control_mappings": {"masvs": ["MASVS-STORAGE-1"], "maswe": ["MASWE-0001"]},
        }],
        deduped_capabilities=[{
            "id": "cap-1",
            "control_mappings": {"masvs": ["MASVS-CRYPTO-2"]},
        }],
    )
    refs = _collect_referenced_ids(art)
    assert "MASVS-STORAGE-1" in refs["masvs"]
    assert "MASVS-CRYPTO-2" in refs["masvs"]
    assert "MASWE-0001" in refs["maswe"]


def test_collect_referenced_harvests_mas_from_coverage_rollups() -> None:
    art = _mas_artifacts(
        masvs_coverage={"controls": [
            {"masvs_id": "MASVS-NETWORK-1", "finding_count": 1},
            {"masvs_id": "MASVS-AUTH-2", "finding_count": 0},
        ]},
        maswe_coverage={"entries": [
            {"maswe_id": "MASWE-0002", "finding_count": 1},
        ]},
    )
    refs = _collect_referenced_ids(art)
    assert {"MASVS-NETWORK-1", "MASVS-AUTH-2"} <= refs["masvs"]
    assert "MASWE-0002" in refs["maswe"]


def test_taxonomy_resolves_masvs_control_with_title_and_url() -> None:
    art = _mas_artifacts(
        deduped_findings=[{
            "id": "rslv-00000001",
            "control_mappings": {"masvs": ["MASVS-STORAGE-1"]},
        }],
    )
    tax = taxonomy_dict(art)
    assert tax["MASVS-STORAGE-1"]["family"] == "OWASP MASVS"
    assert tax["MASVS-STORAGE-1"]["title"]  # resolved statement, not bare id
    # masvs_url is pure-regex; always present for a well-formed control id.
    assert tax["MASVS-STORAGE-1"]["url"] == (
        "https://mas.owasp.org/MASVS/controls/MASVS-STORAGE-1/"
    )


def test_taxonomy_resolves_maswe_weakness_with_family_and_title() -> None:
    art = _mas_artifacts(
        deduped_findings=[{
            "id": "rslv-00000002",
            "control_mappings": {"maswe": ["MASWE-0001"]},
        }],
    )
    tax = taxonomy_dict(art)
    assert tax["MASWE-0001"]["family"] == "OWASP MASWE"
    assert tax["MASWE-0001"]["title"]
    # maswe_url returns a string for a known filing category; the branch sets
    # "url" only when non-None, so assert the family + title even if url omitted.
    if "url" in tax["MASWE-0001"]:
        assert tax["MASWE-0001"]["url"].startswith("https://mas.owasp.org/MASWE/")
