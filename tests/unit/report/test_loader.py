"""Loader unit tests against the canonical legacy_example fixture run."""
from __future__ import annotations

import pathlib

import pytest
from apd_gauntlet.report.loader import (
    MissingArtifactError,
    load_run,
)


def test_load_run_returns_artifacts(legacy_example_run: pathlib.Path) -> None:
    artifacts = load_run(legacy_example_run)
    assert artifacts.run_id == "apd-legacy-example-run"
    assert artifacts.framework_version == "1.4.0"
    assert artifacts.domain_pack_name == "pbm"


def test_load_run_findings_and_capabilities_present(legacy_example_run: pathlib.Path) -> None:
    artifacts = load_run(legacy_example_run)
    assert len(artifacts.deduped_findings) >= 40
    assert len(artifacts.deduped_capabilities) >= 40


def test_load_run_includes_attack_paths(legacy_example_run: pathlib.Path) -> None:
    artifacts = load_run(legacy_example_run)
    assert artifacts.attack_paths is not None
    assert artifacts.attack_paths["paths"], "expected at least one enumerated path"
    assert artifacts.asset_graph is not None
    assert artifacts.defense_graph is not None


def test_load_run_missing_required_raises(tmp_path: pathlib.Path) -> None:
    empty = tmp_path / "empty-run"
    empty.mkdir()
    with pytest.raises(MissingArtifactError) as exc:
        load_run(empty)
    assert ".apd-run.yaml" in str(exc.value) or "asset-inventory" in str(exc.value)


def test_load_run_optional_report_data_absent_is_none(legacy_example_run: pathlib.Path) -> None:
    """The legacy_example fixture predates report-data.yaml — loader returns None."""
    artifacts = load_run(legacy_example_run)
    assert artifacts.report_data is None
