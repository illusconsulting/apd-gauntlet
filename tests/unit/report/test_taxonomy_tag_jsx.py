"""Static-text regression test for TaxonomyTag deep-linking
(report-template/components.jsx) — no JS test runner in this repo."""
from __future__ import annotations

import pathlib

REPO = pathlib.Path(__file__).resolve().parents[3]
SRC = REPO / "report-template" / "components.jsx"


def test_taxonomy_tag_links_to_authoritative_url_in_new_tab() -> None:
    """When a taxonomy entry carries a server-computed `url` (ATT&CK + D3FEND),
    the tag renders as an anchor opening that page in a new tab, safely."""
    src = SRC.read_text(encoding="utf-8")
    assert "const url = entry && entry.url" in src
    assert "href={url}" in src
    assert 'target="_blank"' in src
    assert 'rel="noopener noreferrer"' in src
