# Attack Paths scene — "findings-only" filter — design

- **Date:** 2026-06-13
- **Status:** Approved (brainstorm), pending implementation plan
- **Author:** brainstorming session (grounded in a code-recon of the Attack Paths scene, the shared Cytoscape `GraphView`, the `_asset_graph_view*` transforms, the report-audit checks, and the bundle freshness gate)
- **Affects:** the HTML report's **Attack Paths** scene renderer only. **No `transform.py` change. No schema change. No `data.js`/`report-data.yaml` change. No `audit.py` change. No new agent/skill/LLM dependency.**

## 1. Problem

The report's **Attack Paths** scene
([AttackPaths.jsx](../../../report-template/screens/AttackPaths.jsx)) renders three views off
`data.attack_paths` (`ap`):

1. **Asset graph** — `<GraphView graph={ap.graph} …>` — every node/edge in the computed asset graph
   (including pure trust-boundary and capability-derived edges that no enumerated path touches).
2. **Path-focused graph** — `<GraphView graph={ap.graph_path_focused} …>` — the subset of nodes/edges
   that lie on *any* enumerated path.
3. **Enumerated paths** — `ap.pairs.map(...)` — every attacker→crown-jewel path, grouped by pair.

A reader triaging a report usually cares about the paths that **depend on an actual specialist-identified
vulnerability** — i.e. paths that traverse a `compromisable_via_finding` edge. Those are already flagged
per-path with the **⚑ N findings** badge, but the reader cannot *focus* the scene on them: the graphs and
the path list still show every finding-free (trust-boundary-only) path and every asset that exists solely
to support one.

## 2. Goals / non-goals

**Goals**

- Add a single interactive **toggle** to the Attack Paths scene that filters all three views to
  **finding-bearing paths** (and the assets exclusive to them).
- Default the toggle **ON** so the scene opens focused on finding-bearing paths, with a graceful fallback
  when there is nothing to filter.
- Derive the filter **entirely client-side** from data already present in `data.attack_paths` — a JS mirror
  of the existing `_asset_graph_view_focused` subset logic.

**Non-goals (YAGNI)**

- **No** persistence of the toggle across sessions (no tweaks-panel/localStorage entry). State is ephemeral
  React state, matching the Findings-scene filters.
- **No** per-view independent toggles. One control drives all three views.
- **No** change to which paths/findings/edges get *computed*. This is a render-time view filter only.
- **No** change to the asset-graph **summary banner** numbers (they describe the full computed graph and
  remain factual); the filtered counts live in the new toolbar caption.

## 3. The predicate — "a path has findings"

A path **has findings** iff it traverses at least one **finding-derived edge**:

```js
const pathHasFindings = (p) => (p.edges_detailed || []).some((e) => e.finding_id);
```

This is exactly the signal behind the existing **⚑ N findings** badge
([AttackPaths.jsx](../../../report-template/screens/AttackPaths.jsx), `pathFindingIds`). It is the
*discriminating* signal: pure trust-boundary paths have no `finding_id` on any hop and are filtered out.

**Rejected predicate:** counting the path's own `apath-*` risk finding. Nearly every enumerated risk path
generates an `apath-*` finding, so that predicate filters out almost nothing — not useful.

## 4. Approach — client-side, no data/schema change

Everything the filter needs is already in `data.attack_paths`:

- `ap.pairs[].paths[].edges_detailed[].finding_id` — the predicate (§3).
- `ap.pairs[].paths[].edges` — the edge IDs each path traverses.
- `ap.graph` and `ap.graph_path_focused` — the `{nodes, edges}` views to subset.

So the filter is **pure render logic in `AttackPaths.jsx`** — a JS mirror of the Python
`_asset_graph_view_focused` ([transform.py](../../../tools/apd_gauntlet/report/transform.py)), scoped to
finding-bearing paths.

**Rejected alternative:** precomputing filtered graph variants + `has_findings` flags in `transform.py`.
That would touch the data model, the schema, `data.js`/`report-data.yaml`, and the report-audit surface for
no benefit — all inputs are already client-side. Confirmed the relevant audit checks
(`attack_paths_present`, `attack_path_strip`) read **static data** (`graph_nodes=` from the serialized graph;
`attack_path` strip block on `data.js` findings), **not the rendered DOM**, so a default-ON client-side
toggle leaves every gate green ([audit.py](../../../tools/apd_gauntlet/synthesis/audit.py)).

### 4.1 Derivation (in `AttackPaths.jsx`)

```js
const allPaths     = ap.pairs.flatMap((pair) => pair.paths || []);
const findingPaths = allPaths.filter(pathHasFindings);
const anyFindingPaths = findingPaths.length > 0;

// Default ON, but only "effective" when there is something to filter (see §5).
const [findingsOnly, setFindingsOnly] = React.useState(true);
const effectiveOn = findingsOnly && anyFindingPaths;

// Union of edges traversed by finding-bearing paths.
const keepEdgeIds = new Set(findingPaths.flatMap((p) => p.edges || []));

// JS mirror of _asset_graph_view_focused: keep edges in the set, keep their endpoint nodes.
function subsetGraph(graph, edgeIdSet) {
  if (!graph) return graph;
  const edges = (graph.edges || []).filter((e) => edgeIdSet.has(e.id));
  const keep = new Set();
  edges.forEach((e) => { keep.add(e.source); keep.add(e.target); });
  const nodes = (graph.nodes || []).filter((n) => keep.has(n.id));
  return { ...graph, nodes, edges };
}
```

