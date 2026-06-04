# Threat-model report scene — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a dedicated **Threat model** scene to the HTML report (after Coverage, before Attack paths) that surfaces the threat model and its coverage with relevant visualizations, and is omitted entirely when no threat model exists.

**Architecture:** All block data is shaped + unit-tested in Python (`report/transform.py` + `report/loader.py`); a new `screens/ThreatModel.jsx` renders it, reusing the report's existing CSS classes and shared components. The Mermaid surface map reuses a shared `MermaidGraph` component extracted from `AttackPaths.jsx`. The tab is gated on `data.threat_model.present`.

**Tech Stack:** Python 3.10+ (pytest, ruff, mypy), React (UMD, JSX compiled by esbuild via `tools/build_report_template.py`), Mermaid, YAML fixtures.

**Spec:** `docs/superpowers/specs/2026-06-03-threat-model-report-scene-design.md`

---

## Design-language consistency contract (REQUIRED — do not invent new styling)

The new scene MUST reuse the report's existing tokens, classes, and components. Use these and **only** these patterns; add new CSS only where this plan says so (one class: `matrix-cell--partial`; one rename: graph classes).

- **Headers:** `<div className="section-eyebrow">…</div>` + `<h2 className="section-title">…</h2>` (as in every screen).
- **Sub-tabs (if used):** `cov-tabs` / `cov-tab` / `cov-tab--active` (from `Coverage.jsx`).
- **Block A matrix:** `<table className="apd-matrix">` with `<span className={`matrix-cell matrix-cell--${cls}`}>` where `cls ∈ {covered, gapped, both, silent, partial}`; `legend` + `legend__swatch` with `--cell-*` tokens.
- **Block B / C tables:** `<table className="attack-table">` (or `nist-table`); numeric cells `className="num"`; `coverage-bar` + `seg-covered`/`seg-both`/`seg-gapped` for proportion bars; `cov-cell cov-cell--{covered,gapped,both,silent}` for status chips.
- **Block D graph:** the shared `MermaidGraph` component (Task 8) + `report-graph__wrapper/__toolbar/__canvas` classes.
- **Block E comparator:** `contradiction`, `contradiction__col`, `contradiction__label`, `contradiction__assertion`, `contradiction__id`.
- **Shared atoms (from `components.jsx`, already on `window`):** `SeverityPill`, `CopyPill`, `TaxonomyTag`, `TagRow`, `GOAL_LABELS`.
- **Tokens (from `styles.css`):** `--ink`, `--ink-2`, `--ink-3`, `--paper`, `--paper-2`, `--rule`, `--accent`, `--accent-soft`, `--sev-high`, `--sev-low`, `--radius-sm`, `--space-1..4`, `--text-xs`, `--text-sm`, `--font-mono`, `--line-loose`, `--cell-{covered,both,gapped,silent}` (+ `*-text`).
- **Empty states:** `empty-state` / `empty-state--info`.

---

## File structure

- `tools/apd_gauntlet/report/loader.py` — load the evaluator coverage artifact (Task 1).
- `tools/apd_gauntlet/report/transform.py` — extend `threat_model_block`; add `_tm_*` helpers + `_build_threat_surface_mermaid` (Tasks 2–6); wire `meta.has_threat_model` (Task 2).
- `tools/apd_gauntlet/synthesis/audit.py` — `threat_model_scene_coherent` check (Task 7).
- `report-template/components.jsx` — add shared `MermaidGraph` (Task 8).
- `report-template/screens/AttackPaths.jsx` — refactor to use `MermaidGraph` (Task 8).
- `report-template/screens/ThreatModel.jsx` — **new** scene (Task 9).
- `report-template/app.jsx` — conditional `TABS` + route (Task 10).
- `report-template/screens.css` — `matrix-cell--partial`; rename graph classes to `report-graph__*` (Tasks 8–9).
- Rebuilt bundle + regenerated demo/golden (Task 11). Docs + CHANGELOG (Task 12).

Tests live in `tests/unit/report/` (Python) and `tests/test_workflow_apd_gauntlet.py`-style text-contract tests for JSX.

---

## Task 1: Loader — load `threat-model-coverage.yaml`

**Files:**
- Modify: `tools/apd_gauntlet/report/loader.py` (the `RunArtifacts` dataclass + `load_run` optional-artifact block)
- Test: `tests/unit/report/test_loader.py`

- [ ] **Step 1: Write the failing test**

```python
def test_load_run_reads_threat_model_coverage(example_run: pathlib.Path) -> None:
    artifacts = load_run(example_run)
    # The example ships 40-synthesis/threat-model-coverage.yaml (evaluator output).
    assert isinstance(artifacts.threat_model_coverage, dict)
    assert isinstance(artifacts.threat_model_coverage.get("surface_coverage"), list)
```

- [ ] **Step 2: Run it — expect FAIL**

Run: `.venv/bin/python -m pytest tests/unit/report/test_loader.py::test_load_run_reads_threat_model_coverage -v`
Expected: FAIL — `AttributeError: 'RunArtifacts' object has no attribute 'threat_model_coverage'`.

- [ ] **Step 3: Add the dataclass field**

In `loader.py`, in the `RunArtifacts` dataclass next to the other optional threat-model fields (`threat_model_normalized`, `threat_model_supplied`), add:

```python
    threat_model_coverage: dict[str, Any] | None = None
```

- [ ] **Step 4: Load the artifact in `load_run`**

In `load_run`, in the optional-artifact section (near where `tm_normalized` / `tm_supplied` are read from `context`), add (note: coverage lives under `40-synthesis`, i.e. the `synth` dir):

```python
    tm_coverage = _yaml_optional(synth / "threat-model-coverage.yaml")
```

Then pass it into the `RunArtifacts(...)` constructor:

```python
        threat_model_coverage=tm_coverage,
```

- [ ] **Step 5: Run it — expect PASS**

Run: `.venv/bin/python -m pytest tests/unit/report/test_loader.py::test_load_run_reads_threat_model_coverage -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add tools/apd_gauntlet/report/loader.py tests/unit/report/test_loader.py
git commit -m "feat(report): load threat-model-coverage.yaml into RunArtifacts"
```

---

## Task 2: Transform — entries + provenance (`data.threat_model` core)

**Files:**
- Modify: `tools/apd_gauntlet/report/transform.py` (`threat_model_block`; add `_tm_entries`; module constant)
- Test: `tests/unit/report/test_transform_threat_model.py` (this file already exists for the metadata block — extend it)

- [ ] **Step 1: Write the failing test**

