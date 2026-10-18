"""N20: ``metrics.yaml`` reports real pre-dedup counts.

``build_rollups`` passes ``compute_metrics`` the number of records in the tier
directories' ``*.findings.yaml`` and ``*.capabilities.yaml``, so
``findings_pre_dedup`` and ``capabilities_pre_dedup`` count the records before
apply-clusters merged any, and ``findings_total`` and ``capabilities_total``
the records after. The tier-4 findings (``apath-*``, ``tmeval-*``) never pass
through dedup and are part of ``findings_total``, so they count on both sides.
"""
from __future__ import annotations

import pathlib
import shutil
from typing import Any

import jsonschema
import pytest
import yaml
from apd_gauntlet.synthesis.apply import apply_clusters
from apd_gauntlet.synthesis.metrics import compute_metrics
from apd_gauntlet.synthesis.rollup import build_rollups
from apd_gauntlet.validate import build_registry

REPO = pathlib.Path(__file__).parent.parent
EXAMPLES = REPO / "examples"
METRICS_SCHEMA = "https://github.com/illusconsulting/apd-gauntlet/schemas/metrics.schema.json"


def _validate_metrics(doc: dict[str, Any]) -> None:
    registry = build_registry()
    schema = registry.contents(METRICS_SCHEMA)
    jsonschema.Draft202012Validator(schema, registry=registry).validate(doc)


def _finding(fid: str, agent: str, tier: str, title: str, locator: str) -> dict[str, Any]:
    return {
        "schema_version": 1, "id": fid, "agent": agent, "apd_tier": tier,
        "apd_goal": agent, "disposition": "gap", "severity": "high", "confidence": "high",
        "title": title,
        "summary": f"{title} summary for the pre-dedup count test.",
        "detail": f"{title} detail for the pre-dedup count test.",
        "evidence": [{"artifact": "tech_plan.md", "locator": locator,
                      "excerpt": "no WORM enforcement"}],
        "control_mappings": {"nist_800_53r5": ["AU-9"]},
    }


def _capability(cid: str, scope: str, locator: str) -> dict[str, Any]:
    return {
        "schema_version": 1, "id": cid, "agent": "confidentiality",
        "apd_tier": "trustworthiness", "apd_goal": "confidentiality",
        "maturity": "implemented", "confidence": "high",
        "title": f"Encryption capability covering {scope}",
        "description": f"Encryption is in place and exercised for {scope}.",
        "scope": scope,
        "evidence": [{"artifact": "tech_plan.md", "locator": locator,
                      "excerpt": "encryption enforced"}],
        "control_mappings": {"nist_800_53r5": ["SC-28"]},
    }


NONREP = _finding("nonrep-62124087", "non_repudiation", "auditability",
                  "Audit log entries carry no signature", "§5.2")
IMMUT = _finding("immut-e09e4945", "immutability", "auditability",
                 "Audit log table has no write-once protection", "§5.2")
CAP_A = _capability("conf-cap-11111111", "PHI columns at rest", "§5.1")
CAP_B = _capability("conf-cap-22222222", "PHI on every transport hop", "§5.3")
APATH = _finding("apath-0a0a0a0a", "attack_path", "trustworthiness",
                 "Attack path reaches the audit log", "§6.1")
TMEVAL = _finding("tmeval-0b0b0b0b", "threat_model_evaluator", "auditability",
                  "Threat model omits audit log tampering", "§6.2")

FINDING_MERGE = {
    "group_id": "cluster-cand-0001", "decision": "merge",
    "merged_title": "Audit log is unsigned and stored in a mutable table",
    "merged_summary": "The audit log lacks both signing and storage-layer immutability.",
    "merged_detail": "Both lenses identified this risk from complementary angles.",
    "lens_perspectives": {
        "non_repudiation": {"summary": "Unsigned entries.", "detail": "No signature."},
        "immutability": {"summary": "Mutable table.", "detail": "No write-once storage."},
    },
}
CAPABILITY_MERGE = {
    "group_id": "cluster-cap-0001", "decision": "merge",
    "merged_title": "PHI is encrypted at rest and in transit end to end",
    "merged_summary": "Encryption at rest plus TLS in transit cover PHI.",
    "merged_detail": "Both capabilities confirm complementary PHI protection layers.",
    "lens_perspectives": {
        "at_rest": {"summary": "At rest.", "detail": "Column encryption."},
        "in_transit": {"summary": "In transit.", "detail": "TLS on every hop."},
    },
}
MEMBERS = {
    "cluster-cand-0001": [NONREP["id"], IMMUT["id"]],
    "cluster-cap-0001": [CAP_A["id"], CAP_B["id"]],
}


