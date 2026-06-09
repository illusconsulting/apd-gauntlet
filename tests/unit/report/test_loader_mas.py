from __future__ import annotations

import pathlib

import yaml
from apd_gauntlet.report.loader import RunArtifacts, load_run

EMPTY_METRICS = {"schema_version": 1, "findings_total": 0}


def _bare_artifacts(**overrides) -> RunArtifacts:
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


def test_runartifacts_mas_fields_default_empty() -> None:
    art = _bare_artifacts()
    assert art.masvs_coverage is None
    assert art.maswe_coverage is None
    assert art.active_taxonomies == []


def test_runartifacts_mas_fields_accept_values() -> None:
    art = _bare_artifacts(
        masvs_coverage={"controls": []},
        maswe_coverage={"entries": []},
        active_taxonomies=["masvs", "maswe"],
    )
    assert art.masvs_coverage == {"controls": []}
    assert art.maswe_coverage == {"entries": []}
    assert art.active_taxonomies == ["masvs", "maswe"]


def _write(run_dir: pathlib.Path, rel: str, doc: dict) -> None:
    p = run_dir / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(yaml.safe_dump(doc), encoding="utf-8")


def _minimal_run(run_dir: pathlib.Path) -> None:
    _write(run_dir, ".apd-run.yaml", {
        "run_id": "r", "domains": ["mobile-applications"],
        "framework_version": "1.7.0", "taxonomies": ["masvs", "maswe"],
    })
    _write(run_dir, "00-context/asset-inventory.yaml", {"assets": []})
    _write(run_dir, "40-synthesis/deduped-findings.yaml", {"finding": []})
    _write(run_dir, "40-synthesis/deduped-capabilities.yaml", {"capability": []})
    _write(run_dir, "40-synthesis/nist-coverage.yaml", {})
    _write(run_dir, "40-synthesis/attack-exposure.yaml", {})
    _write(run_dir, "40-synthesis/apd-coverage-matrix.yaml", {})
    _write(run_dir, "40-synthesis/metrics.yaml", {"schema_version": 1})


def test_load_run_reads_mas_coverage_and_taxonomies(tmp_path: pathlib.Path) -> None:
    run = tmp_path / "run"
    _minimal_run(run)
    _write(run, "40-synthesis/masvs-coverage.yaml", {
        "schema_version": 1, "generated_by": "synthesizer",
        "controls": [{"masvs_id": "MASVS-STORAGE-1", "finding_count": 2}],
    })
    _write(run, "40-synthesis/maswe-coverage.yaml", {
        "schema_version": 1, "generated_by": "synthesizer",
        "entries": [{"maswe_id": "MASWE-0001", "finding_count": 1}],
    })
    art = load_run(run)
    assert art.masvs_coverage["controls"][0]["masvs_id"] == "MASVS-STORAGE-1"
    assert art.maswe_coverage["entries"][0]["maswe_id"] == "MASWE-0001"
    assert art.active_taxonomies == ["masvs", "maswe"]
    # MAS coverage files participate in the freshness source-hash set.
    assert "masvs-coverage.yaml" in art.source_hashes
    assert "maswe-coverage.yaml" in art.source_hashes


def test_load_run_omits_mas_when_absent(tmp_path: pathlib.Path) -> None:
    run = tmp_path / "run"
    _minimal_run(run)
    # remove the taxonomies key to model a non-mobile run
    cfg = run / ".apd-run.yaml"
    cfg.write_text(yaml.safe_dump({
        "run_id": "r", "domains": ["pbm"], "framework_version": "1.7.0",
    }), encoding="utf-8")
    art = load_run(run)
    assert art.masvs_coverage is None
    assert art.maswe_coverage is None
    assert art.active_taxonomies == []
    assert "masvs-coverage.yaml" not in art.source_hashes
