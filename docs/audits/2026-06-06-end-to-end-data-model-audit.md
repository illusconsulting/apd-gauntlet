# End-to-end data-model consistency audit — APD gauntlet

**Date:** 2026-06-06
**Scope:** Every task flow from run scaffold through the rendered HTML report, traced
to confirm the data model is internally consistent and reliably produces receipts and
outputs. Method: codebase-memory graph trace of the workflow runner + every
producer/consumer function, cross-referenced against the JSON schemas and the shipped
example fixture (`examples/apd-20260601-claim-event-bus`).
**Framework version at audit:** 1.6.0 (main @ `66b292b`).

This is an **advisory inventory**, not a change. Nothing here is a CI failure — the
pipeline is internally consistent enough that all gates pass; the items below are
divergences between intent/documentation and implementation, latent edge cases, and
cleanup opportunities. The single most material item is **F1** (tmeval findings are
orphaned from the report/rollups in the default pipeline).

> **Resolution status (2026-06-06):** all six findings were fixed on branch
> `fix/data-model-consistency-inventory`. F1 was resolved in the "wire tmeval in
> fully" direction (tmeval findings are now first-class across rollups, metrics,
> the report findings list, and the audit id-coverage check); F3 in the "receipt
> per-class block" direction (the agent receipt now carries `report_audit`
> `{structural_failed, editorial_failed}` so the gate blocks on structural
> completeness only). The descriptions below are the **pre-fix** state; see each
> finding's recommendation for what was implemented.

---

## 1. The verified spine (task → receipt → output)

Canonical order from [.claude/workflows/apd-gauntlet.js](../../.claude/workflows/apd-gauntlet.js):

```
setup (validate scaffold, build-domain-skill, validate-domain)
  └─ intake            → 00-context/context-brief.md, asset-inventory.yaml (always)
  └─ code-recon        → 00-context/code-evidence-index.yaml         (gated: args.code_recon)
  └─ threat-model-author (ALWAYS) → 00-context/threat-model-normalized.yaml + authored.md
  └─ tm-recon          → 00-context/threat-model-supplied-normalized.yaml (gated: args.threat_model)
  └─ tier-1/2/3        → <tier>/<lens>.findings.yaml + .capabilities.yaml  (9 lenses)
        each tier: canonicalize (alwaysRun) → validate --tier gate
  └─ full pre-phase-5 validate (cross-file Pass 3)
  └─ 5a cluster-candidates → cluster-candidates.yaml
  └─ 5b adjudicate         → cluster-decisions.yaml
  └─ 5c apply-clusters     → deduped-findings.yaml, deduped-capabilities.yaml,
                              rejected-records.yaml, severity-disagreements.yaml,
                              contradictions.yaml
       (fallback: apd-synthesizer writes the same set + report-data.yaml, NOT rollups)
  └─ 5.5 tmeval / 5.6 apath (parallel)
        tmeval → 40-synthesis/threat-model-coverage.yaml + 40-threat-model/threat-model.findings.yaml
        apath  → asset-graph.yaml, attack-paths.yaml, defense-graph.yaml, attack-path.findings.yaml
  └─ 5d rollup             → nist-coverage.yaml, attack-exposure.yaml,
                              apd-coverage-matrix.yaml, metrics.yaml
                              (+ cwe/owasp/d3fend/atlas-coverage when declared)
  └─ 5e report-writer      → report-data.yaml + advisory-report.md
  └─ 5f build-report       → report-html/{data.js, app.js, screens.css, index.html,
                              build-manifest.txt, .source-hash}
  └─ 5g audit-report (loop ≤3) → report-audit.yaml  [completeness gate]
  └─ 5h domain-coverage-delta + domain-improvements (advisory, non-blocking)
  └─ closeout (summarize, final validate)
```

### Receipt model — CONSISTENT

