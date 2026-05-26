"""Pass-2 tests: semantic lints (excerpt length, id determinism, hedge words, maturity)."""
from __future__ import annotations

import pathlib
import shutil

from apd_gauntlet import validate as v
from apd_gauntlet.cli import main
from click.testing import CliRunner

FIXTURES = pathlib.Path(__file__).parent / "fixtures" / "runs"

_MITRE_SNIPPET = (
    'nist_800_53r5: ["SC-8(1)", "SC-13", "SC-28(1)"]\n    mitre_attack:\n'
    "      - technique: \"T1530\"\n        sub_technique: null\n"
    "        tactic: \"TA0010\"\n"
    "        rationale: \"Broker compromise could potentially enable"
    " data exfiltration in theory.\""
)


def _copy_clean_run(tmp_path):
    dst = tmp_path / "run"
    shutil.copytree(FIXTURES / "clean-run", dst)
    return dst


def test_long_excerpt_caught(tmp_path):
    dst = _copy_clean_run(tmp_path)
    f = dst / "10-trustworthiness" / "confidentiality.findings.yaml"
    text = f.read_text()
    # Replace the excerpt with 30 words.
    long_excerpt = " ".join(["word"] * 30)
    text = text.replace(
        "excerpt: \"All Kafka topics use AES-256 at-rest encryption via broker-managed keys\"",
        f"excerpt: \"{long_excerpt}\"",
    )
    f.write_text(text)
    runner = CliRunner()
    result = runner.invoke(main, ["validate", str(dst)])
    assert result.exit_code == 1
    assert "excerpt" in result.output.lower()
    assert "25" in result.output


def test_bad_id_caught(tmp_path):
    dst = _copy_clean_run(tmp_path)
    f = dst / "10-trustworthiness" / "confidentiality.findings.yaml"
    text = f.read_text()
    # Change the title so the recomputed id no longer matches.
    text = text.replace(
        'title: "PHI fields in Kafka claim-events topic lack envelope encryption"',
        'title: "Something completely different that changes the hash"',
    )
    f.write_text(text)
    runner = CliRunner()
    result = runner.invoke(main, ["validate", str(dst)])
    assert result.exit_code == 1
    assert "id mismatch" in result.output.lower()


def test_hedge_word_warned(tmp_path):
    dst = _copy_clean_run(tmp_path)
    # Add a mitre_attack entry with a hedge word.
    f = dst / "10-trustworthiness" / "confidentiality.findings.yaml"
    text = f.read_text()
    # Append a mitre_attack entry under control_mappings.
    text = text.replace('nist_800_53r5: ["SC-8(1)", "SC-13", "SC-28(1)"]', _MITRE_SNIPPET)
    f.write_text(text)
    runner = CliRunner()
    # Default: hedge words are warnings, not errors → exit 0.
    result = runner.invoke(main, ["validate", str(dst)])
    assert result.exit_code == 0
    assert "warning" in result.output.lower()
    out = result.output.lower()
    assert "hedge" in out or "could" in out or "potentially" in out


def test_strict_promotes_hedge_warning_to_error(tmp_path):
    dst = _copy_clean_run(tmp_path)
    f = dst / "10-trustworthiness" / "confidentiality.findings.yaml"
    text = f.read_text()
    text = text.replace('nist_800_53r5: ["SC-8(1)", "SC-13", "SC-28(1)"]', _MITRE_SNIPPET)
    f.write_text(text)
    runner = CliRunner()
    result = runner.invoke(main, ["validate", "--strict", str(dst)])
    assert result.exit_code == 1


