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

import hashlib
import json
import pathlib

from apd_gauntlet.attack_path.enumerate import Path as APath
from apd_gauntlet.attack_path.findings import (
    emit_findings,
    select_bounded,
    severity_for_risk,
)
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


def _path_with_two_finding_edges_of_different_goals() -> tuple[Graph, APath]:
    """Build a 3-hop graph + path with two compromisable_via_finding edges
    whose findings carry different apd_goal values (authenticity upstream,
    confidentiality near the jewel). Used to verify that emit_findings
    labels the path by the worst-case category, not the first match.
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
    # Edge A: attacker -> gateway, compromisable_via_finding (authenticity)
    g.add_edge(Edge("edge-aaaaaaaa", "compromisable_via_finding",
                    "atk-aaaaaaaa", "asset-aaaaaaaa",
                    {"source": "artifact"}, "high", 1,
                    finding_id="auth-aaaaaaaa"))
    # Edge B: gateway -> app-server, compromisable_via_finding (confidentiality)
    g.add_edge(Edge("edge-bbbbbbbb", "compromisable_via_finding",
                    "asset-aaaaaaaa", "asset-bbbbbbbb",
                    {"source": "artifact"}, "high", 1,
                    finding_id="conf-bbbbbbbb"))
    # Edge C: app-server -> jewel, data_resides_on
    g.add_edge(Edge("edge-cccccccc", "data_resides_on",
                    "asset-bbbbbbbb", "jewel-aaaaaaaa",
                    {"source": "artifact"}, "high", 1))
    p = APath(
        path_id="path-dddddddd",
        attacker_position="atk-aaaaaaaa",
        crown_jewel="jewel-aaaaaaaa",
        edges=("edge-aaaaaaaa", "edge-bbbbbbbb", "edge-cccccccc"),
        hop_count=3,
        feasibility="high",
        severity_sum=8,
        mitigation_count=0,
    )
    return g, p


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


def test_risk_severity_label_saturates_to_critical_at_or_above_4() -> None:
    # severity_sum=3 -> high; severity_sum>=4 -> critical, including worst-case
    # multi-hop sums that the old dict-based lookup silently downgraded.
    assert severity_for_risk(3) == "high"
    assert severity_for_risk(4) == "critical"
    assert severity_for_risk(6) == "critical"
    assert severity_for_risk(12) == "critical"


def test_inference_picks_worst_case_goal_across_multiple_finding_edges() -> None:
    # 3-hop path with two compromisable_via_finding edges:
    #   edge A finding: apd_goal=authenticity
    #   edge B finding: apd_goal=confidentiality (closer to jewel; worst-case)
    # emit_findings must label the path with apd_goal=confidentiality,
    # not the first-encountered authenticity.
    g, p = _path_with_two_finding_edges_of_different_goals()
    findings_by_id = {
        "auth-aaaaaaaa": {"apd_tier": "trustworthiness", "apd_goal": "authenticity"},
        "conf-bbbbbbbb": {"apd_tier": "trustworthiness", "apd_goal": "confidentiality"},
    }
    results = emit_findings(
        paths=[p],
        overlays=[],
        graph=g,
        findings_by_id=findings_by_id,
        capabilities=[],
    )
    assert any(f["apd_goal"] == "confidentiality" for f in results)
    assert not any(f["apd_goal"] == "authenticity" for f in results)


# ---------------------------------------------------------------------------
# WS4: bounded per-pair risk-finding emission (PR4)
#
# emit_findings(bound=True) keeps all gaps, keeps the worst N risk findings
# per (attacker, crown_jewel) pair, and collapses the suppressed remainder
# into ONE aggregate uncertainty finding.
# ---------------------------------------------------------------------------


def _apath_id_for(path_id: str) -> str:
    return "apath-" + hashlib.sha256(path_id.encode()).hexdigest()[:8]


def _risk_path(
    path_id: str,
    attacker: str,
    jewel: str,
    severity_sum: int,
    hop_count: int = 2,
    feasibility: str = "high",
) -> APath:
    """A risk-eligible path: feasibility != low, severity_sum >= 3, no mitigation."""
    return APath(
        path_id=path_id,
        attacker_position=attacker,
        crown_jewel=jewel,
        edges=("edge-aaaaaaaa", "edge-cccccccc"),
        hop_count=hop_count,
        feasibility=feasibility,  # type: ignore[arg-type]
        severity_sum=severity_sum,
        mitigation_count=0,
    )


def _two_pairs_three_risk_paths_each() -> list[APath]:
    """2 (attacker, jewel) pairs, 3 risk paths each, with distinct severity sums
    so the worst-per-pair is unambiguous."""
    paths: list[APath] = []
    for atk, jwl, tag in (
        ("atk-aaaaaaaa", "jewel-aaaaaaaa", "A"),
        ("atk-bbbbbbbb", "jewel-bbbbbbbb", "B"),
    ):
        paths.append(_risk_path(f"path-{tag}1aaaaa", atk, jwl, severity_sum=6))
        paths.append(_risk_path(f"path-{tag}2bbbbb", atk, jwl, severity_sum=4))
        paths.append(_risk_path(f"path-{tag}3ccccc", atk, jwl, severity_sum=3))
    return paths


def test_select_bounded_keeps_worst_risk_per_pair_by_default() -> None:
    """3 risk paths per pair across 2 pairs -> exactly 2 risk findings (the
    worst-severity path per pair) at the default max_risk_per_pair=1."""
    paths = _two_pairs_three_risk_paths_each()
    # Build the full per-path stream first (each path -> a risk finding).
    g = _g()  # graph not actually traversed for these synthetic paths' ids
    all_findings = [
        {
            "id": _apath_id_for(p.path_id),
            "disposition": "risk",
            "severity": "high",
            "_path_id": p.path_id,
        }
        for p in paths
    ]
    selected, stats = select_bounded(all_findings, paths, max_risk_per_pair=1)
    del g
    risk = [f for f in selected if f["disposition"] == "risk"]
    assert len(risk) == 2, "one worst-risk finding per pair"
    # The kept finding per pair must be the severity_sum=6 path.
    kept_ids = {f["id"] for f in risk}
    assert _apath_id_for("path-A1aaaaa") in kept_ids
    assert _apath_id_for("path-B1aaaaa") in kept_ids
    assert stats["risk_pairs"] == 2
    assert stats["risk_findings"] == 2


def test_select_bounded_collapses_suppressed_into_single_aggregate() -> None:
    """The 4 suppressed risk paths (2 pairs x 3 - 2 kept) collapse into ONE
    aggregate uncertainty finding disclosing the suppressed count."""
    paths = _two_pairs_three_risk_paths_each()
    all_findings = [
        {
            "id": _apath_id_for(p.path_id),
            "disposition": "risk",
            "severity": "high",
        }
        for p in paths
    ]
    selected, stats = select_bounded(all_findings, paths, max_risk_per_pair=1)
    aggregates = [
        f
        for f in selected
        if f["disposition"] == "uncertainty"
        and f.get("recommendation", {}).get("posture") == "consider"
    ]
    assert len(aggregates) == 1, "exactly one aggregate uncertainty finding"
    agg = aggregates[0]
    assert agg["severity"] == "low"
    assert agg["confidence"] == "low"
    assert stats["suppressed_into_aggregate"] == 4
    # The aggregate must disclose suppressed + total counts somewhere readable.
    blob = (agg["summary"] + agg["detail"]).lower()
    assert "4" in blob and "6" in blob  # 4 suppressed of 6 total paths


def test_select_bounded_keeps_all_gap_findings() -> None:
    """Gap-disposition findings are never suppressed regardless of the knob."""
    paths = _two_pairs_three_risk_paths_each()
    gaps = [
        {"id": "apath-gap00001", "disposition": "gap", "severity": "high"},
        {"id": "apath-gap00002", "disposition": "gap", "severity": "medium"},
    ]
    risks = [
        {
            "id": _apath_id_for(p.path_id),
            "disposition": "risk",
            "severity": "high",
        }
        for p in paths
    ]
    selected, stats = select_bounded(gaps + risks, paths, max_risk_per_pair=1)
    kept_gaps = [f for f in selected if f["disposition"] == "gap"]
    assert len(kept_gaps) == 2
    assert stats["gap"] == 2


def test_select_bounded_knob_two_keeps_two_per_pair() -> None:
    """max_risk_per_pair=2 keeps the top 2 risk findings per pair (4 total)."""
    paths = _two_pairs_three_risk_paths_each()
    all_findings = [
        {
            "id": _apath_id_for(p.path_id),
            "disposition": "risk",
            "severity": "high",
        }
        for p in paths
    ]
    selected, stats = select_bounded(all_findings, paths, max_risk_per_pair=2)
    risk = [f for f in selected if f["disposition"] == "risk"]
    assert len(risk) == 4
    assert stats["risk_findings"] == 4
    assert stats["suppressed_into_aggregate"] == 2


def test_emit_findings_bound_default_on_bounds_risk_stream() -> None:
    """emit_findings(bound=True) is the DEFAULT: a graph yielding many risk
    paths per pair emits only the worst per pair plus one aggregate."""
    # Three high-feasibility, severity_sum>=3, no-mitigation paths for ONE pair.
    g = _g()
    paths = [
        APath(
            path_id="path-r1aaaaaa",
            attacker_position="atk-aaaaaaaa",
            crown_jewel="jewel-aaaaaaaa",
            edges=("edge-aaaaaaaa", "edge-bbbbbbbb", "edge-cccccccc"),
            hop_count=3,
            feasibility="high",
            severity_sum=6,
            mitigation_count=0,
        ),
        APath(
            path_id="path-r2bbbbbb",
            attacker_position="atk-aaaaaaaa",
            crown_jewel="jewel-aaaaaaaa",
            edges=("edge-aaaaaaaa", "edge-bbbbbbbb", "edge-cccccccc"),
            hop_count=3,
            feasibility="high",
            severity_sum=4,
            mitigation_count=0,
        ),
        APath(
            path_id="path-r3cccccc",
            attacker_position="atk-aaaaaaaa",
            crown_jewel="jewel-aaaaaaaa",
            edges=("edge-aaaaaaaa", "edge-bbbbbbbb", "edge-cccccccc"),
            hop_count=3,
            feasibility="high",
            severity_sum=3,
            mitigation_count=0,
        ),
    ]
    bounded = emit_findings(
        paths=paths,
        overlays=[],
        graph=g,
        findings_by_id=_findings_by_id(),
        capabilities=[],
    )
    risk = [f for f in bounded if f["disposition"] == "risk"]
    assert len(risk) == 1, "default bound keeps only worst risk per pair"
    aggregates = [
        f
        for f in bounded
        if f["disposition"] == "uncertainty"
        and f.get("recommendation", {}).get("posture") == "consider"
    ]
    assert len(aggregates) == 1


def test_emit_findings_bound_false_yields_one_per_path() -> None:
    """bound=False restores the legacy one-finding-per-path behavior."""
    g = _g()
    paths = [
        APath(
            path_id="path-r1aaaaaa",
            attacker_position="atk-aaaaaaaa",
            crown_jewel="jewel-aaaaaaaa",
            edges=("edge-aaaaaaaa", "edge-bbbbbbbb", "edge-cccccccc"),
            hop_count=3,
            feasibility="high",
            severity_sum=6,
            mitigation_count=0,
        ),
        APath(
            path_id="path-r2bbbbbb",
            attacker_position="atk-aaaaaaaa",
            crown_jewel="jewel-aaaaaaaa",
            edges=("edge-aaaaaaaa", "edge-bbbbbbbb", "edge-cccccccc"),
            hop_count=3,
            feasibility="high",
            severity_sum=4,
            mitigation_count=0,
        ),
    ]
    unbounded = emit_findings(
        paths=paths,
        overlays=[],
        graph=g,
        findings_by_id=_findings_by_id(),
        capabilities=[],
        bound=False,
    )
    risk = [f for f in unbounded if f["disposition"] == "risk"]
    assert len(risk) == 2, "bound=False yields one finding per path"


def test_select_bounded_aggregate_validates_against_schema() -> None:
    """The aggregate uncertainty finding must be schema-valid like any other."""
    validator = _build_finding_validator()
    g = _g()
    paths = [
        APath(
            path_id=f"path-{tag}",
            attacker_position="atk-aaaaaaaa",
            crown_jewel="jewel-aaaaaaaa",
            edges=("edge-aaaaaaaa", "edge-bbbbbbbb", "edge-cccccccc"),
            hop_count=3,
            feasibility="high",
            severity_sum=sev,
            mitigation_count=0,
        )
        for tag, sev in (("a1aaaaaa", 6), ("a2bbbbbb", 4), ("a3cccccc", 3))
    ]
    bounded = emit_findings(
        paths=paths,
        overlays=[],
        graph=g,
        findings_by_id=_findings_by_id(),
        capabilities=[],
    )
    for f in bounded:
        errors = list(validator.iter_errors(f))
        assert errors == [], (
            f"finding {f['id']} failed validation: {[e.message for e in errors]}"
        )
