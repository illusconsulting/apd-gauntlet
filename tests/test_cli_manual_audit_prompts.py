"""Tests for the manual-audit-prompts subcommand.

The generator is deterministic and byte-stable over a committed synthetic
blocked-findings fixture: same input -> same bytes, blocked-only, keyword-routed
commands, no timestamp.
"""
from __future__ import annotations

import copy
import pathlib
import shutil

import yaml
from apd_gauntlet.cli import main
from apd_gauntlet.manual_audit import commands_for, render_prompts, write_prompts
from click.testing import CliRunner

REPO = pathlib.Path(__file__).resolve().parent.parent
FIXTURES = REPO / "tests" / "fixtures" / "manual-audit"
DEDUPED = FIXTURES / "deduped-findings.yaml"
EXPECTED = FIXTURES / "expected-manual-audit-prompts.md"


def _scaffold(tmp_path):
    """Copy the synthetic deduped-findings fixture into a tmp run's 40-synthesis."""
    run_dir = tmp_path / "run"
    synth = run_dir / "40-synthesis"
    synth.mkdir(parents=True)
    shutil.copy2(DEDUPED, synth / "deduped-findings.yaml")
    return run_dir


def test_render_prompts_matches_committed_expected_bytes():
    """render_prompts is byte-stable against the committed expected fixture."""
    doc = yaml.safe_load(DEDUPED.read_text(encoding="utf-8"))
    findings = [f for f in (doc.get("finding") or []) if isinstance(f, dict)]
    assert render_prompts(findings) == EXPECTED.read_text(encoding="utf-8")


def test_render_does_not_mutate_input():
    """render_prompts is pure: it must not mutate the findings list it is given."""
    doc = yaml.safe_load(DEDUPED.read_text(encoding="utf-8"))
    findings = [f for f in (doc.get("finding") or []) if isinstance(f, dict)]
    before = copy.deepcopy(findings)
    render_prompts(findings)
    assert findings == before


def test_only_blocked_findings_appear():
    """A disposition:gap record must not appear; all four blocked ids must."""
    out = EXPECTED.read_text(encoding="utf-8")
    assert "integ-55555555" not in out
    for fid in ("dist-11111111", "auth-22222222", "ephem-33333333", "conf-44444444"):
        assert fid in out


def test_keyword_routing_emits_expected_commands():
    """Each keyword route maps to its command template, deduped in table order."""
    np = {"title": "NetworkPolicy enforcement unknown", "summary": "deny-all declared"}
    assert commands_for(np) == ["kubectl get networkpolicies -A"]

    pa = {"title": "istio PeerAuthentication mTLS mode", "summary": "strict?"}
    assert commands_for(pa) == [
        "kubectl get peerauthentications.security.istio.io -A",
        "istioctl proxy-config secret -n production",
    ]

    none = {"title": "KMS DEK rotation cadence", "summary": "not specified"}
    assert commands_for(none) == []


def test_no_blocked_findings_renders_placeholder():
    """A corpus with no blocked records renders the empty-state line."""
    gap_only = [{"id": "x-1", "disposition": "gap", "title": "t", "summary": "s"}]
    out = render_prompts(gap_only)
    assert "No blocked findings" in out


def test_cli_writes_byte_stable_file(tmp_path):
    """The subcommand writes 40-synthesis/manual-audit-prompts.md byte-for-byte
    equal to the committed expected fixture and reports the blocked count."""
    run_dir = _scaffold(tmp_path)
    runner = CliRunner()
    result = runner.invoke(main, ["manual-audit-prompts", str(run_dir)])
    assert result.exit_code == 0, result.output
    assert "4 blocked findings" in result.output
    written = (run_dir / "40-synthesis" / "manual-audit-prompts.md").read_text(
        encoding="utf-8"
    )
    assert written == EXPECTED.read_text(encoding="utf-8")


def test_cli_missing_deduped_exits_1(tmp_path):
    """Absent deduped-findings.yaml exits non-zero with a clear message."""
    run_dir = tmp_path / "empty"
    (run_dir / "40-synthesis").mkdir(parents=True)
    runner = CliRunner()
    result = runner.invoke(main, ["manual-audit-prompts", str(run_dir)])
    assert result.exit_code != 0
    assert "No deduped-findings.yaml" in result.output


def test_write_prompts_returns_path_and_count(tmp_path):
    """write_prompts returns the output path and the blocked count."""
    run_dir = _scaffold(tmp_path)
    out_path, count = write_prompts(run_dir)
    assert out_path.name == "manual-audit-prompts.md"
    assert count == 4