```python
def test_threat_model_block_emits_entries_and_provenance():
    from apd_gauntlet.report.loader import RunArtifacts
    from apd_gauntlet.report.transform import threat_model_block

    normalized = {
        "generated_by": "threat_model_author",
        "methodology": "stride",
        "source_artifact": "tech_plan.md",
        "entries": [
            {"asset": "api", "threat": "cred theft", "mitigation": "MFA",
             "extraction_confidence": "high", "source_locator": "d[0]",
             "framework_refs": {"stride_letter": "S"},
             "inferred_apd_goals": ["authenticity"]},
            {"asset": "broker", "threat": "tamper", "mitigation": "",
             "extraction_confidence": "med", "source_locator": "d[1]",
             "framework_refs": {"stride_letter": "T"},
             "inferred_apd_goals": ["integrity"]},
        ],
    }
    art = _tm_artifacts(normalized=normalized)   # helper defined in Step 3
    block = threat_model_block(art)

    assert block["present"] is True
    assert block["authored"] is True
    assert block["methodology"] == "stride"
    assert block["source_artifact"] == "tech_plan.md"
    assert block["entry_count"] == 2
    assert block["grounded_count"] == 1
    assert block["gap_count"] == 1
    assert [e["asset"] for e in block["entries"]] == ["api", "broker"]
    assert block["entries"][0]["stride_letter"] == "S"
    assert block["entries"][0]["apd_goals"] == ["authenticity"]


def test_threat_model_block_absent_is_omittable():
    from apd_gauntlet.report.transform import threat_model_block
    block = threat_model_block(_tm_artifacts(normalized=None))
    assert block["present"] is False
    assert block["entries"] == []
    assert block["stride_matrix"] == {"letters_present": [], "rows": []}
    assert block["surface_mermaid"] is None
```

Add this helper at the top of the test module (reused by later tasks):

```python
def _tm_artifacts(*, normalized=None, supplied=None, coverage=None, inventory=None):
    from apd_gauntlet.report.loader import RunArtifacts
    return RunArtifacts(
        run_id="r", framework_version="1.0.0", domain_pack_name="p",
        domain_pack_version="1", subject="s", date="2026-01-01",
        asset_inventory=inventory or {}, deduped_findings=[], deduped_capabilities=[],
        contradictions=[], contradictions_notes=None,
        severity_disagreements=[], severity_disagreements_notes=None,
        nist_coverage={}, attack_exposure={}, apd_coverage_matrix={},
        attack_paths=None, asset_graph=None, defense_graph=None,
        attack_path_findings=[], report_data=None,
        threat_model_normalized=normalized, threat_model_supplied=supplied,
        threat_model_coverage=coverage,
    )
```

- [ ] **Step 2: Run it — expect FAIL**

Run: `.venv/bin/python -m pytest tests/unit/report/test_transform_threat_model.py -k "entries_and_provenance or absent_is_omittable" -v`
Expected: FAIL — `KeyError: 'entry_count'` / `'entries'` (the block only emits metadata today).

- [ ] **Step 3: Add the entries helper + constants**

In `transform.py`, near the other threat-model code, add:

```python
_STRIDE_LETTERS = ["S", "T", "R", "I", "D", "E"]
_LINDDUN_LETTERS = ["L", "I", "N", "D", "D", "U", "N"]


def _tm_entries(normalized: dict[str, Any] | None) -> list[dict[str, Any]]:
    """Normalize TM entries into the report-entry shape (block B)."""
    raw = normalized.get("entries") if isinstance(normalized, dict) else None
    if not isinstance(raw, list):
        return []
    out: list[dict[str, Any]] = []
    for e in raw:
        if not isinstance(e, dict):
            continue
        refs = e.get("framework_refs") or {}
        out.append({
            "asset": str(e.get("asset") or "—"),
            "threat": str(e.get("threat") or ""),
            "stride_letter": refs.get("stride_letter"),
            "linddun_letter": refs.get("linddun_letter"),
            "mitigation": str(e.get("mitigation") or ""),
            "confidence": e.get("extraction_confidence"),
            "source_locator": e.get("source_locator"),
            "apd_goals": [g for g in (e.get("inferred_apd_goals") or []) if isinstance(g, str)],
        })
    return out
```

- [ ] **Step 4: Extend `threat_model_block`**

Replace the body of `threat_model_block` so it keeps the existing metadata keys and adds the scene payload (the matrix/coverage/mermaid/comparator helpers land empty here and are filled by Tasks 3–6 — wire the calls now so the contract is stable):

```python
def threat_model_block(artifacts: RunArtifacts) -> dict[str, Any]:
    """Return the data.threat_model block for the HTML report (scene + provenance)."""
    normalized = artifacts.threat_model_normalized
    supplied = artifacts.threat_model_supplied
    present = isinstance(normalized, dict)
    generated_by = normalized.get("generated_by") if present else None
    authored = generated_by == "threat_model_author"
    methodology = normalized.get("methodology") if present else None
    source_artifact = normalized.get("source_artifact") if present else None
    supplied_present = isinstance(supplied, dict)
    comparator = authored and supplied_present

    entries = _tm_entries(normalized)
    grounded = sum(1 for e in entries if e["mitigation"].strip())
    return {
        "present": present,
        "authored": authored,
        "supplied_present": supplied_present,
        "comparator": comparator,
        "generated_by": generated_by,
        "methodology": methodology,
        "source_artifact": source_artifact,
        "entry_count": len(entries),
        "grounded_count": grounded,
        "gap_count": len(entries) - grounded,
        "entries": entries,
        "stride_matrix": _tm_stride_matrix(entries, methodology),
        "surface_coverage": _tm_surface_coverage(artifacts.threat_model_coverage),
        "surface_mermaid": _build_threat_surface_mermaid(entries, artifacts.asset_inventory),
        "comparator_delta": _tm_comparator_delta(normalized, supplied) if comparator else None,
    }
```

Add minimal stubs for the four helpers so the module imports (each is fully implemented in its own task):

```python
def _tm_stride_matrix(entries, methodology):  # Task 3
    return {"letters_present": [], "rows": []}
def _tm_surface_coverage(coverage):           # Task 4
    return None
def _build_threat_surface_mermaid(entries, asset_inventory):  # Task 5
    return None
def _tm_comparator_delta(normalized, supplied):  # Task 6
    return None
```

- [ ] **Step 5: Wire `meta.has_threat_model`**

In `build_apd_data` (transform.py), locate the existing `data["threat_model"] = threat_model_block(...)` assignment and immediately after it add:

```python
    data["meta"]["has_threat_model"] = data["threat_model"]["present"]
```

- [ ] **Step 6: Run it — expect PASS**

Run: `.venv/bin/python -m pytest tests/unit/report/test_transform_threat_model.py -v`
Expected: PASS (existing metadata tests + the two new ones).

- [ ] **Step 7: Commit**

```bash
git add tools/apd_gauntlet/report/transform.py tests/unit/report/test_transform_threat_model.py
git commit -m "feat(report): threat_model_block emits entries + provenance + scene contract"
```

---

## Task 3: Transform — STRIDE × asset matrix (block A)

**Files:**
- Modify: `tools/apd_gauntlet/report/transform.py` (`_tm_stride_matrix` + `_tm_cell_status`)
- Test: `tests/unit/report/test_transform_threat_model.py`

- [ ] **Step 1: Write the failing test**

```python
def test_tm_stride_matrix_cell_semantics():
    from apd_gauntlet.report.transform import _tm_stride_matrix
    entries = [
        {"asset": "api", "stride_letter": "S", "linddun_letter": None, "mitigation": "MFA"},
        {"asset": "api", "stride_letter": "I", "linddun_letter": None, "mitigation": ""},
        {"asset": "api", "stride_letter": "T", "linddun_letter": None, "mitigation": "x"},
        {"asset": "api", "stride_letter": "T", "linddun_letter": None, "mitigation": ""},
        {"asset": "broker", "stride_letter": "S", "linddun_letter": None, "mitigation": "y"},
    ]
    m = _tm_stride_matrix(entries, "stride")
    assert m["letters_present"] == ["S", "T", "I"]   # only modeled letters, STRIDE order
    rows = {r["asset"]: r["cells"] for r in m["rows"]}
    # api: S covered (mitigated), I gap (no mitigation), T partial (1 of 2 mitigated)
    assert rows["api"]["S"] == "covered"
    assert rows["api"]["I"] == "gap"
    assert rows["api"]["T"] == "partial"
    # broker: only S modeled → covered; unmodeled letters are "silent"
    assert rows["broker"]["S"] == "covered"
    assert rows["broker"]["T"] == "silent"
    # rows sorted by descending threat count: api (4) before broker (1)
    assert [r["asset"] for r in m["rows"]] == ["api", "broker"]
```

