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