def _write(path: pathlib.Path, key: str, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump({"schema_version": 1, key: records}, sort_keys=False),
                    encoding="utf-8")


def _scaffold(tmp_path: pathlib.Path, decisions: list[dict[str, Any]]) -> pathlib.Path:
    """A run with two lens findings and two lens capabilities in the tier directories."""
    run = tmp_path / "run"
    (run / "00-context").mkdir(parents=True)
    (run / "40-synthesis").mkdir()
    (run / ".apd-run.yaml").write_text("run_id: t\ndomains: [pbm]\n", encoding="utf-8")
    (run / "00-context" / "asset-inventory.yaml").write_text(
        "schema_version: 1\ngenerated_by: intake\nassets: []\nidentities: []\n"
        "trust_boundaries: []\n", encoding="utf-8")
    _write(run / "30-auditability" / "non_repudiation.findings.yaml", "finding", [NONREP])
    _write(run / "30-auditability" / "immutability.findings.yaml", "finding", [IMMUT])
    _write(run / "10-trustworthiness" / "confidentiality.capabilities.yaml", "capability",
           [CAP_A, CAP_B])
    (run / "40-synthesis" / "cluster-decisions.yaml").write_text(yaml.safe_dump({
        "schema_version": 1, "generated_by": "apd-cluster-adjudicator",
        "decisions": decisions, "contradictions": [], "_members": MEMBERS,
    }, sort_keys=False), encoding="utf-8")
    return run


def _write_tier4(run: pathlib.Path) -> None:
    _write(run / "40-synthesis" / "attack-path.findings.yaml", "finding", [APATH])
    _write(run / "40-threat-model" / "threat-model.findings.yaml", "finding", [TMEVAL])


def _metrics(run: pathlib.Path) -> dict[str, Any]:
    build_rollups(run)
    doc = yaml.safe_load((run / "40-synthesis" / "metrics.yaml").read_text(encoding="utf-8"))
    _validate_metrics(doc)
    return doc


def _deduped(run: pathlib.Path, name: str, key: str) -> list[dict[str, Any]]:
    doc = yaml.safe_load((run / "40-synthesis" / name).read_text(encoding="utf-8"))
    return list(doc[key])


# --- build_rollups: the run's real counts -------------------------------------


def test_two_lens_findings_merged_into_one(tmp_path):
    run = _scaffold(tmp_path, [FINDING_MERGE])
    apply_clusters(run)
    assert len(_deduped(run, "deduped-findings.yaml", "finding")) == 1
    m = _metrics(run)
    assert m["findings_pre_dedup"] == 2
    assert m["findings_total"] == 1


def test_two_lens_capabilities_merged_into_one(tmp_path):
    run = _scaffold(tmp_path, [CAPABILITY_MERGE])
    apply_clusters(run)
    assert len(_deduped(run, "deduped-capabilities.yaml", "capability")) == 1
    m = _metrics(run)
    assert m["capabilities_pre_dedup"] == 2
    assert m["capabilities_total"] == 1
    assert m["findings_pre_dedup"] == m["findings_total"] == 2


def test_run_without_merges_counts_the_same_on_both_sides(tmp_path):
    run = _scaffold(tmp_path, [])
    apply_clusters(run)
    m = _metrics(run)
    assert m["findings_pre_dedup"] == m["findings_total"] == 2
    assert m["capabilities_pre_dedup"] == m["capabilities_total"] == 2


@pytest.mark.parametrize("tier4_before_apply", [False, True],
                         ids=["tier4-after-apply", "tier4-before-apply"])
def test_tier4_findings_count_before_dedup_too(tmp_path, tier4_before_apply):
    """apath-*/tmeval-* findings are in findings_total, so they count before dedup as well.

    The workflow writes them after apply-clusters, and the rollup unions them in. A
    recovery re-run can find 40-threat-model/ already there, so apply-clusters folds the
    tmeval-* finding into deduped-findings.yaml; it still counts once on each side.
    """
    run = _scaffold(tmp_path, [FINDING_MERGE])
    if tier4_before_apply:
        _write_tier4(run)
    apply_clusters(run)
    if not tier4_before_apply:
        _write_tier4(run)
    m = _metrics(run)
    assert m["findings_total"] == 3  # merged lens finding + apath + tmeval
    assert m["findings_pre_dedup"] == 4  # two lens findings + apath + tmeval


