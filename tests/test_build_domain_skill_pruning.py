"""Tests for per-goal sidecar pruning in build-domain-skill.

The builder emits the full cross-goal SKILL.md (unchanged) plus one
`by-goal/<stem>.md` sidecar per goal that has a common-patterns file. Each
sidecar keeps every calibration file + attack-path surfaces and ONLY its own
goal's common-patterns, with an explicit `pruned` manifest (no silent caps).
"""
from __future__ import annotations

import pathlib
import re

import yaml
from apd_gauntlet.build_domain_skill import GOAL_FILE_STEMS, build_domain_skill
from apd_gauntlet.cli import main
from click.testing import CliRunner

FIXTURES = pathlib.Path("tests/fixtures/domains")
REPO_DOMAINS = pathlib.Path("domains")
_CALIBRATION = (
    "severity-rubric.md",
    "consequential-actions.md",
    "immutability-classes.md",
    "data-taxonomy.md",
)


def _frontmatter(text: str) -> dict:
    m = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    assert m, "no frontmatter"
    return yaml.safe_load(m.group(1))


def _strip_ts(text: str) -> str:
    return re.sub(r"generated: .*", "generated: <TS>", text)


def test_sidecars_emitted_only_for_present_goals(tmp_path):
    out = tmp_path / "apd-domain"
    build_domain_skill(["sample"], FIXTURES, out, "1.0.0")
    # The sample pack ships only a confidentiality common-patterns file.
    assert (out / "by-goal" / "confidentiality.md").exists()
    assert not (out / "by-goal" / "integrity.md").exists()


def test_full_skill_identical_with_and_without_sidecars(tmp_path):
    a, b = tmp_path / "a", tmp_path / "b"
    build_domain_skill(["sample"], FIXTURES, a, "1.0.0")
    build_domain_skill(["sample"], FIXTURES, b, "1.0.0", emit_sidecars=False)
    assert _strip_ts((a / "SKILL.md").read_text()) == _strip_ts((b / "SKILL.md").read_text())
    assert not (b / "by-goal").exists()


def test_full_only_flag_suppresses_sidecars(tmp_path):
    out = tmp_path / "apd-domain"
    res = CliRunner().invoke(main, [
        "build-domain-skill", "sample", "--domains-dir", str(FIXTURES),
        "--out", str(out), "--framework-version", "1.0.0", "--full-only",
    ])
    assert res.exit_code == 0, res.output
    assert (out / "SKILL.md").exists()
    assert not (out / "by-goal").exists()


def test_cli_emits_sidecars_by_default(tmp_path):
    out = tmp_path / "apd-domain"
    res = CliRunner().invoke(main, [
        "build-domain-skill", "sample", "--domains-dir", str(FIXTURES),
        "--out", str(out), "--framework-version", "1.0.0",
    ])
    assert res.exit_code == 0, res.output
    assert (out / "by-goal" / "confidentiality.md").exists()
    assert "per-goal sidecars" in res.output


def test_rebuild_when_a_sidecar_is_missing(tmp_path):
    out = tmp_path / "apd-domain"
    build_domain_skill(["sample"], FIXTURES, out, "1.0.0")
    (out / "by-goal" / "confidentiality.md").unlink()
    # Idempotency guard must account for sidecars and regenerate the missing one.
    build_domain_skill(["sample"], FIXTURES, out, "1.0.0")
    assert (out / "by-goal" / "confidentiality.md").exists()


# ---- full 9-goal pack (pbm) ----------------------------------------------


def test_sidecar_keeps_calibration_and_only_own_goal_patterns(tmp_path):
    out = tmp_path / "apd-domain"
    build_domain_skill(["pbm"], REPO_DOMAINS, out, "1.5.0")
    conf = (out / "by-goal" / "confidentiality.md").read_text()
    for cal in _CALIBRATION:
        assert f"Source: `{cal}`" in conf, f"missing calibration file {cal}"
    assert "common-patterns/confidentiality.md" in conf
    for other in GOAL_FILE_STEMS:
        if other != "confidentiality":
            assert f"common-patterns/{other}.md" not in conf, f"leaked {other} patterns"


def test_sidecar_pruned_manifest_lists_omissions(tmp_path):
    out = tmp_path / "apd-domain"
    build_domain_skill(["pbm"], REPO_DOMAINS, out, "1.5.0")
    meta = _frontmatter((out / "by-goal" / "non-repudiation.md").read_text())["metadata"]
    pruned = meta["pruned"]
    assert pruned["scoped_to_goal"] == "non_repudiation"  # canonical underscored name
    assert set(pruned["omitted_goal_patterns"]) == set(GOAL_FILE_STEMS) - {"non-repudiation"}
    for cal in _CALIBRATION:
        assert cal.removesuffix(".md") in pruned["retained_calibration"]
    assert pruned["full_skill"] == "../SKILL.md"


def test_sidecar_smaller_than_full_skill(tmp_path):
    out = tmp_path / "apd-domain"
    build_domain_skill(["pbm"], REPO_DOMAINS, out, "1.5.0")
    full = (out / "SKILL.md").stat().st_size
    side = (out / "by-goal" / "confidentiality.md").stat().st_size
    assert side < full


def test_all_nine_sidecars_for_complete_pack(tmp_path):
    out = tmp_path / "apd-domain"
    build_domain_skill(["pbm"], REPO_DOMAINS, out, "1.5.0")
    for stem in GOAL_FILE_STEMS:
        assert (out / "by-goal" / f"{stem}.md").exists(), f"missing sidecar {stem}"


def test_generated_skill_files_have_no_blank_line_runs(tmp_path):
    """Pure-Python proxy for markdownlint MD012/MD047 (the markdownlint binary is a
    separate CI job): no 3+ consecutive newlines, exactly one trailing newline."""
    out = tmp_path / "apd-domain"
    build_domain_skill(["pbm"], REPO_DOMAINS, out, "1.5.0")
    targets = [out / "SKILL.md", *sorted((out / "by-goal").glob("*.md"))]
    for path in targets:
        text = path.read_text(encoding="utf-8")
        assert "\n\n\n" not in text, f"{path.name}: has a multi-blank-line run (MD012)"
        assert text.endswith("\n") and not text.endswith("\n\n"), \
            f"{path.name}: must end with exactly one newline (MD047)"
