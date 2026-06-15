// report-template/.build/test/c4_router.test.mjs
// Pure unit tests for the C4 orthogonal connector router + short-label derivation.
// Run: node report-template/.build/test/c4_router.test.mjs  (no deps, no DOM).
// The router functions (c4RouteWaypoints / c4RoundedPath) are ported VERBATIM from
// docs/superpowers/design_handoff_c4_architecture_view (README §204-249 / the
// prototype) and live in components.jsx; they are re-declared here so the math is
// testable under plain node. c4ShortEdgeLabel is re-declared from the SHIPPED
// components.jsx (it landed earlier in this milestone, Task 4) so the node test
// pins the contract that actually ships — see the note above its assertions.
import assert from "node:assert/strict";

// ── ported verbatim from components.jsx ──────────────────────────────────
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
// re-declared VERBATIM from the SHIPPED components.jsx (Task 4). The shipped
// helper strips the CROSS_<TYPE> machine prefix and keeps the first ~3 words; a
// bare CROSS_* relation with no trailing prose collapses to "" (it does NOT carry
// the prototype's hand-curated verb map — that map was intentionally dropped when
// the deterministic helper landed). The FULL rawLabel is kept by the caller for
// the hover tooltip.
function c4ShortEdgeLabel(rawLabel) {
  let s = rawLabel == null ? "" : String(rawLabel);
  s = s.replace(/^\s*CROSS_[A-Z_]+\s*[—:-]*\s*/, "");
  s = s.trim();
  if (!s) return "";
  const words = s.split(/\s+/).filter(Boolean);
  return words.slice(0, 3).join(" ");
}
// ── /ported ──────────────────────────────────────────────────────────────

// horizontal-dominant pair: H-V-H, exits the right edge of s, enters the left edge of t
{
  const s = { x: 0, y: 0, w: 100, h: 40, cx: 50, cy: 20 };
  const t = { x: 400, y: 0, w: 100, h: 40, cx: 450, cy: 20 };
  const wp = c4RouteWaypoints(s, t);
  assert.equal(wp.length, 4);
  assert.deepEqual(wp[0], { x: 100, y: 20 });   // exits right edge of s at s.cy
  assert.deepEqual(wp[3], { x: 400, y: 20 });   // enters left edge of t at t.cy
  assert.equal(wp[1].x, wp[2].x);               // the vertical mid-run shares x (orthogonal)
}
// vertical-dominant pair: V-H-V, exits the bottom edge of s, enters the top edge of t
{
  const s = { x: 0, y: 0, w: 100, h: 40, cx: 50, cy: 20 };
  const t = { x: 0, y: 300, w: 100, h: 40, cx: 50, cy: 320 };
  const wp = c4RouteWaypoints(s, t);
  assert.deepEqual(wp[0], { x: 50, y: 40 });    // exits bottom edge of s at s.cx
  assert.deepEqual(wp[3], { x: 50, y: 300 });   // enters top edge of t at t.cx
  assert.equal(wp[1].y, wp[2].y);               // the horizontal mid-run shares y
}
// target to the LEFT: exit left edge of s, enter right edge of t
{
  const s = { x: 400, y: 0, w: 100, h: 40, cx: 450, cy: 20 };
  const t = { x: 0, y: 0, w: 100, h: 40, cx: 50, cy: 20 };
  const wp = c4RouteWaypoints(s, t);
  assert.deepEqual(wp[0], { x: 400, y: 20 });   // exits LEFT edge of s
  assert.deepEqual(wp[3], { x: 100, y: 20 });   // enters RIGHT edge of t
}
// roundedPath: only H/V segments + quadratic elbows; starts with M, no diagonal L between elbows
{
  const d = c4RoundedPath([{ x: 0, y: 0 }, { x: 50, y: 0 }, { x: 50, y: 50 }, { x: 100, y: 50 }], 7);
  assert.ok(d.startsWith("M 0 0"));
  assert.ok(d.includes("Q "), "elbow must use a quadratic curve");
  assert.ok(d.endsWith("L 100 50"));
}
// roundedPath: collinear / zero-length points are deduped so straight runs stay straight
{
  const d = c4RoundedPath([{ x: 0, y: 0 }, { x: 0, y: 0 }, { x: 100, y: 0 }], 7);
  assert.equal(d, "M 0 0 L 100 0", "consecutive duplicate points must collapse");
}
// roundedPath: fewer than 2 distinct points -> empty string (no edge)
{
  assert.equal(c4RoundedPath([{ x: 5, y: 5 }], 7), "");
  assert.equal(c4RoundedPath([{ x: 5, y: 5 }, { x: 5, y: 5 }], 7), "");
}
// roundedPath is DETERMINISTIC (byte-stable) for the same input
{
  const pts = [{ x: 1, y: 2 }, { x: 30, y: 2 }, { x: 30, y: 80 }, { x: 60, y: 80 }];
  assert.equal(c4RoundedPath(pts, 7), c4RoundedPath(pts, 7));
}
// short-edge-label: strips the CROSS_* prefix and keeps ~3 words
{
  assert.equal(c4ShortEdgeLabel("CROSS_HTTP_CALLS Supervisor POSTs Core /auth/token now"), "Supervisor POSTs Core");
  assert.equal(c4ShortEdgeLabel("controls host daemon via socket"), "controls host daemon");
}
// short-edge-label: a bare CROSS_* relation with no trailing words collapses to ""
// (the SHIPPED deterministic helper drops the prototype's hand-curated verb map).
{
  assert.equal(c4ShortEdgeLabel("CROSS_DBUS_CALLS"), "");
  assert.equal(c4ShortEdgeLabel("CROSS_HTTP_CALLS"), "");
}
// short-edge-label: empty / null input -> empty string
{
  assert.equal(c4ShortEdgeLabel(""), "");
  assert.equal(c4ShortEdgeLabel(null), "");
}
// short-edge-label is deterministic
{
  assert.equal(c4ShortEdgeLabel("CROSS_CHANNEL a b c d"), c4ShortEdgeLabel("CROSS_CHANNEL a b c d"));
}

console.log("c4_router.test.mjs: all assertions passed");
