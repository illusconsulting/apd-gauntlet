# tests/unit/report/test_transform_fallbacks.py
from __future__ import annotations

import pathlib

from apd_gauntlet.report.loader import load_run
from apd_gauntlet.report.transform import (
    contradictions_section,
    severity_disagreements_section,
    next_steps_section,
    posture_summary_section,
    build_apd_data,
)


def test_contradictions_section_shape(legacy_example_run: pathlib.Path) -> None:
    artifacts = load_run(legacy_example_run)
    out = contradictions_section(artifacts)
    for c in out:
        assert {"id", "finding", "capability", "comparison", "resolution"}.issubset(c.keys())
        assert {"id", "assertion"}.issubset(c["finding"].keys())
        assert {"id", "assertion"}.issubset(c["capability"].keys())


def test_severity_disagreements_section_shape(legacy_example_run: pathlib.Path) -> None:
    artifacts = load_run(legacy_example_run)
    out = severity_disagreements_section(artifacts)
    for d in out:
        assert {"id", "agents", "chosen", "rationale"}.issubset(d.keys())
        for a in d["agents"]:
            assert {"lens", "severity"}.issubset(a.keys())


def test_next_steps_supplied_passes_through(legacy_example_run: pathlib.Path) -> None:
    artifacts = load_run(legacy_example_run)
    supplement = [{"rank": 1, "text": "Do the thing.", "refs": ["merged-7c2a4f91"]}]
    assert next_steps_section(supplement) == supplement


def test_next_steps_absent_returns_empty(legacy_example_run: pathlib.Path) -> None:
    assert next_steps_section(None) == []


def test_posture_summary_supplied(legacy_example_run: pathlib.Path) -> None:
    supplied = {"trustworthiness": "T", "scalability": "S", "auditability": "A"}
    assert posture_summary_section(supplied) == supplied


def test_posture_summary_absent_returns_placeholders(legacy_example_run: pathlib.Path) -> None:
    out = posture_summary_section(None)
    assert set(out.keys()) == {"trustworthiness", "scalability", "auditability"}
    for v in out.values():
        assert isinstance(v, str) and v


def test_build_apd_data_assembles_full_window_object(legacy_example_run: pathlib.Path) -> None:
    artifacts = load_run(legacy_example_run)
    data = build_apd_data(artifacts, run_dir=legacy_example_run)
    # Spot-check the top-level keys the React template expects.
    for key in (
        "meta", "summary", "capabilities", "strengths", "findings",
        "contradictions", "severity_disagreements",
        "nist_rollup", "attack_exposure", "apd_matrix",
        "attack_paths", "next_steps", "taxonomy",
    ):
        assert key in data, f"missing key {key}"
