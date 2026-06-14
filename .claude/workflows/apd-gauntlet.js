// apd-gauntlet.js — deterministic APD gauntlet workflow runner (design option C).
//
// Replaces the retired apd-orchestrator LLM agent. The Workflow primitive gives
// this script NO filesystem, NO shell, NO Node API, and NO time/random APIs.
// Therefore EVERY command and every file/idempotency check is performed by a
// DISPATCHED agent: pyStep() dispatches a general-purpose Bash agent that runs
// `apd-gauntlet <cmd> <runDir>`; llmStep() dispatches a repo agent resolved from
// .claude/agents/. The script branches only on the values those agents return.
//
// INTERACTIVE / FOREGROUND. The dispatched specialist agents run as Claude Code
// subagents of the session that launches the run, so the gauntlet is meant to be
// run from a live session — an operator prompts Claude to run it (see
// docs/running-the-gauntlet.md). Driving it headlessly via the background
// Workflow tool can interrupt the specialist dispatches; run it in-session.
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
  description: 'Deterministic APD gauntlet runner (replaces apd-orchestrator); receipt-only dispatch + decomposed synthesis + gated report audit + synthesizer fallback. Runs INTERACTIVE/FOREGROUND — specialists are subagents of the launching session; do not drive it in the background or headlessly (a background launch can interrupt dispatches). See docs/running-the-gauntlet.md.',
  phases: [
    'setup', 'intake', 'code-recon', 'threat-model-author', 'tm-recon',
    'canonicalize',
    'tier-1', 'tier-2', 'tier-3',
    'synthesis-cluster', 'synthesis-adjudicate', 'synthesis-apply',
    'synthesis-fallback', 'tmeval', 'apath', 'synthesis-rollup',
    'synthesis-report', 'synthesis-build', 'synthesis-audit',
    'domain-coverage-delta', 'domain-improvements',
    'closeout',
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
    // F3: per-class completeness counts the audit-report worker lifts from the
    // CLI's printed `structural_failed=<S> editorial_failed=<E>` line. Optional
    // (older workers omit it) — the gate falls back to the command exit status.
    // Lets the workflow block on STRUCTURAL completeness only and surface
    // editorial residuals non-blocking (like the LLM semantic residual).
    report_audit: {
      type: 'object',
      additionalProperties: false,
      properties: {
        structural_failed: { type: 'integer', minimum: 0 },
        editorial_failed: { type: 'integer', minimum: 0 },
      },
    },
  },
};

// args IS the run's .apd-run.yaml (run-config.schema.json). Normalize + validate
// up front so a mis-marshalled invocation (e.g. the named-workflow path delivering
// args as a JSON STRING) fails with an ACTIONABLE error instead of a cryptic
// `.join of undefined` mid-dispatch. `args` is a reassignable binding.
if (typeof args === 'string') {
  try { args = JSON.parse(args); }
  catch (e) {
    throw new Error('apd-gauntlet: args arrived as a string that is not valid JSON (' +
      e.message + '). Pass the run-config as an object, or a JSON string of ' +
      'run-config.schema.json.');
  }
}
if (!args || typeof args !== 'object' || Array.isArray(args)) {
  throw new Error('apd-gauntlet: args must be the run .apd-run.yaml as an object; got ' +
    (Array.isArray(args) ? 'array' : typeof args) + '.');
}
if (typeof args.run_id !== 'string' || !args.run_id) {
  throw new Error('apd-gauntlet: args.run_id is required (the runs/<id> directory name). ' +
    'Got: ' + JSON.stringify(args.run_id) + '. Did you pass the parsed .apd-run.yaml?');
}
if (!Array.isArray(args.domains) || args.domains.length === 0) {
  throw new Error('apd-gauntlet: args.domains must be a non-empty array of domain-pack ' +
    'names (e.g. ["pbm"]). Got: ' + JSON.stringify(args.domains) + '.');
}

