# Attack Paths "findings-only" filter — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a default-ON toggle to the HTML report's Attack Paths scene that filters all three views (asset graph, path-focused graph, enumerated paths) to attack paths that traverse a finding-derived edge.

**Architecture:** Pure client-side render logic in `report-template/screens/AttackPaths.jsx`. A JS mirror of the existing Python `_asset_graph_view_focused` subset, scoped to finding-bearing paths, memoized so the cytoscape graph prop stays identity-stable across unrelated re-renders. No `transform.py`/schema/`data.js`/audit change. The JSX edit is followed by the mandatory esbuild bundle rebuild + tracked-example regeneration (freshness gate).

**Tech Stack:** React (in-browser, esbuild-bundled), cytoscape `GraphView`, Python (`apd-gauntlet` CLI for report build), pytest source-grep tests.

**Spec:** [docs/superpowers/specs/2026-06-13-attack-paths-findings-filter-design.md](../specs/2026-06-13-attack-paths-findings-filter-design.md)

---

## File Structure

| File | Responsibility | Action |
|---|---|---|
| `report-template/screens/AttackPaths.jsx` | The scene: filter state, predicate, memoized graph subsetter, toolbar, apply to 3 views, edge cases | Modify |
| `tests/test_workflow_apd_gauntlet.py` | Source-grep guard asserting the filter markers exist in the scene | Modify (add 1 test) |
| `tools/apd_gauntlet/data/report-template/{app.js,index.html,.source-hash}` | Canonical precompiled bundle shipped with the gauntlet | Regenerate (build script) |
| `examples/apd-20260601-claim-event-bus/expected/40-synthesis/report-html/*` | Tracked example report | Regenerate (`build-report`) |
| `examples/apd-20260602-acme-mobile-banking/expected/40-synthesis/report-html/*` | Tracked example report | Regenerate (`build-report`) |

**Branch:** already on `feat/attack-paths-findings-filter` (the spec is committed there).

---

## Task 1: Implement the findings-only filter in the scene

**Files:**
- Modify: `report-template/screens/AttackPaths.jsx`
- Test: `tests/test_workflow_apd_gauntlet.py`

> **Note on the freshness gate:** this task edits source JSX but does **not** rebuild the bundle. After this task, `tests/unit/report/test_tier3_bundle_freshness.py::test_shipped_bundle_source_hash_matches` is **expected to fail** (stale bundle). Task 2 rebuilds and turns it green. Do **not** run the full suite at the end of this task — run only the scene-specific tests named below.

- [ ] **Step 1: Write the failing test**

Add this function to `tests/test_workflow_apd_gauntlet.py` immediately after `test_attack_paths_uses_graphview_with_path_selection` (which already defines/uses the module-level `REPO` constant):

```python
def test_attack_paths_has_findings_only_filter() -> None:
    ap = (REPO / "report-template" / "screens" / "AttackPaths.jsx").read_text(encoding="utf-8")
    # Default-ON interactive toggle state.
    assert "findingsOnly" in ap and "setFindingsOnly" in ap
    assert "useState(true)" in ap  # the toggle defaults ON
    # Predicate: a path "has findings" iff it traverses a finding-derived edge.
    assert "pathHasFindings" in ap
    # Effective filter state gates the no-findings fallback (default-ON safety).
    assert "anyFindingPaths" in ap and "effectiveOn" in ap
    # Client-side graph subsetter (JS mirror of _asset_graph_view_focused).
    assert "subsetGraph" in ap
    # The toggle is labelled.
    assert "Findings only" in ap
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `pytest tests/test_workflow_apd_gauntlet.py::test_attack_paths_has_findings_only_filter -v`
Expected: **FAIL** (markers like `findingsOnly` / `subsetGraph` not yet in the scene).

- [ ] **Step 3: Read the scene file**

Run: open `report-template/screens/AttackPaths.jsx` with the Read tool (required before Edit, and to confirm the exact strings below match the working tree).

- [ ] **Step 4: Replace the top-of-component derivations + focus effect**

Edit `report-template/screens/AttackPaths.jsx`.

**OLD** (the block from the `selectedPathId` state through the old flat `paths` list):

```jsx
  const [selectedPathId, setSelectedPathId] = React.useState(null);

  // Reverse-nav focus: the <details> pairs are intentionally UNCONTROLLED (no `open`
  // prop), so imperatively setting det.open here is safe and React won't reset it.
  React.useEffect(() => {
    if (!focusPathId) return;
    setSelectedPathId(focusPathId);
    const row = document.getElementById(`ap-row-${focusPathId}`);
    if (row) {
      const det = row.closest("details");
      if (det) det.open = true;
      row.scrollIntoView({ behavior: "smooth", block: "center" });
    }
  }, [focusPathId]);
  const paths = (ap && ap.pairs || []).flatMap((pair) =>
    (pair.paths || []).map((p) => ({ id: p.path_id, edgeIds: p.edges || [] })));
