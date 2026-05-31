"""Tests for the deterministic domain-coverage-delta pre-pass (§5.1)."""
from __future__ import annotations

import pathlib

import yaml
from apd_gauntlet.cli import main
from apd_gauntlet.synthesis.coverage_delta import build_coverage_delta
from click.testing import CliRunner

DOMAINS = pathlib.Path("domains")


def _run_dir(tmp_path, inventory_yaml: str, domains_list):
    run_dir = tmp_path / "run"
    (run_dir / "00-context").mkdir(parents=True)
    (run_dir / "40-synthesis").mkdir(parents=True)
    domains_block = "domains:\n" + "".join(f"  - {d}\n" for d in domains_list)
    (run_dir / ".apd-run.yaml").write_text(
        f"run_id: test\n{domains_block}framework_version: 1.5.0\n", encoding="utf-8"
    )
    (run_dir / "00-context" / "asset-inventory.yaml").write_text(inventory_yaml, encoding="utf-8")
    return run_dir


_INV_CROWN_JEWEL = """\
schema_version: 1
generated_by: intake
assets:
  - asset_id: asset-1a2b3c4d
    name: novel_widget_store
    asset_type: data_store
    data_classifications: [pci]
    provenance:
      source: artifact
      locator: inputs/design.md#widgets
    confidence: high
  - asset_id: asset-2b3c4d5e
    name: pack_default_store
    asset_type: data_store
    provenance:
      source: domain_default
    confidence: medium
identities: []
trust_boundaries: []
"""


def test_crown_jewel_delta_emits_one_candidate(tmp_path):
    run_dir = _run_dir(tmp_path, _INV_CROWN_JEWEL, ["api-security", "pbm"])
    result = build_coverage_delta(run_dir, DOMAINS)
    doc = yaml.safe_load((run_dir / "40-synthesis" / "domain-coverage-delta.yaml").read_text())
    assert doc["generated_by"] == "coverage-delta"
    assert doc["examined_domains"] == ["api-security", "pbm"]
    cj = [c for c in doc["candidates"] if c["improvement_type"] == "missing_crown_jewel"]
    assert len(cj) == 1
    c = cj[0]
    assert c["source"] == "deterministic"
    assert c["priority"] == "high"
    assert c["default_target_pack"] == "api-security"
    assert c["evidence"][0] == {"kind": "asset_inventory", "ref": "asset-1a2b3c4d"}
    # The domain_default asset emits no candidate.
    assert all(c.get("asset_name") != "pack_default_store" for c in doc["candidates"])
    # The build returns the same path the CLI writes.
    assert result == run_dir / "40-synthesis" / "domain-coverage-delta.yaml"


def test_attacker_position_and_trust_boundary_candidates(tmp_path):
    inv = """\
schema_version: 1
generated_by: intake
assets:
  - asset_id: asset-aaaaaaaa
    name: ext_dep
    asset_type: external_dependency
    provenance: { source: artifact }
    confidence: high
  - asset_id: asset-bbbbbbbb
    name: core_svc
    asset_type: service
    provenance: { source: artifact }
    confidence: high
identities:
  - identity_id: idn-cccccccc
    name: partner_portal
    identity_type: external_party
    provenance: { source: artifact }
    confidence: high
  - identity_id: idn-dddddddd
    name: default_external_actor
    identity_type: external_party
    provenance: { source: domain_default }
    confidence: medium
trust_boundaries:
  - boundary_id: tb-dddddddd
    name: novel_partner_to_core
    crosses: [asset-aaaaaaaa, asset-bbbbbbbb]
    provenance: { source: artifact }
  - boundary_id: tb-eeeeeeee
    name: default_corp_boundary
    crosses: []
    provenance: { source: domain_default }
"""
    run_dir = _run_dir(tmp_path, inv, ["api-security"])
    build_coverage_delta(run_dir, DOMAINS)
    doc = yaml.safe_load((run_dir / "40-synthesis" / "domain-coverage-delta.yaml").read_text())
    pos = [c for c in doc["candidates"] if c["improvement_type"] == "missing_attacker_position"]
    bnd = [c for c in doc["candidates"] if c["improvement_type"] == "missing_trust_boundary"]
    assert pos and pos[0]["evidence"][0]["ref"] == "idn-cccccccc"
    assert pos[0]["source"] == "deterministic"
    assert bnd and bnd[0]["evidence"][0]["ref"] == "tb-dddddddd"
    assert bnd[0]["source"] == "deterministic"
    # domain_default identity and boundary must NOT appear as candidates.
    assert all(c.get("evidence", [{}])[0].get("ref") != "idn-dddddddd" for c in doc["candidates"])
    assert all(c.get("evidence", [{}])[0].get("ref") != "tb-eeeeeeee" for c in doc["candidates"])


def test_empty_inventory_emits_empty_candidates(tmp_path):
    inv = (
        "schema_version: 1\ngenerated_by: intake\n"
        "assets: []\nidentities: []\ntrust_boundaries: []\n"
    )
    run_dir = _run_dir(tmp_path, inv, ["pbm"])
    build_coverage_delta(run_dir, DOMAINS)
    doc = yaml.safe_load((run_dir / "40-synthesis" / "domain-coverage-delta.yaml").read_text())
    assert doc["candidates"] == []
    assert doc["examined_domains"] == ["pbm"]


def test_missing_inventory_emits_empty_candidates(tmp_path):
    run_dir = tmp_path / "run"
    (run_dir / "00-context").mkdir(parents=True)
    (run_dir / "40-synthesis").mkdir(parents=True)
    (run_dir / ".apd-run.yaml").write_text(
        "run_id: t\ndomains:\n  - pbm\nframework_version: 1.5.0\n", encoding="utf-8"
    )
    build_coverage_delta(run_dir, DOMAINS)
    doc = yaml.safe_load((run_dir / "40-synthesis" / "domain-coverage-delta.yaml").read_text())
    assert doc["candidates"] == []


def test_output_byte_stable(tmp_path):
    run_dir = _run_dir(tmp_path, _INV_CROWN_JEWEL, ["api-security", "pbm"])
    build_coverage_delta(run_dir, DOMAINS)
    first = (run_dir / "40-synthesis" / "domain-coverage-delta.yaml").read_text()
    build_coverage_delta(run_dir, DOMAINS)
    second = (run_dir / "40-synthesis" / "domain-coverage-delta.yaml").read_text()
    assert first == second


def test_cli_registered_and_runs(tmp_path):
    run_dir = _run_dir(tmp_path, _INV_CROWN_JEWEL, ["api-security"])
    result = CliRunner().invoke(main, ["domain-coverage-delta", str(run_dir)])
    assert result.exit_code == 0, result.output
    assert (run_dir / "40-synthesis" / "domain-coverage-delta.yaml").exists()
