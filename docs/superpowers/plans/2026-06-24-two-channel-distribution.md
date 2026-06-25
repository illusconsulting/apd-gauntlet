# Two-Channel Distribution Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship the APD framework via two distribution channels — a clean PyPI wheel for the deterministic `apd-gauntlet` engine, and an installable Claude Code plugin (with marketplace) for the agents/skills/workflow — fixing the bug where the current wheel crashes on import.

**Architecture:** The repo is a *two-headed product*. The Python engine (`tools/apd_gauntlet/`) is the deterministic CLI; the agentic half (`.claude/agents`, `.claude/skills`, `.claude/workflows/apd-gauntlet.js`) is LLM-driven and runs only inside Claude Code. Today the wheel reads `schemas/` and `domains/` via repo-root-relative paths (`__file__.parent.parent.parent`) that do not exist in a `pip install`, so it `FileNotFoundError`s at import. We **relocate `schemas/` and `domains/` into the package** (`tools/apd_gauntlet/data/`) as the single source of truth, route all reads through one `importlib.resources`-based locator, and add a clean-wheel-install smoke gate to CI. In parallel we make the plugin half spec-conformant (`.claude-plugin/plugin.json` + `.claude-plugin/marketplace.json`, a `commands/` slash-command bridge for the non-component workflow runner) and add a NOTICE file for the redistributed MITRE/OWASP knowledge bases. Both channels ship from one repo, **version-locked**, in **one combined release (1.8.0)**.

**Tech Stack:** Python 3.10–3.12, setuptools + `importlib.resources`, Click, jsonschema, pytest, GitHub Actions (PyPI Trusted Publishing already wired in `release.yml`), Claude Code plugin/marketplace manifests.

---

## Decisions (locked)

| Decision | Choice | Source |
|---|---|---|
| Bundle `schemas/`+`domains/` | **Relocate into the package** (`tools/apd_gauntlet/data/`), single source of truth, `importlib.resources` | user |
| Wheel ↔ plugin versioning | **Lockstep** — one version, plugin pins exact wheel | user |
| Plugin install channel | **`.claude-plugin/marketplace.json` in this repo** | user |
| Release sequencing | **Single combined release** = `1.8.0` | user |

**Version target: `1.8.0`** (minor: adds the plugin distribution channel + relocates packaged data; CLI behavior is backward-compatible). Every version-bearing file is set to `1.8.0` by this plan. *(If a patch is preferred, substitute `1.7.1` consistently — the touchpoint list is in Task D5.)*

## Out of scope

- Porting the LLM orchestration into Python (a wheel cannot run the agents — that is a separate ~4–8 week effort, not this plan).
- Slimming the plugin clone (the marketplace `source: "./"` ships the whole tracked repo; `runs/`, `dist/`, `.venv/` are gitignored so the payload is already lean — a dedicated `plugin/` subdir is a future optimization).
- Changing any analytical behavior of the gauntlet.

## Risks & mitigations

- **Relocation touches many references.** Mitigated by a single `resources` locator (one API), an exhaustive reference list (Task A5), and the full test suite + new wheel smoke test gating the change.
- **Plugin manifest spec drift.** Schemas in this plan are quoted from current Claude Code docs (`code.claude.com/docs`, verified 2026-06-24). Task B0 re-runs `claude plugin validate` to catch version-specific differences.
- **`importlib.resources` + filesystem ops.** We coerce the Traversable to a real `pathlib.Path` (matching the existing `report/build.py` precedent); valid because pip/uv install wheels unzipped. Documented in `resources.py`.

---

## File Structure

**New files:**
- `tools/apd_gauntlet/resources.py` — the single package-relative resource locator (schemas + domain packs). All framework-resource reads route through it.
- `tools/apd_gauntlet/data/schemas/*.schema.json` — relocated from repo-root `schemas/` (43 files, flat, incl. `_defs.schema.json`).
- `tools/apd_gauntlet/data/domains/<pack>/…` — relocated from repo-root `domains/` (6 packs × `domain.yaml` + 4 `.md` + `common-patterns/`).
- `tests/test_resources.py` — unit tests for the locator.
- `tests/test_no_external_path_resolution.py` — AST guard: no module reads above the package at import time.
- `tests/integration/test_wheel_install_smoke.py` — builds + installs the wheel in an isolated venv, runs the CLI (regression test for the import crash).
- `tests/test_plugin_manifest.py` — validates `plugin.json` + `marketplace.json` + referenced component paths.
- `.claude-plugin/plugin.json` — relocated, spec-conformant plugin manifest.
- `.claude-plugin/marketplace.json` — repo-as-marketplace catalog.
- `commands/apd-gauntlet.md` — slash command that bridges the (non-component) workflow runner.
- `hooks/hooks.json` — *(optional)* SessionStart CLI-prerequisite preflight.
- `NOTICE` — third-party KB attributions (MITRE, OWASP).
- `docs/adrs/0023-two-channel-distribution.md` — the ADR.
- `RELEASING.md` — the lockstep release checklist.

**Modified files:**
- `pyproject.toml` — extend `package-data`; register `wheel` pytest marker; bump version.
- `tools/apd_gauntlet/{validate,build_domain_skill,init_run}.py`, `tools/apd_gauntlet/cli.py`, `tools/apd_gauntlet/synthesis/draft.py`, `tools/apd_gauntlet/report/loader.py` — route reads through `resources`.
- `tools/apd_gauntlet/__init__.py` — version bump.
- `.github/workflows/{python-tests,validate,markdown-lint,release}.yml` — wheel-smoke + plugin-validate gates; relocated globs; release hardening.
- `tests/test_workflow_apd_gauntlet.py` — manifest path + version-floor literal.
- `tests/test_meta_schemas.py` and any test hard-coding repo-root `schemas/`/`domains/`.
- `.claude/skills/apd-domain/SKILL.md` (+ `by-goal/`) — regenerated, version-current.
- `README.md`, `docs/architecture.md`, `docs/extending-agents.md`, `CONTRIBUTING.md`, `CHANGELOG.md`, `LICENSE` — docs + attribution + copyright fill.