```

**NEW:**

```jsx
  // --- Findings-only filter (default ON) ---------------------------------
  // A path "has findings" iff it traverses a finding-derived edge — the same
  // signal as the per-path ⚑ N findings badge. One toggle narrows all three
  // views (asset graph, path-focused graph, enumerated paths) to those paths.
  const pathHasFindings = (p) => (p.edges_detailed || []).some((e) => e.finding_id);
  const allPaths = (ap && ap.pairs || []).flatMap((pair) => pair.paths || []);
  const findingPaths = allPaths.filter(pathHasFindings);
  const anyFindingPaths = findingPaths.length > 0;

  const [selectedPathId, setSelectedPathId] = React.useState(null);
  const [findingsOnly, setFindingsOnly] = React.useState(true);
  // "Effective" only when there is something to filter — otherwise default-ON
  // would blank the scene (see the disabled-toggle fallback in the toolbar).
  const effectiveOn = findingsOnly && anyFindingPaths;

  // Reverse-nav focus: the <details> pairs are intentionally UNCONTROLLED (no `open`
  // prop), so imperatively setting det.open here is safe and React won't reset it.
  React.useEffect(() => {
    if (!focusPathId) return;
    setSelectedPathId(focusPathId);
    // If the target path is finding-free, default-ON would hide it — flip off.
    const target = allPaths.find((p) => p.path_id === focusPathId);
    if (target && !pathHasFindings(target)) setFindingsOnly(false);
    const row = document.getElementById(`ap-row-${focusPathId}`);
    if (row) {
      const det = row.closest("details");
      if (det) det.open = true;
      row.scrollIntoView({ behavior: "smooth", block: "center" });
    }
  }, [focusPathId]);

  // Memoized graph views so the GraphView `graph` prop identity is stable
  // across unrelated re-renders (selecting a path must NOT rebuild cytoscape).
  // Recomputes only when the data or the effective filter state changes.
  const graphs = React.useMemo(() => {
    function subsetGraph(graph, edgeIdSet) {
      if (!graph) return graph;
      const edges = (graph.edges || []).filter((e) => edgeIdSet.has(e.id));
      const keep = new Set();
      edges.forEach((e) => { keep.add(e.source); keep.add(e.target); });
      const nodes = (graph.nodes || []).filter((n) => keep.has(n.id));
      return { ...graph, nodes, edges };
    }
    const full = ap && ap.graph;
    const focused = ap && ap.graph_path_focused;
    if (!effectiveOn) return { asset: full, focused };
    const fps = (ap && ap.pairs || []).flatMap((pair) => pair.paths || [])
      .filter((p) => (p.edges_detailed || []).some((e) => e.finding_id));
    const ids = new Set(fps.flatMap((p) => p.edges || []));
    return { asset: subsetGraph(full, ids), focused: subsetGraph(focused, ids) };
  }, [ap, effectiveOn]);

  // Flat path list for graph↔list cross-highlight (narrowed when filtering).
  const highlightPaths = (effectiveOn ? findingPaths : allPaths).map(
    (p) => ({ id: p.path_id, edgeIds: p.edges || [] }));
```

> All four hooks (`useState` ×2, `useEffect`, `useMemo`) stay above the `if (!ap)` early-return and use `ap &&` guards, so a null `ap` is safe and hook order is unconditional.

- [ ] **Step 5: Insert the toolbar + repoint the asset graph**

**OLD** (end of the asset-graph summary banner + the Asset graph section):

```jsx
        {edgeCount} edge{edgeCount !== 1 ? "s" : ""}{" "}
        ({tbEdges} trust-boundary, {findEdges} finding-derived, {capEdges} capability-derived)
      </div>

      <section className="attack-paths__graph">
        <h3 className="attack-paths__section-h">Asset graph</h3>
        <GraphView graph={ap.graph} layout="dagre" idBase="apd-asset-graph"
          paths={paths} selectedPathId={selectedPathId} onSelectPath={setSelectedPathId} />
      </section>
