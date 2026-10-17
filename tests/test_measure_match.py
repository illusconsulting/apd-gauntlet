"""measure.match: title/asset normalisation and deterministic one-to-one matching."""
from __future__ import annotations

import pathlib

import pytest
from apd_gauntlet.measure.match import (
    MatchResult,
    asset_keys,
    match_records,
    title_tokens,
)
from apd_gauntlet.measure.runs import load_run

REPO = pathlib.Path(__file__).parent.parent
HA = REPO / "examples/apd-20260612-home-assistant/expected"


def rec(rid, goal, title, *ev):
    return {"id": rid, "apd_goal": goal, "title": title,
            "evidence": [{"artifact": a, "locator": loc, "excerpt": "x"} for a, loc in ev]}


def test_title_tokens_normalises():
    assert title_tokens("Core .storage (auth) written as PLAINTEXT JSON") == frozenset(
        {"core", "storage", "auth", "written", "as", "plaintext", "json"})


def test_asset_keys_code_artifact_and_graph():
    r = rec("conf-00000001", "confidentiality", "t" * 10,
            ("code-evidence-index.yaml", "code:pkg.Mod.Fn:L1-L9@abc"),
            ("./inputs/Auth/Login.md", "#login, lines 3-4"))
    assert asset_keys(r, {"conf-00000001": ["Token  Store"]}) == frozenset(
        {"code:pkg.mod.fn", "artifact:inputs/auth/login.md", "graph:token store"})


def test_identical_runs_match_one_to_one():
    s = load_run(HA)
    r = match_records(s.findings, s.findings,
                      baseline_targets=s.graph_targets, candidate_targets=s.graph_targets)
    assert len(r.matched) == 94 and r.missing == () and r.new == ()
    assert all(m.baseline_id == m.candidate_id for m in r.matched)


def test_goal_is_a_hard_key():
    b = {"conf-00000001": rec("conf-00000001", "confidentiality",
                              "Plaintext token store on disk", ("a.md", "#x"))}
    c = {"intg-00000001": rec("intg-00000001", "integrity",
                              "Plaintext token store on disk", ("a.md", "#x"))}
    assert match_records(b, c) == MatchResult((), ("conf-00000001",), ("intg-00000001",))


def test_reworded_title_matches_at_threshold():
    b = {"b": rec("b", "ephemeral", "Refresh tokens never rotate", ("a.md", "#x"))}
    c = {"c": rec("c", "ephemeral", "Refresh tokens are never rotated", ("a.md", "#y"))}
    (m,) = match_records(b, c).matched
    assert m.title_similarity == pytest.approx(0.6)


def test_disjoint_assets_block_match():
    b = {"b": rec("b", "ephemeral", "Refresh tokens never rotate", ("a.md", "#x"))}
    c = {"c": rec("c", "ephemeral", "Refresh tokens never rotate", ("b.md", "#x"))}
    assert match_records(b, c).matched == ()
