# tests/unit/report/test_transform_new_shapes.py
"""Coverage for the divergent coverage-YAML shapes the report transforms must
tolerate: the caldera ``control_to_findings`` / ``technique_to_findings`` /
``matrix`` shapes and the authentik ``controls`` / ``techniques`` / ``goals``
shapes (alongside the chainguard-era and crAPI-era array shapes).

Each shape is reproduced here as a synthesized in-memory artifact (MagicMock)
and the transform output is asserted directly — the regression coverage needs
no shipped real-project run on disk. ``load_run`` performs no shape-specific
parsing (it stores the raw coverage dict), so exercising the transforms against
the constructed shapes is the load-independent equivalent.
"""
from __future__ import annotations

from unittest.mock import MagicMock

from apd_gauntlet.report.transform import (
    apd_matrix,
    attack_exposure_rows,
    nist_rollup_rows,
)

# ---------------------------------------------------------------------------
# Synthetic per-shape unit tests — each constructs a divergent coverage shape
# in memory and asserts the transform output, so a shape regression has a
# single, real-run-independent point of failure to investigate.
# ---------------------------------------------------------------------------


def test_nist_control_to_findings_shape() -> None:
    """Caldera shape: flat control_to_findings dict, family derived from id."""
    nist = {
        "control_to_findings": {
            "AC-2":    ["f1"],
            "AC-2(2)": ["f2"],
            "AC-3":    [],          # zero findings, no caps → silent (not counted)
            "AU-2":    ["f3"],
        }
    }
    cap = {
        "id": "cap-1",
        "control_mappings": {"nist_800_53r5": ["AC-3"]},
    }
    artifacts = MagicMock()
    artifacts.nist_coverage = nist
    artifacts.deduped_capabilities = [cap]

    rows = nist_rollup_rows(artifacts)
    by_fam = {r["family"]: r for r in rows}
    assert set(by_fam) == {"AC", "AU"}
    # AC-2 and AC-2(2) gapped (findings only), AC-3 covered (cap only) → 2 gapped + 1 covered
    assert by_fam["AC"]["gapped"] == 2
    assert by_fam["AC"]["covered"] == 1
    assert by_fam["AC"]["both"] == 0
    # AU-2 gapped
    assert by_fam["AU"]["gapped"] == 1


def test_nist_controls_map_shape() -> None:
    """Authentik shape: per-control dict with explicit findings/capabilities."""
    nist = {
        "controls": {
            "AC-2":  {"findings": ["f1"], "capabilities": ["cap-1"]},
            "AC-3":  {"findings": ["f2"], "capabilities": []},
            "AC-6":  {"findings": [],     "capabilities": ["cap-2"]},
            "AU-2":  {"findings": ["f3"], "capabilities": []},
        }
    }
    artifacts = MagicMock()
    artifacts.nist_coverage = nist
    artifacts.deduped_capabilities = []

    rows = nist_rollup_rows(artifacts)
    by_fam = {r["family"]: r for r in rows}
    assert set(by_fam) == {"AC", "AU"}
    # AC: AC-2 both, AC-3 gapped, AC-6 covered
    assert by_fam["AC"]["both"] == 1
    assert by_fam["AC"]["gapped"] == 1
    assert by_fam["AC"]["covered"] == 1
    # AU: AU-2 gapped
    assert by_fam["AU"]["gapped"] == 1


def test_attack_technique_to_findings_shape() -> None:
    """Caldera shape: technique_to_findings + sub_techniques list of IDs."""
    expo = {
        "technique_to_findings": {
            "T1078": {
                "description": "Valid Accounts",
                "tactic":      "TA0001",
                "findings":    ["f1", "f2"],
            },
            "T1110": {
                "description":    "Brute Force",
                "tactic":         "TA0006",
                "findings":       ["f3"],
                "sub_techniques": ["T1110.003"],
            },
        }
    }
    cap = {
        "id": "cap-attk-1",
        "control_mappings": {"mitre_attack": ["T1078"]},
    }
    artifacts = MagicMock()
    artifacts.attack_exposure = expo
    artifacts.deduped_capabilities = [cap]

    rows = attack_exposure_rows(artifacts)
    by_id = {r["id"]: r for r in rows}
    assert {"T1078", "T1110", "T1110.003"}.issubset(by_id.keys())
    # T1078: 2 findings + 1 mitigation → partial
    assert by_id["T1078"]["coverage"] == "partial"
    assert by_id["T1078"]["mitigations"] == ["cap-attk-1"]
    # T1110: 1 finding, no mitigation → uncovered
    assert by_id["T1110"]["coverage"] == "uncovered"
    # T1110.003 emitted as its own row with 0 findings + 0 mitigations
    assert by_id["T1110.003"]["findings"] == 0