```

**NEW:**

```jsx
        {edgeCount} edge{edgeCount !== 1 ? "s" : ""}{" "}
        ({tbEdges} trust-boundary, {findEdges} finding-derived, {capEdges} capability-derived)
      </div>

      {/* Findings-only filter — one toggle drives all three views below. */}
      <div style={{ display: "flex", alignItems: "center", gap: "var(--space-2)", margin: "var(--space-3) 0 0" }}>
        <button
          type="button"
          className={`chip ${effectiveOn ? "chip--active" : ""}`}
          disabled={!anyFindingPaths}
          aria-pressed={effectiveOn}
          onClick={() => { setFindingsOnly((v) => !v); setSelectedPathId(null); }}
          title={anyFindingPaths
            ? "Show only attack paths that traverse a finding-derived edge (and the assets exclusive to them)"
            : "No path traverses a finding-derived edge — nothing to filter"}
          style={{ cursor: anyFindingPaths ? "pointer" : "not-allowed", opacity: anyFindingPaths ? 1 : 0.55 }}
        >⚑ Findings only</button>
        <span style={{ fontFamily: "var(--font-mono)", fontSize: "var(--text-xs)", color: "var(--ink-3)" }}>
          {!anyFindingPaths
            ? "No path traverses a finding-derived edge — nothing to filter."
            : effectiveOn
              ? `showing ${findingPaths.length} of ${allPaths.length} path${allPaths.length === 1 ? "" : "s"} · ${allPaths.length - findingPaths.length} finding-free hidden`
              : `showing all ${allPaths.length} path${allPaths.length === 1 ? "" : "s"}`}
        </span>
      </div>

      <section className="attack-paths__graph">
        <h3 className="attack-paths__section-h">Asset graph</h3>
        <GraphView graph={graphs.asset} layout="dagre" idBase="apd-asset-graph"
          paths={highlightPaths} selectedPathId={selectedPathId} onSelectPath={setSelectedPathId} />
      </section>
```

- [ ] **Step 6: Repoint the path-focused graph**

**OLD:**

```jsx
      {ap.graph_path_focused && (
        <section className="attack-paths__graph">
          <h3 className="attack-paths__section-h">Path-focused graph</h3>
          <GraphView graph={ap.graph_path_focused} layout="dagre" idBase="apd-paths-focused" />
        </section>
      )}
```

**NEW:**

```jsx
      {graphs.focused && (
        <section className="attack-paths__graph">
          <h3 className="attack-paths__section-h">Path-focused graph</h3>
          <GraphView graph={graphs.focused} layout="dagre" idBase="apd-paths-focused" />
        </section>
      )}
