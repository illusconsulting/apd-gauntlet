# Handoff: C4 Architecture view — tiered layout + orthogonal connectors + in-node badges

## Overview

This package redesigns the **Architecture (07 Architecture)** screen of the APD Gauntlet
HTML report. The current screen renders the grounded C4 model with a **Cytoscape
`fcose` force-directed graph**. Because most runs have very few grounded edges
(the Home Assistant example: **82 nodes, 6 edges**), the force layout scatters
the disconnected nodes into a loose grid and the relationships are hard to read.

The redesign replaces that with a **tiered C4 scene** (one horizontal band per
C4 abstraction — System context → Container → Component → Code) connected by
**orthogonal, right-angle connectors with rounded elbows** in the report accent
(the same visual language as a clean "system map"). It also moves the **finding
(⚑) and capability (🛡) counts into the node boxes themselves** instead of only
listing them beneath the diagram, and wires a **data-driven L3 Component tier**
that renders Container → Component → Code whenever a run grounds components and
shows an honest "blocked / none" state otherwise.

This is a change to **one screen of an existing React app**, not a greenfield
build. Everything it needs already exists in the report's data model.

---

## About the design files

The files in `prototype/` are a **design reference created in HTML/CSS/vanilla JS**
— a faithful, interactive prototype of the intended look and behavior. They are
**not** meant to be dropped into the codebase verbatim. The task is to **recreate
this design inside the report's existing React environment**, reusing its
component conventions, CSS tokens, and data plumbing.

- `prototype/APD Gauntlet Architecture (C4).html` — the full working prototype
  (open it in a browser; toggle theme by setting `data-theme="dark"` on `<body>`).
- `prototype/archx-data.js` — the **real** `c4_model` slice exported from the
  Home Assistant run (`window.C4_DATA`), so you can develop against authentic data.
- `prototype/styles.css` — the report's actual design-token stylesheet (copied so
  the prototype renders standalone). **Do not** re-add this to the codebase — it
  is already `report-template/styles.css`.

## Fidelity

**High-fidelity.** Final colors, typography, spacing, radii, interactions, and
the connector-routing algorithm are all settled. Recreate the UI faithfully using
the report's existing tokens and React patterns. The one thing intentionally left
for the implementer is the **deterministic node-placement algorithm** (the
prototype uses a hand-curated position map for the Home Assistant run; production
must derive positions from the data — see "Layout strategy" below).

---

## Where this lives in the codebase

The report is a small React app transpiled/bundled into the run's
`40-synthesis/report-html/app.js`. The **source** is the report template:

| File | Role | Change |
|---|---|---|
| `report-template/screens/C4.jsx` | The C4 scene component (drill state, subgraph build, overlay, drill-list). | **Rewrite the render** to emit the tiered scene + new renderer instead of `<GraphView layout="fcose" compound>`. Keep the drill-state machine, overlay logic, and honest banner — they map over almost 1:1. |
| `report-template/components.jsx` | Holds `GraphView` + `_graphStylesheet` (the shared **Cytoscape** renderer used by AttackPaths, ThreatModel, **and** C4). | **Do not** repurpose `GraphView`. Add a **new** dedicated `C4Scene`/`C4TierGraph` renderer (no Cytoscape) here or in a new `screens/c4/` module. Leave `GraphView` untouched so AttackPaths/ThreatModel keep working. |
| `report-template/screens.css` | All `.c4-*`, `.chip`, `.report-graph__*` styles. | **Add** the new `.archx-*` / tier / node-box / edge-layer rules (see "Design tokens" + the prototype `<style>` block). The existing `.c4-banner`, `.c4-crumbs`, `.c4-badge--*`, `.chip` rules are reused. |
| `report-template/.build/entry.jsx` + the bundler | Wires `window.React`/`ReactDOM`/`window.cytoscape` and bundles to `app.js`. | No structural change. Cytoscape stays (other scenes use it). The C4 renderer is **plain React + SVG + DOM measurement** — no new deps. |
| `tools/apd_gauntlet/report/transform.py` → `c4_model_view()` | Produces `window.APD_DATA.c4_model`. | **No change.** The new renderer consumes the existing shape verbatim (see "Data model"). |
| `schemas/c4-model.schema.json`, `tools/apd_gauntlet/assemble_c4.py` | C4 assembly + schema (incl. `level: component`). | **No change.** L3 is already modeled and hard-blocked-by-default; the new tier just renders it when present. |

