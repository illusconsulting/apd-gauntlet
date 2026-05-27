"""Tests for emit_findings — the four apath-* finding flavors.

Covers:
  1. risk (high-feasibility path, no mitigation, severity_sum >= 3)
  2. uncertainty (low-feasibility paths, severity cap at low/medium)
  3. gap (bottleneck overlay with no existing capability backing)
  4. empty inputs return empty list
  5. all emitted IDs follow the apath- pattern (14 chars total)
  6. every emitted finding carries >=1 evidence entry
  7. emitted findings validate against finding.schema.json (real schema check)
"""
from __future__ import annotations

import json
import pathlib

from apd_gauntlet.attack_path.enumerate import Path as APath
from apd_gauntlet.attack_path.findings import emit_findings
from apd_gauntlet.attack_path.graph import Edge, Graph, Node
from jsonschema import Draft202012Validator
from referencing import Registry, Resource

REPO = pathlib.Path(__file__).parent.parent
SCHEMA_DIR = REPO / "schemas"


def _build_finding_validator() -> Draft202012Validator:
    """Build a Draft202012Validator for finding.schema.json with all schemas
    registered for cross-reference resolution.
    """
    resources = []
    for schema_path in sorted(SCHEMA_DIR.glob("*.schema.json")):
        schema = json.loads(schema_path.read_text())
        sid = schema.get("$id")
        if sid:
            resources.append((sid, Resource.from_contents(schema)))
    registry = Registry().with_resources(resources)
    schema = json.loads((SCHEMA_DIR / "finding.schema.json").read_text())
    return Draft202012Validator(schema, registry=registry)


# -------- graph + fixture helpers --------

def _g() -> Graph:
    """Small graph with attacker, asset, crown_jewel and edges connecting them.

    Includes one compromisable_via_finding edge referencing a finding id and
    one mitigated_by_capability edge so paths can carry varied metadata.
    """
    g = Graph()
    g.add_node(Node("atk-aaaaaaaa", "attacker_position", "external-attacker",
                    {"source": "domain_default"}, "high"))
    g.add_node(Node("asset-aaaaaaaa", "asset", "edge-gateway",
                    {"source": "artifact"}, "high"))
    g.add_node(Node("asset-bbbbbbbb", "asset", "app-server",
                    {"source": "artifact"}, "high"))
    g.add_node(Node("jewel-aaaaaaaa", "crown_jewel", "phi-database",
                    {"source": "domain_default"}, "high",
                    data_classifications=("phi",)))
    # network_reachable: attacker -> gateway (high confidence)
    g.add_edge(Edge("edge-aaaaaaaa", "network_reachable",
                    "atk-aaaaaaaa", "asset-aaaaaaaa",
                    {"source": "artifact"}, "high", 1))
    # compromisable_via_finding: gateway -> app-server (high)
    g.add_edge(Edge("edge-bbbbbbbb", "compromisable_via_finding",
                    "asset-aaaaaaaa", "asset-bbbbbbbb",
                    {"source": "artifact"}, "high", 1,
                    finding_id="conf-deadbeef"))
    # data_resides_on: app-server -> jewel (high)
    g.add_edge(Edge("edge-cccccccc", "data_resides_on",
                    "asset-bbbbbbbb", "jewel-aaaaaaaa",
                    {"source": "artifact"}, "high", 1))
    # mitigated_by_capability: gateway -> app-server alt edge (low confidence)
    g.add_edge(Edge("edge-dddddddd", "mitigated_by_capability",
                    "asset-aaaaaaaa", "asset-bbbbbbbb",
                    {"source": "artifact"}, "low", 1,
                    capability_id="cap-12345678"))
    return g


def _findings_by_id() -> dict[str, dict]:
    return {
        "conf-deadbeef": {
            "schema_version": 1,
            "id": "conf-deadbeef",
            "agent": "confidentiality",
            "apd_tier": "trustworthiness",
            "apd_goal": "confidentiality",
            "disposition": "risk",
            "severity": "high",
            "confidence": "high",
            "control_mappings": {
                "nist_800_53r5": ["AC-3", "AC-6"],
            },
        }
    }


def _high_path_no_mitigation() -> list[APath]:
    """A high-feasibility 3-hop path through a compromisable-via-finding edge
    with severity_sum=3 (high) and zero mitigations.
    """
    return [
        APath(
            path_id="path-aaaaaaaa",
            attacker_position="atk-aaaaaaaa",
            crown_jewel="jewel-aaaaaaaa",
            edges=("edge-aaaaaaaa", "edge-bbbbbbbb", "edge-cccccccc"),
            hop_count=3,
            feasibility="high",
            severity_sum=3,
            mitigation_count=0,
        )
    ]


