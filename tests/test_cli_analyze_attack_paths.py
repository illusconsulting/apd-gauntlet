"""Tests for the `apd-gauntlet analyze-attack-paths` CLI subcommand (Task C-15).

The subcommand wires Tasks C-10 (build) → C-11 (enumerate) → C-12 (D3FEND
overlay) → C-14 (findings) together and writes four artifacts under the
run directory's `40-synthesis/` folder. These tests scaffold a fresh run
directory by copying the C-10 minimal-run fixture into ``tmp_path`` and
optionally mutating the run-config to exercise tuning / blocked branches.
"""
from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

import yaml
from apd_gauntlet.cli import main
from click.testing import CliRunner

FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "attack_path" / "minimal-run"


def _scaffold_minimal_run(
    tmp_path: Path,
    *,
    max_hop: int | None = None,
    max_paths_per_pair: int | None = None,
) -> None:
    """Copy the C-10 minimal-run fixture into ``tmp_path`` and optionally
    override the ``attack_path_analysis`` tuning knobs in ``.apd-run.yaml``.
    """
    for child in FIXTURE_ROOT.iterdir():
        dst = tmp_path / child.name
        if child.is_dir():
            shutil.copytree(child, dst)
        else:
            shutil.copy2(child, dst)
    if max_hop is not None or max_paths_per_pair is not None:
        cfg_path = tmp_path / ".apd-run.yaml"
        cfg: dict[str, Any] = yaml.safe_load(cfg_path.read_text()) or {}
        tuning = cfg.setdefault("attack_path_analysis", {})
        if max_hop is not None:
            tuning["max_hop"] = max_hop
        if max_paths_per_pair is not None:
            tuning["max_paths_per_pair"] = max_paths_per_pair
        cfg_path.write_text(yaml.safe_dump(cfg, sort_keys=False))


def _scaffold_run_without_crown_jewels(tmp_path: Path) -> None:
    """Copy the C-10 minimal-run fixture into ``tmp_path``, then strip
    ``crown_jewels`` from both the run-config and the domain pack so the
    builder raises ``BuilderBlocked``.
    """
    _scaffold_minimal_run(tmp_path)
    cfg_path = tmp_path / ".apd-run.yaml"
    cfg = yaml.safe_load(cfg_path.read_text()) or {}
    cfg["crown_jewels"] = []
    cfg_path.write_text(yaml.safe_dump(cfg, sort_keys=False))
    dom_path = tmp_path / "domains" / "pbm.yaml"
    dom = yaml.safe_load(dom_path.read_text()) or {}
    dom["crown_jewels"] = []
    dom_path.write_text(yaml.safe_dump(dom, sort_keys=False))


def test_analyze_attack_paths_writes_four_artifacts(tmp_path: Path) -> None:
    runner = CliRunner()
    _scaffold_minimal_run(tmp_path)
    result = runner.invoke(main, ["analyze-attack-paths", str(tmp_path)])
    assert result.exit_code == 0, result.output
    synth = tmp_path / "40-synthesis"
    assert (synth / "asset-graph.yaml").exists()
    assert (synth / "attack-paths.yaml").exists()
    assert (synth / "defense-graph.yaml").exists()
    assert (synth / "attack-path-findings.yaml").exists()


def test_analyze_attack_paths_emits_blocked_finding_when_no_crown_jewels(
    tmp_path: Path,
) -> None:
    runner = CliRunner()
    _scaffold_run_without_crown_jewels(tmp_path)
    result = runner.invoke(main, ["analyze-attack-paths", str(tmp_path)])
    assert result.exit_code == 0, result.output  # blocked is not an error
    findings_doc = yaml.safe_load(
        (tmp_path / "40-synthesis" / "attack-path-findings.yaml").read_text()
    )
    blocked = [f for f in findings_doc["findings"] if f["disposition"] == "blocked"]
    assert blocked
    assert "crown jewels" in blocked[0]["title"].lower()


def test_analyze_attack_paths_honors_run_config_tuning(tmp_path: Path) -> None:
    runner = CliRunner()
    _scaffold_minimal_run(tmp_path, max_hop=4, max_paths_per_pair=10)
    result = runner.invoke(main, ["analyze-attack-paths", str(tmp_path)])
    assert result.exit_code == 0, result.output
    attack_paths = yaml.safe_load(
        (tmp_path / "40-synthesis" / "attack-paths.yaml").read_text()
    )
    assert attack_paths["enumeration_parameters"]["max_hop"] == 4
    assert attack_paths["enumeration_parameters"]["max_paths_per_pair"] == 10


def test_analyze_attack_paths_validates_output_against_schemas(
    tmp_path: Path,
) -> None:
    runner = CliRunner()
    _scaffold_minimal_run(tmp_path)
    result = runner.invoke(main, ["analyze-attack-paths", str(tmp_path)])
    assert result.exit_code == 0, result.output
    result2 = runner.invoke(main, ["validate", str(tmp_path)])
    assert result2.exit_code == 0, result2.output