def test_records_in_both_root_key_forms_and_nested_files_count(tmp_path):
    """The count reads the files as load_corpus does: singular or legacy plural root
    key, a single record or a list, and files below a tier directory too."""
    run = _scaffold(tmp_path, [])
    _write(run / "20-scalability" / "resilient.findings.yaml", "findings",
           [_finding("resil-0c0c0c0c", "resilient", "scalability", "Single broker", "§7")])
    nested = run / "20-scalability" / "extra" / "ephemeral.findings.yaml"
    nested.parent.mkdir(parents=True)
    nested.write_text(yaml.safe_dump({"schema_version": 1, "finding": _finding(
        "ephem-0d0d0d0d", "ephemeral", "scalability", "Long-lived tokens", "§8")},
        sort_keys=False), encoding="utf-8")
    apply_clusters(run)
    m = _metrics(run)
    assert m["findings_total"] == 4
    assert m["findings_pre_dedup"] == 4


def test_committed_example_counts_a_merge_and_its_tier4_findings(tmp_path):
    """claim-event-bus: 16 lens findings, one merge of two, and 4 tier-4 findings."""
    run = tmp_path / "run"
    shutil.copytree(EXAMPLES / "apd-20260601-claim-event-bus" / "expected", run)
    m = _metrics(run)
    assert (m["findings_pre_dedup"], m["findings_total"]) == (20, 19)
    assert (m["capabilities_pre_dedup"], m["capabilities_total"]) == (10, 10)


@pytest.mark.parametrize("example", sorted(p.parent.name for p in EXAMPLES.glob("*/expected")))
def test_committed_examples_never_count_fewer_before_dedup(tmp_path, example):
    run = tmp_path / "run"
    shutil.copytree(EXAMPLES / example / "expected", run)
    m = _metrics(run)
    assert m["findings_pre_dedup"] >= m["findings_total"]
    assert m["capabilities_pre_dedup"] >= m["capabilities_total"]


# --- compute_metrics: the keyword-only counts ---------------------------------


def test_compute_metrics_reports_the_given_counts():
    m = compute_metrics([NONREP], [CAP_A], [], [],
                        findings_pre_dedup=5, capabilities_pre_dedup=3)
    assert (m["findings_pre_dedup"], m["findings_total"]) == (5, 1)
    assert (m["capabilities_pre_dedup"], m["capabilities_total"]) == (3, 1)
    _validate_metrics(m)


@pytest.mark.parametrize("kwargs", [{}, {"findings_pre_dedup": None,
                                         "capabilities_pre_dedup": None}])
def test_compute_metrics_none_keeps_the_deduped_length(kwargs):
    m = compute_metrics([NONREP, IMMUT], [CAP_A], [], [], **kwargs)
    assert m["findings_pre_dedup"] == m["findings_total"] == 2
    assert m["capabilities_pre_dedup"] == m["capabilities_total"] == 1


def test_compute_metrics_counts_are_independent():
    m = compute_metrics([NONREP], [CAP_A, CAP_B], [], [], findings_pre_dedup=4)
    assert m["findings_pre_dedup"] == 4
    assert m["capabilities_pre_dedup"] == 2
    m = compute_metrics([NONREP], [CAP_A, CAP_B], [], [], capabilities_pre_dedup=6)
    assert m["findings_pre_dedup"] == 1
    assert m["capabilities_pre_dedup"] == 6


def test_compute_metrics_counts_are_keyword_only():
    with pytest.raises(TypeError):
        compute_metrics([], [], [], [], 0, 3)


def test_compute_metrics_keeps_the_key_order():
    """metrics.yaml is written with sort_keys=False; the two keys stay where they were."""
    keys = list(compute_metrics([], [], [], [], findings_pre_dedup=1,
                                capabilities_pre_dedup=1))
    assert keys.index("findings_pre_dedup") == keys.index("findings_total") + 1
    assert keys.index("capabilities_pre_dedup") == keys.index("capabilities_total") + 1
