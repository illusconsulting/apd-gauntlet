# Token-Resilience Plan 3 — Workflow Runner (C) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship `.claude/workflows/apd-gauntlet.js` — the deterministic workflow runner (design option C) that replaces the LLM `apd-orchestrator` — plus the testable Python deferred items from Plan 2. The runner honors the workflow-tool primitive constraints (no FS / shell / Node / time / random APIs in the script; ALL I/O via dispatched agents), realizes the full phase map (setup → intake → gated recon → 3 parallel tiers → decomposed Phase 5 → gated audit auto-remediate loop cap N=2 → tmeval/apath → closeout), branches on the typed signals (`apply-clusters` exit 2 = `AdjudicationMissing`; `audit-report` exit 1 = audit FAIL), dispatches the `apd-synthesizer` fallback on irrecoverable decomposed-pipeline failure, and resumes via the harness `resumeFromRunId` cache (same-session) + agent-internal idempotency guards (cross-session). The Python deferred items: wire `nist-coverage.yaml`/`attack-exposure.yaml`/`apd-coverage-matrix.yaml` into `validate.SYNTHESIS_ROLLUPS`; regenerate the 3 committed legacy `runs/` coverage to the array shape (preserving the report-transform legacy-shape tolerance tests via a frozen fixture); strengthen `audit-report` to compare the rendered `nist_rollup`. The `apd-orchestrator` is retired to a deprecation shim.

**Architecture:** The runner is a single plain-JS file `.claude/workflows/apd-gauntlet.js`. It begins with a pure-literal `export const meta = {name, description, phases}` block (the structural-test pins), then defines a `RECEIPT` schema constant mirroring `schemas/agent-receipt.schema.json` EXACTLY, two reusable step helpers (`pyStep(cmd, opts)` dispatches a general-purpose Bash agent that runs `apd-gauntlet <cmd> <runDir>` behind an idempotency guard and returns a RECEIPT; `llmStep(prompt, opts)` dispatches a repo `agentType`), and the per-`phase()` body. Every command/file-check is performed by a dispatched `agent()`; the script itself never touches the filesystem or a shell. The decomposed Phase 5 (5a–5g) is strictly sequential; the three lens tiers and the post-5g tmeval/apath pair use `parallel()` barriers. The audit loop and synthesizer fallback are plain in-script control flow over `pyStep`/`llmStep` return values. Because the JS cannot run under plain `node` (it needs the Workflow harness) and CI has no Node step, the runner is verified by a pure-Python structural pytest (modeled on `tests/test_orchestrator_topology.py`) that parses the file as text and asserts the meta block, phase pins, agentType resolution against `.claude/agents/`, CLI-command resolution against the live Click registry, RECEIPT-field fidelity against the schema, and the loop-cap literal — plus a documented manual end-to-end run.

**Tech Stack:** Plain JavaScript (the Workflow primitive; NOT TypeScript, NOT Node-runnable standalone) for the runner. Python 3.10+, `click` (CLI), `jsonschema` (Draft 2020-12) + `referencing.Registry`, `PyYAML` (`yaml.safe_dump(sort_keys=False)`), `pytest` + `click.testing.CliRunner` for the tests and the deferred-Python work. `ruff`, `mypy`, `markdownlint` (CI globs `.claude/**/*.md` + `docs/**/*.md`, plans excluded), `apd-gauntlet lint-agents`. Source under `tools/apd_gauntlet/`; tests under `tests/`.

**Reference:** Design doc `docs/superpowers/specs/2026-05-29-apd-token-resilience-design.md` (§4 architecture / phase-map, §5 receipt contract, §6 resume, §7 Phase-5 decomposition, §7.2 synthesizer fallback, §10 component inventory, §13 risks). Conventions inherited from `docs/superpowers/plans/2026-05-29-token-resilience-plan1-foundations.md` (Plan 1: `validate --errors-only/--tier`; `schemas/agent-receipt.schema.json`; receipt + output-bounding lint rules) and `docs/superpowers/plans/2026-05-29-token-resilience-plan2-synthesis-decomposition.md` (Plan 2: `synthesis/` package; `cluster-candidates`/`apply-clusters`/`rollup`/`audit-report` commands; `apd-cluster-adjudicator`/`apd-report-writer`/`apd-report-auditor` agents; `build-report` re-wired; `*-doc` wrapper schemas exist; nist/attack/matrix wiring + legacy-runs regeneration + audit strengthening explicitly deferred to Plan 3). This is Plan 3 of 3 (the FINAL plan).

---

## File Structure

| Path | Responsibility | Action |
|---|---|---|
| `.claude/workflows/apd-gauntlet.js` | The deterministic workflow runner: meta block + RECEIPT constant + `pyStep`/`llmStep` helpers + the full phase body (setup/intake/recon gates, 3 parallel tiers + per-tier validate gate, full pre-Phase-5 validate gate, decomposed 5a–5g, audit auto-remediate loop cap N=2, synthesizer fallback dispatch, parallel tmeval/apath, closeout) | Create |
| `tools/apd_gauntlet/validate.py` | Wire the 3 coverage-rollup filenames into `SYNTHESIS_ROLLUPS` (nist/attack/matrix → `*-doc` wrapper schemas), replacing the Plan-2 deferral NOTE block | Modify |
| `tools/apd_gauntlet/synthesis/audit.py` | Add `nist_rollup_parity` check: recompute `build_apd_data(load_run(run_dir))["nist_rollup"]` and compare family-level `{family, covered, gapped, both}` + row count against `parsed["nist_rollup"]`; hard FAIL on mismatch, soft (non-blocking) on transform exception. Keep the existing `id_coverage_nist` subset check unchanged | Modify |
| `runs/apd-20260527-crapi-owasp-api-top10/40-synthesis/{nist-coverage,attack-exposure,apd-coverage-matrix,cwe-coverage,owasp-coverage,d3fend-coverage}.yaml` | Regenerated array-shape coverage (via `apd-gauntlet rollup`) | Modify/Create |
| `runs/apd-20260527-authentik-identity-provider/40-synthesis/{...same 6 files...}` | Regenerated array-shape coverage | Modify/Create |
| `runs/apd-20260527-caldera-adversary-emulation/40-synthesis/{...same 6 files...}` | Regenerated array-shape coverage | Modify/Create |
| `tests/fixtures/legacy-coverage-shapes/40-synthesis/nist-coverage.yaml` | Frozen copy of the pre-regeneration crapi `nist-coverage.yaml` (legacy `coverage_by_family` dict shape) so `test_rollup_new_shape_counts_are_nonzero` keeps a real legacy specimen | Create |
| `tests/fixtures/legacy-coverage-shapes/40-synthesis/apd-coverage-matrix.yaml` | Frozen copy of the pre-regeneration crapi `apd-coverage-matrix.yaml` (legacy goal-keyed `coverage` Shape-B) for `test_matrix_new_shape_produces_artifact_component_rows` | Create |
| `tests/fixtures/legacy-coverage-shapes/40-synthesis/attack-exposure.yaml` | Frozen copy of the pre-regeneration crapi `attack-exposure.yaml` (legacy dict-keyed `techniques` shape) — kept for completeness alongside the other two coverage shapes | Create |
| `tests/fixtures/legacy-coverage-shapes/40-synthesis/deduped-findings.yaml` | Frozen copy of the crapi `deduped-findings.yaml` so the Shape-B matrix transform can resolve the `coverage` block's finding IDs to artifact (`tech_plan.md`) component rows without coupling to the live run | Create |
| (no loader module) | The two shape-coupled tests read the frozen fixtures directly via `yaml.safe_load` into a `MagicMock` (mirroring the existing `test_rollup_old_shape_uses_family_summary` / `test_matrix_old_shape_component_rows` pattern) — no loader change, no reflective `RunArtifacts` construction | (Not created) |
| `.claude/agents/apd-orchestrator.md` | Retire to a deprecation shim: replace lifecycle prose with a deprecation note pointing at the workflow runner; keep a trimmed "Historical topology" block so existing topology-test pins survive; keep receipt-exempt + markdownlint-clean | Modify |
| `plugin.json` | Bump `version` to `1.5.0` to match pyproject (closes the version-skew gap). Do NOT add a `workflows` key — there is no verified plugin-manifest schema for one, and a strict `additionalProperties:false` manifest would reject it; the Workflow tool discovers `.claude/workflows/` from the filesystem regardless | Modify |
| `tests/test_workflow_apd_gauntlet.py` | Structural pytest for the runner (meta block, phase pins, agentType resolution, CLI-command resolution, RECEIPT fidelity, loop-cap literal, synthesizer-fallback + typed-signal pins, orchestrator-not-an-agentType) | Create |
| `tests/test_orchestrator_deprecation.py` | Pin the orchestrator deprecation marker + pointer to `.claude/workflows/apd-gauntlet.js` | Create |
| `tests/test_synthesis_doc_wrappers.py` | Update: invert `test_coverage_wrappers_not_wired_yet` → `test_coverage_wrappers_now_wired`; extend `WIRED_WRAPPERS` to include the 3 coverage files | Modify |
| `tests/test_validate_legacy_runs.py` | Parametrized `validate <run_dir> --errors-only` over all 3 regenerated runs asserts exit 0 (Task A/B regression gate, complements the existing C-locale test) | Create |
| `tests/unit/report/test_transform_nist_rollup.py` | Re-point ONLY `test_rollup_new_shape_counts_are_nonzero` at the frozen legacy `coverage_by_family` specimen (the one test that asserts the legacy key). The four other tests — including the two that assert the `SC` family — stay green against the regenerated array-shape `example_run` and are NOT touched | Modify |
| `tests/unit/report/test_transform_apd_matrix.py` | Re-point ONLY `test_matrix_new_shape_produces_artifact_component_rows` at the frozen legacy goal-keyed `coverage` specimen (+ the frozen `deduped-findings.yaml`). The four other tests tolerate the array shape and are NOT touched | Modify |
| `tests/test_cli_audit_report.py` | Extend: nist_rollup_parity FAIL fixture (family counts diverge → audit-report exit 1), clean-run PASS case, transform-exception non-blocking soft case | Modify |

