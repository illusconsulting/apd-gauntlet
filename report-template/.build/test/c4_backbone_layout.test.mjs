// report-template/.build/test/c4_backbone_layout.test.mjs
// Pure unit test for the deterministic C4 backbone layout (layered BFS longest-path
// columns + analyzed/infra partitions + stable sorts). Run: node <thisfile>.
// c4BackboneLayout is re-declared inline (kept behaviorally identical to
// components.jsx) so the placement math is testable under plain node, with no DOM
// and no React.
import assert from "node:assert/strict";

// ── ported from components.jsx (behaviorally identical) ──────────────────────
const COL_W = 360, ROW_H = 150;
function c4BackboneLayout(nodes, edges) {
  const containers = (nodes || []).filter((n) => n && n.type === "container");
  const byId = {};
  containers.forEach((n) => { byId[n.id] = n; });

  // partition: connected = appears as either endpoint of an edge whose BOTH ends
  // are known containers; analyzed / infra fall to the shelves.
  const sub = [];
  const endpoints = {};
  (edges || []).forEach((e) => {
    if (e && byId[e.source] && byId[e.target] && e.source !== e.target) {
      sub.push(e); endpoints[e.source] = true; endpoints[e.target] = true;
    }
  });
  const connectedIds = containers.filter((n) => endpoints[n.id]).map((n) => n.id);
  const connSet = {}; connectedIds.forEach((id) => { connSet[id] = true; });
  const lbl = (id) => (byId[id].label || id);
  const analyzed = containers
    .filter((n) => !connSet[n.id] && n.analysis_state !== "not_analyzed")
    .map((n) => n.id)
    .sort((a, b) => lbl(a).localeCompare(lbl(b)));
  const infra = containers
    .filter((n) => !connSet[n.id] && n.analysis_state === "not_analyzed")
    .map((n) => n.id)
    .sort((a, b) => lbl(a).localeCompare(lbl(b)));

  // longest-path column assignment over the connected subgraph; cycles broken by
  // first-seen (the want is capped at N-1 so a back-edge never inflates columns
  // past the bound, and the pass loop terminates cleanly).
  const col = {};
  connectedIds.forEach((id) => { col[id] = 0; });
  const orderedEdges = sub
    .filter((e) => connSet[e.source] && connSet[e.target])
    .slice()
    .sort((a, b) => {
      const ka = a.source + "|" + a.target, kb = b.source + "|" + b.target;
      return ka < kb ? -1 : ka > kb ? 1 : 0;
    });
  const maxPasses = connectedIds.length + 1;
  for (let pass = 0; pass < maxPasses; pass++) {
    let changed = false;
    for (let i = 0; i < orderedEdges.length; i++) {
      const e = orderedEdges[i];
      const want = col[e.source] + 1;
      if (want <= connectedIds.length - 1 && col[e.target] < want) {
        col[e.target] = want; changed = true;
      }
    }
    if (!changed) break;
  }

  // pull each SOURCE (in-degree 0) right to (min target col − 1) so a source's
  // column-SKIP edge is removed (it would otherwise cross the skipped column's
  // fan-out). No-op unless a source skips a column; never changes a downstream
  // node's longest-path column.
  const indeg = {};
  connectedIds.forEach((id) => { indeg[id] = 0; });
  orderedEdges.forEach((e) => { indeg[e.target] = (indeg[e.target] || 0) + 1; });
  connectedIds.forEach((id) => {
    if (indeg[id] !== 0) return;
    const targetCols = orderedEdges.filter((e) => e.source === id).map((e) => col[e.target]);
    if (!targetCols.length) return;
    const want = Math.min.apply(null, targetCols) - 1;
    if (want > col[id]) col[id] = want;
  });

  // group by column; stable-sort within a column: label asc, then badge desc
  // (foreground hot nodes), then id asc as the final deterministic tie-break.
  // Assign row index + deterministic pixel positions (x = col*COL_W, y = row*ROW_H).
  const cmpInCol = (a, b) => {
    const c = lbl(a).localeCompare(lbl(b));
    if (c !== 0) return c;
    const ba = byId[a].badge || 0, bb = byId[b].badge || 0;
    if (ba !== bb) return bb - ba; // foreground hot nodes
    return a < b ? -1 : a > b ? 1 : 0;
  };
  const cols = {};
  connectedIds.forEach((id) => { (cols[col[id]] = cols[col[id]] || []).push(id); });
  const connected = [];
  Object.keys(cols).map(Number).sort((a, b) => a - b).forEach((c) => {
    cols[c].sort(cmpInCol);
    cols[c].forEach((id, row) => {
      connected.push({ id, col: c, row, x: c * COL_W, y: row * ROW_H });
    });
  });
  return { connected, analyzed, infra };
}
// ── /ported ──────────────────────────────────────────────────────────────

