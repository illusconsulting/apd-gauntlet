# Cytoscape graph renderer (replace Mermaid) — design

## Context

The HTML report renders two node/edge graphs — the Attack-paths asset graph and the
Threat-model trust-boundary surface map — via Mermaid. PR #78 unified them behind a shared
`MermaidGraph` component (`report-template/components.jsx`) that calls `window.mermaid.render`
on a Python-generated Mermaid **string** (`data.attack_paths.mermaid` /
`mermaid_path_focused`, `data.threat_model.surface_mermaid`). Mermaid is `import`ed in
`report-template/.build/react-globals.js` and esbuild-bundled into `app.js` (≈3MB of the
~3.68MB bundle); `build.mjs` also copies a now-vestigial `mermaid.min.js`.

Mermaid renders static SVG with no real interactivity. We are replacing it with
**Cytoscape.js + cytoscape-dagre (+ cytoscape-fcose)** — a purpose-built graph renderer with
pan/zoom/drag, declarative type-keyed styling, hierarchical layout, and click-to-highlight —
fed by **structured `{nodes, edges}`** instead of a Mermaid string. Mermaid is removed
entirely. Both report graphs migrate.

The report is self-contained and offline (`file://`-openable, no network); libraries are
esbuild-bundled into `app.js`. Graph labels are adopter-controlled (potentially adversarial)
and are sanitized in Python today via `_safe_label`; that posture is preserved (Cytoscape
draws labels as canvas text — never HTML).

## Goals

- One shared **`GraphView`** React component (replacing `MermaidGraph`) backed by Cytoscape,
  used by both `AttackPaths.jsx` and `ThreatModel.jsx`.
- Structured graph data in the data block: `data.attack_paths.graph` + `graph_path_focused`,
  `data.threat_model.surface_graph` — replacing the Mermaid string fields.
- Interactivity: pan, wheel-zoom, node drag, fit-to-view, hover tooltip, and
  **click-to-highlight-paths** (in scope).
- Layout: attack graph = **dagre** (top-down attacker → crown-jewel); TM surface map =
  **fcose** with **compound parent nodes** per trust boundary.
- Theming consistent with the report (`--ink`/`--paper`/`--sev-*`/`--accent` tokens; light /
  paper / dark; severity palette), re-applied on theme change.
- **Mermaid fully removed** — import, vendored file, Python `_build_mermaid*` helpers, the
  Mermaid string fields, and the #78 contract tests that pinned them.
