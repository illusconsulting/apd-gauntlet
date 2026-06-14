"""Milestone-4 exit: end-to-end c4_model in window.APD_DATA on the committed fixture run."""
from __future__ import annotations

import pathlib
import shutil

import pytest
from apd_gauntlet.report.loader import load_run
from apd_gauntlet.report.transform import build_apd_data, c4_model_view
from click.testing import CliRunner

# Adaptation: the sibling report unit tests resolve the repo root with
# ``parents[3]`` (tests/unit/report/<file> -> repo). The plan's ``parent.parent``
# resolves only to ``tests/unit`` and would point REAL_RUN at a path that does
# not exist, silently skipping the whole module via ``pytestmark``.
REPO = pathlib.Path(__file__).resolve().parents[3]
REAL_RUN = REPO / "tests" / "fixtures" / "runs" / "c4-home-assistant"


def _assemble_c4_available() -> bool:
    try:
        from apd_gauntlet import assemble_c4  # noqa: F401
        from apd_gauntlet.cli import main  # noqa: F401
    except ImportError:
        return False
    from apd_gauntlet.cli import main

    return "assemble-c4" in (main.commands or {})


pytestmark = pytest.mark.skipif(
    not REAL_RUN.is_dir(), reason="real home-assistant run not present"
)


def _seed_load_run_required(synthesis: pathlib.Path) -> None:
    """Seed the synthesis artifacts ``load_run`` requires but the C4 fixture omits.

    The committed ``c4-home-assistant`` fixture (M0) ships *exactly the artifacts
    the C4 pipeline reads* (asset-graph, code-evidence-index, deduped findings /
    capabilities). ``load_run`` additionally requires four whole-report synthesis
    rollups. We stub them minimally so ``load_run`` -> ``build_apd_data`` succeeds
    while the assembler still consumes the real (14 zero-anchor repo) inputs, which
    keeps ``not_analyzed_count >= 1`` honest. None of these stubs feed the
    ``c4_model`` section under test.
    """
    seeds = {
        "nist-coverage.yaml": 'schema_version: 1\ngenerated_at: "2026-06-12"\ncoverage: []\n',
        "attack-exposure.yaml": (
            'schema_version: 1\ngenerated_at: "2026-06-12"\nexposed_assets: []\n'
        ),
        "apd-coverage-matrix.yaml": (
            'schema_version: 1\ngenerated_at: "2026-06-12"\nmatrix: []\n'
        ),
        "metrics.yaml": (
            'schema_version: 1\ngenerated_at: "2026-06-12"\n'
            "totals: {findings: 0, capabilities: 0}\n"
        ),
    }
    for name, body in seeds.items():
        target = synthesis / name
        if not target.exists():
            target.write_text(body, encoding="utf-8")


def _copy_and_assemble(tmp_path: pathlib.Path) -> pathlib.Path:
    dst = tmp_path / "run"
    shutil.copytree(REAL_RUN, dst)
    # Remove any previously-shipped c4-model so we assemble fresh from M2.
    stale = dst / "40-synthesis" / "c4-model.yaml"
    if stale.exists():
        stale.unlink()
    runner = CliRunner()
    result = runner.invoke(main_cli(), ["assemble-c4", str(dst)])
    assert result.exit_code == 0, result.output
    _seed_load_run_required(dst / "40-synthesis")
    return dst


def main_cli():
    from apd_gauntlet.cli import main

    return main


def test_real_run_c4_model_present_with_expected_counts(tmp_path: pathlib.Path) -> None:
    if not _assemble_c4_available():
        pytest.skip("assemble-c4 CLI not present yet (M2)")
    run = _copy_and_assemble(tmp_path)
    assert (run / "40-synthesis" / "c4-model.yaml").is_file()

    artifacts = load_run(run)
    assert artifacts.c4_model is not None
    assert artifacts.code_evidence_index is not None

    view = c4_model_view(artifacts)
    assert view["present"] is True
    # Container tier (L2) is grounded from asset-graph (75 nodes) + recon; the
    # code tier (L4) is present because code-evidence-index.yaml exists (40 anchors).
    assert "container" in view["levels_present"]
    assert "code" in view["levels_present"]
    # The run has 14 zero-anchor repos -> at least one not_analyzed container.
    assert view["not_analyzed_count"] >= 1
    # Honesty: doc-anchored-but-unlocalized findings are surfaced, never dropped.
    assert view["unlocalized_findings"] >= 0

    data = build_apd_data(artifacts, run_dir=run)
    assert data["c4_model"]["present"] is True
    assert data["c4_model"]["nodes"]
    assert "c4_model" not in data["meta"]["section_errors"]
