"""Closeout summary line for domain-improvement opportunities (§9, §12)."""
from __future__ import annotations

import pathlib

from apd_gauntlet.summary import render_summary, summarize_run


def _run_with_doc(tmp_path, n: int | None) -> pathlib.Path:
    run_dir = tmp_path / "run"
    (run_dir / "40-synthesis").mkdir(parents=True)
    if n is not None:
        improvements = "\n".join(
            f"  - id: dimpr-0000000{i}\n"
            f"    improvement_type: missing_crown_jewel\n"
            f"    target_pack: pbm\n    target_file: domain.yaml\n"
            f"    source: deterministic\n    priority: high\n"
            f"    evidence:\n      - kind: asset_inventory\n        ref: asset-0000000{i}\n"
            f"    rationale: \"grounded gap number {i} in the run inventory data\"\n"
            f"    suggested_action: \"add crown jewel\"\n"
            f"    draft_snippet: \"- pattern: s{i}\\n  description: x\"\n"
            for i in range(n)
        )
        doc = (
            "schema_version: 1\ngenerated_by: domain-auditor\n"
            "examined_domains:\n  - pbm\nimprovements:\n" + (improvements if n else "  []\n")
        )
        (run_dir / "40-synthesis" / "domain-improvements.yaml").write_text(doc, encoding="utf-8")
    return run_dir


def test_summarize_counts_improvements(tmp_path):
    run_dir = _run_with_doc(tmp_path, 2)
    stats = summarize_run(run_dir)
    assert stats["domain_improvements"] == 2


def test_render_emits_line_for_nonzero(tmp_path):
    run_dir = _run_with_doc(tmp_path, 2)
    out = render_summary(summarize_run(run_dir))
    assert ("2 domain-improvement opportunities captured; run apd-gauntlet "
            "draft-domain-improvements <run> to draft pack edits.") in out


def test_render_emits_zero_variant(tmp_path):
    run_dir = _run_with_doc(tmp_path, 0)
    out = render_summary(summarize_run(run_dir))
    assert "0 domain-improvement opportunities captured." in out


def test_absent_artifact_does_not_error_and_omits_line(tmp_path):
    run_dir = _run_with_doc(tmp_path, None)  # no artifact at all
    stats = summarize_run(run_dir)
    assert stats["domain_improvements"] is None
    out = render_summary(stats)
    assert "domain-improvement opportunities" not in out
