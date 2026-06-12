import hashlib

import pytest
from apd_gauntlet.linters import check_tmeval_id, compute_tmeval_id


def _sha8(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()[:8]


def test_supplied_omission_form():
    key = {"flavor": "supplied_omission", "tm_entry_id": "tm-7"}
    assert compute_tmeval_id(key) == "tmeval-" + _sha8("supplied_omission|tm-7")


def test_coverage_gap_form():
    key = {"flavor": "coverage_gap", "surface": "ingest-api", "goal": "confidentiality"}
    assert compute_tmeval_id(key) == "tmeval-" + _sha8("coverage_gap|ingest-api|confidentiality")


def test_contradiction_form():
    key = {
        "flavor": "contradiction",
        "tm_entry_id": "tm-3",
        "contradicting_finding_id": "conf-aabbccdd",
    }
    assert compute_tmeval_id(key) == "tmeval-" + _sha8("contradiction|tm-3|conf-aabbccdd")


def test_silence_form():
    key = {"flavor": "silence", "surface": "worker"}
    assert compute_tmeval_id(key) == "tmeval-" + _sha8("silence|worker")


def test_blocked_form():
    key = {"flavor": "blocked", "source_artifact": "inputs/tm.md"}
    assert compute_tmeval_id(key) == "tmeval-" + _sha8("blocked|inputs/tm.md")


def test_unknown_flavor_raises():
    with pytest.raises(ValueError):
        compute_tmeval_id({"flavor": "nope"})


def test_missing_component_raises():
    with pytest.raises(ValueError):
        compute_tmeval_id({"flavor": "coverage_gap", "surface": "x"})  # missing goal


def test_check_tmeval_id_passes_when_consistent():
    key = {"flavor": "silence", "surface": "worker"}
    rec = {"agent": "threat_model_evaluator", "tmeval_key": key, "id": compute_tmeval_id(key)}
    assert check_tmeval_id(rec) == []


def test_check_tmeval_id_flags_mismatch():
    key = {"flavor": "silence", "surface": "worker"}
    rec = {"agent": "threat_model_evaluator", "tmeval_key": key, "id": "tmeval-00000000"}
    assert check_tmeval_id(rec) != []


def test_check_tmeval_id_ignores_non_tmeval():
    assert check_tmeval_id({"agent": "confidentiality", "id": "conf-12345678"}) == []