def test_capability_maturity_implemented_requires_non_tech_plan_evidence(tmp_path):
    """maturity=implemented with only tech_plan evidence — Pass 2 flags it."""
    dst = _copy_clean_run(tmp_path)
    f = dst / "10-trustworthiness" / "confidentiality.capabilities.yaml"
    text = f.read_text()
    text = text.replace("maturity: designed", "maturity: implemented")
    f.write_text(text)
    runner = CliRunner()
    # Pass 2 alone doesn't have tech_plan_artifacts set, so this won't fire until Pass 3.
    # Run --schema-only to confirm Pass 1 alone doesn't catch it;
    # Pass 3 is tested in test_validate_cross_file.py.
    result = runner.invoke(main, ["validate", "--schema-only", str(dst)])
    assert result.exit_code == 0  # schema allows maturity=implemented at the schema level


# ----------------------------------------------------------------------------
# Task 17: D3FEND counters_attack ⊆ capability's mitre_attack cross-reference.
# ----------------------------------------------------------------------------

# A control_mappings block with d3fend whose counters_attack does NOT intersect
# the (also-provided) mitre_attack[].technique list. The clean-run capability
# starts with only `nist_800_53r5`; we replace that line with this block.
_D3FEND_MISMATCH_BLOCK = (
    'nist_800_53r5: ["SC-12", "SC-12(1)", "SC-13", "SC-28", "SC-28(1)"]\n'
    "    mitre_attack:\n"
    "      - technique: T1078\n"
    "        tactic: TA0001\n"
    "        rationale: \"Capability defends against valid-account abuse"
    " via field-level encryption boundary.\"\n"
    "    d3fend:\n"
    "      - technique: D3-NTA\n"
    "        counters_attack: [\"T9999\"]\n"
    "        rationale: \"Network traffic analysis with mTLS-enforced"
    " identity detects unauthorized traversal.\""
)

# Same shape but counters_attack overlaps mitre_attack exactly.
_D3FEND_EXACT_MATCH_BLOCK = (
    'nist_800_53r5: ["SC-12", "SC-12(1)", "SC-13", "SC-28", "SC-28(1)"]\n'
    "    mitre_attack:\n"
    "      - technique: T1078\n"
    "        tactic: TA0001\n"
    "        rationale: \"Capability defends against valid-account abuse"
    " via field-level encryption boundary.\"\n"
    "    d3fend:\n"
    "      - technique: D3-NTA\n"
    "        counters_attack: [\"T1078\"]\n"
    "        rationale: \"Network traffic analysis with mTLS-enforced"
    " identity detects unauthorized traversal.\""
)

# counters_attack is a sub-technique whose parent appears in mitre_attack[].technique.
_D3FEND_SUBTECH_PARENT_BLOCK = (
    'nist_800_53r5: ["SC-12", "SC-12(1)", "SC-13", "SC-28", "SC-28(1)"]\n'
    "    mitre_attack:\n"
    "      - technique: T1110\n"
    "        tactic: TA0006\n"
    "        rationale: \"Capability defends against brute-force credential"
    " attacks via rate limiting and MFA on the IAM boundary.\"\n"
    "    d3fend:\n"
    "      - technique: D3-MFA\n"
    "        counters_attack: [\"T1110.001\"]\n"
    "        rationale: \"Multi-factor authentication blocks password"
    " guessing variants of brute-force credential attacks.\""
)


def _mutate_capability_controls(run_dir, replacement_block: str) -> None:
    """Replace the clean-run capability's `nist_800_53r5: [...]` line with the
    supplied control_mappings block."""
    f = run_dir / "10-trustworthiness" / "confidentiality.capabilities.yaml"
    text = f.read_text()
    text = text.replace(
        'nist_800_53r5: ["SC-12", "SC-12(1)", "SC-13", "SC-28", "SC-28(1)"]',
        replacement_block,
    )
    f.write_text(text)


def test_validate_rejects_d3fend_counters_attack_not_in_mitre_attack(tmp_path):
    """D3FEND counters_attack must intersect the capability's mitre_attack."""
    dst = _copy_clean_run(tmp_path)
    _mutate_capability_controls(dst, _D3FEND_MISMATCH_BLOCK)
    runner = CliRunner()
    result = runner.invoke(main, ["validate", str(dst)])
    assert result.exit_code == 1, result.output
    out = result.output.lower()
    assert "counters_attack" in out
    assert "t9999" in out


