"""measure.match: title/asset normalisation and deterministic one-to-one matching."""
from __future__ import annotations

import pathlib

import pytest
from apd_gauntlet.measure.match import (
    TITLE_MIN_JACCARD,
    Match,
    MatchResult,
    asset_keys,
    evidence_pairs,
    jaccard,
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


def test_title_threshold_is_one_half():
    assert TITLE_MIN_JACCARD == 0.5


@pytest.mark.parametrize(
    ("baseline_title", "candidate_title"),
    [
        ("Refresh tokens never", "Refresh tokens rotate weekly"),            # Jaccard 2/5
        ("alpha bravo charlie delta echo foxtrot",
         "alpha bravo charlie delta golf hotel india"),                      # Jaccard 4/9
    ],
)
def test_title_jaccard_below_threshold_does_not_match(baseline_title, candidate_title):
    b = {"b": rec("b", "ephemeral", baseline_title, ("a.md", "#x"))}
    c = {"c": rec("c", "ephemeral", candidate_title, ("a.md", "#x"))}
    assert match_records(b, c) == MatchResult((), ("b",), ("c",))


# --- review fixes (Task 1, second round) ------------------------------------


def test_evidence_pairs_normalise_the_artifact_and_strip_the_locator():
    r = rec("x", "g", "t", (".\\./Inputs\\A.md", "  #sec  "), ("b.md", "code:pkg.Fn"))
    assert evidence_pairs(r) == frozenset({("inputs/a.md", "#sec"), ("b.md", "code:pkg.Fn")})


def test_jaccard_of_two_empty_sets_is_zero():
    assert jaccard(frozenset(), frozenset()) == 0.0


def test_stopword_only_titles_never_match():
    b = {"b": rec("b", "ephemeral", "The of a", ("a.md", "#x"))}
    c = {"c": rec("c", "ephemeral", "the OF A", ("a.md", "#x"))}
    assert match_records(b, c) == MatchResult((), ("b",), ("c",))


def test_record_without_assets_never_matches():
    r = {"id": "r", "apd_goal": "ephemeral", "title": TITLE}
    assert match_records({"r": r}, {"r": r}) == MatchResult((), ("r",), ("r",))


def test_missing_and_new_ids_are_sorted():
    b = {"z": rec("z", "ephemeral", TITLE, ("z.md", "#x")),
         "a": rec("a", "ephemeral", TITLE, ("a.md", "#x"))}
    c = {"y": rec("y", "ephemeral", TITLE, ("y.md", "#x")),
         "b": rec("b", "ephemeral", TITLE, ("b.md", "#x"))}
    assert match_records(b, c) == MatchResult((), ("a", "z"), ("b", "y"))


def test_matched_is_sorted_by_id_not_by_pick_order():
    # The greedy pass takes (b2, c2) first (title 1.0), then (b1, c1) (title 0.6).
    other = "Session cookie lacks secure flag"
    b = {"b2": rec("b2", "ephemeral", other, ("b.md", "#x")),
         "b1": rec("b1", "ephemeral", TITLE, ("a.md", "#x"))}
    c = {"c2": rec("c2", "ephemeral", other, ("b.md", "#x")),
         "c1": rec("c1", "ephemeral", "Refresh tokens are never rotated", ("a.md", "#x"))}
    r = match_records(b, c)
    assert [(m.baseline_id, m.candidate_id) for m in r.matched] == [("b1", "c1"), ("b2", "c2")]
    assert r.matched[0].title_similarity == pytest.approx(0.6)
    assert r.matched[1].title_similarity == 1.0
