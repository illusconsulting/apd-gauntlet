# tests/unit/report/test_transform_attack_path_context.py
from __future__ import annotations

import hashlib

from apd_gauntlet.report import transform as T
from apd_gauntlet.report.loader import RunArtifacts
from apd_gauntlet.report.transform import findings_array


def test_normalize_edge_type_canonicalizes():
    assert T._normalize_edge_type("trusts") == "trust_boundary"
    assert T._normalize_edge_type("finding") == "compromisable_via_finding"
    assert T._normalize_edge_type("compromisable_via_finding") == "compromisable_via_finding"
    assert T._normalize_edge_type("capability") == "mitigated_by_capability"
    assert T._normalize_edge_type("network_reachable") == "network_reachable"
    assert T._normalize_edge_type("") == "trust_boundary"


def test_build_node_edge_maps_indexes_by_id():
    ag = {
        "nodes": [{"node_id": "n1", "name": "API", "node_type": "asset"}],
        "edges": [{"edge_id": "e1", "from": "n1", "to": "n2", "edge_type": "trusts"}],
    }
    nodes, edges = T._build_node_edge_maps(ag)
    assert nodes["n1"]["name"] == "API"
    assert edges["e1"]["to"] == "n2"


def test_build_node_edge_maps_is_none_safe_and_skips_non_dicts():
    # None / missing keys → empty maps (no crash).
    assert T._build_node_edge_maps(None) == ({}, {})
    assert T._build_node_edge_maps({}) == ({}, {})
    # Non-dict entries are skipped; well-formed entries are kept.
    nodes, edges = T._build_node_edge_maps(
        {"nodes": ["junk", {"node_id": "n1", "name": "API"}],
         "edges": [42, {"edge_id": "e1", "to": "n1"}]}
    )
    assert list(nodes) == ["n1"] and list(edges) == ["e1"]


def test_hop_node_resolves_name_and_type_with_fallback():
    nodes = {"n1": {"name": "API", "node_type": "service"}}
    assert T._hop_node(nodes, "n1") == {"id": "n1", "name": "API", "type": "service"}
    # Missing node falls back to the id and a default type.
    assert T._hop_node(nodes, "ghost") == {"id": "ghost", "name": "ghost", "type": "asset"}


def _apath_id(path_id: str) -> str:
    return "apath-" + hashlib.sha256(path_id.encode()).hexdigest()[:8]


def _artifacts(*, findings, asset_graph, attack_paths, defense_graph=None):
    """A RunArtifacts with only the fields the attack-path strip path reads."""
    return RunArtifacts(
        run_id="r", framework_version="1", domain_pack_name="p",
        domain_pack_version="1", subject="s", date="2026-01-01",
        asset_inventory={}, deduped_findings=[], deduped_capabilities=[],
        contradictions=[], contradictions_notes=None,
        severity_disagreements=[], severity_disagreements_notes=None,
        nist_coverage={}, attack_exposure={}, apd_coverage_matrix={},
        asset_graph=asset_graph, attack_paths=attack_paths,
        defense_graph=defense_graph, attack_path_findings=findings,
        report_data=None, metrics={"schema_version": 1, "findings_total": 0},
    )


# A 3-hop path: internet --net--> api --compromisable(conf-1)--> worker --authz(BOTTLENECK)--> db
_ASSET_GRAPH = {
    "nodes": [
        {"node_id": "atk-1", "name": "Internet", "node_type": "attacker_position"},
        {"node_id": "svc-api", "name": "API", "node_type": "asset"},
        {"node_id": "svc-wkr", "name": "Worker", "node_type": "asset"},
        {"node_id": "db-1", "name": "Datastore", "node_type": "crown_jewel"},
    ],
    "edges": [
        {"edge_id": "edge-0000aaaa", "from": "atk-1", "to": "svc-api",
         "edge_type": "network_reachable", "confidence": "medium"},
        {"edge_id": "edge-0000bbbb", "from": "svc-api", "to": "svc-wkr",
         "edge_type": "compromisable_via_finding", "confidence": "high",
         "finding_id": "conf-11111111"},
        {"edge_id": "edge-0000cccc", "from": "svc-wkr", "to": "db-1",
         "edge_type": "authz_grants", "confidence": "high"},
    ],
}
_PATH = {
    "path_id": "path-12345678",
    "attacker_position": "atk-1",
    "crown_jewel": "db-1",
    "edges": ["edge-0000aaaa", "edge-0000bbbb", "edge-0000cccc"],
    "bottleneck_edges": ["edge-0000cccc"],
    "hop_count": 3,
    "feasibility": "medium",
    "severity_sum": 7,
    "mitigation_count": 0,
}
_DEFENSE_GRAPH = {
    "bottleneck_overlays": [
        {"edge_id": "edge-0000cccc", "paths_traversing": 6,
         "exposed_attack_techniques": ["T1190"],
         "candidate_d3fend": [], "existing_capability_backing": [],
         "net_new_d3fend": ["D3-NTA", "D3-MFA"]},
    ],
}


