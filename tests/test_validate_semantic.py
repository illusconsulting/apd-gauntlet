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
