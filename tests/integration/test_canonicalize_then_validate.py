"""Integration: non-canonical specialist output -> canonicalize -> validate clean."""
from __future__ import annotations

import pathlib

import yaml
from apd_gauntlet.cli import main
from click.testing import CliRunner


def _write(path: pathlib.Path, doc) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(doc, sort_keys=False), encoding="utf-8")


def _full_finding(agent, title, locator):
    return {
        "schema_version": 1,
        "agent": agent,
        "apd_tier": "trustworthiness",
        "apd_goal": "confidentiality" if agent == "confidentiality" else "integrity",
        "disposition": "gap",
        "severity": "high",
        "confidence": "high",
        "title": title,
        "summary": "one sentence.",
        "detail": "multi paragraph technical analysis.",
        "evidence": [{"artifact": "tech_plan.md", "locator": locator, "excerpt": "short quote"}],
        "control_mappings": {"nist_800_53r5": []},
        "recommendation": {
            "posture": "required",
            "summary": "remediate this finding",
            "detail": "detailed remediation steps go here.",
        },
    }


def test_canonicalize_then_tier_validate_is_clean(tmp_path):
    run = tmp_path / "run"
    # Non-canonical specialist output: plural root + per-record wrapper + fabricated id.
    _write(run / "10-trustworthiness" / "confidentiality.findings.yaml", {
        "findings": [{"finding": dict(_full_finding("confidentiality",
                                                    "PHI in topic", "§4.2"),
                                       id="fabricated-deadbeef")}],
    })
    runner = CliRunner()

    # Before canonicalize: the tier gate ERRORs on the non-canonical envelope.
    pre = runner.invoke(main, ["validate", str(run), "--tier", "10-trustworthiness"])
    assert pre.exit_code != 0
    assert "non-canonical envelope" in pre.output

    # canonicalize, then re-validate the tier.
    canon = runner.invoke(main, ["canonicalize", str(run)])
    assert canon.exit_code == 0, canon.output
    post = runner.invoke(main, ["validate", str(run), "--tier", "10-trustworthiness"])
    assert post.exit_code == 0, post.output
