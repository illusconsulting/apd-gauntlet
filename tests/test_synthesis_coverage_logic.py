"""coverage_logic: the deterministic NIST/posture helpers extracted from transform.py."""
from __future__ import annotations

from apd_gauntlet.synthesis import coverage_logic as cl


def test_normalize_nist_id_canonicalizes():
    assert cl.normalize_nist_id("ac-3") == "AC-3"
    assert cl.normalize_nist_id("SC-7(5)") == "SC-7(5)"
    assert cl.normalize_nist_id("garbage") is None
    assert cl.normalize_nist_id(None) is None


def test_normalize_nist_ids_drops_invalid_preserves_order():
    assert cl.normalize_nist_ids(["sc-13", "junk", "au-9"]) == ["SC-13", "AU-9"]


def test_family_of():
    assert cl.nist_family_of("AC-2(2)") == "AC"
    assert cl.nist_family_of("SC-8") == "SC"


def test_posture_four_states():
    assert cl.posture(has_findings=True, has_caps=True) == "gapped_and_covered"
    assert cl.posture(has_findings=True, has_caps=False) == "gapped"
    assert cl.posture(has_findings=False, has_caps=True) == "covered"
    assert cl.posture(has_findings=False, has_caps=False) == "silent"


def test_goal_short_is_canonical_nine():
    assert list(cl.GOAL_SHORT.keys()) == [
        "confidentiality", "integrity", "availability",
        "distributed", "resilient", "ephemeral",
        "authenticity", "non_repudiation", "immutability",
    ]


def test_build_cap_controls_index_normalizes():
    caps = [{"id": "c1", "control_mappings": {"nist_800_53r5": ["ac-3", "sc-13"]}}]
    idx = cl.build_cap_controls_index(caps)
    assert idx == {"AC-3": {"c1"}, "SC-13": {"c1"}}


def test_transform_reimports_nist_leaf_helpers_from_coverage_logic():
    # transform.py must delegate the 3 NIST leaf helpers to coverage_logic.
    from apd_gauntlet.report import transform as t
    assert t._normalize_nist_id is cl.normalize_nist_id
    assert t._normalize_nist_ids is cl.normalize_nist_ids
    assert t._nist_family_of is cl.nist_family_of


def test_transform_keeps_its_warnings_aware_extract_sibling():
    # M1: transform._extract_ids_from_mapping is NOT aliased to the coverage_logic
    # sibling (it keeps the warnings= kwarg + name-fallback). Prove it is distinct.
    from apd_gauntlet.report import transform as t
    assert t._extract_ids_from_mapping is not cl.extract_ids_from_mapping
    warns: list[dict] = []
    out = t._extract_ids_from_mapping([{"name": "Some Control"}], warnings=warns)
    assert out == ["Some Control"]
    assert warns and warns[0]["issue"] == "mapping_id_missing_using_name"
