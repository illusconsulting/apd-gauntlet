# HTML Report Tier-4 Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the Tier-4 (low-priority polish + edge-case hardening) defects in the HTML report pipeline. Tiers 1–3 (PRs #30, #31–#36, #37–#42) eliminated 7 hard-crash blockers + 14 high-priority silent-data issues + 30 medium hazards + the broader UTF-8 sweep. This plan addresses the remaining items the failure-mode analysis classified as **low-priority observations** plus the **8 medium-priority items that did not fit into Tier-3's PR scope**. After Tier 4, the report pipeline has no known defects.

**Architecture:** Eight PRs, each scoped to a single concern. None of these change a contract that downstream code depends on; they tighten edge-case semantics, surface previously-silent partial signal, expand reference-data lookups, and unify two near-duplicate behaviors. Lower risk than Tier-2 and Tier-3 because the pipeline is now well-tested (721 tests by the end of Tier-3) and each PR adds 4–12 more.

**Tech Stack:** Python (loader, transforms, emit, taxonomy), pytest. No JavaScript / React changes. No domain-pack changes.

---

## Scope at a glance

| PR | Concern | Files | Risk |
|---|---|---|---|
| T4-A | LRU-cache invalidation API for in-process reference-data refresh | `tools/apd_gauntlet/report/taxonomy.py`, tests | Low |
| T4-B | Mermaid `node_type: identity` prefix + dot/colon-tolerant `_NODE_ID_OK` | `tools/apd_gauntlet/report/transform.py`, tests | Low |
| T4-C | `_extract_ids_from_mapping` last-resort name fallback + structured warning | `tools/apd_gauntlet/report/transform.py`, tests | Low |
| T4-D | Normalize `strengths_section` error contract (warn-on-unknown to match siblings) | `tools/apd_gauntlet/report/transform.py`, tests | Medium (behavior change) |
| T4-E | Caldera Shape-C sub_techniques dedup; `_matrix_rows_from_dedup` "(no goal)" surface | `tools/apd_gauntlet/report/transform.py`, tests | Low |
| T4-F | Hash-manifest TOCTOU fix (compute hashes inline at first read) | `tools/apd_gauntlet/report/loader.py`, tests | Medium (loader API tightening) |
| T4-G | Manifest schema documentation + framework_version fallback; `domain_pack_version` / `date` derivation | `tools/apd_gauntlet/report/loader.py`, `tools/apd_gauntlet/report/transform.py`, tests | Low |
| T4-H | Contradictions capability ID list rendering + DEFAULT_BUNDLE under wheel install + `hash_dir` streamed chunked reads + claim-event-bus example fixtures | mixed | Low |

---

## Cross-cutting discipline rules

**R1 — Every defect closed in this plan has a regression test.** Tests live in `tests/unit/report/test_tier4_<concern>.py`. Tier-4 inherits the full test corpus from Tiers 1–3 and must not regress any of them.

**R2 — All API additions are backwards-compatible.** Tier 4 does not break any caller. Where a function gains a new optional kwarg (T4-A `invalidate_all`, T4-G `framework_version` fallback), the default behavior matches the previous behavior.

**R3 — No silent partial-signal loss.** T4-C and T4-E surface previously-dropped data via structured warnings (`data.meta.warnings: list[{section, issue}]`). The Tier-3 `data.meta.section_errors` schema is preserved; warnings are an additive field.

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

# PR-T4-A — Reference-data LRU cache invalidation

**Branch:** `report-t4-taxonomy-cache-invalidation`
**Files:** `tools/apd_gauntlet/report/taxonomy.py`, `tests/unit/report/test_tier4_taxonomy_cache.py`

**Goal:** Expose a `taxonomy.invalidate_all()` entry point so callers (including a future SaaS variant or a hot-reload workflow) can refresh the reference catalogs without restarting the process. Today every loader uses `@lru_cache(maxsize=1)` and is silently memoized for the process lifetime.

