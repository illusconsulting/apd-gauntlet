# tests/unit/report/test_tier1_regressions.py
"""Regression tests for the Tier-1 report-generation hardening pass.

Each test pins a specific defect surfaced by the html-report-failure-mode
analysis so a future change cannot silently re-introduce it.
"""
from __future__ import annotations

import json
import pathlib
import re
from unittest.mock import MagicMock

import pytest
from apd_gauntlet.report.build import build_report
from apd_gauntlet.report.loader import load_run
from apd_gauntlet.report.transform import (
    _collect_referenced_ids,
    _goal_to_tier,
    apd_matrix,
    attack_exposure_rows,
    build_apd_data,
    capability_grid,
    findings_array,
    nist_rollup_rows,
)

REPO = pathlib.Path(__file__).resolve().parents[3]


# ---------------------------------------------------------------------------
# Defect 1: Canonical example fixture used to crash the report build because
# its nist-coverage.yaml uses Shape-A semantics under the *plural* key
# ``controls:`` (a list of {id, family, posture, ...}) which the original
# Shape-A reader didn't recognise — the list passed the truthy check on the
# Shape-C ``controls_map`` branch and the loop called ``.items()`` on it.
# ---------------------------------------------------------------------------


def test_canonical_example_loads_and_builds_without_crash(tmp_path) -> None:
    example_run = REPO / "examples" / "apd-20260601-claim-event-bus" / "expected"
    artifacts = load_run(example_run)
    data = build_apd_data(artifacts, run_dir=example_run)

    # NIST rollup must produce rows; pre-fix it crashed with AttributeError.
    assert len(data["nist_rollup"]) > 0, \
        "canonical example must produce NIST rows"
    # ATT&CK rollup must produce rows (techniques is a plural list here).
    assert len(data["attack_exposure"]) > 0, \
        "canonical example must produce ATT&CK rows"
    # APD matrix must produce rows (components is plural here).
    assert len(data["apd_matrix"]["rows"]) > 0, \
        "canonical example must produce APD matrix rows"


def test_canonical_example_build_report_writes_output(tmp_path) -> None:
    example_run = REPO / "examples" / "apd-20260601-claim-event-bus" / "expected"
    out_dir = tmp_path / "report-html"
    build_report(example_run, out_dir=out_dir)
    assert (out_dir / "index.html").is_file()
    assert (out_dir / "data.js").is_file()
    # data.js must contain a syntactically valid JSON payload.
    data_js = (out_dir / "data.js").read_text(encoding="utf-8")
    start = data_js.find("{")
    end = data_js.rfind("}") + 1
    payload = json.loads(data_js[start:end])
    assert payload["nist_rollup"], "rendered data.js must carry NIST rows"


def test_nist_rollup_plural_controls_list_shape() -> None:
    """Synthetic minimal repro of the canonical-example shape."""
    artifacts = MagicMock()
    artifacts.nist_coverage = {
        "controls": [
            {"id": "AC-3", "family": "AC", "posture": "covered"},
            {"id": "AU-2", "family": "AU", "posture": "gapped"},
            {"id": "SC-8", "family": "SC", "posture": "gapped_and_covered"},
        ],
    }
    artifacts.deduped_capabilities = []
    rows = nist_rollup_rows(artifacts)
    by_fam = {r["family"]: r for r in rows}
    assert set(by_fam) == {"AC", "AU", "SC"}
    assert by_fam["AC"]["covered"] == 1
    assert by_fam["AU"]["gapped"] == 1
    assert by_fam["SC"]["both"] == 1


def test_attack_exposure_plural_techniques_list_shape() -> None:
    """Plural ``techniques`` as a list (Shape-A form) should not crash."""
    artifacts = MagicMock()
    artifacts.attack_exposure = {
        "techniques": [
            {
                "id": "T1078", "name": "Valid Accounts",
                "exposure_finding_count": 2,
                "mitigated_by_capabilities": [{"capability_id": "cap-1"}],
            },
        ],
    }
    rows = attack_exposure_rows(artifacts)
    assert len(rows) == 1
    assert rows[0]["id"] == "T1078"
    assert rows[0]["coverage"] == "partial"