def _low_feasibility_path() -> list[APath]:
    """A low-feasibility path — exercises the uncertainty branch."""
    return [
        APath(
            path_id="path-bbbbbbbb",
            attacker_position="atk-aaaaaaaa",
            crown_jewel="jewel-aaaaaaaa",
            edges=("edge-aaaaaaaa", "edge-dddddddd", "edge-cccccccc"),
            hop_count=3,
            feasibility="low",
            severity_sum=0,
            mitigation_count=1,
        )
    ]


def _paths_sharing_edge() -> list[APath]:
    """Paths used alongside a bottleneck overlay. The overlay drives the
    gap-finding emission; this just needs to be a plausible path list.
    """
    return [
        APath(
            path_id="path-cccccccc",
            attacker_position="atk-aaaaaaaa",
            crown_jewel="jewel-aaaaaaaa",
            edges=("edge-aaaaaaaa", "edge-bbbbbbbb", "edge-cccccccc"),
            hop_count=3,
            feasibility="high",
            severity_sum=3,
            mitigation_count=0,
        )
    ]


def _bottleneck_overlay() -> dict:
    return {
        "edge_id": "edge-bbbbbbbb",
        "paths_traversing": 6,
        "exposed_attack_techniques": ["T1078"],
        "candidate_d3fend": [
            {"d3fend_id": "D3-NTSA", "counters": ["T1078"], "rationale": "..."}
        ],
        "existing_capability_backing": [],
        "net_new_d3fend": ["D3-NTSA"],
    }


# -------- the seven tests --------

def test_emits_high_severity_risk_for_high_feasibility_paths_with_no_mitigation() -> None:
    findings = emit_findings(
        paths=_high_path_no_mitigation(),
        overlays=[],
        graph=_g(),
        findings_by_id=_findings_by_id(),
        capabilities=[],
    )
    assert any(
        f["disposition"] == "risk" and f["severity"] in ("critical", "high")
        for f in findings
    )


def test_emits_uncertainty_for_low_feasibility_paths() -> None:
    findings = emit_findings(
        paths=_low_feasibility_path(),
        overlays=[],
        graph=_g(),
        findings_by_id={},
        capabilities=[],
    )
    assert any(f["disposition"] == "uncertainty" for f in findings)
    for f in findings:
        if f["disposition"] == "uncertainty":
            assert f["severity"] in ("low", "informational", "medium")


def test_emits_gap_for_bottleneck_with_no_d3fend_capability_backing() -> None:
    findings = emit_findings(
        paths=_paths_sharing_edge(),
        overlays=[_bottleneck_overlay()],
        graph=_g(),
        findings_by_id=_findings_by_id(),
        capabilities=[],
    )
    gap_findings = [f for f in findings if f["disposition"] == "gap"]
    assert gap_findings, "bottleneck with no capability backing must emit a gap finding"


def test_emits_nothing_on_empty_inputs() -> None:
    assert emit_findings(
        paths=[],
        overlays=[],
        graph=_g(),
        findings_by_id={},
        capabilities=[],
    ) == []


def test_all_findings_have_apath_id_pattern() -> None:
    findings = emit_findings(
        paths=_high_path_no_mitigation(),
        overlays=[],
        graph=_g(),
        findings_by_id=_findings_by_id(),
        capabilities=[],
    )
    assert findings, "expected at least one finding"
    for f in findings:
        assert f["id"].startswith("apath-")
        assert len(f["id"]) == len("apath-") + 8


def test_all_findings_carry_at_least_one_evidence_entry() -> None:
    findings = emit_findings(
        paths=_high_path_no_mitigation(),
        overlays=[],
        graph=_g(),
        findings_by_id=_findings_by_id(),
        capabilities=[],
    )
    assert findings, "expected at least one finding"
    for f in findings:
        assert len(f["evidence"]) >= 1


def test_emitted_findings_validate_against_finding_schema() -> None:
    """End-to-end correctness: every emitted finding must validate against
    schemas/finding.schema.json — catches subtle drift between the emitter
    and the canonical schema.
    """
    validator = _build_finding_validator()
    findings = emit_findings(
        paths=_high_path_no_mitigation() + _low_feasibility_path(),
        overlays=[_bottleneck_overlay()],
        graph=_g(),
        findings_by_id=_findings_by_id(),
        capabilities=[],
    )
    assert findings, "expected at least one finding to validate"
    for f in findings:
        errors = list(validator.iter_errors(f))
        assert errors == [], (
            f"finding {f['id']} failed validation: "
            f"{[e.message for e in errors]}"
        )