> There are two template copies in the repo: `report-template/` (the editable
> source) and `tools/apd_gauntlet/data/report-template/` (the packaged copy that
> ships built `app.js`). Edit **`report-template/`** and rebuild; the packaged
> copy is a build output.

---

## Data model (already produced — consume as-is)

`window.APD_DATA.c4_model` (see `transform.py::c4_model_view`):

```jsonc
{
  "present": true,
  "levels_present": ["system","person","external_system","container","code"], // canonical L1→L4 order
  "not_analyzed_count": 15,
  "unlocalized_findings": 10,
  "nodes": [
    {
      "id": "c4-2b33e14f",
      "label": "Home Assistant Core",
      "type": "container",            // == C4 level: system|person|external_system|container|component|code
      "kind": "service",              // service|app|data_store|compute|library|external_system (containers); function|class|route|module (code); component (L3); software_system|human_role|external_party|external_dependency (L1)
      "parent": null,                 // containment: code.parent = component|container; component.parent = container
      "badge": 22,                    // finding_count, or null when 0 (NEVER render "0 = clean")
      "capability_badge": 15,         // confirmed-capability count
      "analysis_state": "analyzed",   // "analyzed" | "not_analyzed"
      "provenance": { "first_finding_id": "…", "source": "…", "locator": "…", "repo": "…" }
    }
  ],
  "edges": [
    { "id": "c4e-…", "source": "c4-…", "target": "c4-…", "label": "CROSS_HTTP_CALLS …", "machine_extracted": false }
  ],
  "asset_to_c4": { "<asset-node-id>": "<c4-node-id>" },   // attack-path overlay join (grounded-only; often sparse/empty)
  "finding_to_c4": { "<finding-id>": "<c4-code-node-id>" }
}
```

Key facts that drive the design:

- **Few edges.** Edges are container↔container "uses" relations only. There are
  *no* person→container or system→container edges (containment is `parent`, not an
  edge). **Never invent edges** — draw only what's in `edges[]`.
- **`badge: null` means "analyzed, zero findings"** for analyzed nodes — render a
  muted `⚑ 0`, never hide it as clean. **`analysis_state: "not_analyzed"`** means
  "no code anchors" — render the striped/dashed muted treatment + a `not analyzed`
  marker, distinct from a clean zero.
- **L3 components are usually absent** (`assemble_c4.py` hard-blocks L3 unless
  `c4-recon.components[]` groups symbols). Code then parents directly to its
  container → render L2→L4. When components *do* exist, code parents to a
  component which parents to the container → render L2→L3→L4.

---

## Screens / Views

There is **one screen** with three drill states. It is laid out as stacked,
left-gutter-labeled **tiers** inside a pannable/zoomable stage.

### Tier L1 — System context

- **Purpose:** show the system, its actors, and external dependencies.
- **Layout:** 3-column flex inside the tier body — `Actors` (all `person` nodes, a
  2-col mini-box grid) · the single `system` node (centered, accent-filled,
  emphasized) · `External systems` (all `external_system` nodes, dashed mini boxes,
  1-col). No connectors (no grounded edges at this level).
- **Node detail:** name + (system only) "software system" subtitle. Persons/externals
  carry no badges. `external_party`/`external_dependency` render dashed.

### Tier L2 — Containers (the main band)

- **Purpose:** show containers and their grounded relationships; this is where the
  connectors live.
- **Layout:** three sub-sections, each with a small mono caption:
  1. **Traced relationships** — a positioned canvas holding the containers that
     participate in `edges[]` (the connected backbone), arranged left→right so the
     hub reads clearly, with **orthogonal rounded connectors + short edge labels**.
  2. **Analyzed · no traced relation** — a wrap shelf of full node boxes for
     `analysis_state==="analyzed"` containers not in any edge (they still show their
     ⚑/🛡 badges; `data_store` kinds get the barrel-ish bottom radius).
  3. **Infrastructure · not analyzed** — a wrap shelf of striped/dashed muted chips
     for `analysis_state==="not_analyzed"` containers.
- **Interaction:** clicking a container that has children drills it (selects it,
  reveals L3/L4). Selected container gets an accent ring.

