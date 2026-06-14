"""Guards the committed C4 fixture: it must exist, be tracked (not under the
ignored runs/ tree), parse as YAML, and preserve the counts the downstream C4
milestones assert against (40 code anchors, 23 repos -> 14 with no anchors)."""
from __future__ import annotations

import pathlib

import yaml

REPO = pathlib.Path(__file__).resolve().parent.parent
FIX = REPO / "tests" / "fixtures" / "runs" / "c4-home-assistant"

REQUIRED = [
    ".apd-run.yaml",
    "00-context/code-evidence-index.yaml",
    "00-context/asset-inventory.yaml",
    "40-synthesis/asset-graph.yaml",
    "40-synthesis/deduped-findings.yaml",
    "40-synthesis/deduped-capabilities.yaml",
]


def test_all_required_artifacts_present_and_parse():
    for rel in REQUIRED:
        p = FIX / rel
        assert p.is_file(), f"missing fixture artifact: {rel}"
        yaml.safe_load(p.read_text())  # must parse


def test_fixture_is_not_under_the_ignored_runs_tree():
    # The fixture lives under tests/fixtures/runs/ (the .gitignore carve-out),
    # NOT the ignored top-level runs/ tree.
    assert FIX.is_relative_to(REPO / "tests" / "fixtures" / "runs")


def test_code_evidence_index_preserves_counts():
    doc = yaml.safe_load((FIX / "00-context" / "code-evidence-index.yaml").read_text())
    cei = doc["code_evidence_index"]
    entries = cei["entries"]
    repos = cei["repos"]
    code_kinds = {"function", "class", "route", "module"}
    code_anchors = [e for e in entries if e.get("kind") in code_kinds]
    assert len(code_anchors) == 40, f"expected 40 code anchors, got {len(code_anchors)}"
    assert len(repos) == 23, f"expected 23 repos, got {len(repos)}"
    repos_with_anchors = {e["repo"] for e in entries if "repo" in e}
    not_analyzed = [r for r in repos if r["cbm_project"] not in repos_with_anchors]
    assert len(not_analyzed) == 14, f"expected 14 not-analyzed repos, got {len(not_analyzed)}"


def test_findings_have_the_code_locators_the_badge_join_needs():
    doc = yaml.safe_load((FIX / "40-synthesis" / "deduped-findings.yaml").read_text())
    records = (
        doc
        if isinstance(doc, list)
        else doc.get("finding", doc.get("findings", doc.get("records", [])))
    )
    code_locs = 0
    for rec in records:
        for ev in (rec.get("evidence") or []):
            loc = str(ev.get("locator", ""))
            if loc.startswith("code:"):
                code_locs += 1
    assert code_locs >= 90, f"expected the ~97 code: locators for the badge join, got {code_locs}"
