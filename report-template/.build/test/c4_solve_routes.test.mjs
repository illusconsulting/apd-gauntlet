// report-template/.build/test/c4_solve_routes.test.mjs
// Pure unit + oracle tests for the GLOBAL C4 connector router (c4Grid /
// c4SolveRoutes). Run: node report-template/.build/test/c4_solve_routes.test.mjs
// (no deps, no DOM). The routing fns are re-declared VERBATIM from components.jsx
// so the geometry is testable under plain node — this is the committed,
// reproducible version of the headless oracle (which asserts the same four
// defect counts on the rendered report).
import assert from "node:assert/strict";

// ── verbatim from components.jsx ─────────────────────────────────────────────
function c4RouteWaypoints(s, t) {
  const dx = t.cx - s.cx, dy = t.cy - s.cy;
  if (Math.abs(dx) >= Math.abs(dy)) {
    const sx = dx >= 0 ? s.x + s.w : s.x;
    const tx = dx >= 0 ? t.x : t.x + t.w;
    const midX = (sx + tx) / 2;
    return [{ x: sx, y: s.cy }, { x: midX, y: s.cy }, { x: midX, y: t.cy }, { x: tx, y: t.cy }];
  } else {
    const sy = dy >= 0 ? s.y + s.h : s.y;
    const ty = dy >= 0 ? t.y : t.y + t.h;
    const midY = (sy + ty) / 2;
    return [{ x: s.cx, y: sy }, { x: s.cx, y: midY }, { x: t.cx, y: midY }, { x: t.cx, y: ty }];
  }
}
function c4RoundedPath(pts, rad = 7) {
  const p = [];
  pts.forEach((q) => { const l = p[p.length - 1]; if (!l || Math.abs(l.x - q.x) > 0.5 || Math.abs(l.y - q.y) > 0.5) p.push(q); });
  if (p.length < 2) return "";
  let d = `M ${p[0].x} ${p[0].y}`;
  for (let i = 1; i < p.length - 1; i++) {
    const a = p[i - 1], b = p[i], c = p[i + 1];
    const l1 = Math.hypot(b.x - a.x, b.y - a.y), l2 = Math.hypot(c.x - b.x, c.y - b.y);
    const r = Math.min(rad, l1 / 2, l2 / 2);
    const u1 = { x: (a.x - b.x) / (l1 || 1), y: (a.y - b.y) / (l1 || 1) };
    const u2 = { x: (c.x - b.x) / (l2 || 1), y: (c.y - b.y) / (l2 || 1) };
    d += ` L ${(b.x + u1.x * r).toFixed(1)} ${(b.y + u1.y * r).toFixed(1)}`
       + ` Q ${b.x} ${b.y} ${(b.x + u2.x * r).toFixed(1)} ${(b.y + u2.y * r).toFixed(1)}`;
  }
  const last = p[p.length - 1];
  return d + ` L ${last.x} ${last.y}`;
}
function c4ShortEdgeLabel(rawLabel) {
  let s = rawLabel == null ? "" : String(rawLabel);
  s = s.replace(/^\s*CROSS_[A-Z_]+\s*[—:-]*\s*/, "");
  s = s.trim();
  if (!s) return "";
  const words = s.split(/\s+/).filter(Boolean);
  return words.slice(0, 3).join(" ");
}
const C4_PAD = 8;
const c4Clamp = (v, lo, hi) => Math.max(lo, Math.min(hi, v));
function c4Median(arr) { const s = arr.slice().sort((a, b) => a - b); return s.length ? s[Math.floor(s.length / 2)] : 0; }
function c4Cluster1D(vals, tol) {
  const u = Array.from(new Set(vals)).sort((a, b) => a - b);
  const cl = [];
  u.forEach((v) => { const last = cl[cl.length - 1]; if (!last || v - last.max > tol) cl.push({ lo: v, max: v }); else last.max = v; });
  return cl;
}
function c4Grid(rects) {
  const mw = c4Median(rects.map((r) => r.w)) || 1;
  const mh = c4Median(rects.map((r) => r.h)) || 1;
  const TOLX = 0.5 * mw, TOLY = 0.5 * mh;
  const colCl = c4Cluster1D(rects.map((r) => r.x), TOLX);
  const rowCl = c4Cluster1D(rects.map((r) => r.y), TOLY);
  const C = colCl.length, R = rowCl.length;
  const colL = [], colR = [], rowT = [], rowB = [];
  colCl.forEach((c, i) => { const m = rects.filter((r) => r.x >= c.lo - 0.001 && r.x <= c.max + 0.001); colL[i] = Math.min.apply(null, m.map((r) => r.x)); colR[i] = Math.max.apply(null, m.map((r) => r.x + r.w)); });
  rowCl.forEach((c, i) => { const m = rects.filter((r) => r.y >= c.lo - 0.001 && r.y <= c.max + 0.001); rowT[i] = Math.min.apply(null, m.map((r) => r.y)); rowB[i] = Math.max.apply(null, m.map((r) => r.y + r.h)); });
  const idxBy = (cl, v, tol) => { for (let i = 0; i < cl.length; i++) if (v >= cl[i].lo - tol && v <= cl[i].max + tol) return i; let bi = 0, bd = Infinity; for (let i = 0; i < cl.length; i++) { const d = Math.abs(v - cl[i].lo); if (d < bd) { bd = d; bi = i; } } return bi; };
  const colOf = (rect) => idxBy(colCl, rect.x, TOLX);
  const rowOf = (rect) => idxBy(rowCl, rect.y, TOLY);
  const MARG = 40;
  const gutCenter = (g) => g < 0 ? colL[0] - MARG : g >= C - 1 ? colR[C - 1] + MARG : (colR[g] + colL[g + 1]) / 2;
  const gutLo = (g) => g < 0 ? colL[0] - 2 * MARG : g >= C - 1 ? colR[C - 1] : colR[g];
  const gutHi = (g) => g < 0 ? colL[0] : g >= C - 1 ? colR[C - 1] + 2 * MARG : colL[g + 1];
  const bandCenter = (b) => b < 0 ? rowT[0] - MARG : b >= R - 1 ? rowB[R - 1] + MARG : (rowB[b] + rowT[b + 1]) / 2;
  const bandLo = (b) => b < 0 ? rowT[0] - 2 * MARG : b >= R - 1 ? rowB[R - 1] : rowB[b];
  const bandHi = (b) => b < 0 ? rowT[0] : b >= R - 1 ? rowB[R - 1] + 2 * MARG : rowT[b + 1];
  return { C, R, colL, colR, rowT, rowB, colOf, rowOf, gutCenter, gutLo, gutHi, bandCenter, bandLo, bandHi };
}
function c4SegHitsRect(a, b, r, pad) {
  const x0 = Math.min(a.x, b.x), x1 = Math.max(a.x, b.x), y0 = Math.min(a.y, b.y), y1 = Math.max(a.y, b.y);
  const rx0 = r.x - pad, rx1 = r.x + r.w + pad, ry0 = r.y - pad, ry1 = r.y + r.h + pad;
  return x0 < rx1 && x1 > rx0 && y0 < ry1 && y1 > ry0;
}
function c4WpHitsAny(wp, obstacles, pad) {
  for (let i = 1; i < wp.length; i++) for (let k = 0; k < obstacles.length; k++) if (c4SegHitsRect(wp[i - 1], wp[i], obstacles[k], pad)) return true;
  return false;
}
function c4SolveRoutes(rects, edges, liveSet) {
  const byId = {};
  rects.forEach((r) => { r.r = r.x + r.w; r.b = r.y + r.h; r.cx = r.x + r.w / 2; r.cy = r.y + r.h / 2; byId[r.id] = r; });
  const E = (edges || []).map((e, idx) => ({ e, idx })).filter((o) => byId[o.e.source] && byId[o.e.target] && o.e.source !== o.e.target);
  if (!E.length) return [];
  const grid = c4Grid(rects);
  const obstaclesFor = (m) => rects.filter((r) => r.id !== m.S.id && r.id !== m.T.id);
  const meta = E.map((o) => {
    const S = byId[o.e.source], T = byId[o.e.target];
    const cs = grid.colOf(S), ct = grid.colOf(T), rs = grid.rowOf(S), rt = grid.rowOf(T);
    const dC = ct - cs, dR = rt - rs;
    const hdom = Math.abs(dC) >= Math.abs(dR);
    const srcSide = hdom ? (dC >= 0 ? "R" : "L") : (dR >= 0 ? "B" : "T");
    const tgtSide = hdom ? (dC >= 0 ? "L" : "R") : (dR >= 0 ? "T" : "B");
    return { ...o, S, T, cs, ct, rs, rt, dC, dR, hdom, srcSide, tgtSide, port: {} };
  });
  const groups = {};
  meta.forEach((m) => {
    (groups[m.S.id + "|" + m.srcSide] = groups[m.S.id + "|" + m.srcSide] || []).push({ m, end: "s", box: m.S, side: m.srcSide, other: m.T });
    (groups[m.T.id + "|" + m.tgtSide] = groups[m.T.id + "|" + m.tgtSide] || []).push({ m, end: "t", box: m.T, side: m.tgtSide, other: m.S });
  });
  Object.keys(groups).sort().forEach((k) => {
    const arr = groups[k], side = arr[0].side, box = arr[0].box;
    const vary = (side === "L" || side === "R") ? "cy" : "cx";
    arr.sort((a, b) => (a.other[vary] - b.other[vary]) || (a.m.idx - b.m.idx));
    const n = arr.length;
    arr.forEach((req, k2) => {
      const f = (k2 + 1) / (n + 1); let p;
      if (side === "R") p = { x: box.r, y: box.y + f * box.h };
      else if (side === "L") p = { x: box.x, y: box.y + f * box.h };
      else if (side === "B") p = { x: box.x + f * box.w, y: box.b };
      else p = { x: box.x + f * box.w, y: box.y };
      req.m.port[req.end] = p;
    });
  });
  meta.forEach((m) => {
    const s = m.port.s, t = m.port.t;
    if (m.hdom) {
      m.gutG = m.dC >= 0 ? m.ct - 1 : m.ct;
      const vx0 = grid.gutCenter(m.gutG);
      const wp0 = [s, { x: vx0, y: s.y }, { x: vx0, y: t.y }, t];
      if (Math.abs(m.dC) < 2 && !c4WpHitsAny(wp0, obstaclesFor(m), C4_PAD)) { m.case = "A"; m.gutters = [m.gutG]; m.bands = []; }
      else {
        m.case = "Ad"; m.srcGut = m.dC >= 0 ? m.cs : m.cs - 1;
        let band = m.dR >= 0 ? m.rs : m.rs - 1;
        for (let step = 0; step < grid.R + 1; step++) {
          const by0 = grid.bandCenter(band);
          if (!c4WpHitsAny([{ x: grid.gutCenter(m.srcGut), y: by0 }, { x: vx0, y: by0 }], obstaclesFor(m), C4_PAD)) break;
          band = m.dR >= 0 ? band + 1 : band - 1;
        }
        m.band = band; m.gutters = [m.srcGut, m.gutG]; m.bands = [band];
      }
    } else { m.case = "B"; m.band = m.dR >= 0 ? m.rt - 1 : m.rt; m.gutters = []; m.bands = [m.band]; }
  });
  const gutMembers = {}, bandMembers = {};
  meta.forEach((m) => {
    m.gutters.forEach((g) => { (gutMembers[g] = gutMembers[g] || []); if (gutMembers[g].indexOf(m.idx) < 0) gutMembers[g].push(m.idx); });
    m.bands.forEach((b) => { (bandMembers[b] = bandMembers[b] || []); if (bandMembers[b].indexOf(m.idx) < 0) bandMembers[b].push(m.idx); });
  });
  const vxFor = (g, idx) => { const mem = gutMembers[g] || [idx]; const CH = c4Clamp((grid.gutHi(g) - grid.gutLo(g)) / (mem.length + 1), 8, 18); return c4Clamp(grid.gutCenter(g) + (mem.indexOf(idx) - (mem.length - 1) / 2) * CH, grid.gutLo(g) + C4_PAD, grid.gutHi(g) - C4_PAD); };
  const byFor = (b, idx) => { const mem = bandMembers[b] || [idx]; const CH = c4Clamp((grid.bandHi(b) - grid.bandLo(b)) / (mem.length + 1), 8, 16); return c4Clamp(grid.bandCenter(b) + (mem.indexOf(idx) - (mem.length - 1) / 2) * CH, grid.bandLo(b) + C4_PAD, grid.bandHi(b) - C4_PAD); };
  meta.forEach((m) => {
    const s = m.port.s, t = m.port.t; let wp;
    if (m.case === "A") { const vx = vxFor(m.gutG, m.idx); wp = [s, { x: vx, y: s.y }, { x: vx, y: t.y }, t]; }
    else if (m.case === "Ad") { const vg = vxFor(m.gutG, m.idx), vs = vxFor(m.srcGut, m.idx), by = byFor(m.band, m.idx); wp = [s, { x: vs, y: s.y }, { x: vs, y: by }, { x: vg, y: by }, { x: vg, y: t.y }, t]; }
    else {
      const by = byFor(m.band, m.idx); wp = [s, { x: s.x, y: by }, { x: t.x, y: by }, t];
      if (c4WpHitsAny(wp, obstaclesFor(m), C4_PAD)) {
        const bBelow = grid.bandCenter(m.dR >= 0 ? m.rs : m.rs - 1), bAbove = grid.bandCenter(m.dR >= 0 ? m.rt - 1 : m.rt);
        const tryGut = (gIdx) => { const gx = vxFor(gIdx, m.idx); const w = [s, { x: s.x, y: bBelow }, { x: gx, y: bBelow }, { x: gx, y: bAbove }, { x: t.x, y: bAbove }, t]; return c4WpHitsAny(w, obstaclesFor(m), C4_PAD) ? null : w; };
        wp = tryGut(m.cs) || tryGut(m.cs - 1) || wp;
      }
    }
    if (c4WpHitsAny(wp, obstaclesFor(m), C4_PAD)) { wp = c4RouteWaypoints(m.S, m.T); m.fellBack = true; }
    m.wp = wp;
  });
  const placed = [];
  const estBox = (lx, ly, text) => ({ x: lx - text.length * 3.1, y: ly - 11, w: text.length * 6.2, h: 13 });
  const ov = (a, c) => a.x < c.x + c.w && a.x + a.w > c.x && a.y < c.y + c.h && a.y + a.h > c.y;
  meta.forEach((m) => {
    const text = c4ShortEdgeLabel(m.e.label);
    const cands = [];
    for (let i = 1; i < m.wp.length; i++) { const a = m.wp[i - 1], b = m.wp[i]; if (Math.abs(a.y - b.y) < 0.5 && Math.abs(b.x - a.x) >= 24) cands.push({ y: a.y, x0: Math.min(a.x, b.x), x1: Math.max(a.x, b.x), L: Math.abs(b.x - a.x) }); }
    cands.sort((a, b) => (b.L - a.L) || (a.y - b.y));
    let lx = null, ly = null; const obstacles = text ? rects : [];
    for (let ci = 0; ci < cands.length && lx == null; ci++) {
      const c = cands[ci], fracs = [0.5, 0.35, 0.65, 0.25, 0.75];
      for (let fi = 0; fi < fracs.length; fi++) { const cx = c.x0 + (c.x1 - c.x0) * fracs[fi], cy = c.y - 8; const lb = estBox(cx, cy, text || "x"); if (!obstacles.some((o) => ov(lb, o)) && !placed.some((p) => ov(lb, p))) { lx = cx; ly = cy; break; } }
    }
    if (lx == null) { lx = (Math.min(m.S.r, m.T.r) + Math.max(m.S.x, m.T.x)) / 2; ly = (m.port.s.y + m.port.t.y) / 2 - 8 + (m.idx % 3) * 14; }
    if (text) placed.push(estBox(lx, ly, text));
    m.lx = lx; m.ly = ly; m.labelText = text;
  });
  return meta.map((m) => ({ id: m.e.id, d: c4RoundedPath(m.wp, 7), port: m.wp[0], live: !!(liveSet && liveSet.has && liveSet.has(m.e.source) && liveSet.has(m.e.target)), label: m.labelText, title: m.e.label || "", lx: m.lx, ly: m.ly, horiz: true, _wp: m.wp, _case: m.case, _fellBack: !!m.fellBack }));
}

