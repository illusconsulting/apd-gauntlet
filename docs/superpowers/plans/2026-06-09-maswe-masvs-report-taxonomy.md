# OWASP MASVS + MASWE Report-Taxonomy Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** When the `mobile-applications` domain pack is included in a run, make the HTML report explicitly reference and link to OWASP MASWE and OWASP MASVS exactly the way it already references/links to MITRE ATT&CK and D3FEND — per-finding clickable chips, hover titles, dedicated Coverage sub-tabs, coverage rollups, and the §11 framework card.

**Architecture:** Promote MASVS (control / NIST-analog, on findings + capabilities) and MASWE (weakness / CWE-analog, on findings) from prose-only references to first-class **mapped taxonomies**, following the ATLAS finding-level plumbing pattern plus the ATT&CK/D3FEND clickable-URL treatment. Activation is **pack-declared → auto-seeded**: the mobile pack declares `taxonomies: [masvs, maswe]`, `init_run` unions that into the run's `taxonomies` list, and downstream rollup/report keep gating on that (now auto-populated) list. A new `refresh-mas` CLI builds bundled `masvs.json`/`maswe.json` catalogs that supply titles + canonical `mas.owasp.org` links.

**Tech Stack:** Python 3 (`tools/apd_gauntlet/*`), JSON Schema (Draft 2020-12), pytest, esbuild-bundled React/JSX report template (`report-template/` → `data/report-template/app.js`), YAML run artifacts.

**Design spec:** `docs/superpowers/specs/2026-06-09-maswe-masvs-report-taxonomy-design.md`

**Before you start:** verify the next ADR number is still `0014` and the current version is still `1.6.0` (Phase 9 assumes both). Work on a feature branch off `main`. Many tasks edit JSX — remember every JSX edit requires `python tools/build_report_template.py` + committing the regenerated `app.js` and `.source-hash`, and the CI markdownlint job globs all of `docs/**` so run the full glob before pushing.

---

### Task 1: Create the feature branch

**Files:** (none — git only)

- [ ] **Step 1: Branch off main**
```bash
git checkout main && git pull --ff-only
git checkout -b feat/owasp-mas-mobile-taxonomy
```
- [ ] **Step 2: Confirm a clean baseline**
Run: `python -m pytest -q && python tools/check_report_template_freshness.py`
Expected: all tests PASS and freshness reports the bundle is up to date (this is the green baseline every later task must preserve).

---


## Phase 1 — Reference catalog, `refresh-mas` & taxonomy loaders/URLs

### Task 2: Bundle the masvs.json + maswe.json reference fixtures

**Files:**
- Create: `tools/apd_gauntlet/data/masvs.json`
- Create: `tools/apd_gauntlet/data/maswe.json`
- Test: `tests/test_mas_catalog_fixtures.py`

- [ ] **Step 1: Write the failing test**
```python
"""The bundled MASVS/MASWE catalogs must ship with the exact contract shape so
the report taxonomy loaders and offline tests have a real (if small) subset to
read. Mirrors the discipline of the bundled atlas-techniques.json fixture."""
from __future__ import annotations

import json
import pathlib

_DATA = pathlib.Path(__file__).resolve().parents[1] / "tools" / "apd_gauntlet" / "data"

# All eight MASVS category prefixes from the v2.1.0 release.
_CATEGORIES = {
    "MASVS-STORAGE", "MASVS-CRYPTO", "MASVS-AUTH", "MASVS-NETWORK",
    "MASVS-PLATFORM", "MASVS-CODE", "MASVS-RESILIENCE", "MASVS-PRIVACY",
}


def test_masvs_json_has_meta_and_all_categories() -> None:
    doc = json.loads((_DATA / "masvs.json").read_text(encoding="utf-8"))
    meta = doc["_meta"]
    assert meta["version"] == "v2.1.0"
    assert meta["source"]
    assert meta["source_sha256"]
    assert meta["fetched_at"]
    controls = doc["controls"]
    assert meta["count"] == len(controls)
    # At least one control per category, with the contract field set.
    seen = set()
    for cid, body in controls.items():
        assert cid.startswith(body["category"] + "-"), cid
        assert body["title"]
        assert body["category_title"]
        seen.add(body["category"])
    assert seen == _CATEGORIES
    # Spot-check a known control.
    assert "MASVS-STORAGE-1" in controls


def test_maswe_json_has_meta_and_weakness_shape() -> None:
    doc = json.loads((_DATA / "maswe.json").read_text(encoding="utf-8"))
    meta = doc["_meta"]
    assert meta["source"]
    assert meta["commit"]
    assert meta["fetched_at"]
    weaknesses = doc["weaknesses"]
    assert meta["count"] == len(weaknesses)
    for wid, body in weaknesses.items():
        assert wid.startswith("MASWE-")
        assert body["title"]
        assert body["category"] in _CATEGORIES
        assert body["status"] in {"new", "draft", "deprecated"}
        assert isinstance(body["masvs_v2"], list)
        assert isinstance(body["cwe"], list)
    # The subset must include at least one deprecated weakness for loader tests.
    assert any(b["status"] == "deprecated" for b in weaknesses.values())
    assert "MASWE-0001" in weaknesses
```
- [ ] **Step 2: Run test to verify it fails**
Run: `python -m pytest tests/test_mas_catalog_fixtures.py -q`
Expected: FAIL with `FileNotFoundError: ...data/masvs.json` (file does not yet exist)
- [ ] **Step 3: Author the bundled subset fixtures**
Create `tools/apd_gauntlet/data/masvs.json` (first control of each of the 8 categories; `count` matches the entry total):
```json
{
  "_meta": {
    "fetched_at": "2026-06-09",
    "source": "https://raw.githubusercontent.com/OWASP/masvs/v2.1.0/OWASP_MASVS.yaml",
    "source_sha256": "0000000000000000000000000000000000000000000000000000000000000000",
    "version": "v2.1.0",
    "count": 8
  },
  "controls": {
    "MASVS-STORAGE-1": {"title": "The app securely stores sensitive data.", "category": "MASVS-STORAGE", "category_title": "Storage"},
    "MASVS-CRYPTO-1": {"title": "The app employs current strong cryptography and uses it according to industry best practices.", "category": "MASVS-CRYPTO", "category_title": "Cryptography"},
    "MASVS-AUTH-1": {"title": "The app uses secure authentication and authorization protocols and follows the relevant best practices.", "category": "MASVS-AUTH", "category_title": "Authentication and Authorization"},
    "MASVS-NETWORK-1": {"title": "The app secures all network traffic according to the current best practices.", "category": "MASVS-NETWORK", "category_title": "Network Communication"},
    "MASVS-PLATFORM-1": {"title": "The app uses IPC mechanisms securely.", "category": "MASVS-PLATFORM", "category_title": "Platform Interaction"},
    "MASVS-CODE-1": {"title": "The app requires an up-to-date platform version.", "category": "MASVS-CODE", "category_title": "Code Quality"},
    "MASVS-RESILIENCE-1": {"title": "The app validates the integrity of the platform.", "category": "MASVS-RESILIENCE", "category_title": "Resilience"},
    "MASVS-PRIVACY-1": {"title": "The app minimizes access to sensitive data and resources.", "category": "MASVS-PRIVACY", "category_title": "Privacy"}
  }
}
```
Create `tools/apd_gauntlet/data/maswe.json` (5 weaknesses incl. one deprecated whose `covered_by` collapsed into its `masvs_v2`):
```json
{
  "_meta": {
    "fetched_at": "2026-06-09",
    "source": "https://github.com/OWASP/maswe",
    "commit": "0000000000000000000000000000000000000000",
    "count": 5
  },
  "weaknesses": {
    "MASWE-0001": {"title": "Insertion of Sensitive Information into Log Files", "category": "MASVS-STORAGE", "status": "new", "masvs_v2": ["MASVS-STORAGE-2"], "cwe": [209, 532]},
    "MASWE-0002": {"title": "Sensitive Data Stored Unencrypted in Private Storage Locations", "category": "MASVS-STORAGE", "status": "new", "masvs_v2": ["MASVS-STORAGE-1"], "cwe": [311, 312]},
    "MASWE-0009": {"title": "Insecure Random Number Generators", "category": "MASVS-CRYPTO", "status": "new", "masvs_v2": ["MASVS-CRYPTO-1"], "cwe": [330, 338]},
    "MASWE-0021": {"title": "Insecure or Outdated TLS Versions and Cipher Suites", "category": "MASVS-NETWORK", "status": "draft", "masvs_v2": ["MASVS-NETWORK-1"], "cwe": [326, 327]},
    "MASWE-0050": {"title": "Hardcoded Cryptographic Keys (deprecated; folded into MASWE-0009)", "category": "MASVS-CRYPTO", "status": "deprecated", "masvs_v2": ["MASVS-CRYPTO-1"], "cwe": [321]}
  }
}
```
- [ ] **Step 4: Run test to verify it passes**
Run: `python -m pytest tests/test_mas_catalog_fixtures.py -q`
Expected: PASS
- [ ] **Step 5: Commit**
```bash
git add tools/apd_gauntlet/data/masvs.json tools/apd_gauntlet/data/maswe.json tests/test_mas_catalog_fixtures.py
git commit -m "feat(data): bundle OWASP MASVS v2.1.0 + MASWE reference catalog subset"
```

### Task 3: Add refresh_mas.py projection + write (network-hardened)

**Files:**
- Create: `tools/apd_gauntlet/refresh_mas.py`
- Test: `tests/test_refresh_mas.py`

- [ ] **Step 1: Write the failing test**
```python
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
    assert out["_meta"]["count"] == 3
    assert out["_meta"]["source_sha256"] == hashlib.sha256(_MASVS_YAML).hexdigest()


def test_project_maswe_parses_front_matter() -> None:
    out = project_maswe({"MASWE-0001.md": _MASWE_NEW}, commit="abc123")
    w = out["weaknesses"]["MASWE-0001"]
    assert w["title"] == "Insertion of Sensitive Information into Log Files"
    assert w["category"] == "MASVS-STORAGE"
    assert w["status"] == "new"
    assert w["masvs_v2"] == ["MASVS-STORAGE-2"]
    assert w["cwe"] == [209, 532]
    assert out["_meta"]["commit"] == "abc123"
    assert out["_meta"]["count"] == 1


def test_project_maswe_deprecated_follows_covered_by_category() -> None:
    """A deprecated weakness still records its filing category (from masvs-v2[0])."""
    out = project_maswe({"MASWE-0050.md": _MASWE_DEPRECATED}, commit="abc123")
    w = out["weaknesses"]["MASWE-0050"]
    assert w["status"] == "deprecated"
    assert w["category"] == "MASVS-CRYPTO"
    assert w["masvs_v2"] == ["MASVS-CRYPTO-1"]


def test_fetch_url_passes_timeout() -> None:
    with patch("apd_gauntlet.refresh_mas.urlopen") as mock:
        response = MagicMock()
        response.headers = {"Content-Length": str(len(_MASVS_YAML))}
        response.read.return_value = _MASVS_YAML
        mock.return_value.__enter__.return_value = response
        mock.return_value.__exit__.return_value = False
        fetch_url("https://example.test/x.yaml")
        _, kwargs = mock.call_args
        assert kwargs.get("timeout") == DEFAULT_TIMEOUT_SECONDS


def test_fetch_url_rejects_oversize_content_length() -> None:
    with patch("apd_gauntlet.refresh_mas.urlopen") as mock:
        response = MagicMock()
        response.headers = {"Content-Length": str(MAX_RESPONSE_BYTES + 1)}
        mock.return_value.__enter__.return_value = response
        mock.return_value.__exit__.return_value = False
        with pytest.raises(ValueError, match="exceeds maximum"):
            fetch_url("https://example.test/x.yaml")


def test_fetch_url_rejects_oversize_post_read(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("apd_gauntlet.refresh_mas.MAX_RESPONSE_BYTES", 1024)
    with patch("apd_gauntlet.refresh_mas.urlopen") as mock:
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
```
- [ ] **Step 2: Run test to verify it fails**
Run: `python -m pytest tests/test_refresh_mas.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'apd_gauntlet.refresh_mas'`
- [ ] **Step 3: Implement refresh_mas.py**
```python
"""Refresh the cached OWASP MASVS + MASWE reference catalogs.

Builds two JSONs bundled in ``tools/apd_gauntlet/data/``:

* ``masvs.json`` from ``OWASP_MASVS.yaml`` at the pinned ``v2.1.0`` tag —
  projected to ``{control_id: {title, category, category_title}}``.
* ``maswe.json`` from the ``OWASP/maswe`` repo at a pinned commit — each
  weakness is a markdown file with YAML front-matter (delimited by ``---``);
  we parse the front-matter only and ignore the prose body. A weakness's
  filing ``category`` is taken from the first ``mappings.masvs-v2`` control's
  prefix; ``covered_by`` is preserved for deprecated entries.

Security hardening mirrors :mod:`apd_gauntlet.refresh_atlas` /
:mod:`apd_gauntlet.refresh_d3fend`:

* ``DEFAULT_TIMEOUT_SECONDS = 60`` — bounds time spent waiting for upstream.
* ``MAX_RESPONSE_BYTES = 200 MiB`` — bounds memory if upstream is compromised.
* Defense in depth: a ``Content-Length`` pre-check AND a post-read size check.
"""

from __future__ import annotations

import datetime
import hashlib
import json
import pathlib
from typing import Any
from urllib.request import urlopen

import yaml

MASVS_VERSION = "v2.1.0"
MASVS_URL = (
    "https://raw.githubusercontent.com/OWASP/masvs/"
    f"{MASVS_VERSION}/OWASP_MASVS.yaml"
)
# MASWE is Beta — its IDs/URLs churn — so pin an IMMUTABLE 40-hex commit for
# reproducible refreshes. Before merging, resolve and paste the current SHA from:
#   git ls-remote https://github.com/OWASP/maswe.git HEAD
# "main" works for a first local run but MUST be replaced with the SHA for the PR.
MASWE_COMMIT = "main"
MASWE_REPO = "https://github.com/OWASP/maswe"

MAX_RESPONSE_BYTES = 200 * 1024 * 1024  # 200 MiB
DEFAULT_TIMEOUT_SECONDS = 60

_DATA = pathlib.Path(__file__).resolve().parent / "data"


def fetch_url(url: str) -> bytes:
    """Fetch ``url``. Returns the raw bytes.

    Raises ``ValueError`` if the response exceeds :data:`MAX_RESPONSE_BYTES`
    (checked twice: once via ``Content-Length``, once after reading).
    """
    with urlopen(url, timeout=DEFAULT_TIMEOUT_SECONDS) as response:
        content_length = response.headers.get("Content-Length")
        if content_length is not None:
            try:
                advertised = int(content_length)
            except (TypeError, ValueError):
                advertised = None
            if advertised is not None and advertised > MAX_RESPONSE_BYTES:
                raise ValueError(
                    f"MAS response Content-Length ({advertised}) "
                    f"exceeds maximum ({MAX_RESPONSE_BYTES})"
                )
        body: bytes = response.read(MAX_RESPONSE_BYTES + 1)
    if len(body) > MAX_RESPONSE_BYTES:
        raise ValueError(
            f"MAS response body exceeds maximum ({MAX_RESPONSE_BYTES} bytes); "
            "refusing to load. Verify the upstream feed before retrying."
        )
    return body


def project_masvs(yaml_bytes: bytes, *, fetched_at: str | None = None) -> dict[str, Any]:
    """Project the OWASP_MASVS.yaml bundle to the bundled masvs.json shape.

    Upstream shape: ``{groups: [{id, title, controls: [{id, statement}]}]}``.
    """
    doc = yaml.safe_load(yaml_bytes.decode("utf-8")) or {}
    controls: dict[str, dict[str, str]] = {}
    for group in doc.get("groups", []) or []:
        if not isinstance(group, dict):
            continue
        category = str(group.get("id") or "")
        category_title = str(group.get("title") or "")
        for control in group.get("controls", []) or []:
            if not isinstance(control, dict):
                continue
            cid = str(control.get("id") or "")
            statement = str(control.get("statement") or "")
            if not cid or not category:
                continue
            controls[cid] = {
                "title": statement,
                "category": category,
                "category_title": category_title,
            }
    return {
        "_meta": {
            "fetched_at": fetched_at or datetime.date.today().isoformat(),
            "source": MASVS_URL,
            "source_sha256": hashlib.sha256(yaml_bytes).hexdigest(),
            "version": MASVS_VERSION,
            "count": len(controls),
        },
        "controls": dict(sorted(controls.items())),
    }


def _parse_front_matter(md_bytes: bytes) -> dict[str, Any]:
    """Return the YAML front-matter of a MASWE markdown file (between --- lines)."""
    text = md_bytes.decode("utf-8")
    if not text.lstrip().startswith("---"):
        return {}
    stripped = text.lstrip()
    rest = stripped[3:]  # drop the leading ---
    end = rest.find("\n---")
    if end == -1:
        return {}
    front = rest[:end]
    parsed = yaml.safe_load(front)
    return parsed if isinstance(parsed, dict) else {}


def project_maswe(
    files: dict[str, bytes],
    *,
    commit: str,
    fetched_at: str | None = None,
) -> dict[str, Any]:
    """Project a ``{filename: markdown_bytes}`` map to the bundled maswe.json shape.

    The filing ``category`` is derived from the prefix of the first
    ``mappings.masvs-v2`` control (e.g. ``MASVS-STORAGE-2`` -> ``MASVS-STORAGE``);
    ``covered_by`` is preserved for deprecated weaknesses.
    """
    weaknesses: dict[str, dict[str, Any]] = {}
    for _name, md_bytes in files.items():
        front = _parse_front_matter(md_bytes)
        wid = str(front.get("id") or "")
        if not wid.startswith("MASWE-"):
            continue
        mappings = front.get("mappings") or {}
        masvs_v2 = [str(m) for m in (mappings.get("masvs-v2") or [])]
        cwe = [int(c) for c in (mappings.get("cwe") or []) if str(c).isdigit()]
        category = masvs_v2[0].rsplit("-", 1)[0] if masvs_v2 else ""
        entry: dict[str, Any] = {
            "title": str(front.get("title") or ""),
            "category": category,
            "status": str(front.get("status") or "new"),
            "masvs_v2": masvs_v2,
            "cwe": cwe,
        }
        covered_by = front.get("covered_by")
        if covered_by:
            entry["covered_by"] = [str(c) for c in covered_by]
        weaknesses[wid] = entry
    return {
        "_meta": {
            "fetched_at": fetched_at or datetime.date.today().isoformat(),
            "source": MASWE_REPO,
            "commit": commit,
            "count": len(weaknesses),
        },
        "weaknesses": dict(sorted(weaknesses.items())),
    }


def refresh_masvs(
    output_path: pathlib.Path | None = None,
    *,
    fetched_at: str | None = None,
) -> pathlib.Path:
    """Fetch + project MASVS and write ``data/masvs.json``. Returns the path."""
    out = output_path or (_DATA / "masvs.json")
    raw = fetch_url(MASVS_URL)
    payload = project_masvs(raw, fetched_at=fetched_at)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return out


def refresh_maswe(
    output_path: pathlib.Path | None = None,
    *,
    commit: str = MASWE_COMMIT,
    fetched_at: str | None = None,
) -> pathlib.Path:
    """Fetch the MASWE weakness markdown set @ ``commit`` and write ``data/maswe.json``.

    Walks the repo's ``weaknesses/`` tree via the GitHub trees API at the pinned
    commit, fetches each ``MASWE-*.md`` raw blob, and projects the front-matter.
    """
    out = output_path or (_DATA / "maswe.json")
    tree_url = (
        f"https://api.github.com/repos/OWASP/maswe/git/trees/{commit}?recursive=1"
    )
    tree = json.loads(fetch_url(tree_url).decode("utf-8"))
    files: dict[str, bytes] = {}
    for node in tree.get("tree", []) or []:
        path = node.get("path", "")
        if path.endswith(".md") and "MASWE-" in path:
            raw_url = (
                f"https://raw.githubusercontent.com/OWASP/maswe/{commit}/{path}"
            )
            files[path] = fetch_url(raw_url)
    payload = project_maswe(files, commit=commit, fetched_at=fetched_at)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return out


if __name__ == "__main__":
    print(f"Wrote {refresh_masvs()}")
    print(f"Wrote {refresh_maswe()}")
```
- [ ] **Step 4: Run test to verify it passes**
Run: `python -m pytest tests/test_refresh_mas.py -q`
Expected: PASS
- [ ] **Step 5: Commit**
```bash
git add tools/apd_gauntlet/refresh_mas.py tests/test_refresh_mas.py
git commit -m "feat(refresh): add refresh_mas MASVS/MASWE catalog builders"
```

### Task 4: Register the refresh-mas CLI verb

**Files:**
- Modify: `tools/apd_gauntlet/cli.py:597-603`
- Test: `tests/test_cli.py`

- [ ] **Step 1: Write the failing test**
```python
def test_cli_refresh_mas_invokes_both_builders():
    runner = CliRunner()
    with patch("apd_gauntlet.refresh_mas.refresh_masvs") as masvs, patch(
        "apd_gauntlet.refresh_mas.refresh_maswe"
    ) as maswe:
        masvs.return_value = Path("/tmp/masvs.json")
        maswe.return_value = Path("/tmp/maswe.json")
        result = runner.invoke(main, ["refresh-mas"])
        assert result.exit_code == 0
        masvs.assert_called_once()
        maswe.assert_called_once()
```
- [ ] **Step 2: Run test to verify it fails**
Run: `python -m pytest tests/test_cli.py -k refresh_mas -q`
Expected: FAIL with `Error: No such command 'refresh-mas'` (exit_code != 0)
- [ ] **Step 3: Add the verb after refresh-atlas**
Current code (`tools/apd_gauntlet/cli.py:597-603`):
```python
@main.command("refresh-atlas")
def refresh_atlas_cmd() -> None:
    """Refresh MITRE ATLAS technique-title reference data."""
    from .refresh_atlas import refresh_atlas

    path = refresh_atlas()
    click.echo(f"Wrote {path}")
```
Append immediately after it:
```python
@main.command("refresh-mas")
def refresh_mas_cmd() -> None:
    """Refresh OWASP MASVS v2.1.0 + MASWE mobile reference catalogs."""
    from .refresh_mas import refresh_masvs, refresh_maswe

    click.echo(f"Wrote {refresh_masvs()}")
    click.echo(f"Wrote {refresh_maswe()}")
```
- [ ] **Step 4: Run test to verify it passes**
Run: `python -m pytest tests/test_cli.py -k refresh_mas -q`
Expected: PASS
- [ ] **Step 5: Commit**
```bash
git add tools/apd_gauntlet/cli.py tests/test_cli.py
git commit -m "feat(cli): register refresh-mas verb"
```

### Task 5: Add masvs_titles/maswe_titles loaders to report/taxonomy.py

**Files:**
- Modify: `tools/apd_gauntlet/report/taxonomy.py:244-275` (after `atlas_titles`)
- Test: `tests/unit/report/test_mas_taxonomy.py`

- [ ] **Step 1: Write the failing test**
```python
"""MASVS/MASWE title loaders read the bundled masvs.json / maswe.json catalogs
(projection discipline mirrors atlas_titles / d3fend_titles)."""
from __future__ import annotations

import json

import pytest
from apd_gauntlet.report import taxonomy as tax
from apd_gauntlet.report.taxonomy import maswe_titles, masvs_titles


@pytest.fixture(autouse=True)
def _isolate():
    tax.invalidate_all()
    yield
    tax.invalidate_all()


def test_masvs_titles_resolves_bundled_controls() -> None:
    titles = masvs_titles()
    assert titles["MASVS-STORAGE-1"] == "The app securely stores sensitive data."
    # All 8 categories' first control ship in the bundled subset.
    assert "MASVS-PRIVACY-1" in titles
    assert len(titles) >= 8


def test_maswe_titles_resolves_bundled_weaknesses() -> None:
    titles = maswe_titles()
    assert "Log Files" in titles["MASWE-0001"]
    assert "MASWE-0050" in titles  # the deprecated entry still carries a title


def test_masvs_titles_reads_monkeypatched_data(tmp_path, monkeypatch) -> None:
    p = tmp_path / "masvs.json"
    p.write_text(
        json.dumps(
            {"_meta": {}, "controls": {"MASVS-CODE-9": {"title": "X", "category": "MASVS-CODE", "category_title": "Code Quality"}}}
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(tax, "_DATA", tmp_path)
    tax.invalidate_all()
    assert masvs_titles() == {"MASVS-CODE-9": "X"}


def test_masvs_titles_missing_file_is_empty(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(tax, "_DATA", tmp_path)
    tax.invalidate_all()
    assert masvs_titles() == {}
```
- [ ] **Step 2: Run test to verify it fails**
Run: `python -m pytest tests/unit/report/test_mas_taxonomy.py -k titles -q`
Expected: FAIL with `ImportError: cannot import name 'masvs_titles'`
- [ ] **Step 3: Add the two loaders after `atlas_titles`**
Insert immediately after the `atlas_titles()` function (which ends at `tools/apd_gauntlet/report/taxonomy.py:275`, just before `def reference_db_versions`):
```python
@_register_cached
@lru_cache(maxsize=1)
def masvs_titles() -> dict[str, str]:
    """Map OWASP MASVS control id (MASVS-CATEGORY-N) → statement.

    Reads the bundled masvs.json produced by ``apd-gauntlet refresh-mas``.
    Returns {} if the file is missing/unparseable so callers fall back to the id.
    Shape: {"controls": {"MASVS-STORAGE-1": {"title": ..., "category": ...}, ...}}.
    """
    path = _DATA / "masvs.json"
    try:
        with path.open(encoding="utf-8") as fh:
            raw = json.load(fh)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}
    out: dict[str, str] = {}
    controls = raw.get("controls") if isinstance(raw, dict) else None
    if isinstance(controls, dict):
        for cid, v in controls.items():
            out[cid] = (
                v.get("title") or cid if isinstance(v, dict)
                else v if isinstance(v, str)
                else cid
            )
    return out


@_register_cached
@lru_cache(maxsize=1)
def maswe_titles() -> dict[str, str]:
    """Map OWASP MASWE weakness id (MASWE-####) → title.

    Reads the bundled maswe.json produced by ``apd-gauntlet refresh-mas``.
    Returns {} if the file is missing/unparseable so callers fall back to the id.
    Shape: {"weaknesses": {"MASWE-0001": {"title": ..., "category": ...}, ...}}.
    """
    path = _DATA / "maswe.json"
    try:
        with path.open(encoding="utf-8") as fh:
            raw = json.load(fh)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}
    out: dict[str, str] = {}
    weaknesses = raw.get("weaknesses") if isinstance(raw, dict) else None
    if isinstance(weaknesses, dict):
        for wid, v in weaknesses.items():
            out[wid] = (
                v.get("title") or wid if isinstance(v, dict)
                else v if isinstance(v, str)
                else wid
            )
    return out
```
- [ ] **Step 4: Run test to verify it passes**
Run: `python -m pytest tests/unit/report/test_mas_taxonomy.py -k titles -q`
Expected: PASS
- [ ] **Step 5: Commit**
```bash
git add tools/apd_gauntlet/report/taxonomy.py tests/unit/report/test_mas_taxonomy.py
git commit -m "feat(taxonomy): add masvs_titles/maswe_titles loaders"
```

### Task 6: Add masvs_url/maswe_url builders to report/taxonomy.py

**Files:**
- Modify: `tools/apd_gauntlet/report/taxonomy.py:225-242` (after `d3fend_url`)
- Test: `tests/unit/report/test_mas_taxonomy.py`

- [ ] **Step 1: Write the failing test**
```python
from apd_gauntlet.report.taxonomy import masvs_url, maswe_url


def test_masvs_url_is_pure_regex_no_catalog() -> None:
    assert masvs_url("MASVS-STORAGE-1") == "https://mas.owasp.org/MASVS/controls/MASVS-STORAGE-1/"
    assert masvs_url("MASVS-CRYPTO-2") == "https://mas.owasp.org/MASVS/controls/MASVS-CRYPTO-2/"


def test_masvs_url_rejects_non_control_ids() -> None:
    assert masvs_url("MASVS-STORAGE") is None  # category, not control
    assert masvs_url("MASWE-0001") is None
    assert masvs_url("") is None
    assert masvs_url("MASVS-BOGUS-1") is None  # unknown category prefix


def test_maswe_url_reads_filing_category_from_catalog() -> None:
    # MASWE-0001 ships in the bundled maswe.json with category MASVS-STORAGE.
    assert maswe_url("MASWE-0001") == "https://mas.owasp.org/MASWE/MASVS-STORAGE/MASWE-0001/"


def test_maswe_url_unknown_category_returns_none() -> None:
    # A weakness id not present in the catalog has no resolvable category.
    assert maswe_url("MASWE-9999") is None
    assert maswe_url("") is None
```
- [ ] **Step 2: Run test to verify it fails**
Run: `python -m pytest tests/unit/report/test_mas_taxonomy.py -k url -q`
Expected: FAIL with `ImportError: cannot import name 'masvs_url'`
- [ ] **Step 3: Add a regex + two URL builders after `d3fend_url`**
Current code ends at `tools/apd_gauntlet/report/taxonomy.py:241-242`:
```python
    return f"https://d3fend.mitre.org/technique/d3f:{local}/"
```
Insert immediately after that function (before the `@_register_cached` for `atlas_titles`):
```python
_MASVS_CONTROL_RE = re.compile(
    r"^MASVS-(?:STORAGE|CRYPTO|AUTH|NETWORK|PLATFORM|CODE|RESILIENCE|PRIVACY)-[1-9][0-9]*$"
)


def masvs_url(control_id: str) -> str | None:
    """Authoritative mas.owasp.org URL for a MASVS control id.

    Pure regex (no catalog lookup): MASVS-STORAGE-1 ->
    .../MASVS/controls/MASVS-STORAGE-1/. Returns None for category ids
    (MASVS-STORAGE), weakness ids (MASWE-####), or unknown category prefixes.
    """
    if not _MASVS_CONTROL_RE.match(control_id or ""):
        return None
    return f"https://mas.owasp.org/MASVS/controls/{control_id}/"


def maswe_url(weakness_id: str) -> str | None:
    """Authoritative mas.owasp.org URL for a MASWE weakness id.

    The URL is keyed by the weakness's *filing category* (e.g. MASVS-STORAGE),
    which is read from the bundled maswe.json. Returns None when the weakness
    (or its category) is unknown — never fabricates a category."""
    category = (maswe_categories().get(weakness_id or "") or "").strip()
    if not category:
        return None
    return f"https://mas.owasp.org/MASWE/{category}/{weakness_id}/"
```
Then add the small category-map loader alongside `maswe_titles` (place after `maswe_titles` from the previous task):
```python
@_register_cached
@lru_cache(maxsize=1)
def maswe_categories() -> dict[str, str]:
    """Map MASWE weakness id → filing category (MASVS-CATEGORY) from maswe.json."""
    path = _DATA / "maswe.json"
    try:
        with path.open(encoding="utf-8") as fh:
            raw = json.load(fh)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}
    out: dict[str, str] = {}
    weaknesses = raw.get("weaknesses") if isinstance(raw, dict) else None
    if isinstance(weaknesses, dict):
        for wid, v in weaknesses.items():
            if isinstance(v, dict) and v.get("category"):
                out[wid] = str(v["category"])
    return out
```
- [ ] **Step 4: Run test to verify it passes**
Run: `python -m pytest tests/unit/report/test_mas_taxonomy.py -k url -q`
Expected: PASS
- [ ] **Step 5: Commit**
```bash
git add tools/apd_gauntlet/report/taxonomy.py tests/unit/report/test_mas_taxonomy.py
git commit -m "feat(taxonomy): add masvs_url/maswe_url builders"
```

### Task 7: Register MAS catalogs in reference_db_versions + invalidation map

**Files:**
- Modify: `tools/apd_gauntlet/report/taxonomy.py:286-292` (reference_db_versions table)
- Modify: `tools/apd_gauntlet/report/taxonomy.py:338-344` (invalidation catalog map)
- Test: `tests/unit/report/test_mas_taxonomy.py`

- [ ] **Step 1: Write the failing test**
```python
import os
import time

from apd_gauntlet.report.taxonomy import (
    invalidate_if_modified,
    maswe_categories,
    maswe_titles,
    masvs_titles,
    reference_db_versions,
)


def test_reference_db_versions_includes_masvs_and_maswe() -> None:
    versions = reference_db_versions()
    assert "masvs" in versions
    assert "maswe" in versions
    assert versions["masvs"]["count"] >= 8
    assert versions["masvs"]["source"]  # _meta.source surfaced
    assert versions["maswe"]["count"] >= 1


def test_invalidate_if_modified_clears_masvs_cache(tmp_path) -> None:
    p = tmp_path / "masvs.json"
    p.write_text('{"_meta": {}, "controls": {}}', encoding="utf-8")
    invalidate_if_modified(tmp_path)  # warmup
    future = time.time() + 5
    os.utime(p, (future, future))
    cleared = invalidate_if_modified(tmp_path)
    assert "masvs.json" in cleared


def test_invalidate_if_modified_clears_maswe_caches(tmp_path) -> None:
    p = tmp_path / "maswe.json"
    p.write_text('{"_meta": {}, "weaknesses": {}}', encoding="utf-8")
    invalidate_if_modified(tmp_path)  # warmup
    future = time.time() + 5
    os.utime(p, (future, future))
    cleared = invalidate_if_modified(tmp_path)
    assert "maswe.json" in cleared
```
- [ ] **Step 2: Run test to verify it fails**
Run: `python -m pytest tests/unit/report/test_mas_taxonomy.py -k "reference_db or invalidate" -q`
Expected: FAIL with `assert 'masvs' in versions` (KeyError / AssertionError — not yet registered)
- [ ] **Step 3: Extend both registration tables**
In `reference_db_versions` (current tuple, `tools/apd_gauntlet/report/taxonomy.py:286-292`):
```python
    for family, fn, path_name in (
        ("nist",   nist_control_titles,     "nist-controls.json"),
        ("attack", attack_technique_titles, "mitre-attack-techniques.json"),
        ("cwe",    cwe_titles,              "cwe.json"),
        ("d3fend", d3fend_titles,           "d3fend.json"),
        ("atlas",  atlas_titles,            "atlas-techniques.json"),
    ):
```
becomes:
```python
    for family, fn, path_name in (
        ("nist",   nist_control_titles,     "nist-controls.json"),
        ("attack", attack_technique_titles, "mitre-attack-techniques.json"),
        ("cwe",    cwe_titles,              "cwe.json"),
        ("d3fend", d3fend_titles,           "d3fend.json"),
        ("atlas",  atlas_titles,            "atlas-techniques.json"),
        ("masvs",  masvs_titles,            "masvs.json"),
        ("maswe",  maswe_titles,            "maswe.json"),
    ):
```
In `invalidate_if_modified`'s `catalog_to_loaders` map (current, `tools/apd_gauntlet/report/taxonomy.py:338-344`):
```python
        "nist-controls.json":            (nist_control_titles,),
        "mitre-attack-techniques.json":  (attack_technique_titles,),
        "cwe.json":                      (_cwe_catalog, cwe_titles, cwe_abstractions),
        "d3fend.json":                   (d3fend_titles,),
        "atlas-techniques.json":         (atlas_titles,),
    }
```
becomes:
```python
        "nist-controls.json":            (nist_control_titles,),
        "mitre-attack-techniques.json":  (attack_technique_titles,),
        "cwe.json":                      (_cwe_catalog, cwe_titles, cwe_abstractions),
        "d3fend.json":                   (d3fend_titles,),
        "atlas-techniques.json":         (atlas_titles,),
        "masvs.json":                    (masvs_titles,),
        "maswe.json":                    (maswe_titles, maswe_categories),
    }
```
- [ ] **Step 4: Run test to verify it passes**
Run: `python -m pytest tests/unit/report/test_mas_taxonomy.py -q`
Expected: PASS
- [ ] **Step 5: Commit**
```bash
git add tools/apd_gauntlet/report/taxonomy.py tests/unit/report/test_mas_taxonomy.py
git commit -m "feat(taxonomy): register MASVS/MASWE in reference_db_versions + cache invalidation"
```

---

Notes for the assembler: all five `taxonomy.py` edits land in the same module; if executed in one session the second/third/fourth tasks' insertion anchors (`atlas_titles` end at line 275, `d3fend_url` end at line 241) shift as earlier inserts land — re-grep for the anchor strings (`def reference_db_versions`, `return f"https://d3fend.mitre.org/technique/d3f:{local}/"`) before each Edit rather than trusting the line numbers above. The `maswe_categories` loader is introduced in the URL-builder task and referenced again in the invalidation-map task (`maswe.json: (maswe_titles, maswe_categories)`), so the URL-builder task must land before the registration task.

Relevant real files quoted: `/Users/shoveleejoe/Documents/GitHub/APD-sec-arch-framework/tools/apd_gauntlet/refresh_atlas.py`, `/Users/shoveleejoe/Documents/GitHub/APD-sec-arch-framework/tools/apd_gauntlet/refresh_d3fend.py`, `/Users/shoveleejoe/Documents/GitHub/APD-sec-arch-framework/tools/apd_gauntlet/report/taxonomy.py`, `/Users/shoveleejoe/Documents/GitHub/APD-sec-arch-framework/tools/apd_gauntlet/cli.py`, `/Users/shoveleejoe/Documents/GitHub/APD-sec-arch-framework/tests/test_refresh_atlas.py`, `/Users/shoveleejoe/Documents/GitHub/APD-sec-arch-framework/tests/unit/report/test_tier2_taxonomy.py`, `/Users/shoveleejoe/Documents/GitHub/APD-sec-arch-framework/tests/unit/report/test_tier4_taxonomy_cache.py`, `/Users/shoveleejoe/Documents/GitHub/APD-sec-arch-framework/tests/test_cli.py`.

---


## Phase 2 — Schemas (finding/capability/run-config/domain + coverage)

### Task 8: Add MASVS/MASWE id patterns to _defs.schema.json

**Files:**
- Modify: `schemas/_defs.schema.json:43-47`
- Test: `tests/test_meta_schemas.py`

- [ ] **Step 1: Write the failing test**
```python
def test_defs_declares_mas_id_patterns():
    """_defs carries the three OWASP MAS id patterns for MASWE/MASVS (v1.7)."""
    import json
    import pathlib
    import re

    repo = pathlib.Path(__file__).resolve().parent.parent
    defs = json.loads((repo / "schemas" / "_defs.schema.json").read_text())["$defs"]

    assert defs["maswe_id"]["pattern"] == r"^MASWE-[0-9]{4}$"
    assert re.match(defs["maswe_id"]["pattern"], "MASWE-0001")
    assert not re.match(defs["maswe_id"]["pattern"], "MASWE-1")

    cat = r"^MASVS-(STORAGE|CRYPTO|AUTH|NETWORK|PLATFORM|CODE|RESILIENCE|PRIVACY)$"
    assert defs["masvs_category_id"]["pattern"] == cat
    assert re.match(cat, "MASVS-STORAGE")
    assert not re.match(cat, "MASVS-STORAGE-1")

    ctrl = r"^MASVS-(STORAGE|CRYPTO|AUTH|NETWORK|PLATFORM|CODE|RESILIENCE|PRIVACY)-[1-9][0-9]*$"
    assert defs["masvs_control_id"]["pattern"] == ctrl
    assert re.match(ctrl, "MASVS-STORAGE-1")
    assert not re.match(ctrl, "MASVS-STORAGE-0")
    assert not re.match(ctrl, "MASVS-BOGUS-1")
```
- [ ] **Step 2: Run test to verify it fails**
Run: `python -m pytest tests/test_meta_schemas.py::test_defs_declares_mas_id_patterns -q`
Expected: FAIL with `KeyError: 'maswe_id'`
- [ ] **Step 3: Add the three $defs**
In `schemas/_defs.schema.json`, the `atlas_technique_id` def is currently the last entry in `$defs` (closes at line 47 with no trailing comma). Add a comma after its closing brace and append the three new defs:
```json
    "atlas_technique_id": {
      "type": "string",
      "pattern": "^AML\\.T[0-9]{4}(\\.[0-9]{3})?$",
      "description": "MITRE ATLAS technique ID; accepts both top-level (AML.T0051) and sub-technique (AML.T0051.000) forms."
    },
    "maswe_id": {
      "type": "string",
      "pattern": "^MASWE-[0-9]{4}$",
      "description": "OWASP MAS Weakness Enumeration ID (e.g. MASWE-0001). Always zero-padded to four digits."
    },
    "masvs_control_id": {
      "type": "string",
      "pattern": "^MASVS-(STORAGE|CRYPTO|AUTH|NETWORK|PLATFORM|CODE|RESILIENCE|PRIVACY)-[1-9][0-9]*$",
      "description": "OWASP MASVS v2 control ID: a category prefix plus a 1-based control ordinal (e.g. MASVS-STORAGE-1)."
    },
    "masvs_category_id": {
      "type": "string",
      "pattern": "^MASVS-(STORAGE|CRYPTO|AUTH|NETWORK|PLATFORM|CODE|RESILIENCE|PRIVACY)$",
      "description": "OWASP MASVS v2 control category (e.g. MASVS-STORAGE), without a control ordinal."
    }
```
- [ ] **Step 4: Run test to verify it passes**
Run: `python -m pytest tests/test_meta_schemas.py::test_defs_declares_mas_id_patterns -q`
Expected: PASS
- [ ] **Step 5: Commit**
```bash
git add schemas/_defs.schema.json tests/test_meta_schemas.py
git commit -m "feat(schema): add maswe_id, masvs_control_id, masvs_category_id to _defs"
```

### Task 9: Add masvs + maswe arrays to finding.schema.json control_mappings

**Files:**
- Modify: `schemas/finding.schema.json:100-104`
- Create: `tests/fixtures/valid/finding-with-mas.yaml`
- Create: `tests/fixtures/invalid/finding-with-invalid-maswe.yaml`
- Test: `tests/test_finding_schema.py`

- [ ] **Step 1: Write the failing test**
Append to `tests/test_finding_schema.py`:
```python
def test_finding_accepts_optional_masvs_and_maswe():
    schema = _load_schema()
    data = _load_yaml(FIXTURES / "valid" / "finding-with-mas.yaml")
    validator = _build_validator(schema)
    errors = list(validator.iter_errors(data["finding"]))
    assert errors == [], f"Unexpected errors: {[e.message for e in errors]}"


def test_finding_rejects_invalid_maswe_format():
    schema = _load_schema()
    data = _load_yaml(FIXTURES / "invalid" / "finding-with-invalid-maswe.yaml")
    validator = _build_validator(schema)
    errors = list(validator.iter_errors(data["finding"]))
    assert errors, "Expected validation errors for malformed MASWE id, got none"
```
Create `tests/fixtures/valid/finding-with-mas.yaml`:
```yaml
finding:
  schema_version: 1
  id: conf-a1b2c3d4
  agent: confidentiality
  apd_tier: trustworthiness
  apd_goal: confidentiality
  disposition: gap
  severity: high
  confidence: high
  title: "Session token persisted to insecure on-device storage"
  summary: "The mobile client writes the bearer token to a world-readable shared-preferences file."
  detail: "MainActivity.kt:88 stores the auth token in default SharedPreferences (MODE_WORLD_READABLE), exposing it to any co-resident app; maps to MASVS-STORAGE and MASWE-0006."
  evidence:
    - artifact: app/src/main/java/com/example/MainActivity.kt
      locator: "L88"
      excerpt: 'getSharedPreferences("auth", MODE_WORLD_READABLE).edit().putString("token", t)'
  control_mappings:
    nist_800_53r5: ["SC-28", "IA-5"]
    masvs: ["MASVS-STORAGE-1", "MASVS-STORAGE-2"]
    maswe: ["MASWE-0006"]
  recommendation:
    posture: required
    summary: "Store the token in the Android Keystore / EncryptedSharedPreferences."
    detail: "Replace MODE_WORLD_READABLE SharedPreferences with EncryptedSharedPreferences keyed by a Keystore-backed master key, and clear on logout."
```
Create `tests/fixtures/invalid/finding-with-invalid-maswe.yaml` (same record, but `maswe: ["MASWE-6"]` and `masvs: ["MASVS-BOGUS-1"]`):
```yaml
finding:
  schema_version: 1
  id: conf-a1b2c3d4
  agent: confidentiality
  apd_tier: trustworthiness
  apd_goal: confidentiality
  disposition: gap
  severity: high
  confidence: high
  title: "Session token persisted to insecure on-device storage"
  summary: "The mobile client writes the bearer token to a world-readable shared-preferences file."
  detail: "MainActivity.kt:88 stores the auth token in default SharedPreferences; malformed taxonomy ids under test."
  evidence:
    - artifact: app/src/main/java/com/example/MainActivity.kt
      locator: "L88"
      excerpt: 'getSharedPreferences("auth", MODE_WORLD_READABLE)'
  control_mappings:
    nist_800_53r5: ["SC-28"]
    masvs: ["MASVS-BOGUS-1"]
    maswe: ["MASWE-6"]
  recommendation:
    posture: required
    summary: "Store the token in the Android Keystore / EncryptedSharedPreferences."
    detail: "Replace MODE_WORLD_READABLE SharedPreferences with EncryptedSharedPreferences keyed by a Keystore-backed master key."
```
- [ ] **Step 2: Run test to verify it fails**
Run: `python -m pytest "tests/test_finding_schema.py::test_finding_accepts_optional_masvs_and_maswe" "tests/test_finding_schema.py::test_finding_rejects_invalid_maswe_format" -q`
Expected: FAIL — accept-test errors with "Additional properties are not allowed ('masvs', 'maswe' ...)"; reject-test fails because the unknown keys aren't yet pattern-constrained (it may already error on additionalProperties, but after Step 3 the reject must come from the id pattern).
- [ ] **Step 3: Add the masvs/maswe arrays**
In `schemas/finding.schema.json`, the `atlas` array is the last entry in `control_mappings.properties` (closes at line 103 with no trailing comma). Add a comma after its closing brace and append:
```json
        "atlas": {
          "type": "array",
          "items": { "$ref": "_defs.schema.json#/$defs/atlas_technique_id" }
        },
        "masvs": {
          "type": "array",
          "items": { "$ref": "_defs.schema.json#/$defs/masvs_control_id" }
        },
        "maswe": {
          "type": "array",
          "items": { "$ref": "_defs.schema.json#/$defs/maswe_id" }
        }
```
- [ ] **Step 4: Run test to verify it passes**
Run: `python -m pytest "tests/test_finding_schema.py::test_finding_accepts_optional_masvs_and_maswe" "tests/test_finding_schema.py::test_finding_rejects_invalid_maswe_format" -q`
Expected: PASS
- [ ] **Step 5: Commit**
```bash
git add schemas/finding.schema.json tests/fixtures/valid/finding-with-mas.yaml tests/fixtures/invalid/finding-with-invalid-maswe.yaml tests/test_finding_schema.py
git commit -m "feat(schema): allow findings to carry masvs/maswe control mappings"
```

### Task 10: Add masvs array to capability.schema.json control_mappings

**Files:**
- Modify: `schemas/capability.schema.json:58-75`
- Create: `tests/fixtures/valid/capability-with-masvs.yaml`
- Create: `tests/fixtures/invalid/capability-with-invalid-masvs.yaml`
- Test: `tests/test_capability_schema.py`

- [ ] **Step 1: Write the failing test**
Append to `tests/test_capability_schema.py`:
```python
def test_capability_accepts_optional_masvs():
    validator = _build_validator()
    data = _load_yaml(FIXTURES / "valid" / "capability-with-masvs.yaml")
    errors = list(validator.iter_errors(data["capability"]))
    assert errors == [], f"Unexpected errors: {[e.message for e in errors]}"


def test_capability_rejects_invalid_masvs_format():
    validator = _build_validator()
    data = _load_yaml(FIXTURES / "invalid" / "capability-with-invalid-masvs.yaml")
    errors = list(validator.iter_errors(data["capability"]))
    assert errors, "Expected validation errors for malformed MASVS control id, got none"


def test_capability_control_mappings_has_no_maswe_property():
    """maswe is findings-only; capability control_mappings must not declare it."""
    import json
    schema = json.loads((REPO / "schemas" / "capability.schema.json").read_text())
    props = schema["properties"]["control_mappings"]["properties"]
    assert "masvs" in props
    assert "maswe" not in props
```
Create `tests/fixtures/valid/capability-with-masvs.yaml`:
```yaml
capability:
  schema_version: 1
  id: conf-cap-1a2b3c4d
  agent: confidentiality
  apd_tier: trustworthiness
  apd_goal: confidentiality
  title: "Keystore-backed encrypted credential storage"
  description: "The mobile client stores all auth material in EncryptedSharedPreferences keyed by a hardware-backed Android Keystore master key."
  maturity: implemented
  scope: "Confirmed for the auth and session modules. Not addressed: cached profile images and the offline draft cache."
  evidence:
    - artifact: app/src/main/java/com/example/SecureStore.kt
      locator: "L20"
      excerpt: "EncryptedSharedPreferences.create(... MasterKeys.AES256_GCM_SPEC ...)"
  control_mappings:
    nist_800_53r5: ["SC-28", "IA-5"]
    masvs: ["MASVS-STORAGE-1"]
```
Create `tests/fixtures/invalid/capability-with-invalid-masvs.yaml` (same, but `masvs: ["MASVS-STORAGE-0"]`):
```yaml
capability:
  schema_version: 1
  id: conf-cap-1a2b3c4d
  agent: confidentiality
  apd_tier: trustworthiness
  apd_goal: confidentiality
  title: "Keystore-backed encrypted credential storage"
  description: "The mobile client stores all auth material in EncryptedSharedPreferences keyed by a hardware-backed Android Keystore master key."
  maturity: implemented
  scope: "Confirmed for the auth and session modules. Not addressed: cached profile images and the offline draft cache."
  evidence:
    - artifact: app/src/main/java/com/example/SecureStore.kt
      locator: "L20"
      excerpt: "EncryptedSharedPreferences.create(... MasterKeys.AES256_GCM_SPEC ...)"
  control_mappings:
    nist_800_53r5: ["SC-28"]
    masvs: ["MASVS-STORAGE-0"]
```
- [ ] **Step 2: Run test to verify it fails**
Run: `python -m pytest "tests/test_capability_schema.py::test_capability_accepts_optional_masvs" "tests/test_capability_schema.py::test_capability_rejects_invalid_masvs_format" "tests/test_capability_schema.py::test_capability_control_mappings_has_no_maswe_property" -q`
Expected: FAIL — accept-test errors with "Additional properties are not allowed ('masvs' ...)".
- [ ] **Step 3: Add the masvs array**
In `schemas/capability.schema.json`, the `d3fend` array is the last entry in `control_mappings.properties` (closes at line 74 with no trailing comma). Add a comma after its closing brace and append `masvs` (note: no `maswe` here — maswe is findings-only):
```json
        "d3fend": {
          "type": "array",
          "items": {
            "type": "object",
            "required": ["technique", "counters_attack", "rationale"],
            "additionalProperties": false,
            "properties": {
              "technique":       { "$ref": "_defs.schema.json#/$defs/d3fend_id" },
              "counters_attack": {
                "type": "array",
                "minItems": 1,
                "items": { "$ref": "_defs.schema.json#/$defs/attack_technique_id" }
              },
              "rationale":       { "type": "string", "minLength": 30 }
            }
          }
        },
        "masvs": {
          "type": "array",
          "items": { "$ref": "_defs.schema.json#/$defs/masvs_control_id" }
        }
```
- [ ] **Step 4: Run test to verify it passes**
Run: `python -m pytest "tests/test_capability_schema.py::test_capability_accepts_optional_masvs" "tests/test_capability_schema.py::test_capability_rejects_invalid_masvs_format" "tests/test_capability_schema.py::test_capability_control_mappings_has_no_maswe_property" -q`
Expected: PASS
- [ ] **Step 5: Commit**
```bash
git add schemas/capability.schema.json tests/fixtures/valid/capability-with-masvs.yaml tests/fixtures/invalid/capability-with-invalid-masvs.yaml tests/test_capability_schema.py
git commit -m "feat(schema): allow capabilities to carry masvs control mappings"
```

### Task 11: Add masvs/maswe to run-config taxonomies enum

**Files:**
- Modify: `schemas/run-config.schema.json:15-22`
- Test: `tests/test_run_config_schema.py`

- [ ] **Step 1: Write the failing test**
Append to `tests/test_run_config_schema.py`:
```python
@pytest.mark.parametrize("tax", ["masvs", "maswe"])
def test_run_config_accepts_mas_taxonomies(tax):
    """The OWASP MAS taxonomies (v1.7+) are accepted enum values."""
    data = {
        "run_id": "apd-20260609-mobile",
        "domains": ["mobile-applications"],
        "framework_version": "1.7.0",
        "taxonomies": [tax],
    }
    errors = list(Draft202012Validator(SCHEMA).iter_errors(data))
    assert errors == []


def test_run_config_accepts_both_mas_taxonomies_together():
    data = {
        "run_id": "apd-20260609-mobile",
        "domains": ["mobile-applications"],
        "framework_version": "1.7.0",
        "taxonomies": ["masvs", "maswe"],
    }
    errors = list(Draft202012Validator(SCHEMA).iter_errors(data))
    assert errors == []
```
- [ ] **Step 2: Run test to verify it fails**
Run: `python -m pytest "tests/test_run_config_schema.py::test_run_config_accepts_mas_taxonomies" "tests/test_run_config_schema.py::test_run_config_accepts_both_mas_taxonomies_together" -q`
Expected: FAIL with "'masvs' is not one of [...]" (enum violation)
- [ ] **Step 3: Extend the taxonomies enum**
In `schemas/run-config.schema.json`, the `taxonomies.items.enum` currently reads:
```json
        "enum": ["cwe", "mitre_attack", "d3fend", "owasp_top10", "owasp_api_top10", "owasp_llm_top10", "mitre_atlas"]
```
Replace it with (append `masvs`, `maswe`):
```json
        "enum": ["cwe", "mitre_attack", "d3fend", "owasp_top10", "owasp_api_top10", "owasp_llm_top10", "mitre_atlas", "masvs", "maswe"]
```
- [ ] **Step 4: Run test to verify it passes**
Run: `python -m pytest "tests/test_run_config_schema.py::test_run_config_accepts_mas_taxonomies" "tests/test_run_config_schema.py::test_run_config_accepts_both_mas_taxonomies_together" -q`
Expected: PASS
- [ ] **Step 5: Commit**
```bash
git add schemas/run-config.schema.json tests/test_run_config_schema.py
git commit -m "feat(schema): add masvs/maswe to run-config taxonomies enum"
```

### Task 12: Add optional taxonomies array to domain.schema.json

**Files:**
- Modify: `schemas/domain.schema.json:40-52`
- Create: `tests/fixtures/valid/domain-with-taxonomies.yaml`
- Create: `tests/fixtures/invalid/domain-with-invalid-taxonomy.yaml`
- Test: `tests/test_validate_domain.py`

- [ ] **Step 1: Write the failing test**
Append to `tests/test_validate_domain.py` (it already imports `build_registry` and `Draft202012Validator`; confirm helper names with a quick read, otherwise inline the validator as below):
```python
def test_domain_accepts_optional_taxonomies(tmp_path=None):
    import json
    import pathlib
    import yaml
    from apd_gauntlet.validate import build_registry
    from jsonschema import Draft202012Validator

    repo = pathlib.Path(__file__).resolve().parent.parent
    schema = json.loads((repo / "schemas" / "domain.schema.json").read_text())
    doc = yaml.safe_load(
        (repo / "tests" / "fixtures" / "valid" / "domain-with-taxonomies.yaml").read_text()
    )
    errors = list(Draft202012Validator(schema, registry=build_registry()).iter_errors(doc))
    assert errors == [], [e.message for e in errors]
    assert doc["taxonomies"] == ["masvs", "maswe"]


def test_domain_rejects_unknown_taxonomy():
    import json
    import pathlib
    import yaml
    from apd_gauntlet.validate import build_registry
    from jsonschema import Draft202012Validator

    repo = pathlib.Path(__file__).resolve().parent.parent
    schema = json.loads((repo / "schemas" / "domain.schema.json").read_text())
    doc = yaml.safe_load(
        (repo / "tests" / "fixtures" / "invalid" / "domain-with-invalid-taxonomy.yaml").read_text()
    )
    errors = list(Draft202012Validator(schema, registry=build_registry()).iter_errors(doc))
    assert errors, "unknown domain taxonomy must be rejected by the enum"
```
Create `tests/fixtures/valid/domain-with-taxonomies.yaml`:
```yaml
name: mobile-applications
display_name: "Mobile Applications"
version: 1.0.0
framework_compat: ">=1.7.0,<2.0.0"
description: "Mobile-app severity rubric and pattern library anchored to OWASP MASVS v2 and MASWE."
includes:
  - severity-rubric.md
  - common-patterns/confidentiality.md
regulatory_anchors:
  - "OWASP MASVS"
taxonomies:
  - masvs
  - maswe
```
Create `tests/fixtures/invalid/domain-with-invalid-taxonomy.yaml` (same head, but a bad enum value):
```yaml
name: mobile-applications
display_name: "Mobile Applications"
version: 1.0.0
framework_compat: ">=1.7.0,<2.0.0"
description: "Mobile-app severity rubric and pattern library anchored to OWASP MASVS v2 and MASWE."
includes:
  - severity-rubric.md
regulatory_anchors:
  - "OWASP MASVS"
taxonomies:
  - masvs
  - not_a_real_taxonomy
```
- [ ] **Step 2: Run test to verify it fails**
Run: `python -m pytest "tests/test_validate_domain.py::test_domain_accepts_optional_taxonomies" "tests/test_validate_domain.py::test_domain_rejects_unknown_taxonomy" -q`
Expected: FAIL — accept-test errors with "Additional properties are not allowed ('taxonomies' ...)" because `additionalProperties:false` and the property doesn't exist yet.
- [ ] **Step 3: Add the optional taxonomies array**
In `schemas/domain.schema.json`, the `default_trust_boundaries` block is the last entry in `properties` (closes at line 51 with no trailing comma). Add a comma after its closing brace and append the enum-constrained optional array (keep `taxonomies` OUT of the top-level `required` list — it stays optional):
```json
    "default_trust_boundaries": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["boundary", "description"],
        "additionalProperties": false,
        "properties": {
          "boundary":    { "type": "string", "minLength": 1 },
          "description": { "type": "string", "minLength": 10 }
        }
      }
    },
    "taxonomies": {
      "type": "array",
      "uniqueItems": true,
      "description": "Optional. Taxonomies this pack expects the run to activate (lifted into run-config). Values match the run-config taxonomies enum subset this pack supports; the mobile pack declares [masvs, maswe].",
      "items": {
        "type": "string",
        "enum": ["cwe", "mitre_attack", "d3fend", "owasp_top10", "owasp_api_top10", "owasp_llm_top10", "mitre_atlas", "masvs", "maswe"]
      }
    }
```
- [ ] **Step 4: Run test to verify it passes**
Run: `python -m pytest "tests/test_validate_domain.py::test_domain_accepts_optional_taxonomies" "tests/test_validate_domain.py::test_domain_rejects_unknown_taxonomy" -q`
Expected: PASS
- [ ] **Step 5: Commit**
```bash
git add schemas/domain.schema.json tests/fixtures/valid/domain-with-taxonomies.yaml tests/fixtures/invalid/domain-with-invalid-taxonomy.yaml tests/test_validate_domain.py
git commit -m "feat(schema): add optional enum-constrained taxonomies array to domain packs"
```

### Task 13: Create masvs-coverage.schema.json (NIST-content shape, single-file packaging)

**Files:**
- Create: `schemas/masvs-coverage.schema.json`
- Create: `tests/fixtures/valid/masvs-coverage-valid.yaml`
- Create: `tests/fixtures/invalid/masvs-coverage-invalid.yaml`
- Test: `tests/test_other_schemas.py`

- [ ] **Step 1: Write the failing test**
Append to `tests/test_other_schemas.py` (mirror the `build_registry` + `Draft202012Validator` style used elsewhere; if the file lacks those imports, add them at top):
```python
def test_masvs_coverage_schema_accepts_valid_sample():
    import json
    import pathlib
    import yaml
    from apd_gauntlet.validate import build_registry
    from jsonschema import Draft202012Validator

    repo = pathlib.Path(__file__).resolve().parent.parent
    schema = json.loads((repo / "schemas" / "masvs-coverage.schema.json").read_text())
    doc = yaml.safe_load(
        (repo / "tests" / "fixtures" / "valid" / "masvs-coverage-valid.yaml").read_text()
    )
    errors = list(Draft202012Validator(schema, registry=build_registry()).iter_errors(doc))
    assert errors == [], [e.message for e in errors]


def test_masvs_coverage_schema_rejects_bad_control_id():
    import json
    import pathlib
    import yaml
    from apd_gauntlet.validate import build_registry
    from jsonschema import Draft202012Validator

    repo = pathlib.Path(__file__).resolve().parent.parent
    schema = json.loads((repo / "schemas" / "masvs-coverage.schema.json").read_text())
    doc = yaml.safe_load(
        (repo / "tests" / "fixtures" / "invalid" / "masvs-coverage-invalid.yaml").read_text()
    )
    errors = list(Draft202012Validator(schema, registry=build_registry()).iter_errors(doc))
    assert errors, "bad masvs_id / posture must be rejected"
```
Create `tests/fixtures/valid/masvs-coverage-valid.yaml`:
```yaml
schema_version: 1
generated_by: synthesizer
controls:
  - masvs_id: MASVS-STORAGE-1
    name: "The app securely stores sensitive data."
    category: MASVS-STORAGE
    category_title: "Storage"
    finding_count: 1
    finding_ids: [conf-a1b2c3d4]
    surfaces:
      - "android/shared-preferences"
    capability_count: 1
    capability_ids: [conf-cap-1a2b3c4d]
    posture: gapped_and_covered
  - masvs_id: MASVS-CRYPTO-2
    name: "The app uses cryptographic primitives appropriately."
    category: MASVS-CRYPTO
    category_title: "Cryptography"
    finding_count: 0
    finding_ids: []
    surfaces: []
    capability_count: 0
    capability_ids: []
    posture: silent
```
Create `tests/fixtures/invalid/masvs-coverage-invalid.yaml` (bad `masvs_id` ordinal and bad `posture`):
```yaml
schema_version: 1
generated_by: synthesizer
controls:
  - masvs_id: MASVS-STORAGE-0
    name: "The app securely stores sensitive data."
    category: MASVS-STORAGE
    category_title: "Storage"
    finding_count: 0
    finding_ids: []
    surfaces: []
    capability_count: 0
    capability_ids: []
    posture: not_a_posture
```
- [ ] **Step 2: Run test to verify it fails**
Run: `python -m pytest "tests/test_other_schemas.py::test_masvs_coverage_schema_accepts_valid_sample" "tests/test_other_schemas.py::test_masvs_coverage_schema_rejects_bad_control_id" -q`
Expected: FAIL with `FileNotFoundError: .../schemas/masvs-coverage.schema.json`
- [ ] **Step 3: Create the schema (single-file convention like cwe-coverage; NIST content shape with masvs_id + category)**
Create `schemas/masvs-coverage.schema.json`:
```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://github.com/shoveleejoe/apd-gauntlet/schemas/masvs-coverage.schema.json",
  "title": "APD Gauntlet OWASP MASVS Coverage Rollup",
  "type": "object",
  "required": ["schema_version", "generated_by", "controls"],
  "additionalProperties": false,
  "properties": {
    "schema_version": { "type": "integer", "const": 1 },
    "generated_by":   { "type": "string", "enum": ["synthesizer"] },
    "controls": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["masvs_id", "name", "category", "category_title", "finding_count", "finding_ids", "capability_count", "capability_ids", "posture"],
        "additionalProperties": false,
        "properties": {
          "masvs_id":         { "$ref": "_defs.schema.json#/$defs/masvs_control_id" },
          "name":             { "type": "string", "minLength": 3 },
          "category":         { "$ref": "_defs.schema.json#/$defs/masvs_category_id" },
          "category_title":   { "type": "string", "minLength": 1 },
          "finding_count":    { "type": "integer", "minimum": 0 },
          "finding_ids":      { "type": "array", "items": { "type": "string" } },
          "surfaces":         { "type": "array", "items": { "type": "string", "minLength": 1 } },
          "capability_count": { "type": "integer", "minimum": 0 },
          "capability_ids":   { "type": "array", "items": { "type": "string" } },
          "posture":          { "type": "string", "enum": ["silent", "covered", "gapped", "gapped_and_covered"] }
        }
      }
    }
  }
}
```
- [ ] **Step 4: Run test to verify it passes**
Run: `python -m pytest "tests/test_other_schemas.py::test_masvs_coverage_schema_accepts_valid_sample" "tests/test_other_schemas.py::test_masvs_coverage_schema_rejects_bad_control_id" -q`
Expected: PASS
- [ ] **Step 5: Commit**
```bash
git add schemas/masvs-coverage.schema.json tests/fixtures/valid/masvs-coverage-valid.yaml tests/fixtures/invalid/masvs-coverage-invalid.yaml tests/test_other_schemas.py
git commit -m "feat(schema): add masvs-coverage rollup schema"
```

### Task 14: Create maswe-coverage.schema.json (cwe-coverage packaging shape)

**Files:**
- Create: `schemas/maswe-coverage.schema.json`
- Create: `tests/fixtures/valid/maswe-coverage-valid.yaml`
- Create: `tests/fixtures/invalid/maswe-coverage-invalid.yaml`
- Test: `tests/test_other_schemas.py`

- [ ] **Step 1: Write the failing test**
Append to `tests/test_other_schemas.py`:
```python
def test_maswe_coverage_schema_accepts_valid_sample():
    import json
    import pathlib
    import yaml
    from apd_gauntlet.validate import build_registry
    from jsonschema import Draft202012Validator

    repo = pathlib.Path(__file__).resolve().parent.parent
    schema = json.loads((repo / "schemas" / "maswe-coverage.schema.json").read_text())
    doc = yaml.safe_load(
        (repo / "tests" / "fixtures" / "valid" / "maswe-coverage-valid.yaml").read_text()
    )
    errors = list(Draft202012Validator(schema, registry=build_registry()).iter_errors(doc))
    assert errors == [], [e.message for e in errors]


def test_maswe_coverage_schema_rejects_bad_weakness_id():
    import json
    import pathlib
    import yaml
    from apd_gauntlet.validate import build_registry
    from jsonschema import Draft202012Validator

    repo = pathlib.Path(__file__).resolve().parent.parent
    schema = json.loads((repo / "schemas" / "maswe-coverage.schema.json").read_text())
    doc = yaml.safe_load(
        (repo / "tests" / "fixtures" / "invalid" / "maswe-coverage-invalid.yaml").read_text()
    )
    errors = list(Draft202012Validator(schema, registry=build_registry()).iter_errors(doc))
    assert errors, "bad maswe_id / parent_masvs must be rejected"
```
Create `tests/fixtures/valid/maswe-coverage-valid.yaml`:
```yaml
schema_version: 1
generated_by: synthesizer
entries:
  - maswe_id: MASWE-0006
    name: "Sensitive data stored in unencrypted shared storage"
    category: MASVS-STORAGE
    status: new
    parent_masvs: [MASVS-STORAGE-1, MASVS-STORAGE-2]
    finding_count: 1
    finding_ids: [conf-a1b2c3d4]
    surfaces:
      - "android/shared-preferences"
  - maswe_id: MASWE-0001
    name: "Hardcoded cryptographic key"
    category: MASVS-CRYPTO
    status: draft
    parent_masvs: []
    finding_count: 0
    finding_ids: []
    surfaces: []
```
Create `tests/fixtures/invalid/maswe-coverage-invalid.yaml` (bad `maswe_id` width and bad `parent_masvs` entry):
```yaml
schema_version: 1
generated_by: synthesizer
entries:
  - maswe_id: MASWE-6
    name: "Sensitive data stored in unencrypted shared storage"
    category: MASVS-STORAGE
    status: new
    parent_masvs: [MASVS-STORAGE]
    finding_count: 0
    finding_ids: []
    surfaces: []
```
- [ ] **Step 2: Run test to verify it fails**
Run: `python -m pytest "tests/test_other_schemas.py::test_maswe_coverage_schema_accepts_valid_sample" "tests/test_other_schemas.py::test_maswe_coverage_schema_rejects_bad_weakness_id" -q`
Expected: FAIL with `FileNotFoundError: .../schemas/maswe-coverage.schema.json`
- [ ] **Step 3: Create the schema (cwe-coverage shape: entries[] with single-file packaging)**
Create `schemas/maswe-coverage.schema.json`. `parent_masvs` items are `masvs_control_id` (not category) since a weakness maps to specific MASVS v2 controls:
```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://github.com/shoveleejoe/apd-gauntlet/schemas/maswe-coverage.schema.json",
  "title": "APD Gauntlet OWASP MASWE Coverage Rollup",
  "type": "object",
  "required": ["schema_version", "generated_by", "entries"],
  "additionalProperties": false,
  "properties": {
    "schema_version": { "type": "integer", "const": 1 },
    "generated_by":   { "type": "string", "enum": ["synthesizer"] },
    "entries": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["maswe_id", "name", "category", "status", "parent_masvs", "finding_count", "finding_ids"],
        "additionalProperties": false,
        "properties": {
          "maswe_id":      { "$ref": "_defs.schema.json#/$defs/maswe_id" },
          "name":          { "type": "string", "minLength": 3 },
          "category":      { "$ref": "_defs.schema.json#/$defs/masvs_category_id" },
          "status":        { "type": "string", "minLength": 1 },
          "parent_masvs":  { "type": "array", "items": { "$ref": "_defs.schema.json#/$defs/masvs_control_id" } },
          "finding_count": { "type": "integer", "minimum": 0 },
          "finding_ids":   { "type": "array", "items": { "type": "string" } },
          "surfaces":      { "type": "array", "items": { "type": "string", "minLength": 1 } }
        }
      }
    }
  }
}
```
- [ ] **Step 4: Run test to verify it passes**
Run: `python -m pytest "tests/test_other_schemas.py::test_maswe_coverage_schema_accepts_valid_sample" "tests/test_other_schemas.py::test_maswe_coverage_schema_rejects_bad_weakness_id" -q`
Expected: PASS
- [ ] **Step 5: Commit**
```bash
git add schemas/maswe-coverage.schema.json tests/fixtures/valid/maswe-coverage-valid.yaml tests/fixtures/invalid/maswe-coverage-invalid.yaml tests/test_other_schemas.py
git commit -m "feat(schema): add maswe-coverage rollup schema"
```

### Task 15: Register masvs-coverage + maswe-coverage in validate.py SYNTHESIS_ROLLUPS

**Files:**
- Modify: `tools/apd_gauntlet/validate.py:234-274`
- Test: `tests/test_synthesis_doc_wrappers.py`

- [ ] **Step 1: Write the failing test**
Append to `tests/test_synthesis_doc_wrappers.py`:
```python
def test_mas_coverage_rollups_wired_into_synthesis_rollups():
    """The two OWASP MAS coverage rollups (v1.7) are wired to their single-file schemas."""
    assert SYNTHESIS_ROLLUPS["masvs-coverage.yaml"] == "masvs-coverage.schema.json"
    assert SYNTHESIS_ROLLUPS["maswe-coverage.yaml"] == "maswe-coverage.schema.json"
```
- [ ] **Step 2: Run test to verify it fails**
Run: `python -m pytest "tests/test_synthesis_doc_wrappers.py::test_mas_coverage_rollups_wired_into_synthesis_rollups" -q`
Expected: FAIL with `KeyError: 'masvs-coverage.yaml'`
- [ ] **Step 3: Add the two entries to SYNTHESIS_ROLLUPS**
In `tools/apd_gauntlet/validate.py`, the `SYNTHESIS_ROLLUPS` dict opens at line 234. Add the two MAS rollups alongside the other coverage rollups (insert right after the `atlas-coverage.yaml` line at 238):
```python
    "cwe-coverage.yaml":           "cwe-coverage.schema.json",
    "owasp-coverage.yaml":         "owasp-coverage.schema.json",
    "d3fend-coverage.yaml":        "d3fend-coverage.schema.json",
    "atlas-coverage.yaml":         "atlas-coverage.schema.json",
    # v1.7 — OWASP MAS (mobile) coverage rollups. Single-file convention like
    # cwe-coverage (no -doc wrapper); registered directly here.
    "masvs-coverage.yaml":         "masvs-coverage.schema.json",
    "maswe-coverage.yaml":         "maswe-coverage.schema.json",
```
- [ ] **Step 4: Run test to verify it passes**
Run: `python -m pytest "tests/test_synthesis_doc_wrappers.py::test_mas_coverage_rollups_wired_into_synthesis_rollups" -q`
Expected: PASS
- [ ] **Step 5: Commit**
```bash
git add tools/apd_gauntlet/validate.py tests/test_synthesis_doc_wrappers.py
git commit -m "feat(validate): wire masvs/maswe coverage rollups into SYNTHESIS_ROLLUPS"
```

### Task 16: Verify the full schema test suite is green (regression gate)

**Files:**
- Test: `tests/test_finding_schema.py`, `tests/test_capability_schema.py`, `tests/test_run_config_schema.py`, `tests/test_validate_domain.py`, `tests/test_other_schemas.py`, `tests/test_synthesis_doc_wrappers.py`, `tests/test_meta_schemas.py`

- [ ] **Step 1: Write the failing test**
No new test — this is the consolidated regression gate over every schema touched in this section. (The parametrized fixture-glob tests in `test_finding_schema.py` / `test_capability_schema.py` automatically pick up the new `tests/fixtures/valid/*` and `tests/fixtures/invalid/*` files, so confirm they all still pass together.)
- [ ] **Step 2: Run test to verify it fails**
Run: `python -m pytest tests/test_finding_schema.py tests/test_capability_schema.py tests/test_run_config_schema.py tests/test_validate_domain.py tests/test_other_schemas.py tests/test_synthesis_doc_wrappers.py tests/test_meta_schemas.py -q`
Expected: PASS if all prior tasks landed; if any FAIL, fix the offending schema/fixture before proceeding (e.g. a new invalid fixture accidentally also matching the `valid/` glob, or a trailing-comma JSON error surfacing as a load failure across many tests).
- [ ] **Step 3: Confirm JSON well-formedness of every edited schema**
```bash
python -c "import json,glob; [json.loads(open(f).read()) for f in glob.glob('schemas/*.schema.json')]; print('all schemas parse')"
```
- [ ] **Step 4: Run test to verify it passes**
Run: `python -m pytest tests/test_finding_schema.py tests/test_capability_schema.py tests/test_run_config_schema.py tests/test_validate_domain.py tests/test_other_schemas.py tests/test_synthesis_doc_wrappers.py tests/test_meta_schemas.py -q`
Expected: PASS
- [ ] **Step 5: Commit**
```bash
git add -A
git commit -m "test(schema): green regression gate for masvs/maswe additive schema changes" --allow-empty
```

---


## Phase 3 — Activation: pack-declared → auto-seeded run taxonomies

### Task 17: Verify run-config + domain taxonomy enums accept masvs/maswe

> **Reconciliation note:** the schema edits here are the SAME changes already made in **Task 11** (run-config `taxonomies` enum) and **Task 12** (domain `taxonomies` array). Executing in order, those edits are done and the test below already PASSES — treat this as a verification checkpoint. If it fails, apply the edits from Tasks 11–12 first, then re-run.

**Files:**
- Modify: `schemas/run-config.schema.json:15-22`
- Modify: `schemas/domain.schema.json:6-15`
- Test: `tests/test_init_run_config.py`

- [ ] **Step 1: Write the failing test**
```python
# Append to tests/test_init_run_config.py

def test_run_config_schema_accepts_mas_taxonomies(tmp_path):
    """run-config taxonomy enum must accept masvs + maswe so a MAS run validates."""
    inputs = tmp_path / "in"
    inputs.mkdir()
    (inputs / "tech_plan.md").write_text("# Plan\n")

    run_dir = scaffold_run(
        "run-mas", inputs, ["pbm"], tmp_path / "runs",
        taxonomies=["masvs", "maswe"],
    )

    cfg = yaml.safe_load((run_dir / ".apd-run.yaml").read_text())
    assert cfg["taxonomies"] == ["masvs", "maswe"]
    errors = list(Draft202012Validator(RUN_CONFIG_SCHEMA).iter_errors(cfg))
    assert errors == [], [e.message for e in errors]


def test_domain_schema_accepts_taxonomies_field(tmp_path):
    """domain.schema.json must allow an optional top-level taxonomies array with the
    masvs/maswe enum values (additionalProperties is false, so it needs an explicit
    property)."""
    import json
    schema = json.loads((REPO / "schemas" / "domain.schema.json").read_text())
    meta = {
        "name": "x",
        "display_name": "X Domain",
        "version": "1.0.0",
        "framework_compat": ">=1.0.0,<2.0.0",
        "description": "A domain pack used only for this schema test, padded.",
        "includes": ["severity-rubric.md"],
        "regulatory_anchors": [],
        "taxonomies": ["masvs", "maswe"],
    }
    errors = list(Draft202012Validator(schema).iter_errors(meta))
    assert errors == [], [e.message for e in errors]
```
- [ ] **Step 2: Run test to verify it fails**
Run: `python3 -m pytest tests/test_init_run_config.py::test_run_config_schema_accepts_mas_taxonomies tests/test_init_run_config.py::test_domain_schema_accepts_taxonomies_field -q`
Expected: FAIL — first test errors with "'masvs' is not one of [...]" (enum reject); second with "Additional properties are not allowed ('taxonomies' was unexpected)"
- [ ] **Step 3: Add the enum values and the domain taxonomies property**

In `schemas/run-config.schema.json`, extend the `taxonomies` enum (currently lines 15-22):
```json
    "taxonomies": {
      "type": "array",
      "uniqueItems": true,
      "items": {
        "type": "string",
        "enum": ["cwe", "mitre_attack", "d3fend", "owasp_top10", "owasp_api_top10", "owasp_llm_top10", "mitre_atlas", "masvs", "maswe"]
      }
    },
```

In `schemas/domain.schema.json`, add a `taxonomies` property after `regulatory_anchors` (current line 15) so `additionalProperties: false` no longer rejects it:
```json
    "regulatory_anchors": { "type": "array", "items": { "type": "string" } },
    "taxonomies": {
      "type": "array",
      "uniqueItems": true,
      "items": {
        "type": "string",
        "enum": ["cwe", "mitre_attack", "d3fend", "owasp_top10", "owasp_api_top10", "owasp_llm_top10", "mitre_atlas", "masvs", "maswe"]
      },
      "description": "Optional taxonomies this pack auto-seeds onto the run's taxonomies list when selected. Unioned with operator-supplied --taxonomies (deduped, stable order)."
    },
```
- [ ] **Step 4: Run test to verify it passes**
Run: `python3 -m pytest tests/test_init_run_config.py::test_run_config_schema_accepts_mas_taxonomies tests/test_init_run_config.py::test_domain_schema_accepts_taxonomies_field -q`
Expected: PASS
- [ ] **Step 5: Commit**
```bash
git add schemas/run-config.schema.json schemas/domain.schema.json tests/test_init_run_config.py
git commit -m "feat(schema): accept masvs/maswe in run-config taxonomy enum and add domain taxonomies field"
```

### Task 18: Declare taxonomies [masvs, maswe] on the mobile pack

**Files:**
- Modify: `domains/mobile-applications/domain.yaml:20`
- Test: `tests/test_init_run_config.py`

- [ ] **Step 1: Write the failing test**
```python
# Append to tests/test_init_run_config.py

def test_mobile_pack_declares_mas_taxonomies():
    """The mobile pack must declare taxonomies: [masvs, maswe] so selecting it
    auto-seeds the run taxonomies; the file must still schema-validate."""
    import json
    schema = json.loads((REPO / "schemas" / "domain.schema.json").read_text())
    meta = yaml.safe_load(
        (REPO / "domains" / "mobile-applications" / "domain.yaml").read_text()
    )
    assert meta.get("taxonomies") == ["masvs", "maswe"]
    errors = list(Draft202012Validator(schema).iter_errors(meta))
    assert errors == [], [e.message for e in errors]
```
- [ ] **Step 2: Run test to verify it fails**
Run: `python3 -m pytest tests/test_init_run_config.py::test_mobile_pack_declares_mas_taxonomies -q`
Expected: FAIL with "assert None == ['masvs', 'maswe']" (taxonomies field absent)
- [ ] **Step 3: Add the taxonomies block to the mobile domain.yaml**

The file currently has `regulatory_anchors:` ending at line 30 followed by `crown_jewels:` at line 31. Insert the `taxonomies` block between them:
```yaml
  - "Google Play Data Safety"
taxonomies:
  - masvs
  - maswe
crown_jewels:
```
- [ ] **Step 4: Run test to verify it passes**
Run: `python3 -m pytest tests/test_init_run_config.py::test_mobile_pack_declares_mas_taxonomies -q && python3 -m apd_gauntlet validate-domain mobile-applications`
Expected: PASS; validate-domain prints "Domain pack 'mobile-applications' OK"
- [ ] **Step 5: Commit**
```bash
git add domains/mobile-applications/domain.yaml tests/test_init_run_config.py
git commit -m "feat(mobile): declare taxonomies [masvs, maswe] on the mobile pack"
```

### Task 19: Add pack-taxonomy resolver to init_run

**Files:**
- Modify: `tools/apd_gauntlet/init_run.py:1-13`
- Test: `tests/test_init_run.py`

- [ ] **Step 1: Write the failing test**
```python
# Append to tests/test_init_run.py

def test_resolve_pack_taxonomies_unions_in_stable_order(tmp_path):
    """_resolve_pack_taxonomies reads each pack's domain.yaml taxonomies and unions
    them in declared-pack order, deduping, ignoring packs without the field."""
    from apd_gauntlet.init_run import _resolve_pack_taxonomies

    domains_dir = tmp_path / "domains"
    (domains_dir / "alpha").mkdir(parents=True)
    (domains_dir / "alpha" / "domain.yaml").write_text(
        "name: alpha\ntaxonomies:\n  - masvs\n  - maswe\n"
    )
    (domains_dir / "beta").mkdir(parents=True)
    (domains_dir / "beta" / "domain.yaml").write_text(
        "name: beta\ntaxonomies:\n  - maswe\n  - cwe\n"
    )
    (domains_dir / "gamma").mkdir(parents=True)
    (domains_dir / "gamma" / "domain.yaml").write_text("name: gamma\n")

    out = _resolve_pack_taxonomies(["alpha", "beta", "gamma"], domains_dir)
    assert out == ["masvs", "maswe", "cwe"]


def test_resolve_pack_taxonomies_missing_pack_dir_returns_empty(tmp_path):
    """A selected pack with no domain.yaml contributes nothing (no crash)."""
    from apd_gauntlet.init_run import _resolve_pack_taxonomies

    out = _resolve_pack_taxonomies(["nope"], tmp_path / "domains")
    assert out == []
```
- [ ] **Step 2: Run test to verify it fails**
Run: `python3 -m pytest tests/test_init_run.py::test_resolve_pack_taxonomies_unions_in_stable_order tests/test_init_run.py::test_resolve_pack_taxonomies_missing_pack_dir_returns_empty -q`
Expected: FAIL with "ImportError: cannot import name '_resolve_pack_taxonomies'"
- [ ] **Step 3: Add the resolver helper**

Add `yaml` to the imports at the top of `tools/apd_gauntlet/init_run.py` (currently lines 1-8 import `pathlib`, `re`, `shutil`, and `__version__`):
```python
"""Scaffold a runs/<run-id>/ directory."""
from __future__ import annotations

import pathlib
import re
import shutil

import yaml

from . import __version__
```

Then add the resolver function just below `_validate_run_id` (before `scaffold_run`):
```python
def _resolve_pack_taxonomies(
    domains: list[str], domains_dir: pathlib.Path
) -> list[str]:
    """Union the ``taxonomies`` declared by each selected pack's ``domain.yaml``,
    in declared-pack/declared-entry order, deduped. Packs with no ``domain.yaml``
    or no ``taxonomies`` field contribute nothing."""
    seen: dict[str, None] = {}
    for name in domains:
        meta_path = domains_dir / name / "domain.yaml"
        if not meta_path.exists():
            continue
        meta = yaml.safe_load(meta_path.read_text(encoding="utf-8")) or {}
        for tax in meta.get("taxonomies", []) or []:
            seen.setdefault(tax, None)
    return list(seen)
```
- [ ] **Step 4: Run test to verify it passes**
Run: `python3 -m pytest tests/test_init_run.py::test_resolve_pack_taxonomies_unions_in_stable_order tests/test_init_run.py::test_resolve_pack_taxonomies_missing_pack_dir_returns_empty -q`
Expected: PASS
- [ ] **Step 5: Commit**
```bash
git add tools/apd_gauntlet/init_run.py tests/test_init_run.py
git commit -m "feat(init-run): add _resolve_pack_taxonomies helper that unions pack-declared taxonomies"
```

### Task 20: Wire pack taxonomies into scaffold_run output

**Files:**
- Modify: `tools/apd_gauntlet/init_run.py:29-66`
- Test: `tests/test_init_run_config.py`

- [ ] **Step 1: Write the failing test**
```python
# Append to tests/test_init_run_config.py

def test_scaffold_mobile_auto_seeds_mas_taxonomies(tmp_path):
    """Scaffolding with domain=mobile-applications and NO --taxonomies must still
    write taxonomies including masvs + maswe (auto-seeded from the pack)."""
    inputs = tmp_path / "in"
    inputs.mkdir()
    (inputs / "tech_plan.md").write_text("# Plan\n")

    run_dir = scaffold_run("run-mob", inputs, ["mobile-applications"], tmp_path / "runs")

    cfg = yaml.safe_load((run_dir / ".apd-run.yaml").read_text())
    assert "masvs" in cfg["taxonomies"]
    assert "maswe" in cfg["taxonomies"]
    errors = list(Draft202012Validator(RUN_CONFIG_SCHEMA).iter_errors(cfg))
    assert errors == [], [e.message for e in errors]


def test_scaffold_non_mobile_pack_seeds_no_taxonomies(tmp_path):
    """A pack without a taxonomies field (pbm) must not gain a taxonomies list."""
    inputs = tmp_path / "in"
    inputs.mkdir()
    (inputs / "tech_plan.md").write_text("# Plan\n")

    run_dir = scaffold_run("run-pbm", inputs, ["pbm"], tmp_path / "runs")

    cfg = yaml.safe_load((run_dir / ".apd-run.yaml").read_text())
    assert "taxonomies" not in cfg


def test_scaffold_operator_taxonomies_merge_with_pack(tmp_path):
    """Operator --taxonomies still merge with the pack-auto-seeded set, deduped,
    operator entries first, then any pack entry not already present."""
    inputs = tmp_path / "in"
    inputs.mkdir()
    (inputs / "tech_plan.md").write_text("# Plan\n")

    run_dir = scaffold_run(
        "run-merge", inputs, ["mobile-applications"], tmp_path / "runs",
        taxonomies=["cwe", "masvs"],
    )

    cfg = yaml.safe_load((run_dir / ".apd-run.yaml").read_text())
    tax = cfg["taxonomies"]
    assert tax[:2] == ["cwe", "masvs"]      # operator order preserved, masvs not duplicated
    assert "maswe" in tax                    # pack entry merged in
    assert tax.count("masvs") == 1           # dedupe held
    errors = list(Draft202012Validator(RUN_CONFIG_SCHEMA).iter_errors(cfg))
    assert errors == [], [e.message for e in errors]
```
- [ ] **Step 2: Run test to verify it fails**
Run: `python3 -m pytest tests/test_init_run_config.py::test_scaffold_mobile_auto_seeds_mas_taxonomies tests/test_init_run_config.py::test_scaffold_non_mobile_pack_seeds_no_taxonomies tests/test_init_run_config.py::test_scaffold_operator_taxonomies_merge_with_pack -q`
Expected: FAIL — `test_scaffold_mobile_auto_seeds_mas_taxonomies` errors with "KeyError: 'taxonomies'" (no auto-seed yet)
- [ ] **Step 3: Merge pack taxonomies into scaffold_run**

`scaffold_run` currently takes its packs as `domains: list[str]` and writes the optional `taxonomies` block only from the operator arg (current lines 34, 48, 58-60). Add an optional `domains_dir` param defaulting to the repo `domains/` dir, resolve pack taxonomies, union with the operator list (operator entries first, then pack entries not already present), and write the merged list:
```python
def scaffold_run(
    run_id: str,
    inputs_src: pathlib.Path,
    domains: list[str],
    root: pathlib.Path,
    taxonomies: list[str] | None = None,
    threat_model: str | None = None,
    methodology_hint: str | None = None,
    domains_dir: pathlib.Path | None = None,
) -> pathlib.Path:
    _validate_run_id(run_id)
    if domains_dir is None:
        domains_dir = pathlib.Path(__file__).resolve().parent.parent.parent / "domains"
    run_dir = root / run_id
    for sub in SUBDIRS:
        (run_dir / sub).mkdir(parents=True, exist_ok=True)
    for item in inputs_src.iterdir():
        target = run_dir / "inputs" / item.name
        if item.is_dir():
            shutil.copytree(item, target, dirs_exist_ok=True)
        else:
            shutil.copy2(item, target)
    # Operator --taxonomies first (order preserved), then pack-declared taxonomies
    # not already present. Dedupe; stable order.
    merged_tax: dict[str, None] = {}
    for t in (taxonomies or []):
        merged_tax.setdefault(t, None)
    for t in _resolve_pack_taxonomies(domains, domains_dir):
        merged_tax.setdefault(t, None)
    effective_taxonomies = list(merged_tax)
    domains_block = "domains:\n" + "".join(f"  - {d}\n" for d in domains)
    config_text = (
        f"run_id: {run_id}\n"
        f"{domains_block}"
        f"framework_version: {__version__}\n"
        f"code_recon: auto\n"
        "# code_recon: enabled  # hard-fail if CBM not reachable\n"
        "# code_recon: disabled # skip code-recon entirely\n"
        "# cbm_project: <project-name>  # optional CBM project pointer override\n"
    )
    if effective_taxonomies:
        taxonomies_block = (
            "taxonomies:\n" + "".join(f"  - {t}\n" for t in effective_taxonomies)
        )
        config_text += taxonomies_block
    if threat_model:
        config_text += f"threat_model: {threat_model}\n"
    if methodology_hint:
        config_text += f"methodology_hint: {methodology_hint}\n"
    (run_dir / ".apd-run.yaml").write_text(config_text, encoding="utf-8")
    return run_dir
```
- [ ] **Step 4: Run test to verify it passes**
Run: `python3 -m pytest tests/test_init_run_config.py tests/test_init_run.py -q`
Expected: PASS (new MAS tests green; existing `test_init_run_without_taxonomies_omits_field` / `test_init_run_empty_taxonomies_omits_field` still pass since pbm contributes none)
- [ ] **Step 5: Commit**
```bash
git add tools/apd_gauntlet/init_run.py tests/test_init_run_config.py
git commit -m "feat(init-run): auto-seed pack-declared taxonomies into .apd-run.yaml, merging operator --taxonomies"
```

### Task 21: Update --taxonomies help text for masvs/maswe

**Files:**
- Modify: `tools/apd_gauntlet/cli.py:186-193`
- Test: `tests/test_cli.py`

- [ ] **Step 1: Write the failing test**
```python
# Append to tests/test_cli.py

def test_init_run_help_lists_mas_taxonomies():
    """The init-run --taxonomies help must advertise masvs + maswe."""
    from apd_gauntlet.cli import main
    from click.testing import CliRunner

    result = CliRunner().invoke(main, ["init-run", "--help"])
    assert result.exit_code == 0, result.output
    assert "masvs" in result.output
    assert "maswe" in result.output
```
- [ ] **Step 2: Run test to verify it fails**
Run: `python3 -m pytest tests/test_cli.py::test_init_run_help_lists_mas_taxonomies -q`
Expected: FAIL with "assert 'masvs' in result.output" (help omits MAS taxonomies)
- [ ] **Step 3: Extend the --taxonomies help string**

`tools/apd_gauntlet/cli.py` currently defines the option (lines 186-193) with help listing only the non-MAS taxonomies:
```python
@click.option(
    "--taxonomies",
    default=None,
    help=(
        "Comma-separated taxonomies "
        "(cwe,mitre_attack,d3fend,owasp_top10,owasp_api_top10,owasp_llm_top10,"
        "mitre_atlas,masvs,maswe). "
        "Selected packs may auto-seed taxonomies (e.g. mobile-applications -> "
        "masvs,maswe); these merge with any supplied here."
    ),
)
```
- [ ] **Step 4: Run test to verify it passes**
Run: `python3 -m pytest tests/test_cli.py::test_init_run_help_lists_mas_taxonomies -q`
Expected: PASS
- [ ] **Step 5: Commit**
```bash
git add tools/apd_gauntlet/cli.py tests/test_cli.py
git commit -m "docs(cli): document masvs/maswe and pack auto-seed in init-run --taxonomies help"
```

### Task 22: Surface merged pack taxonomies in apd-domain SKILL.md frontmatter

**Files:**
- Modify: `tools/apd_gauntlet/build_domain_skill.py:177-178`
- Modify: `tools/apd_gauntlet/build_domain_skill.py:270-282`
- Test: `tests/test_build_domain_skill.py`

- [ ] **Step 1: Write the failing test**
```python
# Append to tests/test_build_domain_skill.py

import yaml as _yaml


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
```
- [ ] **Step 2: Run test to verify it fails**
Run: `python3 -m pytest tests/test_build_domain_skill.py::test_pack_taxonomies_in_full_skill_frontmatter tests/test_build_domain_skill.py::test_no_taxonomies_omits_frontmatter_key -q`
Expected: FAIL with "KeyError: 'taxonomies'" (frontmatter has no taxonomies key)
- [ ] **Step 3: Compute merged taxonomies and emit them in frontmatter**

Add a helper next to `_packs_yaml` (currently line 177-178):
```python
def _packs_yaml(metas: list[tuple[str, dict[str, Any], pathlib.Path]]) -> str:
    return "".join(f"    - name: {n}\n      version: {m['version']}\n" for (n, m, _) in metas)


def _merge_taxonomies(metas: list[tuple[str, dict[str, Any], pathlib.Path]]) -> list[str]:
    """Union the packs' declared ``taxonomies`` in declared-pack/declared-entry order,
    deduped. Empty when no pack declares any."""
    seen: dict[str, None] = {}
    for _, meta, _ in metas:
        for tax in meta.get("taxonomies", []) or []:
            seen.setdefault(tax, None)
    return list(seen)
```

Then in `build_domain_skill`, where the full-skill `frontmatter` is built (currently lines 270-282), compute the merged taxonomies and inject an optional `taxonomies:` line under `metadata:`:
```python
    surfaces = _render_surfaces_section(_merge_surfaces([(n, m) for (n, m, _) in metas]))
    taxonomies = _merge_taxonomies(metas)
    taxonomies_yaml = (
        "  taxonomies:\n" + "".join(f"    - {t}\n" for t in taxonomies)
        if taxonomies
        else ""
    )
    timestamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    frontmatter = (
        "---\n"
        "name: apd-domain\n"
        "description: Active domain pack content — severity rubric, consequential actions,"
        " common patterns. Generated from one or more domain packs at build time;"
        " do not edit by hand.\n"
        "metadata:\n"
        "  packs:\n"
        f"{_packs_yaml(metas)}"
        f"{taxonomies_yaml}"
        f"  framework_version: {framework_version}\n"
        f"  generated: {timestamp}\n"
        "---\n"
    )
```
- [ ] **Step 4: Run test to verify it passes**
Run: `python3 -m pytest tests/test_build_domain_skill.py -q`
Expected: PASS (new taxonomy tests green; existing single/multi-pack/idempotency tests unaffected since they assert substrings, not exact frontmatter)
- [ ] **Step 5: Commit**
```bash
git add tools/apd_gauntlet/build_domain_skill.py tests/test_build_domain_skill.py
git commit -m "feat(build-domain-skill): surface merged pack taxonomies in apd-domain SKILL.md frontmatter"
```
```

---


## Phase 4 — Synthesis rollups (`_masvs_rollup` / `_maswe_rollup`)

### Task 23: Verify masvs-coverage + maswe-coverage schemas exist

> **Reconciliation note:** these schema files are already created in **Task 13** (`masvs-coverage.schema.json`) and **Task 14** (`maswe-coverage.schema.json`). Executing in order, they exist and the test below PASSES — verification checkpoint. If it fails, create them per Tasks 13–14.

**Files:**
- Create: `schemas/masvs-coverage.schema.json`
- Create: `schemas/maswe-coverage.schema.json`
- Test: `tests/test_other_schemas.py`

- [ ] **Step 1: Write the failing test**
```python
# Append to tests/test_other_schemas.py
import json
import pathlib

import jsonschema

_REPO = pathlib.Path(__file__).parent.parent
_SCHEMA_DIR = _REPO / "schemas"


def test_masvs_coverage_schema_is_valid_metaschema_and_accepts_minimal_doc():
    schema = json.loads((_SCHEMA_DIR / "masvs-coverage.schema.json").read_text())
    jsonschema.Draft202012Validator.check_schema(schema)
    doc = {
        "schema_version": 1,
        "generated_by": "synthesizer",
        "controls": [{
            "masvs_id": "MASVS-STORAGE-1",
            "name": "The app securely stores sensitive data.",
            "category": "MASVS-STORAGE",
            "category_title": "Storage",
            "finding_count": 1,
            "finding_ids": ["conf-aabbccdd"],
            "surfaces": ["src/Store.kt:12"],
            "capability_count": 0,
            "capability_ids": [],
            "posture": "gapped",
        }],
    }
    # Validate against the registry so the _defs.schema.json $refs resolve.
    from apd_gauntlet.validate import build_registry
    errs = list(jsonschema.Draft202012Validator(schema, registry=build_registry()).iter_errors(doc))
    assert errs == [], errs


def test_maswe_coverage_schema_is_valid_metaschema_and_accepts_minimal_doc():
    schema = json.loads((_SCHEMA_DIR / "maswe-coverage.schema.json").read_text())
    jsonschema.Draft202012Validator.check_schema(schema)
    doc = {
        "schema_version": 1,
        "generated_by": "synthesizer",
        "entries": [{
            "maswe_id": "MASWE-0001",
            "name": "Insecure data storage",
            "category": "MASVS-STORAGE",
            "status": "new",
            "parent_masvs": ["MASVS-STORAGE-2"],
            "finding_count": 1,
            "finding_ids": ["conf-aabbccdd"],
            "surfaces": ["src/Store.kt:12"],
        }],
    }
    from apd_gauntlet.validate import build_registry
    errs = list(jsonschema.Draft202012Validator(schema, registry=build_registry()).iter_errors(doc))
    assert errs == [], errs
```

- [ ] **Step 2: Run test to verify it fails**
Run: `python -m pytest tests/test_other_schemas.py -k "masvs_coverage_schema or maswe_coverage_schema" -q`
Expected: FAIL with `FileNotFoundError: ... schemas/masvs-coverage.schema.json` (the two new schema files do not exist yet)

- [ ] **Step 3: Create the two single-file schemas**

`schemas/masvs-coverage.schema.json` (mirrors `cwe-coverage.schema.json` shape — no `-doc` wrapper):
```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://github.com/shoveleejoe/apd-gauntlet/schemas/masvs-coverage.schema.json",
  "title": "APD Gauntlet OWASP MASVS Coverage Rollup",
  "type": "object",
  "required": ["schema_version", "generated_by", "controls"],
  "additionalProperties": false,
  "properties": {
    "schema_version": { "type": "integer", "const": 1 },
    "generated_by":   { "type": "string", "enum": ["synthesizer"] },
    "controls": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["masvs_id", "name", "category", "finding_count", "finding_ids", "capability_count", "capability_ids", "posture"],
        "additionalProperties": false,
        "properties": {
          "masvs_id":         { "$ref": "_defs.schema.json#/$defs/masvs_control_id" },
          "name":             { "type": "string", "minLength": 3 },
          "category":         { "$ref": "_defs.schema.json#/$defs/masvs_category_id" },
          "category_title":   { "type": "string" },
          "finding_count":    { "type": "integer", "minimum": 0 },
          "finding_ids":      { "type": "array", "items": { "type": "string" } },
          "surfaces":         { "type": "array", "items": { "type": "string", "minLength": 1 } },
          "capability_count": { "type": "integer", "minimum": 0 },
          "capability_ids":   { "type": "array", "items": { "type": "string" } },
          "posture":          { "type": "string", "enum": ["gapped", "covered", "gapped_and_covered", "silent"] }
        }
      }
    }
  }
}
```

`schemas/maswe-coverage.schema.json` (mirrors `atlas-coverage.schema.json` shape):
```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://github.com/shoveleejoe/apd-gauntlet/schemas/maswe-coverage.schema.json",
  "title": "APD Gauntlet OWASP MASWE Coverage Rollup",
  "type": "object",
  "required": ["schema_version", "generated_by", "entries"],
  "additionalProperties": false,
  "properties": {
    "schema_version": { "type": "integer", "const": 1 },
    "generated_by":   { "type": "string", "enum": ["synthesizer"] },
    "entries": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["maswe_id", "name", "category", "finding_count", "finding_ids"],
        "additionalProperties": false,
        "properties": {
          "maswe_id":      { "$ref": "_defs.schema.json#/$defs/maswe_id" },
          "name":          { "type": "string", "minLength": 3 },
          "category":      { "$ref": "_defs.schema.json#/$defs/masvs_category_id" },
          "status":        { "type": ["string", "null"] },
          "parent_masvs":  { "type": "array", "items": { "$ref": "_defs.schema.json#/$defs/masvs_control_id" } },
          "finding_count": { "type": "integer", "minimum": 0 },
          "finding_ids":   { "type": "array", "items": { "type": "string" } },
          "surfaces":      { "type": "array", "items": { "type": "string", "minLength": 1 } }
        }
      }
    }
  }
}
```

- [ ] **Step 4: Run test to verify it passes**
Run: `python -m pytest tests/test_other_schemas.py -k "masvs_coverage_schema or maswe_coverage_schema" -q`
Expected: PASS

- [ ] **Step 5: Commit**
```bash
git add schemas/masvs-coverage.schema.json schemas/maswe-coverage.schema.json tests/test_other_schemas.py
git commit -m "feat(schemas): add masvs-coverage and maswe-coverage rollup schemas"
```

### Task 24: Verify MASVS/MASWE coverage schemas are registered in validate.py

> **Reconciliation note:** this registration is already done in **Task 15** (`SYNTHESIS_ROLLUPS`). Executing in order, the test below PASSES — verification checkpoint. If it fails, apply Task 15.

**Files:**
- Modify: `tools/apd_gauntlet/validate.py:234-239`
- Test: `tests/test_other_schemas.py`

- [ ] **Step 1: Write the failing test**
```python
# Append to tests/test_other_schemas.py
def test_masvs_maswe_coverage_registered_in_synthesis_rollups():
    from apd_gauntlet.validate import SYNTHESIS_ROLLUPS
    assert SYNTHESIS_ROLLUPS.get("masvs-coverage.yaml") == "masvs-coverage.schema.json"
    assert SYNTHESIS_ROLLUPS.get("maswe-coverage.yaml") == "maswe-coverage.schema.json"
```

- [ ] **Step 2: Run test to verify it fails**
Run: `python -m pytest tests/test_other_schemas.py -k "registered_in_synthesis_rollups" -q`
Expected: FAIL with `AssertionError: assert None == 'masvs-coverage.schema.json'`

- [ ] **Step 3: Add the two entries to SYNTHESIS_ROLLUPS**

Current code (`tools/apd_gauntlet/validate.py:234-239`):
```python
SYNTHESIS_ROLLUPS: dict[str, str] = {
    "cwe-coverage.yaml":           "cwe-coverage.schema.json",
    "owasp-coverage.yaml":         "owasp-coverage.schema.json",
    "d3fend-coverage.yaml":        "d3fend-coverage.schema.json",
    "atlas-coverage.yaml":         "atlas-coverage.schema.json",
    "threat-model-coverage.yaml":  "threat-model-coverage.schema.json",
```
Edit — insert the two MAS entries directly after the `atlas-coverage.yaml` line:
```python
SYNTHESIS_ROLLUPS: dict[str, str] = {
    "cwe-coverage.yaml":           "cwe-coverage.schema.json",
    "owasp-coverage.yaml":         "owasp-coverage.schema.json",
    "d3fend-coverage.yaml":        "d3fend-coverage.schema.json",
    "atlas-coverage.yaml":         "atlas-coverage.schema.json",
    "masvs-coverage.yaml":         "masvs-coverage.schema.json",
    "maswe-coverage.yaml":         "maswe-coverage.schema.json",
    "threat-model-coverage.yaml":  "threat-model-coverage.schema.json",
```

- [ ] **Step 4: Run test to verify it passes**
Run: `python -m pytest tests/test_other_schemas.py -k "registered_in_synthesis_rollups" -q`
Expected: PASS

- [ ] **Step 5: Commit**
```bash
git add tools/apd_gauntlet/validate.py tests/test_other_schemas.py
git commit -m "feat(validate): register masvs/maswe coverage rollups in SYNTHESIS_ROLLUPS"
```

### Task 25: Add masvs and maswe fields to RollupResult dataclass

**Files:**
- Modify: `tools/apd_gauntlet/synthesis/rollup.py:47-56`
- Test: `tests/test_cli_rollup.py`

- [ ] **Step 1: Write the failing test**
```python
# Append to tests/test_cli_rollup.py
def test_rollup_result_has_masvs_and_maswe_fields():
    from apd_gauntlet.synthesis.rollup import RollupResult
    rr = RollupResult()
    assert rr.masvs is None
    assert rr.maswe is None
```

- [ ] **Step 2: Run test to verify it fails**
Run: `python -m pytest tests/test_cli_rollup.py -k "result_has_masvs_and_maswe" -q`
Expected: FAIL with `AttributeError: 'RollupResult' object has no attribute 'masvs'`

- [ ] **Step 3: Add the two fields**

Current dataclass (`tools/apd_gauntlet/synthesis/rollup.py:47-56`):
```python
@dataclass
class RollupResult:
    nist: list[dict[str, Any]] = field(default_factory=list)
    attack: list[dict[str, Any]] = field(default_factory=list)
    matrix: list[dict[str, Any]] = field(default_factory=list)
    cwe: dict[str, Any] | None = None
    owasp: dict[str, Any] | None = None
    d3fend: dict[str, Any] | None = None
    atlas: dict[str, Any] | None = None
    metrics: dict[str, Any] = field(default_factory=dict)
```
Edit — add `masvs` and `maswe` after `atlas`:
```python
@dataclass
class RollupResult:
    nist: list[dict[str, Any]] = field(default_factory=list)
    attack: list[dict[str, Any]] = field(default_factory=list)
    matrix: list[dict[str, Any]] = field(default_factory=list)
    cwe: dict[str, Any] | None = None
    owasp: dict[str, Any] | None = None
    d3fend: dict[str, Any] | None = None
    atlas: dict[str, Any] | None = None
    masvs: dict[str, Any] | None = None
    maswe: dict[str, Any] | None = None
    metrics: dict[str, Any] = field(default_factory=dict)
```

- [ ] **Step 4: Run test to verify it passes**
Run: `python -m pytest tests/test_cli_rollup.py -k "result_has_masvs_and_maswe" -q`
Expected: PASS

- [ ] **Step 5: Commit**
```bash
git add tools/apd_gauntlet/synthesis/rollup.py tests/test_cli_rollup.py
git commit -m "feat(rollup): add masvs/maswe fields to RollupResult"
```

### Task 26: Implement _maswe_rollup (CWE-style exposure over MASWE weaknesses)

**Files:**
- Modify: `tools/apd_gauntlet/synthesis/rollup.py` (add `_maswe_rollup` after `_atlas_rollup` ~369)
- Test: `tests/test_cli_rollup.py`

- [ ] **Step 1: Write the failing test**
```python
# Append to tests/test_cli_rollup.py
def test_maswe_rollup_groups_by_id_with_surfaces_and_first_appearance_order():
    from apd_gauntlet.synthesis.rollup import _maswe_rollup
    findings = [
        {"id": "intg-b2222222", "evidence": [{"artifact": "p.md", "locator": "src/B.kt:9"}],
         "control_mappings": {"maswe": ["MASWE-0002"]}},
        {"id": "conf-a1111111", "evidence": [{"artifact": "p.md", "locator": "src/A.kt:3"}],
         "control_mappings": {"maswe": ["MASWE-0001"]}},
        {"id": "conf-a3333333", "evidence": [{"artifact": "p.md", "locator": "src/A.kt:7"}],
         "control_mappings": {"maswe": ["MASWE-0001"]}},
    ]
    doc = _maswe_rollup(findings)
    assert doc["schema_version"] == 1
    assert doc["generated_by"] == "synthesizer"
    by_id = {e["maswe_id"]: e for e in doc["entries"]}
    # MASWE-0002 cited first → appears before MASWE-0001 (first-appearance order).
    assert [e["maswe_id"] for e in doc["entries"]] == ["MASWE-0002", "MASWE-0001"]
    # MASWE-0001 cited by two findings → one entry, finding_count == 2, sorted ids + surfaces.
    assert by_id["MASWE-0001"]["finding_count"] == 2
    assert by_id["MASWE-0001"]["finding_ids"] == ["conf-a1111111", "conf-a3333333"]
    assert by_id["MASWE-0001"]["surfaces"] == ["src/A.kt:3", "src/A.kt:7"]
    # name/category/status/parent_masvs resolved from the maswe.json catalog.
    assert by_id["MASWE-0001"]["category"] == "MASVS-STORAGE"
    assert by_id["MASWE-0001"]["status"] == "new"
    assert by_id["MASWE-0001"]["parent_masvs"] == ["MASVS-STORAGE-2"]
    assert len(by_id["MASWE-0001"]["name"]) >= 3


def test_maswe_rollup_falls_back_to_id_when_weakness_unknown():
    from apd_gauntlet.synthesis.rollup import _maswe_rollup
    findings = [{"id": "conf-z9999999", "control_mappings": {"maswe": ["MASWE-9999"]}}]
    doc = _maswe_rollup(findings)
    e = doc["entries"][0]
    assert e["maswe_id"] == "MASWE-9999"
    assert e["name"] == "MASWE-9999"
    assert e["category"] is None
    assert e["status"] is None
    assert e["parent_masvs"] == []
```

- [ ] **Step 2: Run test to verify it fails**
Run: `python -m pytest tests/test_cli_rollup.py -k "maswe_rollup" -q`
Expected: FAIL with `ImportError: cannot import name '_maswe_rollup' from 'apd_gauntlet.synthesis.rollup'`

- [ ] **Step 3: Implement `_maswe_rollup`**

Add this function immediately after `_atlas_rollup` (after `tools/apd_gauntlet/synthesis/rollup.py:369`), modeled on `_cwe_rollup`:
```python
def _maswe_rollup(findings: list[dict[str, Any]]) -> dict[str, Any]:
    # Mirrors _cwe_rollup: MASWE is a flat weakness-id list on
    # control_mappings.maswe (MASWE-####). name/category/status/parent_masvs
    # resolve from the bundled OWASP MAS catalog (data/maswe.json, weaknesses
    # map), falling back to the id (name) / None (category, status) / [] on miss.
    # First-appearance order over the deduped finding order, then by id.
    maswe_data = json.loads((_PKG_DATA / "maswe.json").read_text(encoding="utf-8"))
    by_id = maswe_data.get("weaknesses", {})
    order: list[str] = []
    grouped: dict[str, dict[str, Any]] = {}
    for f in findings:
        for wid in cl.extract_ids_from_mapping((f.get("control_mappings") or {}).get("maswe")):
            if wid not in grouped:
                grouped[wid] = {"finding_ids": [], "surfaces": set()}
                order.append(wid)
            if f["id"] not in grouped[wid]["finding_ids"]:
                grouped[wid]["finding_ids"].append(f["id"])
            for ev in f.get("evidence") or []:
                if isinstance(ev, dict) and ev.get("locator"):
                    grouped[wid]["surfaces"].add(str(ev["locator"]))
    entries = []
    for wid in sorted(order, key=lambda w: (order.index(w), w)):
        ref = by_id.get(wid, {})
        entries.append({
            "maswe_id": wid, "name": ref.get("title") or wid,
            "category": ref.get("category"),
            "status": ref.get("status"),
            "parent_masvs": list(ref.get("masvs_v2") or []),
            "finding_count": len(grouped[wid]["finding_ids"]),
            "finding_ids": sorted(grouped[wid]["finding_ids"]),
            "surfaces": sorted(grouped[wid]["surfaces"]),
        })
    return {"schema_version": 1, "generated_by": "synthesizer", "entries": entries}
```

- [ ] **Step 4: Run test to verify it passes**
Run: `python -m pytest tests/test_cli_rollup.py -k "maswe_rollup" -q`
Expected: PASS

- [ ] **Step 5: Commit**
```bash
git add tools/apd_gauntlet/synthesis/rollup.py tests/test_cli_rollup.py
git commit -m "feat(rollup): implement _maswe_rollup MASWE exposure aggregation"
```

### Task 27: Implement _masvs_rollup (NIST-style posture over MASVS controls)

**Files:**
- Modify: `tools/apd_gauntlet/synthesis/rollup.py` (add `_masvs_titles`/`_masvs_catalog` helper + `_masvs_rollup` after `_maswe_rollup`)
- Test: `tests/test_cli_rollup.py`

- [ ] **Step 1: Write the failing test**
```python
# Append to tests/test_cli_rollup.py
def test_masvs_rollup_posture_transitions_and_union():
    from apd_gauntlet.synthesis.rollup import _masvs_rollup
    findings = [
        # gapped: finding only
        {"id": "conf-a1111111", "evidence": [{"artifact": "p.md", "locator": "src/A.kt:3"}],
         "control_mappings": {"masvs": ["MASVS-STORAGE-1"]}},
        # gapped_and_covered: shares MASVS-CRYPTO-1 with a capability below
        {"id": "conf-a2222222", "evidence": [{"artifact": "p.md", "locator": "src/B.kt:5"}],
         "control_mappings": {"masvs": ["MASVS-CRYPTO-1"]}},
    ]
    capabilities = [
        # covered: capability only
        {"id": "auth-cap-c1111111", "control_mappings": {"masvs": ["MASVS-AUTH-1"]}},
        # gapped_and_covered partner for MASVS-CRYPTO-1
        {"id": "crypto-cap-c2222222", "control_mappings": {"masvs": ["MASVS-CRYPTO-1"]}},
    ]
    doc = _masvs_rollup(findings, capabilities)
    assert doc["schema_version"] == 1
    assert doc["generated_by"] == "synthesizer"
    by_id = {c["masvs_id"]: c for c in doc["controls"]}
    assert by_id["MASVS-STORAGE-1"]["posture"] == "gapped"
    assert by_id["MASVS-STORAGE-1"]["finding_ids"] == ["conf-a1111111"]
    assert by_id["MASVS-STORAGE-1"]["surfaces"] == ["src/A.kt:3"]
    assert by_id["MASVS-STORAGE-1"]["capability_count"] == 0
    assert by_id["MASVS-AUTH-1"]["posture"] == "covered"
    assert by_id["MASVS-AUTH-1"]["capability_ids"] == ["auth-cap-c1111111"]
    assert by_id["MASVS-AUTH-1"]["finding_count"] == 0
    assert by_id["MASVS-CRYPTO-1"]["posture"] == "gapped_and_covered"
    assert by_id["MASVS-CRYPTO-1"]["finding_ids"] == ["conf-a2222222"]
    assert by_id["MASVS-CRYPTO-1"]["capability_ids"] == ["crypto-cap-c2222222"]
    # name/category/category_title resolved from masvs.json catalog.
    assert by_id["MASVS-STORAGE-1"]["category"] == "MASVS-STORAGE"
    assert by_id["MASVS-STORAGE-1"]["category_title"] == "Storage"
    assert len(by_id["MASVS-STORAGE-1"]["name"]) >= 3


def test_masvs_rollup_first_appearance_then_id_ordering():
    from apd_gauntlet.synthesis.rollup import _masvs_rollup
    findings = [
        {"id": "conf-b2222222", "control_mappings": {"masvs": ["MASVS-CRYPTO-1"]}},
        {"id": "conf-a1111111", "control_mappings": {"masvs": ["MASVS-STORAGE-1"]}},
    ]
    # Capability cites an id not in any finding → appended after the finding-ordered ids.
    capabilities = [{"id": "net-cap-c1", "control_mappings": {"masvs": ["MASVS-NETWORK-1"]}}]
    doc = _masvs_rollup(findings, capabilities)
    ids = [c["masvs_id"] for c in doc["controls"]]
    # finding first-appearance: CRYPTO-1 then STORAGE-1; cap-only NETWORK-1 last.
    assert ids == ["MASVS-CRYPTO-1", "MASVS-STORAGE-1", "MASVS-NETWORK-1"]
    assert doc["controls"][2]["posture"] == "covered"
```

- [ ] **Step 2: Run test to verify it fails**
Run: `python -m pytest tests/test_cli_rollup.py -k "masvs_rollup" -q`
Expected: FAIL with `ImportError: cannot import name '_masvs_rollup' from 'apd_gauntlet.synthesis.rollup'`

- [ ] **Step 3: Implement `_masvs_rollup` and its catalog/cap-index helpers**

Add these immediately after `_maswe_rollup`. The MASVS cap index mirrors `cl.build_cap_controls_index` (which is NIST-specific) but reads the `masvs` mapping key; it lives in `rollup.py` to keep `coverage_logic` NIST/ATT&CK only:
```python
def _masvs_catalog() -> dict[str, dict[str, Any]]:
    """Return {masvs_id: {title, category, category_title}} from data/masvs.json."""
    raw = json.loads((_PKG_DATA / "masvs.json").read_text(encoding="utf-8"))
    controls = raw.get("controls", {})
    return controls if isinstance(controls, dict) else {}


def _masvs_cap_index(caps: list[dict[str, Any]]) -> dict[str, set[str]]:
    """Return {masvs_id: {cap_id, ...}} for capabilities citing control_mappings.masvs."""
    index: dict[str, set[str]] = {}
    for cap in caps:
        cap_id = cap.get("id", "")
        cm = cap.get("control_mappings") or {}
        for mid in cl.extract_ids_from_mapping(cm.get("masvs")):
            index.setdefault(mid, set()).add(cap_id)
    return index


def _masvs_rollup(
    findings: list[dict[str, Any]],
    caps: list[dict[str, Any]],
) -> dict[str, Any]:
    # Mirrors _nist_rollup: per-control union of finding_ids + capability_ids,
    # posture from coverage_logic.posture(), name/category/category_title from
    # the bundled OWASP MAS catalog (data/masvs.json). First-appearance order
    # over the deduped finding order, with cap-only controls sorted in by id.
    catalog = _masvs_catalog()
    order: list[str] = []
    fmap: dict[str, list[str]] = {}
    surfaces: dict[str, set[str]] = {}
    for f in findings:
        for mid in cl.extract_ids_from_mapping((f.get("control_mappings") or {}).get("masvs")):
            if mid not in fmap:
                fmap[mid] = []
                surfaces[mid] = set()
                order.append(mid)
            if f["id"] not in fmap[mid]:
                fmap[mid].append(f["id"])
            for ev in f.get("evidence") or []:
                if isinstance(ev, dict) and ev.get("locator"):
                    surfaces[mid].add(str(ev["locator"]))
    cap_index = _masvs_cap_index(caps)
    all_ids = set(order) | set(cap_index)
    order_index = {c: i for i, c in enumerate(order)}
    controls: list[dict[str, Any]] = []
    for mid in sorted(all_ids, key=lambda c: (order_index.get(c, 1_000_000), c)):
        fids = sorted(fmap.get(mid, []))
        cids = sorted(cap_index.get(mid, set()))
        ref = catalog.get(mid, {})
        controls.append({
            "masvs_id": mid,
            "name": ref.get("title") or mid,
            "category": ref.get("category"),
            "category_title": ref.get("category_title"),
            "finding_count": len(fids), "finding_ids": fids,
            "surfaces": sorted(surfaces.get(mid, set())),
            "capability_count": len(cids), "capability_ids": cids,
            "posture": cl.posture(has_findings=bool(fids), has_caps=bool(cids)),
        })
    return {"schema_version": 1, "generated_by": "synthesizer", "controls": controls}
```

- [ ] **Step 4: Run test to verify it passes**
Run: `python -m pytest tests/test_cli_rollup.py -k "masvs_rollup" -q`
Expected: PASS

- [ ] **Step 5: Commit**
```bash
git add tools/apd_gauntlet/synthesis/rollup.py tests/test_cli_rollup.py
git commit -m "feat(rollup): implement _masvs_rollup MASVS posture aggregation"
```

### Task 28: Gate masvs/maswe rollups in build_rollups on declared taxonomies

**Files:**
- Modify: `tools/apd_gauntlet/synthesis/rollup.py:282-290`
- Test: `tests/test_cli_rollup.py`

- [ ] **Step 1: Write the failing test**
```python
# Append to tests/test_cli_rollup.py
def test_build_rollups_skips_masvs_maswe_when_not_declared(tmp_path):
    from apd_gauntlet.synthesis.rollup import build_rollups
    findings_yaml = (
        "finding:\n"
        "  - schema_version: 1\n"
        "    id: conf-aabbccdd\n"
        "    apd_goal: confidentiality\n"
        "    disposition: gap\n"
        "    control_mappings:\n"
        "      masvs: [MASVS-STORAGE-1]\n"
        "      maswe: [MASWE-0001]\n"
    )
    run_dir = _build_minimal_run(
        tmp_path, "run_id: t\ndomain: pbm\n", findings_yaml, "capability: []\n"
    )
    result = build_rollups(run_dir)
    assert result.masvs is None
    assert result.maswe is None


def test_build_rollups_emits_masvs_maswe_when_declared(tmp_path):
    from apd_gauntlet.synthesis.rollup import build_rollups
    findings_yaml = (
        "finding:\n"
        "  - schema_version: 1\n"
        "    id: conf-aabbccdd\n"
        "    apd_goal: confidentiality\n"
        "    disposition: gap\n"
        "    control_mappings:\n"
        "      masvs: [MASVS-STORAGE-1]\n"
        "      maswe: [MASWE-0001]\n"
    )
    run_dir = _build_minimal_run(
        tmp_path,
        "run_id: t\ndomain: mobile-applications\ntaxonomies: [masvs, maswe]\n",
        findings_yaml,
        "capability: []\n",
    )
    result = build_rollups(run_dir)
    assert result.masvs is not None
    assert result.maswe is not None
    assert result.masvs["controls"][0]["masvs_id"] == "MASVS-STORAGE-1"
    assert result.maswe["entries"][0]["maswe_id"] == "MASWE-0001"
```

- [ ] **Step 2: Run test to verify it fails**
Run: `python -m pytest tests/test_cli_rollup.py -k "build_rollups_skips_masvs_maswe or build_rollups_emits_masvs_maswe" -q`
Expected: FAIL with `AssertionError` (declared case: `result.masvs is None` because the gating branch does not exist yet)

- [ ] **Step 3: Add the gated branches**

Current gated block (`tools/apd_gauntlet/synthesis/rollup.py:282-290`):
```python
    declared = _declared_taxonomies(run_cfg)
    if "cwe" in declared:
        result.cwe = _cwe_rollup(findings)
    if declared & {"owasp_top10", "owasp_api_top10", "owasp_llm_top10"}:
        result.owasp = _owasp_rollup(findings, declared)
    if "d3fend" in declared:
        result.d3fend = _d3fend_rollup(findings, caps)
    if "mitre_atlas" in declared:
        result.atlas = _atlas_rollup(findings)
```
Edit — append the two MAS branches after the `mitre_atlas` branch:
```python
    declared = _declared_taxonomies(run_cfg)
    if "cwe" in declared:
        result.cwe = _cwe_rollup(findings)
    if declared & {"owasp_top10", "owasp_api_top10", "owasp_llm_top10"}:
        result.owasp = _owasp_rollup(findings, declared)
    if "d3fend" in declared:
        result.d3fend = _d3fend_rollup(findings, caps)
    if "mitre_atlas" in declared:
        result.atlas = _atlas_rollup(findings)
    if "masvs" in declared:
        result.masvs = _masvs_rollup(findings, caps)
    if "maswe" in declared:
        result.maswe = _maswe_rollup(findings)
```

- [ ] **Step 4: Run test to verify it passes**
Run: `python -m pytest tests/test_cli_rollup.py -k "build_rollups_skips_masvs_maswe or build_rollups_emits_masvs_maswe" -q`
Expected: PASS

- [ ] **Step 5: Commit**
```bash
git add tools/apd_gauntlet/synthesis/rollup.py tests/test_cli_rollup.py
git commit -m "feat(rollup): gate masvs/maswe rollups on declared taxonomies"
```

### Task 29: Write masvs-coverage.yaml and maswe-coverage.yaml conditionally in _write

**Files:**
- Modify: `tools/apd_gauntlet/synthesis/rollup.py:500-502`
- Test: `tests/test_cli_rollup.py`

- [ ] **Step 1: Write the failing test**
```python
# Append to tests/test_cli_rollup.py
def test_masvs_maswe_coverage_written_and_schema_valid_only_when_declared(tmp_path):
    findings_yaml = (
        "finding:\n"
        "  - schema_version: 1\n"
        "    id: conf-aabbccdd\n"
        "    apd_goal: confidentiality\n"
        "    disposition: gap\n"
        "    evidence:\n"
        "      - artifact: scan.md\n"
        "        locator: 'src/Store.kt:12'\n"
        "    control_mappings:\n"
        "      masvs: [MASVS-STORAGE-1]\n"
        "      maswe: [MASWE-0001]\n"
    )
    caps_yaml = (
        "capability:\n"
        "  - schema_version: 1\n"
        "    id: auth-cap-c1111111\n"
        "    apd_goal: authenticity\n"
        "    control_mappings:\n"
        "      masvs: [MASVS-AUTH-1]\n"
    )

    # 1) Not declared → both files absent.
    undeclared = _build_minimal_run(
        tmp_path / "u", "run_id: t\ndomain: pbm\n", findings_yaml, caps_yaml
    )
    CliRunner().invoke(main, ["rollup", str(undeclared)])
    assert not (undeclared / "40-synthesis" / "masvs-coverage.yaml").exists()
    assert not (undeclared / "40-synthesis" / "maswe-coverage.yaml").exists()

    # 2) Declared → both present and schema-valid.
    declared = _build_minimal_run(
        tmp_path / "d",
        "run_id: t\ndomain: mobile-applications\ntaxonomies: [masvs, maswe]\n",
        findings_yaml,
        caps_yaml,
    )
    result = CliRunner().invoke(main, ["rollup", str(declared)])
    assert result.exit_code == 0, result.output
    masvs_doc = yaml.safe_load((declared / "40-synthesis" / "masvs-coverage.yaml").read_text())
    assert _validate(masvs_doc, "masvs-coverage.schema.json") == []
    maswe_doc = yaml.safe_load((declared / "40-synthesis" / "maswe-coverage.yaml").read_text())
    assert _validate(maswe_doc, "maswe-coverage.schema.json") == []
    # MASVS-AUTH-1 cap-only → covered; MASVS-STORAGE-1 finding-only → gapped.
    by_id = {c["masvs_id"]: c for c in masvs_doc["controls"]}
    assert by_id["MASVS-AUTH-1"]["posture"] == "covered"
    assert by_id["MASVS-STORAGE-1"]["posture"] == "gapped"
    assert maswe_doc["entries"][0]["maswe_id"] == "MASWE-0001"
```

- [ ] **Step 2: Run test to verify it fails**
Run: `python -m pytest tests/test_cli_rollup.py -k "masvs_maswe_coverage_written" -q`
Expected: FAIL with `FileNotFoundError` / `TypeError` from `yaml.safe_load` reading a missing `masvs-coverage.yaml` (the `_write` conditional does not exist yet)

- [ ] **Step 3: Add the conditional writes**

Current tail of `_write` (`tools/apd_gauntlet/synthesis/rollup.py:500-502`):
```python
    if result.atlas is not None:
        (synth / "atlas-coverage.yaml").write_text(
            yaml.safe_dump(result.atlas, sort_keys=False), encoding="utf-8")
```
Edit — append the two MAS conditional writes after the atlas block:
```python
    if result.atlas is not None:
        (synth / "atlas-coverage.yaml").write_text(
            yaml.safe_dump(result.atlas, sort_keys=False), encoding="utf-8")
    if result.masvs is not None:
        (synth / "masvs-coverage.yaml").write_text(
            yaml.safe_dump(result.masvs, sort_keys=False), encoding="utf-8")
    if result.maswe is not None:
        (synth / "maswe-coverage.yaml").write_text(
            yaml.safe_dump(result.maswe, sort_keys=False), encoding="utf-8")
```

- [ ] **Step 4: Run test to verify it passes**
Run: `python -m pytest tests/test_cli_rollup.py -k "masvs_maswe_coverage_written" -q`
Expected: PASS

- [ ] **Step 5: Commit**
```bash
git add tools/apd_gauntlet/synthesis/rollup.py tests/test_cli_rollup.py
git commit -m "feat(rollup): write masvs/maswe coverage yamls when declared"
```

### Task 30: Verify full rollup + validate suite green after MASVS/MASWE rollups

**Files:**
- Test: `tests/test_cli_rollup.py`
- Test: `tests/test_other_schemas.py`

- [ ] **Step 1: Write the failing test**
```python
# Append to tests/test_cli_rollup.py — guards that an undeclared run never
# regresses the existing non-MAS rollups when masvs/maswe code is present.
def test_existing_rollups_unchanged_when_mas_not_declared(tmp_path):
    dst = _copy_example(tmp_path)
    result = CliRunner().invoke(main, ["rollup", str(dst)])
    assert result.exit_code == 0, result.output
    # MAS files must NOT appear for a non-mobile example run.
    assert not (dst / "40-synthesis" / "masvs-coverage.yaml").exists()
    assert not (dst / "40-synthesis" / "maswe-coverage.yaml").exists()
    # The canonical nist/attack/matrix outputs still validate.
    nist = yaml.safe_load((dst / "40-synthesis" / "nist-coverage.yaml").read_text())
    assert _validate(nist, "nist-coverage-doc.schema.json") == []
```

- [ ] **Step 2: Run test to verify it fails**
Run: `python -m pytest tests/test_cli_rollup.py -k "existing_rollups_unchanged_when_mas_not_declared" -q`
Expected: PASS if the example run does not declare masvs/maswe; FAIL with an `AssertionError` on the MAS-file-absent check if the gating leaks (this is the regression guard). Run before the assertion is trusted — if it fails, the gating branch or `_write` conditional is wrong.

- [ ] **Step 3: Run the whole rollup + schema suite to confirm no regressions**
```bash
python -m pytest tests/test_cli_rollup.py tests/test_other_schemas.py tests/test_synthesis_equivalence.py tests/test_tmeval_first_class.py tests/unit/synthesis/test_rollup_metrics.py -q
```

- [ ] **Step 4: Run test to verify it passes**
Run: `python -m pytest tests/test_cli_rollup.py tests/test_other_schemas.py -q && python -m ruff check tools/apd_gauntlet/synthesis/rollup.py tools/apd_gauntlet/validate.py`
Expected: PASS (all tests green; ruff reports `All checks passed!`)

- [ ] **Step 5: Commit**
```bash
git add tests/test_cli_rollup.py
git commit -m "test(rollup): guard non-MAS runs never emit masvs/maswe coverage"
```

---


## Phase 5 — Report data (loader + transform)

### Task 31: RunArtifacts gains masvs_coverage, maswe_coverage, active_taxonomies fields

**Files:**
- Modify: `tools/apd_gauntlet/report/loader.py:124-137`
- Test: `tests/unit/report/test_loader_mas.py`

- [ ] **Step 1: Write the failing test**
```python
# tests/unit/report/test_loader_mas.py
from __future__ import annotations

from apd_gauntlet.report.loader import RunArtifacts

EMPTY_METRICS = {"schema_version": 1, "findings_total": 0}


def _bare_artifacts(**overrides) -> RunArtifacts:
    base = dict(
        run_id="r", framework_version="1", domain_pack_name="p",
        domain_pack_version="1", subject="s", date="2026-01-01",
        asset_inventory={}, deduped_findings=[], deduped_capabilities=[],
        contradictions=[], contradictions_notes=None,
        severity_disagreements=[], severity_disagreements_notes=None,
        nist_coverage={}, attack_exposure={}, apd_coverage_matrix={},
        attack_paths=None, asset_graph=None, defense_graph=None,
        attack_path_findings=[], report_data=None, metrics=EMPTY_METRICS,
    )
    base.update(overrides)
    return RunArtifacts(**base)


def test_runartifacts_mas_fields_default_empty() -> None:
    art = _bare_artifacts()
    assert art.masvs_coverage is None
    assert art.maswe_coverage is None
    assert art.active_taxonomies == []


def test_runartifacts_mas_fields_accept_values() -> None:
    art = _bare_artifacts(
        masvs_coverage={"controls": []},
        maswe_coverage={"entries": []},
        active_taxonomies=["masvs", "maswe"],
    )
    assert art.masvs_coverage == {"controls": []}
    assert art.maswe_coverage == {"entries": []}
    assert art.active_taxonomies == ["masvs", "maswe"]
```
- [ ] **Step 2: Run test to verify it fails**
Run: `python -m pytest tests/unit/report/test_loader_mas.py -q`
Expected: FAIL with `TypeError: __init__() got an unexpected keyword argument 'masvs_coverage'`
- [ ] **Step 3: Add the three optional fields to the RunArtifacts dataclass**

Insert after the `threat_model_findings` field (currently the last field, ending at line 137):
```python
    threat_model_findings: list[dict[str, Any]] = field(default_factory=list)
    # OWASP MAS (mobile) coverage rollups, loaded from 40-synthesis/ when the
    # synthesizer emitted them (mobile-applications pack runs declaring the
    # masvs / maswe taxonomies). Optional — None on non-mobile runs. Consumed by
    # the transform's masvs_coverage / maswe_coverage scenes and harvested into
    # the taxonomy dict so MASVS/MASWE ids resolve clickable titles + URLs.
    masvs_coverage: dict[str, Any] | None = None
    maswe_coverage: dict[str, Any] | None = None
    # The run-config ``taxonomies`` list, lifted verbatim so the transform can
    # emit data.meta.active_taxonomies (drives which taxonomy chips the report
    # advertises). Empty when the run declared no taxonomies key.
    active_taxonomies: list[str] = field(default_factory=list)
```
- [ ] **Step 4: Run test to verify it passes**
Run: `python -m pytest tests/unit/report/test_loader_mas.py -q`
Expected: PASS
- [ ] **Step 5: Commit**
```bash
git add tools/apd_gauntlet/report/loader.py tests/unit/report/test_loader_mas.py
git commit -m "feat(report): add masvs_coverage/maswe_coverage/active_taxonomies to RunArtifacts"
```

### Task 32: load_run reads MAS coverage YAMLs and active_taxonomies

**Files:**
- Modify: `tools/apd_gauntlet/report/loader.py:574-590` (optional-artifact load + hash block)
- Modify: `tools/apd_gauntlet/report/loader.py:625-628` (RunArtifacts construction)
- Test: `tests/unit/report/test_loader_mas.py`

- [ ] **Step 1: Write the failing test**
```python
# append to tests/unit/report/test_loader_mas.py
import pathlib

import yaml
from apd_gauntlet.report.loader import load_run


def _write(run_dir: pathlib.Path, rel: str, doc: dict) -> None:
    p = run_dir / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(yaml.safe_dump(doc), encoding="utf-8")


def _minimal_run(run_dir: pathlib.Path) -> None:
    _write(run_dir, ".apd-run.yaml", {
        "run_id": "r", "domains": ["mobile-applications"],
        "framework_version": "1.7.0", "taxonomies": ["masvs", "maswe"],
    })
    _write(run_dir, "00-context/asset-inventory.yaml", {"assets": []})
    _write(run_dir, "40-synthesis/deduped-findings.yaml", {"finding": []})
    _write(run_dir, "40-synthesis/deduped-capabilities.yaml", {"capability": []})
    _write(run_dir, "40-synthesis/nist-coverage.yaml", {})
    _write(run_dir, "40-synthesis/attack-exposure.yaml", {})
    _write(run_dir, "40-synthesis/apd-coverage-matrix.yaml", {})
    _write(run_dir, "40-synthesis/metrics.yaml", {"schema_version": 1})


def test_load_run_reads_mas_coverage_and_taxonomies(tmp_path: pathlib.Path) -> None:
    run = tmp_path / "run"
    _minimal_run(run)
    _write(run, "40-synthesis/masvs-coverage.yaml", {
        "schema_version": 1, "generated_by": "synthesizer",
        "controls": [{"masvs_id": "MASVS-STORAGE-1", "finding_count": 2}],
    })
    _write(run, "40-synthesis/maswe-coverage.yaml", {
        "schema_version": 1, "generated_by": "synthesizer",
        "entries": [{"maswe_id": "MASWE-0001", "finding_count": 1}],
    })
    art = load_run(run)
    assert art.masvs_coverage["controls"][0]["masvs_id"] == "MASVS-STORAGE-1"
    assert art.maswe_coverage["entries"][0]["maswe_id"] == "MASWE-0001"
    assert art.active_taxonomies == ["masvs", "maswe"]
    # MAS coverage files participate in the freshness source-hash set.
    assert "masvs-coverage.yaml" in art.source_hashes
    assert "maswe-coverage.yaml" in art.source_hashes


def test_load_run_omits_mas_when_absent(tmp_path: pathlib.Path) -> None:
    run = tmp_path / "run"
    _minimal_run(run)
    # remove the taxonomies key to model a non-mobile run
    cfg = run / ".apd-run.yaml"
    cfg.write_text(yaml.safe_dump({
        "run_id": "r", "domains": ["pbm"], "framework_version": "1.7.0",
    }), encoding="utf-8")
    art = load_run(run)
    assert art.masvs_coverage is None
    assert art.maswe_coverage is None
    assert art.active_taxonomies == []
    assert "masvs-coverage.yaml" not in art.source_hashes
```
- [ ] **Step 2: Run test to verify it fails**
Run: `python -m pytest tests/unit/report/test_loader_mas.py -q -k "reads_mas_coverage or omits_mas"`
Expected: FAIL with `AttributeError: 'RunArtifacts' object has no attribute 'masvs_coverage'` is already satisfied, so the failure is `KeyError` / `AssertionError` — actually `load_run` does not populate the fields, so `art.masvs_coverage` is None even when files exist → AssertionError on `art.masvs_coverage["controls"]` (TypeError: 'NoneType' object is not subscriptable)
- [ ] **Step 3: Load the MAS coverage YAMLs and active_taxonomies in load_run**

After the `tm_coverage = _yaml_optional(synth / "threat-model-coverage.yaml")` line (currently line 575), add:
```python
    # The evaluator's coverage artifact lives under 40-synthesis (the synth dir).
    tm_coverage = _yaml_optional(synth / "threat-model-coverage.yaml")
    # OWASP MAS (mobile) coverage rollups — present only on mobile-applications
    # pack runs that declared the masvs / maswe taxonomies. Tolerant: absent on
    # every non-mobile run, so _yaml_optional returns None and the transform
    # omits the MAS scenes/meta gracefully.
    masvs_coverage = _yaml_optional(synth / "masvs-coverage.yaml")
    maswe_coverage = _yaml_optional(synth / "maswe-coverage.yaml")
```

In the optional-artifact hash block (after the `report-data.yaml` hash, currently line 590), add:
```python
    if report_data is not None:
        source_hashes["report-data.yaml"] = _hash(synth / "report-data.yaml")
    if masvs_coverage is not None:
        source_hashes["masvs-coverage.yaml"] = _hash(synth / "masvs-coverage.yaml")
    if maswe_coverage is not None:
        source_hashes["maswe-coverage.yaml"] = _hash(synth / "maswe-coverage.yaml")
```

In the `RunArtifacts(...)` construction, after `threat_model_findings=tm_findings,` (currently line 628), add:
```python
        threat_model_findings=tm_findings,
        masvs_coverage=masvs_coverage,
        maswe_coverage=maswe_coverage,
        active_taxonomies=_extract_str_list(run_cfg, "taxonomies"),
    )
```
- [ ] **Step 4: Run test to verify it passes**
Run: `python -m pytest tests/unit/report/test_loader_mas.py -q`
Expected: PASS
- [ ] **Step 5: Commit**
```bash
git add tools/apd_gauntlet/report/loader.py tests/unit/report/test_loader_mas.py
git commit -m "feat(report): load masvs/maswe coverage + active_taxonomies in load_run"
```

### Task 33: meta_block emits active_taxonomies

**Files:**
- Modify: `tools/apd_gauntlet/report/transform.py:193-213` (meta_block return dict)
- Test: `tests/unit/report/test_transform_meta.py`

- [ ] **Step 1: Write the failing test**
```python
# append to tests/unit/report/test_transform_meta.py
from apd_gauntlet.report.loader import RunArtifacts

_EMPTY_METRICS = {"schema_version": 1, "findings_total": 0}


def _meta_artifacts(**overrides) -> RunArtifacts:
    base = dict(
        run_id="r", framework_version="1.7.0", domain_pack_name="mobile-applications",
        domain_pack_version="1", subject="s", date="2026-01-01",
        asset_inventory={}, deduped_findings=[], deduped_capabilities=[],
        contradictions=[], contradictions_notes=None,
        severity_disagreements=[], severity_disagreements_notes=None,
        nist_coverage={}, attack_exposure={}, apd_coverage_matrix={},
        attack_paths=None, asset_graph=None, defense_graph=None,
        attack_path_findings=[], report_data=None, metrics=_EMPTY_METRICS,
    )
    base.update(overrides)
    return RunArtifacts(**base)


def test_meta_active_taxonomies_present() -> None:
    art = _meta_artifacts(active_taxonomies=["masvs", "maswe"])
    meta = meta_block(art)
    assert meta["active_taxonomies"] == ["masvs", "maswe"]


def test_meta_active_taxonomies_empty_on_non_mobile_run(example_run: pathlib.Path) -> None:
    # example declares [cwe, mitre_attack, d3fend, owasp_api_top10] — no MAS.
    artifacts = load_run(example_run)
    meta = meta_block(artifacts)
    assert "masvs" not in meta["active_taxonomies"]
    assert "maswe" not in meta["active_taxonomies"]
```
- [ ] **Step 2: Run test to verify it fails**
Run: `python -m pytest tests/unit/report/test_transform_meta.py -q -k active_taxonomies`
Expected: FAIL with `KeyError: 'active_taxonomies'`
- [ ] **Step 3: Add active_taxonomies to the meta_block return dict**

In the `meta_block` return dict, after the `"reference_db_versions"` entry (currently line 212):
```python
        "is_empty_run": is_empty_run,
        "reference_db_versions": _taxonomy.reference_db_versions(),
        # Taxonomies the run declared (run-config ``taxonomies``), lifted by the
        # loader. Drives which taxonomy families the report advertises (e.g.
        # ["masvs", "maswe"] on a mobile run). Empty list on runs that declared
        # none, so non-mobile runs carry no MAS advertisement.
        "active_taxonomies": list(artifacts.active_taxonomies),
    }
```
- [ ] **Step 4: Run test to verify it passes**
Run: `python -m pytest tests/unit/report/test_transform_meta.py -q`
Expected: PASS
- [ ] **Step 5: Commit**
```bash
git add tools/apd_gauntlet/report/transform.py tests/unit/report/test_transform_meta.py
git commit -m "feat(report): emit data.meta.active_taxonomies from run-config taxonomies"
```

### Task 34: findings_array maps masvs + maswe control_mappings

**Files:**
- Modify: `tools/apd_gauntlet/report/transform.py:377-407` (findings_array mappings dict)
- Test: `tests/unit/report/test_transform_findings.py`

- [ ] **Step 1: Write the failing test**
```python
# append to tests/unit/report/test_transform_findings.py
from apd_gauntlet.report.loader import RunArtifacts
from apd_gauntlet.report.transform import findings_array

_FA_METRICS = {"schema_version": 1, "findings_total": 0}


def _fa_artifacts(findings):
    return RunArtifacts(
        run_id="r", framework_version="1", domain_pack_name="p",
        domain_pack_version="1", subject="s", date="2026-01-01",
        asset_inventory={}, deduped_findings=findings, deduped_capabilities=[],
        contradictions=[], contradictions_notes=None,
        severity_disagreements=[], severity_disagreements_notes=None,
        nist_coverage={}, attack_exposure={}, apd_coverage_matrix={},
        attack_paths=None, asset_graph=None, defense_graph=None,
        attack_path_findings=[], report_data=None, metrics=_FA_METRICS,
    )


def test_findings_array_includes_masvs_and_maswe() -> None:
    art = _fa_artifacts([
        {
            "id": "rslv-00000001",
            "control_mappings": {
                "masvs": ["MASVS-STORAGE-1", "MASVS-CRYPTO-2"],
                "maswe": ["MASWE-0001"],
            },
            "evidence": [{"artifact": "src/Store.kt", "locator": "L42"}],
        }
    ])
    rows = findings_array(art, headline_supplement=None)
    mappings = rows[0]["mappings"]
    assert mappings["masvs"] == ["MASVS-STORAGE-1", "MASVS-CRYPTO-2"]
    assert mappings["maswe"] == ["MASWE-0001"]


def test_findings_array_masvs_maswe_empty_when_absent() -> None:
    art = _fa_artifacts([
        {"id": "conf-00000001", "control_mappings": {"cwe": ["CWE-79"]},
         "evidence": [{"artifact": "x", "locator": "y"}]}
    ])
    rows = findings_array(art, headline_supplement=None)
    assert rows[0]["mappings"]["masvs"] == []
    assert rows[0]["mappings"]["maswe"] == []
```
- [ ] **Step 2: Run test to verify it fails**
Run: `python -m pytest tests/unit/report/test_transform_findings.py -q -k "masvs or maswe"`
Expected: FAIL with `KeyError: 'masvs'`
- [ ] **Step 3: Add masvs + maswe to the findings_array mappings dict**

In the `"mappings"` dict, after the `"atlas"` entry (currently lines 403-406):
```python
                "atlas":     _extract_ids_from_mapping(
                    (f.get("control_mappings") or {}).get("atlas"),
                    warnings=warnings,
                ),
                "masvs":     _extract_ids_from_mapping(
                    (f.get("control_mappings") or {}).get("masvs"),
                    warnings=warnings,
                ),
                "maswe":     _extract_ids_from_mapping(
                    (f.get("control_mappings") or {}).get("maswe"),
                    warnings=warnings,
                ),
            },
```
- [ ] **Step 4: Run test to verify it passes**
Run: `python -m pytest tests/unit/report/test_transform_findings.py -q`
Expected: PASS
- [ ] **Step 5: Commit**
```bash
git add tools/apd_gauntlet/report/transform.py tests/unit/report/test_transform_findings.py
git commit -m "feat(report): map masvs/maswe control_mappings into findings_array"
```

### Task 35: _MASVS / _MASWE family display constants

**Files:**
- Modify: `tools/apd_gauntlet/report/transform.py:1916-1920` (family display consts)
- Test: `tests/unit/report/test_transform_taxonomy.py`

- [ ] **Step 1: Write the failing test**
```python
# append to tests/unit/report/test_transform_taxonomy.py
from apd_gauntlet.report import transform as _t


def test_mas_family_display_constants() -> None:
    assert _t._MASVS_FAMILY_DISPLAY == "OWASP MASVS"
    assert _t._MASWE_FAMILY_DISPLAY == "OWASP MASWE"
```
- [ ] **Step 2: Run test to verify it fails**
Run: `python -m pytest tests/unit/report/test_transform_taxonomy.py -q -k mas_family_display`
Expected: FAIL with `AttributeError: module 'apd_gauntlet.report.transform' has no attribute '_MASVS_FAMILY_DISPLAY'`
- [ ] **Step 3: Add the MAS family display constants**

After `_ATLAS_FAMILY_DISPLAY = "MITRE ATLAS"` (currently line 1920):
```python
_ATLAS_FAMILY_DISPLAY = "MITRE ATLAS"
_MASVS_FAMILY_DISPLAY = "OWASP MASVS"
_MASWE_FAMILY_DISPLAY = "OWASP MASWE"
```
- [ ] **Step 4: Run test to verify it passes**
Run: `python -m pytest tests/unit/report/test_transform_taxonomy.py -q -k mas_family_display`
Expected: PASS
- [ ] **Step 5: Commit**
```bash
git add tools/apd_gauntlet/report/transform.py tests/unit/report/test_transform_taxonomy.py
git commit -m "feat(report): add _MASVS/_MASWE family display constants"
```

### Task 36: _collect_referenced_ids harvests masvs + maswe from findings, capabilities, and coverage rollups

**Files:**
- Modify: `tools/apd_gauntlet/report/transform.py:2003-2005` (out dict init)
- Modify: `tools/apd_gauntlet/report/transform.py:2006-2042` (finding + capability harvest)
- Modify: `tools/apd_gauntlet/report/transform.py:2114-2117` (coverage-rollup harvest + return)
- Test: `tests/unit/report/test_transform_taxonomy.py`

- [ ] **Step 1: Write the failing test**
```python
# append to tests/unit/report/test_transform_taxonomy.py
from apd_gauntlet.report.transform import _collect_referenced_ids


def _mas_artifacts(**overrides) -> RunArtifacts:
    base = dict(
        run_id="r", framework_version="1", domain_pack_name="p",
        domain_pack_version="1", subject="s", date="2026-01-01",
        asset_inventory={}, deduped_findings=[], deduped_capabilities=[],
        contradictions=[], contradictions_notes=None,
        severity_disagreements=[], severity_disagreements_notes=None,
        nist_coverage={}, attack_exposure={}, apd_coverage_matrix={},
        attack_paths=None, asset_graph=None, defense_graph=None,
        attack_path_findings=[], report_data=None, metrics=EMPTY_METRICS,
    )
    base.update(overrides)
    return RunArtifacts(**base)


def test_collect_referenced_harvests_mas_from_findings_and_caps() -> None:
    art = _mas_artifacts(
        deduped_findings=[{
            "id": "rslv-00000001",
            "control_mappings": {"masvs": ["MASVS-STORAGE-1"], "maswe": ["MASWE-0001"]},
        }],
        deduped_capabilities=[{
            "id": "cap-1",
            "control_mappings": {"masvs": ["MASVS-CRYPTO-2"]},
        }],
    )
    refs = _collect_referenced_ids(art)
    assert "MASVS-STORAGE-1" in refs["masvs"]
    assert "MASVS-CRYPTO-2" in refs["masvs"]
    assert "MASWE-0001" in refs["maswe"]


def test_collect_referenced_harvests_mas_from_coverage_rollups() -> None:
    art = _mas_artifacts(
        masvs_coverage={"controls": [
            {"masvs_id": "MASVS-NETWORK-1", "finding_count": 1},
            {"masvs_id": "MASVS-AUTH-2", "finding_count": 0},
        ]},
        maswe_coverage={"entries": [
            {"maswe_id": "MASWE-0002", "finding_count": 1},
        ]},
    )
    refs = _collect_referenced_ids(art)
    assert {"MASVS-NETWORK-1", "MASVS-AUTH-2"} <= refs["masvs"]
    assert "MASWE-0002" in refs["maswe"]
```
- [ ] **Step 2: Run test to verify it fails**
Run: `python -m pytest tests/unit/report/test_transform_taxonomy.py -q -k "harvests_mas"`
Expected: FAIL with `KeyError: 'masvs'`
- [ ] **Step 3: Harvest masvs/maswe in _collect_referenced_ids**

Add `masvs`/`maswe` to the out-dict init (currently lines 2003-2005):
```python
    out: dict[str, set[str]] = {
        "nist": set(), "attack": set(), "cwe": set(), "d3fend": set(), "atlas": set(),
        "masvs": set(), "maswe": set(),
    }
```

In the finding loop, after the `out["atlas"].update(...)` block (currently lines 2024-2026):
```python
        out["atlas"].update(_extract_ids_from_mapping(
            cm.get("atlas"), warnings=warnings,
        ))
        # MASVS lives on both findings and capabilities; MASWE is findings-only.
        out["masvs"].update(_extract_ids_from_mapping(
            cm.get("masvs"), warnings=warnings,
        ))
        out["maswe"].update(_extract_ids_from_mapping(
            cm.get("maswe"), warnings=warnings,
        ))
```

In the capability loop, after the `out["d3fend"].update(...)` block (currently lines 2040-2042):
```python
        out["d3fend"].update(_extract_ids_from_mapping(
            cm.get("d3fend"), warnings=warnings,
        ))
        # MASVS is the only MAS taxonomy carried on capabilities (MASWE is
        # findings-only per the control_mappings contract).
        out["masvs"].update(_extract_ids_from_mapping(
            cm.get("masvs"), warnings=warnings,
        ))
```

Just before the final `return out` (currently lines 2114-2117), after the defense-graph overlay loop ends, add the coverage-rollup harvest:
```python
        for t in (o.get("exposed_attack_techniques") or []):
            if isinstance(t, str) and t:
                out["attack"].add(t)
    # MAS coverage rollups (40-synthesis/masvs-coverage.yaml + maswe-coverage.yaml).
    # The synthesizer rolls up every cited control/weakness here, so harvesting
    # the rollup ids guarantees a taxonomy entry even for ids the per-finding
    # mappings express in a shape the extractor did not recover.
    for c in ((artifacts.masvs_coverage or {}).get("controls") or []):
        if isinstance(c, dict):
            mid = c.get("masvs_id")
            if isinstance(mid, str) and mid:
                out["masvs"].add(mid)
    for e in ((artifacts.maswe_coverage or {}).get("entries") or []):
        if isinstance(e, dict):
            wid = e.get("maswe_id")
            if isinstance(wid, str) and wid:
                out["maswe"].add(wid)
    return out
```
- [ ] **Step 4: Run test to verify it passes**
Run: `python -m pytest tests/unit/report/test_transform_taxonomy.py -q -k "harvests_mas"`
Expected: PASS
- [ ] **Step 5: Commit**
```bash
git add tools/apd_gauntlet/report/transform.py tests/unit/report/test_transform_taxonomy.py
git commit -m "feat(report): harvest masvs/maswe ids from findings, caps, and coverage rollups"
```

### Task 37: taxonomy_dict adds masvs + maswe clickable branches

**Files:**
- Modify: `tools/apd_gauntlet/report/transform.py:2177-2184` (taxonomy_dict ATLAS branch + return)
- Test: `tests/unit/report/test_transform_taxonomy.py`

- [ ] **Step 1: Write the failing test**
```python
# append to tests/unit/report/test_transform_taxonomy.py
def test_taxonomy_resolves_masvs_control_with_title_and_url() -> None:
    art = _mas_artifacts(
        deduped_findings=[{
            "id": "rslv-00000001",
            "control_mappings": {"masvs": ["MASVS-STORAGE-1"]},
        }],
    )
    tax = taxonomy_dict(art)
    assert tax["MASVS-STORAGE-1"]["family"] == "OWASP MASVS"
    assert tax["MASVS-STORAGE-1"]["title"]  # resolved statement, not bare id
    # masvs_url is pure-regex; always present for a well-formed control id.
    assert tax["MASVS-STORAGE-1"]["url"] == (
        "https://mas.owasp.org/MASVS/controls/MASVS-STORAGE-1/"
    )


def test_taxonomy_resolves_maswe_weakness_with_family_and_title() -> None:
    art = _mas_artifacts(
        deduped_findings=[{
            "id": "rslv-00000002",
            "control_mappings": {"maswe": ["MASWE-0001"]},
        }],
    )
    tax = taxonomy_dict(art)
    assert tax["MASWE-0001"]["family"] == "OWASP MASWE"
    assert tax["MASWE-0001"]["title"]
    # maswe_url returns a string for a known filing category; the branch sets
    # "url" only when non-None, so assert the family + title even if url omitted.
    if "url" in tax["MASWE-0001"]:
        assert tax["MASWE-0001"]["url"].startswith("https://mas.owasp.org/MASWE/")
```
- [ ] **Step 2: Run test to verify it fails**
Run: `python -m pytest tests/unit/report/test_transform_taxonomy.py -q -k "resolves_masvs or resolves_maswe"`
Expected: FAIL with `KeyError: 'MASVS-STORAGE-1'`
- [ ] **Step 3: Add masvs + maswe branches to taxonomy_dict**

After the MITRE ATLAS branch, before `return out` (currently lines 2177-2184):
```python
    # MITRE ATLAS: titles from taxonomy module; fall back to id if absent.
    atlas = _taxonomy.atlas_titles()
    for aid in sorted(refs["atlas"]):
        if not aid:
            continue
        out[aid] = {"family": _ATLAS_FAMILY_DISPLAY, "title": atlas.get(aid, aid)}

    # OWASP MASVS controls: titles (the verification statement) from the bundled
    # masvs.json catalog; URL is pure-regex (mas.owasp.org/MASVS/controls/<id>/),
    # so every well-formed control id is clickable.
    masvs = _taxonomy.masvs_titles()
    for mid in sorted(refs["masvs"]):
        if not mid:
            continue
        out[mid] = {"family": _MASVS_FAMILY_DISPLAY, "title": masvs.get(mid, mid)}
        _url = _taxonomy.masvs_url(mid)
        if _url:
            out[mid]["url"] = _url

    # OWASP MASWE weaknesses: titles from the bundled maswe.json catalog; URL is
    # derived from the weakness's filing category (mas.owasp.org/MASWE/<cat>/<id>/)
    # and may be None when the category is unknown — left unlinked in that case.
    maswe = _taxonomy.maswe_titles()
    for wid in sorted(refs["maswe"]):
        if not wid:
            continue
        out[wid] = {"family": _MASWE_FAMILY_DISPLAY, "title": maswe.get(wid, wid)}
        _url = _taxonomy.maswe_url(wid)
        if _url:
            out[wid]["url"] = _url

    return out
```
- [ ] **Step 4: Run test to verify it passes**
Run: `python -m pytest tests/unit/report/test_transform_taxonomy.py -q -k "resolves_masvs or resolves_maswe"`
Expected: PASS
- [ ] **Step 5: Commit**
```bash
git add tools/apd_gauntlet/report/transform.py tests/unit/report/test_transform_taxonomy.py
git commit -m "feat(report): resolve masvs/maswe taxonomy entries with title + clickable URL"
```

### Task 38: masvs_coverage_rows scene builder

**Files:**
- Modify: `tools/apd_gauntlet/report/transform.py` (add masvs_coverage_rows near attack_exposure_rows, ~line 697)
- Test: `tests/unit/report/test_transform_mas_coverage.py`

- [ ] **Step 1: Write the failing test**
```python
# tests/unit/report/test_transform_mas_coverage.py
from __future__ import annotations

from apd_gauntlet.report.loader import RunArtifacts
from apd_gauntlet.report.transform import masvs_coverage_rows

EMPTY_METRICS = {"schema_version": 1, "findings_total": 0}


def _artifacts(**overrides) -> RunArtifacts:
    base = dict(
        run_id="r", framework_version="1", domain_pack_name="mobile-applications",
        domain_pack_version="1", subject="s", date="2026-01-01",
        asset_inventory={}, deduped_findings=[], deduped_capabilities=[],
        contradictions=[], contradictions_notes=None,
        severity_disagreements=[], severity_disagreements_notes=None,
        nist_coverage={}, attack_exposure={}, apd_coverage_matrix={},
        attack_paths=None, asset_graph=None, defense_graph=None,
        attack_path_findings=[], report_data=None, metrics=EMPTY_METRICS,
    )
    base.update(overrides)
    return RunArtifacts(**base)


def test_masvs_coverage_rows_from_rollup() -> None:
    art = _artifacts(masvs_coverage={
        "schema_version": 1, "generated_by": "synthesizer",
        "controls": [
            {"masvs_id": "MASVS-STORAGE-1", "name": "Store secrets securely",
             "category": "MASVS-STORAGE", "category_title": "Storage",
             "finding_count": 2, "finding_ids": ["rslv-1", "rslv-2"],
             "surfaces": ["local-db"], "capability_count": 0,
             "capability_ids": [], "posture": "gapped"},
            {"masvs_id": "MASVS-CRYPTO-2", "name": "Use strong crypto",
             "category": "MASVS-CRYPTO", "category_title": "Cryptography",
             "finding_count": 0, "finding_ids": [], "surfaces": [],
             "capability_count": 1, "capability_ids": ["cap-1"],
             "posture": "covered"},
        ],
    })
    rows = masvs_coverage_rows(art)
    assert len(rows) == 2
    by_id = {r["masvs_id"]: r for r in rows}
    assert by_id["MASVS-STORAGE-1"]["finding_count"] == 2
    assert by_id["MASVS-STORAGE-1"]["posture"] == "gapped"
    assert by_id["MASVS-STORAGE-1"]["category_title"] == "Storage"
    assert by_id["MASVS-CRYPTO-2"]["capability_count"] == 1


def test_masvs_coverage_rows_empty_when_absent() -> None:
    art = _artifacts(masvs_coverage=None)
    assert masvs_coverage_rows(art) == []
```
- [ ] **Step 2: Run test to verify it fails**
Run: `python -m pytest tests/unit/report/test_transform_mas_coverage.py -q -k masvs`
Expected: FAIL with `ImportError: cannot import name 'masvs_coverage_rows'`
- [ ] **Step 3: Add masvs_coverage_rows after attack_exposure helpers**

Immediately before `def attack_exposure_rows(` (currently line 709) — or after the `nist_rollup_rows` block ending at line 697 — add:
```python
def masvs_coverage_rows(artifacts: RunArtifacts) -> list[dict[str, Any]]:
    """Return rows for the MASVS coverage table — one per cited OWASP MASVS
    control, straight off ``40-synthesis/masvs-coverage.yaml``.

    The synthesizer's ``_masvs_rollup`` already computes per-control counts,
    surfaces, and posture (via coverage_logic.posture()), so this is a tolerant
    passthrough: each ``controls[]`` entry maps to a row. Returns ``[]`` when the
    rollup is absent (non-mobile run) so the Coverage tab omits the MASVS scene
    gracefully.
    """
    controls = (artifacts.masvs_coverage or {}).get("controls") or []
    rows: list[dict[str, Any]] = []
    for c in controls:
        if not isinstance(c, dict):
            continue
        rows.append({
            "masvs_id":         c.get("masvs_id", ""),
            "name":             c.get("name", ""),
            "category":         c.get("category", ""),
            "category_title":   c.get("category_title", ""),
            "finding_count":    c.get("finding_count", 0),
            "finding_ids":      list(c.get("finding_ids") or []),
            "surfaces":         list(c.get("surfaces") or []),
            "capability_count": c.get("capability_count", 0),
            "capability_ids":   list(c.get("capability_ids") or []),
            "posture":          c.get("posture", "silent"),
        })
    # Order: most-cited controls first (finding+capability volume desc), then id.
    rows.sort(key=lambda r: (-(r["finding_count"] + r["capability_count"]), r["masvs_id"]))
    return rows


```
- [ ] **Step 4: Run test to verify it passes**
Run: `python -m pytest tests/unit/report/test_transform_mas_coverage.py -q -k masvs`
Expected: PASS
- [ ] **Step 5: Commit**
```bash
git add tools/apd_gauntlet/report/transform.py tests/unit/report/test_transform_mas_coverage.py
git commit -m "feat(report): add masvs_coverage_rows scene builder"
```

### Task 39: maswe_coverage_rows scene builder

**Files:**
- Modify: `tools/apd_gauntlet/report/transform.py` (add maswe_coverage_rows after masvs_coverage_rows)
- Test: `tests/unit/report/test_transform_mas_coverage.py`

- [ ] **Step 1: Write the failing test**
```python
# append to tests/unit/report/test_transform_mas_coverage.py
from apd_gauntlet.report.transform import maswe_coverage_rows


def test_maswe_coverage_rows_from_rollup() -> None:
    art = _artifacts(maswe_coverage={
        "schema_version": 1, "generated_by": "synthesizer",
        "entries": [
            {"maswe_id": "MASWE-0001", "name": "Insecure data storage",
             "category": "MASVS-STORAGE", "status": "new",
             "parent_masvs": ["MASVS-STORAGE-2"], "finding_count": 3,
             "finding_ids": ["rslv-1", "rslv-2", "rslv-3"],
             "surfaces": ["local-db"]},
            {"maswe_id": "MASWE-0002", "name": "Weak crypto",
             "category": "MASVS-CRYPTO", "status": "draft",
             "parent_masvs": [], "finding_count": 1,
             "finding_ids": ["rslv-4"], "surfaces": []},
        ],
    })
    rows = maswe_coverage_rows(art)
    assert len(rows) == 2
    by_id = {r["maswe_id"]: r for r in rows}
    assert by_id["MASWE-0001"]["finding_count"] == 3
    assert by_id["MASWE-0001"]["status"] == "new"
    assert by_id["MASWE-0001"]["parent_masvs"] == ["MASVS-STORAGE-2"]
    assert by_id["MASWE-0002"]["category"] == "MASVS-CRYPTO"
    # ordered most-cited-first
    assert rows[0]["maswe_id"] == "MASWE-0001"


def test_maswe_coverage_rows_empty_when_absent() -> None:
    art = _artifacts(maswe_coverage=None)
    assert maswe_coverage_rows(art) == []
```
- [ ] **Step 2: Run test to verify it fails**
Run: `python -m pytest tests/unit/report/test_transform_mas_coverage.py -q -k maswe`
Expected: FAIL with `ImportError: cannot import name 'maswe_coverage_rows'`
- [ ] **Step 3: Add maswe_coverage_rows after masvs_coverage_rows**

Immediately after the `masvs_coverage_rows` function added in the previous task:
```python
def maswe_coverage_rows(artifacts: RunArtifacts) -> list[dict[str, Any]]:
    """Return rows for the MASWE coverage table — one per cited OWASP MASWE
    weakness, straight off ``40-synthesis/maswe-coverage.yaml``.

    MASWE is findings-only (no capability cross-walk), so the synthesizer's
    ``_maswe_rollup`` carries per-weakness finding counts, the filing category,
    the catalog status, parent MASVS controls, and the touched surfaces. Tolerant
    passthrough; returns ``[]`` on a non-mobile run so the Coverage tab omits the
    MASWE scene gracefully.
    """
    entries = (artifacts.maswe_coverage or {}).get("entries") or []
    rows: list[dict[str, Any]] = []
    for e in entries:
        if not isinstance(e, dict):
            continue
        rows.append({
            "maswe_id":      e.get("maswe_id", ""),
            "name":          e.get("name", ""),
            "category":      e.get("category", ""),
            "status":        e.get("status", ""),
            "parent_masvs":  list(e.get("parent_masvs") or []),
            "finding_count": e.get("finding_count", 0),
            "finding_ids":   list(e.get("finding_ids") or []),
            "surfaces":      list(e.get("surfaces") or []),
        })
    rows.sort(key=lambda r: (-r["finding_count"], r["maswe_id"]))
    return rows


```
- [ ] **Step 4: Run test to verify it passes**
Run: `python -m pytest tests/unit/report/test_transform_mas_coverage.py -q -k maswe`
Expected: PASS
- [ ] **Step 5: Commit**
```bash
git add tools/apd_gauntlet/report/transform.py tests/unit/report/test_transform_mas_coverage.py
git commit -m "feat(report): add maswe_coverage_rows scene builder"
```

### Task 40: register masvs_coverage + maswe_coverage scenes in the sections list

**Files:**
- Modify: `tools/apd_gauntlet/report/transform.py:1836-1838` (sections list, after attack_exposure)
- Test: `tests/unit/report/test_transform_mas_coverage.py`

- [ ] **Step 1: Write the failing test**
```python
# append to tests/unit/report/test_transform_mas_coverage.py
import pathlib

from apd_gauntlet.report.loader import load_run
from apd_gauntlet.report.transform import build_apd_data


def test_build_apd_data_includes_mas_coverage_scenes() -> None:
    art = _artifacts(
        masvs_coverage={"controls": [
            {"masvs_id": "MASVS-STORAGE-1", "finding_count": 1, "posture": "gapped"},
        ]},
        maswe_coverage={"entries": [
            {"maswe_id": "MASWE-0001", "finding_count": 1, "status": "new"},
        ]},
    )
    data = build_apd_data(art)
    assert data["masvs_coverage"][0]["masvs_id"] == "MASVS-STORAGE-1"
    assert data["maswe_coverage"][0]["maswe_id"] == "MASWE-0001"


def test_build_apd_data_mas_scenes_empty_on_non_mobile(example_run: pathlib.Path) -> None:
    # the example run ships no MAS coverage rollups
    art = load_run(example_run)
    data = build_apd_data(art)
    assert data["masvs_coverage"] == []
    assert data["maswe_coverage"] == []
```
- [ ] **Step 2: Run test to verify it fails**
Run: `python -m pytest tests/unit/report/test_transform_mas_coverage.py -q -k build_apd_data`
Expected: FAIL with `KeyError: 'masvs_coverage'`
- [ ] **Step 3: Register the two scenes after attack_exposure in the sections list**

In the `sections` list, after the `attack_exposure` tuple (currently lines 1836-1838):
```python
        ("attack_exposure",
         lambda: attack_exposure_rows(artifacts),
         []),
        ("masvs_coverage",
         lambda: masvs_coverage_rows(artifacts),
         []),
        ("maswe_coverage",
         lambda: maswe_coverage_rows(artifacts),
         []),
```
- [ ] **Step 4: Run test to verify it passes**
Run: `python -m pytest tests/unit/report/test_transform_mas_coverage.py -q && python -m pytest tests/unit/report -q`
Expected: PASS (both the new MAS suite and the full report unit suite stay green)
- [ ] **Step 5: Commit**
```bash
git add tools/apd_gauntlet/report/transform.py tests/unit/report/test_transform_mas_coverage.py
git commit -m "feat(report): register masvs_coverage/maswe_coverage scenes in build_apd_data"
```
```

---


## Phase 6 — Report template (JSX) + bundle rebuild

### Task 41: Findings.jsx — add MASVS + MASWE mapping-group blocks and extend the Control-mappings guard

**Files:**
- Modify: `report-template/screens/Findings.jsx:299-321`
- Test: `python tools/check_report_template_freshness.py`

- [ ] **Step 1: Write the failing test (freshness gate sees the JSX edit, bundle stale)**
This is a JSX edit; there is no unit-test harness. The project gate is the freshness check, which must go RED after the JSX change and before the bundle rebuild. Run it first to capture the current (green) baseline so the later red is meaningful:
```bash
python tools/check_report_template_freshness.py
```
Expected before any edit: `check_report_template_freshness: OK (<hash>)`

- [ ] **Step 2: Make the edit, then re-run to verify it fails**
Run: `python tools/check_report_template_freshness.py`
Expected after the Step-3 edit: exit 1 with
`check_report_template_freshness: report-template/ has changed since the precompiled bundle was generated.` followed by `expected=… actual=…`

- [ ] **Step 3: Extend the outer guard + add the two mapping-group blocks**
The current outer guard (line 299) and ATLAS block (lines 317-319) read:
```jsx
        {(f.mappings?.nist?.length || f.mappings?.attack?.length || f.mappings?.cwe?.length || f.mappings?.owasp_api?.length || f.mappings?.owasp?.length || f.mappings?.atlas?.length) > 0 && (
          <section className="finding-detail__block">
            <div className="finding-detail__block-head"><span>Control mappings</span></div>
```
Extend the guard to include `masvs` and `maswe`:
```jsx
        {(f.mappings?.nist?.length || f.mappings?.attack?.length || f.mappings?.cwe?.length || f.mappings?.owasp_api?.length || f.mappings?.owasp?.length || f.mappings?.atlas?.length || f.mappings?.masvs?.length || f.mappings?.maswe?.length) > 0 && (
          <section className="finding-detail__block">
            <div className="finding-detail__block-head"><span>Control mappings</span></div>
```
Then add the two new `<dl className="mapping-group">` blocks immediately after the existing ATLAS block. The current ATLAS block is the last one before the closing `</section>`:
```jsx
            {f.mappings?.atlas?.length > 0 && (
              <dl className="mapping-group"><dt>MITRE ATLAS</dt><dd><TagRow ids={f.mappings.atlas} /></dd></dl>
            )}
          </section>
```
Becomes (insert the MASVS + MASWE blocks between the ATLAS `)}` and the `</section>`):
```jsx
            {f.mappings?.atlas?.length > 0 && (
              <dl className="mapping-group"><dt>MITRE ATLAS</dt><dd><TagRow ids={f.mappings.atlas} /></dd></dl>
            )}
            {f.mappings?.masvs?.length > 0 && (
              <dl className="mapping-group"><dt>OWASP MASVS</dt><dd><TagRow ids={f.mappings.masvs} /></dd></dl>
            )}
            {f.mappings?.maswe?.length > 0 && (
              <dl className="mapping-group"><dt>OWASP MASWE</dt><dd><TagRow ids={f.mappings.maswe} /></dd></dl>
            )}
          </section>
```
No change to `components.jsx`: `TagRow`/`TaxonomyTag` already render any `id` and become a link when the corresponding `data.taxonomy[id].url` is present (the report-data section populates MASVS/MASWE entries with `url` via `masvs_url`/`maswe_url`). The clickability is therefore data-driven and needs no JSX change here.

- [ ] **Step 4: (Deferred) bundle rebuild runs in the dedicated rebuild task**
Do NOT rebuild here. The freshness check stays RED until the final rebuild task runs `build_report_template.py`. This task is committed JSX-source-only; the rebuild task commits the regenerated bundle. (Per project convention the JSX edits and the single bundle rebuild are separate commits — see Step 5.)

- [ ] **Step 5: Commit (source only — bundle rebuilt later)**
```bash
git add report-template/screens/Findings.jsx
git commit -m "feat(report): render OWASP MASVS + MASWE mapping groups on findings"
```

### Task 42: Coverage.jsx — add MASVS sub-tab (MasvsTable) gated on active_taxonomies + data

**Files:**
- Modify: `report-template/screens/Coverage.jsx:4-29` (tab state + tab buttons + body switch)
- Modify: `report-template/screens/Coverage.jsx:167` (add `MasvsTable` component before `window.Coverage`)
- Test: `python tools/check_report_template_freshness.py`

- [ ] **Step 1: Capture green baseline (freshness gate)**
Run: `python tools/check_report_template_freshness.py`
Expected: `check_report_template_freshness: OK (<hash>)` (exit 0)

- [ ] **Step 2: After the Step-3 edit, re-run to verify it fails**
Run: `python tools/check_report_template_freshness.py`
Expected: exit 1, `report-template/ has changed since the precompiled bundle was generated.`

- [ ] **Step 3: Add the MASVS sub-tab button (gated) and the MasvsTable component**
The MASVS/MASWE tabs are gated on (a) the taxonomy being declared active for the run and (b) the scene being non-empty. Define a helper at the top of `Coverage` and render the button conditionally. Replace the current component body (lines 4-29):
```jsx
function Coverage({ data }) {
  const [tab, setTab] = useState("nist");

  return (
    <div>
      <div className="section-eyebrow">§ 7-9 — Coverage</div>
      <h2 className="section-title">Control + technique + component coverage</h2>

      <div className="cov-tabs">
        <button className={`cov-tab ${tab === "nist" ? "cov-tab--active" : ""}`} onClick={() => setTab("nist")}>
          NIST 800-53r5 · § 7
        </button>
        <button className={`cov-tab ${tab === "attack" ? "cov-tab--active" : ""}`} onClick={() => setTab("attack")}>
          MITRE ATT&CK · § 8
        </button>
        <button className={`cov-tab ${tab === "apd" ? "cov-tab--active" : ""}`} onClick={() => setTab("apd")}>
          APD component matrix · § 9
        </button>
      </div>

      {tab === "nist" && <NistTable rows={data.nist_rollup} />}
      {tab === "attack" && <AttackTable rows={data.attack_exposure} />}
      {tab === "apd" && <APDMatrix matrix={data.apd_matrix} />}
    </div>
  );
}
```
with (active-taxonomy + non-empty gating; MAS sub-tabs render between ATT&CK and the APD matrix, and the APD-matrix section number shifts when they are present):
```jsx
function Coverage({ data }) {
  const [tab, setTab] = useState("nist");

  const active = (data.meta && data.meta.active_taxonomies) || [];
  const masvsRows = data.masvs_coverage || [];
  const masweRows = data.maswe_coverage || [];
  const showMasvs = active.includes("masvs") && masvsRows.length > 0;
  const showMaswe = active.includes("maswe") && masweRows.length > 0;
  // APD matrix is § 9 by default; each MAS sub-tab inserted before it bumps
  // its section number so the tab labels stay contiguous after ATT&CK (§ 8).
  let n = 9;
  const masvsSec = showMasvs ? n++ : null;
  const masweSec = showMaswe ? n++ : null;
  const apdSec = n;

  return (
    <div>
      <div className="section-eyebrow">§ 7-{apdSec} — Coverage</div>
      <h2 className="section-title">Control + technique + component coverage</h2>

      <div className="cov-tabs">
        <button className={`cov-tab ${tab === "nist" ? "cov-tab--active" : ""}`} onClick={() => setTab("nist")}>
          NIST 800-53r5 · § 7
        </button>
        <button className={`cov-tab ${tab === "attack" ? "cov-tab--active" : ""}`} onClick={() => setTab("attack")}>
          MITRE ATT&CK · § 8
        </button>
        {showMasvs && (
          <button className={`cov-tab ${tab === "masvs" ? "cov-tab--active" : ""}`} onClick={() => setTab("masvs")}>
            OWASP MASVS · § {masvsSec}
          </button>
        )}
        {showMaswe && (
          <button className={`cov-tab ${tab === "maswe" ? "cov-tab--active" : ""}`} onClick={() => setTab("maswe")}>
            OWASP MASWE · § {masweSec}
          </button>
        )}
        <button className={`cov-tab ${tab === "apd" ? "cov-tab--active" : ""}`} onClick={() => setTab("apd")}>
          APD component matrix · § {apdSec}
        </button>
      </div>

      {tab === "nist" && <NistTable rows={data.nist_rollup} />}
      {tab === "attack" && <AttackTable rows={data.attack_exposure} />}
      {tab === "masvs" && showMasvs && <MasvsTable rows={masvsRows} />}
      {tab === "maswe" && showMaswe && <MasweTable rows={masweRows} />}
      {tab === "apd" && <APDMatrix matrix={data.apd_matrix} />}
    </div>
  );
}
```
Then add the `MasvsTable` component immediately before `window.Coverage = Coverage;` (line 169). It consumes a `masvs_coverage` row shaped per the contract (`masvs_id, name, category, category_title, finding_count, finding_ids, surfaces, capability_count, capability_ids, posture`); the `masvs_id` cell renders via `TaxonomyTag` (clickable when `data.taxonomy[masvs_id].url` is present), and `posture` reuses the `cov-cell` style of `AttackTable`:
```jsx
function MasvsTable({ rows }) {
  const postureClass = (p) =>
    p === "satisfying" || p === "covered" ? "covered"
      : p === "exposed" || p === "gapped" ? "gapped"
      : "both";
  return (
    <div>
      <p style={{ color: "var(--ink-2)", maxWidth: "72ch", marginBottom: "var(--space-4)", lineHeight: 1.6 }}>
        OWASP MASVS controls touched by this run, with the capabilities that satisfy them and the findings that expose them. Posture is <strong>satisfying</strong> (capabilities, no findings), <strong>exposed</strong> (findings, no satisfying capability), or <strong>both</strong> (review scope alignment). Authoritative version in <code className="mono">40-synthesis/masvs-coverage.yaml</code>.
      </p>
      <table className="nist-table">
        <thead>
          <tr>
            <th>Control</th>
            <th>Category</th>
            <th>Statement</th>
            <th className="num">Satisfying</th>
            <th className="num">Exposed</th>
            <th>Surfaces</th>
            <th>Posture</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.masvs_id}>
              <td><TaxonomyTag id={r.masvs_id} /></td>
              <td style={{ fontSize: "var(--text-xs)", color: "var(--ink-3)" }}>{r.category_title || r.category}</td>
              <td style={{ color: "var(--ink)" }}>{r.name}</td>
              <td className="num">{r.capability_count}</td>
              <td className="num" style={{ color: r.finding_count > 0 ? "var(--sev-high)" : undefined }}>{r.finding_count}</td>
              <td style={{ fontSize: "var(--text-xs)", color: "var(--ink-3)" }}>{(r.surfaces || []).join(", ") || "—"}</td>
              <td><span className={`cov-cell cov-cell--${postureClass(r.posture)}`}>{r.posture}</span></td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
```

- [ ] **Step 4: Re-run the gate (still RED — bundle rebuilt in the final task)**
Run: `python tools/check_report_template_freshness.py`
Expected: still exit 1 (`report-template/ has changed …`). It goes green only after the rebuild task. The data-presence verification for the `masvs_coverage` scene lives in the report-data section's transform tests, not here.

- [ ] **Step 5: Commit (source only)**
```bash
git add report-template/screens/Coverage.jsx
git commit -m "feat(report): add gated OWASP MASVS coverage sub-tab"
```

### Task 43: Coverage.jsx — add MASWE sub-tab (MasweTable weakness-exposure table)

**Files:**
- Modify: `report-template/screens/Coverage.jsx` (add `MasweTable` component before `window.Coverage`; the `tab === "maswe"` switch + button were already added in the MASVS task)
- Test: `python tools/check_report_template_freshness.py`

- [ ] **Step 1: Capture baseline before this edit**
Run: `python tools/check_report_template_freshness.py`
Expected: exit 1 from the prior uncommitted MASVS edit if run in the same working tree, OR `OK` if the MASVS task was committed and (later) the bundle was rebuilt. The meaningful signal is that adding `MasweTable` leaves/keeps the gate RED until rebuild.

- [ ] **Step 2: After Step-3, confirm the gate is RED**
Run: `python tools/check_report_template_freshness.py`
Expected: exit 1, `report-template/ has changed since the precompiled bundle was generated.`

- [ ] **Step 3: Add the MasweTable component**
Insert immediately after the `MasvsTable` component and before `window.Coverage = Coverage;`. It consumes a `maswe_coverage` row shaped per the contract (`maswe_id, name, category, status, parent_masvs, finding_count, finding_ids, surfaces`). MASWE is findings-only (no satisfying capabilities), so the table is a weakness-exposure table: the `maswe_id` is a `TaxonomyTag` (clickable when `data.taxonomy[maswe_id].url` is set — `maswe_url` returns `null` for unknown categories, in which case it renders as a plain tag), `parent_masvs` renders via `TagRow`:
```jsx
function MasweTable({ rows }) {
  return (
    <div>
      <p style={{ color: "var(--ink-2)", maxWidth: "72ch", marginBottom: "var(--space-4)", lineHeight: 1.6 }}>
        OWASP MASWE weaknesses exposed by findings in this run, with the MASVS control each weakness rolls up to. MASWE is a findings-only weakness taxonomy — there is no &ldquo;satisfying capability&rdquo; column. Authoritative version in <code className="mono">40-synthesis/maswe-coverage.yaml</code>.
      </p>
      <table className="attack-table">
        <thead>
          <tr>
            <th>Weakness</th>
            <th>Name</th>
            <th>Category</th>
            <th>Parent MASVS</th>
            <th className="num">Findings</th>
            <th>Surfaces</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.maswe_id}>
              <td><TaxonomyTag id={r.maswe_id} /></td>
              <td style={{ color: "var(--ink)" }}>{r.name}</td>
              <td style={{ fontSize: "var(--text-xs)", color: "var(--ink-3)" }}>{r.category}</td>
              <td><TagRow ids={r.parent_masvs || []} /></td>
              <td className="num" style={{ color: r.finding_count > 0 ? "var(--sev-high)" : undefined }}>{r.finding_count}</td>
              <td style={{ fontSize: "var(--text-xs)", color: "var(--ink-3)" }}>{(r.surfaces || []).join(", ") || "—"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
```

- [ ] **Step 4: Confirm gate still RED (rebuild pending)**
Run: `python tools/check_report_template_freshness.py`
Expected: exit 1 until the rebuild task runs.

- [ ] **Step 5: Commit (source only)**
```bash
git add report-template/screens/Coverage.jsx
git commit -m "feat(report): add gated OWASP MASWE weakness-exposure sub-tab"
```

### Task 44: Annexes.jsx — make the MASVS/MASWE Sources line + enforcement-note conditional on active_taxonomies

**Files:**
- Modify: `report-template/screens/Annexes.jsx:88` (thread `data` through to the Sources section — already in scope; no signature change needed)
- Modify: `report-template/screens/Annexes.jsx:265` (the Sources `<li>` naming MASVS/MASTG "not a mapped taxonomy")
- Modify: `report-template/screens/Annexes.jsx:276` (the enforcement note's opt-in vocabulary list)
- Test: `python tools/check_report_template_freshness.py`

- [ ] **Step 1: Capture baseline**
Run: `python tools/check_report_template_freshness.py`
Expected: `check_report_template_freshness: OK (<hash>)` if rebuilt since last edit, else exit 1 (carry-over). The check goes/stays RED after the Step-3 edit.

- [ ] **Step 2: After Step-3, confirm the gate is RED**
Run: `python tools/check_report_template_freshness.py`
Expected: exit 1, `report-template/ has changed since the precompiled bundle was generated.`

- [ ] **Step 3: Add the active-taxonomy flag and make the two MAS spans conditional**
At the top of `Annexes` (the function signature is `function Annexes({ data, onOpenFinding }) {` at line 88), add the active-taxonomy flags right after the opening brace:
```jsx
function Annexes({ data, onOpenFinding }) {
  const active = (data.meta && data.meta.active_taxonomies) || [];
  const masActive = active.includes("masvs") || active.includes("maswe");
  return (
    <div>
```
Then change the MASVS/MASWE Sources `<li>` (line 265). Current:
```jsx
            <li><strong>OWASP Top 10 / API Security Top 10 / LLM Top 10</strong> — application, API, and AI-application security; <strong>OWASP MASVS / MASTG</strong> — the Mobile Application Security Verification Standard and Testing Guide, which inform the mobile domain pack but are not a mapped taxonomy</li>
```
Becomes (mapped wording when active, current wording when not):
```jsx
            <li><strong>OWASP Top 10 / API Security Top 10 / LLM Top 10</strong> — application, API, and AI-application security; <strong>OWASP MASVS / MASWE</strong> — {masActive
              ? "the Mobile Application Security Verification Standard (MASVS) and Mobile Application Security Weakness Enumeration (MASWE), mapped on findings (and MASVS on capabilities) for this run"
              : "the Mobile Application Security Verification Standard and Testing Guide, which inform the mobile domain pack but are not a mapped taxonomy"}</li>
```
Then change the enforcement note (line 276). The current note ends its opt-in sentence with:
```jsx
            Three more are opt-in per run — they apply only when declared in the run's configuration because they fit a specific surface: OWASP Top 10 / API Top 10 / LLM Top 10 (on findings) and MITRE ATLAS (on findings, for adversarial-machine-learning threats).
```
Make the MAS membership conditional by splicing a clause in. Replace that sentence with:
```jsx
            {masActive
              ? "Five more are opt-in per run — they apply only when declared in the run's configuration because they fit a specific surface: OWASP Top 10 / API Top 10 / LLM Top 10 (on findings), MITRE ATLAS (on findings, for adversarial-machine-learning threats), OWASP MASVS (on findings and capabilities), and OWASP MASWE (on findings, for mobile-application weaknesses)."
              : "Three more are opt-in per run — they apply only when declared in the run's configuration because they fit a specific surface: OWASP Top 10 / API Top 10 / LLM Top 10 (on findings) and MITRE ATLAS (on findings, for adversarial-machine-learning threats)."}{" "}
```
Note: this clause sits inside the existing `<p>…</p>` enforcement paragraph; keep the surrounding sentences ("Everything in this list other than NIST 800-53r5 is a descriptive cross-reference …" and "The remaining bodies above … shaped the nine goals but are not emitted as machine mappings at all.") unchanged. The trailing `{" "}` preserves the space before the next sentence.

- [ ] **Step 4: Confirm gate still RED (rebuild pending)**
Run: `python tools/check_report_template_freshness.py`
Expected: exit 1 until the rebuild task runs.

- [ ] **Step 5: Commit (source only)**
```bash
git add report-template/screens/Annexes.jsx
git commit -m "feat(report): reframe §11 Annexes MAS sources when MASVS/MASWE are active"
```

### Task 45: Rebuild the report bundle + commit the regenerated app.js and .source-hash

**Files:**
- Modify (regenerated, do not hand-edit): `tools/apd_gauntlet/data/report-template/app.js`
- Modify (regenerated, do not hand-edit): `tools/apd_gauntlet/data/report-template/.source-hash`
- Test: `python tools/check_report_template_freshness.py`

- [ ] **Step 1: Confirm the gate is RED before rebuild (the JSX edits from the prior tasks made it stale)**
Run: `python tools/check_report_template_freshness.py`
Expected: exit 1 with
```
check_report_template_freshness: report-template/ has changed since the precompiled bundle was generated.
Run `python tools/build_report_template.py` and commit the result.
  expected=<old hash>
  actual  =<new hash>
```

- [ ] **Step 2: Rebuild the bundle**
Run: `python tools/build_report_template.py`
Expected: `build-report-template: bundle written.` (exit 0). This runs `npm ci`/`npm install` in `report-template/.build/` if `node_modules` is missing, then `node build.mjs`, which regenerates `tools/apd_gauntlet/data/report-template/app.js` (the concatenated/minified JSX bundle) and rewrites `.source-hash` with the new tree hash. If Node/npm are absent it exits 2 with `build-report-template: node + npm are required.` — Node 20+ must be installed for this step.

- [ ] **Step 3: Verify the gate is now GREEN**
Run: `python tools/check_report_template_freshness.py`
Expected: exit 0, `check_report_template_freshness: OK (<new hash>)` where `<new hash>` matches the `actual` printed in Step 1.

- [ ] **Step 4: Sanity-check that the new app.js contains the new symbols**
Run: `grep -c "MasvsTable\|MasweTable\|active_taxonomies\|OWASP MASVS" tools/apd_gauntlet/data/report-template/app.js`
Expected: a non-zero count (the minified bundle contains the new component names and the MASVS/MASWE strings literally, since they are string literals and identifiers that esbuild preserves or mangles deterministically — at minimum the string literals `OWASP MASVS` and `active_taxonomies` survive minification).

- [ ] **Step 5: Commit the regenerated bundle**
```bash
git add tools/apd_gauntlet/data/report-template/app.js tools/apd_gauntlet/data/report-template/.source-hash
git commit -m "build(report): rebuild bundle for MASVS/MASWE chips, coverage sub-tabs, annex reframe"
```

---


## Phase 7 — Specialist discipline + mobile-pack content

### Task 46: Add masvs/maswe to the apd-control-mappings allowed-keys structural rule

**Files:**
- Modify: `.claude/skills/apd-control-mappings/SKILL.md:12`
- Test: `tests/test_skill_apd_control_mappings.py`

- [ ] **Step 1: Write the failing test**
```python
"""Tests for the apd-control-mappings project skill.

Body-anchored assertions guard against the trap where the frontmatter
``description:`` field happens to contain a phrase the test is looking for.
The allowed-keys list and the MASVS/MASWE discipline subsection are the
contract the mobile pack grounds its structured mappings against.
"""

import re
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SKILL = REPO / ".claude" / "skills" / "apd-control-mappings" / "SKILL.md"


def _body() -> str:
    """Return SKILL.md content after the closing ``---`` of the frontmatter."""
    text = SKILL.read_text()
    parts = text.split("---", 2)
    return parts[2] if len(parts) >= 3 else text


def _allowed_keys_paragraph() -> str:
    """Return the 'Allowed keys:' structural-rule paragraph."""
    for line in _body().splitlines():
        if "Allowed keys:" in line:
            return line
    return ""


def test_skill_exists() -> None:
    assert SKILL.exists()


def test_allowed_keys_paragraph_lists_masvs_and_maswe() -> None:
    para = _allowed_keys_paragraph()
    assert para, "the 'Allowed keys:' structural-rule line is missing"
    assert "`masvs`" in para
    assert "`maswe`" in para


def test_allowed_keys_marks_maswe_as_findings_only() -> None:
    para = _allowed_keys_paragraph()
    # maswe is findings-ONLY; masvs is on BOTH findings and capabilities.
    assert "findings-only" in para.lower() or "findings only" in para.lower()
```
- [ ] **Step 2: Run test to verify it fails**
Run: `python -m pytest tests/test_skill_apd_control_mappings.py -q`
Expected: FAIL with `AssertionError` on `test_allowed_keys_paragraph_lists_masvs_and_maswe` ("`masvs`" in para)

- [ ] **Step 3: Add masvs/maswe to the allowed-keys structural rule**

The current line 12 reads:

```markdown
ALL taxonomy mappings go UNDER the `control_mappings` block — never at the finding/capability root. Allowed keys: `nist_800_53r5`, `mitre_attack`, `cwe`, `owasp_top10`, `owasp_api_top10`, `owasp_llm_top10`, `atlas`. The MITRE ATLAS key on a record is exactly **`atlas`** — NOT `mitre_atlas` (`mitre_atlas` is only the `.apd-run.yaml` declaration name).
```

Replace it with:

```markdown
ALL taxonomy mappings go UNDER the `control_mappings` block — never at the finding/capability root. Allowed keys: `nist_800_53r5`, `mitre_attack`, `cwe`, `owasp_top10`, `owasp_api_top10`, `owasp_llm_top10`, `atlas`, `masvs`, `maswe`. The MITRE ATLAS key on a record is exactly **`atlas`** — NOT `mitre_atlas` (`mitre_atlas` is only the `.apd-run.yaml` declaration name). The OWASP MAS keys are `masvs` and `maswe`: `masvs` may appear on BOTH findings and capabilities (a control violated, or a control satisfied), while `maswe` is findings-only (a specific weakness exposed). Both are emitted only when the run declares `masvs` / `maswe` (i.e. the mobile-applications pack is active) — see the OWASP MAS subsection under Per-taxonomy discipline.
```
- [ ] **Step 4: Run test to verify it passes**
Run: `python -m pytest tests/test_skill_apd_control_mappings.py -q`
Expected: PASS

- [ ] **Step 5: Commit**
```bash
git add .claude/skills/apd-control-mappings/SKILL.md tests/test_skill_apd_control_mappings.py
git commit -m "feat(skill): add masvs/maswe to control_mappings allowed-keys"
```

### Task 47: Add the OWASP MAS per-taxonomy discipline subsection to apd-control-mappings

**Files:**
- Modify: `.claude/skills/apd-control-mappings/SKILL.md:281-287` (insert a new subsection after the MITRE ATLAS subsection, before `## High-confidence-only rule`)
- Modify: `.claude/skills/apd-control-mappings/SKILL.md:289` (extend the high-confidence-only rule line)
- Test: `tests/test_skill_apd_control_mappings.py`

- [ ] **Step 1: Write the failing test (append to the file from the previous task)**
```python
def test_owasp_mas_subsection_present() -> None:
    body = _body()
    assert "### OWASP MAS (mobile — MASVS on findings + capabilities, MASWE on findings, optional)" in body


def test_owasp_mas_subsection_codifies_emit_only_when_declared() -> None:
    body = _body().lower()
    # Emit ONLY when the run declares masvs/maswe (mobile pack active).
    assert "only emit" in body
    assert "mobile-applications" in body


def test_owasp_mas_subsection_states_masvs_on_capability_means_satisfied() -> None:
    body = _body()
    # masvs on a capability = control SATISFIED; on a finding = control VIOLATED.
    assert "control satisfied" in body.lower()
    assert "control violated" in body.lower()


def test_owasp_mas_subsection_carries_maswe_beta_caveat() -> None:
    assert "MASWE-Beta" in _body()


def test_owasp_mas_subsection_grounds_ids_in_pack_prose() -> None:
    body = _body().lower()
    # Every id must be grounded in the mobile pack prose (rubric / patterns).
    assert "ground" in body
    assert "severity-rubric" in body or "common-patterns" in body


def test_owasp_mas_subsection_is_flat_list_no_rationale() -> None:
    body = _body().lower()
    # MAS ids are flat ID strings with no rationale field (like cwe / atlas).
    assert "no rationale field" in body


def test_high_confidence_rule_covers_mas() -> None:
    # The existing high-confidence-only rule must explicitly extend to MAS.
    body = _body()
    idx = body.find("## High-confidence-only rule")
    assert idx != -1
    tail = body[idx:]
    assert "MASVS" in tail or "MASWE" in tail
```
- [ ] **Step 2: Run test to verify it fails**
Run: `python -m pytest tests/test_skill_apd_control_mappings.py -q`
Expected: FAIL with `AssertionError` on `test_owasp_mas_subsection_present`

- [ ] **Step 3: Insert the OWASP MAS subsection and extend the high-confidence rule**

The MITRE ATLAS subsection currently ends (line 287) with this bullet, immediately followed by the `## High-confidence-only rule` heading (line 289):

```markdown
- ATLAS and the `agentic-ai` domain pack pair naturally — but ATLAS is a taxonomy, not a pack: declare it on any run with an ML surface, regardless of domain.

## High-confidence-only rule (extends unchanged)
```

Insert the new subsection between them, so the result reads:

```markdown
- ATLAS and the `agentic-ai` domain pack pair naturally — but ATLAS is a taxonomy, not a pack: declare it on any run with an ML surface, regardless of domain.

### OWASP MAS (mobile — MASVS on findings + capabilities, MASWE on findings, optional)

- OWASP MAS is the mobile application security taxonomy: **MASVS** is the verification standard (control IDs like `MASVS-STORAGE-1`) and **MASWE** is the companion weakness enumeration (IDs like `MASWE-0001`). **Only emit `masvs` / `maswe` when the run declares them** — they are declared together by the `mobile-applications` domain pack (`taxonomies: [masvs, maswe]` on its `domain.yaml`). A run without the mobile pack active does not authorize either key, exactly as the CWE/OWASP/ATLAS keys are gated on their declarations.
- **MASVS attaches to BOTH findings and capabilities — direction-sensitive.** On a *finding*, a `masvs` ID names the **control violated** (the requirement the architecture fails). On a *capability*, the same ID names the **control satisfied** (the requirement the design demonstrably meets, scored on the capability's maturity ladder). MASVS is the only one of these taxonomies that lives on capabilities as a *positive* attestation as well as on findings as a gap.
- **MASWE attaches to findings only** — it names the **specific weakness** the finding's gap instantiates (the MASWE entry whose description and `masvs_v2` parent match the weakness pattern), mirroring how `cwe` and `atlas` attach. A capability never carries `maswe` (there is no "weakness satisfied").
- **Ground every MAS ID in the mobile pack prose.** Each `masvs` / `maswe` ID you emit must already be paired with its pattern in the active pack content — the `MAS mapping:` line on the matching clause in `domains/mobile-applications/severity-rubric.md` or the `MAS mapping:` line under the matching pattern in `domains/mobile-applications/common-patterns/*.md`. If the pack prose does not pair the pattern with a MASVS control (and, where known, a MASWE weakness), do not invent one — emit no MAS ID and justify the gap in `detail`, as with the other taxonomies.
- Each `masvs` / `maswe` mapping is just the ID string — a **flat list, no rationale field** on the schema (like `cwe` and `atlas`). The finding's `detail` (or the capability's evidence) must justify the match: a reviewer should read the prose and see why `MASVS-NETWORK-1` is violated or why the capability satisfies `MASVS-STORAGE-1`.
- ID formats: MASVS controls are `MASVS-<CATEGORY>-<n>` where `<CATEGORY>` is one of `STORAGE`, `CRYPTO`, `AUTH`, `NETWORK`, `PLATFORM`, `CODE`, `RESILIENCE`, `PRIVACY` (e.g. `MASVS-CRYPTO-2`); MASWE weaknesses are `MASWE-####` (e.g. `MASWE-0001`). A bare or unresolvable id fails the report completeness audit (`taxonomy_titles_resolve`) — every id must resolve in the bundled catalogs (`tools/apd_gauntlet/data/masvs.json`, `tools/apd_gauntlet/data/maswe.json`).
- **MASWE-Beta caveat.** MASWE is published as a beta enumeration whose IDs and category assignments are still being stabilized upstream. Cite a `MASWE-####` id only when it resolves in the bundled `maswe.json` snapshot; when the weakness pattern is real but no stable MASWE id covers it yet, cite the MASVS control alone and name the weakness in prose. Do not coin a `MASWE-####` id that is not in the snapshot.

**Examples — accepted MAS mappings**

```yaml
# Finding: a long-lived refresh token is written to SharedPreferences in
# cleartext, readable from a device backup. The mobile confidentiality pattern
# pairs this with MASVS-STORAGE-1 + MASWE-0006.
control_mappings:
  masvs: ["MASVS-STORAGE-1"]
  maswe: ["MASWE-0006"]
```

```yaml
# Capability: all on-device secrets are held in a hardware-backed Keystore
# with non-exportable keys (the confidentiality capability pattern). MASVS on a
# capability = control SATISFIED; no maswe on a capability.
control_mappings:
  masvs: ["MASVS-STORAGE-1", "MASVS-CRYPTO-2"]
```

**Examples — rejected MAS mappings**

```yaml
# Finding on a run with NO mobile pack active (taxonomies do not include masvs).
# Rejected: the run does not declare masvs/maswe, so neither key is authorized —
# the same gating that forbids emitting cwe on an undeclared run.
control_mappings:
  masvs: ["MASVS-STORAGE-1"]   # WRONG: mobile-applications pack is not active
```

```yaml
# Finding: certificate validation is disabled on a PII channel. The author
# reached for a MASWE id by memory that is not in the bundled snapshot.
# Rejected: MASWE-Beta caveat — cite the MASVS control alone and name the
# weakness in prose rather than coining an unresolvable id.
control_mappings:
  masvs: ["MASVS-NETWORK-1"]
  maswe: ["MASWE-9999"]        # WRONG: not in maswe.json — drop it, justify in detail
```

## High-confidence-only rule (extends unchanged)
```

Then extend the high-confidence-only rule paragraph. The current line 291 reads:

```markdown
The existing high-confidence-only rule applies to all six new taxonomies. When uncertain whether a CWE matches the weakness pattern, when uncertain whether the SUT actually exposes the OWASP-categorized surface, when uncertain whether a capability truly implements a D3FEND technique, when uncertain whether an ATLAS technique matches the finding's weakness — **do not map**. Leave the field absent.
```

Replace it with:

```markdown
The existing high-confidence-only rule applies to all eight extension taxonomies. When uncertain whether a CWE matches the weakness pattern, when uncertain whether the SUT actually exposes the OWASP-categorized surface, when uncertain whether a capability truly implements a D3FEND technique, when uncertain whether an ATLAS technique matches the finding's weakness, when uncertain whether a MASVS control is the one the architecture violates or satisfies, or when uncertain whether a MASWE weakness resolves in the bundled snapshot — **do not map**. Leave the field absent.
```
- [ ] **Step 4: Run test to verify it passes**
Run: `python -m pytest tests/test_skill_apd_control_mappings.py -q`
Expected: PASS

- [ ] **Step 5: Commit**
```bash
git add .claude/skills/apd-control-mappings/SKILL.md tests/test_skill_apd_control_mappings.py
git commit -m "feat(skill): add OWASP MAS per-taxonomy discipline subsection"
```

### Task 48: Lint the updated apd-control-mappings SKILL.md against the CI markdownlint glob

**Files:**
- Test: (CI gate — no new file) `.claude/skills/apd-control-mappings/SKILL.md`

- [ ] **Step 1: Run the CI markdownlint glob locally to confirm a clean baseline before edits land downstream**

The CI job (`.github/workflows/markdown-lint.yml`) runs `markdownlint-cli2` over these globs (`.claude/**/*.md` covers the skill); config is `.markdownlint.json` (`MD013`/`MD024 siblings_only`/`MD033`/`MD036`/`MD040`/`MD041`/`MD060` tuned). Reproduce it exactly:

Run:
```bash
npx --yes markdownlint-cli2 \
  "docs/**/*.md" "!docs/superpowers/plans/**" ".claude/**/*.md" \
  "domains/**/*.md" "README.md" "CONTRIBUTING.md" "CHANGELOG.md" "CODE_OF_CONDUCT.md"
```
Expected (before the SKILL.md edits are correct): a `markdownlint-cli2` summary ending in a nonzero `Summary: N error(s)` if the new subsection introduced an MD-rule violation (most likely MD032 blanks-around-lists or MD031 blanks-around-fences around the inserted YAML fences).

- [ ] **Step 2: Fix any reported violations in the edited region**
Ensure every inserted fenced code block has a blank line before and after it, every `- ` bullet list has a blank line above the first item, and the new `###` / `**Examples …**` headings are surrounded by blank lines. (The inserted content in the prior tasks already follows this; this step verifies it under the real linter.)

- [ ] **Step 3: Re-run the exact CI glob**
Run:
```bash
npx --yes markdownlint-cli2 \
  "docs/**/*.md" "!docs/superpowers/plans/**" ".claude/**/*.md" \
  "domains/**/*.md" "README.md" "CONTRIBUTING.md" "CHANGELOG.md" "CODE_OF_CONDUCT.md"
```
Expected: PASS — summary line `Summary: 0 error(s)` and exit code 0.

- [ ] **Step 4: Run the full skill test suite to confirm no regression**
Run: `python -m pytest tests/test_skill_apd_control_mappings.py -q`
Expected: PASS

- [ ] **Step 5: Commit (only if Step 2 changed anything)**
```bash
git add .claude/skills/apd-control-mappings/SKILL.md
git commit -m "style(skill): satisfy markdownlint for OWASP MAS subsection"
```

### Task 49: Add a 'MAS mapping' convention and per-clause lines to the mobile severity-rubric

**Files:**
- Modify: `domains/mobile-applications/severity-rubric.md:3` (add the convention note)
- Modify: `domains/mobile-applications/severity-rubric.md:23-49` (append a `MAS mapping:` line to each Critical/High/Medium clause that already names a MASVS control)
- Test: `tests/test_mobile_pack_mas_mapping.py`

- [ ] **Step 1: Write the failing test**
```python
"""The mobile pack must pair each pattern with its MASVS control (and, where
known, its MASWE weakness) explicitly, so a specialist can ground a structured
`control_mappings.masvs` / `.maswe` mapping in the pack prose.

The convention is a literal ``MAS mapping:`` marker carrying ``MASVS-...`` ids
(and optional ``MASWE-####`` ids). These greps are the contract the
apd-control-mappings 'ground every MAS ID in the pack prose' rule depends on.
"""

import re
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PACK = REPO / "domains" / "mobile-applications"
RUBRIC = PACK / "severity-rubric.md"

MASVS_ID = re.compile(r"MASVS-(STORAGE|CRYPTO|AUTH|NETWORK|PLATFORM|CODE|RESILIENCE|PRIVACY)-[1-9][0-9]*")
MASWE_ID = re.compile(r"MASWE-[0-9]{4}")


def test_rubric_documents_mas_mapping_convention() -> None:
    text = RUBRIC.read_text()
    assert "MAS mapping:" in text
    # The convention must be explained near the top, not only used inline.
    head = text[: text.find("## Critical")]
    assert "MAS mapping:" in head


def test_rubric_has_at_least_six_mas_mapping_lines() -> None:
    lines = [ln for ln in RUBRIC.read_text().splitlines() if "MAS mapping:" in ln]
    # one per Critical/High/Medium clause that names a MASVS control
    assert len(lines) >= 6, f"only {len(lines)} MAS mapping lines"


def test_every_mas_mapping_line_carries_a_valid_masvs_id() -> None:
    for ln in RUBRIC.read_text().splitlines():
        if "MAS mapping:" in ln:
            assert MASVS_ID.search(ln), f"no MASVS id on: {ln!r}"


def test_mas_mapping_ids_use_only_valid_categories() -> None:
    # No typo'd category outside the 8-category enum slips into a mapping line.
    bad = re.compile(r"MASVS-(?!STORAGE|CRYPTO|AUTH|NETWORK|PLATFORM|CODE|RESILIENCE|PRIVACY)\w+")
    for ln in RUBRIC.read_text().splitlines():
        if "MAS mapping:" in ln:
            assert not bad.search(ln), f"invalid MASVS category on: {ln!r}"
```
- [ ] **Step 2: Run test to verify it fails**
Run: `python -m pytest tests/test_mobile_pack_mas_mapping.py -q`
Expected: FAIL with `AssertionError` on `test_rubric_documents_mas_mapping_convention` ("MAS mapping:" in text)

- [ ] **Step 3: Add the convention note and per-clause MAS mapping lines**

First, after the existing inline-reference sentence in the intro (line 3 ends with "...OWASP MAS supplies the technical requirements it evaluates against."), add a convention note. Edit the end of that paragraph by appending a new paragraph immediately after line 3:

```markdown
> **`MAS mapping:` convention.** Each rubric clause and each common-pattern below that maps to an OWASP MAS requirement carries an explicit `MAS mapping:` line naming its MASVS control(s) and, where a stable weakness exists, its MASWE id. A specialist grounds a structured `control_mappings.masvs` (control violated on a finding, control satisfied on a capability) and findings-only `control_mappings.maswe` mapping in that line — never inventing an id the pack prose does not pair with the pattern. MASWE is a beta enumeration: where no stable `MASWE-####` covers the weakness, the line names the MASVS control alone.
```

Then append a `MAS mapping:` line to each rubric clause that already names a MASVS control. The Critical clauses (lines 23-28) become:

```markdown
- **Hardcoded backend credential, shared symmetric secret, or signing key embedded in the binary** and recoverable by static analysis from any IPA/APK, granting backend or third-party access for the entire install base. The scale-vector and all-users blast-radius modifiers both load; obfuscation (MASVS-RESILIENCE-2) is not a mitigant. Maps to MASVS-CRYPTO-2 and the MASWE hardcoded-secret area. MAS mapping: MASVS-CRYPTO-2, MASVS-RESILIENCE-2; MASWE-0013.
- **The backend trusts a client-asserted security signal as an authorization input** — a root/jailbreak verdict, a "biometric/step-up passed" assertion, an entitlement or feature flag, or a price/amount/quantity computed client-side and accepted server-side without re-verification. The client-side-only-enforcement modifier pivots a device-local bypass into a backend write at fleet scale. MAS mapping: MASVS-AUTH-1.
- **No transport encryption, or certificate validation disabled / trust-all on a PII- or credential-bearing channel, on stock devices** — a network MitM yields token or PII theft at scale without needing a rooted device. Maps to MASVS-NETWORK-1. MAS mapping: MASVS-NETWORK-1; MASWE-0050.
- **A privileged or consequential action gated only by client-side local authentication** (a `BiometricPrompt`/`LAContext` UI check or `canEvaluatePolicy`-style gate) with no server re-authentication of the action — a patched or instrumented client performs the action with no factor presented. Maps to MASVS-AUTH-3. MAS mapping: MASVS-AUTH-3.
- **A malicious, compromised, or over-broad in-process third-party SDK** with network, storage, and reflection capability shipped to the install base — the backdoored-SDK scale-vector reaching every user's on-device data and tokens. Maps to MASVS-CODE-2. MAS mapping: MASVS-CODE-2.
- **A backend authorization decision (object-level or function-level) made client-side**, so backend endpoints accept any request the patched app can send — equivalent to BOLA/BFLA at fleet scale. Routes to api-security / identity-security for the server-side decision; filed here as the mobile-origin critical with the "the client is not an authorization point" framing. MAS mapping: MASVS-AUTH-1.
```

The High clauses (lines 34-39) become:

```markdown
- **Sensitive data — access/refresh tokens, PII/PHI, or keys — persisted in unprotected on-device storage** (plist, `SharedPreferences`, unencrypted SQLite, plain files, NSUserDefaults) rather than the Keystore/Keychain, readable from a device backup or a stolen device, or by a co-resident app where the storage is shared. Maps to MASVS-STORAGE-1. MAS mapping: MASVS-STORAGE-1; MASWE-0006.
- **A long-lived access or refresh token stored on the device with no server-side revocation, rotation, or device-binding** — stolen-device or extracted-token replay grants the token's full lifetime. Maps to MASVS-AUTH-2. MAS mapping: MASVS-AUTH-2.
- **A WebView JavaScript bridge exposes native capability or data to loaded web content without origin allowlisting** (`addJavascriptInterface`, `WKScriptMessageHandler`, `file://` access, mixed content) — untrusted content crosses into native privilege. Maps to MASVS-PLATFORM-2. MAS mapping: MASVS-PLATFORM-2.
- **An exported component, unverified deep link, or custom URL scheme accepts unauthenticated parameters that drive an in-app state change or sensitive data read** without server re-verification. Maps to MASVS-PLATFORM-1. MAS mapping: MASVS-PLATFORM-1.
- **No certificate or public-key pinning on a high-value channel** whose threat model includes user-installed MitM CAs or hostile networks. High rather than critical because stock-device default TLS still holds against the casual on-path case. Maps to MASVS-NETWORK-2. MAS mapping: MASVS-NETWORK-2.
- **Sensitive data leaks to system surfaces** — clipboard, keyboard cache, task-switcher screenshot/backgrounding snapshot, autofill, or analytics-SDK egress carrying PII or tokens. Maps to MASVS-STORAGE-2 and MASVS-PLATFORM-3. MAS mapping: MASVS-STORAGE-2, MASVS-PLATFORM-3.
```

The Medium clauses (lines 45-49) become:

```markdown
- **Root/jailbreak/Frida/debugger/emulator detection absent or trivially bypassable** — Medium because it is an advisory defense-in-depth signal, not a control; it escalates to the Critical client-side-enforcement clause only if the backend actually relies on the verdict. Maps to MASVS-RESILIENCE-1. MAS mapping: MASVS-RESILIENCE-1.
- **No obfuscation or anti-decompilation on a binary that embeds sensitive (but non-secret) business logic or endpoint inventory** — a cost-raiser gap, not an exposure on its own. Maps to MASVS-RESILIENCE-2. MAS mapping: MASVS-RESILIENCE-2.
- **No anti-tamper or repackaging/re-sign detection, with no compensating server-side attestation** — Medium absent a server-trusted decision behind it; escalates if a client-trusted control depends on binary integrity. Maps to MASVS-RESILIENCE-3. MAS mapping: MASVS-RESILIENCE-3.
- **No forced-update / minimum-version kill-switch** — vulnerable client versions linger indefinitely; escalates with a known client CVE. Maps to MASVS-CODE-4. MAS mapping: MASVS-CODE-4.
- **Outdated minimum-OS or target-SDK floor** losing a platform security feature, with a compensating control present. Maps to MASVS-CODE-1. MAS mapping: MASVS-CODE-1.
```
- [ ] **Step 4: Run test to verify it passes**
Run: `python -m pytest tests/test_mobile_pack_mas_mapping.py -q`
Expected: PASS

- [ ] **Step 5: Commit**
```bash
git add domains/mobile-applications/severity-rubric.md tests/test_mobile_pack_mas_mapping.py
git commit -m "feat(mobile-pack): add MAS mapping convention + per-clause lines to severity-rubric"
```

### Task 50: Add MAS mapping lines to mobile common-patterns confidentiality.md

**Files:**
- Modify: `domains/mobile-applications/common-patterns/confidentiality.md` (append a `MAS mapping:` line as the last bullet of each `Detail:`-bearing finding/capability pattern)
- Test: `tests/test_mobile_pack_mas_mapping.py`

- [ ] **Step 1: Extend the failing test (append to the file from the prior task)**
```python
CONF = PACK / "common-patterns" / "confidentiality.md"


def test_confidentiality_patterns_carry_mas_mapping_lines() -> None:
    lines = [ln for ln in CONF.read_text().splitlines() if "MAS mapping:" in ln]
    # 8 finding patterns + 4 capability patterns name a MASVS control; the
    # generic blocked/uncertainty pattern does not. Expect at least 9 lines.
    assert len(lines) >= 9, f"only {len(lines)} MAS mapping lines in confidentiality.md"


def test_confidentiality_mas_mapping_ids_valid() -> None:
    for ln in CONF.read_text().splitlines():
        if "MAS mapping:" in ln:
            assert MASVS_ID.search(ln), f"no MASVS id on: {ln!r}"
            bad = re.compile(r"MASVS-(?!STORAGE|CRYPTO|AUTH|NETWORK|PLATFORM|CODE|RESILIENCE|PRIVACY)\w+")
            assert not bad.search(ln), f"invalid MASVS category on: {ln!r}"
```
- [ ] **Step 2: Run test to verify it fails**
Run: `python -m pytest tests/test_mobile_pack_mas_mapping.py::test_confidentiality_patterns_carry_mas_mapping_lines -q`
Expected: FAIL with `AssertionError: only 0 MAS mapping lines in confidentiality.md`

- [ ] **Step 3: Append a `MAS mapping:` bullet to each pattern**

Each finding pattern ends with a `- Detail:` bullet; add a `- MAS mapping:` bullet right after it (the structured pairing the specialist grounds against; prose stays in `Detail`). The edits, anchored by the unique closing phrase of each `Detail` line:

For the unprotected-storage pattern (Detail ends "...the at-rest layer, not the control of last resort."), append after that bullet:

```markdown
- MAS mapping: MASVS-STORAGE-1; MASWE-0006
```

For the hardcoded-secret pattern (Detail ends "...applies to the JS bundle exactly as to the compiled binary."), append:

```markdown
- MAS mapping: MASVS-CRYPTO-2, MASVS-RESILIENCE-2; MASWE-0013
```

For the system-surfaces leakage pattern (Detail ends "...the secret's authority, which remains server-revocable."), append:

```markdown
- MAS mapping: MASVS-STORAGE-2, MASVS-PLATFORM-3
```

For the third-party-SDK egress pattern (Detail ends "...not a runtime check inside the same process."), append:

```markdown
- MAS mapping: MASVS-STORAGE-2, MASVS-PRIVACY-2; MASWE-0064
```

For the PII-to-logs pattern (Detail ends "...does not change the secret's server-side authority."), append:

```markdown
- MAS mapping: MASVS-STORAGE-1; MASWE-0001
```

For the cleartext-in-transit pattern (Detail ends "...not a user-installed MitM CA."), append:

```markdown
- MAS mapping: MASVS-NETWORK-1; MASWE-0050
```

For the WebView-bridge / content-provider leak pattern (Detail ends "...the device — and thus the attacker — can reach."), append:

```markdown
- MAS mapping: MASVS-PLATFORM-2, MASVS-PLATFORM-1
```

For the weak-at-rest-crypto pattern (Detail ends "...the secret's authority must still be server-revocable."), append:

```markdown
- MAS mapping: MASVS-CRYPTO-1; MASWE-0020
```

The blocked/uncertainty pattern (`Disposition: blocked or uncertainty`) names no single MASVS control and gets no MAS mapping line.

Then add a `MAS mapping:` clause to each capability pattern. Capability patterns are single paragraphs, so append the convention sentence to the end of each. For the Keystore/Keychain capability (ends "...StrongBox-unavailable fallback policy."), append at paragraph end:

```markdown
 MAS mapping: MASVS-STORAGE-1, MASVS-CRYPTO-2 (control satisfied).
```

For the screenshot/clipboard-hardening capability (ends "...flags a sensitive Activity missing `FLAG_SECURE`."), append:

```markdown
 MAS mapping: MASVS-STORAGE-2, MASVS-PLATFORM-3 (control satisfied).
```

For the TLS-floor capability (ends "...enforced in CI against config drift."), append:

```markdown
 MAS mapping: MASVS-NETWORK-1 (control satisfied).
```

For the obfuscation/anti-decompilation capability (ends "...delays the reverse engineer rather than stopping them."), append:

```markdown
 MAS mapping: MASVS-RESILIENCE-2 (control satisfied, defense-in-depth).
```
- [ ] **Step 4: Run test to verify it passes**
Run: `python -m pytest tests/test_mobile_pack_mas_mapping.py -q`
Expected: PASS

- [ ] **Step 5: Commit**
```bash
git add domains/mobile-applications/common-patterns/confidentiality.md tests/test_mobile_pack_mas_mapping.py
git commit -m "feat(mobile-pack): add MAS mapping lines to confidentiality patterns"
```

### Task 51: Add MAS mapping lines to mobile common-patterns authenticity.md

**Files:**
- Modify: `domains/mobile-applications/common-patterns/authenticity.md` (append a `MAS mapping:` line to each finding/capability pattern)
- Test: `tests/test_mobile_pack_mas_mapping.py`

- [ ] **Step 1: Extend the failing test (append to the file)**
```python
AUTH = PACK / "common-patterns" / "authenticity.md"


def test_authenticity_patterns_carry_mas_mapping_lines() -> None:
    lines = [ln for ln in AUTH.read_text().splitlines() if "MAS mapping:" in ln]
    # 6 finding patterns + 4 capability patterns name a MASVS control; the
    # generic blocked/uncertainty pattern does not. Expect at least 8 lines.
    assert len(lines) >= 8, f"only {len(lines)} MAS mapping lines in authenticity.md"


def test_authenticity_mas_mapping_ids_valid() -> None:
    bad = re.compile(r"MASVS-(?!STORAGE|CRYPTO|AUTH|NETWORK|PLATFORM|CODE|RESILIENCE|PRIVACY)\w+")
    for ln in AUTH.read_text().splitlines():
        if "MAS mapping:" in ln:
            assert MASVS_ID.search(ln), f"no MASVS id on: {ln!r}"
            assert not bad.search(ln), f"invalid MASVS category on: {ln!r}"
```
- [ ] **Step 2: Run test to verify it fails**
Run: `python -m pytest tests/test_mobile_pack_mas_mapping.py::test_authenticity_patterns_carry_mas_mapping_lines -q`
Expected: FAIL with `AssertionError: only 0 MAS mapping lines in authenticity.md`

- [ ] **Step 3: Append a `MAS mapping:` bullet to each pattern**

For the no-hardware-attestation finding (Detail ends "...score the consequence of the backend having no cryptographic genuine-client proof at all."), append:

```markdown
- MAS mapping: MASVS-RESILIENCE-4; MASWE-0099
```

For the no-pinning finding (Detail ends "...it does not relieve the backend of independently re-authorizing every request."), append:

```markdown
- MAS mapping: MASVS-NETWORK-2; MASWE-0052
```

For the biometric-UI-only finding (Detail ends "...never a client-asserted \"biometric passed\" flag."), append:

```markdown
- MAS mapping: MASVS-AUTH-3, MASVS-CRYPTO-2; MASWE-0042
```

For the app-signing/provenance finding (Detail ends "...the developer's key before executing an update, because an OTA channel that applies an unsigned bundle is an app-signing bypass reaching the install base outside store review (see the OTA pattern in integrity.md)."), append:

```markdown
- MAS mapping: MASVS-RESILIENCE-3, MASVS-CODE-1; MASWE-0097
```

For the AAL/PKCE finding (Detail ends "...rather than trusting a client-asserted \"step-up passed\" flag."), append:

```markdown
- MAS mapping: MASVS-AUTH-1, MASVS-AUTH-3; MASWE-0040
```

For the SDK-provenance finding (Detail ends "...no SDK-originated request is trusted more than any other client request."), append:

```markdown
- MAS mapping: MASVS-CODE-2; MASWE-0079
```

For the deep-link/IPC-caller-identity finding (Detail ends "...cannot satisfy the server-side authorization contract on its own."), append:

```markdown
- MAS mapping: MASVS-PLATFORM-1; MASWE-0072
```

The blocked/uncertainty pattern gets no MAS mapping line.

Then append the convention sentence to each capability paragraph. Hardware-attestation capability (ends "...rather than logged and ignored."):

```markdown
 MAS mapping: MASVS-RESILIENCE-4 (control satisfied).
```

Pinning capability (ends "...enforced in CI against drift."):

```markdown
 MAS mapping: MASVS-NETWORK-2 (control satisfied).
```

Biometric-key-release capability (ends "...rather than trusting a client flag."):

```markdown
 MAS mapping: MASVS-AUTH-3, MASVS-CRYPTO-2 (control satisfied).
```

PKCE + SBOM capability (ends "...to retire a compromised component fleet-wide."):

```markdown
 MAS mapping: MASVS-AUTH-1, MASVS-CODE-2 (control satisfied).
```
- [ ] **Step 4: Run test to verify it passes**
Run: `python -m pytest tests/test_mobile_pack_mas_mapping.py -q`
Expected: PASS

- [ ] **Step 5: Commit**
```bash
git add domains/mobile-applications/common-patterns/authenticity.md tests/test_mobile_pack_mas_mapping.py
git commit -m "feat(mobile-pack): add MAS mapping lines to authenticity patterns"
```

### Task 52: Add MAS mapping lines to mobile common-patterns integrity.md

**Files:**
- Modify: `domains/mobile-applications/common-patterns/integrity.md` (append a `MAS mapping:` line to each finding/capability pattern)
- Test: `tests/test_mobile_pack_mas_mapping.py`

- [ ] **Step 1: Extend the failing test (append to the file)**
```python
INTEG = PACK / "common-patterns" / "integrity.md"


def test_integrity_patterns_carry_mas_mapping_lines() -> None:
    lines = [ln for ln in INTEG.read_text().splitlines() if "MAS mapping:" in ln]
    # 8 finding patterns + 4 capability patterns name a MASVS control; the
    # generic blocked/uncertainty pattern does not. Expect at least 9 lines.
    assert len(lines) >= 9, f"only {len(lines)} MAS mapping lines in integrity.md"


def test_integrity_mas_mapping_ids_valid() -> None:
    bad = re.compile(r"MASVS-(?!STORAGE|CRYPTO|AUTH|NETWORK|PLATFORM|CODE|RESILIENCE|PRIVACY)\w+")
    for ln in INTEG.read_text().splitlines():
        if "MAS mapping:" in ln:
            assert MASVS_ID.search(ln), f"no MASVS id on: {ln!r}"
            assert not bad.search(ln), f"invalid MASVS category on: {ln!r}"
```
- [ ] **Step 2: Run test to verify it fails**
Run: `python -m pytest tests/test_mobile_pack_mas_mapping.py::test_integrity_patterns_carry_mas_mapping_lines -q`
Expected: FAIL with `AssertionError: only 0 MAS mapping lines in integrity.md`

- [ ] **Step 3: Append a `MAS mapping:` bullet to each pattern**

For the untrusted-inbound-input finding (Detail ends "...not performed because the client received the message."), append:

```markdown
- MAS mapping: MASVS-PLATFORM-1, MASVS-PLATFORM-2, MASVS-CODE-3; MASWE-0070
```

For the client-side-only-control finding (Detail ends "...an advisory risk input (see the RASP pattern below), never the gate itself."), append:

```markdown
- MAS mapping: MASVS-AUTH-1; MASWE-0045
```

For the WebView-bridge finding (Detail ends "...any backend action the bridge triggers is re-authorized server-side."), append:

```markdown
- MAS mapping: MASVS-PLATFORM-2; MASWE-0069
```

For the exported-component/deep-link finding (Detail ends "...cannot satisfy the server-side authorization contract on its own."), append:

```markdown
- MAS mapping: MASVS-PLATFORM-1; MASWE-0072
```

For the RASP/runtime-integrity finding (Detail ends "...the genuine integrity floor is hardware attestation, which Authenticity owns."), append:

```markdown
- MAS mapping: MASVS-RESILIENCE-1; MASWE-0093
```

For the anti-tamper/repackaging finding (Detail ends "...distinguishes a genuine build from a repackaged one regardless of what the client claims."), append:

```markdown
- MAS mapping: MASVS-RESILIENCE-3; MASWE-0097
```

For the poisoned-SDK finding (Detail ends "...an unattested dependency set fails the organizational vetting gate as well as the runtime trust check."), append:

```markdown
- MAS mapping: MASVS-CODE-2; MASWE-0079
```

For the in-transit-tamper finding (Detail ends "...rather than trusting that transport preserved it."), append:

```markdown
- MAS mapping: MASVS-NETWORK-1; MASWE-0050
```

For the OTA-bundle finding (Detail ends "...the backend re-authorizes every action regardless of which bundle version issued it."), append:

```markdown
- MAS mapping: MASVS-CODE-2, MASVS-RESILIENCE-3; MASWE-0098
```

The blocked/uncertainty pattern gets no MAS mapping line.

Then append the convention sentence to each capability paragraph. Server-side-enforcement capability (ends "...client-asserted security signals are confirmed to carry zero authorization weight."):

```markdown
 MAS mapping: MASVS-AUTH-1 (control satisfied).
```

Typed-validated-boundary capability (ends "...the App Links `assetlinks.json` / `apple-app-site-association` verification is monitored."):

```markdown
 MAS mapping: MASVS-PLATFORM-1, MASVS-CODE-3 (control satisfied).
```

Runtime-integrity-shipped-to-server capability (ends "...feed an active risk-scoring or step-up decision rather than sitting unread."):

```markdown
 MAS mapping: MASVS-RESILIENCE-1 (control satisfied, advisory signal).
```

Anti-repackaging-plus-attestation capability (ends "...can retire a compromised build fleet-wide."):

```markdown
 MAS mapping: MASVS-RESILIENCE-3, MASVS-RESILIENCE-4 (control satisfied).
```
- [ ] **Step 4: Run test to verify it passes**
Run: `python -m pytest tests/test_mobile_pack_mas_mapping.py -q`
Expected: PASS

- [ ] **Step 5: Commit**
```bash
git add domains/mobile-applications/common-patterns/integrity.md tests/test_mobile_pack_mas_mapping.py
git commit -m "feat(mobile-pack): add MAS mapping lines to integrity patterns"
```

### Task 53: Lint the mobile pack edits against the CI markdownlint glob

**Files:**
- Test: (CI gate — no new file) `domains/mobile-applications/severity-rubric.md`, `domains/mobile-applications/common-patterns/*.md`

- [ ] **Step 1: Run the CI markdownlint glob locally**

The `domains/**/*.md` glob in `.github/workflows/markdown-lint.yml` covers every edited pack file. The new `MAS mapping:` bullets are appended to existing lists, and the convention note in `severity-rubric.md` is a new blockquote paragraph — both can trip MD032 (blanks-around-lists) or MD028 (blank-line-inside-blockquote). Run the exact CI invocation:

Run:
```bash
npx --yes markdownlint-cli2 \
  "docs/**/*.md" "!docs/superpowers/plans/**" ".claude/**/*.md" \
  "domains/**/*.md" "README.md" "CONTRIBUTING.md" "CHANGELOG.md" "CODE_OF_CONDUCT.md"
```
Expected (before fixes): nonzero exit with a `Summary: N error(s)` line if any new MD violation was introduced, naming the file:line and rule (e.g. `severity-rubric.md:5 MD028/no-blanks-blockquote`).

- [ ] **Step 2: Fix any reported violations**
For the `severity-rubric.md` convention note, ensure the new `> **\`MAS mapping:\` convention.** ...` blockquote is separated from the surrounding content by blank lines and is not a bare blank line inside an existing blockquote. For the `MAS mapping:` bullets, ensure each sits flush inside its existing list (`- ` at the same indent, no blank line inserted before it).

- [ ] **Step 3: Re-run the exact CI glob**
Run:
```bash
npx --yes markdownlint-cli2 \
  "docs/**/*.md" "!docs/superpowers/plans/**" ".claude/**/*.md" \
  "domains/**/*.md" "README.md" "CONTRIBUTING.md" "CHANGELOG.md" "CODE_OF_CONDUCT.md"
```
Expected: PASS — `Summary: 0 error(s)`, exit code 0.

- [ ] **Step 4: Run the full mobile-pack assertion suite**
Run: `python -m pytest tests/test_mobile_pack_mas_mapping.py -q`
Expected: PASS

- [ ] **Step 5: Commit (only if Step 2 changed anything)**
```bash
git add domains/mobile-applications/severity-rubric.md domains/mobile-applications/common-patterns/confidentiality.md domains/mobile-applications/common-patterns/authenticity.md domains/mobile-applications/common-patterns/integrity.md
git commit -m "style(mobile-pack): satisfy markdownlint for MAS mapping lines"
```

---


## Phase 8 — Gates / audit / linter

### Task 54: Audit id_coverage_masvs + id_coverage_maswe (every cited MAS id is a taxonomy key)

**Files:**
- Modify: `tools/apd_gauntlet/synthesis/audit.py:166-172`
- Test: `tests/test_cli_audit_report.py`

- [ ] **Step 1: Write the failing test**
```python
# Append to tests/test_cli_audit_report.py (uses existing _copy_example + _mutate_data_js helpers).

# ---------------------------------------------------------------------------
# id_coverage_masvs / id_coverage_maswe (OWASP MAS — subset of taxonomy keys)
# ---------------------------------------------------------------------------

def test_id_coverage_mas_exempt_when_no_mas_findings(tmp_path):
    """The shipped example cites no MAS ids, so both checks pass vacuously."""
    dst = _copy_example(tmp_path)
    result = audit_report(dst)
    names = {c["name"] for c in result.checks}
    assert "id_coverage_masvs" in names
    assert "id_coverage_maswe" in names
    masvs = [c for c in result.checks if c["name"] == "id_coverage_masvs"][0]
    maswe = [c for c in result.checks if c["name"] == "id_coverage_maswe"][0]
    assert masvs["status"] == "pass" and masvs["klass"] == "structural", masvs
    assert maswe["status"] == "pass" and maswe["klass"] == "structural", maswe


def test_id_coverage_masvs_fails_on_cited_id_missing_from_taxonomy(tmp_path):
    """A finding citing a MASVS id with no matching taxonomy entry FAILS."""
    dst = _copy_example(tmp_path)

    def _add(d):
        d["findings"][0].setdefault("control_mappings", {})["masvs"] = ["MASVS-STORAGE-1"]
        # Deliberately do NOT add MASVS-STORAGE-1 to d["taxonomy"].
    _mutate_data_js(dst, _add)
    result = audit_report(dst)
    c = [x for x in result.checks if x["name"] == "id_coverage_masvs"][0]
    assert c["status"] == "fail", c
    assert "MASVS-STORAGE-1" in c["detail"]
    assert result.status == "fail"


def test_id_coverage_maswe_fails_on_cited_id_missing_from_taxonomy(tmp_path):
    """A finding citing a MASWE id with no matching taxonomy entry FAILS."""
    dst = _copy_example(tmp_path)

    def _add(d):
        d["findings"][0].setdefault("control_mappings", {})["maswe"] = ["MASWE-0001"]
    _mutate_data_js(dst, _add)
    result = audit_report(dst)
    c = [x for x in result.checks if x["name"] == "id_coverage_maswe"][0]
    assert c["status"] == "fail", c
    assert "MASWE-0001" in c["detail"]


def test_id_coverage_masvs_passes_when_cited_id_present_in_taxonomy(tmp_path):
    """Citing a MASVS id that IS a taxonomy key keeps the check green."""
    dst = _copy_example(tmp_path)

    def _add(d):
        d["findings"][0].setdefault("control_mappings", {})["masvs"] = ["MASVS-STORAGE-1"]
        d["taxonomy"]["MASVS-STORAGE-1"] = {
            "family": "OWASP MASVS", "title": "The app securely stores sensitive data."}
    _mutate_data_js(dst, _add)
    result = audit_report(dst)
    c = [x for x in result.checks if x["name"] == "id_coverage_masvs"][0]
    assert c["status"] == "pass", c
```
- [ ] **Step 2: Run test to verify it fails**
Run: `python3 -m pytest tests/test_cli_audit_report.py::test_id_coverage_mas_exempt_when_no_mas_findings tests/test_cli_audit_report.py::test_id_coverage_masvs_fails_on_cited_id_missing_from_taxonomy tests/test_cli_audit_report.py::test_id_coverage_maswe_fails_on_cited_id_missing_from_taxonomy -q`
Expected: FAIL with "AssertionError" — `id_coverage_masvs` / `id_coverage_maswe` not in the emitted check names (the checks don't exist yet).

- [ ] **Step 3: Add the two MAS subset checks after id_coverage_attack**
Current code (audit.py lines 166-172):
```python
    # ATT&CK per-technique (data.attack_exposure is 1:1).
    # Subset check (yaml_ids ⊆ data_attack_ids): attack_exposure carries the full reference catalog
    # (more keys than the run cites), so only "every cited id is present" is required, not equality.
    attack_ids = {row.get("id") for row in attack}
    data_attack_ids = {row.get("id") for row in parsed.get("attack_exposure", [])}
    _check(result, "id_coverage_attack", attack_ids <= data_attack_ids,
           f"yaml={len(attack_ids)} data.js={len(data_attack_ids)}")
```
Insert immediately after it (mirrors id_coverage_nist's "every cited id ⊆ taxonomy keys" pattern; `taxonomy` is bound by the id_coverage_nist block above):
```python
    # OWASP MAS per-id (findings cite masvs/maswe in control_mappings; both must
    # resolve to a taxonomy_dict key so the report renders a title, never a bare
    # ID). Mirror id_coverage_attack: every CITED id must be a taxonomy key.
    # Zero cited ids -> empty set -> vacuously passes (no MAS-active run penalty).
    def _cited_mas_ids(key: str) -> set[str]:
        ids: set[str] = set()
        for f in parsed.get("findings", []):
            cm = f.get("control_mappings") if isinstance(f, dict) else None
            vals = (cm or {}).get(key) if isinstance(cm, dict) else None
            if isinstance(vals, list):
                ids.update(str(v) for v in vals if v)
        return ids

    masvs_cited = _cited_mas_ids("masvs")
    masvs_missing = sorted(cid for cid in masvs_cited if cid not in taxonomy)[:5]
    _check(result, "id_coverage_masvs", not masvs_missing,
           f"cited={len(masvs_cited)} missing_from_taxonomy={masvs_missing}",
           klass="structural")

    maswe_cited = _cited_mas_ids("maswe")
    maswe_missing = sorted(cid for cid in maswe_cited if cid not in taxonomy)[:5]
    _check(result, "id_coverage_maswe", not maswe_missing,
           f"cited={len(maswe_cited)} missing_from_taxonomy={maswe_missing}",
           klass="structural")
```
- [ ] **Step 4: Run test to verify it passes**
Run: `python3 -m pytest tests/test_cli_audit_report.py -k "id_coverage_mas" -q`
Expected: PASS (4 tests).

- [ ] **Step 5: Commit**
```bash
git add tools/apd_gauntlet/synthesis/audit.py tests/test_cli_audit_report.py
git commit -m "feat(audit): id_coverage_masvs + id_coverage_maswe (cited MAS id must be a taxonomy key)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 55: Extend coverage_rollups_nonempty for MAS (active + cited => rows required)

**Files:**
- Modify: `tools/apd_gauntlet/synthesis/audit.py:348-361`
- Test: `tests/test_cli_audit_report.py`

- [ ] **Step 1: Write the failing test**
```python
# Append to tests/test_cli_audit_report.py.

# ---------------------------------------------------------------------------
# coverage_rollups_nonempty — MAS extension (active + cited => rows required)
# ---------------------------------------------------------------------------

def test_coverage_rollups_mas_exempt_when_inactive(tmp_path):
    """No 'masvs'/'maswe' in meta.active_taxonomies => MAS does not gate the check."""
    dst = _copy_example(tmp_path)
    result = audit_report(dst)
    c = [x for x in result.checks if x["name"] == "coverage_rollups_nonempty"][0]
    assert c["status"] == "pass", c


def test_coverage_rollups_mas_exempt_when_active_but_no_findings(tmp_path):
    """MASVS active but ZERO findings cite a MASVS id => exempt (no empty-rows penalty)."""
    dst = _copy_example(tmp_path)
    _mutate_data_js(dst, lambda d: d["meta"].__setitem__("active_taxonomies", ["masvs", "maswe"]))
    result = audit_report(dst)
    c = [x for x in result.checks if x["name"] == "coverage_rollups_nonempty"][0]
    assert c["status"] == "pass", c


def test_coverage_rollups_fail_when_masvs_active_cited_but_rows_empty(tmp_path):
    """MASVS active + a finding cites a MASVS id, but masvs_coverage rows are empty => FAIL."""
    dst = _copy_example(tmp_path)

    def _mut(d):
        d["meta"]["active_taxonomies"] = ["masvs", "maswe"]
        d["findings"][0].setdefault("control_mappings", {})["masvs"] = ["MASVS-STORAGE-1"]
        d["taxonomy"]["MASVS-STORAGE-1"] = {"family": "OWASP MASVS", "title": "Secure storage."}
        d["masvs_coverage"] = []  # rendered rollup dropped
    _mutate_data_js(dst, _mut)
    result = audit_report(dst)
    c = [x for x in result.checks if x["name"] == "coverage_rollups_nonempty"][0]
    assert c["status"] == "fail", c
    assert "masvs" in c["detail"]
    assert result.status == "fail"


def test_coverage_rollups_fail_when_maswe_active_cited_but_rows_empty(tmp_path):
    """MASWE active + a finding cites a MASWE id, but maswe_coverage rows are empty => FAIL."""
    dst = _copy_example(tmp_path)

    def _mut(d):
        d["meta"]["active_taxonomies"] = ["masvs", "maswe"]
        d["findings"][0].setdefault("control_mappings", {})["maswe"] = ["MASWE-0001"]
        d["taxonomy"]["MASWE-0001"] = {"family": "OWASP MASWE", "title": "Sensitive data stored unencrypted."}
        d["maswe_coverage"] = []
    _mutate_data_js(dst, _mut)
    result = audit_report(dst)
    c = [x for x in result.checks if x["name"] == "coverage_rollups_nonempty"][0]
    assert c["status"] == "fail", c
    assert "maswe" in c["detail"]


def test_coverage_rollups_pass_when_mas_active_cited_and_rows_present(tmp_path):
    """MASVS+MASWE active + cited + non-empty rendered rows => PASS."""
    dst = _copy_example(tmp_path)

    def _mut(d):
        d["meta"]["active_taxonomies"] = ["masvs", "maswe"]
        cm = d["findings"][0].setdefault("control_mappings", {})
        cm["masvs"] = ["MASVS-STORAGE-1"]
        cm["maswe"] = ["MASWE-0001"]
        d["taxonomy"]["MASVS-STORAGE-1"] = {"family": "OWASP MASVS", "title": "Secure storage."}
        d["taxonomy"]["MASWE-0001"] = {"family": "OWASP MASWE", "title": "Sensitive data unencrypted."}
        d["masvs_coverage"] = [{"masvs_id": "MASVS-STORAGE-1", "finding_count": 1}]
        d["maswe_coverage"] = [{"maswe_id": "MASWE-0001", "finding_count": 1}]
    _mutate_data_js(dst, _mut)
    result = audit_report(dst)
    c = [x for x in result.checks if x["name"] == "coverage_rollups_nonempty"][0]
    assert c["status"] == "pass", c
```
- [ ] **Step 2: Run test to verify it fails**
Run: `python3 -m pytest tests/test_cli_audit_report.py -k "coverage_rollups" -q`
Expected: FAIL — `test_coverage_rollups_fail_when_masvs_active_cited_but_rows_empty` / `_maswe_` assert FAIL but the current check ignores MAS and returns pass; "masvs"/"maswe" absent from detail.

- [ ] **Step 3: Extend coverage_rollups_nonempty with the MAS active+cited gate**
Current code (audit.py lines 348-361):
```python
    # Completeness check #6b — coverage rollups (structural; per design spec):
    # rendered rollups must be non-empty when the authoritative coverage YAML has rows.
    _nr = parsed.get("nist_rollup")
    nist_rollup = _nr if isinstance(_nr, list) else []
    _ae = parsed.get("attack_exposure")
    attack_exposure = _ae if isinstance(_ae, list) else []
    rollups_ok = is_empty_run or (
        (len(nist) == 0 or len(nist_rollup) > 0)
        and (len(attack) == 0 or len(attack_exposure) > 0)
    )
    _check(result, "coverage_rollups_nonempty", rollups_ok,
           f"nist_controls={len(nist)} nist_rollup_rows={len(nist_rollup)} "
           f"attack_techniques={len(attack)} attack_exposure_rows={len(attack_exposure)}",
           klass="structural")
```
Replace with (adds the MAS clause; reuses _cited_mas_ids defined in the id_coverage_masvs block above — both blocks run within audit_report):
```python
    # Completeness check #6b — coverage rollups (structural; per design spec):
    # rendered rollups must be non-empty when the authoritative coverage YAML has rows.
    _nr = parsed.get("nist_rollup")
    nist_rollup = _nr if isinstance(_nr, list) else []
    _ae = parsed.get("attack_exposure")
    attack_exposure = _ae if isinstance(_ae, list) else []
    # OWASP MAS extension: when a taxonomy is active (lifted into
    # meta.active_taxonomies from run-config) AND at least one finding cites a
    # MAS id, the corresponding rendered coverage rows MUST be present. Zero
    # cited ids stays exempt (a MAS-active run with no mobile findings is fine).
    _at_raw = meta.get("active_taxonomies")
    active_taxonomies = {str(t) for t in _at_raw} if isinstance(_at_raw, list) else set()
    _masvs_cov = parsed.get("masvs_coverage")
    masvs_cov = _masvs_cov if isinstance(_masvs_cov, list) else []
    _maswe_cov = parsed.get("maswe_coverage")
    maswe_cov = _maswe_cov if isinstance(_maswe_cov, list) else []
    masvs_gated = "masvs" in active_taxonomies and bool(masvs_cited)
    maswe_gated = "maswe" in active_taxonomies and bool(maswe_cited)
    rollups_ok = is_empty_run or (
        (len(nist) == 0 or len(nist_rollup) > 0)
        and (len(attack) == 0 or len(attack_exposure) > 0)
        and (not masvs_gated or len(masvs_cov) > 0)
        and (not maswe_gated or len(maswe_cov) > 0)
    )
    _check(result, "coverage_rollups_nonempty", rollups_ok,
           f"nist_controls={len(nist)} nist_rollup_rows={len(nist_rollup)} "
           f"attack_techniques={len(attack)} attack_exposure_rows={len(attack_exposure)} "
           f"masvs_active={'masvs' in active_taxonomies} masvs_cited={len(masvs_cited)} "
           f"masvs_rows={len(masvs_cov)} "
           f"maswe_active={'maswe' in active_taxonomies} maswe_cited={len(maswe_cited)} "
           f"maswe_rows={len(maswe_cov)}",
           klass="structural")
```
- [ ] **Step 4: Run test to verify it passes**
Run: `python3 -m pytest tests/test_cli_audit_report.py -k "coverage_rollups" -q`
Expected: PASS (existing 3 + new 5).

- [ ] **Step 5: Commit**
```bash
git add tools/apd_gauntlet/synthesis/audit.py tests/test_cli_audit_report.py
git commit -m "feat(audit): gate coverage_rollups_nonempty on MAS rows when active+cited

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 56: Taxonomy accessor maswe_masvs_parents() for the consistency lint

**Files:**
- Modify: `tools/apd_gauntlet/report/taxonomy.py:96-107`
- Test: `tests/test_taxonomy_mas.py`

- [ ] **Step 1: Write the failing test**
```python
# tests/test_taxonomy_mas.py
"""maswe_masvs_parents() — {MASWE-NNNN: [MASVS-...]} projection of maswe.json."""
from __future__ import annotations

from apd_gauntlet.report import taxonomy


def test_maswe_masvs_parents_accessor_shape() -> None:
    parents = taxonomy.maswe_masvs_parents()
    assert isinstance(parents, dict)
    # Every value is a list of MASVS-* control ids.
    for weakness_id, masvs_ids in parents.items():
        assert weakness_id.startswith("MASWE-")
        assert isinstance(masvs_ids, list)
        for mid in masvs_ids:
            assert mid.startswith("MASVS-")
    # MASWE-0001 maps to its masvs_v2 parents per the bundled catalog.
    assert parents.get("MASWE-0001"), "MASWE-0001 must carry masvs_v2 parents"


def test_maswe_masvs_parents_is_empty_dict_when_catalog_absent(monkeypatch, tmp_path) -> None:
    # Point the loader at a dir with no maswe.json; loader degrades to {}.
    monkeypatch.setattr(taxonomy, "_PKG_DATA", tmp_path)
    taxonomy.maswe_masvs_parents.cache_clear()
    assert taxonomy.maswe_masvs_parents() == {}
    taxonomy.maswe_masvs_parents.cache_clear()
```
- [ ] **Step 2: Run test to verify it fails**
Run: `python3 -m pytest tests/test_taxonomy_mas.py -q`
Expected: FAIL with "AttributeError: module 'apd_gauntlet.report.taxonomy' has no attribute 'maswe_masvs_parents'".

- [ ] **Step 3: Add maswe_masvs_parents() after cwe_abstractions()**
Current code ends the cwe block at taxonomy.py lines 96-107:
```python
@_register_cached
@lru_cache(maxsize=1)
def cwe_abstractions() -> dict[str, str]:
    """Return {CWE-NNN: abstraction} for all entries in cwe.json.

    Abstraction is one of category/pillar/class/base/variant/compound (or "" when
    the source carries none). Projection of the single :func:`_cwe_catalog`
    loader so it cannot drift from :func:`cwe_titles`. Consumed by the G6
    CWE-resolves guardrail in ``linters.check_cwe_resolves``.
    """
    return {cid: e["abstraction"] for cid, e in _cwe_catalog().items()}
```
Insert immediately after it:
```python
@_register_cached
@lru_cache(maxsize=1)
def maswe_masvs_parents() -> dict[str, list[str]]:
    """Return {MASWE-NNNN: [MASVS-...]} from the bundled maswe.json.

    Each weakness in maswe.json carries a ``masvs_v2`` list naming the MASVS v2
    controls it maps to. Consumed by the ``check_maswe_masvs_consistency`` lint
    so a finding's cited maswe parents can be reconciled with its cited masvs
    ids. Defensive: returns {} when the catalog is missing or unparseable so
    the lint degrades to a no-op rather than raising.
    """
    path = _PKG_DATA / "maswe.json"
    if not path.is_file():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    weaknesses = raw.get("weaknesses") if isinstance(raw, dict) else None
    out: dict[str, list[str]] = {}
    if isinstance(weaknesses, dict):
        for wid, entry in weaknesses.items():
            if not isinstance(entry, dict):
                continue
            parents = entry.get("masvs_v2")
            out[str(wid)] = [str(p) for p in parents if p] if isinstance(parents, list) else []
    return out
```
- [ ] **Step 4: Run test to verify it passes**
Run: `python3 -m pytest tests/test_taxonomy_mas.py -q`
Expected: PASS (2 tests).

- [ ] **Step 5: Commit**
```bash
git add tools/apd_gauntlet/report/taxonomy.py tests/test_taxonomy_mas.py
git commit -m "feat(taxonomy): maswe_masvs_parents() accessor over maswe.json masvs_v2

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 57: Linter check_maswe_masvs_consistency (warn) wired into validate.py

**Files:**
- Modify: `tools/apd_gauntlet/linters.py:164-173`
- Modify: `tools/apd_gauntlet/validate.py:456-457`
- Test: `tests/test_validate_maswe_masvs_consistency.py`

- [ ] **Step 1: Write the failing test**
```python
# tests/test_validate_maswe_masvs_consistency.py
"""check_maswe_masvs_consistency — WARN when a cited maswe's masvs_v2 parents
disagree with the finding's cited masvs ids."""
from __future__ import annotations

from apd_gauntlet import linters

# Synthetic parents index (mirrors taxonomy.maswe_masvs_parents()'s shape).
_PARENTS = {
    "MASWE-0001": ["MASVS-STORAGE-2"],
    "MASWE-0002": ["MASVS-STORAGE-1", "MASVS-CRYPTO-2"],
}


def test_consistent_pair_no_warning() -> None:
    """maswe parents fully covered by the cited masvs ids => no warning."""
    record = {"control_mappings": {"maswe": ["MASWE-0001"], "masvs": ["MASVS-STORAGE-2"]}}
    assert linters.check_maswe_masvs_consistency(record, _PARENTS) == []


def test_inconsistent_pair_warns() -> None:
    """A cited maswe whose masvs_v2 parent is NOT among the cited masvs ids => warn."""
    record = {"control_mappings": {"maswe": ["MASWE-0001"], "masvs": ["MASVS-CRYPTO-2"]}}
    warnings = linters.check_maswe_masvs_consistency(record, _PARENTS)
    assert len(warnings) == 1
    assert "MASWE-0001" in warnings[0]
    assert "MASVS-STORAGE-2" in warnings[0]  # the unmet parent is named


def test_no_masvs_cited_warns_with_expected_parents() -> None:
    """maswe cited but no masvs cited at all => warn (the parents are unmet)."""
    record = {"control_mappings": {"maswe": ["MASWE-0002"]}}
    warnings = linters.check_maswe_masvs_consistency(record, _PARENTS)
    assert len(warnings) == 1
    assert "MASWE-0002" in warnings[0]


def test_unknown_maswe_id_no_warning() -> None:
    """A maswe id absent from the parents index is not graded here (id_coverage owns it)."""
    record = {"control_mappings": {"maswe": ["MASWE-9999"], "masvs": ["MASVS-AUTH-1"]}}
    assert linters.check_maswe_masvs_consistency(record, _PARENTS) == []


def test_no_maswe_block_no_warning() -> None:
    assert linters.check_maswe_masvs_consistency({}, _PARENTS) == []
    assert linters.check_maswe_masvs_consistency(
        {"control_mappings": {"masvs": ["MASVS-STORAGE-2"]}}, _PARENTS) == []


def test_wired_into_semantic_pass_as_warning(tmp_path) -> None:
    """The check runs in run_semantic_pass on findings and lands in warnings, not errors."""
    import pathlib
    import shutil

    from apd_gauntlet import validate

    fixtures = pathlib.Path(__file__).parent / "fixtures" / "runs"
    dst = tmp_path / "run"
    shutil.copytree(fixtures / "clean-run", dst)
    f = dst / "10-trustworthiness" / "confidentiality.findings.yaml"
    text = f.read_text()
    assert "nist_800_53r5:" in text
    # Cite a maswe with a masvs parent that is NOT among the finding's masvs ids.
    text = text.replace(
        'nist_800_53r5: ["SC-8(1)", "SC-13", "SC-28(1)"]',
        'nist_800_53r5: ["SC-8(1)", "SC-13", "SC-28(1)"]\n'
        '    maswe: ["MASWE-0001"]\n'
        '    masvs: ["MASVS-CRYPTO-2"]',
        1,
    )
    f.write_text(text)
    report = validate.run_semantic_pass(dst)
    msgs = [v.message for v in report.warnings]
    assert any("MASWE-0001" in m and "masvs" in m.lower() for m in msgs), msgs
    # It is a warning, not a hard error.
    assert not any("MASWE-0001" in v.message for v in report.errors)
```
- [ ] **Step 2: Run test to verify it fails**
Run: `python3 -m pytest tests/test_validate_maswe_masvs_consistency.py -q`
Expected: FAIL with "AttributeError: module 'apd_gauntlet.linters' has no attribute 'check_maswe_masvs_consistency'".

- [ ] **Step 3a: Add check_maswe_masvs_consistency to linters.py**
Insert after `check_hedge_words_in_attack_rationale` (linters.py lines 164-173), before `check_d3fend_counters_attack`:
```python
def check_maswe_masvs_consistency(
    record: dict[str, Any], maswe_parents: dict[str, list[str]]
) -> list[str]:
    """WARNING-level: a finding's cited ``maswe`` ids should be consistent with
    its cited ``masvs`` ids.

    Each MASWE weakness declares ``masvs_v2`` parent controls in maswe.json
    (passed in as ``maswe_parents`` = {MASWE-NNNN: [MASVS-...]}). When a finding
    cites a maswe whose parent control(s) are NONE of the finding's cited masvs
    ids, the mapping is likely incomplete or mismatched — warn so the author can
    add the parent control or correct the weakness id. A maswe id that is ABSENT
    from ``maswe_parents`` is not graded here (id_coverage_maswe owns unknown
    ids); a maswe with an EMPTY parent list is exempt (no constraint to check).
    Returns ``[]`` when no ``maswe`` is cited.
    """
    warnings: list[str] = []
    control_mappings = record.get("control_mappings") or {}
    maswe_ids = control_mappings.get("maswe") or []
    if not maswe_ids:
        return warnings
    cited_masvs = {str(m) for m in (control_mappings.get("masvs") or [])}
    for wid in maswe_ids:
        expected = maswe_parents.get(str(wid))
        if not expected:  # unknown id or no declared parents -> not graded here
            continue
        if not (set(expected) & cited_masvs):
            warnings.append(
                f"control_mappings.maswe {wid!r} maps to MASVS {sorted(expected)} "
                f"(per maswe.json masvs_v2), but the finding cites masvs "
                f"{sorted(cited_masvs) or 'none'}; add the parent MASVS control or "
                f"correct the weakness id"
            )
    return warnings
```
- [ ] **Step 3b: Wire it into run_semantic_pass as a warning**
Current code (validate.py lines 456-457, inside the `if kind == "finding":` block):
```python
            for msg in linters.check_hedge_words_in_attack_rationale(record):
                report.warnings.append(Violation(path, rid, msg))
```
Add the loader near the existing `cwe_index` build (validate.py line 440) and a new warning loop. First, after line 440:
```python
    cwe_index = _taxonomy.cwe_abstractions()
    maswe_parents = _taxonomy.maswe_masvs_parents()
```
Then, immediately after the hedge-words warning loop:
```python
            for msg in linters.check_hedge_words_in_attack_rationale(record):
                report.warnings.append(Violation(path, rid, msg))
            for msg in linters.check_maswe_masvs_consistency(record, maswe_parents):
                report.warnings.append(Violation(path, rid, msg))
```
- [ ] **Step 4: Run test to verify it passes**
Run: `python3 -m pytest tests/test_validate_maswe_masvs_consistency.py -q`
Expected: PASS (6 tests).

- [ ] **Step 5: Commit**
```bash
git add tools/apd_gauntlet/linters.py tools/apd_gauntlet/validate.py tests/test_validate_maswe_masvs_consistency.py
git commit -m "feat(linters): warn-level MASWE->MASVS consistency lint, wired into semantic pass

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 58: Regression — full audit + linter suite stays green on the shipped example

**Files:**
- Test: `tests/test_cli_audit_report.py`

- [ ] **Step 1: Write the failing test**
```python
# Append to tests/test_cli_audit_report.py.

def test_completeness_gate_emits_all_mas_checks_and_stays_green(tmp_path):
    """The committed example cites no MAS ids and declares no active MAS taxonomy,
    so the new checks are emitted AND pass, leaving overall status pass."""
    dst = _copy_example(tmp_path)
    build = CliRunner().invoke(main, ["build-report", str(dst), "--quiet"])
    assert build.exit_code == 0, build.output
    result = audit_report(dst)
    failed = [c for c in result.checks if c["status"] == "fail"]
    assert result.status == "pass", failed
    names = {c["name"] for c in result.checks}
    for expected in ("id_coverage_masvs", "id_coverage_maswe", "coverage_rollups_nonempty"):
        assert expected in names, f"missing check {expected}"
    # Every check still carries a valid klass.
    for c in result.checks:
        assert c["klass"] in ("structural", "editorial"), c
```
- [ ] **Step 2: Run test to verify it fails**
Run: `python3 -m pytest tests/test_cli_audit_report.py::test_completeness_gate_emits_all_mas_checks_and_stays_green -q`
Expected: PASS if prior tasks landed; if run BEFORE Task 1/2, FAIL with "missing check id_coverage_masvs". (Confirms the regression test depends on the new checks existing.)

- [ ] **Step 3: No implementation — this task is the green-bar gate**
Run the full audit + new linter suites together to confirm no regression:
```bash
python3 -m pytest tests/test_cli_audit_report.py tests/test_taxonomy_mas.py \
  tests/test_validate_maswe_masvs_consistency.py tests/test_validate_cwe_resolves.py -q
```
- [ ] **Step 4: Run test to verify it passes**
Run: `python3 -m pytest tests/test_cli_audit_report.py -q && python3 -m ruff check tools/apd_gauntlet/synthesis/audit.py tools/apd_gauntlet/linters.py tools/apd_gauntlet/validate.py tools/apd_gauntlet/report/taxonomy.py`
Expected: PASS (all audit tests green; ruff clean).

- [ ] **Step 5: Commit**
```bash
git add tests/test_cli_audit_report.py
git commit -m "test(audit): regression guard — MAS checks emitted + green on shipped example

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---


## Phase 9 — Docs, ADR-0014 & version bump (1.6.0 → 1.7.0)

### Task 59: Bump package version 1.6.0 -> 1.7.0 (pyproject + plugin + __init__)

**Files:**
- Modify: `pyproject.toml:7`
- Modify: `plugin.json:3`
- Modify: `tools/apd_gauntlet/__init__.py:2`
- Test: `tests/test_workflow_apd_gauntlet.py:235-240`

- [ ] **Step 1: Update the failing skew test to expect 1.7.0**
The existing test pins `plugin.json` to the literal `"1.6.0"`. Edit it to assert `1.7.0` so it fails red until the bump lands. Current code at `tests/test_workflow_apd_gauntlet.py:235-240`:
```python
def test_plugin_manifest_version_is_1_6_0() -> None:
    """plugin.json must report version 1.6.0 (matches pyproject; closes skew gap)."""
    manifest = json.loads(PLUGIN_MANIFEST.read_text(encoding="utf-8"))
    assert manifest["version"] == "1.6.0", (
        f"plugin.json version is {manifest['version']!r}; expected '1.6.0'"
    )
```
Replace with a version-skew assertion that derives the expected value from `pyproject.toml` (so the three locations can never drift again), plus a literal floor of `1.7.0`:
```python
def test_plugin_manifest_version_matches_pyproject() -> None:
    """plugin.json, pyproject.toml, and tools/apd_gauntlet/__init__ must agree (no skew)."""
    import re

    manifest = json.loads(PLUGIN_MANIFEST.read_text(encoding="utf-8"))
    pyproject = (REPO / "pyproject.toml").read_text(encoding="utf-8")
    py_version = re.search(r'(?m)^version = "([^"]+)"', pyproject).group(1)
    init_text = (REPO / "tools" / "apd_gauntlet" / "__init__.py").read_text(encoding="utf-8")
    init_version = re.search(r'__version__ = "([^"]+)"', init_text).group(1)

    assert manifest["version"] == py_version, (
        f"plugin.json version is {manifest['version']!r}; pyproject is {py_version!r}"
    )
    assert init_version == py_version, (
        f"__init__ version is {init_version!r}; pyproject is {py_version!r}"
    )
    assert py_version == "1.7.0", (
        f"expected the 1.7.0 release version; pyproject reports {py_version!r}"
    )
```

- [ ] **Step 2: Run test to verify it fails**
Run: `python -m pytest tests/test_workflow_apd_gauntlet.py::test_plugin_manifest_version_matches_pyproject -q`
Expected: FAIL with `AssertionError: expected the 1.7.0 release version; pyproject reports '1.6.0'`

- [ ] **Step 3: Bump all three version locations to 1.7.0**
`pyproject.toml:7`:
```toml
version = "1.7.0"
```
`plugin.json:3`:
```json
  "version": "1.7.0",
```
`tools/apd_gauntlet/__init__.py:2`:
```python
__version__ = "1.7.0"
```

- [ ] **Step 4: Run test to verify it passes**
Run: `python -m pytest tests/test_workflow_apd_gauntlet.py::test_plugin_manifest_version_matches_pyproject -q`
Expected: PASS

- [ ] **Step 5: Commit**
```bash
git add pyproject.toml plugin.json tools/apd_gauntlet/__init__.py tests/test_workflow_apd_gauntlet.py
git commit -m "chore(release): bump 1.6.0 -> 1.7.0 + harden version-skew test to derive from pyproject"
```

---

### Task 60: Write ADR-0014 (OWASP MAS mobile taxonomy)

**Files:**
- Create: `docs/adrs/0014-owasp-mas-mobile-taxonomy.md`
- Test: (gate) markdownlint over the new ADR

- [ ] **Step 1: Write the failing test (the markdownlint gate must run before the file exists, then over it)**
Run the exact CI glob set scoped to the ADR directory so a malformed ADR fails. With the file absent the lint passes vacuously, so instead first create a stub that violates a rule (no top-level H1) to confirm the gate is wired:
Run: `npx --yes markdownlint-cli2 "docs/adrs/0014-owasp-mas-mobile-taxonomy.md"`
Expected (before Step 3, with a stub missing its `# ` heading): FAIL with `MD041/first-line-heading/first-line-h1`

- [ ] **Step 2: (covered by Step 1)**
The lint command in Step 1 is the failing check.

- [ ] **Step 3: Write the ADR**
Mirror the section structure of `docs/adrs/0012-mitre-atlas-finding-taxonomy.md` (Status/Date/Supersedes header, Context, Decision with bolded sub-decisions, Alternatives considered, Consequences).
```markdown
# ADR-0014: OWASP MAS (MASVS + MASWE) as Mobile Finding/Capability Taxonomies

**Status:** Accepted
**Date:** 2026-06-09
**Supersedes:** —
**Superseded by:** —

## Context

APD Gauntlet v1.7.0 ships the `mobile-applications` domain pack, which targets
the adversary-controlled-client surface: on-device storage, keystore/TEE, TLS
pinning, WebView/JS bridges, deep-link/IPC, in-process SDKs, reverse-engineering
resilience, and hardware attestation. The control and weakness vocabulary the
mobile-security community uses for this surface is the **OWASP Mobile Application
Security (MAS)** project: **MASVS** (the verification standard — eight control
categories: Storage, Crypto, Auth, Network, Platform, Code, Resilience, Privacy)
and **MASWE** (the weakness enumeration that maps each weakness to a MASVS v2
control and, where applicable, to CWE).

Neither MITRE ATT&CK (Enterprise or Mobile) nor MITRE ATLAS expresses the
client-side verification requirements MASVS catalogs, and CWE — while it covers
many underlying weakness classes — does not carry the mobile-specific
verification framing (e.g. "MASVS-RESILIENCE-2: the app implements anti-tampering
mechanisms") that a mobile reviewer expects to see. Without MASVS/MASWE IDs,
`mobile-applications` findings can express the mobile control gap only in prose,
losing the structured cross-referencing and coverage rollups that taxonomy IDs
enable.

ADR-0008 codified the multi-framework taxonomy approach (per-run-scoped IDs in
`control_mappings`, coverage rollups synthesized from them, reference data via a
`refresh-*` verb), and ADR-0012 extended it to a findings-only offensive catalog
(ATLAS). MAS sits across both halves of the finding/capability split: a MASVS
control is a *verification requirement* a capability can satisfy and a finding
can flag as unmet, so MASVS belongs on **both** findings and capabilities; MASWE
is a *weakness* catalog — what is wrong — so it belongs on **findings only**,
parallel to ATLAS.

## Decision

Adopt **OWASP MASVS and MASWE as per-run-scoped mobile taxonomies**, extending
the multi-framework taxonomy-mapping approach of ADR-0008 and ADR-0012.

**Schema placement.** Specialists emit MASVS control IDs in
`control_mappings.masvs` and MASWE weakness IDs in `control_mappings.maswe`, both
as flat ID lists (the CWE/OWASP/ATLAS shape, not the dict-with-rationale ATT&CK
shape). `masvs` appears on **both** findings and capabilities; `maswe` is
**findings-only**. The `$defs` add `maswe_id` (`^MASWE-[0-9]{4}$`),
`masvs_control_id`
(`^MASVS-(STORAGE|CRYPTO|AUTH|NETWORK|PLATFORM|CODE|RESILIENCE|PRIVACY)-[1-9][0-9]*$`),
and `masvs_category_id`
(`^MASVS-(STORAGE|CRYPTO|AUTH|NETWORK|PLATFORM|CODE|RESILIENCE|PRIVACY)$`).

**Activation by pack declaration, then auto-seed.** Unlike ATLAS (declared
directly in `.apd-run.yaml`), MAS activates through the domain pack: a pack
declares a top-level optional `taxonomies:` array in `domain.yaml`, and the
`mobile-applications` pack declares `taxonomies: [masvs, maswe]`. At `init-run`,
the selected packs' declared taxonomies are unioned into the run-config
`taxonomies:` list (pack -> run auto-seed), so an operator who selects
`--domain mobile-applications` gets MASVS/MASWE in scope without naming them.
The operator can still add or remove taxonomies in `.apd-run.yaml` afterward.
Default-off for every other pack.

**Reference data.** Two bundled catalogs ship with the gauntlet:
`tools/apd_gauntlet/data/masvs.json` (MASVS v2.1.0 controls, keyed by control
ID, carrying title + category + category title) and
`tools/apd_gauntlet/data/maswe.json` (MASWE weaknesses, keyed by weakness ID,
carrying title + filing category + status + parent MASVS v2 controls + CWE
list). A new `apd-gauntlet refresh-mas` verb refreshes both in one pass.

**URL resolution.** `masvs_url(control_id)` is pure-regex and resolves to
`https://mas.owasp.org/MASVS/controls/{id}/` with no catalog read.
`maswe_url(weakness_id)` reads `maswe.json` for the weakness's filing category
and resolves to `https://mas.owasp.org/MASWE/{category}/{id}/`, returning `None`
when the category is unknown.

**Coverage rollups.** Two gated synthesis rollups are emitted when the matching
taxonomy is declared and at least one record cites it:
`40-synthesis/masvs-coverage.yaml` (controls with finding/capability counts,
surfaces, and a `posture` from `coverage_logic.posture()`) and
`40-synthesis/maswe-coverage.yaml` (weaknesses with finding counts and parent
MASVS controls). New single-file schemas `masvs-coverage.schema.json` and
`maswe-coverage.schema.json` (no `-doc` wrapper, the `cwe-coverage.schema.json`
convention) register directly in `validate.py`'s `SYNTHESIS_ROLLUPS`. The report
surfaces them as the **"OWASP MASVS"** and **"OWASP MASWE"** taxonomy families
in two Coverage sub-tabs.

**MASWE-Beta pinning.** MASWE is published as a Beta enumeration. The bundled
`maswe.json` records the upstream `commit` it was projected from in `_meta`, and
each weakness carries its `status` (e.g. `new`). The catalog is pinned to a
specific upstream commit per refresh; we do not track the moving Beta tip
silently. Refresh cadence follows the quarterly pattern of the other `refresh-*`
verbs.

## Alternatives considered

### MASVS/MASWE in narrative prose only (no structured field)

**Rejected.** Prose references cannot drive coverage rollups, the
`taxonomy_titles_resolve` audit check, or the report's taxonomy family
rendering. Structured `control_mappings.masvs`/`.maswe` enables all three and is
additive within `control_mappings`, consistent with ADR-0008's additive-only
policy.

### Fold MASWE into CWE (map mobile weaknesses to their CWE parents only)

**Rejected.** Many MASWE weaknesses carry a CWE list, but the mobile-verification
framing (which MASVS control the weakness violates) is exactly what a mobile
reviewer needs and what CWE does not express. Keeping MASWE first-class preserves
the MASWE -> MASVS-v2 linkage in `maswe.json` that the rollup uses.

### MASVS findings-only, like ATLAS

**Rejected.** A MASVS control is a verification requirement, not an attack
technique. A capability that implements (say) certificate pinning *satisfies*
MASVS-NETWORK; recording that on the capability is exactly the
defensive-coverage signal the coverage rollup needs. Restricting MASVS to
findings would discard the capability-side coverage. MASWE, by contrast, is
weakness-only and stays findings-only.

### Declare MAS directly in `.apd-run.yaml` (like ATLAS), no pack auto-seed

**Rejected.** MASVS/MASWE are relevant precisely when the
`mobile-applications` pack is in scope. Auto-seeding the taxonomies from the
pack's `domain.yaml` removes a manual step that an operator would otherwise have
to remember, while still allowing explicit override. ATLAS pre-dates the pack
`taxonomies:` field; the auto-seed is the new general mechanism and ATLAS-style
direct declaration remains supported.

## Consequences

- Mobile findings and capabilities carry precise MASVS control IDs and (findings)
  MASWE weakness IDs rather than prose; the `masvs-coverage` and `maswe-coverage`
  rollups quantify which controls and weaknesses the run addresses.
- Schema additions are fully additive within v1.x: `control_mappings.masvs` (on
  findings and capabilities) and `control_mappings.maswe` (findings) are new
  optional arrays. v1.6-format findings validate unchanged against v1.7 schemas.
- A new top-level optional `taxonomies:` field on `domain.yaml` lets any pack
  declare its default taxonomies; `init-run` unions them into the run config.
  Packs that omit the field are unaffected.
- `report-audit.yaml` gains `id_coverage_masvs` and `id_coverage_maswe` checks,
  and `coverage_rollups_nonempty` extends to the MAS rollups when MAS is active
  and cited. Runs without MAS in scope are exempt.
- A new `refresh-mas` CLI verb and the `masvs.json`/`maswe.json` catalogs join
  the quarterly refresh cadence. Operators who never select the
  `mobile-applications` pack (or never declare `masvs`/`maswe`) are unaffected.
- MASWE is pinned per refresh to an upstream commit recorded in `_meta.commit`;
  the Beta status is surfaced per weakness so consumers can see which weaknesses
  are provisional.
```

- [ ] **Step 4: Run the lint over the ADR to verify it passes**
Run: `npx --yes markdownlint-cli2 "docs/adrs/0014-owasp-mas-mobile-taxonomy.md"`
Expected: PASS (`markdownlint-cli2 ... Summary: 0 error(s)`)

- [ ] **Step 5: Commit**
```bash
git add docs/adrs/0014-owasp-mas-mobile-taxonomy.md
git commit -m "docs(adr): add ADR-0014 OWASP MAS (MASVS+MASWE) mobile taxonomy"
```

---

### Task 61: Extend taxonomy-mappings.md (MASVS/MASWE rows, URLs, rollups, refresh-mas)

**Files:**
- Modify: `docs/taxonomy-mappings.md:3` (intro), `:18` (table), `:58` (discipline), `:96-118` (rollups + refresh), `:120-125` (data state)
- Test: (gate) markdownlint over the doc

- [ ] **Step 1: Write the failing test (assert the new content is present)**
Run: `grep -q "MASVS" docs/taxonomy-mappings.md && grep -q "refresh-mas" docs/taxonomy-mappings.md && echo FOUND || echo MISSING`
Expected: `MISSING`

- [ ] **Step 2: (covered by Step 1)**
The grep is the failing check.

- [ ] **Step 3: Add the MAS rows, discipline, rollup, and refresh content**
Intro line, current `docs/taxonomy-mappings.md:3` ends `...adversarial-ML threat coverage.`:
```markdown
As of v1.7, OWASP MASVS (mobile verification controls) and OWASP MASWE (mobile weakness enumeration) are available as first-class mobile taxonomies, auto-seeded into a run's scope when the `mobile-applications` domain pack is selected.
```
(Append the sentence to the end of the existing line 3 paragraph.)

Add two rows to the "Which taxonomies, where, and why" table, after the MITRE ATLAS row at `:18`:
```markdown
| OWASP MASVS | findings + capabilities (optional, v1.7+) | Mobile security, app-vetting |
| OWASP MASWE | findings (optional, v1.7+) | Mobile security, AppSec |
```
After the ATLAS attachment note at `:22`, add:
```markdown
MASVS attaches to **both findings and capabilities** — a verification control a capability satisfies or a finding flags as unmet. MASWE attaches to **findings only** as a mobile weakness catalog, parallel to ATLAS. Both are auto-seeded from the `mobile-applications` pack's `domain.yaml` `taxonomies:` declaration (`[masvs, maswe]`) at `init-run`; operators may still adjust the run-config `taxonomies:` list afterward.
```
Add a MAS bullet to the Mapping discipline list, after the MITRE ATLAS bullet at `:58`:
```markdown
- **OWASP MASVS / MASWE** — map only when the SUT is (or includes) a mobile application. MASVS control IDs follow `MASVS-<CATEGORY>-<n>` (categories: STORAGE, CRYPTO, AUTH, NETWORK, PLATFORM, CODE, RESILIENCE, PRIVACY); MASWE IDs follow `MASWE-####`. MASVS on a capability means the control is satisfied; MASVS on a finding means it is unmet. Map a MASWE weakness to the specific weakness observed, not the broad category.
```
Add a new section after the MITRE ATLAS section (before `## Synthesizer rollups` at `:96`):
```markdown
## OWASP MASVS and MASWE

OWASP MAS is the mobile-security counterpart to the web/API/LLM OWASP catalogs. **MASVS** is the verification standard — eight control categories (Storage, Crypto, Auth, Network, Platform, Code, Resilience, Privacy). **MASWE** is the weakness enumeration; each MASWE weakness maps to a MASVS v2 control and, where applicable, to CWE.

### Schema shape

Both ride in `control_mappings` as flat ID lists. MASVS is on findings **and** capabilities; MASWE is findings-only:

\`\`\`yaml
control_mappings:
  nist_800_53r5: [SC-28, SC-13]
  masvs:
    - MASVS-STORAGE-1
    - MASVS-CRYPTO-1
  maswe:
    - MASWE-0001
\`\`\`

### ID format and URLs

- MASVS control: `MASVS-(STORAGE|CRYPTO|AUTH|NETWORK|PLATFORM|CODE|RESILIENCE|PRIVACY)-<n>` → `https://mas.owasp.org/MASVS/controls/{id}/` (resolved by `masvs_url()`, pure regex, no catalog read).
- MASWE weakness: `MASWE-####` → `https://mas.owasp.org/MASWE/{category}/{id}/`, where `{category}` is the weakness's filing category read from `maswe.json` (`maswe_url()`; returns `None` if the category is unknown).

### Declaring and refreshing

Selecting the `mobile-applications` pack auto-seeds `masvs` and `maswe` into `.apd-run.yaml`'s `taxonomies:` list. Refresh the two bundled catalogs in one pass:

\`\`\`bash
apd-gauntlet refresh-mas
\`\`\`

This writes `tools/apd_gauntlet/data/masvs.json` (MASVS v2.1.0 controls) and `tools/apd_gauntlet/data/maswe.json` (MASWE weaknesses, pinned to the upstream `commit` recorded in `_meta`). MASWE is a **Beta** enumeration; each weakness carries its `status`, and the catalog is pinned per refresh rather than tracking the moving tip.

### Coverage rollups

When `masvs` is declared, the synthesizer emits `40-synthesis/masvs-coverage.yaml` (schema: `masvs-coverage.schema.json`) — one entry per cited control with `finding_count`, `capability_count`, surfaces, and a `posture` from `coverage_logic.posture()`. When `maswe` is declared, it emits `40-synthesis/maswe-coverage.yaml` (schema: `maswe-coverage.schema.json`) — one entry per cited weakness with `finding_count`, the filing `category`/`status`, and the `parent_masvs` controls. The report renders these as the **"OWASP MASVS"** and **"OWASP MASWE"** taxonomy families in two Coverage sub-tabs.
```
In the `## Synthesizer rollups` list, after the `atlas-coverage.yaml` bullet at `:103`, add:
```markdown
- `40-synthesis/masvs-coverage.yaml` — MASVS controls cited by findings and capabilities, with per-control counts, surfaces, and posture. Only emitted when `masvs` is declared and at least one record carries a MASVS mapping.
- `40-synthesis/maswe-coverage.yaml` — MASWE weaknesses cited by findings, with finding counts, filing category/status, and parent MASVS controls. Only emitted when `maswe` is declared and at least one finding carries a MASWE mapping.
```
In the Reference-data refresh fenced block at `:111-116`, after `apd-gauntlet refresh-atlas`, add:
```bash
apd-gauntlet refresh-mas
```
Under "Current data state", bump the heading and append two entries (current `:120` reads `**Current data state (v1.6.0):**`):
```markdown
**Current data state (v1.7.0):**
```
And after the MITRE ATLAS line at `:125`:
```markdown
- OWASP MASVS: 24 controls across 8 categories, projected from MASVS v2.1.0
- OWASP MASWE: weakness enumeration (Beta), pinned per refresh to the upstream `commit` recorded in `maswe.json` `_meta`
```

- [ ] **Step 4: Run the doc lint to verify it passes**
Run: `npx --yes markdownlint-cli2 "docs/taxonomy-mappings.md" && grep -q "refresh-mas" docs/taxonomy-mappings.md && echo OK`
Expected: PASS, prints `OK`

- [ ] **Step 5: Commit**
```bash
git add docs/taxonomy-mappings.md
git commit -m "docs(taxonomy): document OWASP MASVS/MASWE mappings, rollups, refresh-mas"
```

---

### Task 62: Extend html-report.md (MAS families, Coverage sub-tabs, active_taxonomies, gate checks)

**Files:**
- Modify: `docs/html-report.md:14-21` (Coverage families), `:134-156` (gate checks), `:153-156` (pre-existing cross-checks)
- Test: (gate) markdownlint over the doc

- [ ] **Step 1: Write the failing test (assert the new content is present)**
Run: `grep -q "OWASP MASVS" docs/html-report.md && grep -q "active_taxonomies" docs/html-report.md && grep -q "id_coverage_masvs" docs/html-report.md && echo FOUND || echo MISSING`
Expected: `MISSING`

- [ ] **Step 2: (covered by Step 1)**
The grep is the failing check.

- [ ] **Step 3: Add the families, sub-tabs, active_taxonomies, and gate checks**
The Coverage-tab families paragraph, current `docs/html-report.md:14-21`:
```markdown
The Coverage tab renders taxonomy tooltips for every cited control or technique
ID. Tooltip families include NIST 800-53r5, MITRE ATT&CK, CWE, OWASP (web /
API / LLM), MITRE D3FEND, and — when `mitre_atlas` is declared for the run —
**MITRE ATLAS** (adversarial-ML techniques). A bare ID in a tooltip (title
equals the ID string) means the reference catalog for that family failed to
load; this is caught by the completeness gate's `taxonomy_titles_resolve` check.
```
Replace the `**MITRE ATLAS** (adversarial-ML techniques).` sentence-fragment so the families include MAS, and append a sub-tab note:
```markdown
The Coverage tab renders taxonomy tooltips for every cited control or technique
ID. Tooltip families include NIST 800-53r5, MITRE ATT&CK, CWE, OWASP (web /
API / LLM), MITRE D3FEND, — when `mitre_atlas` is declared for the run —
**MITRE ATLAS** (adversarial-ML techniques), and — when the
`mobile-applications` pack auto-seeds `masvs`/`maswe` — **OWASP MASVS** and
**OWASP MASWE** (mobile verification controls and weaknesses). A bare ID in a
tooltip (title equals the ID string) means the reference catalog for that family
failed to load; this is caught by the completeness gate's
`taxonomy_titles_resolve` check.

When `masvs` or `maswe` is active, the Coverage tab adds two sub-tabs — an
**OWASP MASVS** control-coverage view (sourced from
`40-synthesis/masvs-coverage.yaml`, one row per control with finding/capability
counts, surfaces, and a posture pill) and an **OWASP MASWE** weakness view
(sourced from `maswe-coverage.yaml`, one row per weakness with finding count,
filing category/status, and parent MASVS controls). Both sub-tabs are omitted
when the taxonomy is not active. The transform exposes the active taxonomy set
as `data.meta.active_taxonomies` (lifted from the run-config `taxonomies:`
list), which the Coverage tab reads to decide which family sub-tabs to render.
```
In the structural-checks list, after `coverage_rollups_nonempty` at `:147`, add:
```markdown
- `id_coverage_masvs` — every MASVS control cited on a finding or capability must
  appear in the rendered `masvs-coverage.yaml` (exempt when `masvs` is not active).
- `id_coverage_maswe` — every MASWE weakness cited on a finding must appear in the
  rendered `maswe-coverage.yaml` (exempt when `maswe` is not active).
```
Extend the `coverage_rollups_nonempty` line at `:146-147`:
```markdown
- `coverage_rollups_nonempty` — rendered NIST and ATT&CK rollups must be
  non-empty when the authoritative coverage YAMLs have rows; this also covers the
  MASVS and MASWE rollups when those taxonomies are active and cited.
```
Add the new checks to the "Pre-existing cross-checks" structural list at `:153-156`:
```markdown
Pre-existing cross-checks (`id_coverage_findings`, `id_coverage_capabilities`,
`id_coverage_nist`, `id_coverage_attack`, `id_coverage_masvs`,
`id_coverage_maswe`, `count_parity_severity`, `count_parity_totals`,
`nist_rollup_parity`, `data_js_recompute_drift`) are also structural.
```

- [ ] **Step 4: Run the doc lint to verify it passes**
Run: `npx --yes markdownlint-cli2 "docs/html-report.md" && grep -q "active_taxonomies" docs/html-report.md && echo OK`
Expected: PASS, prints `OK`

- [ ] **Step 5: Commit**
```bash
git add docs/html-report.md
git commit -m "docs(report): document MASVS/MASWE Coverage sub-tabs, active_taxonomies, MAS gate checks"
```

---

### Task 63: Extend adapting-to-other-domains.md (pack taxonomies field + auto-seed)

**Files:**
- Modify: `docs/adapting-to-other-domains.md:45-55` (domain.yaml schema), `:186-191` (§5 taxonomy discipline)
- Test: (gate) markdownlint over the doc

- [ ] **Step 1: Write the failing test (assert the new content is present)**
Run: `grep -q "taxonomies:" docs/adapting-to-other-domains.md && grep -qi "auto-seed" docs/adapting-to-other-domains.md && echo FOUND || echo MISSING`
Expected: `MISSING`

- [ ] **Step 2: (covered by Step 1)**
The grep is the failing check.

- [ ] **Step 3: Document the new pack `taxonomies` field and auto-seed**
The `domain.yaml` schema list, current `docs/adapting-to-other-domains.md:54-55`:
```markdown
- `includes` — at least one path, each with no leading `/` and no `..`; the runtime skill is assembled from these files.
- `regulatory_anchors` — a list of strings.
```
After the `regulatory_anchors` line add the optional-fields note:
```markdown
- `regulatory_anchors` — a list of strings.

There is also one optional top-level field beyond the three attack-path blocks:

- `taxonomies` — an optional array of taxonomy enum strings (e.g. `masvs`, `maswe`, `mitre_atlas`) the pack wants in scope by default. At `init-run`, the selected packs' declared taxonomies are unioned into the run-config `taxonomies:` list (pack -> run auto-seed), so an operator who selects the pack gets those taxonomies without naming them. The operator can still add or remove taxonomies in `.apd-run.yaml` afterward. The `mobile-applications` pack declares `taxonomies: [masvs, maswe]`; a pack that omits the field changes nothing about run scope.
```
In §5 "Taxonomy and mapping discipline" at `:191`, after the existing MITRE ATLAS / CSA MAESTRO paragraph, add:
```markdown
The `mobile-applications` pack additionally declares the **OWASP MASVS** and **OWASP MASWE** taxonomies via the optional `taxonomies: [masvs, maswe]` field in its `domain.yaml`, so selecting the pack auto-seeds both into the run's `taxonomies:` list. Mobile specialists emit `masvs` control IDs (on findings **and** capabilities) and `maswe` weakness IDs (findings only) in `control_mappings`, feeding the `masvs-coverage`/`maswe-coverage` synthesis rollups and the report's MASVS/MASWE Coverage sub-tabs; titles resolve via `apd-gauntlet refresh-mas`. As with CWE/ATT&CK/ATLAS, the actual MASVS/MASWE mapping is emitted on the finding or capability the specialist raises — not as bullet rows in the pattern markdown.
```

- [ ] **Step 4: Run the doc lint to verify it passes**
Run: `npx --yes markdownlint-cli2 "docs/adapting-to-other-domains.md" && grep -qi "auto-seed" docs/adapting-to-other-domains.md && echo OK`
Expected: PASS, prints `OK`

- [ ] **Step 5: Commit**
```bash
git add docs/adapting-to-other-domains.md
git commit -m "docs(domains): document optional domain.yaml taxonomies field + pack->run auto-seed"
```

---

### Task 64: Extend running-the-gauntlet.md (refresh-mas verb + MAS preflight)

**Files:**
- Modify: `docs/running-the-gauntlet.md:50` (CLI reference), `:134-144` (taxonomy scope), `:279` (preflight table row)
- Test: (gate) markdownlint over the doc

- [ ] **Step 1: Write the failing test (assert the new content is present)**
Run: `grep -q "refresh-mas" docs/running-the-gauntlet.md && echo FOUND || echo MISSING`
Expected: `MISSING`

- [ ] **Step 2: (covered by Step 1)**
The grep is the failing check.

- [ ] **Step 3: Add the refresh-mas verb, taxonomy-scope note, and preflight row**
In the CLI subcommand listing, after the `refresh-atlas` line at `:50`:
```
apd-gauntlet refresh-mas                         # refresh OWASP MASVS + MASWE mobile taxonomy reference data
```
In the "Taxonomy scope (v1.2+)" section, after the ATLAS paragraph at `:144`, add:
```markdown
Selecting the `mobile-applications` pack (`--domain mobile-applications`) auto-seeds the OWASP **MASVS** and **MASWE** mobile taxonomies into `.apd-run.yaml`'s `taxonomies:` list (declared as `taxonomies: [masvs, maswe]` in the pack's `domain.yaml`), so you do not name them explicitly:

\`\`\`yaml
taxonomies:
  - masvs   # auto-seeded by the mobile-applications pack
  - maswe   # auto-seeded by the mobile-applications pack
\`\`\`

Refresh the bundled MAS reference data with `apd-gauntlet refresh-mas`. When `masvs`/`maswe` are declared, the rollup phase includes MASVS and MASWE coverage summaries. See [docs/taxonomy-mappings.md](taxonomy-mappings.md) for the full operator guide.
```
Update the preflight "Declared taxonomy catalogs present" row at `:279`:
```markdown
| Declared taxonomy catalogs present | `apd-gauntlet refresh-{mitre,mitre-mobile,cwe,owasp,d3fend,atlas,mas}` as the `taxonomies:` list requires | conditional |
```

- [ ] **Step 4: Run the doc lint to verify it passes**
Run: `npx --yes markdownlint-cli2 "docs/running-the-gauntlet.md" && grep -q "refresh-mas" docs/running-the-gauntlet.md && echo OK`
Expected: PASS, prints `OK`

- [ ] **Step 5: Commit**
```bash
git add docs/running-the-gauntlet.md
git commit -m "docs(running): add refresh-mas verb, MAS taxonomy auto-seed note, preflight row"
```

---

### Task 65: Add CHANGELOG.md entry for v1.7.0 (MAS taxonomy + version bump)

**Files:**
- Modify: `CHANGELOG.md:5-21` (Unreleased) -> new `## v1.7.0` release heading
- Test: (gate) markdownlint over CHANGELOG (CI lints `CHANGELOG.md` in the same job)

- [ ] **Step 1: Write the failing test (assert the new entry is present)**
Run: `grep -q "OWASP MASVS / MASWE" CHANGELOG.md && grep -q "ADR 0014" CHANGELOG.md && echo FOUND || echo MISSING`
Expected: `MISSING`

- [ ] **Step 2: (covered by Step 1)**
The grep is the failing check.

- [ ] **Step 3: Convert the `## [Unreleased]` block to a `## v1.7.0` release and add MAS entries**
Current `CHANGELOG.md:5`:
```markdown
## [Unreleased]
```
Replace with a fresh empty Unreleased section above a new dated v1.7.0 release, and add the MAS Added entries at the top of v1.7.0's `### Added`:
```markdown
## [Unreleased]

## v1.7.0 — 2026-06-09

### Added

- **OWASP MASVS / MASWE as first-class mobile taxonomies** — the `mobile-applications` pack declares `taxonomies: [masvs, maswe]` in `domain.yaml`, auto-seeded into a run's `taxonomies:` at `init-run`. Specialists emit `masvs` control IDs (`MASVS-<CATEGORY>-<n>`, on findings **and** capabilities) and `maswe` weakness IDs (`MASWE-####`, findings-only) in `control_mappings`, feeding two new gated synthesis rollups (`masvs-coverage.yaml`, `maswe-coverage.yaml` + their single-file schemas) and two new Coverage sub-tabs in the HTML report. New `apd-gauntlet refresh-mas` verb + bundled `masvs.json` (v2.1.0, 24 controls) and `maswe.json` (Beta, pinned per-refresh to an upstream commit). `data.meta.active_taxonomies` now lifts the run's taxonomy scope; `audit-report` gains `id_coverage_masvs` / `id_coverage_maswe` structural checks and `coverage_rollups_nonempty` extends to the MAS rollups.
- **Optional `taxonomies` field on `domain.yaml`** — any pack can declare default taxonomies that `init-run` unions into the run config (pack -> run auto-seed). Packs that omit the field are unaffected.
- **ADR 0014** — OWASP MAS (MASVS + MASWE) as mobile finding/capability taxonomies.
```
(All the prior `## [Unreleased]` content at lines 7-33 — Added/Changed/Fixed bullets — moves under the new `## v1.7.0 — 2026-06-09` release block, after the three Added bullets above; the new `## [Unreleased]` heading sits empty at the top.)

- [ ] **Step 4: Run the CHANGELOG lint to verify it passes**
Run: `npx --yes markdownlint-cli2 "CHANGELOG.md" && grep -q "OWASP MASVS / MASWE" CHANGELOG.md && echo OK`
Expected: PASS, prints `OK`

- [ ] **Step 5: Commit**
```bash
git add CHANGELOG.md
git commit -m "docs(changelog): cut v1.7.0 — OWASP MASVS/MASWE mobile taxonomy + version bump"
```

---

### Task 66: Run the FULL CI markdownlint glob locally before push (warning gate)

**Files:**
- Test: (gate) the exact `markdownlint-cli2` glob set CI uses (`.github/workflows/markdown-lint.yml:16-23`)

WARNING: The project's CI `markdown-lint` job lints the entire `docs/**` tree (plus `.claude/**`, `domains/**`, `README.md`, `CONTRIBUTING.md`, `CHANGELOG.md`, `CODE_OF_CONDUCT.md`) — **not** only the files you edited. A doc you did not touch can be red on `main` and your PR inherits it. Per the project's prior lesson, ALWAYS run the full glob locally before pushing, never just the edited doc.

- [ ] **Step 1: Run the failing check (the full CI glob, run before all doc edits are clean)**
The CI action runs `markdownlint-cli2` with the glob list from `.github/workflows/markdown-lint.yml`. The exact local equivalent (same globs, in order, including the `!docs/superpowers/plans/**` exclusion and the `.markdownlint.json` config picked up automatically from repo root):
Run:
```bash
npx --yes markdownlint-cli2 \
  "docs/**/*.md" "!docs/superpowers/plans/**" \
  ".claude/**/*.md" "domains/**/*.md" \
  "README.md" "CONTRIBUTING.md" "CHANGELOG.md" "CODE_OF_CONDUCT.md"
```
Expected (if any edited doc still violates a rule, e.g. an MD032/MD004 list-spacing slip in the new sections): FAIL with a non-zero exit and lines like `docs/taxonomy-mappings.md:NN MD032/blanks-around-lists ...`

- [ ] **Step 2: (covered by Step 1)**
The full-glob command in Step 1 is the failing/again-green check.

- [ ] **Step 3: Fix any violations the full glob surfaces**
Resolve each reported `MDxxx` line in the edited docs (most commonly MD032 blanks-around-lists and MD004 unordered-list-style around the fenced YAML/bash blocks and the new bullet lists added above). Re-run the command until it is clean. No code change beyond the doc edits already made in prior tasks.

- [ ] **Step 4: Run the full glob to verify it passes**
Run:
```bash
npx --yes markdownlint-cli2 \
  "docs/**/*.md" "!docs/superpowers/plans/**" \
  ".claude/**/*.md" "domains/**/*.md" \
  "README.md" "CONTRIBUTING.md" "CHANGELOG.md" "CODE_OF_CONDUCT.md"
```
Expected: PASS — final line `markdownlint-cli2 ... Summary: 0 error(s)` and exit code 0.

- [ ] **Step 5: Commit (only if Step 3 changed any file)**
```bash
git add -A docs CHANGELOG.md README.md CONTRIBUTING.md CODE_OF_CONDUCT.md
git commit -m "docs: satisfy full CI markdownlint glob for the v1.7.0 MAS docs"
```

---


## Phase 10 — Golden example regen + final verification

### Task 67: Declare masvs+maswe taxonomies and bump the mobile example run-config to 1.7.0

**Files:**
- Modify: `examples/apd-20260602-acme-mobile-banking/.apd-run.yaml:4-7`
- Modify: `examples/apd-20260602-acme-mobile-banking/expected/.apd-run.yaml`
- Test: `tests/test_validate_example_run.py`

- [ ] **Step 1: Write the failing test**
```python
# Append to tests/test_validate_example_run.py
import yaml as _yaml

MOBILE = (
    pathlib.Path(__file__).resolve().parent.parent
    / "examples" / "apd-20260602-acme-mobile-banking" / "expected"
)


def test_mobile_run_config_declares_mas_taxonomies() -> None:
    cfg = _yaml.safe_load((MOBILE / ".apd-run.yaml").read_text(encoding="utf-8"))
    tax = cfg.get("taxonomies") or []
    assert "masvs" in tax, f"masvs must be declared; got {tax}"
    assert "maswe" in tax, f"maswe must be declared; got {tax}"
    # MAS taxonomy support landed in 1.7.0; the example must advertise it.
    assert cfg.get("framework_version") == "1.7.0", cfg.get("framework_version")
```
- [ ] **Step 2: Run test to verify it fails**
Run: `python -m pytest tests/test_validate_example_run.py::test_mobile_run_config_declares_mas_taxonomies -q`
Expected: FAIL with `AssertionError: masvs must be declared; got ['cwe', 'mitre_attack']`
- [ ] **Step 3: Add the taxonomies + bump the framework version**

Current `examples/apd-20260602-acme-mobile-banking/.apd-run.yaml` (lines 4-7):
```yaml
framework_version: 1.5.0
taxonomies:
  - cwe
  - mitre_attack
```
Replace with:
```yaml
framework_version: 1.7.0
taxonomies:
  - cwe
  - mitre_attack
  - masvs
  - maswe
```
Apply the identical edit to the copy at `examples/apd-20260602-acme-mobile-banking/expected/.apd-run.yaml` (the `expected/` tree is the one `validate`/`rollup`/`build-report` actually run against).
- [ ] **Step 4: Run test to verify it passes**
Run: `python -m pytest tests/test_validate_example_run.py::test_mobile_run_config_declares_mas_taxonomies -q`
Expected: PASS
- [ ] **Step 5: Commit**
```bash
git add examples/apd-20260602-acme-mobile-banking/.apd-run.yaml \
        examples/apd-20260602-acme-mobile-banking/expected/.apd-run.yaml \
        tests/test_validate_example_run.py
git commit -m "test(example): declare masvs+maswe taxonomies on mobile example, bump to 1.7.0"
```

### Task 68: Add masvs+maswe control_mappings to the confidentiality storage finding

**Files:**
- Modify: `examples/apd-20260602-acme-mobile-banking/expected/10-trustworthiness/confidentiality.findings.yaml:20-27`
- Test: `tests/test_examples.py`

- [ ] **Step 1: Write the failing test**
```python
# Append to tests/test_examples.py
import yaml


def _load_findings(rel):
    repo = pathlib.Path(__file__).parent.parent
    p = repo / "examples" / "apd-20260602-acme-mobile-banking" / "expected" / rel
    return {f["id"]: f for f in yaml.safe_load(p.read_text())["finding"]}


def test_storage_finding_carries_mas_mappings():
    f = _load_findings("10-trustworthiness/confidentiality.findings.yaml")["conf-9c065684"]
    cm = f["control_mappings"]
    # The detail cites MASVS-STORAGE-1 + the MASWE storage-leakage area; the
    # structured mappings must make those first-class.
    assert "MASVS-STORAGE-1" in cm["masvs"], cm
    assert "MASVS-STORAGE-2" in cm["masvs"], cm
    assert "MASWE-0006" in cm["maswe"], cm
```
- [ ] **Step 2: Run test to verify it fails**
Run: `python -m pytest tests/test_examples.py::test_storage_finding_carries_mas_mappings -q`
Expected: FAIL with `KeyError: 'masvs'`
- [ ] **Step 3: Add the masvs+maswe keys**

Current `control_mappings` block for `conf-9c065684` (lines 20-27):
```yaml
  control_mappings:
    nist_800_53r5:
    - SC-28
    - SC-28(1)
    - IA-5
    cwe:
    - CWE-312
    - CWE-522
```
Replace with (masvs = STORAGE controls the detail names; maswe = the sensitive-data-in-cleartext-storage weakness, MASVS-STORAGE category):
```yaml
  control_mappings:
    nist_800_53r5:
    - SC-28
    - SC-28(1)
    - IA-5
    cwe:
    - CWE-312
    - CWE-522
    masvs:
    - MASVS-STORAGE-1
    - MASVS-STORAGE-2
    maswe:
    - MASWE-0006
```
- [ ] **Step 4: Run test to verify it passes**
Run: `python -m pytest tests/test_examples.py::test_storage_finding_carries_mas_mappings -q`
Expected: PASS
- [ ] **Step 5: Commit**
```bash
git add examples/apd-20260602-acme-mobile-banking/expected/10-trustworthiness/confidentiality.findings.yaml \
        tests/test_examples.py
git commit -m "test(example): map conf-9c065684 to MASVS-STORAGE-1/2 + MASWE-0006"
```

### Task 69: Add masvs+maswe control_mappings to the hardcoded-secret finding

**Files:**
- Modify: `examples/apd-20260602-acme-mobile-banking/expected/10-trustworthiness/confidentiality.findings.yaml:50-58`
- Test: `tests/test_examples.py`

- [ ] **Step 1: Write the failing test**
```python
# Append to tests/test_examples.py
def test_hardcoded_secret_finding_carries_mas_mappings():
    f = _load_findings("10-trustworthiness/confidentiality.findings.yaml")["conf-4149d0db"]
    cm = f["control_mappings"]
    # detail cites MASVS-CRYPTO-2 (key management) and MASVS-RESILIENCE-2
    # (obfuscation is not a mitigant); the weakness is a hardcoded cryptographic key.
    assert "MASVS-CRYPTO-2" in cm["masvs"], cm
    assert "MASVS-RESILIENCE-2" in cm["masvs"], cm
    assert "MASWE-0014" in cm["maswe"], cm
```
- [ ] **Step 2: Run test to verify it fails**
Run: `python -m pytest tests/test_examples.py::test_hardcoded_secret_finding_carries_mas_mappings -q`
Expected: FAIL with `KeyError: 'masvs'`
- [ ] **Step 3: Add the masvs+maswe keys**

Current `control_mappings` block for `conf-4149d0db` (lines 50-58):
```yaml
  control_mappings:
    nist_800_53r5:
    - IA-5
    - IA-5(7)
    - SC-12
    - SC-28
    cwe:
    - CWE-798
    - CWE-321
```
Replace with:
```yaml
  control_mappings:
    nist_800_53r5:
    - IA-5
    - IA-5(7)
    - SC-12
    - SC-28
    cwe:
    - CWE-798
    - CWE-321
    masvs:
    - MASVS-CRYPTO-2
    - MASVS-RESILIENCE-2
    maswe:
    - MASWE-0014
```
- [ ] **Step 4: Run test to verify it passes**
Run: `python -m pytest tests/test_examples.py::test_hardcoded_secret_finding_carries_mas_mappings -q`
Expected: PASS
- [ ] **Step 5: Commit**
```bash
git add examples/apd-20260602-acme-mobile-banking/expected/10-trustworthiness/confidentiality.findings.yaml \
        tests/test_examples.py
git commit -m "test(example): map conf-4149d0db to MASVS-CRYPTO-2/RESILIENCE-2 + MASWE-0014"
```

### Task 70: Add masvs+maswe control_mappings to the client-side-limit integrity finding

**Files:**
- Modify: `examples/apd-20260602-acme-mobile-banking/expected/10-trustworthiness/integrity.findings.yaml:17-23`
- Test: `tests/test_examples.py`

- [ ] **Step 1: Write the failing test**
```python
# Append to tests/test_examples.py
def test_clientside_limit_finding_carries_mas_mappings():
    f = _load_findings("10-trustworthiness/integrity.findings.yaml")["intg-573fc767"]
    cm = f["control_mappings"]
    # detail cites MASVS-AUTH-1 (server-side authorization); the weakness is
    # business-logic / authorization enforced only client-side.
    assert "MASVS-AUTH-1" in cm["masvs"], cm
    assert "MASWE-0027" in cm["maswe"], cm
```
- [ ] **Step 2: Run test to verify it fails**
Run: `python -m pytest tests/test_examples.py::test_clientside_limit_finding_carries_mas_mappings -q`
Expected: FAIL with `KeyError: 'masvs'`
- [ ] **Step 3: Add the masvs+maswe keys**

Current `control_mappings` block for `intg-573fc767` (lines 17-23):
```yaml
  control_mappings:
    nist_800_53r5:
    - AC-3
    - AC-4
    - SI-10
    cwe:
    - CWE-602
    - CWE-603
```
Replace with:
```yaml
  control_mappings:
    nist_800_53r5:
    - AC-3
    - AC-4
    - SI-10
    cwe:
    - CWE-602
    - CWE-603
    masvs:
    - MASVS-AUTH-1
    maswe:
    - MASWE-0027
```
- [ ] **Step 4: Run test to verify it passes**
Run: `python -m pytest tests/test_examples.py::test_clientside_limit_finding_carries_mas_mappings -q`
Expected: PASS
- [ ] **Step 5: Commit**
```bash
git add examples/apd-20260602-acme-mobile-banking/expected/10-trustworthiness/integrity.findings.yaml \
        tests/test_examples.py
git commit -m "test(example): map intg-573fc767 to MASVS-AUTH-1 + MASWE-0027"
```

### Task 71: Add masvs control_mapping to the HTTPS-only transport capability

**Files:**
- Modify: `examples/apd-20260602-acme-mobile-banking/expected/10-trustworthiness/confidentiality.capabilities.yaml:18-22`
- Test: `tests/test_examples.py`

- [ ] **Step 1: Write the failing test**
```python
# Append to tests/test_examples.py
def test_https_capability_carries_masvs_mapping():
    repo = pathlib.Path(__file__).parent.parent
    p = (repo / "examples" / "apd-20260602-acme-mobile-banking" / "expected"
         / "10-trustworthiness" / "confidentiality.capabilities.yaml")
    caps = {c["id"]: c for c in yaml.safe_load(p.read_text())["capability"]}
    cm = caps["conf-cap-3ad59773"]["control_mappings"]
    # masvs is on BOTH findings and capabilities; maswe is findings-ONLY.
    assert "MASVS-NETWORK-1" in cm["masvs"], cm
    assert "maswe" not in cm, "maswe is findings-only and must not appear on a capability"
```
- [ ] **Step 2: Run test to verify it fails**
Run: `python -m pytest tests/test_examples.py::test_https_capability_carries_masvs_mapping -q`
Expected: FAIL with `KeyError: 'masvs'`
- [ ] **Step 3: Add the masvs key (no maswe)**

Current `control_mappings` block for `conf-cap-3ad59773` (lines 18-22):
```yaml
  control_mappings:
    nist_800_53r5:
    - SC-8
    - SC-8(1)
    - SC-13
```
Replace with (HTTPS-only transport confirms the secure-comms control; maswe omitted — it is findings-only):
```yaml
  control_mappings:
    nist_800_53r5:
    - SC-8
    - SC-8(1)
    - SC-13
    masvs:
    - MASVS-NETWORK-1
```
- [ ] **Step 4: Run test to verify it passes**
Run: `python -m pytest tests/test_examples.py::test_https_capability_carries_masvs_mapping -q`
Expected: PASS
- [ ] **Step 5: Commit**
```bash
git add examples/apd-20260602-acme-mobile-banking/expected/10-trustworthiness/confidentiality.capabilities.yaml \
        tests/test_examples.py
git commit -m "test(example): map HTTPS-only transport capability to MASVS-NETWORK-1"
```

### Task 72: Promote mobile-example specialist records into a deduped 40-synthesis corpus

**Files:**
- Create: `examples/apd-20260602-acme-mobile-banking/expected/40-synthesis/deduped-findings.yaml`
- Create: `examples/apd-20260602-acme-mobile-banking/expected/40-synthesis/deduped-capabilities.yaml`
- Test: `tests/test_examples.py`

- [ ] **Step 1: Write the failing test**
```python
# Append to tests/test_examples.py
def test_mobile_deduped_corpus_carries_mas_mappings():
    repo = pathlib.Path(__file__).parent.parent
    synth = (repo / "examples" / "apd-20260602-acme-mobile-banking"
             / "expected" / "40-synthesis")
    fdoc = yaml.safe_load((synth / "deduped-findings.yaml").read_text())
    findings = {f["id"]: f for f in fdoc["finding"]}
    # The deduped corpus is what rollup reads; the MAS mappings must survive into it.
    assert findings["conf-9c065684"]["control_mappings"]["masvs"] == [
        "MASVS-STORAGE-1", "MASVS-STORAGE-2"]
    assert "MASWE-0014" in findings["conf-4149d0db"]["control_mappings"]["maswe"]
    cdoc = yaml.safe_load((synth / "deduped-capabilities.yaml").read_text())
    caps = {c["id"]: c for c in cdoc["capability"]}
    assert "MASVS-NETWORK-1" in caps["conf-cap-3ad59773"]["control_mappings"]["masvs"]
```
- [ ] **Step 2: Run test to verify it fails**
Run: `python -m pytest tests/test_examples.py::test_mobile_deduped_corpus_carries_mas_mappings -q`
Expected: FAIL with `FileNotFoundError: .../40-synthesis/deduped-findings.yaml`
- [ ] **Step 3: Generate the deduped corpus from the specialist files**

`rollup`/`build-report`/`audit-report` read `40-synthesis/deduped-findings.yaml` and `deduped-capabilities.yaml`, not the raw `10-/20-/30-` trees. Generate them deterministically from the (now MAS-mapped) specialist files with a one-off script, then commit the output:
```bash
python - <<'PY'
import pathlib, yaml
base = pathlib.Path("examples/apd-20260602-acme-mobile-banking/expected")
synth = base / "40-synthesis"
synth.mkdir(parents=True, exist_ok=True)

findings, caps = [], []
for fp in sorted(base.rglob("*.findings.yaml")):
    if "40-synthesis" in fp.parts:
        continue
    findings += (yaml.safe_load(fp.read_text()) or {}).get("finding", []) or []
for cp in sorted(base.rglob("*.capabilities.yaml")):
    if "40-synthesis" in cp.parts:
        continue
    caps += (yaml.safe_load(cp.read_text()) or {}).get("capability", []) or []

findings.sort(key=lambda f: f["id"])
caps.sort(key=lambda c: c["id"])
(synth / "deduped-findings.yaml").write_text(
    yaml.safe_dump({"finding": findings}, sort_keys=False, allow_unicode=True))
(synth / "deduped-capabilities.yaml").write_text(
    yaml.safe_dump({"capability": caps}, sort_keys=False, allow_unicode=True))
print(f"deduped: {len(findings)} findings, {len(caps)} capabilities")
PY
```
This mirrors the shipped claim-event-bus example, which carries a committed `40-synthesis/deduped-findings.yaml` consumed by rollup/audit. The mobile example previously shipped only specialist records and no synthesis; this makes it a second fully-buildable run so the MAS rollups and report can be regenerated deterministically.
- [ ] **Step 4: Run test to verify it passes**
Run: `python -m pytest tests/test_examples.py::test_mobile_deduped_corpus_carries_mas_mappings -q`
Expected: PASS
- [ ] **Step 5: Commit**
```bash
git add examples/apd-20260602-acme-mobile-banking/expected/40-synthesis/deduped-findings.yaml \
        examples/apd-20260602-acme-mobile-banking/expected/40-synthesis/deduped-capabilities.yaml
git commit -m "test(example): promote mobile specialist records into deduped 40-synthesis corpus"
```

### Task 73: Regenerate masvs-coverage + maswe-coverage rollups for the mobile example

**Files:**
- Create: `examples/apd-20260602-acme-mobile-banking/expected/40-synthesis/masvs-coverage.yaml`
- Create: `examples/apd-20260602-acme-mobile-banking/expected/40-synthesis/maswe-coverage.yaml`
- Create: `examples/apd-20260602-acme-mobile-banking/expected/40-synthesis/nist-coverage.yaml`
- Create: `examples/apd-20260602-acme-mobile-banking/expected/40-synthesis/attack-exposure.yaml`
- Create: `examples/apd-20260602-acme-mobile-banking/expected/40-synthesis/apd-coverage-matrix.yaml`
- Create: `examples/apd-20260602-acme-mobile-banking/expected/40-synthesis/cwe-coverage.yaml`
- Create: `examples/apd-20260602-acme-mobile-banking/expected/40-synthesis/metrics.yaml`
- Test: `tests/test_examples.py`

- [ ] **Step 1: Write the failing test**
```python
# Append to tests/test_examples.py
def test_mobile_mas_coverage_rollups_present_and_populated():
    repo = pathlib.Path(__file__).parent.parent
    synth = (repo / "examples" / "apd-20260602-acme-mobile-banking"
             / "expected" / "40-synthesis")
    masvs = yaml.safe_load((synth / "masvs-coverage.yaml").read_text())
    assert masvs["schema_version"] == 1
    assert masvs["generated_by"] == "synthesizer"
    ctrl_ids = {c["masvs_id"] for c in masvs["controls"]}
    # Controls cited across the mapped finding + capability must roll up.
    assert {"MASVS-STORAGE-1", "MASVS-CRYPTO-2", "MASVS-AUTH-1",
            "MASVS-NETWORK-1"} <= ctrl_ids, sorted(ctrl_ids)
    maswe = yaml.safe_load((synth / "maswe-coverage.yaml").read_text())
    entry_ids = {e["maswe_id"] for e in maswe["entries"]}
    assert {"MASWE-0006", "MASWE-0014", "MASWE-0027"} <= entry_ids, sorted(entry_ids)
```
- [ ] **Step 2: Run test to verify it fails**
Run: `python -m pytest tests/test_examples.py::test_mobile_mas_coverage_rollups_present_and_populated -q`
Expected: FAIL with `FileNotFoundError: .../40-synthesis/masvs-coverage.yaml`
- [ ] **Step 3: Run the rollup against the example run-dir**

`rollup` reads `<run-dir>/.apd-run.yaml` taxonomies (now `[cwe, mitre_attack, masvs, maswe]`) and the deduped corpus, then writes every coverage YAML into `40-synthesis/`, including `masvs-coverage.yaml` and `maswe-coverage.yaml` (gated on `'masvs' in declared` / `'maswe' in declared`):
```bash
apd-gauntlet rollup examples/apd-20260602-acme-mobile-banking/expected
```
Expected stdout (control/technique/file counts are informational):
```
rollup: wrote <N> controls, <M> techniques, <K> components, <T> extra coverage files
```
Confirm both MAS files were written and carry rows:
```bash
test -s examples/apd-20260602-acme-mobile-banking/expected/40-synthesis/masvs-coverage.yaml
test -s examples/apd-20260602-acme-mobile-banking/expected/40-synthesis/maswe-coverage.yaml
```
- [ ] **Step 4: Run test to verify it passes**
Run: `python -m pytest tests/test_examples.py::test_mobile_mas_coverage_rollups_present_and_populated -q`
Expected: PASS
- [ ] **Step 5: Commit**
```bash
git add examples/apd-20260602-acme-mobile-banking/expected/40-synthesis/masvs-coverage.yaml \
        examples/apd-20260602-acme-mobile-banking/expected/40-synthesis/maswe-coverage.yaml \
        examples/apd-20260602-acme-mobile-banking/expected/40-synthesis/nist-coverage.yaml \
        examples/apd-20260602-acme-mobile-banking/expected/40-synthesis/attack-exposure.yaml \
        examples/apd-20260602-acme-mobile-banking/expected/40-synthesis/apd-coverage-matrix.yaml \
        examples/apd-20260602-acme-mobile-banking/expected/40-synthesis/cwe-coverage.yaml \
        examples/apd-20260602-acme-mobile-banking/expected/40-synthesis/metrics.yaml
git commit -m "feat(example): regenerate MAS + base coverage rollups for mobile example"
```

### Task 74: Rebuild the mobile example report data.js + HTML with MAS chips/tabs

**Files:**
- Create: `examples/apd-20260602-acme-mobile-banking/expected/40-synthesis/report-data.yaml`
- Modify: `examples/apd-20260602-acme-mobile-banking/expected/40-synthesis/` (report-html/ output — gitignored, rebuilt at audit time)
- Test: `tests/test_examples.py`

- [ ] **Step 1: Write the failing test**
```python
# Append to tests/test_examples.py
def test_mobile_report_builds_with_active_mas_taxonomies(tmp_path):
    import shutil
    from apd_gauntlet.synthesis.audit import parse_data_js
    repo = pathlib.Path(__file__).parent.parent
    src = repo / "examples" / "apd-20260602-acme-mobile-banking" / "expected"
    dst = tmp_path / "run"
    shutil.copytree(src, dst)
    result = subprocess.run(
        ["apd-gauntlet", "build-report", str(dst), "--quiet"],
        capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0, result.stderr
    data = parse_data_js(dst / "40-synthesis" / "report-html" / "data.js")
    meta = data["meta"]
    # data.meta.active_taxonomies is lifted from the run-config taxonomies.
    assert "masvs" in meta["active_taxonomies"]
    assert "maswe" in meta["active_taxonomies"]
    # The MAS coverage scenes render from the rollups.
    assert data["masvs_coverage"], "masvs_coverage scene must be populated"
    assert data["maswe_coverage"], "maswe_coverage scene must be populated"
```
- [ ] **Step 2: Run test to verify it fails**
Run: `python -m pytest tests/test_examples.py::test_mobile_report_builds_with_active_mas_taxonomies -q`
Expected: FAIL — `build-report` exits nonzero because `40-synthesis/report-data.yaml` (editorial sections) is absent, or `active_taxonomies`/MAS scenes are missing in the freshly-parsed data.js.
- [ ] **Step 3: Create the editorial report-data.yaml, then build the report**

`build-report` requires `40-synthesis/report-data.yaml` (exec summary + editorial sections), mirroring the claim example. Author a minimal, faithful one for the mobile example:
```bash
cat > examples/apd-20260602-acme-mobile-banking/expected/40-synthesis/report-data.yaml <<'YAML'
schema_version: 1
generated_by: synthesizer
exec_summary:
  - The Acme mobile banking app splits trust between an adversary-controlled client and the backend; the headline gaps are a fleet-wide hardcoded HMAC request-signing secret compiled into every install, session and refresh tokens persisted in plaintext key-value stores instead of the platform hardware-backed key store, and a daily transfer limit enforced only client-side while the backend honors any submitted amount.
  - Confirmed capabilities are narrow but real — HTTPS-only transport with no cleartext exemptions on both platforms — and do not offset the structural client-trust gaps, every one of which requires a server-side invariant rather than a client-side measure.
YAML
apd-gauntlet build-report examples/apd-20260602-acme-mobile-banking/expected --quiet
```
Expected: the command exits 0 and writes `40-synthesis/report-html/{index.html,app.js,data.js,styles.css,screens.css,...}`. The `report-html/` dir is gitignored (per the CI lesson — shipped-run report-html is never committed); only `report-data.yaml` is committed. The MAS chips/tabs render off the committed `masvs-coverage.yaml` / `maswe-coverage.yaml` + `data.meta.active_taxonomies` the next time any consumer rebuilds.
- [ ] **Step 4: Run test to verify it passes**
Run: `python -m pytest tests/test_examples.py::test_mobile_report_builds_with_active_mas_taxonomies -q`
Expected: PASS
- [ ] **Step 5: Commit**
```bash
git add examples/apd-20260602-acme-mobile-banking/expected/40-synthesis/report-data.yaml \
        tests/test_examples.py
git commit -m "feat(example): author editorial report-data.yaml so mobile report renders MAS scenes"
```

### Task 75: Shipped mobile-example audit passes with MAS coverage present

**Files:**
- Test: `tests/test_cli_audit_report.py`

- [ ] **Step 1: Write the failing test**
```python
# Append to tests/test_cli_audit_report.py
MOBILE = REPO / "examples" / "apd-20260602-acme-mobile-banking" / "expected"


def _copy_mobile(tmp_path):
    dst = tmp_path / "mobile"
    shutil.copytree(MOBILE, dst)
    return dst


def test_mobile_example_audit_passes_after_build_with_mas_coverage(tmp_path):
    """Build the mobile report fresh from the committed YAMLs, then audit — the
    MAS-enabled run must pass the completeness gate with MAS id-coverage present.
    report-html/ is gitignored, so the audit MUST build-report first (CI lesson)."""
    dst = _copy_mobile(tmp_path)
    build = CliRunner().invoke(main, ["build-report", str(dst), "--quiet"])
    assert build.exit_code == 0, build.output
    result = audit_report(dst)
    failed = [c for c in result.checks if c["status"] == "fail"]
    assert result.status == "pass", failed
    names = {c["name"] for c in result.checks}
    # The MAS id-coverage checks must be present and the run must carry MAS rows.
    assert "id_coverage_masvs" in names
    assert "id_coverage_maswe" in names
    masvs = [c for c in result.checks if c["name"] == "id_coverage_masvs"][0]
    maswe = [c for c in result.checks if c["name"] == "id_coverage_maswe"][0]
    assert masvs["status"] == "pass", masvs
    assert maswe["status"] == "pass", maswe
```
- [ ] **Step 2: Run test to verify it fails**
Run: `python -m pytest tests/test_cli_audit_report.py::test_mobile_example_audit_passes_after_build_with_mas_coverage -q`
Expected: FAIL — initially because the committed `40-synthesis` may lack a parity-clean build, or the `id_coverage_masvs`/`id_coverage_maswe` checks have not yet observed MAS rows in this run; the assertion that trips first is `assert "id_coverage_masvs" in names` or the `status == "pass"` parity for the MAS coverage.
- [ ] **Step 3: No production code change — verify the committed example is audit-clean**

This task is a verification gate, not a feature. The `id_coverage_masvs` / `id_coverage_maswe` checks were added to `audit.py` by the audit-extension task earlier in this plan; the MAS coverage YAMLs and `report-data.yaml` were committed by the preceding tasks. If the test fails on a parity check, rebuild and re-commit the coverage artifacts so the committed YAMLs match a fresh build:
```bash
apd-gauntlet rollup examples/apd-20260602-acme-mobile-banking/expected
apd-gauntlet build-report examples/apd-20260602-acme-mobile-banking/expected --quiet
apd-gauntlet audit-report examples/apd-20260602-acme-mobile-banking/expected
```
Expected final line:
```
audit-report: pass (<N> checks, 0 failed; structural_failed=0 editorial_failed=0)
```
Re-stage any coverage/metrics YAML the rebuild changed.
- [ ] **Step 4: Run test to verify it passes**
Run: `python -m pytest tests/test_cli_audit_report.py::test_mobile_example_audit_passes_after_build_with_mas_coverage -q`
Expected: PASS
- [ ] **Step 5: Commit**
```bash
git add tests/test_cli_audit_report.py \
        examples/apd-20260602-acme-mobile-banking/expected/40-synthesis
git commit -m "test(audit): shipped mobile example passes completeness gate with MAS id-coverage"
```

### Task 76: Final full-suite gate verification (pytest, ruff, mypy, markdownlint, freshness, shipped-example audits)

**Files:**
- Test: (whole repo — no source edit; this task only runs every gate green)

- [ ] **Step 1: Write the failing test**
There is no new test file; the "failing check first" is running the full gate suite and confirming every command is green BEFORE declaring step 10 done. Run them in order and capture output. If any is red, fix in its own task and re-run.
- [ ] **Step 2: Run the report-template freshness gate**
Run: `python tools/check_report_template_freshness.py`
Expected: `check_report_template_freshness: OK (<12-hex>)` and exit 0. (Step 10 does not touch `report-template/` JSX, so the bundle stays fresh — this gate must already be green; it confirms no accidental JSX/bundle drift.)
- [ ] **Step 3: Run ruff, mypy, and markdownlint over the full globs**
Run (lint + types):
```bash
ruff check .
mypy tools/apd_gauntlet
```
Expected: `All checks passed!` from ruff and `Success: no issues found` from mypy (zero errors).
Run (markdown — the FULL CI glob, not just edited docs, per the #75 CI lesson that markdownlint globs all of `docs/**`):
```bash
markdownlint-cli2 "docs/**/*.md" "*.md"
```
Expected: exit 0, no MD0xx violations. (Step 10 edits no markdown except possibly the ADR added by an earlier task; this confirms no MD032/MD004-class regressions.)
- [ ] **Step 4: Run the entire pytest suite**
Run: `python -m pytest -q`
Expected: PASS — all tests green, including the full set added this plan:
- `tests/test_validate_example_run.py` (mobile run-config declares masvs+maswe, framework 1.7.0)
- `tests/test_examples.py` (both example `validate`s clean + the five MAS-mapping/coverage/build tests)
- `tests/test_cli_audit_report.py` (claim-event-bus suite still green + `test_mobile_example_audit_passes_after_build_with_mas_coverage`)
- `tests/integration/report/test_example_golden.py` (claim-event-bus golden data.js still byte-identical — step 10 does not touch that example)

Then re-confirm the two shipped-example audits explicitly:
```bash
apd-gauntlet validate examples/apd-20260601-claim-event-bus/expected --errors-only
apd-gauntlet validate examples/apd-20260602-acme-mobile-banking/expected --errors-only
apd-gauntlet audit-report examples/apd-20260602-acme-mobile-banking/expected
```
Expected: both `validate` exit 0, and `audit-report: pass (<N> checks, 0 failed; structural_failed=0 editorial_failed=0)`.
- [ ] **Step 5: Commit**
No code change in this task — it is the final green gate. If steps 2-4 required any fixups, commit them in their own focused tasks above, then re-run this whole gate suite once more and confirm every command is green before opening the PR. If everything was already green, there is nothing to commit here.
```bash
git status --porcelain   # expected: clean (all work committed in prior tasks)
```
```

That is the complete step-10 GOLDEN-EXAMPLE REGEN + FINAL INTEGRATION section, grounded in the real files: the mobile example's actual `.apd-run.yaml` (`framework_version: 1.5.0`, `taxonomies: [cwe, mitre_attack]`), the real finding blocks (`conf-9c065684`, `conf-4149d0db`, `intg-573fc767`, capability `conf-cap-3ad59773`) with their exact existing `control_mappings`, the real CLI verbs (`rollup`, `build-report`, `audit-report` at `cli.py:1098/1224/1314`), the real freshness gate (`tools/check_report_template_freshness.py`), and the existing test patterns (`tests/test_examples.py`, `tests/test_cli_audit_report.py`, `tests/test_validate_example_run.py`).

Key grounding notes for the assembler:
- The mobile example currently ships ONLY specialist findings/capabilities under `10-trustworthiness/` (no `40-synthesis/`), and is covered solely by `test_mobile_banking_example_validates`. The claim-event-bus example is the one with a full committed `40-synthesis/` (deduped-findings.yaml, coverage YAMLs, metrics.yaml) consumed by rollup/audit. To make the mobile example demonstrate MAS end-to-end and pass a shipped-example audit deterministically, step 10 promotes it to a second fully-buildable run (committed `40-synthesis/deduped-findings.yaml`, coverage YAMLs, `report-data.yaml`) — hence the corpus-promotion task before the rollup.
- `report-html/` is gitignored (per the MEMORY CI lesson), so the audit task build-reports first.
- The MASVS/MASWE ids used are tied to each finding's existing prose (STORAGE-1/2 + MASWE-0006 for the SharedPreferences token leak; CRYPTO-2 + RESILIENCE-2 + MASWE-0014 for the hardcoded HMAC key; AUTH-1 + MASWE-0027 for the client-side limit; NETWORK-1 for the HTTPS-only capability) and match the contract regexes — `MASVS-<CATEGORY>-<n>` and `MASWE-NNNN`. The exact MASWE numeric ids must be reconciled against the committed `tools/apd_gauntlet/data/maswe.json` produced by the earlier catalog/`refresh-mas` task; the assembler should confirm those four MASWE ids exist in that catalog (they are placeholders chosen to match the STORAGE/CRYPTO/AUTH categories) and adjust the test+YAML literals together if the real catalog numbers differ.

---