// String concat only — no FS.
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
//   args.domains.join(' ') for build-domain-skill/validate-domain).
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
    opts.alwaysRun
      ? 'NO IDEMPOTENT SKIP for this setup step — always perform the WORK COMMAND below (the command is itself idempotent).'
      : guard(outputs, scope, flags),
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
    // F3: the audit-report worker ALSO lifts the per-class completeness counts the
    // CLI prints (`audit-report: <status> (... structural_failed=<S> editorial_failed=<E>)`)
    // into a report_audit block so the gate can block on STRUCTURAL failures only.
    opts.reportAudit
      ? '  report_audit: parse the command stdout line ' +
        '`audit-report: <status> (... structural_failed=<S> editorial_failed=<E>)` and ' +
        'set report_audit:{structural_failed:<S>, editorial_failed:<E>} (integers) in the receipt'
      : null,
    'NEVER summarize the file contents in prose — return the receipt only.',
  ].filter(Boolean).join('\n');
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

// A null/undefined receipt means the DISPATCH did not complete — e.g. a subagent
// was interrupted/cancelled. This is the failure mode when the runner is driven
// headlessly via the background Workflow primitive (foreground dispatches are not
// interrupted). It is DISTINCT from a genuine CLI/agent error, which returns a
// receipt with status:'error'. The run is NOT lost: every finished phase is on
// disk and re-invoking the runner replays completed phases via the per-agent
// idempotency guards. See docs/running-the-gauntlet.md Step 2.
function isInterrupted(r) { return r === null || r === undefined; }
function bailIfInterrupted(r, phaseName) {
  if (!isInterrupted(r)) return;
  throw new Error(
    'apd-gauntlet: run interrupted at phase "' + phaseName + '" — a dispatched subagent ' +
    'did not complete. The run is NOT lost: finished phases are on disk under ' + runDir +
    '. RE-INVOKE the runner to resume (idempotency guards replay completed phases). If the ' +
    'background Workflow primitive keeps interrupting dispatches, drive the run in the ' +
    'FOREGROUND: `apd-gauntlet plan-run ' + runDir + '` (docs/running-the-gauntlet.md Step 2).');
}

// ===========================================================================
// PHASE 0 — setup
// ===========================================================================
phase('setup');
log('apd-gauntlet runner: setup for ' + args.run_id + ' (domains=' + args.domains.join(',') + ')');
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
// 0b — build-domain-skill takes BARE domain_name positionals (NOT the run dir),
// so use noRunDir + positional=args.domains.join(' '). --framework-version is a flag.
// alwaysRun bypasses the JS-side idempotency guard; the Python command is itself
// idempotent and decides pack-set freshness.
// Emits the full cross-goal SKILL.md (read by intake / attack-path / domain-auditor)
// PLUS .claude/skills/apd-domain/by-goal/<goal>.md sidecars — one per lens agent,
// goal-scoped to bound context on multi-domain runs (each lens reads only its own).
// GUARD the --framework-version flag on args.framework_version being present: blindly
// concatenating an absent value stringifies `undefined`, yielding the literal arg
// `--framework-version undefined`, which crashes build_domain_skill at int('undefined').
// When the key is absent, OMIT the flag so the CLI's own `default=__version__` applies.
pyStep('build-domain-skill', {
  phase: 'setup', label: 'build-domain-skill',
  noRunDir: true, positional: args.domains.join(' '),
  cliArgs: args.framework_version ? ('--framework-version ' + args.framework_version) : '',
  outputs: '.claude/skills/apd-domain/SKILL.md + by-goal/<goal>.md (9 lens sidecars)',
  validateScope: runDir, alwaysRun: true,
});
// 0c — validate-domain also takes a BARE domain_name positional (read-only check).
pyStep('validate-domain', {
  phase: 'setup', label: 'validate-domain',
  noRunDir: true, positional: args.domains.join(' '),
  outputs: 'domain pack ' + args.domains.join(',') + ' (read-only check)',
  validateScope: runDir,
});

