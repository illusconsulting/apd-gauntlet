"""Validator integration tests for code-evidence-index.yaml."""
from __future__ import annotations

import pathlib

from apd_gauntlet.validate import run_schema_pass, run_cross_file_pass

FIXTURES = pathlib.Path(__file__).resolve().parent / "fixtures"


def _make_run(tmp_path, include_index: bool, valid: bool = True):
    """Build a minimal run directory; optionally drop in a code-evidence-index."""
    (tmp_path / "00-context").mkdir(parents=True)
    (tmp_path / "00-context" / "context-brief.md").write_text(
        "---\n"
        "framework_version: 1.1.0\n"
        "run_id: t\n"
        "domain_pack: { name: pbm, version: 1.0.0 }\n"
        "artifacts:\n"
        "  - { filename: tech_plan.md, type: tech_plan }\n"
        "---\n"
        "# brief\n"
    )
    if include_index:
        src = "valid/code-evidence-index.yaml" if valid else "invalid/code-evidence-index-malformed.yaml"
        (tmp_path / "00-context" / "code-evidence-index.yaml").write_text(
            (FIXTURES / src).read_text()
        )
    return tmp_path


def test_schema_pass_flags_invalid_code_evidence_index(tmp_path):
    run_dir = _make_run(tmp_path, include_index=True, valid=False)
    report = run_schema_pass(run_dir)
    assert any("code-evidence-index" in str(v.file) for v in report.errors)


def test_schema_pass_accepts_valid_code_evidence_index(tmp_path):
    run_dir = _make_run(tmp_path, include_index=True, valid=True)
    report = run_schema_pass(run_dir)
    errors_for_index = [v for v in report.errors if "code-evidence-index" in str(v.file)]
    assert errors_for_index == []


def test_cross_file_pass_recognizes_index_as_known_artifact(tmp_path):
    run_dir = _make_run(tmp_path, include_index=True, valid=True)
    # Drop a finding that cites code-evidence-index.yaml as its artifact.
    (run_dir / "10-trustworthiness").mkdir()
    (run_dir / "10-trustworthiness" / "authenticity.findings.yaml").write_text(
        "finding:\n"
        "  - id: auth-deadbeef\n"
        "    agent: authenticity\n"
        "    title: JWT verifier is the sole identity boundary\n"
        "    apd_goal: authenticity\n"
        "    severity: medium\n"
        "    disposition: open\n"
        "    recommendation_posture: recommended\n"
        "    detail: '...'\n"
        "    evidence:\n"
        "      - artifact: code-evidence-index.yaml\n"
        "        locator: 'code:claim_bus.auth.jwt.JWTValidator.verify:L42-L51@a1b2c3d4'\n"
        "        excerpt: 'def verify(self, token: str) -> Claims: return self._decode(token, self.signing_keys)'\n"
        "    recommendation: '...'\n"
    )
    report = run_cross_file_pass(run_dir)
    # No 'artifact not in intake brief' error for code-evidence-index.yaml.
    artifact_errors = [v for v in report.errors if "code-evidence-index.yaml" in v.message and "not in intake brief" in v.message]
    assert artifact_errors == []


def test_cross_file_pass_without_index_does_not_grant_implicit_artifact(tmp_path):
    """If code-evidence-index.yaml is absent, citing it should still fail."""
    run_dir = _make_run(tmp_path, include_index=False)
    (run_dir / "10-trustworthiness").mkdir()
    (run_dir / "10-trustworthiness" / "authenticity.findings.yaml").write_text(
        "finding:\n"
        "  - id: auth-deadbeef\n"
        "    agent: authenticity\n"
        "    title: x\n"
        "    apd_goal: authenticity\n"
        "    severity: medium\n"
        "    disposition: open\n"
        "    recommendation_posture: recommended\n"
        "    detail: '...'\n"
        "    evidence:\n"
        "      - artifact: code-evidence-index.yaml\n"
        "        locator: x\n"
        "        excerpt: x\n"
        "    recommendation: '...'\n"
    )
    report = run_cross_file_pass(run_dir)
    assert any("code-evidence-index.yaml" in v.message and "not in intake brief" in v.message for v in report.errors)
