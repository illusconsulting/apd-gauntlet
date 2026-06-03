# HTML report completeness gate — Design

**Status:** approved design (brainstorming) → ready for implementation plan
**Branch:** `feat/report-completeness-gate` (proposed)
**Date:** 2026-06-02

## Context

Every gauntlet run must produce a complete, trustworthy HTML report —
executive summary, accurate finding/capability counts, attack-path analysis,
and the D3FEND overlay — at `runs/<run_id>/40-synthesis/report-html/`. Today
the report *pipeline* is well-hardened (tiers 1–4 landed: atomic writes,
`_normalize_for_json`, taxonomy reference DBs, per-section isolation,
`is_empty_run`, `section_errors`), but there is **no end-to-end guarantee that
the artifact a user opens is actually complete.** Two design properties combine
into a silent gap:

1. **Per-section isolation.** [`build_apd_data`](../../../tools/apd_gauntlet/report/transform.py)
   wraps each of its 14 sections in try/except: a section that raises is
   replaced by a placeholder and recorded in `meta.section_errors`, and *the
   build still exits 0*. The only hard failure is when `meta_block` itself
   cannot assemble.
2. **Editorial fallback.** When `report-data.yaml` is absent or sparse,
   `build-report` substitutes a placeholder exec summary
   (`"Run summary not provided by synthesizer."`) and empty editorial blocks.

So a run can finish "successfully" while shipping a placeholder exec summary,
counts that don't reconcile with the deduped corpus, an empty attack-paths
section, or a missing D3FEND overlay — and the workflow never notices, because
its audit loop **surfaces residual discrepancies non-blocking** after the
remediation cap (`apd-gauntlet.js`, the `synthesis-audit` loop).

This design closes that gap with a **preventive completeness gate**: a run that
cannot produce a complete report **self-heals what is remediable, then blocks**
rather than shipping a degraded report silently.

### What already exists (why we extend, not rebuild)

A deterministic structural checker already exists and is already cleanly
separated from the LLM judge:

- **`audit-report`** (Python, `tools/apd_gauntlet/synthesis/audit.py:audit_report`)
  parses the shipped `data.js` (`parse_data_js` reverses the `</`→`<\/` escaping)
  and cross-checks it against the authoritative YAMLs. It **already** checks:
  `id_coverage_findings`, `id_coverage_capabilities`, `id_coverage_nist`,
  `nist_rollup_parity`, `id_coverage_attack`, `count_parity_severity`,
  `count_parity_totals`, `data_js_recompute_drift`, `section_errors_empty`, and
  bundle source-hash drift. It emits `40-synthesis/report-audit.yaml` and exits 1
  on `status == "fail"`.
- **`apd-report-auditor`** (LLM agent) is a *separate* actor that judges
  *semantic faithfulness* of the editorial prose (misleading severity, material
  omission, invented content) and returns `GATE: pass|fail`. It reads
  `report-audit.yaml` + `advisory-report.md` + `report-data.yaml` — **never**
  `data.js` — and writes nothing.
- **`apd-report-writer`** (LLM agent) is the *author*: it produces
  `report-data.yaml` (exec_summary, posture_summary, headline_findings,
  next_steps) + `advisory-report.md`, and on remediation re-authors them.

The workflow's `synthesis-audit` loop already runs `audit-report` and
`apd-report-auditor` as two distinct gate conditions
(`structuralOk && semanticOk`). The missing pieces are therefore narrow:
**(a)** a handful of completeness checks `audit_report` does not yet make, and
**(b)** the terminal behavior — residual structural failure is surfaced
*non-blocking* when the user needs it to *block*.

A new `verify-report` command was considered and rejected: it would duplicate
~70% of `audit_report` (data.js parsing, count parity, section_errors,
id-coverage, recompute-drift) and add a second overlapping loop.

## Locked design decisions

