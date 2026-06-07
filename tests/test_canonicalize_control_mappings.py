"""Unit tests for the G4 control-mappings normalization auto-fix (PR2 part A).

canonicalize deterministically self-heals two specialist-output frictions BEFORE
the validate gate hard-blocks them:
  - a root-level ``mitre_atlas`` key moved to ``control_mappings.atlas``;
  - root-level taxonomy keys (cwe / owasp_* / atlas / mitre_attack /
    nist_800_53r5) LIFTED into ``control_mappings`` — scoped per record kind
    (finding vs capability allowed-key sets differ).

Loss-preventing: a non-empty existing destination sub-key is never overwritten;
the root key is left in place so the schema's additionalProperties:false gate
still fires for a human to resolve.
"""
from __future__ import annotations

import pathlib

import yaml
from apd_gauntlet.canonicalize import _normalize_control_mappings, canonicalize_run


def _write(path: pathlib.Path, doc) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(doc, sort_keys=False), encoding="utf-8")


def _finding(agent, title, locator, fid="fabricated-00000000", **extra):
    rec = {
        "id": fid,
        "agent": agent,
        "title": title,
        "evidence": [{"artifact": "tech_plan.md", "locator": locator, "excerpt": "q"}],
    }
    rec.update(extra)
    return rec


# --- pure helper ----------------------------------------------------------


def test_helper_moves_mitre_atlas_to_control_mappings_atlas():
    rec = {"agent": "confidentiality", "mitre_atlas": ["AML.T0051"]}
    mutated = _normalize_control_mappings(rec)
    assert mutated is True
    assert "mitre_atlas" not in rec
    assert rec["control_mappings"]["atlas"] == ["AML.T0051"]


def test_helper_lifts_root_taxonomy_keys_into_control_mappings():
    rec = {
        "agent": "confidentiality",
        "cwe": ["CWE-200"],
        "owasp_api_top10": ["API1:2023"],
        "mitre_attack": [{"technique": "T1078", "tactic": "TA0001", "rationale": "x" * 30}],
    }
    mutated = _normalize_control_mappings(rec)
    assert mutated is True
    cm = rec["control_mappings"]
    assert cm["cwe"] == ["CWE-200"]
    assert cm["owasp_api_top10"] == ["API1:2023"]
    assert cm["mitre_attack"][0]["technique"] == "T1078"
    assert "cwe" not in rec
    assert "owasp_api_top10" not in rec
    assert "mitre_attack" not in rec


def test_helper_conflict_leaves_root_key_in_place():
    # control_mappings.atlas is already non-empty -> do NOT overwrite, and LEAVE
    # the root mitre_atlas in place so the schema gate fires for a human.
    rec = {
        "agent": "confidentiality",
        "mitre_atlas": ["AML.T0051"],
        "control_mappings": {"atlas": ["AML.T0043"]},
    }
    mutated = _normalize_control_mappings(rec)
    assert mutated is False
    assert rec["mitre_atlas"] == ["AML.T0051"]  # root key untouched
    assert rec["control_mappings"]["atlas"] == ["AML.T0043"]  # destination untouched


def test_helper_conflict_on_lifted_taxonomy_key_leaves_root_in_place():
    rec = {
        "agent": "confidentiality",
        "cwe": ["CWE-200"],
        "control_mappings": {"cwe": ["CWE-89"]},
    }
    mutated = _normalize_control_mappings(rec)
    assert mutated is False
    assert rec["cwe"] == ["CWE-200"]  # root key untouched (gate will fire)
    assert rec["control_mappings"]["cwe"] == ["CWE-89"]


def test_helper_empty_destination_subkey_is_overwritten():
    # An EMPTY existing destination sub-key is not loss-preventing -> lift wins.
    rec = {"agent": "confidentiality", "cwe": ["CWE-200"], "control_mappings": {"atlas": []}}
    mutated = _normalize_control_mappings(rec)
    assert mutated is True
    assert rec["control_mappings"]["cwe"] == ["CWE-200"]
    assert "cwe" not in rec


