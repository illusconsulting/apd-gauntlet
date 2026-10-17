"""measure.match: title/asset normalisation and deterministic one-to-one matching."""
from __future__ import annotations

import pathlib

import pytest
from apd_gauntlet.measure.match import (
    Match,
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


# --- review fixes (Task 1) -------------------------------------------------

TITLE = "Refresh tokens never rotate"


def test_title_tokens_applies_nfkc_and_splits_underscores():
    # NFKC folds full-width letters and the "fi" ligature; "_" separates words.
    assert title_tokens("ＴＬＳ_cert-rotation ﬁle") == frozenset(
        {"tls", "cert", "rotation", "file"})


@pytest.mark.parametrize(
    "locator", ["code:pkg.Mod.Fn@abc", "code:pkg.Mod.Fn", " code:pkg.Mod.Fn:L1-L9 "])
def test_code_locator_keys_on_the_symbol_with_or_without_a_line_range(locator):
    r = rec("conf-00000001", "confidentiality", "t", ("code-evidence-index.yaml", locator))
    assert asset_keys(r, {}) == frozenset({"code:pkg.mod.fn"})


def test_more_asset_overlap_wins_a_title_tie():
    b = {"b": rec("b", "ephemeral", TITLE, ("a.md", "#x"), ("b.md", "#x"))}
    c = {"c1": rec("c1", "ephemeral", TITLE, ("a.md", "#x")),
         "c2": rec("c2", "ephemeral", TITLE, ("a.md", "#x"), ("b.md", "#x"))}
    assert match_records(b, c) == MatchResult((Match("b", "c2", 1.0, 1.0),), (), ("c1",))


def test_same_id_pair_wins_a_full_tie():
    b = {"a": rec("a", "ephemeral", TITLE, ("a.md", "#x")),
         "m": rec("m", "ephemeral", TITLE, ("a.md", "#x"))}
    c = {"m": rec("m", "ephemeral", TITLE, ("a.md", "#x"))}
    assert match_records(b, c) == MatchResult((Match("m", "m", 1.0, 1.0),), ("a",), ())


def test_lower_ids_win_a_full_tie():
    b = {"b2": rec("b2", "ephemeral", TITLE, ("a.md", "#x")),
         "b1": rec("b1", "ephemeral", TITLE, ("a.md", "#x"))}
    c = {"c2": rec("c2", "ephemeral", TITLE, ("a.md", "#x"))}
    assert match_records(b, c) == MatchResult((Match("b1", "c2", 1.0, 1.0),), ("b2",), ())
    c = {"c2": rec("c2", "ephemeral", TITLE, ("a.md", "#x")),
         "c1": rec("c1", "ephemeral", TITLE, ("a.md", "#x"))}
    assert match_records({"b1": b["b1"]}, c) == MatchResult(
        (Match("b1", "c1", 1.0, 1.0),), (), ("c2",))


def test_result_does_not_depend_on_insertion_order():
    recs = [rec(rid, "ephemeral", TITLE, ("a.md", "#x")) for rid in ("r3", "r1", "r2")]
    forward = {r["id"]: r for r in recs}
    backward = {r["id"]: r for r in reversed(recs)}
    cand = {"r9": rec("r9", "ephemeral", TITLE, ("a.md", "#x")),
            "r0": rec("r0", "ephemeral", TITLE, ("a.md", "#x"))}
    cand_rev = dict(reversed(list(cand.items())))
    expected = MatchResult(
        (Match("r1", "r0", 1.0, 1.0), Match("r2", "r9", 1.0, 1.0)), ("r3",), ())
    assert match_records(forward, cand) == expected
    assert match_records(backward, cand_rev) == expected


def test_title_jaccard_exactly_at_threshold_matches():
    b = {"b": rec("b", "ephemeral", "Refresh tokens never", ("a.md", "#x"))}
    c = {"c": rec("c", "ephemeral", "Refresh tokens rotate", ("a.md", "#x"))}
    (m,) = match_records(b, c).matched
    assert m.title_similarity == 0.5