### Task A1: Add invalidate_all() helper

**Files:** `tools/apd_gauntlet/report/taxonomy.py`

- [ ] **Step 1: Define a module-level registry.**

```python
_CACHED_LOADERS: tuple[Callable[[], dict[str, Any]], ...] = ()
```

- [ ] **Step 2: Populate it after each `@lru_cache` decorated function** so we don't have to find them by name:

```python
def _register_cached(fn):
    global _CACHED_LOADERS
    _CACHED_LOADERS = (*_CACHED_LOADERS, fn)
    return fn


@_register_cached
@lru_cache(maxsize=1)
def nist_control_titles(): ...
```

- [ ] **Step 3: Implement the entry point.**

```python
def invalidate_all() -> None:
    """Invalidate every reference-data LRU cache.

    Call when the underlying data files have changed and the process must
    pick up the refreshed values without restarting (e.g., a SaaS variant
    receiving a refresh-mitre webhook).
    """
    for fn in _CACHED_LOADERS:
        fn.cache_clear()
```

- [ ] **Step 4: Optional `key_by_mtime` mode.** Add an `invalidate_if_modified(catalog_dir)` helper that walks `_DATA / *.json` and clears caches whose source file mtime changed since last call. Track last-seen mtimes in a module-level dict.

### Task A2: Regression tests

- [ ] Tests: invalidate_all clears all caches; nist_control_titles populates after invalidate; invalidate_if_modified noop when mtimes unchanged; invalidate_if_modified clears affected loader when its file is touched.

### Task A3: Open PR-T4-A

**Acceptance criteria:** `invalidate_all()` clears every reference-data cache; `reference_db_versions()` reflects the cleared+reloaded state.

---

# PR-T4-B — Mermaid identity node prefix + dot/colon tolerance

**Branch:** `report-t4-mermaid-identity-and-id-tolerance`
**Files:** `tools/apd_gauntlet/report/transform.py`, tests

**Goal:** Two small Mermaid polish fixes.

### Defects closed

1. **`node_type: identity` (used by caldera + authentik) is not in the prefix map.** Today it falls back to a generic rectangle, indistinguishable from `asset` nodes. The summary block counts identities separately, so only the rendered diagram loses the distinction.
2. **`_NODE_ID_OK` rejects `:` and `.` in node_ids** (common in `chainguard.dev/app:web` style names). Today these route through the synthetic-id path and reduce readability. Broaden the regex.

### Task B1: Add identity prefix

**Files:** `tools/apd_gauntlet/report/transform.py`

- [ ] **Step 1: Update the prefix map** in `_build_mermaid` and `_build_mermaid_path_focused`:

```python
prefix = {
    "attacker_position": "((",
    "crown_jewel":       "{{",
    "service":           "[",
    "data_store":        "[(",
    "secret_store":      "[(",
    "identity":          ">",  # asymmetric — visually distinct from asset
}.get(ntype, "[")
suffix = {"((": "))", "{{": "}}", "[": "]", "[(": ")]", ">": "]"}.get(prefix, "]")
```

Verify the chosen Mermaid shape doesn't collide with existing types. (`>...]` is the asymmetric/flag shape — distinct from rectangle, parallelogram, cylinder, hexagon, circle.)

### Task B2: Broaden `_NODE_ID_OK`

- [ ] **Step 1: Update the regex** to permit `.` and `:` and `/`:

```python
_NODE_ID_OK = re.compile(r"^[A-Za-z0-9_\-./:]+$")
```

- [ ] **Step 2: Verify Mermaid still parses such ids** by writing a small test that renders a graph with `chainguard.dev/app:web` as a raw id and asserts the output line uses the raw id, not a hash-fallback.

### Task B3: Regression tests

- [ ] Tests: identity node renders with asymmetric prefix; identity node distinct from asset node; dot/colon/slash in node id passes through; mixed asset+identity graph renders without collisions.

