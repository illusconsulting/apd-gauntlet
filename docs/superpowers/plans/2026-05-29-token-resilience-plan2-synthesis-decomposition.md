# Token-Resilience Plan 2 — Synthesis Decomposition (B) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Decompose the monolithic `apd-synthesizer` LLM context into a deterministic Python backbone (`cluster-candidates` → `apply-clusters` → `rollup` → `audit-report`) plus three small-context LLM agents (`apd-cluster-adjudicator`, `apd-report-writer`, `apd-report-auditor`), re-wiring the EXISTING `build-report` out of the synthesizer into a first-class phase. The decomposed pipeline must reproduce outputs equivalent (modulo deterministic ordering) to the committed golden 40-synthesis for the deterministic artifacts — the merged record semantics + nist-coverage/attack-exposure membership and posture. The `apd-coverage-matrix` reproduces the golden shape and per-cell posture semantics but NOT its editorial logical-asset component labels (I1 — see `_matrix_rollup`); the editorial report-data/advisory prose is likewise not a byte-equivalence target. The legacy `apd-synthesizer` stays a maintained fallback.

**Architecture:** A new `tools/apd_gauntlet/synthesis/` package houses one module per Python step (`loader.py`, `coverage_logic.py`, `cluster.py`, `apply.py`, `rollup.py`, `audit.py`), each with a single top-level entry function called from a lazy import inside a `@main.command` in `cli.py` — mirroring the `attack_path/` precedent exactly. `coverage_logic.py` is EXTRACTED from `report/transform.py` (so both `rollup` and `transform` import the shared NIST/ATT&CK/posture helpers, breaking a `report → synthesis` cycle by living in `synthesis` and being imported by `report.transform`). Four new whole-document schemas (`cluster-candidates`, `cluster-decisions`, `rejected-records`, `report-audit`) plus five thin `$ref` wrapper schemas (`nist-coverage-doc`, `attack-exposure-doc`, `coverage-matrix-doc`, `severity-disagreements-doc`, `contradictions-doc`) wire into `validate.SYNTHESIS_ROLLUPS` so the workflow `phaseDone` guard can `validate --schema-only` the new artifacts. Three new agent `.md` files carry the Plan-1 receipt contract. Equivalence is proven by a NORMALIZED-CONTENT comparator against `examples/apd-20260601-claim-event-bus/expected/` (the canonical complete output set), scoped to the deterministic artifacts (merged-record semantics + nist-coverage projection); the matrix component labels and editorial prose are explicitly out of the equivalence target (I1).

**Tech Stack:** Python 3.10+, `click` (CLI), `jsonschema` (Draft 2020-12) + `referencing.Registry`, `PyYAML` (`yaml.safe_dump(sort_keys=False)`), `pytest` + `click.testing.CliRunner`, `ruff`, `mypy`, `markdownlint` (CI globs). Source under `tools/apd_gauntlet/`; tests under `tests/`.

**Reference:** Design doc `docs/superpowers/specs/2026-05-29-apd-token-resilience-design.md` (§7 Phase-5 decomposition table, §7.1 per-step responsibilities, §7.2 synthesizer fallback, §10 component inventory, §11 migration/validation). Conventions inherited verbatim from `docs/superpowers/plans/2026-05-29-token-resilience-plan1-foundations.md` (Plan 1, already landed: `validate --errors-only/--tier`; `schemas/agent-receipt.schema.json`; the `## Final message` receipt lint rule in `tools/apd_gauntlet/lint_agents.py`). This is Plan 2 of 3 (Plan 1 = foundations, Plan 3 = workflow runner + audit-loop wiring + synthesizer fallback dispatch).

---

## File Structure

| Path | Responsibility | Action |
|---|---|---|
| `tools/apd_gauntlet/synthesis/__init__.py` | Docstring-only package marker (no re-exports) — mirrors `attack_path/__init__.py` | Create |
| `tools/apd_gauntlet/synthesis/loader.py` | `load_corpus(run_dir, *, include_attack_path=False)` shared corpus loader (adds apath + tmeval inclusion flag vs `cli._load_records`) | Create |
| `tools/apd_gauntlet/synthesis/coverage_logic.py` | Deterministic coverage helpers EXTRACTED from `transform.py` (`_normalize_nist_id`, `_nist_family_of`, posture, 9-goal order, cap indexes) | Create |
| `tools/apd_gauntlet/synthesis/cluster.py` | `build_candidates(run_dir, *, max_group_size=8)` — 3 mechanical signals + union-find + group-size bounding | Create |
| `tools/apd_gauntlet/synthesis/apply.py` | `apply_clusters(run_dir)` — merge/link/separate; merged-id sha8; union mappings; conservative maturity; emits deduped + sev-dis + rejected; `AdjudicationMissing` exception | Create |
| `tools/apd_gauntlet/synthesis/rollup.py` | `build_rollups(run_dir)` — canonical list-shaped coverage YAMLs (nist/attack-exposure/matrix + cwe/owasp/d3fend when declared) | Create |
| `tools/apd_gauntlet/synthesis/audit.py` | `audit_report(run_dir)` + `parse_data_js(path)` — structural data.js↔YAML cross-check, compact `report-audit.yaml` | Create |
| `tools/apd_gauntlet/report/transform.py` | Re-point the 3 NIST-id leaf helpers (`_normalize_nist_id`/`_normalize_nist_ids`/`_nist_family_of`) to `synthesis.coverage_logic`; KEEP `_posture` + the warnings-aware `_extract_ids_from_mapping` (deliberate siblings, M1); keep 4-shape tolerance | Modify |
| `tools/apd_gauntlet/cli.py` | Add 4 `@main.command` registrations + `_write_*` helpers mirroring `analyze-attack-paths` | Modify |
| `tools/apd_gauntlet/validate.py` | Wire 4 new-artifact schemas + 3 wrapper schemas into `SYNTHESIS_ROLLUPS` | Modify |
| `schemas/cluster-candidates.schema.json` | Whole-doc schema for 5a output | Create |
| `schemas/cluster-decisions.schema.json` | Whole-doc schema for 5b LLM output | Create |
| `schemas/rejected-records.schema.json` | Whole-doc schema for apply-clusters `rejected-records.yaml` | Create |
| `schemas/report-audit.schema.json` | Whole-doc schema for 5g compact audit output | Create |
| `schemas/nist-coverage-doc.schema.json` | Thin `$ref` wrapper: `{controls: [nist-coverage.schema.json]}` | Create |
| `schemas/attack-exposure-doc.schema.json` | Thin `$ref` wrapper: `{techniques: [attack-exposure.schema.json]}` | Create |
| `schemas/coverage-matrix-doc.schema.json` | Thin `$ref` wrapper: `{components: [coverage-matrix.schema.json]}` | Create |
| `schemas/severity-disagreements-doc.schema.json` | Thin `$ref` wrapper: `{severity_disagreements: [severity-disagreement.schema.json]}` | Create |
| `schemas/contradictions-doc.schema.json` | Thin `$ref` wrapper: `{contradictions: [contradiction.schema.json]}` | Create |
| `.claude/agents/apd-cluster-adjudicator.md` | 5b LLM agent — disposition + merged prose + contradiction classification | Create |
| `.claude/agents/apd-report-writer.md` | 5e LLM agent — editorial report-data.yaml + advisory-report.md | Create |
| `.claude/agents/apd-report-auditor.md` | 5g LLM agent — semantic faithfulness gate | Create |
| `.claude/agents/apd-synthesizer.md` | Remove the `## Trailing HTML build` section (build-report re-wired out) | Modify |
| `tests/fixtures/cluster_decisions/example-cluster-decisions.yaml` | Hand-built decisions fixture driving the merge in the example run | Create |
| `tests/test_synthesis_loader.py` | Cover `load_corpus` apath/tmeval inclusion | Create |
| `tests/test_synthesis_coverage_logic.py` | Cover extracted helpers + transform re-import | Create |
| `tests/test_cli_cluster_candidates.py` | CliRunner + schema-validate cluster-candidates.yaml | Create |
| `tests/test_cli_apply_clusters.py` | CliRunner + merge/link/separate + rejected schema | Create |
| `tests/test_cli_rollup.py` | CliRunner + wrapper-schema validation of rollups | Create |
| `tests/test_cli_audit_report.py` | CliRunner + audit pass/fail exit codes | Create |
| `tests/test_synthesis_equivalence.py` | Normalized-content comparator vs example golden | Create |
| `tests/test_cluster_candidates_schema.py` | Content tests for cluster-candidates schema | Create |
| `tests/test_cluster_decisions_schema.py` | Content tests for cluster-decisions schema | Create |
| `tests/test_rejected_records_schema.py` | Content tests for rejected-records schema | Create |
| `tests/test_report_audit_schema.py` | Content tests for report-audit schema | Create |
| `tests/test_synthesis_doc_wrappers.py` | Content tests for the 3 wrapper schemas + validate wiring | Create |
| `tests/test_new_agents_receipt.py` | New agents carry receipt contract + lint clean | Create |
| `tests/test_synthesizer_rewiring.py` | Synthesizer no longer triggers build-report | Create |

**Dispatched-set notes.** The three new agents (`apd-cluster-adjudicator`, `apd-report-writer`, `apd-report-auditor`) are dispatched children of the future workflow runner, so the Plan-1 lint rule (`lint_agent_file`: every agent not in `RECEIPT_EXEMPT` must contain `## Final message`) applies to them — each MUST include the `## Final message (receipt only)` section and reference `schemas/agent-receipt.schema.json`. They are NOT specialists, so they do NOT need the `## Output bounding` section (`SPECIALIST_NAMES` does not include them). `apd-synthesizer` stays in `RECEIPT_EXEMPT` (unchanged). The four new `*.schema.json` files plus five wrapper schemas (`nist-coverage-doc`, `attack-exposure-doc`, `coverage-matrix-doc`, `severity-disagreements-doc`, `contradictions-doc`) are auto-covered by `tests/test_meta_schemas.py`'s `glob("*.schema.json")` parametrization (meta-validity); this plan adds CONTENT tests for each, mirroring Plan 1's `test_agent_receipt_schema.py`.

**Resolved open questions (from the design brief), grounding the tasks below:**
- *deduped-* glob:* Confirmed via `fnmatch.fnmatch('deduped-findings.yaml','*.findings.yaml') == False` and `fnmatch.fnmatch('deduped-capabilities.yaml','*.capabilities.yaml') == False`. NEITHER deduped file is per-record validated today (the `*` does not absorb a literal `.`). Plan 2 does NOT add a deduped-* per-record path (out of scope, YAGNI); the equivalence test guards record well-formedness instead, and Plan 3 may add it. `apply-clusters` re-running `apd-gauntlet validate --tier 10-trustworthiness` etc. on the source tier files (which DO match the glob) remains the upstream gate.
- *generated_at / wrapper metadata:* `apply-clusters` emits the BARE `finding:` / `capability:` list matching the example golden (loader `_records_from_doc` reads only the `finding`/`capability` key; the stats block is recomputable by `rollup`/`summarize`). No `generated_at` is emitted so output is reproducible.
- *one cluster-candidates file:* one `cluster-candidates.yaml` with a `kind` discriminator per group (keeps the adjudicator read small).
- *chosen_severity authority:* `apply-clusters` HONORS adjudicator `chosen_severity` when present (does not recompute), else applies highest-wins. `severity-disagreements.yaml` is emitted when lens severities differ OR `chosen_severity != cluster-max`.
- *must-address NIST list:* default behavior is OMIT silent rows (the example golden emits none). `silent` rows are out of scope for Plan 2.
- *generated_by values:* `cluster-candidates` + `audit-report` use `apd-gauntlet`; `cluster-decisions` uses `apd-cluster-adjudicator`; deduped/rollup/rejected emit `generated_by: synthesizer` (or omit, for deduped bare-list) so the existing hardcoded enums on cwe/owasp/d3fend schemas hold.
- *fallback dispatch:* Plan 2 only provides typed-failure signals (`AdjudicationMissing` exception, `audit-report` exit 1). The fallback DISPATCH is Plan 3 (workflow).
- *coverage-file global wiring (post-Task-3 fix):* `nist-coverage.yaml`, `attack-exposure.yaml`, and `apd-coverage-matrix.yaml` are NOT globally wired into `SYNTHESIS_ROLLUPS` in Plan 2. The committed `runs/*/40-synthesis/` files predate the current array-shaped wrapper format (they use `coverage_by_family`/dict-keyed/`coverage` dicts) and can only be regenerated by the new `rollup` command; wiring legacy-format files against the new array schemas would break `apd-gauntlet validate` on every existing run. The three `*-doc` wrapper schemas exist and the `rollup` command validates its own fresh output against them directly (Task 6). Global run-dir wiring of these three plus regeneration of the legacy `runs/` is deferred to Plan 3 (workflow runner). `severity-disagreements.yaml` and `contradictions.yaml` ARE wired into `SYNTHESIS_ROLLUPS`; their wrapper schemas have an optional `notes` field added so that legacy runs with an empty array and a prose `notes:` block validate cleanly.

---

## Task 1: `synthesis/` package skeleton + shared corpus loader

**Files:**
- Create: `tools/apd_gauntlet/synthesis/__init__.py`
- Create: `tools/apd_gauntlet/synthesis/loader.py`
- Test: `tests/test_synthesis_loader.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_synthesis_loader.py`:

```python
"""load_corpus: shared corpus loader. Includes apath + tmeval ONLY when flagged."""
from __future__ import annotations

import pathlib

from apd_gauntlet.synthesis.loader import load_corpus

REPO = pathlib.Path(__file__).parent.parent
EXAMPLE = REPO / "examples" / "apd-20260601-claim-event-bus" / "expected"


def test_default_excludes_attack_path_findings():
    findings, caps = load_corpus(EXAMPLE)
    # apath-* live in 40-synthesis/attack-path.findings.yaml — excluded by default.
    assert not any(fid.startswith("apath-") for fid in findings)
    assert caps  # capabilities still load


def test_include_attack_path_pulls_apath_and_tmeval():
    findings, caps = load_corpus(EXAMPLE, include_attack_path=True)
    assert any(fid.startswith("apath-") for fid in findings), "apath-* must be included"
    assert any(fid.startswith("tmeval-") for fid in findings), "tmeval-* must be included"


def test_skips_deduped_outputs_so_corpus_is_specialist_records():
    # The loader reads the *source* tier files, never 40-synthesis deduped outputs
    # (whose filenames do not match the per-tier glob). No merged-* leaks in.
    findings, _caps = load_corpus(EXAMPLE, include_attack_path=True)
    assert not any(fid.startswith("merged-") for fid in findings)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_synthesis_loader.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'apd_gauntlet.synthesis'`.

- [ ] **Step 3: Create the package marker**

Create `tools/apd_gauntlet/synthesis/__init__.py`:

```python
"""Synthesis decomposition primitives — clustering candidate detection, cluster application, coverage rollups, report audit."""
```

- [ ] **Step 4: Write the loader**

Create `tools/apd_gauntlet/synthesis/loader.py`:

```python
"""Shared corpus loader for the synthesis decomposition commands.

Based on ``cli._load_records`` but adds an ``include_attack_path`` flag so
``cluster-candidates`` and ``rollup`` can pull the tier-4 corpus —
``40-synthesis/attack-path.findings.yaml`` (apath-*) and
``40-threat-model/threat-model.findings.yaml`` (tmeval-*) — which
``cli._load_records`` SKIPS to avoid re-ingestion during attack-path analysis.

Same discipline as ``cli._load_records``: singular root key ``finding`` /
``capability`` (legacy plural accepted defensively), warn-on-malformed via
``click.echo(err=True)``, skip records missing ``id``.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import click
import yaml


def _records(raw: Any) -> list[dict[str, Any]]:
    return raw if isinstance(raw, list) else ([raw] if isinstance(raw, dict) else [])


def load_corpus(
    run_dir: Path,
    *,
    include_attack_path: bool = False,
) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:
    """Index findings by ``id`` and collect capabilities across the run.

    With ``include_attack_path=False`` (default) the analyzer's own
    ``40-synthesis/attack-path.findings.yaml`` is excluded (matching
    ``cli._load_records``). With ``include_attack_path=True`` it IS included,
    along with ``40-threat-model/threat-model.findings.yaml`` — both required
    by the rollup matrix/nist steps and the clustering corpus per spec
    Steps 2/8.
    """
    findings_by_id: dict[str, dict[str, Any]] = {}
    capabilities: list[dict[str, Any]] = []
    for f in sorted(run_dir.glob("**/*.findings.yaml")):
        is_apath = "40-synthesis" in f.parts and f.name == "attack-path.findings.yaml"
        if is_apath and not include_attack_path:
            continue
        doc = yaml.safe_load(f.read_text(encoding="utf-8")) or {}
        raw = doc.get("finding")
        if raw is None:
            raw = doc.get("findings")
        for idx, rec in enumerate(_records(raw)):
            if not isinstance(rec, dict):
                click.echo(f"WARNING: {f}: finding[{idx}] is not a dict; skipping", err=True)
                continue
            if "id" not in rec:
                click.echo(f"WARNING: {f}: finding[{idx}] missing 'id'; skipping", err=True)
                continue
            findings_by_id[rec["id"]] = rec
    for f in sorted(run_dir.glob("**/*.capabilities.yaml")):
        doc = yaml.safe_load(f.read_text(encoding="utf-8")) or {}
        raw = doc.get("capability")
        if raw is None:
            raw = doc.get("capabilities")
        for idx, rec in enumerate(_records(raw)):
            if not isinstance(rec, dict):
                click.echo(f"WARNING: {f}: capability[{idx}] is not a dict; skipping", err=True)
                continue
            capabilities.append(rec)
    return findings_by_id, capabilities
```

(`40-threat-model/threat-model.findings.yaml` ends in `.findings.yaml`, so the `**/*.findings.yaml` glob already matches it — `include_attack_path` only gates the apath file, but tmeval is always present in the glob. The default `False` is the analyzer-safe path; the synthesis commands always call with `True`. The test `test_include_attack_path_pulls_apath_and_tmeval` proves both prefixes appear.)

- [ ] **Step 5: Run test to verify it passes**

Run: `python3 -m pytest tests/test_synthesis_loader.py -v`
Expected: PASS (3 passed) — the example run has `attack-path.findings.yaml` (apath-*) and `40-threat-model/threat-model.findings.yaml` (tmeval-*).

- [ ] **Step 6: Commit**

```bash
git add tools/apd_gauntlet/synthesis/__init__.py tools/apd_gauntlet/synthesis/loader.py tests/test_synthesis_loader.py
git commit -m "feat(synthesis): synthesis package + shared corpus loader (apath/tmeval inclusion)"
```

---

## Task 2: Extract shared coverage helpers into `coverage_logic.py`

Break the would-be `report → synthesis` import cycle by housing the deterministic NIST/posture helpers in `synthesis.coverage_logic`, then re-importing them in `report.transform`. The 4-shape tolerance in `transform.py` STAYS (legacy fixtures + synthesizer fallback); only the small leaf helpers move.

> **M1 — scope of "single source of truth".** ONLY the three NIST-id leaf
> helpers are re-pointed to `coverage_logic`: `_normalize_nist_id`,
> `_normalize_nist_ids`, `_nist_family_of`. `coverage_logic.extract_ids_from_mapping`
> is a DELIBERATE simpler, warnings-free SIBLING of `transform._extract_ids_from_mapping`
> — it is NOT shared/aliased: `transform._extract_ids_from_mapping` carries a
> `warnings=` aggregator kwarg AND a last-resort name-fallback (T4-C) that the
> rollup deliberately does not want, and every transform call site passes
> `warnings=`. Aliasing it to the coverage_logic version would raise `TypeError`
> on those call sites and silently drop the name-fallback. So `transform`
> KEEPS its own `_extract_ids_from_mapping` unchanged; `coverage_logic` and
> `rollup` use the clean sibling. The guard test pins (a) the 3 NIST aliases
> resolve to the coverage_logic functions, and (b) transform's
> `_extract_ids_from_mapping` still accepts `warnings=` (proving it was NOT
> replaced).

**Files:**
- Create: `tools/apd_gauntlet/synthesis/coverage_logic.py`
- Modify: `tools/apd_gauntlet/report/transform.py`
- Test: `tests/test_synthesis_coverage_logic.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_synthesis_coverage_logic.py`:

```python
"""coverage_logic: the deterministic NIST/posture helpers extracted from transform.py."""
from __future__ import annotations

from apd_gauntlet.synthesis import coverage_logic as cl


def test_normalize_nist_id_canonicalizes():
    assert cl.normalize_nist_id("ac-3") == "AC-3"
    assert cl.normalize_nist_id("SC-7(5)") == "SC-7(5)"
    assert cl.normalize_nist_id("garbage") is None
    assert cl.normalize_nist_id(None) is None


def test_normalize_nist_ids_drops_invalid_preserves_order():
    assert cl.normalize_nist_ids(["sc-13", "junk", "au-9"]) == ["SC-13", "AU-9"]


def test_family_of():
    assert cl.nist_family_of("AC-2(2)") == "AC"
    assert cl.nist_family_of("SC-8") == "SC"


def test_posture_four_states():
    assert cl.posture(has_findings=True, has_caps=True) == "gapped_and_covered"
    assert cl.posture(has_findings=True, has_caps=False) == "gapped"
    assert cl.posture(has_findings=False, has_caps=True) == "covered"
    assert cl.posture(has_findings=False, has_caps=False) == "silent"


def test_goal_short_is_canonical_nine():
    assert list(cl.GOAL_SHORT.keys()) == [
        "confidentiality", "integrity", "availability",
        "distributed", "resilient", "ephemeral",
        "authenticity", "non_repudiation", "immutability",
    ]


def test_build_cap_controls_index_normalizes():
    caps = [{"id": "c1", "control_mappings": {"nist_800_53r5": ["ac-3", "sc-13"]}}]
    idx = cl.build_cap_controls_index(caps)
    assert idx == {"AC-3": {"c1"}, "SC-13": {"c1"}}


def test_transform_reimports_nist_leaf_helpers_from_coverage_logic():
    # transform.py must delegate the 3 NIST leaf helpers to coverage_logic.
    from apd_gauntlet.report import transform as t
    assert t._normalize_nist_id is cl.normalize_nist_id
    assert t._normalize_nist_ids is cl.normalize_nist_ids
    assert t._nist_family_of is cl.nist_family_of


def test_transform_keeps_its_warnings_aware_extract_sibling():
    # M1: transform._extract_ids_from_mapping is NOT aliased to the coverage_logic
    # sibling (it keeps the warnings= kwarg + name-fallback). Prove it is distinct.
    from apd_gauntlet.report import transform as t
    assert t._extract_ids_from_mapping is not cl.extract_ids_from_mapping
    warns: list[dict] = []
    out = t._extract_ids_from_mapping([{"name": "Some Control"}], warnings=warns)
    assert out == ["Some Control"]
    assert warns and warns[0]["issue"] == "mapping_id_missing_using_name"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_synthesis_coverage_logic.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'apd_gauntlet.synthesis.coverage_logic'`.

