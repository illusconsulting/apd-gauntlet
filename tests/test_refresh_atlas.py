"""Tests for the refresh-atlas command (network mocked).

Mirrors ``test_refresh_d3fend.py`` / ``test_refresh_mitre.py`` discipline:

* The standard timeout and size-cap constants are pinned.
* :func:`apd_gauntlet.refresh_atlas.project_atlas` is exercised against a
  real-shape ATLAS bundle (``matrices[0].techniques[]``), including the
  sub-technique parent-prefix convention.
* Network hardening (Content-Length pre-check + post-read cap) is exercised.
* ``source_sha256`` is computed over the *raw upstream bytes*.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml
from apd_gauntlet.refresh_atlas import (
    DEFAULT_TIMEOUT_SECONDS,
    MAX_RESPONSE_BYTES,
    fetch_atlas,
    project_atlas,
    refresh_atlas,
)

# A real-shape ATLAS bundle: top-level keys, one matrix with techniques that
# include a base technique, two of its sub-techniques, and an orphan sub
# (parent absent) to exercise the graceful fallback.
_BUNDLE = {
    "id": "ATLAS",
    "name": "MITRE ATLAS",
    "version": "5.6.0",
    "matrices": [
        {
            "id": "ATLAS",
            "name": "ATLAS Machine Learning Threat Matrix",
            "techniques": [
                {"id": "AML.T0051", "name": "LLM Prompt Injection"},
                {"id": "AML.T0051.000", "name": "Direct"},
                {"id": "AML.T0051.001", "name": "Indirect"},
                {"id": "AML.T0020", "name": "Poison Training Data"},
                # Orphan sub-technique: parent AML.T9999 not present.
                {"id": "AML.T9999.000", "name": "Orphan Leaf"},
                # Junk rows that must be skipped.
                {"id": "AML.T0043"},  # no name
                {"name": "no id"},  # no id
                "not-a-dict",
            ],
        }
    ],
}
_BUNDLE_BYTES = yaml.safe_dump(_BUNDLE).encode("utf-8")


# ---- security-hardening constants ----------------------------------------


def test_atlas_timeout_constant_is_60s() -> None:
    assert DEFAULT_TIMEOUT_SECONDS == 60


def test_atlas_size_cap_is_200_mib() -> None:
    assert MAX_RESPONSE_BYTES == 200 * 1024 * 1024


# ---- projection ----------------------------------------------------------


def test_project_extracts_base_and_subtechniques() -> None:
    titles = project_atlas(_BUNDLE)
    assert titles["AML.T0051"] == "LLM Prompt Injection"
    assert titles["AML.T0020"] == "Poison Training Data"


def test_project_prefixes_subtechnique_with_parent_name() -> None:
    """A sub-technique (AML.T####.###) gets a ``Parent: Leaf`` title."""
    titles = project_atlas(_BUNDLE)
    assert titles["AML.T0051.000"] == "LLM Prompt Injection: Direct"
    assert titles["AML.T0051.001"] == "LLM Prompt Injection: Indirect"


def test_project_orphan_subtechnique_falls_back_to_plain_name() -> None:
    """When the parent id is absent, the sub-technique keeps its bare name."""
    titles = project_atlas(_BUNDLE)
    assert titles["AML.T9999.000"] == "Orphan Leaf"


def test_project_skips_rows_missing_id_or_name() -> None:
    titles = project_atlas(_BUNDLE)
    assert "AML.T0043" not in titles  # had no name
    assert "no id" not in titles
    assert "not-a-dict" not in titles


def test_project_handles_empty_or_missing_matrices() -> None:
    assert project_atlas({}) == {}
    assert project_atlas({"matrices": []}) == {}
    assert project_atlas({"matrices": [{}]}) == {}


# ---- network hardening ---------------------------------------------------


def test_fetch_atlas_passes_timeout() -> None:
    with patch("apd_gauntlet.refresh_atlas.urlopen") as mock:
        response = MagicMock()
        response.headers = {"Content-Length": str(len(_BUNDLE_BYTES))}
        response.read.return_value = _BUNDLE_BYTES
        mock.return_value.__enter__.return_value = response
        mock.return_value.__exit__.return_value = False
        fetch_atlas()
        _, kwargs = mock.call_args
        assert kwargs.get("timeout") == DEFAULT_TIMEOUT_SECONDS


def test_fetch_atlas_rejects_oversize_response_content_length() -> None:
    with patch("apd_gauntlet.refresh_atlas.urlopen") as mock:
        response = MagicMock()
        response.headers = {"Content-Length": str(MAX_RESPONSE_BYTES + 1)}
        mock.return_value.__enter__.return_value = response
        mock.return_value.__exit__.return_value = False
        with pytest.raises(ValueError, match="exceeds maximum"):
            fetch_atlas()


def test_fetch_atlas_rejects_oversize_response_post_read(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("apd_gauntlet.refresh_atlas.MAX_RESPONSE_BYTES", 1024)
    fake_oversize = b"x" * 2048
    with patch("apd_gauntlet.refresh_atlas.urlopen") as mock:
        response = MagicMock()
        response.headers = {}
        response.read.return_value = fake_oversize
        mock.return_value.__enter__.return_value = response
        mock.return_value.__exit__.return_value = False
        with pytest.raises(ValueError, match="exceeds maximum"):
            fetch_atlas()


# ---- end-to-end write ----------------------------------------------------


def test_refresh_atlas_writes_to_data_dir(tmp_path: Path) -> None:
    """End-to-end: refresh_atlas writes {_meta, techniques} with the raw-bytes hash."""
    with patch(
        "apd_gauntlet.refresh_atlas.fetch_atlas", return_value=_BUNDLE_BYTES
    ):
        target = tmp_path / "atlas-techniques.json"
        refresh_atlas(output_path=target, fetched_at="2026-06-02")
    assert target.exists()
    data = json.loads(target.read_text())
    assert data["_meta"]["source_sha256"] == hashlib.sha256(_BUNDLE_BYTES).hexdigest()
    assert data["_meta"]["source"]
    assert data["_meta"]["version"] == "5.6.0"
    assert data["_meta"]["fetched_at"] == "2026-06-02"
    assert data["techniques"]["AML.T0051.000"] == "LLM Prompt Injection: Direct"