def test_validate_accepts_d3fend_counters_attack_intersects_mitre_attack(tmp_path):
    """Cross-reference satisfied when there's at least one exact overlap."""
    dst = _copy_clean_run(tmp_path)
    _mutate_capability_controls(dst, _D3FEND_EXACT_MATCH_BLOCK)
    runner = CliRunner()
    result = runner.invoke(main, ["validate", str(dst)])
    # No counters_attack errors should be raised by the cross-reference check.
    assert "counters_attack" not in result.output.lower(), result.output
    # And the run as a whole should be clean (other lints unaffected).
    assert result.exit_code == 0, result.output


def test_validate_accepts_d3fend_subtechnique_when_parent_in_mitre_attack(tmp_path):
    """Sub-technique counters_attack (T1110.001) satisfied by parent T1110 in mitre_attack."""
    dst = _copy_clean_run(tmp_path)
    _mutate_capability_controls(dst, _D3FEND_SUBTECH_PARENT_BLOCK)
    runner = CliRunner()
    result = runner.invoke(main, ["validate", str(dst)])
    assert "counters_attack" not in result.output.lower(), result.output
    assert result.exit_code == 0, result.output


# ----------------------------------------------------------------------------
# Task B-25: tmeval- evidence-pointer + contradiction cross-reference checks.
# ----------------------------------------------------------------------------

# Valid tmeval- finding: cites the normalized TM artifact, disposition gap.
_TMEVAL_VALID_FULL = (
    "finding:\n"
    "  schema_version: 1\n"
    "  id: tmeval-a1b2c3d4\n"
    "  agent: threat_model_evaluator\n"
    "  apd_tier: trustworthiness\n"
    "  apd_goal: confidentiality\n"
    "  disposition: gap\n"
    "  severity: medium\n"
    "  confidence: high\n"
    '  title: "TM omits Repudiation analysis for audit-log-writer service"\n'
    '  summary: "No Repudiation entries for audit-log-writer in normalized TM."\n'
    "  detail: \"Per STRIDE, Repudiation threats must be evaluated for every"
    " audit-writing service. The audit-log-writer is absent from the TM's"
    " Repudiation category.\"\n"
    "  evidence:\n"
    '    - artifact: "00-context/threat-model-normalized.yaml"\n'
    '      locator: "entries[entry_id=tm-a1b2c3d4]"\n'
    '      excerpt: "audit-log-writer has no repudiation entries"\n'
    "  control_mappings:\n"
    '    nist_800_53r5: ["AU-9"]\n'
    "  recommendation:\n"
    "    posture: recommended\n"
    '    summary: "Add Repudiation entries for audit-log-writer to TM."\n'
    '    detail: "Enumerate Repudiation threats for audit-log-writer covering'
    " log tampering scenarios, then re-evaluate non-repudiation controls.\"\n"
)

# tmeval- finding whose evidence points at a code file — not the TM.
_TMEVAL_MISSING_TM_EVIDENCE = (
    "finding:\n"
    "  schema_version: 1\n"
    "  id: tmeval-b2c3d4e5\n"
    "  agent: threat_model_evaluator\n"
    "  apd_tier: trustworthiness\n"
    "  apd_goal: confidentiality\n"
    "  disposition: gap\n"
    "  severity: medium\n"
    "  confidence: high\n"
    '  title: "TM missing Spoofing coverage for claim-event-bus"\n'
    '  summary: "No Spoofing entries for claim-event-bus in the threat model."\n'
    '  detail: "The threat model has no Spoofing entries for claim-event-bus.'
    " This coverage gap must be addressed before production deployment.\"\n"
    "  evidence:\n"
    '    - artifact: "src/main.py"\n'
    '      locator: "line 42"\n'
    '      excerpt: "producer sends unauthenticated claim events to bus"\n'
    "  control_mappings:\n"
    '    nist_800_53r5: ["AU-9"]\n'
    "  recommendation:\n"
    "    posture: recommended\n"
    '    summary: "Add Spoofing entries for claim-event-bus to the TM."\n'
    '    detail: "Model spoofing scenarios for claim-event-bus covering identity'
    " and message-origin spoofing vectors on both producer and consumer sides.\"\n"
)