- [ ] **Step 3: Create `coverage_logic.py`**

Create `tools/apd_gauntlet/synthesis/coverage_logic.py` (note: `posture` differs from the legacy `transform._posture` only in returning the canonical YAML enum `gapped_and_covered` rather than the data.js short `both` — the rollup needs the YAML enum, and `transform._posture` callers want `both`, so `transform.py` keeps its own `both`-returning private wrapper while sharing the leaf helpers):

```python
"""Deterministic coverage helpers shared by report.transform and synthesis.rollup.

Extracted from report/transform.py so both modules import one source of truth
without a report→synthesis import cycle (this module imports nothing from
report). The 4-shape tolerance in transform.py is unaffected — only these leaf
helpers were factored out.
"""
from __future__ import annotations

import re
from typing import Any

# Canonical APD goal order (used by the 9xN matrix and goal iteration).
GOAL_SHORT: dict[str, str] = {
    "confidentiality": "conf",
    "integrity":       "intg",
    "availability":    "avail",
    "distributed":     "dist",
    "resilient":       "resil",
    "ephemeral":       "ephem",
    "authenticity":    "auth",
    "non_repudiation": "nonrep",
    "immutability":    "immut",
}

_NIST_ID_CANONICAL = re.compile(r"[A-Z]{2,3}-\d+(\([\dA-Z]+\))?")


def normalize_nist_id(raw: str | None) -> str | None:
    """Normalise a NIST 800-53r5 control id to canonical form (e.g. 'ac-3' -> 'AC-3').

    Returns None for input that cannot be normalised so callers drop the entry.
    """
    if not isinstance(raw, str):
        return None
    norm = raw.strip().upper()
    if not norm:
        return None
    if not _NIST_ID_CANONICAL.fullmatch(norm):
        return None
    return norm


def normalize_nist_ids(ids: list[str]) -> list[str]:
    """Apply normalize_nist_id over a list, dropping invalid entries; preserve order."""
    return [n for n in (normalize_nist_id(x) for x in ids) if n]


def nist_family_of(control_id: str) -> str:
    """Return the NIST family prefix of a control id (e.g. 'AC-2(2)' -> 'AC')."""
    return control_id.split("-", 1)[0] if "-" in control_id else control_id


def posture(*, has_findings: bool, has_caps: bool) -> str:
    """Return the canonical coverage posture enum used in the rollup YAMLs."""
    if has_findings and has_caps:
        return "gapped_and_covered"
    if has_findings:
        return "gapped"
    if has_caps:
        return "covered"
    return "silent"


def extract_ids_from_mapping(raw: Any, *fallback_keys: str) -> list[str]:
    """Extract string IDs from a control-mapping field (list of str or list of dicts).

    Tries 'id' then each fallback key. Items with no usable id are skipped.
    Deliberately the silent variant (no warnings aggregator) — rollup wants
    only the clean ids; the report keeps the warnings-aware copy in transform.py.
    """
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
        if isinstance(found, str) and found:
            ids.append(found)
    return ids


def build_cap_controls_index(capabilities: list[dict[str, Any]]) -> dict[str, set[str]]:
    """Return {control_id: {cap_id, ...}} for capabilities with NIST mappings (normalised)."""
    index: dict[str, set[str]] = {}
    for cap in capabilities:
        cap_id = cap.get("id", "")
        cm = cap.get("control_mappings") or {}
        for ctrl in normalize_nist_ids(extract_ids_from_mapping(cm.get("nist_800_53r5"))):
            index.setdefault(ctrl, set()).add(cap_id)
    return index


def build_cap_attack_index(capabilities: list[dict[str, Any]]) -> dict[str, set[str]]:
    """Return {attack_id: {cap_id, ...}} for capabilities with MITRE ATT&CK mappings."""
    index: dict[str, set[str]] = {}
    for cap in capabilities:
        cap_id = cap.get("id", "")
        cm = cap.get("control_mappings") or {}
        for tech in extract_ids_from_mapping(cm.get("mitre_attack"), "technique"):
            index.setdefault(tech, set()).add(cap_id)
    return index
```

- [ ] **Step 4: Re-point `report/transform.py` at the shared helpers**

In `tools/apd_gauntlet/report/transform.py`, just below the existing import block (`from .loader import RunArtifacts`), add:

```python
from ..synthesis import coverage_logic as _cl
```

Then DELETE the bodies of the now-duplicated leaf helpers and replace them with thin delegations. Replace the existing `_normalize_nist_id` definition (the `def _normalize_nist_id(raw: str | None) -> str | None:` block) with:

```python
_normalize_nist_id = _cl.normalize_nist_id
_normalize_nist_ids = _cl.normalize_nist_ids
_nist_family_of = _cl.nist_family_of
```

Delete the now-superseded standalone `def _normalize_nist_ids(...)` and `def _nist_family_of(...)` definitions (their logic lives in `coverage_logic`). DELETE the module-level `_NIST_ID_CANONICAL` regex too — after removing `_normalize_nist_id` nothing else in `transform.py` references it (verified: its only uses are the regex def at `transform.py:521` and `_normalize_nist_id` at `:540`), and the identical canonical regex now lives in `coverage_logic`, so behavior is preserved. The alias assignments above go at MODULE TOP LEVEL right after `from ..synthesis import coverage_logic as _cl`, and the three original `def`s are removed in the SAME edit (so there is no shadowing — the alias is the only binding).

Do NOT touch the following — they are deliberately distinct and STAY in `transform.py` unchanged:

- `_posture` keeps returning the data.js short label `"both"`; `coverage_logic.posture` returns the YAML enum `"gapped_and_covered"` (the rollup's contract). They are intentional siblings — the identity test pins ONLY the 3 NIST-leaf helpers, never `_posture`.
- `_extract_ids_from_mapping` keeps its `warnings=` aggregator kwarg + last-resort name-fallback (T4-C). Every transform call site passes `warnings=`, so aliasing it to `coverage_logic.extract_ids_from_mapping` (which has neither) would raise `TypeError` and silently drop the name-fallback. `transform` keeps its own; `coverage_logic`/`rollup` use the clean sibling. NO `_extract_ids_from_mapping` alias is added.
- `_build_cap_controls_index` / `_build_cap_attack_index` stay as-is (they call transform's `_extract_ids_from_mapping`).

The guard tests (`test_transform_reimports_nist_leaf_helpers_from_coverage_logic` + `test_transform_keeps_its_warnings_aware_extract_sibling`) were written correctly in Step 1, so no test edit is needed here — Step 5 just runs them green.

- [ ] **Step 5: Run test to verify it passes + no transform regression**

Run: `python3 -m pytest tests/test_synthesis_coverage_logic.py tests/unit/report/test_transform_nist_rollup.py tests/unit/report/test_transform_summary.py -v`
Expected: PASS (all) — `transform.py` still produces identical rollup rows because the extracted helpers are byte-identical in behavior.

- [ ] **Step 6: Commit**

```bash
git add tools/apd_gauntlet/synthesis/coverage_logic.py tools/apd_gauntlet/report/transform.py tests/test_synthesis_coverage_logic.py
git commit -m "refactor(synthesis): extract coverage_logic leaf helpers; transform.py delegates"
```

---

## Task 3: New whole-document + wrapper schemas (+ validate wiring)

Author the four new-artifact schemas and the five thin `$ref` wrappers, and wire all nine filenames into `validate.SYNTHESIS_ROLLUPS` so the workflow `phaseDone` guard (`validate --schema-only --errors-only`) catches malformed rollup/cluster output. The `$id` convention is `https://github.com/illusconsulting/apd-gauntlet/schemas/<name>.schema.json` (matches every existing schema). The wrappers `$ref` the EXISTING per-row schemas (recon option b — minimal new logic; the `build_registry()` registry resolves cross-schema `$ref` by `$id`). The two NEW annex wrappers (`severity-disagreements-doc`, `contradictions-doc`) close the I5 gap: `apply-clusters` emits `severity-disagreements.yaml` (`{severity_disagreements: [...]}`) and `contradictions.yaml` (`{contradictions: [...]}`), but neither filename was schema-wired — so a malformed annex slipped past `validate --schema-only`. They `$ref` the EXISTING `severity-disagreement.schema.json` / `contradiction.schema.json` per-row schemas.

**Files:**
- Create: `schemas/cluster-candidates.schema.json`, `schemas/cluster-decisions.schema.json`, `schemas/rejected-records.schema.json`, `schemas/report-audit.schema.json`, `schemas/nist-coverage-doc.schema.json`, `schemas/attack-exposure-doc.schema.json`, `schemas/coverage-matrix-doc.schema.json`, `schemas/severity-disagreements-doc.schema.json`, `schemas/contradictions-doc.schema.json`
- Modify: `tools/apd_gauntlet/validate.py`
- Test: `tests/test_cluster_candidates_schema.py`, `tests/test_cluster_decisions_schema.py`, `tests/test_rejected_records_schema.py`, `tests/test_report_audit_schema.py`, `tests/test_synthesis_doc_wrappers.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_cluster_candidates_schema.py`:

```python
"""cluster-candidates schema: accepts a minimal valid candidate doc, rejects bad signals."""
from __future__ import annotations

import json
import pathlib

from jsonschema import Draft202012Validator

REPO = pathlib.Path(__file__).parent.parent
SCHEMA = REPO / "schemas" / "cluster-candidates.schema.json"


def _validator():
    return Draft202012Validator(json.loads(SCHEMA.read_text()))


def _group(**over):
    base = {
        "group_id": "cluster-cand-0001",
        "kind": "finding",
        "signals": ["evidence_locator_overlap"],
        "members": [
            {"id": "conf-7aa376c5", "agent": "confidentiality", "apd_goal": "confidentiality",
             "severity": "high", "title": "x" * 12, "summary": "y" * 12,
             "first_evidence": {"artifact": "a.md", "locator": "L", "excerpt": "e"},
             "related_concerns": ["integrity"],
             "mapping_ids": {"nist": ["SC-8(1)"], "attack": ["T1530"]}},
            {"id": "intg-42a3ebbd", "agent": "integrity", "apd_goal": "integrity",
             "severity": "high", "title": "x" * 12, "summary": "y" * 12,
             "first_evidence": {"artifact": "a.md", "locator": "L", "excerpt": "e"},
             "related_concerns": ["confidentiality"],
             "mapping_ids": {"nist": [], "attack": []}},
        ],
    }
    base.update(over)
    return base


def test_minimal_valid_doc():
    doc = {"schema_version": 1, "generated_by": "apd-gauntlet", "groups": [_group()]}
    assert list(_validator().iter_errors(doc)) == []


def test_rejects_bad_generated_by():
    doc = {"schema_version": 1, "generated_by": "synthesizer", "groups": [_group()]}
    assert list(_validator().iter_errors(doc))


def test_rejects_single_member_group():
    doc = {"schema_version": 1, "generated_by": "apd-gauntlet",
           "groups": [_group(members=[_group()["members"][0]])]}
    assert list(_validator().iter_errors(doc))  # minItems: 2


def test_rejects_unknown_signal():
    doc = {"schema_version": 1, "generated_by": "apd-gauntlet",
           "groups": [_group(signals=["nist_overlap"])]}
    assert list(_validator().iter_errors(doc))  # control overlap is NOT a signal
```

Create `tests/test_cluster_decisions_schema.py`:

```python
"""cluster-decisions schema: merge/link/separate dispositions + contradictions."""
from __future__ import annotations

import json
import pathlib

from jsonschema import Draft202012Validator

REPO = pathlib.Path(__file__).parent.parent
SCHEMA = REPO / "schemas" / "cluster-decisions.schema.json"


def _validator():
    return Draft202012Validator(json.loads(SCHEMA.read_text()))


def test_minimal_merge_decision():
    doc = {
        "schema_version": 1,
        "generated_by": "apd-cluster-adjudicator",
        "decisions": [{
            "group_id": "cluster-cand-0001",
            "disposition": "merge",
            "merged_title": "x" * 12,
            "merged_summary": "y" * 12,
            "merged_detail": "z" * 21,
            "merged_recommendation": {"posture": "required", "summary": "s" * 12, "detail": "d" * 21},
            "lens_perspectives": {
                "non_repudiation": {"summary": "a" * 5, "detail": "b" * 5},
                "immutability": {"summary": "a" * 5, "detail": "b" * 5},
            },
            "chosen_severity": "critical",
            "severity_rationale": "elevated " * 5,
        }],
    }
    assert list(_validator().iter_errors(doc)) == []


def test_separate_decision_is_minimal():
    doc = {"schema_version": 1, "generated_by": "apd-cluster-adjudicator",
           "decisions": [{"group_id": "cluster-cand-0002", "disposition": "separate"}]}
    assert list(_validator().iter_errors(doc)) == []


def test_rejects_bad_disposition():
    doc = {"schema_version": 1, "generated_by": "apd-cluster-adjudicator",
           "decisions": [{"group_id": "g", "disposition": "combine"}]}
    assert list(_validator().iter_errors(doc))


def test_contradiction_classification_enum():
    doc = {"schema_version": 1, "generated_by": "apd-cluster-adjudicator", "decisions": [],
           "contradictions": [{"finding_id": "conf-7aa376c5", "capability_id": "conf-cap-89e19793",
                               "classification": "stale", "finding_assertion": "a",
                               "capability_assertion": "b", "evidence_comparison": "c",
                               "recommended_resolution": "d"}]}
    assert list(_validator().iter_errors(doc)) == []


def test_top_level_members_map_validates_clean():
    # C3/C6: apply.py + the adjudicator agent + both fixtures carry a top-level
    # _members map keyed by group_id. The root is additionalProperties:false, so
    # the schema MUST declare _members or every real decisions doc fails
    # validate --schema-only (the workflow phaseDone guard).
    doc = {
        "schema_version": 1,
        "generated_by": "apd-cluster-adjudicator",
        "decisions": [{"group_id": "cluster-cand-0001", "disposition": "merge",
                       "merged_title": "x" * 12, "merged_summary": "y" * 12,
                       "merged_detail": "z" * 21}],
        "_members": {"cluster-cand-0001": ["nonrep-62124087", "immut-e09e4945"]},
    }
    assert list(_validator().iter_errors(doc)) == []


def test_members_values_must_be_string_arrays():
    doc = {"schema_version": 1, "generated_by": "apd-cluster-adjudicator", "decisions": [],
           "_members": {"cluster-cand-0001": "not-a-list"}}
    assert list(_validator().iter_errors(doc))  # values must be arrays of strings
```

Create `tests/test_rejected_records_schema.py`:

```python
"""rejected-records schema: failed-validation + stale-downgrade categories."""
from __future__ import annotations

import json
import pathlib

from jsonschema import Draft202012Validator

REPO = pathlib.Path(__file__).parent.parent
SCHEMA = REPO / "schemas" / "rejected-records.schema.json"


def _validator():
    return Draft202012Validator(json.loads(SCHEMA.read_text()))


def test_minimal_rejected_doc():
    doc = {"schema_version": 1, "generated_by": "synthesizer",
           "rejected": [{"id": "conf-7aa376c5", "reason": "failed schema validation",
                         "category": "failed_validation"}]}
    assert list(_validator().iter_errors(doc)) == []


def test_stale_downgrade_record():
    doc = {"schema_version": 1, "generated_by": "synthesizer",
           "rejected": [{"id": "conf-cap-89e19793", "reason": "evidence supports designed only",
                         "category": "stale_capability_downgrade",
                         "from_maturity": "tested", "to_maturity": "designed"}]}
    assert list(_validator().iter_errors(doc)) == []


def test_rejects_short_reason():
    doc = {"schema_version": 1, "generated_by": "synthesizer",
           "rejected": [{"id": "x", "reason": "no", "category": "failed_validation"}]}
    assert list(_validator().iter_errors(doc))  # reason minLength 10
```

Create `tests/test_report_audit_schema.py`:

```python
"""report-audit schema: compact structural audit output."""
from __future__ import annotations

import json
import pathlib

from jsonschema import Draft202012Validator

REPO = pathlib.Path(__file__).parent.parent
SCHEMA = REPO / "schemas" / "report-audit.schema.json"


def _validator():
    return Draft202012Validator(json.loads(SCHEMA.read_text()))


def test_minimal_pass_audit():
    doc = {
        "schema_version": 1,
        "generated_by": "apd-gauntlet",
        "status": "pass",
        "checks": [{"name": "id_coverage_findings", "status": "pass", "detail": "90/90"}],
        "counts": {
            "findings_yaml": 15, "findings_data_js": 90,
            "capabilities_yaml": 10, "capabilities_data_js": 10,
            "nist_controls_yaml": 10, "nist_ids_in_taxonomy": 10,
            "attack_techniques_yaml": 4, "attack_techniques_data_js": 4,
        },
        "drift": [],
    }
    assert list(_validator().iter_errors(doc)) == []


def test_rejects_bad_status():
    doc = {"schema_version": 1, "generated_by": "apd-gauntlet", "status": "warn",
           "checks": [], "counts": {}, "drift": []}
    assert list(_validator().iter_errors(doc))
```

Create `tests/test_synthesis_doc_wrappers.py`:

```python
"""The three doc-wrapper schemas validate the example golden rollups, and are wired in."""
from __future__ import annotations

import json
import pathlib

import yaml
from apd_gauntlet.validate import SYNTHESIS_ROLLUPS, build_registry
from jsonschema import Draft202012Validator

REPO = pathlib.Path(__file__).parent.parent
SCHEMA_DIR = REPO / "schemas"
EXAMPLE_SYNTH = REPO / "examples" / "apd-20260601-claim-event-bus" / "expected" / "40-synthesis"

WRAPPERS = {
    "nist-coverage.yaml": "nist-coverage-doc.schema.json",
    "attack-exposure.yaml": "attack-exposure-doc.schema.json",
    "apd-coverage-matrix.yaml": "coverage-matrix-doc.schema.json",
    # I5 — the apply-clusters annex outputs (both present in the example golden).
    "severity-disagreements.yaml": "severity-disagreements-doc.schema.json",
    "contradictions.yaml": "contradictions-doc.schema.json",
}


def _validator(schema_name):
    schema = json.loads((SCHEMA_DIR / schema_name).read_text())
    return Draft202012Validator(schema, registry=build_registry())


def test_wrappers_validate_example_rollups():
    for filename, schema_name in WRAPPERS.items():
        doc = yaml.safe_load((EXAMPLE_SYNTH / filename).read_text())
        errors = list(_validator(schema_name).iter_errors(doc))
        assert errors == [], f"{filename}: {[e.message for e in errors]}"


def test_wrappers_and_new_artifacts_wired_into_synthesis_rollups():
    for filename, schema_name in WRAPPERS.items():
        assert SYNTHESIS_ROLLUPS.get(filename) == schema_name
    assert SYNTHESIS_ROLLUPS["cluster-candidates.yaml"] == "cluster-candidates.schema.json"
    assert SYNTHESIS_ROLLUPS["cluster-decisions.yaml"] == "cluster-decisions.schema.json"
    assert SYNTHESIS_ROLLUPS["rejected-records.yaml"] == "rejected-records.schema.json"
    assert SYNTHESIS_ROLLUPS["report-audit.yaml"] == "report-audit.schema.json"
```

(The example golden's `severity-disagreements.yaml` is a single merged-record disagreement and its `contradictions.yaml` is a single `contra-*` row — both already conform to the per-row schemas the wrappers `$ref`, so this test proves the canonical golden validates against the annex wrappers we just authored.)

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_cluster_candidates_schema.py tests/test_cluster_decisions_schema.py tests/test_rejected_records_schema.py tests/test_report_audit_schema.py tests/test_synthesis_doc_wrappers.py -v`
Expected: FAIL — all schema files are absent (`FileNotFoundError`), and `SYNTHESIS_ROLLUPS` lacks the new keys.

- [ ] **Step 3: Create the four new-artifact schemas**

Create `schemas/cluster-candidates.schema.json`:

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://github.com/illusconsulting/apd-gauntlet/schemas/cluster-candidates.schema.json",
  "title": "APD Gauntlet Cluster Candidates",
  "description": "Mechanical candidate groups emitted by the cluster-candidates command (5a). Read by the apd-cluster-adjudicator.",
  "type": "object",
  "additionalProperties": false,
  "required": ["schema_version", "generated_by", "groups"],
  "properties": {
    "schema_version": { "type": "integer", "const": 1 },
    "generated_by": { "type": "string", "enum": ["apd-gauntlet"] },
    "groups": {
      "type": "array",
      "items": {
        "type": "object",
        "additionalProperties": false,
        "required": ["group_id", "kind", "signals", "members"],
        "properties": {
          "group_id": { "type": "string", "pattern": "^cluster-cand-[0-9a-f]{4,8}$" },
          "kind": { "type": "string", "enum": ["finding", "capability"] },
          "signals": {
            "type": "array",
            "minItems": 1,
            "items": { "type": "string", "enum": ["evidence_locator_overlap", "title_similarity", "related_concerns"] }
          },
          "members": {
            "type": "array",
            "minItems": 2,
            "items": {
              "type": "object",
              "additionalProperties": false,
              "required": ["id", "agent", "apd_goal", "severity", "title", "summary", "first_evidence", "related_concerns", "mapping_ids"],
              "properties": {
                "id": { "type": "string", "minLength": 1 },
                "agent": { "type": "string", "minLength": 1 },
                "apd_goal": { "type": "string", "minLength": 1 },
                "severity": { "type": "string", "enum": ["critical", "high", "medium", "low", "informational"] },
                "title": { "type": "string", "minLength": 10 },
                "summary": { "type": "string", "minLength": 10 },
                "first_evidence": {
                  "type": "object",
                  "additionalProperties": false,
                  "required": ["artifact", "locator", "excerpt"],
                  "properties": {
                    "artifact": { "type": "string" },
                    "locator": { "type": "string" },
                    "excerpt": { "type": "string" }
                  }
                },
                "related_concerns": { "type": "array", "items": { "type": "string" } },
                "mapping_ids": {
                  "type": "object",
                  "additionalProperties": false,
                  "required": ["nist", "attack"],
                  "properties": {
                    "nist": { "type": "array", "items": { "type": "string" } },
                    "attack": { "type": "array", "items": { "type": "string" } }
                  }
                }
              }
            }
          }
        }
      }
    }
  }
}
```

Create `schemas/cluster-decisions.schema.json`:

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://github.com/illusconsulting/apd-gauntlet/schemas/cluster-decisions.schema.json",
  "title": "APD Gauntlet Cluster Decisions",
  "description": "Disposition + merged prose emitted by the apd-cluster-adjudicator (5b). Consumed by apply-clusters.",
  "type": "object",
  "additionalProperties": false,
  "required": ["schema_version", "generated_by", "decisions"],
  "properties": {
    "schema_version": { "type": "integer", "const": 1 },
    "generated_by": { "type": "string", "enum": ["apd-cluster-adjudicator"] },
    "decisions": {
      "type": "array",
      "items": {
        "type": "object",
        "additionalProperties": false,
        "required": ["group_id", "disposition"],
        "properties": {
          "group_id": { "type": "string", "minLength": 1 },
          "disposition": { "type": "string", "enum": ["merge", "link", "separate"] },
          "merged_title": { "type": "string", "minLength": 10 },
          "merged_summary": { "type": "string", "minLength": 10 },
          "merged_detail": { "type": "string", "minLength": 20 },
          "merged_recommendation": {
            "type": "object",
            "additionalProperties": false,
            "required": ["posture", "summary"],
            "properties": {
              "posture": { "type": "string", "enum": ["required", "recommended", "consider"] },
              "summary": { "type": "string", "minLength": 10 },
              "detail": { "type": "string", "minLength": 20 }
            }
          },
          "lens_perspectives": {
            "type": "object",
            "additionalProperties": {
              "type": "object",
              "additionalProperties": false,
              "required": ["summary", "detail"],
              "properties": {
                "summary": { "type": "string" },
                "detail": { "type": "string" }
              }
            }
          },
          "chosen_severity": { "type": "string", "enum": ["critical", "high", "medium", "low", "informational"] },
          "severity_rationale": { "type": "string", "minLength": 10 },
          "links": {
            "type": "array",
            "items": {
              "type": "object",
              "additionalProperties": false,
              "required": ["from", "to"],
              "properties": { "from": { "type": "string" }, "to": { "type": "string" } }
            }
          }
        }
      }
    },
    "contradictions": {
      "type": "array",
      "items": {
        "type": "object",
        "additionalProperties": false,
        "required": ["finding_id", "capability_id", "classification", "finding_assertion", "capability_assertion", "evidence_comparison", "recommended_resolution"],
        "properties": {
          "finding_id": { "type": "string" },
          "capability_id": { "type": "string" },
          "classification": { "type": "string", "enum": ["compatible", "contradicted", "stale"] },
          "finding_assertion": { "type": "string" },
          "capability_assertion": { "type": "string" },
          "evidence_comparison": { "type": "string" },
          "recommended_resolution": { "type": "string" }
        }
      }
    },
    "_members": {
      "type": "object",
      "additionalProperties": { "type": "array", "items": { "type": "string" } }
    }
  }
}
```

> **C3/C6 — `_members` is a first-class property.** The root object is
> `additionalProperties: false`, and `apply.py`, the `apd-cluster-adjudicator`
> agent, and BOTH fixtures (`tests/test_cli_apply_clusters.py`'s inline
> scaffold + `tests/fixtures/cluster_decisions/example-cluster-decisions.yaml`)
> all carry a top-level `_members` map keyed by `group_id`. Without the
> `_members` property above, every real `cluster-decisions.yaml` would FAIL
> `validate --schema-only` (the workflow `phaseDone` guard) and would falsely
> make the adjudicator's `schema_valid: true` receipt claim a lie. The
> `_members` map's values are arrays of member record ids
> (e.g. `{"cluster-cand-0001": ["nonrep-62124087", "immut-e09e4945"]}`).

Create `schemas/rejected-records.schema.json`:

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://github.com/illusconsulting/apd-gauntlet/schemas/rejected-records.schema.json",
  "title": "APD Gauntlet Rejected Records",
  "description": "Records excluded from clustering (validation failures) and stale-capability maturity downgrades, with a reason per record.",
  "type": "object",
  "additionalProperties": false,
  "required": ["schema_version", "generated_by", "rejected"],
  "properties": {
    "schema_version": { "type": "integer", "const": 1 },
    "generated_by": { "type": "string", "enum": ["synthesizer"] },
    "rejected": {
      "type": "array",
      "items": {
        "type": "object",
        "additionalProperties": false,
        "required": ["id", "reason", "category"],
        "properties": {
          "id": { "type": "string", "minLength": 1 },
          "reason": { "type": "string", "minLength": 10 },
          "category": { "type": "string", "enum": ["failed_validation", "stale_capability_downgrade"] },
          "from_maturity": { "type": "string", "enum": ["designed", "implemented", "tested", "operationalized"] },
          "to_maturity": { "type": "string", "enum": ["designed", "implemented", "tested", "operationalized"] }
        }
      }
    }
  }
}
```

Create `schemas/report-audit.schema.json`:

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://github.com/illusconsulting/apd-gauntlet/schemas/report-audit.schema.json",
  "title": "APD Gauntlet Report Audit",
  "description": "Compact structural audit emitted by the audit-report command (5g). Read by the apd-report-auditor (never data.js itself).",
  "type": "object",
  "additionalProperties": false,
  "required": ["schema_version", "generated_by", "status", "checks", "counts", "drift"],
  "properties": {
    "schema_version": { "type": "integer", "const": 1 },
    "generated_by": { "type": "string", "enum": ["apd-gauntlet"] },
    "status": { "type": "string", "enum": ["pass", "fail"] },
    "checks": {
      "type": "array",
      "items": {
        "type": "object",
        "additionalProperties": false,
        "required": ["name", "status", "detail"],
        "properties": {
          "name": { "type": "string" },
          "status": { "type": "string", "enum": ["pass", "fail"] },
          "detail": { "type": "string" }
        }
      }
    },
    "counts": {
      "type": "object",
      "additionalProperties": false,
      "properties": {
        "findings_yaml": { "type": "integer" },
        "findings_data_js": { "type": "integer" },
        "capabilities_yaml": { "type": "integer" },
        "capabilities_data_js": { "type": "integer" },
        "nist_controls_yaml": { "type": "integer" },
        "nist_ids_in_taxonomy": { "type": "integer" },
        "attack_techniques_yaml": { "type": "integer" },
        "attack_techniques_data_js": { "type": "integer" }
      }
    },
    "drift": {
      "type": "array",
      "items": {
        "type": "object",
        "additionalProperties": false,
        "required": ["file", "manifest_hash", "current_hash"],
        "properties": {
          "file": { "type": "string" },
          "manifest_hash": { "type": "string" },
          "current_hash": { "type": "string" }
        }
      }
    }
  }
}
```

- [ ] **Step 4: Create the five thin wrapper schemas**

Create `schemas/nist-coverage-doc.schema.json`:

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://github.com/illusconsulting/apd-gauntlet/schemas/nist-coverage-doc.schema.json",
  "title": "APD Gauntlet NIST Coverage Document",
  "type": "object",
  "required": ["controls"],
  "additionalProperties": false,
  "properties": {
    "controls": {
      "type": "array",
      "items": { "$ref": "https://github.com/illusconsulting/apd-gauntlet/schemas/nist-coverage.schema.json" }
    }
  }
}
```

Create `schemas/attack-exposure-doc.schema.json`:

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://github.com/illusconsulting/apd-gauntlet/schemas/attack-exposure-doc.schema.json",
  "title": "APD Gauntlet ATT&CK Exposure Document",
  "type": "object",
  "required": ["techniques"],
  "additionalProperties": false,
  "properties": {
    "techniques": {
      "type": "array",
      "items": { "$ref": "https://github.com/illusconsulting/apd-gauntlet/schemas/attack-exposure.schema.json" }
    }
  }
}
```

Create `schemas/coverage-matrix-doc.schema.json`:

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://github.com/illusconsulting/apd-gauntlet/schemas/coverage-matrix-doc.schema.json",
  "title": "APD Gauntlet Coverage Matrix Document",
  "type": "object",
  "required": ["components"],
  "additionalProperties": false,
  "properties": {
    "components": {
      "type": "array",
      "items": { "$ref": "https://github.com/illusconsulting/apd-gauntlet/schemas/coverage-matrix.schema.json" }
    }
  }
}
```

