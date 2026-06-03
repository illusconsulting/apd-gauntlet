"""Threat-model block transform — authored baseline + supplied comparator."""
from __future__ import annotations

from apd_gauntlet.report.loader import RunArtifacts
from apd_gauntlet.report.transform import threat_model_block


def _artifacts(
    *,
    normalized: dict | None,
    supplied: dict | None,
) -> RunArtifacts:
    return RunArtifacts(
        run_id="r",
        framework_version="1.6.0",
        domain_pack_name="pbm",
        domain_pack_version="1.0.0",
        subject="s",
        date="2026-06-03",
        asset_inventory={},
        deduped_findings=[],
        deduped_capabilities=[],
        contradictions=[],
        contradictions_notes=None,
        severity_disagreements=[],
        severity_disagreements_notes=None,
        nist_coverage={},
        attack_exposure={},
        apd_coverage_matrix={},
        attack_paths=None,
        asset_graph=None,
        defense_graph=None,
        attack_path_findings=[],
        report_data=None,
        threat_model_normalized=normalized,
        threat_model_supplied=supplied,
    )


def test_no_threat_model_returns_absent_block() -> None:
    block = threat_model_block(_artifacts(normalized=None, supplied=None))
    assert block == {
        "present": False,
        "authored": False,
        "supplied_present": False,
        "comparator": False,
        "entry_count": 0,
        "generated_by": None,
    }


def test_authored_baseline_recognized() -> None:
    block = threat_model_block(_artifacts(
        normalized={
            "generated_by": "threat_model_author",
            "entries": [{"entry_id": "tm-00000000"}, {"entry_id": "tm-11111111"}],
        },
        supplied=None,
    ))
    assert block["present"] is True
    assert block["authored"] is True
    assert block["supplied_present"] is False
    assert block["comparator"] is False
    assert block["entry_count"] == 2
    assert block["generated_by"] == "threat_model_author"


def test_supplied_present_enables_comparator() -> None:
    block = threat_model_block(_artifacts(
        normalized={
            "generated_by": "threat_model_author",
            "entries": [{"entry_id": "tm-00000000"}],
        },
        supplied={
            "generated_by": "threat_model_recon",
            "entries": [{"entry_id": "tm-22222222"}],
        },
    ))
    assert block["authored"] is True
    assert block["supplied_present"] is True
    assert block["comparator"] is True


def test_recon_canonical_plus_supplied_is_not_comparator() -> None:
    # Legacy/transitional: a recon-parsed canonical TM + a supplied sibling must
    # NOT be a comparator (the comparator is supplied-vs-AUTHORED only, spec C6).
    block = threat_model_block(_artifacts(
        normalized={"generated_by": "threat_model_recon", "entries": [{"entry_id": "tm-33333333"}]},
        supplied={"generated_by": "threat_model_recon", "entries": [{"entry_id": "tm-44444444"}]},
    ))
    assert block["authored"] is False
    assert block["supplied_present"] is True
    assert block["comparator"] is False


def test_recon_only_baseline_not_marked_authored() -> None:
    block = threat_model_block(_artifacts(
        normalized={"generated_by": "threat_model_recon", "entries": []},
        supplied=None,
    ))
    assert block["present"] is True
    assert block["authored"] is False
    assert block["generated_by"] == "threat_model_recon"