def _risk_finding(**over):
    f = {
        "id": _apath_id("path-12345678"), "disposition": "risk", "severity": "high",
        "confidence": "medium", "title": "t", "summary": "s", "detail": "d",
        "evidence": [{"artifact": "40-synthesis/attack-paths.yaml",
                      "locator": "path-12345678", "excerpt": "x"}],
        "recommendation": {
            "posture": "required",
            "summary": "Add a control on the highest-confidence edge",
        },
    }
    f.update(over)
    return f


def _get_block(findings, asset_graph=_ASSET_GRAPH, attack_paths=None, defense_graph=_DEFENSE_GRAPH):
    arts = _artifacts(findings=findings, asset_graph=asset_graph,
                      attack_paths=attack_paths or {"paths": [_PATH]},
                      defense_graph=defense_graph)
    arr = findings_array(arts, headline_supplement=None)
    return {f["id"]: f for f in arr}


def test_risk_apath_finding_gets_attack_path_block():
    f = _risk_finding()
    block = _get_block([f])[f["id"]]["attack_path"]
    assert block["path_id"] == "path-12345678"
    assert block["attacker"]["name"] == "Internet"
    assert block["crown_jewel"]["name"] == "Datastore"
    assert [h["edge_type"] for h in block["hops"]] == [
        "network_reachable", "compromisable_via_finding", "authz_grants"]
    vuln = [h for h in block["hops"] if h["is_vuln"]]
    assert len(vuln) == 1 and vuln[0]["finding_id"] == "conf-11111111"
    fix = [h for h in block["hops"] if h["is_fix"]]
    assert len(fix) == 1 and fix[0]["edge_id"] == "edge-0000bbbb"
    choke = [h for h in block["hops"] if h["chokepoint"]]
    assert len(choke) == 1 and choke[0]["edge_id"] == "edge-0000cccc"
    assert choke[0]["chokepoint"]["d3fend"] == ["D3-MFA", "D3-NTA"]
    assert choke[0]["chokepoint"]["paths_traversing"] == 6


def test_non_risk_apath_finding_gets_no_block():
    f = _risk_finding(disposition="uncertainty")
    assert "attack_path" not in _get_block([f])[f["id"]]


def test_non_apath_finding_gets_no_block():
    f = _risk_finding(id="conf-22222222")
    assert "attack_path" not in _get_block([f])[f["id"]]


def test_unresolvable_apath_finding_gets_no_block():
    f = _risk_finding(id="apath-deadbeef", evidence=[])
    assert "attack_path" not in _get_block([f])[f["id"]]


def test_locator_fallback_resolves_when_hash_misses():
    f = _risk_finding(
        id="apath-deadbeef",
        evidence=[{"artifact": "a", "locator": "edges (path path-12345678)", "excerpt": "x"}],
    )
    block = _get_block([f])[f["id"]].get("attack_path")
    assert block is not None and block["path_id"] == "path-12345678"


def test_no_bottleneck_overlay_degrades_to_fix_only():
    f = _risk_finding()
    block = _get_block([f], defense_graph={"bottleneck_overlays": []})[f["id"]]["attack_path"]
    assert all(h["chokepoint"] is None for h in block["hops"])
    assert any(h["is_fix"] for h in block["hops"])


def test_attack_path_block_is_deterministic():
    f = _risk_finding()
    arts = _artifacts(findings=[f], asset_graph=_ASSET_GRAPH,
                      attack_paths={"paths": [_PATH]}, defense_graph=_DEFENSE_GRAPH)
    a = findings_array(arts, headline_supplement=None)
    b = findings_array(arts, headline_supplement=None)
    assert a == b  # byte-for-byte stable across invocations
    choke = next(h for h in a[0]["attack_path"]["hops"] if h["chokepoint"])
    assert choke["chokepoint"]["d3fend"] == sorted(choke["chokepoint"]["d3fend"])
