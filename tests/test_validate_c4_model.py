"""validate.py registers c4-model.yaml + c4-recon.yaml (optional, presence-gated)."""
from __future__ import annotations

import pathlib
import shutil

import pytest
from apd_gauntlet.cli import main
from apd_gauntlet.validate import CONTEXT_ROLLUPS, SCHEMAS_DIR, SYNTHESIS_ROLLUPS
from click.testing import CliRunner

FIXTURES = pathlib.Path(__file__).parent / "fixtures" / "runs"


def test_c4_model_registered_in_synthesis_rollups() -> None:
    assert SYNTHESIS_ROLLUPS.get("c4-model.yaml") == "c4-model.schema.json"


def test_c4_recon_registered_in_context_rollups() -> None:
    assert CONTEXT_ROLLUPS.get("c4-recon.yaml") == "c4-recon.schema.json"


def test_validate_passes_clean_run_without_c4_model() -> None:
    """c4-model.yaml is presence-gated: a clean run lacking it still validates."""
    runner = CliRunner()
    result = runner.invoke(main, ["validate", str(FIXTURES / "clean-run")])
    assert result.exit_code == 0, result.output


def test_validate_flags_malformed_c4_model(tmp_path: pathlib.Path) -> None:
    """A present-but-malformed c4-model.yaml is caught by the schema pass."""
    if not (SCHEMAS_DIR / "c4-model.schema.json").is_file():
        pytest.skip("c4-model.schema.json not authored yet (M1)")
    dst = tmp_path / "run"
    shutil.copytree(FIXTURES / "clean-run", dst)
    # nodes must be an array per the schema; a scalar is malformed.
    (dst / "40-synthesis" / "c4-model.yaml").write_text(
        "schema_version: 1\n"
        "generated_by: assemble_c4\n"
        "nodes: not-a-list\n"
        "edges: []\n"
        "build_summary: {}\n",
        encoding="utf-8",
    )
    runner = CliRunner()
    result = runner.invoke(main, ["validate", str(dst)])
    assert result.exit_code == 1
    assert "c4-model.yaml" in result.output


def test_validate_accepts_valid_c4_model(tmp_path: pathlib.Path) -> None:
    """A present, well-formed c4-model.yaml validates cleanly (presence-gated)."""
    if not (SCHEMAS_DIR / "c4-model.schema.json").is_file():
        pytest.skip("c4-model.schema.json not authored yet (M1)")
    dst = tmp_path / "run"
    shutil.copytree(FIXTURES / "clean-run", dst)
    (dst / "40-synthesis" / "c4-model.yaml").write_text(
        "schema_version: 1\n"
        "generated_by: assemble_c4\n"
        "nodes:\n"
        "  - id: c4-11111111\n"
        "    level: container\n"
        "    parent: null\n"
        "    name: api\n"
        "    kind: service\n"
        "    provenance: {source: artifact, artifact: c4-recon.yaml, locator: 'containers[0]'}\n"
        "    finding_count: 0\n"
        "    capability_count: 0\n"
        "    analysis_state: analyzed\n"
        "edges: []\n"
        "build_summary:\n"
        "  node_count: 1\n"
        "  system_count: 0\n"
        "  person_count: 0\n"
        "  external_system_count: 0\n"
        "  container_count: 1\n"
        "  component_count: 0\n"
        "  code_count: 0\n"
        "  uses_edge_count: 0\n"
        "  unlocalized_finding_count: 0\n"
        "  not_analyzed_container_count: 0\n",
        encoding="utf-8",
    )
    runner = CliRunner()
    result = runner.invoke(main, ["validate", str(dst)])
    assert result.exit_code == 0, result.output
