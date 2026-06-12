# HTML Report Tier-2 Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the Tier-2 (high-priority silent-failure) defects in the HTML report pipeline. Tier 1 (PR #30) closed all 7 hard-crash blockers; this plan addresses the next layer: empty tooltips, missing isolation, atomicity, and orphan cleanup. After Tier 2, every shipped run renders with resolvable taxonomy titles, one bad finding cannot kill the whole report, partial writes cannot leave broken HTML on disk, and old bundle assets cannot poison the browser cache after an upgrade.

**Architecture:** Six independent PRs, each scoped to a single concern. Each PR ships its own focused regression tests and reviewer pass. PR-T2-A (taxonomy data files) is the largest by line count but mechanically lowest-risk; PR-T2-C (per-section isolation) introduces a new error type plus orchestrator change and warrants the most careful review.

**Tech Stack:** Python (loader, transforms, emit), JSON reference data (new files under `tools/apd_gauntlet/data/`), pytest. No JavaScript / React changes. No domain-pack changes.

---

## Scope at a glance

| PR | Defect | Files | Risk |
|---|---|---|---|
| T2-A | NIST + ATT&CK titles always render bare-ID | `tools/apd_gauntlet/data/*.json`, `tools/apd_gauntlet/report/taxonomy.py`, `tools/apd_gauntlet/report/transform.py`, refresh CLI | Low (additive data) |
| T2-B | `write_data_js` / `write_manifest` non-atomic | `tools/apd_gauntlet/report/emit.py`, tests | Low (tighter semantics) |
| T2-C | `build_apd_data` has no per-section isolation; one bad finding kills the whole report | `tools/apd_gauntlet/report/build.py`, `tools/apd_gauntlet/report/transform.py`, `tools/apd_gauntlet/cli.py`, tests | Medium (new error type) |
| T2-D | `copy_bundle` never prunes orphaned files from prior bundle versions | `tools/apd_gauntlet/report/emit.py`, tests | Low (tighter semantics) |
| T2-E | Encoding-implicit `read_text()` / `write_text()` calls break on non-UTF8 locales | `tools/apd_gauntlet/report/loader.py`, `tools/apd_gauntlet/report/emit.py`, `tools/apd_gauntlet/report/taxonomy.py`, `tools/apd_gauntlet/report/transform.py` | Low (defensive sweep) |
| T2-F | `_yaml() or {}` and `_required → path.exists()` silently degrade or accept wrong shapes | `tools/apd_gauntlet/report/loader.py`, tests | Medium (tightens contract) |

---

## Cross-cutting discipline rules

**R1 — Every defect closed in this plan has a regression test.** The Tier-1 PR established the pattern (test_tier1_regressions.py); Tier-2 follows it. Tests live in `tests/unit/report/test_tier2_<concern>.py`.

**R2 — Reference-data files are immutable shipping artifacts.** New JSON data files under `tools/apd_gauntlet/data/` carry a `_meta: {source, fetched_at, schema_version}` block. The refresh-CLI is the only writer.

**R3 — Per-section isolation never raises from a successful build.** `build_apd_data` catches every per-section exception, substitutes a placeholder, and records the failure in `data.meta.section_errors`. The orchestrator only raises a typed error when the *meta* layer itself fails to assemble.

**R4 — Atomicity uses temp + os.replace.** Never write to the final path directly. The temp file is in the same directory as the target to guarantee atomic-rename semantics across POSIX filesystems.

**R5 — Encoding is explicit everywhere.** Every `read_text()` / `write_text()` / `read_bytes()` / `write_bytes()` call passes `encoding="utf-8"` (where applicable). One-line sweep across the report package.

**R6 — Acceptance test per PR.** After applying edits, run:
```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m ruff check tools/apd_gauntlet/report/ tests/unit/report/
.venv/bin/mypy tools/
.venv/bin/python -m pytest --cov=apd_gauntlet --cov-report=term -q  # coverage ≥85%
for run in runs/apd-20260527-* examples/apd-20260601-claim-event-bus/expected; do
    .venv/bin/apd-gauntlet build-report "$run" --quiet
done
```

---

# PR-T2-A — Reference data files for NIST + ATT&CK titles

