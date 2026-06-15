"""CAPEC bridge — derived CWE <-> ATT&CK view (ADR-0022).

The rollup is a pure function of (findings, catalog): it corroborates a finding's
co-tagged CWE + ATT&CK technique when a CAPEC attack pattern relates both, and
suggests the missing side when a finding carries only one. Absence of a CAPEC
link is SILENCE — never a bridge, never a suggestion, never a mismatch.
"""
from __future__ import annotations

import json
import pathlib

import yaml
from apd_gauntlet.cli import main
from apd_gauntlet.synthesis.rollup import RollupResult, _capec_bridge_rollup, build_rollups
from apd_gauntlet.validate import build_registry
from click.testing import CliRunner
from jsonschema import Draft202012Validator

REPO = pathlib.Path(__file__).parent.parent
SCHEMA_DIR = REPO / "schemas"

# Synthetic catalog: {capec_id: {name, related_cwe[], related_attack[]}}.
CATALOG = {
    "CAPEC-66": {"name": "SQL Injection",
                 "related_cwe": ["CWE-89", "CWE-1286"], "related_attack": ["T1190"]},
    "CAPEC-63": {"name": "Cross-Site Scripting (XSS)",
                 "related_cwe": ["CWE-79"], "related_attack": ["T1059"]},
    "CAPEC-7": {"name": "Blind SQL Injection",
                "related_cwe": ["CWE-89"], "related_attack": ["T1190"]},
}


def _finding(fid, *, cwe=None, attack=None):
    cm = {}
    if cwe is not None:
        cm["cwe"] = cwe
    if attack is not None:
        cm["mitre_attack"] = [{"technique": t} for t in attack]
    return {"id": fid, "control_mappings": cm}


def test_rollup_result_has_capec_field():
    assert RollupResult().capec is None


def test_corroborates_when_a_capec_relates_both_cwe_and_attack():
    findings = [_finding("intg-f0000001", cwe=["CWE-89"], attack=["T1190"])]
    doc = _capec_bridge_rollup(findings, CATALOG)
    assert doc["schema_version"] == 1
    assert doc["generated_by"] == "synthesizer"
    assert doc["suggestions"] == []
    # CAPEC-66 and CAPEC-7 both relate CWE-89 + T1190 -> two corroborating bridges.
    bridges = [b for b in doc["bridges"] if b["finding_id"] == "intg-f0000001"]
    by_capec = {b["capec_id"]: b for b in bridges}
    assert set(by_capec) == {"CAPEC-66", "CAPEC-7"}
    assert by_capec["CAPEC-66"]["capec_name"] == "SQL Injection"
    assert by_capec["CAPEC-66"]["cwe"] == ["CWE-89"]
    assert by_capec["CAPEC-66"]["attack"] == ["T1190"]


def test_sub_technique_parent_folds_for_corroboration():
    # Finding tags the sub-technique T1059.007; CAPEC-63 maps the parent T1059.
    findings = [_finding("conf-f0000002", cwe=["CWE-79"], attack=["T1059.007"])]
    doc = _capec_bridge_rollup(findings, CATALOG)
    bridges = doc["bridges"]
    assert len(bridges) == 1
    assert bridges[0]["capec_id"] == "CAPEC-63"
    assert bridges[0]["cwe"] == ["CWE-79"]
    # The finding's actual (sub-)technique id is reported, not the catalog parent.
    assert bridges[0]["attack"] == ["T1059.007"]


def test_suggests_attack_when_finding_has_only_cwe():
    findings = [_finding("conf-f0000003", cwe=["CWE-89"])]  # no technique
    doc = _capec_bridge_rollup(findings, CATALOG)
    assert doc["bridges"] == []
    sugg = doc["suggestions"]
    assert len(sugg) == 1
    assert sugg[0]["finding_id"] == "conf-f0000003"
    assert sugg[0]["direction"] == "cwe_to_attack"
    # CAPEC-66 and CAPEC-7 both relate CWE-89 and carry a technique.
    assert sugg[0]["via_capec"] == ["CAPEC-7", "CAPEC-66"]
    assert sugg[0]["suggested"] == ["T1190"]


def test_suggests_cwe_when_finding_has_only_attack():
    findings = [_finding("conf-f0000004", attack=["T1190"])]  # no cwe
    doc = _capec_bridge_rollup(findings, CATALOG)
    assert doc["bridges"] == []
    sugg = doc["suggestions"]
    assert len(sugg) == 1
    assert sugg[0]["direction"] == "attack_to_cwe"
    assert sugg[0]["via_capec"] == ["CAPEC-7", "CAPEC-66"]
    # Union of related CWE across the matching CAPECs, sorted.
    assert sugg[0]["suggested"] == ["CWE-1286", "CWE-89"]


def test_silent_when_both_sides_present_but_no_capec_links_them():
    # CWE-79 + T1190: CAPEC-66/7 relate T1190 but not CWE-79; CAPEC-63 relates
    # CWE-79 but maps T1059, not T1190. No single CAPEC bridges the pair.
    findings = [_finding("conf-f0000005", cwe=["CWE-79"], attack=["T1190"])]
    doc = _capec_bridge_rollup(findings, CATALOG)
    assert doc["bridges"] == []
    assert doc["suggestions"] == []  # silence-on-absence: NOT a mismatch finding


