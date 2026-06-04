# tests/unit/report/test_transform_taxonomy.py
from __future__ import annotations

import pathlib
from typing import Any

from apd_gauntlet.report.loader import RunArtifacts, load_run
from apd_gauntlet.report.transform import taxonomy_dict

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