### Tier L3 — Components (data-driven; honest when empty)

- **Purpose:** show a container's grounded components, when present.
- **Layout / states:**
  - No container selected → hint: *"L3 components appear here when a run grounds
    them via `c4-recon.components[]` … blocked by default, so most runs drill L2 → L4."*
  - Container selected **with** components → the container box (echoed) + a grid of
    `component` boxes (clickable, each with its own ⚑/🛡 badges).
  - Container selected **without** components → honest note: *"No grounded L3
    components under {container} … renders L2 → L4."*
- **Interaction:** clicking a component selects it and populates L4 with its code.

### Tier L4 — Code

- **Purpose:** show the grounded code elements for the active parent.
- **Layout:** the active parent box (the selected component, or the selected
  container when it has no components) + a responsive grid of `code` boxes. Each
  code box: `kind` chip (function/class/route/module) + mono name + ⚑/🛡 badges.
- **States:** nothing selected → hint; container-with-components but no component
  selected → "select a component"; otherwise the code grid.

### Beneath the diagram — Code-elements list (kept)

A plain index list of the active parent's code elements (mirrors the original
"CODE ELEMENTS" list), now redundant-but-handy because the badges also live in the
boxes. Header reflects `{container} › {component}` when a component is active.

---

## The headline change: badges INSIDE nodes

Every node box renders a `.nb__badges` row. Rules (`badgeHTML` in the prototype):

- `analysis_state === "not_analyzed"` → a single dashed italic `not analyzed`
  pill. **No counts.**
- else:
  - `badge > 0` → `⚑ {badge}` in **sev-high** styling; **clickable** → calls
    `onOpenFinding(provenance.first_finding_id)` (deep-link into Findings), exactly
    like the current `c4-badge--finding`. When no `first_finding_id`, render the
    count as static (not a link) — never hide it.
  - `badge == null` (analyzed, 0) and node is container/component/code → muted `⚑ 0`.
  - `capability_badge > 0` → `🛡 {capability_badge}` in **sev-low** styling.

This applies in the backbone, both shelves, the L3 component grid, and the L4 code
grid — i.e. **every tier**, not just the list.

---

## Connector router (orthogonal, rounded) — use verbatim

Connectors are drawn in an **SVG overlay** that covers the stage, sized to
`stage.scrollWidth/Height`, `pointer-events:none`, behind the node boxes
(`z-index` below `.nb`). Anchors are measured from the **layout box model**
(`offsetLeft/Top/Width/Height` walked up to the stage) so they are correct
regardless of the CSS `transform: scale()` zoom. Redraw on: render, `window`
load, `document.fonts.ready`, resize (debounced), and a theme `MutationObserver`.

```js
// 1. layout-space rect of an element relative to the (un-scaled) stage
function anchors(srcEl, tgtEl, stage) {
  const r = el => {
    let x = 0, y = 0, e = el;
    while (e && e !== stage) { x += e.offsetLeft; y += e.offsetTop; e = e.offsetParent; }
    return { x, y, w: el.offsetWidth, h: el.offsetHeight,
             cx: x + el.offsetWidth / 2, cy: y + el.offsetHeight / 2 };
  };
  return [r(srcEl), r(tgtEl)];
}

// 2. orthogonal waypoints: exit/enter on the side facing the target,
//    H-V-H when horizontally dominant, V-H-V otherwise
function routeWaypoints(s, t) {
  const dx = t.cx - s.cx, dy = t.cy - s.cy;
  if (Math.abs(dx) >= Math.abs(dy)) {
    const sx = dx >= 0 ? s.x + s.w : s.x;
    const tx = dx >= 0 ? t.x : t.x + t.w;
    const midX = (sx + tx) / 2;
    return [{x:sx,y:s.cy},{x:midX,y:s.cy},{x:midX,y:t.cy},{x:tx,y:t.cy}];
  } else {
    const sy = dy >= 0 ? s.y + s.h : s.y;
    const ty = dy >= 0 ? t.y : t.y + t.h;
    const midY = (sy + ty) / 2;
    return [{x:s.cx,y:sy},{x:s.cx,y:midY},{x:t.cx,y:midY},{x:t.cx,y:ty}];
  }
}

// 3. polyline with rounded corners (radius ~7px == report --radius, slightly larger).
//    Dedupes collinear/zero-length points so straight runs stay straight.
function roundedPath(pts, rad) {
  const p = [];
  pts.forEach(q => { const l = p[p.length-1]; if (!l || Math.abs(l.x-q.x)>0.5 || Math.abs(l.y-q.y)>0.5) p.push(q); });
  if (p.length < 2) return "";
  let d = `M ${p[0].x} ${p[0].y}`;
  for (let i = 1; i < p.length - 1; i++) {
    const a = p[i-1], b = p[i], c = p[i+1];
    const l1 = Math.hypot(b.x-a.x, b.y-a.y), l2 = Math.hypot(c.x-b.x, c.y-b.y);
    const r = Math.min(rad, l1/2, l2/2);
    const u1 = { x:(a.x-b.x)/(l1||1), y:(a.y-b.y)/(l1||1) };
    const u2 = { x:(c.x-b.x)/(l2||1), y:(c.y-b.y)/(l2||1) };
    d += ` L ${(b.x+u1.x*r).toFixed(1)} ${(b.y+u1.y*r).toFixed(1)}`
       + ` Q ${b.x} ${b.y} ${(b.x+u2.x*r).toFixed(1)} ${(b.y+u2.y*r).toFixed(1)}`;
  }
  const last = p[p.length-1];
  return d + ` L ${last.x} ${last.y}`;
}
```

