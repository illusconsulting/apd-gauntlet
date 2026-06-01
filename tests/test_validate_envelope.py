"""C2 / F1: validate is non-vacuous AND rejects non-canonical envelopes."""
from __future__ import annotations

import pathlib

import yaml
from apd_gauntlet.cli import main
from apd_gauntlet.linters import compute_capability_id, compute_id
from click.testing import CliRunner


def _write(path: pathlib.Path, doc) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(doc, sort_keys=False), encoding="utf-8")


def _bad_excerpt_record():
    # excerpt > 25 tokens -> a per-record semantic error the lint MUST catch
    return {
        "schema_version": 1,
        "id": "conf-00000000",
        "agent": "confidentiality",
        "apd_tier": "trustworthiness",
        "apd_goal": "confidentiality",
        "disposition": "gap",
        "severity": "high",
        "confidence": "high",
        "title": "t",
        "summary": "s",
        "detail": "d",
        "evidence": [{"artifact": "tech_plan.md", "locator": "§1",
                      "excerpt": "word " * 40}],
        "recommendation": {"posture": "required", "summary": "s", "detail": "d"},
    }


def test_plural_root_is_non_vacuously_validated(tmp_path):
    # Under the OLD bug this exited 0 (zero records matched). Now the per-record
    # excerpt lint fires AND the envelope error fires.
    run = tmp_path / "run"
    _write(run / "10-trustworthiness" / "confidentiality.findings.yaml",
           {"findings": [_bad_excerpt_record()]})
    result = CliRunner().invoke(main, ["validate", str(run), "--tier",
                                       "10-trustworthiness"])
    assert result.exit_code != 0, result.output


def test_plural_root_emits_envelope_error(tmp_path):
    run = tmp_path / "run"
    _write(run / "10-trustworthiness" / "confidentiality.findings.yaml",
           {"findings": [_bad_excerpt_record()]})
    result = CliRunner().invoke(main, ["validate", str(run), "--tier",
                                       "10-trustworthiness"])
    assert "non-canonical envelope" in result.output, result.output


def test_wrapped_record_emits_envelope_error(tmp_path):
    run = tmp_path / "run"
    _write(run / "10-trustworthiness" / "confidentiality.findings.yaml",
           {"finding": [{"finding": _bad_excerpt_record()}]})
    result = CliRunner().invoke(main, ["validate", str(run), "--tier",
                                       "10-trustworthiness"])
    assert "non-canonical envelope" in result.output, result.output


def test_canonical_singular_input_has_no_envelope_error(tmp_path):
    run = tmp_path / "run"
    good = _bad_excerpt_record()
    good["evidence"][0]["excerpt"] = "short quote"  # within limit
    # id must match the deterministic rule so check_finding_id passes
    good["id"] = compute_id("conf", good["title"], good["evidence"][0]["locator"])
    _write(run / "10-trustworthiness" / "confidentiality.findings.yaml",
           {"finding": [good]})
    result = CliRunner().invoke(main, ["validate", str(run), "--tier",
                                       "10-trustworthiness"])
    assert "non-canonical envelope" not in result.output, result.output


def _valid_cap(title: str = "Confidentiality capability title long", locator: str = "§1"):
    """Return a schema-plausible capability record dict."""
    return {
        "schema_version": 1,
        "id": compute_capability_id("conf", title, locator),
        "agent": "confidentiality",
        "apd_tier": "trustworthiness",
        "apd_goal": "confidentiality",
        "maturity": "designed",
        "title": title,
        "description": "Describes how confidentiality is protected in this system.",
        "scope": "Applies to all data-at-rest and data-in-transit paths.",
        "evidence": [{"artifact": "tech_plan.md", "locator": locator, "excerpt": "short quote"}],
        "control_mappings": {"nist_800_53r5": ["SC-8"]},
    }


def test_plural_capability_root_emits_envelope_error(tmp_path):
    """A real 'capabilities:' plural root key must be flagged as non-canonical."""
    run = tmp_path / "run"
    _write(run / "10-trustworthiness" / "confidentiality.capabilities.yaml",
           {"capabilities": [_valid_cap()]})  # REAL plural root key
    result = CliRunner().invoke(main, ["validate", str(run), "--tier",
                                       "10-trustworthiness"])
    assert "non-canonical envelope" in result.output, result.output


def test_plural_capability_root_is_non_vacuously_validated(tmp_path):
    """A plural-root capabilities file with a wrong id must trigger the
    capability id-mismatch lint, proving extract_records reaches the records."""
    run = tmp_path / "run"
    cap = _valid_cap()
    cap["id"] = "conf-cap-deadbeef"  # wrong deterministic id
    _write(run / "10-trustworthiness" / "confidentiality.capabilities.yaml",
           {"capabilities": [cap]})
    result = CliRunner().invoke(main, ["validate", str(run), "--tier", "10-trustworthiness"])
    assert result.exit_code != 0, result.output
    assert "id mismatch" in result.output, result.output


def test_wrapped_capability_emits_envelope_error(tmp_path):
    """Exercises the *.capabilities.yaml branch of _check_envelopes via the
    per-record wrapper path."""
    run = tmp_path / "run"
    cap = _valid_cap()
    _write(run / "10-trustworthiness" / "confidentiality.capabilities.yaml",
           {"capability": [{"capability": cap}]})  # per-record wrapper
    result = CliRunner().invoke(main, ["validate", str(run), "--tier",
                                       "10-trustworthiness"])
    assert "non-canonical envelope" in result.output, result.output
