"""Edge-case tests to bring validator coverage above 85%."""
from __future__ import annotations

import json
import pathlib
import shutil

import pytest
from apd_gauntlet import validate as v
from apd_gauntlet.cli import main
from click.testing import CliRunner

FIXTURES = pathlib.Path(__file__).parent / "fixtures" / "runs"


def _copy_clean_run(tmp_path: pathlib.Path) -> pathlib.Path:
    dst = tmp_path / "run"
    shutil.copytree(FIXTURES / "clean-run", dst)
    return dst


# ---------------------------------------------------------------------------
# parse_intake_brief edge cases
# ---------------------------------------------------------------------------


def test_parse_intake_brief_missing_file(tmp_path: pathlib.Path) -> None:
    """parse_intake_brief returns {} when the file does not exist."""
    result = v.parse_intake_brief(tmp_path / "nonexistent.md")
    assert result == {}


def test_parse_intake_brief_no_frontmatter(tmp_path: pathlib.Path) -> None:
    """parse_intake_brief returns {} when the file has no frontmatter."""
    brief = tmp_path / "brief.md"
    brief.write_text("# Just a markdown file\n\nNo frontmatter here.\n")
    assert v.parse_intake_brief(brief) == {}


def test_parse_intake_brief_unclosed_frontmatter(tmp_path: pathlib.Path) -> None:
    """parse_intake_brief returns {} when frontmatter has no closing '---'."""
    brief = tmp_path / "brief.md"
    brief.write_text("---\nfoo: bar\nbaz: qux\n# Body without closing.\n")
    assert v.parse_intake_brief(brief) == {}


# ---------------------------------------------------------------------------
# YAML parse-error path
# ---------------------------------------------------------------------------


def test_yaml_parse_error_caught(tmp_path: pathlib.Path) -> None:
    """A file with invalid YAML produces a parse-error violation, exit 1."""
    dst = _copy_clean_run(tmp_path)
    bad = dst / "10-trustworthiness" / "broken.findings.yaml"
    bad.write_text("this is: not: valid: yaml: at: all:\n  - [\n")
    runner = CliRunner()
    result = runner.invoke(main, ["validate", str(dst)])
    assert result.exit_code == 1
    assert "parse error" in result.output.lower()


# ---------------------------------------------------------------------------
# cross-file: merged_from dangling ID
# ---------------------------------------------------------------------------


def test_dangling_merged_from_caught(tmp_path: pathlib.Path) -> None:
    """merged_from referencing an unknown ID is flagged by the cross-file pass."""
    dst = _copy_clean_run(tmp_path)
    f = dst / "10-trustworthiness" / "confidentiality.findings.yaml"
    text = f.read_text()
    text = text.replace("  evidence:", "  merged_from:\n    - conf-deadbeef\n  evidence:")
    f.write_text(text)
    runner = CliRunner()
    result = runner.invoke(main, ["validate", str(dst)])
    assert result.exit_code == 1
    assert "merged_from" in result.output.lower()


# ---------------------------------------------------------------------------
# cross-file: contradictions with dangling IDs
# ---------------------------------------------------------------------------


def test_contradictions_file_with_dangling_ids(tmp_path: pathlib.Path) -> None:
    """contradictions.yaml referencing unknown finding/capability IDs is flagged."""
    dst = _copy_clean_run(tmp_path)
    contradictions = dst / "40-synthesis" / "contradictions.yaml"
    contradictions.write_text(
        "contradictions:\n"
        "  - id: contra-deadbeef\n"
        "    finding_id: conf-deadbeef\n"
        "    capability_id: conf-cap-deadbeef\n"
        "    finding_assertion: \"Something asserted by a finding\"\n"
        "    capability_assertion: \"Something asserted by a capability\"\n"
        "    evidence_comparison: \"Comparison text that is long enough to satisfy minLength\"\n"
        "    recommended_resolution: \"Resolution text\"\n"
    )
    runner = CliRunner()
    result = runner.invoke(main, ["validate", str(dst)])
    assert result.exit_code == 1
    out = result.output.lower()
    assert "not found" in out
    assert "finding_id" in out or "capability_id" in out


# ---------------------------------------------------------------------------
# empty run directory
# ---------------------------------------------------------------------------


def test_empty_run_dir(tmp_path: pathlib.Path) -> None:
    """A run dir with no YAML files validates clean (zero records)."""
    empty = tmp_path / "empty"
    empty.mkdir()
    (empty / "00-context").mkdir()
    runner = CliRunner()
    result = runner.invoke(main, ["validate", str(empty)])
    assert result.exit_code == 0
    out = result.output.lower()
    assert "records: 0" in out or "0  records" in out or "records 0" in out


# ---------------------------------------------------------------------------
# JSON output flag
# ---------------------------------------------------------------------------


def test_validate_json_output(tmp_path: pathlib.Path) -> None:
    """--json flag emits valid JSON with errors/warnings/records/files keys."""
    dst = _copy_clean_run(tmp_path)
    runner = CliRunner()
    result = runner.invoke(main, ["validate", "--json", str(dst)])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert "errors" in data and "warnings" in data
    assert isinstance(data["errors"], list)
    assert isinstance(data["records"], int)


