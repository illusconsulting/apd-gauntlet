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
            "description": (
                "This capability demonstrates encryption in transit for all API endpoints."
            ),
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
        "exec_summary": {
            "paragraphs": ["A paragraph long enough for the minLength rule to accept."]
        },
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
        "exec_summary": {
            "paragraphs": ["A paragraph long enough for the minLength rule to accept."]
        },
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
        "exec_summary": {
            "paragraphs": ["A paragraph long enough for the minLength rule to accept."]
        },
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
        "exec_summary": {
            "paragraphs": ["A paragraph long enough for the minLength rule to accept."]
        },
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


# ---------------------------------------------------------------------------
# Regression tests for F4: deduped-findings.yaml union in cross-ref resolver
# ---------------------------------------------------------------------------

def _write_deduped_run(tmp_path: pathlib.Path, headline_id: str) -> pathlib.Path:
    """Build a minimal run dir whose only finding lives in deduped-findings.yaml.

    The file is under 40-synthesis/ and its name does NOT match *.findings.yaml,
    so _iter_records never sees it.  Before the F4 fix the cross-ref check would
    raise 'unknown finding'; after the fix it must resolve clean.
    """
    run = tmp_path / "run"
    synth = run / "40-synthesis"
    synth.mkdir(parents=True)
    # A merged finding minted by apply.py — lives ONLY in the deduped corpus.
    deduped_finding = {
        "schema_version": 1,
        "id": "merged-abcd1234",
        "agent": "synthesizer",
        "apd_tier": "trustworthiness",
        "apd_goal": "confidentiality",
        "disposition": "gap",
        "severity": "high",
        "confidence": "high",
        "title": "Merged PHI exposure cluster",
        "summary": "Summary text long enough to satisfy minLength.",
        "detail": "Detail text long enough to satisfy the minLength constraint.",
        "evidence": [{"artifact": "tech_plan.md", "locator": "§1", "excerpt": "q"}],
        "recommendation": {"posture": "required", "summary": "Remediate this finding promptly.",
                           "detail": "Implement the recommended control to address this gap."},
    }
    (synth / "deduped-findings.yaml").write_text(
        yaml.safe_dump({"finding": [deduped_finding]}, sort_keys=False),
        encoding="utf-8",
    )
    report_data = {
        "schema_version": 1,
        "headline_findings": [{"id": headline_id, "rank": 1}],
    }
    (synth / "report-data.yaml").write_text(
        yaml.safe_dump(report_data, sort_keys=False),
        encoding="utf-8",
    )
    return run


def test_report_data_resolves_merged_id_from_deduped_corpus(tmp_path: pathlib.Path) -> None:
    """F4 regression: a merged-* id present in deduped-findings.yaml resolves clean.

    Before the fix, _validate_report_data_cross_refs built its known-id set only
    from _iter_records (which skips deduped-findings.yaml), so a headline pointing
    at a merged-* id always failed with 'unknown finding'.
    """
    run = _write_deduped_run(tmp_path, headline_id="merged-abcd1234")
    rep = run_cross_file_pass(run)
    # The right invariant: the minimal fixture must validate fully clean.
    assert rep.is_clean, rep.render()
    # Also assert specifically that no 'unknown finding' error exists (documents intent).
    assert not any("unknown finding" in v.message for v in rep.errors), (
        "F4 regression: merged-* id not resolved from deduped corpus.\n"
        + rep.render()
    )


def test_report_data_unknown_id_still_errors(tmp_path: pathlib.Path) -> None:
    """F4 regression: a headline id absent from ALL sources still produces an error.

    Ensures the deduped-union path does not accidentally suppress real errors.
    """
    run = _write_deduped_run(tmp_path, headline_id="merged-deadbeef")
    rep = run_cross_file_pass(run)
    assert not rep.is_clean, (
        "Expected a cross-ref error for unknown id 'merged-deadbeef', but none was raised."
    )
    assert any("merged-deadbeef" in v.message for v in rep.errors), rep.render()