- [ ] **Step 2: Run it — expect FAIL**

Run: `.venv/bin/python -m pytest tests/unit/report/test_transform_threat_model.py::test_tm_stride_matrix_cell_semantics -v`
Expected: FAIL — stub returns empty matrix.

- [ ] **Step 3: Implement**

Replace the `_tm_stride_matrix` stub with:

```python
def _tm_cell_status(cell_entries: list[dict[str, Any]]) -> str:
    """silent (no entry) | gap (none mitigated) | covered (all mitigated) | partial (some)."""
    if not cell_entries:
        return "silent"
    mitigated = [bool((e.get("mitigation") or "").strip()) for e in cell_entries]
    if all(mitigated):
        return "covered"
    if any(mitigated):
        return "partial"
    return "gap"


def _tm_stride_matrix(entries: list[dict[str, Any]], methodology: str | None) -> dict[str, Any]:
    """Asset (rows) × methodology-letter (cols) status matrix (block A)."""
    linddun = str(methodology or "").lower() == "linddun"
    key = "linddun_letter" if linddun else "stride_letter"
    order = _LINDDUN_LETTERS if linddun else _STRIDE_LETTERS
    by_asset: dict[str, dict[str, list[dict[str, Any]]]] = {}
    for e in entries:
        letter = e.get(key)
        if letter not in order:
            continue
        by_asset.setdefault(e["asset"], {}).setdefault(letter, []).append(e)
    # de-dup order while preserving STRIDE/LINDDUN sequence
    seen = []
    for letter in order:
        if letter not in seen and any(letter in cells for cells in by_asset.values()):
            seen.append(letter)
    letters_present = seen
    rows = []
    for asset, cells in by_asset.items():
        count = sum(len(v) for v in cells.values())
        rows.append({
            "asset": asset,
            "cells": {L: _tm_cell_status(cells.get(L, [])) for L in letters_present},
            "_count": count,
        })
    rows.sort(key=lambda r: (-r["_count"], r["asset"]))
    for r in rows:
        del r["_count"]
    return {"letters_present": letters_present, "rows": rows}
```

- [ ] **Step 4: Run it — expect PASS**

Run: `.venv/bin/python -m pytest tests/unit/report/test_transform_threat_model.py::test_tm_stride_matrix_cell_semantics -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add tools/apd_gauntlet/report/transform.py tests/unit/report/test_transform_threat_model.py
git commit -m "feat(report): TM STRIDE x asset matrix (block A)"
```

---

## Task 4: Transform — coverage by surface (block C)

**Files:**
- Modify: `tools/apd_gauntlet/report/transform.py` (`_tm_surface_coverage`)
- Test: `tests/unit/report/test_transform_threat_model.py`

- [ ] **Step 1: Write the failing test**

```python
def test_tm_surface_coverage_parsing():
    from apd_gauntlet.report.transform import _tm_surface_coverage
    coverage = {
        "surface_coverage": [
            {"surface": "api", "categories_present": ["S", "I"],
             "categories_absent": ["R"], "tm_entry_count": 5},
        ],
        "summary": {"contradictions_emitted": 1, "silences_emitted": 1,
                    "coverage_gaps_emitted": 1, "surfaces_examined": 3},
    }
    out = _tm_surface_coverage(coverage)
    assert out["rows"][0] == {"surface": "api", "present": ["S", "I"],
                              "absent": ["R"], "entry_count": 5}
    assert out["summary"]["contradictions_emitted"] == 1

def test_tm_surface_coverage_absent_returns_none():
    from apd_gauntlet.report.transform import _tm_surface_coverage
    assert _tm_surface_coverage(None) is None
    assert _tm_surface_coverage({}) is None
```

- [ ] **Step 2: Run it — expect FAIL**

Run: `.venv/bin/python -m pytest tests/unit/report/test_transform_threat_model.py -k surface_coverage -v`
Expected: FAIL — stub returns None for the populated case.

- [ ] **Step 3: Implement**

Replace the `_tm_surface_coverage` stub with:

```python
def _tm_surface_coverage(coverage: dict[str, Any] | None) -> dict[str, Any] | None:
    """Per-surface STRIDE-category coverage from the evaluator (block C)."""
    if not isinstance(coverage, dict):
        return None
    raw = coverage.get("surface_coverage")
    if not isinstance(raw, list):
        return None
    rows = []
    for s in raw:
        if not isinstance(s, dict):
            continue
        rows.append({
            "surface": str(s.get("surface") or "—"),
            "present": [c for c in (s.get("categories_present") or []) if isinstance(c, str)],
            "absent": [c for c in (s.get("categories_absent") or []) if isinstance(c, str)],
            "entry_count": int(s.get("tm_entry_count") or 0),
        })
    summary = coverage.get("summary") if isinstance(coverage.get("summary"), dict) else {}
    return {"rows": rows, "summary": summary}
```

- [ ] **Step 4: Run it — expect PASS**

Run: `.venv/bin/python -m pytest tests/unit/report/test_transform_threat_model.py -k surface_coverage -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add tools/apd_gauntlet/report/transform.py tests/unit/report/test_transform_threat_model.py
git commit -m "feat(report): TM coverage-by-surface (block C)"
```

---

## Task 5: Transform — trust-boundary surface map (block D, Mermaid)

**Files:**
- Modify: `tools/apd_gauntlet/report/transform.py` (`_build_threat_surface_mermaid` + `_tm_asset_boundary`)
- Test: `tests/unit/report/test_transform_threat_model.py`

Uses the existing `_mermaid_safe_id(raw)` helper already in `transform.py`.

- [ ] **Step 1: Write the failing tests**

```python
def test_build_threat_surface_mermaid_clusters_and_hot():
    from apd_gauntlet.report.transform import _build_threat_surface_mermaid
    entries = [
        {"asset": "api", "stride_letter": "S", "mitigation": "MFA"},
        {"asset": "api", "stride_letter": "I", "mitigation": ""},   # gap → hot
        {"asset": "broker", "stride_letter": "T", "mitigation": "x"},
    ]
    inv = {"trust_boundaries": [
        {"name": "internet", "assets": ["api"]},
        {"name": "data-plane", "assets": ["broker"]},
    ]}
    out = _build_threat_surface_mermaid(entries, inv)
    assert out.startswith("graph TD")
    assert "subgraph" in out                    # clustered by trust boundary
    assert "api [S I]" in out or 'api [S I]' in out  # node label badged with letters
    assert "classDef hot" in out and ":::hot" in out  # api has a gap → hot class
    assert "broker" in out

def test_build_threat_surface_mermaid_degrades_without_boundaries():
    from apd_gauntlet.report.transform import _build_threat_surface_mermaid
    entries = [{"asset": "api", "stride_letter": "S", "mitigation": "MFA"}]
    out = _build_threat_surface_mermaid(entries, {})  # no trust boundaries
    assert out.startswith("graph TD")
    assert "subgraph" not in out                 # flat node list, no clusters
    assert "api [S]" in out

def test_build_threat_surface_mermaid_none_when_no_entries():
    from apd_gauntlet.report.transform import _build_threat_surface_mermaid
    assert _build_threat_surface_mermaid([], {"trust_boundaries": []}) is None
```