// ── HA backbone fixture (162x77; cols x{291,651,1011,1371}, rows y{777,927,1077}) ──
const R = (id, x, y) => ({ id, x, y, w: 162, h: 77 });
const haRects = [R("cli", 291, 777), R("ios", 291, 927), R("sup", 651, 777), R("core", 1011, 777), R("dock", 1011, 927), R("osa", 1011, 1077), R("fcm", 1371, 777)];
const haEdges = [
  { id: "e0", source: "cli", target: "sup", label: "CROSS_HTTP_CALLS — ha CLI invokes the Supervisor API" },
  { id: "e1", source: "sup", target: "core", label: "CROSS_HTTP_CALLS — Supervisor POSTs Core /auth/token" },
  { id: "e2", source: "sup", target: "dock", label: "CROSS_CHANNEL — Supervisor controls the host Docker daemon" },
  { id: "e3", source: "sup", target: "osa", label: "CROSS_CHANNEL — Supervisor calls os-agent host primitives" },
  { id: "e4", source: "ios", target: "core", label: "CROSS_HTTP_CALLS — iOS Companion WKWebView loads the Core" },
  { id: "e5", source: "core", target: "fcm", label: "CROSS_HTTP_CALLS — Core mobile_app integration pushes to FCM" },
];

// oracle helpers (mirror the headless oracle, computed from the emitted geometry)
const estBox = (lx, ly, text) => ({ x: lx - text.length * 3.1, y: ly - 11, w: text.length * 6.2, h: 13 });
const ovArea = (a, c) => Math.max(0, Math.min(a.x + a.w, c.x + c.w) - Math.max(a.x, c.x)) * Math.max(0, Math.min(a.y + a.h, c.y + c.h) - Math.max(a.y, c.y));
function oracles(rects, edges) {
  const out = c4SolveRoutes(rects.map((r) => ({ id: r.id, x: r.x, y: r.y, w: r.w, h: r.h })), edges, null);
  let crossings = 0;
  out.forEach((o, i) => { const e = edges[i]; for (const b of rects) { if (b.id === e.source || b.id === e.target) continue; for (let k = 1; k < o._wp.length; k++) if (c4SegHitsRect(o._wp[k - 1], o._wp[k], b, 3)) crossings++; } });
  const buckets = {};
  out.forEach((o, i) => { const e = edges[i], a = o._wp[0], z = o._wp[o._wp.length - 1]; const k1 = e.source + ":" + Math.round(a.x) + "," + Math.round(a.y), k2 = e.target + ":" + Math.round(z.x) + "," + Math.round(z.y); (buckets[k1] = buckets[k1] || 0, buckets[k1]++); (buckets[k2] = buckets[k2] || 0, buckets[k2]++); });
  const shared = Object.values(buckets).filter((v) => v > 1).length;
  const labs = out.map((o) => estBox(o.lx, o.ly, o.label || "x"));
  let labBox = 0; out.forEach((o, i) => { if (!o.label) return; for (const b of rects) if (ovArea(labs[i], b) > 1) labBox++; });
  let labLab = 0; for (let i = 0; i < labs.length; i++) for (let j = i + 1; j < labs.length; j++) if (out[i].label && out[j].label && ovArea(labs[i], labs[j]) > 1) labLab++;
  // edge-edge COLLINEAR overlap: two DIFFERENT edges' segments running along the
  // same line (same y for horizontals / same x for verticals) with overlapping
  // extent — i.e. lines drawn on top of each other (distinct from a single-point
  // crossing, which is normal). Must be 0.
  const segs = [];
  out.forEach((o, i) => { const wp = o._wp; for (let k = 1; k < wp.length; k++) { const a = wp[k - 1], b = wp[k]; const h = Math.abs(a.y - b.y) < 0.5, v = Math.abs(a.x - b.x) < 0.5; if (h || v) segs.push({ e: edges[i].id, h, x0: Math.min(a.x, b.x), x1: Math.max(a.x, b.x), y0: Math.min(a.y, b.y), y1: Math.max(a.y, b.y) }); } });
  let collinear = 0;
  for (let i = 0; i < segs.length; i++) for (let j = i + 1; j < segs.length; j++) {
    const A = segs[i], B = segs[j]; if (A.e === B.e || A.h !== B.h) continue;
    if (A.h && Math.abs(A.y0 - B.y0) < 2 && Math.min(A.x1, B.x1) - Math.max(A.x0, B.x0) > 4) collinear++;
    if (!A.h && Math.abs(A.x0 - B.x0) < 2 && Math.min(A.y1, B.y1) - Math.max(A.y0, B.y0) > 4) collinear++;
  }
  return { out, crossings, shared, labBox, labLab, collinear };
}

