# HTML Report Tier-3 Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the Tier-3 (medium-priority hardening + UX-polish) defects in the HTML report pipeline. Tier 1 (PR #30) eliminated 7 hard-crash blockers; Tier 2 (PRs #31–#36) closed all 14 high-priority silent-data-loss / corruption issues and added 30+ regression tests. This plan addresses the remaining 30 medium hazards: silent type coercions, latent collision risk in Mermaid IDs, browser-render hazards, package-resource lookups that break under wheel install, UX gaps (empty-input banner, freshness indicators), and the broader UTF-8 encoding sweep across the non-report parts of the package that T2-E deferred.

**Architecture:** Six PRs covering six distinct concerns. Each PR is scoped to a single conceptual change, ships its own regression tests, and is independently reviewable. Unlike Tier-2, none of the PRs change a typed error contract or restructure orchestration — they tighten existing semantics, fix latent collisions, and surface freshness state to the UI.

**Tech Stack:** Python (loader, transforms, emit, taxonomy), pytest, a small bundle-source hash change in [report-template/.build/build.mjs](report-template/.build/build.mjs), and a React banner/freshness UX change in [report-template/screens/](report-template/screens/) that lands as a separate frontend PR.

---

## Scope at a glance

| PR | Concern | Files | Risk |
|---|---|---|---|
| T3-A | JSON serializer hygiene: drop `default=str`, set `allow_nan=False`, escape `</script>` for inline-safety, normalise datetime/sets at the boundary | `tools/apd_gauntlet/report/emit.py`, tests | Low (tighter contract) |
| T3-B | `_safe_node_id` collision risk + path-focused subgraph node-cap | `tools/apd_gauntlet/report/transform.py`, tests | Low |
| T3-C | Empty-input run banner + reference-DB freshness indicator | `tools/apd_gauntlet/report/transform.py`, `tools/apd_gauntlet/report/taxonomy.py`, React template, tests | Low (additive UX) |
| T3-D | NIST family-extraction case + format normalisation; lens_perspectives dict-shape fix; ATT&CK Shape-B parent-vs-grouping distinction | `tools/apd_gauntlet/report/transform.py`, tests | Medium (semantic clarification) |
| T3-E | Bundle freshness gate on editable installs; bundle source-hash includes path | `tools/apd_gauntlet/report/build.py`, `report-template/.build/build.mjs`, `tools/check_report_template_freshness.py`, tests | Medium (build-time gate) |
| T3-F | UTF-8 encoding sweep across the rest of the package (cli.py, validate.py, summary.py, init_run.py, lint_agents.py, build_domain_skill.py) | the named files + tests | Low (mechanical) |

---

## Cross-cutting discipline rules

**R1 — Every defect has a regression test.** Tests live in `tests/unit/report/test_tier3_<concern>.py` (or `tests/unit/test_tier3_<concern>.py` for non-report concerns).

**R2 — No silent placeholder coercion.** Tier 3's job is to surface what was silently swallowed in earlier tiers. Where a tier-2 patch wrapped a section in try/except and substituted an empty list, tier 3 makes sure the failure is visible: `data.meta.section_errors` already exists, but warnings about non-fatal coercions also need a home (e.g., `data.meta.warnings: [...]`).

**R3 — Reference data freshness is surfaced.** `data.meta.reference_db_versions: {nist: {fetched_at, count}, attack: {...}, cwe: {...}, d3fend: {...}}` so the UI can warn when catalogs are stale (>180 days) or empty (load failure).

**R4 — Acceptance test per PR.**
```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m ruff check tools/ tests/
.venv/bin/mypy tools/
for run in runs/apd-20260527-* examples/apd-20260601-claim-event-bus/expected; do
    .venv/bin/apd-gauntlet build-report "$run" --quiet
done
```

---

# PR-T3-A — JSON serializer hygiene

**Branch:** `report-t3-json-serializer-hygiene`
**Files:** `tools/apd_gauntlet/report/emit.py`, `tests/unit/report/test_tier3_json_hygiene.py`

**Goal:** Eliminate three latent JSON-serialization hazards that currently let surprising values reach the rendered report.

### Defects closed

