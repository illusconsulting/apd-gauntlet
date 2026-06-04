"""Loader unit tests against the canonical example fixture run."""
from __future__ import annotations

import pathlib

import pytest
from apd_gauntlet.report.loader import (
    MissingArtifactError,
    load_run,
)


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
