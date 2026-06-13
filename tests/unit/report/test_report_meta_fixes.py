# tests/unit/report/test_report_meta_fixes.py
"""Regression tests for the report meta-layer rendering fixes.

Three defects observed on the open-notebook run report:
  R1. ``subject`` rendered as ``GitHub`` — the path-slug humaniser returned
      the last *capitalised* segment (the ``GitHub`` parent dir) instead of the
      lowercase repo name ``open-notebook``.
  R2. domain pack version rendered as ``vunknown`` — the loader never read the
      declared ``domains: [...]`` packs' versions.
  R3. artifact count under-reported (14 vs 31) — ``_count_artifact_types`` did
      a non-recursive ``iterdir()`` so files inside inputs/ subdirs were missed.
"""
from __future__ import annotations

import pathlib

import pytest
from apd_gauntlet.report.loader import (
    _extract_domain_pack_version,
    _extract_subject,
    _humanise_slug,
)
from apd_gauntlet.report.transform import _count_artifact_types

# ---------------------------------------------------------------------------
# R1 — subject / path-slug humaniser
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "slug, expected",
    [
        # The headline bug: lowercase multi-word repo after GitHub-.
        ("Users-shoveleejoe-Documents-GitHub-open-notebook", "Open Notebook"),
        ("Users-x-Documents-GitHub-data-formulator", "Data Formulator"),
        # CamelCase repo names are preserved, not title-flattened.
        ("Users-alice-Documents-GitHub-MyProject", "MyProject"),
        ("Users-jon-Documents-GitHub-ChainGuard", "ChainGuard"),
        # Single lowercase word repo.
        ("Users-x-Documents-GitHub-authentik", "Authentik"),
        # No known parent dir → prettified last segment.
        ("some-bare-slug", "Slug"),
    ],
)
def test_humanise_slug_recovers_repo_name(slug: str, expected: str) -> None:
    assert _humanise_slug(slug) == expected


def test_humanise_slug_never_returns_parent_dir() -> None:
    """The exact open-notebook regression: must NOT be 'GitHub'."""
    assert _humanise_slug("Users-shoveleejoe-Documents-GitHub-open-notebook") != "GitHub"


def test_extract_subject_explicit_wins() -> None:
    run_cfg = {
        "subject": "Open Notebook",
        "cbm_project": "Users-x-Documents-GitHub-something-else",
    }
    assert _extract_subject(run_cfg) == "Open Notebook"


def test_extract_subject_humanises_cbm_slug() -> None:
    run_cfg = {"cbm_project": "Users-shoveleejoe-Documents-GitHub-open-notebook"}
    assert _extract_subject(run_cfg) == "Open Notebook"


def test_extract_subject_passes_through_non_slug() -> None:
    run_cfg = {"cbm_project": "open-notebook"}
    assert _extract_subject(run_cfg) == "open-notebook"


def test_extract_subject_empty_when_nothing() -> None:
    assert _extract_subject({}) == ""


# ---------------------------------------------------------------------------
# R2 — domain pack version from the declared packs
# ---------------------------------------------------------------------------

def _make_domains(tmp_path: pathlib.Path, packs: dict[str, str]) -> pathlib.Path:
    domains = tmp_path / "domains"
    for name, version in packs.items():
        d = domains / name
        d.mkdir(parents=True)
        (d / "domain.yaml").write_text(
            f"name: {name}\nversion: {version}\n", encoding="utf-8"
        )
    return domains


def test_domain_pack_version_from_declared_domains(tmp_path: pathlib.Path) -> None:
    domains = _make_domains(tmp_path, {"agentic-ai": "1.0.0", "api-security": "1.0.0"})
    run_cfg = {"domains": ["agentic-ai", "api-security"]}
    assert (
        _extract_domain_pack_version(run_cfg, None, domains_dir=domains)
        == "1.0.0+1.0.0"
    )


def test_domain_pack_version_declared_order_preserved(tmp_path: pathlib.Path) -> None:
    domains = _make_domains(tmp_path, {"agentic-ai": "2.1.0", "api-security": "1.3.4"})
    run_cfg = {"domains": ["api-security", "agentic-ai"]}
    assert (
        _extract_domain_pack_version(run_cfg, None, domains_dir=domains)
        == "1.3.4+2.1.0"
    )