---

# Milestone A — Engine packaging fix (make the wheel run standalone)

> Goal of A: `pip install apd_gauntlet-1.8.0-py3-none-any.whl` into a clean venv → `apd-gauntlet --help`, `validate`, `build-report`, `validate-domain pbm` all run. Independently mergeable; lands with B–D in one release.

### Task A0: Pin the bug with a failing clean-wheel smoke test

**Files:**
- Create: `tests/integration/test_wheel_install_smoke.py`
- Modify: `pyproject.toml` (register the `wheel` marker)

- [ ] **Step 1: Register the `wheel` marker** in `pyproject.toml` under `[tool.pytest.ini_options]` (after the existing `addopts` line):

```toml
markers = [
  "wheel: builds and installs the wheel into an isolated venv (slow; needs uv or pip+build)",
]
```

- [ ] **Step 2: Write the failing smoke test**

```python
# tests/integration/test_wheel_install_smoke.py
"""Build the wheel, install it into a clean venv with NO repo on sys.path, and
run the CLI. This is the regression test for the import-time FileNotFoundError
(schemas/domain.schema.json) that shipped in 1.7.0."""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
pytestmark = pytest.mark.wheel

_HAVE_UV = shutil.which("uv") is not None
_SKIP = os.environ.get("APD_SKIP_WHEEL_TESTS") == "1"


def _run(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if k != "PYTHONPATH"}
    return subprocess.run(cmd, cwd=cwd, env=env, capture_output=True, text=True, timeout=300)


@pytest.fixture(scope="session")
def venv_bin(tmp_path_factory: pytest.TempPathFactory) -> Path:
    if _SKIP or not _HAVE_UV:
        pytest.skip("needs uv and APD_SKIP_WHEEL_TESTS unset")
    dist = tmp_path_factory.mktemp("dist")
    venv = tmp_path_factory.mktemp("venv")
    build = _run(["uv", "build", "--wheel", "--out-dir", str(dist), str(REPO)], cwd=REPO)
    assert build.returncode == 0, build.stderr
    whl = next(dist.glob("*.whl"))
    assert _run(["uv", "venv", str(venv)], cwd=dist).returncode == 0
    py = venv / "bin" / "python"
    inst = _run(["uv", "pip", "install", "--python", str(py), str(whl)], cwd=dist)
    assert inst.returncode == 0, inst.stderr
    return venv / "bin"


def test_help_runs_without_import_error(venv_bin: Path, tmp_path: Path) -> None:
    r = _run([str(venv_bin / "apd-gauntlet"), "--help"], cwd=tmp_path)
    assert r.returncode == 0, r.stderr
    assert "Traceback" not in r.stderr and "FileNotFoundError" not in r.stderr
    assert "Usage:" in r.stdout


def test_version_runs(venv_bin: Path, tmp_path: Path) -> None:
    r = _run([str(venv_bin / "apd-gauntlet"), "--version"], cwd=tmp_path)
    assert r.returncode == 0, r.stderr
    assert "1.8.0" in r.stdout


def test_validate_domain_pbm(venv_bin: Path, tmp_path: Path) -> None:
    r = _run([str(venv_bin / "apd-gauntlet"), "validate-domain", "pbm"], cwd=tmp_path)
    assert r.returncode == 0, r.stderr
```

- [ ] **Step 3: Run it and confirm it FAILS today**

Run: `APD_SKIP_WHEEL_TESTS= pytest tests/integration/test_wheel_install_smoke.py -m wheel -v`
Expected: FAIL — `test_help_runs_without_import_error` shows `FileNotFoundError: .../schemas/domain.schema.json` (proves the bug).

- [ ] **Step 4: Commit**

```bash
git add tests/integration/test_wheel_install_smoke.py pyproject.toml
git commit -m "test: failing clean-wheel-install smoke test (pins the 1.7.0 import crash)"
```

### Task A1: Add the `resources` locator + relocate schemas/ and domains/ into the package

**Files:**
- Create: `tools/apd_gauntlet/resources.py`
- Create: `tests/test_resources.py`
- Move: `schemas/` → `tools/apd_gauntlet/data/schemas/`; `domains/` → `tools/apd_gauntlet/data/domains/`
- Modify: `pyproject.toml` (`[tool.setuptools.package-data]`)

- [ ] **Step 1: Write the failing locator test**

```python
# tests/test_resources.py
from apd_gauntlet import resources


def test_schemas_dir_has_defs_and_finding() -> None:
    sd = resources.schemas_dir()
    assert (sd / "_defs.schema.json").is_file()
    assert (sd / "finding.schema.json").is_file()
    assert sum(1 for _ in sd.glob("*.schema.json")) >= 40


def test_domains_dir_has_pbm_pack() -> None:
    dd = resources.domains_dir()
    assert (dd / "pbm" / "domain.yaml").is_file()


def test_read_schema_parses() -> None:
    doc = resources.read_schema("domain.schema.json")
    assert doc.get("$id")
```

- [ ] **Step 2: Run it to verify it fails**

Run: `pytest tests/test_resources.py -v`
Expected: FAIL with `ModuleNotFoundError: apd_gauntlet.resources`.

- [ ] **Step 3: Relocate the trees (single source of truth)**

```bash
git mv schemas tools/apd_gauntlet/data/schemas
git mv domains tools/apd_gauntlet/data/domains
```

- [ ] **Step 4: Extend `package-data`** in `pyproject.toml` so the relocated trees ship in the wheel:

```toml
[tool.setuptools.package-data]
apd_gauntlet = [
  "data/*.json",
  "data/report-template/**/*",
  "data/schemas/*.json",
  "data/domains/**/*",
]
```

- [ ] **Step 5: Write `resources.py`** (the only place that knows where packaged data lives):

