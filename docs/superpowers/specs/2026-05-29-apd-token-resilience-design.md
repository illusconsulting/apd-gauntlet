# APD Gauntlet Token-Resilience Design

- **Date:** 2026-05-29
- **Status:** Approved (design); implementation plan pending
- **Author:** brainstormed with Claude Code
- **Scope:** Restructure how the APD gauntlet is orchestrated and how synthesis/report
  are produced so a full run does not overrun model context windows, and so an
  interrupted run resumes automatically with minimal user input.

## 1. Problem

Full gauntlet runs frequently fail to complete because individual agent contexts
overrun their token budget. Measured against a real run
(`runs/apd-20260527-authentik-identity-provider/`), three structural causes:

1. **The synthesizer is a single-context monolith.** `apd-synthesizer` must read
   ~6,475 lines of YAML (9 findings files at 364–760 lines each + 9 capability
   files + tier-4 finding files), plus 5 skills + the context brief, and then
   **write ~9,000+ lines** — `deduped-findings.yaml` alone is 6,940 lines, plus
   `nist-coverage.yaml` (400), `attack-exposure.yaml` (292), the 9×N matrix (223),
   the 585-line advisory report, and `report-data.yaml`. Steps 6–8 (NIST / ATT&CK /
   9×N rollups) are pure mechanical aggregation that does not need an LLM.

2. **The orchestrator is a long-lived context with no discharge valve.**
   `apd-orchestrator` lives the whole run and accumulates: every specialist's
   *prose* return (no specialist defines a receipt-only contract today), plus
   `apd-gauntlet validate <run-dir>` output dumped 3+ times over the **whole** run
   dir (the validator has no `--quiet`/`--errors-only`/`--tier` scoping), plus
   intake/recon returns.

3. **No resumability.** If any phase overruns, the whole run restarts — there is
   no phase ledger and no skip-if-already-done check. A single token limit becomes
   "cannot complete."

## 2. Goals / Non-Goals

**Goals**

- No single context ever holds the whole findings/capabilities corpus.
- The run driver retains only tiny structured receipts, not analysis content.
- An interrupted run resumes automatically (same-session) and idempotently
  (cross-session) with no special user action beyond re-invoking the runner.
- Deterministic work (rollups, coverage matrices, dedup application, report build,
  structural report audit, summary counts) executes in Python, not the LLM.
- The HTML report is produced by script as a first-class deterministic phase, and
  its completeness/accuracy is audited before the run closes.

**Non-Goals**

- Changing the APD framework, the nine security lenses, the finding/capability
  schema, or the domain-pack mechanism.
- Changing what findings are produced — only *how* the run is orchestrated and how
  synthesis/report are assembled. The decomposed pipeline must reproduce equivalent
  authoritative outputs (modulo deterministic ordering).

## 3. Decisions (resolved during brainstorming)

| Decision | Choice |
|---|---|
| Restructure depth | A (behavioral hardening) **then** B (decompose heavy contexts) content changes |
| Resume model | Fully automatic |
| Orchestration substrate | **Full C** — Workflow script is the sole runner; orchestrator agent retired to a shim |
| Report generator | **Reuse existing** `apd-gauntlet build-report`; re-wire to a deterministic workflow phase |
| Report auditor | **New** — Python structural check + LLM semantic agent (does not exist today) |
| Auditor authority | **Gate + auto-remediate loop** (cap N≈2), then surface remaining discrepancies non-blocking |
| Synthesizer | **Kept as a working fallback** if the decomposed 5a–5e path fails irrecoverably |

## 4. Architecture — Workflow script as the sole runner

The orchestrator's lifecycle logic moves into `.claude/workflows/apd-gauntlet.js`,
a deterministic Workflow script. The script's retained state is only schema'd
receipts, so the "context that lives the whole run" problem disappears. Every unit
of real work happens in a fresh, isolated agent context or a Python subprocess.

