# Unified Metrics Model Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make a single canonical `40-synthesis/metrics.yaml` the only source of the report's finding/capability counts — computed once in synthesis, read by the transform, audit, and report-writer — so the Executive Summary and Severity distribution can never disagree.

**Architecture:** A new pure function `compute_metrics()` (synthesis) produces the full report `summary` block over the deduped∪apath finding universe; `build_rollups()` persists it as `metrics.yaml`. The transform's `summary_rollup()` becomes a passthrough of `artifacts.metrics`; the audit asserts the rendered `data.js.summary` equals `metrics.yaml` (no parallel recompute) plus internal-consistency invariants. The Overview renders a reconciling count strip, and both report-writer surfaces (HTML exec-summary + markdown advisory report) drop hand-authored counts.

**Tech Stack:** Python 3 (Click CLI, PyYAML, jsonschema, pytest), React/JSX report template (esbuild bundle via `tools/build_report_template.py`).

**Spec:** [docs/superpowers/specs/2026-06-04-unified-metrics-model-design.md](../specs/2026-06-04-unified-metrics-model-design.md)

---

## File Structure

**Created:**
- `tools/apd_gauntlet/synthesis/metrics.py` — the single `compute_metrics()` implementation (pure).
- `schemas/metrics.schema.json` — doc schema for `metrics.yaml`.
- `tests/unit/synthesis/test_metrics.py` — unit tests for `compute_metrics()`.

**Modified:**
- `tools/apd_gauntlet/synthesis/rollup.py` — `RollupResult.metrics`; `build_rollups()` calls `compute_metrics`; `_write()` emits `metrics.yaml`.
- `tools/apd_gauntlet/validate.py` — register `metrics.yaml → metrics.schema.json` in `SYNTHESIS_ROLLUPS`.
- `tools/apd_gauntlet/report/loader.py` — `RunArtifacts.metrics` (required); `load_run()` reads `metrics.yaml`.
- `tools/apd_gauntlet/report/transform.py` — `summary_rollup()` passthrough; `findings_array()` tier default.
- `tools/apd_gauntlet/synthesis/audit.py` — delete recompute; passthrough parity + internal-consistency check.
- `report-template/screens/Overview.jsx` — count strip + breakdown fix; rebuild bundle.
- `.claude/agents/apd-report-writer.md`, `templates/report-data.template.yaml`, `templates/advisory-report.template.md`, `.claude/workflows/apd-gauntlet.js` — prose stays qualitative; inputs updated.
- ~6 test files constructing `RunArtifacts(...)` + 3 MagicMock helpers — add `metrics`.
- Tracked fixtures: `examples/apd-20260601-claim-event-bus/expected/40-synthesis/{metrics.yaml, report-html/*}`; `tests/fixtures/report-html/claim-event-bus-golden-data.js`.

**Shared literal used by several test edits — `EMPTY_METRICS`** (a schema-valid all-zero metrics dict; copy verbatim where referenced):

```python
EMPTY_METRICS = {
    "schema_version": 1,
    "findings_total": 0, "findings_pre_dedup": 0,
    "cross_lens_merged_clusters": 0, "linked_clusters": 0,
    "bySeverity": {"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0},
    "byDisposition": {"gap": 0, "blocked": 0, "risk": 0, "uncertainty": 0, "ok": 0},
    "byTier": {"trustworthiness": 0, "scalability": 0, "auditability": 0},
    "capabilities_total": 0, "capabilities_pre_dedup": 0,
    "capabilitiesByMaturity": {"designed": 0, "implemented": 0, "tested": 0, "operationalized": 0},
    "contradictions": 0, "severity_disagreements": 0,
}
```

---

## Task 1: `compute_metrics()` — the single source

**Files:**
- Create: `tools/apd_gauntlet/synthesis/metrics.py`
- Test: `tests/unit/synthesis/test_metrics.py`

- [ ] **Step 1: Write the failing test**

Create `tests/unit/synthesis/test_metrics.py`:

```python
# tests/unit/synthesis/test_metrics.py
"""Unit tests for compute_metrics — the single canonical report summary block."""
from __future__ import annotations

from apd_gauntlet.synthesis.metrics import compute_metrics


def _f(fid, severity="high", disposition="gap", tier="trustworthiness", **extra):
    return {"id": fid, "severity": severity, "disposition": disposition,
            "apd_tier": tier, **extra}


def test_severity_counts_normalize_informational_to_info():
    findings = [_f("a", "informational"), _f("b", "critical"), _f("apath-1", "high")]
    m = compute_metrics(findings, [], [], [])
    assert m["bySeverity"] == {"critical": 1, "high": 1, "medium": 0, "low": 0, "info": 1}
    assert m["findings_total"] == 3


def test_missing_severity_disposition_tier_default():
    m = compute_metrics([{"id": "x"}], [], [], [])
    assert m["bySeverity"]["info"] == 1          # missing severity -> info
    assert m["byDisposition"]["gap"] == 1        # missing disposition -> gap
    assert m["byTier"]["trustworthiness"] == 1   # missing apd_tier -> trustworthiness


def test_capability_maturity_and_cluster_counts():
    caps = [{"id": "cap-1", "maturity": "tested"},
            {"id": "cap-merged-1", "maturity": "implemented", "lens_perspectives": [{}]}]
    m = compute_metrics([], caps, [], [])
    assert m["capabilities_total"] == 2
    assert m["capabilitiesByMaturity"]["tested"] == 1
    assert m["cross_lens_merged_clusters"] == 1


def test_contradiction_and_disagreement_counts():
    m = compute_metrics([], [], [{"x": 1}, {"y": 2}], [{"z": 3}])
    assert m["contradictions"] == 2
    assert m["severity_disagreements"] == 1


def test_internal_consistency_invariants_hold():
    findings = [_f("a", "high", "gap", "trustworthiness"),
                _f("b", "low", "risk", "scalability"),
                _f("c", "informational", "blocked", "auditability")]
    m = compute_metrics(findings, [], [], [])
    t = m["findings_total"]
    assert sum(m["bySeverity"].values()) == t
    assert sum(m["byTier"].values()) == t
    assert (m["byDisposition"]["gap"] + m["byDisposition"]["risk"]
            + m["byDisposition"]["uncertainty"] + m["byDisposition"]["blocked"]) == t


def test_schema_version_present():
    assert compute_metrics([], [], [], [])["schema_version"] == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit/synthesis/test_metrics.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'apd_gauntlet.synthesis.metrics'`

