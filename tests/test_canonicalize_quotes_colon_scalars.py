"""G5 — regression coverage for the safe-YAML-emit guardrail (no behavior change).

canonicalize emits via ``yaml.safe_dump`` which quotes colon-space and special
scalars correctly. These tests pin that round-trip and confirm a malformed-YAML
file is SKIPPED (not aborting the pass) and surfaced in ``parse_errors``.
"""
from __future__ import annotations

import pathlib

import yaml
from apd_gauntlet.canonicalize import canonicalize_run


def _write(path: pathlib.Path, doc) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(doc, sort_keys=False), encoding="utf-8")


def test_colon_space_and_em_dash_scalars_round_trip(tmp_path):
    run = tmp_path / "run"
    path = run / "10-trustworthiness" / "confidentiality.findings.yaml"
    tricky_title = "Auth bypass: token reuse — replay window"
    tricky_excerpt = "config: enabled — see note"
    _write(path, {"finding": [{
        "id": "fabricated-00000000",
        "agent": "confidentiality",
        "title": tricky_title,
        "evidence": [{"artifact": "tech_plan.md", "locator": "§4.2", "excerpt": tricky_excerpt}],
    }]})
    canonicalize_run(run)
    # The rewritten file must be valid YAML that round-trips the EXACT values.
    doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    rec = doc["finding"][0]
    assert rec["title"] == tricky_title
    assert rec["evidence"][0]["excerpt"] == tricky_excerpt


def test_malformed_yaml_file_skipped_and_listed_in_parse_errors(tmp_path):
    run = tmp_path / "run"
    valid_path = run / "10-trustworthiness" / "confidentiality.findings.yaml"
    _write(valid_path, {"finding": [{
        "id": "fabricated-00000000",
        "agent": "confidentiality",
        "title": "PHI in topic",
        "evidence": [{"artifact": "tech_plan.md", "locator": "§4.2", "excerpt": "q"}],
    }]})
    bad_path = run / "10-trustworthiness" / "integrity.findings.yaml"
    bad_path.parent.mkdir(parents=True, exist_ok=True)
    bad_path.write_text(
        "finding:\n  - title: broken: unquoted colon: scalar\n    agent: integrity\n",
        encoding="utf-8",
    )
    bad_before = bad_path.read_bytes()

    result = canonicalize_run(run)  # must NOT raise

    # malformed file left untouched + surfaced; pass not aborted.
    assert bad_path.read_bytes() == bad_before
    assert len(result.parse_errors) == 1
    assert result.parse_errors[0][0] == str(bad_path)
    assert result.parse_errors[0][1]
    # valid file still canonicalized.
    assert yaml.safe_load(valid_path.read_text())["finding"][0]["id"].startswith("conf-")
