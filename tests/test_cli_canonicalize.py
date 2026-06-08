"""CLI tests for `apd-gauntlet canonicalize`."""
from __future__ import annotations

import pathlib

import yaml
from apd_gauntlet.cli import main
from apd_gauntlet.linters import compute_id
from click.testing import CliRunner


def _write(path: pathlib.Path, doc) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(doc, sort_keys=False), encoding="utf-8")


def test_canonicalize_command_normalizes_and_reports(tmp_path):
    run = tmp_path / "run"
    _write(run / "10-trustworthiness" / "confidentiality.findings.yaml", {
        "findings": [{"finding": {
            "id": "fabricated-00000000",
            "agent": "confidentiality",
            "title": "PHI in topic",
            "evidence": [{"artifact": "tech_plan.md", "locator": "§4.2", "excerpt": "q"}],
        }}],
    })
    result = CliRunner().invoke(main, ["canonicalize", str(run)])
    assert result.exit_code == 0, result.output
    assert "recanonicalized" in result.output
    doc = yaml.safe_load(
        (run / "10-trustworthiness" / "confidentiality.findings.yaml").read_text()
    )
    assert "finding" in doc, doc.keys()
    assert doc["finding"][0]["id"] == compute_id("conf", "PHI in topic", "§4.2")


def test_canonicalize_command_exits_nonzero_on_collision(tmp_path):
    run = tmp_path / "run"
    rec = {
        "agent": "confidentiality", "title": "dup",
        "evidence": [{"artifact": "tech_plan.md", "locator": "§1", "excerpt": "q"}],
    }
    _write(run / "10-trustworthiness" / "confidentiality.findings.yaml", {
        "finding": [dict(rec, id="fab-1"), dict(rec, id="fab-2")],
    })
    result = CliRunner().invoke(main, ["canonicalize", str(run)])
    assert result.exit_code == 1, result.output
    # Click 8.4.1 removed mix_stderr kwarg; stderr is always separate and exposed as result.stderr
    assert "collision" in result.stderr.lower(), result.stderr


def test_canonicalize_command_exits_nonzero_on_unparseable_file(tmp_path):
    """FW-1: an unparseable specialist file is a HARD failure (nonzero exit),
    not a quiet note in a zero-exit summary — but every PARSEABLE file is still
    canonicalized first (the malformed one is skipped, not aborted)."""
    run = tmp_path / "run"
    _write(run / "10-trustworthiness" / "confidentiality.findings.yaml", {
        "finding": [{
            "id": "fabricated-00000000",
            "agent": "confidentiality",
            "title": "PHI in topic",
            "evidence": [{"artifact": "tech_plan.md", "locator": "§4.2", "excerpt": "q"}],
        }],
    })
    # An unparseable sibling: an unquoted colon-space inside a flow value.
    bad = run / "20-scalability" / "resilient.findings.yaml"
    bad.parent.mkdir(parents=True, exist_ok=True)
    bad.write_text(
        'finding:\n- id: x\n  excerpt: retry={"max_attempts": 1} broke yaml\n',
        encoding="utf-8",
    )
    result = CliRunner().invoke(main, ["canonicalize", str(run)])
    assert result.exit_code == 1, result.output
    assert "unparseable" in result.stderr.lower() or "skipped" in result.stderr.lower()
    # The valid file was still canonicalized (pass not aborted).
    doc = yaml.safe_load(
        (run / "10-trustworthiness" / "confidentiality.findings.yaml").read_text()
    )
    assert doc["finding"][0]["id"] == compute_id("conf", "PHI in topic", "§4.2")
