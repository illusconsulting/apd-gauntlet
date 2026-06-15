// check-fixture-keys.js — node, no deps. Asserts archx-data.js exposes the
// REAL window.APD_DATA.c4_model field names (from transform.py::c4_model_view)
// and NONE of the prototype-era abbreviations (cap/state/ff/me/overlay_paths).
// Usage: node check-fixture-keys.js  → exit 0 = pass, 1 = fail (prints diffs).
'use strict';
const fs = require('fs');
const path = require('path');

// Evaluate the fixture in a minimal window sandbox.
const src = fs.readFileSync(path.join(__dirname, 'archx-data.js'), 'utf8');
const window = {};
// eslint-disable-next-line no-new-func
new Function('window', src)(window);
const C4 = window.C4_DATA;

const fails = [];
const ok = (cond, msg) => { if (!cond) fails.push(msg); };

// ── top-level shape (the full c4_model_view return) ──────────────────────
const TOP_REQUIRED = [
  'present', 'nodes', 'edges', 'unlocalized_findings', 'not_analyzed_count',
  'levels_present', 'asset_to_c4', 'finding_to_c4',
];
TOP_REQUIRED.forEach(k => ok(k in C4, `MISSING top-level key: ${k}`));
ok(C4.present === true, 'present must be true (this is a present run slice)');
ok(!('overlay_paths' in C4), 'FORBIDDEN fabricated top-level key: overlay_paths');
ok(Array.isArray(C4.nodes) && C4.nodes.length > 0, 'nodes must be a non-empty array');
ok(Array.isArray(C4.edges) && C4.edges.length > 0, 'edges must be a non-empty array');
ok(C4.asset_to_c4 && typeof C4.asset_to_c4 === 'object', 'asset_to_c4 must be an object');
ok(C4.finding_to_c4 && typeof C4.finding_to_c4 === 'object', 'finding_to_c4 must be an object');

// ── node shape ───────────────────────────────────────────────────────────
const NODE_REQUIRED = [
  'id', 'label', 'type', 'kind', 'parent', 'badge', 'capability_badge',
  'analysis_state', 'provenance',
];
const NODE_FORBIDDEN = ['cap', 'state', 'ff', 'me'];
C4.nodes.forEach((n, i) => {
  NODE_REQUIRED.forEach(k => ok(k in n, `node[${i}] (${n.id}) MISSING key: ${k}`));
  NODE_FORBIDDEN.forEach(k => ok(!(k in n), `node[${i}] (${n.id}) FORBIDDEN abbrev key: ${k}`));
  // badge is finding_count|null (never the literal 0 'clean' lie)
  ok(n.badge === null || (typeof n.badge === 'number' && n.badge > 0),
     `node[${i}] (${n.id}) badge must be null or a positive int, got ${JSON.stringify(n.badge)}`);
  ok(typeof n.capability_badge === 'number',
     `node[${i}] (${n.id}) capability_badge must be a number`);
  ok(n.analysis_state === 'analyzed' || n.analysis_state === 'not_analyzed',
     `node[${i}] (${n.id}) analysis_state must be analyzed|not_analyzed`);
  ok(n.provenance && typeof n.provenance === 'object',
     `node[${i}] (${n.id}) provenance must be an object`);
});

// ── edge shape ─────────────────────────────────────────────────────────────
const EDGE_REQUIRED = ['id', 'source', 'target', 'label', 'machine_extracted'];
C4.edges.forEach((e, i) => {
  EDGE_REQUIRED.forEach(k => ok(k in e, `edge[${i}] (${e.id}) MISSING key: ${k}`));
  ok(!('me' in e), `edge[${i}] (${e.id}) FORBIDDEN abbrev key: me`);
  ok(typeof e.machine_extracted === 'boolean',
     `edge[${i}] (${e.id}) machine_extracted must be boolean`);
  ok(typeof e.label === 'string' && e.label.startsWith('CROSS_'),
     `edge[${i}] (${e.id}) label must be the full machine string (CROSS_*)`);
});

// ── spot-check the real HA values survived the regeneration ────────────────
const core = C4.nodes.find(n => n.id === 'c4-2b33e14f');
ok(core && core.badge === 22 && core.capability_badge === 15,
   'Core (c4-2b33e14f) must keep badge=22, capability_badge=15');
const docker = C4.nodes.find(n => n.id === 'c4-bc1e61b2');
ok(docker && docker.analysis_state === 'not_analyzed' && docker.badge === null,
   'docker (c4-bc1e61b2) must be not_analyzed with badge=null');

if (fails.length) {
  console.error(`FIXTURE KEY CHECK FAILED (${fails.length}):`);
  fails.forEach(f => console.error('  - ' + f));
  process.exit(1);
}
console.log(`fixture key check OK: ${C4.nodes.length} nodes, ${C4.edges.length} edges, real keys present, abbreviations absent.`);