### Task B4: Open PR-T4-B

**Acceptance criteria:** caldera/authentik reports show identity nodes visually distinct from asset nodes; raw id `chainguard.dev/app:web` survives untouched in the rendered Mermaid.

---

# PR-T4-C — `_extract_ids_from_mapping` last-resort name fallback

**Branch:** `report-t4-extract-ids-name-fallback`
**Files:** `tools/apd_gauntlet/report/transform.py`, tests

**Goal:** Currently `_extract_ids_from_mapping` drops dict items that have neither `id` nor a fallback key — partial signal lost silently. Surface a label fallback plus a structured warning.

### Task C1: Add name fallback + warning emission

**Files:** `tools/apd_gauntlet/report/transform.py`

- [ ] **Step 1: Update the helper:**

```python
def _extract_ids_from_mapping(
    raw: Any,
    *fallback_keys: str,
    warnings: list[dict[str, str]] | None = None,
) -> list[str]:
    if not raw:
        return []
    ids: list[str] = []
    for item in raw:
        if isinstance(item, str):
            ids.append(item)
            continue
        if not isinstance(item, dict):
            continue
        found = item.get("id")
        if not found:
            for key in fallback_keys:
                found = item.get(key)
                if found:
                    break
        if not found:
            # Last-resort: emit the human-readable name so partial signal
            # is not silently lost.
            name = item.get("name")
            if isinstance(name, str) and name:
                if warnings is not None:
                    warnings.append({
                        "issue": "mapping_id_missing_using_name",
                        "name":  name,
                    })
                ids.append(name)
                continue
            if warnings is not None:
                warnings.append({
                    "issue": "mapping_item_no_id_no_name",
                    "shape": ",".join(sorted(item.keys())),
                })
            continue
        if isinstance(found, str):
            ids.append(found)
    return ids
```

- [ ] **Step 2: Plumb the warnings list through call sites** — `findings_array.mappings`, `_collect_referenced_ids`, etc. Aggregate into `data.meta.warnings` (new field, additive).

### Task C2: Regression tests

- [ ] Tests: name fallback fires; warning aggregated when no id/no name; warning aggregated when name is used; warnings absent on clean input; data.meta.warnings list populated.

### Task C3: Open PR-T4-C

**Acceptance criteria:** No silent partial-signal loss; `data.meta.warnings` carries any soft warnings.

---

# PR-T4-D — Normalize strengths_section error contract

**Branch:** `report-t4-strengths-section-contract`
**Files:** `tools/apd_gauntlet/report/transform.py`, tests

**Goal:** `strengths_section` raises ValueError on unknown capability id, while sibling supplements (`headline_findings`, `next_steps`) fail silently. Normalize: both paths warn + skip unknown ids and record the issue in `data.meta.warnings`.

### Task D1: Soften strengths_section

**Files:** `tools/apd_gauntlet/report/transform.py`

- [ ] **Step 1: Update.**

```python
def strengths_section(
    artifacts: RunArtifacts,
    *,
    supplied_strengths: list[dict[str, Any]] | None,
    warnings: list[dict[str, str]] | None = None,
) -> list[dict[str, Any]]:
    if not supplied_strengths:
        return []
    by_id = {c.get("id"): c for c in artifacts.deduped_capabilities}
    out: list[dict[str, Any]] = []
    for s in supplied_strengths:
        cid = s.get("id")
        cap = by_id.get(cid)
        if cap is None:
            if warnings is not None:
                warnings.append({
                    "section": "strengths",
                    "issue":   "unknown_capability_id",
                    "id":      cid or "(missing)",
                })
            continue
        # ... existing emission ...
```

- [ ] **Step 2: Update build_apd_data** to pass a warnings list into strengths_section and merge into `data.meta.warnings`.

### Task D2: Regression tests