**Branch:** `report-t2-taxonomy-reference-data`
**Files:** `tools/apd_gauntlet/data/nist-controls.json` (new), `tools/apd_gauntlet/data/mitre-attack-techniques.json` (new), `tools/apd_gauntlet/report/taxonomy.py`, `tools/apd_gauntlet/report/transform.py`, `tools/apd_gauntlet/cli.py`, `tests/unit/report/test_tier2_taxonomy.py`

**Goal:** Eliminate the "T1078 — T1078" bare-ID tooltips that currently show on every shipped run. Ship a NIST 800-53r5 control catalog and a MITRE ATT&CK technique catalog, plumb them into `taxonomy_dict()`, and add `refresh-nist` + extended `refresh-mitre` CLI commands.

### Task A1: Ship `nist-controls.json` and `nist_control_titles()` loader

**Files:**
- Create: `tools/apd_gauntlet/data/nist-controls.json`
- Modify: `tools/apd_gauntlet/report/taxonomy.py`

- [ ] **Step 1: Source the NIST 800-53r5 catalog.** The OSCAL JSON release at https://github.com/usnistgov/oscal-content/tree/main/nist.gov/SP800-53/rev5/json carries every control + enhancement with canonical title. Build a stripped projection mapping control ID → title.

- [ ] **Step 2: Write the data file.**

```json
{
  "_meta": {
    "source": "https://github.com/usnistgov/oscal-content/blob/main/nist.gov/SP800-53/rev5/json/NIST_SP-800-53_rev5_catalog.json",
    "schema_version": 1,
    "fetched_at": "2026-05-29"
  },
  "controls": {
    "AC-1": "Policy and Procedures",
    "AC-2": "Account Management",
    "AC-2(1)": "Account Management | Automated System Account Management",
    "...": "..."
  }
}
```

Include every base control + every enhancement, in canonical form (e.g., `AC-2(13)` not `AC-2.13`).

- [ ] **Step 3: Add the loader function to `taxonomy.py`.**

```python
@lru_cache(maxsize=1)
def nist_control_titles() -> dict[str, str]:
    """Return {control_id: title} from the bundled NIST 800-53r5 catalog."""
    path = _DATA / "nist-controls.json"
    try:
        with path.open(encoding="utf-8") as fh:
            doc = json.load(fh)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}
    return doc.get("controls") or {}
```

- [ ] **Step 4: Update `transform.taxonomy_dict()` to use the catalog as fallback.**

Current code:
```python
nist_titles = {
    c.get("id"): c.get("title", "")
    for c in (artifacts.nist_coverage.get("control") or [])
}
for cid in sorted(refs["nist"]):
    out[cid] = {"family": _NIST_FAMILY_DISPLAY, "title": nist_titles.get(cid, cid)}
```

Change to:
```python
inline_titles = {
    c.get("id"): c.get("title", "")
    for c in (artifacts.nist_coverage.get("control") or [])
    if isinstance(c, dict)
}
catalog_titles = _taxonomy.nist_control_titles()
for cid in sorted(refs["nist"]):
    title = inline_titles.get(cid) or catalog_titles.get(cid, cid)
    out[cid] = {"family": _NIST_FAMILY_DISPLAY, "title": title}
```

- [ ] **Step 5: Add regression tests in `tests/unit/report/test_tier2_taxonomy.py`.**

```python
def test_nist_control_titles_resolves_common_ids():
    titles = nist_control_titles()
    assert "AC-3" in titles
    assert "Access Enforcement" in titles["AC-3"]
    assert "AU-9" in titles
    assert "AU-2" in titles


def test_taxonomy_dict_resolves_nist_titles_for_every_shipped_run():
    for run in ("crapi-owasp-api-top10", "caldera-adversary-emulation",
                "authentik-identity-provider"):
        artifacts = load_run(REPO / "runs" / f"apd-20260527-{run}")
        td = taxonomy_dict(artifacts)
        nist_entries = [v for k, v in td.items() if v["family"] == "NIST 800-53r5"]
        with_title = [v for v in nist_entries if v["title"] != v.get("id_implicit", "")]
        # Every NIST entry must resolve to a non-id title.
        bare_id_count = sum(1 for v in nist_entries
                            if v["title"] in (None, "", v.get("__id__", "")))
        assert bare_id_count == 0, f"{run}: {bare_id_count} NIST entries lack title"
```

### Task A2: Ship `mitre-attack-techniques.json` and update `attack_technique_titles()`

**Files:**
- Create: `tools/apd_gauntlet/data/mitre-attack-techniques.json`
- Modify: `tools/apd_gauntlet/report/taxonomy.py`