Every `pyStep`/`llmStep` returns an agent receipt. The JS `RECEIPT` constant
([apd-gauntlet.js:50](../../.claude/workflows/apd-gauntlet.js#L50)) matches
[schemas/agent-receipt.schema.json](../../schemas/agent-receipt.schema.json)
field-for-field (required `[agent,status,outputs,counts]`; `status ∈ {ok,blocked,error}`;
`additionalProperties:false` throughout). The workflow branches only on
`receipt.status`, which mirrors the dispatched CLI exit code. ✓

### Unified metrics chain — CONSISTENT

`build_rollups` → `compute_metrics` writes `metrics.yaml`
([rollup.py `_write`](../../tools/apd_gauntlet/synthesis/rollup.py)) → `load_run` **requires**
it → `summary_rollup` returns it verbatim (no recompute) → `audit_report` re-checks
`metrics.yaml.bySeverity == data.js.summary.bySeverity` and the internal-sum invariants.
Single source of truth holds end to end. ✓

### Enum closure — CONSISTENT

`audit.metrics_internal_consistency` asserts `sev_sum == tier_sum == disp_sum == findings_total`.
This is only safe if the finding enums are closed over the keys it sums. Verified against
[schemas/finding.schema.json](../../schemas/finding.schema.json):
`disposition ∈ {gap,risk,uncertainty,blocked}` (== disp_sum keys) and
`apd_tier ∈ {trustworthiness,scalability,auditability}` (== tier_sum keys). ✓
Severity uses `informational` in the schema but `info` in metrics/data.js — bridged by
`metrics._norm_sev` and `transform._display_severity` (see F6).

### Report-data contract — CONSISTENT

[schemas/report-data.schema.json](../../schemas/report-data.schema.json) required keys
(`exec_summary, headline_findings, strengths, next_steps, posture_summary`, optional
`domain_pack_caveat`) match exactly the `supplement.get(...)` keys read by
`transform.build_apd_data`. ✓

### Loader required-set ↔ producers — CONSISTENT

`load_run` requires `.apd-run.yaml`, `asset-inventory.yaml`, `deduped-findings.yaml`,
`deduped-capabilities.yaml`, `nist-coverage.yaml`, `attack-exposure.yaml`,
`apd-coverage-matrix.yaml`, `metrics.yaml` — each produced by intake / apply-clusters /
rollup upstream. `report-data.yaml` is optional at the loader (algorithmic fallback) but
required-in-practice by the audit gate's editorial checks. ✓

### Audit gate — COMPREHENSIVE

`audit_report` cross-checks id coverage (findings/caps/nist/attack), `nist_rollup_parity`
(recompute), metrics parity + internal consistency, `data_js_recompute_drift`,
`section_errors_empty`, `source_hash_drift`, and the structural/editorial completeness set
(exec summary, editorial sections, attack-paths, D3FEND overlay, APD matrix, coverage
rollups, taxonomy titles, threat-model scene). Empty-state exemptions are explicit. ✓

---

## 2. Inventory

| ID | Type | Severity | Location | One-line |
|----|------|----------|----------|----------|
| F1 | Inconsistency / coverage gap | **Medium-High** | `rollup._load_deduped`, `transform.findings_array`, `loader.load_run`, `audit.audit_report` | tmeval findings are orphaned from rollups/metrics/report in the default pipeline, contradicting the C-20 contract. |
| F2 | Gap (broken fallback) | **Medium** | `apd-gauntlet.js` rollup last-resort | The rollup last-resort omits `metrics.yaml`, which the loader requires → build-report cannot ship. |
| F3 | Inconsistency / opportunity | Low-Medium | `cli.audit_report_cmd`, `apd-gauntlet.js` audit loop | The completeness gate cannot separate structural vs editorial at the workflow boundary; editorial residuals block. |
| F4 | Latent edge case | Low | `apply.apply_clusters` | `include_attack_path=True` runs before apath; on a corruption-recovery re-run it can duplicate apath rows in the report. |
| F5 | Doc / cosmetic | Low | `apd-gauntlet.js` `outputs` strings | Advisory `outputs` labels drift from actual writes (e.g. rollup omits `metrics.yaml`). |
| F6 | Vocabulary seam | Low / Info | schema vs metrics/transform | Two severity tokens (`informational` vs `info`) bridged by helpers. |

---

### F1 — tmeval findings are orphaned from the report, metrics, and coverage rollups (default/decomposed pipeline)

**Evidence**

- `synthesis/rollup.py:_load_deduped` feeds **all** rollups + `compute_metrics`. It seeds
  from `deduped-findings.yaml` then unions tier-4 findings with **only**
  `if fid.startswith("apath-")`. `tmeval-*` records are never added.
- `report/transform.py:findings_array` builds the report findings list as
  `artifacts.deduped_findings + artifacts.attack_path_findings`. There is **no**
  tmeval source — `report/loader.py:load_run` exposes `attack_path_findings` but has no
  `threat_model_findings` field.
- `synthesis/audit.py:audit_report` checks `id_coverage_findings` as
  `deduped ∪ apath == data.findings` — i.e. the gate *agrees* with the omission, so it can
  never catch it.
- Ordering guarantees this is the live behavior: apply-clusters (5c) **and** the
  synthesizer fallback both run *before* tmeval (5.5), so tmeval findings can never be in
  `deduped-findings.yaml`; the only downstream union (`_load_deduped`) excludes them.

**What it contradicts**

- The workflow's own comment: "_load_deduped … UNION the tier-4 apath-*/**tmeval-*** findings"
  ([apd-gauntlet.js:464-468](../../.claude/workflows/apd-gauntlet.js#L464) and L539-541).
- The **C-20 contract**: `validate._iter_records` *does* aggregate tmeval (proven by
  `tests/test_synthesis_matrix_includes_tier4_findings.py`), and the `apd-synthesizer`
  agent prompt documents tmeval participation in the 9×N matrix. The decomposed `rollup`
  path (the default) and the legacy `_iter_records`/synthesizer path therefore **disagree**
  on whether tmeval participates.
- The finding schema treats `tmeval-` as a first-class finding id with a **required**
  `control_mappings.nist_800_53r5` — implying those NIST controls (e.g. `AU-10`) should
  roll into `nist-coverage.yaml`. They don't.

**Confirmed in the example fixture**: `deduped-findings.yaml` has 0 tmeval and 0 apath ids;
the 3 tmeval findings live in `40-threat-model/threat-model.findings.yaml` and surface in
`data.js` *only* as `finding_id` references (contradictions / cross-refs), never as report
findings or matrix/nist rows. (apath, by contrast, reaches the report via
`attack_path_findings` and the rollup via the `apath-` union — fully wired.)

**Net effect:** a whole finding class — the threat-model evaluator's coverage-gap /
contradiction / silence findings, with real severities and NIST mappings — is computed and
validated, then silently dropped from the headline findings, severity distribution, NIST
coverage, ATT&CK exposure, the 9×N matrix, and `metrics.findings_total`. Their only report
surface is the threat-model scene (driven by `threat-model-coverage.yaml`, not the finding
records).

**Recommendation (decide intent, then make one path true):**

1. *If tmeval should participate* (matches C-20 + the schema's NIST requirement): teach
   `_load_deduped` to also union `tmeval-` (the loader already pulls
   `40-threat-model/threat-model.findings.yaml` via `load_corpus`), add a
   `threat_model_findings` field to `RunArtifacts`, include it in `findings_array`, and
   widen `audit.id_coverage_findings` to `deduped ∪ apath ∪ tmeval`. Regenerate the golden.
2. *If tmeval should NOT be report findings* (only the scene): correct the workflow comment,
   the synthesizer agent prompt / C-20 wording, and reconcile the finding schema's tmeval
   NIST-mapping expectation. Either way, eliminate the decomposed-vs-legacy divergence so
   the two synthesis paths produce identical coverage for the same run.

---

### F2 — rollup last-resort fallback cannot produce a shippable report (missing `metrics.yaml`)

**Evidence** ([apd-gauntlet.js:546-560](../../.claude/workflows/apd-gauntlet.js#L546)): when
the deterministic `rollup` fails twice, the synthesizer last-resort is instructed to
"write **ONLY** the coverage rollups `nist-coverage.yaml, attack-exposure.yaml,
apd-coverage-matrix.yaml` … then STOP." But `report/loader.py:load_run` makes
`40-synthesis/metrics.yaml` a **required** input (added by the unified-metrics model). With
no `metrics.yaml`, the subsequent `build-report` raises `MissingArtifactError`, `data.js`
is never written, and the 5g completeness gate throws ("audit-report produced no receipt").
The last-resort prompt predates `metrics.yaml` becoming required and was not updated.

**Recommendation:** add `40-synthesis/metrics.yaml` to the last-resort file list (and have
the synthesizer compute it from the deduped corpus ∪ apath, mirroring `compute_metrics`), so
the deepest fallback can still yield a valid `load_run` input set.

---

### F3 — completeness gate conflates structural vs editorial failures at the workflow boundary

**Evidence:** `synthesis/audit.py:_check` sets `result.status="fail"` on **any** failing
check, including `klass="editorial"`. `cli.audit_report_cmd` exits 1 whenever
`result.status=="fail"` — it computes `structural_failed`/`editorial_failed` for the console
line but **uses neither** for the exit code. The workflow then reads the *receipt* status:
`const structuralOk = audit && audit.status === 'ok'`. So `structuralOk` actually means
"the audit command exited 0", and at the N=2 cap `if (!structuralOk) throw` fires on a
**surviving editorial failure** (e.g. an exec summary still equal to the placeholder),
despite "editorial" being the nominally non-blocking class (the design routes the LLM
semantic residual as non-blocking).

This is a *documented compromise* — the agent-receipt schema carries no per-class counts, so
the loop "branches on `audit.status` only" by design. But it leaves a misnomer and a
behavioral surprise.

**Recommendation (opportunity, not a defect):** rename `structuralOk` →
`auditCommandPassed` for honesty; and consider adding an optional
`report_audit: {structural_failed, editorial_failed}` block to
`agent-receipt.schema.json` so the loop can block on **structural-only** and surface
residual editorial gaps non-blocking (consistent with the LLM semantic-residual policy).
Keep the in-loop report-writer remediation as the driver for editorial fixes.

---

### F4 — `apply_clusters` reads the corpus with `include_attack_path=True` although it runs before apath

**Evidence:** `apply.apply_clusters` calls `load_corpus(run_dir, include_attack_path=True)`.
In the normal flow `attack-path.findings.yaml` doesn't exist yet (apply precedes apath), so
this is a no-op. On a **corruption-recovery re-run** where `deduped-findings.yaml` was
deleted/invalidated *and* `attack-path.findings.yaml` already exists, apply would emit
`apath-*` into `deduped-findings.yaml`. Downstream id-keyed unions are idempotent to this
(`_load_deduped`'s `seen` set; the audit's set-equality), so **counts stay correct**, but
`findings_array` = `deduped + attack_path_findings` would then list each apath finding
**twice** as array items (the id-set audit check still passes, so it wouldn't be caught).

**Recommendation:** set `include_attack_path=False` in `apply_clusters` (it precedes apath;
apath is unioned downstream regardless), or de-duplicate `findings_array` by id as a belt.

---

### F5 — workflow `outputs` advisory strings drift from actual writes

**Evidence:** the rollup `pyStep` `outputs` string lists
"nist-coverage.yaml, attack-exposure.yaml, apd-coverage-matrix.yaml (+ declared-taxonomy
coverage files)" but `build_rollups` also writes `metrics.yaml`. These strings are advisory
(injected into the idempotency-guard prompt), and the guard validates by **scope/path**, not
by this list — so the impact is low — but the drift can mislead a reader/operator.

**Recommendation:** add `metrics.yaml` to the rollup `outputs` label; sweep the other step
labels for parity with the real write sets while there.

---

### F6 — two severity vocabularies (`informational` vs `info`)

**Evidence:** `finding.schema.json` severity enum uses `informational`; `compute_metrics`
and `data.js`/template use `info`. Bridged by `metrics._norm_sev`
(`informational → info`, via `_INFORMATIONAL_TO_INFO`) and `transform._display_severity`.
Functionally handled (and a prior fix wired the template's informational token), but the
dual vocabulary is a standing seam where a future mapping site could be missed.

**Recommendation (optional):** converge on one canonical token at the schema boundary, or
add a single shared normalizer imported by both synthesis and transform so there is exactly
one mapping.

---

## 3. What is verifiably solid (no action)

- Agent-receipt JS constant ↔ schema: exact match; workflow branches only on the typed status.
- Unified metrics: single source (`compute_metrics`), passthrough at the report, re-verified
  by the audit's parity + internal-consistency checks.
- Finding enum closure underwrites the audit's sum invariants.
- `report-data.schema.json` ↔ transform supplement keys: exact.
- `load_run` required set ↔ upstream producers: exact; per-section isolation in
  `build_apd_data` keeps one bad section from sinking the whole report.
- apath findings are fully wired (rollup union + `attack_path_findings` + audit coverage).
- CLI commands all registered and every workflow `agentType` resolves to a
  `.claude/agents/*.md` (test-pinned: `test_every_cli_command_is_registered`,
  `test_every_agenttype_resolves_to_an_agent_file`).
- Idempotency guard + same-session/cross-session resume design is coherent (skip-sentinel
  convention; `canonicalize` `alwaysRun` before each tier gate).
- Completeness gate blocks degraded HTML reports (structural failures + missing audit
  receipt) with explicit empty-state exemptions.

---

## 4. Suggested priority

1. **F1** — decide tmeval's role and unify the two synthesis paths (correctness of report
   coverage; highest reviewer-visible impact).
2. **F2** — one-line fix to the rollup last-resort prompt (restores the deepest fallback).
3. **F3** — receipt per-class block + variable rename (gate honesty).
4. **F4 / F5 / F6** — cleanups.