// ===========================================================================
// PHASE 1 — intake
// ===========================================================================
phase('intake');
const intakeReceipt = llmStep('apd-intake',
  'Analyze ' + runDir + '/inputs and emit 00-context/context-brief.md PLUS ' +
  '00-context/asset-inventory.yaml (ALWAYS emit the inventory: populate it from the artifacts when ' +
  'crown_jewels are declared in the run-config or the apd-domain skill, otherwise emit a schema-valid ' +
  'EMPTY inventory {schema_version:1, generated_by:intake, assets:[], identities:[], trust_boundaries:[]} ' +
  '— the rollup and HTML-report build read it as a required input).',
  { phase: 'intake', label: 'intake', validateScope: runDir + '/00-context',
    outputs: runDir + '/00-context/context-brief.md, ' + runDir + '/00-context/asset-inventory.yaml' });
bailIfInterrupted(intakeReceipt, 'intake');

// FW: assemble the asset inventory — mint deterministic asset-/idn-/tb- ids from
// name+provenance and wire trust_boundaries.crosses (authored by NAME) to the
// minted asset ids. MUST run before specialists cite inventory ids (code-recon +
// tier-1 onward), so ids are stable for the rest of the run; placed before the
// 00-context schema-gate so the gate validates the canonical (id-bearing) form.
pyStep('assemble-inventory', {
  phase: 'intake', label: 'assemble-inventory',
  outputs: runDir + '/00-context/asset-inventory.yaml (asset-/idn-/tb- ids minted; crosses wired)',
  validateScope: runDir + '/00-context', alwaysRun: true,
});

// FW-2: schema-gate 00-context immediately after intake so an invalid
// asset-inventory (e.g. a data_classifications value outside the schema enum,
// or malformed context-brief frontmatter) surfaces HERE, in the intake phase —
// not 9 specialists later at the pre-Phase-5 whole-run gate. Only 00-context
// exists at this point, so a whole-run --schema-only pass is effectively the
// 00-context schema gate. Read-only receipt, mirroring the tier gates.
pyStep('validate', {
  phase: 'intake', label: 'intake-schema-gate',
  cliArgs: '--schema-only --errors-only',
  outputs: runDir + '/00-context schema gate (asset-inventory + brief frontmatter)',
  validateScope: runDir,
});

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
// PHASE 1.55 — threat-model-author (ALWAYS-ON; occupies the old tm-recon slot).
// Two steps, floor-before-enrich (mirrors the parse/analyze deterministic-floor
// pattern): (1) pyStep('author-threat-model') builds the surface x applicable-
// STRIDE skeleton at 00-context/threat-model-skeleton.yaml (deterministic, no
// LLM, never-invents-a-surface); (2) llmStep('apd-threat-model-author') grounds
// or blocks each skeleton cell, reconstructs flow direction in-LLM, and emits the
// canonical 00-context/threat-model-normalized.yaml (generated_by:
// threat_model_author) + 00-context/threat-model-authored.md. No gate: the
// grounded baseline ALWAYS exists, so tmeval always has a TM to grade.
// ===========================================================================
phase('threat-model-author');
pyStep('author-threat-model', {
  phase: 'threat-model-author', label: 'author-threat-model-floor',
  outputs: runDir + '/00-context/threat-model-skeleton.yaml',
  validateScope: runDir + '/00-context',
});
llmStep('apd-threat-model-author',
  'Author the grounded baseline threat model. Run apd-gauntlet author-threat-model ' +
  'internally to (re)build 00-context/threat-model-skeleton.yaml, then ground or BLOCK ' +
  'each skeleton cell and emit the canonical 00-context/threat-model-normalized.yaml ' +
  '(generated_by: threat_model_author) PLUS the human-readable 00-context/threat-model-authored.md.',
  { phase: 'threat-model-author', label: 'threat-model-author',
    validateScope: runDir + '/00-context',
    outputs: runDir + '/00-context/threat-model-normalized.yaml, ' +
      runDir + '/00-context/threat-model-authored.md' });