- Net bundle size **drops** (Cytoscape+dagre+fcose ≪ Mermaid's ~3MB).

## Non-goals

- No change to how the asset graph / threat model are computed upstream (`asset-graph.yaml`,
  `threat-model-normalized.yaml`, the analyzer/author/evaluator agents) — those YAMLs are
  inputs here, unchanged.
- No new graph analytics (centrality, etc.) — rendering + interaction only.
- No server/runtime dependency on Node for consumers (build-time only, as today).

## Inputs (already produced)

- `40-synthesis/asset-graph.yaml` — `nodes[]` (`node_id`, `node_type` ∈
  attacker/asset/identity/crown_jewel, `name`, `provenance{source,artifact,locator}`,
  `confidence`, `asset_type`) and `edges[]` (`edge_id`, `edge_type` ∈
  network_reachable/trust/finding/capability/data_resides_on/…, `from`, `to`,
  `provenance`, `confidence`, `traversal_cost`). Loaded as `artifacts.asset_graph`.
- `data.attack_paths.pairs[].paths[]` — each path has `path_id`, `edges` (edge-id list),
  `bottleneck_edges`, `hop_count`, etc. (used for path highlighting).
- Threat-model entries + `asset-inventory` trust boundaries (block-D inputs from #78).

## Data shape (transform.py)

Two new builders replace the three `_build_*mermaid` functions. Both sanitize every
adopter-controlled label via the existing `_safe_label`.

```
node = {
  id: str, type: "attacker"|"asset"|"identity"|"crown_jewel"|"boundary",
  label: str,                 # sanitized name / boundary name
  parent?: str,               # boundary node id (TM compound clusters only)
  badge?: str,                # STRIDE letters, TM surface map only
  hot?: bool,                 # TM: asset has an unmitigated threat
  provenance?: {artifact, locator}, confidence?: str,
}
edge = {
  id: str, type: str, source: str, target: str,
  bottleneck?: bool, finding_id?: str, capability_id?: str,
}
graph = { nodes: [node], edges: [edge] }
```

- `_asset_graph_view(asset_graph)` → `graph` for `data.attack_paths.graph`
  (node.type from `node_type`; edge.type from `edge_type`; map `from`/`to`→source/target;
  carry provenance/confidence/traversal_cost; `bottleneck` from the path bottleneck set).
- A focused variant `data.attack_paths.graph_path_focused` (nodes/edges that appear in any
  enumerated path) — parity with today's `mermaid_path_focused`. `None`/omitted when there
  are no enumerated paths.
- `_threat_surface_graph(entries, asset_inventory)` → `data.threat_model.surface_graph`:
  one `asset` node per distinct asset (`badge` = STRIDE letters, `hot` per gap), plus one
  `boundary` compound node per trust boundary with member assets as children
  (`parent`); edges from inventory flows when present, else none (graceful degrade).
  `None` when there are no entries (so the block is omitted, as in #78).

The Mermaid string fields (`mermaid`, `mermaid_path_focused`, `surface_mermaid`) are removed.

## `GraphView` component (components.jsx)

Replaces `MermaidGraph`. Props:

```
GraphView({
  graph,                 // {nodes, edges}; renders empty-state when falsy/empty
  layout = "dagre",      // "dagre" | "fcose"
  idBase,                // unique cy container key
  paths = null,          // optional [{id, edgeIds:[...]}] for path highlighting
  selectedPathId = null, // controlled: highlight this path (from a sibling list)
  onSelectPath = null,   // (pathId|null) => void — node/path click reports selection
  compound = false,      // TM: honor node.parent for trust-boundary clusters
})
```

Behavior:

- Builds a Cytoscape instance into `report-graph__canvas` (reuses the #78
  `report-graph__wrapper` + `report-graph__toolbar`). Elements from `graph.nodes/edges`
  (compound parents wired via `data.parent` when `compound`).
- **Stylesheet** derived at mount from `getComputedStyle(document.body)` reads of the report
  CSS tokens; node style keyed on `type` (crown_jewel/attacker distinct shape+color, `hot`
  → `--sev-high`), edge style on `type` (+ `bottleneck` → thicker `--sev-high`; arrowheads
  for directed types). Re-applied on `body[data-theme]` change via a `MutationObserver`.
- **Layout:** `dagre` (rankDir TB) for the attack graph; `fcose` for the TM map. `fit()` on
  layout stop.
- **Interactivity:** pan + wheel-zoom (Ctrl/Cmd or always — match the #78 toolbar behavior) +
  node drag; toolbar −/%/＋/100%/fit drives `cy.zoom()`/`cy.fit()`.
- **Hover tooltip:** an absolutely-positioned `report-graph__tooltip` div (no HTML from data
  — text nodes only) showing node `label`·`type`·provenance, or edge `type`·finding/
  capability id, following the cursor; hidden on mouseout.
- **Click-to-highlight-paths (in scope):**
  - When `paths` is provided, clicking a node selects the **union of paths that include that
    node** (a path includes a node if any of its `edgeIds` is incident to the node); the
    selected paths' nodes+edges get a `.hl` class, everything else `.dim`. `onSelectPath`
    fires with the chosen path id (or a synthetic "node:<id>" selection). Clicking the same
    node again, or background, clears (`onSelectPath(null)`).
  - `selectedPathId` is honored as a **controlled** input so a sibling list (the Attack-paths
    "Enumerated paths" entries) can drive the same highlight — clicking a path row highlights
    it on the graph and vice-versa (two-way via `onSelectPath`).
  - When `paths` is absent (TM map), clicking a node highlights its **immediate neighborhood**
    (incident edges + adjacent nodes), dimming the rest; background clears.
- **Empty / error:** empty graph → existing `empty-state`; a Cytoscape exception →
  `report-graph__canvas` shows a "graph render failed: <msg>" text node (mirrors the Mermaid
  catch). Destroy the cy instance on unmount.

## Screen wiring

- `AttackPaths.jsx`: derive `paths = ap.pairs.flatMap(p => p.paths).map(p => ({id: p.path_id, edgeIds: p.edges}))`; render `<GraphView graph={ap.graph} layout="dagre" idBase="apd-asset-graph" paths={paths} selectedPathId={sel} onSelectPath={setSel} />` and the focused graph from `ap.graph_path_focused`. The "Enumerated paths" list rows become clickable and call `setSel(p.path_id)` (and show selected state), giving graph↔list cross-highlight. Banner + pairs + D3FEND overlay unchanged.
- `ThreatModel.jsx`: `<GraphView graph={tm.surface_graph} layout="fcose" idBase="apd-tm-surface" compound />` (block D). Blocks A/B/C/E unchanged.

## Vendoring / build

- `.build/package.json`: add `cytoscape`, `cytoscape-dagre`, `cytoscape-fcose`; remove `mermaid`.
- `.build/react-globals.js`: remove the Mermaid import; add
  `import cytoscape from "cytoscape"; import dagre from "cytoscape-dagre"; import fcose from "cytoscape-fcose"; cytoscape.use(dagre); cytoscape.use(fcose); window.cytoscape = cytoscape;`.
- `.build/build.mjs`: delete the `mermaid.min.js` copy step; update `vendor-licenses.txt`
  (Cytoscape MIT, cytoscape-dagre MIT, dagre MIT, cytoscape-fcose MIT) — drop the Mermaid line.
- `screens.css`: keep `report-graph__wrapper/__toolbar/__canvas`; remove the
  `…__mermaid svg …` rules; add `report-graph__tooltip`, `.hl`/`.dim` are Cytoscape classes
  (styled in JS, not CSS). `report-graph__canvas` gets an explicit height (Cytoscape needs a
  sized container).

## Audit (audit.py)

`attack_paths_present` (and any check that referenced the `mermaid` field) now asserts the
structured `graph` presence (`attack_paths.graph.nodes` non-empty when the run has an asset
graph). Threat-model coherence (the #78 `threat_model_scene_coherent`) is unchanged in intent
but no longer depends on `surface_mermaid`.

## Testing

- **Python:** `_asset_graph_view` (node/edge type mapping, source/target, bottleneck flag,
  `_safe_label` sanitization of adversarial names, counts) and `_threat_surface_graph`
  (compound boundary parents, STRIDE `badge`, `hot`, graceful no-boundary/no-entry degrade);
  the focused-graph subset; updated `audit.py` tests for the `graph` field.
- **JS contract tests** (text, mirroring #78's read-as-text approach): `GraphView` exists +
  uses `window.cytoscape` + dagre/fcose; both screens render `<GraphView`; `react-globals`
  imports cytoscape, not mermaid; `build.mjs` no longer copies `mermaid.min.js`; the built
  `index.html`/sources contain no `mermaid` reference; the #78 `MermaidGraph`/`securityLevel`
  assertions are replaced. A grep-style test asserts **zero** `mermaid` references remain in
  `report-template/` and `tools/`.
- **Regen + gates:** rebuild the bundle; regenerate the golden
  (`tests/fixtures/report-html/claim-event-bus-golden-data.js`), `report-template/data.js`,
  and the example's committed `expected/40-synthesis/report-html/` (the #78 lesson — the
  shipped example must demonstrate the change); `data.js` now carries `graph` objects, not
  Mermaid strings. Assert `tools/.../app.js` **shrank** vs main. ruff + mypy + `pytest -q` +
  `check_report_template_freshness.py` all green. markdownlint clean.
- **Manual:** open the example report; on both the Attack-paths and Threat-model tabs verify
  nodes/edges render with type styling, pan/zoom/drag/fit work, hover tooltips show
  provenance, **clicking a node highlights its path(s)** and the Attack-paths list ↔ graph
  cross-highlight, and theme switching (light/paper/dark) recolors the graph.

## Files to change (representative)

- `tools/apd_gauntlet/report/transform.py` — replace the 3 `_build_*mermaid` helpers with
  `_asset_graph_view` + `_threat_surface_graph`; update `data.attack_paths` /
  `data.threat_model` fields.
- `tools/apd_gauntlet/synthesis/audit.py` — `attack_paths_present` checks `graph`.
- `report-template/components.jsx` — `MermaidGraph` → `GraphView` (Cytoscape).
- `report-template/screens/AttackPaths.jsx`, `report-template/screens/ThreatModel.jsx` —
  use `GraphView`; AttackPaths adds list↔graph path selection.
- `report-template/.build/{package.json,react-globals.js,build.mjs}`,
  `report-template/screens.css`.
- Rebuilt bundle + regenerated golden/demo/example report-html.
- Tests under `tests/unit/report/` + `tests/test_workflow_apd_gauntlet.py`-style contract;
  `docs/html-report.md`; `CHANGELOG.md`.

## Risks / watch-items

- **Bundle/offline:** confirm Cytoscape + dagre + fcose bundle cleanly under esbuild IIFE and
  run over `file://` with no network. Verify the net `app.js` size drop.
- **Canvas theming:** Cytoscape canvas doesn't inherit CSS vars — must read computed token
  values and re-style on theme change; verify all three themes + the severity palette.
- **Compound + fcose** for the TM map must degrade gracefully when a run has no trust
  boundaries (flat nodes) and when there are no edges.
- **Path-id integrity:** path `edgeIds` must match `asset-graph` `edge_id`s so highlighting
  resolves; covered by a transform/contract test.
- **Golden churn:** regenerate deterministically; the `graph` objects replace large Mermaid
  strings — eyeball the diff.
- **Accessibility/print:** canvas graphs don't print/scale like SVG; acceptable (the report
  is screen-first), but note it.
