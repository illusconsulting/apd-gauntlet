"""Tests for compute_improvement_id + check_domain_improvement_id (§4.1 / §7.4)."""
from __future__ import annotations

import hashlib

from apd_gauntlet.linters import check_domain_improvement_id, compute_improvement_id


def _expected(itype, pack, tfile, ref):
    key = "|".join([itype, pack, tfile, ref]).lower()
    return "dimpr-" + hashlib.sha256(key.encode()).hexdigest()[:8]


def test_compute_improvement_id_matches_verbatim_payload():
    got = compute_improvement_id(
        "missing_crown_jewel", "api-security", "domain.yaml", "asset-1a2b3c4d"
    )
    assert got == _expected("missing_crown_jewel", "api-security", "domain.yaml", "asset-1a2b3c4d")


def test_compute_improvement_id_is_not_compute_id():
    """It does NOT reuse compute_id's (prefix, title, locator) 2-field payload."""
    from apd_gauntlet.linters import compute_id

    a = compute_improvement_id("missing_crown_jewel", "pbm", "domain.yaml", "asset-1a2b3c4d")
    b = compute_id("dimpr", "missing_crown_jewel", "asset-1a2b3c4d")
    assert a != b


def test_compute_improvement_id_lowercases_key():
    lower = compute_improvement_id("missing_crown_jewel", "pbm", "domain.yaml", "asset-1A2B")
    same = compute_improvement_id("missing_crown_jewel", "pbm", "domain.yaml", "asset-1a2b")
    assert lower == same


def _record(itype="missing_crown_jewel", pack="api-security",
            tfile="domain.yaml", ref="asset-1a2b3c4d", rid=None):
    rid = rid or compute_improvement_id(itype, pack, tfile, ref)
    return {
        "id": rid,
        "improvement_type": itype,
        "target_pack": pack,
        "target_file": tfile,
        "evidence": [{"kind": "asset_inventory", "ref": ref}],
    }


def test_check_passes_on_matching_id():
    assert check_domain_improvement_id(_record()) == []


def test_check_flags_mismatched_id():
    rec = _record(rid="dimpr-deadbeef")
    msgs = check_domain_improvement_id(rec)
    assert msgs and "id mismatch" in msgs[0]


def test_check_uses_first_evidence_ref():
    rec = _record()
    rec["evidence"].insert(0, {"kind": "finding", "ref": "conf-00000000"})
    # id was computed from the (now-second) asset ref, so prepending a finding
    # ref makes primary_ref the finding ref -> mismatch.
    assert check_domain_improvement_id(rec)
