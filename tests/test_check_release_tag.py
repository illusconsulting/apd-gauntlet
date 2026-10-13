"""Unit tests for the release-tag gate (tools/check_release_tag.py)."""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
_SPEC = importlib.util.spec_from_file_location(
    "check_release_tag", REPO_ROOT / "tools" / "check_release_tag.py"
)
mod = importlib.util.module_from_spec(_SPEC)
assert _SPEC.loader is not None
_SPEC.loader.exec_module(mod)


def _plugin(v: str) -> dict[str, str]:
    return {"plugin.json version": v, "marketplace.json entry version": v}


def _eval(
    tag: str,
    py: str,
    *,
    plugin: str | None = None,
    init: str | None = None,
    branches: list[str] | None = None,
    tags: list[str] | None = None,
):
    return mod.evaluate(
        tag,
        py,
        init if init is not None else py,
        _plugin(plugin if plugin is not None else py),
        branches if branches is not None else ["main"],
        tags if tags is not None else [],
    )


def test_stable_patch_on_main_is_latest() -> None:
    d = _eval("v1.7.1", "1.7.1", tags=["v1.7.0", "v1.7.1"])
    assert d == mod.Decision("1.7.1", False, True)


def test_prerelease_on_next_is_not_latest() -> None:
    d = _eval("v2.0.0a1", "2.0.0a1", plugin="2.0.0-alpha.1", branches=["next"],
              tags=["v1.7.0"])
    assert d == mod.Decision("2.0.0a1", True, False)


def test_rc_and_dev_count_as_prereleases() -> None:
    assert _eval("v2.0.0rc1", "2.0.0rc1", branches=["next"]).prerelease
    assert _eval("v2.0.0.dev0", "2.0.0.dev0", branches=["next"]).prerelease


def test_maintenance_release_after_ga_is_not_latest() -> None:
    d = _eval("v1.7.2", "1.7.2", branches=["release/1.7"],
              tags=["v1.7.0", "v1.7.1", "v2.0.0", "v2.1.0a1"])
    assert d == mod.Decision("1.7.2", False, False)


def test_ga_on_main_is_latest_even_with_newer_prerelease_tags() -> None:
    d = _eval("v2.0.0", "2.0.0", tags=["v1.7.0", "v2.0.0a1", "v2.1.0a1"])
    assert d.make_latest and not d.prerelease


def test_stable_tag_on_next_is_refused() -> None:
    with pytest.raises(mod.ReleaseGateError, match="stable tags must be on one of"):
        _eval("v2.0.0", "2.0.0", branches=["next"])


def test_tag_on_feature_branch_is_refused() -> None:
    with pytest.raises(mod.ReleaseGateError, match="must be on one of"):
        _eval("v2.0.0a1", "2.0.0a1", branches=["feat/x"])
    with pytest.raises(mod.ReleaseGateError, match="no branch"):
        _eval("v1.7.1", "1.7.1", branches=[])


def test_tag_must_match_pyproject_exactly() -> None:
    with pytest.raises(mod.ReleaseGateError, match="expected tag 'v1.7.0'"):
        _eval("v1.7.1", "1.7.0")
    with pytest.raises(mod.ReleaseGateError, match="expected tag 'v2.0.0a1'"):
        _eval("v2.0.0-alpha.1", "2.0.0a1", branches=["next"])


def test_pyproject_version_must_be_canonical() -> None:
    with pytest.raises(mod.ReleaseGateError, match="not canonical"):
        _eval("v2.0.0-alpha.1", "2.0.0-alpha.1", branches=["next"])


def test_init_version_must_match_string() -> None:
    with pytest.raises(mod.ReleaseGateError, match="__init__"):
        _eval("v1.7.1", "1.7.1", init="1.7.0")


def test_plugin_semver_prerelease_spelling_is_equivalent() -> None:
    assert _eval("v2.0.0b2", "2.0.0b2", plugin="2.0.0-beta.2", branches=["next"]).prerelease


def test_plugin_version_mismatch_is_refused() -> None:
    with pytest.raises(mod.ReleaseGateError, match="plugin.json"):
        _eval("v2.0.0a2", "2.0.0a2", plugin="2.0.0-alpha.1", branches=["next"])


def test_unparseable_tags_are_ignored_for_latest() -> None:
    assert _eval("v1.7.1", "1.7.1", tags=["vnext", "v1.7.0", "nightly"]).make_latest


def test_repository_versions_are_readable_and_consistent() -> None:
    py, init, plugin = mod.read_versions(REPO_ROOT)
    d = mod.evaluate(f"v{py}", py, init, plugin, ["main", "next"], [])
    assert d.version == py