# ---------------------------------------------------------------------------
# --schema-only flag
# ---------------------------------------------------------------------------


def test_schema_only_flag(tmp_path: pathlib.Path) -> None:
    """--schema-only passes for a clean run."""
    dst = _copy_clean_run(tmp_path)
    runner = CliRunner()
    result = runner.invoke(main, ["validate", "--schema-only", str(dst)])
    assert result.exit_code == 0


# ---------------------------------------------------------------------------
# linters edge cases
# ---------------------------------------------------------------------------


def test_linters_check_finding_id_unknown_agent() -> None:
    """check_finding_id returns [] for an agent not in the prefix map."""
    from apd_gauntlet.linters import check_finding_id

    assert check_finding_id({"agent": "unknown_agent", "title": "x", "evidence": []}) == []


def test_linters_check_finding_id_no_evidence() -> None:
    """check_finding_id returns [] when evidence list is empty."""
    from apd_gauntlet.linters import check_finding_id

    assert check_finding_id({"agent": "confidentiality", "title": "x", "evidence": []}) == []


def test_linters_check_capability_id_no_evidence() -> None:
    """check_capability_id returns [] when evidence is missing or empty."""
    from apd_gauntlet.linters import check_capability_id

    assert check_capability_id({"agent": "confidentiality", "title": "x", "evidence": []}) == []
    assert check_capability_id({"agent": "confidentiality", "title": "x"}) == []


def test_linters_check_capability_maturity_evidence_designed_skipped() -> None:
    """Maturity below implemented is not checked — always returns []."""
    from apd_gauntlet.linters import check_capability_maturity_evidence

    rec = {"maturity": "designed", "evidence": [{"artifact": "tech_plan.md"}]}
    assert check_capability_maturity_evidence(rec, {"tech_plan.md"}) == []


def test_linters_check_capability_maturity_evidence_empty_tech_plan_set() -> None:
    """When the tech_plan set is empty the check is skipped (no context)."""
    from apd_gauntlet.linters import check_capability_maturity_evidence

    rec = {"maturity": "implemented", "evidence": [{"artifact": "tech_plan.md"}]}
    assert check_capability_maturity_evidence(rec, set()) == []


# ---------------------------------------------------------------------------
# cross-file: no artifacts in brief → evidence check skipped
# ---------------------------------------------------------------------------


def test_cross_file_no_brief_skips_artifact_check(tmp_path: pathlib.Path) -> None:
    """When there is no context-brief, known_artifacts is empty and evidence
    artifact references do not produce errors."""
    dst = _copy_clean_run(tmp_path)
    brief = dst / "00-context" / "context-brief.md"
    brief.unlink()
    runner = CliRunner()
    result = runner.invoke(main, ["validate", str(dst)])
    assert result.exit_code == 0


# ---------------------------------------------------------------------------
# Violation.render paths
# ---------------------------------------------------------------------------


def test_violation_render_with_path() -> None:
    """Violation.render includes record_id and path when present."""
    violation = v.Violation(
        file=pathlib.Path("some/file.yaml"),
        record_id="conf-abc",
        message="test message",
        path="evidence/0",
    )
    rendered = violation.render()
    assert "conf-abc" in rendered
    assert "evidence/0" in rendered
    assert "test message" in rendered


def test_violation_render_without_id_or_path() -> None:
    """Violation.render works when record_id and path are absent."""
    violation = v.Violation(
        file=pathlib.Path("some/file.yaml"),
        record_id=None,
        message="bare message",
    )
    rendered = violation.render()
    assert "bare message" in rendered
    assert "[" not in rendered


# ---------------------------------------------------------------------------
# ValidationReport.render
# ---------------------------------------------------------------------------


def test_validation_report_render_with_warnings() -> None:
    """render() includes WARNING lines when warnings are present."""
    report = v.ValidationReport()
    report.warnings.append(
        v.Violation(pathlib.Path("f.yaml"), "id-1", "something suspicious")
    )
    out = report.render()
    assert "WARNING" in out
    assert "something suspicious" in out


def test_validation_report_render_not_clean() -> None:
    """render() includes ERROR lines when errors are present, no 'Clean.' suffix."""
    report = v.ValidationReport()
    report.errors.append(v.Violation(pathlib.Path("f.yaml"), "id-1", "bad"))
    out = report.render()
    assert "ERROR" in out
    assert "Clean." not in out


# ---------------------------------------------------------------------------
# _iter_records: dict payload (not list)
# ---------------------------------------------------------------------------


def test_iter_records_dict_payload(tmp_path: pathlib.Path) -> None:
    """_iter_records yields a single record when the root key maps to a dict."""
    f = tmp_path / "single.findings.yaml"
    f.write_text(
        "finding:\n"
        "  schema_version: 1\n"
        "  id: conf-abc123\n"
        "  agent: confidentiality\n"
        "  title: test\n"
    )
    records = list(v._iter_records(tmp_path))
    assert len(records) == 1
    assert records[0][1] == "finding"
    assert records[0][2].get("id") == "conf-abc123"


