"""check_maswe_masvs_consistency — WARN when a cited maswe's masvs_v2 parents
disagree with the finding's cited masvs ids."""
from __future__ import annotations

from apd_gauntlet import linters

# Synthetic parents index (mirrors taxonomy.maswe_masvs_parents()'s shape).
_PARENTS = {
    "MASWE-0001": ["MASVS-STORAGE-2"],
    "MASWE-0002": ["MASVS-STORAGE-1", "MASVS-CRYPTO-2"],
}


def test_consistent_pair_no_warning() -> None:
    """maswe parents fully covered by the cited masvs ids => no warning."""
    record = {"control_mappings": {"maswe": ["MASWE-0001"], "masvs": ["MASVS-STORAGE-2"]}}
    assert linters.check_maswe_masvs_consistency(record, _PARENTS) == []


def test_inconsistent_pair_warns() -> None:
    """A cited maswe whose masvs_v2 parent is NOT among the cited masvs ids => warn."""
    record = {"control_mappings": {"maswe": ["MASWE-0001"], "masvs": ["MASVS-CRYPTO-2"]}}
    warnings = linters.check_maswe_masvs_consistency(record, _PARENTS)
    assert len(warnings) == 1
    assert "MASWE-0001" in warnings[0]
    assert "MASVS-STORAGE-2" in warnings[0]  # the unmet parent is named


def test_no_masvs_cited_warns_with_expected_parents() -> None:
    """maswe cited but no masvs cited at all => warn (the parents are unmet)."""
    record = {"control_mappings": {"maswe": ["MASWE-0002"]}}
    warnings = linters.check_maswe_masvs_consistency(record, _PARENTS)
    assert len(warnings) == 1
    assert "MASWE-0002" in warnings[0]


def test_unknown_maswe_id_no_warning() -> None:
    """A maswe id absent from the parents index is not graded here (id_coverage owns it)."""
    record = {"control_mappings": {"maswe": ["MASWE-9999"], "masvs": ["MASVS-AUTH-1"]}}
    assert linters.check_maswe_masvs_consistency(record, _PARENTS) == []


def test_no_maswe_block_no_warning() -> None:
    assert linters.check_maswe_masvs_consistency({}, _PARENTS) == []
    assert linters.check_maswe_masvs_consistency(
        {"control_mappings": {"masvs": ["MASVS-STORAGE-2"]}}, _PARENTS) == []


def test_wired_into_semantic_pass_as_warning(tmp_path) -> None:
    """The check runs in run_semantic_pass on findings and lands in warnings, not errors."""
    import pathlib
    import shutil

    from apd_gauntlet import validate

    fixtures = pathlib.Path(__file__).parent / "fixtures" / "runs"
    dst = tmp_path / "run"
    shutil.copytree(fixtures / "clean-run", dst)
    f = dst / "10-trustworthiness" / "confidentiality.findings.yaml"
    text = f.read_text()
    assert "nist_800_53r5:" in text
    # Cite a maswe with a masvs parent that is NOT among the finding's masvs ids.
    text = text.replace(
        'nist_800_53r5: ["SC-8(1)", "SC-13", "SC-28(1)"]',
        'nist_800_53r5: ["SC-8(1)", "SC-13", "SC-28(1)"]\n'
        '    maswe: ["MASWE-0001"]\n'
        '    masvs: ["MASVS-CRYPTO-2"]',
        1,
    )
    f.write_text(text)
    report = validate.run_semantic_pass(dst)
    msgs = [v.message for v in report.warnings]
    assert any("MASWE-0001" in m and "masvs" in m.lower() for m in msgs), msgs
    # It is a warning, not a hard error.
    assert not any("MASWE-0001" in v.message for v in report.errors)
