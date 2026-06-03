"""Pass-1 tests: schema validation of records in a run directory."""
from __future__ import annotations

import pathlib
import shutil
from textwrap import dedent

from apd_gauntlet.cli import main
from click.testing import CliRunner

FIXTURES = pathlib.Path(__file__).parent / "fixtures" / "runs"


def _copy_clean_run(tmp_path: pathlib.Path) -> pathlib.Path:
    dst = tmp_path / "run"
    shutil.copytree(FIXTURES / "clean-run", dst)
    return dst


def test_validate_clean_run_returns_zero():
    runner = CliRunner()
    result = runner.invoke(main, ["validate", str(FIXTURES / "clean-run")])
    assert result.exit_code == 0, result.output


def test_validate_run_with_bad_record_returns_one(tmp_path):
    src = FIXTURES / "clean-run"
    dst = tmp_path / "run"
    shutil.copytree(src, dst)
    # Corrupt the finding by deleting required `severity:` line.
    finding_file = dst / "10-trustworthiness" / "confidentiality.findings.yaml"
    text = finding_file.read_text()
    finding_file.write_text(text.replace("  severity: high\n", ""))
    runner = CliRunner()
    result = runner.invoke(main, ["validate", str(dst)])
    assert result.exit_code == 1
    assert "severity" in result.output.lower()


def test_validate_picks_up_valid_cwe_coverage_rollup(tmp_path):
    dst = _copy_clean_run(tmp_path)
    (dst / "40-synthesis" / "cwe-coverage.yaml").write_text(dedent("""\
        schema_version: 1
        generated_by: synthesizer
        entries:
          - cwe_id: CWE-287
            name: "Improper Authentication"
            abstraction: class
            finding_count: 1
            finding_ids: [conf-deadbeef]
    """))
    runner = CliRunner()
    result = runner.invoke(main, ["validate", str(dst)])
    assert result.exit_code == 0, result.output
    # Baseline clean-run scans 2 files; the rollup adds 1.
    assert "Files scanned: 3" in result.output


def test_validate_rejects_malformed_cwe_coverage(tmp_path):
    dst = _copy_clean_run(tmp_path)
    (dst / "40-synthesis" / "cwe-coverage.yaml").write_text(dedent("""\
        schema_version: 1
        generated_by: synthesizer
        entries:
          - cwe_id: "NOT-A-CWE"
            name: "broken"
            abstraction: base
            finding_count: 1
            finding_ids: [conf-deadbeef]
    """))
    runner = CliRunner()
    result = runner.invoke(main, ["validate", str(dst)])
    assert result.exit_code == 1
    assert "cwe-coverage.yaml" in result.output


def test_validate_picks_up_valid_owasp_coverage_rollup(tmp_path):
    dst = _copy_clean_run(tmp_path)
    (dst / "40-synthesis" / "owasp-coverage.yaml").write_text(dedent("""\
        schema_version: 1
        generated_by: synthesizer
        entries:
          - taxonomy: owasp_api_top10
            category_id: "API2:2023"
            name: "Broken Authentication"
            finding_count: 0
            finding_ids: []
            silent: true
    """))
    runner = CliRunner()
    result = runner.invoke(main, ["validate", str(dst)])
    assert result.exit_code == 0, result.output
    assert "Files scanned: 3" in result.output


def test_validate_rejects_malformed_owasp_coverage(tmp_path):
    dst = _copy_clean_run(tmp_path)
    # owasp_llm_top10 with LLM00 — outside published range, blocked by the
    # tightened pattern from Task B-2.
    (dst / "40-synthesis" / "owasp-coverage.yaml").write_text(dedent("""\
        schema_version: 1
        generated_by: synthesizer
        entries:
          - taxonomy: owasp_llm_top10
            category_id: "LLM00"
            name: "Imaginary Category"
            finding_count: 0
            finding_ids: []
            silent: true
    """))
    runner = CliRunner()
    result = runner.invoke(main, ["validate", str(dst)])
    assert result.exit_code == 1
    assert "owasp-coverage.yaml" in result.output


def test_validate_picks_up_valid_d3fend_coverage_rollup(tmp_path):
    dst = _copy_clean_run(tmp_path)
    (dst / "40-synthesis" / "d3fend-coverage.yaml").write_text(dedent("""\
        schema_version: 1
        generated_by: synthesizer
        defensive_entries:
          - d3fend_id: D3-AA
            name: "Agent Authentication"
            capability_count: 0
            capability_ids: []
            counters_attack: ["T1078"]
        counter_coverage:
          - attack_technique: T1530
            exposed_by_finding_count: 0
            exposed_by_finding_ids: []
            countered_by_d3fend: []
            countered_by_capability_ids: []
            has_capability_coverage: false
    """))
    runner = CliRunner()
    result = runner.invoke(main, ["validate", str(dst)])
    assert result.exit_code == 0, result.output
    assert "Files scanned: 3" in result.output