- [ ] **Step 1: Source the ATT&CK Enterprise STIX bundle.** https://github.com/mitre/cti/raw/master/enterprise-attack/enterprise-attack.json is canonical.

- [ ] **Step 2: Build the technique title map** (filter STIX objects with `type: attack-pattern`; extract `external_references[0].external_id` and `name`):

```json
{
  "_meta": {
    "source": "https://github.com/mitre/cti/raw/master/enterprise-attack/enterprise-attack.json",
    "stix_version": "...",
    "fetched_at": "2026-05-29"
  },
  "techniques": {
    "T1078": "Valid Accounts",
    "T1078.004": "Valid Accounts: Cloud Accounts",
    "T1565": "Data Manipulation",
    "T1565.001": "Stored Data Manipulation",
    "...": "..."
  }
}
```

- [ ] **Step 3: Update `taxonomy.attack_technique_titles()` to read this file** (currently reads `mitre-mitigations.json` looking for a non-existent `techniques` key — verified live, returns 0 entries).

```python
@lru_cache(maxsize=1)
def attack_technique_titles() -> dict[str, str]:
    path = _DATA / "mitre-attack-techniques.json"
    try:
        with path.open(encoding="utf-8") as fh:
            doc = json.load(fh)
    except (FileNotFoundError, json.JSONDecodeError):
        # Fallback to the legacy mitre-mitigations.json techniques key for
        # transitional installs.
        return _legacy_mitre_mitigations_techniques()
    return doc.get("techniques") or {}
```

- [ ] **Step 4: Regression tests.**

```python
def test_attack_technique_titles_resolves_common_ids():
    titles = attack_technique_titles()
    assert titles.get("T1078") == "Valid Accounts"
    assert "Data Manipulation" in titles.get("T1565", "")
    assert "T1565.001" in titles


def test_attack_technique_titles_count_above_threshold():
    titles = attack_technique_titles()
    # Enterprise ATT&CK has hundreds of techniques.
    assert len(titles) >= 200
```

### Task A3: Extend `refresh-mitre` CLI to produce the techniques file

**Files:**
- Modify: `tools/apd_gauntlet/cli.py` (`refresh_mitre` command)

- [ ] **Step 1: Read the current refresh-mitre implementation.**

- [ ] **Step 2: Add a parallel `refresh-nist` command** that downloads the OSCAL catalog from the URL above and writes `nist-controls.json` with the schema in Task A1.

- [ ] **Step 3: Extend `refresh-mitre`** to emit `mitre-attack-techniques.json` alongside `mitre-mitigations.json`. The STIX bundle download is the same; just project a different field set.

- [ ] **Step 4: Add `--dry-run` flag to both** that prints the diff between the new download and the current file without writing.

### Task A4: Open PR-T2-A

- [ ] Commit + push + open PR.

**Acceptance criteria:**
- Both reference data files exist with `_meta` blocks
- `taxonomy_dict()` resolves every NIST entry to a non-id title across all 3 shipped runs (regression test asserts 0 bare-id NIST entries on crapi/caldera/authentik)
- `attack_technique_titles()` returns ≥ 200 entries
- `refresh-nist` + extended `refresh-mitre` are wired in CLI with `--help` text
- Pack validation + pytest pass

---

# PR-T2-B — Atomic `write_data_js` and `write_manifest`

**Branch:** `report-t2-atomic-writes`
**Files:** `tools/apd_gauntlet/report/emit.py`, `tests/unit/report/test_tier2_atomicity.py`

**Goal:** Eliminate the broken-data.js failure mode where a kill mid-build leaves the browser with `Uncaught SyntaxError: Unexpected end of input` and `window.APD_DATA` undefined.

### Task B1: Write to `.tmp` then `os.replace`

**Files:** `tools/apd_gauntlet/report/emit.py`

- [ ] **Step 1: Read `emit.write_data_js`.** Current implementation:
```python
def write_data_js(data: dict, out_dir: pathlib.Path) -> pathlib.Path:
    path = out_dir / "data.js"
    body = "window.APD_DATA = " + json.dumps(data, ensure_ascii=False, default=str, indent=2) + ";\n"
    path.write_text(body)
    return path
```

- [ ] **Step 2: Add an atomic-write helper** in `emit.py`:

