"""Loader unit tests against the canonical example fixture run."""
from __future__ import annotations

import pathlib

import pytest
from apd_gauntlet.report.loader import (
    MissingArtifactError,
    load_run,
)

REPO = pathlib.Path(__file__).resolve().parents[3]


def test_load_run_returns_artifacts(example_run: pathlib.Path) -> None:
    artifacts = load_run(example_run)
    assert artifacts.run_id == "apd-20260601-claim-event-bus"
    assert artifacts.framework_version == "1.4.0"
    assert artifacts.domain_pack_name == "pbm"


def test_load_run_findings_and_capabilities_present(example_run: pathlib.Path) -> None:
    artifacts = load_run(example_run)
    assert len(artifacts.deduped_findings) >= 10
    assert len(artifacts.deduped_capabilities) >= 5


def test_load_run_includes_attack_paths(example_run: pathlib.Path) -> None:
    artifacts = load_run(example_run)
    assert artifacts.attack_paths is not None
    assert artifacts.asset_graph is not None
    assert artifacts.defense_graph is not None
    # The example's attack-paths.yaml may carry zero paths if asset-inventory↔finding
    # edge connectivity is sparse; the file's presence + asset_graph + defense_graph
    # is what we assert.


def test_load_run_missing_required_raises(tmp_path: pathlib.Path) -> None:
    empty = tmp_path / "empty-run"
    empty.mkdir()
    with pytest.raises(MissingArtifactError) as exc:
        load_run(empty)
    assert ".apd-run.yaml" in str(exc.value) or "asset-inventory" in str(exc.value)


def test_load_run_report_data_present(example_run: pathlib.Path) -> None:
    """The example fixture ships with report-data.yaml; loader returns a non-None dict."""
    artifacts = load_run(example_run)
    assert artifacts.report_data is not None


def test_load_run_reads_threat_model_coverage(example_run: pathlib.Path) -> None:
    artifacts = load_run(example_run)
    # The example ships 40-synthesis/threat-model-coverage.yaml (evaluator output).
    assert isinstance(artifacts.threat_model_coverage, dict)
    assert isinstance(artifacts.threat_model_coverage.get("surface_coverage"), list)


def test_load_run_code_evidence_and_c4_absent_are_none(tmp_path: pathlib.Path) -> None:
    """A run with no code-evidence-index.yaml and no c4-model.yaml yields None
    for both new optional fields (never a guessed empty dict)."""
    # The acme-mobile-banking example ships neither artifact (the claim-event-bus
    # example now seeds a code-evidence-index.yaml, so it is unfit for this case).
    src = REPO / "examples" / "apd-20260602-acme-mobile-banking" / "expected"
    dst = tmp_path / "run"
    import shutil

    shutil.copytree(src, dst)
    # The example fixture ships neither artifact; assert that precondition then load.
    assert not (dst / "00-context" / "code-evidence-index.yaml").is_file()
    assert not (dst / "40-synthesis" / "c4-model.yaml").is_file()
    artifacts = load_run(dst)
    assert artifacts.code_evidence_index is None
    assert artifacts.c4_model is None


def test_load_run_reads_code_evidence_and_c4_when_present(tmp_path: pathlib.Path) -> None:
    """When both optional artifacts exist, load_run returns parsed dicts and
    records their content hashes in source_hashes."""
    src = REPO / "examples" / "apd-20260601-claim-event-bus" / "expected"
    dst = tmp_path / "run"
    import shutil

    shutil.copytree(src, dst)
    (dst / "00-context" / "code-evidence-index.yaml").write_text(
        "schema_version: 1\n"
        "generated_by: code_recon\n"
        "code_evidence_index:\n"
        "  entries:\n"
        "    - id: cev-aaaaaaaa\n"
        "      qualified_name: pkg.mod.fn\n"
        "      kind: function\n"
        "      file_path: pkg/mod.py\n"
        "      c4_container: api\n"
        "      c4_component: null\n"
        "      c4_level: code\n",
        encoding="utf-8",
    )
    (dst / "40-synthesis" / "c4-model.yaml").write_text(
        "schema_version: 1\n"
        "generated_by: assemble_c4\n"
        "nodes:\n"
        "  - id: c4-11111111\n"
        "    level: container\n"
        "    parent: null\n"
        "    name: api\n"
        "    kind: service\n"
        "    provenance: {source: c4-recon.yaml, locator: 'containers[0]', repo: core}\n"
        "    finding_count: 3\n"
        "    capability_count: 1\n"
        "    analysis_state: analyzed\n"
        "edges: []\n"
        "build_summary: {node_count: 1, container_count: 1}\n",
        encoding="utf-8",
    )
    artifacts = load_run(dst)
    assert isinstance(artifacts.code_evidence_index, dict)
    assert artifacts.code_evidence_index["generated_by"] == "code_recon"
    assert isinstance(artifacts.c4_model, dict)
    assert artifacts.c4_model["nodes"][0]["id"] == "c4-11111111"
    assert "code-evidence-index.yaml" in artifacts.source_hashes
    assert "c4-model.yaml" in artifacts.source_hashes