def test_apd_matrix_plural_components_list_shape() -> None:
    """Plural ``components`` as a list should be recognised as Shape-A."""
    coverage_matrix = {
        "components": [
            {
                "name": "claim-event-bus",
                "cells": {g: {"posture": "covered"} for g in [
                    "confidentiality", "integrity", "availability",
                    "distributed", "resilient", "ephemeral",
                    "authenticity", "non_repudiation", "immutability",
                ]},
            },
        ],
    }
    artifacts = MagicMock()
    artifacts.apd_coverage_matrix = coverage_matrix
    artifacts.deduped_findings = []
    artifacts.attack_path_findings = []
    m = apd_matrix(artifacts)
    assert len(m["rows"]) == 1
    assert m["rows"][0]["component"] == "claim-event-bus"


# ---------------------------------------------------------------------------
# Defect 2: ``_collect_referenced_ids`` used ``.update()`` directly on the
# raw nist_800_53r5 value, raising TypeError when entries were list-of-dicts
# (the apd-control-mappings discipline shape).
# ---------------------------------------------------------------------------


def test_collect_referenced_ids_tolerates_list_of_dicts_nist() -> None:
    artifacts = MagicMock()
    artifacts.deduped_findings = [
        {
            "control_mappings": {
                "nist_800_53r5": [
                    {"id": "AC-3", "rationale": "access enforcement"},
                    "SC-8",  # mixed bare-string + dict, both valid shapes
                ],
            },
        },
    ]
    artifacts.attack_path_findings = []
    artifacts.deduped_capabilities = []
    artifacts.nist_coverage = {}
    artifacts.attack_exposure = {}
    refs = _collect_referenced_ids(artifacts)
    assert refs["nist"] == {"AC-3", "SC-8"}


# ---------------------------------------------------------------------------
# Defect 3: findings_array leaked raw dict mapping entries into
# data.findings[].mappings.nist (and cwe/owasp_api/owasp), producing
# [object Object] in the React-rendered tooltip.
# ---------------------------------------------------------------------------


def test_findings_array_normalises_list_of_dict_mappings() -> None:
    artifacts = MagicMock()
    artifacts.deduped_findings = [
        {
            "id": "conf-001",
            "control_mappings": {
                "nist_800_53r5": [{"id": "AC-3", "rationale": "..."}, "SC-8"],
                "cwe": [{"id": "CWE-79"}, "CWE-89"],
                "owasp_api_top10": [{"id": "API1"}, "API5"],
                "owasp_top10": [{"id": "A01"}, "A07"],
            },
        },
    ]
    artifacts.attack_path_findings = []
    artifacts.deduped_capabilities = []
    out = findings_array(artifacts, headline_supplement=None)
    mappings = out[0]["mappings"]
    assert mappings["nist"] == ["AC-3", "SC-8"]
    assert mappings["cwe"] == ["CWE-79", "CWE-89"]
    assert mappings["owasp_api"] == ["API1", "API5"]
    assert mappings["owasp"] == ["A01", "A07"]


# ---------------------------------------------------------------------------
# Defect 4: capability_grid emitted tier=None / goal=None for every
# capability when the records lacked apd_tier / apd_goal. Caldera carries
# the goal under ``agent`` and authentik carries apd_goal but no apd_tier.
# ---------------------------------------------------------------------------


def test_goal_to_tier_reverse_lookup() -> None:
    assert _goal_to_tier("confidentiality") == "trustworthiness"
    assert _goal_to_tier("resilient") == "scalability"
    assert _goal_to_tier("non_repudiation") == "auditability"
    assert _goal_to_tier(None) is None
    assert _goal_to_tier("unknown_goal") is None


def test_capability_grid_caldera_agent_fallback() -> None:
    """Caldera caps carry ``agent: confidentiality`` but no apd_goal / apd_tier."""
    artifacts = MagicMock()
    artifacts.deduped_capabilities = [
        {"id": "cap-1", "agent": "confidentiality"},
        {"id": "cap-2", "agent": "resilient"},
    ]
    grid = capability_grid(artifacts)
    assert grid[0]["goal"] == "confidentiality"
    assert grid[0]["tier"] == "trustworthiness"
    assert grid[1]["goal"] == "resilient"
    assert grid[1]["tier"] == "scalability"


