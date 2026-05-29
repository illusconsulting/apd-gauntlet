# tests/unit/report/test_tier2_loader_contracts.py
"""Regression tests for tightened loader contracts."""
from __future__ import annotations

import pytest
from apd_gauntlet.report.loader import (
    MalformedArtifactError,
    MissingArtifactError,
    _required,
    _yaml,
    _yaml_optional,
)


def test_yaml_returns_dict_for_canonical_input(tmp_path):
    p = tmp_path / "fixture.yaml"
    p.write_text("foo: 1\nbar: [1, 2]\n", encoding="utf-8")
    assert _yaml(p) == {"foo": 1, "bar": [1, 2]}


def test_yaml_empty_file_returns_empty_dict(tmp_path):
    p = tmp_path / "fixture.yaml"
    p.write_text("", encoding="utf-8")
    assert _yaml(p) == {}


def test_yaml_comment_only_file_returns_empty_dict(tmp_path):
    """Comment-only YAML parses to None — we coerce to {} (documented)."""
    p = tmp_path / "fixture.yaml"
    p.write_text("# nothing here yet\n", encoding="utf-8")
    assert _yaml(p) == {}


def test_yaml_raises_on_list_top_level(tmp_path):
    p = tmp_path / "fixture.yaml"
    p.write_text("- foo\n- bar\n", encoding="utf-8")
    with pytest.raises(MalformedArtifactError) as exc_info:
        _yaml(p)
    assert exc_info.value.path == p
    assert "list" in str(exc_info.value)


def test_yaml_raises_on_scalar_top_level(tmp_path):
    p = tmp_path / "fixture.yaml"
    p.write_text("just-a-string\n", encoding="utf-8")
    with pytest.raises(MalformedArtifactError):
        _yaml(p)


def test_required_rejects_directory(tmp_path):
    (tmp_path / "fake.yaml").mkdir()
    with pytest.raises(MissingArtifactError) as exc_info:
        _required(tmp_path, "fake.yaml")
    assert "directory" in str(exc_info.value).lower()


def test_required_returns_existing_file(tmp_path):
    (tmp_path / "real.yaml").write_text("x: 1\n", encoding="utf-8")
    p = _required(tmp_path, "real.yaml")
    assert p == tmp_path / "real.yaml"


def test_required_raises_on_missing(tmp_path):
    with pytest.raises(MissingArtifactError):
        _required(tmp_path, "missing.yaml")


def test_yaml_optional_returns_none_for_missing(tmp_path):
    assert _yaml_optional(tmp_path / "absent.yaml") is None


def test_yaml_optional_swallows_malformed_yaml(tmp_path, capsys):
    p = tmp_path / "broken.yaml"
    p.write_text("key: [unclosed\n", encoding="utf-8")
    assert _yaml_optional(p) is None
    captured = capsys.readouterr()
    assert "malformed YAML" in captured.err


def test_yaml_optional_returns_parsed_dict(tmp_path):
    p = tmp_path / "good.yaml"
    p.write_text("foo: bar\n", encoding="utf-8")
    assert _yaml_optional(p) == {"foo": "bar"}
