# tests/unit/report/test_findings_attack_path_strip_jsx.py
"""Static-text regression tests for the per-finding attack-path strip
(no JS test runner in this repo — assert source invariants)."""
from __future__ import annotations

import pathlib

REPO = pathlib.Path(__file__).resolve().parents[3]
COMPONENTS = REPO / "report-template" / "components.jsx"


def test_attack_path_strip_component_defined_and_exported():
    src = COMPONENTS.read_text(encoding="utf-8")
    assert "function AttackPathStrip(" in src
    assert "AttackPathStrip" in src.split("Object.assign(window")[1]  # in the export


def test_attack_path_strip_renders_layered_markers():
    src = COMPONENTS.read_text(encoding="utf-8")
    assert "h.is_vuln" in src and "h.is_fix" in src and "h.chokepoint" in src
    assert "onOpenPath" in src and "view full graph" in src
    assert "chokepoint.d3fend" in src
    assert "var(--rec)" in src  # 💡/🛡 markers use the recommendation token


FINDINGS = REPO / "report-template" / "screens" / "Findings.jsx"


def test_finding_detail_renders_strip_guarded_on_attack_path():
    src = FINDINGS.read_text(encoding="utf-8")
    assert "f.attack_path &&" in src
    assert "<AttackPathStrip" in src
    assert "onOpenPath" in src
    assert src.count("onOpenPath={onOpenPath}") >= 2


APP = REPO / "report-template" / "app.jsx"
ATTACK_PATHS = REPO / "report-template" / "screens" / "AttackPaths.jsx"


def test_app_defines_and_wires_on_open_path():
    src = APP.read_text(encoding="utf-8")
    assert "const onOpenPath" in src
    assert 'setActiveTab("attack_paths")' in src
    assert "focusPathId" in src
    assert "onOpenPath={onOpenPath}" in src


def test_attack_paths_accepts_and_applies_focus():
    src = ATTACK_PATHS.read_text(encoding="utf-8")
    assert "focusPathId" in src
    assert "ap-row-${p.path_id}" in src