- [ ] **Step 2: Run it — expect FAIL**

Run: `.venv/bin/python -m pytest tests/unit/report/test_transform_threat_model.py -k surface_mermaid -v`
Expected: FAIL — stub returns None.

- [ ] **Step 3: Implement**

Replace the `_build_threat_surface_mermaid` stub with:

```python
def _tm_asset_boundary(asset: str, asset_inventory: dict[str, Any]) -> str | None:
    """Resolve an asset's trust-boundary name from asset-inventory, or None."""
    boundaries = asset_inventory.get("trust_boundaries") if isinstance(asset_inventory, dict) else None
    if not isinstance(boundaries, list):
        return None
    for b in boundaries:
        if not isinstance(b, dict):
            continue
        members = b.get("assets") or b.get("members") or []
        if isinstance(members, list) and asset in members:
            name = b.get("name") or b.get("boundary") or b.get("boundary_id")
            return str(name) if name else None
    return None


def _build_threat_surface_mermaid(
    entries: list[dict[str, Any]], asset_inventory: dict[str, Any]
) -> str | None:
    """Trust-boundary surface map (block D). Assets as nodes badged with their
    STRIDE letters, grouped into trust-boundary subgraphs when the inventory
    provides them, `hot` when an asset has an unmitigated (gap) threat. No
    fabricated edges — clusters/nodes only, degrading to a flat list."""
    if not entries:
        return None
    # asset -> {letters:set, has_gap:bool}
    assets: dict[str, dict[str, Any]] = {}
    for e in entries:
        a = e["asset"]
        rec = assets.setdefault(a, {"letters": set(), "has_gap": False})
        L = e.get("stride_letter") or e.get("linddun_letter")
        if L:
            rec["letters"].add(L)
        if not (e.get("mitigation") or "").strip():
            rec["has_gap"] = True
    inv = asset_inventory if isinstance(asset_inventory, dict) else {}
    # group by boundary
    clusters: dict[str | None, list[str]] = {}
    for a in assets:
        clusters.setdefault(_tm_asset_boundary(a, inv), []).append(a)
    has_boundaries = any(k is not None for k in clusters)

    lines = ["graph TD"]

    def _node(a: str) -> str:
        rec = assets[a]
        letters = " ".join(L for L in _STRIDE_LETTERS + _LINDDUN_LETTERS if L in rec["letters"])
        label = f"{a} [{letters}]" if letters else a
        nid = _mermaid_safe_id(a)
        hot = ":::hot" if rec["has_gap"] else ""
        return f'  {nid}["{label}"]{hot}'

    if has_boundaries:
        for boundary, members in clusters.items():
            bid = _mermaid_safe_id(boundary) if boundary else "unbounded"
            blabel = boundary or "unbounded"
            lines.append(f'  subgraph {bid}["{blabel}"]')
            for a in sorted(members):
                lines.append("  " + _node(a))
            lines.append("  end")
    else:
        for a in sorted(assets):
            lines.append(_node(a))

    lines.append("  classDef hot fill:#fbe9e9,stroke:#c0392b,color:#7a1f1f;")
    return "\n".join(lines)
```

- [ ] **Step 4: Run it — expect PASS**

Run: `.venv/bin/python -m pytest tests/unit/report/test_transform_threat_model.py -k surface_mermaid -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add tools/apd_gauntlet/report/transform.py tests/unit/report/test_transform_threat_model.py
git commit -m "feat(report): TM trust-boundary surface map mermaid (block D)"
```

---

## Task 6: Transform — supplied-vs-authored comparator (block E)

**Files:**
- Modify: `tools/apd_gauntlet/report/transform.py` (`_tm_comparator_delta`)
- Test: `tests/unit/report/test_transform_threat_model.py`

- [ ] **Step 1: Write the failing test**

```python
def test_tm_comparator_delta():
    from apd_gauntlet.report.transform import _tm_comparator_delta
    authored = {"entries": [
        {"asset": "api", "threat": "Credential theft"},
        {"asset": "broker", "threat": "Key rotation disabled"},
    ]}
    supplied = {"entries": [
        {"asset": "api", "threat": "credential theft"},   # corroborated (case-insensitive)
        {"asset": "edge", "threat": "DDoS"},               # supplied-only
    ]}
    d = _tm_comparator_delta(authored, supplied)
    assert [x["threat"] for x in d["authored_only"]] == ["Key rotation disabled"]
    assert [x["threat"] for x in d["supplied_only"]] == ["DDoS"]
    assert [x["threat"] for x in d["corroborated"]] == ["Credential theft"]

def test_tm_comparator_delta_block_only_when_comparator():
    # Integration: threat_model_block emits comparator_delta only when authored AND supplied.
    from apd_gauntlet.report.transform import threat_model_block
    authored = {"generated_by": "threat_model_author", "methodology": "stride",
                "entries": [{"asset": "api", "threat": "t"}]}
    supplied = {"generated_by": "threat_model_recon",
                "entries": [{"asset": "api", "threat": "t"}]}
    assert threat_model_block(_tm_artifacts(normalized=authored))["comparator_delta"] is None
    block = threat_model_block(_tm_artifacts(normalized=authored, supplied=supplied))
    assert block["comparator"] is True
    assert block["comparator_delta"] is not None
```

- [ ] **Step 2: Run it — expect FAIL**

Run: `.venv/bin/python -m pytest tests/unit/report/test_transform_threat_model.py -k comparator -v`
Expected: FAIL — stub returns None for the populated case.

- [ ] **Step 3: Implement**

Replace the `_tm_comparator_delta` stub with:

```python
def _tm_comparator_delta(
    normalized: dict[str, Any] | None, supplied: dict[str, Any] | None
) -> dict[str, Any]:
    """Authored-vs-supplied delta keyed on (asset, threat) case-insensitively."""
    def _index(doc):
        out = {}
        for e in (doc.get("entries") if isinstance(doc, dict) else None) or []:
            if isinstance(e, dict):
                key = (str(e.get("asset") or "").lower(), str(e.get("threat") or "").lower())
                out[key] = {"asset": e.get("asset"), "threat": e.get("threat")}
        return out
    a, s = _index(normalized), _index(supplied)
    authored_only = [v for k, v in a.items() if k not in s]
    supplied_only = [v for k, v in s.items() if k not in a]
    corroborated = [v for k, v in a.items() if k in s]
    return {"authored_only": authored_only, "supplied_only": supplied_only,
            "corroborated": corroborated}
```

- [ ] **Step 4: Run it — expect PASS**

Run: `.venv/bin/python -m pytest tests/unit/report/test_transform_threat_model.py -k comparator -v`
Expected: PASS.

- [ ] **Step 5: Full transform-TM module + commit**

Run: `.venv/bin/python -m pytest tests/unit/report/test_transform_threat_model.py -v` → all PASS.