```python
# tools/apd_gauntlet/resources.py
"""Wheel-safe access to packaged framework resources (JSON Schemas, domain packs).

Every read of a *framework* resource MUST go through this module so it resolves
package-relative via importlib.resources and survives a pip-wheel install — where
the repo root and its former sibling schemas/ and domains/ trees do not exist.

We coerce the Traversable to a real pathlib.Path (mirroring report/build.py): valid
because pip/uv install wheels unzipped. The taxonomy JSONs under data/*.json are
already read package-relative elsewhere (report/taxonomy.py, synthesis/rollup.py)
and are intentionally NOT re-routed here (YAGNI)."""
from __future__ import annotations

import json
import pathlib
from functools import lru_cache
from importlib import resources
from typing import Any


@lru_cache(maxsize=1)
def data_dir() -> pathlib.Path:
    """Absolute path to the packaged ``tools/apd_gauntlet/data`` root."""
    return pathlib.Path(str(resources.files("apd_gauntlet") / "data"))


def schemas_dir() -> pathlib.Path:
    """Directory of packaged ``*.schema.json`` files."""
    return data_dir() / "schemas"


def domains_dir() -> pathlib.Path:
    """Directory of packaged built-in domain packs (operator custom packs override via --domains-dir)."""
    return data_dir() / "domains"


def read_schema(filename: str) -> dict[str, Any]:
    """Parse one packaged schema, e.g. ``read_schema("domain.schema.json")``."""
    return json.loads((schemas_dir() / filename).read_text(encoding="utf-8"))
```

- [ ] **Step 6: Run the locator test to verify it passes**

Run: `pytest tests/test_resources.py -v`
Expected: PASS (all three).

- [ ] **Step 7: Commit**

```bash
git add tools/apd_gauntlet/resources.py tools/apd_gauntlet/data/schemas tools/apd_gauntlet/data/domains tests/test_resources.py pyproject.toml
git commit -m "feat(packaging): relocate schemas/ + domains/ into the package; add resources locator"
```

### Task A2: Fix the import-time crash (`build_domain_skill.py`)

**Files:**
- Modify: `tools/apd_gauntlet/build_domain_skill.py:14-15`

- [ ] **Step 1: Replace the module-level eager read** (the line that crashes every subcommand). Change:

```python
REPO = pathlib.Path(__file__).resolve().parent.parent.parent
DOMAIN_SCHEMA = json.loads((REPO / "schemas" / "domain.schema.json").read_text(encoding="utf-8"))
```

to a lazy, package-relative loader:

```python
from . import resources as _resources


@lru_cache(maxsize=1)
def _domain_schema() -> dict[str, Any]:
    return _resources.read_schema("domain.schema.json")
```

Add `from functools import lru_cache` to the imports. Replace every in-function use of `DOMAIN_SCHEMA` with `_domain_schema()`. (`REPO` is no longer needed here — remove it if nothing else in the module uses it; grep first.)

- [ ] **Step 2: Verify the import no longer crashes in a wheel layout**

Run: `pytest tests/integration/test_wheel_install_smoke.py::test_help_runs_without_import_error -m wheel -v`
Expected: PASS (`--help` runs; no `FileNotFoundError`).

- [ ] **Step 3: Run the unit suite for this module**

Run: `pytest tests/ -k "domain_skill" -v`
Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add tools/apd_gauntlet/build_domain_skill.py
git commit -m "fix(packaging): lazy package-relative domain schema load (stops CLI-wide import crash)"
```

### Task A3: Route command-time schema reads through `resources`

**Files:**
- Modify: `tools/apd_gauntlet/validate.py:17-18,76`
- Modify: `tools/apd_gauntlet/cli.py:239,273-274,368-369,720-723`
- Modify: `tools/apd_gauntlet/synthesis/draft.py:119-120`

- [ ] **Step 1: Fix `validate.py`** — replace lines 17-18:

```python
REPO = pathlib.Path(__file__).resolve().parent.parent.parent
SCHEMAS_DIR = REPO / "schemas"
```

with:

```python
from . import resources as _resources

SCHEMAS_DIR = _resources.schemas_dir()
```

`build_registry()` at line 76 keeps `sorted(SCHEMAS_DIR.glob("*.schema.json"))` unchanged — `schemas_dir()` returns a real `Path`, so `.glob` works.

- [ ] **Step 2: Fix the four `cli.py` schema sites.** Each currently builds `...parent.parent.parent / "schemas" / "<name>.schema.json"`. Replace each with the shared accessor:
  - `cli.py:239` (`validate-domain-cmd`): `from .validate import SCHEMAS_DIR` then `SCHEMAS_DIR / "domain.schema.json"` — or `resources.read_schema("domain.schema.json")` if it parses inline.
  - `cli.py:273-274` (`validate-run-config-cmd`): `resources.read_schema("run-config.schema.json")`.
  - `cli.py:368-369` (`plan-run-cmd`): `resources.read_schema("run-config.schema.json")`.
  - `cli.py:720-723` (`parse-threat-model-cmd`): `resources.read_schema("threat-model-normalized.schema.json")`; the adjacent `validate.build_registry()` at 726 is fixed transitively by Step 1.

  Add `from .resources import read_schema` (or `from . import resources`) at the top of `cli.py` if not present.

- [ ] **Step 3: Fix `synthesis/draft.py:119-120`** — replace the `repo = ...parent.parent.parent.parent` + `repo/"schemas"/"domain.schema.json"` read with `from .. import resources` and `resources.read_schema("domain.schema.json")`.

- [ ] **Step 4: Run validation tests**

Run: `pytest tests/ -k "validate or threat_model or draft" -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add tools/apd_gauntlet/validate.py tools/apd_gauntlet/cli.py tools/apd_gauntlet/synthesis/draft.py
git commit -m "fix(packaging): route command-time schema reads through resources locator"
```

### Task A4: Route domain-pack defaults through `resources`

**Files:**
- Modify: `tools/apd_gauntlet/cli.py:132,233,1360,1376` (the four `--domains-dir` defaults)
- Modify: `tools/apd_gauntlet/init_run.py:59-60`
- Modify: `tools/apd_gauntlet/report/loader.py:316`

> Why: the workflow runner calls `build-domain-skill`/`validate-domain` **without** `--domains-dir`, relying on the CLI default `Path("domains")` (cwd). After relocation that path is gone. Default it to the packaged packs; operators with custom packs still pass `--domains-dir`.

- [ ] **Step 1: Change the four `cli.py` defaults.** Click defaults are evaluated at import, so use a callable to avoid importing-order issues. For each `--domains-dir` option (lines 132, 233, 1360, 1376), change `default=pathlib.Path("domains")` (or `default=Path("domains")`) to:

```python
default=None,
```

and at the top of each command body, resolve the fallback:

```python
from .resources import domains_dir as _packaged_domains
...
if domains_dir is None:
    domains_dir = _packaged_domains()