def test_bridges_are_deterministically_ordered():
    findings = [
        _finding("conf-b0000001", cwe=["CWE-89"], attack=["T1190"]),
        _finding("aaaa-a0000001", cwe=["CWE-89"], attack=["T1190"]),
    ]
    doc = _capec_bridge_rollup(findings, CATALOG)
    keys = [(b["finding_id"], b["capec_id"]) for b in doc["bridges"]]
    # Sorted by finding_id then numeric CAPEC id (CAPEC-7 before CAPEC-66).
    assert keys == [
        ("aaaa-a0000001", "CAPEC-7"), ("aaaa-a0000001", "CAPEC-66"),
        ("conf-b0000001", "CAPEC-7"), ("conf-b0000001", "CAPEC-66"),
    ]


# ---- build_rollups gating (uses the real bundled data/capec.json) ----

def _build_minimal_run(tmp_path, run_yaml, findings_yaml) -> pathlib.Path:
    run_dir = tmp_path / "run"
    synth = run_dir / "40-synthesis"
    ctx = run_dir / "00-context"
    synth.mkdir(parents=True)
    ctx.mkdir(parents=True)
    (run_dir / ".apd-run.yaml").write_text(run_yaml, encoding="utf-8")
    (synth / "deduped-findings.yaml").write_text(findings_yaml, encoding="utf-8")
    (synth / "deduped-capabilities.yaml").write_text("capability: []\n", encoding="utf-8")
    (ctx / "asset-inventory.yaml").write_text("assets: []\n", encoding="utf-8")
    return run_dir


# CAPEC-2 (real catalog): CWE-645 -> T1531.
_REAL_BRIDGE_FINDING = (
    "finding:\n"
    "  - schema_version: 1\n"
    "    id: ephem-aabbccdd\n"
    "    apd_goal: ephemeral\n"
    "    disposition: gap\n"
    "    control_mappings:\n"
    "      cwe: [CWE-645]\n"
    "      mitre_attack:\n"
    "        - technique: T1531\n"
)


def test_build_rollups_skips_capec_unless_both_cwe_and_attack_declared(tmp_path):
    # Only cwe declared (no mitre_attack) -> no bridge.
    run_dir = _build_minimal_run(
        tmp_path, "run_id: t\ndomain: pbm\ntaxonomies: [cwe]\n", _REAL_BRIDGE_FINDING
    )
    assert build_rollups(run_dir).capec is None
    assert not (run_dir / "40-synthesis" / "capec-bridge.yaml").exists()


def test_build_rollups_emits_capec_when_both_declared_and_a_bridge_exists(tmp_path):
    run_dir = _build_minimal_run(
        tmp_path, "run_id: t\ndomain: pbm\ntaxonomies: [cwe, mitre_attack]\n",
        _REAL_BRIDGE_FINDING,
    )
    result = build_rollups(run_dir)
    assert result.capec is not None
    by_capec = {b["capec_id"]: b for b in result.capec["bridges"]}
    assert "CAPEC-2" in by_capec
    assert by_capec["CAPEC-2"]["cwe"] == ["CWE-645"]
    assert by_capec["CAPEC-2"]["attack"] == ["T1531"]
    doc = yaml.safe_load((run_dir / "40-synthesis" / "capec-bridge.yaml").read_text())
    schema = json.loads((SCHEMA_DIR / "capec-bridge.schema.json").read_text())
    assert list(Draft202012Validator(schema, registry=build_registry()).iter_errors(doc)) == []


def test_build_rollups_capec_absent_when_declared_but_no_bridge_or_suggestion(tmp_path):
    # A finding whose CWE+technique no CAPEC links, and which is not one-sided.
    findings_yaml = (
        "finding:\n"
        "  - schema_version: 1\n"
        "    id: conf-deadbeef\n"
        "    apd_goal: confidentiality\n"
        "    disposition: gap\n"
        "    control_mappings:\n"
        "      cwe: [CWE-99999]\n"
        "      mitre_attack:\n"
        "        - technique: T9999\n"
    )
    run_dir = _build_minimal_run(
        tmp_path, "run_id: t\ndomain: pbm\ntaxonomies: [cwe, mitre_attack]\n", findings_yaml
    )
    assert build_rollups(run_dir).capec is None
    assert not (run_dir / "40-synthesis" / "capec-bridge.yaml").exists()


def test_existing_example_run_still_rolls_up(tmp_path):
    import shutil
    dst = tmp_path / "run"
    shutil.copytree(REPO / "examples" / "apd-20260601-claim-event-bus" / "expected", dst)
    result = CliRunner().invoke(main, ["rollup", str(dst)])
    assert result.exit_code == 0, result.output
    # nist/attack still produced; capec-bridge is additive (emitted only when a
    # bridge or suggestion exists — that is fine either way for the example).
    nist = yaml.safe_load((dst / "40-synthesis" / "nist-coverage.yaml").read_text())
    assert nist["controls"]
    capec = dst / "40-synthesis" / "capec-bridge.yaml"
    if capec.exists():
        doc = yaml.safe_load(capec.read_text())
        schema = json.loads((SCHEMA_DIR / "capec-bridge.schema.json").read_text())
        assert list(Draft202012Validator(schema, registry=build_registry()).iter_errors(doc)) == []