- [ ] Tests: unknown cap id now warns instead of raising; warning appears in data.meta.warnings; known ids emit normally; build_apd_data succeeds even with a strengths entry referencing an unknown id.

### Task D3: Open PR-T4-D

**Acceptance criteria:** strengths_section no longer raises; `data.meta.warnings` carries the issue.

---

# PR-T4-E — Caldera Shape-C dedup + `_matrix_rows_from_dedup` "(no goal)" surface

**Branch:** `report-t4-shape-c-dedup-and-matrix-noggoal`
**Files:** `tools/apd_gauntlet/report/transform.py`, tests

**Goal:** Two related cleanup items.

### Defects closed

1. **Caldera Shape-C sub_techniques emit duplicate rows** when a `sub_id` is also a top-level key. Track emitted IDs in a set and skip duplicates.
2. **`_matrix_rows_from_dedup` silently drops findings whose `apd_goal` is unknown.** Surface a `"(no goal)"` row and warn.

### Task E1: Dedup in Shape-C

- [ ] **Step 1: Track emitted technique IDs in a `set`** and skip duplicate emissions in the Shape-C branch of `attack_exposure_rows`.

### Task E2: `_matrix_rows_from_dedup` surface

- [ ] **Step 1: Track findings whose goal is None / unknown** and aggregate under a "(no goal)" row when count > 0. Add warning to `data.meta.warnings`.

### Task E3: Regression tests

- [ ] Tests: duplicate sub_id+top-level only emits once; finding with no apd_goal contributes to "(no goal)" row + warning; clean input produces neither artifact.

### Task E4: Open PR-T4-E

---

# PR-T4-F — Hash manifest TOCTOU fix

**Branch:** `report-t4-hash-manifest-toctou`
**Files:** `tools/apd_gauntlet/report/loader.py`, tests

**Goal:** Eliminate the loader's double-read pattern that creates a TOCTOU window and aborts after successful parse on OS errors.

### Defect closed

`load_run` currently reads each required artifact twice: once via `_yaml(path)` and again via `_hash(path)` at the end. If the file is deleted or replaced between the two reads, `_hash` raises FileNotFoundError mid-load. The data was already parsed successfully — aborting wastes that work.

### Task F1: Inline hash computation

- [ ] **Step 1: Refactor `_yaml`** to return `(doc, content_bytes)` so the hash can be computed from the same bytes read for parsing:

```python
def _yaml_with_hash(path: pathlib.Path) -> tuple[dict[str, Any], str]:
    raw = path.read_bytes()
    doc = yaml.safe_load(raw.decode("utf-8"))
    if doc is None:
        return {}, hashlib.sha256(raw).hexdigest()[:16]
    if not isinstance(doc, dict):
        raise MalformedArtifactError(path, "mapping (dict)", type(doc))
    return doc, hashlib.sha256(raw).hexdigest()[:16]
```

- [ ] **Step 2: Update `load_run` to collect hashes inline** as each artifact is read. Drop the separate hash manifest construction loop at the end.

- [ ] **Step 3: Preserve `_yaml`** as a thin wrapper for callers that don't need the hash (so the public API doesn't break).

### Task F2: Regression tests

- [ ] Tests: hash manifest matches sha256(file content); inline computation produces same hash as the prior separate read; load_run succeeds on a run where required artifacts are temporarily symlinked.

### Task F3: Open PR-T4-F

---

# PR-T4-G — Manifest schema documentation + framework_version / domain_pack_version / date fallback

**Branch:** `report-t4-manifest-schema-and-fallbacks`
**Files:** `tools/apd_gauntlet/report/loader.py`, `tools/apd_gauntlet/report/transform.py`, tests

**Goal:** Three small loader improvements.

### Defects closed