def test_validate_rejects_malformed_d3fend_coverage(tmp_path):
    dst = _copy_clean_run(tmp_path)
    # Invalid d3fend_id breaks the ^D3-[A-Z]{2,7}$ pattern (now sourced from _defs).
    (dst / "40-synthesis" / "d3fend-coverage.yaml").write_text(dedent("""\
        schema_version: 1
        generated_by: synthesizer
        defensive_entries:
          - d3fend_id: "BAD-CODE"
            name: "Invalid"
            capability_count: 0
            capability_ids: []
            counters_attack: []
        counter_coverage: []
    """))
    runner = CliRunner()
    result = runner.invoke(main, ["validate", str(dst)])
    assert result.exit_code == 1
    assert "d3fend-coverage.yaml" in result.output


def test_validate_picks_up_valid_threat_model_coverage_rollup(tmp_path):
    dst = _copy_clean_run(tmp_path)
    (dst / "40-synthesis" / "threat-model-coverage.yaml").write_text(dedent("""\
        schema_version: 1
        generated_by: threat_model_evaluator
        methodology: stride
        surface_coverage:
          - surface: test-surface
            categories_present: [S, T]
            categories_absent: [R, I, D, E]
            tm_entry_count: 2
            tm_entry_ids: [tm-deadbeef, tm-cafebabe]
        summary:
          total_entries: 2
          contradictions_emitted: 0
          silences_emitted: 0
          coverage_gaps_emitted: 0
          surfaces_examined: 1
    """))
    runner = CliRunner()
    result = runner.invoke(main, ["validate", str(dst)])
    assert result.exit_code == 0, result.output
    # Baseline clean-run scans 2 files; the rollup adds 1.
    assert "Files scanned: 3" in result.output


def test_validate_picks_up_valid_threat_model_normalized_rollup(tmp_path):
    dst = _copy_clean_run(tmp_path)
    (dst / "00-context" / "threat-model-normalized.yaml").write_text(dedent("""\
        schema_version: 1
        generated_by: threat_model_recon
        source_artifact: inputs/threat-model.json
        methodology: stride
        extraction_summary:
          entry_count: 1
          high_confidence_count: 1
          low_confidence_count: 0
        entries:
          - entry_id: tm-deadbeef
            asset: test-asset
            threat: test-threat
            extraction_confidence: high
            methodology: stride
            framework_refs:
              stride_letter: S
              linddun_letter: null
              attack_tree_position: null
              mitre_attack: []
            inferred_apd_goals: [confidentiality]
    """))
    runner = CliRunner()
    result = runner.invoke(main, ["validate", str(dst)])
    assert result.exit_code == 0, result.output
    # Baseline clean-run scans 2 files; the rollup adds 1.
    assert "Files scanned: 3" in result.output


def test_validate_rejects_malformed_threat_model_coverage(tmp_path):
    dst = _copy_clean_run(tmp_path)
    # Invalid generated_by value
    (dst / "40-synthesis" / "threat-model-coverage.yaml").write_text(dedent("""\
        schema_version: 1
        generated_by: invalid_agent
        methodology: stride
        surface_coverage: []
        summary:
          total_entries: 0
          contradictions_emitted: 0
          silences_emitted: 0
          coverage_gaps_emitted: 0
    """))
    runner = CliRunner()
    result = runner.invoke(main, ["validate", str(dst)])
    assert result.exit_code == 1
    assert "threat-model-coverage.yaml" in result.output


def test_validate_rejects_malformed_threat_model_normalized(tmp_path):
    dst = _copy_clean_run(tmp_path)
    # Invalid generated_by value
    (dst / "00-context" / "threat-model-normalized.yaml").write_text(dedent("""\
        schema_version: 1
        generated_by: invalid_agent
        source_artifact: inputs/threat-model.json
        methodology: stride
        entries: []
    """))
    runner = CliRunner()
    result = runner.invoke(main, ["validate", str(dst)])
    assert result.exit_code == 1
    assert "threat-model-normalized.yaml" in result.output


def test_validate_picks_up_valid_threat_model_supplied_sibling(tmp_path):
    dst = _copy_clean_run(tmp_path)
    (dst / "00-context" / "threat-model-supplied-normalized.yaml").write_text(dedent("""\
        schema_version: 1
        generated_by: threat_model_recon
        source_artifact: inputs/threat-model.json
        methodology: stride
        entries:
          - entry_id: tm-deadbeef
            asset: test-asset
            threat: test-threat
            extraction_confidence: high
            methodology: stride
            framework_refs:
              stride_letter: S
              linddun_letter: null
              attack_tree_position: null
              mitre_attack: []
            inferred_apd_goals: [confidentiality]
    """))
    runner = CliRunner()
    result = runner.invoke(main, ["validate", str(dst)])
    assert result.exit_code == 0, result.output
    # Baseline clean-run scans 2 files; the sibling adds 1.
    assert "Files scanned: 3" in result.output


def test_validate_rejects_malformed_threat_model_supplied_sibling(tmp_path):
    dst = _copy_clean_run(tmp_path)
    # Invalid generated_by value — must be caught against the same schema.
    (dst / "00-context" / "threat-model-supplied-normalized.yaml").write_text(dedent("""\
        schema_version: 1
        generated_by: invalid_agent
        source_artifact: inputs/threat-model.json
        methodology: stride
        entries: []
    """))
    runner = CliRunner()
    result = runner.invoke(main, ["validate", str(dst)])
    assert result.exit_code == 1
    assert "threat-model-supplied-normalized.yaml" in result.output