```

- [ ] **Step 7: Filter the enumerated paths (skip emptied pairs)**

**OLD** (the start of the pair map — first two lines):

```jsx
        {ap.pairs.map((pair, idx) => {
          const atkName  = pair.attacker_position_name || pair.attacker_position;
```

**NEW:**

```jsx
        {ap.pairs.map((pair, idx) => {
          const visiblePaths = effectiveOn
            ? (pair.paths || []).filter(pathHasFindings)
            : (pair.paths || []);
          if (visiblePaths.length === 0) return null;
          const atkName  = pair.attacker_position_name || pair.attacker_position;
```

- [ ] **Step 8: Use the filtered list for the per-pair count**

**OLD:**

```jsx
                <span className="attack-pair__count">{pair.paths.length} path{pair.paths.length === 1 ? "" : "s"}</span>
```

**NEW:**

```jsx
                <span className="attack-pair__count">{visiblePaths.length} path{visiblePaths.length === 1 ? "" : "s"}</span>
```

- [ ] **Step 9: Render the filtered paths**

**OLD:**

```jsx
              <ul className="attack-pair__paths">
                {pair.paths.map((p) => {
```

**NEW:**

```jsx
              <ul className="attack-pair__paths">
                {visiblePaths.map((p) => {
```

- [ ] **Step 10: Run the scene tests to verify they pass**

Run: `pytest tests/test_workflow_apd_gauntlet.py::test_attack_paths_has_findings_only_filter tests/test_workflow_apd_gauntlet.py::test_attack_paths_uses_graphview_with_path_selection -v`
Expected: **both PASS** (new markers present; the pre-existing scene contract — `GraphView`, `ap.graph`, `ap.graph_path_focused`, `selectedPathId`, `onSelectPath`, `edgeIds`, `path_id` — is preserved).

- [ ] **Step 11: Commit**

```bash
git add report-template/screens/AttackPaths.jsx tests/test_workflow_apd_gauntlet.py
git commit -m "feat(report): findings-only filter for the Attack Paths scene

Default-ON toggle that narrows the asset graph, path-focused graph, and
enumerated paths to attack paths traversing a finding-derived edge (the
per-path findings badge). Disabled fallback when no path has findings;
reverse-nav to a finding-free path auto-disables the filter. Client-side
only — no transform/schema/data/audit change. Bundle rebuilt in the next
commit.

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 2: Rebuild the bundle + regenerate tracked example reports

**Files:**
- Regenerate: `tools/apd_gauntlet/data/report-template/{app.js,index.html,.source-hash}`
- Regenerate: `examples/apd-20260601-claim-event-bus/expected/40-synthesis/report-html/*`
- Regenerate: `examples/apd-20260602-acme-mobile-banking/expected/40-synthesis/report-html/*`

- [ ] **Step 1: Rebuild the canonical bundle**

Run: `python tools/build_report_template.py`
Expected: prints `build-report-template: bundle written.` (Requires Node 20+ and npm; the script runs `npm ci` in `report-template/.build/` on first use.)

- [ ] **Step 2: Confirm the freshness gate is now green**

Run: `pytest tests/unit/report/test_tier3_bundle_freshness.py -v`
Expected: **PASS** — in particular `test_shipped_bundle_source_hash_matches` (the rebuilt `.source-hash` now equals `compute_source_hash()`).

- [ ] **Step 3: Regenerate the two tracked example reports**

Run:
```bash
apd-gauntlet build-report examples/apd-20260601-claim-event-bus/expected/ --quiet
apd-gauntlet build-report examples/apd-20260602-acme-mobile-banking/expected/ --quiet
```
Expected: each exits 0 and refreshes that example's `report-html/` from the new canonical bundle.

- [ ] **Step 4: Review what changed**

Run: `git status --porcelain && git diff --stat`
Expected: changes confined to the canonical bundle (`tools/apd_gauntlet/data/report-template/`) and the two `examples/*/expected/40-synthesis/report-html/` trees. `data.js` files should be unchanged (no data-model change). If any `data.js` shows a diff, STOP and investigate — the feature must not alter serialized data.

- [ ] **Step 5: Run the full gate**

Run:
```bash
pytest -q
ruff check . && mypy tools
```
Expected: **all green** (mypy scope follows the repo's configured target; mirror the CI invocation if different).

- [ ] **Step 6: Commit**

```bash
git add tools/apd_gauntlet/data/report-template examples/apd-20260601-claim-event-bus/expected/40-synthesis/report-html examples/apd-20260602-acme-mobile-banking/expected/40-synthesis/report-html
git commit -m "build(report): rebuild bundle + regenerate example reports for findings filter

Refreshes app.js + .source-hash (freshness gate) and the two tracked
example report-html bundles. data.js unchanged.

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Manual / visual verification (after Task 2)

Apply the `superpowers:verification-before-completion` discipline — confirm behavior in a browser, don't just assert it.

- [ ] Open a regenerated example report in a browser, e.g.
  `examples/apd-20260602-acme-mobile-banking/expected/40-synthesis/report-html/index.html`,
  and go to the **Attack Paths** tab.
- [ ] **Default ON:** the `⚑ Findings only` chip is active; the asset graph, path-focused graph, and enumerated-paths list show only finding-bearing paths/assets; the caption reads `showing N of M paths · X finding-free hidden`.
- [ ] **Toggle off:** clicking the chip restores every path/asset; caption reads `showing all M paths`; selecting a path still cross-highlights the graph (no canvas flicker on selection — confirms the `useMemo` identity stability).
- [ ] **Fallback:** if an example has no finding-bearing paths, the chip is disabled with the "nothing to filter" caption and all three views render unfiltered. (If neither example exhibits this, it is covered by the `anyFindingPaths`/`effectiveOn` branch; note that in the PR rather than forcing a fixture.)
- [ ] **Reverse-nav:** from a finding with an attack-path hop-strip, click "view full graph →"; the Attack Paths tab opens scrolled to that path. If that path is finding-free, the filter auto-disables so the row is visible.

---

## Self-Review

**1. Spec coverage** — every spec section maps to a task:
- §3 predicate → Task 1 Step 4 (`pathHasFindings`).
- §4.1 derivation + §4.2 three-view application → Task 1 Steps 4–9 (`graphs` memo, `highlightPaths`, asset/focused graph repoint, `visiblePaths`).
- §5 control & UX (default ON, label, count, reset selection) → Task 1 Step 5.
- §6 edge cases (no-findings disabled fallback; reverse-nav auto-off) → Task 1 Steps 4 (focus effect) and 5 (`disabled`/caption).
- §7 files / §9 build commands → Task 2.
- §8 tests/freshness → Task 1 Step 1 (source-grep) + Task 2 Steps 2,5.

**2. Placeholder scan** — none. Every code step shows complete code; every run step shows the exact command + expected result.

**3. Type/name consistency** — `pathHasFindings`, `allPaths`, `findingPaths`, `anyFindingPaths`, `findingsOnly`/`setFindingsOnly`, `effectiveOn`, `graphs` (`.asset`/`.focused`), `subsetGraph`, `highlightPaths`, `visiblePaths` are used identically across the test markers (Step 1) and the implementation (Steps 4–9). The asset graph consumes `graphs.asset` + `highlightPaths`; the path-focused graph consumes `graphs.focused`; the test asserts the same identifiers. The old `paths` const is fully removed (replaced by `highlightPaths`) — no dangling reference remains.

**4. Out-of-spec hygiene (optional, not a task)** — the spec scoped no docs change. If house style wants it, a one-line `CHANGELOG.md` entry under the current unreleased/1.7.0 section is reasonable at PR time, but it is intentionally **not** in this plan to stay faithful to the approved spec.
