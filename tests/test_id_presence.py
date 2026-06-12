from apd_gauntlet.linters import check_id_present


def _rec(**kw):
    base = {
        "agent": "confidentiality",
        "title": "KMS key rotation absent",
        "evidence": [{"artifact": "tech_plan.md", "locator": "L42", "excerpt": "no rotation"}],
    }
    base.update(kw)
    return base


def test_in_scope_record_missing_id_is_flagged():
    msgs = check_id_present(_rec())  # no 'id'
    assert msgs and "missing tooling-authored id" in msgs[0]


def test_in_scope_record_with_id_passes():
    assert check_id_present(_rec(id="conf-1a2b3c4d")) == []


def test_out_of_scope_agent_is_not_flagged():
    assert check_id_present(_rec(agent="attack_path_analyzer")) == []


def test_record_without_evidence_is_not_flagged():
    assert check_id_present(_rec(evidence=[])) == []


def test_in_scope_record_with_evidence_but_no_locator_is_not_flagged():
    # locator-less evidence → no deterministic id computable → backstop skips
    assert check_id_present(_rec(evidence=[{"artifact": "tech_plan.md", "excerpt": "x"}])) == []
