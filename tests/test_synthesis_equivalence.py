"""Decomposed pipeline reproduces the example golden (normalized-content comparison).

Byte-equivalence is impossible (the golden carries author comment banners and a
fixed ordering); instead we project both sides to stable semantic keys and diff.

The merge sources nonrep-62124087 + immut-e09e4945 ALREADY EXIST in the example
tier files (30-auditability/{non_repudiation,immutability}.findings.yaml), so we
re-merge the REAL records — no synthetic un-merge, no double-counted ids. We do
NOT pin the exact golden id merged-4dd83f6a (its sha8 depends on the synthesizer's
member-order-dependent first-evidence locator, which is not a deterministic
equivalence target). The matrix is excluded from the projection per I1.
"""
from __future__ import annotations

import pathlib
import shutil

import yaml
from apd_gauntlet.synthesis.apply import apply_clusters
from apd_gauntlet.synthesis.rollup import build_rollups

REPO = pathlib.Path(__file__).parent.parent
EXAMPLE = REPO / "examples" / "apd-20260601-claim-event-bus" / "expected"
DECISIONS_FIXTURE = (
    REPO / "tests" / "fixtures" / "cluster_decisions" / "example-cluster-decisions.yaml"
)


def _merged_record(findings):
    """The single synthesizer-built merge in the produced findings."""
    merged = [f for f in findings if f.get("agent") == "synthesizer"]
    assert len(merged) == 1, [f.get("id") for f in merged]
    return merged[0]


def _project_nist(controls):
    return {c["id"]: {"finding_ids": sorted(c["finding_ids"]),
                      "capability_ids": sorted(c["capability_ids"]), "posture": c["posture"]}
            for c in controls}


def test_apply_clusters_reproduces_merged_record_semantics(tmp_path):
    run = tmp_path / "run"
    shutil.copytree(EXAMPLE, run)
    # Drop the golden deduped output so apply-clusters rebuilds it from the REAL
    # tier corpus (the two merge sources are already in 30-auditability/).
    (run / "40-synthesis" / "deduped-findings.yaml").unlink()
    (run / "40-synthesis" / "deduped-capabilities.yaml").unlink()
    shutil.copy2(DECISIONS_FIXTURE, run / "40-synthesis" / "cluster-decisions.yaml")
    result = apply_clusters(run)

    # Key the merged record by agent=='synthesizer' (NOT the exact sha8 id).
    m = _merged_record(result.findings)
    # merged_from is the sorted real source ids.
    assert m["merged_from"] == sorted(["nonrep-62124087", "immut-e09e4945"])
    # Adjudicator chosen_severity wins.
    assert m["severity"] == "critical"
    # Sorted union of the two REAL sources' NIST controls. Python's sorted() yields
    # ["AU-10", "AU-9", "AU-9(2)", "AU-9(3)"] (lexical: '1' < '9' at position 3) — matching
    # Task 5's assertion. The golden YAML stores the natural order
    # ["AU-9","AU-9(2)","AU-9(3)","AU-10"]; the golden-vs-produced compare below
    # re-sorts both sides, so it is order-agnostic.
    assert sorted(m["control_mappings"]["nist_800_53r5"]) == ["AU-10", "AU-9", "AU-9(2)", "AU-9(3)"]
    assert set(m["lens_perspectives"].keys()) == {"non_repudiation", "immutability"}
    # The two sources no longer appear as standalone findings.
    fids = {f["id"] for f in result.findings}
    assert "nonrep-62124087" not in fids and "immut-e09e4945" not in fids
    # The golden merged record carries the SAME merged_from + severity + NIST union.
    golden_doc = (EXAMPLE / "40-synthesis" / "deduped-findings.yaml").read_text()
    golden = yaml.safe_load(golden_doc)["finding"]
    gm = next(f for f in golden if f.get("agent") == "synthesizer")
    assert sorted(gm["merged_from"]) == m["merged_from"]
    assert gm["severity"] == m["severity"]
    gm_nist = sorted(gm["control_mappings"]["nist_800_53r5"])
    m_nist = sorted(m["control_mappings"]["nist_800_53r5"])
    assert gm_nist == m_nist


def test_rollup_reproduces_nist_projection(tmp_path):
    run = tmp_path / "run"
    shutil.copytree(EXAMPLE, run)
    build_rollups(run)  # rolls up directly over the committed deduped golden + apath
    produced = _project_nist(
        yaml.safe_load((run / "40-synthesis" / "nist-coverage.yaml").read_text())["controls"])
    golden = _project_nist(
        yaml.safe_load((EXAMPLE / "40-synthesis" / "nist-coverage.yaml").read_text())["controls"])
    # Every golden control's finding/capability set + posture is reproduced.
    for cid, proj in golden.items():
        assert cid in produced, f"rollup dropped control {cid}"
        assert produced[cid] == proj, f"control {cid} projection differs"
