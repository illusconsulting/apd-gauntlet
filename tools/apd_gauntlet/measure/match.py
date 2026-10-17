"""Deterministic one-to-one matching of findings (or capabilities) across two runs.

Finding records carry no asset field, so the asset a record is about is derived
from its evidence (a code symbol or a normalised artifact path) and from the
asset-graph nodes its edges target. Two records are a candidate pair when they
share an ``apd_goal``, at least one asset key, and a title token Jaccard of at
least ``TITLE_MIN_JACCARD``. Pairs are then taken greedily in a total order, so
the result never depends on dict or file order.
"""
from __future__ import annotations

import re
import unicodedata
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

STOPWORDS: frozenset[str] = frozenset(
    {
        "a", "an", "and", "are", "at", "be", "by", "for", "from", "in",
        "is", "of", "on", "or", "the", "to", "via", "with",
    }
)
TITLE_MIN_JACCARD: float = 0.5

_NON_WORD = re.compile(r"[\W_]+")
# A ``code:<qualified_name>[:Lx-Ly][@sha]`` locator; group 1 is the symbol, which
# stops at the first ':' or '@' (the grammar of assemble_c4._CODE_LOCATOR_RE).
_CODE_LOCATOR = re.compile(r"^code:([^:@]+)")


def title_tokens(title: str) -> frozenset[str]:
    """Return the casefolded word tokens of ``title`` without stopwords."""
    s = unicodedata.normalize("NFKC", title).casefold()
    s = _NON_WORD.sub(" ", s)
    return frozenset(t for t in s.split() if t not in STOPWORDS)


def _normalise_artifact(artifact: str) -> str:
    s = artifact.strip().replace("\\", "/")
    while s.startswith("./"):
        s = s[2:]
    return s.casefold()


def _evidence_items(record: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    raw = record.get("evidence")
    if not isinstance(raw, list):
        return []
    return [e for e in raw if isinstance(e, Mapping)]


def _text(value: Any) -> str:
    return value if isinstance(value, str) else ""


def asset_keys(
    record: Mapping[str, Any], graph_targets: Mapping[str, Sequence[str]]
) -> frozenset[str]:
    """Derive the asset keys of ``record``.

    Per evidence item: ``code:<symbol casefolded>`` when the locator is a
    ``code:<symbol>[:Lx-Ly][@sha]`` locator, else ``artifact:<normalised artifact>``. Plus
    ``graph:<node name>`` (casefolded, whitespace collapsed) for each asset-graph
    node an edge for this record's id points to.
    """
    keys: set[str] = set()
    for ev in _evidence_items(record):
        code = _CODE_LOCATOR.match(_text(ev.get("locator")).strip())
        if code:
            keys.add("code:" + code.group(1).casefold())
            continue
        artifact = _normalise_artifact(_text(ev.get("artifact")))
        if artifact:
            keys.add("artifact:" + artifact)
    rid = record.get("id")
    if isinstance(rid, str):
        for name in graph_targets.get(rid, ()):
            collapsed = " ".join(name.split()).casefold()
            if collapsed:
                keys.add("graph:" + collapsed)
    return frozenset(keys)


def evidence_pairs(record: Mapping[str, Any]) -> frozenset[tuple[str, str]]:
    """Return ``(normalised artifact, stripped locator)`` for each evidence item."""
    return frozenset(
        (_normalise_artifact(_text(ev.get("artifact"))), _text(ev.get("locator")).strip())
        for ev in _evidence_items(record)
    )


def jaccard(a: frozenset[str], b: frozenset[str]) -> float:
    """Jaccard similarity; 0.0 when both sets are empty."""
    union = a | b
    if not union:
        return 0.0
    return len(a & b) / len(union)


@dataclass(frozen=True)
class Match:
    baseline_id: str
    candidate_id: str
    title_similarity: float
    asset_similarity: float


@dataclass(frozen=True)
class MatchResult:
    matched: tuple[Match, ...]
    missing: tuple[str, ...]
    new: tuple[str, ...]


@dataclass(frozen=True)
class _Prepared:
    goal: Any
    title: frozenset[str]
    assets: frozenset[str]


def _prepare(
    records: Mapping[str, Mapping[str, Any]],
    targets: Mapping[str, Sequence[str]],
) -> dict[str, _Prepared]:
    return {
        rid: _Prepared(
            goal=rec.get("apd_goal"),
            title=title_tokens(_text(rec.get("title"))),
            assets=asset_keys(rec, targets),
        )
        for rid, rec in records.items()
    }


def match_records(
    baseline: Mapping[str, Mapping[str, Any]],
    candidate: Mapping[str, Mapping[str, Any]],
    *,
    baseline_targets: Mapping[str, Sequence[str]] | None = None,
    candidate_targets: Mapping[str, Sequence[str]] | None = None,
) -> MatchResult:
    """Match ``baseline`` records to ``candidate`` records one to one.

    Both mappings are keyed by record id. Candidate pairs share ``apd_goal``,
    intersect on ``asset_keys`` and reach ``TITLE_MIN_JACCARD`` on title tokens.
    The greedy pass takes pairs by highest title similarity, then highest asset
    similarity, then same id first, then by ids; ids are unique within a run, so
    the order is total and the result is deterministic.
    """
    base = _prepare(baseline, baseline_targets or {})
    cand = _prepare(candidate, candidate_targets or {})

    pairs: list[tuple[float, float, bool, str, str]] = []
    for bid, b in base.items():
        if not b.assets:
            continue
        for cid, c in cand.items():
            if b.goal != c.goal or not (b.assets & c.assets):
                continue
            title_sim = jaccard(b.title, c.title)
            if title_sim < TITLE_MIN_JACCARD:
                continue
            pairs.append((title_sim, jaccard(b.assets, c.assets), bid != cid, bid, cid))
    pairs.sort(key=lambda p: (-p[0], -p[1], p[2], p[3], p[4]))

    used_b: set[str] = set()
    used_c: set[str] = set()
    matched: list[Match] = []
    for title_sim, asset_sim, _, bid, cid in pairs:
        if bid in used_b or cid in used_c:
            continue
        used_b.add(bid)
        used_c.add(cid)
        matched.append(Match(bid, cid, title_sim, asset_sim))

    return MatchResult(
        matched=tuple(sorted(matched, key=lambda m: (m.baseline_id, m.candidate_id))),
        missing=tuple(sorted(set(base) - used_b)),
        new=tuple(sorted(set(cand) - used_c)),
    )