```bash
git add tools/apd_gauntlet/report/transform.py tests/unit/report/test_transform_threat_model.py
git commit -m "feat(report): TM supplied-vs-authored comparator (block E)"
```

---

## Task 7: Audit — `threat_model_scene_coherent` completeness check

**Files:**
- Modify: `tools/apd_gauntlet/synthesis/audit.py` (add the check to the checks the auditor emits)
- Test: `tests/test_cli_audit_report.py`

Read `audit.py` first to match how existing structural checks are appended (each is a dict `{"name","status","klass","detail"}` added to `result.checks`). Follow that exact shape.

- [ ] **Step 1: Write the failing tests**

```python
def test_threat_model_scene_coherent_passes_on_example(tmp_path):
    dst = _copy_example(tmp_path)
    result = audit_report(dst)
    c = [x for x in result.checks if x["name"] == "threat_model_scene_coherent"]
    assert c and c[0]["status"] == "pass"
    assert c[0]["klass"] == "structural"

def test_threat_model_scene_coherent_exempt_when_absent(tmp_path):
    dst = _copy_example(tmp_path)
    _mutate_data_js(dst, lambda d: d.__setitem__("threat_model", {"present": False}))
    result = audit_report(dst)
    c = [x for x in result.checks if x["name"] == "threat_model_scene_coherent"]
    assert c and c[0]["status"] == "pass"   # absent → exempt

def test_threat_model_scene_coherent_fails_when_present_but_empty(tmp_path):
    dst = _copy_example(tmp_path)
    _mutate_data_js(dst, lambda d: d.__setitem__(
        "threat_model", {"present": True, "entries": [], "stride_matrix": {"rows": []}}))
    result = audit_report(dst)
    c = [x for x in result.checks if x["name"] == "threat_model_scene_coherent"]
    assert c and c[0]["status"] == "fail"
    assert result.status == "fail"
```

- [ ] **Step 2: Run it — expect FAIL**

Run: `.venv/bin/python -m pytest tests/test_cli_audit_report.py -k threat_model_scene_coherent -v`
Expected: FAIL — no such check emitted.

- [ ] **Step 3: Implement the check**

In `audit_report` (audit.py), insert this **after** the `taxonomy_titles_resolve` `_check(...)` block and **before** `result.counts = {`. The parsed data.js dict is the local `parsed`; checks are appended via the existing `_check(result, name, ok, detail, klass="structural")` helper:

```python
    # Completeness check — threat-model scene coherence (structural; exempt when
    # the scene is legitimately omitted, matching the gate's empty-state policy).
    tm = parsed.get("threat_model") or {}
    if not tm.get("present"):
        _check(result, "threat_model_scene_coherent", True,
               "no threat model present — scene omitted (exempt)", klass="structural")
    else:
        tm_rows = ((tm.get("stride_matrix") or {}).get("rows")) or []
        _check(result, "threat_model_scene_coherent",
               bool(tm.get("entries")) and bool(tm_rows),
               f"entries={len(tm.get('entries') or [])} matrix_rows={len(tm_rows)}",
               klass="structural")
```

- [ ] **Step 4: Run it — expect PASS**

Run: `.venv/bin/python -m pytest tests/test_cli_audit_report.py -k threat_model_scene_coherent -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add tools/apd_gauntlet/synthesis/audit.py tests/test_cli_audit_report.py
git commit -m "feat(audit): threat_model_scene_coherent structural check (exempt when absent)"
```

---

## Task 8: JSX — shared `MermaidGraph` component + graph-CSS rename

