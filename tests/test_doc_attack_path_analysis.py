"""Tests pinning the operator guide `docs/attack-path-analysis.md` (Task C-25).

These tests assert the doc exists, is of meaningful size, and covers the
operator-facing concepts that the v1.4 attack-path analyzer relies on:
crown-jewel and attacker-position declarations, enumeration tuning knobs,
the block-on-missing-crown-jewels rule, the D3FEND overlay on bottleneck
edges, the 50-node Mermaid cap, and the partial-graph caveat.
"""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DOC = REPO_ROOT / "docs" / "attack-path-analysis.md"


def test_doc_exists_and_nonempty() -> None:
    assert DOC.exists(), f"Expected doc at {DOC}"
    assert DOC.stat().st_size > 5000, (
        f"Doc is too small ({DOC.stat().st_size} bytes); expected a "
        "meaningful operator guide of at least 5000 bytes."
    )


def test_doc_covers_declaring_crown_jewels() -> None:
    text = DOC.read_text().lower()
    assert "declare crown jewels" in text or "declaring crown jewels" in text


def test_doc_covers_declaring_attacker_positions() -> None:
    text = DOC.read_text().lower()
    assert "attacker position" in text


def test_doc_covers_tuning_knobs() -> None:
    text = DOC.read_text()
    assert "max_hop" in text
    assert "max_paths_per_pair" in text
    assert "bottleneck_threshold" in text


def test_doc_explains_block_on_missing_crown_jewels() -> None:
    text = DOC.read_text().lower()
    assert "block" in text and "crown jewel" in text


def test_doc_describes_d3fend_overlay() -> None:
    text = DOC.read_text()
    assert "D3FEND" in text
    assert "bottleneck" in text.lower()


def test_doc_describes_50_node_mermaid_cap() -> None:
    text = DOC.read_text().lower()
    assert "50 node" in text or "50-node" in text or "50 nodes" in text


def test_doc_warns_against_partial_graph_overclaiming() -> None:
    text = DOC.read_text().lower()
    assert (
        "partial graph" in text
        or "never claim all paths" in text
        or "top-n paths" in text
    )