```

(This keeps `--domains-dir ./custom` working and makes the omitted-flag path use the packaged packs.)

- [ ] **Step 2: Fix `init_run.py:59-60`** — replace:

```python
if domains_dir is None:
    domains_dir = pathlib.Path(__file__).resolve().parent.parent.parent / "domains"
```

with:

```python
if domains_dir is None:
    from .resources import domains_dir as _packaged_domains
    domains_dir = _packaged_domains()
```

- [ ] **Step 3: Fix `report/loader.py:316`** — replace `_DOMAINS_DIR = pathlib.Path(__file__).resolve().parents[3] / "domains"` with:

```python
from .. import resources as _resources
_DOMAINS_DIR = _resources.domains_dir()
```

(The read at line 337 stays try/except-guarded; pack versions now populate from packaged packs instead of falling back to `"unknown"`.)

- [ ] **Step 4: Verify the full standalone surface**

Run: `pytest tests/integration/test_wheel_install_smoke.py -m wheel -v`
Expected: PASS (`--help`, `--version`, `validate-domain pbm`).

- [ ] **Step 5: Commit**

```bash
git add tools/apd_gauntlet/cli.py tools/apd_gauntlet/init_run.py tools/apd_gauntlet/report/loader.py
git commit -m "fix(packaging): default --domains-dir to packaged packs; route loader/init_run via resources"
```

### Task A5: Add the AST guard test + update relocated-path references

**Files:**
- Create: `tests/test_no_external_path_resolution.py`
- Modify: `.github/workflows/markdown-lint.yml:20`
- Modify: `tests/test_meta_schemas.py` and any test hard-coding `REPO / "schemas"` / `REPO / "domains"`
- Modify: docs referencing top-level `schemas/`/`domains/`

- [ ] **Step 1: Write the AST guard** (cheap, runs on every PR; would have caught the original bug):

```python
# tests/test_no_external_path_resolution.py
"""Guard: no apd_gauntlet module resolves a framework resource ABOVE the package.
Reads of schemas/ and domains/ must go through apd_gauntlet.resources."""
from __future__ import annotations

import ast
from pathlib import Path

PKG = Path(__file__).resolve().parents[1] / "tools" / "apd_gauntlet"
_BANNED_LITERALS = {"schemas", "domains"}


def _walks_above_package(node: ast.AST) -> bool:
    # ".parent.parent.parent" (3+) or "parents[n]" with n>=3
    hops = 0
    cur = node
    while isinstance(cur, ast.Attribute):
        if cur.attr == "parent":
            hops += 1
        cur = cur.value
    if hops >= 3:
        return True
    if isinstance(node, ast.Subscript) and isinstance(node.value, ast.Attribute) \
            and node.value.attr == "parents":
        idx = node.slice
        return isinstance(idx, ast.Constant) and isinstance(idx.value, int) and idx.value >= 3
    return False


def test_no_module_resolves_schemas_or_domains_above_package() -> None:
    offenders: list[str] = []
    for path in PKG.rglob("*.py"):
        if path.name == "resources.py":
            continue  # the one allowed locator
        tree = ast.parse(path.read_text(encoding="utf-8"))
        consts = {
            n.value for n in ast.walk(tree)
            if isinstance(n, ast.Constant) and n.value in _BANNED_LITERALS
        }
        if not consts:
            continue
        for n in ast.walk(tree):
            if _walks_above_package(n):
                offenders.append(f"{path.relative_to(PKG)}: walk-up joined near {consts}")
                break
    assert not offenders, "Route framework-resource reads through apd_gauntlet.resources:\n" + "\n".join(offenders)