- [ ] **Step 3: Write the implementation**

Create `tools/apd_gauntlet/synthesis/metrics.py`:

```python
# tools/apd_gauntlet/synthesis/metrics.py
"""Canonical report summary-block metrics — the single source of truth.

compute_metrics() is the ONE implementation of the report summary block. It is
pure (takes already-loaded record lists, returns a dict) so it is trivially
unit-testable. build_rollups() calls it and persists the result as
40-synthesis/metrics.yaml; the transform reads that artifact verbatim and the
audit asserts the rendered data.js carries it faithfully.
"""
from __future__ import annotations

import collections
from typing import Any

SCHEMA_VERSION = 1

_INFORMATIONAL_TO_INFO = {"informational": "info"}


def _norm_sev(value: Any) -> str:
    s = str(value or "informational")
    return _INFORMATIONAL_TO_INFO.get(s, s)


def compute_metrics(
    findings: list[dict[str, Any]],
    capabilities: list[dict[str, Any]],
    contradictions: list[dict[str, Any]],
    severity_disagreements: list[dict[str, Any]],
) -> dict[str, Any]:
    """Return the canonical report summary block.

    ``findings`` MUST be the deduped-findings UNION the apath-* findings (the
    same union ``_load_deduped`` builds). Severity is normalized to ``info``
    inside, so no downstream re-normalization is needed.
    """
    by_sev = collections.Counter(_norm_sev(f.get("severity")) for f in findings)
    by_disp = collections.Counter(f.get("disposition", "gap") for f in findings)
    by_tier = collections.Counter(f.get("apd_tier", "trustworthiness") for f in findings)
    by_mat = collections.Counter(c.get("maturity", "implemented") for c in capabilities)

    cross_lens_merged = sum(
        1 for c in capabilities
        if c.get("merged") or (
            c.get("lens_perspectives") and c.get("id", "").startswith("cap-merged")
        )
    )
    linked_clusters = sum(1 for f in findings if f.get("linked_perspectives"))

    return {
        "schema_version": SCHEMA_VERSION,
        "findings_total": len(findings),
        "findings_pre_dedup": len(findings),
        "cross_lens_merged_clusters": cross_lens_merged,
        "linked_clusters": linked_clusters,
        "bySeverity": {
            "critical": by_sev.get("critical", 0),
            "high":     by_sev.get("high", 0),
            "medium":   by_sev.get("medium", 0),
            "low":      by_sev.get("low", 0),
            "info":     by_sev.get("info", 0),
        },
        "byDisposition": {
            "gap":         by_disp.get("gap", 0),
            "blocked":     by_disp.get("blocked", 0),
            "risk":        by_disp.get("risk", 0),
            "uncertainty": by_disp.get("uncertainty", 0),
            "ok":          0,
        },
        "byTier": {
            "trustworthiness": by_tier.get("trustworthiness", 0),
            "scalability":     by_tier.get("scalability", 0),
            "auditability":    by_tier.get("auditability", 0),
        },
        "capabilities_total": len(capabilities),
        "capabilities_pre_dedup": len(capabilities),
        "capabilitiesByMaturity": {
            "designed":        by_mat.get("designed", 0),
            "implemented":     by_mat.get("implemented", 0),
            "tested":          by_mat.get("tested", 0),
            "operationalized": by_mat.get("operationalized", 0),
        },
        "contradictions": len(contradictions),
        "severity_disagreements": len(severity_disagreements),
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/unit/synthesis/test_metrics.py -q`
Expected: PASS (6 passed)

- [ ] **Step 5: Commit**

```bash
git add tools/apd_gauntlet/synthesis/metrics.py tests/unit/synthesis/test_metrics.py
git commit -m "feat(metrics): add compute_metrics canonical report summary block"
```

---

## Task 2: `metrics.schema.json` + validator wiring

**Files:**
- Create: `schemas/metrics.schema.json`
- Modify: `tools/apd_gauntlet/validate.py:185-223` (`SYNTHESIS_ROLLUPS`)
- Test: `tests/unit/synthesis/test_metrics_schema.py`

- [ ] **Step 1: Write the failing test**

Create `tests/unit/synthesis/test_metrics_schema.py`:

```python
# tests/unit/synthesis/test_metrics_schema.py
"""metrics.yaml validates against metrics.schema.json; compute_metrics output is valid."""
from __future__ import annotations

import jsonschema
import pytest

from apd_gauntlet.synthesis.metrics import compute_metrics
from apd_gauntlet.validate import build_registry


def _validator():
    reg = build_registry()
    schema = reg.contents(
        "https://github.com/shoveleejoe/apd-gauntlet/schemas/metrics.schema.json"
    )
    return jsonschema.Draft202012Validator(schema, registry=reg)


def test_compute_metrics_output_validates():
    doc = compute_metrics([{"id": "a", "severity": "high"}], [], [], [])
    _validator().validate(doc)  # raises on failure


def test_missing_required_key_fails():
    doc = compute_metrics([], [], [], [])
    del doc["bySeverity"]
    with pytest.raises(jsonschema.ValidationError):
        _validator().validate(doc)


def test_negative_count_fails():
    doc = compute_metrics([], [], [], [])
    doc["findings_total"] = -1
    with pytest.raises(jsonschema.ValidationError):
        _validator().validate(doc)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit/synthesis/test_metrics_schema.py -q`
Expected: FAIL — registry has no `metrics.schema.json` (`KeyError`/`Unresolvable`).

- [ ] **Step 3: Create the schema**

