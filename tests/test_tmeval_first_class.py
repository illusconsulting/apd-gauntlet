"""F1: tmeval (threat-model-evaluator) findings are first-class downstream.

Before this fix the decomposed pipeline unioned only ``apath-*`` tier-4 findings
into the rollups/metrics/report, silently dropping ``tmeval-*`` from coverage,
the severity distribution, the 9xN matrix, and the report findings list (they
appeared only as ``finding_id`` references and in the threat-model scene). These
tests pin tmeval as a first-class finding source across:

  * ``rollup._load_deduped`` (-> metrics + nist/attack/matrix coverage)
  * ``loader.RunArtifacts.threat_model_findings`` (loaded from
    ``40-threat-model/threat-model.findings.yaml``)
  * ``transform.findings_array`` (the report findings list)
  * the shipped example golden (data.js carries the tmeval finding records)
"""
from __future__ import annotations

import pathlib

import yaml
from apd_gauntlet.report.loader import RunArtifacts, load_run
from apd_gauntlet.report.transform import findings_array
from apd_gauntlet.synthesis.rollup import _load_deduped, build_rollups

REPO = pathlib.Path(__file__).parent.parent
EXAMPLE = REPO / "examples" / "apd-20260601-claim-event-bus" / "expected"

_TMEVAL = {
    "schema_version": 1, "id": "tmeval-abcabc12", "agent": "threat_model_evaluator",
    "apd_tier": "auditability", "apd_goal": "non_repudiation", "disposition": "gap",
    "severity": "medium", "confidence": "high",
    "title": "Threat model omits Repudiation for the audit-log-writer surface",
    "summary": "STRIDE Repudiation entry absent for the audit-log-writer surface.",
    "detail": "The authored baseline lists S, T, I, D, E but no R for this surface.",
    "evidence": [{"artifact": "00-context/threat-model-normalized.yaml",
                  "locator": "entries[asset=audit-log-writer]",
                  "excerpt": "5 entries: S,T,I,D,E; no R"}],
    "control_mappings": {"nist_800_53r5": ["AU-10"]},
    "recommendation": {"posture": "recommended",
                       "summary": "Add a Repudiation entry for the audit-log-writer.",
                       "detail": "Cover non-repudiation explicitly in the threat model."},
}
_LENS = {
    "schema_version": 1, "id": "conf-13131313", "agent": "confidentiality",
    "apd_tier": "trustworthiness", "apd_goal": "confidentiality", "disposition": "gap",
    "severity": "high", "confidence": "high",
    "title": "Plaintext PHI on the claim-events topic",
    "summary": "PHI fields are plaintext on the topic.",
    "detail": "Only broker-level encryption applies; payloads are plaintext.",
    "evidence": [{"artifact": "tech_plan.md", "locator": "§4.2", "excerpt": "broker only"}],
    "control_mappings": {"nist_800_53r5": ["SC-8"]},
    "recommendation": {"posture": "required", "summary": "Encrypt PHI payloads.",
                       "detail": "Apply envelope encryption before publishing."},
}


def _minimal_run(tmp_path: pathlib.Path) -> pathlib.Path:
    run = tmp_path / "run"
    (run / "40-synthesis").mkdir(parents=True)
    (run / "40-threat-model").mkdir(parents=True)
    (run / "00-context").mkdir(parents=True)
    (run / ".apd-run.yaml").write_text("run_id: t\ndomains: [pbm]\n")
    (run / "00-context" / "asset-inventory.yaml").write_text(
        "schema_version: 1\ngenerated_by: intake\nassets: []\nidentities: []\n"
        "trust_boundaries: []\n")
    (run / "40-synthesis" / "deduped-findings.yaml").write_text(
        yaml.safe_dump({"schema_version": 1, "finding": [_LENS]}, sort_keys=False))
    (run / "40-synthesis" / "deduped-capabilities.yaml").write_text(
        yaml.safe_dump({"schema_version": 1, "capability": []}, sort_keys=False))
    (run / "40-threat-model" / "threat-model.findings.yaml").write_text(
        yaml.safe_dump({"schema_version": 1, "finding": [_TMEVAL]}, sort_keys=False))
    return run


# --- unit: _load_deduped unions tmeval-* (drives metrics + coverage) ---------


def test_load_deduped_unions_tmeval(tmp_path: pathlib.Path) -> None:
    run = _minimal_run(tmp_path)
    findings, _caps = _load_deduped(run)
    ids = {f["id"] for f in findings}
    assert "conf-13131313" in ids
    assert "tmeval-abcabc12" in ids, "tmeval-* must be unioned into the rollup corpus"


def test_metrics_count_includes_tmeval(tmp_path: pathlib.Path) -> None:
    run = _minimal_run(tmp_path)
    build_rollups(run)
    metrics = yaml.safe_load((run / "40-synthesis" / "metrics.yaml").read_text())
    assert metrics["findings_total"] == 2  # lens + tmeval
    assert metrics["byTier"]["auditability"] == 1  # the tmeval finding's tier


def test_nist_rollup_includes_tmeval_control(tmp_path: pathlib.Path) -> None:
    run = _minimal_run(tmp_path)
    build_rollups(run)
    nist = yaml.safe_load((run / "40-synthesis" / "nist-coverage.yaml").read_text())
    control_ids = {c.get("id") for c in nist.get("controls", [])}
    assert "AU-10" in control_ids, "the tmeval finding's NIST control must roll up"


# --- unit: loader exposes threat_model_findings -----------------------------


def test_loader_exposes_threat_model_findings(tmp_path: pathlib.Path) -> None:
    run = _minimal_run(tmp_path)
    # The minimal run lacks some required loader inputs (nist/attack/matrix/metrics);
    # build them first so load_run succeeds, then assert the tmeval finding is read.
    build_rollups(run)
    artifacts = load_run(run)
    ids = {f["id"] for f in artifacts.threat_model_findings}
    assert ids == {"tmeval-abcabc12"}


# --- unit: findings_array includes tmeval -----------------------------------


def test_findings_array_includes_tmeval() -> None:
    artifacts = RunArtifacts(
        run_id="r", framework_version="1", domain_pack_name="p",
        domain_pack_version="1", subject="s", date="2026-01-01",
        asset_inventory={}, deduped_findings=[_LENS], deduped_capabilities=[],
        contradictions=[], contradictions_notes=None, severity_disagreements=[],
        severity_disagreements_notes=None, nist_coverage={}, attack_exposure={},
        apd_coverage_matrix={}, attack_paths=None, asset_graph=None,
        defense_graph=None, attack_path_findings=[], report_data=None, metrics={},
        threat_model_findings=[_TMEVAL],
    )
    rows = findings_array(artifacts, headline_supplement=None)
    ids = {r["id"] for r in rows}
    assert "conf-13131313" in ids
    assert "tmeval-abcabc12" in ids, "the report findings list must include tmeval-*"


# --- integration: the shipped example golden carries tmeval -----------------


def test_example_golden_data_js_carries_tmeval_findings() -> None:
    artifacts = load_run(EXAMPLE)
    tmeval_ids = {f["id"] for f in artifacts.threat_model_findings}
    assert len(tmeval_ids) == 3, "the example ships 3 tmeval findings"
    data_js = (EXAMPLE / "40-synthesis" / "report-html" / "data.js").read_text()
    for fid in tmeval_ids:
        # Each tmeval id must appear as a finding record id in data.js (not only
        # as a finding_id reference). The findings array entries carry "id": "<fid>".
        assert f'"id": "{fid}"' in data_js, f"{fid} missing from data.js findings"
