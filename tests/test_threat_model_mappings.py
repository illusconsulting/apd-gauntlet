"""Tests for the canonical methodology→APD-goal mapping tables."""
from __future__ import annotations

from apd_gauntlet.threat_model.mappings import (
    LINDDUN_TO_APD_GOALS,
    MAESTRO_TO_APD_GOALS,
    STRIDE_TO_APD_GOALS,
    linddun_letter_to_apd_goals,
    maestro_layer_to_apd_goals,
    stride_letter_to_apd_goals,
)


def test_stride_to_apd_goals_complete():
    assert dict(STRIDE_TO_APD_GOALS) == {
        "S": ["authenticity"],
        "T": ["integrity"],
        "R": ["non_repudiation"],
        "I": ["confidentiality"],
        "D": ["availability"],
        "E": ["authenticity", "integrity"],
    }


def test_linddun_to_apd_goals_complete():
    assert dict(LINDDUN_TO_APD_GOALS) == {
        "L":              ["confidentiality"],
        "I":              ["confidentiality"],
        "N_repudiation":  ["non_repudiation"],
        "D_etectability": ["confidentiality"],
        "D_isclosure":    ["confidentiality"],
        "U":              ["authenticity"],
        "N_compliance":   ["non_repudiation"],
    }


def test_stride_letter_lookup_returns_apd_goals():
    assert stride_letter_to_apd_goals("E") == ["authenticity", "integrity"]
    assert stride_letter_to_apd_goals("S") == ["authenticity"]
    assert stride_letter_to_apd_goals("X") == []  # unknown letter


def test_linddun_letter_lookup_returns_apd_goals():
    assert linddun_letter_to_apd_goals("L") == ["confidentiality"]
    assert linddun_letter_to_apd_goals("N_repudiation") == ["non_repudiation"]
    assert linddun_letter_to_apd_goals("N_compliance") == ["non_repudiation"]
    assert linddun_letter_to_apd_goals("BOGUS") == []  # unknown returns empty


def test_stride_letter_lookup_returns_fresh_list_each_call():
    """Mutating the returned list must not corrupt the canonical table."""
    first = stride_letter_to_apd_goals("E")
    first.append("availability")
    second = stride_letter_to_apd_goals("E")
    assert second == ["authenticity", "integrity"]


def test_maestro_to_apd_goals_complete():
    assert dict(MAESTRO_TO_APD_GOALS) == {
        "L1": ["integrity", "confidentiality"],
        "L2": ["integrity", "confidentiality"],
        "L3": ["authenticity", "integrity"],
        "L4": ["availability", "confidentiality", "resilient"],
        "L5": ["non_repudiation", "immutability"],
        "L6": ["non_repudiation"],
        "L7": ["authenticity", "confidentiality", "distributed"],
    }


def test_maestro_layer_lookup_returns_apd_goals():
    assert maestro_layer_to_apd_goals("L1") == ["integrity", "confidentiality"]
    assert maestro_layer_to_apd_goals("L7") == ["authenticity", "confidentiality", "distributed"]
    assert maestro_layer_to_apd_goals("L9") == []  # unknown layer
    assert maestro_layer_to_apd_goals("") == []


def test_maestro_layer_lookup_returns_fresh_list_each_call():
    first = maestro_layer_to_apd_goals("L4")
    first.append("integrity")
    second = maestro_layer_to_apd_goals("L4")
    assert second == ["availability", "confidentiality", "resilient"]