### 4.2 Applying the filter to the three views

1. **Asset graph**
   - `graph = effectiveOn ? subsetGraph(ap.graph, keepEdgeIds) : ap.graph`
   - The `paths` highlight-prop is likewise narrowed:
     `effectiveOn ? findingPaths.map(...) : allPaths.map(...)` (so click-to-highlight only offers
     finding-bearing paths when filtered).
2. **Path-focused graph**
   - `graph = effectiveOn ? subsetGraph(ap.graph_path_focused, keepEdgeIds) : ap.graph_path_focused`
   - The section's existing `ap.graph_path_focused && (...)` guard is unchanged; when `effectiveOn` the
     subset is non-empty (because `effectiveOn ⇒ anyFindingPaths`).
3. **Enumerated paths**
   - For each pair, render `effectiveOn ? pair.paths.filter(pathHasFindings) : pair.paths`.
   - **Skip rendering any pair whose visible-path list is empty.**
   - Per-pair count and the new toolbar caption reflect the filtered counts. The section `<h2>` keeps the
     analysis totals (`ap.summary.total_pairs` / `total_paths`) — those are factual run totals.

## 5. Control & UX

A single toggle, inserted as a small toolbar row **after the asset-graph summary banner and before the
"Asset graph" section**, styled with the existing `chip` / `chip--active` convention used by the Findings
toolbar.

- **Default ON.** The scene opens showing only finding-bearing paths/assets.
- **Label + live count**, e.g. **`⚑ Findings only`** followed by *"showing N of M paths · X finding-free
  hidden"*; toggled off: *"showing all M paths."*
- **Toggling resets `selectedPathId`** to `null`, so a highlight selected before the toggle does not dangle
  on a now-hidden path.

## 6. Edge cases

- **No path has findings** (`anyFindingPaths === false`): default-ON would blank the scene, so `effectiveOn`
  is forced **false** and the toggle renders **disabled** with the caption *"No path traverses a
  finding-derived edge — nothing to filter."* All three views show everything. This is the safety valve for
  the default-ON choice.
- **Reverse-nav (`focusPathId`)**: the existing focus effect
  ([AttackPaths.jsx](../../../report-template/screens/AttackPaths.jsx)) scrolls to a path opened from a
  finding's hop-strip "view full graph →" link
  ([per the 2026-06-10 hop-strip design](2026-06-10-attack-path-finding-visualization-design.md)). If the
  targeted path is finding-*free*, the effect **flips `findingsOnly` off** before scrolling, so default-ON
  cannot silently swallow the navigation.
- **`ap` null / `ap.pairs` empty**: existing empty states are unchanged; the toolbar is not rendered.

## 7. What changes

| File | Change |
|---|---|
| [report-template/screens/AttackPaths.jsx](../../../report-template/screens/AttackPaths.jsx) | filter state + `effectiveOn`, `pathHasFindings`, `subsetGraph`, toolbar row, apply to the 3 views, §6 edge cases |
| [report-template/screens.css](../../../report-template/screens.css) | *only if* the existing `chip` styles are insufficient — the goal is **no CSS change** (reuse `chip`/`chip--active` + inline styles already used in this scene) |
| `tools/apd_gauntlet/data/report-template/{app.js,index.html,.source-hash}` | regenerated by `python tools/build_report_template.py` (freshness gate) |
| `examples/apd-20260601-claim-event-bus/expected/40-synthesis/report-html/{app.js,.source-hash}` | regenerated via `apd-gauntlet build-report …` (the new bundle; `data.js` unchanged) |
| `examples/apd-20260602-acme-mobile-banking/expected/40-synthesis/report-html/{app.js,.source-hash}` | same |

## 8. Tests & verification

- **Source-grep test** (repo convention for JSX, alongside
  `test_attack_paths_uses_graphview_with_path_selection` in
  [tests/test_workflow_apd_gauntlet.py](../../../tests/test_workflow_apd_gauntlet.py)): assert the new
  filter markers are present in `AttackPaths.jsx` (e.g. the predicate, `subsetGraph`, the toggle label, the
  default-ON state). The existing test must keep passing (all of `GraphView`, `ap.graph`,
  `ap.graph_path_focused`, `selectedPathId`, `onSelectPath`, `edgeIds`, `path_id` remain present).
- **Freshness:** `tests/unit/report/test_tier3_bundle_freshness.py::test_shipped_bundle_source_hash_matches`
  enforces the rebuild (`.source-hash` must equal `compute_source_hash()`).
- **Full suite green:** `pytest` + `ruff` + `mypy` + `markdownlint` per the usual CI gate.
- **Manual / visual:** build a report that has attack paths → confirm (a) default-ON filters all three views,
  (b) toggling off restores every path/asset, (c) the no-findings fallback renders the disabled toggle, and
  (d) a hop-strip reverse-nav to a finding-free path flips the filter off and lands on the row.

## 9. Build & verification commands

```bash
# 1. Rebuild the canonical bundle (refreshes app.js + .source-hash).
python tools/build_report_template.py

# 2. Regenerate the two tracked example reports (new bundle; data.js unchanged).
apd-gauntlet build-report examples/apd-20260601-claim-event-bus/expected/ --quiet
apd-gauntlet build-report examples/apd-20260602-acme-mobile-banking/expected/ --quiet

# 3. Gates.
pytest tests/unit/report/test_tier3_bundle_freshness.py tests/test_workflow_apd_gauntlet.py -q
pytest -q
ruff check . && mypy tools && markdownlint docs/**/*.md
```