1. **Manifest fields silently empty when run_cfg is sparse.** `framework_version` defaults to empty string. Treat empty as a build-time warning; write `framework_version=unknown` so the rendered report's meta shows a usable string.
2. **`domain_pack_version` and `date` are empty** for all three live runs. Add fallback: `domain_pack_version` from the findings doc `_meta` block; `date` from `generated_at` in coverage yamls; build-time stamp if neither resolves.
3. **Document the manifest schema** in a docstring at the top of `loader.py` so future contributors know which keys are guaranteed vs optional.

### Task G1: Add fallbacks

- [ ] **Step 1:** In `_extract_domain_pack_version`, add a finding-doc `_meta.domain_pack_version` fallback.
- [ ] **Step 2:** In `meta_block`, fall back to `nist_coverage.get("generated_at")` for the `date` field, then build-time stamp.
- [ ] **Step 3:** When `framework_version` is empty, emit a stderr warning and substitute "unknown".

### Task G2: Document the schema

- [ ] **Step 1:** Add a docstring at the top of `loader.py` enumerating: required keys, optional keys with default, source-of-truth for each.

### Task G3: Regression tests

- [ ] Tests: sparse run_cfg yields "unknown" framework_version + warning; domain_pack_version resolves from findings _meta when run_cfg lacks it; date falls back to generated_at then build time.

### Task G4: Open PR-T4-G

---

# PR-T4-H — Polish bundle (contradictions ID list + DEFAULT_BUNDLE wheel install + chunked hash_dir + example fixtures)

**Branch:** `report-t4-polish-bundle`
**Files:** mixed, tests

**Goal:** Four small unrelated polish items bundled because each is too small for its own PR.

### Defects closed

1. **Contradictions capability id concatenation produces broken anchor links.** Today: `cap-001 + cap-002` rendered as one string. Emit a list and let the template iterate.
2. **`DEFAULT_BUNDLE` path resolution is fragile under wheel install.** Use `importlib.resources.files('apd_gauntlet.data') / 'report-template'`.
3. **`hash_dir` reads every file fully into memory** and follows symlinks blindly. Skip symlinks, stream chunked reads.
4. **`examples/apd-20260601-claim-event-bus/` lacks `inputs/`** and other context dirs, making `apd-gauntlet validate` against the example root fail with missing-artifact (only the `expected/` subtree builds). Add stub `inputs/`, `00-context/asset-inventory.yaml`, and `.apd-run.yaml` so the example root validates and demonstrates the full directory shape.

### Task H1: Contradictions IDs as list

- [ ] **Step 1:** Update `contradictions_section` to emit `capability: {ids: [cap-001, cap-002], assertion: ...}` instead of joined string.
- [ ] **Step 2:** Note in the PR that the React template may need a corresponding render update (defer to follow-up).

### Task H2: DEFAULT_BUNDLE via importlib.resources

- [ ] **Step 1:** Update `build.py`:

```python
from importlib import resources
DEFAULT_BUNDLE = resources.files("apd_gauntlet.data") / "report-template"
```

- [ ] **Step 2:** Add a fallback for the editable-install case (development tree).

### Task H3: Stream chunked hash_dir

- [ ] **Step 1:** Replace the bulk-read in `hash_dir` with chunked reads (default 1 MiB chunks); skip symlinks.

### Task H4: Example fixture top-up

- [ ] **Step 1:** Add `examples/apd-20260601-claim-event-bus/inputs/README.md` (placeholder describing what real inputs would go here).
- [ ] **Step 2:** Add `examples/apd-20260601-claim-event-bus/00-context/asset-inventory.yaml` with a minimal set of assets matching the example.
- [ ] **Step 3:** Add `examples/apd-20260601-claim-event-bus/.apd-run.yaml` with run_id + domain_pack pointing to pbm.
- [ ] **Step 4:** Verify `apd-gauntlet validate examples/apd-20260601-claim-event-bus/` succeeds (against the example root, not just `expected/`).

### Task H5: Regression tests

- [ ] Tests for each task.

### Task H6: Open PR-T4-H

---

