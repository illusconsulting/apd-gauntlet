"""Tests for refresh_mas (network mocked).

Mirrors test_refresh_atlas.py / test_refresh_d3fend.py discipline:
* the standard timeout and size-cap constants are pinned,
* the YAML/front-matter projections are exercised against real-shape inputs,
* network hardening (Content-Length pre-check + post-read cap) is exercised,
* source_sha256 / commit metadata is recorded over the raw upstream bytes.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from apd_gauntlet.refresh_mas import (
    DEFAULT_TIMEOUT_SECONDS,
    MASVS_COMMIT,
    MASVS_URL,
    MASVS_VERSION,
    MAX_RESPONSE_BYTES,
    fetch_url,
    project_masvs,
    project_maswe,
    refresh_masvs,
    refresh_maswe,
)

# The OWASP_MASVS.yaml top-level shape: {groups:[{id,title,controls:[{id,statement}]}]}.
_MASVS_YAML = b"""
groups:
  - id: MASVS-STORAGE
    title: Storage
    controls:
      - id: MASVS-STORAGE-1
        statement: The app securely stores sensitive data.
      - id: MASVS-STORAGE-2
        statement: The app prevents leakage of sensitive data.
  - id: MASVS-CRYPTO
    title: Cryptography
    controls:
      - id: MASVS-CRYPTO-1
        statement: The app employs current strong cryptography.
"""

# Each MASWE markdown file is YAML front-matter delimited by --- lines.
_MASWE_NEW = b"""---
title: Insertion of Sensitive Information into Log Files
id: MASWE-0001
status: new
mappings:
  masvs-v2:
    - MASVS-STORAGE-2
  cwe:
    - 209
    - 532
---
Body prose that must be ignored.
"""

_MASWE_DEPRECATED = b"""---
title: Old Weakness
id: MASWE-0050
status: deprecated
covered_by:
  - MASWE-0009
mappings:
  masvs-v2:
    - MASVS-CRYPTO-1
  cwe:
    - 321
---
"""

# BUG 2 fixture: this weakness is FILED under MASVS-STORAGE (its repo path) but
# its first mapped control is MASVS-PRIVACY-1. The filing-directory category must
# win, or the mas.owasp.org/MASWE/{category}/{id}/ deep-link 404s.
_MASWE_DIVERGENT = b"""---
title: Weakness Filed Under Storage But Mapped To Privacy
id: MASWE-0099
status: new
mappings:
  masvs-v2:
    - MASVS-PRIVACY-1
  cwe:
    - 200