Each edge gets: the `roundedPath` (`marker-end` arrow), a small start **port**
circle, and a label placed at the **midpoint of the last segment >18px long** (so
fan-out spokes from a hub separate by row instead of colliding). Label has a
`paper`-filled `rect` background sized from `getBBox()`. See `drawEdges()` in the
prototype for the exact implementation, including the attack-path "live"
(accent + thicker) styling.

**Edge labels:** the raw `edge.label` is a long machine string
(`"CROSS_HTTP_CALLS Supervisor POSTs Core /auth/token …"`). The prototype shows a
**curated short label**. For production, derive a short label deterministically
(e.g. strip the `CROSS_*` prefix and take the first ~3 words, or map relation
type → verb) and show the full string in the hover tooltip. Don't hand-curate per run.

### Field-name crosswalk (fixture vs production)

The prototype's `archx-data.js` fixture (`window.C4_DATA`) is now a faithful copy
of the **production** `window.APD_DATA.c4_model` slice that
`tools/apd_gauntlet/report/transform.py::c4_model_view` emits. The React scene MUST
read the production names — there are no abbreviations. Earlier drafts of this
fixture used short keys; the table below is the historical crosswalk so reviewers
of the prototype `.html` are not confused:

| Production key (use this)        | Old fixture abbrev (do NOT use) | Notes |
|----------------------------------|----------------------------------|-------|
| `node.type` (= C4 level)         | —                                | `system\|person\|external_system\|container\|component\|code` |
| `node.kind`                      | —                                | service/data_store/compute/app/external_system; function/class/route/module |
| `node.badge`                     | —                                | `finding_count` when > 0, else `null` (never `0`; "0 ≠ clean") |
| `node.capability_badge`          | `node.cap`                       | integer, `0` when none |
| `node.analysis_state`            | `node.state`                     | `analyzed` \| `not_analyzed` |
| `node.provenance.first_finding_id` | `node.ff`                      | per-node ⚑ deep-link key (present only when `badge` > 0) |
| `node.provenance{source,locator,repo}` | —                          | passed through verbatim from the assembler |
| `edge.machine_extracted`         | `edge.me`                        | boolean |
| `edge.label`                     | —                                | FULL machine string (e.g. `CROSS_HTTP_CALLS …`); short label derived at render |
| top: `present`, `levels_present`, `not_analyzed_count`, `unlocalized_findings`, `asset_to_c4`, `finding_to_c4` | (omitted) | rollups + overlay crosswalks; `asset_to_c4`/`finding_to_c4` are grounded-only and may be `{}` |
| (removed) | `overlay_paths` | **fabricated** in the old fixture — attack-path overlays are rebuilt from `data.attack_paths` + `asset_to_c4`/`finding_to_c4`, never shipped on the c4 slice |

The backbone positions and short edge labels the prototype hard-codes
(`BACKBONE` / `EDGE_SHORT` / `ANALYZED_SHELF` constants) are **render-derived in
production** by `c4BackboneLayout` / `c4ShortEdgeLabel` (see Layout strategy + Edge
labels above) — they are deliberately NOT fixture fields.

