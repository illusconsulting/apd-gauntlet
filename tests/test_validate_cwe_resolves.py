"""G6 — CWE-resolves guardrail.

A finding's ``control_mappings.cwe`` entries must resolve to a CONCRETE node in
the bundled CWE catalog. ERROR when an id is ABSENT from the catalog OR has an
``abstraction`` of ``category`` / ``pillar`` (too coarse to be actionable). A
``base`` / ``class`` / ``variant`` / ``compound`` id is acceptable.

The check is wired into the Pass-2 semantic pass so it fires at the tier gate
(``validate --tier``), not only the late report-audit.
"""
from __future__ import annotations

import pathlib
import shutil

from apd_gauntlet import linters
from apd_gauntlet.cli import main
from apd_gauntlet.report import taxonomy
from click.testing import CliRunner

FIXTURES = pathlib.Path(__file__).parent / "fixtures" / "runs"


def _copy_clean_run(tmp_path: pathlib.Path) -> pathlib.Path:
    dst = tmp_path / "run"
    shutil.copytree(FIXTURES / "clean-run", dst)
    return dst


# ---------------------------------------------------------------------------
# Unit: the taxonomy accessor exposes {cwe_id: abstraction}
# ---------------------------------------------------------------------------


def test_cwe_abstractions_accessor_shape() -> None:
    """cwe_abstractions() returns {CWE-NNN: abstraction} from the bundled catalog."""
    abstractions = taxonomy.cwe_abstractions()
    assert isinstance(abstractions, dict)
    # CWE-79 (XSS) is a concrete base weakness in the catalog.
    assert abstractions.get("CWE-79") == "base"
    # CWE-840 is the catalog's sole 'category' entry (Business Logic Errors).
    assert abstractions.get("CWE-840") == "category"


# ---------------------------------------------------------------------------
# Unit: check_cwe_resolves(record, cwe_index)
# ---------------------------------------------------------------------------


def _index() -> dict[str, str]:
    return taxonomy.cwe_abstractions()


def test_concrete_base_cwe_ok() -> None:
    """CWE-79 (base) → no error."""
    record = {"control_mappings": {"cwe": ["CWE-79"]}}
    assert linters.check_cwe_resolves(record, _index()) == []


def test_category_cwe_errors() -> None:
    """A category-abstraction CWE → error mentioning the abstraction."""
    # CWE-840 is the catalog's category entry.
    record = {"control_mappings": {"cwe": ["CWE-840"]}}
    errors = linters.check_cwe_resolves(record, _index())
    assert len(errors) == 1
    assert "CWE-840" in errors[0]
    assert "category" in errors[0].lower()


def test_pillar_cwe_errors() -> None:
    """A pillar-abstraction CWE → error mentioning the abstraction."""
    # CWE-284 (Improper Access Control) is a pillar.
    record = {"control_mappings": {"cwe": ["CWE-284"]}}
    errors = linters.check_cwe_resolves(record, _index())
    assert len(errors) == 1
    assert "CWE-284" in errors[0]
    assert "pillar" in errors[0].lower()


def test_absent_cwe_errors() -> None:
    """A CWE id not present in the bundled catalog → error."""
    record = {"control_mappings": {"cwe": ["CWE-9999999"]}}
    errors = linters.check_cwe_resolves(record, _index())
    assert len(errors) == 1
    assert "CWE-9999999" in errors[0]
    # CWE-320 is documented as a Category but is also absent from this catalog —
    # either way it must error (the task's CWE-320 example).
    record2 = {"control_mappings": {"cwe": ["CWE-320"]}}
    assert linters.check_cwe_resolves(record2, _index()) != []


def test_class_and_variant_cwe_ok() -> None:
    """class / variant abstractions are concrete enough → no error."""
    # CWE-287 is a class, CWE-5 is a variant.
    record = {"control_mappings": {"cwe": ["CWE-287", "CWE-5"]}}
    assert linters.check_cwe_resolves(record, _index()) == []


def test_multiple_bad_cwes_each_error() -> None:
    """Each offending id yields its own error message."""
    record = {"control_mappings": {"cwe": ["CWE-840", "CWE-79", "CWE-9999999"]}}
    errors = linters.check_cwe_resolves(record, _index())
    assert len(errors) == 2  # CWE-840 (category) + CWE-9999999 (absent); CWE-79 ok


def test_no_cwe_block_ok() -> None:
    """No control_mappings / no cwe key → no error (vacuously fine)."""
    assert linters.check_cwe_resolves({}, _index()) == []
    assert linters.check_cwe_resolves({"control_mappings": {}}, _index()) == []
    assert linters.check_cwe_resolves(
        {"control_mappings": {"cwe": []}}, _index()
    ) == []


# ---------------------------------------------------------------------------
# Integration: a category CWE in a finding fails `validate` at the tier gate
# ---------------------------------------------------------------------------


def test_category_cwe_fails_validate(tmp_path: pathlib.Path) -> None:
    """A finding citing a category CWE makes `validate` exit 1."""
    dst = _copy_clean_run(tmp_path)
    f = dst / "10-trustworthiness" / "confidentiality.findings.yaml"
    text = f.read_text()
    assert "nist_800_53r5:" in text  # guard against a no-op edit
    # Add a category CWE (CWE-840) to the first finding's control_mappings.
    text = text.replace(
        'nist_800_53r5: ["SC-8(1)", "SC-13", "SC-28(1)"]',
        'nist_800_53r5: ["SC-8(1)", "SC-13", "SC-28(1)"]\n    cwe: ["CWE-840"]',
        1,
    )
    f.write_text(text)
    runner = CliRunner()
    result = runner.invoke(main, ["validate", str(dst)])
    assert result.exit_code == 1
    assert "CWE-840" in result.output


def test_category_cwe_fails_validate_tier_gate(tmp_path: pathlib.Path) -> None:
    """The check is reachable via `validate --tier` (semantic pass), not only
    the full run."""
    dst = _copy_clean_run(tmp_path)
    f = dst / "10-trustworthiness" / "confidentiality.findings.yaml"
    text = f.read_text()
    text = text.replace(
        'nist_800_53r5: ["SC-8(1)", "SC-13", "SC-28(1)"]',
        'nist_800_53r5: ["SC-8(1)", "SC-13", "SC-28(1)"]\n    cwe: ["CWE-840"]',
        1,
    )
    f.write_text(text)
    runner = CliRunner()
    result = runner.invoke(main, ["validate", str(dst), "--tier", "10-trustworthiness"])
    assert result.exit_code == 1
    assert "CWE-840" in result.output


def test_concrete_cwe_passes_validate(tmp_path: pathlib.Path) -> None:
    """A finding citing a concrete (base) CWE keeps `validate` clean."""
    dst = _copy_clean_run(tmp_path)
    f = dst / "10-trustworthiness" / "confidentiality.findings.yaml"
    text = f.read_text()
    text = text.replace(
        'nist_800_53r5: ["SC-8(1)", "SC-13", "SC-28(1)"]',
        'nist_800_53r5: ["SC-8(1)", "SC-13", "SC-28(1)"]\n    cwe: ["CWE-79"]',
        1,
    )
    f.write_text(text)
    runner = CliRunner()
    result = runner.invoke(main, ["validate", str(dst)])
    assert result.exit_code == 0, result.output