**Step-archetype notes.** Two dispatch archetypes back every phase. (1) PYTHON STEP — `pyStep(cmd, opts)` dispatches a GENERAL-PURPOSE agent (no `agentType`, so it carries Bash/Read/Write) whose fixed prompt template runs `apd-gauntlet <cmd> <runDir>` behind an idempotency guard and returns a `RECEIPT` whose `agent` field is `"pystep:" + cmd` (command identity, so the script can branch past the exit-code overloading where `validate`/`build-report`/`audit-report` all use exit 1) and whose `errors[0].message` on nonzero exit is `"exit=<N>; <stderr-tail>"`. (2) LLM STEP — `llmStep(prompt, {agentType: 'apd-...'})` dispatches a repo agent resolved from `.claude/agents/`. The auditor is the ONE dispatch done WITHOUT `{schema}` so `agent()` returns its free-text critique string (the loop variable lives in the script's resume cache, needs no new schema/file). The skip convention reuses `status: 'ok'` plus a sentinel `{path: '<phase>.skipped', schema_valid: true}` output entry — NO `agent-receipt.schema.json` change (real agents already emit the 3-status shape).

**Resolved decisions (grounding the tasks below):**
- *Legacy-runs resolution (the central Task-B risk):* Recon claimed "regenerate, stays green" — true for `test_validate_runs_under_c_locale` (which only runs `validate`, and `validate` never touches `report-html`), but FALSE for exactly TWO report-transform unit tests that pin the crapi fixture's LEGACY coverage shape: `tests/unit/report/test_transform_nist_rollup.py::test_rollup_new_shape_counts_are_nonzero` (asserts `nist_coverage.get("coverage_by_family") is not None` — the array shape replaces `coverage_by_family` with `controls`) and `tests/unit/report/test_transform_apd_matrix.py::test_matrix_new_shape_produces_artifact_component_rows` (asserts `apd_coverage_matrix.get("coverage") is not None` — the array shape uses a top-level `components` list). EMPIRICALLY VERIFIED by regenerating crapi in place (`build_rollups`) and running both suites: only those 2 tests fail; the other 9 pass. Plan 3 therefore (a) FREEZES the current legacy crapi coverage files into `tests/fixtures/legacy-coverage-shapes/` and re-points ONLY those 2 shape-coupled tests there, then (b) regenerates the 3 runs' coverage to array shape. This preserves the loader's documented multi-shape tolerance AND makes the runs validate-clean once nist/attack/matrix are wired. (Empirically verified: `build_rollups(runs/apd-20260527-crapi-owasp-api-top10)` → array shape → `validate --errors-only` exit 0; regenerated crapi families are `AC, AU, CM, CP, IA, IR, MP, SA, SC, SI, SR` — note `SC` IS present, `SC-8 Transmission Confidentiality and Integrity`, so the `SC`-family tests stay green and need NO change.)
- *report-html is NOT tracked:* `.gitignore` excludes `runs/*/40-synthesis/report-html/` for all 3 legacy runs (verified). So regeneration touches only the tracked coverage YAMLs; there is no committed `build-manifest.txt` to drift, and `audit.py::_source_hash_drift` is irrelevant to the committed state. We do NOT run `build-report`/`audit-report` as part of the migration (the recon's source_hash_drift concern applies only when report-html IS committed, which it is not for these runs). The example `examples/apd-20260601-claim-event-bus/expected/40-synthesis/report-html/` IS tracked and is the canonical audit fixture — untouched by Task B.
- *the .js is tested structurally, never executed in CI:* CI `python-tests.yml` has no Node step; node is a dev-only esbuild dep; and the script needs the Workflow harness (not plain `node`) to run. The structural pytest reads the file as text (mirrors `test_orchestrator_topology.py`) and pins the contract; the end-to-end run is a DOCUMENTED manual step (Task 8).
- *skip status:* reuse `status: 'ok'` + a `<phase>.skipped` sentinel output; no schema change.
- *auditor critique transport:* the auditor is dispatched WITHOUT `{schema}` so it returns its critique as a string; the loop branches on a `GATE: pass`/`GATE: fail` regex (open-question A in the design — Plan 3 takes the schema-less-string option for determinism + minimal surface).
- *typed signals:* `AdjudicationMissing` (apply-clusters exit 2) → retry 5b once then fallback; `audit-report` exit 1 → remediate loop (not fallback); `build-report` exit 1 surviving one 5e regenerate → fallback; any of {cluster-candidates, apply-clusters, rollup} `status:error` on command + one retry, or 5b/5e `status:error` on 2 consecutive dispatches → fallback. `status:blocked` (missing evidence) is NEVER re-dispatched identically — surfaced as data.
- *plugin.json version bump:* installed CLI on PATH is `1.4.0` while pyproject is `1.5.0`. There is NO `init-run` step in the workflow (the run is pre-scaffolded; see the setup-phase note in Task 1), so the version-skew guard is enforced OUT-OF-BAND: the manual e2e (Task 8) runs `pip install -e ".[dev]"` and asserts `apd-gauntlet --version == 1.5.0` BEFORE invoking the workflow. Bumping `plugin.json` version to `1.5.0` aligns the manifest with pyproject so the installed CLI reports the version the (pre-workflow) scaffold + the design's framework_version expect.

---

## Task 1: Author the workflow runner `.claude/workflows/apd-gauntlet.js`

The runner is a single plain-JS file. This task creates the complete file content; Task 2 adds the structural pytest that pins it. The file is tracked (`.gitignore` excludes only `.claude/settings*.json`).

**Files:**
- Create: `.claude/workflows/apd-gauntlet.js`

- [ ] **Step 1: Create the runner file with the complete content below**

Create `.claude/workflows/apd-gauntlet.js`:

```javascript
// apd-gauntlet.js — deterministic APD gauntlet workflow runner (design option C).
//
// Replaces the retired apd-orchestrator LLM agent. The Workflow primitive gives
// this script NO filesystem, NO shell, NO Node API, and NO time/random APIs.
// Therefore EVERY command and every file/idempotency check is performed by a
// DISPATCHED agent: pyStep() dispatches a general-purpose Bash agent that runs
// `apd-gauntlet <cmd> <runDir>`; llmStep() dispatches a repo agent resolved from
// .claude/agents/. The script branches only on the values those agents return.
//
// RESUME (design §6, two layers):
//  - Same-session: Workflow({scriptPath, resumeFromRunId}) replays every
//    completed agent() call from the harness cache. The only script-side
//    requirement is a DISTINCT opts.label per logical dispatch (retries and
//    remediate attempts use label suffixes so the cache does not replay a
//    prior failure).
//  - Cross-session (fresh chat, cache gone): correctness rests on the
//    agent-internal IDEMPOTENCY GUARD embedded verbatim in every step prompt —
//    each agent checks whether its outputs already exist AND validate, and
//    returns an ok+skip receipt cheaply if so. Conservatism: a missing /
//    schema-invalid / half-written file is treated as NOT-DONE.
//
// SKIP CONVENTION: agent-receipt.schema.json has no 'skipped' status. An
// idempotent skip returns status:'ok' with every expected output marked
// schema_valid:true PLUS a sentinel {path:'<phase>.skipped', schema_valid:true}.
// The script does not need to distinguish skip from fresh — both are ok.

export const meta = {
  name: 'apd-gauntlet',
  description: 'Deterministic APD gauntlet runner (replaces apd-orchestrator); receipt-only dispatch + decomposed synthesis + gated report audit + synthesizer fallback.',
  phases: [
    'setup', 'intake', 'code-recon', 'tm-recon',
    'tier-1', 'tier-2', 'tier-3',
    'synthesis-cluster', 'synthesis-adjudicate', 'synthesis-apply',
    'synthesis-rollup', 'synthesis-fallback',
    'synthesis-report', 'synthesis-build', 'synthesis-audit',
    'tmeval', 'apath', 'closeout',
  ],
};

// RECEIPT — mirrors schemas/agent-receipt.schema.json EXACTLY so
// agent(prompt, {schema: RECEIPT}) validation matches what agents already emit.
const RECEIPT = {
  type: 'object',
  additionalProperties: false,
  required: ['agent', 'status', 'outputs', 'counts'],
  properties: {
    agent: { type: 'string', minLength: 1 },
    status: { enum: ['ok', 'blocked', 'error'] },
    outputs: {
      type: 'array',
      items: {
        type: 'object',
        additionalProperties: false,
        required: ['path', 'schema_valid'],
        properties: {
          path: { type: 'string', minLength: 1 },
          schema_valid: { type: 'boolean' },
        },
      },
    },
    counts: {
      type: 'object',
      additionalProperties: false,
      properties: {
        findings_by_severity: { type: 'object', additionalProperties: { type: 'integer', minimum: 0 } },
        capabilities_by_maturity: { type: 'object', additionalProperties: { type: 'integer', minimum: 0 } },
        blocked: { type: 'integer', minimum: 0 },
      },
    },
    errors: {
      type: 'array',
      items: {
        type: 'object',
        additionalProperties: false,
        required: ['path', 'message'],
        properties: {
          path: { type: 'string', minLength: 1 },
          message: { type: 'string', minLength: 1 },
        },
      },
    },
  },
};

// args IS .apd-run.yaml (run-config.schema.json). String concat only — no FS.
const runDir = 'runs/' + args.run_id;

// ---------------------------------------------------------------------------
// IDEMPOTENCY GUARD text — embedded verbatim as the FIRST instruction of every
// step prompt (the cross-session resume guard; design §6/§13).
// ---------------------------------------------------------------------------
// validateScope carries ONLY the positional run/subdir PATH; validateFlags
// carries any trailing option(s) (e.g. '--tier 10-trustworthiness'). guard()
// injects '--schema-only --errors-only' exactly ONCE, then appends the path,
// then the caller's extra flags — so the rendered command is always
// `validate --schema-only --errors-only <path> [<extra flags>]` with no
// duplicated flags and no path/flag interleaving (I1).
function guard(outputsList, validateScope, validateFlags) {
  const cmd = 'apd-gauntlet validate --schema-only --errors-only ' + validateScope +
    (validateFlags ? ' ' + validateFlags : '');
  return [
    'IDEMPOTENCY GUARD (run this FIRST):',
    'Check whether this phase\'s outputs already exist AND are valid.',
    'The expected outputs are: ' + outputsList + '.',
    'Run `' + cmd + '`.',
    'If EVERY expected output file exists AND that validate command exits 0,',
    'DO NOT redo the work: return a receipt with status:ok, one outputs[] entry',
    'per expected path with schema_valid:true, PLUS a sentinel output entry',
    '{path:"' + '<phase>.skipped' + '", schema_valid:true}, and counts:{}.',
    'Treat ANY of {a file missing, validate exit nonzero, YAML that fails to parse,',
    'a zero-byte/half-written file} as NOT-DONE and perform the work.',
    'NEVER skip on a partial or schema-invalid file.',
  ].join(' ');
}

// ---------------------------------------------------------------------------
// pyStep — dispatch a general-purpose Bash agent to run a CLI command behind
// the guard, returning a RECEIPT whose agent field carries command identity
// ('pystep:<cmd>') and whose errors[0].message on nonzero exit is
// 'exit=<N>; <stderr-tail>' so the script recovers both the command and code.
// ---------------------------------------------------------------------------
// opts.noRunDir: this command does NOT take the run dir as its positional
//   (setup commands keyed by domain name, not run path).
// opts.positional: the literal positional to use instead of runDir (e.g.
//   args.domain for build-domain-skill/validate-domain).
// opts.validateScope / opts.validateFlags: the guard's positional path and any
//   trailing option (e.g. '--tier 10-trustworthiness'); never embed flags in
//   the scope string (I1).
function pyStep(cmd, opts) {
  opts = opts || {};
  const outputs = opts.outputs || ('expected ' + cmd + ' outputs under ' + runDir + '/40-synthesis/');
  const scope = opts.validateScope || runDir;
  const flags = opts.validateFlags || '';
  const cliArgs = opts.cliArgs || '';
  // Positional argument: runDir by default; opts.positional when set; none when noRunDir.
  const positional = opts.noRunDir ? (opts.positional || '') : (opts.positional || runDir);
  const invocation = ('apd-gauntlet ' + cmd +
    (positional ? ' ' + positional : '') +
    (cliArgs ? ' ' + cliArgs : '')).replace(/\s+/g, ' ').trim();
  const prompt = [
    guard(outputs, scope, flags),
    '',
    'You are a python-step worker for the apd-gauntlet workflow.',
    'WORK COMMAND (distinct from the GUARD CHECK above — run this ONLY if the guard determined NOT-DONE) — via Bash, run:',
    '  ' + invocation,
    'Capture the exit code and the last lines of stderr.',
    'Return ONLY a receipt conforming to schemas/agent-receipt.schema.json with:',
    '  agent: "pystep:' + cmd + '"',
    '  status: "ok" if exit==0, else "error"',
    '  outputs: one {path, schema_valid:true} per file the command wrote (or the skip sentinel if you short-circuited)',
    '  counts: {} (or blocked:N if the command reported blocked findings)',
    '  errors: on nonzero exit, [{path:"' + cmd + '", message:"exit=<N>; <stderr-tail>"}]',
    'NEVER summarize the file contents in prose — return the receipt only.',
  ].join('\n');
  return agent(prompt, {
    schema: RECEIPT,
    phase: opts.phase,
    label: opts.label || ('pystep-' + cmd),
  });
}

// ---------------------------------------------------------------------------
// llmStep — dispatch a repo agentType behind the guard, returning a RECEIPT.
// ---------------------------------------------------------------------------
function llmStep(agentType, instruction, opts) {
  opts = opts || {};
  const outputs = opts.outputs || ('the ' + agentType + ' output files under ' + runDir);
  const scope = opts.validateScope || runDir;
  const flags = opts.validateFlags || '';
  const prompt = [
    guard(outputs, scope, flags),
    '',
    instruction,
    'The run directory is ' + runDir + '. Return ONLY a receipt conforming to',
    'schemas/agent-receipt.schema.json as your final message — never prose.',
  ].join('\n');
  return agent(prompt, {
    agentType: agentType,
    schema: RECEIPT,
    phase: opts.phase,
    label: opts.label || agentType,
  });
}

// Decide whether a fallback to the legacy synthesizer is warranted.
function isErr(r) { return !r || r.status === 'error'; }

// ===========================================================================
// PHASE 0 — setup
// ===========================================================================
phase('setup');
log('apd-gauntlet runner: setup for ' + args.run_id + ' (domain=' + args.domain + ')');
// NOTE: NO init-run here. Per design §4, `args` IS the run's .apd-run.yaml — the
// run is ALREADY scaffolded (runs/<id>/inputs/ + .apd-run.yaml exist) BEFORE the
// workflow is invoked. init-run takes a BARE run_id positional + a REQUIRED
// --inputs and CREATES the run dir, so dispatching it here would be a
// chicken-and-egg with the idempotency guard (which validates the run that
// init-run would create). Instead, setup VALIDATES the existing scaffold and
// (re)builds the domain skill.
//
// 0a — validate the pre-existing scaffold (schema-only; confirms .apd-run.yaml +
// inputs/ are present and the run dir is well-formed). This pyStep targets the
// run dir as its positional (the default).
pyStep('validate', {
  phase: 'setup', label: 'validate-scaffold',
  cliArgs: '--schema-only --errors-only',
  outputs: runDir + '/.apd-run.yaml + runDir/inputs/ (pre-existing scaffold)',
  validateScope: runDir,
});
// 0b — build-domain-skill takes a BARE domain_name positional (NOT the run dir),
// so use noRunDir + positional=args.domain. --framework-version is a flag.
pyStep('build-domain-skill', {
  phase: 'setup', label: 'build-domain-skill',
  noRunDir: true, positional: args.domain,
  cliArgs: '--framework-version ' + args.framework_version,
  outputs: '.claude/skills/apd-domain/SKILL.md',
  validateScope: runDir,
});
// 0c — validate-domain also takes a BARE domain_name positional (read-only check).
pyStep('validate-domain', {
  phase: 'setup', label: 'validate-domain',
  noRunDir: true, positional: args.domain,
  outputs: 'domain pack ' + args.domain + ' (read-only check)',
  validateScope: runDir,
});

// ===========================================================================
// PHASE 1 — intake
// ===========================================================================
phase('intake');
llmStep('apd-intake',
  'Analyze ' + runDir + '/inputs and emit 00-context/context-brief.md' +
  (Array.isArray(args.crown_jewels) && args.crown_jewels.length
    ? ' plus 00-context/asset-inventory.yaml (crown_jewels are declared).'
    : '.'),
  { phase: 'intake', label: 'intake', validateScope: runDir + '/00-context',
    outputs: runDir + '/00-context/context-brief.md' +
      (Array.isArray(args.crown_jewels) && args.crown_jewels.length
        ? ', ' + runDir + '/00-context/asset-inventory.yaml' : '') });

// ===========================================================================
// PHASE 1.5 — code-recon (gate on args.code_recon)
// ===========================================================================
phase('code-recon');
if (args.code_recon && args.code_recon !== 'disabled') {
  const cr = llmStep('apd-code-recon',
    'Run code reconnaissance for the run; emit 00-context/code-evidence-index.yaml ' +
    'OR (when code_recon==auto and CBM is unreachable) 00-context/code-recon-skipped.md.',
    { phase: 'code-recon', label: 'code-recon',
      validateScope: runDir + '/00-context',
      outputs: runDir + '/00-context/code-evidence-index.yaml (or code-recon-skipped.md)' });
  // disposition mirrors the orchestrator: enabled -> HALT on error; auto -> tolerate skip.
  // HALT is via a THROWN Error (not a bare top-level `return;`, which is a
  // SyntaxError in an ES module unless the harness happens to wrap the body —
  // unverified). A thrown Error in the async workflow body aborts the run
  // cleanly and is valid JS regardless of how the harness invokes the script (I2).
  if (args.code_recon === 'enabled' && isErr(cr)) {
    log('code-recon: status:error under code_recon=enabled — HALT (fix CBM or set auto/disabled).');
    throw new Error('Phase 1.5 code-recon failed with code_recon=enabled; aborting run — ' +
      'fix CBM availability or set code_recon to auto/disabled.');
  }
} else {
  log('code-recon: disabled — skipping Phase 1.5.');
}

// ===========================================================================
// PHASE 1.6 — tm-recon (gate on args.threat_model)
// ===========================================================================
phase('tm-recon');
if (args.threat_model) {
  llmStep('apd-threat-model-recon',
    'Parse + enrich the threat model at ' + args.threat_model + ' (run apd-gauntlet ' +
    'parse-threat-model internally as your agent contract specifies); emit ' +
    '00-context/threat-model-normalized.yaml.',
    { phase: 'tm-recon', label: 'tm-recon',
      validateScope: runDir + '/00-context',
      outputs: runDir + '/00-context/threat-model-normalized.yaml' });
} else {
  log('tm-recon: no threat_model declared — skipping Phase 1.6.');
}

// ===========================================================================
// Tier helper: parallel lens dispatch + per-lens 2-retry + tier validate gate.
// ===========================================================================
function runTier(phaseName, tierDir, lenses) {
  phase(phaseName);
  // parallel(thunks) resolves to a positionally-ordered array aligned to thunk
  // order (a failed thunk -> null at its index), so receipts[i] maps to lenses[i]
  // in the retry loop below. This ordered-array return is the standard
  // Workflow-tool contract.
  const receipts = parallel(lenses.map(function (lens) {
    return function () {
      return llmStep('apd-' + lens,
        'Analyze the ' + lens + ' lens; emit ' + tierDir + '/' + lens +
        '.findings.yaml and ' + tierDir + '/' + lens + '.capabilities.yaml.',
        { phase: phaseName, label: lens,
          validateScope: runDir, validateFlags: '--tier ' + tierDir,
          outputs: tierDir + '/' + lens + '.findings.yaml, ' + tierDir + '/' + lens + '.capabilities.yaml' });
    };
  }));
  // Inspect each receipt after the barrier; null or error -> up to 2 retries.
  lenses.forEach(function (lens, i) {
    let r = receipts[i];
    for (let k = 1; k <= 2 && isErr(r); k++) {
      log('tier ' + tierDir + ': lens ' + lens + ' failed; retry ' + k + '/2.');
      r = llmStep('apd-' + lens,
        'Retry the ' + lens + ' lens; emit ' + tierDir + '/' + lens + '.findings.yaml and ' +
        tierDir + '/' + lens + '.capabilities.yaml.',
        { phase: phaseName, label: lens + '-retry-' + k,
          validateScope: runDir, validateFlags: '--tier ' + tierDir,
          outputs: tierDir + '/' + lens + '.findings.yaml, ' + tierDir + '/' + lens + '.capabilities.yaml' });
    }
  });
  // Tier-end gate. --tier SKIPS cross-file Pass 3; the full pre-Phase-5 gate covers that.
  // The CLI joins --tier to the run dir (target = run_dir / tier), so the gate
  // invocation is `validate runs/<id> --tier <tierDir> --errors-only` and the
  // guard's own validate is `validate --schema-only --errors-only runs/<id> --tier <tierDir>`.
  pyStep('validate', {
    phase: phaseName, label: 'validate-' + tierDir,
    cliArgs: '--tier ' + tierDir + ' --errors-only',
    outputs: 'tier ' + tierDir + ' records (read-only gate)',
    validateScope: runDir, validateFlags: '--tier ' + tierDir,
  });
}

// ===========================================================================
// PHASE 2/3/4 — the three parallel lens tiers
// ===========================================================================
runTier('tier-1', '10-trustworthiness', ['confidentiality', 'integrity', 'availability']);
runTier('tier-2', '20-scalability', ['distributed', 'resilient', 'ephemeral']);
runTier('tier-3', '30-auditability', ['authenticity', 'non-repudiation', 'immutability']);

// FULL pre-Phase-5 cross-file gate (--tier skips Pass 3; cluster-candidates
// must read a cross-file-clean corpus).
pyStep('validate', {
  phase: 'tier-3', label: 'validate-full-prephase5',
  cliArgs: '--errors-only',
  outputs: 'whole-run cross-file clean (read-only gate)',
  validateScope: runDir,
});

// ===========================================================================
// PHASE 5 — decomposed synthesis (strictly sequential 5a..5g).
// ===========================================================================
let fellBack = false;

// 5a cluster-candidates (Python).
phase('synthesis-cluster');
let cc = pyStep('cluster-candidates', {
  phase: 'synthesis-cluster', label: 'cluster-candidates',
  outputs: runDir + '/40-synthesis/cluster-candidates.yaml' });
if (isErr(cc)) {
  cc = pyStep('cluster-candidates', { phase: 'synthesis-cluster', label: 'cluster-candidates-retry-1',
    outputs: runDir + '/40-synthesis/cluster-candidates.yaml' });
  if (isErr(cc)) { fellBack = true; }
}

// 5b adjudicator (LLM).
let adjudicateErrStreak = 0;
if (!fellBack) {
  phase('synthesis-adjudicate');
  let adj = llmStep('apd-cluster-adjudicator',
    'Read ONLY 40-synthesis/cluster-candidates.yaml; emit 40-synthesis/cluster-decisions.yaml ' +
    '(with the _members map keyed by group_id).',
    { phase: 'synthesis-adjudicate', label: 'adjudicate',
      outputs: runDir + '/40-synthesis/cluster-decisions.yaml' });
  if (isErr(adj)) { adjudicateErrStreak = 1; }

  // 5c apply-clusters (Python) — typed signal AdjudicationMissing == exit 2.
  phase('synthesis-apply');
  let ap = pyStep('apply-clusters', { phase: 'synthesis-apply', label: 'apply-clusters',
    outputs: runDir + '/40-synthesis/deduped-findings.yaml, deduped-capabilities.yaml, rejected-records.yaml, severity-disagreements.yaml, contradictions.yaml' });
  const isAdjMissing = ap && ap.status === 'error' && ap.errors && ap.errors[0] &&
    /exit=2/.test(ap.errors[0].message);
  if (isAdjMissing) {
    // 5b did not produce a valid cluster-decisions.yaml. Re-dispatch 5b ONCE, then retry 5c.
    log('apply-clusters: AdjudicationMissing (exit 2) — re-running adjudicator once.');
    const adj2 = llmStep('apd-cluster-adjudicator',
      'Re-emit 40-synthesis/cluster-decisions.yaml (with the _members map). The prior attempt ' +
      'did not produce a valid decisions file.',
      { phase: 'synthesis-adjudicate', label: 'adjudicate-retry-1',
        outputs: runDir + '/40-synthesis/cluster-decisions.yaml' });
    if (isErr(adj2)) { adjudicateErrStreak = 2; }
    ap = pyStep('apply-clusters', { phase: 'synthesis-apply', label: 'apply-clusters-retry-1',
      outputs: runDir + '/40-synthesis/deduped-findings.yaml' });
    if (ap && ap.status === 'error' && ap.errors && ap.errors[0] && /exit=2/.test(ap.errors[0].message)) {
      log('apply-clusters: AdjudicationMissing persists after one adjudicator retry — fallback.');
      fellBack = true;
    } else if (isErr(ap)) {
      ap = pyStep('apply-clusters', { phase: 'synthesis-apply', label: 'apply-clusters-retry-2',
        outputs: runDir + '/40-synthesis/deduped-findings.yaml' });
      if (isErr(ap)) { fellBack = true; }
    }
  } else if (isErr(ap)) {
    ap = pyStep('apply-clusters', { phase: 'synthesis-apply', label: 'apply-clusters-retry-1b',
      outputs: runDir + '/40-synthesis/deduped-findings.yaml' });
    if (isErr(ap)) { fellBack = true; }
  }
  if (adjudicateErrStreak >= 2) { fellBack = true; }
}

// 5d rollup (Python). After this, the FULL validate covers nist/attack/matrix (Plan-3 wiring).
if (!fellBack) {
  phase('synthesis-rollup');
  let rl = pyStep('rollup', { phase: 'synthesis-rollup', label: 'rollup',
    outputs: runDir + '/40-synthesis/nist-coverage.yaml, attack-exposure.yaml, apd-coverage-matrix.yaml (+ declared-taxonomy coverage files)' });
  if (isErr(rl)) {
    rl = pyStep('rollup', { phase: 'synthesis-rollup', label: 'rollup-retry-1',
      outputs: runDir + '/40-synthesis/nist-coverage.yaml' });
    if (isErr(rl)) { fellBack = true; }
  }
}

// ===========================================================================
// SYNTHESIZER FALLBACK (design §7.2). workflow() cannot nest, so this is a
// direct agent() dispatch to apd-synthesizer (RECEIPT_EXEMPT; returns prose,
// dispatched WITHOUT schema). A tiny run-state breadcrumb is written first by
// a general-purpose Bash agent (the script has no FS).
// ===========================================================================
if (fellBack) {
  phase('synthesis-fallback');
  log('synthesis: decomposed pipeline failed irrecoverably — dispatching apd-synthesizer fallback.');
  agent(
    'Append a run-state.yaml breadcrumb to ' + runDir + '/40-synthesis/run-state.yaml using Bash: ' +
    'a YAML entry {phase: synthesis, decision: synthesizer-fallback, reason: decomposed-pipeline-failed}. ' +
    'This is advisory only. Return a one-line confirmation.',
    { phase: 'synthesis-fallback', label: 'run-state-fallback' });
  agent(
    'Run as the synthesis FALLBACK. The decomposed pipeline failed. Read the tier corpus under ' +
    runDir + ' and write ALL 40-synthesis YAMLs INCLUDING report-data.yaml, then STOP — do NOT ' +
    'build or audit the report (the workflow owns build + audit). Return your usual summary.',
    { agentType: 'apd-synthesizer', phase: 'synthesis-fallback', label: 'synthesizer-fallback' });
}

// ===========================================================================
// 5e report-writer (LLM) -> 5f build-report (Python) -> 5g audit loop (cap N=2).
// The workflow owns build + audit even in fallback.
// ===========================================================================
phase('synthesis-report');
llmStep('apd-report-writer',
  'Read 40-synthesis/deduped-findings.yaml + the COMPACT rollups + contradictions/' +
  'severity-disagreements; emit 40-synthesis/advisory-report.md + 40-synthesis/report-data.yaml.',
  { phase: 'synthesis-report', label: 'report-writer-attempt-0',
    outputs: runDir + '/40-synthesis/report-data.yaml, advisory-report.md' });

phase('synthesis-build');
let build = pyStep('build-report', { phase: 'synthesis-build', label: 'build-report-attempt-0',
  outputs: runDir + '/40-synthesis/report-html/data.js, build-manifest.txt' });
// build-report exit 1 surviving one 5e regenerate -> fallback (synthesizer rewrites report-data.yaml).
if (isErr(build) && !fellBack) {
  log('build-report: error — regenerating report-data via report-writer once.');
  llmStep('apd-report-writer',
    'Regenerate 40-synthesis/report-data.yaml + advisory-report.md (the prior build failed).',
    { phase: 'synthesis-report', label: 'report-writer-attempt-build-fix',
      outputs: runDir + '/40-synthesis/report-data.yaml' });
  build = pyStep('build-report', { phase: 'synthesis-build', label: 'build-report-attempt-build-fix',
    outputs: runDir + '/40-synthesis/report-html/data.js' });
  if (isErr(build)) {
    log('build-report: still failing — dispatching synthesizer fallback to rewrite report-data.yaml.');
    agent('Run as the synthesis FALLBACK and rewrite ' + runDir + '/40-synthesis/report-data.yaml ' +
      'from the tier corpus, then STOP.',
      { agentType: 'apd-synthesizer', phase: 'synthesis-build', label: 'synthesizer-fallback-build' });
    build = pyStep('build-report', { phase: 'synthesis-build', label: 'build-report-attempt-postfallback',
      outputs: runDir + '/40-synthesis/report-html/data.js' });
  }
}

// 5g audit loop — gate + auto-remediate, cap N=2 (3 attempts total).
phase('synthesis-audit');
let critique = null;
for (let i = 0; i <= 2; i++) {
  const audit = pyStep('audit-report', { phase: 'synthesis-audit', label: 'audit-report-attempt-' + i,
    outputs: runDir + '/40-synthesis/report-audit.yaml' });
  const auditorPrompt =
    'Read ONLY 40-synthesis/report-audit.yaml + the rendered advisory-report.md + report-data.yaml ' +
    'editorial blocks (NEVER data.js). Judge semantic faithfulness (misleading-severity / material-' +
    'omission / invented-content). Emit a BOUNDED critique: at most 8 lines, each ' +
    '{kind: misleading-severity|material-omission|invented-content, section: <N>, fix: <one line>}. ' +
    'End your message with the literal "GATE: pass" or "GATE: fail".' +
    (critique ? ' PRIOR CRITIQUE (verify it was addressed): ' + critique : '');
  // The auditor is the ONE dispatch WITHOUT {schema} -> agent() returns its critique STRING.
  const auditor = agent(auditorPrompt,
    { agentType: 'apd-report-auditor', phase: 'synthesis-audit', label: 'auditor-attempt-' + i });
  const structuralOk = audit && audit.status === 'ok';
  const semanticOk = typeof auditor === 'string' && /GATE:\s*pass/i.test(auditor);
  if (structuralOk && semanticOk) { break; }
  if (i === 2) {
    log('report audit: residual discrepancies after 2 remediations; surfacing non-blocking.');
    break;
  }
  critique = auditor;
  // Feed the compact critique back into 5e, then rebuild 5f.
  llmStep('apd-report-writer',
    'Address each item in this PRIOR AUDIT CRITIQUE and regenerate 40-synthesis/report-data.yaml + ' +
    'advisory-report.md accordingly. CRITIQUE: ' + critique,
    { phase: 'synthesis-report', label: 'report-writer-attempt-' + (i + 1),
      outputs: runDir + '/40-synthesis/report-data.yaml' });
  pyStep('build-report', { phase: 'synthesis-build', label: 'build-report-attempt-' + (i + 1),
    outputs: runDir + '/40-synthesis/report-html/data.js' });
}

// ===========================================================================
// PHASE 5.5 / 5.6 — tmeval + apath in parallel AFTER 5g.
// Both phase() literals are emitted up front (phase() is an advisory
// breadcrumb): phase('tmeval') for the evaluator branch and phase('apath') for
// the analyzer branch. This gives apath its OWN phase() literal (C1) so the
// structural test can pin `phase('apath')` directly, while the two thunks still
// run concurrently inside the single parallel() barrier.
// ===========================================================================
phase('tmeval');
phase('apath');
parallel([
  function () {
    if (args.threat_model) {
      return llmStep('apd-threat-model-evaluator',
        'Evaluate the run against 00-context/threat-model-normalized.yaml; emit ' +
        '40-synthesis/threat-model-coverage.yaml + tmeval findings.',
        { phase: 'tmeval', label: 'tmeval',
          outputs: runDir + '/40-synthesis/threat-model-coverage.yaml' });
    }
    log('tmeval: no threat_model — skipping Phase 5.5.');
    return null;
  },
  function () {
    if (Array.isArray(args.crown_jewels) && args.crown_jewels.length) {
      return llmStep('apd-attack-path-analyzer',
        'Run attack-path analysis (the analyzer runs apd-gauntlet analyze-attack-paths internally; ' +
        'exit 0 even on BuilderBlocked -> writes a disposition:blocked finding); emit the ' +
        '40-synthesis/asset-graph.yaml / attack-paths.yaml / defense-graph.yaml / ' +
        'attack-path.findings.yaml set.',
        { phase: 'apath', label: 'apath',
          outputs: runDir + '/40-synthesis/attack-path.findings.yaml' });
    }
    log('apath: crown_jewels empty/absent — Phase 5.6 disabled.');
    return null;
  },
]);

// ===========================================================================
// PHASE 6 — closeout.
// ===========================================================================
phase('closeout');
pyStep('summarize', { phase: 'closeout', label: 'summarize',
  outputs: runDir + ' run summary (read-only)' });
pyStep('validate', { phase: 'closeout', label: 'validate-final',
  cliArgs: '--errors-only', outputs: 'whole-run final clean (read-only assertion)',
  validateScope: runDir });
log('apd-gauntlet runner: complete for ' + args.run_id + '.');
```

**Runner notes (grounding the structural test + the harness contract):**

- *HALT is via a thrown Error, never a bare top-level `return;`.* A bare
  `return;` at module top level is a SyntaxError in an ES module unless the
  harness happens to wrap the body in a function — which is unverified. So every
  irrecoverable early-exit (the code_recon HALT under `code_recon=enabled`)
  throws an `Error` instead; a thrown Error in the async workflow body aborts the
  run cleanly and is valid JS regardless of how the harness invokes the script.
  The structural test pins this (`assert "throw new Error" in text` and asserts
  no bare top-level `return;`).
- *Setup does NOT call `init-run`.* The run is pre-scaffolded (`args` IS its
  `.apd-run.yaml`); the setup phase VALIDATES the existing scaffold via
  `pyStep('validate', ...)` and rebuilds the domain skill. `build-domain-skill`
  and `validate-domain` take a BARE `domain_name` positional (not the run dir),
  so they are dispatched with `noRunDir:true, positional: args.domain`.
- *No `validateScope` string ever embeds a flag.* `guard()` injects
  `--schema-only --errors-only` once and appends `opts.validateFlags` (e.g.
  `--tier 10-trustworthiness`) after the positional path. Tier gates therefore
  render `validate --schema-only --errors-only runs/<id> --tier <tierDir>` — the
  CLI joins `--tier` onto the run dir (`target = run_dir / tier`), so the
  positional must be the RUN dir, not the tier subdir.

- [ ] **Step 2: Confirm the file is tracked and not gitignored**

Run: `git check-ignore .claude/workflows/apd-gauntlet.js; echo "exit=$?"`
Expected: no output and `exit=1` (NOT ignored — `.gitignore` excludes only `.claude/settings*.json`).

- [ ] **Step 3: Commit the runner**

```bash
git add .claude/workflows/apd-gauntlet.js
git commit -m "feat(workflow): apd-gauntlet.js deterministic runner (replaces orchestrator)"
```

---

## Task 2: Structural pytest for the runner

The `.js` cannot run under CI (no Node step; needs the Workflow harness). This test reads the file AS TEXT and pins its contract — mirroring `tests/test_orchestrator_topology.py`. It uses the live Click registry as the source of truth for CLI commands and the on-disk `.claude/agents/` set for agentType resolution.

**Files:**
- Create: `tests/test_workflow_apd_gauntlet.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_workflow_apd_gauntlet.py`:

```python
"""Structural contract test for the workflow runner .claude/workflows/apd-gauntlet.js.

The runner is plain JS for the Workflow primitive; it cannot run under plain
node and CI has no Node step. We pin its contract by reading it AS TEXT
(mirrors tests/test_orchestrator_topology.py): meta block + phase pins +
agentType resolution against .claude/agents/ + CLI-command resolution against
the live Click registry + RECEIPT-field fidelity against the schema + the
audit loop-cap literal + the synthesizer-fallback and typed-signal pins.
"""
from __future__ import annotations

import json
import pathlib
import re

from apd_gauntlet.cli import main as cli

REPO = pathlib.Path(__file__).resolve().parent.parent
RUNNER = REPO / ".claude" / "workflows" / "apd-gauntlet.js"
AGENTS_DIR = REPO / ".claude" / "agents"
RECEIPT_SCHEMA = REPO / "schemas" / "agent-receipt.schema.json"

# Expanded §4/§7 phase pins (5a..5g surfaced). meta.phases lists every phase
# name. But the runner emits the three TIER phases DYNAMICALLY (runTier(name)
# calls phase(name) internally), so a literal `phase('tier-1')` never appears in
# the source — those three are pinned via the runTier(...) call tokens instead.
# Every OTHER phase is emitted by a direct `phase('X')` literal in the body.
EXPECTED_PHASES = [
    "setup", "intake", "code-recon", "tm-recon",
    "tier-1", "tier-2", "tier-3",
    "synthesis-cluster", "synthesis-adjudicate", "synthesis-apply",
    "synthesis-rollup", "synthesis-fallback",
    "synthesis-report", "synthesis-build", "synthesis-audit",
    "tmeval", "apath", "closeout",
]

# Phases emitted by a DIRECT `phase('X')` literal (checked as call literals).
DIRECT_PHASE_LITERALS = [
    "setup", "intake", "code-recon", "tm-recon",
    "synthesis-cluster", "synthesis-adjudicate", "synthesis-apply",
    "synthesis-rollup", "synthesis-fallback",
    "synthesis-report", "synthesis-build", "synthesis-audit",
    "tmeval", "apath", "closeout",
]

# Tier phases emitted DYNAMICALLY via runTier(name){ phase(name) } — checked via
# the runTier('tier-N', ...) call tokens, NOT via a `phase('tier-N')` literal.
TIER_PHASES_VIA_RUNTIER = ["tier-1", "tier-2", "tier-3"]


def _text() -> str:
    return RUNNER.read_text(encoding="utf-8")


def test_runner_file_exists() -> None:
    assert RUNNER.is_file(), f"missing runner at {RUNNER}"


def test_meta_block_is_pure_literal_first_export() -> None:
    text = _text()
    assert "export const meta = {" in text
    assert "name: 'apd-gauntlet'" in text
    assert "description:" in text
    assert "phases:" in text


def test_every_expected_phase_present_in_meta_phases() -> None:
    text = _text()
    # Bounded extraction of the phases:[...] array (meta is a pure literal).
    m = re.search(r"phases:\s*\[(.*?)\]", text, re.DOTALL)
    assert m, "phases:[...] array not found in meta"
    phases_blob = m.group(1)
    found = set(re.findall(r"'([^']+)'", phases_blob))
    for p in EXPECTED_PHASES:
        assert p in found, f"phase {p!r} missing from meta.phases"


def test_direct_phase_literals_invoked_in_body() -> None:
    """Every non-tier phase is emitted by a literal phase('X') call in the body."""
    text = _text()
    for p in DIRECT_PHASE_LITERALS:
        assert f"phase('{p}')" in text, f"phase('{p}') not invoked in body"


def test_tier_phases_invoked_via_runtier() -> None:
    """tier-1/2/3 are emitted dynamically by runTier(name){ phase(name) }, so they
    appear as runTier('tier-N', ...) call tokens, not as phase('tier-N') literals."""
    text = _text()
    for p in TIER_PHASES_VIA_RUNTIER:
        assert f"runTier('{p}'" in text, f"runTier('{p}', ...) call not found"
        # And confirm they are NOT (mistakenly) also emitted as direct literals,
        # which would mean the runner double-emits the phase.
        assert f"phase('{p}')" not in text, (
            f"tier phase {p} should be emitted via runTier(name), not a phase('{p}') literal"
        )


def test_every_meta_phase_is_emitted_one_way_or_the_other() -> None:
    """Union of the direct-literal set and the runTier tier set == meta.phases."""
    assert set(DIRECT_PHASE_LITERALS) | set(TIER_PHASES_VIA_RUNTIER) == set(EXPECTED_PHASES)


def _referenced_agent_types(text: str) -> set[str]:
    """All agentTypes the runner dispatches, from BOTH dispatch forms:
      - `llmStep('apd-foo', ...)`   — agent is the FIRST POSITIONAL arg
      - `agent(prompt, {agentType: 'apd-foo', ...})` — raw agentType opts key
    The dynamic lens dispatch is `llmStep('apd-' + lens, ...)`, which yields the
    fragment 'apd-' (a bare prefix); drop it and pin the concrete lens set
    separately so 'apd-' is never treated as a real agentType.
    """
    refs = set(re.findall(r"llmStep\('([^']+)'", text))
    refs |= set(re.findall(r"agentType:\s*'([^']+)'", text))
    refs.discard("apd-")  # the 'apd-' + lens concat fragment, not a real agent
    return refs


def test_every_agenttype_resolves_to_an_agent_file() -> None:
    text = _text()
    referenced = _referenced_agent_types(text)
    # The dynamic 'apd-' + lens concat must also resolve; pin the lens set.
    lenses = ["confidentiality", "integrity", "availability",
              "distributed", "resilient", "ephemeral",
              "authenticity", "non-repudiation", "immutability"]
    referenced |= {"apd-" + lens for lens in lenses}
    for at in referenced:
        assert (AGENTS_DIR / f"{at}.md").is_file(), f"agentType {at} has no .claude/agents/{at}.md"


def test_orchestrator_is_not_an_agenttype() -> None:
    text = _text()
    referenced = _referenced_agent_types(text)
    assert "apd-orchestrator" not in referenced, "orchestrator is retired; never dispatch it"


def test_expected_agent_set_is_referenced() -> None:
    text = _text()
    referenced = _referenced_agent_types(text)
    # The fixed (non-lens) dispatches the runner must name. apd-intake /
    # apd-code-recon / apd-threat-model-recon / apd-cluster-adjudicator /
    # apd-report-writer / apd-threat-model-evaluator / apd-attack-path-analyzer
    # go through llmStep('apd-...'); apd-report-auditor (schema-less) and
    # apd-synthesizer (fallback) go through raw agent(..., {agentType:'...'}).
    for at in ("apd-intake", "apd-code-recon", "apd-threat-model-recon",
               "apd-cluster-adjudicator", "apd-report-writer", "apd-report-auditor",
               "apd-threat-model-evaluator", "apd-attack-path-analyzer", "apd-synthesizer"):
        assert at in referenced, f"{at} not dispatched by the runner"


def test_every_cli_command_is_registered() -> None:
    text = _text()
    registered = set(cli.commands.keys())
    # The runner executes CLI commands ONLY via pyStep('<cmd>', ...); extract
    # exactly those command tokens. We deliberately do NOT scrape the broad
    # `apd-gauntlet <word>` regex: the runner's log()/comment/instruction prose
    # contains non-command tokens ('apd-gauntlet runner: setup', 'apd-gauntlet
    # workflow') that are not subcommands, and the recon-agent prose mentions
    # commands the agents run internally (parse-threat-model, analyze-attack-paths)
    # which the runner never invokes directly. pyStep('<cmd>') is the true
    # CLI-dispatch contract.
    cmds = set(re.findall(r"pyStep\('([a-z][a-z0-9-]+)'", text))
    assert cmds, "no pyStep('<cmd>') calls found — extraction regex drifted"
    for c in cmds:
        assert c in registered, f"pyStep references unregistered command {c!r}"


def test_referenced_commands_cover_the_pipeline() -> None:
    text = _text()
    # init-run is intentionally ABSENT: per design §4 the run is scaffolded
    # before the workflow runs (args IS .apd-run.yaml), so setup VALIDATES the
    # existing scaffold via pyStep('validate', ...) rather than creating it.
    for c in ("build-domain-skill", "validate-domain", "validate",
              "cluster-candidates", "apply-clusters", "rollup", "build-report",
              "audit-report", "summarize"):
        assert f"pyStep('{c}'" in text, f"pipeline command {c} not invoked via pyStep"
    assert "pyStep('init-run'" not in text, (
        "init-run must NOT be dispatched: the run is pre-scaffolded; setup validates it"
    )


def test_receipt_constant_matches_schema_required() -> None:
    text = _text()
    schema = json.loads(RECEIPT_SCHEMA.read_text(encoding="utf-8"))
    schema_required = set(schema["required"])
    m = re.search(r"required:\s*\[([^\]]*)\]", text)
    assert m, "RECEIPT required array not found"
    js_required = set(re.findall(r"'([^']+)'", m.group(1)))
    assert js_required == schema_required, (
        f"RECEIPT required {js_required} != schema required {schema_required}"
    )


def test_audit_loop_cap_literal_present() -> None:
    text = _text()
    # The cap is N=2 (3 attempts: initial + 2 remediations). Pin the literal so
    # it cannot regress silently.
    assert "i <= 2" in text, "audit loop cap (i <= 2) literal missing"


def test_typed_signals_and_fallback_pinned() -> None:
    text = _text()
    assert "/exit=2/" in text, "AdjudicationMissing (exit 2) branch missing"
    assert "synthesizer-fallback" in text, "synthesizer fallback label missing"
    assert "agentType: 'apd-synthesizer'" in text, "fallback must dispatch apd-synthesizer"


def test_skip_sentinel_convention_documented() -> None:
    text = _text()
    assert ".skipped" in text, "idempotent-skip sentinel convention missing"
```

- [ ] **Step 2: Run the test to verify it passes**

Run: `python3 -m pytest tests/test_workflow_apd_gauntlet.py -v`
Expected: PASS (all). If `test_every_cli_command_is_registered` fails, a `pyStep` references a command not in `set(apd_gauntlet.cli.main.commands.keys())` — fix the runner, not the test. If `test_every_agenttype_resolves_to_an_agent_file` fails, an `agentType` string lacks a `.claude/agents/<name>.md` — fix the runner.

- [ ] **Step 3: Commit**

```bash
git add tests/test_workflow_apd_gauntlet.py
git commit -m "test(workflow): structural pytest pins apd-gauntlet.js contract"
```

---

## Task 3 (Task A): Wire the 3 coverage rollups into `validate.SYNTHESIS_ROLLUPS`

Add exactly three filename→`*-doc` schema entries, replacing the Plan-2 deferral NOTE block at `validate.py` lines ~119-125. The `*-doc` wrapper schemas already exist (verified: `schemas/nist-coverage-doc.schema.json`, `attack-exposure-doc.schema.json`, `coverage-matrix-doc.schema.json`). This task wires them WITHOUT regenerating the legacy runs first, so Step 2 watches the C-locale test FAIL (proving the wiring bites); Task B then regenerates the runs.

**Files:**
- Modify: `tools/apd_gauntlet/validate.py`
- Modify: `tests/test_synthesis_doc_wrappers.py`

- [ ] **Step 1: Update the doc-wrappers test to expect the new wiring**

In `tests/test_synthesis_doc_wrappers.py`, REPLACE the `WIRED_WRAPPERS` block and the two tests `test_wired_wrappers_in_synthesis_rollups` / `test_coverage_wrappers_not_wired_yet` with the wired-state contract. Replace:

```python
# Wrappers that are globally wired into SYNTHESIS_ROLLUPS in Plan 2.
# nist-coverage / attack-exposure / apd-coverage-matrix are intentionally NOT wired yet —
# legacy runs/ predate the array format; global wiring deferred to Plan 3.
WIRED_WRAPPERS = {
    "severity-disagreements.yaml": "severity-disagreements-doc.schema.json",
    "contradictions.yaml": "contradictions-doc.schema.json",
}
```

with:

```python
# Plan 3 wires ALL five wrappers globally into SYNTHESIS_ROLLUPS.
WIRED_WRAPPERS = {
    "nist-coverage.yaml": "nist-coverage-doc.schema.json",
    "attack-exposure.yaml": "attack-exposure-doc.schema.json",
    "apd-coverage-matrix.yaml": "coverage-matrix-doc.schema.json",
    "severity-disagreements.yaml": "severity-disagreements-doc.schema.json",
    "contradictions.yaml": "contradictions-doc.schema.json",
}
```

Then DELETE the `test_coverage_wrappers_not_wired_yet` function in its entirety and REPLACE the `test_wired_wrappers_in_synthesis_rollups` docstring/body to drop the Plan-2 framing:

```python
def test_wired_wrappers_in_synthesis_rollups():
    """All five doc wrappers (nist/attack/matrix + sev-dis/contradictions) are wired (Plan 3)."""
    for filename, schema_name in WIRED_WRAPPERS.items():
        assert SYNTHESIS_ROLLUPS.get(filename) == schema_name, (
            f"{filename} should be wired to {schema_name} in SYNTHESIS_ROLLUPS"
        )
```

- [ ] **Step 2: Run the test to verify the new wiring assertions FAIL**

Run: `python3 -m pytest tests/test_synthesis_doc_wrappers.py::test_wired_wrappers_in_synthesis_rollups -v`
Expected: FAIL — `SYNTHESIS_ROLLUPS.get("nist-coverage.yaml")` is `None` (not yet wired).

- [ ] **Step 3: Wire the three filenames into `SYNTHESIS_ROLLUPS`**

In `tools/apd_gauntlet/validate.py`, REPLACE the deferral NOTE block (the comment block beginning `# NOTE (Plan 2): nist-coverage.yaml / attack-exposure.yaml / apd-coverage-matrix.yaml` through `# Plan 3 (workflow runner). See plan resolved-open-questions.`) with the three wired entries:

```python
    # Plan 3 — the three coverage rollups, now wired globally against their
    # array-shaped *-doc wrapper schemas. The legacy runs/ were regenerated to
    # the array shape via `apd-gauntlet rollup` (Plan 3 Task B), so this no
    # longer breaks validate on the committed runs. The matrix doc schema is
    # named coverage-matrix-doc.schema.json (NOT apd-coverage-matrix-doc); all
    # three map to the DOC wrappers (array-of-$ref), never the per-row schemas.
    "nist-coverage.yaml":          "nist-coverage-doc.schema.json",
    "attack-exposure.yaml":        "attack-exposure-doc.schema.json",
    "apd-coverage-matrix.yaml":    "coverage-matrix-doc.schema.json",
```

(Keep the immediately-following `# Plan 2 (I5) — apply-clusters annex outputs` comment + the `severity-disagreements.yaml` / `contradictions.yaml` entries unchanged.)

- [ ] **Step 4: Run the doc-wrappers test (now green) + the C-locale test (now expected to FAIL)**

Run: `python3 -m pytest tests/test_synthesis_doc_wrappers.py tests/unit/test_tier3_encoding_package.py::test_validate_runs_under_c_locale -v`
Expected: `test_synthesis_doc_wrappers.py` PASSES (the wrappers validate the example golden + are wired). `test_validate_runs_under_c_locale` FAILS — the legacy crapi `nist-coverage.yaml` is `coverage_by_family` dict shape and now fails the array `*-doc` schema (exit 1). This failure is RESOLVED by Task B.

- [ ] **Step 5: Commit the wiring (test red is expected until Task B)**

```bash
git add tools/apd_gauntlet/validate.py tests/test_synthesis_doc_wrappers.py
git commit -m "feat(validate): wire nist/attack/matrix coverage into SYNTHESIS_ROLLUPS (Plan 3 Task A)"
```

(The C-locale regression is intentionally left red across this single commit; Task B's commit restores green. If your review process forbids a transient-red commit, fold Task A Step 3 and Task B Steps 1-5 into one commit — the TDD ordering is preserved either way.)

---

## Task 4 (Task B): Regenerate the 3 legacy runs + preserve the legacy-shape fixture

Regenerate each committed run's coverage to the array shape via `apd-gauntlet rollup`, which makes them validate-clean under the Task-A wiring. EMPIRICALLY VERIFIED: regenerating crapi in place and running the two transform suites breaks EXACTLY two tests — `test_transform_nist_rollup.py::test_rollup_new_shape_counts_are_nonzero` (asserts the legacy `coverage_by_family` key is present) and `test_transform_apd_matrix.py::test_matrix_new_shape_produces_artifact_component_rows` (asserts the legacy goal-keyed `coverage` key is present). The other 9 tests in those files (including `test_rollup_one_row_per_family` and `test_rollup_carries_title_from_families_data`, both of which assert an `SC` family) STAY GREEN, because the regenerated crapi array shape DOES contain `SC` (`SC-8 Transmission Confidentiality and Integrity`). So FIRST freeze the current legacy crapi coverage (plus the matching `deduped-findings.yaml`) into a fixture and re-point ONLY those 2 tests there — leave the other 9 untouched.

**Files:**
- Create: `tests/fixtures/legacy-coverage-shapes/40-synthesis/{nist-coverage.yaml, attack-exposure.yaml, apd-coverage-matrix.yaml, deduped-findings.yaml}`
- Modify: `tests/unit/report/test_transform_nist_rollup.py`, `tests/unit/report/test_transform_apd_matrix.py`
- Modify: `runs/apd-20260527-{crapi-owasp-api-top10, authentik-identity-provider, caldera-adversary-emulation}/40-synthesis/{nist-coverage, attack-exposure, apd-coverage-matrix}.yaml` (+ new `cwe/owasp/d3fend-coverage.yaml`)
- Create: `tests/test_validate_legacy_runs.py`

- [ ] **Step 1: Freeze the legacy-shape crapi coverage into a fixture (BEFORE regeneration)**

Copy the current (legacy-shape) crapi coverage files into a frozen fixture dir (the re-pointed tests load these specimens directly into a `MagicMock` via `yaml.safe_load` — no `load_run`, so no full run scaffold is needed in the fixture):

```bash
mkdir -p tests/fixtures/legacy-coverage-shapes/40-synthesis
cp runs/apd-20260527-crapi-owasp-api-top10/40-synthesis/nist-coverage.yaml \
   tests/fixtures/legacy-coverage-shapes/40-synthesis/nist-coverage.yaml
cp runs/apd-20260527-crapi-owasp-api-top10/40-synthesis/attack-exposure.yaml \
   tests/fixtures/legacy-coverage-shapes/40-synthesis/attack-exposure.yaml
cp runs/apd-20260527-crapi-owasp-api-top10/40-synthesis/apd-coverage-matrix.yaml \
   tests/fixtures/legacy-coverage-shapes/40-synthesis/apd-coverage-matrix.yaml
# The legacy goal-keyed matrix (Shape B) synthesises component rows by resolving
# the coverage block's finding IDs against deduped_findings; freeze the matching
# deduped findings so the matrix test is fully self-contained (no live coupling).
cp runs/apd-20260527-crapi-owasp-api-top10/40-synthesis/deduped-findings.yaml \
   tests/fixtures/legacy-coverage-shapes/40-synthesis/deduped-findings.yaml
```

Confirm the frozen `nist-coverage.yaml` carries `coverage_by_family:` (legacy dict shape) and the matrix carries `coverage:`:

Run: `grep -l "coverage_by_family" tests/fixtures/legacy-coverage-shapes/40-synthesis/nist-coverage.yaml && grep -c "^coverage:" tests/fixtures/legacy-coverage-shapes/40-synthesis/apd-coverage-matrix.yaml`
Expected: prints the nist path (it contains `coverage_by_family`) and `1` (matrix has a top-level `coverage:` key).

These frozen fixtures are tracked under `tests/fixtures/`, which `.gitignore` does NOT exclude (the only `runs/` exclusions are the three per-run `runs/apd-20260527-*/40-synthesis/report-html/` lines; the `!tests/fixtures/runs/` + `!tests/fixtures/runs/**` re-includes confirm `tests/fixtures/` is intended to be tracked — verified).

- [ ] **Step 2: Re-point the two shape-coupled report tests at the frozen fixture**

EMPIRICAL SCOPE (verified by regenerating crapi in place + running both suites): exactly ONE test in `test_transform_nist_rollup.py` breaks — `test_rollup_new_shape_counts_are_nonzero`, which asserts the legacy `coverage_by_family` key is present (the array shape replaces it with `controls`). DO NOT touch `test_rollup_one_row_per_family`, `test_rollup_carries_title_from_families_data`, `test_rollup_counts_match_family_summary`, or `test_rollup_notable_is_string`: the regenerated crapi array shape still contains the `SC` family (`SC-8 Transmission Confidentiality and Integrity`) and the `family_summary` cross-walk still works, so all four stay green against the regenerated `example_run`. There is NO `SC`-absence to compensate for.

In `tests/unit/report/test_transform_nist_rollup.py`, add a frozen-fixture path constant after the existing imports (the file already imports `pathlib`, `MagicMock`; add `import yaml`):

```python
LEGACY_NIST = (
    pathlib.Path(__file__).resolve().parents[3]
    / "tests" / "fixtures" / "legacy-coverage-shapes" / "40-synthesis" / "nist-coverage.yaml"
)
```

Then REPLACE only `test_rollup_new_shape_counts_are_nonzero` so it reads the FROZEN legacy `coverage_by_family` specimen instead of `example_run`. Mirror the EXISTING in-file construction pattern — `test_rollup_old_shape_uses_family_summary` builds `artifacts = MagicMock(); artifacts.nist_coverage = ...; artifacts.deduped_capabilities = []` (NOT a real `RunArtifacts(...)` — `nist_rollup_rows` reads only `artifacts.nist_coverage` and `artifacts.deduped_capabilities`):

```python
def test_rollup_new_shape_counts_are_nonzero() -> None:
    """Loader tolerance: the FROZEN legacy coverage_by_family doc cross-walks to nonzero rows."""
    legacy = yaml.safe_load(LEGACY_NIST.read_text(encoding="utf-8"))
    assert legacy.get("coverage_by_family") is not None, \
        "Frozen fixture should use the legacy coverage_by_family shape"
    artifacts = MagicMock()
    artifacts.nist_coverage = legacy
    artifacts.deduped_capabilities = []
    rows = nist_rollup_rows(artifacts)
    total = sum(r["covered"] + r["gapped"] + r["both"] for r in rows)
    assert total > 0, "Expected non-zero control counts from coverage_by_family cross-walk"
```

In `tests/unit/report/test_transform_apd_matrix.py`, exactly ONE test breaks — `test_matrix_new_shape_produces_artifact_component_rows`, which asserts the legacy goal-keyed `coverage` key is present (the array shape uses a top-level `components` list). The other four tests stay green against the regenerated `example_run`. Add a frozen-fixture path constant after the imports (the file already imports `pathlib`, `MagicMock`; add `import yaml`):

```python
LEGACY_MATRIX = (
    pathlib.Path(__file__).resolve().parents[3]
    / "tests" / "fixtures" / "legacy-coverage-shapes" / "40-synthesis" / "apd-coverage-matrix.yaml"
)
LEGACY_DEDUPED = (
    pathlib.Path(__file__).resolve().parents[3]
    / "tests" / "fixtures" / "legacy-coverage-shapes" / "40-synthesis" / "deduped-findings.yaml"
)
```

Then REPLACE only `test_matrix_new_shape_produces_artifact_component_rows` so it reads the FROZEN legacy goal-keyed matrix. `apd_matrix` synthesises Shape-B component rows by resolving the `coverage` block's finding IDs against `artifacts.deduped_findings + artifacts.attack_path_findings`, so feed the frozen `deduped-findings.yaml` into `deduped_findings` (mirror the in-file MagicMock pattern from `test_matrix_old_shape_component_rows`):

```python
def test_matrix_new_shape_produces_artifact_component_rows() -> None:
    """Loader tolerance: the FROZEN legacy goal-keyed coverage shape yields artifact rows."""
    legacy = yaml.safe_load(LEGACY_MATRIX.read_text(encoding="utf-8"))
    assert legacy.get("coverage") is not None, \
        "Frozen fixture should use the legacy goal-keyed coverage shape"
    deduped = yaml.safe_load(LEGACY_DEDUPED.read_text(encoding="utf-8"))
    findings = deduped.get("finding") or []
    artifacts = MagicMock()
    artifacts.apd_coverage_matrix = legacy
    artifacts.deduped_findings = findings
    artifacts.attack_path_findings = []
    m = apd_matrix(artifacts)
    component_names = {r["component"] for r in m["rows"]}
    # tech_plan.md is by far the most cited artifact in the frozen crapi fixture.
    assert "tech_plan.md" in component_names
```

The other `example_run`-based matrix tests (`test_matrix_returns_goals_and_rows`, `test_matrix_cells_use_short_posture_keys`, `test_matrix_posture_gapped_and_covered_becomes_both`) tolerate the array shape — verify in Step 5.

- [ ] **Step 3: Regenerate the coverage for all 3 runs**

Run (each `rollup` rewrites nist/attack/matrix to array shape AND emits cwe/owasp/d3fend-coverage additively):

```bash
apd-gauntlet rollup runs/apd-20260527-crapi-owasp-api-top10
apd-gauntlet rollup runs/apd-20260527-authentik-identity-provider
apd-gauntlet rollup runs/apd-20260527-caldera-adversary-emulation
```

Expected: each echoes e.g. `rollup: wrote 111 controls, 13 techniques, 24 components, 3 extra coverage files` (counts vary per run; all exit 0).

- [ ] **Step 4: Confirm each regenerated run validates clean**

Run:

```bash
for r in crapi-owasp-api-top10 authentik-identity-provider caldera-adversary-emulation; do
  apd-gauntlet validate runs/apd-20260527-$r --errors-only && echo "$r OK"
done
```

Expected: each prints `<r> OK` (exit 0). (`validate` never reads `report-html/`, so the gitignored/untracked report build is irrelevant; no `build-report`/`audit-report` migration step is needed.)

- [ ] **Step 5: Add the legacy-runs validate regression test + run the report + C-locale suites**

Create `tests/test_validate_legacy_runs.py`:

```python
"""All 3 committed runs validate clean after the Plan-3 coverage regeneration."""
from __future__ import annotations

import pathlib

import pytest
from apd_gauntlet.cli import main
from click.testing import CliRunner

REPO = pathlib.Path(__file__).resolve().parent.parent
RUNS = [
    "apd-20260527-crapi-owasp-api-top10",
    "apd-20260527-authentik-identity-provider",
    "apd-20260527-caldera-adversary-emulation",
]


@pytest.mark.parametrize("run_id", RUNS)
def test_run_validates_clean(run_id: str) -> None:
    result = CliRunner().invoke(main, ["validate", str(REPO / "runs" / run_id), "--errors-only"])
    assert result.exit_code == 0, result.output


@pytest.mark.parametrize("run_id", RUNS)
def test_run_coverage_is_array_shape(run_id: str) -> None:
    """Post-regeneration, each run's coverage uses the array (controls/techniques/components) shape."""
    import yaml
    synth = REPO / "runs" / run_id / "40-synthesis"
    nist = yaml.safe_load((synth / "nist-coverage.yaml").read_text(encoding="utf-8"))
    assert isinstance(nist.get("controls"), list), "nist-coverage must be array-shaped post-rollup"
    assert "coverage_by_family" not in nist
    attack = yaml.safe_load((synth / "attack-exposure.yaml").read_text(encoding="utf-8"))
    assert isinstance(attack.get("techniques"), list), "attack-exposure must be array-shaped post-rollup"
    matrix = yaml.safe_load((synth / "apd-coverage-matrix.yaml").read_text(encoding="utf-8"))
    assert isinstance(matrix.get("components"), list), "apd-coverage-matrix must be array-shaped post-rollup"
    assert "coverage" not in matrix
```

Run: `python3 -m pytest tests/test_validate_legacy_runs.py tests/unit/test_tier3_encoding_package.py tests/unit/report/test_transform_nist_rollup.py tests/unit/report/test_transform_apd_matrix.py -v`
Expected: PASS (all). The C-locale `test_validate_runs_under_c_locale` is now GREEN again (crapi validates clean post-regeneration); the report-transform shape tests pass against the frozen fixture + the tolerated array shape.

- [ ] **Step 6: Commit the regeneration + fixture + test re-pointing**

```bash
git add tests/fixtures/legacy-coverage-shapes/ tests/unit/report/test_transform_nist_rollup.py \
        tests/unit/report/test_transform_apd_matrix.py tests/test_validate_legacy_runs.py \
        runs/apd-20260527-crapi-owasp-api-top10/40-synthesis/ \
        runs/apd-20260527-authentik-identity-provider/40-synthesis/ \
        runs/apd-20260527-caldera-adversary-emulation/40-synthesis/
git commit -m "fix(runs): regenerate legacy coverage to array shape; freeze legacy-shape fixture (Plan 3 Task B)"
```

---

## Task 5 (Task C): Strengthen `audit-report` with a `nist_rollup_parity` check

Add a best-effort check that recomputes the rendered family-aggregated `nist_rollup` and compares it against `parsed["nist_rollup"]` from `data.js`. A row-level mismatch is a HARD FAIL (drives the remediate loop, exit 1); a transform EXCEPTION is a non-blocking soft entry. Keep the existing `id_coverage_nist` subset check unchanged. `audit.py` already imports `load_run` + `build_apd_data` (lines 61-62) and calls `build_apd_data(load_run(run_dir), run_dir=run_dir)` at line 139, so the dependency is in scope.

**Files:**
- Modify: `tools/apd_gauntlet/synthesis/audit.py`
- Modify: `tests/test_cli_audit_report.py`

- [ ] **Step 1: Write the failing tests**

In `tests/test_cli_audit_report.py`, append three tests (the file already imports `audit_report`, `parse_data_js`, `yaml`, `shutil`, `CliRunner`, `main`, and defines `_copy_example`):

```python
def _family_counts(rollup):
    return {r["family"]: (r["covered"], r["gapped"], r["both"]) for r in rollup}


def test_nist_rollup_parity_passes_on_committed_example(tmp_path):
    dst = _copy_example(tmp_path)
    result = audit_report(dst)
    parity = [c for c in result.checks if c["name"] == "nist_rollup_parity"]
    assert parity, "nist_rollup_parity check must be emitted"
    assert parity[0]["status"] == "pass", parity[0]["detail"]


def test_nist_rollup_parity_fails_when_data_js_diverges(tmp_path):
    dst = _copy_example(tmp_path)
    # Diverge a data.js nist_rollup family count from the recompute. The committed
    # data.js is pretty-printed (json.dumps indent=2), so a single-line text
    # needle like '"family": "IA", "title"' has ZERO matches and cannot be used.
    # Instead: parse the dict, mutate one family's "covered", then re-serialize
    # the SAME way emit.write_data_js does (window.APD_DATA = json.dumps(indent=2,
    # ensure_ascii=False, sort_keys=False, allow_nan=False) + the '</' -> '<\\/'
    # escaping + ';\\n'). Calling write_data_js directly is the canonical mirror.
    from apd_gauntlet.report.emit import write_data_js

    data_js = dst / "40-synthesis" / "report-html" / "data.js"
    parsed = parse_data_js(data_js)
    assert parsed.get("nist_rollup"), "example data.js must carry nist_rollup rows"
    parsed["nist_rollup"][0]["covered"] = int(parsed["nist_rollup"][0].get("covered", 0)) + 9999
    write_data_js(parsed, data_js)
    # Round-trip sanity: the mutation persisted and re-parses cleanly.
    assert parse_data_js(data_js)["nist_rollup"][0]["covered"] >= 9999
    result = audit_report(dst)
    parity = [c for c in result.checks if c["name"] == "nist_rollup_parity"]
    assert parity and parity[0]["status"] == "fail", parity
    assert result.status == "fail"
    # CLI exits 1.
    cli_result = CliRunner().invoke(main, ["audit-report", str(dst)])
    assert cli_result.exit_code == 1, cli_result.output


def test_nist_rollup_parity_soft_on_transform_exception(tmp_path, monkeypatch):
    dst = _copy_example(tmp_path)
    # Force the recompute to raise; the parity check must record a NON-blocking soft entry.
    import apd_gauntlet.synthesis.audit as audit_mod

    def _boom(*a, **k):
        raise RuntimeError("synthetic transform failure")

    # Patch the rollup recompute path used by the new parity check.
    monkeypatch.setattr(audit_mod, "_recompute_nist_rollup", _boom, raising=True)
    result = audit_report(dst)
    parity = [c for c in result.checks if c["name"] == "nist_rollup_parity"]
    assert parity, "parity check must still be emitted on transform failure"
    # Soft: the parity check itself reports pass (non-blocking) and notes the exception.
    assert parity[0]["status"] == "pass"
    assert "exception" in parity[0]["detail"].lower() or "skipped" in parity[0]["detail"].lower()
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python3 -m pytest tests/test_cli_audit_report.py -k nist_rollup_parity -v`
Expected: FAIL — no `nist_rollup_parity` check exists yet (and `_recompute_nist_rollup` is not defined for the monkeypatch).

- [ ] **Step 3: Add the parity helper + check to `audit.py`**

In `tools/apd_gauntlet/synthesis/audit.py`, add a module-level helper (after `_yaml_records`) that isolates the recompute so the test can monkeypatch it:

```python
def _recompute_nist_rollup(run_dir: Path) -> list[dict[str, Any]]:
    """Recompute the family-aggregated nist_rollup the report renderer produces.

    Isolated so the audit's parity check can be monkeypatched in tests and so a
    transform exception is caught at one call site.
    """
    from ..report.loader import load_run
    from ..report.transform import build_apd_data

    data = build_apd_data(load_run(run_dir), run_dir=run_dir)
    rollup = data.get("nist_rollup") or []
    return [r for r in rollup if isinstance(r, dict)]
```

Then, inside `audit_report`, AFTER the existing `id_coverage_nist` `_check(...)` block (the one ending `f"controls={len(nist_ids)} missing_from_taxonomy={missing_nist_sample}")`) and BEFORE the ATT&CK check, add the parity comparison:

```python
    # NIST rendered-rollup parity (Plan 3): recompute the family-aggregated
    # nist_rollup and compare family-level {covered, gapped, both} + row count
    # against the data.js parsed['nist_rollup']. Hard FAIL on mismatch (drives
    # the remediate loop); soft (non-blocking pass) on a transform exception.
    parsed_rollup = [r for r in (parsed.get("nist_rollup") or []) if isinstance(r, dict)]
    try:
        expected_rollup = _recompute_nist_rollup(run_dir)
    except Exception as exc:  # noqa: BLE001 — recompute is best-effort
        _check(result, "nist_rollup_parity", True,
               f"skipped (recompute exception, non-blocking): {exc}")
    else:
        def _fam_counts(rows: list[dict[str, Any]]) -> dict[str, tuple[int, int, int]]:
            return {
                str(r.get("family")): (
                    int(r.get("covered", 0)), int(r.get("gapped", 0)), int(r.get("both", 0))
                )
                for r in rows
            }
        expected_counts = _fam_counts(expected_rollup)
        parsed_counts = _fam_counts(parsed_rollup)
        rows_ok = len(expected_rollup) == len(parsed_rollup)
        counts_ok = expected_counts == parsed_counts
        mismatched = sorted(
            fam for fam in set(expected_counts) | set(parsed_counts)
            if expected_counts.get(fam) != parsed_counts.get(fam)
        )[:5]
        _check(result, "nist_rollup_parity", rows_ok and counts_ok,
               f"recompute_rows={len(expected_rollup)} data.js_rows={len(parsed_rollup)} "
               f"mismatched_families={mismatched}")
```

(`Any` and `Path` are already imported in `audit.py`.)

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python3 -m pytest tests/test_cli_audit_report.py -v`
Expected: PASS (all — the 3 new parity tests plus the existing audit tests; the committed example's data.js `nist_rollup` matches the recompute, so parity passes there).

- [ ] **Step 5: Commit**

```bash
git add tools/apd_gauntlet/synthesis/audit.py tests/test_cli_audit_report.py
git commit -m "feat(audit): nist_rollup_parity check compares rendered family rollup (Plan 3 Task C)"
```

---

## Task 6: Retire `apd-orchestrator` to a deprecation shim

Replace the orchestrator's lifecycle prose with a deprecation note pointing at the workflow runner, while keeping a trimmed "Historical topology (for reference)" block so the existing `tests/test_orchestrator_topology.py` substring pins survive (lower-churn than rewriting that test). Add a new test pinning the deprecation marker + the pointer. The orchestrator is already `RECEIPT_EXEMPT` (`lint_agents.py:14`) so no receipt clause is needed; keep the frontmatter valid and markdownlint-clean.

**Files:**
- Modify: `.claude/agents/apd-orchestrator.md`
- Create: `tests/test_orchestrator_deprecation.py`

- [ ] **Step 1: Write the failing deprecation test**

Create `tests/test_orchestrator_deprecation.py`:

```python
"""apd-orchestrator is retired to a deprecation shim (Plan 3); pins the marker + pointer."""
from __future__ import annotations

from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
AGENT = REPO / ".claude" / "agents" / "apd-orchestrator.md"


def test_orchestrator_marked_deprecated() -> None:
    text = AGENT.read_text(encoding="utf-8")
    assert "DEPRECATED" in text


def test_orchestrator_points_at_workflow_runner() -> None:
    text = AGENT.read_text(encoding="utf-8")
    assert ".claude/workflows/apd-gauntlet.js" in text


def test_orchestrator_references_design_spec() -> None:
    text = AGENT.read_text(encoding="utf-8")
    assert "2026-05-29-apd-token-resilience-design.md" in text


def test_orchestrator_ends_with_single_trailing_newline() -> None:
    raw = AGENT.read_text(encoding="utf-8")
    assert raw.endswith("\n") and not raw.endswith("\n\n"), "MD047: single trailing newline"
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python3 -m pytest tests/test_orchestrator_deprecation.py -v`
Expected: FAIL — the shim text/pointer are not present yet.

- [ ] **Step 3: Rewrite the orchestrator body as a deprecation shim**

In `.claude/agents/apd-orchestrator.md`, update the frontmatter `description` and replace the run-lifecycle body with the deprecation note + a trimmed historical block that retains the existing topology pins. Change the frontmatter `description:` line to:

```
description: Deprecated — superseded by the apd-gauntlet workflow runner (.claude/workflows/apd-gauntlet.js, invoked via the Workflow tool). This agent no longer orchestrates runs; retained as a historical-topology reference.
```

Keep `tools: Read, Glob, Grep, Write, Agent` unchanged. Replace the entire body BELOW the frontmatter (everything from `# APD Gauntlet Orchestrator` to end of file) with:

```markdown
# APD Gauntlet Orchestrator (DEPRECATED)

**DEPRECATED.** The APD gauntlet is now run by the deterministic workflow
runner `.claude/workflows/apd-gauntlet.js` (invoke it via the Workflow tool).
This agent no longer orchestrates runs — the runner dispatches intake, the tier
specialists, the decomposed synthesis pipeline, and the gated report audit
directly, with native auto-resume. See
`docs/superpowers/specs/2026-05-29-apd-token-resilience-design.md` §4 for the
architecture and §7 for the decomposed Phase 5.

`apd-cluster-adjudicator`, `apd-report-writer`, and `apd-report-auditor` are
workflow-runner agents (Plan 3) dispatched by the runner, not by this agent.

## Historical topology (for reference)

Before the workflow runner, this orchestrator coordinated 16 agents. The
mapping below is retained so historical run notes remain legible; it is NOT a
live contract.

### Tier-0 (intake / context)

- `apd-intake` (required); `apd-code-recon` (optional); `apd-threat-model-recon`
  (optional). When `crown_jewels` are declared, intake also emits
  `00-context/asset-inventory.yaml`.

### Tier-1 (Trustworthiness)

- `apd-confidentiality`, `apd-integrity`, `apd-availability`

### Tier-2 (Scalability)

- `apd-distributed`, `apd-resilient`, `apd-ephemeral`

### Tier-3 (Auditability)

- `apd-authenticity`, `apd-non-repudiation`, `apd-immutability`

### Tier-4 (synthesis)

- `apd-synthesizer` (now the workflow's fallback path);
  `apd-threat-model-evaluator` (Phase 5.5, threat-model gate);
  `apd-attack-path-analyzer` (Phase 5.6, `crown_jewels` activation gate; emits
  `asset-graph.yaml`, `attack-paths.yaml`, `defense-graph.yaml`,
  `attack-path.findings.yaml`).

The runner realizes the same phase ordering deterministically; consult the
design spec rather than this block for current behavior.
```

(End the file with exactly one trailing newline.) This retains the substrings `apd-attack-path-analyzer`, `16 agents`, `Phase 5.6`, `crown_jewels`, and the analyzer output filenames that `tests/test_orchestrator_topology.py` pins, and adds the new deprecation marker + pointer. Note `15 agents` must NOT appear (the topology test asserts its absence) — the rewrite above does not contain it.

- [ ] **Step 4: Run both orchestrator tests + lint-agents**

Run: `python3 -m pytest tests/test_orchestrator_topology.py tests/test_orchestrator_deprecation.py -v && apd-gauntlet lint-agents --agent-dir .claude/agents/`
Expected: both test files PASS; `lint-agents` prints `Lint clean: 19 agents checked.` (orchestrator is `RECEIPT_EXEMPT`; the deprecation shim still satisfies the required-reading lint because all backticked `.md`/`.js` refs resolve — `.claude/workflows/apd-gauntlet.js` exists from Task 1, and the design spec path exists).

> If `lint-agents` flags the `` `.claude/workflows/apd-gauntlet.js` `` backtick as an unresolved required-reading reference: the `REQUIRED_READING_PATTERN` is `` `([^`]+\.md)` `` (matches only `.md` paths), so a `.js` backtick is NOT matched and not linted — verified against `lint_agents.py:10`. No mitigation needed.

- [ ] **Step 5: Markdownlint the shim**

Run: `npx markdownlint-cli2 ".claude/agents/apd-orchestrator.md"`
Expected: clean (MD047 single trailing newline; no bare-URL / heading-spacing issues). If the repo CI uses a different invocation, match the `.github/workflows/markdown-lint.yml` glob set (it includes `.claude/**/*.md`).

- [ ] **Step 6: Commit**

```bash
git add .claude/agents/apd-orchestrator.md tests/test_orchestrator_deprecation.py
git commit -m "refactor(agents): retire apd-orchestrator to a deprecation shim (Plan 3)"
```

---

## Task 7: Align `plugin.json` version to 1.5.0

Bump `version` to `1.5.0` to match pyproject (closes the version-skew gap so a fresh `pip install -e .` install reports a version the runner's Phase-0 scaffold guard accepts) and refresh the `description` to name the workflow runner + synthesizer fallback. Do NOT add a `workflows` key: there is no verified plugin-manifest schema documenting one, and if the live manifest is validated with `additionalProperties:false` an unknown key would break plugin load; the Workflow tool discovers `.claude/workflows/` from the filesystem regardless, so the key buys nothing today.

**Files:**
- Modify: `plugin.json`

- [ ] **Step 1: Bump version + refresh description (no new keys)**

In `plugin.json`, change the `"version": "1.4.0"` line to `"version": "1.5.0"` and update `description` to name the runner. Keep the existing `agents`/`skills` keys unchanged; add NO `workflows` key. The result:

```json
{
  "name": "apd-gauntlet",
  "version": "1.5.0",
  "description": "APD security architecture review framework — 9 specialist agents plus intake, the apd-gauntlet workflow runner, and a synthesizer fallback.",
  "author": "shoveleejoe",
  "license": "Apache-2.0",
  "repository": "https://github.com/shoveleejoe/apd-gauntlet",
  "agents": "./.claude/agents/",
  "skills": "./.claude/skills/"
}
```

- [ ] **Step 2: Confirm it is valid JSON**

Run: `python3 -c "import json,pathlib; d=json.loads(pathlib.Path('plugin.json').read_text()); print(d['version']); assert 'workflows' not in d, 'no unverified workflows key'"`
Expected: prints `1.5.0` and exits 0 (no `workflows` key present).

> NOTE: a `workflows` manifest key can be added later IF the plugin-manifest schema is documented to support one. Until then the runner is discovered from the filesystem and dispatches its agents by resolving agentTypes from `.claude/agents/`; the version bump is the only change needed here.

- [ ] **Step 3: Commit**

```bash
git add plugin.json
git commit -m "chore(plugin): bump version to 1.5.0; refresh description (Plan 3)"
```

---

## Task 8: Final gate — full suite + lint/type/markdown + documented manual end-to-end

**Files:** none (verification only), plus a documented manual run.

- [ ] **Step 1: Run the whole suite**

Run: `python3 -m pytest -q`
Expected: PASS (all green). Specifically: `tests/test_workflow_apd_gauntlet.py`, `tests/test_synthesis_doc_wrappers.py`, `tests/test_validate_legacy_runs.py`, `tests/unit/test_tier3_encoding_package.py` (C-locale green again), `tests/unit/report/test_transform_nist_rollup.py` + `test_transform_apd_matrix.py` (frozen-fixture re-pointed), `tests/test_cli_audit_report.py` (parity), `tests/test_orchestrator_topology.py` + `test_orchestrator_deprecation.py`. The bundle-gated golden tests skip if the precompiled report bundle is absent (unchanged).

- [ ] **Step 2: Lint + type check**

Run: `ruff check tools/ tests/ && mypy tools/apd_gauntlet`
Expected: clean. The only Python edits are `validate.py` (3 dict entries), `audit.py` (one helper + one check block — annotated), and test files; no new type surface.

- [ ] **Step 3: Markdownlint the CI globs that changed**

Run: `npx markdownlint-cli2 ".claude/**/*.md"`
Expected: clean — the only changed `.md` is the orchestrator shim (the plan itself is CI-excluded under `!docs/superpowers/plans/**`).

- [ ] **Step 4: `apd-gauntlet lint-agents` end-to-end**

Run: `apd-gauntlet lint-agents --agent-dir .claude/agents/`
Expected: `Lint clean: 19 agents checked.`

- [ ] **Step 5: Confirm the runner's structural contract one more time**

Run: `python3 -m pytest tests/test_workflow_apd_gauntlet.py -q`
Expected: PASS — every `agentType` resolves, every `pyStep` command is registered, the RECEIPT required fields match the schema, the `i <= 2` cap is present, and the typed-signal/fallback pins hold.

- [ ] **Step 6: DOCUMENTED MANUAL end-to-end run (cannot be auto-run in pytest)**

The runner cannot execute under plain `node` (it needs the Workflow harness), and CI has no Node step. Perform this verification manually in a Claude Code session and record the result in the PR description:

1. Ensure a fresh install so dispatched agents get the Plan-2/3 CLI: `pip install -e ".[dev]"` then `apd-gauntlet --version` → expect `1.5.0` (this is the version-skew guard, enforced out-of-band since the workflow no longer runs `init-run`).
2. Scaffold the run OUTSIDE the workflow FIRST (the workflow assumes a pre-scaffolded run; `args` IS the run's `.apd-run.yaml`): `apd-gauntlet init-run apd-smoke-wf --inputs <a tiny inputs dir> --domain pbm` (or reuse an existing `runs/<id>` with `inputs/` + `.apd-run.yaml`). Confirm `runs/apd-smoke-wf/.apd-run.yaml` and `runs/apd-smoke-wf/inputs/` exist before step 3.
3. In your Claude Code session, invoke the Workflow tool:
   `Workflow({ scriptPath: '.claude/workflows/apd-gauntlet.js', args: { run_id: 'apd-smoke-wf', domain: 'pbm', framework_version: '1.5.0', code_recon: 'disabled', crown_jewels: [] } })`
   Expected: the runner walks `setup (validate-scaffold + build-domain-skill + validate-domain) → intake → (code-recon skipped) → (tm-recon skipped) → tier-1/2/3` (each tier 3-wide parallel + a `validate --tier` gate) `→ full validate → 5a..5g → (tmeval skipped) → (apath skipped, empty crown_jewels) → closeout`, emitting `phase(...)`/`log(...)` breadcrumbs. The first setup step runs `apd-gauntlet validate runs/apd-smoke-wf --schema-only --errors-only` against the pre-existing scaffold. The final `closeout` `validate --errors-only` returns the run clean.
4. RESUME check (same session): re-invoke with `Workflow({ scriptPath: '.claude/workflows/apd-gauntlet.js', resumeFromRunId: '<the run id from step 3>' })`. Expect every completed `agent()` call to replay from cache instantly (no re-dispatch).
5. CROSS-SESSION resume check (new chat): invoke the workflow again with the same `args`. Expect each step-agent to hit its idempotency guard, run `validate --schema-only --errors-only`, find the outputs valid, and return an `ok` + `<phase>.skipped` sentinel cheaply — only missing/invalid phases do real work.
6. CODE-RECON HALT check: re-invoke with `args.code_recon: 'enabled'` on a run where CBM is unreachable so `apd-code-recon` returns `status:error`. Expect the runner to log the HALT message and ABORT by THROWING an `Error` (`Phase 1.5 code-recon failed with code_recon=enabled; aborting run …`) — NOT silently continue, and NOT crash with a top-level-`return` SyntaxError. Confirm no tier phases run after the halt.
7. FALLBACK check (optional): delete `40-synthesis/cluster-decisions.yaml` mid-run before 5c and confirm `apply-clusters` exits 2 → the runner re-dispatches the adjudicator once (label `adjudicate-retry-1`) → retries 5c. Persisting exit 2 routes to the `apd-synthesizer` fallback (phase `synthesis-fallback`, label `synthesizer-fallback`) and a `run-state.yaml` breadcrumb is written.

Record: phase sequence observed, resume behavior (cache replay + cross-session skip), and any fallback exercised. This manual evidence substitutes for an auto-run since the harness is not available in CI.

- [ ] **Step 7: Final commit (if any verification fixups were needed)**

```bash
git add -A
git commit -m "test: token-resilience Plan 3 final gate green + manual e2e documented"
```

---

## Self-Review

**Spec coverage (vs design §4 phase-map / §6 resume / §7.2 fallback / §10 inventory + the deferred items):**

| Design item | Realization | Task |
|---|---|---|
| §4 runner file `.claude/workflows/apd-gauntlet.js` (meta literal + RECEIPT + pyStep/llmStep + per-phase body) | Full script content | Task 1 ✓ |
| §4 phase map: P0 setup (validate scaffold / build-domain-skill / validate-domain) | 3 sequential `pyStep` in `phase('setup')`: `validate` (pre-existing scaffold, NO init-run), then `build-domain-skill` + `validate-domain` dispatched with `noRunDir:true, positional: args.domain` (bare domain positional). Version-skew guard is out-of-band (manual e2e step 1) | Task 1 ✓ |
| §4 P1 intake; P1.5 code-recon gate (enabled HALT / auto tolerate / disabled skip); P1.6 tm-recon gate | `llmStep('apd-intake')`; `if (args.code_recon !== 'disabled')` with HALT-on-error under `enabled` via `throw new Error(...)` (not a top-level `return;`); `if (args.threat_model)` | Task 1 ✓ |
| §4 P2/3/4 three 3-wide parallel tiers + per-lens 2-retry + `validate --tier NN --errors-only` gate + FULL `validate` before Phase 5 (Pass-3 coverage) | `runTier()` `parallel(...)` barrier + retry loop with distinct labels + tier gate (`validateScope: runDir, validateFlags: '--tier '+tierDir` — positional is the RUN dir so the CLI's `target = run_dir/tier` resolves correctly, no doubled `--schema-only`); explicit full-run gate after tier-3 | Task 1 ✓ |
| §7 decomposed 5a cluster-candidates / 5b adjudicator / 5c apply-clusters / 5d rollup / 5e report-writer / 5f build-report / 5g audit loop | Strictly sequential; python vs LLM steps per §7; AdjudicationMissing branch | Task 1 ✓ |
| §7 5g audit auto-remediate loop cap N=2; auditor schema-less (returns critique string); `GATE: pass/fail` regex | `for (i=0; i<=2; i++)`; auditor dispatched WITHOUT `{schema}`; `/GATE:\s*pass/i`; feeds compact critique into 5e | Task 1 ✓ |
| §7.2 synthesizer fallback: direct `agent('apd-synthesizer')` (no nest), typed-signal-driven, run-state breadcrumb via a Bash agent | Fallback on persistent AdjudicationMissing / cluster-candidates+apply+rollup error+retry / 2× adjudicator error / build-report-after-regenerate; emitted under its own `phase('synthesis-fallback')` (M1, distinct from `synthesis-rollup`); breadcrumb agent before dispatch | Task 1 ✓ |
| §5 receipt contract mirrored exactly | `RECEIPT` constant fields == `agent-receipt.schema.json` (test pins the `required` set) | Task 1, Task 2 ✓ |
| §6 resume: same-session cache (distinct labels) + cross-session agent-internal phaseDone guard (conservative: schema-invalid = not-done) | `guard()` embedded verbatim in every step prompt; `validate --schema-only --errors-only` is the done-signal; skip sentinel | Task 1 ✓ |
| §6 skip convention without schema change | `status:'ok'` + `{path:'<phase>.skipped'}` sentinel | Task 1 ✓ |
| §10 orchestrator → deprecation shim (kept in lint set, receipt-exempt, topology pins survive) | Shim + trimmed historical block; new deprecation test; topology test still green | Task 6 ✓ |
| Structural test for the .js (no Node in CI) | Text-as-contract pytest: meta/phases/agentType-exist/cmd-exist/RECEIPT-fidelity/loop-cap/fallback pins | Task 2 ✓ |
| Deferred Task A — wire nist/attack/matrix into SYNTHESIS_ROLLUPS (→ `*-doc` schemas; matrix → `coverage-matrix-doc`) | 3 entries replace the deferral NOTE; doc-wrappers test inverted to wired-state | Task 3 ✓ |
| Deferred Task B — regenerate legacy runs; keep C-locale test green + runs internally consistent | `rollup` on all 3 runs → array shape; frozen legacy-shape fixture (incl. deduped-findings) re-points EXACTLY the 2 shape-coupled tests via `MagicMock`; `validate` exit 0; new parametrized legacy-runs test | Task 4 ✓ |
| Deferred Task C — strengthen audit-report to compare rendered nist_rollup | `nist_rollup_parity`: recompute via `build_apd_data(load_run())`, hard-fail on family-count/row mismatch, soft on transform exception; `id_coverage_nist` kept. The FAIL test diverges data.js via parse→mutate→`write_data_js` (format-tolerant), not a brittle single-line needle | Task 5 ✓ |
| plugin.json version align to 1.5.0 (no `workflows` key) | Version bump + description refresh only; no unverified manifest key | Task 7 ✓ |
| Final gate (pytest -q; ruff; mypy; markdownlint `.claude/**`; lint-agents) + documented manual e2e | Verification task + step-by-step manual Workflow invocation incl. same-session resume, cross-session skip, fallback | Task 8 ✓ |

**Grounding verified against the real repo (no invented names/flags/paths):**
- CLI registry (live `apd_gauntlet.cli.main.commands`): every `pyStep` command — `validate`, `build-domain-skill`, `validate-domain`, `cluster-candidates`, `apply-clusters`, `rollup`, `build-report`, `audit-report`, `summarize` — is registered (Task 2's `test_every_cli_command_is_registered` enforces this against the live group by extracting ONLY `pyStep('<cmd>')` tokens, no hardcoded list). `init-run` is intentionally NOT dispatched (the run is pre-scaffolded; setup validates it) and Task 2 pins its absence. The runner does NOT call `parse-threat-model`/`analyze-attack-paths` directly (the recon agents run them internally per their contracts); those appear only in instruction prose, never as `pyStep` calls, and the pyStep-only extraction excludes them along with non-command prose tokens like `apd-gauntlet workflow`.
- Exit codes match `cli.py`: `apply-clusters` `raise SystemExit(2)` on `AdjudicationMissing` (the unique code → exit-2 regex branch); `audit-report` `raise SystemExit(1)` on `status == "fail"` (remediate-loop signal, NOT fallback); `build-report` `SystemExit(1)` on the 5 build errors (regenerate-once then fallback); `validate` `SystemExit(0 if is_clean else 1)`. The pyStep prompt carries command identity (`pystep:<cmd>`) + `exit=<N>` in `errors[0].message` so the overloaded exit-1 is disambiguated by which command ran.
- AgentTypes: all 9 lenses (`apd-confidentiality` … `apd-immutability`) + `apd-intake`, `apd-code-recon`, `apd-threat-model-recon`, `apd-threat-model-evaluator`, `apd-attack-path-analyzer`, `apd-cluster-adjudicator`, `apd-report-writer`, `apd-report-auditor`, `apd-synthesizer` resolve to `.claude/agents/<name>.md` (18 dispatched; `apd-orchestrator` is the 19th lint-counted agent but is NEVER an `agentType` — Task 2 pins its absence). `lint-agents` count stays 19. Task 2 resolves agents from BOTH dispatch forms — `llmStep('apd-foo', ...)` (agent is the first POSITIONAL arg; the lenses, intake, recon, adjudicator, report-writer, evaluator, analyzer use this) AND `agent(..., {agentType:'apd-foo'})` (raw opts; report-auditor and synthesizer use this) — and discards the `'apd-'` + lens concat fragment, then pins the concrete 9-lens set separately (empirically verified all 18 resolve to on-disk agent files).
- Schemas: `RECEIPT` mirrors `schemas/agent-receipt.schema.json` (`required: [agent,status,outputs,counts]`, `status` enum `ok|blocked|error`, `outputs[].{path,schema_valid}`, `counts.{findings_by_severity,capabilities_by_maturity,blocked}`, optional `errors[].{path,message}`); the `*-doc` schema filenames are exactly `nist-coverage-doc`, `attack-exposure-doc`, `coverage-matrix-doc` (NOT `apd-coverage-matrix-doc`) — verified on disk.
- run-config gates: the runner branches only on `args.run_id`, `args.domain`, `args.framework_version`, `args.code_recon` (enum `enabled|auto|disabled`), `args.threat_model`, `args.crown_jewels` (empty array disables apath) — all real `run-config.schema.json` fields. The non-schema `subject:` key is never read.
- Legacy-runs facts: `report-html/` is gitignored for all 3 runs (so no committed build-manifest to drift — no `build-report`/`audit-report` migration needed); coverage YAMLs ARE tracked; `rollup` succeeds on each (empirically run on a crapi copy AND in place → array shape → `validate --errors-only` exit 0). The regenerated crapi families are `AC, AU, CM, CP, IA, IR, MP, SA, SC, SI, SR` — `SC` IS present (`SC-8 Transmission Confidentiality and Integrity`), so the recon's earlier "SC dropped" claim was FALSE and the two `SC`-asserting tests stay green untouched. EMPIRICALLY: regenerating crapi in place + running both transform suites breaks EXACTLY 2 tests (`test_rollup_new_shape_counts_are_nonzero`, `test_matrix_new_shape_produces_artifact_component_rows`), each asserting the OLD `coverage_by_family`/goal-keyed-`coverage` key. Both are re-pointed at the frozen `tests/fixtures/legacy-coverage-shapes/` specimens via `MagicMock` (matching the in-file `test_*_old_shape_*` pattern — NOT a reflective `RunArtifacts(...)` helper); the other 9 stay green.
- Audit recompute: `audit.py` already imports `load_run` + `build_apd_data` and the rendered `data.js` carries `nist_rollup` family rows `{family,title,covered,gapped,both,notable}` (verified on the example data.js: 7 rows). The parity helper reuses `build_apd_data(load_run(run_dir), run_dir=run_dir)["nist_rollup"]`.

**Placeholder scan:** No "TBD / TODO / handle edge cases / similar to Task N". Every JS line and every Python edit is shown in full; every command has an expected output. Task 4's test re-points use the concrete in-file `MagicMock` pattern (`artifacts = MagicMock(); artifacts.nist_coverage = ...; artifacts.deduped_capabilities = []`) — there is NO reflective `inspect.signature(RunArtifacts)` helper (the dataclass has ~24 required no-default fields, so reflection was self-contradictory and is dropped). Task 7 adds NO `workflows` key (no verified manifest schema; the version bump is the only change). Task 3 Step 5 documents a single intentional transient-red commit (with a fold-into-one-commit alternative) — the TDD red→green ordering is preserved.

**Cross-task consistency:** Task 3 (wire) and Task 4 (regenerate) are sequenced so the only window where `validate` is red on the legacy runs is the single Task-3 commit (with an explicit fold option). Task 5's parity check is additive and orthogonal to Tasks 3/4 (it compares `data.js` vs recompute, not the committed coverage shape) and the committed example passes it. Task 6's shim retains every `tests/test_orchestrator_topology.py` substring pin (`apd-attack-path-analyzer`, `16 agents`, `Phase 5.6`, `crown_jewels`, analyzer outputs) AND avoids `15 agents`, so both the legacy topology test and the new deprecation test pass. Task 2's structural test and Task 1's runner agree on the phase model, the RECEIPT `required` set, the `i <= 2` cap, the `/exit=2/` branch, and the `apd-synthesizer` fallback dispatch. Phase reconciliation is explicit (verified by simulating the test against the runner code block): the 15 non-tier phases — including the new `synthesis-fallback` (M1, no longer a duplicate `synthesis-rollup`) and the now-explicit `phase('apath')` (C1) — are checked via direct `phase('X')` literals, while `tier-1/2/3` are emitted dynamically by `runTier(name){ phase(name) }` and are checked via the `runTier('tier-N', ...)` call tokens (and asserted to NOT appear as `phase('tier-N')` literals); the union of both sets equals `meta.phases`. The test imports the live Click group and globs `.claude/agents/`, so any drift between the runner and the real CLI/agent sets fails CI. All new/edited `.md` (the orchestrator shim) ends with a single trailing newline (MD047) and is markdownlint-clean under the `.claude/**/*.md` CI glob; the plan file itself is CI-excluded.
