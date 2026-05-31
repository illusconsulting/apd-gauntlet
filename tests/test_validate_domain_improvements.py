"""Validate-wiring tests for the domain-improvements + coverage-delta artifacts."""
from __future__ import annotations

import pathlib

from apd_gauntlet.validate import SYNTHESIS_ROLLUPS, run_cross_file_pass, run_schema_pass


def _run_with(tmp_path, **synth_files: str) -> pathlib.Path:
    run_dir = tmp_path / "run"
    synth = run_dir / "40-synthesis"
    synth.mkdir(parents=True)
    for name, text in synth_files.items():
        (synth / name).write_text(text, encoding="utf-8")
    return run_dir


def test_rollups_dict_has_both_new_entries():
    assert SYNTHESIS_ROLLUPS["domain-improvements.yaml"] == "domain-improvements-doc.schema.json"
    assert (
        SYNTHESIS_ROLLUPS["domain-coverage-delta.yaml"] == "domain-coverage-delta-doc.schema.json"
    )


_GOOD_DOC = """\
schema_version: 1
generated_by: domain-auditor
examined_domains:
  - pbm
improvements:
  - id: dimpr-1a2b3c4d
    improvement_type: missing_crown_jewel
    target_pack: pbm
    target_file: domain.yaml
    source: deterministic
    priority: high
    evidence:
      - kind: asset_inventory
        ref: asset-1a2b3c4d
    rationale: "The run exercised a data store no selected pack declares."
    suggested_action: "add a crown jewel to pbm/domain.yaml"
    draft_snippet: |
      - pattern: novel_store
        description: "A store grounded in the run inventory."
"""

_BAD_DOC = """\
schema_version: 1
generated_by: domain-auditor
examined_domains:
  - pbm
improvements:
  - id: dimpr-BADID
    improvement_type: not_a_type
    target_pack: pbm
    target_file: domain.yaml
    source: deterministic
    priority: high
    evidence: []
    rationale: short
    suggested_action: short
    draft_snippet: ""
"""


def test_schema_pass_accepts_good_improvements_doc(tmp_path):
    run_dir = _run_with(tmp_path, **{"domain-improvements.yaml": _GOOD_DOC})
    report = run_schema_pass(run_dir)
    assert report.is_clean, report.render()


def test_schema_pass_rejects_bad_improvements_doc(tmp_path):
    run_dir = _run_with(tmp_path, **{"domain-improvements.yaml": _BAD_DOC})
    report = run_schema_pass(run_dir)
    assert not report.is_clean


def _run_with_corpus(
    tmp_path, improvements_doc: str, *, inventory: str, findings: str | None = None
):
    run_dir = tmp_path / "run"
    synth = run_dir / "40-synthesis"
    ctx = run_dir / "00-context"
    synth.mkdir(parents=True)
    ctx.mkdir(parents=True)
    (synth / "domain-improvements.yaml").write_text(improvements_doc, encoding="utf-8")
    (ctx / "asset-inventory.yaml").write_text(inventory, encoding="utf-8")
    if findings is not None:
        (synth / "deduped-findings.yaml").write_text(findings, encoding="utf-8")
    return run_dir


_INV = """\
schema_version: 1
generated_by: intake
assets:
  - asset_id: asset-1a2b3c4d
    name: novel_store
    asset_type: data_store
    provenance: { source: artifact }
    confidence: high
identities: []
trust_boundaries: []
"""


def _doc_with_ref(itype, pack, tfile, kind, ref):
    from apd_gauntlet.linters import compute_improvement_id
    rid = compute_improvement_id(itype, pack, tfile, ref)
    return f"""\
schema_version: 1
generated_by: domain-auditor
examined_domains:
  - pbm
improvements:
  - id: {rid}
    improvement_type: {itype}
    target_pack: {pack}
    target_file: {tfile}
    source: deterministic
    priority: high
    evidence:
      - kind: {kind}
        ref: {ref}
    rationale: "The run exercised something no selected pack declares fully."
    suggested_action: "add the missing item to the pack"
    draft_snippet: |
      - pattern: novel_store
        description: "grounded in the run inventory"
"""


def test_cross_file_accepts_resolving_asset_ref(tmp_path):
    doc = _doc_with_ref(
        "missing_crown_jewel", "pbm", "domain.yaml", "asset_inventory", "asset-1a2b3c4d"
    )
    run_dir = _run_with_corpus(tmp_path, doc, inventory=_INV)
    report = run_cross_file_pass(run_dir)
    assert report.is_clean, report.render()


def test_cross_file_rejects_dangling_asset_ref(tmp_path):
    doc = _doc_with_ref(
        "missing_crown_jewel", "pbm", "domain.yaml", "asset_inventory", "asset-deadbeef"
    )
    run_dir = _run_with_corpus(tmp_path, doc, inventory=_INV)
    report = run_cross_file_pass(run_dir)
    assert not report.is_clean
    assert any("asset-deadbeef" in v.message for v in report.errors)


def test_cross_file_rejects_dangling_finding_ref(tmp_path):
    doc = _doc_with_ref(
        "missing_severity_clause", "pbm", "severity-rubric.md", "finding", "conf-deadbeef"
    )
    run_dir = _run_with_corpus(tmp_path, doc, inventory=_INV, findings="finding: []\n")
    report = run_cross_file_pass(run_dir)
    assert not report.is_clean
    assert any("conf-deadbeef" in v.message for v in report.errors)


def test_cross_file_recomputes_dimpr_id(tmp_path):
    tampered = """\
schema_version: 1
generated_by: domain-auditor
examined_domains:
  - pbm
improvements:
  - id: dimpr-deadbeef
    improvement_type: missing_crown_jewel
    target_pack: pbm
    target_file: domain.yaml
    source: deterministic
    priority: high
    evidence:
      - kind: asset_inventory
        ref: asset-1a2b3c4d
    rationale: "The id below does not match the deterministic recomputation."
    suggested_action: "add the missing item to the pack"
    draft_snippet: |
      - pattern: novel_store
        description: "grounded in the run inventory"
"""
    run_dir = _run_with_corpus(tmp_path, tampered, inventory=_INV)
    report = run_cross_file_pass(run_dir)
    assert not report.is_clean
    assert any("id mismatch" in v.message for v in report.errors)


def test_cross_file_resolves_merged_finding_ref_from_deduped(tmp_path):
    """A merged-<sha8> id lives ONLY in 40-synthesis/deduped-findings.yaml (the
    decomposed apply path writes no merged.findings.yaml), which does NOT match the
    *.findings.yaml glob _iter_records walks. The validator must union in the
    deduped-findings corpus, else a legitimate merged-* evidence ref false-positives
    as 'not found in run corpus'. This pins that union (§4.3 / Issue: merged-* refs)."""
    doc = _doc_with_ref(
        "missing_severity_clause", "pbm", "severity-rubric.md", "finding", "merged-44bdb663"
    )
    deduped = """\
finding:
  - id: merged-44bdb663
    schema_version: 1
"""
    run_dir = _run_with_corpus(tmp_path, doc, inventory=_INV, findings=None)
    (run_dir / "40-synthesis" / "deduped-findings.yaml").write_text(deduped, encoding="utf-8")
    report = run_cross_file_pass(run_dir)
    assert report.is_clean, report.render()