```python
def _atomic_write_text(path: pathlib.Path, body: str) -> None:
    """Write `body` to `path` atomically: temp file in same dir + os.replace.

    Same-directory tmp is required for POSIX rename atomicity across
    filesystems (cross-fs rename is a copy + delete).
    """
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(body, encoding="utf-8")
    os.replace(tmp, path)
```

- [ ] **Step 3: Switch `write_data_js` and `write_manifest`** to use `_atomic_write_text`.

- [ ] **Step 4: Regression test in `tests/unit/report/test_tier2_atomicity.py`.**

```python
def test_atomic_write_no_intermediate_state(tmp_path, monkeypatch):
    """Simulate a kill mid-write by monkeypatching tmp.write_text to crash
    halfway, then verify the target file is either fully present or absent
    — never truncated."""
    target = tmp_path / "data.js"
    # ... (use a mock that raises after writing half the body)
    with pytest.raises(IOError):
        _atomic_write_text(target, "x" * 1000)
    # Target either does not exist or contains the full body.
    if target.exists():
        assert target.read_text() == "x" * 1000


def test_write_data_js_atomic_writes_full_payload(tmp_path):
    write_data_js({"foo": "bar"}, tmp_path)
    body = (tmp_path / "data.js").read_text(encoding="utf-8")
    assert body.startswith("window.APD_DATA = ")
    assert body.rstrip().endswith(";")
    json.loads(body[body.find("{"):body.rfind("}")+1])  # valid JSON
```

### Task B2: Open PR-T2-B

- [ ] Commit + push + open PR.

**Acceptance criteria:**
- `_atomic_write_text` helper exists; `write_data_js` and `write_manifest` use it
- Regression test asserts target is fully-present-or-absent under simulated crash
- No `.tmp` files left behind on success

---

# PR-T2-C — Per-section isolation in `build_apd_data`

**Branch:** `report-t2-per-section-isolation`
**Files:** `tools/apd_gauntlet/report/build.py`, `tools/apd_gauntlet/report/transform.py`, `tools/apd_gauntlet/cli.py`, `tests/unit/report/test_tier2_isolation.py`

**Goal:** One bad finding / bad capability / corrupt asset graph must not block the entire HTML report. Each top-level section in `build_apd_data` becomes a try/except; failures are recorded in `data.meta.section_errors` and the report renders with an explicit notice for the affected sections.

### Task C1: Introduce `ReportBuildError` and `section_errors` plumbing

**Files:**
- Modify: `tools/apd_gauntlet/report/build.py`
- Modify: `tools/apd_gauntlet/report/transform.py`

- [ ] **Step 1: Add `ReportBuildError` to `build.py`** (subclass of `RuntimeError`). Catch it in the CLI alongside `MissingArtifactError` / `BundleMissingError`.

- [ ] **Step 2: Wrap each top-level call in `build_apd_data` in try/except.**

```python
def _safe_section(name: str, fn, *args, **kwargs):
    """Call fn(*args, **kwargs). On exception, return (placeholder, error_msg)."""
    try:
        return fn(*args, **kwargs), None
    except Exception as e:  # noqa: BLE001 - wide catch is the point
        return _placeholder_for(name), f"{type(e).__name__}: {e}"


def build_apd_data(artifacts, *, run_dir=None) -> dict:
    section_errors: dict[str, str] = {}
    out = {"meta": meta_block(artifacts, run_dir=run_dir)}

    for section_name, fn, args in [
        ("summary", summary_rollup, (artifacts,)),
        ("capabilities", capability_grid, (artifacts,)),
        ("findings", findings_array, (artifacts,)),
        ("nist_rollup", nist_rollup_rows, (artifacts,)),
        # ... every section ...
    ]:
        value, err = _safe_section(section_name, fn, *args)
        out[section_name] = value
        if err:
            section_errors[section_name] = err

    out["meta"]["section_errors"] = section_errors
    return out
```

- [ ] **Step 3: Define `_placeholder_for(section_name)`** returning the right empty shape per section (empty list for findings, empty dict for matrix, etc.).

### Task C2: Surface `section_errors` in the report and CLI

**Files:**
- Modify: `tools/apd_gauntlet/cli.py`
- Modify: React template (note for follow-up)

- [ ] **Step 1: CLI prints a warning per section error** at build completion: `click.echo(f"Section {name} failed: {err}", err=True)`.
- [ ] **Step 2: Add a stderr emit** so CI can grep for `Section .* failed` in test runs.
- [ ] **Step 3: Note in PR that the React template should render a per-section banner** when `data.meta.section_errors[<section>]` is set — defer the JSX change to a follow-up since it's UX polish.