**Files:**
- Modify: `report-template/components.jsx` (add `MermaidGraph`, export on `window`)
- Modify: `report-template/screens/AttackPaths.jsx` (use `MermaidGraph`; delete the local `ZoomToolbar`/render/zoom code)
- Modify: `report-template/screens.css` (rename `.attack-paths__graph-wrapper` → `.report-graph__wrapper`, `.attack-paths__zoom-toolbar` → `.report-graph__toolbar`, `.attack-paths__mermaid` → `.report-graph__canvas`, incl. their descendant selectors)
- Test: `tests/test_workflow_apd_gauntlet.py` (text-contract — there is no client-side render test; this mirrors the repo's JS-as-text convention)

- [ ] **Step 1: Write the failing contract test**

Add to `tests/test_workflow_apd_gauntlet.py` (or a new `tests/test_report_template_contract.py` using the same read-as-text approach):

```python
def test_mermaid_graph_is_shared_component() -> None:
    comp = (REPO / "report-template" / "components.jsx").read_text(encoding="utf-8")
    assert "function MermaidGraph(" in comp
    assert "securityLevel: \"strict\"" in comp and "htmlLabels: false" in comp
    assert "MermaidGraph" in comp.split("Object.assign(window")[1]  # exported

def test_attack_paths_uses_shared_mermaid_graph() -> None:
    ap = (REPO / "report-template" / "screens" / "AttackPaths.jsx").read_text(encoding="utf-8")
    assert "MermaidGraph" in ap
    # The bespoke renderer is gone — no duplicate mermaid.render in the screen.
    assert "window.mermaid.render" not in ap and "window.mermaid\n" not in ap
```

(Define `REPO = pathlib.Path(__file__).resolve().parent.parent` at module top if not present.)

- [ ] **Step 2: Run it — expect FAIL**

Run: `.venv/bin/python -m pytest tests/test_workflow_apd_gauntlet.py -k "mermaid_graph or attack_paths_uses" -v`
Expected: FAIL — `MermaidGraph` does not exist yet.

- [ ] **Step 3: Add `MermaidGraph` to `components.jsx`**

Insert before the `Object.assign(window, {…})` block (move the zoom constants + `parseSvgNode`/`svgNaturalWidth`/`applyZoom`/`ZoomToolbar`/render logic out of AttackPaths.jsx verbatim, wrapped as one self-contained component keyed by `idBase`):

```jsx
// ── Shared Mermaid graph (asset graph, threat-model surface map) ────────────
var GRAPH_ZOOM_MIN = 0.25, GRAPH_ZOOM_MAX = 4.0, GRAPH_ZOOM_STEP = 0.25;

function MermaidGraph({ source, idBase }) {
  const ref = React.useRef(null);
  const baseWidth = React.useRef(null);
  const [zoom, setZoom] = React.useState(1.0);
  const zoomRef = React.useRef(1.0);

  function parseSvgNode(svg) {
    const node = new DOMParser().parseFromString(svg, "image/svg+xml").documentElement;
    node.removeAttribute("style"); node.removeAttribute("width"); node.removeAttribute("height");
    return node;
  }
  function svgNaturalWidth(n) {
    const vb = n && n.getAttribute && n.getAttribute("viewBox");
    if (vb) { const p = vb.trim().split(/\s+|,/); if (p.length >= 4) { const w = parseFloat(p[2]); if (w > 0) return w; } }
    return null;
  }
  function applyZoom(el, z, base) {
    if (!el) return; const svg = el.querySelector("svg"); if (!svg) return;
    if (z === null) { const w = el.parentElement ? el.parentElement.clientWidth : el.clientWidth; svg.style.width = w + "px"; }
    else { svg.style.width = ((base || 2400) * z) + "px"; }
  }
  React.useEffect(() => {
    if (!source || !window.mermaid || !ref.current) return;
    window.mermaid.initialize({ startOnLoad: false, theme: "neutral", securityLevel: "strict", flowchart: { htmlLabels: false } });
    window.mermaid.render(idBase, source)
      .then(({ svg }) => { const n = parseSvgNode(svg); baseWidth.current = svgNaturalWidth(n); ref.current.replaceChildren(n); applyZoom(ref.current, zoomRef.current, baseWidth.current); })
      .catch((e) => { ref.current.textContent = "Graph render failed: " + e.message; });
  }, [source, idBase]);
  React.useEffect(() => { zoomRef.current = zoom; applyZoom(ref.current, zoom, baseWidth.current); }, [zoom]);
  function onWheel(e) {
    if (!e.ctrlKey && !e.metaKey) return; e.preventDefault();
    setZoom((z) => { const cur = z === null ? 1.0 : z; const d = e.deltaY > 0 ? -GRAPH_ZOOM_STEP : GRAPH_ZOOM_STEP;
      return Math.min(GRAPH_ZOOM_MAX, Math.max(GRAPH_ZOOM_MIN, Math.round((cur + d) / GRAPH_ZOOM_STEP) * GRAPH_ZOOM_STEP)); });
  }
  const pct = Math.round((zoom === null ? 1.0 : zoom) * 100) + "%";
  if (!source) return null;
  return (
    <div className="report-graph__wrapper" onWheel={onWheel}>
      <div className="report-graph__toolbar">
        <button onClick={() => setZoom((z) => Math.max(GRAPH_ZOOM_MIN, (z === null ? 1.0 : z) - GRAPH_ZOOM_STEP))} title="Zoom out">−</button>
        <span className="zoom-level">{pct}</span>
        <button onClick={() => setZoom((z) => Math.min(GRAPH_ZOOM_MAX, (z === null ? 1.0 : z) + GRAPH_ZOOM_STEP))} title="Zoom in">+</button>
        <button onClick={() => setZoom(1.0)} title="Reset to 100%">100%</button>
        <button onClick={() => setZoom(null)} title="Fit to width">fit</button>
      </div>
      <div ref={ref} className="report-graph__canvas" />
    </div>
  );
}
```

Add `MermaidGraph` to the `Object.assign(window, { … })` exports.

- [ ] **Step 4: Refactor `AttackPaths.jsx`**

Delete the local `ZOOM_*` consts, `ZoomToolbar`, the refs/`useEffect`/`parseSvgNode`/`applyZoom`/`makeWheelHandler` blocks, and replace the two graph `<div ref=…>` sites with:

```jsx
        <MermaidGraph source={ap.mermaid} idBase="apd-asset-graph" />
```

and (in the focused section):

```jsx
        <MermaidGraph source={ap.mermaid_path_focused} idBase="apd-paths-focused" />
```

Keep the surrounding `<section className="attack-paths__graph">` + `<h3 className="attack-paths__section-h">` headers.

- [ ] **Step 5: Rename graph CSS classes in `screens.css`**

Mechanically rename (and their descendant selectors): `.attack-paths__graph-wrapper` → `.report-graph__wrapper`; `.attack-paths__zoom-toolbar` → `.report-graph__toolbar` (incl. `… button`, `… .zoom-level`); `.attack-paths__mermaid` → `.report-graph__canvas` (incl. `… svg`, `… svg .nodeLabel`, etc.). Leave `.attack-paths__graph` and `.attack-paths__section-h` as-is.

- [ ] **Step 6: Run it — expect PASS**

Run: `.venv/bin/python -m pytest tests/test_workflow_apd_gauntlet.py -k "mermaid_graph or attack_paths_uses" -v`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add report-template/components.jsx report-template/screens/AttackPaths.jsx report-template/screens.css tests/test_workflow_apd_gauntlet.py
git commit -m "refactor(report): extract shared MermaidGraph; generalize graph CSS"
```

---

## Task 9: JSX — `ThreatModel.jsx` scene (blocks A–E)

**Files:**
- Create: `report-template/screens/ThreatModel.jsx`
- Modify: `report-template/screens.css` (add `matrix-cell--partial`)
- Test: `tests/test_workflow_apd_gauntlet.py`

- [ ] **Step 1: Write the failing contract test**

```python
def test_threat_model_screen_exists_and_renders_blocks() -> None:
    src = (REPO / "report-template" / "screens" / "ThreatModel.jsx").read_text(encoding="utf-8")
    assert "function ThreatModel(" in src and "window.ThreatModel = ThreatModel" in src
    # reuses the report's design language, not bespoke styling
    assert "section-eyebrow" in src and "section-title" in src
    assert "apd-matrix" in src and "matrix-cell--" in src        # block A
    assert "attack-table" in src                                  # blocks B/C
    assert "coverage-bar" in src                                  # block C
    assert "MermaidGraph" in src                                  # block D
    assert "contradiction" in src                                 # block E
    # conditional blocks
    assert "surface_coverage" in src and "comparator_delta" in src
```

- [ ] **Step 2: Run it — expect FAIL**

Run: `.venv/bin/python -m pytest tests/test_workflow_apd_gauntlet.py -k threat_model_screen_exists -v`
Expected: FAIL — file does not exist.

- [ ] **Step 3: Create `report-template/screens/ThreatModel.jsx`**

```jsx
/* eslint-disable */
// Threat-model screen — provenance banner + STRIDE matrix + entries + coverage
// + trust-boundary surface map + supplied-vs-authored comparator. Omitted at the
// tab level (app.jsx) when data.threat_model.present is false.

function ThreatModel({ data }) {
  const tm = data.threat_model || {};
  const MATRIX_CLASS = { covered: "covered", gap: "gapped", partial: "partial", silent: "silent" };
  const MATRIX_LABEL = { covered: "covd", gap: "gap", partial: "part", silent: "—" };

  return (
    <div className="threat-model">
      <div className="section-eyebrow">§ Threat model — {tm.methodology ? tm.methodology.toUpperCase() : "model"}</div>
      <h2 className="section-title">Modeled threats · {tm.entry_count} entries · {tm.grounded_count} mitigated · {tm.gap_count} gaps</h2>

      {/* Provenance banner — reuses the attack-paths summary-banner inline style */}
      <div style={{
        fontFamily: "var(--font-mono)", fontSize: "var(--text-xs)", color: "var(--ink-3)",
        background: "var(--paper-2)", border: "1px solid var(--rule)", borderLeft: "3px solid var(--accent)",
        borderRadius: "0 var(--radius-sm) var(--radius-sm) 0", padding: "var(--space-2) var(--space-3)", lineHeight: 1.6,
      }}>
        <strong style={{ color: "var(--ink)" }}>
          {tm.authored ? "Authored baseline" : "User-supplied"}
        </strong>{" "}
        — generated by <code>{tm.generated_by}</code>
        {tm.source_artifact ? <> · grounded from <code>{tm.source_artifact}</code></> : null}
        {tm.comparator ? " · supplied-vs-authored comparator below" : null}
      </div>

      {/* A — STRIDE × asset matrix */}
      <section>
        <div className="section-eyebrow" style={{ marginTop: "var(--space-5)" }}>A — STRIDE × asset</div>
        <div style={{ overflowX: "auto" }}>
          <table className="apd-matrix">
            <thead>
              <tr>
                <th>Asset / surface</th>
                {tm.stride_matrix.letters_present.map((L) => <th key={L}>{L}</th>)}
              </tr>
            </thead>
            <tbody>
              {tm.stride_matrix.rows.map((row) => (
                <tr key={row.asset}>
                  <td>{row.asset}</td>
                  {tm.stride_matrix.letters_present.map((L) => {
                    const v = row.cells[L];
                    return <td key={L}><span className={`matrix-cell matrix-cell--${MATRIX_CLASS[v]}`}>{MATRIX_LABEL[v]}</span></td>;
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="legend">
          <span><span className="legend__swatch" style={{ background: "var(--cell-covered)" }} />covered — mitigated</span>
          <span><span className="legend__swatch" style={{ background: "var(--cell-both)" }} />partial — some mitigated</span>
          <span><span className="legend__swatch" style={{ background: "var(--cell-gapped)" }} />gap — no mitigation</span>
          <span><span className="legend__swatch" style={{ background: "var(--cell-silent)" }} />silent — not modeled</span>
        </div>
      </section>

      {/* B — entries table */}
      <section>
        <div className="section-eyebrow" style={{ marginTop: "var(--space-5)" }}>B — Threat entries</div>
        <table className="attack-table">
          <thead>
            <tr><th>Asset</th><th>Threat</th><th>STRIDE</th><th>Mitigation</th><th>Conf.</th><th>APD goals</th><th>Source</th></tr>
          </thead>
          <tbody>
            {tm.entries.map((e, i) => (
              <tr key={i}>
                <td style={{ color: "var(--ink)" }}>{e.asset}</td>
                <td>{e.threat}</td>
                <td><span className="mono">{e.stride_letter || e.linddun_letter || "—"}</span></td>
                <td>{e.mitigation
                  ? e.mitigation
                  : <span style={{ color: "var(--sev-high)", fontSize: "var(--text-xs)", fontFamily: "var(--font-mono)" }}>— none</span>}</td>
                <td><span className="mono">{e.confidence || "—"}</span></td>
                <td><div className="tagrow">{(e.apd_goals || []).map((g) => (
                  <span key={g} className="pill">{(window.GOAL_LABELS || {})[g] || g}</span>
                ))}</div></td>
                <td style={{ fontSize: "var(--text-xs)", color: "var(--ink-3)" }} className="mono">{e.source_locator || "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      {/* C — coverage by surface (only when the evaluator ran) */}
      {tm.surface_coverage && (
        <section>
          <div className="section-eyebrow" style={{ marginTop: "var(--space-5)" }}>C — Coverage by surface</div>
          <p style={{ color: "var(--ink-2)", fontSize: "var(--text-sm)", marginBottom: "var(--space-3)" }}>
            Evaluator examined {tm.surface_coverage.summary.surfaces_examined || tm.surface_coverage.rows.length} surface(s) —{" "}
            {tm.surface_coverage.summary.coverage_gaps_emitted || 0} coverage gap(s),{" "}
            {tm.surface_coverage.summary.contradictions_emitted || 0} contradiction(s),{" "}
            {tm.surface_coverage.summary.silences_emitted || 0} silence(s).
          </p>
          <table className="attack-table">
            <thead>
              <tr><th>Surface</th><th>Categories present</th><th>Absent</th><th className="num">Entries</th><th>Coverage</th></tr>
            </thead>
            <tbody>
              {tm.surface_coverage.rows.map((r) => {
                const present = r.present.length, absent = r.absent.length;
                return (
                  <tr key={r.surface}>
                    <td style={{ color: "var(--ink)" }}>{r.surface}</td>
                    <td><div className="tagrow">{r.present.map((c) => <span key={c} className="mono">{c}</span>)}</div></td>
                    <td><div className="tagrow">{r.absent.length
                      ? r.absent.map((c) => <span key={c} className="mono" style={{ color: "var(--ink-3)" }}>{c}</span>)
                      : <span style={{ color: "var(--ink-3)" }}>—</span>}</div></td>
                    <td className="num">{r.entry_count}</td>
                    <td><div className="coverage-bar">
                      <span className="seg-covered" style={{ flex: present }} />
                      <span className="seg-gapped" style={{ flex: absent }} />
                    </div></td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </section>
      )}

      {/* D — trust-boundary surface map */}
      {tm.surface_mermaid && (
        <section>
          <div className="section-eyebrow" style={{ marginTop: "var(--space-5)" }}>D — Surface map</div>
          <MermaidGraph source={tm.surface_mermaid} idBase="apd-tm-surface" />
        </section>
      )}

      {/* E — supplied-vs-authored comparator (only when both TMs exist) */}
      {tm.comparator_delta && (
        <section>
          <div className="section-eyebrow" style={{ marginTop: "var(--space-5)" }}>E — Supplied vs authored</div>
          {[["authored_only", "Authored only — author surfaced, not in supplied TM"],
            ["supplied_only", "Supplied only — in your TM, author did not surface"],
            ["corroborated", "Corroborated — present in both"]].map(([key, label]) => (
            <div key={key} className="contradiction">
              <div className="contradiction__col">
                <div className="contradiction__label">{label} ({tm.comparator_delta[key].length})</div>
                {tm.comparator_delta[key].map((x, i) => (
                  <div key={i} className="contradiction__assertion">{x.asset}: {x.threat}</div>
                ))}
              </div>
            </div>
          ))}
        </section>
      )}
    </div>
  );
}

window.ThreatModel = ThreatModel;
```

- [ ] **Step 4: Add the `matrix-cell--partial` CSS**

In `screens.css`, immediately after the `.matrix-cell--both` rule, add:

```css
.matrix-cell--partial { background: var(--cell-both); color: var(--cell-both-text); }
```

- [ ] **Step 5: Run it — expect PASS**

Run: `.venv/bin/python -m pytest tests/test_workflow_apd_gauntlet.py -k threat_model_screen_exists -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add report-template/screens/ThreatModel.jsx report-template/screens.css tests/test_workflow_apd_gauntlet.py
git commit -m "feat(report): ThreatModel scene (blocks A-E) in existing design language"
```

---

## Task 10: JSX — tab gating + route in `app.jsx`

**Files:**
- Modify: `report-template/app.jsx`
- Test: `tests/test_workflow_apd_gauntlet.py`

- [ ] **Step 1: Write the failing contract test**

```python
def test_threat_model_tab_is_conditional_and_routed() -> None:
    src = (REPO / "report-template" / "app.jsx").read_text(encoding="utf-8")
    # tab entry present
    assert 'id: "threat_model"' in src and 'label: "Threat model"' in src
    # gated on data.threat_model.present (omit when absent)
    assert "data.threat_model" in src and "present" in src
    # routed to the screen
    assert 'activeTab === "threat_model"' in src and "<ThreatModel" in src
    # placed after coverage, before attack_paths
    i_cov = src.index('"coverage"'); i_tm = src.index('"threat_model"'); i_ap = src.index('"attack_paths"')
    assert i_cov < i_tm < i_ap
```

- [ ] **Step 2: Run it — expect FAIL**

Run: `.venv/bin/python -m pytest tests/test_workflow_apd_gauntlet.py -k threat_model_tab_is_conditional -v`
Expected: FAIL.

- [ ] **Step 3: Make `TABS` data-driven + conditional**

In `app.jsx`, replace the module-level `const TABS = [...]` usage. Inside `App()`, build the tab list from `data` and derive `num` from index so renumbering is automatic:

```jsx
  const BASE_TABS = [
    { id: "overview", label: "Overview" },
    { id: "findings", label: "Findings" },
    { id: "capabilities", label: "Capabilities" },
    { id: "coverage", label: "Coverage" },
    ...(data.threat_model && data.threat_model.present
      ? [{ id: "threat_model", label: "Threat model" }] : []),
    { id: "attack_paths", label: "Attack paths" },
    { id: "annexes", label: "Annexes" },
  ];
  const TABS = BASE_TABS.map((t, i) => ({ ...t, num: String(i + 1).padStart(2, "0") }));
```

(If `TABS` is referenced at module scope elsewhere, move those references inside `App()` or compute from `data`. The `data-screen-label` lookups using `TABS.find(...)` continue to work unchanged.)

- [ ] **Step 4: Add the route**

In the `<main>` routing block, after the `coverage` branch and before `attack_paths`, add:

```jsx
        {activeTab === "threat_model" && <ThreatModel data={data} />}
```

- [ ] **Step 5: Run it — expect PASS**

Run: `.venv/bin/python -m pytest tests/test_workflow_apd_gauntlet.py -k threat_model_tab_is_conditional -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add report-template/app.jsx tests/test_workflow_apd_gauntlet.py
git commit -m "feat(report): gate + route the Threat model tab (omit when absent)"
```

---

## Task 11: Build the bundle + regenerate golden/demo data + full verification

**Files:**
- Modify (generated): `tools/apd_gauntlet/data/report-template/app.js`, `.../.source-hash`, `report-template/data.js`, `tests/fixtures/report-html/claim-event-bus-golden-data.js`

- [ ] **Step 1: Rebuild the precompiled bundle**

Run: `.venv/bin/python tools/build_report_template.py`
Expected: `build-report-template: bundle written.`

- [ ] **Step 2: Verify freshness gate**

Run: `.venv/bin/python tools/check_report_template_freshness.py`
Expected: `check_report_template_freshness: OK (...)`.

- [ ] **Step 3: Regenerate the golden + demo data from the example**

```bash
.venv/bin/apd-gauntlet build-report examples/apd-20260601-claim-event-bus/expected --out /tmp/tm-golden
cp /tmp/tm-golden/data.js tests/fixtures/report-html/claim-event-bus-golden-data.js
cp /tmp/tm-golden/data.js report-template/data.js
```

Then re-run the bundle build so `.source-hash` reflects the updated `report-template/data.js`:

Run: `.venv/bin/python tools/build_report_template.py && .venv/bin/python tools/check_report_template_freshness.py`
Expected: OK.

- [ ] **Step 4: Inspect the golden diff (sanity)**

Run: `git --no-pager diff --stat tests/fixtures/report-html/ report-template/data.js`
Expected: only `data.js` payloads changed; confirm the `threat_model` block now carries `entries`, `stride_matrix`, `surface_coverage`, `surface_mermaid` (and `comparator_delta: null`, since the example has no supplied sibling).

- [ ] **Step 5: Lint + full suite**

Run: `.venv/bin/ruff check tools/ tests/ && .venv/bin/python -m mypy tools/ && .venv/bin/python -m pytest -q`
Expected: ruff clean, mypy clean, pytest all green (incl. the regenerated golden comparison).

- [ ] **Step 6: Manual visual check**

Run: `.venv/bin/apd-gauntlet build-report examples/apd-20260601-claim-event-bus/expected --out /tmp/tm-view && open /tmp/tm-view/index.html`
Confirm: a **05 Threat model** tab sits between Coverage and Attack paths; blocks A/B/C/D render in the report's styling; block E is absent (no supplied TM); the surface-map Mermaid shows trust-boundary clusters and zoom works.

- [ ] **Step 7: Negative (omit) check**

```bash
mkdir -p /tmp/tm-none && cp -r examples/apd-20260601-claim-event-bus/expected/* /tmp/tm-none/
rm /tmp/tm-none/00-context/threat-model-normalized.yaml /tmp/tm-none/00-context/threat-model-supplied-normalized.yaml 2>/dev/null
.venv/bin/apd-gauntlet build-report /tmp/tm-none --out /tmp/tm-none-out
```

Confirm in `/tmp/tm-none-out/data.js` that `threat_model.present` is `false`; open `index.html` and confirm **no** Threat model tab, and `audit-report /tmp/tm-none` passes (`threat_model_scene_coherent` exempt).

- [ ] **Step 8: Commit**

```bash
git add tools/apd_gauntlet/data/report-template/app.js tools/apd_gauntlet/data/report-template/.source-hash report-template/data.js tests/fixtures/report-html/claim-event-bus-golden-data.js
git commit -m "build(report): rebuild bundle + regenerate golden/demo data for Threat model scene"
```

---

## Task 12: Docs + CHANGELOG

**Files:**
- Modify: `docs/html-report.md`, `CHANGELOG.md`

- [ ] **Step 1: Document the scene**

In `docs/html-report.md`, add a "Threat model" entry to the tab list describing the five blocks and the omit behavior (no tab when no normalized TM; block C requires the evaluator; block E requires both a supplied TM and the authored baseline).

- [ ] **Step 2: CHANGELOG**

Under `## [Unreleased]` → `### Added`:

```markdown
- **Threat-model report scene** — a dedicated report tab (after Coverage, before Attack paths) detailing the threat model: STRIDE×asset matrix, entries table, coverage-by-surface, a trust-boundary surface map (Mermaid), and a supplied-vs-authored comparator. Gracefully omitted when no threat model exists (no user-supplied TM and none authored). Renders in the existing report design language (shared `MermaidGraph`, `apd-matrix`/`coverage-bar`/`contradiction` classes).
```

- [ ] **Step 3: Lint docs**

Run: `npx --yes markdownlint-cli2 "docs/html-report.md" "CHANGELOG.md"`
Expected: `Summary: 0 error(s)`.

- [ ] **Step 4: Commit**

```bash
git add docs/html-report.md CHANGELOG.md
git commit -m "docs: document the Threat model report scene"
```

---

## Self-Review

(Completed by the plan author — see notes appended after this section if any gaps were found and fixed.)

- **Spec coverage:** all five blocks (A Task 3 + Task 9; B Task 2 + 9; C Task 4 + 9; D Task 5 + 8 + 9; E Task 6 + 9), provenance (Task 2), omit (Task 10), loader (Task 1), audit gate (Task 7), bundle/golden (Task 11), docs (Task 12) — covered.
- **Design-language consistency:** the consistency contract section + per-block class assertions in the JSX contract tests (Task 9) enforce reuse of `section-eyebrow`/`apd-matrix`/`matrix-cell`/`attack-table`/`coverage-bar`/`contradiction`/`MermaidGraph` — the user's explicit requirement.
- **Type consistency:** `data.threat_model` keys defined in Task 2 are the exact keys consumed in Tasks 9–10 and asserted in Task 7; helper names (`_tm_entries`, `_tm_stride_matrix`, `_tm_cell_status`, `_tm_surface_coverage`, `_build_threat_surface_mermaid`, `_tm_asset_boundary`, `_tm_comparator_delta`) are introduced as stubs in Task 2 and implemented in Tasks 3–6.

## Execution handoff

Branch `feat/threat-model-report-scene` (already created off `main`, spec committed). Implement task-by-task with the chosen sub-skill.