Create `schemas/metrics.schema.json`:

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://github.com/shoveleejoe/apd-gauntlet/schemas/metrics.schema.json",
  "title": "APD Gauntlet Report Metrics (canonical summary block)",
  "type": "object",
  "additionalProperties": false,
  "required": [
    "schema_version", "findings_total", "findings_pre_dedup",
    "cross_lens_merged_clusters", "linked_clusters",
    "bySeverity", "byDisposition", "byTier",
    "capabilities_total", "capabilities_pre_dedup", "capabilitiesByMaturity",
    "contradictions", "severity_disagreements"
  ],
  "properties": {
    "schema_version": { "const": 1 },
    "findings_total": { "type": "integer", "minimum": 0 },
    "findings_pre_dedup": { "type": "integer", "minimum": 0 },
    "cross_lens_merged_clusters": { "type": "integer", "minimum": 0 },
    "linked_clusters": { "type": "integer", "minimum": 0 },
    "bySeverity": {
      "type": "object", "additionalProperties": false,
      "required": ["critical", "high", "medium", "low", "info"],
      "properties": {
        "critical": { "type": "integer", "minimum": 0 },
        "high":     { "type": "integer", "minimum": 0 },
        "medium":   { "type": "integer", "minimum": 0 },
        "low":      { "type": "integer", "minimum": 0 },
        "info":     { "type": "integer", "minimum": 0 }
      }
    },
    "byDisposition": {
      "type": "object", "additionalProperties": false,
      "required": ["gap", "blocked", "risk", "uncertainty", "ok"],
      "properties": {
        "gap":         { "type": "integer", "minimum": 0 },
        "blocked":     { "type": "integer", "minimum": 0 },
        "risk":        { "type": "integer", "minimum": 0 },
        "uncertainty": { "type": "integer", "minimum": 0 },
        "ok":          { "type": "integer", "minimum": 0 }
      }
    },
    "byTier": {
      "type": "object", "additionalProperties": false,
      "required": ["trustworthiness", "scalability", "auditability"],
      "properties": {
        "trustworthiness": { "type": "integer", "minimum": 0 },
        "scalability":     { "type": "integer", "minimum": 0 },
        "auditability":    { "type": "integer", "minimum": 0 }
      }
    },
    "capabilities_total": { "type": "integer", "minimum": 0 },
    "capabilities_pre_dedup": { "type": "integer", "minimum": 0 },
    "capabilitiesByMaturity": {
      "type": "object", "additionalProperties": false,
      "required": ["designed", "implemented", "tested", "operationalized"],
      "properties": {
        "designed":        { "type": "integer", "minimum": 0 },
        "implemented":     { "type": "integer", "minimum": 0 },
        "tested":          { "type": "integer", "minimum": 0 },
        "operationalized": { "type": "integer", "minimum": 0 }
      }
    },
    "contradictions": { "type": "integer", "minimum": 0 },
    "severity_disagreements": { "type": "integer", "minimum": 0 }
  }
}
```

- [ ] **Step 4: Wire the filename → schema mapping**

In `tools/apd_gauntlet/validate.py`, add a line to the `SYNTHESIS_ROLLUPS` dict (after the `report-data.yaml` entry, ~line 206):

```python
    # The canonical report summary block (unified-metrics-model).
    "metrics.yaml":                "metrics.schema.json",
```

(No `RECORD_KINDS` change — `metrics.yaml` is a doc, not a `*.findings.yaml` record file; `build_registry()` auto-indexes the new schema by its `$id`.)

- [ ] **Step 5: Run tests to verify they pass**

Run: `python -m pytest tests/unit/synthesis/test_metrics_schema.py -q`
Expected: PASS (3 passed)

- [ ] **Step 6: Commit**

```bash
git add schemas/metrics.schema.json tools/apd_gauntlet/validate.py tests/unit/synthesis/test_metrics_schema.py
git commit -m "feat(metrics): add metrics.schema.json and wire into validate"
```

---

## Task 3: Emit `metrics.yaml` from `build_rollups`; generate the example fixture's copy

**Files:**
- Modify: `tools/apd_gauntlet/synthesis/rollup.py` (`RollupResult` :47-54; `build_rollups` :228-254; `_write` :424-444; new `_read_records` helper)
- Test: `tests/unit/synthesis/test_rollup_metrics.py`
- Generate (commit): `examples/apd-20260601-claim-event-bus/expected/40-synthesis/metrics.yaml`

- [ ] **Step 1: Write the failing test**

Create `tests/unit/synthesis/test_rollup_metrics.py`:

```python
# tests/unit/synthesis/test_rollup_metrics.py
"""build_rollups emits 40-synthesis/metrics.yaml matching compute_metrics over deduped∪apath."""
from __future__ import annotations

import pathlib
import shutil

import yaml

from apd_gauntlet.synthesis.rollup import build_rollups

EXAMPLE = pathlib.Path(__file__).resolve().parents[2] / "examples" / \
    "apd-20260601-claim-event-bus" / "expected"


def test_build_rollups_emits_metrics_yaml(tmp_path: pathlib.Path):
    run = tmp_path / "run"
    shutil.copytree(EXAMPLE, run)
    # Remove any pre-existing metrics.yaml so we prove build_rollups writes it.
    (run / "40-synthesis" / "metrics.yaml").unlink(missing_ok=True)

    build_rollups(run)

    metrics = yaml.safe_load((run / "40-synthesis" / "metrics.yaml").read_text())
    assert metrics["schema_version"] == 1
    # Severity bucket sums reconcile to the total (internal consistency).
    assert sum(metrics["bySeverity"].values()) == metrics["findings_total"]
    assert sum(metrics["byTier"].values()) == metrics["findings_total"]
    assert metrics["findings_total"] >= 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit/synthesis/test_rollup_metrics.py -q`
Expected: FAIL — `metrics.yaml` is not written (file missing).

- [ ] **Step 3: Add `metrics` to `RollupResult`**

In `tools/apd_gauntlet/synthesis/rollup.py`, in the `RollupResult` dataclass (after `atlas`):

```python
    atlas: dict[str, Any] | None = None
    metrics: dict[str, Any] = field(default_factory=dict)
```

- [ ] **Step 4: Add the key-tolerant reader + wire `compute_metrics` into `build_rollups`**

In `tools/apd_gauntlet/synthesis/rollup.py`, add the import near the top (with the other relative imports):

```python
from .metrics import compute_metrics
```

Add this helper above `build_rollups`:

```python
def _read_records(path: Path, *keys: str) -> list[dict[str, Any]]:
    """Key-tolerant record reader matching loader.load_run's fallbacks so the
    metrics counts equal the transform's view of the same files."""
    if not path.is_file():
        return []
    doc = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(doc, dict):
        return []
    for key in keys:
        value = doc.get(key)
        if isinstance(value, list):
            return [r for r in value if isinstance(r, dict)]
    return []