# ---------------------------------------------------------------------------
# run_semantic_pass: capability branch
# ---------------------------------------------------------------------------


def test_run_semantic_pass_capability_branch(tmp_path: pathlib.Path) -> None:
    """run_semantic_pass processes capability records without errors on valid data."""
    dst = _copy_clean_run(tmp_path)
    report = v.run_semantic_pass(dst)
    assert report.is_clean


# ---------------------------------------------------------------------------
# Parametrize: known valid agents in check_finding_id
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "agent",
    [
        "confidentiality", "integrity", "availability", "distributed",
        "resilient", "ephemeral", "authenticity", "non_repudiation",
        "immutability", "synthesizer",
    ],
)
def test_check_finding_id_known_agents_with_no_evidence(agent: str) -> None:
    """All known agents with no evidence return [] (no crash)."""
    from apd_gauntlet.linters import check_finding_id

    assert check_finding_id({"agent": agent, "title": "t", "evidence": []}) == []


# ---------------------------------------------------------------------------
# linters: capability_id mismatch path
# ---------------------------------------------------------------------------


def test_linters_check_capability_id_mismatch() -> None:
    """check_capability_id returns error when actual id != computed id."""
    from apd_gauntlet.linters import check_capability_id

    rec = {
        "agent": "confidentiality",
        "title": "Some title",
        "id": "conf-cap-deadbeef",
        "evidence": [{"locator": "§1"}],
    }
    errors = check_capability_id(rec)
    assert len(errors) == 1
    assert "id mismatch" in errors[0]


def test_linters_check_capability_id_unknown_agent() -> None:
    """check_capability_id returns [] for an unknown agent."""
    from apd_gauntlet.linters import check_capability_id

    rec = {"agent": "unknown", "title": "x", "evidence": [{"locator": "a"}]}
    assert check_capability_id(rec) == []


# ---------------------------------------------------------------------------
# linters: maturity evidence path — positive error case
# ---------------------------------------------------------------------------


def test_linters_maturity_only_tech_plan_evidence_returns_error() -> None:
    """maturity=implemented with only tech_plan evidence returns an error message."""
    from apd_gauntlet.linters import check_capability_maturity_evidence

    rec = {
        "maturity": "implemented",
        "evidence": [{"artifact": "tech_plan.md"}],
    }
    errors = check_capability_maturity_evidence(rec, {"tech_plan.md"})
    assert len(errors) == 1
    assert "non-tech-plan evidence" in errors[0]


def test_linters_maturity_with_non_tech_plan_evidence_passes() -> None:
    """maturity=implemented with at least one non-tech_plan evidence returns []."""
    from apd_gauntlet.linters import check_capability_maturity_evidence

    rec = {
        "maturity": "implemented",
        "evidence": [
            {"artifact": "tech_plan.md"},
            {"artifact": "deployment_record.md"},
        ],
    }
    assert check_capability_maturity_evidence(rec, {"tech_plan.md"}) == []


# ---------------------------------------------------------------------------
# lint_agents: error paths
# ---------------------------------------------------------------------------


def test_lint_agent_no_frontmatter(tmp_path: pathlib.Path) -> None:
    """An agent file without frontmatter produces an error."""
    from apd_gauntlet.lint_agents import lint_agent_file

    agent = tmp_path / "agent.md"
    agent.write_text("# Just a body\n\nNo frontmatter.\n")
    errors = lint_agent_file(agent, tmp_path)
    assert errors
    assert "frontmatter" in errors[0].lower()


def test_lint_agent_invalid_yaml_frontmatter(tmp_path: pathlib.Path) -> None:
    """An agent file with invalid YAML in frontmatter produces a parse error."""
    from apd_gauntlet.lint_agents import lint_agent_file

    agent = tmp_path / "agent.md"
    agent.write_text("---\nname: [unclosed\n---\n\n# Body\n")
    errors = lint_agent_file(agent, tmp_path)
    assert errors
    assert "parse error" in errors[0].lower()


def test_lint_agent_frontmatter_not_mapping(tmp_path: pathlib.Path) -> None:
    """An agent file with non-mapping YAML frontmatter produces an error."""
    from apd_gauntlet.lint_agents import lint_agent_file

    agent = tmp_path / "agent.md"
    agent.write_text("---\n- item1\n- item2\n---\n\n# Body\n")
    errors = lint_agent_file(agent, tmp_path)
    assert errors
    assert "mapping" in errors[0].lower()


def test_lint_agent_missing_name_and_description(tmp_path: pathlib.Path) -> None:
    """An agent file missing both name and description produces two errors."""
    from apd_gauntlet.lint_agents import lint_agent_file

    agent = tmp_path / "agent.md"
    agent.write_text("---\nother_key: value\n---\n\n# Body\n")
    errors = lint_agent_file(agent, tmp_path)
    assert len(errors) == 2
    assert any("name" in e for e in errors)
    assert any("description" in e for e in errors)
