"""Validator tests for the report-data.yaml file under 40-synthesis/."""
from __future__ import annotations

import pathlib

import pytest
import yaml

from apd_gauntlet.validate import run_cross_file_pass, run_schema_pass


@pytest.fixture
def minimal_run(tmp_path: pathlib.Path) -> pathlib.Path:
    """Build a minimal run dir with one finding, one capability, and report-data.yaml."""
    run = tmp_path / "run"
    (run / "40-synthesis").mkdir(parents=True)
    findings_doc = {
        "schema_version": 1,
        "finding": [{
            "schema_version": 1,
            "id": "conf-12345678",
            "agent": "confidentiality",
            "apd_tier": "trustworthiness",
            "apd_goal": "confidentiality",
            "disposition": "gap",
            "severity": "high",
            "confidence": "high",
            "title": "A confidentiality finding for testing purposes only",
            "summary": "Summary text long enough to satisfy minLength.",
            "detail": "Detail text long enough to satisfy the minLength constraint.",
            "evidence": [{"artifact": "x.md", "locator": "L1", "excerpt": "ex"}],
            "control_mappings": {"nist_800_53r5": ["SC-8"]},
            "recommendation": {
                "posture": "required",
                "summary": "Remediate this finding promptly.",
                "detail": "Implement the recommended control to address this gap.",
            },
        }],
    }
    capabilities_doc = {
        "schema_version": 1,
        "capability": [{
            "schema_version": 1,
            "id": "conf-cap-abcd1234",
            "agent": "confidentiality",
            "apd_tier": "trustworthiness",
            "apd_goal": "confidentiality",
            "maturity": "implemented",
            "title": "A capability for testing purposes",
            "description": "This capability demonstrates encryption in transit for all API endpoints.",
            "scope": "Scope text long enough to satisfy the minLength constraint.",
            "evidence": [{"artifact": "x.md", "locator": "L1", "excerpt": "ex"}],
            "control_mappings": {"nist_800_53r5": ["SC-8"]},
        }],
    }
    (run / "10-trustworthiness").mkdir()
    (run / "10-trustworthiness" / "confidentiality.findings.yaml").write_text(
        yaml.safe_dump(findings_doc)
    )
    (run / "10-trustworthiness" / "confidentiality.capabilities.yaml").write_text(
        yaml.safe_dump(capabilities_doc)
    )
    return run


def test_report_data_valid_schema(minimal_run: pathlib.Path) -> None:
    """A schema-valid report-data.yaml passes the schema pass."""
    doc = {
        "schema_version": 1,
        "exec_summary": {"paragraphs": ["A paragraph long enough for the minLength rule to accept."]},
        "headline_findings": [{"id": "conf-12345678", "rank": 1}],
        "strengths": [{"id": "conf-cap-abcd1234", "caveats": ["A caveat long enough."]}],
        "next_steps": [{"rank": 1, "text": "Do the thing now.", "refs": ["conf-12345678"]}],
        "posture_summary": {
            "trustworthiness": "Trust posture statement.",
            "scalability":     "Scale posture statement.",
            "auditability":    "Audit posture statement.",
        },
    }
    (minimal_run / "40-synthesis" / "report-data.yaml").write_text(yaml.safe_dump(doc))
    rep = run_schema_pass(minimal_run)
    assert rep.is_clean, rep.render()


def test_report_data_unknown_finding_ref_fails_cross_file(minimal_run: pathlib.Path) -> None:
    """A headline_findings entry pointing at a non-existent finding fails cross-file."""
    doc = {
        "schema_version": 1,
        "exec_summary": {"paragraphs": ["A paragraph long enough for the minLength rule to accept."]},
        "headline_findings": [{"id": "conf-00000000", "rank": 1}],
        "strengths": [{"id": "conf-cap-abcd1234", "caveats": ["A caveat long enough."]}],
        "next_steps": [{"rank": 1, "text": "Do the thing now.", "refs": ["conf-12345678"]}],
        "posture_summary": {
            "trustworthiness": "Trust posture statement.",
            "scalability":     "Scale posture statement.",
            "auditability":    "Audit posture statement.",
        },
    }
    (minimal_run / "40-synthesis" / "report-data.yaml").write_text(yaml.safe_dump(doc))
    rep = run_cross_file_pass(minimal_run)
    assert not rep.is_clean
    assert any("conf-00000000" in v.message for v in rep.errors)


def test_report_data_unknown_strength_ref_fails_cross_file(minimal_run: pathlib.Path) -> None:
    """A strengths entry pointing at a non-existent capability fails cross-file."""
    doc = {
        "schema_version": 1,
        "exec_summary": {"paragraphs": ["A paragraph long enough for the minLength rule to accept."]},
        "headline_findings": [{"id": "conf-12345678", "rank": 1}],
        "strengths": [{"id": "conf-cap-zzzzzzzz", "caveats": ["A caveat long enough."]}],
        "next_steps": [{"rank": 1, "text": "Do the thing now.", "refs": ["conf-12345678"]}],
        "posture_summary": {
            "trustworthiness": "Trust posture statement.",
            "scalability":     "Scale posture statement.",
            "auditability":    "Audit posture statement.",
        },
    }
    (minimal_run / "40-synthesis" / "report-data.yaml").write_text(yaml.safe_dump(doc))
    rep = run_cross_file_pass(minimal_run)
    assert not rep.is_clean
    assert any("conf-cap-zzzzzzzz" in v.message for v in rep.errors)


def test_report_data_absent_is_silent(minimal_run: pathlib.Path) -> None:
    """No report-data.yaml means nothing to validate; runs stay clean."""
    rep_schema = run_schema_pass(minimal_run)
    rep_cross = run_cross_file_pass(minimal_run)
    assert rep_schema.is_clean and rep_cross.is_clean


def test_report_data_unknown_next_steps_ref_fails_cross_file(minimal_run: pathlib.Path) -> None:
    """A next_steps refs entry pointing at neither a finding nor a capability fails cross-file."""
    doc = {
        "schema_version": 1,
        "exec_summary": {"paragraphs": ["A paragraph long enough for the minLength rule to accept."]},
        "headline_findings": [{"id": "conf-12345678", "rank": 1}],
        "strengths": [{"id": "conf-cap-abcd1234", "caveats": ["A caveat long enough."]}],
        "next_steps": [{"rank": 1, "text": "Do the thing now.", "refs": ["nonexistent-00000000"]}],
        "posture_summary": {
            "trustworthiness": "Trust posture statement.",
            "scalability":     "Scale posture statement.",
            "auditability":    "Audit posture statement.",
        },
    }
    (minimal_run / "40-synthesis" / "report-data.yaml").write_text(yaml.safe_dump(doc))
    rep = run_cross_file_pass(minimal_run)
    assert not rep.is_clean
    assert any("nonexistent-00000000" in v.message for v in rep.errors)
