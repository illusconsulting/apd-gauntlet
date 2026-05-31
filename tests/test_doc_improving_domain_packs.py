"""Pins the §10 author-doc pointer deliverable for Subsystem B."""
from __future__ import annotations

import pathlib

REPO = pathlib.Path(__file__).resolve().parent.parent
DOCS = REPO / "docs"


def test_improving_domain_packs_guide_exists():
    guide = DOCS / "improving-domain-packs.md"
    assert guide.is_file(), "docs/improving-domain-packs.md must exist (§10)"
    assert "draft-domain-improvements" in guide.read_text(encoding="utf-8")


def test_adapting_doc_links_to_improving_guide():
    text = (DOCS / "adapting-to-other-domains.md").read_text(encoding="utf-8")
    assert "improving-domain-packs.md" in text, (
        "adapting-to-other-domains.md must link to improving-domain-packs.md (§10 pointer)"
    )
