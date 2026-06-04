# Unified Metrics Model — Design Spec

- **Date:** 2026-06-04
- **Status:** Approved (brainstorming) — pending spec review. Revised after adversarial spec-verification (16-item punch-list folded in).
- **Author:** Jon King (with Claude)
- **Topic:** Single canonical metrics artifact (`40-synthesis/metrics.yaml`) consumed by the report-writer, transform, and audit; removal of the report summary block's parallel recomputation.

---

## 1. Problem statement

Running projects through the gauntlet repeatedly produces reports where the **finding counts in the §1 Executive Summary disagree with the Severity distribution** on the Overview scene. Investigation (codebase-memory graph trace of the report pipeline) found the report runs on a **two-track data model** that counts findings over **different universes** with **no reconciliation between them**.

### Track A — computed spine (deterministic)

- `summary_rollup()` ([transform.py:195](../../../tools/apd_gauntlet/report/transform.py#L195)) builds `data.summary` (`findings_total`, `bySeverity`, …) from `artifacts.deduped_findings + artifacts.attack_path_findings`.
- `findings_array()` ([transform.py:364](../../../tools/apd_gauntlet/report/transform.py#L364)) builds `data.findings` from the same union.
- These drive the Overview headline grid and the **Severity distribution** rail ([Overview.jsx](../../../report-template/screens/Overview.jsx) — `s.findings_total`, `s.bySeverity.*`).
- Verified by `audit_report()` ([audit.py:81](../../../tools/apd_gauntlet/synthesis/audit.py#L81)) via `count_parity_severity` / `count_parity_totals`, which **independently recompute** from `deduped_f + apath_f` (normalizing `informational→info` through `_INFORMATIONAL_TO_INFO`, audit.py:18).

### Track B — authored editorial layer (LLM prose)

- The `apd-report-writer` agent authors `exec_summary.paragraphs` into `report-data.yaml`.
- `build_apd_data()` ([transform.py:1797](../../../tools/apd_gauntlet/report/transform.py#L1797)) splices it into `data.exec_summary` (rendered as §1).
- `schemas/report-data.schema.json` treats paragraphs as **free strings** (`minLength: 40`) — no numeric structure.

### Root cause (two compounding mechanisms)

1. **Mismatched finding universes (the repeatable driver).** The report-writer authors counts from its own reading; the agent doc's Inputs list ([apd-report-writer.md:45-49](../../../.claude/agents/apd-report-writer.md)) names only `deduped-findings.yaml` and never mentions attack-path findings (which live in the separate `attack-path.findings.yaml`). The workflow *dispatch prompt* does hand it `attack-path.findings.yaml` ([apd-gauntlet.js](../../../.claude/workflows/apd-gauntlet.js) line ~568), creating doc/workflow drift, and even then the model must union and count by hand with no canonical anchor. When attack-path analysis activates (crown jewels declared — increasingly the common case), the prose count is systematically short by the apath finding count while the severity rail includes them.
2. **No reconciliation / loose coupling.** Even with no apath findings, prose numbers are hand-authored with nothing binding them to `data.summary`. The audit's `exec_summary_present` check ([audit.py:208-217](../../../tools/apd_gauntlet/synthesis/audit.py#L208)) is `klass="editorial"` and **presence-only** — no numeric cross-check. Any miscount ships silently.

The same prose-miscount risk applies to the **markdown** `advisory-report.md` (a second surface authored by the same agent — see §6.7), whose template explicitly prompts literal counts and which the audit never inspects.

### Secondary / latent divergences (also addressed)

- The headline-grid breakdown ([Overview.jsx:27-33](../../../report-template/screens/Overview.jsx#L27)) shows only `high · med · low` — omitting **critical** and **info** — so the sub-line never sums to `findings_total` when criticals exist. This alone makes the Overview *look* internally inconsistent.
- `summary_rollup` keys off **raw** `severity`; `findings_array`/§2 tier posture/§4 headline rows key off `_display_severity()`-normalized severity ([transform.py:328-334](../../../tools/apd_gauntlet/report/transform.py#L328)). Benign today (only `informational→info` is remapped) but fragile.
- §2 tier posture (`data.findings.filter(f => f.tier === tier)`) silently drops any finding whose `apd_tier` is missing/unrecognized, so it can sum below the rail (`summary_rollup` defaults missing tier to `trustworthiness`; `findings_array` does not default).

---

## 2. Goals / non-goals

### Goals

- **One canonical metrics object** for the **report summary block**, computed exactly once in synthesis, persisted as `40-synthesis/metrics.yaml`.
- **All report-summary consumers read it** (transform, audit, report-writer) — eliminate the report summary block's parallel recomputation.
- **Authoritative counts render structurally** from the canonical object on **both** report surfaces (HTML Overview and markdown `advisory-report.md`); exec-summary prose stays qualitative.
- **Fix the Overview breakdown omission** (show critical + info) and add a reconciling **count strip**.
- **CI guardrail**: audit asserts the rendered HTML report faithfully carries the canonical metrics (passthrough parity) plus cheap internal-consistency.

### Non-goals (YAGNI)

- **The `apd-gauntlet summarize` CLI (`summarize_run`, [summary.py:11-56](../../../tools/apd_gauntlet/summary.py#L11)) is deliberately NOT unified.** It is a *pre-dedup* progress counter that runs over per-lens `*.findings.yaml` (via `validate._iter_records`) **before** `metrics.yaml` exists; it serves a different role (early run triage) over a different universe. It is explicitly **not** the report summary block. (See §7.)
- Folding coverage totals (NIST/ATT&CK/CWE/OWASP/D3FEND/ATLAS) into `metrics.yaml` — they keep their own audited YAMLs and parity checks.
- Any prose-number-extraction gate (avoided by design — counts render structurally, not from prose).
- Backward-compatibility with runs that predate `metrics.yaml`. **No old-shape tolerance**: to refresh a report the user re-runs the full workflow and regenerates all artifacts.
- Unrelated refactors of `transform.py` beyond the touched functions.

---

## 3. Locked decisions

| # | Decision | Choice |
|---|----------|--------|
| 1 | Canonical home | New `40-synthesis/metrics.yaml` computed in `build_rollups()` (synthesis), loaded via `artifacts.metrics`. |
| 2 | Scope of metrics.yaml | The **full report `summary` block** (finding + capability counts, dispositions, tiers, cluster counts, contradictions, sev-disagreements). |
| 3 | Prose binding | Counts render **structurally** from `metrics.yaml` on both report surfaces; report-writer prose stays qualitative and is *given* the canonical numbers + apath findings. |
| 4 | Migration | `metrics.yaml` is **required**; old report-summary recompute paths **deleted**; all *tracked* fixtures **regenerated**; **no old-shape tolerance**. |
| 5 | Audit backstop | **(a) Pure passthrough** — audit checks `data.js.summary == metrics.yaml` + internal-consistency; correctness of the single function is guaranteed by its own unit tests. No parallel recompute. |
| 6 | Frontend | Count-strip + breakdown fix **included now**. |
| 7 | `summarize` CLI | **Carved out** as a non-goal (separate pre-dedup counter — §2). |
| 8 | Markdown report | `advisory-report.md` counts fixed in this spec too (both surfaces — §6.7). |

---

## 4. Architecture & data flow

### 4.1 Single computation

A new pure function is the **one and only** implementation of the report summary block:

```
tools/apd_gauntlet/synthesis/metrics.py        # NEW MODULE

def compute_metrics(
    findings: list[dict],          # deduped ∪ apath-* (see universe note below)
    capabilities: list[dict],
    contradictions: list[dict],
    severity_disagreements: list[dict],
) -> dict:
    """The canonical report summary block. Severity stored already-normalized (info)."""
```

- **Pure** (takes already-loaded record lists, returns a dict) → trivially unit-testable.
- **Finding universe — pin precisely:** `deduped-findings.yaml` records **UNION** the `apath-*` records, matching exactly the union `_load_deduped()` builds (rollup.py:73-85: it calls `load_corpus(run_dir, include_attack_path=True)` then re-appends **only** records whose id `startswith("apath-")` at [rollup.py:80](../../../tools/apd_gauntlet/synthesis/rollup.py#L80)). This **excludes** `threat-model.findings.yaml` (which `load_corpus` also returns). Implementers must keep the `apath-` prefix filter; do **not** simplify `compute_metrics` to call `load_corpus` directly, which would silently widen the universe and diverge from the report/audit counts (the report universe is `artifacts.deduped_findings + artifacts.attack_path_findings`, transform.py:195-197).
- Severity is normalized to `info` **inside** `compute_metrics`, so no downstream re-normalization exists.

### 4.2 Phase order (unchanged; confirmed in apd-gauntlet.js lines 41-42)

```
synthesis-apply (label "apply-clusters") → tmeval → apath
        │
        ▼
synthesis-rollup:  build_rollups() ──calls──> compute_metrics()
                   └─ _write() emits 40-synthesis/metrics.yaml      ← NEW canonical artifact
        │
        ├──> synthesis-report:  report-writer reads metrics.yaml (counts given, not counted)
        │
        ├──> synthesis-build:   load_run() → artifacts.metrics ; summary_rollup() = load-and-passthrough
        │
        └──> synthesis-audit:   data.js.summary == metrics.yaml   (passthrough parity)
```

Because `build_rollups` (synthesis-rollup) runs **before** the report-writer, the transform/build, and the audit, all three consume the artifact.

---

## 5. The `metrics.yaml` contract

### 5.1 Example (claim-event-bus shape, illustrative numbers)

```yaml
schema_version: 1
findings_total: 54
findings_pre_dedup: 54            # == findings_total today; see note
cross_lens_merged_clusters: 3
linked_clusters: 5
bySeverity:    {critical: 7, high: 31, medium: 16, low: 0, info: 0}
byDisposition: {gap: 40, blocked: 4, risk: 8, uncertainty: 2, ok: 0}
byTier:        {trustworthiness: 30, scalability: 14, auditability: 10}
capabilities_total: 22
capabilities_pre_dedup: 22
capabilitiesByMaturity: {designed: 5, implemented: 12, tested: 4, operationalized: 1}
contradictions: 2
severity_disagreements: 1
```

Keys are **identical** to today's `summary_rollup` return shape so `data.summary` is byte-for-byte equivalent (modulo `schema_version`, which is stripped before rendering).

**Note on `*_pre_dedup`:** `findings_pre_dedup == findings_total` today (and `capabilities_pre_dedup == capabilities_total`) — the current code sets them to `len(findings)`/`len(caps)` with the comment "post-dedup view; pre/post unknown without specialist counts" (transform.py:217-218). They are kept as distinct keys only for template/shape parity, **not** because a genuine pre-dedup count exists.

### 5.2 `schemas/metrics.schema.json` (NEW)

- Mirrors the `*-coverage-doc.schema.json` style: `additionalProperties: false`, `schema_version: {const: 1}`, every count `{type: integer, minimum: 0}`, the five `bySeverity` keys / five `byDisposition` keys / three `byTier` keys / four `capabilitiesByMaturity` keys all `required`.
- Wired into the full `validate` command's known-doc-schema set (so a malformed `metrics.yaml` fails validation like any other artifact).

### 5.3 Invariants (asserted by audit `metrics_internal_consistency`)

- `sum(bySeverity.values()) == findings_total`
- `sum(byTier.values()) == findings_total`
- `byDisposition["gap"] + byDisposition["risk"] + byDisposition["uncertainty"] + byDisposition["blocked"] == findings_total`

The disposition enum is exactly `[gap, risk, uncertainty, blocked]` (schemas/finding.schema.json) and `summary_rollup` defaults a missing disposition to `gap` (transform.py:201), so the four finding-side keys are exhaustive over findings and do sum to the total. `ok` is a fixed `0` sentinel kept for template parity (a capability-side concept) and is **excluded** from the sum — a naive five-key sum would mislead. All three invariants catch the same corruption class cheaply.

---

## 6. Component-by-component changes

### 6.1 NEW — `tools/apd_gauntlet/synthesis/metrics.py`

- `compute_metrics(findings, capabilities, contradictions, severity_disagreements) -> dict` (§4.1). Contains the logic currently in `summary_rollup` (transform.py:198-249), with severity normalized to `info` inside.

### 6.2 `tools/apd_gauntlet/synthesis/rollup.py`

- `build_rollups()` ([rollup.py:228](../../../tools/apd_gauntlet/synthesis/rollup.py#L228)): after computing coverage, read `contradictions.yaml` + `severity-disagreements.yaml` (present by rollup time — written by the synthesis-apply phase) and call `compute_metrics(findings, caps, contradictions, sev_dis)` where `findings, caps = _load_deduped(run_dir)` (already unions `apath-*` per §4.1). Store on `RollupResult`.
- `_write()` ([rollup.py:424](../../../tools/apd_gauntlet/synthesis/rollup.py#L424)): emit `40-synthesis/metrics.yaml` (`yaml.safe_dump(metrics, sort_keys=False)`).
- `RollupResult` gains a `metrics` field.
- **Key-tolerance:** `build_rollups` does **not** currently read contradictions/sev-disagreements. The new reads must use the **same** key fallbacks as `load_run` (`contradictions`/`contradiction`; `severity_disagreements`/`disagreements`/`severity_disagreement` — loader.py:432-460) so the counts match the transform's view exactly. Factor a tiny shared reader or inline the identical fallbacks.

### 6.3 `tools/apd_gauntlet/report/loader.py`

- `RunArtifacts` ([loader.py:94-117](../../../tools/apd_gauntlet/report/loader.py#L94)) is a `@dataclass(frozen=True)`. Add `metrics: dict[str, Any]` as a **required** field, placed after the last required field (`report_data`, :116) and before the first defaulted field (`source_hashes`, :117). Keeping it required (no default) honors the "no old-shape tolerance" decision and forces every construction site to be explicit (fails loud with `TypeError` if missed). **This breaks 14 `RunArtifacts(...)` constructor sites — enumerated in §9.**
- `load_run()` ([loader.py:395](../../../tools/apd_gauntlet/report/loader.py#L395)): add `40-synthesis/metrics.yaml` to the `_required(...)` set, read via `_yaml_with_hash` (hashed like all required artifacts), pass to `RunArtifacts(metrics=...)`. Missing → `MissingArtifactError` (intended).

### 6.4 `tools/apd_gauntlet/report/transform.py`

- `summary_rollup(artifacts)` ([transform.py:195](../../../tools/apd_gauntlet/report/transform.py#L195)): collapses to return `artifacts.metrics` with `schema_version` stripped (shape-validated). **The `collections.Counter` logic is deleted** — no recomputation.
- `findings_array()` ([transform.py:364](../../../tools/apd_gauntlet/report/transform.py#L364)): default the `tier` field to `"trustworthiness"` **when `apd_tier` is missing** (matching `compute_metrics`/`summary_rollup` tier defaulting — both key off `apd_tier` only, no goal derivation), so §2 tier sums cannot drift below `byTier`. (`_display_severity` unchanged; `metrics.yaml` already stores `info`.)

### 6.5 `tools/apd_gauntlet/synthesis/audit.py`

- **Delete** `_INFORMATIONAL_TO_INFO` (audit.py:18), `_norm_sev`, and the independent `count_parity_severity`/`count_parity_totals` recompute (audit.py ~169-187).
- **Replace** with passthrough parity: load `40-synthesis/metrics.yaml`; assert `data.js.summary.bySeverity == metrics.bySeverity` and `data.js.summary.findings_total == metrics.findings_total` (same check ids retained for continuity, new semantics).
- **Add** `metrics_internal_consistency` (§5.3 invariants).
- `data_js_recompute_drift` (findings-id coverage via `build_apd_data` recompute) is **unchanged** — different purpose (ids, not counts), and `build_apd_data` now reads `metrics.yaml`, so it stays consistent.
- `_recompute_nist_rollup` indirectly calls `build_apd_data` → `summary_rollup`; since that now reads `artifacts.metrics`, the recompute requires `metrics.yaml` to exist — true for any run reaching audit.

### 6.6 `report-template/screens/Overview.jsx` + rebuild

- Add a **count strip** in the exec-summary/headline area sourced from `data.summary`: e.g. `54 findings · 7 critical · 31 high · 16 med · 0 low · 0 info`.
- **Fix the breakdown omission**: include `critical` and `info` in the `headline-grid__breakdown` (Overview.jsx:27-33) so it reconciles with `findings_total`.
- Run `tools/build_report_template.py` and **commit** the rebuilt `app.js` + `.source-hash` (the freshness CI gate — `tools/check_report_template_freshness.py`). No new CSS required (reuse existing tokens/classes).

### 6.7 Report-writer agent + templates + workflow (both report surfaces)

- [.claude/agents/apd-report-writer.md](../../../.claude/agents/apd-report-writer.md): add `40-synthesis/metrics.yaml` **and** `40-synthesis/attack-path.findings.yaml` to **Inputs** (fixes doc/workflow drift). Rewrite **Executive summary guidance**: *prose stays qualitative — do NOT restate raw totals or per-severity counts; those render structurally from `metrics.yaml`. Reference magnitude/shape qualitatively.*
- [templates/report-data.template.yaml](../../../templates/report-data.template.yaml): drop the "artifact count" / "blocked-on-evidence count" numeric prompts from the `exec_summary` placeholder; replace with qualitative framing guidance.
- [templates/advisory-report.template.md](../../../templates/advisory-report.template.md) (**markdown report — decision #8**): the §1 template currently prompts literal counts (line 28: `<n> critical, <n> high, …, plus <n> blocked-on-evidence and <n> strengths`; line 30: capability-maturity counts). Replace those literal-count prompts so the §1 posture is either **qualitative** or **copies `metrics.yaml` numbers verbatim** — so the writer owns no authoritative count on the markdown surface either.
- [.claude/workflows/apd-gauntlet.js](../../../.claude/workflows/apd-gauntlet.js) (~line 568): add `metrics.yaml` to the report-writer step's read list.
- `EXEC_SUMMARY_PLACEHOLDER` (transform.py:28) and the `exec_summary_present` audit check are **unchanged** (presence/non-placeholder, editorial).

### 6.8 Validator wiring

- Register `schemas/metrics.schema.json` so the full `validate` command schema-checks `40-synthesis/metrics.yaml`.

---

## 7. Removed code (the report summary block's parallel recomputation)

| Location | Removed |
|----------|---------|
| `transform.summary_rollup` (transform.py:198-249) | `collections.Counter` finding/cap rollup logic → replaced by passthrough |
| `audit.py:18` | `_INFORMATIONAL_TO_INFO` constant |
| `audit_report` (~169-187) | `_norm_sev` + independent severity/total recompute → replaced by passthrough parity |

After this change there is exactly **one implementation of the report summary block** (`compute_metrics`) and exactly **one persisted source** (`metrics.yaml`). This claim is scoped to the **report** summary block: the `apd-gauntlet summarize` CLI (`summary.py:summarize_run`) remains a deliberately separate **pre-dedup** counter over a different universe (per-lens `*.findings.yaml`; note `deduped-findings.yaml` does **not** match its dotted `*.findings.yaml` glob, while `attack-path.findings.yaml` does) and is **not** touched — see §2 non-goals. The existing audit.py:170 comment ("NOT against summarize_run (which omits apath)") already records this intentional divergence.

---

## 8. Migration

`metrics.yaml` is **required, no fallback**. Only **git-tracked** fixtures are regenerated-and-committed. Local working runs under `runs/` are **never committed** (`.gitignore` ignores the entire `runs/` tree — they may contain sensitive security reviews; only `!tests/fixtures/runs/` is allowlisted) and are refreshed simply by re-running the workflow locally.

Tracked artifacts to regenerate and recommit:

- **`examples/apd-20260601-claim-event-bus/expected/`** (the enriched audit-test fixture run):
  - `40-synthesis/metrics.yaml` (new)
  - its **tracked** `report-html/{data.js, app.js, .source-hash}` — these are git-tracked (not gitignored) and go stale under the passthrough rewrite; regenerate via build-report.
- **`tests/fixtures/report-html/claim-event-bus-golden-data.js`** — the **byte-exact golden** that `tests/integration/report/test_example_golden.py` diffs against a freshly built `data.js`. Its `data.summary` block changes under the rewrite (and build-report now requires `metrics.yaml`), so the golden must be rebuilt and recommitted per that test's header recipe.
- Rebuilt `report-template` `app.js` + `.source-hash` (from §6.6) committed.

**Correction vs. earlier draft:** there is **no** committed `runs/*` fixture set to regenerate (they are gitignored), and the `tests/fixtures/legacy-coverage-shapes/` fixture is a **no-op** for this change: nothing calls `load_run` on it (its consuming tests use the example run for `load_run` and touch the legacy dir only via `MagicMock`/direct YAML reads), and it contains no `contradictions.yaml`/`severity-disagreements.yaml`. It needs **no** `metrics.yaml` and has **no** metrics-absence tolerance assertion to remove.

---

## 9. Testing strategy (TDD)

### New tests (write failing first)

- **`compute_metrics()`** (the new single source — heavy coverage): severity counts include `apath-*` and exclude threat-model findings; `informational→info` normalization; disposition/tier/maturity rollups; contradictions/sev-disagreements counts; tier defaulting; the three internal-consistency invariants (§5.3).
- **Loader**: reads `metrics.yaml`; missing → `MissingArtifactError`; hash recorded.
- **`summary_rollup` passthrough**: returns `artifacts.metrics` (schema_version stripped); does not recompute.
- **Audit (new)**: ADD passthrough-parity tests (pass on faithful data.js; **fail on injected drift** where `data.js.summary != metrics.yaml`) and `metrics_internal_consistency` pass/fail. (Note: today there are **no** `count_parity_*`-named tests; that path is covered only indirectly via the stale-`data.js` recompute-drift test — so these are net-new, not "repointed".)
- **Schema**: `metrics.schema.json` valid/invalid cases.
- **Frontend/transform**: `data.summary == metrics`; count strip + breakdown reconcile to `findings_total`.

### Updated existing tests

- **`RunArtifacts(...)` constructor fan-out (required `metrics` field):** 14 keyword-construction sites across 6 files must add `metrics=...`: `test_transform_attack_paths.py` (8), `test_transform_threat_model.py` (2), `test_transform_fallbacks.py`, `test_transform_taxonomy.py`, `test_tier4_manifest_fallbacks.py`, `test_tier4_shape_c_and_matrix.py`. (All raise `TypeError` until updated.)
- **MagicMock `_make_minimal_artifacts` helpers must set `a.metrics` explicitly** — `MagicMock` auto-creates a child mock for `a.metrics` instead of failing loud, so `summary_rollup` would return a `Mock` and confuse assertions. Helpers in: `test_informational_severity.py:30`, `test_tier4_strengths_contract.py:20`, `test_tier2_isolation.py:22`.
- **Summary-content tests repointed to the passthrough/single-source model:** `tests/unit/report/test_transform_summary.py` (severity/disposition/tier/capabilities/contradictions); `tests/unit/report/test_informational_severity.py` (`test_summary_rollup_counts_informational_under_info`).
- **`test_synthesis_equivalence.py`:** its two tests (`test_apply_clusters_reproduces_merged_record_semantics`, `test_rollup_reproduces_nist_projection`) are unrelated to the summary block — **nothing to repoint**. If a metrics rollup-equivalence test is desired, add it as a **new** test.

Full suite (1255+ tests per recent history) must stay green; run the full CI markdownlint glob (`docs/**`) locally pre-push.

---

## 10. Failure modes & acceptance criteria

### Failure modes

- **`metrics.yaml` absent** → `load_run` raises `MissingArtifactError`; build-report fails loudly. Intended (no silent fallback).
- **`metrics.yaml` malformed** → schema validation fails in `validate`; passthrough returns it but audit `metrics_internal_consistency` / parity catches gross corruption.
- **`compute_metrics` bug** → caught by its dedicated unit tests (the trade-off accepted under decision #5).

### Acceptance criteria

1. A fresh full-workflow run emits `40-synthesis/metrics.yaml` validating against `schemas/metrics.schema.json`.
2. `data.summary` in `data.js` equals `metrics.yaml` (minus `schema_version`).
3. Overview §1 count strip and headline-grid breakdown both reconcile exactly to `findings_total` (critical + high + medium + low + info), including attack-path findings.
4. Neither report-writer output owns an authoritative count: **HTML** Overview counts come only from `metrics.yaml`, **and** the markdown `advisory-report.md` §1 posture is qualitative or copied verbatim from `metrics.yaml`.
5. `audit_report` passes on a faithful build and fails when `data.js.summary` is perturbed away from `metrics.yaml`.
6. No `collections.Counter` summary recompute remains in `transform.py`; no `_norm_sev`/`_INFORMATIONAL_TO_INFO` recompute remains in `audit.py`. (`summarize_run` is intentionally retained — §2/§7.)
7. All tracked fixtures (example run + tracked `report-html` + byte-exact golden + rebuilt `app.js`/`.source-hash`) carry/reflect `metrics.yaml`; full test suite green.

---

## 11. Open questions / risks

- **`RollupResult` ↔ contradictions read**: `build_rollups` does not currently read contradictions/sev-disagreements; the new reads must use the same key-tolerance as `load_run` (§6.2) to avoid a count mismatch. (Resolved in spec; flagged for implementer attention.)
- **`schema_version` strip is settled**: verified no renderer reads `summary.schema_version`; stripping it is a safe no-op required only to satisfy byte-parity AC#2.
- **Markdown verbatim-vs-qualitative (§6.7)**: the implementation plan should pick one of the two `advisory-report.md` §1 treatments (fully qualitative, or verbatim-from-`metrics.yaml`). Default recommendation: **qualitative** (consistent with the HTML exec-summary treatment; avoids re-introducing hand-typed numbers).
