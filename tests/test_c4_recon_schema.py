"""c4-recon schema: agent-authored (content-only) C4 reconnaissance input.

Mirrors test_cluster_decisions_schema.py: load the .schema.json, validate a
fully-written example doc, and prove a malformed doc is rejected. No fixtures —
the example docs are inline so the contract is self-documenting.
"""
from __future__ import annotations

import json
import pathlib

import yaml
from jsonschema import Draft202012Validator

REPO = pathlib.Path(__file__).resolve().parent.parent
SCHEMA = REPO / "schemas" / "c4-recon.schema.json"
FIXTURES = REPO / "tests" / "fixtures"


def _validator() -> Draft202012Validator:
    return Draft202012Validator(json.loads(SCHEMA.read_text()))


# A fully-written, grounded c4-recon.yaml modeled on the REAL Home Assistant run:
# two code-bearing containers (core analyzed, os-agent analyzed), one not_analyzed
# container (a 14/23 empty repo), one machine_extracted cross-repo 'uses' edge from
# a CROSS_* code edge, and one hand_read edge with a file_path locator. components
# is empty (L3 blocked: no artifact groups symbols).
GOOD = {
    "schema_version": 1,
    "generated_by": "code_recon",
    "containers": [
        {
            "name": "core",
            "kind": "service",
            "repo": "Users-shoveleejoe-Documents-GitHub-home-assistant-repos-core",
            "provenance": {"source": "code_evidence", "locator": "code-evidence-index.yaml#core"},
            "analysis_state": "analyzed",
        },
        {
            "name": "os-agent",
            "kind": "compute",
            "repo": "Users-shoveleejoe-Documents-GitHub-home-assistant-repos-os-agent",
            "provenance": {
                "source": "code_evidence",
                "locator": "code-evidence-index.yaml#os-agent",
            },
            "analysis_state": "analyzed",
        },
        {
            "name": "plugin-dns",
            "kind": "service",
            "repo": "Users-shoveleejoe-Documents-GitHub-home-assistant-repos-plugin-dns",
            "provenance": {"source": "artifact", "locator": "code-architecture-brief.md#repos"},
            "analysis_state": "not_analyzed",
        },
    ],
    "components": [],
    "uses_edges": [
        {
            "from": "core",
            "to": "os-agent",
            "label": "invokes host-management D-Bus API",
            "machine_extracted": True,
            "provenance": {
                "source": "code_evidence",
                "locator": "code-evidence-index.yaml#CROSS_CHANNEL:core->os-agent",
            },
        },
        {
            "from": "supervisor",
            "to": "core",
            "label": "proxies Core REST API",
            "machine_extracted": False,
            "provenance": {
                "source": "code_evidence",
                "locator": "supervisor/api/__init__.py:L40-L72",
            },
        },
    ],
}


def test_good_c4_recon_validates_clean():
    assert list(_validator().iter_errors(GOOD)) == []


def test_components_may_be_present_when_an_artifact_groups_symbols():
    doc = json.loads(json.dumps(GOOD))
    doc["components"] = [{
        "name": "auth-manager",
        "container": "core",
        "provenance": {"source": "artifact", "locator": "docs/component-map.md#auth-manager"},
    }]
    assert list(_validator().iter_errors(doc)) == []


def test_rejects_bad_generated_by():
    doc = json.loads(json.dumps(GOOD))
    doc["generated_by"] = "assemble_c4"  # wrong producer for a recon (input) doc
    errors = list(_validator().iter_errors(doc))
    assert errors
    assert any("generated_by" in str(e.path) or "generated_by" in e.message for e in errors)


def test_rejects_bad_container_kind():
    doc = json.loads(json.dumps(GOOD))
    doc["containers"][0]["kind"] = "microservice"  # not in the kind enum
    assert list(_validator().iter_errors(doc))


def test_rejects_bad_analysis_state():
    doc = json.loads(json.dumps(GOOD))
    doc["containers"][2]["analysis_state"] = "partial"  # only analyzed|not_analyzed
    assert list(_validator().iter_errors(doc))


def test_uses_edge_requires_machine_extracted_flag():
    doc = json.loads(json.dumps(GOOD))
    # the machine_extracted vs hand_read flag is mandatory
    del doc["uses_edges"][0]["machine_extracted"]
    errors = list(_validator().iter_errors(doc))
    assert errors
    assert any("machine_extracted" in e.message for e in errors)


def test_rejects_unknown_top_level_key():
    doc = json.loads(json.dumps(GOOD))
    doc["bogus"] = 1  # additionalProperties:false at the root
    assert list(_validator().iter_errors(doc))


# --- Fixture-driven tests for the authored home-assistant c4-recon.yaml example ---
# The tracked example fixture (tests/fixtures/valid/c4-recon.yaml) is the concrete
# apd-20260612-home-assistant C4 input the assemble-c4 step consumes; these tests
# pin its shape (9 containers, honest not_analyzed flag, 6 hand-read §5 edges, L3
# blocked) and prove the malformed sibling is rejected.


def test_valid_c4_recon_passes():
    data = yaml.safe_load((FIXTURES / "valid/c4-recon.yaml").read_text())
    errors = list(_validator().iter_errors(data))
    assert errors == [], [e.message for e in errors]


def test_home_assistant_example_has_nine_containers():
    data = yaml.safe_load((FIXTURES / "valid/c4-recon.yaml").read_text())
    assert len(data["containers"]) == 9


def test_home_assistant_example_has_not_analyzed_containers():
    data = yaml.safe_load((FIXTURES / "valid/c4-recon.yaml").read_text())
    states = {c["analysis_state"] for c in data["containers"]}
    assert "not_analyzed" in states, "honesty: at least one container is not_analyzed"
    assert "analyzed" in states


def test_home_assistant_example_has_six_uses_edges_all_hand_read():
    data = yaml.safe_load((FIXTURES / "valid/c4-recon.yaml").read_text())
    edges = data["uses_edges"]
    assert len(edges) == 6, "the six §5 cross-boundary edges from the brief"
    assert all(e["machine_extracted"] is False for e in edges), (
        "HA auto-linker found 0 CROSS_* edges; all six were hand-read"
    )


def test_l3_components_are_blocked_empty():
    data = yaml.safe_load((FIXTURES / "valid/c4-recon.yaml").read_text())
    assert data["components"] == [], "L3 is blocked: no artifact groups symbols"


def test_generated_by_is_code_recon():
    data = yaml.safe_load((FIXTURES / "valid/c4-recon.yaml").read_text())
    assert data["generated_by"] == "code_recon"
    assert data["schema_version"] == 1


def test_malformed_c4_recon_is_flagged():
    data = yaml.safe_load((FIXTURES / "invalid/c4-recon-malformed.yaml").read_text())
    errors = list(_validator().iter_errors(data))
    messages = " ".join(e.message for e in errors)
    # bad container kind enum
    assert "not-a-kind" in messages or "kind" in messages
    # bad analysis_state enum
    assert "maybe" in messages or "analysis_state" in messages
    # machine_extracted not a bool
    assert "yes" in messages or "machine_extracted" in messages
    # generated_by wrong const
    assert "intake" in messages or "generated_by" in messages
