"""Every committed corpus manifest under ``eval/`` loads, and its labels are fully reviewed."""
from __future__ import annotations

import pathlib

import pytest
from apd_gauntlet.eval.corpus import load_corpus_manifest, load_labels

REPO = pathlib.Path(__file__).resolve().parent.parent


@pytest.mark.parametrize("path", sorted((REPO / "eval").glob("*/corpus.yaml")), ids=str)
def test_committed_corpus_and_labels_valid(path):
    c = load_corpus_manifest(path)
    for e in c.entries:
        items = load_labels(e.labels_path).data.get("items", [])
        assert all(i.get("verdict") != "unreviewed" for i in items)