// ── 1. grid ──
const g = c4Grid(haRects);
assert.equal(g.C, 4, "HA = 4 columns"); assert.equal(g.R, 3, "HA = 3 rows");
assert.equal(c4Cluster1D([291, 294, 651], 81).length, 2, "3px jitter stays one column; 198px apart splits");

// ── 2. the four-defect oracle on the HA backbone MUST all be 0 ──
const O = oracles(haRects, haEdges);
assert.equal(O.crossings, 0, "edge-crosses-box == 0");
assert.equal(O.shared, 0, "shared-ports == 0");
assert.equal(O.labBox, 0, "label-over-box == 0");
assert.equal(O.labLab, 0, "label-label == 0");
assert.equal(O.collinear, 0, "edge-edge collinear overlap == 0 (lines never drawn on top of each other)");
assert.equal(O.out.find((o) => o.id === "e4")._case, "Ad", "iOS->Core (2-col span) routes via a sub-laned band, not the port-row");
assert.ok(O.out.every((o) => !o._fellBack), "no edge falls back to legacy on HA");
assert.equal(O.out.find((o) => o.id === "e3")._case, "B", "Supervisor->os-agent is V-dominant (CASE B)");

// ── 3. distinct co-terminal ports ──
const supR = O.out.filter((o) => ["e1", "e2"].includes(o.id)).map((o) => Math.round(o._wp[0].y));
const coreL = O.out.filter((o) => ["e1", "e4"].includes(o.id)).map((o) => { const z = o._wp[o._wp.length - 1]; return Math.round(z.y); });
assert.notEqual(supR[0], supR[1], "Supervisor right-side ports are distinct");
assert.notEqual(coreL[0], coreL[1], "Core left-side ports are distinct");