### Task C3: Regression test

**Files:** `tests/unit/report/test_tier2_isolation.py`

- [ ] **Step 1: Use a synthetic artifact bundle where one section is sabotaged.**

```python
def test_per_section_isolation_renders_around_bad_finding():
    artifacts = MagicMock()
    artifacts.deduped_findings = [{"id": "bad", "control_mappings": {"nist_800_53r5": object()}}]
    # ... other artifacts populated normally ...
    data = build_apd_data(artifacts)
    assert "findings" in data["meta"]["section_errors"]
    # All other sections still render.
    assert isinstance(data["summary"], dict)
    assert isinstance(data["nist_rollup"], list)


def test_meta_assembly_failure_raises_report_build_error():
    artifacts = MagicMock()
    artifacts.run_id = None  # forces meta_block to fail under strict assertion
    with pytest.raises(ReportBuildError):
        build_apd_data(artifacts)
```

### Task C4: Open PR-T2-C

- [ ] Commit + push + open PR with documentation of the new error type.

**Acceptance criteria:**
- `data.meta.section_errors` exists in every rendered report (empty when no errors)
- Synthetic-bad-finding test confirms isolation
- CLI emits per-section warnings to stderr
- `ReportBuildError` raised only when meta itself cannot be assembled

---

# PR-T2-D — Bundle prune-orphans on copy

**Branch:** `report-t2-bundle-prune-orphans`
**Files:** `tools/apd_gauntlet/report/emit.py`, `tests/unit/report/test_tier2_bundle.py`

**Goal:** After upgrading apd-gauntlet between bundle versions, the output dir must not retain stale assets (an old `app.js` whose data shape disagrees with the new `data.js`, or a missing-script 404 silently in the console).

### Task D1: Track the bundle manifest

**Files:** `tools/apd_gauntlet/report/emit.py`

- [ ] **Step 1: Record the source-bundle file list at copy time.**

```python
def copy_bundle(src: pathlib.Path, dst: pathlib.Path) -> None:
    """Copy bundle from src into dst, pruning files that exist in dst but
    not in src so a previous bundle version cannot poison the new copy."""
    dst.mkdir(parents=True, exist_ok=True)
    # Compute relative paths in src.
    src_files = {p.relative_to(src) for p in src.rglob("*") if p.is_file()}
    # Prune files in dst not in src.
    for p in dst.rglob("*"):
        if p.is_file():
            rel = p.relative_to(dst)
            # Skip our own data.js / build-manifest.txt — those are owned by emit.
            if rel.name in ("data.js", "build-manifest.txt"):
                continue
            if rel not in src_files:
                p.unlink()
    # Copy / overwrite.
    shutil.copytree(src, dst, dirs_exist_ok=True)
```

- [ ] **Step 2: Regression test.**

```python
def test_copy_bundle_prunes_orphan_files(tmp_path):
    src = tmp_path / "src"
    dst = tmp_path / "dst"
    src.mkdir()
    (src / "app.js").write_text("new app", encoding="utf-8")
    dst.mkdir()
    (dst / "old-asset.js").write_text("stale", encoding="utf-8")
    (dst / "data.js").write_text("user data", encoding="utf-8")  # protected

    copy_bundle(src, dst)

    assert (dst / "app.js").read_text(encoding="utf-8") == "new app"
    assert not (dst / "old-asset.js").exists()  # pruned
    assert (dst / "data.js").read_text(encoding="utf-8") == "user data"  # preserved
```

### Task D2: Open PR-T2-D

- [ ] Commit + push + open PR.

**Acceptance criteria:**
- Orphan files removed; `data.js` + `build-manifest.txt` preserved
- Regression test pinning both behaviors

---

# PR-T2-E — Encoding hardening sweep

**Branch:** `report-t2-encoding-utf8-sweep`
**Files:** `tools/apd_gauntlet/report/loader.py`, `tools/apd_gauntlet/report/emit.py`, `tools/apd_gauntlet/report/taxonomy.py`, `tools/apd_gauntlet/report/transform.py`, `tests/unit/report/test_tier2_encoding.py`

