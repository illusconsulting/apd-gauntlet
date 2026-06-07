# tests/unit/synthesis/test_metrics.py
"""Unit tests for compute_metrics — the single canonical report summary block."""
from __future__ import annotations

from apd_gauntlet.synthesis.metrics import compute_metrics


def _f(fid, severity="high", disposition="gap", tier="trustworthiness", **extra):
    return {"id": fid, "severity": severity, "disposition": disposition,
            "apd_tier": tier, **extra}


def test_severity_counts_normalize_informational_to_info():
    findings = [_f("a", "informational"), _f("b", "critical"), _f("apath-1", "high")]
    m = compute_metrics(findings, [], [], [])
    assert m["bySeverity"] == {"critical": 1, "high": 1, "medium": 0, "low": 0, "info": 1}
    assert m["findings_total"] == 3


def test_missing_severity_disposition_tier_default():
    m = compute_metrics([{"id": "x"}], [], [], [])
    assert m["bySeverity"]["info"] == 1          # missing severity -> info
    assert m["byDisposition"]["gap"] == 1        # missing disposition -> gap
    assert m["byTier"]["trustworthiness"] == 1   # missing apd_tier -> trustworthiness


def test_capability_maturity_and_cluster_counts():
    caps = [{"id": "cap-1", "maturity": "tested"},
            {"id": "cap-merged-1", "maturity": "implemented", "lens_perspectives": [{}]}]
    m = compute_metrics([], caps, [], [])
    assert m["capabilities_total"] == 2
    assert m["capabilitiesByMaturity"]["tested"] == 1
    assert m["cross_lens_merged_clusters"] == 1


def test_contradiction_and_disagreement_counts():
    m = compute_metrics([], [], [{"x": 1}, {"y": 2}], [{"z": 3}])
    assert m["contradictions"] == 2
    assert m["severity_disagreements"] == 1


def test_internal_consistency_invariants_hold():
    findings = [_f("a", "high", "gap", "trustworthiness"),
                _f("b", "low", "risk", "scalability"),
                _f("c", "informational", "blocked", "auditability")]
    m = compute_metrics(findings, [], [], [])
    t = m["findings_total"]
    assert sum(m["bySeverity"].values()) == t
    assert sum(m["byTier"].values()) == t
    assert (m["byDisposition"]["gap"] + m["byDisposition"]["risk"]
            + m["byDisposition"]["uncertainty"] + m["byDisposition"]["blocked"]) == t


def test_schema_version_present():
    assert compute_metrics([], [], [], [])["schema_version"] == 1


def test_cross_lens_merged_counts_merged_flag_branch():
    caps = [{"id": "cap-9", "merged": True},                       # merged-flag branch
            {"id": "cap-plain", "maturity": "designed"}]
    assert compute_metrics([], caps, [], [])["cross_lens_merged_clusters"] == 1


def test_linked_clusters_counts_findings_with_linked_perspectives():
    findings = [{"id": "a", "severity": "high", "linked_perspectives": [{"x": 1}]},
                {"id": "b", "severity": "low"}]
    assert compute_metrics(findings, [], [], [])["linked_clusters"] == 1


def test_pre_dedup_fields_mirror_totals():
    findings = [{"id": "a", "severity": "high"}]
    caps = [{"id": "c", "maturity": "tested"}]
    m = compute_metrics(findings, caps, [], [])
    assert m["findings_pre_dedup"] == m["findings_total"] == 1
    assert m["capabilities_pre_dedup"] == m["capabilities_total"] == 1


# --- PR3: cap-merged capabilities + linked findings AND capabilities ----------


def test_cross_lens_merged_counts_cap_merged_capability():
    """A real cap-merged-<sha8> capability with lens_perspectives is counted."""
    caps = [
        {"id": "cap-merged-abcd1234", "maturity": "tested",
         "lens_perspectives": {"at_rest": {"summary": "x", "detail": "y"}}},
        {"id": "conf-cap-11111111", "maturity": "implemented"},
    ]
    assert compute_metrics([], caps, [], [])["cross_lens_merged_clusters"] == 1


def test_linked_clusters_counts_findings_and_capabilities():
    """linked_clusters counts records with linked_perspectives across BOTH
    findings and capabilities (previously findings only)."""
    findings = [{"id": "conf-aaaaaaaa", "severity": "high",
                 "linked_perspectives": ["conf-bbbbbbbb"]},
                {"id": "conf-bbbbbbbb", "severity": "low",
                 "linked_perspectives": ["conf-aaaaaaaa"]}]
    caps = [{"id": "conf-cap-11111111", "maturity": "tested",
             "linked_perspectives": ["conf-cap-22222222"]},
            {"id": "conf-cap-22222222", "maturity": "tested"}]
    m = compute_metrics(findings, caps, [], [])
    assert m["linked_clusters"] == 3  # 2 findings + 1 capability


def test_unresolved_authored_merges_surfaced_in_metrics():
    """compute_metrics surfaces the unresolved_authored_merges count."""
    m = compute_metrics([], [], [], [], unresolved_authored_merges=2)
    assert m["unresolved_authored_merges"] == 2
    # Defaults to 0 when not supplied (backwards compatible).
    assert compute_metrics([], [], [], [])["unresolved_authored_merges"] == 0