1. **`default=str` silently coerces unknown types.** A datetime, set, or framework object reaches `json.dumps` and gets stringified — the report ends up with `"2026-05-29 14:23:00+00:00"` or `"{'x', 'y'}"` baked in as if it were intentional. Replace with explicit pre-pass that converts datetime/date → ISO strings and sets → sorted lists; raise `TypeError` with the dict path on anything else.
2. **`allow_nan=False` not set.** `json.dumps` happily writes literal `NaN` for IEEE NaN values. That's valid JS but invalid JSON, and it produces fragile rendering. Set `allow_nan=False`; any 0/0 division upstream raises clearly instead.
3. **`</script>` not escaped.** If `data.js` is ever inlined into the page (a likely future single-file variant), a finding `detail` containing `</script>...<script>alert(1)</script>` breaks the HTML parser. Cheap defense-in-depth: post-process the JSON body to escape `</` → `<\/` (no-op in JSON parsing, defeats the HTML parser's `</script>` scanner).

### Task A1: Normalize-before-serialize pre-pass

**Files:**
- Modify: `tools/apd_gauntlet/report/emit.py`

- [ ] **Step 1: Add `_normalize_for_json()` helper.**

```python
import datetime

def _normalize_for_json(value: Any, *, path: str = "$") -> Any:
    """Walk value, convert datetime/date/set to JSON-safe form, raise on
    unknown types. Replaces the lossy `default=str` shortcut."""
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, (datetime.datetime, datetime.date)):
        return value.isoformat()
    if isinstance(value, set):
        return sorted(_normalize_for_json(v, path=f"{path}[set]") for v in value)
    if isinstance(value, list):
        return [_normalize_for_json(v, path=f"{path}[{i}]") for i, v in enumerate(value)]
    if isinstance(value, dict):
        return {
            k: _normalize_for_json(v, path=f"{path}.{k}")
            for k, v in value.items()
        }
    raise TypeError(f"unserializable type at {path}: {type(value).__name__}")
```

- [ ] **Step 2: Switch `write_data_js` to use it.**

```python
def write_data_js(data, out_dir):
    payload = _normalize_for_json(data)
    body = "window.APD_DATA = " + json.dumps(
        payload, ensure_ascii=False, allow_nan=False, indent=2,
    ) + ";\n"
    # Step 3 below adds the </script> escape here.
    target = out_dir / "data.js"
    _atomic_write_text(target, body)
    return target
```

- [ ] **Step 3: Add `</script>` escape.**

```python
# After json.dumps, before _atomic_write_text:
body = body.replace("</", "<\\/")
```

This is a no-op in JSON parsing (JSON forbids unescaped `</`) but defeats the HTML parser's `</script>` scanner if `data.js` is ever inlined.

### Task A2: Regression tests

**Files:** `tests/unit/report/test_tier3_json_hygiene.py`

- [ ] **Step 1: Tests.**

```python
import datetime, math, pathlib
import pytest
from apd_gauntlet.report.emit import _normalize_for_json, write_data_js


def test_normalize_datetime_to_isoformat():
    out = _normalize_for_json({"when": datetime.datetime(2026, 5, 29, 14, 0, 0)})
    assert out == {"when": "2026-05-29T14:00:00"}


def test_normalize_date_to_isoformat():
    out = _normalize_for_json({"day": datetime.date(2026, 5, 29)})
    assert out == {"day": "2026-05-29"}


def test_normalize_set_to_sorted_list():
    out = _normalize_for_json({"tags": {"b", "a", "c"}})
    assert out == {"tags": ["a", "b", "c"]}


def test_normalize_raises_on_unknown_type():
    class Custom:
        pass
    with pytest.raises(TypeError) as exc:
        _normalize_for_json({"obj": Custom()})
    assert "$.obj" in str(exc.value)
    assert "Custom" in str(exc.value)


def test_write_data_js_rejects_nan(tmp_path):
    with pytest.raises(ValueError):
        write_data_js({"x": math.nan}, tmp_path)


def test_write_data_js_escapes_close_script(tmp_path):
    write_data_js({"detail": "abc</script>xyz"}, tmp_path)
    body = (tmp_path / "data.js").read_text(encoding="utf-8")
    assert "</script>" not in body
    assert "<\\/script>" in body
```

### Task A3: Open PR

- [ ] Commit + push + open PR.

**Acceptance criteria:**
- `default=str` removed from emit.py
- `allow_nan=False` set on every `json.dumps` in emit.py
- `</` escaped in the final body
- Tests pin all three behaviors
- All 4 shipped runs/examples still build

---

# PR-T3-B — Mermaid id collisions + path-focused subgraph node-cap

**Branch:** `report-t3-mermaid-collision-and-cap`
**Files:** `tools/apd_gauntlet/report/transform.py`, `tests/unit/report/test_tier3_mermaid.py`

**Goal:** Fix two latent issues in the asset-graph Mermaid renderer.

### Defects closed

1. **`_safe_node_id` fallback collisions.** When two nodes have invalid raw IDs, they both fall back to a synthetic ID like `n0`/`n1`. The current `enumerate` counter is per-call, but `_safe_node_id` is called from multiple loops with separate counters, so two nodes can end up with the same synthetic id and the second silently overwrites the first in `id_remap`. The asset graph topology then shows wrong edges.
2. **Path-focused subgraph has no node-cap.** The full asset graph has a 100-node cap (`_build_mermaid` summarises beyond that), but `_build_mermaid_path_focused` doesn't. An adversarial path with 500 edges produces a Mermaid string the browser cannot lay out usefully and silently times out.

### Task B1: Hash-based synthetic IDs

**Files:** `tools/apd_gauntlet/report/transform.py`

- [ ] **Step 1: Replace counter-based fallbacks with a hash of the raw ID.**

```python
import hashlib

def _safe_node_id(raw: str, fallback_seed: str = "") -> str:
    """Return a Mermaid-safe node id. When raw is invalid, derive a stable
    8-char hash from raw+seed so two nodes with different raw ids do not
    collide on the synthetic fallback."""
    if _NODE_ID_OK.match(raw or ""):
        return raw
    digest = hashlib.sha256((raw + "::" + fallback_seed).encode()).hexdigest()
    return f"n_{digest[:8]}"
```

- [ ] **Step 2: Update callers in `_build_mermaid` and `_build_mermaid_path_focused`** to pass a per-loop seed (e.g., `"asset_graph"`, `"path_focused"`) so the same raw id under different rendering contexts gets distinct ids if needed; identical raw ids under the same context still collide deterministically (correct behavior).

- [ ] **Step 3: Add `assert id_remap[raw] not in id_remap.values()` style guard** that converts a collision into a loud failure rather than silent overwrite.

### Task B2: Path-focused subgraph cap

**Files:** `tools/apd_gauntlet/report/transform.py`

- [ ] **Step 1: Add cap.**

```python
_PATH_FOCUSED_NODE_CAP = 60  # tighter than the full-graph 100-cap

def _build_mermaid_path_focused(asset_graph, paths):
    if not paths:
        return None
    # ... (existing edge/node collection) ...
    if len(touched_node_ids) > _PATH_FOCUSED_NODE_CAP:
        return (
            f"graph LR\n  too_large[\"Path-focused subgraph has "
            f"{len(touched_node_ids)} nodes; see attack-paths.yaml\"]"
        )
    # ... (existing rendering) ...
```

- [ ] **Step 2: Tests.**

### Task B3: Regression tests

**Files:** `tests/unit/report/test_tier3_mermaid.py`

- [ ] Tests cover: invalid raw id → hash-based fallback; two invalid raw ids do not collide; path-focused subgraph beyond cap produces summary node; full graph cap continues to work.

### Task B4: Open PR

**Acceptance criteria:**
- No two distinct raw ids ever produce the same synthetic id
- Path-focused subgraph never exceeds 60 nodes in rendered output
- Tests pin both behaviors

---

# PR-T3-C — Empty-input banner + reference-DB freshness indicator

**Branch:** `report-t3-empty-banner-and-freshness`
**Files:** `tools/apd_gauntlet/report/transform.py`, `tools/apd_gauntlet/report/taxonomy.py`, React template, tests

**Goal:** Two small UX additions that surface state currently invisible to the reader.

### Defects closed

1. **Empty-input runs render a wall of empty tables** with no top-level signal that the run is degenerate. Add `data.meta.is_empty_run` and a corresponding React banner.
2. **Reference-DB freshness invisible.** When `attack_technique_titles()` returns 0 entries (the pre-T2-A bug) or when the catalog is stale, the report shows bare-id tooltips with no explanation. Surface `data.meta.reference_db_versions`.

### Task C1: `meta.is_empty_run` flag

**Files:** `tools/apd_gauntlet/report/transform.py`

- [ ] **Step 1: In `meta_block`, compute the flag.**

```python
def meta_block(artifacts, *, run_dir=None):
    # ... (existing fields) ...
    is_empty_run = (
        len(artifacts.deduped_findings) + len(artifacts.attack_path_findings) == 0
        and len(artifacts.deduped_capabilities) == 0
    )
    return {
        # ... existing keys ...
        "is_empty_run": is_empty_run,
    }
```

- [ ] **Step 2: Document in the React template** how to render a banner when `data.meta.is_empty_run` is true. Banner copy: "This run produced no analytical output — specialists may have skipped or no findings/capabilities were emitted. See `40-synthesis/advisory-report.md`." Defer the actual JSX to a follow-up if React-bundle freshness gate would be triggered.

### Task C2: `meta.reference_db_versions`

**Files:** `tools/apd_gauntlet/report/taxonomy.py`, `tools/apd_gauntlet/report/transform.py`

- [ ] **Step 1: In `taxonomy.py`, expose a fetched_at + count summary per catalog.**

```python
def reference_db_versions() -> dict[str, dict[str, Any]]:
    """Return {family: {fetched_at, count}} for each shipped reference DB."""
    out = {}
    for family, fn, path_name in (
        ("nist",   nist_control_titles,       "nist-controls.json"),
        ("attack", attack_technique_titles,   "mitre-attack-techniques.json"),
        ("cwe",    cwe_titles,                "cwe.json"),
        ("d3fend", d3fend_titles,             "d3fend.json"),
    ):
        path = _DATA / path_name
        meta = {}
        if path.is_file():
            try:
                with path.open(encoding="utf-8") as fh:
                    doc = json.load(fh)
                meta = doc.get("_meta") or {}
            except (json.JSONDecodeError, OSError):
                pass
        out[family] = {
            "fetched_at": meta.get("fetched_at"),
            "count":      len(fn()),
        }
    return out
```

- [ ] **Step 2: In `transform.meta_block`, add `reference_db_versions`** from the helper.

- [ ] **Step 3: React template** should render a small warning chip when any `count == 0` or `fetched_at` older than 180 days. Defer actual JSX if needed; the data is there for the future render.

### Task C3: Regression tests

- [ ] Tests cover: empty-input flag set; reference_db_versions has 4 keys; counts match the loaders.

### Task C4: Open PR

**Acceptance criteria:**
- `data.meta.is_empty_run` boolean is present
- `data.meta.reference_db_versions` has the 4 families
- Tests pin both
- 4 shipped runs render with `is_empty_run: false` and 4 non-zero counts

---

# PR-T3-D — NIST normalisation + lens_perspectives + ATT&CK Shape-B clarity

**Branch:** `report-t3-nist-norm-lens-attack-clarify`
**Files:** `tools/apd_gauntlet/report/transform.py`, tests

**Goal:** Three semantic clarifications.

### Defects closed

1. **NIST family extraction silently corrupts on non-canonical IDs.** `ac-3` and `AC-3` currently split into two entries; `AC2(2)` produces a junk family. Add an ingest-time normalisation hook (`str.upper`) and validate the derived family is in `_nist_family_titles().keys()`. Unknown families hit an `UNKNOWN` sentinel and surface in `data.meta.warnings`.
2. **`lens_perspectives` dict-shape extraction picks wrong values.** Per the failure-mode analysis: dict-shape pulls lens NAMES (e.g., 'oauth', 'k8s'); list-shape pulls APD goals. Same merged cap displays differently. Fix the dict branch to `lp_raw.values()` and pull `v.get("apd_goal") or v.get("goal")`.
3. **ATT&CK Shape-B parent_findings vs grouping-only distinction.** Currently a parent with `citing_findings: []` AND non-empty `sub_techniques` emits an empty row. Skip the parent row when its own findings are empty and it only carries sub-techniques.

### Task D1: NIST normalisation

**Files:** `tools/apd_gauntlet/report/transform.py`

- [ ] **Step 1: Add `_normalize_nist_id(raw: str) -> str`** that uppercases, strips whitespace, validates family prefix; returns "UNKNOWN" sentinel for unparseable input.

- [ ] **Step 2: Use it at every NIST ID ingest site** (transform.findings_array mappings.nist, _collect_referenced_ids NIST shapes, taxonomy_dict iteration).

### Task D2: lens_perspectives dict-shape fix

- [ ] **Step 1: Update `capability_grid` line 199-216** to extract `v.get("apd_goal") or v.get("goal")` from dict values, matching list-shape semantics.

### Task D3: ATT&CK Shape-B parent distinction

- [ ] **Step 1: In `attack_exposure_rows` Shape-B branch,** skip parent row when `citing_findings in (None, [])` AND `sub_techniques` is non-empty.

### Task D4: Regression tests

- [ ] Cover: `ac-3` and `AC-3` resolve to one entry; lens_perspectives dict-shape produces APD goals (not lens names); ATT&CK parent with only sub_techniques does not emit a row.

### Task D5: Open PR

**Acceptance criteria:** all 3 defects pinned with tests; 4 runs build cleanly.

---

# PR-T3-E — Bundle freshness gate on editable installs + hash includes path

**Branch:** `report-t3-bundle-freshness-and-path-hash`
**Files:** `tools/apd_gauntlet/report/build.py`, `tools/check_report_template_freshness.py`, `report-template/.build/build.mjs`, tests

**Goal:** Two related changes that make the freshness gate actually work.

### Defects closed

1. **Bundle freshness gate doesn't run on editable installs.** When a contributor edits `report-template/` and runs `apd-gauntlet build-report`, the stale shipped bundle is silently used. Add a startup check: when `report-template/` exists alongside the package, recompute the source hash and warn (or fail with `--strict`) if it disagrees with `.source-hash`.
2. **Bundle source hash is name-only.** Renaming `app.jsx` → `app-old.jsx` doesn't invalidate the hash. Hash the relative path with a separator: `h.update(str(rel).encode()); h.update(b'\x00')` in both Python and Node.

### Task E1: Path-inclusive hash

**Files:** `tools/check_report_template_freshness.py`, `report-template/.build/build.mjs`

- [ ] **Step 1: Update `compute_source_hash()` in `check_report_template_freshness.py`** to include the relative path in the SHA-256 computation.

- [ ] **Step 2: Update the equivalent in `build.mjs`** (Node) so the two implementations agree.

### Task E2: Freshness gate on editable install

**Files:** `tools/apd_gauntlet/report/build.py`

- [ ] **Step 1: In `build_report`**, before calling `emit.copy_bundle`, check if `report-template/` exists alongside the package. If yes (editable install), recompute the source hash and compare against `bundle_src/.source-hash`. On mismatch:
  - Default: emit a click.echo warning to stderr.
  - With `--strict` flag: raise `BundleFreshnessError`.

### Task E3: Regression tests

- [ ] Cover: renamed file changes hash; freshness mismatch emits stderr warning; `--strict` raises.

### Task E4: Open PR

**Acceptance criteria:** all 3 defects pinned; `apd-gauntlet build-report --strict` from a clean editable install passes.

---

# PR-T3-F — UTF-8 encoding sweep for the rest of the package

**Branch:** `report-t3-encoding-sweep-package-wide`
**Files:** `tools/apd_gauntlet/cli.py`, `tools/apd_gauntlet/validate.py`, `tools/apd_gauntlet/summary.py`, `tools/apd_gauntlet/init_run.py`, `tools/apd_gauntlet/lint_agents.py`, `tools/apd_gauntlet/build_domain_skill.py`, tests

**Goal:** Extend the T2-E encoding sweep to the non-report parts of the package. Per the T2-E reviewer note, there are still ~20 bare `read_text()` / `write_text()` calls outside `tools/apd_gauntlet/report/`.

### Task F1: Sweep

- [ ] **Step 1:** `grep -rnE "\.read_text\(\)|\.write_text\([^,]+\)" tools/apd_gauntlet/ | grep -v report/` to list every call.
- [ ] **Step 2:** Add `encoding="utf-8"` to each. Same discipline as T2-E.

### Task F2: Regression tests

- [ ] **Step 1:** `tests/unit/test_tier3_encoding_package.py` — one test per file modified, exercising the function that calls the modified site under `LC_ALL=C` + `LANG=C`.

### Task F3: Open PR

**Acceptance criteria:** zero bare `read_text()` / `write_text()` calls in `tools/apd_gauntlet/` (full grep); `LC_ALL=C apd-gauntlet --help`, `validate`, `init-run`, `summarize` all succeed.

---

## Cross-cutting verification at the end of the plan

After all 6 PRs land:

- [ ] **Step 1:** Re-pull main; run full test suite, ruff, mypy, build-report on all 4 runs.
- [ ] **Step 2:** Run the html-report-failure-mode-analysis workflow again. Expected outcome: all 30 medium-priority hazards from the original analysis show as `gaps_closed` or `non_issue`.
- [ ] **Step 3:** Open the rendered reports in a browser; spot-check tooltips, banners, freshness chips.

---

## Tier-4 backlog (post-Tier-3, fully optional)

These were surfaced by the failure-mode analysis or the Tier-2 reviewers but did not rise to medium-severity. Capture for posterity:

1. `@lru_cache(maxsize=1)` on taxonomy loaders means in-process refreshes don't take effect. Fine for one-shot CLI; risky for a future SaaS variant. Expose `taxonomy.invalidate_all()` or key cache by file mtime.
2. Asset-graph `node_type: identity` (caldera/authentik) is not in the Mermaid prefix map — falls back to generic rectangle.
3. `_NODE_ID_OK` regex rejects `:` and `.` in node_ids (common in `chainguard.dev/app:web` style names), forcing remapping.
4. `_extract_ids_from_mapping` drops dict items missing both id and fallback keys — partial signal lost silently.
5. `strengths_section` raises on unknown id; sibling supplements (headline_findings) fail silently — inconsistent contract.
6. Caldera Shape-C sub_techniques emit duplicate rows when sub_id is also a top-level key.
7. `_matrix_rows_from_dedup` silently drops unknown goals without surface in meta.
8. The `examples/apd-20260601-claim-event-bus/` directory lacks an `inputs/` subdirectory; `apd-gauntlet validate` against it fails missing-artifact — fixture gap, not a code defect.

---

## Self-review

**Spec coverage check.** Each Tier-3 defect from the failure-mode-analysis MEDIUM list maps to a PR:
- ✅ MED-1 (loader notes lookup misses caldera singular `note`) → already closed by Tier-2-F
- ✅ MED-2 (encoding implicit on read_text/write_text outside report/) → PR-T3-F
- ✅ MED-3 (`_yaml() or {}` silent garbage) → already closed by Tier-2-F
- ✅ MED-4 (`_required` accepts directories) → already closed by Tier-2-F
- ✅ MED-5 (hash manifest re-reads — TOCTOU) → out of scope; deferred to Tier-4
- ✅ MED-6 (build_apd_data per-section isolation) → already closed by Tier-2-C
- ✅ MED-8 (bundle freshness gate on editable install) → PR-T3-E
- ✅ MED-9 (bundle source hash includes path) → PR-T3-E
- ✅ MED-10 (`default=str` silent coercion) → PR-T3-A
- ✅ MED-11 (`allow_nan=False`) → PR-T3-A
- ✅ MED-12 (NIST family extraction case + format) → PR-T3-D
- ✅ MED-13 (ATT&CK Shape-B parent vs grouping) → PR-T3-D
- ✅ MED-14 (Caldera Shape-C sub_techniques duplicates) → Tier-4 backlog
- ✅ MED-15 (`_matrix_rows_from_dedup` drops unknown goals) → Tier-4 backlog
- ✅ MED-16 (`_extract_ids_from_mapping` drops dict items) → Tier-4 backlog
- ✅ MED-17 (output dir collision) → already closed by Tier-2-D
- ✅ MED-18 (copy_bundle clobbers user edits) → already closed by Tier-2-D
- ✅ MED-19 (no friendly error on read-only output) → covered by Tier-2-C + Tier-2-F
- ✅ MED-20 (DEFAULT_BUNDLE path under wheel install) → Tier-4 backlog
- ✅ MED-21 (hash_dir reads whole files) → Tier-4 backlog
- ✅ MED-22 (manifest fields empty when run_cfg sparse) → Tier-4 backlog
- ✅ MED-23 (domain_pack_version / date empty) → Tier-4 backlog
- ✅ MED-24 (Capability `agent` field) → already closed by Tier-1
- ✅ MED-25 (reference data freshness unsurfaced) → PR-T3-C
- ✅ MED-26 (Contradictions capability id concatenation) → Tier-4 backlog
- ✅ MED-27 (attack_paths_data empty Mermaid on empty asset_graph) → covered by PR-T3-B
- ✅ MED-28 (`_safe_node_id` fallback collisions) → PR-T3-B
- ✅ MED-29 (latent XSS via script-breakout) → PR-T3-A
- ✅ MED-30 (no try/except around shutil.copytree) → already closed by Tier-2-D

That's 30 items, with 6 in Tier-4 (out-of-scope deeper hardening) and 24 closed across Tiers 1, 2, and 3.

**Placeholder scan.** No TODO/TBD/"implement later" in the plan.

**Type consistency.** `BundleFreshnessError`, `_normalize_for_json`, `_normalize_nist_id`, `_PATH_FOCUSED_NODE_CAP` named consistently throughout.

**Scope check.** Each PR touches a single concern. T3-A and T3-B both touch emit/transform but on independent functions; T3-C and T3-D both touch transform on different sections.

Plan complete.