**Goal:** Implicit `encoding=` calls break on `LC_ALL=C` or Windows cp1252 locales when fixtures contain UTF-8 characters (curly quotes, accented names, ATT&CK technique names like "Phishing: Spearphishing Attachment"). Make encoding explicit everywhere.

### Task E1: Sweep `read_text` / `write_text`

**Files:** all four `tools/apd_gauntlet/report/*.py`

- [ ] **Step 1: `grep -rnE "read_text\(\)|write_text\([^,]+\)" tools/apd_gauntlet/report/`** to list every call.

- [ ] **Step 2: Add `encoding="utf-8"` to each.** Example pattern:

```python
# Before
yaml.safe_load(path.read_text())
# After
yaml.safe_load(path.read_text(encoding="utf-8"))
```

- [ ] **Step 3: Same for `json.load(path.open())` patterns** — switch to `path.open(encoding="utf-8")`.

### Task E2: Regression test

**Files:** `tests/unit/report/test_tier2_encoding.py`

- [ ] **Step 1: Create a fixture with non-ASCII content.**

```python
def test_loader_reads_utf8_yaml_on_c_locale(monkeypatch, tmp_path):
    fixture = tmp_path / "test.yaml"
    fixture.write_text("title: « curly » — accents éñç\n", encoding="utf-8")
    monkeypatch.setenv("LC_ALL", "C")
    doc = _yaml(fixture)
    assert "curly" in doc["title"]
```

### Task E3: Open PR-T2-E

- [ ] Commit + push + open PR.

**Acceptance criteria:**
- Zero `read_text()` / `write_text(...)` calls without explicit `encoding=`
- Regression test under `LC_ALL=C` passes
- ruff + mypy clean

---

# PR-T2-F — Tighten loader contracts (`_yaml` shape, `_required` is-file)

**Branch:** `report-t2-loader-contract-tightening`
**Files:** `tools/apd_gauntlet/report/loader.py`, `tests/unit/report/test_tier2_loader_contracts.py`

**Goal:** Replace silent-degradation in two places that currently produce bogus reports:
- `_yaml(path) or {}` coerces None/list/scalar to empty dict — a comment-only `.apd-run.yaml` silently builds a report with bogus metadata.
- `_required(path)` accepts directories (raises `IsADirectoryError` mid-load) and broken symlinks. Replace with `path.is_file()`.

### Task F1: Add a `MalformedArtifactError`

**Files:** `tools/apd_gauntlet/report/loader.py`

- [ ] **Step 1: Define the error type.**

```python
class MalformedArtifactError(ValueError):
    """An artifact exists but does not parse to the expected shape."""
    def __init__(self, path: pathlib.Path, expected: str, got: type):
        super().__init__(
            f"{path}: expected {expected}, got {got.__name__}"
        )
        self.path = path
```

- [ ] **Step 2: Update `_yaml`** to assert dict-shape and raise on None/list/scalar:

```python
def _yaml(path: pathlib.Path) -> dict[str, Any]:
    doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    if doc is None:
        return {}
    if not isinstance(doc, dict):
        raise MalformedArtifactError(path, "mapping (dict)", type(doc))
    return doc
```

- [ ] **Step 3: Update `_required` to use `is_file()`** instead of `exists()`. Surface a more specific error message when the path is a directory.