// ===========================================================================
// PHASE 1.6 — tm-recon (gate on args.threat_model)
// ===========================================================================
phase('tm-recon');
if (args.threat_model) {
  // A TM was supplied: recon parses it into the SIBLING file so it can be diffed
  // against the always-on authored baseline (the author owns the canonical
  // 00-context/threat-model-normalized.yaml). Recon runs its parse-threat-model
  // CLI with --output 00-context/threat-model-supplied-normalized.yaml.
  llmStep('apd-threat-model-recon',
    'Parse + enrich the supplied threat model at ' + args.threat_model + ' (run apd-gauntlet ' +
    'parse-threat-model internally with --output ' +
    '00-context/threat-model-supplied-normalized.yaml as your agent contract specifies); ' +
    'emit 00-context/threat-model-supplied-normalized.yaml. Do NOT touch the canonical ' +
    'threat-model-normalized.yaml — the apd-threat-model-author agent owns it.',
    { phase: 'tm-recon', label: 'tm-recon',
      validateScope: runDir + '/00-context',
      outputs: runDir + '/00-context/threat-model-supplied-normalized.yaml' });
} else {
  log('tm-recon: no threat_model supplied — skipping Phase 1.6 (the authored baseline always exists).');
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
  // Canonicalize the whole run (idempotent, structural-only) so the tier gate
  // below sees canonical envelopes + deterministic ids. alwaysRun bypasses the
  // JS-side idempotency guard: that guard only runs `validate --schema-only`,
  // which would NOT catch fabricated ids (a semantic-pass check), so it could
  // wrongly skip canonicalize and let the tier gate fail. canonicalize is itself
  // idempotent, so always running it is safe. Runs before EACH tier gate.
  pyStep('canonicalize', {
    phase: 'canonicalize', label: 'canonicalize-' + tierDir,
    outputs: 'canonicalized lens records under ' + runDir,
    alwaysRun: true,
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
// W0: capture the receipt and HARD-BLOCK on isErr. Previously the receipt was
// unassigned, making this whole-run schema/cross-file gate advisory. A
// dict-scope capability (or any schema violation) makes `validate --errors-only`
// exit 1, which pyStep surfaces as status:'error' -> isErr true. Blocking here
// stops a poisoned corpus from reaching Phase-5 synthesis.
const vfull = pyStep('validate', {
  phase: 'tier-3', label: 'validate-full-prephase5',
  cliArgs: '--errors-only',
  outputs: 'whole-run cross-file clean (read-only gate)',
  validateScope: runDir,
});
if (isErr(vfull)) {
  log('validate-full-prephase5: status:error — whole-run corpus not schema/cross-file clean — HALT before Phase-5 synthesis.');
  throw new Error(
    'validate-full-prephase5 FAILED — the whole-run corpus is not '
    + 'schema/cross-file clean (e.g. a non-string capability scope). Fix the '
    + 'offending records before Phase-5 synthesis. See the ERROR lines above.');
}

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

// 5d rollup has MOVED: it now runs AFTER tmeval/apath (Phase 5.5/5.6) so the
// coverage rollups (nist/attack/matrix) UNION the tier-4 apath-*/tmeval-* findings
// via synthesis/rollup.py `_load_deduped` + `load_corpus(include_attack_path=True)`.
// Running it before attack-path analysis (the old order) silently produced
// coverage — and an HTML report + audit — that omitted every apath/tmeval finding.

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
    runDir + ' and write the synthesis corpus — deduped-findings.yaml, deduped-capabilities.yaml, ' +
    'contradictions.yaml, severity-disagreements.yaml, rejected-records.yaml — AND report-data.yaml, ' +
    'but do NOT write the coverage rollups (nist-coverage / attack-exposure / apd-coverage-matrix): ' +
    'the workflow runs the deterministic rollup AFTER attack-path analysis so coverage includes the ' +
    'tier-4 apath/tmeval findings. Then STOP — do NOT build or audit the report (the workflow owns ' +
    'build + audit). Return your usual summary.',
    { agentType: 'apd-synthesizer', phase: 'synthesis-fallback', label: 'synthesizer-fallback' });
}

// ===========================================================================
// PHASE 5.5 / 5.6 — tmeval + apath, in parallel, AFTER the synthesis corpus
// (deduped-findings/-capabilities exist via the decomposed apply OR the fallback)
// and BEFORE the rollup/report/build/audit — so the coverage rollups, the HTML
// report, and the audit all reflect the tier-4 apath-*/tmeval-* findings. Both
// phase() literals are emitted up front (phase() is an advisory breadcrumb) so
// the structural test can pin phase('tmeval') and phase('apath') directly, while
// the two thunks run concurrently inside the single parallel() barrier.
// ===========================================================================
phase('tmeval');
phase('apath');
parallel([
  function () {
    // tmeval gate WIDENED from args.threat_model to TM-present: the always-on
    // author phase guarantees a canonical 00-context/threat-model-normalized.yaml
    // (generated_by: threat_model_author), so the evaluator ALWAYS runs. Its own
    // internal activation is file-existence. When a TM was supplied, the recon
    // sibling 00-context/threat-model-supplied-normalized.yaml is also present and
    // the evaluator runs the supplied-vs-authored comparator; with no sibling it
    // runs the baseline-only carve-out (contradiction + specialist corroboration).
    return llmStep('apd-threat-model-evaluator',
      'Evaluate the run against the authored baseline 00-context/threat-model-normalized.yaml ' +
      '(generated_by: threat_model_author). If 00-context/threat-model-supplied-normalized.yaml ' +
      'exists, run the supplied-vs-authored comparator (emit omission findings + the ' +
      'supplied_vs_authored delta block); otherwise apply the baseline-only carve-out. Emit ' +
      '40-synthesis/threat-model-coverage.yaml + tmeval findings.',
      { phase: 'tmeval', label: 'tmeval',
        outputs: runDir + '/40-synthesis/threat-model-coverage.yaml' });
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

// 5c.4 assemble-c4 (Python) — deterministic C4 model assembler. Runs HERE,
// after the tmeval/apath barrier so 40-synthesis/asset-graph.yaml exists, and
// BEFORE canonicalize/rollup. Mirrors assemble-inventory (ADR-0020 field
// ownership): the agent-authored 00-context/c4-recon.yaml + asset-graph.yaml
// are content-only; assemble-c4 is the SOLE minter of c4-/c4e- ids and the
// finding_count/capability_count badge rollups it writes to
// 40-synthesis/c4-model.yaml. It runs whenever asset-graph.yaml exists and
// includes the L4/L3 code tiers only when 00-context/code-evidence-index.yaml
// is present (the C4 scene then renders whatever c4-model.yaml contains).
pyStep('assemble-c4', {
  phase: 'apath', label: 'assemble-c4',
  outputs: runDir + '/40-synthesis/c4-model.yaml (c4-/c4e- ids minted; finding/capability badges rolled up)',
  alwaysRun: true,
});

// 5c.5 canonicalize — mint tmeval-* ids from the evaluator's tmeval_key BEFORE
// rollup. The evaluator now emits a structured tmeval_key (not a hand-computed
// id); the assembler is the sole author of tmeval-<sha8>. This MUST run after the
// tmeval/apath barrier and before rollup, which loads tmeval-* findings BY ID into
// nist/attack/matrix coverage — an un-minted (id-less) tmeval finding would drop
// out of the rollup. (apath-* records are out-of-scope here and pass through.)
pyStep('canonicalize', {
  phase: 'tmeval', label: 'canonicalize-tmeval',
  outputs: 'tmeval- ids minted under ' + runDir + '/40-threat-model/',
  alwaysRun: true,
});

// 5d rollup (Python) — runs HERE, after tmeval/apath, in BOTH the decomposed and
// fallback paths. synthesis/rollup.py `_load_deduped` unions the apath-* findings
// (load_corpus pulls tmeval-* too), so nist/attack/matrix coverage now reflects
// the tier-4 findings. After this, the FULL validate covers nist/attack/matrix.
phase('synthesis-rollup');
let rl = pyStep('rollup', { phase: 'synthesis-rollup', label: 'rollup',
  outputs: runDir + '/40-synthesis/nist-coverage.yaml, attack-exposure.yaml, apd-coverage-matrix.yaml, metrics.yaml (+ declared-taxonomy coverage files)' });
if (isErr(rl)) {
  rl = pyStep('rollup', { phase: 'synthesis-rollup', label: 'rollup-retry-1',
    outputs: runDir + '/40-synthesis/nist-coverage.yaml' });
  if (isErr(rl)) {
    // Last resort: the deterministic rollup failed twice. Have the synthesizer
    // write the coverage rollups directly (deduped corpus + apath findings) so
    // build-report's required nist/attack/matrix inputs exist.
    log('rollup: deterministic rollup failed after retry — synthesizer writes coverage as last resort.');
    agent(
      'Run as the synthesis FALLBACK and write the coverage rollups ' +
      runDir + '/40-synthesis/nist-coverage.yaml, attack-exposure.yaml, apd-coverage-matrix.yaml ' +
      'AND 40-synthesis/metrics.yaml (the report loader REQUIRES metrics.yaml — without it ' +
      'build-report cannot run, so a coverage-only last resort would still block the report) ' +
      'from the deduped corpus PLUS the tier-4 findings (attack-path.findings.yaml apath-* AND ' +
      '40-threat-model/threat-model.findings.yaml tmeval-*), then STOP.',
      { agentType: 'apd-synthesizer', phase: 'synthesis-rollup', label: 'synthesizer-fallback-rollup' });
  }
}

// ===========================================================================
// 5e report-writer (LLM) -> 5f build-report (Python) -> 5g audit loop (cap N=2).
// The workflow owns build + audit even in fallback.
// ===========================================================================
phase('synthesis-report');
llmStep('apd-report-writer',
  'Read 40-synthesis/metrics.yaml + deduped-findings.yaml + attack-path.findings.yaml (apath-*, when present) + ' +
  'the COMPACT rollups + contradictions/severity-disagreements; rank the headline findings across ' +
  'BOTH the deduped and apath sets; emit 40-synthesis/advisory-report.md + 40-synthesis/report-data.yaml.',
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

// If build-report's dispatch was INTERRUPTED (null receipt — distinct from a real
// exit-1, which carries status:'error'), the report cannot exist; bail with the
// resume guidance rather than entering the audit loop and emitting a misleading
// "completeness gate FAILED" on a wiped run.
bailIfInterrupted(build, 'synthesis-build');

// 5g audit loop — gate + auto-remediate, cap N=2 (3 attempts total).
phase('synthesis-audit');
let critique = null;
for (let i = 0; i <= 2; i++) {
  const audit = pyStep('audit-report', { phase: 'synthesis-audit', label: 'audit-report-attempt-' + i,
    reportAudit: true,
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
  // F3: split the deterministic audit into its STRUCTURAL vs EDITORIAL classes.
  // structuralOk now keys on the per-class structural_failed count the worker
  // lifted into report_audit (truthful name); it falls back to the command exit
  // status for older receipts that omit report_audit. Editorial completeness is
  // remediated in-loop but, like the LLM semantic residual, is NON-BLOCKING at
  // the cap — only STRUCTURAL completeness (or an unverifiable report) blocks.
  const ra = audit && audit.report_audit;
  const structuralOk = !!audit && (ra ? ra.structural_failed === 0 : audit.status === 'ok');
  const editorialOk = !ra || ra.editorial_failed === 0;
  const semanticOk = typeof auditor === 'string' && /GATE:\s*pass/i.test(auditor);
  if (structuralOk && editorialOk && semanticOk) { break; }
  if (i === 2) {
    // Report completeness gate: a STRUCTURAL failure (or an unverifiable report)
    // must NEVER ship. The LLM auditor's semantic residual AND any residual
    // editorial completeness gap stay non-blocking after the remediation cap.
    if (!audit) {
      // A null audit receipt = an INTERRUPTED dispatch, not a genuine structural
      // failure. Surface the resume guidance instead of a misleading completeness
      // verdict on a report that may simply not have been built yet.
      bailIfInterrupted(audit, 'synthesis-audit');
    }
    if (!structuralOk) {
      throw new Error(
        'report completeness gate: audit-report still FAILED a STRUCTURAL check after 2 ' +
        'remediations — the HTML report is structurally incomplete (see ' + runDir +
        '/40-synthesis/report-audit.yaml). Refusing to ship a degraded report.');
    }
    log('report audit: residual SEMANTIC discrepancies (plus any editorial residual) after 2 ' +
        'remediations; surfacing non-blocking.');
    break;
  }
  critique = typeof auditor === 'string' ? auditor : '';
  // Feed BOTH the structural audit (report-audit.yaml) AND the semantic critique back
  // into 5e, then rebuild 5f. The report-writer reads report-audit.yaml and fixes any
  // failed editorial completeness checks (exec_summary/posture_summary/headline/next_steps).
  llmStep('apd-report-writer',
    'Read ' + runDir + '/40-synthesis/report-audit.yaml: address EVERY failed check whose ' +
    'klass is "editorial" by regenerating 40-synthesis/report-data.yaml + advisory-report.md ' +
    '(exec_summary paragraphs, posture_summary, headline_findings, next_steps). ALSO address ' +
    'this semantic critique. CRITIQUE: ' + critique,
    { phase: 'synthesis-report', label: 'report-writer-attempt-' + (i + 1),
      outputs: runDir + '/40-synthesis/report-data.yaml' });
  pyStep('build-report', { phase: 'synthesis-build', label: 'build-report-attempt-' + (i + 1),
    outputs: runDir + '/40-synthesis/report-html/data.js' });
}

// ===========================================================================
// PHASE 5.5 / 5.6 (tmeval + apath) have MOVED earlier — they now run BEFORE the
// rollup/report/build/audit (see above) so the coverage rollups, the HTML
// report, and the audit all reflect the tier-4 apath-*/tmeval-* findings.
// ===========================================================================

// ===========================================================================
// PHASE 5h — domain-improvement capture (Subsystem B). ADVISORY / NON-BLOCKING.
// Runs AFTER the 5g audit loop and BEFORE closeout, over the SETTLED corpus.
// Never gates the run, never touches the HTML report. Empty-but-valid artifact
// when there are no opportunities. Neither step is wrapped in isErr()/throw.
// ===========================================================================
phase('domain-coverage-delta');
// 5h-i — deterministic coverage-delta pre-pass (Python). Best-effort: a failure
// here does NOT halt the run; the agent can still harvest judgment opportunities.
pyStep('domain-coverage-delta', {
  phase: 'domain-coverage-delta', label: 'domain-coverage-delta',
  outputs: runDir + '/40-synthesis/domain-coverage-delta.yaml' });

phase('domain-improvements');
// 5h-ii — apd-domain-auditor (LLM) reads the delta + settled findings + the merged
// apd-domain skill + asset-inventory; writes domain-improvements.yaml. Advisory:
// NOT wrapped in isErr()/HALT; a single best-effort dispatch, and the run proceeds
// to closeout regardless of its status.
llmStep('apd-domain-auditor',
  'Capture domain-improvement opportunities for this run. Read ' +
  '40-synthesis/domain-coverage-delta.yaml + 40-synthesis/deduped-findings.yaml + ' +
  '.claude/skills/apd-domain/SKILL.md + 00-context/asset-inventory.yaml; emit ' +
  '40-synthesis/domain-improvements.yaml (an empty-but-valid {schema_version:1, ' +
  'generated_by:domain-auditor, examined_domains:[...], improvements:[]} when there ' +
  'are no opportunities). ADVISORY — this never gates the run.',
  { phase: 'domain-improvements', label: 'domain-auditor',
    validateScope: runDir + '/40-synthesis',
    outputs: runDir + '/40-synthesis/domain-improvements.yaml' });

// 5h-iii canonicalize — mint dimpr-<sha8> ids from the domain-auditor's records
// (it now emits content only; the assembler is the sole id author). Runs before
// the closeout validate, whose _validate_domain_improvements_cross_refs recomputes
// and would flag an un-minted (id-less) record.
pyStep('canonicalize', {
  phase: 'domain-improvements', label: 'canonicalize-dimpr',
  outputs: 'dimpr- ids minted in ' + runDir + '/40-synthesis/domain-improvements.yaml',
  alwaysRun: true,
});

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