---

## Layout strategy (the part to make data-driven)

The prototype hard-codes backbone positions for the Home Assistant run
(`BACKBONE` map) and a curated shelf order. **Production must derive these from the
data.** Recommended deterministic algorithm:

1. **Partition containers** into:
   - `connected` = containers appearing in any `edges[]` endpoint,
   - `analyzed` = remaining `analysis_state==="analyzed"` containers,
   - `infra` = `analysis_state==="not_analyzed"` containers.
2. **Backbone columns** for `connected`: compute a layered left→right order over
   the edge subgraph — column 0 = nodes with no incoming edge; each subsequent
   column = targets of the previous column (BFS longest-path layering; break cycles
   by first-seen). Stable-sort nodes within a column by label (or by descending
   `badge` to foreground hot nodes). Assign `x = col * COL_W`, `y = row * ROW_H`.
   Box width ~162px, `COL_W ~360`, `ROW_H ~150`.
3. **Shelves**: `analyzed` then `infra` as wrap rows under the backbone, sorted by
   label (or badge-desc). `infra` uses the muted striped chip variant.
4. Draw connectors by **measuring the rendered boxes** (the router above) — so the
   exact positioning method (absolute vs. computed) doesn't matter to routing.
5. **L1**: persons sorted → left grid; system → center; externals sorted → right.
6. **L3/L4**: simple responsive grids (no positioning needed); the parent box sits
   above the grid. (Optional enhancement: draw a single rounded connector from the
   parent box down into the grid header to echo containment — the prototype omits
   per-child connectors for code to avoid 18-way crossing noise.)

Keep it fully deterministic (no randomness, stable sorts) so report output is
reproducible across runs — this matches the framework's determinism contract.

---

## Interactions & behavior

- **Drill** (`drill(id)` in prototype; mirrors C4.jsx's `selectedContainer` /
  `selectedComponent` machine):
  - container → toggle `selectedContainer`, clear `selectedComponent`.
  - component → set `selectedContainer = parent`, toggle `selectedComponent`.
  - clicking a `⚑` badge must **not** trigger drill (stop propagation).
- **Breadcrumb**: `⌂ System / Container: X [/ Component: Y]` with an "↑ up to {X}"
  control when a component is selected. `⌂ System` resets.
- **Zoom/fit toolbar**: `−` / `100%` / `+` / `fit`. Zoom applies
  `transform: scale()` to the stage inner; `fit` solves scale to wrapper width.
  Reuse the look of `.report-graph__toolbar`.
- **Attack-path overlay**: reuse C4.jsx's existing logic. Selecting a path
  resolves grounded C4 node ids via `asset_to_c4` + `finding_to_c4` (already
  computed). Highlight = set membership → dim non-members (`opacity`), and draw the
  induced edges as "live" (accent, thicker). Keep the existing "parallel asset
  hops — no C4 mapping" strip for unmapped hops. **Honest partial highlight only.**
- **Hover tooltip**: text-only (never inject HTML from adopter data) — label, level,
  kind, counts, and a "↳ click to drill (N …)" hint. Mirrors the current
  canvas-tooltip contract.
- **Deep-link**: `⚑` badge → `onOpenFinding(provenance.first_finding_id)` (the C4
  scene already receives `onOpenFinding` from the report shell).
- **Theme reactivity**: all colors are CSS vars; re-measure/redraw edges on
  `data-theme` / `data-sev` changes (the report already toggles these on `<body>`).

### Removable demo affordance

The prototype includes a **"▸ L3 demo (synthetic)"** toggle that synthesizes a
component grouping for one container so reviewers can preview the L3 drill (since
no current run grounds components). **Do not ship this.** It exists only to
demonstrate the L3-ready code path. Production renders L3 purely from
`type==="component"` nodes.

---

## State management