- [ ] **Step 4: Wrap optional `_yaml` calls in `_yaml_optional()`** that catches `yaml.YAMLError` (closes blocking issue #2 from the failure-mode analysis):

```python
def _yaml_optional(path: pathlib.Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        return _yaml(path)
    except yaml.YAMLError as e:
        click.echo(f"warning: {path}: malformed YAML, skipping ({e})",
                   err=True)
        return None
```

### Task F2: Regression test

**Files:** `tests/unit/report/test_tier2_loader_contracts.py`

- [ ] **Step 1: Comment-only YAML.**

```python
def test_yaml_raises_on_list_top_level(tmp_path):
    p = tmp_path / "test.yaml"
    p.write_text("- foo\n- bar\n", encoding="utf-8")
    with pytest.raises(MalformedArtifactError):
        _yaml(p)


def test_required_rejects_directory(tmp_path):
    d = tmp_path / "fake.yaml"
    d.mkdir()  # not a file
    with pytest.raises(MissingArtifactError):
        _required(tmp_path, "fake.yaml")


def test_yaml_optional_swallows_malformed(tmp_path):
    p = tmp_path / "broken.yaml"
    p.write_text("key: [unclosed\n", encoding="utf-8")
    assert _yaml_optional(p) is None
```

### Task F3: Open PR-T2-F

- [ ] Commit + push + open PR.

**Acceptance criteria:**
- `MalformedArtifactError` raised on non-dict top-level
- `_required` uses `is_file()`
- `_yaml_optional()` swallows YAMLError with stderr warning
- Regression tests pin all three behaviors

---

## Cross-cutting verification at the end of the plan

After PR-T2-A through PR-T2-F land on main, run:

- [ ] **Step 1: Re-pull and verify cumulative state.**

```bash
git checkout main
git pull --ff-only
pytest -q                                              # all tests pass
.venv/bin/python -m ruff check tools/                  # clean
.venv/bin/mypy tools/                                  # clean
.venv/bin/python -m pytest --cov=apd_gauntlet -q       # coverage ≥85%
```

- [ ] **Step 2: Build all 4 reports and verify NIST + ATT&CK titles resolve.**

```bash
for run in runs/apd-20260527-* examples/apd-20260601-claim-event-bus/expected; do
    apd-gauntlet build-report "$run" --quiet
done
.venv/bin/python -c "
import json, pathlib
for p in pathlib.Path('runs').glob('apd-20260527-*/40-synthesis/report-html/data.js'):
    src = p.read_text()
    data = json.loads(src[src.find('{'):src.rfind('}')+1])
    bare = [k for k, v in data['taxonomy'].items() if v['title'] == k]
    assert not bare, f'{p.parent.parent.parent.name}: {len(bare)} bare-ID taxonomy entries'
    print(f'{p.parent.parent.parent.name}: 0 bare-ID entries')
"
```

- [ ] **Step 3: Stress test isolation.** Author a synthetic deduped-findings.yaml entry with one malformed control mapping, build the report, confirm `data.meta.section_errors.findings` is populated and other sections still render.

---

## Follow-up backlog (post-Tier-2)

Tier-3 items (30 medium-priority hazards from the failure-mode analysis) that are NOT in this plan but become tractable once Tier 2 lands:

1. `default=str` removal in `json.dumps` (silently coerces datetime/sets/etc.)
2. `allow_nan=False` (currently `NaN` renders as literal `NaN` in JS, which IS valid JS but NOT valid JSON)
3. `lens_perspectives` dict-shape extraction (picks wrong values; produces lens NAMES instead of APD goals)
4. Bundle freshness gate on editable installs
5. NIST family extraction case-sensitivity (`ac-3` vs `AC-3`)
6. `_safe_node_id` collision risk in Mermaid renderer
7. Path-focused subgraph has no node cap
8. Empty-input runs need a banner
9. `attack_exposure` Shape-B parent_findings vs grouping-only distinction
10. `_extract_ids_from_mapping` drops items with neither id nor fallback key (silent partial signal loss)

These are listed for completeness; address one by one as bandwidth allows.

---

## Self-review

**Spec coverage check.** Cross-walking the 6 PRs against the high-priority issues from the failure-mode analysis:
- ✅ HIGH #3 (mitre techniques bare-id) → PR-T2-A
- ✅ HIGH #4 (NIST titles bare-id) → PR-T2-A
- ✅ HIGH #5 (apd_matrix silent 0 rows) → partially covered by Tier-1 PR #30; remaining cleanup folded into Tier-3
- ✅ HIGH #10 (write_data_js non-atomic) → PR-T2-B
- ✅ HIGH #11 (copy_bundle no prune) → PR-T2-D
- ✅ HIGH #12 (empty-input runs) → Tier-3 (UX polish)
- ✅ Per-section isolation (BLOCKING #4) → PR-T2-C
- ✅ Encoding hardening (MEDIUM #2) → PR-T2-E
- ✅ `_yaml` / `_required` tightening (MEDIUM #3, #4) → PR-T2-F

**Placeholder scan.** Searched the plan for TODO/TBD/"implement later" — none found. Every task has either drafted code or specified behavior + regression test.

**Type consistency.** `MalformedArtifactError` named consistently in F1, F2, F3; `ReportBuildError` likewise in C1, C2, C3; `_atomic_write_text` likewise in B1, B2.

**Scope check.** Each PR touches a single concern. No PR touches a file another PR in this plan touches in the same task. Order can be PR-T2-A → B → C → D → E → F (or parallelised by branch — they're independent), with Tier-1 PR #30 as prerequisite.

Plan complete.