```

- [ ] **Step 2: Run it**

Run: `pytest tests/test_no_external_path_resolution.py -v`
Expected: PASS (Tasks A2–A4 removed every offender).

- [ ] **Step 3: Update the markdownlint glob** in `.github/workflows/markdown-lint.yml` — change line 20 `domains/**/*.md` to `tools/apd_gauntlet/data/domains/**/*.md`. (Line 19 `.claude/**/*.md` is unchanged — agents/skills stay there.)

- [ ] **Step 4: Update tests that hard-code the old paths.** Find them:

Run: `grep -rnE '"schemas"|"domains"|/ .schemas|/ .domains' tests/`
For each (notably `tests/test_meta_schemas.py`, which walks the schema tree), repoint to `tools/apd_gauntlet/data/schemas` / `…/domains`, or import `from apd_gauntlet import resources` and use `resources.schemas_dir()`. `tests/test_workflow_apd_gauntlet.py` reads `schemas/agent-receipt.schema.json` at repo root — repoint to `resources.schemas_dir() / "agent-receipt.schema.json"`.

- [ ] **Step 5: Update docs** referencing top-level `schemas/`/`domains/` (`README.md`, `docs/architecture.md`, `docs/extending-agents.md`, `CONTRIBUTING.md`): note the new location `tools/apd_gauntlet/data/{schemas,domains}/` and that custom domain packs are supplied via `--domains-dir`.

- [ ] **Step 6: Full green check**

Run: `ruff check tools/ tests/ && mypy tools/ && pytest -q && python tools/check_report_template_freshness.py`
Expected: all PASS.

- [ ] **Step 7: Commit**

```bash
git add tests/test_no_external_path_resolution.py .github/workflows/markdown-lint.yml tests/ docs/ README.md CONTRIBUTING.md
git commit -m "test+chore(packaging): AST guard + repoint relocated schema/domain references"
```

---

# Milestone B — Claude Code plugin channel

> Goal of B: a user can `/plugin marketplace add illusconsulting/apd-gauntlet` then `/plugin install apd-gauntlet@apd-security`, get the agents/skills/workflow, and be told to `pip install apd-gauntlet`. Manifest is spec-conformant and validated.

### Task B0: Verify the plugin spec against the installed Claude Code

- [ ] **Step 1:** Run `claude plugin validate .` (or note it's unavailable). Confirm three doc-derived facts against the installed version: (a) `.claude-plugin/plugin.json` is the required manifest path; (b) `skills`/`agents` may point at `./.claude/...`; (c) `workflows/` is not a component. Record any deltas; if a delta contradicts this plan, adjust the affected task before proceeding.

*(No commit — verification only.)*

### Task B1: Relocate + complete the plugin manifest

**Files:**
- Move/rewrite: `plugin.json` → `.claude-plugin/plugin.json`
- Modify: `tests/test_workflow_apd_gauntlet.py:232` (manifest path) and `:251` (version floor)

- [ ] **Step 1: Author `.claude-plugin/plugin.json`**:

```json
{
  "name": "apd-gauntlet",
  "displayName": "APD Gauntlet",
  "version": "1.8.0",
  "description": "APD security architecture review framework — 9 specialist agents plus intake, the apd-gauntlet workflow runner, and a synthesizer fallback. Requires the apd-gauntlet PyPI package on PATH.",
  "author": { "name": "APD Gauntlet contributors", "url": "https://github.com/illusconsulting/apd-gauntlet" },
  "homepage": "https://github.com/illusconsulting/apd-gauntlet",
  "repository": "https://github.com/illusconsulting/apd-gauntlet",
  "license": "Apache-2.0",
  "keywords": ["security", "architecture", "review", "threat-model", "apd"],
  "agents": "./.claude/agents/",
  "skills": "./.claude/skills/",
  "commands": "./commands/",
  "hooks": "./hooks/hooks.json"
}
```

- [ ] **Step 2: Remove the old root manifest**

```bash
git rm plugin.json
```

- [ ] **Step 3: Update the manifest test.** In `tests/test_workflow_apd_gauntlet.py` change line 232:

```python
PLUGIN_MANIFEST = REPO / ".claude-plugin" / "plugin.json"
```

and the version-floor literal at line 251 from `"1.7.0"` to `"1.8.0"`.

- [ ] **Step 4: Run the manifest test**

Run: `pytest tests/test_workflow_apd_gauntlet.py -k plugin -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add .claude-plugin/plugin.json tests/test_workflow_apd_gauntlet.py
git rm plugin.json
git commit -m "feat(plugin): move manifest to .claude-plugin/plugin.json with full metadata"
```

### Task B2: Bridge the workflow via a slash command

**Files:**
- Create: `commands/apd-gauntlet.md`

> Why: `workflows/` is not a plugin component. A `commands/` slash command is the supported way to expose the runner; it references the installed file via `${CLAUDE_PLUGIN_ROOT}` and does the wheel preflight.

- [ ] **Step 1: Write `commands/apd-gauntlet.md`**:

```markdown
---
description: Run the APD security gauntlet against a prepared run directory
---

You are about to drive the APD gauntlet. Do this in order:

1. **Preflight the engine.** Run `apd-gauntlet --version` in the shell. If it is
   missing, STOP and tell the user: "Install the engine first: `pip install apd-gauntlet==1.8.0`
   (or `pipx install apd-gauntlet`)." If the version's major.minor differs from this
   plugin's (1.8), warn that the plugin and CLI should be version-matched.

2. **Confirm the run is scaffolded** — a `runs/<run-id>/` with `inputs/` and an
   `.apd-run.yaml`. If not, point the user to docs/running-the-gauntlet.md.

3. **Launch the runner** via the Workflow tool, executing the script at
   `${CLAUDE_PLUGIN_ROOT}/.claude/workflows/apd-gauntlet.js`, passing the run's
   parsed `.apd-run.yaml` as `args`. Run it INTERACTIVE/FOREGROUND (never headless —
   a background launch can interrupt the specialist subagent dispatches).
```

- [ ] **Step 2: Sanity-check it parses** (frontmatter + body):

Run: `python -c "import pathlib,re,sys; t=pathlib.Path('commands/apd-gauntlet.md').read_text(); assert t.startswith('---') and 'description:' in t and 'CLAUDE_PLUGIN_ROOT' in t; print('ok')"`
Expected: `ok`.

- [ ] **Step 3: Commit**

```bash
git add commands/apd-gauntlet.md
git commit -m "feat(plugin): /apd-gauntlet slash command bridging the workflow runner"
```

### Task B3: SessionStart prerequisite hook (optional but recommended)

**Files:**
- Create: `hooks/hooks.json`

- [ ] **Step 1: Write a non-fatal preflight hook** (warns if the CLI is absent; never blocks a session):

```json
{
  "hooks": {
    "SessionStart": [
      {
        "matcher": "startup",
        "hooks": [
          {
            "type": "command",
            "command": "command -v apd-gauntlet >/dev/null 2>&1 || echo 'APD Gauntlet plugin: the apd-gauntlet CLI is not on PATH — run: pip install apd-gauntlet==1.8.0'"
          }
        ]
      }
    ]
  }
}
```

- [ ] **Step 2: Validate JSON**

Run: `python -c "import json; json.load(open('hooks/hooks.json')); print('ok')"`
Expected: `ok`.

- [ ] **Step 3: Commit**

```bash
git add hooks/hooks.json
git commit -m "feat(plugin): non-fatal SessionStart hook warning when apd-gauntlet CLI is absent"
```

### Task B4: Add the marketplace manifest

**Files:**
- Create: `.claude-plugin/marketplace.json`

- [ ] **Step 1: Author `.claude-plugin/marketplace.json`** (`apd-security` is not a reserved name; the single plugin lives at repo root → `source: "./"`):

```json
{
  "name": "apd-security",
  "owner": { "name": "APD Gauntlet contributors", "url": "https://github.com/illusconsulting/apd-gauntlet" },
  "description": "APD security architecture review framework — agents, skills, and the gauntlet workflow.",
  "plugins": [
    {
      "name": "apd-gauntlet",
      "source": "./",
      "description": "9 APD specialist agents + intake + workflow runner + synthesizer. Requires the apd-gauntlet PyPI package on PATH.",
      "version": "1.8.0",
      "license": "Apache-2.0",
      "homepage": "https://github.com/illusconsulting/apd-gauntlet",
      "keywords": ["security", "architecture", "review", "apd"]
    }
  ]
}
```

- [ ] **Step 2: Validate** (if available): `claude plugin validate .` ; always: `python -c "import json; json.load(open('.claude-plugin/marketplace.json')); print('ok')"`.
Expected: `ok` (and no validator errors).

- [ ] **Step 3: Commit**

```bash
git add .claude-plugin/marketplace.json
git commit -m "feat(plugin): repo-as-marketplace catalog (.claude-plugin/marketplace.json)"
```

### Task B5: Add the plugin-manifest test

**Files:**
- Create: `tests/test_plugin_manifest.py`

- [ ] **Step 1: Write the test**:

```python
# tests/test_plugin_manifest.py
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
PLUGIN = REPO / ".claude-plugin" / "plugin.json"
MARKET = REPO / ".claude-plugin" / "marketplace.json"