# tmeval- contradiction (disposition: risk) with an empty cross_references list.
_TMEVAL_CONTRADICTION_WITHOUT_CROSS_REF = (
    "finding:\n"
    "  schema_version: 1\n"
    "  id: tmeval-c3d4e5f6\n"
    "  agent: threat_model_evaluator\n"
    "  apd_tier: trustworthiness\n"
    "  apd_goal: confidentiality\n"
    "  disposition: risk\n"
    "  severity: high\n"
    "  confidence: high\n"
    '  title: "TM claims mTLS but specialist finding shows bearer tokens"\n'
    '  summary: "TM marks broker link as mTLS; conf- finding shows bearer tokens."\n'
    '  detail: "The normalized TM records the adjudication->pricing link as'
    " mitigated via mTLS. The confidentiality specialist finding shows bearer"
    " tokens are used instead, directly contradicting the TM mitigation claim.\"\n"
    "  evidence:\n"
    '    - artifact: "00-context/threat-model-normalized.yaml"\n'
    '      locator: "entries[entry_id=tm-c3d4e5f6]"\n'
    '      excerpt: "adjudication->pricing marked mitigated: mTLS enforced"\n'
    "  control_mappings:\n"
    '    nist_800_53r5: ["SC-8"]\n'
    "  cross_references: []\n"
    "  recommendation:\n"
    "    posture: required\n"
    '    summary: "Update TM to reflect actual bearer-token auth on this link."\n'
    '    detail: "Correct the TM entry for adjudication->pricing to reflect the'
    " bearer-token auth mechanism and schedule mTLS remediation.\"\n"
)

# tmeval- contradiction with a populated cross_references — should pass.
_TMEVAL_CONTRADICTION_WITH_CROSS_REF = (
    "finding:\n"
    "  schema_version: 1\n"
    "  id: tmeval-d4e5f6a7\n"
    "  agent: threat_model_evaluator\n"
    "  apd_tier: trustworthiness\n"
    "  apd_goal: confidentiality\n"
    "  disposition: risk\n"
    "  severity: high\n"
    "  confidence: high\n"
    '  title: "TM claims field-level encryption but PHI is in plaintext"\n'
    '  summary: "TM marks PHI fields encrypted; conf- finding shows plaintext."\n'
    '  detail: "The normalized TM records the Kafka claim-events topic as'
    " field-level encrypted. The confidentiality specialist finding shows only"
    " broker-level encryption, leaving PHI in plaintext between endpoints.\"\n"
    "  evidence:\n"
    '    - artifact: "00-context/threat-model-normalized.yaml"\n'
    '      locator: "entries[entry_id=tm-d4e5f6a7]"\n'
    '      excerpt: "claim-events marked mitigated: field-level AES-256"\n'
    "  control_mappings:\n"
    '    nist_800_53r5: ["SC-8"]\n'
    '  cross_references: ["conf-7aa376c5"]\n'
    "  recommendation:\n"
    "    posture: required\n"
    '    summary: "Update TM to reflect broker-level-only encryption."\n'
    '    detail: "Correct the TM entry for claim-events Kafka topic to reflect'
    " broker-level-only encryption and schedule field-level encryption work.\"\n"
)