```

In `build_rollups`, immediately before `_write(run_dir, result)`:

```python
    synth = run_dir / "40-synthesis"
    contradictions = _read_records(
        synth / "contradictions.yaml", "contradictions", "contradiction")
    sev_dis = _read_records(
        synth / "severity-disagreements.yaml",
        "severity_disagreements", "disagreements", "severity_disagreement")
    # findings already UNION apath-* (via _load_deduped); compute_metrics is the
    # single canonical report summary block.
    result.metrics = compute_metrics(findings, caps, contradictions, sev_dis)
```

- [ ] **Step 5: Emit `metrics.yaml` in `_write`**

In `tools/apd_gauntlet/synthesis/rollup.py`, in `_write()`, after the `apd-coverage-matrix.yaml` write:

```python
    (synth / "metrics.yaml").write_text(
        yaml.safe_dump(result.metrics, sort_keys=False), encoding="utf-8")
```

- [ ] **Step 6: Run test to verify it passes**

Run: `python -m pytest tests/unit/synthesis/test_rollup_metrics.py -q`
Expected: PASS (1 passed)

- [ ] **Step 7: Generate the example fixture's `metrics.yaml` (required by every later task that loads the example)**

Run: `python -m apd_gauntlet rollup examples/apd-20260601-claim-event-bus/expected`
Then confirm only `metrics.yaml` is new (coverage rollups are deterministic/idempotent):

Run: `git status --short examples/apd-20260601-claim-event-bus/expected/40-synthesis/`
Expected: a single new untracked file `…/40-synthesis/metrics.yaml` (no modified coverage YAMLs). If a coverage YAML shows as modified, inspect the diff — it should be empty/whitespace-only; if a real drift appears, STOP and investigate before committing.

- [ ] **Step 8: Commit**

```bash
git add tools/apd_gauntlet/synthesis/rollup.py tests/unit/synthesis/test_rollup_metrics.py \
        examples/apd-20260601-claim-event-bus/expected/40-synthesis/metrics.yaml
git commit -m "feat(metrics): emit 40-synthesis/metrics.yaml from build_rollups; seed example fixture"
```

---

## Task 4: Loader reads `metrics.yaml` (required) + fix all `RunArtifacts` construction sites

**Files:**
- Modify: `tools/apd_gauntlet/report/loader.py` (`RunArtifacts` :94-117; `load_run` :395-526)
- Modify (test constructors): `tests/unit/report/test_transform_attack_paths.py`, `test_transform_threat_model.py`, `test_transform_fallbacks.py`, `test_transform_taxonomy.py`, `test_tier4_manifest_fallbacks.py`, `test_tier4_shape_c_and_matrix.py`
- Modify (MagicMock helpers): `tests/unit/report/test_informational_severity.py:30`, `test_tier4_strengths_contract.py:20`, `test_tier2_isolation.py:22`
- Test: `tests/unit/report/test_loader_metrics.py`

- [ ] **Step 1: Write the failing test**

Create `tests/unit/report/test_loader_metrics.py`:

```python
# tests/unit/report/test_loader_metrics.py
"""load_run reads 40-synthesis/metrics.yaml; absence is a hard MissingArtifactError."""
from __future__ import annotations

import pathlib
import shutil

import pytest

from apd_gauntlet.report.loader import MissingArtifactError, load_run

EXAMPLE = pathlib.Path(__file__).resolve().parents[3] / "examples" / \
    "apd-20260601-claim-event-bus" / "expected"


def test_load_run_reads_metrics(tmp_path):
    run = tmp_path / "run"
    shutil.copytree(EXAMPLE, run)
    artifacts = load_run(run)
    assert artifacts.metrics["schema_version"] == 1
    assert "bySeverity" in artifacts.metrics
    assert "metrics.yaml" in artifacts.source_hashes


def test_load_run_missing_metrics_raises(tmp_path):
    run = tmp_path / "run"
    shutil.copytree(EXAMPLE, run)
    (run / "40-synthesis" / "metrics.yaml").unlink()
    with pytest.raises(MissingArtifactError):
        load_run(run)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit/report/test_loader_metrics.py -q`
Expected: FAIL — `RunArtifacts` has no `metrics` attribute / `load_run` does not read it.

- [ ] **Step 3: Add the required `metrics` field to `RunArtifacts`**

In `tools/apd_gauntlet/report/loader.py`, in the `RunArtifacts` dataclass, add `metrics` immediately after `report_data` (the last required field, before `source_hashes`):

```python
    report_data: dict[str, Any] | None
    metrics: dict[str, Any]
    source_hashes: dict[str, str] = field(default_factory=dict)
```

- [ ] **Step 4: Read `metrics.yaml` in `load_run`**

In `tools/apd_gauntlet/report/loader.py`, add to the required-path block (with the other `_required` calls near the top of `load_run`):

```python
    metrics_path = _required(run_dir, "40-synthesis/metrics.yaml")
```

In the read-with-hash pass (with the other `_yaml_with_hash` reads):

```python
    metrics_doc, source_hashes["metrics.yaml"] = _yaml_with_hash(metrics_path)
```

In the `return RunArtifacts(...)` call, add the keyword (right after `report_data=report_data,`):

```python
        report_data=report_data,
        metrics=metrics_doc,
```

- [ ] **Step 5: Run the loader test to verify it passes**

Run: `python -m pytest tests/unit/report/test_loader_metrics.py -q`
Expected: PASS (2 passed)

- [ ] **Step 6: Fix the keyword `RunArtifacts(...)` construction sites**

In each of the six test files, every `RunArtifacts(...)` call ends with `attack_path_findings=[..], report_data=...,`. Add a `metrics=EMPTY_METRICS` keyword immediately after the `report_data=` keyword at each site. Add the `EMPTY_METRICS` literal (from the File Structure section) once near the top of each file (after imports). Sites: `test_transform_attack_paths.py` (8), `test_transform_threat_model.py` (2), `test_transform_fallbacks.py` (1+), `test_transform_taxonomy.py` (1+), `test_tier4_manifest_fallbacks.py` (1+), `test_tier4_shape_c_and_matrix.py` (1+).

Find every site:

Run: `grep -rn "RunArtifacts(" tests/`

For each, the edit pattern is:

```python
        attack_path_findings=[...], report_data=None,
        metrics=EMPTY_METRICS,
    )