---
"""


def test_timeout_constant_is_60s() -> None:
    assert DEFAULT_TIMEOUT_SECONDS == 60


def test_size_cap_is_200_mib() -> None:
    assert MAX_RESPONSE_BYTES == 200 * 1024 * 1024


def test_project_masvs_builds_controls_with_category() -> None:
    out = project_masvs(_MASVS_YAML)
    controls = out["controls"]
    assert controls["MASVS-STORAGE-1"]["title"] == "The app securely stores sensitive data."
    assert controls["MASVS-STORAGE-1"]["category"] == "MASVS-STORAGE"
    assert controls["MASVS-STORAGE-1"]["category_title"] == "Storage"
    assert controls["MASVS-CRYPTO-1"]["category"] == "MASVS-CRYPTO"
    assert out["_meta"]["version"] == "v2.1.0"
    assert out["_meta"]["commit"] == MASVS_COMMIT
    assert out["_meta"]["source"] == MASVS_URL
    assert out["_meta"]["count"] == 3
    assert out["_meta"]["source_sha256"] == hashlib.sha256(_MASVS_YAML).hexdigest()


def test_masvs_url_is_commit_pinned() -> None:
    # OWASP_MASVS.yaml does not exist at the v2.1.0 git tag (it 404s); it is
    # fetched from a pinned master commit while v2.1.0 stays the display label.
    assert MASVS_VERSION == "v2.1.0"
    assert MASVS_COMMIT in MASVS_URL
    assert MASVS_VERSION not in MASVS_URL
    assert MASVS_URL.endswith("/OWASP_MASVS.yaml")


def test_project_maswe_parses_front_matter() -> None:
    out = project_maswe(
        {"weaknesses/MASVS-STORAGE/MASWE-0001.md": _MASWE_NEW}, commit="abc123"
    )
    w = out["weaknesses"]["MASWE-0001"]
    assert w["title"] == "Insertion of Sensitive Information into Log Files"
    assert w["category"] == "MASVS-STORAGE"
    assert w["status"] == "new"
    assert w["masvs_v2"] == ["MASVS-STORAGE-2"]
    assert w["cwe"] == [209, 532]
    assert out["_meta"]["commit"] == "abc123"
    assert out["_meta"]["count"] == 1


def test_project_maswe_category_from_path_wins_over_mapped_control() -> None:
    """BUG 2: filing category comes from the repo PATH, not masvs_v2[0].

    The weakness is filed under MASVS-STORAGE but maps to MASVS-PRIVACY-1; the
    path-derived category must win (else the deep-link would 404).
    """
    out = project_maswe(
        {"weaknesses/MASVS-STORAGE/MASWE-0099.md": _MASWE_DIVERGENT}, commit="abc123"
    )
    w = out["weaknesses"]["MASWE-0099"]
    assert w["category"] == "MASVS-STORAGE"
    assert w["masvs_v2"] == ["MASVS-PRIVACY-1"]


def test_project_maswe_falls_back_to_mapped_control_when_path_has_no_category() -> None:
    """When the path has no recognizable MASVS-* segment, fall back to masvs_v2[0]."""
    out = project_maswe({"MASWE-0099.md": _MASWE_DIVERGENT}, commit="abc123")
    w = out["weaknesses"]["MASWE-0099"]
    assert w["category"] == "MASVS-PRIVACY"


def test_project_maswe_deprecated_follows_path_category() -> None:
    """A deprecated weakness records its filing category from the repo path."""
    out = project_maswe(
        {"weaknesses/MASVS-CRYPTO/MASWE-0050.md": _MASWE_DEPRECATED}, commit="abc123"
    )
    w = out["weaknesses"]["MASWE-0050"]
    assert w["status"] == "deprecated"
    assert w["category"] == "MASVS-CRYPTO"
    assert w["masvs_v2"] == ["MASVS-CRYPTO-1"]


def test_fetch_url_passes_timeout() -> None:
    with patch("apd_gauntlet.kb_fetch.urlopen") as mock:
        response = MagicMock()
        response.headers = {"Content-Length": str(len(_MASVS_YAML))}
        response.read.return_value = _MASVS_YAML
        mock.return_value.__enter__.return_value = response
        mock.return_value.__exit__.return_value = False
        fetch_url("https://example.test/x.yaml")
        _, kwargs = mock.call_args
        assert kwargs.get("timeout") == DEFAULT_TIMEOUT_SECONDS


def test_fetch_url_rejects_oversize_content_length() -> None:
    with patch("apd_gauntlet.kb_fetch.urlopen") as mock:
        response = MagicMock()
        response.headers = {"Content-Length": str(MAX_RESPONSE_BYTES + 1)}
        mock.return_value.__enter__.return_value = response
        mock.return_value.__exit__.return_value = False
        with pytest.raises(ValueError, match="exceeds maximum"):
            fetch_url("https://example.test/x.yaml")


def test_fetch_url_rejects_oversize_post_read(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("apd_gauntlet.refresh_mas.MAX_RESPONSE_BYTES", 1024)
    with patch("apd_gauntlet.kb_fetch.urlopen") as mock:
        response = MagicMock()
        response.headers = {}
        response.read.return_value = b"x" * 2048
        mock.return_value.__enter__.return_value = response
        mock.return_value.__exit__.return_value = False
        with pytest.raises(ValueError, match="exceeds maximum"):
            fetch_url("https://example.test/x.yaml")


def test_refresh_masvs_writes_to_data_dir(tmp_path: Path) -> None:
    with patch("apd_gauntlet.refresh_mas.fetch_url", return_value=_MASVS_YAML):
        target = tmp_path / "masvs.json"
        refresh_masvs(output_path=target, fetched_at="2026-06-09")
    data = json.loads(target.read_text())
    assert data["controls"]["MASVS-STORAGE-1"]["category"] == "MASVS-STORAGE"
    assert data["_meta"]["fetched_at"] == "2026-06-09"


def test_refresh_maswe_writes_to_data_dir(tmp_path: Path) -> None:
    """End-to-end: walk the trees API, fetch each MASWE-*.md, write maswe.json."""
    tree = json.dumps(
        {
            "tree": [
                {"path": "weaknesses/MASVS-STORAGE/MASWE-0001.md"},
                {"path": "docs/index.md"},  # ignored: no MASWE- in path
            ]
        }
    ).encode("utf-8")

    def _fake_fetch(url: str) -> bytes:
        if "api.github.com" in url:
            return tree
        return _MASWE_NEW

    with patch("apd_gauntlet.refresh_mas.fetch_url", side_effect=_fake_fetch):
        target = tmp_path / "maswe.json"
        refresh_maswe(output_path=target, commit="abc123", fetched_at="2026-06-09")
    data = json.loads(target.read_text())
    assert data["weaknesses"]["MASWE-0001"]["category"] == "MASVS-STORAGE"
    assert data["_meta"]["commit"] == "abc123"
    assert data["_meta"]["fetched_at"] == "2026-06-09"
    assert data["_meta"]["count"] == 1
