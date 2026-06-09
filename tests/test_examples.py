"""Integration test: the bundled example must validate cleanly."""

from __future__ import annotations

import pathlib
import subprocess

import yaml


def test_claim_event_bus_example_validates():
    repo = pathlib.Path(__file__).parent.parent
    example = repo / "examples" / "apd-20260601-claim-event-bus" / "expected"
    result = subprocess.run(
        ["apd-gauntlet", "validate", str(example)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, (
        f"Validation failed:\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )


def _load_findings(rel):
    repo = pathlib.Path(__file__).parent.parent
    p = repo / "examples" / "apd-20260602-acme-mobile-banking" / "expected" / rel
    return {f["id"]: f for f in yaml.safe_load(p.read_text())["finding"]}


def test_storage_finding_carries_mas_mappings():
    f = _load_findings("10-trustworthiness/confidentiality.findings.yaml")["conf-9c065684"]
    cm = f["control_mappings"]
    # The detail cites MASVS-STORAGE-1 + the MASWE storage-leakage area; the
    # structured mappings must make those first-class.
    assert "MASVS-STORAGE-1" in cm["masvs"], cm
    assert "MASVS-STORAGE-2" in cm["masvs"], cm
    assert "MASWE-0006" in cm["maswe"], cm


def test_mobile_banking_example_validates():
    repo = pathlib.Path(__file__).parent.parent
    example = repo / "examples" / "apd-20260602-acme-mobile-banking" / "expected"
    result = subprocess.run(
        ["apd-gauntlet", "validate", str(example)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, (
        f"Validation failed:\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )


def test_hardcoded_secret_finding_carries_mas_mappings():
    f = _load_findings("10-trustworthiness/confidentiality.findings.yaml")["conf-4149d0db"]
    cm = f["control_mappings"]
    # detail cites MASVS-CRYPTO-2 (key management) and MASVS-RESILIENCE-2
    # (obfuscation is not a mitigant); the weakness is a hardcoded cryptographic key.
    assert "MASVS-CRYPTO-2" in cm["masvs"], cm
    assert "MASVS-RESILIENCE-2" in cm["masvs"], cm
    assert "MASWE-0014" in cm["maswe"], cm


def test_clientside_limit_finding_carries_mas_mappings():
    f = _load_findings("10-trustworthiness/integrity.findings.yaml")["intg-573fc767"]
    cm = f["control_mappings"]
    # detail cites MASVS-AUTH-1 (server-side authorization); the weakness is
    # business-logic / authorization enforced only client-side.
    assert "MASVS-AUTH-1" in cm["masvs"], cm
    assert "MASWE-0042" in cm["maswe"], cm


def test_https_capability_carries_masvs_mapping():
    repo = pathlib.Path(__file__).parent.parent
    p = (repo / "examples" / "apd-20260602-acme-mobile-banking" / "expected"
         / "10-trustworthiness" / "confidentiality.capabilities.yaml")
    caps = {c["id"]: c for c in yaml.safe_load(p.read_text())["capability"]}
    cm = caps["conf-cap-3ad59773"]["control_mappings"]
    # masvs is on BOTH findings and capabilities; maswe is findings-ONLY.
    assert "MASVS-NETWORK-1" in cm["masvs"], cm
    assert "maswe" not in cm, "maswe is findings-only and must not appear on a capability"


def test_mobile_deduped_corpus_carries_mas_mappings():
    repo = pathlib.Path(__file__).parent.parent
    synth = (repo / "examples" / "apd-20260602-acme-mobile-banking"
             / "expected" / "40-synthesis")
    fdoc = yaml.safe_load((synth / "deduped-findings.yaml").read_text())
    findings = {f["id"]: f for f in fdoc["finding"]}
    # The deduped corpus is what rollup reads; the MAS mappings must survive into it.
    assert findings["conf-9c065684"]["control_mappings"]["masvs"] == [
        "MASVS-STORAGE-1", "MASVS-STORAGE-2"]
    assert "MASWE-0014" in findings["conf-4149d0db"]["control_mappings"]["maswe"]
    cdoc = yaml.safe_load((synth / "deduped-capabilities.yaml").read_text())
    caps = {c["id"]: c for c in cdoc["capability"]}
    assert "MASVS-NETWORK-1" in caps["conf-cap-3ad59773"]["control_mappings"]["masvs"]


def test_mobile_mas_coverage_rollups_present_and_populated():
    repo = pathlib.Path(__file__).parent.parent
    synth = (repo / "examples" / "apd-20260602-acme-mobile-banking"
             / "expected" / "40-synthesis")
    masvs = yaml.safe_load((synth / "masvs-coverage.yaml").read_text())
    assert masvs["schema_version"] == 1
    assert masvs["generated_by"] == "synthesizer"
    ctrl_ids = {c["masvs_id"] for c in masvs["controls"]}
    # Controls cited across the mapped finding + capability must roll up.
    assert {"MASVS-STORAGE-1", "MASVS-CRYPTO-2", "MASVS-AUTH-1",
            "MASVS-NETWORK-1"} <= ctrl_ids, sorted(ctrl_ids)
    maswe = yaml.safe_load((synth / "maswe-coverage.yaml").read_text())
    entry_ids = {e["maswe_id"] for e in maswe["entries"]}
    assert {"MASWE-0006", "MASWE-0014", "MASWE-0042"} <= entry_ids, sorted(entry_ids)


def test_mobile_report_builds_with_active_mas_taxonomies(tmp_path):
    import shutil

    from apd_gauntlet.synthesis.audit import parse_data_js
    repo = pathlib.Path(__file__).parent.parent
    src = repo / "examples" / "apd-20260602-acme-mobile-banking" / "expected"
    dst = tmp_path / "run"
    shutil.copytree(src, dst)
    result = subprocess.run(
        ["apd-gauntlet", "build-report", str(dst), "--quiet"],
        capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0, result.stderr
    data = parse_data_js(dst / "40-synthesis" / "report-html" / "data.js")
    meta = data["meta"]
    # data.meta.active_taxonomies is lifted from the run-config taxonomies.
    assert "masvs" in meta["active_taxonomies"]
    assert "maswe" in meta["active_taxonomies"]
    # The MAS coverage scenes render from the rollups.
    assert data["masvs_coverage"], "masvs_coverage scene must be populated"
    assert data["maswe_coverage"], "maswe_coverage scene must be populated"
