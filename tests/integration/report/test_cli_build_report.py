"""End-to-end integration: build_report against the canonical example fixture
writes the expected directory structure to tmp_path.
"""
from __future__ import annotations

import pathlib

import pytest
from apd_gauntlet.report.build import build_report

REPO = pathlib.Path(__file__).resolve().parents[3]
FIXTURE_RUN = REPO / "examples" / "apd-20260601-claim-event-bus" / "expected"


@pytest.fixture(autouse=True)
def _require_bundle() -> None:
    """Skip these tests if the precompiled bundle hasn't been generated yet.
    During Phase D this fixture stays skipped until Task 5.4 lands the bundle.
    """
    bundle = REPO / "tools" / "apd_gauntlet" / "data" / "report-template"
    if not bundle.exists() or not (bundle / "index.html").exists():
        pytest.skip("precompiled report-template bundle not present")


def test_build_writes_data_js(tmp_path: pathlib.Path) -> None:
    out, _ = build_report(FIXTURE_RUN, out_dir=tmp_path)
    assert (out / "data.js").exists()
    body = (out / "data.js").read_text()
    assert "window.APD_DATA" in body


def test_build_writes_index_html_and_bundle(tmp_path: pathlib.Path) -> None:
    out, _ = build_report(FIXTURE_RUN, out_dir=tmp_path)
    assert (out / "index.html").exists()
    assert (out / "app.js").exists()
    assert (out / "styles.css").exists()


def test_build_writes_manifest(tmp_path: pathlib.Path) -> None:
    out, _ = build_report(FIXTURE_RUN, out_dir=tmp_path)
    manifest = (out / "build-manifest.txt").read_text()
    assert "framework_version=" in manifest
    assert "deduped-findings.yaml=" in manifest


def test_build_default_out_dir_is_under_synthesis(tmp_path: pathlib.Path) -> None:
    # Copy the fixture into tmp_path so we can write into it safely.
    import shutil as _sh
    work = tmp_path / "run"
    _sh.copytree(FIXTURE_RUN, work)
    out, _ = build_report(work)
    assert out == work / "40-synthesis" / "report-html"
    assert (out / "data.js").exists()


def test_cli_build_report_smoke(tmp_path: pathlib.Path) -> None:
    """Invoke the Click command from Python."""
    from apd_gauntlet.cli import build_report_cmd
    from click.testing import CliRunner

    result = CliRunner().invoke(
        build_report_cmd,
        [str(FIXTURE_RUN), "--out", str(tmp_path)],
    )
    assert result.exit_code == 0, result.output
    assert (tmp_path / "data.js").exists()