# A normal conf- finding without TM evidence (should NOT trigger tmeval checks).
_CONF_FINDING_NO_TM_EVIDENCE = (
    "finding:\n"
    "  schema_version: 1\n"
    "  id: conf-a1b2c3d4\n"
    "  agent: confidentiality\n"
    "  apd_tier: trustworthiness\n"
    "  apd_goal: confidentiality\n"
    "  disposition: gap\n"
    "  severity: medium\n"
    "  confidence: high\n"
    '  title: "Kafka topic lacks field-level envelope encryption for PHI"\n'
    '  summary: "Broker-level encryption only; PHI fields travel in plaintext."\n'
    '  detail: "Per the impact-to-PBM rubric, PHI exposure beyond the'
    " minimum-necessary internal audience is a high-severity confidentiality"
    " gap. The broker-level key is accessible to all operators.\"\n"
    "  evidence:\n"
    '    - artifact: "tech_plan.md"\n'
    '      locator: "section 4.2 paragraph 3"\n'
    '      excerpt: "All Kafka topics use AES-256 at-rest encryption"\n'
    "  control_mappings:\n"
    '    nist_800_53r5: ["SC-8"]\n'
    "  recommendation:\n"
    "    posture: recommended\n"
    '    summary: "Apply field-level encryption before serialization."\n'
    '    detail: "Replace broker-level encryption with envelope encryption in'
    " the producer SDK using DEKs issued by the existing KMS hierarchy.\"\n"
)


def _write_finding(path: pathlib.Path, yaml_text: str) -> None:
    """Write a YAML finding file, creating parent directories as needed.

    ``yaml_text`` must be a complete YAML document (including the ``finding:``
    wrapper key) — this helper just ensures the directory exists and writes it.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml_text)


def run_validation(run_dir: pathlib.Path) -> v.ValidationReport:
    """Run Pass 2 (semantic lints) against *run_dir* and return the report."""
    return v.run_semantic_pass(run_dir)


def test_tmeval_finding_with_tm_evidence_passes(tmp_path):
    """A valid tmeval- finding pointing at the normalized TM should not trigger evidence checks."""
    _write_finding(
        tmp_path / "20-findings" / "40-threat-model" / "tmeval-a1b2c3d4.findings.yaml",
        _TMEVAL_VALID_FULL,
    )
    result = run_validation(tmp_path)
    assert not any("missing tm evidence" in v_item.message.lower() for v_item in result.errors)


def test_tmeval_finding_without_tm_evidence_fails(tmp_path):
    """A tmeval- finding whose evidence points at a code file must be flagged."""
    _write_finding(
        tmp_path / "20-findings" / "40-threat-model" / "tmeval-b2c3d4e5.findings.yaml",
        _TMEVAL_MISSING_TM_EVIDENCE,
    )
    result = run_validation(tmp_path)
    assert any(
        "evidence" in v_item.message.lower() and "threat-model" in v_item.message.lower()
        for v_item in result.errors
    )


def test_tmeval_contradiction_without_cross_reference_fails(tmp_path):
    """A tmeval- contradiction (disposition: risk) with empty cross_references must be flagged."""
    _write_finding(
        tmp_path / "20-findings" / "40-threat-model" / "tmeval-c3d4e5f6.findings.yaml",
        _TMEVAL_CONTRADICTION_WITHOUT_CROSS_REF,
    )
    result = run_validation(tmp_path)
    assert any(
        "contradiction" in v_item.message.lower() and "cross_references" in v_item.message
        for v_item in result.errors
    )


def test_tmeval_contradiction_with_cross_reference_passes(tmp_path):
    """A tmeval- contradiction with a populated cross_references list should pass."""
    _write_finding(
        tmp_path / "20-findings" / "40-threat-model" / "tmeval-d4e5f6a7.findings.yaml",
        _TMEVAL_CONTRADICTION_WITH_CROSS_REF,
    )
    result = run_validation(tmp_path)
    assert not any("cross_references" in v_item.message.lower() for v_item in result.errors)


def test_non_tmeval_findings_not_subject_to_tmeval_checks(tmp_path):
    """A regular conf- finding without TM evidence should NOT trigger the tmeval checks."""
    _write_finding(
        tmp_path / "10-trustworthiness" / "conf-a1b2c3d4.findings.yaml",
        _CONF_FINDING_NO_TM_EVIDENCE,
    )
    result = run_validation(tmp_path)
    assert not any("missing tm evidence" in v_item.message.lower() for v_item in result.errors)
