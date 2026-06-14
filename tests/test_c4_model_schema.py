"""c4-model schema: the canonical, assembler-minted C4 model (ids + badges).

Asserts the c4-XXXXXXXX node-id and c4e-XXXXXXXX edge-id patterns (mirroring the
attack-path/findings sha8 minting scheme), the level/kind enums, the
finding_count/capability_count badge ints, analysis_state honesty, and the
build_summary tallies. Validates a fully-written example and rejects bad ones.
"""
from __future__ import annotations

import json
import pathlib

from jsonschema import Draft202012Validator

REPO = pathlib.Path(__file__).resolve().parent.parent
SCHEMA = REPO / "schemas" / "c4-model.schema.json"


def _validator() -> Draft202012Validator:
    return Draft202012Validator(json.loads(SCHEMA.read_text()))


# A fully-written c4-model.yaml: a system node, the HA Core container (analyzed,
# 3 findings / 1 capability), an os-agent container (analyzed), a not_analyzed
# container (0 badges, NOT "0 findings = clean" — the honesty rule), one L4 code
# node under core, and one uses edge core->os-agent. ids are real 8-hex shapes.
GOOD = {
    "schema_version": 1,
    "generated_by": "assemble_c4",
    "nodes": [
        {
            "id": "c4-1a2b3c4d", "level": "system", "parent": None,
            "name": "Home Assistant", "kind": "software_system",
            "provenance": {"source": "asset_inventory", "locator": "asset-graph.yaml#system"},
            "finding_count": 0, "capability_count": 0, "analysis_state": "analyzed",
        },
        {
            "id": "c4-5e6f7a8b", "level": "container", "parent": "c4-1a2b3c4d",
            "name": "core", "kind": "service",
            "provenance": {
                "source": "code_evidence",
                "locator": "code-evidence-index.yaml#core",
                "repo": "home-assistant-repos-core",
                "machine_extracted": True,
            },
            "finding_count": 3, "capability_count": 1, "analysis_state": "analyzed",
        },
        {
            "id": "c4-9c0d1e2f", "level": "container", "parent": "c4-1a2b3c4d",
            "name": "os-agent", "kind": "compute",
            "provenance": {
                "source": "code_evidence",
                "locator": "code-evidence-index.yaml#os-agent",
            },
            "finding_count": 2, "capability_count": 0, "analysis_state": "analyzed",
        },
        {
            "id": "c4-3a4b5c6d", "level": "container", "parent": "c4-1a2b3c4d",
            "name": "plugin-dns", "kind": "service",
            "provenance": {"source": "artifact", "locator": "code-architecture-brief.md#repos"},
            "finding_count": 0, "capability_count": 0, "analysis_state": "not_analyzed",
        },
        {
            "id": "c4-7e8f9a0b", "level": "code", "parent": "c4-5e6f7a8b",
            "name": "homeassistant.auth.providers.homeassistant.async_validate_login",
            "kind": "function",
            "provenance": {
                "source": "code_evidence",
                "locator": "code:...:L120-L150@28076bc",
                "repo": "home-assistant-repos-core",
                "machine_extracted": True,
            },
            "finding_count": 1, "capability_count": 0, "analysis_state": "analyzed",
        },
    ],
    "edges": [
        {
            "id": "c4e-aabbccdd", "edge_type": "uses",
            "from": "c4-5e6f7a8b", "to": "c4-9c0d1e2f",
            "label": "invokes host-management D-Bus API", "machine_extracted": True,
            "provenance": {
                "source": "code_evidence",
                "locator": "code-evidence-index.yaml#CROSS_CHANNEL:core->os-agent",
            },
        }
    ],
    "build_summary": {
        "node_count": 5, "system_count": 1, "person_count": 0, "external_system_count": 0,
        "container_count": 3, "component_count": 0, "code_count": 1, "uses_edge_count": 1,
        "unlocalized_finding_count": 4, "not_analyzed_container_count": 1,
    },
}


def test_good_c4_model_validates_clean():
    assert list(_validator().iter_errors(GOOD)) == []


def test_rejects_bad_node_id_prefix():
    doc = json.loads(json.dumps(GOOD))
    doc["nodes"][0]["id"] = "node-1a2b3c4d"  # must be c4-XXXXXXXX
    assert list(_validator().iter_errors(doc))


def test_rejects_short_node_id_hash():
    doc = json.loads(json.dumps(GOOD))
    doc["nodes"][0]["id"] = "c4-1a2b"  # 4 hex, must be 8
    assert list(_validator().iter_errors(doc))


def test_rejects_bad_edge_id_prefix():
    doc = json.loads(json.dumps(GOOD))
    doc["edges"][0]["id"] = "c4-aabbccdd"  # edges are c4e-, not c4-
    assert list(_validator().iter_errors(doc))


def test_rejects_unknown_level():
    doc = json.loads(json.dumps(GOOD))
    doc["nodes"][0]["level"] = "module"  # not in level enum
    assert list(_validator().iter_errors(doc))


def test_rejects_non_uses_edge_type():
    doc = json.loads(json.dumps(GOOD))
    doc["edges"][0]["edge_type"] = "contains"  # only "uses" is allowed
    assert list(_validator().iter_errors(doc))


def test_rejects_negative_finding_count():
    doc = json.loads(json.dumps(GOOD))
    doc["nodes"][1]["finding_count"] = -1  # badge counts are >= 0
    assert list(_validator().iter_errors(doc))


def test_not_analyzed_with_zero_badges_is_valid():
    """0 findings on a not_analyzed container is HONEST, not a schema error."""
    doc = json.loads(json.dumps(GOOD))
    assert doc["nodes"][3]["analysis_state"] == "not_analyzed"
    assert doc["nodes"][3]["finding_count"] == 0
    assert list(_validator().iter_errors(doc)) == []


def test_rejects_unknown_build_summary_key():
    doc = json.loads(json.dumps(GOOD))
    # asset-graph spells it uses_edge_count here; bogus key rejected
    doc["build_summary"]["edge_count"] = 1
    assert list(_validator().iter_errors(doc))