// ── 4. determinism ──
const a = JSON.stringify(oracles(haRects, haEdges).out.map((o) => [o.d, o.lx, o.ly]));
const b = JSON.stringify(oracles(haRects, haEdges).out.map((o) => [o.d, o.lx, o.ly]));
assert.equal(a, b, "c4SolveRoutes is deterministic on identical input");

// ── 5. generality: fixture-unexercised paths the prior C4 reviews warned about ──
{ // same-row crosser must detour (Ad), not cross, not fall back
  const O2 = oracles([R("a", 0, 0), R("b", 360, 0), R("c", 720, 0)], [{ id: "ac", source: "a", target: "c", label: "x crosses" }]);
  assert.equal(O2.crossings, 0, "same-row crosser does not cross intervening box");
  assert.equal(O2.out[0]._case, "Ad", "same-row crosser uses the A-detour");
  assert.ok(!O2.out[0]._fellBack, "same-row crosser does not fall back to legacy");
}
{ // V-dominant with an intervening same-column box must detour through a gutter
  const O3 = oracles([R("p", 0, 0), R("q", 0, 150), R("z", 0, 300)], [{ id: "pz", source: "p", target: "z", label: "vdom" }]);
  assert.equal(O3.out[0]._case, "B", "same-column 2-rows-apart is CASE B");
  assert.equal(O3.crossings, 0, "CASE B detours around the intervening same-column box");
}
{ // single edge -> exact side center (legacy-preserving)
  const O4 = oracles([R("a", 0, 0), R("b", 360, 0)], [{ id: "ab", source: "a", target: "b", label: "one" }]);
  assert.ok(Math.abs(O4.out[0]._wp[0].y - 38.5) < 0.01, "single-edge port at exact side center");
}

console.log("c4_solve_routes.test.mjs: all assertions passed (4-defect oracle = 0 on HA + generality)");
