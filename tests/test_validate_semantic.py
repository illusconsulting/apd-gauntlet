"""Pass-2 tests: semantic lints (excerpt length, id determinism, hedge words, maturity)."""
from __future__ import annotations

import pathlib
import shutil

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