1. **Extend `audit_report`; no new command or module.** All check logic lands
   in `tools/apd_gauntlet/synthesis/audit.py`, reusing `parse_data_js`,
   `AuditResult`, `_check`, `_write`. Everything stays in `report-audit.yaml` —
   no separate completeness artifact.
2. **Self-heal (editorial) then block (structural).** A failure remediable by
   regenerating `report-data.yaml` (the report-writer's output) is healed via
   the existing loop; an unresolved *structural* failure blocks the run.
3. **Per-check classification.** Every check carries `klass ∈ {structural,
   editorial}`. Only `exec_summary_present` and `editorial_sections_present` are
   `editorial`; all others are `structural`. The report-writer controls only
   `report-data.yaml`, so only editorial failures can be healed by re-running it.
4. **Exempt legitimately-empty states.** The gate fires only on degradation, not
   on accurate zero-output. Exemptions: `meta.is_empty_run` (content checks);
   attack-path analysis not activated — no `asset-graph.yaml` (checks 3/4);
   `pairs_empty_explanation` present (a documented valid "graph exists, no
   traversable chain" outcome); no `defense-graph.yaml` or zero bottleneck edges
   (check 4); an `apath-*` blocked finding (check 3).
5. **The LLM semantic auditor is untouched.** Its prompt, its role, and its
   non-blocking *semantic* residual after the cap are unchanged. Only the
   *structural completeness* side becomes blocking.

## Components

### C1 — New/tightened checks in `synthesis/audit.py`

`_check` gains a `klass: str = "structural"` parameter so every existing check is
classified automatically; the two editorial checks pass `klass="editorial"`.
The full catalog (the user's 8 requested checks → concrete checks):

| # | Check name | `klass` | Status | Pass condition | Exemption |
|---|---|---|---|---|---|
| 2 | `id_coverage_findings`, `id_coverage_capabilities`, `count_parity_severity`, `count_parity_totals` | structural | exists | data.js ids/counts equal the deduped ∪ apath corpus | — |
| 5 | `section_errors_empty` | structural | exists | `meta.section_errors` empty | — |
| 1 | `exec_summary_present` | editorial | new | `data.exec_summary` non-empty **and** ≠ `EXEC_SUMMARY_PLACEHOLDER` | `meta.is_empty_run` |
| 8 | `editorial_sections_present` | editorial | new | `report-data.yaml` has non-empty `posture_summary`, `headline_findings`, `next_steps` | `meta.is_empty_run` |
| 3 | `attack_paths_present` | structural | new | see logic below | analysis not activated; blocked-finding present |
| 4 | `d3fend_overlay_present` | structural | new | see logic below | no `defense-graph.yaml`; zero bottleneck edges |
| 6 | `apd_matrix_nonempty` | structural | new (tighten) | `apd_matrix.rows` non-empty when findings exist; `nist_rollup` / `attack_exposure` non-empty when ≥1 finding carries that mapping | `meta.is_empty_run` |
| 7 | `taxonomy_titles_resolve` | structural | new (tighten) | every cited family's `reference_db_versions[fam].count > 0` **and** no taxonomy entry has `title == id` | families with no cited ids |

**`EXEC_SUMMARY_PLACEHOLDER`.** The string `"Run summary not provided by
synthesizer."` is currently a literal in `build_apd_data`. Lift it to a module
constant in `transform.py` and import it in `audit.py` so the emitter and the
checker cannot drift.

**Check 3 — `attack_paths_present`.** The activation signal is
`40-synthesis/asset-graph.yaml` (the analyzer emits it on crown-jewel
activation):

- `asset-graph.yaml` absent → **exempt** (analysis not activated). Pass.
- present but `data.attack_paths is None` → **FAIL** ("analysis ran but build
  dropped the section").
- present, `data.attack_paths` non-None, `asset_graph_summary.node_count == 0` →
  **FAIL**, unless an `apath-*` blocked finding exists → **exempt**.
- present, graph rendered, `total_paths == 0` **with** `pairs_empty_explanation`
  → **PASS** (documented valid state; never require paths > 0).

**Check 4 — `d3fend_overlay_present`.** Gated on
`40-synthesis/defense-graph.yaml`:

- absent → **exempt**. Pass.
- present with non-empty `bottleneck_overlays` in the YAML →
  `data.attack_paths.bottleneck_overlays` must be **non-empty, equal in count**,
  and every overlay must carry a D3FEND technique id → else **FAIL**
  ("defense-graph N overlays vs data.js M").
- present but zero bottleneck edges → **exempt** (nothing to overlay).

**Check 6 — `apd_matrix_nonempty`.** Every finding has an `apd_goal`, so the
9×N matrix must have rows whenever findings exist; `nist_rollup` /
`attack_exposure` non-emptiness is required only when ≥1 deduped finding carries
a NIST / ATT&CK mapping (otherwise legitimately empty). `nist_rollup_parity`
(existing) already covers the populated-vs-populated case.

**Check 7 — `taxonomy_titles_resolve`.** Fails if a cited family's reference DB
loaded zero entries (`reference_db_versions[fam].count == 0`) or any taxonomy
entry renders as a bare ID (`title == id`, e.g. `T1078 — T1078`). Tightens the
existing `id_coverage_nist`, which only checks that cited ids are present as keys.

### C2 — Classification + per-class counts

- `_check(result, name, ok, detail, klass="structural")` records `klass` on each
  check dict in `AuditResult.checks`. `klass` is **optional** in
  `report-audit.schema.json` (backwards-compatible with already-committed
  `report-audit.yaml` fixtures) but always emitted by `_check`.
- `audit_report_cmd` computes `structural_failed` / `editorial_failed` (failed
  checks per `klass`) and **prints them to stdout** for log/human visibility. It
  does **not** put them in the agent receipt — see the planning-refinement note
  below.

**Planning refinement (loop control uses `audit.status` only).** The workflow
`RECEIPT` mirrors `agent-receipt.schema.json`, whose `counts` is
`additionalProperties: false`, and the workflow JS has no filesystem access. So
per-class counts cannot reach the loop without changing the global receipt
contract shared by all agents. Rather than do that for a micro-optimization, the
workflow loop branches on `audit.status` (ok/error) alone — which already
delivers self-heal-then-block. `klass` still lives in `report-audit.yaml` for
humans, tests, and the report-auditor, and targeted editorial remediation is
achieved by the **report-writer agent reading `report-audit.yaml`** (it has file
access). The only dropped element is the purely-structural short-circuit: a
structural failure may consume up to 2 remediation cycles before blocking (a
latency cost, not a correctness one).

### C3 — Workflow audit loop: self-heal then block

Replace the terminal behavior of the `synthesis-audit` loop in
`.claude/workflows/apd-gauntlet.js`. Loop control uses `audit.status` only
(per the C2 refinement):

```
for (let i = 0; i <= 2; i++) {
    const audit   = pyStep('audit-report');        // writes report-audit.yaml; status ok|error
    const auditor = agent('apd-report-auditor');   // unchanged: semantic GATE pass|fail (judgment, non-blocking)
    const structuralOk = audit && audit.status === 'ok';
    const semanticOk   = typeof auditor === 'string' && /GATE:\s*pass/i.test(auditor);
    if (structuralOk && semanticOk) break;
    if (i === 2) {
        if (!structuralOk) {
            throw new Error('report completeness gate: audit-report still FAILED after 2 ' +
                'remediations — structurally incomplete report (see report-audit.yaml). ' +
                'Refusing to ship a degraded report.');
        }
        log('report audit: residual SEMANTIC discrepancies after 2 remediations; non-blocking.');
        break;
    }
    // Self-heal: the report-writer reads report-audit.yaml and fixes failed EDITORIAL checks,
    // and also addresses the semantic critique; then rebuild.
    critique = auditor;
    llmStep('apd-report-writer', 'Read report-audit.yaml: address every failed check whose ' +
        'klass is "editorial" (regenerate report-data.yaml + advisory-report.md). ALSO address ' +
        'this semantic critique. CRITIQUE: ' + critique);
    pyStep('build-report');
}
```

Two behavioral changes vs. today: (1) the post-cap terminal state **throws** on
structural failure instead of `log(...); break`; (2) the report-writer
remediation reads `report-audit.yaml` and addresses failed editorial checks (not
just the semantic critique). The semantic auditor's non-blocking residual is
preserved. (The purely-structural short-circuit from earlier drafts is dropped —
see the C2 refinement note.)

### C4 — Schema delta

- `schemas/report-audit.schema.json` — add **optional** `klass` (`enum:
  [structural, editorial]`) to each check item (kept optional so the
  already-committed `report-audit.yaml` fixtures, which lack it, still validate;
  `_check` always emits it on fresh output).
- `schemas/agent-receipt.schema.json` — **unchanged.** Its `counts` is
  `additionalProperties: false`; per the C2 refinement we deliberately do not add
  per-class counts to the receipt, so this global contract is untouched.
- No new schema files.

## Testing

- **Unit (`tests/test_cli_audit_report.py`)** — for each new/tightened check, a
  *pass*, a *fail*, and the *exemption* case. Priority: `exec_summary_present`
  (placeholder→fail, real→pass, empty-run→exempt); `attack_paths_present`
  (asset-graph present + null section→fail; `pairs_empty_explanation`→pass; no
  asset-graph→exempt); `d3fend_overlay_present` (overlay count mismatch→fail; no
  defense-graph→exempt); `taxonomy_titles_resolve` (bare-ID→fail; empty
  reference DB→fail).
- **Classification** — assert each failed check reports the correct `klass` and
  that `audit_report_cmd`'s stdout prints the `structural_failed` /
  `editorial_failed` tally.
- **Schema (`tests/test_report_audit_schema.py`)** — extend the fixture +
  assertion so every check carries a valid `klass`.
- **Workflow (`tests/test_workflow_apd_gauntlet.py`, static-source)** — pin
  (a) the post-cap structural throw exists (`/report completeness gate/`),
  (b) the semantic-only non-blocking `log(...)` is preserved, (c) the
  report-writer remediation prompt reads `report-audit.yaml`; the existing
  `test_audit_loop_cap_literal_present` (cap `i <= 2`) stays green.
- **Regression guard (critical)** — `audit-report` must yield zero failures
  (`status == "ok"`) on every shipped run (`runs/apd-20260527-*`) + the enriched
  committed example, so the gate cannot false-positive on real reports.

## Out of scope

- No React / `report-template/` changes.
- No new CLI command or module.
- No change to the `apd-report-auditor` prompt or its non-blocking semantic
  residual.
- No change to `build-report`'s per-section isolation contract (build still never
  hard-fails on one bad section; the gate is what enforces completeness).

## Self-review

**Coverage.** All 8 requested checks map to a concrete check: counts (2) and
section_errors (5) exist; coverage-rollups (6) and taxonomy (7) are tightened;
exec_summary (1), editorial sections (8), attack-paths (3), and D3FEND (4) are
new. Enforcement (self-heal-then-block) and classification (editorial vs
structural) are specified in C2/C3.

**Placeholder scan.** No TODO/TBD/"implement later"; every check has explicit
pass + exemption logic.

**Consistency.** `klass`, `EXEC_SUMMARY_PLACEHOLDER`, `structural_failed` /
`editorial_failed`, and the check names are used identically across C1–C4 and
Testing. The exemption set in decision 4 matches the per-check exemptions in C1.

**Scope.** Single concern (report completeness), one Python module + one workflow
loop + one schema + tests. No unrelated refactoring.
