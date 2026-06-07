"""Tests for the `apd-gauntlet analyze-attack-paths` CLI subcommand (Task C-15).

The subcommand wires Tasks C-10 (build) → C-11 (enumerate) → C-12 (D3FEND
overlay) → C-14 (findings) together and writes four artifacts under the
run directory's `40-synthesis/` folder. These tests scaffold a fresh run
directory by copying the C-10 minimal-run fixture into ``tmp_path`` and
optionally mutating the run-config to exercise tuning / blocked branches.
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

import yaml
from apd_gauntlet.cli import main
from click.testing import CliRunner
from jsonschema import Draft202012Validator
from referencing import Registry, Resource

FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "attack_path" / "minimal-run"
REPO_ROOT = Path(__file__).parent.parent
SCHEMA_DIR = REPO_ROOT / "schemas"


def _build_registry() -> Registry:
    """Build a referencing.Registry containing every schema under ``schemas/``
    so that ``$ref``/``$id`` lookups resolve during validation.
    """
    resources = []
    for schema_path in sorted(SCHEMA_DIR.glob("*.schema.json")):
        schema = json.loads(schema_path.read_text())
        sid = schema.get("$id")
        if sid:
            resources.append((sid, Resource.from_contents(schema)))
    return Registry().with_resources(resources)


def _scaffold_minimal_run(
    tmp_path: Path,
    *,
    max_hop: int | None = None,
    max_paths_per_pair: int | None = None,
    bottleneck_threshold: int | None = None,
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
    if (
        max_hop is not None
        or max_paths_per_pair is not None
        or bottleneck_threshold is not None
    ):
        cfg_path = tmp_path / ".apd-run.yaml"
        cfg: dict[str, Any] = yaml.safe_load(cfg_path.read_text()) or {}
        tuning = cfg.setdefault("attack_path_analysis", {})
        if max_hop is not None:
            tuning["max_hop"] = max_hop
        if max_paths_per_pair is not None:
            tuning["max_paths_per_pair"] = max_paths_per_pair
        if bottleneck_threshold is not None:
            tuning["bottleneck_threshold"] = bottleneck_threshold
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
    assert (synth / "attack-path.findings.yaml").exists()


def test_analyze_attack_paths_emits_blocked_finding_when_no_crown_jewels(
    tmp_path: Path,
) -> None:
    runner = CliRunner()
    _scaffold_run_without_crown_jewels(tmp_path)
    result = runner.invoke(main, ["analyze-attack-paths", str(tmp_path)])
    assert result.exit_code == 0, result.output  # blocked is not an error
    findings_doc = yaml.safe_load(
        (tmp_path / "40-synthesis" / "attack-path.findings.yaml").read_text()
    )
    blocked = [f for f in findings_doc["finding"] if f["disposition"] == "blocked"]
    assert blocked
    assert "crown jewels" in blocked[0]["title"].lower()


def test_analyze_attack_paths_honors_run_config_tuning(tmp_path: Path) -> None:
    runner = CliRunner()
    _scaffold_minimal_run(
        tmp_path, max_hop=4, max_paths_per_pair=10, bottleneck_threshold=3
    )
    result = runner.invoke(main, ["analyze-attack-paths", str(tmp_path)])
    assert result.exit_code == 0, result.output
    attack_paths = yaml.safe_load(
        (tmp_path / "40-synthesis" / "attack-paths.yaml").read_text()
    )
    assert attack_paths["enumeration_parameters"]["max_hop"] == 4
    assert attack_paths["enumeration_parameters"]["max_paths_per_pair"] == 10
    assert attack_paths["enumeration_parameters"]["bottleneck_threshold"] == 3


def test_analyze_attack_paths_validate_does_not_crash(
    tmp_path: Path,
) -> None:
    """Regression guard: ``apd-gauntlet validate`` exits 0 against a run
    directory containing the four C-15 artifacts. Post-C-21, validate
    schema-checks the three graph artifacts via ``SYNTHESIS_ROLLUPS`` and
    iterates ``attack-path.findings.yaml`` records via the ``*.findings.yaml``
    glob — so this test now exercises real validation (not a vacuous pass).
    """
    runner = CliRunner()
    _scaffold_minimal_run(tmp_path)
    result = runner.invoke(main, ["analyze-attack-paths", str(tmp_path)])
    assert result.exit_code == 0, result.output
    result2 = runner.invoke(main, ["validate", str(tmp_path)])
    assert result2.exit_code == 0, result2.output


def test_analyze_attack_paths_emits_schema_valid_artifacts(
    tmp_path: Path,
) -> None:
    """Directly validate every C-15-emitted artifact against its JSON Schema.

    Independent schema check that doesn't depend on ``apd-gauntlet validate``'s
    wiring — useful as a focused regression guard against schema drift in any
    of the four artifact emitters, even if a future refactor changes how
    ``validate`` discovers Phase C files.
    """
    runner = CliRunner()
    _scaffold_minimal_run(tmp_path)
    result = runner.invoke(main, ["analyze-attack-paths", str(tmp_path)])
    assert result.exit_code == 0, result.output

    synth = tmp_path / "40-synthesis"
    registry = _build_registry()

    # Top-level documents validate as a whole against their schema.
    for filename, schema_name in [
        ("asset-graph.yaml",    "asset-graph.schema.json"),
        ("attack-paths.yaml",   "attack-path.schema.json"),
        ("defense-graph.yaml",  "defense-graph.schema.json"),
    ]:
        doc = yaml.safe_load((synth / filename).read_text())
        schema = json.loads((SCHEMA_DIR / schema_name).read_text())
        validator = Draft202012Validator(schema, registry=registry)
        errors = list(validator.iter_errors(doc))
        assert errors == [], (
            f"{filename} failed schema validation: "
            f"{[e.message for e in errors]}"
        )

    # The findings file is a wrapper {schema_version, finding: [...]} per the
    # singular root-key convention in validate.RECORD_KINDS; finding.schema.json
    # describes one finding record, so iterate.
    findings_doc = yaml.safe_load(
        (synth / "attack-path.findings.yaml").read_text()
    )
    finding_schema = json.loads(
        (SCHEMA_DIR / "finding.schema.json").read_text()
    )
    finding_validator = Draft202012Validator(finding_schema, registry=registry)
    for f in findings_doc["finding"]:
        errors = list(finding_validator.iter_errors(f))
        assert errors == [], (
            f"finding {f.get('id')} failed schema validation: "
            f"{[e.message for e in errors]}"
        )


def test_analyze_attack_paths_defaults_max_risk_findings_per_pair_to_one(
    tmp_path: Path, monkeypatch: Any
) -> None:
    """With no override, the CLI passes ``max_risk_per_pair=1`` to emit_findings
    (the bounded default for every run)."""
    import apd_gauntlet.attack_path.findings as findings_mod

    captured: dict[str, Any] = {}
    real_emit = findings_mod.emit_findings

    def _spy(*args: Any, **kwargs: Any) -> Any:
        captured.update(kwargs)
        return real_emit(*args, **kwargs)

    monkeypatch.setattr(findings_mod, "emit_findings", _spy)

    runner = CliRunner()
    _scaffold_minimal_run(tmp_path)
    result = runner.invoke(main, ["analyze-attack-paths", str(tmp_path)])
    assert result.exit_code == 0, result.output
    assert captured.get("max_risk_per_pair") == 1
    assert captured.get("bound") is True


def test_analyze_attack_paths_honors_max_risk_findings_per_pair(
    tmp_path: Path, monkeypatch: Any
) -> None:
    """The analyze-attack-paths CLI must read
    ``attack_path_analysis.max_risk_findings_per_pair`` from the run-config and
    thread it into emit_findings as ``max_risk_per_pair``."""
    import apd_gauntlet.attack_path.findings as findings_mod

    captured: dict[str, Any] = {}
    real_emit = findings_mod.emit_findings

    def _spy(*args: Any, **kwargs: Any) -> Any:
        captured.update(kwargs)
        return real_emit(*args, **kwargs)

    monkeypatch.setattr(findings_mod, "emit_findings", _spy)

    runner = CliRunner()
    _scaffold_minimal_run(tmp_path)
    cfg_path = tmp_path / ".apd-run.yaml"
    cfg = yaml.safe_load(cfg_path.read_text()) or {}
    cfg.setdefault("attack_path_analysis", {})["max_risk_findings_per_pair"] = 3
    cfg_path.write_text(yaml.safe_dump(cfg, sort_keys=False))

    result = runner.invoke(main, ["analyze-attack-paths", str(tmp_path)])
    assert result.exit_code == 0, result.output
    assert captured.get("max_risk_per_pair") == 3


def test_analyze_attack_paths_keeps_every_path_in_attack_paths_yaml(
    tmp_path: Path,
) -> None:
    """attack-paths.yaml is the artifact of record: every enumerated path is
    retained there regardless of the findings bound. Only the findings file is
    bounded — so the path count in attack-paths.yaml must NOT shrink when the
    findings are capped."""
    runner = CliRunner()
    _scaffold_minimal_run(tmp_path)
    result = runner.invoke(main, ["analyze-attack-paths", str(tmp_path)])
    assert result.exit_code == 0, result.output
    attack_paths = yaml.safe_load(
        (tmp_path / "40-synthesis" / "attack-paths.yaml").read_text()
    )
    # The summary echoes the path count; it must match the actual paths list.
    paths = attack_paths.get("paths", [])
    # The default bound caps findings, but every path stays in attack-paths.yaml.
    findings_doc = yaml.safe_load(
        (tmp_path / "40-synthesis" / "attack-path.findings.yaml").read_text()
    )
    risk = [f for f in findings_doc["finding"] if f["disposition"] == "risk"]
    # Bound is on by default: risk findings are at most one per pair, which for
    # this fixture is far fewer than the raw path count.
    assert len(paths) >= len(risk), (
        "attack-paths.yaml must retain every path even when findings are bounded"
    )


def test_analyze_attack_paths_output_is_iterable_by_validate(tmp_path: Path) -> None:
    """End-to-end regression: the analyzer's emitted ``attack-path.findings.yaml``
    must satisfy *both* the ``*.findings.yaml`` glob *and* the singular
    ``finding:`` root key that ``validate._iter_records`` keys off.

    Pre-C-20 the file was named ``attack-path-findings.yaml`` (hyphen) and
    therefore did not match the ``*.findings.yaml`` glob — so ``apath-*``
    records never reached the synthesizer's matrix. The C-20 rename closed
    the filename half of that gap; this test guards the convention half:
    if any future change re-introduces the plural ``findings:`` root key,
    ``_iter_records`` will return zero apath records and this assertion
    will fail loudly.
    """
    from apd_gauntlet.validate import _iter_records

    runner = CliRunner()
    _scaffold_minimal_run(tmp_path)
    result = runner.invoke(main, ["analyze-attack-paths", str(tmp_path)])
    assert result.exit_code == 0, result.output

    all_records = list(_iter_records(tmp_path))
    finding_records = [rec for _path, kind, rec in all_records if kind == "finding"]
    apath_records = [
        r for r in finding_records if str(r.get("id", "")).startswith("apath-")
    ]
    assert apath_records, (
        "analyzer findings should be reachable via _iter_records — was broken "
        "pre-C-20 by the filename+root-key convention split"
    )