Create `schemas/severity-disagreements-doc.schema.json` (I5 — wraps the EXISTING per-row `severity-disagreement.schema.json`; `apply-clusters` emits `{severity_disagreements: [...]}`):

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://github.com/illusconsulting/apd-gauntlet/schemas/severity-disagreements-doc.schema.json",
  "title": "APD Gauntlet Severity Disagreements Document",
  "type": "object",
  "required": ["severity_disagreements"],
  "additionalProperties": false,
  "properties": {
    "severity_disagreements": {
      "type": "array",
      "items": { "$ref": "https://github.com/illusconsulting/apd-gauntlet/schemas/severity-disagreement.schema.json" }
    }
  }
}
```

Create `schemas/contradictions-doc.schema.json` (I5/C5 — wraps the EXISTING per-row `contradiction.schema.json`; `apply-clusters` emits `{contradictions: [...]}`):

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://github.com/illusconsulting/apd-gauntlet/schemas/contradictions-doc.schema.json",
  "title": "APD Gauntlet Contradictions Document",
  "type": "object",
  "required": ["contradictions"],
  "additionalProperties": false,
  "properties": {
    "contradictions": {
      "type": "array",
      "items": { "$ref": "https://github.com/illusconsulting/apd-gauntlet/schemas/contradiction.schema.json" }
    }
  }
}
```

- [ ] **Step 5: Wire the nine filenames into `SYNTHESIS_ROLLUPS`**

In `tools/apd_gauntlet/validate.py`, extend the `SYNTHESIS_ROLLUPS` dict. Replace the closing `}` of the existing dict (after the `"report-data.yaml": "report-data.schema.json",` line) so the dict now also contains:

```python
    # Plan 2 — synthesis decomposition artifacts.
    "cluster-candidates.yaml":     "cluster-candidates.schema.json",
    "cluster-decisions.yaml":      "cluster-decisions.schema.json",
    "rejected-records.yaml":       "rejected-records.schema.json",
    "report-audit.yaml":           "report-audit.schema.json",
    # Plan 2 — thin whole-doc wrappers around the existing per-row schemas so
    # the rollup outputs are schema-validated end-to-end (closes the validator
    # wiring gap for nist-coverage / attack-exposure / apd-coverage-matrix).
    "nist-coverage.yaml":          "nist-coverage-doc.schema.json",
    "attack-exposure.yaml":        "attack-exposure-doc.schema.json",
    "apd-coverage-matrix.yaml":    "coverage-matrix-doc.schema.json",
    # Plan 2 (I5) — apply-clusters annex outputs, previously unwired so a
    # malformed annex slipped past validate --schema-only. Wrap the existing
    # per-row severity-disagreement / contradiction schemas.
    "severity-disagreements.yaml": "severity-disagreements-doc.schema.json",
    "contradictions.yaml":         "contradictions-doc.schema.json",
}
```

(`_validate_synthesis_rollups` already loads each schema through `build_registry()`, so the `$ref` to the per-row schemas resolves. Missing files stay silent — these are optional until emitted.)

- [ ] **Step 6: Run tests + meta-schema + example regression to verify they pass**

Run: `python3 -m pytest tests/test_cluster_candidates_schema.py tests/test_cluster_decisions_schema.py tests/test_rejected_records_schema.py tests/test_report_audit_schema.py tests/test_synthesis_doc_wrappers.py tests/test_meta_schemas.py -v`
Expected: PASS (all) — including the 9 new `test_schema_is_valid_meta[...]` cases auto-discovered by the glob (4 new-artifact + 5 wrapper schemas).

Run: `apd-gauntlet validate examples/apd-20260601-claim-event-bus/expected --errors-only`
Expected: exit 0, NO output. The example's `nist-coverage.yaml` / `attack-exposure.yaml` / `apd-coverage-matrix.yaml` now schema-validate via the new wrappers and remain clean (proving the canonical golden conforms to the wrappers we just authored).

- [ ] **Step 7: Commit**

```bash
git add schemas/cluster-candidates.schema.json schemas/cluster-decisions.schema.json schemas/rejected-records.schema.json schemas/report-audit.schema.json schemas/nist-coverage-doc.schema.json schemas/attack-exposure-doc.schema.json schemas/coverage-matrix-doc.schema.json schemas/severity-disagreements-doc.schema.json schemas/contradictions-doc.schema.json tools/apd_gauntlet/validate.py tests/test_cluster_candidates_schema.py tests/test_cluster_decisions_schema.py tests/test_rejected_records_schema.py tests/test_report_audit_schema.py tests/test_synthesis_doc_wrappers.py
git commit -m "feat(schema): cluster/rejected/report-audit schemas + rollup + annex doc-wrappers wired into validate"
```

---

## Task 4: `cluster-candidates` command (5a)

Mechanical signal detection + union-find grouping + group-size bounding. NEVER use shared NIST/ATT&CK mapping as a signal (the spec lists only the 3 below; control overlap over-groups). Findings and capabilities cluster separately. Deterministic ordering: `group_id` sequential, members sorted by `id`.

**Files:**
- Create: `tools/apd_gauntlet/synthesis/cluster.py`
- Modify: `tools/apd_gauntlet/cli.py`
- Test: `tests/test_cli_cluster_candidates.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_cli_cluster_candidates.py`:

```python
"""cluster-candidates: emits a schema-valid cluster-candidates.yaml; signals are the 3 mechanical ones."""
from __future__ import annotations

import json
import pathlib
import shutil

import yaml
from apd_gauntlet.cli import main
from click.testing import CliRunner
from jsonschema import Draft202012Validator
from referencing import Registry, Resource

REPO = pathlib.Path(__file__).parent.parent
SCHEMA_DIR = REPO / "schemas"
EXAMPLE = REPO / "examples" / "apd-20260601-claim-event-bus" / "expected"


def _build_registry() -> Registry:
    resources = []
    for schema_path in sorted(SCHEMA_DIR.glob("*.schema.json")):
        schema = json.loads(schema_path.read_text())
        sid = schema.get("$id")
        if sid:
            resources.append((sid, Resource.from_contents(schema)))
    return Registry().with_resources(resources)


def _copy_example(tmp_path):
    dst = tmp_path / "run"
    shutil.copytree(EXAMPLE, dst)
    return dst


def test_cluster_candidates_emits_schema_valid_doc(tmp_path):
    dst = _copy_example(tmp_path)
    result = CliRunner().invoke(main, ["cluster-candidates", str(dst)])
    assert result.exit_code == 0, result.output
    out = dst / "40-synthesis" / "cluster-candidates.yaml"
    assert out.exists()
    doc = yaml.safe_load(out.read_text())
    schema = json.loads((SCHEMA_DIR / "cluster-candidates.schema.json").read_text())
    validator = Draft202012Validator(schema, registry=_build_registry())
    assert list(validator.iter_errors(doc)) == [], result.output


def test_groups_are_deterministically_ordered_and_signals_valid(tmp_path):
    dst = _copy_example(tmp_path)
    CliRunner().invoke(main, ["cluster-candidates", str(dst)])
    doc = yaml.safe_load((dst / "40-synthesis" / "cluster-candidates.yaml").read_text())
    valid_signals = {"evidence_locator_overlap", "title_similarity", "related_concerns"}
    for g in doc["groups"]:
        # members sorted by id
        ids = [m["id"] for m in g["members"]]
        assert ids == sorted(ids)
        # only the 3 mechanical signals (control overlap must NEVER appear)
        assert set(g["signals"]) <= valid_signals
    # group_ids are sorted
    gids = [g["group_id"] for g in doc["groups"]]
    assert gids == sorted(gids)


def test_findings_and_capabilities_cluster_separately(tmp_path):
    dst = _copy_example(tmp_path)
    CliRunner().invoke(main, ["cluster-candidates", str(dst)])
    doc = yaml.safe_load((dst / "40-synthesis" / "cluster-candidates.yaml").read_text())
    for g in doc["groups"]:
        kinds = {m["id"].count("-cap-") for m in g["members"]}
        # a group is either all-finding (0 '-cap-') or all-capability (1 '-cap-')
        assert len(kinds) == 1
        assert (g["kind"] == "capability") == (kinds == {1})


def test_no_group_exceeds_cap(tmp_path):
    dst = _copy_example(tmp_path)
    CliRunner().invoke(main, ["cluster-candidates", str(dst), "--max-group-size", "8"])
    doc = yaml.safe_load((dst / "40-synthesis" / "cluster-candidates.yaml").read_text())
    for g in doc["groups"]:
        assert 2 <= len(g["members"]) <= 8
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_cli_cluster_candidates.py -v`
Expected: FAIL — `Error: No such command 'cluster-candidates'.` (exit 2).

- [ ] **Step 3: Write `cluster.py`**

Create `tools/apd_gauntlet/synthesis/cluster.py`:

```python
"""5a cluster-candidates — mechanical signal detection + union-find grouping.

Detects three signals (NEVER shared control mappings — that over-groups):
  1. evidence_locator_overlap — two records cite the same (artifact, locator).
  2. title_similarity — token Jaccard >= 0.5 over normalised titles.
  3. related_concerns — reciprocal cross-goal related_concerns (A in lens X cites
     Y, B in lens Y cites X) AND a shared evidence artifact.

Groups via union-find over the signal graph, then bounds group size so the
adjudicator's context stays small. Findings and capabilities cluster separately.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .coverage_logic import extract_ids_from_mapping, normalize_nist_ids
from .loader import load_corpus

_TOKEN_STOP = {"the", "a", "an", "of", "in", "on", "for", "and", "or", "to", "is", "no", "not", "with"}
_TOKEN_RE = re.compile(r"[a-z0-9]+")


@dataclass
class CandidateResult:
    groups: list[dict[str, Any]] = field(default_factory=list)


def _title_tokens(title: str) -> set[str]:
    return {t for t in _TOKEN_RE.findall(title.lower()) if t not in _TOKEN_STOP and len(t) > 2}


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def _first_evidence(rec: dict[str, Any]) -> dict[str, str]:
    ev = rec.get("evidence") or []
    if ev and isinstance(ev[0], dict):
        return {
            "artifact": str(ev[0].get("artifact", "")),
            "locator": str(ev[0].get("locator", "")),
            "excerpt": str(ev[0].get("excerpt", "")),
        }
    return {"artifact": "", "locator": "", "excerpt": ""}


class _UnionFind:
    def __init__(self, items: list[str]) -> None:
        self.parent = {i: i for i in items}

    def find(self, x: str) -> str:
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def union(self, a: str, b: str) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.parent[max(ra, rb)] = min(ra, rb)


def _signals_between(r1: dict[str, Any], r2: dict[str, Any]) -> set[str]:
    sigs: set[str] = set()
    e1, e2 = _first_evidence(r1), _first_evidence(r2)
    shared_artifact = bool(e1["artifact"]) and e1["artifact"] == e2["artifact"]
    if shared_artifact and e1["locator"] and e1["locator"] == e2["locator"]:
        sigs.add("evidence_locator_overlap")
    if _jaccard(_title_tokens(r1.get("title", "")), _title_tokens(r2.get("title", ""))) >= 0.5:
        sigs.add("title_similarity")
    g1, g2 = r1.get("apd_goal"), r2.get("apd_goal")
    rc1 = set(r1.get("related_concerns") or [])
    rc2 = set(r2.get("related_concerns") or [])
    if g1 and g2 and g2 in rc1 and g1 in rc2 and shared_artifact:
        sigs.add("related_concerns")
    return sigs


def _member_view(rec: dict[str, Any]) -> dict[str, Any]:
    cm = rec.get("control_mappings") or {}
    return {
        "id": rec["id"],
        "agent": rec.get("agent", ""),
        "apd_goal": rec.get("apd_goal", ""),
        "severity": rec.get("severity", "informational"),
        "title": rec.get("title", ""),
        "summary": rec.get("summary", "") or rec.get("description", ""),
        "first_evidence": _first_evidence(rec),
        "related_concerns": list(rec.get("related_concerns") or []),
        "mapping_ids": {
            "nist": normalize_nist_ids(extract_ids_from_mapping(cm.get("nist_800_53r5"))),
            "attack": extract_ids_from_mapping(cm.get("mitre_attack"), "technique"),
        },
    }


def _group_records(records: list[dict[str, Any]], kind: str, max_group_size: int) -> list[dict[str, Any]]:
    ids = [r["id"] for r in records]
    by_id = {r["id"]: r for r in records}
    uf = _UnionFind(ids)
    edge_signals: dict[tuple[str, str], set[str]] = {}
    for i in range(len(ids)):
        for j in range(i + 1, len(ids)):
            sigs = _signals_between(by_id[ids[i]], by_id[ids[j]])
            if sigs:
                uf.union(ids[i], ids[j])
                edge_signals[(ids[i], ids[j])] = sigs
    clusters: dict[str, list[str]] = {}
    for rid in ids:
        clusters.setdefault(uf.find(rid), []).append(rid)
    groups: list[dict[str, Any]] = []
    for root in sorted(clusters):
        members = sorted(clusters[root])
        if len(members) < 2:
            continue
        # Bound group size: split into deterministic chunks of <= max_group_size.
        for chunk_start in range(0, len(members), max_group_size):
            chunk = members[chunk_start:chunk_start + max_group_size]
            if len(chunk) < 2:
                # A trailing single is folded back into the previous chunk so no
                # sub-group is a singleton (which the adjudicator cannot act on).
                if groups and groups[-1]["kind"] == kind:
                    groups[-1]["members"].append(_member_view(by_id[chunk[0]]))
                    groups[-1]["members"].sort(key=lambda m: m["id"])
                continue
            chunk_set = set(chunk)
            sigs: set[str] = set()
            for (a, b), s in edge_signals.items():
                if a in chunk_set and b in chunk_set:
                    sigs |= s
            groups.append({
                "kind": kind,
                "signals": sorted(sigs) or ["title_similarity"],
                "members": [_member_view(by_id[m]) for m in chunk],
            })
    return groups


def build_candidates(run_dir: Path, *, max_group_size: int = 8) -> CandidateResult:
    """Detect candidate clusters across findings and (separately) capabilities."""
    findings_by_id, capabilities = load_corpus(run_dir, include_attack_path=True)
    finding_groups = _group_records(list(findings_by_id.values()), "finding", max_group_size)
    cap_groups = _group_records(capabilities, "capability", max_group_size)
    all_groups = finding_groups + cap_groups
    # Assign deterministic sequential group_ids after the records are ordered.
    for idx, g in enumerate(all_groups, start=1):
        g["group_id"] = f"cluster-cand-{idx:04x}"
    # Reorder keys: group_id first, then kind/signals/members.
    ordered = [
        {"group_id": g["group_id"], "kind": g["kind"], "signals": g["signals"], "members": g["members"]}
        for g in sorted(all_groups, key=lambda g: g["group_id"])
    ]
    return CandidateResult(groups=ordered)
```

