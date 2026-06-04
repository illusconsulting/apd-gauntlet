"""Regression tests for per-section isolation in build_apd_data (PR-T2-C).

After PR-T2-C, one bad finding / bad capability / corrupt asset graph must
not block the entire HTML report. Each top-level section in build_apd_data
is wrapped in a try/except; failures are recorded in
``data.meta.section_errors`` and the section is filled with a safe placeholder.
The orchestrator only raises ``ReportBuildError`` when the meta layer itself
cannot be assembled.
"""
from __future__ import annotations

import json
import pathlib
from unittest.mock import MagicMock

from apd_gauntlet.report.build import ReportBuildError, build_report
from apd_gauntlet.report.transform import build_apd_data

REPO = pathlib.Path(__file__).resolve().parents[3]


def _make_minimal_artifacts() -> MagicMock:
    """Build a RunArtifacts-shaped mock with every field populated to a benign
    default. Each transform section receives valid (if empty) inputs so the
    baseline run records zero section errors.
    """
    a = MagicMock()
    a.run_id = "test-run"
    a.subject = "test"
    a.date = "2026-05-29"
    a.framework_version = "1.5.0"
    a.domain_pack_name = "pbm"
    a.domain_pack_version = "1.0.0"
    a.run_crown_jewels = []
    a.run_attacker_positions = []
    a.asset_inventory = {}
    a.report_data = {}
    a.deduped_findings = []
    a.attack_path_findings = []
    a.deduped_capabilities = []
    a.nist_coverage = {}
    a.attack_exposure = {}
    a.apd_coverage_matrix = {}
    a.contradictions = []
    a.contradictions_notes = None
    a.severity_disagreements = []
    a.severity_disagreements_notes = None
    a.attack_paths = None
    a.asset_graph = None
    a.defense_graph = None
    return a


def test_build_apd_data_emits_empty_section_errors_on_clean_input() -> None:
    """Baseline: a clean minimal artifacts bundle records zero section errors."""
    artifacts = _make_minimal_artifacts()
    data = build_apd_data(artifacts)
    assert "section_errors" in data["meta"]
    assert data["meta"]["section_errors"] == {}


def test_build_apd_data_isolates_single_bad_finding() -> None:
    """A finding that crashes findings_array must not block other sections.

    ``deduped_findings`` is consumed by ``findings_array`` (via the ``+``
    operator with ``attack_path_findings``). A custom non-list iterable that
    raises from ``__add__`` triggers a fault inside findings_array without
    impacting independent sections like ``nist_rollup``, ``apd_matrix``, or
    ``taxonomy``. Note: ``summary_rollup`` also concatenates findings so it
    will fail too — that's expected per-section isolation behaviour.
    """
    artifacts = _make_minimal_artifacts()

    class BombList:
        def __add__(self, _other):
            raise TypeError("simulated finding shape error")

        def __radd__(self, _other):
            raise TypeError("simulated finding shape error")

        def __iter__(self):
            raise TypeError("simulated finding shape error")

    artifacts.deduped_findings = BombList()
    data = build_apd_data(artifacts)
    # findings section should carry the error.
    assert "findings" in data["meta"]["section_errors"]
    assert "simulated finding shape error" in data["meta"]["section_errors"]["findings"]
    # Independent sections still render with real values (not placeholders).
    assert "nist_rollup" in data
    assert "taxonomy" in data
    assert data["nist_rollup"] == []  # empty input -> empty rollup, not placeholder
    # findings itself should be the empty-list placeholder.
    assert data["findings"] == []


def test_build_apd_data_isolates_bad_nist_coverage() -> None:
    """Crashing nist_rollup must not block findings."""
    artifacts = _make_minimal_artifacts()

    class BombDict:
        def get(self, *_a, **_kw):
            raise RuntimeError("simulated nist shape error")

    artifacts.nist_coverage = BombDict()
    data = build_apd_data(artifacts)
    assert "nist_rollup" in data["meta"]["section_errors"]
    # nist_rollup placeholder is an empty list.
    assert data["nist_rollup"] == []
    # Findings still render — they don't depend on nist_coverage.
    assert isinstance(data["findings"], list)