```

- [ ] **Step 7: Fix the MagicMock helpers (they will NOT fail loud — set `metrics` explicitly)**

In `tests/unit/report/test_informational_severity.py`, `test_tier4_strengths_contract.py`, and `test_tier2_isolation.py`, inside each `_make_minimal_artifacts()` (a `MagicMock`), add before `return a`:

```python
    a.metrics = EMPTY_METRICS
```

Add the `EMPTY_METRICS` literal near the top of each file (after imports). (Without this, `summary_rollup` returns a `MagicMock` instead of a dict and assertions fail confusingly.)

- [ ] **Step 8: Run the full report + tier4 test suites to verify green**

Run: `python -m pytest tests/unit/report -q`
Expected: PASS (collection errors from missing `metrics=` are gone; any remaining summary-content failures are addressed in Task 5).
Note: tests asserting on `data["summary"]`/`summary_rollup` content depend on Task 5 — if a handful fail purely on summary shape, proceed to Task 5 and re-run; they must be green by end of Task 5.

- [ ] **Step 9: Commit**

```bash
git add tools/apd_gauntlet/report/loader.py tests/unit/report/test_loader_metrics.py \
        tests/unit/report/test_transform_attack_paths.py tests/unit/report/test_transform_threat_model.py \
        tests/unit/report/test_transform_fallbacks.py tests/unit/report/test_transform_taxonomy.py \
        tests/unit/report/test_tier4_manifest_fallbacks.py tests/unit/report/test_tier4_shape_c_and_matrix.py \
        tests/unit/report/test_informational_severity.py tests/unit/report/test_tier4_strengths_contract.py \
        tests/unit/report/test_tier2_isolation.py
git commit -m "feat(metrics): load required metrics.yaml; update RunArtifacts constructors"
```

---

## Task 5: `summary_rollup` passthrough + `findings_array` tier default

**Files:**
- Modify: `tools/apd_gauntlet/report/transform.py` (`summary_rollup` :195-250; `findings_array` :397 the `"tier"` line)
- Modify: `tests/unit/report/test_informational_severity.py` (`test_summary_rollup_counts_informational_under_info`)
- Test: `tests/unit/report/test_summary_passthrough.py`

- [ ] **Step 1: Write the failing test**

Create `tests/unit/report/test_summary_passthrough.py`:

```python
# tests/unit/report/test_summary_passthrough.py
"""summary_rollup is a pure passthrough of artifacts.metrics (schema_version stripped)."""
from __future__ import annotations

from unittest.mock import MagicMock

from apd_gauntlet.report.transform import summary_rollup


def test_summary_rollup_returns_metrics_without_schema_version():
    a = MagicMock()
    a.metrics = {
        "schema_version": 1, "findings_total": 3,
        "bySeverity": {"critical": 1, "high": 1, "medium": 0, "low": 0, "info": 1},
    }
    s = summary_rollup(a)
    assert "schema_version" not in s
    assert s["findings_total"] == 3
    assert s["bySeverity"]["critical"] == 1


def test_summary_rollup_does_not_recompute_from_findings():
    a = MagicMock()
    a.metrics = {"findings_total": 99}
    a.deduped_findings = [{"id": "x", "severity": "high"}]   # ignored by passthrough
    a.attack_path_findings = []
    assert summary_rollup(a)["findings_total"] == 99
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit/report/test_summary_passthrough.py -q`
Expected: FAIL — current `summary_rollup` recomputes from `deduped_findings` (returns `findings_total == 1`, not 99) and includes `schema_version` is absent but recompute differs.

- [ ] **Step 3: Rewrite `summary_rollup` as passthrough**

In `tools/apd_gauntlet/report/transform.py`, replace the entire body of `summary_rollup` (lines 195-250) with:

```python
def summary_rollup(artifacts: RunArtifacts) -> dict[str, Any]:
    """Return the data.summary block — the canonical metrics, passthrough.

    Metrics are computed once in synthesis (synthesis/metrics.py) and persisted
    as 40-synthesis/metrics.yaml; this strips the schema_version envelope and
    returns the rest verbatim. NO recomputation — single source of truth.
    """
    metrics = dict(artifacts.metrics or {})
    metrics.pop("schema_version", None)
    return metrics
```

(The `import collections` at the top of transform.py may now be unused — leave it only if other functions in the file use it; otherwise remove it. Check with `grep -n "collections\." tools/apd_gauntlet/report/transform.py`.)

- [ ] **Step 4: Default the tier in `findings_array`**

In `tools/apd_gauntlet/report/transform.py`, in `findings_array`, change the `"tier"` entry:

```python
            "tier":         f.get("apd_tier") or "trustworthiness",
