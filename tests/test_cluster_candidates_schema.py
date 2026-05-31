"""cluster-candidates schema: accepts a minimal valid candidate doc, rejects bad signals."""
from __future__ import annotations

import json
import pathlib

from jsonschema import Draft202012Validator

REPO = pathlib.Path(__file__).parent.parent
SCHEMA = REPO / "schemas" / "cluster-candidates.schema.json"


def _validator():
    return Draft202012Validator(json.loads(SCHEMA.read_text()))


def _group(**over):
    base = {
        "group_id": "cluster-cand-0001",
        "kind": "finding",
        "signals": ["evidence_locator_overlap"],
        "members": [
            {"id": "conf-7aa376c5", "agent": "confidentiality", "apd_goal": "confidentiality",
             "severity": "high", "title": "x" * 12, "summary": "y" * 12,
             "first_evidence": {"artifact": "a.md", "locator": "L", "excerpt": "e"},
             "related_concerns": ["integrity"],
             "mapping_ids": {"nist": ["SC-8(1)"], "attack": ["T1530"]}},
            {"id": "intg-42a3ebbd", "agent": "integrity", "apd_goal": "integrity",
             "severity": "high", "title": "x" * 12, "summary": "y" * 12,
             "first_evidence": {"artifact": "a.md", "locator": "L", "excerpt": "e"},
             "related_concerns": ["confidentiality"],
             "mapping_ids": {"nist": [], "attack": []}},
        ],
    }
    base.update(over)
    return base


def test_minimal_valid_doc():
    doc = {"schema_version": 1, "generated_by": "apd-gauntlet", "groups": [_group()]}
    assert list(_validator().iter_errors(doc)) == []


def test_rejects_bad_generated_by():
    doc = {"schema_version": 1, "generated_by": "synthesizer", "groups": [_group()]}
    assert list(_validator().iter_errors(doc))


def test_rejects_single_member_group():
    doc = {"schema_version": 1, "generated_by": "apd-gauntlet",
           "groups": [_group(members=[_group()["members"][0]])]}
    assert list(_validator().iter_errors(doc))  # minItems: 2


def test_rejects_unknown_signal():
    doc = {"schema_version": 1, "generated_by": "apd-gauntlet",
           "groups": [_group(signals=["nist_overlap"])]}
    assert list(_validator().iter_errors(doc))  # control overlap is NOT a signal
