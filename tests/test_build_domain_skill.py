"""Tests for the build-domain-skill merge engine."""
from __future__ import annotations

import pathlib

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
