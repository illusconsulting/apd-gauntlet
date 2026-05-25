"""Tests for the validate-domain command."""
from __future__ import annotations

from apd_gauntlet.cli import main
from click.testing import CliRunner


def test_validate_domain_sample_fixture():
    runner = CliRunner()
    result = runner.invoke(main, ["validate-domain", "sample",
                                  "--domains-dir", "tests/fixtures/domains"])
    assert result.exit_code == 0, result.output
    assert "OK" in result.output


def test_validate_domain_missing_includes(tmp_path):
    # Create a domain with a missing include.
    dom_dir = tmp_path / "domains" / "broken"
    dom_dir.mkdir(parents=True)
    (dom_dir / "domain.yaml").write_text("""\
name: broken
display_name: "Broken Domain"
version: 0.1.0
framework_compat: ">=1.0.0,<2.0.0"
description: "A test domain with a missing include file."
includes:
  - nonexistent.md
regulatory_anchors: []
""")
    runner = CliRunner()
    result = runner.invoke(main, ["validate-domain", "broken",
                                  "--domains-dir", str(tmp_path / "domains")])
    assert result.exit_code == 1
    assert "missing include" in result.output.lower()
