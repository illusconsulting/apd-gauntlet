// Test-only harness: run the apd-gauntlet workflow under stub Workflow globals and
// print every dispatch it makes.
//
//   node tests/js/workflow_dispatch_trace.mjs <workflow.js> '<args-json>' ['<fail-json>']
//
// Prints a JSON list of {agentType, label, phase, guard, command} on stdout, one entry
// per agent() call in dispatch order. command is the prompt's `COMMAND: ` line (null
// for an agent step) and guard says whether the prompt carries the idempotency guard.
// If the workflow throws, the list of dispatches made so far is still printed, the
// message goes to stderr and the exit code is 3.
//
// fail-json maps a label to the names of its failing steps: that dispatch returns
// status 'error' with one errors[] entry per name (message 'exit=1; stub'); an empty
// list yields one error whose path is the label. Every other receipt is 'ok'. A
// dispatch without a schema (the report auditor, a fallback) answers 'GATE: pass'.
//
// The stubs behave like the Workflow runtime: agent() records its trace entry at call
// time and returns a Promise of the receipt, resolved on a later macrotask, so a dispatch
// the workflow does not await reads as a pending Promise, as it would at runtime.
// parallel(thunks) is a barrier that never rejects: a thunk that throws or rejects
// resolves to null at its index.
//
// With TRACE_LOGS set in the environment, every log() message the workflow wrote is
// also printed on stderr, one `log: <message>` line each, before any failure message.
import { readFileSync } from 'node:fs';
import vm from 'node:vm';

const [, , wfPath, argsJson, failJson] = process.argv;
const fail = failJson ? JSON.parse(failJson) : {};
const src = readFileSync(wfPath, 'utf8').replace(/^export const meta/m, 'const meta');
const trace = [];
const logs = [];

function receipt(prompt, opts) {
  const m = /^COMMAND: (.+)$/m.exec(prompt);
  trace.push({
    agentType: opts.agentType || null, label: opts.label, phase: opts.phase || null,
    guard: prompt.includes('IDEMPOTENCY GUARD'), command: m ? m[1] : null,
  });
  if (!opts.schema) return 'GATE: pass';
  const base = {
    agent: 'stub', outputs: [], counts: {}, resume_plan: { engine_version: '0', steps: [] },
    report_audit: { structural_failed: 0, editorial_failed: 0 },
  };
  const names = fail[opts.label];
  if (!names) return { ...base, status: 'ok' };
  return {
    ...base, status: 'error',
    errors: (names.length ? names : [opts.label]).map((n) => ({ path: n, message: 'exit=1; stub' })),
  };
}

function agent(prompt, opts = {}) {
  const value = receipt(prompt, opts);
  return new Promise((r) => setTimeout(() => r(value), 0));
}

const ctx = {
  args: JSON.parse(argsJson), agent, phase() {}, log(m) { logs.push(String(m)); },
  parallel: (ts) => Promise.all(ts.map((t) => (async () => {
    try { return await t(); } catch (e) { return null; }
  })())),
};
let failed = null;
try {
  await vm.runInNewContext('(async function () {\n' + src + '\n})()', ctx);
} catch (e) {
  failed = String((e && e.message) || e);
}
process.stdout.write(JSON.stringify(trace));
if (process.env.TRACE_LOGS) process.stderr.write(logs.map((m) => 'log: ' + m + '\n').join(''));
if (failed !== null) {
  process.stderr.write(failed);
  // exitCode, not exit(): a write to a pipe can still be pending on macOS.
  process.exitCode = 3;
}