def test_domain_pack_version_run_cfg_still_wins(tmp_path: pathlib.Path) -> None:
    domains = _make_domains(tmp_path, {"agentic-ai": "1.0.0"})
    run_cfg = {"domain_pack": {"version": "9.9.9"}, "domains": ["agentic-ai"]}
    assert (
        _extract_domain_pack_version(run_cfg, None, domains_dir=domains) == "9.9.9"
    )


def test_domain_pack_version_unknown_when_pack_missing(tmp_path: pathlib.Path) -> None:
    domains = _make_domains(tmp_path, {"agentic-ai": "1.0.0"})
    run_cfg = {"domains": ["agentic-ai", "nonexistent-pack"]}
    assert _extract_domain_pack_version(run_cfg, None, domains_dir=domains) == "unknown"


def test_domain_pack_version_backward_compatible_without_domains_dir() -> None:
    """The pre-existing 2-arg contract must be unchanged: no domains_dir →
    no pack read → 'unknown'."""
    assert _extract_domain_pack_version({}, {}) == "unknown"
    assert _extract_domain_pack_version({"domains": ["agentic-ai"]}, None) == "unknown"


# ---------------------------------------------------------------------------
# R3 — recursive artifact count
# ---------------------------------------------------------------------------

def test_count_artifact_types_recurses_into_subdirs(tmp_path: pathlib.Path) -> None:
    inputs = tmp_path / "inputs"
    (inputs / "deploy").mkdir(parents=True)
    (inputs / "docs").mkdir()
    (inputs / "PRD.md").write_text("x", encoding="utf-8")
    (inputs / "SRS.md").write_text("x", encoding="utf-8")
    (inputs / "pyproject.toml").write_text("x", encoding="utf-8")
    (inputs / "deploy" / "Dockerfile").write_text("x", encoding="utf-8")
    (inputs / "deploy" / "compose.yml").write_text("x", encoding="utf-8")
    (inputs / "docs" / "architecture.md").write_text("x", encoding="utf-8")

    count, types = _count_artifact_types(tmp_path)

    assert count == 6  # all files, recursive; subdirs themselves not counted
    # md×3 (PRD, SRS, docs/architecture), then file (Dockerfile), toml, yml
    assert "md×3" in types
    assert "toml" in types
    assert "yml" in types
    # The subdir names must NOT be counted as artifacts.
    assert all("deploy" not in t and "docs" not in t for t in types)


def test_count_artifact_types_empty_when_no_inputs(tmp_path: pathlib.Path) -> None:
    assert _count_artifact_types(tmp_path) == (0, [])
    assert _count_artifact_types(None) == (0, [])


# ---------------------------------------------------------------------------
# W1b T5 — multi-repo repos[] back-stop for _extract_subject
# ---------------------------------------------------------------------------

def test_extract_subject_explicit_wins_over_repos() -> None:
    """An explicit subject always wins, even when repos[] is declared."""
    run_cfg = {
        "subject": "Polyglot Payments Platform",
        "repos": [{"cbm_project": "payments-api", "role": "primary"}],
    }
    assert _extract_subject(run_cfg) == "Polyglot Payments Platform"


def test_extract_subject_falls_back_to_primary_repo() -> None:
    """No subject, no cbm_project, but repos[] present => use the primary repo name."""
    run_cfg = {
        "repos": [
            {"cbm_project": "payments-worker", "role": "dependency"},
            {"cbm_project": "payments-api", "role": "primary"},
        ]
    }
    assert _extract_subject(run_cfg) == "payments-api"


def test_extract_subject_falls_back_to_first_repo_when_no_primary() -> None:
    """No role: primary => first repos[] entry's cbm_project is the back-stop."""
    run_cfg = {"repos": [{"cbm_project": "svc-one"}, {"cbm_project": "svc-two"}]}
    assert _extract_subject(run_cfg) == "svc-one"


def test_extract_subject_cbm_project_still_wins_over_repos() -> None:
    """A top-level cbm_project (single-repo back-compat) is preferred over repos[]."""
    run_cfg = {
        "cbm_project": "open-notebook",
        "repos": [{"cbm_project": "payments-api", "role": "primary"}],
    }
    assert _extract_subject(run_cfg) == "open-notebook"
