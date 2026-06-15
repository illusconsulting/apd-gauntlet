"""cluster-decisions schema: merge/link/separate decisions + contradictions."""
from __future__ import annotations

import json
import pathlib

from jsonschema import Draft202012Validator
from referencing import Registry, Resource

REPO = pathlib.Path(__file__).parent.parent
SCHEMA_DIR = REPO / "schemas"
SCHEMA = SCHEMA_DIR / "cluster-decisions.schema.json"


def _build_registry():
    # cluster-decisions now $refs _defs.schema.json (chosen_severity); the
    # registry must carry every schema by $id so the cross-file ref resolves.
    resources = []
    for schema_path in sorted(SCHEMA_DIR.glob("*.schema.json")):
        schema = json.loads(schema_path.read_text())
        sid = schema.get("$id")
        if sid:
            resources.append((sid, Resource.from_contents(schema)))
    return Registry().with_resources(resources)


def _validator():
    return Draft202012Validator(json.loads(SCHEMA.read_text()), registry=_build_registry())


def test_minimal_merge_decision():
    doc = {
        "schema_version": 1,
        "generated_by": "apd-cluster-adjudicator",
        "decisions": [{
            "group_id": "cluster-cand-0001",
            "decision": "merge",
            "merged_title": "x" * 12,
            "merged_summary": "y" * 12,
            "merged_detail": "z" * 21,
            "merged_recommendation": {
                "posture": "required", "summary": "s" * 12, "detail": "d" * 21
            },
            "lens_perspectives": {
                "non_repudiation": {"summary": "a" * 5, "detail": "b" * 5},
                "immutability": {"summary": "a" * 5, "detail": "b" * 5},
            },
            "chosen_severity": "critical",
            "severity_rationale": "elevated " * 5,
        }],
    }
    assert list(_validator().iter_errors(doc)) == []


def test_separate_decision_is_minimal():
    doc = {"schema_version": 1, "generated_by": "apd-cluster-adjudicator",
           "decisions": [{"group_id": "cluster-cand-0002", "decision": "separate"}]}
    assert list(_validator().iter_errors(doc)) == []


def test_rejects_bad_decision():
    doc = {"schema_version": 1, "generated_by": "apd-cluster-adjudicator",
           "decisions": [{"group_id": "g", "decision": "combine"}]}
    assert list(_validator().iter_errors(doc))


def test_contradiction_classification_enum():
    doc = {"schema_version": 1, "generated_by": "apd-cluster-adjudicator", "decisions": [],
           "contradictions": [{"finding_id": "conf-7aa376c5", "capability_id": "conf-cap-89e19793",
                               "classification": "stale",
                               "finding_assertion": "a" * 10,
                               "capability_assertion": "b" * 10,
                               "evidence_comparison": "c" * 30,
                               "recommended_resolution": "d" * 20}]}
    assert list(_validator().iter_errors(doc)) == []


def test_contradiction_rejects_short_assertions():
    """Short assertion strings must be REJECTED at the adjudicator's output boundary."""
    doc = {"schema_version": 1, "generated_by": "apd-cluster-adjudicator", "decisions": [],
           "contradictions": [{"finding_id": "conf-7aa376c5", "capability_id": "conf-cap-89e19793",
                               "classification": "contradicted",
                               "finding_assertion": "too short",   # only 9 chars < minLength 10
                               "capability_assertion": "b" * 10,
                               "evidence_comparison": "c" * 30,
                               "recommended_resolution": "d" * 20}]}
    assert list(_validator().iter_errors(doc))


def test_contradiction_accepts_adequate_assertions():
    """Assertions meeting all minLengths must be accepted."""
    doc = {
        "schema_version": 1,
        "generated_by": "apd-cluster-adjudicator",
        "decisions": [],
        "contradictions": [{
            "finding_id": "conf-7aa376c5",
            "capability_id": "conf-cap-89e19793",
            "classification": "compatible",
            "finding_assertion": "finding is adequate length",
            "capability_assertion": "capability is adequate",
            "evidence_comparison": "evidence comparison text is long enough here",
            "recommended_resolution": "recommendation text is ok",
        }],
    }
    assert list(_validator().iter_errors(doc)) == []


def test_top_level_members_map_validates_clean():
    # C3/C6: apply.py + the adjudicator agent + both fixtures carry a top-level
    # _members map keyed by group_id. The root is additionalProperties:false, so
    # the schema MUST declare _members or every real decisions doc fails
    # validate --schema-only (the workflow phaseDone guard).
    doc = {
        "schema_version": 1,
        "generated_by": "apd-cluster-adjudicator",
        "decisions": [{"group_id": "cluster-cand-0001", "decision": "merge",
                       "merged_title": "x" * 12, "merged_summary": "y" * 12,
                       "merged_detail": "z" * 21}],
        "_members": {"cluster-cand-0001": ["nonrep-62124087", "immut-e09e4945"]},
    }
    assert list(_validator().iter_errors(doc)) == []


def test_members_values_must_be_string_arrays():
    doc = {"schema_version": 1, "generated_by": "apd-cluster-adjudicator", "decisions": [],
           "_members": {"cluster-cand-0001": "not-a-list"}}
    assert list(_validator().iter_errors(doc))  # values must be arrays of strings
