"""refresh-crosswalks: ground the control-level compliance crosswalks against the
authoritative NIST CPRT exports (ADR-0022).

The CPRT CSF 2.0 export maps each subcategory to 800-53 *families* (family-level);
the 800-66r2 export has no control-level HIPAA mapping. So this tool does not
*replace* the curated control-level crosswalks — it VALIDATES that every curated
(target -> control) mapping is a subset of NIST's stated references, drops any
that exceed NIST's scope, and enriches target titles from the real export.
"""
from __future__ import annotations

from apd_gauntlet.refresh_crosswalks import (
    csf2_family_index,
    ground_csf2,
    ground_hipaa,
)

# Minimal CPRT-shaped fixtures (response.elements.{elements, relationships}).
CSF2_CPRT = {
    "response": {"elements": {
        "elements": [
            {"element_identifier": "PR.AA-05", "element_type": "subcategory",
             "title": "", "text": "Access permissions are managed"},
            {"element_identifier": "PR.DS-01", "element_type": "subcategory",
             "title": "", "text": "Data-at-rest is protected"},
        ],
        "relationships": [
            # PR.AA-05 -> AC, IA families (800-53)
            {"source_element_identifier": "PR.AA-05", "dest_element_identifier": "AC",
             "dest_doc_identifier": "SP_800_53_5_1_1",
             "relationship_identifier": "external_reference"},
            {"source_element_identifier": "PR.AA-05", "dest_element_identifier": "IA",
             "dest_doc_identifier": "SP_800_53_5_1_1",
             "relationship_identifier": "external_reference"},
            {"source_element_identifier": "PR.DS-01", "dest_element_identifier": "SC",
             "dest_doc_identifier": "SP_800_53_5_1_1",
             "relationship_identifier": "external_reference"},
            # an internal (non-800-53) rel that must be ignored
            {"source_element_identifier": "PR.AA-05", "dest_element_identifier": "PR.AA",
             "dest_doc_identifier": "CSF_2_0_0", "relationship_identifier": "projection"},
        ],
    }},
}

HIPAA_CPRT = {
    "response": {"elements": {
        "elements": [
            {"element_identifier": "164.312(b)", "element_type": "standard",
             "title": "Audit Controls", "text": ""},
        ],
        "relationships": [],
    }},
}


def test_csf2_family_index_extracts_only_800_53_external_references():
    idx = csf2_family_index(CSF2_CPRT)
    assert idx["PR.AA-05"] == {"AC", "IA"}
    assert idx["PR.DS-01"] == {"SC"}
    # the internal projection rel is not a family reference
    assert "PR.AA" not in idx["PR.AA-05"]


def test_ground_csf2_keeps_in_scope_controls_and_enriches_title():
    curated = {"PR.AA-05": ["AC-3", "AC-6"]}
    mappings, dropped = ground_csf2(curated, CSF2_CPRT)
    assert dropped == []
    by_ctrl = {m["nist"]: m for m in mappings}
    assert set(by_ctrl) == {"AC-3", "AC-6"}
    assert by_ctrl["AC-3"]["target_id"] == "PR.AA-05"
    # title enriched from the CPRT subcategory text
    assert by_ctrl["AC-3"]["target_title"] == "Access permissions are managed"
    assert by_ctrl["AC-3"]["relationship"] == "intersects_with"


def test_ground_csf2_drops_controls_outside_nist_family_scope():
    # SI-7's family SI is NOT in PR.AA-05's authoritative refs {AC, IA} -> dropped.
    curated = {"PR.AA-05": ["AC-3", "SI-7"]}
    mappings, dropped = ground_csf2(curated, CSF2_CPRT)
    assert [m["nist"] for m in mappings] == ["AC-3"]
    assert len(dropped) == 1
    assert dropped[0]["target_id"] == "PR.AA-05" and dropped[0]["nist"] == "SI-7"
    assert "SI" in dropped[0]["reason"]


def test_ground_csf2_drops_subcategory_with_no_800_53_refs():
    # A subcategory NIST gives no 800-53 refs for -> every curated control dropped.
    curated = {"DE.AE-02": ["AU-6"]}
    mappings, dropped = ground_csf2(curated, CSF2_CPRT)
    assert mappings == []
    assert len(dropped) == 1


def test_ground_hipaa_validates_id_and_enriches_title():
    curated = {"164.312(b)": ("Audit Controls (curated)", ["AU-2", "AU-12"])}
    mappings, unmatched = ground_hipaa(curated, HIPAA_CPRT)
    by_ctrl = {m["nist"]: m for m in mappings}
    assert set(by_ctrl) == {"AU-2", "AU-12"}
    # title comes from the authoritative export, not the curated fallback
    assert by_ctrl["AU-2"]["target_title"] == "Audit Controls"
    assert unmatched == []


def test_ground_hipaa_keeps_curated_title_when_id_absent_from_export():
    curated = {"164.312(a)(1)": ("Access Control", ["AC-3"])}
    mappings, unmatched = ground_hipaa(curated, HIPAA_CPRT)
    assert mappings[0]["target_title"] == "Access Control"
    assert unmatched == ["164.312(a)(1)"]


def test_refresh_crosswalks_writes_both_files_with_provenance(tmp_path):
    import json

    from apd_gauntlet.refresh_crosswalks import refresh_crosswalks
    csf2_path = tmp_path / "csf2.json"
    csf2_path.write_text(json.dumps(CSF2_CPRT), encoding="utf-8")
    hipaa_path = tmp_path / "hipaa.json"
    hipaa_path.write_text(json.dumps(HIPAA_CPRT), encoding="utf-8")
    data_dir = tmp_path / "data"
    report = refresh_crosswalks(csf2_path, hipaa_path, data_dir=data_dir)
    assert "csf2" in report and "hipaa" in report
    for name in ("csf2-800-53-crosswalk.json", "hipaa-800-53-crosswalk.json"):
        doc = json.loads((data_dir / name).read_text())
        # provenance the freshness gate requires (source + hash + fetched_at)
        assert doc["_meta"]["source"]
        assert len(doc["_meta"]["source_sha256"]) == 64
        assert doc["_meta"]["fetched_at"]
        assert isinstance(doc["mappings"], list)