def test_capability_grid_authentik_tier_derived_from_goal() -> None:
    """Authentik caps carry apd_goal but no apd_tier; tier must be derived."""
    artifacts = MagicMock()
    artifacts.deduped_capabilities = [
        {"id": "cap-1", "apd_goal": "authenticity"},
        {"id": "cap-2", "apd_goal": "immutability"},
    ]
    grid = capability_grid(artifacts)
    assert grid[0]["tier"] == "auditability"
    assert grid[1]["tier"] == "auditability"


# ---------------------------------------------------------------------------
# Defect 5: apd_matrix Shape-A loop crashed on list-of-strings component
# shorthand because it called .get on a string.
# ---------------------------------------------------------------------------


def test_apd_matrix_shape_a_skips_non_dict_entries() -> None:
    coverage_matrix = {
        "component": ["service-a", {"name": "service-b", "cells": {}}],
    }
    artifacts = MagicMock()
    artifacts.apd_coverage_matrix = coverage_matrix
    artifacts.deduped_findings = []
    artifacts.attack_path_findings = []
    m = apd_matrix(artifacts)
    # The string entry must be skipped, the dict entry must be emitted.
    assert len(m["rows"]) == 1
    assert m["rows"][0]["component"] == "service-b"


# ---------------------------------------------------------------------------
# Defect 6: Loader's singular key names (``contradiction``,
# ``severity_disagreement``) never matched any shipped run's actual key.
# ---------------------------------------------------------------------------


def test_loader_reads_plural_contradictions_key_from_canonical_example() -> None:
    example_run = REPO / "examples" / "apd-20260601-claim-event-bus" / "expected"
    artifacts = load_run(example_run)
    assert len(artifacts.contradictions) >= 1, \
        "canonical example contains contradictions under plural key"


def test_loader_reads_plural_severity_disagreements_from_canonical_example() -> None:
    example_run = REPO / "examples" / "apd-20260601-claim-event-bus" / "expected"
    artifacts = load_run(example_run)
    assert len(artifacts.severity_disagreements) >= 1, \
        "canonical example contains severity disagreements under plural key"


def test_loader_reads_disagreements_alias(tmp_path) -> None:
    """Some synthesizers emit the abbreviated ``disagreements:`` key instead of the
    canonical ``severity_disagreements:``. The loader fallback must read both. Tested
    at the ``_records`` helper level so it needs no real run fixture."""
    from apd_gauntlet.report.loader import _records
    p = tmp_path / "severity-disagreements.yaml"
    p.write_text("disagreements:\n  - id: sd-1\n    note: scope\n", encoding="utf-8")
    recs = _records(
        p, "severity_disagreements", "disagreements", "severity_disagreement",
    )
    assert [r["id"] for r in recs] == ["sd-1"]


# ---------------------------------------------------------------------------
# Defect 7: stale runs/apd-20260526-chainguard-quickpath/ directory.
# ---------------------------------------------------------------------------


def test_chainguard_directory_removed() -> None:
    assert not (REPO / "runs" / "apd-20260526-chainguard-quickpath").exists(), \
        "stale chainguard-quickpath directory must remain removed"


# ---------------------------------------------------------------------------
# End-to-end: the canonical example builds successfully.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("run_path", [
    "examples/apd-20260601-claim-event-bus/expected",
])
def test_build_report_succeeds_on_canonical_example(run_path: str, tmp_path) -> None:
    run = REPO / run_path
    out = tmp_path / "report"
    build_report(run, out_dir=out)
    assert (out / "index.html").is_file()
    data_js = (out / "data.js").read_text(encoding="utf-8")
    # data.js must be syntactically valid JSON (no truncation, no NaN).
    payload = re.search(r"window\.APD_DATA\s*=\s*(\{.*\});?", data_js, re.DOTALL)
    assert payload, f"{run_path}: data.js lacks window.APD_DATA assignment"
    json.loads(payload.group(1))  # would raise on malformed JSON