def test_helper_no_root_taxonomy_keys_is_noop():
    rec = {"agent": "confidentiality", "control_mappings": {"nist_800_53r5": ["SC-8"]}}
    assert _normalize_control_mappings(rec) is False


def test_helper_capability_scoped_to_its_allowed_keys():
    # capability control_mappings allows mitre_attack + nist_800_53r5, but NOT
    # cwe / owasp* / atlas. A root cwe on a capability is NOT lifted (would just
    # move the schema violation), so it is left at the root.
    rec = {
        "agent": "confidentiality",
        "cwe": ["CWE-200"],
        "mitre_attack": [{"technique": "T1078", "tactic": "TA0001", "rationale": "x" * 30}],
        "maturity": "implemented",
    }
    mutated = _normalize_control_mappings(rec, kind="capability")
    assert mutated is True
    assert rec["control_mappings"]["mitre_attack"][0]["technique"] == "T1078"
    assert "mitre_attack" not in rec
    # cwe is NOT a capability control_mappings key -> left at the root.
    assert rec["cwe"] == ["CWE-200"]
    assert "cwe" not in rec.get("control_mappings", {})


def test_helper_capability_does_not_lift_atlas_from_mitre_atlas_root():
    # atlas is not a capability control_mappings key; mitre_atlas root stays put.
    rec = {"agent": "confidentiality", "mitre_atlas": ["AML.T0051"], "maturity": "designed"}
    mutated = _normalize_control_mappings(rec, kind="capability")
    assert mutated is False
    assert rec["mitre_atlas"] == ["AML.T0051"]


# --- end-to-end through canonicalize_run ----------------------------------


def test_canonicalize_normalizes_mitre_atlas_on_finding(tmp_path):
    run = tmp_path / "run"
    path = run / "10-trustworthiness" / "confidentiality.findings.yaml"
    _write(path, {"finding": [_finding(
        "confidentiality", "PHI leak via topic", "§4.2", mitre_atlas=["AML.T0051"],
    )]})
    canonicalize_run(run)
    rec = yaml.safe_load(path.read_text())["finding"][0]
    assert "mitre_atlas" not in rec
    assert rec["control_mappings"]["atlas"] == ["AML.T0051"]


def test_canonicalize_lifts_root_taxonomy_keys_on_finding(tmp_path):
    run = tmp_path / "run"
    path = run / "10-trustworthiness" / "confidentiality.findings.yaml"
    _write(path, {"finding": [_finding(
        "confidentiality", "PHI leak via topic", "§4.2",
        cwe=["CWE-200"],
        owasp_api_top10=["API1:2023"],
        mitre_attack=[{"technique": "T1078", "tactic": "TA0001", "rationale": "z" * 30}],
    )]})
    canonicalize_run(run)
    rec = yaml.safe_load(path.read_text())["finding"][0]
    cm = rec["control_mappings"]
    assert cm["cwe"] == ["CWE-200"]
    assert cm["owasp_api_top10"] == ["API1:2023"]
    assert cm["mitre_attack"][0]["technique"] == "T1078"
    for k in ("cwe", "owasp_api_top10", "mitre_attack"):
        assert k not in rec


def test_canonicalize_conflict_leaves_root_key_in_place(tmp_path):
    run = tmp_path / "run"
    path = run / "10-trustworthiness" / "confidentiality.findings.yaml"
    _write(path, {"finding": [_finding(
        "confidentiality", "PHI leak via topic", "§4.2",
        mitre_atlas=["AML.T0051"],
        control_mappings={"atlas": ["AML.T0043"]},
    )]})
    canonicalize_run(run)
    rec = yaml.safe_load(path.read_text())["finding"][0]
    # root key stays -> schema additionalProperties:false will block for a human.
    assert rec["mitre_atlas"] == ["AML.T0051"]
    assert rec["control_mappings"]["atlas"] == ["AML.T0043"]