Input is `.apd-run.yaml` (passed as the workflow's `args`): `run_id`, `domain`,
`taxonomies`, `threat_model`, `crown_jewels`, `attacker_positions`, `code_recon`.

```
args = .apd-run.yaml  →  Workflow runner (.claude/workflows/apd-gauntlet.js)
  Phase 0   setup            Bash:  init-run, build-domain-skill, validate-domain
  Phase 1   intake           agent() → receipt
  Phase 1.5 code-recon       agent() (gated on code_recon)
  Phase 1.6 tm-recon         agent() (gated on threat_model / TM detection)
  Phase 2   tier-1 (×3)      parallel(agent×3) → receipts; Bash: validate --tier 10 --errors-only
  Phase 3   tier-2 (×3)      parallel(agent×3);            Bash: validate --tier 20 --errors-only
  Phase 4   tier-3 (×3)      parallel(agent×3);            Bash: validate --tier 30 --errors-only
  Phase 5   synthesis+report DECOMPOSED (see §7)
  Phase 5.5 tmeval           agent() (gated; parallel with 5.6)
  Phase 5.6 apath            agent() (gated; parallel with 5.5)
  Phase 6   closeout         Bash:  apd-gauntlet summarize  (no LLM)
```

The orchestrator `.md` remains in-repo only as a thin deprecation note pointing at
the workflow, so existing docs/muscle-memory do not break.

## 5. Receipt contract — the core leak fix

Every `agent()` call returns a **schema-validated receipt, never prose**. The
workflow retains only this:

```js
const RECEIPT = {
  type: 'object',
  required: ['status', 'outputs', 'counts'],
  properties: {
    status:  { enum: ['ok', 'blocked', 'error'] },
    outputs: { type: 'array', items: { /* {path, schema_valid} */ } },
    counts:  { /* findings_by_severity, capabilities_by_maturity, blocked */ },
    errors:  { type: 'array', items: { /* {path, message} */ } }, // only on failure
  },
}
```

Each specialist/intake/recon `.md` gains an explicit clause: **"Your final message
is a receipt only: status, files written, and counts. Do NOT restate findings or
capabilities."** Today none have this, so they return full prose summaries that the
driver accumulates. This single change removes most of the orchestrator-side leak.

## 6. Resume — automatic, belt-and-suspenders

- **Same-session:** `Workflow({scriptPath, resumeFromRunId})` replays completed
  `agent()` calls from cache instantly. Zero user action.
- **Cross-session (new chat):** every phase is wrapped in an idempotency guard —
  `if (await phaseDone(dir, paths)) skip` — where `phaseDone` checks the output
  files exist and pass `validate --schema-only --errors-only`. A brand-new session
  re-running the workflow skips everything already on disk and finishes only what
  is missing.

The run directory **is** the checkpoint ledger. A small `run-state.yaml` breadcrumb
(phase → status → timestamp-from-args) is written for human visibility, but
correctness depends on the output files + validation, not on the breadcrumb.

`blocked` findings remain first-class data, never failures, and never trigger
re-dispatch with identical inputs.

## 7. Phase 5 — Synthesis + Report (fully decomposed)

The single 6.5k-read / 9k-write synthesizer context splits into units, only the
ones marked **LLM** consume a model context:

```
  5a  cluster-candidates       Python   18 files (streamed) → small candidate groups
  5b  apd-cluster-adjudicator  LLM      candidate records only → merge/link/separate decisions + merged prose
  5c  apply-clusters           Python   decisions + raw files → deduped-findings.yaml, deduped-capabilities.yaml
  5d  rollup                   Python   deduped → nist-coverage, attack-exposure, apd-coverage-matrix,
                                                  cwe/owasp/d3fend-coverage
  5e  apd-report-writer        LLM      deduped + COMPACT rollups → advisory-report.md, report-data.yaml
  5f  build-report             Python   (EXISTING) report-data.yaml → report-html/   ← re-wired out of synthesizer
  ┌─ 5g  REPORT AUDIT LOOP (gate + auto-remediate, cap N≈2) ───────────────────────┐
  │   audit-report             Python   structural: ID coverage, count parity,
  │                                     data.js ↔ YAML drift → report-audit.yaml
  │   apd-report-auditor       LLM      semantic: compact audit + rendered prose → faithfulness findings
  │   if fail → feed COMPACT critique back to 5e (and/or 5f), rebuild, re-audit
  │   after N tries → surface remaining discrepancies (non-blocking) and continue
  └─────────────────────────────────────────────────────────────────────────────────┘
```

### 7.1 Per-step responsibilities

- **5a `cluster-candidates` (Python).** Mechanically detect candidate clusters via
  the three signals the synthesizer spec already defines: evidence-locator overlap,
  title token similarity (component + concern verb), and reciprocal
  `related_concerns`. Stream the 18 files; emit only the candidate groups (IDs +
  the minimal fields needed for adjudication) to `40-synthesis/cluster-candidates.yaml`.
- **5b `apd-cluster-adjudicator` (LLM).** Reads only `cluster-candidates.yaml` and
  the specific candidate records (kilobytes, not the whole corpus) + the framework /
  finding-schema skills. Applies the merge / link / separate disposition rule
  (bias to link on ambiguity), and for merges writes the rewritten merged
  `summary` / `detail` / combined `recommendation` and `lens_perspectives`. Emits
  `40-synthesis/cluster-decisions.yaml` (decisions + merged prose only).
- **5c `apply-clusters` (Python).** Applies decisions deterministically: copies
  unchanged records, builds merged records from the adjudicator's prose + the union
  of NIST/ATT&CK mappings + highest severity + `merged_from`, records links via
  `cross_references`, downgrades stale capabilities. Writes the large
  `deduped-findings.yaml` / `deduped-capabilities.yaml` — never built up in a model
  window. Also writes `rejected-records.yaml` and `severity-disagreements.yaml`
  (mechanical: highest-severity-wins; rationale prose comes from the adjudicator
  when present).
- **5d `rollup` (Python).** Pure aggregation over the deduped files: `nist-coverage.yaml`,
  `attack-exposure.yaml`, `apd-coverage-matrix.yaml`, and (when declared)
  `cwe-coverage.yaml`, `owasp-coverage.yaml`, `d3fend-coverage.yaml`. Roll up only
  what records cite; never synthesize coverage from reference data. Matches existing
  `analyze-attack-paths` / `parse-threat-model` / `summarize` Python precedent.
- **5e `apd-report-writer` (LLM).** Fresh context. Reads `deduped-findings.yaml`
  (for the §4 Findings narrative and headline ranking) + the **compact** rollup
  YAMLs (not raw specialist files) + the contradiction/severity annex files.
  Produces `advisory-report.md` (the 10-section structure) and `report-data.yaml`
  (editorial prose blocks for the HTML report).
- **5f `build-report` (Python, EXISTING).** `apd-gauntlet build-report <run_dir>`
  consumes `report-data.yaml` (algorithmic fallback if absent) and emits
  `report-html/`. Re-wired from a trailing synthesizer step to a first-class
  workflow phase invoked via Bash.
- **5g report audit loop.**
  - `audit-report` (Python): structural completeness/accuracy — every finding /
    capability / coverage row in the authoritative YAMLs appears in `data.js`;
    severity/maturity counts in the rendered data match `summarize`; no
    data.js ↔ YAML drift. Emits compact `40-synthesis/report-audit.yaml`.
  - `apd-report-auditor` (LLM): reads only the compact `report-audit.yaml` + the
    rendered prose; judges semantic faithfulness (no misleading severity framing,
    no material omission, no invented content). Emits faithfulness findings.
  - **Gate + auto-remediate:** if either fails, feed the auditor's *compact*
    critique back to 5e (regenerate `report-data.yaml`) and/or 5f (rebuild), then
    re-audit. Cap at N≈2 iterations. Each retry is a small fresh context. After N,
    surface remaining discrepancies to the user (non-blocking) so the run still
    completes — consistent with the "complete with minimal user input" goal.

### 7.2 Synthesizer fallback

`apd-synthesizer` is **kept fully functional and maintained** as a fallback. If the
decomposed path fails irrecoverably (a new Python command errors out, or 5b/5e fail
repeatedly), the workflow invokes the legacy single-context synthesizer to produce
the synthesis outputs, accepting the token risk as a last resort. The decomposed
path is the default; the synthesizer is the safety net. Trigger conditions and the
fallback dispatch are encoded in the workflow script and logged in `run-state.yaml`.

## 8. Specialist output bounding (defense in depth)

So a single specialist cannot overrun its own context on a large SUT:

- Soft per-severity caps on emitted findings, with an explicit, **non-silent**
  truncation finding ("N lower-severity findings omitted; re-run with a focus
  hint") per the evidence-discipline "no silent caps" rule.
- Reinforce honoring the intake relevance table: read only `primary` / `secondary`
  artifacts for the lens, not all of `inputs/`.

## 9. CLI changes

- `validate`: add `--errors-only` (suppress pass lines) and `--tier <dir>` (scope to
  one tier directory); keep `--json`. The workflow consumes exit code + compact
  errors only.
- New commands: `cluster-candidates`, `apply-clusters`, `rollup`, `audit-report`.
- Reuse existing `summarize` for Phase 6 closeout (no LLM counting).

## 10. Component inventory

**Reused, re-wired (no build):** `build-report` + `tools/apd_gauntlet/report/`
package (→ workflow Bash phase 5f) · `summarize` (→ closeout) · `validate` (+flags).

**New Python CLI:** `cluster-candidates` · `apply-clusters` · `rollup` ·
`audit-report` · `validate --errors-only --tier`.

**New agents:** `apd-cluster-adjudicator` · `apd-report-writer` · `apd-report-auditor`.

**Kept as fallback:** `apd-synthesizer` (decomposed path is default; synthesizer is
the safety net).

**Retired → deprecation shim:** `apd-orchestrator` (the workflow is the runner).

**New runner:** `.claude/workflows/apd-gauntlet.js`.

## 11. Migration & validation

- The three existing runs in `runs/` become regression fixtures. The decomposed
  pipeline (5a–5e) must reproduce equivalent `deduped-findings.yaml` /
  `deduped-capabilities.yaml` / coverage YAMLs versus the committed golden outputs,
  allowing for deterministic ordering differences.
- New Python commands get unit tests against those runs.
- The orchestrator `.md` becomes a deprecation shim; the synthesizer `.md` stays in
  the agent lint/validation set as a maintained fallback.
- `pytest` + `apd-gauntlet validate` over each fixture run must remain clean.

## 12. Token-budget rationale

| Context | Before | After |
|---|---|---|
| Run driver | LLM orchestrator holding whole-run prose + 3× full validate dumps | Workflow script holding only receipts |
| Dedup/cluster | Reads all 18 files, writes 6,940-line file | Python candidates + LLM reading only candidates + Python apply |
| Coverage rollups | In the synthesizer's LLM context | Python (`rollup`) |
| Advisory + report-data | Same context as dedup | Fresh `report-writer` reading compact rollups |
| HTML build | Trailing call inside synthesizer LLM context | Python phase (`build-report`) |
| Report audit | (did not exist) | Python structural + small LLM semantic, compact critique loop |
| Closeout counts | LLM | Python (`summarize`) |

Net: no context holds the whole corpus; the driver holds only receipts; an
interrupted run resumes automatically.

## 13. Risks / open questions

- **Workflow tool availability.** Full-C ties the canonical runner to the Workflow
  primitive. Mitigated by the maintained `apd-synthesizer` fallback for the heaviest
  LLM step; the rest is Python + standalone agents that also work under manual
  dispatch.
- **Cross-session resume fidelity.** `resumeFromRunId` is same-session only;
  cross-session relies on the file-existence + validation guards. The guards must be
  conservative (treat schema-invalid output as not-done) to avoid resuming on a
  half-written file.
- **Adjudicator candidate sizing.** If `cluster-candidates` over-groups, 5b's
  context could still grow. The Python pre-pass must bound candidate group size and
  split large groups.
- **Golden-output equivalence.** Deterministic Python ordering may differ from the
  current LLM-authored ordering; regression comparison must normalize ordering
  before diffing.