- [ ] **Step 4: Register the CLI command**

In `tools/apd_gauntlet/cli.py`, add the command after the `build_report_cmd` definition (before `if __name__ == "__main__":`):

```python
@main.command("cluster-candidates")
@click.argument("run_dir", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option(
    "--max-group-size",
    default=8,
    show_default=True,
    help="Maximum members per candidate group; larger clusters are split.",
)
def cluster_candidates_cmd(run_dir: Path, max_group_size: int) -> None:
    """5a: mechanically detect cluster candidates; emit cluster-candidates.yaml."""
    from .synthesis.cluster import build_candidates

    synth = run_dir / "40-synthesis"
    synth.mkdir(parents=True, exist_ok=True)
    run_cfg_path = run_dir / ".apd-run.yaml"
    try:
        run_cfg: dict[str, Any] = (
            yaml.safe_load(run_cfg_path.read_text(encoding="utf-8"))
            if run_cfg_path.exists()
            else {}
        ) or {}
    except yaml.YAMLError as exc:
        raise click.UsageError(f".apd-run.yaml is not valid YAML: {exc}") from exc
    cap = int(run_cfg.get("max_candidate_group_size", max_group_size))
    result = build_candidates(run_dir, max_group_size=cap)
    doc = {"schema_version": 1, "generated_by": "apd-gauntlet", "groups": result.groups}
    (synth / "cluster-candidates.yaml").write_text(
        yaml.safe_dump(doc, sort_keys=False), encoding="utf-8"
    )
    click.echo(f"cluster-candidates: wrote {len(result.groups)} candidate groups")
```

- [ ] **Step 5: Run test to verify it passes**

Run: `python3 -m pytest tests/test_cli_cluster_candidates.py -v`
Expected: PASS (4 passed). The example `expected/` tree IS a complete run — it contains all nine tier `*.findings.yaml` / `*.capabilities.yaml` files under `10-trustworthiness/`, `20-scalability/`, `30-auditability/`, PLUS `40-synthesis/attack-path.findings.yaml` (apath-*) and `40-threat-model/threat-model.findings.yaml` (tmeval-*). So `load_corpus(run_dir, include_attack_path=True)` loads the FULL specialist corpus (the 16 tier findings (15 survive into deduped after the one merge) + 75 apath + 3 tmeval findings + 10 tier capabilities), NOT an empty set. `cluster-candidates` therefore yields REAL candidate groups — including the reciprocal `nonrep-62124087` / `immut-e09e4945` pair (each cites `related_concerns: [immutability]` / `[non_repudiation]` and a shared `tech_plan.md` evidence artifact) plus any title/locator-similar pairs. The four tests are written to be TOLERANT of the exact group count: they assert ordering (`group_id` + members sorted), the cap (2..8 members), signal validity (only the 3 mechanical signals, never control overlap), and finding/capability separation — never a specific number of groups. (The MERGE itself is exercised by `apply-clusters` over a `cluster-decisions.yaml` fixture in Tasks 5/8; `cluster-candidates` only proposes groups.)

- [ ] **Step 6: Commit**

```bash
git add tools/apd_gauntlet/synthesis/cluster.py tools/apd_gauntlet/cli.py tests/test_cli_cluster_candidates.py
git commit -m "feat(synthesis): cluster-candidates command (3 mechanical signals + bounded union-find)"
```

---

## Task 5: `apply-clusters` command (5c)

(Design step 5b is the `apd-cluster-adjudicator` LLM agent, authored in Task 9 — the 5a→5c command jump here is intentional; the adjudicator produces the `cluster-decisions.yaml` this command consumes.)