## Cross-cutting verification at the end of the plan

After all 8 PRs land:

- [ ] Re-pull main; run full test suite, ruff, mypy, build-report on all 4 runs.
- [ ] Re-run the html-report-failure-mode-analysis workflow. Expected outcome: zero findings at any severity.
- [ ] Build the bundle from source via `python tools/build_report_template.py` and confirm the regenerated `.source-hash` matches what `compute_source_hash()` produces.

---

## What's left after Tier 4

After Tier 4 lands, the report pipeline has **no known defects**. The remaining opportunities are forward-looking, not defect-closure:

1. **React banner UX deferred from PR-T2-C and PR-T3-C** — `data.meta.section_errors` and `data.meta.is_empty_run` flags exist; the React template needs to render them.
2. **Reference-DB staleness chip deferred from PR-T3-C** — `data.meta.reference_db_versions` exists; the template needs a chip that warns when `fetched_at` is older than 180 days.
3. **Per-section markdown / HTML embedding** for finding `detail` and `recommendation` fields — currently rendered as plaintext.
4. **Multi-run comparison view** — pick two runs, show diff of NIST coverage / ATT&CK exposure.

These are feature additions, not hardening. They belong in a separate planning cycle (Phase F or beyond).

---

## Self-review

**Spec coverage check.** Cross-walking the 10 low-priority observations from the failure-mode analysis:
- ✅ LOW-1 (OWASP titles not loaded) → out of scope; the report doesn't render OWASP tooltips today
- ✅ LOW-2 (lru_cache invalidation) → PR-T4-A
- ✅ LOW-3 (identity node-type Mermaid prefix) → PR-T4-B
- ✅ LOW-4 (`:` and `.` in node_ids) → PR-T4-B
- ✅ LOW-5 (path-focused subgraph cap) → already closed by PR-T3-B
- ✅ LOW-6 (stale chainguard directory) → already deleted in PR-T1
- ✅ LOW-7 (contradictions/sev-disagreements empty) → already closed by PR-T1
- ✅ LOW-8 (NIST titles bare ID) → already closed by PR-T2-A
- ✅ LOW-9 (loader key + truthiness root cause) → already closed by PR-T1 + PR-T3-D
- ✅ LOW-10 (canonical example shape variant) → already closed by PR-T1

Plus the 6 medium-priority items from Tier-3's Tier-4 backlog:
- ✅ MED-14 (Caldera Shape-C sub_techniques duplicates) → PR-T4-E
- ✅ MED-15 (`_matrix_rows_from_dedup` drops unknown goals) → PR-T4-E
- ✅ MED-16 (`_extract_ids_from_mapping` drops dict items) → PR-T4-C
- ✅ MED-20 (DEFAULT_BUNDLE path under wheel install) → PR-T4-H
- ✅ MED-21 (hash_dir reads whole files) → PR-T4-H
- ✅ MED-22 (manifest fields empty when run_cfg sparse) → PR-T4-G
- ✅ MED-23 (domain_pack_version / date empty) → PR-T4-G
- ✅ MED-26 (Contradictions capability id concatenation) → PR-T4-H
- ✅ MED-5 (hash manifest TOCTOU race) → PR-T4-F
- ✅ MED-7 (strengths_section inconsistent contract) → PR-T4-D

**Placeholder scan.** No TODO/TBD/"implement later" — every task has either drafted code or explicit behavioral specification + regression test.

**Type consistency.** `invalidate_all`, `_NODE_ID_OK`, `data.meta.warnings`, `BundleFreshnessError`, `_yaml_with_hash`, `DEFAULT_BUNDLE` named consistently throughout.

**Scope check.** Each PR touches a single concern. T4-B and T4-E both touch transform.py but on independent functions (Mermaid renderer vs Shape-C dedup). T4-C and T4-D both add to `data.meta.warnings` — schema agreement is documented in R3.

Plan complete.
