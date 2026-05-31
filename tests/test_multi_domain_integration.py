"""End-to-end check that two real shipped packs blend into one provenance-tagged
skill with both rubrics labeled and a merged, deduped attack-path defaults section."""
from __future__ import annotations

import pathlib

from apd_gauntlet.build_domain_skill import build_domain_skill

DOMAINS = pathlib.Path("domains")
FRAMEWORK_VERSION = "1.4.0"
SHARED_JEWEL = "audit_log_store"


def test_pbm_plus_api_security_blend(tmp_path):
    out = tmp_path / "apd-domain"
    build_domain_skill(["pbm", "api-security"], DOMAINS, out, FRAMEWORK_VERSION)
    text = (out / "SKILL.md").read_text()
    # both packs present in frontmatter
    assert "name: pbm" in text and "name: api-security" in text
    # both severity rubrics labeled by pack
    assert "## Domain: pbm — Source: `severity-rubric.md`" in text
    assert "## Domain: api-security — Source: `severity-rubric.md`" in text
    # merged attack-path defaults section exists with provenance
    assert "## Domain attack-path defaults (merged across packs)" in text
    assert "domains:" in text  # per-entry provenance list
    # a jewel declared by BOTH packs is deduped to a single merged entry
    assert text.count(f"pattern: {SHARED_JEWEL}") == 1