Two pieces of view state (same as today's C4.jsx, plus the existing overlay state):

- `selectedContainer: string | null`
- `selectedComponent: string | null`
- `selectedOverlayPath: string | null` (already present)

Derived (memoize): `byId`, `childrenOf`, `compsOf(id)`, `codeOf(id)`,
`activeCodeParent()` = selected component, else the code-bearing selected
container. No data fetching — `c4_model` is embedded in `data.js`.

---

## Design tokens (all from `report-template/styles.css` — do not invent)

| Token | Light value | Use |
|---|---|---|
| `--bg` | `#faf8f4` | page |
| `--paper` | `#fffdf8` | node fill |
| `--paper-2` | `#f5f1e8` | inset / chips / striped not-analyzed |
| `--rule` | `#e3dccc` | hairline borders |
| `--rule-strong` | `#c9bfa8` | node border, idle connector stroke |
| `--ink` / `--ink-2` / `--ink-3` | `#1a1814` / `#4a463d` / `#7a7363` | text primary/secondary/meta |
| `--accent` | `#5b3a1f` | system fill, selected ring, **live connectors**, edge labels |
| `--sev-high` | `#a33a1a` | ⚑ finding badge |
| `--sev-low` | `#4a6c4a` | 🛡 capability badge |
| `--radius-sm/md/lg` | `3 / 5 / 8px` | chips / boxes / stage; connector elbow ≈ **7px** |
| `--space-*` | `2,4,8,12,16,24,32,48,64` | spacing scale |
| Fonts | `Newsreader` (display) · `IBM Plex Sans` (body) · `IBM Plex Mono` (mono/labels/badges) | already loaded |

Dark + `paper` themes are defined in `styles.css` via `[data-theme]` and just
work because everything is token-driven. Connector/badge colors are read from the
CSS vars at draw time (mirror `_graphStylesheet`'s `getComputedStyle` approach so
theme switches recolor live).

The complete, final CSS for the new tiers / node boxes / edge layer is in the
`<style>` block of `prototype/APD Gauntlet Architecture (C4).html` (search
`.archx`, `.tier`, `.nb`, `.edge-layer`). Lift it into `screens.css`, scoped under
the C4 scene root.

---

## Assets

None. No images or icons beyond inline text glyphs (`⚑ 🛡 ⌂ ↑ →`) and the dotted
background (a CSS `radial-gradient`). Fonts are already loaded by the report shell.

## Files in this package

- `prototype/APD Gauntlet Architecture (C4).html` — full prototype (markup + final CSS + renderer JS).
- `prototype/archx-data.js` — real Home Assistant `c4_model` slice (`window.C4_DATA`) for dev.
- `prototype/styles.css` — the report's token stylesheet (reference only; already in repo).

## Codebase files to touch

- `report-template/screens/C4.jsx` — rewrite render to the tiered scene; keep drill/overlay/banner logic.
- `report-template/components.jsx` — add a new non-Cytoscape C4 renderer; leave `GraphView` for AttackPaths/ThreatModel.
- `report-template/screens.css` — add `.archx-*`/tier/node-box/edge-layer rules; reuse existing `.c4-*`/`.chip`.
- (rebuild to regenerate `…/report-html/app.js`; packaged `tools/apd_gauntlet/data/report-template/` is a build output.)
- No changes to `transform.py`, `assemble_c4.py`, or the schemas.

---

## Acceptance checklist

- [ ] C4 screen renders as stacked tiers L1 → L2 → (L3) → L4 with left-gutter labels.
- [ ] Connectors are orthogonal (H/V only) with ~7px rounded elbows, accent-colored, arrowheads + start ports; only the grounded `edges[]` are drawn (no invented edges).
- [ ] Edge labels are short, de-collided, with the full relation string on hover.
- [ ] Every node box shows in-box ⚑ findings and 🛡 capabilities; `not_analyzed` is striped/dashed with a `not analyzed` marker; analyzed-zero shows muted `⚑ 0` (never hidden as clean).
- [ ] Clicking a container drills (L3 if components exist, else L4); clicking a component drills to its code; `⚑` deep-links to Findings; breadcrumb + up-one-level work.
- [ ] L3 tier renders components when present and an honest "blocked / none" state otherwise (Home Assistant run shows L2→L4).
- [ ] Zoom/fit toolbar, attack-path overlay (with the unmapped-hops strip), and hover tooltips work; light/dark/paper themes recolor live.
- [ ] Node placement is deterministic from the data (no curated per-run position map; no randomness).
- [ ] AttackPaths/ThreatModel screens (still Cytoscape `GraphView`) are unaffected.
- [ ] The "L3 demo (synthetic)" affordance is NOT shipped.