def test_canonicalize_normalizes_apath_record(tmp_path):
    """apath-* findings (agent attack_path_analyzer, NOT in _PREFIX_BY_AGENT)
    must STILL be normalized — normalization does not gate on agent prefix."""
    run = tmp_path / "run"
    path = run / "40-synthesis" / "attack-path.findings.yaml"
    _write(path, {"finding": [{
        "schema_version": 1,
        "id": "apath-deadbeef",
        "agent": "attack_path_analyzer",
        "title": "Crown-jewel reachable",
        "evidence": [{"artifact": ".apd-run.yaml", "locator": "x", "excerpt": "y"}],
        "mitre_atlas": ["AML.T0051"],
    }]})
    canonicalize_run(run)
    rec = yaml.safe_load(path.read_text())["finding"][0]
    assert "mitre_atlas" not in rec
    assert rec["control_mappings"]["atlas"] == ["AML.T0051"]
    # id of an out-of-scope agent is left untouched (no recompute).
    assert rec["id"] == "apath-deadbeef"


def test_canonicalize_normalizes_tmeval_record(tmp_path):
    run = tmp_path / "run"
    path = run / "40-threat-model" / "threat-model.findings.yaml"
    _write(path, {"finding": [{
        "schema_version": 1,
        "id": "tmeval-deadbeef",
        "agent": "threat_model_evaluator",
        "title": "STRIDE gap on spoofing",
        "evidence": [{"artifact": "tm.md", "locator": "x", "excerpt": "y"}],
        "cwe": ["CWE-287"],
    }]})
    canonicalize_run(run)
    rec = yaml.safe_load(path.read_text())["finding"][0]
    assert "cwe" not in rec
    assert rec["control_mappings"]["cwe"] == ["CWE-287"]
    assert rec["id"] == "tmeval-deadbeef"


def test_canonicalize_file_needing_only_normalization_is_written_back(tmp_path):
    """A file whose ONLY change is a normalization (no id recompute, because the
    agent is out-of-scope for id recompute) must STILL be written back."""
    run = tmp_path / "run"
    path = run / "40-synthesis" / "attack-path.findings.yaml"
    _write(path, {"finding": [{
        "schema_version": 1,
        "id": "apath-deadbeef",
        "agent": "attack_path_analyzer",
        "title": "Crown-jewel reachable",
        "evidence": [{"artifact": ".apd-run.yaml", "locator": "x", "excerpt": "y"}],
        "mitre_atlas": ["AML.T0051"],
    }]})
    before = path.read_bytes()
    canonicalize_run(run)
    after = path.read_bytes()
    assert after != before  # file WAS rewritten despite no id recompute
    rec = yaml.safe_load(path.read_text())["finding"][0]
    assert "mitre_atlas" not in rec


def test_canonicalize_normalization_is_idempotent(tmp_path):
    run = tmp_path / "run"
    path = run / "10-trustworthiness" / "confidentiality.findings.yaml"
    _write(path, {"finding": [_finding(
        "confidentiality", "PHI leak via topic", "§4.2", mitre_atlas=["AML.T0051"],
    )]})
    canonicalize_run(run)
    first = path.read_bytes()
    canonicalize_run(run)
    second = path.read_bytes()
    assert first == second  # 2nd canonicalize = no further change


def test_canonicalize_capability_normalization_scoped(tmp_path):
    run = tmp_path / "run"
    path = run / "10-trustworthiness" / "confidentiality.capabilities.yaml"
    _write(path, {"capability": [{
        "id": "fabricated-00000000",
        "agent": "confidentiality",
        "title": "Field encryption capability",
        "maturity": "implemented",
        "evidence": [{"artifact": "tech_plan.md", "locator": "§1", "excerpt": "q"}],
        "cwe": ["CWE-200"],
        "mitre_attack": [{"technique": "T1078", "tactic": "TA0001", "rationale": "z" * 30}],
    }]})
    canonicalize_run(run)
    rec = yaml.safe_load(path.read_text())["capability"][0]
    # mitre_attack IS a capability control_mappings key -> lifted.
    assert rec["control_mappings"]["mitre_attack"][0]["technique"] == "T1078"
    assert "mitre_attack" not in rec
    # cwe is NOT a capability control_mappings key -> left at root.
    assert rec["cwe"] == ["CWE-200"]
    assert "cwe" not in rec.get("control_mappings", {})