Mechanical application of `cluster-decisions.yaml`. `separate` → copy unchanged; `link` → copy both + reciprocal `cross_references`; `merge` → build merged record (`agent='synthesizer'`, `id='merged-'+sha8(title+'|'+first_locator)`, severity = adjudicator `chosen_severity` if present else max-of-cluster, sorted-union NIST/ATT&CK, sorted `merged_from`, adjudicator `lens_perspectives` + prose). Also the MECHANICAL PRODUCER of `contradictions.yaml` (C5/I3 — strips the adjudicator's `classification`, emits `contra-<sha8>` rows matching the existing `contradiction.schema.json` + cross-ref) and applies the stale-capability maturity downgrade (I4 — design §7.1-5c). Emits bare `finding:` / `capability:` lists (no `generated_at`), `severity-disagreements.yaml`, `contradictions.yaml`, `rejected-records.yaml`. Defines `AdjudicationMissing` (mirrors `attack_path.BuilderBlocked`) for the workflow fallback.

**Files:**
- Create: `tools/apd_gauntlet/synthesis/apply.py`
- Modify: `tools/apd_gauntlet/cli.py`
- Test: `tests/test_cli_apply_clusters.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_cli_apply_clusters.py`:

```python
"""apply-clusters: merge/link/separate application + merged-id rule + reproducibility."""
from __future__ import annotations

import hashlib
import json
import pathlib
import shutil

import yaml
from apd_gauntlet.cli import main
from apd_gauntlet.synthesis.apply import AdjudicationMissing, apply_clusters
from apd_gauntlet.validate import run_cross_file_pass
from click.testing import CliRunner
from jsonschema import Draft202012Validator

REPO = pathlib.Path(__file__).parent.parent
SCHEMA_DIR = REPO / "schemas"
FIXTURES = REPO / "tests" / "fixtures"


def _scaffold_two_finding_run(tmp_path):
    """A minimal run: two reciprocal findings + a hand-built merge decision."""
    run = tmp_path / "run"
    (run / "10-trustworthiness").mkdir(parents=True)
    (run / "30-auditability").mkdir(parents=True)
    (run / "40-synthesis").mkdir()
    (run / ".apd-run.yaml").write_text("run_id: t\ndomain: pbm\n")
    nonrep = {
        "schema_version": 1, "id": "nonrep-62124087", "agent": "non_repudiation",
        "apd_tier": "auditability", "apd_goal": "non_repudiation", "disposition": "gap",
        "severity": "high", "confidence": "high",
        "title": "Audit log unsigned no HMAC protection present",
        "summary": "Unsigned audit entries cannot prove non-tampering of records.",
        "detail": "Without HMAC there is no cryptographic proof entries are unmodified.",
        "evidence": [{"artifact": "tech_plan.md", "locator": "§5.2", "excerpt": "no WORM enforcement"}],
        "control_mappings": {"nist_800_53r5": ["AU-9", "AU-10"]},
        "recommendation": {"posture": "required", "summary": "Sign every audit entry with HMAC.",
                           "detail": "Sign each audit entry with a KMS-derived HMAC at write time."},
        "related_concerns": ["immutability"],
    }
    immut = {
        "schema_version": 1, "id": "immut-e09e4945", "agent": "immutability",
        "apd_tier": "auditability", "apd_goal": "immutability", "disposition": "gap",
        "severity": "high", "confidence": "high",
        "title": "Audit log mutable table no WORM enforcement present",
        "summary": "No storage-layer write-once protection prevents record deletion.",
        "detail": "Application-level append-only discipline can be bypassed by any DBA.",
        "evidence": [{"artifact": "tech_plan.md", "locator": "§5.2", "excerpt": "no WORM enforcement"}],
        "control_mappings": {"nist_800_53r5": ["AU-9(2)", "AU-9(3)"]},
        "recommendation": {"posture": "required", "summary": "Migrate to WORM-protected storage.",
                           "detail": "Migrate audit log storage to S3 with Object Lock in Compliance mode."},
        "related_concerns": ["non_repudiation"],
    }
    # A real capability + finding the contradiction (C5) + stale downgrade (I4)
    # reference; both ids must resolve in validate.run_cross_file_pass.
    conf_cap = {
        "schema_version": 1, "id": "conf-cap-89e19793", "agent": "confidentiality",
        "apd_tier": "trustworthiness", "apd_goal": "confidentiality",
        "maturity": "tested", "confidence": "high",
        "title": "Field-level envelope encryption on PHI columns",
        "description": "Envelope encryption is applied to PHI columns in the RDS tables at rest.",
        "scope": "member_demographics and claims tables at rest",
        "evidence": [{"artifact": "tech_plan.md", "locator": "§5.1", "excerpt": "field-level encryption"}],
        "control_mappings": {"nist_800_53r5": ["SC-28"]},
    }
    conf_finding = {
        "schema_version": 1, "id": "conf-7aa376c5", "agent": "confidentiality",
        "apd_tier": "trustworthiness", "apd_goal": "confidentiality", "disposition": "gap",
        "severity": "high", "confidence": "high",
        "title": "Kafka claim-events topic carries plaintext PHI payloads",
        "summary": "PHI fields in the Kafka topic are protected only at the broker level.",
        "detail": "Payload-level PHI is plaintext; only broker-level encryption applies today.",
        "evidence": [{"artifact": "tech_plan.md", "locator": "§4.2", "excerpt": "broker encryption only"}],
        "control_mappings": {"nist_800_53r5": ["SC-8"]},
        "recommendation": {"posture": "required", "summary": "Encrypt PHI payloads field-level.",
                           "detail": "Apply envelope encryption to PHI fields before publishing to Kafka."},
    }
    (run / "30-auditability" / "non_repudiation.findings.yaml").write_text(
        yaml.safe_dump({"schema_version": 1, "finding": [nonrep]}, sort_keys=False))
    (run / "30-auditability" / "immutability.findings.yaml").write_text(
        yaml.safe_dump({"schema_version": 1, "finding": [immut]}, sort_keys=False))
    (run / "10-trustworthiness" / "confidentiality.findings.yaml").write_text(
        yaml.safe_dump({"schema_version": 1, "finding": [conf_finding]}, sort_keys=False))
    (run / "10-trustworthiness" / "confidentiality.capabilities.yaml").write_text(
        yaml.safe_dump({"schema_version": 1, "capability": [conf_cap]}, sort_keys=False))
    decisions = {
        "schema_version": 1, "generated_by": "apd-cluster-adjudicator",
        "decisions": [{
            "group_id": "cluster-cand-0001", "disposition": "merge",
            "merged_title": "Audit log is unsigned and stored in a mutable table",
            "merged_summary": "The audit_log lacks both signing and storage-layer immutability.",
            "merged_detail": "Both lenses identified this risk from complementary angles together.",
            "merged_recommendation": {"posture": "required",
                                      "summary": "Implement HMAC signing and migrate to WORM storage.",
                                      "detail": "Sign entries and migrate to S3 Object Lock compliance mode."},
            "lens_perspectives": {
                "non_repudiation": {"summary": "Unsigned entries cannot prove non-tampering.",
                                    "detail": "No cryptographic proof a record was not modified."},
                "immutability": {"summary": "No write-once protection prevents deletion.",
                                 "detail": "Append-only discipline can be bypassed by a DBA."},
            },
            "chosen_severity": "critical",
            "severity_rationale": "Combination triggers HIPAA breach-notification exposure beyond either lens.",
        }],
        "contradictions": [{
            "finding_id": "conf-7aa376c5", "capability_id": "conf-cap-89e19793",
            "classification": "stale",
            "finding_assertion": "PHI payloads in the Kafka topic are plaintext at the payload level.",
            "capability_assertion": "Field-level envelope encryption is applied to PHI columns at rest.",
            "evidence_comparison": "The capability covers RDS storage; the finding covers Kafka topics — different storage layers, different postures.",
            "recommended_resolution": "Confirm the encryption capability scope explicitly excludes Kafka payloads and update its scope statement.",
        }],
        "_members": {"cluster-cand-0001": ["nonrep-62124087", "immut-e09e4945"]},
    }
    (run / "40-synthesis" / "cluster-decisions.yaml").write_text(
        yaml.safe_dump(decisions, sort_keys=False))
    return run


def test_merge_builds_merged_record_with_sha8_id(tmp_path):
    run = _scaffold_two_finding_run(tmp_path)
    result = apply_clusters(run)
    merged = [f for f in result.findings if f["agent"] == "synthesizer"]
    assert len(merged) == 1
    m = merged[0]
    title = "Audit log is unsigned and stored in a mutable table"
    first_locator = "§5.2"
    expect = "merged-" + hashlib.sha256(f"{title}|{first_locator}".encode()).hexdigest()[:8]
    assert m["id"] == expect
    assert m["merged_from"] == ["immut-e09e4945", "nonrep-62124087"]  # sorted
    assert m["severity"] == "critical"  # honors adjudicator chosen_severity
    assert m["control_mappings"]["nist_800_53r5"] == ["AU-10", "AU-9", "AU-9(2)", "AU-9(3)"]  # sorted union
    assert set(m["lens_perspectives"].keys()) == {"non_repudiation", "immutability"}
    # source records no longer appear as top-level findings
    assert not any(f["id"] in ("nonrep-62124087", "immut-e09e4945") for f in result.findings)


def test_merge_emits_severity_disagreement(tmp_path):
    run = _scaffold_two_finding_run(tmp_path)
    apply_clusters(run)
    sevdis = yaml.safe_load((run / "40-synthesis" / "severity-disagreements.yaml").read_text())
    rows = sevdis["severity_disagreements"]
    assert len(rows) == 1
    assert rows[0]["chosen_severity"] == "critical"
    assert rows[0]["agent_severities"] == {"non_repudiation": "high", "immutability": "high"}


def test_outputs_are_schema_valid_and_reproducible(tmp_path):
    run = _scaffold_two_finding_run(tmp_path)
    result1 = apply_clusters(run)
    deduped1 = (run / "40-synthesis" / "deduped-findings.yaml").read_text()
    result2 = apply_clusters(run)  # idempotent / reproducible
    deduped2 = (run / "40-synthesis" / "deduped-findings.yaml").read_text()
    assert deduped1 == deduped2, "apply-clusters output must be reproducible (no generated_at)"
    assert "generated_at" not in deduped1
    finding_schema = json.loads((SCHEMA_DIR / "finding.schema.json").read_text())
    from referencing import Registry, Resource
    resources = []
    for p in sorted(SCHEMA_DIR.glob("*.schema.json")):
        s = json.loads(p.read_text())
        if s.get("$id"):
            resources.append((s["$id"], Resource.from_contents(s)))
    registry = Registry().with_resources(resources)
    v = Draft202012Validator(finding_schema, registry=registry)
    for f in result1.findings:
        assert list(v.iter_errors(f)) == [], f.get("id")


def test_contradictions_written_and_pass_cross_ref_validation(tmp_path):
    # C5/I3: apply-clusters is the producer of contradictions.yaml. The emitted
    # file must (a) have the per-row shape (id contra-<sha8> + the 6 prose
    # fields, NO classification), (b) reference real ids so the EXISTING
    # validate.run_cross_file_pass contradiction cross-ref passes.
    run = _scaffold_two_finding_run(tmp_path)
    result = apply_clusters(run)
    assert len(result.contradictions) == 1
    row = result.contradictions[0]
    assert row["id"].startswith("contra-") and len(row["id"]) == len("contra-") + 8
    assert "classification" not in row  # adjudicator-only; stripped on disk
    contra = yaml.safe_load((run / "40-synthesis" / "contradictions.yaml").read_text())
    # Validate per-row against the EXISTING contradiction schema.
    from referencing import Registry, Resource
    resources = []
    for p in sorted(SCHEMA_DIR.glob("*.schema.json")):
        s = json.loads(p.read_text())
        if s.get("$id"):
            resources.append((s["$id"], Resource.from_contents(s)))
    registry = Registry().with_resources(resources)
    cschema = json.loads((SCHEMA_DIR / "contradiction.schema.json").read_text())
    v = Draft202012Validator(cschema, registry=registry)
    for r in contra["contradictions"]:
        assert list(v.iter_errors(r)) == [], r
    # Cross-file pass: contradictions.yaml references must resolve to real
    # finding/capability ids written into the run.
    report = run_cross_file_pass(run)
    dangling = [e for e in report.errors if "contradictions.yaml" in str(e.file)]
    assert dangling == [], [e.render() for e in dangling]


def test_stale_contradiction_downgrades_capability_and_logs_rejected(tmp_path):
    # I4: a 'stale' contradiction downgrades the named capability one maturity
    # notch (tested -> implemented) and logs a stale_capability_downgrade row.
    run = _scaffold_two_finding_run(tmp_path)
    result = apply_clusters(run)
    cap = next(c for c in result.capabilities if c["id"] == "conf-cap-89e19793")
    assert cap["maturity"] == "implemented"  # was "tested", down one notch
    downgrades = [r for r in result.rejected if r["category"] == "stale_capability_downgrade"]
    assert len(downgrades) == 1
    assert downgrades[0]["from_maturity"] == "tested"
    assert downgrades[0]["to_maturity"] == "implemented"
    # rejected-records.yaml validates against its schema (category + maturities).
    rej = yaml.safe_load((run / "40-synthesis" / "rejected-records.yaml").read_text())
    schema = json.loads((SCHEMA_DIR / "rejected-records.schema.json").read_text())
    assert list(Draft202012Validator(schema).iter_errors(rej)) == []


def test_missing_decisions_raises_adjudication_missing(tmp_path):
    run = tmp_path / "run"
    (run / "40-synthesis").mkdir(parents=True)
    (run / ".apd-run.yaml").write_text("run_id: t\n")
    try:
        apply_clusters(run)
        raise AssertionError("expected AdjudicationMissing")
    except AdjudicationMissing:
        pass


def test_cli_apply_clusters_smoke(tmp_path):
    run = _scaffold_two_finding_run(tmp_path)
    result = CliRunner().invoke(main, ["apply-clusters", str(run)])
    assert result.exit_code == 0, result.output
    assert (run / "40-synthesis" / "deduped-findings.yaml").exists()
    assert (run / "40-synthesis" / "deduped-capabilities.yaml").exists()
    assert (run / "40-synthesis" / "rejected-records.yaml").exists()
    assert (run / "40-synthesis" / "contradictions.yaml").exists()
    assert (run / "40-synthesis" / "severity-disagreements.yaml").exists()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_cli_apply_clusters.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'apd_gauntlet.synthesis.apply'`.

- [ ] **Step 3: Write `apply.py`**

Create `tools/apd_gauntlet/synthesis/apply.py`:

```python
"""5c apply-clusters — mechanically apply cluster-decisions.yaml.

Builds the authoritative deduped-findings.yaml / deduped-capabilities.yaml
(bare singular-root-key lists; no generated_at so output is reproducible),
plus severity-disagreements.yaml, contradictions.yaml, and
rejected-records.yaml. Raises AdjudicationMissing (mirrors
attack_path.BuilderBlocked) when the decisions file is absent or malformed so
the workflow can fall back to the synthesizer.

Contradictions (C5/I3): the adjudicator JUDGES finding-vs-capability conflicts
in cluster-decisions.yaml's ``contradictions`` block (with a ``classification``:
compatible|contradicted|stale). apply-clusters is the MECHANICAL PRODUCER of
40-synthesis/contradictions.yaml — it strips the adjudicator's ``classification``
(an adjudicator-only field, NOT part of the on-disk contradiction.schema.json
row) and emits a ``contra-<sha8>`` id + the per-row shape that the existing
schemas/contradiction.schema.json and validate.run_cross_file_pass enforce.

Stale-capability downgrade (I4): for each adjudicator contradiction classified
``stale``, the named capability's maturity is downgraded ONE notch via
_MATURITY_RANK and a ``stale_capability_downgrade`` record is logged to
rejected-records.yaml — implementing design §7.1-5c's "downgrades stale
capabilities".
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from .loader import load_corpus

_SEV_RANK = {"critical": 0, "high": 1, "medium": 2, "low": 3, "informational": 4}
_MATURITY_RANK = {"designed": 0, "implemented": 1, "tested": 2, "operationalized": 3}
_MATURITY_BY_RANK = {v: k for k, v in _MATURITY_RANK.items()}


class AdjudicationMissing(Exception):
    """Raised when cluster-decisions.yaml is absent or malformed."""


@dataclass
class ApplyResult:
    findings: list[dict[str, Any]] = field(default_factory=list)
    capabilities: list[dict[str, Any]] = field(default_factory=list)
    severity_disagreements: list[dict[str, Any]] = field(default_factory=list)
    contradictions: list[dict[str, Any]] = field(default_factory=list)
    rejected: list[dict[str, Any]] = field(default_factory=list)


def _sha8(title: str, first_locator: str) -> str:
    return hashlib.sha256(f"{title}|{first_locator}".encode()).hexdigest()[:8]


def _downgrade_maturity(current: str) -> str | None:
    """Return the maturity one notch below ``current`` (None if already lowest)."""
    rank = _MATURITY_RANK.get(current)
    if rank is None or rank == 0:
        return None
    return _MATURITY_BY_RANK[rank - 1]


def _first_locator(rec: dict[str, Any]) -> str:
    ev = rec.get("evidence") or []
    if ev and isinstance(ev[0], dict):
        return str(ev[0].get("locator", ""))
    return ""


def _max_severity(records: list[dict[str, Any]]) -> str:
    return min((r.get("severity", "informational") for r in records), key=lambda s: _SEV_RANK.get(s, 9))


def _sorted_union(records: list[dict[str, Any]], path: tuple[str, ...]) -> list[str]:
    out: set[str] = set()
    for r in records:
        node: Any = r
        for key in path:
            node = (node or {}).get(key) if isinstance(node, dict) else None
        for item in node or []:
            if isinstance(item, str):
                out.add(item)
    return sorted(out)


def _union_attack(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: dict[str, dict[str, Any]] = {}
    for r in records:
        for m in (r.get("control_mappings") or {}).get("mitre_attack") or []:
            if isinstance(m, dict) and m.get("technique"):
                seen.setdefault(m["technique"], m)
    return [seen[k] for k in sorted(seen)]


def _load_decisions(run_dir: Path) -> dict[str, Any]:
    path = run_dir / "40-synthesis" / "cluster-decisions.yaml"
    if not path.is_file():
        raise AdjudicationMissing(f"cluster-decisions.yaml absent at {path}")
    try:
        doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise AdjudicationMissing(f"cluster-decisions.yaml malformed: {exc}") from exc
    if not isinstance(doc, dict) or "decisions" not in doc:
        raise AdjudicationMissing("cluster-decisions.yaml missing 'decisions'")
    return doc


def _members_for(doc: dict[str, Any], decision: dict[str, Any]) -> list[str]:
    """Resolve the member ids for a decision.

    The adjudicator carries member ids in the optional ``_members`` map keyed by
    group_id (mirrors cluster-candidates.yaml group membership). Tests and the
    workflow supply it; if absent for a merge, the decision is treated as a
    rejected record rather than silently dropped.
    """
    return list((doc.get("_members") or {}).get(decision.get("group_id"), []))


def apply_clusters(run_dir: Path) -> ApplyResult:
    doc = _load_decisions(run_dir)
    findings_by_id, capabilities = load_corpus(run_dir, include_attack_path=True)
    caps_by_id = {c["id"]: c for c in capabilities if "id" in c}

    result = ApplyResult()
    consumed: set[str] = set()
    cross_refs: dict[str, list[str]] = {}

    for decision in doc.get("decisions") or []:
        disp = decision.get("disposition")
        members = _members_for(doc, decision)
        if disp == "merge":
            sources = [findings_by_id[m] for m in members if m in findings_by_id]
            if len(sources) < 2:
                for m in members:
                    result.rejected.append({
                        "id": m, "category": "failed_validation",
                        "reason": "merge member not found in corpus during apply-clusters",
                    })
                continue
            consumed.update(members)
            title = decision.get("merged_title", "")
            first_locator = _first_locator(sorted(sources, key=lambda r: r["id"])[0])
            cluster_max = _max_severity(sources)
            chosen = decision.get("chosen_severity")
            severity = chosen or cluster_max
            evidence: list[dict[str, Any]] = []
            for s in sorted(sources, key=lambda r: r["id"]):
                for ev in s.get("evidence") or []:
                    if ev not in evidence:
                        evidence.append(ev)
            merged = {
                "schema_version": 1,
                "id": "merged-" + _sha8(title, first_locator),
                "agent": "synthesizer",
                "apd_tier": sources[0].get("apd_tier"),
                "apd_goal": sources[0].get("apd_goal"),
                "disposition": "gap",
                "severity": severity,
                "confidence": min(
                    (s.get("confidence", "low") for s in sources),
                    key=lambda c: {"high": 0, "medium": 1, "low": 2}.get(c, 9),
                ),
                "title": title,
                "summary": decision.get("merged_summary", ""),
                "detail": decision.get("merged_detail", ""),
                "evidence": evidence,
                "merged_from": sorted(members),
                "lens_perspectives": decision.get("lens_perspectives", {}),
                "control_mappings": {"nist_800_53r5": _sorted_union(sources, ("control_mappings", "nist_800_53r5"))},
                "recommendation": decision.get("merged_recommendation", {}),
            }
            attack = _union_attack(sources)
            if attack:
                merged["control_mappings"]["mitre_attack"] = attack
            related = sorted({c for s in sources for c in (s.get("related_concerns") or [])})
            if related:
                merged["related_concerns"] = related
            result.findings.append(merged)
            # Emit a severity-disagreement when lens severities differ OR the
            # adjudicator elevated above the cluster max.
            lens_sevs = {s.get("apd_goal"): s.get("severity") for s in sources}
            if len(set(lens_sevs.values())) > 1 or (chosen and chosen != cluster_max):
                # severity-disagreement.schema.json requires rationale minLength
                # 30; the >=30-char default fires only when the adjudicator
                # omitted a rationale (rare — it supplies one on any elevation).
                result.severity_disagreements.append({
                    "finding_id": merged["id"],
                    "agent_severities": lens_sevs,
                    "chosen_severity": severity,
                    "rationale": decision.get("severity_rationale")
                    or "Highest-severity-wins across the merged lens severities; "
                       "no adjudicator rationale was supplied for this cluster.",
                })
        elif disp == "link":
            for link in decision.get("links") or []:
                a, b = link.get("from"), link.get("to")
                if a and b:
                    cross_refs.setdefault(a, []).append(b)
                    cross_refs.setdefault(b, []).append(a)
        # separate: no-op; both records flow through unchanged below.

    # Emit all non-consumed findings unchanged (tier order then id within tier),
    # attaching reciprocal cross_references for linked records.
    for rec in _ordered_records(findings_by_id):
        if rec["id"] in consumed:
            continue
        out = dict(rec)
        refs = sorted(set(cross_refs.get(rec["id"], [])))
        if refs:
            out["cross_references"] = sorted(set(out.get("cross_references", [])) | set(refs))
        result.findings.append(out)

    # Contradictions (C5/I3) + stale-capability downgrade (I4).
    # The adjudicator's contradiction rows carry a ``classification`` that is an
    # adjudicator-only field; the on-disk contradiction.schema.json row does NOT
    # include it, so it is stripped here. The id is a deterministic
    # ``contra-<sha8(finding_id|capability_id)>`` so output is reproducible.
    caps_by_id = {c["id"]: dict(c) for c in caps_by_id.values()}  # mutable copies
    for raw in doc.get("contradictions") or []:
        fid = raw.get("finding_id")
        cid = raw.get("capability_id")
        if not fid or not cid:
            continue
        contra_id = "contra-" + hashlib.sha256(f"{fid}|{cid}".encode()).hexdigest()[:8]
        result.contradictions.append({
            "id": contra_id,
            "finding_id": fid,
            "capability_id": cid,
            "finding_assertion": raw.get("finding_assertion", ""),
            "capability_assertion": raw.get("capability_assertion", ""),
            "evidence_comparison": raw.get("evidence_comparison", ""),
            "recommended_resolution": raw.get("recommended_resolution", ""),
        })
        # I4: stale → downgrade the named capability one maturity notch.
        if raw.get("classification") == "stale" and cid in caps_by_id:
            cap = caps_by_id[cid]
            current = cap.get("maturity", "implemented")
            new_maturity = _downgrade_maturity(current)
            if new_maturity is not None:
                cap["maturity"] = new_maturity
                result.rejected.append({
                    "id": cid,
                    "category": "stale_capability_downgrade",
                    "reason": (raw.get("recommended_resolution")
                               or "Adjudicator classified the capability as stale "
                                  "relative to the finding evidence."),
                    "from_maturity": current,
                    "to_maturity": new_maturity,
                })

    result.capabilities = list(caps_by_id.values())

    _write_outputs(run_dir, result)
    return result


_TIER_ORDER = {"trustworthiness": 0, "scalability": 1, "auditability": 2}


def _ordered_records(by_id: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        by_id.values(),
        key=lambda r: (_TIER_ORDER.get(r.get("apd_tier", ""), 9), r["id"]),
    )


def _write_outputs(run_dir: Path, result: ApplyResult) -> None:
    synth = run_dir / "40-synthesis"
    synth.mkdir(parents=True, exist_ok=True)
    # Merged records sort last (id starts 'merged-'); keep tier order for the rest.
    findings_sorted = sorted(
        result.findings,
        key=lambda r: (
            0 if r["id"].startswith("merged-") else -1,
            _TIER_ORDER.get(r.get("apd_tier", ""), 9),
            r["id"],
        ),
    )
    (synth / "deduped-findings.yaml").write_text(
        yaml.safe_dump({"finding": findings_sorted}, sort_keys=False), encoding="utf-8")
    (synth / "deduped-capabilities.yaml").write_text(
        yaml.safe_dump({"capability": sorted(result.capabilities, key=lambda c: c.get("id", ""))},
                       sort_keys=False), encoding="utf-8")
    (synth / "severity-disagreements.yaml").write_text(
        yaml.safe_dump({"severity_disagreements": sorted(
            result.severity_disagreements, key=lambda r: r["finding_id"])}, sort_keys=False),
        encoding="utf-8")
    # C5/I3: apply-clusters is the producer of contradictions.yaml. Bare
    # {contradictions: [...]} per-row shape, matching the EXISTING
    # contradiction.schema.json + validate.run_cross_file_pass cross-ref.
    (synth / "contradictions.yaml").write_text(
        yaml.safe_dump({"contradictions": sorted(
            result.contradictions, key=lambda r: r["id"])}, sort_keys=False),
        encoding="utf-8")
    (synth / "rejected-records.yaml").write_text(
        yaml.safe_dump({"schema_version": 1, "generated_by": "synthesizer",
                        "rejected": sorted(result.rejected, key=lambda r: r["id"])},
                       sort_keys=False), encoding="utf-8")
```

- [ ] **Step 4: Register the CLI command**

In `tools/apd_gauntlet/cli.py`, add after `cluster_candidates_cmd`:

```python
@main.command("apply-clusters")
@click.argument("run_dir", type=click.Path(exists=True, file_okay=False, path_type=Path))
def apply_clusters_cmd(run_dir: Path) -> None:
    """5c: apply cluster-decisions.yaml; emit deduped + severity-disagreements + rejected."""
    from .synthesis.apply import AdjudicationMissing, apply_clusters

    try:
        result = apply_clusters(run_dir)
    except AdjudicationMissing as exc:
        click.echo(f"apply-clusters: blocked - {exc}", err=True)
        raise SystemExit(2) from None
    click.echo(
        f"apply-clusters: wrote {len(result.findings)} findings, "
        f"{len(result.capabilities)} capabilities, "
        f"{len(result.contradictions)} contradictions, "
        f"{len(result.rejected)} rejected"
    )
```

(Exit code 2 on `AdjudicationMissing` distinguishes the fallback signal from a clean run; Plan 3's workflow branches on it. This mirrors `parse-threat-model`'s `click.Abort()` non-zero exit and `analyze-attack-paths`'s blocked branch.)

- [ ] **Step 5: Run test to verify it passes**

Run: `python3 -m pytest tests/test_cli_apply_clusters.py -v`
Expected: PASS (5 passed). The sorted-union assertion `["AU-10", "AU-9", "AU-9(2)", "AU-9(3)"]` holds because Python's default string sort orders `AU-10 < AU-9` (the `1` < `9` at position 3); the test pins this exact order so the implementation's `sorted()` is the contract.

- [ ] **Step 6: Commit**

```bash
git add tools/apd_gauntlet/synthesis/apply.py tools/apd_gauntlet/cli.py tests/test_cli_apply_clusters.py
git commit -m "feat(synthesis): apply-clusters (merge/link/separate + contradictions.yaml producer + stale-cap downgrade + reproducible deduped output)"
```

---

## Task 6: `rollup` command (5d)

Pure aggregation over the deduped files + apath, reproducing the canonical list-shaped coverage YAMLs (`controls:` / `techniques:` / `components:`) plus cwe/owasp/d3fend when the run declares those taxonomies. Imports `coverage_logic` + the three reference JSONs. Deterministic ordering (first-appearance over deduped record order, then by id). `generated_by: synthesizer` on cwe/owasp/d3fend (their schemas hardcode that enum).

**Files:**
- Create: `tools/apd_gauntlet/synthesis/rollup.py`
- Modify: `tools/apd_gauntlet/cli.py`
- Test: `tests/test_cli_rollup.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_cli_rollup.py`:

```python
"""rollup: emits the canonical list-shaped coverage YAMLs validated by the doc-wrappers."""
from __future__ import annotations

import json
import pathlib
import shutil

import yaml
from apd_gauntlet.cli import main
from apd_gauntlet.validate import build_registry
from click.testing import CliRunner
from jsonschema import Draft202012Validator

REPO = pathlib.Path(__file__).parent.parent
SCHEMA_DIR = REPO / "schemas"
EXAMPLE = REPO / "examples" / "apd-20260601-claim-event-bus" / "expected"


def _copy_example(tmp_path):
    dst = tmp_path / "run"
    shutil.copytree(EXAMPLE, dst)
    return dst


def _validate(doc, schema_name):
    schema = json.loads((SCHEMA_DIR / schema_name).read_text())
    return list(Draft202012Validator(schema, registry=build_registry()).iter_errors(doc))


def test_rollup_emits_doc_wrapper_valid_nist_attack_matrix(tmp_path):
    dst = _copy_example(tmp_path)
    result = CliRunner().invoke(main, ["rollup", str(dst)])
    assert result.exit_code == 0, result.output
    nist = yaml.safe_load((dst / "40-synthesis" / "nist-coverage.yaml").read_text())
    assert _validate(nist, "nist-coverage-doc.schema.json") == []
    attack = yaml.safe_load((dst / "40-synthesis" / "attack-exposure.yaml").read_text())
    assert _validate(attack, "attack-exposure-doc.schema.json") == []
    matrix = yaml.safe_load((dst / "40-synthesis" / "apd-coverage-matrix.yaml").read_text())
    assert _validate(matrix, "coverage-matrix-doc.schema.json") == []


def test_nist_finding_count_equals_len_finding_ids(tmp_path):
    dst = _copy_example(tmp_path)
    CliRunner().invoke(main, ["rollup", str(dst)])
    nist = yaml.safe_load((dst / "40-synthesis" / "nist-coverage.yaml").read_text())
    for ctrl in nist["controls"]:
        assert ctrl["finding_count"] == len(ctrl["finding_ids"])
        assert ctrl["capability_count"] == len(ctrl["capability_ids"])
        has_f, has_c = bool(ctrl["finding_ids"]), bool(ctrl["capability_ids"])
        expect = ("gapped_and_covered" if has_f and has_c
                  else "gapped" if has_f else "covered" if has_c else "silent")
        assert ctrl["posture"] == expect


def test_attack_technique_present_only_if_a_finding_maps_it(tmp_path):
    dst = _copy_example(tmp_path)
    CliRunner().invoke(main, ["rollup", str(dst)])
    attack = yaml.safe_load((dst / "40-synthesis" / "attack-exposure.yaml").read_text())
    for tech in attack["techniques"]:
        assert tech["exposure_finding_count"] >= 1


def test_attack_name_never_empty_and_schema_valid(tmp_path):
    # C4: name must be looked up (minLength:3); name:"" would FAIL the wrapper
    # schema. Validate via the doc-wrapper AND assert each name is non-empty.
    dst = _copy_example(tmp_path)
    CliRunner().invoke(main, ["rollup", str(dst)])
    attack = yaml.safe_load((dst / "40-synthesis" / "attack-exposure.yaml").read_text())
    assert _validate(attack, "attack-exposure-doc.schema.json") == []
    for tech in attack["techniques"]:
        assert len(tech["name"]) >= 3, tech["id"]
    # T1530 resolves to its real title from the bundled catalog.
    by_id = {t["id"]: t for t in attack["techniques"]}
    if "T1530" in by_id:
        assert by_id["T1530"]["name"] == "Data from Cloud Storage"


def test_owasp_d3fend_names_resolved_when_declared(tmp_path):
    # I2: owasp/d3fend names come from the bundled catalogs, not raw ids.
    dst = _copy_example(tmp_path)
    CliRunner().invoke(main, ["rollup", str(dst)])
    owasp = dst / "40-synthesis" / "owasp-coverage.yaml"
    if owasp.exists():
        doc = yaml.safe_load(owasp.read_text())
        for e in doc["entries"]:
            # A resolved name is non-empty; for known cats it differs from the id.
            assert e["name"]
            if e["category_id"] == "API2:2023":
                assert e["name"] == "Broken Authentication"
    d3 = dst / "40-synthesis" / "d3fend-coverage.yaml"
    if d3.exists():
        doc = yaml.safe_load(d3.read_text())
        for e in doc["defensive_entries"]:
            assert e["name"]


def test_matrix_emits_all_nine_goals_per_component(tmp_path):
    dst = _copy_example(tmp_path)
    CliRunner().invoke(main, ["rollup", str(dst)])
    matrix = yaml.safe_load((dst / "40-synthesis" / "apd-coverage-matrix.yaml").read_text())
    nine = {"confidentiality", "integrity", "availability", "distributed", "resilient",
            "ephemeral", "authenticity", "non_repudiation", "immutability"}
    for comp in matrix["components"]:
        assert set(comp["cells"].keys()) == nine


def test_cwe_owasp_d3fend_emitted_only_when_declared(tmp_path):
    dst = _copy_example(tmp_path)
    # The example .apd-run.yaml declares taxonomies; rollup should emit cwe/owasp/d3fend.
    CliRunner().invoke(main, ["rollup", str(dst)])
    cwe = dst / "40-synthesis" / "cwe-coverage.yaml"
    if cwe.exists():
        doc = yaml.safe_load(cwe.read_text())
        assert doc["generated_by"] == "synthesizer"
        assert _validate(doc, "cwe-coverage.schema.json") == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_cli_rollup.py -v`
Expected: FAIL — `Error: No such command 'rollup'.`

- [ ] **Step 3: Write `rollup.py`**

Create `tools/apd_gauntlet/synthesis/rollup.py`:

```python
"""5d rollup — pure aggregation over deduped records into canonical coverage YAMLs.

Reproduces the example-golden list shapes (NOT the divergent runs/ shapes):
  nist-coverage.yaml      controls: [ {id, family, title, finding_count, finding_ids,
                                       capability_count, capability_ids, posture} ]
  attack-exposure.yaml    techniques: [ {id, sub_technique, tactic, name,
                                         exposure_finding_count, exposure_finding_ids,
                                         mitigated_by_capabilities} ]
  apd-coverage-matrix.yaml components: [ {name, cells: {<9 goals>: {findings, capabilities, posture}}} ]
  cwe/owasp/d3fend-coverage.yaml — only when the run declares those taxonomies.

Deterministic: controls/techniques sorted by first-appearance over deduped
record order then by id; cells emit all 9 goals in canonical GOAL_SHORT order.
Roll up ONLY what records cite; never synthesize from reference data.

EQUIVALENCE SCOPE (I1): nist-coverage / attack-exposure reproduce the golden's
per-row finding/capability membership + posture. The apd-coverage-matrix
reproduces the golden SHAPE and per-cell posture SEMANTICS, but its component
LABELS are NOT a golden-equivalence target — the golden labels components by
editorial logical-asset names that no deterministic rule reproduces (see
_matrix_rollup). The matrix is excluded from the Task 8 equivalence projection.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from ..report.taxonomy import attack_technique_titles, d3fend_titles
from . import coverage_logic as cl
from .loader import load_corpus

_PKG_DATA = Path(__file__).resolve().parent.parent / "data"

# Import-cycle note: report.taxonomy imports only stdlib (no synthesis import),
# and synthesis.rollup is never imported by report.*, so this synthesis->report
# edge does NOT close the report->synthesis cycle that coverage_logic broke
# (report.transform->synthesis.coverage_logic is the only report->synthesis edge,
# and it does not touch rollup or taxonomy).


@dataclass
class RollupResult:
    nist: list[dict[str, Any]] = field(default_factory=list)
    attack: list[dict[str, Any]] = field(default_factory=list)
    matrix: list[dict[str, Any]] = field(default_factory=list)
    cwe: dict[str, Any] | None = None
    owasp: dict[str, Any] | None = None
    d3fend: dict[str, Any] | None = None


def _nist_titles() -> dict[str, str]:
    path = _PKG_DATA / "nist-controls.json"
    if not path.is_file():
        return {}
    raw = json.loads(path.read_text(encoding="utf-8"))
    return raw.get("controls", raw) if isinstance(raw, dict) else {}


def _family_titles() -> dict[str, str]:
    return json.loads((_PKG_DATA / "nist-families.json").read_text(encoding="utf-8"))


def _load_deduped(run_dir: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    synth = run_dir / "40-synthesis"
    fdoc = yaml.safe_load((synth / "deduped-findings.yaml").read_text(encoding="utf-8")) or {}
    cdoc = yaml.safe_load((synth / "deduped-capabilities.yaml").read_text(encoding="utf-8")) or {}
    findings = [f for f in (fdoc.get("finding") or []) if isinstance(f, dict)]
    caps = [c for c in (cdoc.get("capability") or []) if isinstance(c, dict)]
    # Include apath-* (spec Steps 2/8 — apath in the finding corpus for nist/matrix).
    apath_by_id, _ = load_corpus(run_dir, include_attack_path=True)
    seen = {f.get("id") for f in findings}
    for fid, rec in apath_by_id.items():
        if fid.startswith("apath-") and fid not in seen:
            findings.append(rec)
    return findings, caps


def _nist_rollup(findings, caps, titles, fam_titles) -> list[dict[str, Any]]:
    order: list[str] = []
    fmap: dict[str, list[str]] = {}
    for f in findings:
        for cid in cl.normalize_nist_ids(
            cl.extract_ids_from_mapping((f.get("control_mappings") or {}).get("nist_800_53r5"))
        ):
            if cid not in fmap:
                fmap[cid] = []
                order.append(cid)
            if f["id"] not in fmap[cid]:
                fmap[cid].append(f["id"])
    cap_index = cl.build_cap_controls_index(caps)
    rows: list[dict[str, Any]] = []
    for cid in sorted(set(order) | set(cap_index), key=lambda c: (order.index(c) if c in order else 1_000_000, c)):
        fids = sorted(fmap.get(cid, []))
        cids = sorted(cap_index.get(cid, set()))
        fam = cl.nist_family_of(cid)
        rows.append({
            "id": cid, "family": fam,
            "title": titles.get(cid) or fam_titles.get(fam, fam),
            "finding_count": len(fids), "finding_ids": fids,
            "capability_count": len(cids), "capability_ids": cids,
            "posture": cl.posture(has_findings=bool(fids), has_caps=bool(cids)),
        })
    return rows


def _attack_rollup(findings, caps) -> list[dict[str, Any]]:
    mit_path = _PKG_DATA / "mitre-mitigations.json"
    mitigations = json.loads(mit_path.read_text(encoding="utf-8")).get("mitigations", {})
    # C4: attack-exposure.schema.json requires name minLength:3 — name:"" FAILS
    # validation and contradicts the golden (which carries real technique names
    # like "Data from Cloud Storage"). Look up the title from the bundled
    # ATT&CK catalog (report.taxonomy.attack_technique_titles returns {tid: name}),
    # falling back to the id (always >= 3 chars: "T####") so name is never "".
    titles = attack_technique_titles()
    order: list[str] = []
    tech: dict[str, dict[str, Any]] = {}
    for f in findings:
        for m in (f.get("control_mappings") or {}).get("mitre_attack") or []:
            if not isinstance(m, dict) or not m.get("technique"):
                continue
            tid = m["technique"]
            if tid not in tech:
                tech[tid] = {"tactic": m.get("tactic"), "sub_technique": m.get("sub_technique"),
                             "finding_ids": []}
                order.append(tid)
            if f["id"] not in tech[tid]["finding_ids"]:
                tech[tid]["finding_ids"].append(f["id"])
    rows: list[dict[str, Any]] = []
    for tid in sorted(order, key=lambda t: (order.index(t), t)):
        fids = sorted(tech[tid]["finding_ids"])
        mits: list[dict[str, str]] = []
        for cap in caps:
            for m in (cap.get("control_mappings") or {}).get("mitre_attack_mitigations") or []:
                mid = m.get("id") if isinstance(m, dict) else None
                if mid and tid in mitigations.get(mid, []):
                    mits.append({"capability_id": cap["id"], "mitigation_id": mid})
        mits.sort(key=lambda x: (x["capability_id"], x["mitigation_id"]))
        rows.append({
            "id": tid, "sub_technique": tech[tid]["sub_technique"], "tactic": tech[tid]["tactic"],
            "name": titles.get(tid, tid), "exposure_finding_count": len(fids),
            "exposure_finding_ids": fids, "mitigated_by_capabilities": mits,
        })
    return rows


def _matrix_rollup(findings, caps, inventory) -> list[dict[str, Any]]:
    # I1 — DIVERGENCE (grounded against the golden, not a defect to "fix"):
    # the example golden apd-coverage-matrix.yaml keys components by LOGICAL
    # ASSET LABELS ("Kafka claim-events topic", "RDS audit_log table") and
    # attributes the SAME finding id to MULTIPLE components (e.g. intg-42a3ebbd
    # — whose only evidence artifact is threat-model.md — appears under BOTH
    # the Kafka and RDS components; immut-067a7391 appears under Kafka.immut AND
    # RDS.availability). asset-inventory.yaml asset names are
    # "claim-ingress-api"/"audit-log-store"/... — they match NEITHER the golden
    # labels NOR a single evidence-artifact filename. The golden component
    # attribution is therefore an EDITORIAL (LLM/synthesizer) judgement about
    # which logical assets a finding touches, NOT a function any deterministic
    # one-component-per-record _label() can reproduce. Consequently:
    #   * the COMPONENT LABEL is explicitly NOT a golden-equivalence target;
    #   * only the per-cell posture SEMANTICS (gapped/covered/both/silent given
    #     a component's finding+capability membership, all 9 goals present) are
    #     a reproducible contract — and those ARE tested below;
    #   * the rollup keys deterministically by the first-evidence ARTIFACT label
    #     (one component per record), which is a faithful, reproducible matrix —
    #     it just won't byte-match the golden's editorial logical-asset labels.
    # The Task 8 equivalence test does NOT project the matrix for this reason
    # (it projects nist only). Plan 3 may add an optional LLM matrix-labeling
    # pass if logical-asset attribution becomes a requirement.
    components = [a.get("name", "") for a in (inventory.get("assets") or [])
                 if isinstance(a, dict) and a.get("name")]
    # Index findings/caps by (component-artifact-label, goal).
    def _label(rec):
        ev = rec.get("evidence") or []
        return str(ev[0].get("artifact")) if ev and isinstance(ev[0], dict) else "(unattributed)"
    comp_goal_f: dict[str, dict[str, list[str]]] = {}
    comp_goal_c: dict[str, dict[str, list[str]]] = {}
    for f in findings:
        g = f.get("apd_goal")
        if g in cl.GOAL_SHORT:
            comp_goal_f.setdefault(_label(f), {}).setdefault(g, []).append(f["id"])
    for c in caps:
        g = c.get("apd_goal")
        if g in cl.GOAL_SHORT:
            comp_goal_c.setdefault(_label(c), {}).setdefault(g, []).append(c["id"])
    names = sorted(set(components) | set(comp_goal_f) | set(comp_goal_c))
    rows: list[dict[str, Any]] = []
    for name in names:
        cells: dict[str, Any] = {}
        for goal in cl.GOAL_SHORT:
            fids = sorted(comp_goal_f.get(name, {}).get(goal, []))
            cids = sorted(comp_goal_c.get(name, {}).get(goal, []))
            cells[goal] = {"findings": fids, "capabilities": cids,
                           "posture": cl.posture(has_findings=bool(fids), has_caps=bool(cids))}
        rows.append({"name": name, "cells": cells})
    return rows


def _declared_taxonomies(run_cfg: dict[str, Any]) -> set[str]:
    raw = run_cfg.get("taxonomies") or []
    return {str(t).strip() for t in raw} if isinstance(raw, list) else set()


def build_rollups(run_dir: Path) -> RollupResult:
    findings, caps = _load_deduped(run_dir)
    inventory = yaml.safe_load(
        (run_dir / "00-context" / "asset-inventory.yaml").read_text(encoding="utf-8")
    ) or {}
    run_cfg = yaml.safe_load(
        (run_dir / ".apd-run.yaml").read_text(encoding="utf-8")
    ) if (run_dir / ".apd-run.yaml").is_file() else {}
    run_cfg = run_cfg or {}

    result = RollupResult()
    result.nist = _nist_rollup(findings, caps, _nist_titles(), _family_titles())
    result.attack = _attack_rollup(findings, caps)
    result.matrix = _matrix_rollup(findings, caps, inventory)

    declared = _declared_taxonomies(run_cfg)
    if "cwe" in declared:
        result.cwe = _cwe_rollup(findings)
    if declared & {"owasp_top10", "owasp_api_top10", "owasp_llm_top10"}:
        result.owasp = _owasp_rollup(findings, declared)
    if "d3fend" in declared:
        result.d3fend = _d3fend_rollup(findings, caps)

    _write(run_dir, result)
    return result


def _cwe_rollup(findings) -> dict[str, Any]:
    cwe_data = json.loads((_PKG_DATA / "cwe.json").read_text(encoding="utf-8"))
    by_id = {e["cwe_id"]: e for e in cwe_data.get("entries", []) if isinstance(e, dict)}
    order: list[str] = []
    grouped: dict[str, dict[str, Any]] = {}
    for f in findings:
        for cid in cl.extract_ids_from_mapping((f.get("control_mappings") or {}).get("cwe")):
            if cid not in grouped:
                grouped[cid] = {"finding_ids": [], "surfaces": set()}
                order.append(cid)
            grouped[cid]["finding_ids"].append(f["id"])
            for ev in f.get("evidence") or []:
                if isinstance(ev, dict) and ev.get("locator"):
                    grouped[cid]["surfaces"].add(str(ev["locator"]))
    entries = []
    for cid in sorted(order, key=lambda c: (order.index(c), c)):
        ref = by_id.get(cid, {})
        parents = ref.get("parents") or []
        entries.append({
            "cwe_id": cid, "name": ref.get("name", cid),
            "abstraction": ref.get("abstraction", "base"),
            "parent_pillar": parents[0] if parents else None,
            "finding_count": len(grouped[cid]["finding_ids"]),
            "finding_ids": sorted(grouped[cid]["finding_ids"]),
            "surfaces": sorted(grouped[cid]["surfaces"]),
        })
    return {"schema_version": 1, "generated_by": "synthesizer", "entries": entries}


def _owasp_names(tax_key: str) -> dict[str, str]:
    """Return {category_id: name} from the bundled owasp_*.json catalog (I2).

    The data files are {"entries": [{category_id, name}, ...]}; the golden
    owasp-coverage carries real names (e.g. "Broken Authentication"), so a
    raw-id name diverges. Falls back to {} (callers use category_id) on miss.
    """
    path = _PKG_DATA / f"{tax_key}.json"
    if not path.is_file():
        return {}
    raw = json.loads(path.read_text(encoding="utf-8"))
    out: dict[str, str] = {}
    for entry in (raw.get("entries") or []) if isinstance(raw, dict) else []:
        if isinstance(entry, dict) and entry.get("category_id"):
            out[entry["category_id"]] = entry.get("name") or entry["category_id"]
    return out


def _owasp_rollup(findings, declared) -> dict[str, Any]:
    entries = []
    for tax_key, field_key in (("owasp_top10", "owasp_top10"),
                               ("owasp_api_top10", "owasp_api_top10"),
                               ("owasp_llm_top10", "owasp_llm_top10")):
        if tax_key not in declared:
            continue
        names = _owasp_names(tax_key)
        grouped: dict[str, dict[str, Any]] = {}
        order: list[str] = []
        for f in findings:
            for cat in cl.extract_ids_from_mapping((f.get("control_mappings") or {}).get(field_key)):
                if cat not in grouped:
                    grouped[cat] = {"finding_ids": [], "surfaces": set()}
                    order.append(cat)
                grouped[cat]["finding_ids"].append(f["id"])
                for ev in f.get("evidence") or []:
                    if isinstance(ev, dict) and ev.get("locator"):
                        grouped[cat]["surfaces"].add(str(ev["locator"]))
        for cat in sorted(order, key=lambda c: (order.index(c), c)):
            entries.append({
                "taxonomy": tax_key, "category_id": cat, "name": names.get(cat, cat),
                "finding_count": len(grouped[cat]["finding_ids"]),
                "finding_ids": sorted(grouped[cat]["finding_ids"]),
                "surfaces": sorted(grouped[cat]["surfaces"]), "silent": False,
            })
    return {"schema_version": 1, "generated_by": "synthesizer", "entries": entries}
```

(Note: the example golden's `owasp-coverage.yaml` also emits `silent: true` rows for every non-cited category in a declared taxonomy. Plan 2's `_owasp_rollup` emits only the cited rows — a deliberate scope limit (the silent-row enumeration is the same out-of-scope `silent` behavior deferred in the resolved-open-questions §; the equivalence test does NOT project owasp). The I2 fix is strictly the per-row NAME lookup so cited rows carry real category names instead of the raw id.)

```python


def _d3fend_rollup(findings, caps) -> dict[str, Any]:
    # I2: the golden d3fend-coverage carries real names (e.g. "Agent
    # Authentication"); name=d["technique"] (the raw id) diverges. Look up from
    # the bundled D3FEND catalog (report.taxonomy.d3fend_titles → {id: name}),
    # falling back to the id on miss.
    d3_names = d3fend_titles()
    defensive = []
    for cap in caps:
        for d in (cap.get("control_mappings") or {}).get("d3fend") or []:
            if isinstance(d, dict) and d.get("technique"):
                did = d["technique"]
                defensive.append({
                    "d3fend_id": did, "name": d3_names.get(did, did),
                    "capability_count": 1, "capability_ids": [cap["id"]],
                    "counters_attack": sorted(d.get("counters_attack") or []),
                })
    defensive.sort(key=lambda e: e["d3fend_id"])
    counter = []
    for f in findings:
        for m in (f.get("control_mappings") or {}).get("mitre_attack") or []:
            tid = m.get("technique") if isinstance(m, dict) else None
            if tid:
                counter.append({
                    "attack_technique": tid, "exposed_by_finding_count": 1,
                    "exposed_by_finding_ids": [f["id"]],
                    "countered_by_d3fend": [], "countered_by_capability_ids": [],
                    "has_capability_coverage": False,
                })
    counter.sort(key=lambda e: e["attack_technique"])
    return {"schema_version": 1, "generated_by": "synthesizer",
            "defensive_entries": defensive, "counter_coverage": counter}


def _write(run_dir: Path, result: RollupResult) -> None:
    synth = run_dir / "40-synthesis"
    synth.mkdir(parents=True, exist_ok=True)
    (synth / "nist-coverage.yaml").write_text(
        yaml.safe_dump({"controls": result.nist}, sort_keys=False), encoding="utf-8")
    (synth / "attack-exposure.yaml").write_text(
        yaml.safe_dump({"techniques": result.attack}, sort_keys=False), encoding="utf-8")
    (synth / "apd-coverage-matrix.yaml").write_text(
        yaml.safe_dump({"components": result.matrix}, sort_keys=False), encoding="utf-8")
    if result.cwe is not None:
        (synth / "cwe-coverage.yaml").write_text(
            yaml.safe_dump(result.cwe, sort_keys=False), encoding="utf-8")
    if result.owasp is not None:
        (synth / "owasp-coverage.yaml").write_text(
            yaml.safe_dump(result.owasp, sort_keys=False), encoding="utf-8")
    if result.d3fend is not None:
        (synth / "d3fend-coverage.yaml").write_text(
            yaml.safe_dump(result.d3fend, sort_keys=False), encoding="utf-8")
```

- [ ] **Step 4: Register the CLI command**

In `tools/apd_gauntlet/cli.py`, add after `apply_clusters_cmd`:

```python
@main.command("rollup")
@click.argument("run_dir", type=click.Path(exists=True, file_okay=False, path_type=Path))
def rollup_cmd(run_dir: Path) -> None:
    """5d: aggregate deduped records into the canonical coverage YAMLs."""
    from .synthesis.rollup import build_rollups

    result = build_rollups(run_dir)
    taxonomies = sum(x is not None for x in (result.cwe, result.owasp, result.d3fend))
    click.echo(
        f"rollup: wrote {len(result.nist)} controls, {len(result.attack)} techniques, "
        f"{len(result.matrix)} components, {taxonomies} extra coverage files"
    )
```

- [ ] **Step 5: Run test to verify it passes**

Run: `python3 -m pytest tests/test_cli_rollup.py -v`
Expected: PASS (5 passed). The example run's `.apd-run.yaml` taxonomy declaration drives the cwe/owasp/d3fend conditional; if the example does not declare them, those files are not emitted and `test_cwe_owasp_d3fend_emitted_only_when_declared` is satisfied by the `if cwe.exists():` guard.

- [ ] **Step 6: Commit**

```bash
git add tools/apd_gauntlet/synthesis/rollup.py tools/apd_gauntlet/cli.py tests/test_cli_rollup.py
git commit -m "feat(synthesis): rollup command (canonical list-shaped coverage YAMLs, deterministic)"
```

---

## Task 7: `audit-report` command (5g, Python half)

Parse `data.js` back to a dict, RECOMPUTE via `report.loader.load_run` + `report.transform.build_apd_data`, run the structural checks, emit compact `report-audit.yaml`. Exit 1 on FAIL so the workflow gate branches. Houses `parse_data_js(path)`.

> **M3 — severity-count parity deviates from "match summarize" (deliberate, more faithful).** Design §7.1 says the audit should "match summarize", but `summarize_run` counts ONLY the deduped findings and OMITS apath, whereas `data.js` renders `findings_total: 90 = 15 deduped + 75 apath` (confirmed against the golden). Matching `summarize` would therefore FALSELY flag every run as drifted. So `audit-report` recomputes the severity counts directly from `deduped-findings + attack-path.findings` (normalizing `informational`→`info` to match the data.js enum) — a more faithful parity check against what the report actually shows. (Maturity-count parity is OUT OF SCOPE for Plan 2 — the audit checks finding severity totals + id coverage, not capability maturity histograms.)

> **PRECONDITION (I6) — commit the golden `report-html/` fixture FIRST.** Tasks 7, 8, and 11 read `examples/apd-20260601-claim-event-bus/expected/40-synthesis/report-html/{data.js,build-manifest.txt}`, which are currently UNTRACKED in git (verify: `git status --short examples/.../40-synthesis/report-html/` shows `??`). On a clean checkout / in CI those files would be absent and `test_parse_data_js_roundtrips_window_assignment` + `test_audit_passes_on_committed_example` would error with `FileNotFoundError`. Because this directory IS the golden reference, commit it before Task 7's tests run:
>
> ```bash
> git add examples/apd-20260601-claim-event-bus/expected/40-synthesis/report-html/
> git commit -m "test(fixtures): commit golden report-html/ (data.js + build-manifest) for audit/equivalence tests"
> ```
>
> (Do this as the first step of Task 7 — or fold it into the Task 3 commit if executing earlier. The font/woff2 + vendored JS files in that directory are part of the committed golden bundle and should be added too.)

**Files:**
- Create: `tools/apd_gauntlet/synthesis/audit.py`
- Modify: `tools/apd_gauntlet/cli.py`
- Test: `tests/test_cli_audit_report.py`
- Precondition: `git add examples/apd-20260601-claim-event-bus/expected/40-synthesis/report-html/` (untracked golden fixture)

- [ ] **Step 1: Write the failing test**

Create `tests/test_cli_audit_report.py`:

```python
"""audit-report: structural data.js<->YAML cross-check; exit 1 on FAIL."""
from __future__ import annotations

import json
import pathlib
import shutil

import pytest
import yaml
from apd_gauntlet.cli import main
from apd_gauntlet.synthesis.audit import audit_report, parse_data_js
from click.testing import CliRunner

REPO = pathlib.Path(__file__).parent.parent
EXAMPLE = REPO / "examples" / "apd-20260601-claim-event-bus" / "expected"
BUNDLE = REPO / "tools" / "apd_gauntlet" / "data" / "report-template" / "index.html"


def _copy_example(tmp_path):
    dst = tmp_path / "run"
    shutil.copytree(EXAMPLE, dst)
    return dst


def test_parse_data_js_roundtrips_window_assignment(tmp_path):
    data_js = EXAMPLE / "40-synthesis" / "report-html" / "data.js"
    d = parse_data_js(data_js)
    assert "findings" in d and "meta" in d
    # 15 deduped + 75 apath = 90 findings in the rendered data.
    assert len(d["findings"]) == 90


def test_audit_passes_on_committed_example(tmp_path):
    dst = _copy_example(tmp_path)
    result = audit_report(dst)
    assert result.status == "pass", [c for c in result.checks if c["status"] == "fail"]
    assert any(c["name"] == "id_coverage_findings" for c in result.checks)


def test_audit_writes_compact_report_audit_yaml(tmp_path):
    dst = _copy_example(tmp_path)
    audit_report(dst)
    out = dst / "40-synthesis" / "report-audit.yaml"
    doc = yaml.safe_load(out.read_text())
    assert doc["generated_by"] == "apd-gauntlet"
    assert doc["status"] in ("pass", "fail")
    # Compact: never embeds the full data.js (no 'findings' array).
    assert "findings" not in doc


def test_audit_fails_on_stale_data_js(tmp_path):
    dst = _copy_example(tmp_path)
    # Corrupt data.js so the recompute<->parsed diff and id-coverage fail.
    data_js = dst / "40-synthesis" / "report-html" / "data.js"
    text = data_js.read_text().replace('"conf-7aa376c5"', '"conf-DELETED0"', 1)
    data_js.write_text(text)
    result = audit_report(dst)
    assert result.status == "fail"


def test_cli_audit_report_exit_code(tmp_path):
    dst = _copy_example(tmp_path)
    result = CliRunner().invoke(main, ["audit-report", str(dst)])
    assert result.exit_code == 0, result.output
    # Now break it: stale data.js -> exit 1.
    data_js = dst / "40-synthesis" / "report-html" / "data.js"
    data_js.write_text(data_js.read_text().replace('"conf-7aa376c5"', '"conf-DELETED0"', 1))
    result2 = CliRunner().invoke(main, ["audit-report", str(dst)])
    assert result2.exit_code == 1, result2.output
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_cli_audit_report.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'apd_gauntlet.synthesis.audit'`.

- [ ] **Step 3: Write `audit.py`**

Create `tools/apd_gauntlet/synthesis/audit.py`:

```python
"""5g audit-report — structural data.js<->YAML cross-check.

Parses data.js back to a dict, RECOMPUTES the expected data via
report.loader.load_run + report.transform.build_apd_data, and runs structural
checks. Emits compact report-audit.yaml (the LLM auditor reads this, never
data.js). Status fail -> CLI exits 1 so the workflow gate branches.
"""
from __future__ import annotations

import collections
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

_INFORMATIONAL_TO_INFO = {"informational": "info"}


@dataclass
class AuditResult:
    status: str = "pass"
    checks: list[dict[str, str]] = field(default_factory=list)
    counts: dict[str, int] = field(default_factory=dict)
    drift: list[dict[str, str]] = field(default_factory=list)


def parse_data_js(path: Path) -> dict[str, Any]:
    """Parse 'window.APD_DATA = {...};' back into a dict.

    Strips the prefix + trailing ';', reverses the '</' -> '<\\/' escaping that
    emit.write_data_js applies, then json.loads.
    """
    text = path.read_text(encoding="utf-8").strip()
    prefix = "window.APD_DATA = "
    if text.startswith(prefix):
        text = text[len(prefix):]
    text = text.rstrip()
    if text.endswith(";"):
        text = text[:-1]
    text = text.replace("<\\/", "</")
    return json.loads(text)


def _yaml_records(path: Path, key: str) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    doc = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return [r for r in (doc.get(key) or []) if isinstance(r, dict)]


def _check(result: AuditResult, name: str, ok: bool, detail: str) -> None:
    result.checks.append({"name": name, "status": "pass" if ok else "fail", "detail": detail})
    if not ok:
        result.status = "fail"


def audit_report(run_dir: Path) -> AuditResult:
    from ..report.loader import load_run
    from ..report.transform import build_apd_data

    synth = run_dir / "40-synthesis"
    result = AuditResult()

    data_js_path = synth / "report-html" / "data.js"
    if not data_js_path.is_file():
        _check(result, "data_js_present", False, f"missing {data_js_path}")
        _write(run_dir, result)
        return result
    parsed = parse_data_js(data_js_path)

    # Authoritative YAML record sets.
    deduped_f = _yaml_records(synth / "deduped-findings.yaml", "finding")
    deduped_c = _yaml_records(synth / "deduped-capabilities.yaml", "capability")
    apath_f = _yaml_records(synth / "attack-path.findings.yaml", "finding")
    nist = _yaml_records(synth / "nist-coverage.yaml", "controls")
    attack = _yaml_records(synth / "attack-exposure.yaml", "techniques")

    # ID coverage (findings): deduped UNION apath == data.findings ids.
    yaml_fids = {f.get("id") for f in deduped_f} | {f.get("id") for f in apath_f}
    data_fids = {f.get("id") for f in parsed.get("findings", [])}
    _check(result, "id_coverage_findings", yaml_fids == data_fids,
           f"yaml={len(yaml_fids)} data.js={len(data_fids)} missing={sorted(yaml_fids - data_fids)[:5]}")

    # ID coverage (capabilities).
    yaml_cids = {c.get("id") for c in deduped_c}
    data_cids = {c.get("id") for c in parsed.get("capabilities", [])}
    _check(result, "id_coverage_capabilities", yaml_cids == data_cids,
           f"yaml={len(yaml_cids)} data.js={len(data_cids)}")

    # NIST per-control vs taxonomy keys (nist_rollup is family-aggregated).
    taxonomy = parsed.get("taxonomy", {})
    nist_ids = {row.get("id") for row in nist}
    missing_nist = {cid for cid in nist_ids if cid not in taxonomy}
    _check(result, "id_coverage_nist", not missing_nist,
           f"controls={len(nist_ids)} missing_from_taxonomy={sorted(missing_nist)[:5]}")

    # ATT&CK per-technique (data.attack_exposure is 1:1).
    attack_ids = {row.get("id") for row in attack}
    data_attack_ids = {row.get("id") for row in parsed.get("attack_exposure", [])}
    _check(result, "id_coverage_attack", attack_ids <= data_attack_ids,
           f"yaml={len(attack_ids)} data.js={len(data_attack_ids)}")

    # Count parity (severity): recompute from deduped+apath, normalizing
    # 'informational'->'info'. NOT against summarize_run (which omits apath).
    by_sev = collections.Counter(
        _INFORMATIONAL_TO_INFO.get(f.get("severity", "informational"), f.get("severity", "informational"))
        for f in deduped_f + apath_f
    )
    data_by_sev = parsed.get("summary", {}).get("bySeverity", {})
    sev_ok = all(data_by_sev.get(k, 0) == by_sev.get(k, 0)
                 for k in ("critical", "high", "medium", "low", "info"))
    _check(result, "count_parity_severity", sev_ok, f"recomputed={dict(by_sev)} data.js={data_by_sev}")

    # Count parity (totals).
    total_ok = parsed.get("summary", {}).get("findings_total") == len(deduped_f) + len(apath_f)
    _check(result, "count_parity_totals", total_ok,
           f"data.js={parsed.get('summary', {}).get('findings_total')} yaml={len(deduped_f) + len(apath_f)}")

    # data.js <-> recomputed drift.
    try:
        recomputed = build_apd_data(load_run(run_dir), run_dir=run_dir)
        recomputed_fids = {f.get("id") for f in recomputed.get("findings", [])}
        drift_ok = recomputed_fids == data_fids
        _check(result, "data_js_recompute_drift", drift_ok,
               f"recompute_findings={len(recomputed_fids)} data.js={len(data_fids)}")
    except Exception as exc:  # noqa: BLE001 — recompute is best-effort
        _check(result, "data_js_recompute_drift", False, f"recompute failed: {exc}")

    # section_errors gate.
    section_errors = (parsed.get("meta") or {}).get("section_errors") or {}
    _check(result, "section_errors_empty", not section_errors, f"section_errors={list(section_errors)}")

    result.counts = {
        "findings_yaml": len(deduped_f), "findings_data_js": len(data_fids),
        "capabilities_yaml": len(deduped_c), "capabilities_data_js": len(data_cids),
        "nist_controls_yaml": len(nist_ids),
        "nist_ids_in_taxonomy": len(nist_ids - missing_nist),
        "attack_techniques_yaml": len(attack_ids), "attack_techniques_data_js": len(data_attack_ids),
    }
    _source_hash_drift(run_dir, result)
    _write(run_dir, result)
    return result


def _source_hash_drift(run_dir: Path, result: AuditResult) -> None:
    from ..report.loader import _yaml_with_hash

    manifest = run_dir / "40-synthesis" / "report-html" / "build-manifest.txt"
    if not manifest.is_file():
        return
    recorded: dict[str, str] = {}
    for line in manifest.read_text(encoding="utf-8").splitlines():
        if "=" in line:
            k, v = line.split("=", 1)
            recorded[k] = v
    for filename in ("deduped-findings.yaml", "deduped-capabilities.yaml",
                     "nist-coverage.yaml", "attack-exposure.yaml", "apd-coverage-matrix.yaml"):
        path = run_dir / "40-synthesis" / filename
        if not path.is_file() or filename not in recorded:
            continue
        _doc, current = _yaml_with_hash(path)
        if current != recorded[filename]:
            result.drift.append({"file": filename, "manifest_hash": recorded[filename],
                                 "current_hash": current})
    if result.drift:
        _check(result, "source_hash_drift", False,
               f"stale: {[d['file'] for d in result.drift]}")


def _write(run_dir: Path, result: AuditResult) -> None:
    synth = run_dir / "40-synthesis"
    synth.mkdir(parents=True, exist_ok=True)
    doc = {
        "schema_version": 1, "generated_by": "apd-gauntlet", "status": result.status,
        "checks": result.checks, "counts": result.counts, "drift": result.drift,
    }
    (synth / "report-audit.yaml").write_text(yaml.safe_dump(doc, sort_keys=False), encoding="utf-8")
```

- [ ] **Step 4: Register the CLI command**

In `tools/apd_gauntlet/cli.py`, add after `rollup_cmd`:

```python
@main.command("audit-report")
@click.argument("run_dir", type=click.Path(exists=True, file_okay=False, path_type=Path))
def audit_report_cmd(run_dir: Path) -> None:
    """5g: structurally cross-check data.js against the authoritative YAMLs."""
    from .synthesis.audit import audit_report

    result = audit_report(run_dir)
    failed = [c["name"] for c in result.checks if c["status"] == "fail"]
    click.echo(f"audit-report: {result.status} ({len(result.checks)} checks, {len(failed)} failed)")
    for name in failed:
        click.echo(f"  FAIL: {name}", err=True)
    if result.status == "fail":
        raise SystemExit(1)
```

(Exit 1 on FAIL mirrors `validate`'s `SystemExit(0 if clean else 1)` so the workflow gate branches on exit code.)

- [ ] **Step 5: Run test to verify it passes**

Run: `python3 -m pytest tests/test_cli_audit_report.py -v`
Expected: PASS (5 passed). The example's checked-in `report-html/data.js` is consistent with its YAMLs (the committed golden was built from them), so the unmodified audit passes; the corruption tests flip `status` to `fail` and `exit_code` to 1. Note: the recompute-drift check requires the precompiled bundle ONLY for `build_report`, not for `load_run`/`build_apd_data`, so this test does NOT need a bundle-presence skip.

- [ ] **Step 6: Commit**

```bash
git add tools/apd_gauntlet/synthesis/audit.py tools/apd_gauntlet/cli.py tests/test_cli_audit_report.py
git commit -m "feat(synthesis): audit-report command (data.js<->YAML structural cross-check, exit 1 on fail)"
```

---

## Task 8: End-to-end equivalence regression vs the example golden

Prove the decomposed Python pipeline (`apply-clusters` → `rollup`) reproduces outputs equivalent to the committed example golden, using a NORMALIZED-CONTENT comparator (parse + project), NOT a byte diff. A hand-built `cluster-decisions.yaml` fixture drives the one merge in the example (the merged audit-log record from the REAL `nonrep-62124087` + `immut-e09e4945` source findings).

The example `expected/` tree is a COMPLETE run (all tier source files present), and the two merge sources `nonrep-62124087` + `immut-e09e4945` ALREADY EXIST in `30-auditability/non_repudiation.findings.yaml` and `30-auditability/immutability.findings.yaml`. So there is NO need to fabricate or "un-merge" source findings (the dropped `_reconstruct_source_corpus` approach double-counted ids and invented synthetic tier files). Instead the test: copies `expected/` to a temp run, DELETES the golden `40-synthesis/deduped-findings.yaml` (so apply-clusters rebuilds it from the real tier corpus), supplies the `cluster-decisions.yaml` fixture pointing `_members` at the two REAL source ids, runs `apply-clusters` over that real corpus, then projects the produced merged record + a NIST projection and compares to the golden.

EQUIVALENCE SCOPE (grounded, see I1 + the merged-id note below): the test pins the merge SEMANTICS — `merged_from` (sorted), `severity: critical`, the NIST union (the golden YAML stores it in natural order `["AU-9", "AU-9(2)", "AU-9(3)", "AU-10"]`; the deterministic `sorted()` union the test pins is `["AU-10", "AU-9", "AU-9(2)", "AU-9(3)"]` — the golden-vs-produced check re-sorts both sides), which is exactly the union of the two real sources' control mappings, matching the golden, and the `lens_perspectives` keys — and the nist-coverage finding/capability/posture projection. It does NOT pin the exact golden id `merged-4dd83f6a`: that id is `sha8(merged_title|first_evidence_locator)`, and the golden's first-evidence locator (`§5.2 paragraph 2`, from `nonrep-62124087`) reflects the synthesizer's member-ORDER-dependent evidence concatenation, which is not a deterministic equivalence target. The matrix is excluded from the projection per I1.

> **PRECONDITION (I6):** these tests `shutil.copytree(EXAMPLE, ...)`; the golden `report-html/` directory under `expected/40-synthesis/` must be committed (see Task 7's precondition) so a clean checkout / CI has it.

**Files:**
- Create: `tests/fixtures/cluster_decisions/example-cluster-decisions.yaml`
- Test: `tests/test_synthesis_equivalence.py`

- [ ] **Step 1: Build the cluster-decisions fixture**

Create `tests/fixtures/cluster_decisions/example-cluster-decisions.yaml` (the adjudicator output that, applied to the REAL source corpus already in the example's `30-auditability/` tier files, reproduces the example golden's merged audit-log record). The `merged_*` prose is copied verbatim from the example golden's merged record (`deduped-findings.yaml`, the `merged-4dd83f6a` block) and `_members` points at the two REAL source ids that already exist in the tier files:

```yaml
schema_version: 1
generated_by: apd-cluster-adjudicator
decisions:
  - group_id: cluster-cand-0001
    disposition: merge
    merged_title: "Audit log is unsigned and stored in a mutable table with no WORM enforcement"
    merged_summary: "The audit_log table lacks both cryptographic signing and storage-layer immutability, meaning records can be altered or deleted by privileged users without detection."
    merged_detail: "Non-Repudiation and Immutability agents both identified this risk from complementary angles. The Non-Repudiation lens focuses on the inability to prove audit entries were not tampered with after the fact. The Immutability lens focuses on the absence of storage-layer WORM protection that would physically prevent modification. Together, these gaps mean the audit log cannot serve as reliable evidence in a HIPAA breach investigation or regulatory audit."
    merged_recommendation:
      posture: required
      summary: "Implement HMAC signing on all audit entries and migrate to WORM-protected storage."
      detail: "Sign each audit entry with a KMS-derived HMAC at write time. Migrate audit log storage to S3 with Object Lock in Compliance mode. Remove DBA-level DELETE permissions on the audit_log table as an interim control. Verify integrity on a scheduled basis via batch HMAC verification."
    lens_perspectives:
      non_repudiation:
        summary: "Unsigned audit entries cannot prove non-tampering."
        detail: "Without HMAC or digital signatures on audit entries, there is no cryptographic proof that a log record has not been modified after the fact. An insider can alter records to cover unauthorized PHI access."
      immutability:
        summary: "No storage-layer write-once protection prevents record deletion."
        detail: "Application-level append-only discipline can be bypassed by any user with direct database access. WORM enforcement at the storage layer would prevent even DBAs from altering audit records."
    chosen_severity: critical
    severity_rationale: "Synthesizer elevates to critical because the combination of unsigned entries and mutable storage means the audit log cannot serve as evidence in HIPAA breach investigations, triggering regulatory breach-notification exposure beyond what either agent assessed in isolation."
_members:
  cluster-cand-0001: ["nonrep-62124087", "immut-e09e4945"]
```

- [ ] **Step 2: Write the equivalence test**

Create `tests/test_synthesis_equivalence.py`:

```python
"""Decomposed pipeline reproduces the example golden (normalized-content comparison).

Byte-equivalence is impossible (the golden carries author comment banners and a
fixed ordering); instead we project both sides to stable semantic keys and diff.

The merge sources nonrep-62124087 + immut-e09e4945 ALREADY EXIST in the example
tier files (30-auditability/{non_repudiation,immutability}.findings.yaml), so we
re-merge the REAL records — no synthetic un-merge, no double-counted ids. We do
NOT pin the exact golden id merged-4dd83f6a (its sha8 depends on the synthesizer's
member-order-dependent first-evidence locator, which is not a deterministic
equivalence target). The matrix is excluded from the projection per I1.
"""
from __future__ import annotations

import pathlib
import shutil

import yaml
from apd_gauntlet.synthesis.apply import apply_clusters
from apd_gauntlet.synthesis.rollup import build_rollups

REPO = pathlib.Path(__file__).parent.parent
EXAMPLE = REPO / "examples" / "apd-20260601-claim-event-bus" / "expected"
DECISIONS_FIXTURE = REPO / "tests" / "fixtures" / "cluster_decisions" / "example-cluster-decisions.yaml"


def _merged_record(findings):
    """The single synthesizer-built merge in the produced findings."""
    merged = [f for f in findings if f.get("agent") == "synthesizer"]
    assert len(merged) == 1, [f.get("id") for f in merged]
    return merged[0]


def _project_nist(controls):
    return {c["id"]: {"finding_ids": sorted(c["finding_ids"]),
                      "capability_ids": sorted(c["capability_ids"]), "posture": c["posture"]}
            for c in controls}


def test_apply_clusters_reproduces_merged_record_semantics(tmp_path):
    run = tmp_path / "run"
    shutil.copytree(EXAMPLE, run)
    # Drop the golden deduped output so apply-clusters rebuilds it from the REAL
    # tier corpus (the two merge sources are already in 30-auditability/).
    (run / "40-synthesis" / "deduped-findings.yaml").unlink()
    (run / "40-synthesis" / "deduped-capabilities.yaml").unlink()
    shutil.copy2(DECISIONS_FIXTURE, run / "40-synthesis" / "cluster-decisions.yaml")
    result = apply_clusters(run)

    # Key the merged record by agent=='synthesizer' (NOT the exact sha8 id).
    m = _merged_record(result.findings)
    # merged_from is the sorted real source ids.
    assert m["merged_from"] == sorted(["nonrep-62124087", "immut-e09e4945"])
    # Adjudicator chosen_severity wins.
    assert m["severity"] == "critical"
    # Sorted union of the two REAL sources' NIST controls. Python's sorted() yields
    # ["AU-10", "AU-9", "AU-9(2)", "AU-9(3)"] (lexical: '1' < '9' at position 3) — matching
    # Task 5's assertion. The golden YAML stores the natural order ["AU-9","AU-9(2)","AU-9(3)","AU-10"];
    # the golden-vs-produced compare on line 3074 re-sorts both sides, so it is order-agnostic.
    assert sorted(m["control_mappings"]["nist_800_53r5"]) == ["AU-10", "AU-9", "AU-9(2)", "AU-9(3)"]
    assert set(m["lens_perspectives"].keys()) == {"non_repudiation", "immutability"}
    # The two sources no longer appear as standalone findings.
    fids = {f["id"] for f in result.findings}
    assert "nonrep-62124087" not in fids and "immut-e09e4945" not in fids
    # The golden merged record carries the SAME merged_from + severity + NIST union.
    golden = yaml.safe_load((EXAMPLE / "40-synthesis" / "deduped-findings.yaml").read_text())["finding"]
    gm = next(f for f in golden if f.get("agent") == "synthesizer")
    assert sorted(gm["merged_from"]) == m["merged_from"]
    assert gm["severity"] == m["severity"]
    assert sorted(gm["control_mappings"]["nist_800_53r5"]) == sorted(m["control_mappings"]["nist_800_53r5"])


def test_rollup_reproduces_nist_projection(tmp_path):
    run = tmp_path / "run"
    shutil.copytree(EXAMPLE, run)
    build_rollups(run)  # rolls up directly over the committed deduped golden + apath
    produced = _project_nist(
        yaml.safe_load((run / "40-synthesis" / "nist-coverage.yaml").read_text())["controls"])
    golden = _project_nist(
        yaml.safe_load((EXAMPLE / "40-synthesis" / "nist-coverage.yaml").read_text())["controls"])
    # Every golden control's finding/capability set + posture is reproduced.
    for cid, proj in golden.items():
        assert cid in produced, f"rollup dropped control {cid}"
        assert produced[cid] == proj, f"control {cid} projection differs"
```

- [ ] **Step 3: Run test to verify it fails (if a projection is off)**

Run: `python3 -m pytest tests/test_synthesis_equivalence.py -v`
Expected (first run): may FAIL on `test_rollup_reproduces_nist_projection` if a control's finding/capability id set differs — the projection deliberately ignores `title` and `family` (those depend on the NIST-title lookup source) and compares only `finding_ids` / `capability_ids` / `posture`. A failing id set is a real rollup defect to fix in `rollup.py` (e.g. apath findings not folded into the corpus, or a NIST normalization mismatch); fix and re-run. The `apply-clusters` semantics test should pass given Task 5 is correct (the NIST union is recomputed from the two real sources, which exactly equals the golden's union).

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_synthesis_equivalence.py -v`
Expected: PASS (2 passed) — the decomposed pipeline reproduces the example golden's merged-record semantics and NIST coverage projection.

- [ ] **Step 5: Commit**

```bash
git add tests/fixtures/cluster_decisions/example-cluster-decisions.yaml tests/test_synthesis_equivalence.py
git commit -m "test(synthesis): equivalence regression vs example golden (re-merge real sources + nist projection)"
```

---

## Task 9: Three new LLM agents

Each agent `.md` MUST end with a trailing newline (MD047) and MUST include the `## Final message (receipt only)` section (the Plan-1 lint rule flags any non-exempt agent lacking it). None are specialists, so none need `## Output bounding`. Each references `schemas/agent-receipt.schema.json`.

**Files:**
- Create: `.claude/agents/apd-cluster-adjudicator.md`, `.claude/agents/apd-report-writer.md`, `.claude/agents/apd-report-auditor.md`
- Test: `tests/test_new_agents_receipt.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_new_agents_receipt.py`:

```python
"""The three new LLM agents carry the receipt contract and lint clean."""
from __future__ import annotations

import pathlib

from apd_gauntlet.lint_agents import RECEIPT_MARKER, lint_agent_file

REPO = pathlib.Path(__file__).parent.parent
AGENTS = REPO / ".claude" / "agents"

NEW_AGENTS = ["apd-cluster-adjudicator", "apd-report-writer", "apd-report-auditor"]


def test_new_agents_carry_receipt_contract():
    for name in NEW_AGENTS:
        text = (AGENTS / f"{name}.md").read_text()
        assert RECEIPT_MARKER in text, f"{name}.md missing receipt contract"
        assert "schemas/agent-receipt.schema.json" in text, f"{name}.md must reference the receipt schema"


def test_new_agents_end_with_trailing_newline():
    for name in NEW_AGENTS:
        text = (AGENTS / f"{name}.md").read_text()
        assert text.endswith("\n") and not text.endswith("\n\n\n"), f"{name}.md must end with one trailing newline (MD047)"


def test_new_agents_lint_clean():
    for name in NEW_AGENTS:
        errors = lint_agent_file(AGENTS / f"{name}.md", REPO)
        assert errors == [], f"{name}.md lint errors: {errors}"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_new_agents_receipt.py -v`
Expected: FAIL — the three agent files do not exist (`FileNotFoundError`).

- [ ] **Step 3: Create `apd-cluster-adjudicator.md`**

Create `.claude/agents/apd-cluster-adjudicator.md` (the receipt block is verbatim from Plan 1's appended section so the lint marker matches; file ends with exactly one newline):

```markdown
---
name: apd-cluster-adjudicator
description: |
  5b judgment-only agent. Reads ONLY 40-synthesis/cluster-candidates.yaml (the
  candidate groups + minimal per-record fields the cluster-candidates command
  extracted — kilobytes, never the 18 raw files). For each candidate group,
  decides disposition merge|link|separate (bias to link on ambiguity). For
  merges, authors the rewritten merged summary/detail/recommendation and the
  per-lens lens_perspectives narrative, classifies finding-vs-capability
  contradictions (compatible|contradicted|stale), and supplies chosen_severity
  + rationale when elevating above the cluster max. Emits
  40-synthesis/cluster-decisions.yaml. Does NOT compute merged ids, NIST/ATT&CK
  unions, or write the deduped files — those are the apply-clusters command.
tools:
  - Read
  - Write
model: opus
---

# apd-cluster-adjudicator

## Required reading

- `.claude/skills/apd-framework/SKILL.md`
- `.claude/skills/apd-finding-schema/SKILL.md` (merge-vs-link rule, lens_perspectives semantics)
- `.claude/skills/apd-control-mappings/SKILL.md` (union-of-mappings discipline)

## Job

Judgment only. Fresh, small context. Your ONLY corpus input is
`40-synthesis/cluster-candidates.yaml`. For each `group`:

- **Decide disposition.** `merge` when the records describe the same root cause
  through different lenses; `link` when they share evidence but are distinct;
  `separate` when the mechanical signal was spurious. **Bias to `link` on
  ambiguity** — a link is reversible, a merge is not.
- **For `merge`:** author `merged_title`, `merged_summary`, `merged_detail`,
  and a combined `merged_recommendation` (reconcile conflicting remediation —
  surface the conflict if paths diverge, integrate if they reinforce). Preserve
  each source record's original summary/detail under `lens_perspectives` keyed
  by APD goal. If the combined severity warrants elevation ABOVE the cluster
  max, supply `chosen_severity` + `severity_rationale`.
- **For `link`:** emit `links: [{from, to}]` so apply-clusters writes reciprocal
  `cross_references`.
- **Contradictions.** Classify each finding-vs-capability conflict as
  `compatible` | `contradicted` | `stale`, and write `evidence_comparison` +
  `recommended_resolution` prose. The mechanical apply-clusters command writes
  the contradictions.yaml records, applies any stale-maturity downgrade, and
  logs it to rejected-records.yaml — you only judge and write prose.

## Inputs

- `40-synthesis/cluster-candidates.yaml` (the ONLY corpus input)

## Outputs

- `40-synthesis/cluster-decisions.yaml` (validated against
  `schemas/cluster-decisions.schema.json`). Include a TOP-LEVEL `_members` map
  keyed by `group_id` whose value is the array of that group's member record
  ids (copied verbatim from `cluster-candidates.yaml`), e.g.
  `_members: {cluster-cand-0001: [nonrep-62124087, immut-e09e4945]}`. The
  schema declares `_members` as a first-class property, so a doc carrying it
  passes `validate --schema-only`; apply-clusters reads it to resolve which
  source records each decision merges/links.

## Final message (receipt only)

Your final message back to the run driver is a **receipt, not prose**. Do NOT
restate decisions or merged narratives — those live in the file you wrote.
Return only a compact object conforming to `schemas/agent-receipt.schema.json`:

```yaml
agent: apd-cluster-adjudicator
status: ok | blocked | error
outputs:
  - path: 40-synthesis/cluster-decisions.yaml
    schema_valid: true
counts:
  blocked: 0
errors: []   # populate only on status: error
```

The driver retains only this receipt; keeping it small is what keeps the run
within context.
```

- [ ] **Step 4: Create `apd-report-writer.md`**

Create `.claude/agents/apd-report-writer.md`:

```markdown
---
name: apd-report-writer
description: |
  5e judgment-only agent. Fresh context. Reads 40-synthesis/deduped-findings.yaml
  (for the §4 Findings narrative + headline ranking) plus the COMPACT rollups
  (nist-coverage, attack-exposure, apd-coverage-matrix, cwe/owasp/d3fend-coverage)
  and the contradictions/severity-disagreements annex files. Produces the
  editorial prose: exec_summary.paragraphs, headline_findings ranking (<=10),
  strengths caveats, next_steps, posture_summary — the report-data.schema.json
  contract — plus the human-readable advisory-report.md. report-data.yaml is the
  one editorial output with full existing schema + cross-ref validation coverage.
tools:
  - Read
  - Write
model: opus
---

# apd-report-writer

## Required reading

- `.claude/skills/apd-framework/SKILL.md`
- `templates/report-data.template.yaml`
- `templates/advisory-report.template.md`

## Job

Judgment only. Fresh context. Produce the editorial layer the deterministic
rollups cannot: `exec_summary.paragraphs`, the `headline_findings` ranking
(<=10 by materiality), `strengths` caveats, `next_steps`, and `posture_summary`
— exactly the `schemas/report-data.schema.json` contract. Also write the
10-section `advisory-report.md` narrative. Your `report-data.yaml` is validated
both by schema and by `validate.py`'s `_validate_report_data_cross_refs`
(headline_findings[].id / strengths[].id / next_steps[].refs must match real
finding/capability ids). The output is NOT a byte-equivalence target — it is
editorial.

## Inputs

- `40-synthesis/deduped-findings.yaml`
- `40-synthesis/nist-coverage.yaml`, `attack-exposure.yaml`,
  `apd-coverage-matrix.yaml`, and `cwe/owasp/d3fend-coverage.yaml` (the compact
  rollups — already aggregated, NOT raw specialist files)
- `40-synthesis/contradictions.yaml`, `severity-disagreements.yaml` (annex inputs)
- `templates/report-data.template.yaml`, `templates/advisory-report.template.md`

## Outputs

- `40-synthesis/advisory-report.md` (10-section advisory narrative)
- `40-synthesis/report-data.yaml` (validated against
  `schemas/report-data.schema.json`)

## Final message (receipt only)

Your final message back to the run driver is a **receipt, not prose**. Do NOT
restate the report — it lives in the files you wrote. Return only a compact
object conforming to `schemas/agent-receipt.schema.json`:

```yaml
agent: apd-report-writer
status: ok | blocked | error
outputs:
  - path: 40-synthesis/report-data.yaml
    schema_valid: true
  - path: 40-synthesis/advisory-report.md
    schema_valid: true
counts:
  blocked: 0
errors: []   # populate only on status: error
```

The driver retains only this receipt; keeping it small is what keeps the run
within context.
```

- [ ] **Step 5: Create `apd-report-auditor.md`**

Create `.claude/agents/apd-report-auditor.md`:

```markdown
---
name: apd-report-auditor
description: |
  5g judgment-only agent. Reads ONLY the compact 40-synthesis/report-audit.yaml
  (counts/coverage/drift summary emitted by the audit-report command, NOT the
  full data.js) plus the rendered advisory-report.md / report-data.yaml editorial
  blocks. Judges semantic faithfulness: no misleading severity framing, no
  material omission, no invented content untraceable to a finding/capability. On
  fail, it returns a compact critique; the workflow (Plan 3) may feed that
  critique back to the report-writer/build-report phases for a bounded number of
  rebuilds. This agent owns the typed gate SIGNAL, not the loop control.
tools:
  - Read
  - Write
model: opus
---

# apd-report-auditor

## Required reading

- `.claude/skills/apd-framework/SKILL.md`
- `.claude/skills/apd-evidence-discipline/SKILL.md`

## Job

Judgment only. Small context. Read the COMPACT structural audit
(`40-synthesis/report-audit.yaml`) — the Python audit-report command already did
the mechanical ID-coverage / count-parity / drift checks; you do NOT re-read
data.js. Then read the rendered prose (`advisory-report.md` + the editorial
blocks of `report-data.yaml`) and judge semantic faithfulness:

- **No misleading severity framing** — the prose must not soften or inflate a
  finding's severity relative to its record.
- **No material omission** — a critical/high finding the structural audit counted
  must be represented in the narrative.
- **No invented content** — every claim must be traceable to a finding or
  capability id.

If the structural audit `status: fail` OR you find a faithfulness defect, emit a
compact critique and a typed gate signal. The workflow (Plan 3) may feed this
critique back to the report-writer/build-report phases for a bounded number of
rebuilds; once that bound is reached, remaining discrepancies are surfaced
non-blocking so the run still completes. Loop control lives in the workflow, not
in this agent — Plan 2 provides only the signal.

## Inputs

- `40-synthesis/report-audit.yaml` (the compact structural audit)
- `40-synthesis/advisory-report.md` + `report-data.yaml` editorial blocks

## Outputs

- Faithfulness findings appended to `40-synthesis/report-audit.yaml` under an
  `auditor_findings` block, or returned to the workflow as the gate signal.

## Final message (receipt only)

Your final message back to the run driver is a **receipt, not prose**. Do NOT
restate the critique narrative — return only the gate signal. Return a compact
object conforming to `schemas/agent-receipt.schema.json`:

```yaml
agent: apd-report-auditor
status: ok | blocked | error
outputs:
  - path: 40-synthesis/report-audit.yaml
    schema_valid: true
counts:
  blocked: 0
errors: []   # populate only on status: error
```

The driver retains only this receipt; keeping it small is what keeps the run
within context.
```

- [ ] **Step 6: Run test + lint-agents to verify they pass**

Run: `python3 -m pytest tests/test_new_agents_receipt.py tests/test_lint_agents_receipt.py tests/test_lint_agents.py -v`
Expected: PASS (all). The three new agents carry the receipt marker and reference the receipt schema; they are not in `SPECIALIST_NAMES` so the bounding check does not apply.

Run: `apd-gauntlet lint-agents`
Expected: `Lint clean: 19 agents checked.` (16 existing + 3 new). Note: the new agents' `## Required reading` references (`.claude/skills/...`) must resolve — confirm each referenced skill file exists (they were listed in the system skill registry: `apd-framework`, `apd-finding-schema`, `apd-control-mappings`, `apd-evidence-discipline`). The `templates/...` references in `apd-report-writer.md` do NOT start with `.claude/`, so the lint's path check skips them (it only checks `.claude/`-prefixed refs).

- [ ] **Step 7: Commit**

```bash
git add .claude/agents/apd-cluster-adjudicator.md .claude/agents/apd-report-writer.md .claude/agents/apd-report-auditor.md tests/test_new_agents_receipt.py
git commit -m "feat(agents): apd-cluster-adjudicator + apd-report-writer + apd-report-auditor (5b/5e/5g)"
```

---

## Task 10: Re-wire `build-report` out of the synthesizer

Remove the trailing `build-report` trigger from `apd-synthesizer.md` (the synthesizer stays a maintained fallback but no longer triggers the HTML build). NO code change to `report/`. The workflow runner (Plan 3) invokes `apd-gauntlet build-report <run_dir>` as the standalone Bash phase 5f; this task only neuters the synthesizer's `## Trailing HTML build` section and documents that the report audit loop (Plan 3) will gate it.

**Files:**
- Modify: `.claude/agents/apd-synthesizer.md`
- Test: `tests/test_synthesizer_rewiring.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_synthesizer_rewiring.py`:

```python
"""The synthesizer no longer triggers build-report; the build is a workflow phase (Plan 3)."""
from __future__ import annotations

import pathlib

REPO = pathlib.Path(__file__).parent.parent
SYNTH = REPO / ".claude" / "agents" / "apd-synthesizer.md"


def test_synthesizer_does_not_trigger_build_report():
    text = SYNTH.read_text()
    assert "## Trailing HTML build" not in text, "synthesizer must not own the trailing HTML build"
    # The synthesizer must not instruct invoking build-report itself anymore.
    assert "apd-gauntlet build-report" not in text


def test_synthesizer_documents_build_is_a_workflow_phase():
    text = SYNTH.read_text()
    # A short note explaining the re-wiring (so a reader knows where the build went).
    assert "build-report" in text  # referenced in prose, not as a trigger
    assert "workflow" in text.lower()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_synthesizer_rewiring.py -v`
Expected: FAIL — `test_synthesizer_does_not_trigger_build_report` fails because the `## Trailing HTML build` section + `apd-gauntlet build-report` invocation are still present.

- [ ] **Step 3: Replace the `## Trailing HTML build` section**

In `.claude/agents/apd-synthesizer.md`, locate the `## Trailing HTML build` section (the heading plus its body that ends with "The HTML report is a derived view, not part of the authoritative deliverable."). Replace the ENTIRE section (heading + body + fenced bash block) with this note (which keeps the words `build-report` and `workflow` so the second test passes, and drops the trigger):

```markdown
## HTML report (re-wired to the workflow)

The HTML report build is no longer triggered here. As of the token-resilience
decomposition, the workflow runner invokes `apd-gauntlet build-report <run_dir>`
as a standalone phase AFTER `report-data.yaml` is written, and the report audit
loop gates it. When this synthesizer runs as the fallback path, it stops after
writing the 40-synthesis YAMLs (including `report-data.yaml`); the workflow owns
the report build and audit.
```

Ensure the file still ends with exactly one trailing newline.

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_synthesizer_rewiring.py -v`
Expected: PASS (2 passed).

- [ ] **Step 5: Confirm the synthesizer still lints clean + example still validates**

Run: `apd-gauntlet lint-agents`
Expected: `Lint clean: 19 agents checked.` (the synthesizer stays in `RECEIPT_EXEMPT`, so removing the section does not trip the receipt rule).

Run: `python3 -m pytest tests/test_examples.py -v`
Expected: PASS — the example `expected/` tree is unchanged; `apd-gauntlet validate` over it still exits 0.

- [ ] **Step 6: Commit**

```bash
git add .claude/agents/apd-synthesizer.md tests/test_synthesizer_rewiring.py
git commit -m "refactor(agents): re-wire build-report out of synthesizer into a workflow phase"
```

---

## Task 11: Full regression + lint/type/markdown gate

**Files:** none (verification only)

> **PRECONDITION (I6):** confirm the golden `report-html/` directory is committed (Task 7's precondition) — the Step 5 smoke `cp -r examples/.../expected /tmp/apd-smoke` and the audit/equivalence suites depend on `report-html/{data.js,build-manifest.txt}`. Run `git status --short examples/apd-20260601-claim-event-bus/expected/40-synthesis/report-html/` and expect EMPTY output (no `??`) before this task.

- [ ] **Step 1: Run the whole suite**

Run: `python3 -m pytest -q`
Expected: PASS (all green; no regressions in validate, lint, schema, report, or the new synthesis suites). The bundle-gated report golden tests (`tests/integration/report/test_example_golden.py`) skip if the precompiled bundle is absent — that is unchanged by Plan 2.

- [ ] **Step 2: Lint + type check**

Run: `ruff check tools/ tests/ && mypy tools/apd_gauntlet`
Expected: clean (no new errors). If `mypy` flags the new dataclass return types, confirm `RollupResult` / `ApplyResult` / `CandidateResult` / `AuditResult` fields are annotated (they are, via `field(default_factory=...)`).

- [ ] **Step 3: Markdown lint on the new agent files**

Run: `npx markdownlint-cli2 ".claude/agents/apd-cluster-adjudicator.md" ".claude/agents/apd-report-writer.md" ".claude/agents/apd-report-auditor.md"`
Expected: clean — specifically MD047 (single trailing newline) passes, which the embedded ```yaml fences and headings do not violate. If the CI uses a different invocation, match the repo's existing markdownlint CI glob (check `.github/workflows/` for the exact command and run that instead).

- [ ] **Step 4: `apd-gauntlet lint-agents` end-to-end**

Run: `apd-gauntlet lint-agents`
Expected: `Lint clean: 19 agents checked.`

- [ ] **Step 5: Smoke-test the new CLI pipeline on the example run**

Run:
```bash
cp -r examples/apd-20260601-claim-event-bus/expected /tmp/apd-smoke
cp tests/fixtures/cluster_decisions/example-cluster-decisions.yaml /tmp/apd-smoke/40-synthesis/cluster-decisions.yaml
apd-gauntlet cluster-candidates /tmp/apd-smoke
apd-gauntlet rollup /tmp/apd-smoke
apd-gauntlet audit-report /tmp/apd-smoke
apd-gauntlet validate /tmp/apd-smoke --schema-only --errors-only
```

Expected: `cluster-candidates` / `rollup` / `audit-report` each echo a one-line summary and exit 0; the final `validate --schema-only` exits 0 with no output, proving the newly-emitted `cluster-candidates.yaml` + rollups validate against the wired-in schemas. (`apply-clusters` is exercised in the Task 8 equivalence test, which re-merges the REAL source findings; running it on the example's already-merged deduped output is not part of the smoke.)

- [ ] **Step 6: Final commit (if any verification fixups were needed)**

```bash
git add -A
git commit -m "test: token-resilience Plan 2 regression + lint/type/markdown gate green"
```

---

## Self-Review

**Spec coverage (vs design §7 decomposition table + §7.1 responsibilities):**

| Design step | Artifact / behavior | Task |
|---|---|---|
| 5a `cluster-candidates` (Python) | 3 mechanical signals + union-find + bounding → `cluster-candidates.yaml` | Task 4 ✓ |
| 5b `apd-cluster-adjudicator` (LLM) | disposition + merged prose + contradiction classification → `cluster-decisions.yaml` | Task 9 ✓ (agent); Task 3 ✓ (schema) |
| 5c `apply-clusters` (Python) | merge/link/separate, sha8 id, union mappings, conservative maturity → deduped + sev-dis + rejected | Task 5 ✓ |
| 5d `rollup` (Python) | canonical nist/attack-exposure/matrix + cwe/owasp/d3fend when declared | Task 6 ✓ |
| 5e `apd-report-writer` (LLM) | editorial `report-data.yaml` + `advisory-report.md` | Task 9 ✓ (agent; report-data.schema.json already exists, recon area 1) |
| 5f `build-report` (Python, EXISTING) | re-wired out of synthesizer into a workflow phase; NO `report/` code change | Task 10 ✓ |
| 5g `audit-report` (Python) | data.js↔YAML structural cross-check → `report-audit.yaml`; exit 1 on fail. Severity parity recomputes from deduped+apath (NOT `summarize`, which omits apath — M3); maturity-count parity out of scope | Task 7 ✓ |
| 5g `apd-report-auditor` (LLM) | semantic faithfulness gate | Task 9 ✓ (agent); Task 3 ✓ (schema) |
| New schemas (4) | cluster-candidates / cluster-decisions (with `_members` first-class — C3/C6) / rejected-records (incl. `stale_capability_downgrade`) / report-audit | Task 3 ✓ |
| Validator-wiring gap fix (6 filenames wired) | severity-disagreements + contradictions wired into SYNTHESIS_ROLLUPS (with optional `notes` for legacy-run compat); nist/attack-exposure/coverage-matrix `*-doc` wrapper schemas exist but global wiring deferred to Plan 3 (legacy runs/ predate array format; rollup command validates its own output per-command in Task 6) | Task 3 ✓ (+ post-Task-3 fix) |
| `contradictions.yaml` producer (C5/I3) | apply-clusters emits `{contradictions:[...]}` (contra-sha8, classification stripped) matching the existing schema + cross-ref | Task 5 ✓ |
| Stale-capability downgrade (I4) | `stale` contradiction → maturity one notch down via `_MATURITY_RANK` + `stale_capability_downgrade` rejected row | Task 5 ✓ |
| Coverage-name lookups (C4/I2) | attack/owasp/d3fend names from bundled catalogs (never raw ids; attack `name` minLength:3) | Task 6 ✓ |
| Shared helper extraction (no import cycle) | `coverage_logic.py` ← from `transform.py`; transform delegates the 3 NIST leaf helpers only (M1) | Task 2 ✓ |
| §11 equivalence regression (normalized) | apply-clusters merge semantics + rollup nist projection vs example golden (matrix labels + editorial prose explicitly NOT a target — I1) | Task 8 ✓ |
| §11 `pytest` + `validate` stay clean | full gate | Task 11 ✓ |
| Golden `report-html/` fixture committed (I6) | untracked `data.js`/`build-manifest.txt` git-added before audit/equivalence tests run | Task 7 precondition ✓ |
| Lint/topology fixtures | new agents covered by receipt lint; `lint-agents` → 19 agents (16 existing + 3 new) | Task 9, Task 10 ✓ |

**Out of Plan-2 scope (correctly deferred to Plan 3):** the workflow runner (`.claude/workflows/apd-gauntlet.js`), the gate + auto-remediate LOOP wiring, the synthesizer FALLBACK dispatch (Plan 2 only provides the typed signals: `AdjudicationMissing` → exit 2; `audit-report` fail → exit 1), `apd-orchestrator` deprecation shim, and any deduped-* per-record validation path (the `*.findings.yaml`/`*.capabilities.yaml` glob does NOT match `deduped-*` — confirmed by `fnmatch` — and adding a path is YAGNI for Plan 2).

**Placeholder scan:** No "TBD / TODO / handle edge cases / similar to Task N". Every code step shows the actual code; every command shows expected output. The one pre-existing `# TODO` left untouched is inside `cli._write_blocked_finding` (Plan-1 code, not modified here). Task 8 Step 3 explicitly anticipates a possible first-run rollup-projection failure and states the exact remediation (it is a debugging note, not a placeholder — the passing path is Step 4).

**Type/name consistency (verified against the real repo):**

- Entry functions match the package-layout contract: `load_corpus(run_dir, *, include_attack_path=False)`, `build_candidates(run_dir, *, max_group_size=8) -> CandidateResult`, `apply_clusters(run_dir) -> ApplyResult` (+ `AdjudicationMissing`), `build_rollups(run_dir) -> RollupResult`, `audit_report(run_dir) -> AuditResult` (+ `parse_data_js`).
- `coverage_logic` exports `GOAL_SHORT`, `normalize_nist_id`, `normalize_nist_ids`, `nist_family_of`, `posture(*, has_findings, has_caps)`, `extract_ids_from_mapping`, `build_cap_controls_index`, `build_cap_attack_index` — referenced identically in `cluster.py` / `rollup.py` / the transform delegation. `coverage_logic.posture` returns the YAML enum `gapped_and_covered`; `transform._posture` keeps the data.js short `both` (documented divergence; the identity test only pins the NIST-id leaf helpers).
- CLI commands mirror `analyze-attack-paths`: `click.Path(exists=True, file_okay=False, path_type=Path)` run-dir arg, lazy imports inside the body, `synth.mkdir(parents=True, exist_ok=True)`, `yaml.safe_dump(doc, sort_keys=False)`, one-line `click.echo` summary. Exit codes: `cluster-candidates`/`rollup` default 0; `apply-clusters` raises `SystemExit(2)` on `AdjudicationMissing`; `audit-report` raises `SystemExit(1)` on audit FAIL.
- Root keys match the example golden + loader expectations exactly: `finding:` / `capability:` (singular), `controls:` / `techniques:` / `components:`, `contradictions:` / `severity_disagreements:` (plural), `rejected:`. `generated_by`: `apd-gauntlet` (cluster-candidates, report-audit), `apd-cluster-adjudicator` (cluster-decisions), `synthesizer` (rejected/cwe/owasp/d3fend — satisfies the hardcoded enums in `cwe/owasp/d3fend-coverage.schema.json`). Deduped findings/caps emit NO `generated_by` and NO `generated_at` (bare list, reproducible).
- Merged-id rule `merged-<sha8(title + "|" + first_evidence_locator)>` matches the `apd-finding-schema` skill. The exact golden id `merged-4dd83f6a` is reproduced only when `first_evidence_locator == "§5.2 paragraph 2"` (nonrep's locator, by member order) — the synthesizer's member-ORDER-dependent evidence concatenation; the Task 8 equivalence test therefore pins merge SEMANTICS (merged_from/severity/NIST-union/lens keys), NOT the literal id (verified: id-sorted first-locator yields a different sha8). Evidence field key is `artifact` (NOT `file`), per `finding.schema.json`.
- The on-disk `contradictions.yaml` row (`contra-<sha8(finding_id|capability_id)>` + the 6 prose fields, NO `classification`) matches the EXISTING `schemas/contradiction.schema.json` (required `id` pattern `^contra-[0-9a-f]{8}$`; assertion min-lengths supplied by the adjudicator) and passes `validate.run_cross_file_pass`'s contradiction cross-ref. `severity-disagreements.yaml` `rationale` satisfies the existing minLength-30; `agent_severities` carries the 2 merge-lens goals (minProperties 2).
- Schema `$id`s follow `https://github.com/illusconsulting/apd-gauntlet/schemas/<name>.schema.json` (every existing schema uses this; wrappers `$ref` the per-row schemas by full `$id`). All nine new schemas (4 new-artifact + 5 wrappers) are auto-meta-validated by `tests/test_meta_schemas.py`'s glob.
- All three new agent `.md` files contain the exact `## Final message (receipt only)` heading the Plan-1 lint rule (`RECEIPT_MARKER = "## Final message"`) requires, reference `schemas/agent-receipt.schema.json`, and end with one trailing newline (MD047). `apd-synthesizer` stays in `RECEIPT_EXEMPT`; the three new agents are NOT in `SPECIALIST_NAMES` (no bounding section required). `lint-agents` count goes 16 → 19.
- `contradictions.yaml` is PRODUCED by `apply-clusters` (C5/I3), wired into `validate.SYNTHESIS_ROLLUPS` via `contradictions-doc.schema.json` (I5), listed as an input by `apd-report-writer`, and cross-ref-validated by `validate.run_cross_file_pass` — no dangling reference remains. The on-disk `cluster-decisions.yaml` carries a first-class top-level `_members` map (C3/C6) so it passes `validate --schema-only`. (Cross-ref scope: `contradictions.yaml` `finding_id`/`capability_id` resolve against the per-tier `*.findings.yaml`/`*.capabilities.yaml` source records, which match the validator globs; a `merged-*` record lives only in `deduped-findings.yaml` — which does NOT match `*.findings.yaml` — so cross-ref resolution of a `merged-*` id against deduped output is deferred to Plan 3 alongside the deduped-glob wiring.)
