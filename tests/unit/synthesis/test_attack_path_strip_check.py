# tests/unit/synthesis/test_attack_path_strip_check.py
from __future__ import annotations

from apd_gauntlet.synthesis.audit import _attack_path_strip_status


def test_exempt_when_no_risk_apath_findings():
    ok, detail = _attack_path_strip_status(apath_findings=[], data_findings=[])
    assert ok is True and "exempt" in detail


def test_pass_when_risk_apath_has_strip_in_data_js():
    apath = [{"id": "apath-1", "disposition": "risk"}]
    data = [{"id": "apath-1", "attack_path": {"path_id": "path-1", "hops": []}}]
    ok, _ = _attack_path_strip_status(apath_findings=apath, data_findings=data)
    assert ok is True


def test_fail_when_risk_apath_present_but_no_strip_reached_data_js():
    apath = [{"id": "apath-1", "disposition": "risk"}]
    data = [{"id": "apath-1"}]  # no attack_path block
    ok, detail = _attack_path_strip_status(apath_findings=apath, data_findings=data)
    assert ok is False and "0" in detail
