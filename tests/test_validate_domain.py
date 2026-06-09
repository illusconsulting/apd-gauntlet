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


def test_validate_domain_accepts_multiple_packs():
    result = CliRunner().invoke(
        main, ["validate-domain", "sample", "sample2", "--domains-dir", "tests/fixtures/domains"]
    )
    assert result.exit_code == 0, result.output
    assert "sample" in result.output and "sample2" in result.output


def test_domain_accepts_optional_taxonomies(tmp_path=None):
    import json
    import pathlib

    import yaml
    from apd_gauntlet.validate import build_registry
    from jsonschema import Draft202012Validator

    repo = pathlib.Path(__file__).resolve().parent.parent
    schema = json.loads((repo / "schemas" / "domain.schema.json").read_text())
    doc = yaml.safe_load(
        (repo / "tests" / "fixtures" / "valid" / "domain-with-taxonomies.yaml").read_text()
    )
    errors = list(Draft202012Validator(schema, registry=build_registry()).iter_errors(doc))
    assert errors == [], [e.message for e in errors]
    assert doc["taxonomies"] == ["masvs", "maswe"]


def test_domain_rejects_unknown_taxonomy():
    import json
    import pathlib

    import yaml
    from apd_gauntlet.validate import build_registry
    from jsonschema import Draft202012Validator

    repo = pathlib.Path(__file__).resolve().parent.parent
    schema = json.loads((repo / "schemas" / "domain.schema.json").read_text())
    doc = yaml.safe_load(
        (repo / "tests" / "fixtures" / "invalid" / "domain-with-invalid-taxonomy.yaml").read_text()
    )
    errors = list(Draft202012Validator(schema, registry=build_registry()).iter_errors(doc))
    assert errors, "unknown domain taxonomy must be rejected by the enum"
