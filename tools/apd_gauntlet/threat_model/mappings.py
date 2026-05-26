"""Canonical methodology→APD-goal mapping tables.

This module is the single source of truth for how STRIDE letters,
LINDDUN categories, and attack-tree leaves map into the nine APD goals.
Both Python parser code (Tasks B-12 through B-16) and the
apd-threat-model-methodologies skill (Task B-19) reference these tables.
"""

from __future__ import annotations

from collections.abc import Mapping

STRIDE_TO_APD_GOALS: Mapping[str, list[str]] = {
    "S": ["authenticity"],
    "T": ["integrity"],
    "R": ["non_repudiation"],
    "I": ["confidentiality"],
    "D": ["availability"],
    "E": ["authenticity", "integrity"],
}

LINDDUN_TO_APD_GOALS: Mapping[str, list[str]] = {
    "L":              ["confidentiality"],
    "I":              ["confidentiality"],
    "N_repudiation":  ["non_repudiation"],
    "D_etectability": ["confidentiality"],
    "D_isclosure":    ["confidentiality"],
    "U":              ["authenticity"],
    "N_compliance":   ["non_repudiation"],
}


def stride_letter_to_apd_goals(letter: str) -> list[str]:
    """Return a fresh list of APD-goal names for the given STRIDE letter.

    Unknown letters return an empty list. The returned list is a copy of
    the canonical entry, safe for the caller to mutate.
    """
    return list(STRIDE_TO_APD_GOALS.get(letter, []))


def linddun_letter_to_apd_goals(letter_or_compound: str) -> list[str]:
    """Return a fresh list of APD-goal names for the given LINDDUN key.

    Accepts the compound-key form used by the LINDDUN parser
    (``L``, ``I``, ``N_repudiation``, ``D_etectability``, ``D_isclosure``,
    ``U``, ``N_compliance``). Unknown keys return an empty list.
    """
    return list(LINDDUN_TO_APD_GOALS.get(letter_or_compound, []))
