"""Tests for the build-domain-skill merge engine."""
from __future__ import annotations

import pathlib

import yaml as _yaml
from apd_gauntlet.build_domain_skill import build_domain_skill
from apd_gauntlet.cli import main
from click.testing import CliRunner

DOMAINS = pathlib.Path("tests/fixtures/domains")


def test_single_pack_emits_packs_frontmatter(tmp_path):
    out = tmp_path / "apd-domain"
    build_domain_skill(["sample"], DOMAINS, out, "1.0.0")
    text = (out / "SKILL.md").read_text()
    assert "name: apd-domain" in text
    assert "packs:" in text
    assert "name: sample" in text
    assert "Sample severity rubric" in text
    assert "## Domain: sample — Source: `severity-rubric.md`" in text


def test_two_packs_merge_both_rubrics_labeled(tmp_path):
    out = tmp_path / "apd-domain"
    build_domain_skill(["sample", "sample2"], DOMAINS, out, "1.0.0")
    text = (out / "SKILL.md").read_text()
    assert "name: sample" in text and "name: sample2" in text
    assert "## Domain: sample — Source: `severity-rubric.md`" in text
    assert "## Domain: sample2 — Source: `severity-rubric.md`" in text
    assert "Sample severity rubric" in text and "Sample2 severity rubric" in text


def test_incompatible_framework_in_any_pack_rejected(tmp_path):
    out = tmp_path / "apd-domain"
    try:
        build_domain_skill(["sample", "sample2"], DOMAINS, out, "2.0.0")
        raise AssertionError("expected ValueError")
    except ValueError as e:
        assert "incompatible" in str(e).lower()


def test_idempotent_no_rewrite_when_pack_set_unchanged(tmp_path):
    out = tmp_path / "apd-domain"
    p = build_domain_skill(["sample"], DOMAINS, out, "1.0.0")
    first = p.read_text()
    p2 = build_domain_skill(["sample"], DOMAINS, out, "1.0.0")
    assert p2.read_text() == first  # byte-identical: not rewritten


def test_rebuild_when_pack_set_changes(tmp_path):
    out = tmp_path / "apd-domain"
    build_domain_skill(["sample"], DOMAINS, out, "1.0.0")
    build_domain_skill(["sample", "sample2"], DOMAINS, out, "1.0.0")
    text = (out / "SKILL.md").read_text()
    assert "name: sample2" in text  # stale single-pack skill was replaced


def test_merged_surfaces_section_dedups_shared_key(tmp_path):
    out = tmp_path / "apd-domain"
    build_domain_skill(["sample", "sample2"], DOMAINS, out, "1.0.0")
    text = (out / "SKILL.md").read_text()
    assert "## Domain attack-path defaults (merged across packs)" in text
    # shared_audit_log is declared by BOTH packs -> exactly one merged entry
    assert text.count("pattern: shared_audit_log") == 1
    # provenance: the shared entry lists both contributing packs
    assert "sample" in text and "sample2" in text


def test_duplicate_pack_names_are_deduped(tmp_path):
    out = tmp_path / "apd-domain"
    build_domain_skill(["sample", "sample"], DOMAINS, out, "1.0.0")
    text = (out / "SKILL.md").read_text()
    assert text.count("name: sample\n") == 1  # frontmatter lists sample once


def test_cli_accepts_multiple_domain_names(tmp_path):
    out = tmp_path / "apd-domain"
    result = CliRunner().invoke(
        main,
        ["build-domain-skill", "sample", "sample2",
         "--domains-dir", str(DOMAINS), "--out", str(out),
         "--framework-version", "1.0.0"],
    )
    assert result.exit_code == 0, result.output
    assert "name: sample2" in (out / "SKILL.md").read_text()


def _frontmatter(text):
    assert text.startswith("---\n")
    end = text.find("\n---\n", 4)
    return _yaml.safe_load(text[4:end])


def test_pack_taxonomies_in_full_skill_frontmatter(tmp_path):
    """A pack declaring taxonomies must surface them under metadata.taxonomies in the
    full SKILL.md frontmatter, deduped and in declared order."""
    domains_dir = tmp_path / "domains"
    (domains_dir / "taxpack").mkdir(parents=True)
    (domains_dir / "taxpack" / "domain.yaml").write_text(
        "name: taxpack\n"
        "display_name: Taxonomy Pack\n"
        "version: 1.0.0\n"
        'framework_compat: ">=1.0.0,<2.0.0"\n'
        "description: A pack used to test taxonomy frontmatter emission, padded.\n"
        "includes:\n  - severity-rubric.md\n"
        "regulatory_anchors: []\n"
        "taxonomies:\n  - masvs\n  - maswe\n"
    )
    (domains_dir / "taxpack" / "severity-rubric.md").write_text("# rubric\n")

    out = tmp_path / "apd-domain"
    build_domain_skill(["taxpack"], domains_dir, out, "1.0.0", emit_sidecars=False)
    fm = _frontmatter((out / "SKILL.md").read_text())
    assert fm["metadata"]["taxonomies"] == ["masvs", "maswe"]


def test_no_taxonomies_omits_frontmatter_key(tmp_path):
    """A pack with no taxonomies field must NOT emit a metadata.taxonomies key."""
    out = tmp_path / "apd-domain"
    build_domain_skill(["sample"], DOMAINS, out, "1.0.0", emit_sidecars=False)
    fm = _frontmatter((out / "SKILL.md").read_text())
    assert "taxonomies" not in fm["metadata"]