const N = (id, label, st, badge) => ({ id, label, type: "container", analysis_state: st || "analyzed", badge: badge });

// hub-and-spoke (the Home Assistant shape): cli -> supervisor -> core -> {os-agent, dockerd}
{
  const nodes = [
    N("a", "ha CLI"), N("s", "Supervisor"), N("c", "Core"),
    N("o", "os-agent"), N("d", "host-dockerd"),
    N("x", "Frontend"),                 // analyzed, no edge -> shelf
    N("z", ".storage", "not_analyzed"), // infra shelf
  ];
  const edges = [
    { source: "a", target: "s" }, { source: "s", target: "c" },
    { source: "c", target: "o" }, { source: "c", target: "d" },
  ];
  const { connected, analyzed, infra } = c4BackboneLayout(nodes, edges);
  const colOf = {}; connected.forEach((p) => { colOf[p.id] = p.col; });
  assert.equal(colOf.a, 0, "root of the chain is column 0");
  assert.equal(colOf.s, 1);
  assert.equal(colOf.c, 2);
  assert.equal(colOf.o, 3); assert.equal(colOf.d, 3, "both leaves land in the last column");
  // x/z are NOT in the backbone; they fall to the shelves
  assert.deepEqual(analyzed, ["x"]);
  assert.deepEqual(infra, ["z"]);
  // pixel positions derive from col/row deterministically
  const pa = connected.find((p) => p.id === "a");
  assert.equal(pa.x, 0); assert.equal(pa.y, 0);
}
// same column nodes stable-sort by label and get distinct rows
{
  const nodes = [N("h", "Hub"), N("b", "Beta"), N("a", "Alpha")];
  const edges = [{ source: "h", target: "b" }, { source: "h", target: "a" }];
  const { connected } = c4BackboneLayout(nodes, edges);
  const col1 = connected.filter((p) => p.col === 1).sort((p, q) => p.row - q.row);
  assert.deepEqual(col1.map((p) => p.id), ["a", "b"], "column members ordered by label");
  assert.deepEqual(col1.map((p) => p.row), [0, 1], "distinct rows within a column");
}
// within a column, same label -> higher badge wins the LOWER row (badge desc).
// hot1/hot2 share the label "Dup" but differ in badge (9 vs 2); a distinct third
// ("Edge") sorts after by label. Pins the badge-desc tie-break.
{
  const nodes = [
    N("h", "Hub"),
    N("hot1", "Dup", "analyzed", 2),
    N("hot2", "Dup", "analyzed", 9),
    N("e", "Edge", "analyzed", 0),
  ];
  const edges = [
    { source: "h", target: "hot1" },
    { source: "h", target: "hot2" },
    { source: "h", target: "e" },
  ];
  const { connected } = c4BackboneLayout(nodes, edges);
  const col1 = connected.filter((p) => p.col === 1).sort((p, q) => p.row - q.row);
  // label "Dup" (badge 9 then badge 2) sorts before label "Edge"
  assert.deepEqual(col1.map((p) => p.id), ["hot2", "hot1", "e"],
    "label asc, then badge desc: hotter Dup node leads, then cooler Dup, then Edge");
  const rowOf = {}; col1.forEach((p) => { rowOf[p.id] = p.row; });
  assert.equal(rowOf.hot2, 0, "higher badge (9) gets the lower row index");
  assert.ok(rowOf.hot2 < rowOf.hot1, "badge desc: hot2 (9) above hot1 (2)");
}
// final tie-break: same label AND same badge -> lower id is row 0 (id asc).
{
  const nodes = [
    N("h", "Hub"),
    N("zeta", "Same", "analyzed", 5),
    N("alpha", "Same", "analyzed", 5),
  ];
  const edges = [
    { source: "h", target: "zeta" },
    { source: "h", target: "alpha" },
  ];
  const { connected } = c4BackboneLayout(nodes, edges);
  const col1 = connected.filter((p) => p.col === 1).sort((p, q) => p.row - q.row);
  assert.deepEqual(col1.map((p) => p.id), ["alpha", "zeta"],
    "same label + same badge -> id asc decides");
  const rowOf = {}; col1.forEach((p) => { rowOf[p.id] = p.row; });
  assert.equal(rowOf.alpha, 0, "lower id ('alpha') gets row 0 on the final tie-break");
}
// a 2-cycle does not loop forever and does not push a node infinitely right
{
  const nodes = [N("p", "P"), N("q", "Q")];
  const edges = [{ source: "p", target: "q" }, { source: "q", target: "p" }];
  const { connected } = c4BackboneLayout(nodes, edges);
  assert.equal(connected.length, 2);
  connected.forEach((p) => assert.ok(p.col <= 1, "cycle broken by first-seen; bounded columns"));
}
// self-edges and edges to non-containers are ignored (never invented endpoints)
{
  const nodes = [N("a", "A"), N("b", "B")];
  const edges = [{ source: "a", target: "a" }, { source: "a", target: "ghost" }];
  const { connected, analyzed } = c4BackboneLayout(nodes, edges);
  assert.equal(connected.length, 0, "no real edge -> empty backbone");
  assert.deepEqual(analyzed, ["a", "b"]);
}
// a column-SKIPPING source is PULLED adjacent to its nearest target (this is what
// removes the iOS Companion -> Core cross-the-Supervisor-hub crossings).
{
  const nodes = [N("root", "Root"), N("mid", "Mid"), N("far", "Far"), N("src", "Src")];
  // spine root->mid->far puts far at col 2; src->far alone would be col 1, but
  // longest-path parks the SOURCE src at col 0, making src->far a 2-col skip.
  const edges = [
    { source: "root", target: "mid" }, { source: "mid", target: "far" },
    { source: "src", target: "far" },
  ];
  const { connected } = c4BackboneLayout(nodes, edges);
  const colOf = {}; connected.forEach((p) => { colOf[p.id] = p.col; });
  assert.equal(colOf.far, 2, "far is col 2 via the longest path root->mid->far");
  assert.equal(colOf.src, 1, "the source 'src' is PULLED to col 1 (adjacent to far), not col 0");
  assert.ok(colOf.src === colOf.far - 1, "pulled source sits one column left of its nearest target");
}
// the pull is a NO-OP when a source's target is already adjacent (no skip)
{
  const nodes = [N("a", "A"), N("b", "B")];
  const { connected } = c4BackboneLayout(nodes, [{ source: "a", target: "b" }]);
  const colOf = {}; connected.forEach((p) => { colOf[p.id] = p.col; });
  assert.equal(colOf.a, 0, "adjacent source stays col 0 (no skip to remove)");
  assert.equal(colOf.b, 1);
}
// DETERMINISM: identical input -> byte-identical output
{
  const nodes = [N("a", "A"), N("b", "B"), N("c", "C")];
  const edges = [{ source: "a", target: "b" }, { source: "b", target: "c" }];
  assert.equal(JSON.stringify(c4BackboneLayout(nodes, edges)),
               JSON.stringify(c4BackboneLayout(nodes, edges)));
}

console.log("c4_backbone_layout.test.mjs: all assertions passed");
