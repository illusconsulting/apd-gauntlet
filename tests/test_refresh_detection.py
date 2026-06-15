"""ATT&CK detection overlay catalog projection (ADR-0022 derived overlay).

ATT&CK v17+ model: a ``detects`` relationship links an ``x-mitre-detection-strategy``
to a technique; the strategy's ``x_mitre_analytic_refs`` point at ``x-mitre-analytic``
objects whose ``x_mitre_log_source_references`` cite the ``x-mitre-data-component``
(``DC####``) telemetry. ``project_detection`` walks that chain to
{technique_id: [{data_component_id, data_component_name}]}.
"""
from __future__ import annotations

from apd_gauntlet.refresh_mitre import project_detection

BUNDLE = {
    "type": "bundle",
    "objects": [
        {"type": "attack-pattern", "id": "attack-pattern--t1",
         "name": "Data from Cloud Storage",
         "external_references": [{"source_name": "mitre-attack", "external_id": "T1530"}]},
        {"type": "x-mitre-data-component", "id": "dc--1", "name": "Cloud Storage Access",
         "external_references": [{"source_name": "mitre-attack", "external_id": "DC0010"}]},
        {"type": "x-mitre-data-component", "id": "dc--2", "name": "Cloud Storage Modification",
         "external_references": [{"source_name": "mitre-attack", "external_id": "DC0011"}]},
        {"type": "x-mitre-analytic", "id": "an--1", "name": "A",
         "x_mitre_log_source_references": [
             {"x_mitre_data_component_ref": "dc--1",
              "name": "aws:cloudtrail", "channel": "GetObject"},
             {"x_mitre_data_component_ref": "dc--2",
              "name": "aws:cloudtrail", "channel": "PutObject"},
             # A second reference to the same component (different channel) must dedupe.
             {"x_mitre_data_component_ref": "dc--1",
              "name": "aws:cloudtrail", "channel": "ListObjects"},
         ]},
        {"type": "x-mitre-detection-strategy", "id": "det--1", "name": "DET",
         "x_mitre_analytic_refs": ["an--1"]},
        {"type": "relationship", "relationship_type": "detects",
         "source_ref": "det--1", "target_ref": "attack-pattern--t1"},
        # A non-detects relationship must be ignored.
        {"type": "relationship", "relationship_type": "mitigates",
         "source_ref": "det--1", "target_ref": "attack-pattern--t1"},
    ],
}


def test_project_detection_maps_technique_to_data_components() -> None:
    det = project_detection(BUNDLE)
    assert "T1530" in det
    by_comp = {c["data_component_name"]: c for c in det["T1530"]}
    assert by_comp["Cloud Storage Access"]["data_component_id"] == "DC0010"
    assert by_comp["Cloud Storage Modification"]["data_component_id"] == "DC0011"


def test_project_detection_components_sorted_and_deduped() -> None:
    det = project_detection(BUNDLE)
    names = [c["data_component_name"] for c in det["T1530"]]
    assert names == sorted(names)
    assert len(names) == len(set(names)) == 2  # DC0010 cited twice -> deduped


def test_project_detection_ignores_non_detects_relationships() -> None:
    det = project_detection(BUNDLE)
    assert len(det["T1530"]) == 2