def test_build_apd_data_isolates_bad_capabilities() -> None:
    """A capability that crashes capability_grid must not block findings/nist."""
    artifacts = _make_minimal_artifacts()

    class BombCaps(list):  # type: ignore[type-arg]
        def __iter__(self):  # noqa: D401
            raise ValueError("simulated capability shape error")

    artifacts.deduped_capabilities = BombCaps()
    data = build_apd_data(artifacts)
    assert "capabilities" in data["meta"]["section_errors"]
    assert data["capabilities"] == []
    # findings / nist_rollup are independent and still render.
    assert isinstance(data["findings"], list)
    assert isinstance(data["nist_rollup"], list)


def test_section_errors_is_keyed_by_section_name() -> None:
    """section_errors keys must be the canonical section names.

    A failure in a single, fully-isolated section (``next_steps``, whose only
    input is ``supplement.get("next_steps")``) must register exactly one
    section name in section_errors — no prefixes, no synthetic keys, no
    accidental cascade into adjacent sections.
    """
    artifacts = _make_minimal_artifacts()

    class BombSupplement(dict):  # type: ignore[type-arg]
        def get(self, key, default=None):
            if key == "next_steps":
                raise RuntimeError("simulated supplement read error")
            return super().get(key, default)

    # Pre-populate so the supplement isn't falsy (build_apd_data does
    # ``supplement = artifacts.report_data or {}`` which would otherwise
    # swap the bomb for a plain dict on empty input).
    bomb = BombSupplement()
    bomb["_keep_truthy"] = True
    artifacts.report_data = bomb
    data = build_apd_data(artifacts)
    assert "next_steps" in data["meta"]["section_errors"]
    # next_steps placeholder is the empty list.
    assert data["next_steps"] == []
    # No cascade into independent sections.
    assert "summary" in data
    assert "findings" in data
    assert "taxonomy" in data


def test_build_report_returns_data_dict(tmp_path: pathlib.Path) -> None:
    """build_report must return a (target_dir, data) tuple so the CLI can
    surface section_errors as stderr warnings without re-parsing data.js.
    """
    out = tmp_path / "report"
    result = build_report(
        REPO / "examples" / "apd-20260601-claim-event-bus" / "expected",
        out_dir=out,
        quiet=True,
    )
    assert isinstance(result, tuple)
    target, data = result
    assert target == out
    assert isinstance(data, dict)
    assert "meta" in data
    assert "section_errors" in data["meta"]


def test_build_report_succeeds_on_canonical_example_with_empty_section_errors(
    tmp_path: pathlib.Path,
) -> None:
    """After Tier-2-C, the canonical example builds with no section errors.

    This locks in the baseline so a future regression that crashes a section
    fails CI loudly. Per-section isolation is a safety net — it must not
    silently mask new authoring errors that would have rendered cleanly before.
    """
    for run_path in (
        "examples/apd-20260601-claim-event-bus/expected",
    ):
        out = tmp_path / run_path.replace("/", "_")
        target, data = build_report(REPO / run_path, out_dir=out, quiet=True)
        # Confirm meta.section_errors is empty.
        assert data["meta"]["section_errors"] == {}, (
            f"{run_path}: unexpected section errors: "
            f"{data['meta']['section_errors']}"
        )
        # Cross-check against the rendered data.js so we know the in-memory
        # dict matches what landed on disk.
        data_js = (target / "data.js").read_text(encoding="utf-8")
        start = data_js.find("{")
        end = data_js.rfind("}") + 1
        parsed = json.loads(data_js[start:end])
        assert parsed["meta"]["section_errors"] == {}


def test_report_build_error_exported_from_build_module() -> None:
    """ReportBuildError must be importable from ``apd_gauntlet.report.build``
    so the CLI and downstream callers can catch it as a typed orchestrator
    failure (distinct from MissingArtifactError / BundleMissingError).
    """
    assert issubclass(ReportBuildError, RuntimeError)