def test_attack_techniques_dict_authentik_keys() -> None:
    """Authentik shape: techniques dict using findings + capabilities_with_mitigation."""
    expo = {
        "techniques": {
            "T1040": {
                "name":                         "Network Sniffing",
                "tactic":                       "TA0006",
                "findings":                     ["f1", "f2"],
                "capabilities_with_mitigation": [],
                "notes":                        "PostgreSQL TLS default-off",
            },
            "T1110": {
                "name":                         "Brute Force",
                "tactic":                       "TA0006",
                "findings":                     ["f3"],
                "capabilities_with_mitigation": ["cap-a", "cap-b"],
            },
        }
    }
    artifacts = MagicMock()
    artifacts.attack_exposure = expo
    artifacts.deduped_capabilities = []

    rows = attack_exposure_rows(artifacts)
    by_id = {r["id"]: r for r in rows}
    assert by_id["T1040"]["coverage"] == "uncovered"
    assert by_id["T1040"]["mitigations"] == []
    assert "TLS" in by_id["T1040"]["note"]
    assert by_id["T1110"]["coverage"] == "partial"
    assert sorted(by_id["T1110"]["mitigations"]) == ["cap-a", "cap-b"]


def test_apd_matrix_goals_shape() -> None:
    """Authentik shape: goals map with findings: [{id, severity, disposition}]."""
    coverage_matrix = {
        "goals": {
            "confidentiality": {
                "findings":     [{"id": "f1", "severity": "high", "disposition": "gap"}],
                "capabilities": [{"id": "cap-1"}],
            },
            "integrity": {
                "findings":     [{"id": "f2", "severity": "medium", "disposition": "risk"}],
                "capabilities": [],
            },
        }
    }
    finding_f1 = {
        "id": "f1", "apd_goal": "confidentiality",
        "evidence": [{"artifact": "config/postgres.yaml"}],
    }
    finding_f2 = {
        "id": "f2", "apd_goal": "integrity",
        "evidence": [{"artifact": "api/handlers.go"}],
    }
    artifacts = MagicMock()
    artifacts.apd_coverage_matrix = coverage_matrix
    artifacts.deduped_findings = [finding_f1, finding_f2]
    artifacts.attack_path_findings = []

    m = apd_matrix(artifacts)
    rows_by_comp = {r["component"]: r for r in m["rows"]}
    assert set(rows_by_comp) == {"config/postgres.yaml", "api/handlers.go"}
    # postgres has the conf finding + conf has a capability → both
    assert rows_by_comp["config/postgres.yaml"]["cells"]["conf"] == "both"
    # postgres has no intg finding; intg has no caps → silent
    assert rows_by_comp["config/postgres.yaml"]["cells"]["intg"] == "silent"
    # api has the intg finding; intg has no caps → gapped
    assert rows_by_comp["api/handlers.go"]["cells"]["intg"] == "gapped"
    # api has no conf finding but conf has a capability — capability projects
    # across all rows (matches the crAPI ``coverage`` branch semantics).
    assert rows_by_comp["api/handlers.go"]["cells"]["conf"] == "covered"


def test_apd_matrix_matrix_shape_uses_dedup_fallback() -> None:
    """Caldera shape: matrix map has only counts; rows are derived from
    deduped findings (group by goal × evidence[0].artifact)."""
    coverage_matrix = {
        "matrix": {
            "confidentiality": {"findings_total": 1, "capabilities_total": 0},
            "integrity":       {"findings_total": 1, "capabilities_total": 1},
        }
    }
    finding_f1 = {
        "id": "f1", "apd_goal": "confidentiality",
        "evidence": [{"artifact": "operator/op-config.yml"}],
    }
    finding_f2 = {
        "id": "f2", "apd_goal": "integrity",
        "evidence": [{"artifact": "operator/op-config.yml"}],
    }
    cap = {"id": "cap-1", "apd_goal": "integrity"}
    artifacts = MagicMock()
    artifacts.apd_coverage_matrix = coverage_matrix
    artifacts.deduped_findings = [finding_f1, finding_f2]
    artifacts.attack_path_findings = []
    artifacts.deduped_capabilities = [cap]

    m = apd_matrix(artifacts)
    assert len(m["rows"]) == 1
    row = m["rows"][0]
    assert row["component"] == "operator/op-config.yml"
    # confidentiality: finding present, no cap → gapped
    assert row["cells"]["conf"] == "gapped"
    # integrity: finding + cap → both
    assert row["cells"]["intg"] == "both"
    # untouched goals are silent
    assert row["cells"]["avail"] == "silent"