def test_plugin_manifest_well_formed_and_paths_exist() -> None:
    m = json.loads(PLUGIN.read_text(encoding="utf-8"))
    for k in ("name", "version", "description", "license", "agents", "skills"):
        assert m.get(k), f"missing {k}"
    agents = (REPO / m["agents"].lstrip("./")).resolve()
    skills = (REPO / m["skills"].lstrip("./")).resolve()
    assert agents.is_dir() and list(agents.glob("*.md"))
    assert skills.is_dir() and any((p / "SKILL.md").is_file() for p in skills.iterdir() if p.is_dir())
    assert (REPO / "commands" / "apd-gauntlet.md").is_file()


def test_marketplace_manifest_well_formed() -> None:
    mk = json.loads(MARKET.read_text(encoding="utf-8"))
    assert mk["name"] == "apd-security"
    assert isinstance(mk.get("owner"), dict) and mk["owner"].get("name")
    entry = next(p for p in mk["plugins"] if p["name"] == "apd-gauntlet")
    assert entry["source"] == "./"
    assert entry["version"] == json.loads(PLUGIN.read_text())["version"]
```

- [ ] **Step 2: Run it**

Run: `pytest tests/test_plugin_manifest.py -v`
Expected: PASS.

- [ ] **Step 3: Commit**

```bash
git add tests/test_plugin_manifest.py
git commit -m "test(plugin): validate plugin + marketplace manifests and referenced paths"
```

### Task B6: Regenerate the committed `apd-domain` skill to a version-current default

**Files:**
- Modify: `.claude/skills/apd-domain/SKILL.md` + `.claude/skills/apd-domain/by-goal/*.md`

> The committed skill is a stale `identity-security`@1.6.0 snapshot. Ship a deterministic, version-matched default (`pbm` — the README's lead example); the runner regenerates it per-run from the selected pack.

- [ ] **Step 1: Regenerate** (uses the now-package-relative packed packs):

Run: `apd-gauntlet build-domain-skill pbm --framework-version 1.8.0`

- [ ] **Step 2: Confirm freshness gates pass**

Run: `python tools/check_report_template_freshness.py && pytest tests/ -k "domain" -q`
Expected: PASS.

- [ ] **Step 3: Commit**

```bash
git add .claude/skills/apd-domain
git commit -m "chore(plugin): ship version-current pbm apd-domain skill (runner regenerates per run)"
```

### Task B7: Document CBM as an optional MCP dependency

**Files:**
- Modify: `README.md` (plugin install section)

- [ ] **Step 1: Add a short "Plugin install" + "Optional code_recon (CBM)" section** to `README.md`: how to `/plugin marketplace add illusconsulting/apd-gauntlet` + `/plugin install apd-gauntlet@apd-security`; that `pip install apd-gauntlet==1.8.0` is required; and that `codebase-memory-mcp` is optional — with `code_recon: auto` (default) the gauntlet degrades to prose-only when CBM is absent, `code_recon: enabled` requires it.

- [ ] **Step 2: Markdownlint**

Run: `npx markdownlint-cli2 "README.md"` (or the repo's configured lint)
Expected: clean.

- [ ] **Step 3: Commit**

```bash
git add README.md
git commit -m "docs(plugin): document plugin install, wheel prerequisite, and optional CBM"
```

---

# Milestone C — CI / release hardening

> Goal of C: CI installs the *built artifact* (not just `-e`) and fails if the wheel can't run; the plugin manifests are gated; release builds + smoke-tests before publishing.

### Task C1: Add a clean-wheel-install job to `python-tests.yml`

**Files:**
- Modify: `.github/workflows/python-tests.yml`

- [ ] **Step 1: Append a new job** (the existing editable matrix stays):

```yaml
  wheel-smoke:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@df4cb1c069e1874edd31b4311f1884172cec0e10  # v6.0.3
      - uses: astral-sh/setup-uv@<pinned-sha>  # latest pinned
      - uses: actions/setup-python@a309ff8b426b58ec0e2a45f0f869d46889d02405  # v6.2.0
        with: { python-version: "3.12" }
      - run: pip install -e ".[dev]"   # for pytest + the test harness only
      - run: pytest tests/integration/test_wheel_install_smoke.py -m wheel -v
```

(If `astral-sh/setup-uv` is undesirable, the smoke fixture also accepts `python -m build` + `pip` — adjust the fixture's `_HAVE_UV` branch accordingly. Pin any new action by SHA, matching the repo convention.)

- [ ] **Step 2: Validate the workflow YAML**

Run: `python -c "import yaml; yaml.safe_load(open('.github/workflows/python-tests.yml')); print('ok')"`
Expected: `ok`.

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/python-tests.yml
git commit -m "ci: clean-wheel-install smoke job (installs the built artifact, not -e)"
```

### Task C2: Gate the plugin manifests in CI

**Files:**
- Modify: `.github/workflows/markdown-lint.yml` (or `validate.yml`)

- [ ] **Step 1: Add a plugin-validate step** to the `lint-agents` job (it already installs the package and lints agents):

```yaml
      - name: Validate plugin manifests
        run: pytest tests/test_plugin_manifest.py -v
```

- [ ] **Step 2: Validate YAML + run locally**

Run: `python -c "import yaml; yaml.safe_load(open('.github/workflows/markdown-lint.yml')); print('ok')" && pytest tests/test_plugin_manifest.py -q`
Expected: `ok` + PASS.

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/markdown-lint.yml
git commit -m "ci: gate plugin + marketplace manifest validity"
```

### Task C3: Harden `release.yml` (smoke before publish)

**Files:**
- Modify: `.github/workflows/release.yml`

- [ ] **Step 1: Insert a wheel-smoke + coverage gate before publish.** After `- run: python -m build` (line 21) and before the attestation step, add:

```yaml
      - name: Smoke-test the built wheel in a clean venv
        run: |
          python -m venv /tmp/whlenv
          /tmp/whlenv/bin/pip install dist/*.whl
          cd /tmp && /tmp/whlenv/bin/apd-gauntlet --version
          /tmp/whlenv/bin/apd-gauntlet validate-domain pbm
      - name: Validate plugin manifests
        run: pytest tests/test_plugin_manifest.py -v
```

And change the existing `- run: pytest` (line 19) to `- run: pytest --cov --cov-report=term-missing` so the 85% floor is enforced at release time (today only PRs enforce it).

- [ ] **Step 2: Validate YAML**

Run: `python -c "import yaml; yaml.safe_load(open('.github/workflows/release.yml')); print('ok')"`
Expected: `ok`.

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/release.yml
git commit -m "ci(release): smoke-test wheel + validate plugin + enforce coverage before publish"
```

---

# Milestone D — Licensing, version lockstep, docs

### Task D1: Add the `NOTICE` file (third-party KB attributions)

**Files:**
- Create: `NOTICE`
- Modify: `pyproject.toml` (ship NOTICE in the dist-info)

- [ ] **Step 1: Write `NOTICE`** — attribute the redistribution-restricted bundled KBs (MITRE Terms of Use require citing the catalog + MITRE; OWASP content is CC BY-SA 4.0; NIST is US-Gov public domain, courtesy line):

```text
APD Gauntlet
Copyright 2026 APD Gauntlet contributors

This product bundles third-party knowledge bases under tools/apd_gauntlet/data/.
Their content remains under the upstream licenses/terms below.

MITRE (https://www.mitre.org) — used under the MITRE Terms of Use; ATT&CK, CAPEC,
CWE, and D3FEND are trademarks of The MITRE Corporation.
  - ATT&CK (Enterprise + Mobile): data/mitre-attack-techniques.json,
    data/mitre-attack-detection.json, data/mitre-mitigations.json
  - CAPEC: data/capec.json
  - CWE: data/cwe.json
  - D3FEND: data/d3fend.json
  - ATLAS (mitre-atlas/atlas-data, Apache-2.0): data/atlas-techniques.json

OWASP (https://owasp.org) — Creative Commons Attribution-ShareAlike 4.0
(CC BY-SA 4.0, https://creativecommons.org/licenses/by-sa/4.0/):
  - MASVS: data/masvs.json
  - MASWE: data/maswe.json
  - Top 10 (Web / API / LLM): data/owasp_top10.json, data/owasp_api_top10.json,
    data/owasp_llm_top10.json

NIST (https://www.nist.gov) — U.S. Government works, public domain
(17 U.S.C. 105); attribution provided as a courtesy:
  - SP 800-53r5 (OSCAL): data/nist-controls.json, data/nist-families.json
  - CSF 2.0 crosswalk: data/csf2-800-53-crosswalk.json
  - SP 800-66 (HIPAA) crosswalk: data/hipaa-800-53-crosswalk.json
```

- [ ] **Step 2: Ship NOTICE in the wheel metadata.** In `pyproject.toml` under `[project]`, add `license-files = ["LICENSE", "NOTICE"]` (setuptools ≥ 77 / PEP 639) so both land in `*.dist-info/`. *(If the pinned setuptools predates `license-files`, instead add `NOTICE` to `package-data` by placing a copy at `tools/apd_gauntlet/data/NOTICE` — pick whichever the pinned build backend supports; verify with Task C1's wheel build.)*

- [ ] **Step 3: Verify NOTICE ships**

Run: `uv build --wheel --out-dir /tmp/nt . && python -c "import zipfile,glob; z=zipfile.ZipFile(glob.glob('/tmp/nt/*.whl')[0]); print([n for n in z.namelist() if 'NOTICE' in n])"`
Expected: a non-empty list (NOTICE present in the wheel).

- [ ] **Step 4: Commit**

```bash
git add NOTICE pyproject.toml
git commit -m "legal: NOTICE attributing bundled MITRE + OWASP (CC BY-SA 4.0) knowledge bases"
```

### Task D2: Fill the LICENSE copyright placeholder

**Files:**
- Modify: `LICENSE`

- [ ] **Step 1:** Replace `Copyright [yyyy] [name of copyright owner]` with `Copyright 2026 APD Gauntlet contributors`.

- [ ] **Step 2: Commit**

```bash
git add LICENSE
git commit -m "legal: fill Apache-2.0 copyright line"
```

### Task D3: Add a NOTICE-presence CI check

**Files:**
- Modify: `tools/check_kb_cache_freshness.py` (or new `tools/check_notice_present.py`)

- [ ] **Step 1: Add an assertion** that every attribution-required KB filename appearing in `tools/apd_gauntlet/data/` is named in `NOTICE`. Minimal new checker:

```python
# tools/check_notice_present.py
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
REQUIRED = [
    "mitre-attack-techniques.json", "capec.json", "cwe.json", "d3fend.json",
    "atlas-techniques.json", "masvs.json", "maswe.json",
    "owasp_top10.json", "owasp_api_top10.json", "owasp_llm_top10.json",
]
notice = (REPO / "NOTICE").read_text(encoding="utf-8")
missing = [f for f in REQUIRED if f not in notice]
if missing:
    print("NOTICE is missing attribution for:", missing); sys.exit(1)
print("NOTICE present for all attribution-required KBs.")
```

- [ ] **Step 2: Wire into `python-tests.yml`** next to the existing freshness steps:

```yaml
      - name: Check NOTICE attributions present
        run: python tools/check_notice_present.py
```

- [ ] **Step 3: Run + commit**

Run: `python tools/check_notice_present.py` → expect the success line.

```bash
git add tools/check_notice_present.py .github/workflows/python-tests.yml
git commit -m "ci(legal): assert NOTICE covers attribution-required knowledge bases"
```

### Task D4: ADR + CHANGELOG

**Files:**
- Create: `docs/adrs/0023-two-channel-distribution.md`
- Modify: `CHANGELOG.md`

- [ ] **Step 1: Write ADR-0023** capturing: the two-channel decision; relocation of `schemas/`+`domains/` into the package with the `resources` locator; lockstep versioning; marketplace-in-repo; NOTICE for redistributed KBs. Follow the existing ADR format (`docs/adrs/0022-*.md` as template).

- [ ] **Step 2: Add a CHANGELOG `## [1.8.0]` entry** under `## [Unreleased]` summarizing: fixed standalone-wheel import crash; relocated packaged data; added Claude Code plugin + marketplace manifests; added NOTICE; lockstep versioning.

- [ ] **Step 3: Markdownlint**

Run: the repo's markdownlint glob over the two files.
Expected: clean.

- [ ] **Step 4: Commit**

```bash
git add docs/adrs/0023-two-channel-distribution.md CHANGELOG.md
git commit -m "docs: ADR-0023 two-channel distribution + CHANGELOG 1.8.0"
```

### Task D5: Version lockstep bump + RELEASING.md

**Files:**
- Modify: `pyproject.toml:7`, `tools/apd_gauntlet/__init__.py:2`, `.claude-plugin/plugin.json` (done in B1), `.claude-plugin/marketplace.json` (done in B4), `tests/test_workflow_apd_gauntlet.py:251` (done in B1)
- Create: `RELEASING.md`

- [ ] **Step 1: Set version to `1.8.0`** in `pyproject.toml:7` (`version = "1.8.0"`) and `tools/apd_gauntlet/__init__.py:2` (`__version__ = "1.8.0"`). (plugin.json, marketplace.json, and the test floor were set to `1.8.0` in Milestone B.)

- [ ] **Step 2: Write `RELEASING.md`** documenting the lockstep touchpoints so future releases can't skew:

```markdown
# Releasing

Versions are LOCKSTEP. To cut release X.Y.Z, update ALL of:
1. `pyproject.toml` → `version = "X.Y.Z"`
2. `tools/apd_gauntlet/__init__.py` → `__version__ = "X.Y.Z"`
3. `.claude-plugin/plugin.json` → `"version": "X.Y.Z"`
4. `.claude-plugin/marketplace.json` → the apd-gauntlet entry `"version": "X.Y.Z"`
5. `tests/test_workflow_apd_gauntlet.py` → the version-floor literal
6. `CHANGELOG.md` → new `## [X.Y.Z]` section

Then: `pytest -q`, `git tag vX.Y.Z`, `git push --tags`. The `release` workflow
builds, smoke-tests the wheel, validates the plugin, publishes to PyPI (Trusted
Publishing), and cuts a GitHub Release. Plugin consumers must bump the plugin
version to receive updates (Claude Code caches by version).
```

- [ ] **Step 3: Assert lockstep**

Run: `pytest tests/test_workflow_apd_gauntlet.py -k version -v && pytest tests/test_plugin_manifest.py -v`
Expected: PASS (all version sources agree on `1.8.0`).

- [ ] **Step 4: Commit**

```bash
git add pyproject.toml tools/apd_gauntlet/__init__.py RELEASING.md
git commit -m "release: bump to 1.8.0 (lockstep) + RELEASING.md"
```

---

## Final verification (run before tagging)

- [ ] `ruff check tools/ tests/` — clean
- [ ] `mypy tools/` — clean
- [ ] `pytest --cov --cov-report=term-missing` — green, coverage ≥ 85%
- [ ] `pytest tests/integration/test_wheel_install_smoke.py -m wheel -v` — green (the regression)
- [ ] `python tools/check_report_template_freshness.py && python tools/check_kb_cache_freshness.py && python tools/check_notice_present.py` — all pass
- [ ] `apd-gauntlet validate examples/apd-20260601-claim-event-bus/expected/` — clean
- [ ] `claude plugin validate .` (if available) — no errors
- [ ] Manual: in a scratch dir, `uv build`, `pip install` the wheel into a fresh venv, run `apd-gauntlet build-report` on an example run → `index.html` produced

## Self-review notes (spec coverage)

- Import crash → A0/A2. Standalone schemas → A1/A3. Standalone domains → A1/A4. Guard against regression → A0 (runtime) + A5 (static AST) + C1/C3 (CI). Plugin recognized by Claude Code → B0/B1. Non-component workflow shipped → B2. Wheel prerequisite surfaced → B2/B3/B7. Marketplace install → B4. Manifest gated → B5/C2. Stale skill → B6. CBM optional → B7. Release safety → C3. KB licensing → D1/D2/D3. Lockstep version → B1/B4/D5. ADR/docs → D4/A5/B7.
- Shared interface used consistently across tasks: `apd_gauntlet.resources.{data_dir,schemas_dir,domains_dir,read_schema}` (defined A1; consumed A2–A4; guarded A5).