```

(Matches `compute_metrics`'s tier defaulting so §2 tier-posture sums cannot drift below `byTier`.)

- [ ] **Step 5: Update the informational-bucketing test to passthrough semantics**

In `tests/unit/report/test_informational_severity.py`, replace `test_summary_rollup_counts_informational_under_info` with:

```python
def test_summary_rollup_passthrough_returns_metrics_bysev() -> None:
    """summary_rollup now passes through artifacts.metrics; the informational→info
    bucketing itself is covered by tests/unit/synthesis/test_metrics.py."""
    artifacts = _make_minimal_artifacts()
    artifacts.metrics = {**EMPTY_METRICS,
                         "findings_total": 1,
                         "bySeverity": {"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 1}}
    summary = summary_rollup(artifacts)
    assert summary["bySeverity"]["info"] == 1
    assert "schema_version" not in summary
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `python -m pytest tests/unit/report/test_summary_passthrough.py tests/unit/report/test_informational_severity.py tests/unit/report/test_transform_summary.py -q`
Expected: PASS. (`test_transform_summary.py` is unchanged — it exercises the full `build_rollups → metrics.yaml → load_run → summary_rollup` round-trip via the example fixture and its invariants still hold.)

- [ ] **Step 7: Commit**

```bash
git add tools/apd_gauntlet/report/transform.py tests/unit/report/test_summary_passthrough.py \
        tests/unit/report/test_informational_severity.py
git commit -m "feat(metrics): summary_rollup passthrough; findings_array tier default"
```

---

## Task 6: Audit — delete recompute, add passthrough parity + internal-consistency

**Files:**
- Modify: `tools/apd_gauntlet/synthesis/audit.py` (delete `_INFORMATIONAL_TO_INFO` :18 and the `_norm_sev`/`count_parity_*` block ~169-187; add parity + consistency)
- Test: `tests/test_cli_audit_report.py` (add three tests)

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_cli_audit_report.py` (it already builds the example report into a tmp dir then audits — reuse that pattern; the helper that builds+audits an enriched copy is used by `test_completeness_gate_passes_on_enriched_example`):

```python
def test_count_parity_passes_on_faithful_build(tmp_path):
    run = _build_enriched_run(tmp_path)          # existing helper: copies example, build-reports
    result = audit_report(run)
    assert result.checks["count_parity_severity"].ok
    assert result.checks["count_parity_totals"].ok
    assert result.checks["metrics_internal_consistency"].ok


def test_count_parity_fails_on_injected_severity_drift(tmp_path):
    run = _build_enriched_run(tmp_path)
    data_js = run / "40-synthesis" / "report-html" / "data.js"
    text = data_js.read_text()
    # Perturb the rendered critical count so data.js diverges from metrics.yaml.
    text = text.replace('"critical":', '"critical": 999, "_orig_critical":', 1)
    data_js.write_text(text)
    result = audit_report(run)
    assert not result.checks["count_parity_severity"].ok


def test_metrics_internal_consistency_fails_on_corrupt_metrics(tmp_path):
    run = _build_enriched_run(tmp_path)
    metrics = run / "40-synthesis" / "metrics.yaml"
    doc = yaml.safe_load(metrics.read_text())
    doc["findings_total"] = doc["findings_total"] + 7   # break the invariant
    metrics.write_text(yaml.safe_dump(doc, sort_keys=False))
    # Rebuild data.js so it carries the corrupted total (parity stays ok; consistency must fail).
    from apd_gauntlet.report.build import build_report
    build_report(run, out_dir=run / "40-synthesis" / "report-html")
    result = audit_report(run)
    assert not result.checks["metrics_internal_consistency"].ok
```

If `_build_enriched_run` does not already exist as a shared helper in this file, factor it from the existing enriched-example test (it copies `examples/apd-20260601-claim-event-bus/expected` to `tmp_path/run` and runs `build_report(run, out_dir=run/"40-synthesis"/"report-html")`), and ensure `import yaml` is present.

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_cli_audit_report.py -q -k "count_parity or metrics_internal"`
Expected: FAIL — `metrics_internal_consistency` check does not exist yet; severity parity still recomputes from YAML rather than comparing to metrics.yaml.

- [ ] **Step 3: Delete the old recompute**

In `tools/apd_gauntlet/synthesis/audit.py`:
- Delete the module constant `_INFORMATIONAL_TO_INFO = {"informational": "info"}` (line 18).
- Inside `audit_report`, delete the `_norm_sev` nested def and the `count_parity_severity` + `count_parity_totals` block (the ~169-187 region that builds `by_sev = collections.Counter(_norm_sev(f) for f in deduped_f + apath_f)` and the two `_check` calls).
- If `import collections` is now unused in this file, remove it (`grep -n "collections\." tools/apd_gauntlet/synthesis/audit.py`).

- [ ] **Step 4: Add passthrough parity + internal-consistency**

In `tools/apd_gauntlet/synthesis/audit.py`, in place of the deleted block (still inside `audit_report`, where `synth` and `parsed` are in scope):

```python
    # Count parity (passthrough): the rendered data.js.summary must faithfully
    # carry the canonical 40-synthesis/metrics.yaml. compute_metrics
    # (synthesis/metrics.py) is the single source — no independent recompute.
    _m_raw = yaml.safe_load((synth / "metrics.yaml").read_text(encoding="utf-8")) \
        if (synth / "metrics.yaml").is_file() else None
    metrics_doc = _m_raw if isinstance(_m_raw, dict) else {}
    m_by_sev = metrics_doc.get("bySeverity") or {}
    data_summary = parsed.get("summary") or {}
    data_by_sev = data_summary.get("bySeverity") or {}
    sev_ok = all(data_by_sev.get(k, 0) == m_by_sev.get(k, 0)
                 for k in ("critical", "high", "medium", "low", "info"))
    _check(result, "count_parity_severity", sev_ok,
           f"metrics.yaml={dict(m_by_sev)} data.js={data_by_sev}")

    m_total = metrics_doc.get("findings_total")
    data_total = data_summary.get("findings_total")
    _check(result, "count_parity_totals", data_total == m_total,
           f"data.js={data_total} metrics.yaml={m_total}")

    def _sum(d: dict[str, Any], *keys: str) -> int:
        return sum(int((d or {}).get(k, 0)) for k in keys)

    total = int(m_total or 0)
    by_tier = metrics_doc.get("byTier") or {}
    by_disp = metrics_doc.get("byDisposition") or {}
    sev_sum = _sum(m_by_sev, "critical", "high", "medium", "low", "info")
    tier_sum = _sum(by_tier, "trustworthiness", "scalability", "auditability")
    disp_sum = _sum(by_disp, "gap", "risk", "uncertainty", "blocked")
    _check(result, "metrics_internal_consistency",
           sev_sum == total and tier_sum == total and disp_sum == total,
           f"total={total} sev_sum={sev_sum} tier_sum={tier_sum} disp_sum={disp_sum}")
```

(`yaml` is already imported in audit.py — it is used for `rd_path` reading.)

- [ ] **Step 5: Run tests to verify they pass**

Run: `python -m pytest tests/test_cli_audit_report.py -q`
Expected: PASS (including the three new tests; existing audit tests unaffected — `nist_rollup_parity` is a separate check left unchanged).

- [ ] **Step 6: Commit**

```bash
git add tools/apd_gauntlet/synthesis/audit.py tests/test_cli_audit_report.py
git commit -m "feat(metrics): audit passthrough parity + internal-consistency; drop recompute"
```

---

## Task 7: Overview count strip + breakdown fix + rebuild bundle

**Files:**
- Modify: `report-template/screens/Overview.jsx` (headline-grid breakdown :27-33; add count strip)
- Rebuild: `tools/apd_gauntlet/data/report-template/*` via `tools/build_report_template.py`
- Test: `tests/unit/report/test_overview_breakdown.py`

- [ ] **Step 1: Write the failing test (JSX source assertion)**

Create `tests/unit/report/test_overview_breakdown.py`:

```python
# tests/unit/report/test_overview_breakdown.py
"""The Overview headline-grid breakdown must include critical and info so it
reconciles with findings_total, and a count strip must render from data.summary."""
from __future__ import annotations

import pathlib

SRC = (pathlib.Path(__file__).resolve().parents[3]
       / "report-template" / "screens" / "Overview.jsx").read_text()


def test_breakdown_includes_critical_and_info():
    # The headline breakdown previously showed only high/medium/low.
    assert "s.bySeverity.critical" in SRC
    assert "s.bySeverity.info" in SRC


def test_count_strip_present():
    assert "count-strip" in SRC
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit/report/test_overview_breakdown.py -q`
Expected: FAIL — breakdown omits critical/info; no `count-strip`.

- [ ] **Step 3: Edit `Overview.jsx`**

In `report-template/screens/Overview.jsx`, replace the `headline-grid__breakdown` block inside the Findings cell (currently showing high/med/low) with the full five-bucket breakdown:

```jsx
              <div className="headline-grid__breakdown">
                <span>{s.bySeverity.critical} crit</span>
                <span>·</span>
                <span>{s.bySeverity.high} high</span>
                <span>·</span>
                <span>{s.bySeverity.medium} med</span>
                <span>·</span>
                <span>{s.bySeverity.low} low</span>
                <span>·</span>
                <span>{s.bySeverity.info} info</span>
              </div>
```

Add a reconciling count strip at the top of the exec-summary `<section>` (immediately after the `§ 1 — Executive Summary` eyebrow `<div>`):

```jsx
          <div className="count-strip">
            <strong>{s.findings_total}</strong> findings —{" "}
            {s.bySeverity.critical} critical · {s.bySeverity.high} high ·{" "}
            {s.bySeverity.medium} medium · {s.bySeverity.low} low ·{" "}
            {s.bySeverity.info} info
          </div>
```

(No new CSS is required — `count-strip` inherits default text styling; if a styled treatment is wanted later it can reuse existing tokens. Keep this task scoped to structure + data binding.)

- [ ] **Step 4: Rebuild the precompiled bundle**

Run: `python tools/build_report_template.py`
Then verify freshness passes:
Run: `python -m pytest tests/unit/report/test_tier3_bundle_freshness.py -q`
Expected: PASS (the `.source-hash` now matches the rebuilt sources).

- [ ] **Step 5: Run the JSX assertion test**

Run: `python -m pytest tests/unit/report/test_overview_breakdown.py -q`
Expected: PASS (2 passed)

- [ ] **Step 6: Commit**

```bash
git add report-template/screens/Overview.jsx tests/unit/report/test_overview_breakdown.py \
        tools/apd_gauntlet/data/report-template/
git commit -m "feat(report): Overview count strip + full severity breakdown; rebuild bundle"
```

---

## Task 8: Report-writer prose stays qualitative (both surfaces) + inputs

**Files:**
- Modify: `.claude/agents/apd-report-writer.md` (Inputs + Executive summary guidance)
- Modify: `templates/report-data.template.yaml` (exec_summary placeholder)
- Modify: `templates/advisory-report.template.md` (§1 Finding/Capability posture — lines 28, 30)
- Modify: `.claude/workflows/apd-gauntlet.js` (~line 568 report-writer read list)
- Test: `tests/test_report_writer_qualitative.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_report_writer_qualitative.py`:

```python
# tests/test_report_writer_qualitative.py
"""The report-writer is told metrics render structurally; prose stays qualitative,
and metrics.yaml + attack-path findings are declared inputs on both surfaces."""
from __future__ import annotations

import pathlib

REPO = pathlib.Path(__file__).resolve().parents[1]
AGENT = (REPO / ".claude" / "agents" / "apd-report-writer.md").read_text()
ADVISORY_TMPL = (REPO / "templates" / "advisory-report.template.md").read_text()


def test_agent_declares_metrics_and_apath_inputs():
    assert "metrics.yaml" in AGENT
    assert "attack-path.findings.yaml" in AGENT


def test_agent_instructs_qualitative_prose():
    lowered = AGENT.lower()
    assert "do not restate" in lowered or "do not author" in lowered
    assert "qualitative" in lowered


def test_advisory_template_drops_literal_count_prompts():
    # The old §1 prompted "<n> critical, <n> high, <n> medium, <n> low, <n> informational".
    assert "<n> critical, <n> high, <n> medium, <n> low" not in ADVISORY_TMPL
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_report_writer_qualitative.py -q`
Expected: FAIL — agent doc lacks `metrics.yaml`/qualitative guidance; advisory template still prompts literal counts.

- [ ] **Step 3: Edit the report-writer agent doc**

In `.claude/agents/apd-report-writer.md`, in the `## Inputs` list, add two bullets:

```markdown
- `40-synthesis/metrics.yaml` (the canonical report summary block — the authoritative counts)
- `40-synthesis/attack-path.findings.yaml` (apath-* findings, when present)
```

Replace the `## Executive summary guidance` section body with:

```markdown
## Executive summary guidance

The opening paragraph of `exec_summary` must name the domain pack(s) the run
examined, read from the run's `.apd-run.yaml` `domains` list (e.g. "Reviewed
across the PBM and API-security domains.").

Keep the prose **qualitative**. Do NOT restate raw totals or per-severity
counts: the authoritative numbers render structurally from `metrics.yaml` (the
HTML Overview count strip and the markdown report read them directly). Describe
the *shape* of the assessment (e.g. "a concentration of high-severity
auditability gaps against strong trustworthiness posture"), not the digits.
```

- [ ] **Step 4: Edit the report-data template**

In `templates/report-data.template.yaml`, replace the two `exec_summary.paragraphs` placeholder lines with count-free, qualitative guidance:

```yaml
exec_summary:
  paragraphs:
    - "<2-4 sentences framing the run — subject, domain-pack applicability, the headline architectural signal (qualitative; do NOT state raw counts — they render from metrics.yaml).>"
    - "<2-3 more sentences on the dedup/cluster shape and what is most actionable next, qualitatively.>"
```

- [ ] **Step 5: Edit the markdown advisory-report template (§1)**

In `templates/advisory-report.template.md`, replace the **Finding posture** paragraph (line 28) and **Capability posture** paragraph (line 30) with qualitative versions:

```markdown
**Finding posture.** One paragraph describing the *shape* of the assessment qualitatively — which tiers/goals carry the headline gaps and which carry strength (e.g. "predominantly auditability gaps with strong trustworthiness posture"). Do NOT hand-type counts: the authoritative finding numbers live in `40-synthesis/metrics.yaml` and the HTML report's Overview.
```

```markdown
**Capability posture.** One paragraph naming, qualitatively, what was confirmed and where coverage is strongest vs. thinnest across tiers/goals. Do NOT hand-type maturity counts — they are carried by `metrics.yaml` and the HTML report.
```

- [ ] **Step 6: Edit the workflow read list**

In `.claude/workflows/apd-gauntlet.js` (~line 568), in the report-writer step prompt string, add `metrics.yaml` to the read list:

```javascript
  'Read 40-synthesis/metrics.yaml + deduped-findings.yaml + attack-path.findings.yaml (apath-*, when present) + ' +
```

- [ ] **Step 7: Run tests to verify they pass**

Run: `python -m pytest tests/test_report_writer_qualitative.py -q`
Expected: PASS (3 passed)

- [ ] **Step 8: Commit**

```bash
git add .claude/agents/apd-report-writer.md templates/report-data.template.yaml \
        templates/advisory-report.template.md .claude/workflows/apd-gauntlet.js \
        tests/test_report_writer_qualitative.py
git commit -m "feat(report): report-writer prose stays qualitative; metrics inputs declared (both surfaces)"
```

---

## Task 9: Regenerate tracked report artifacts + full verification

**Files:**
- Regenerate (commit): `examples/apd-20260601-claim-event-bus/expected/40-synthesis/report-html/{data.js,app.js,.source-hash,...}`
- Regenerate (commit): `tests/fixtures/report-html/claim-event-bus-golden-data.js`

- [ ] **Step 1: Regenerate the example's tracked report-html (in place)**

Run: `python -m apd_gauntlet build-report examples/apd-20260601-claim-event-bus/expected`
(Default `--out` is `<run_dir>/40-synthesis/report-html/`, which is the tracked dir.)

- [ ] **Step 2: Regenerate the byte-exact golden** (per `test_example_golden.py` header recipe)

Run: `python -m apd_gauntlet build-report examples/apd-20260601-claim-event-bus/expected --out /tmp/golden && cp /tmp/golden/data.js tests/fixtures/report-html/claim-event-bus-golden-data.js`

- [ ] **Step 3: Run the golden + integration report tests**

Run: `python -m pytest tests/integration/report/test_example_golden.py -q`
Expected: PASS (the freshly built `data.js` is byte-identical to the regenerated golden).

- [ ] **Step 4: Run the full test suite**

Run: `python -m pytest -q`
Expected: PASS (full suite green — no collection errors, no count-parity failures).

- [ ] **Step 5: Run the full validate + audit on the example to prove the pipeline**

Run: `python -m apd_gauntlet validate examples/apd-20260601-claim-event-bus/expected --schema-only`
Expected: no errors (metrics.yaml validates against metrics.schema.json).

Run: `python -m apd_gauntlet audit-report examples/apd-20260601-claim-event-bus/expected`
Expected: `count_parity_severity`, `count_parity_totals`, and `metrics_internal_consistency` all pass.

- [ ] **Step 6: Run the markdownlint glob locally (CI parity)**

Run: `npx markdownlint-cli2 "docs/**/*.md"` (or the repo's configured markdownlint command)
Expected: no new errors introduced by this branch.

- [ ] **Step 7: Commit**

```bash
git add examples/apd-20260601-claim-event-bus/expected/40-synthesis/report-html/ \
        tests/fixtures/report-html/claim-event-bus-golden-data.js
git commit -m "chore(metrics): regenerate example report-html + byte-exact golden"
```

---

## Self-Review (completed by plan author)

**Spec coverage:** Every §6 component maps to a task — compute_metrics+schema (T1/T2), rollup emit (T3), loader (T4), transform passthrough+tier default (T5), audit passthrough+consistency (T6), Overview strip+breakdown (T7), agent/templates/workflow incl. markdown surface (T8), fixtures+golden+verification (T9). §7 removals are in T5/T6. §8 migration (example metrics in T3, tracked report-html + golden in T9; no `runs/*` commits, legacy fixture a no-op) honored. §5.3 three invariants in T1+T6. §2 `summarize_run` carve-out is a non-goal (untouched).

**Placeholder scan:** No TBD/TODO; every code step shows full code; every command states expected output.

**Type consistency:** `compute_metrics(findings, capabilities, contradictions, severity_disagreements)` used identically in T1 (def), T3 (call). `RunArtifacts.metrics` (T4) ↔ `artifacts.metrics` (T5 passthrough) ↔ `metrics.yaml` (T3 emit, T6 audit read) consistent. `EMPTY_METRICS` literal defined once and reused. Check ids `count_parity_severity`/`count_parity_totals`/`metrics_internal_consistency` consistent across T6 impl and tests.

**Known seam to watch during execution:** T4 makes `metrics.yaml` a required artifact; T3 Step 7 seeds the example fixture *before* T4, so `load_run(example_run)` keeps working. If any non-example committed run is discovered to be `load_run`'d by a test, seed its `metrics.yaml` the same way (none known — `runs/*` is gitignored, `legacy-coverage-shapes` is not loaded).
