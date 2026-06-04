# Cytoscape graph renderer (replace Mermaid) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the Mermaid renderer with a shared Cytoscape-based `GraphView` (dagre + fcose) that draws the Attack-paths asset graph and the Threat-model surface map from structured `{nodes, edges}` data, with pan/zoom/drag, hover tooltips, and click-to-highlight-paths.

**Architecture:** Python `transform.py` emits structured graphs (replacing Mermaid strings); a new shared `GraphView` React component (Cytoscape.js) renders them; Mermaid is removed from the bundle entirely. Both report scenes migrate.

**Tech Stack:** Python 3.10+ (pytest, ruff, mypy); React UMD + esbuild bundle; Cytoscape.js + cytoscape-dagre + cytoscape-fcose (vendored via npm + esbuild).

**Spec:** `docs/superpowers/specs/2026-06-03-cytoscape-graph-renderer-design.md`

---

## Design-language consistency contract (REQUIRED)

- Keep the #78 scene structure: `section-eyebrow` / `section-title` headers; the graph mounts in `report-graph__wrapper` + `report-graph__toolbar` + `report-graph__canvas`.
- Node/edge colors come **only** from the report CSS tokens read via `getComputedStyle`: `--ink`, `--ink-3`, `--paper`, `--paper-2`, `--rule`, `--accent`, `--sev-high`, `--sev-low`. No hard-coded palette.
- Reuse shared atoms (`CopyPill`, etc.) and the existing `empty-state` / `empty-state--info` for empty/disabled graphs.
- Labels are sanitized in Python via the existing `_safe_label`; Cytoscape draws them as canvas text (never HTML).

## File structure

- `report-template/.build/package.json` — deps: + cytoscape/cytoscape-dagre/cytoscape-fcose, − mermaid.
- `report-template/.build/react-globals.js` — register cytoscape globally; drop mermaid.
- `report-template/.build/build.mjs` — drop the `mermaid.min.js` copy; update vendor-licenses.
- `report-template/components.jsx` — `MermaidGraph` → `GraphView` (Cytoscape).
- `report-template/screens/AttackPaths.jsx` — render `GraphView`; path selection + list↔graph cross-highlight.
- `report-template/screens/ThreatModel.jsx` — render `GraphView` (compound surface map).
- `report-template/screens.css` — drop mermaid-svg rules; add `report-graph__tooltip`; give `report-graph__canvas` a height.
- `tools/apd_gauntlet/report/transform.py` — `_asset_graph_view` + `_asset_graph_view_focused` + `_threat_surface_graph`; remove the three `_build_*mermaid` helpers + the mermaid string fields.
- `tools/apd_gauntlet/synthesis/audit.py` — `attack_paths_present` also asserts `graph.nodes`.
- Regenerated: bundle (`app.js`, `.source-hash`), `report-template/data.js`, `tests/fixtures/report-html/claim-event-bus-golden-data.js`, `examples/apd-20260601-claim-event-bus/expected/40-synthesis/report-html/`.
- Tests in `tests/unit/report/` + `tests/test_workflow_apd_gauntlet.py`; `docs/html-report.md`; `CHANGELOG.md`.

---

## Task 1: Build deps + globals + vendoring (Cytoscape in, Mermaid out)

**Files:**
- Modify: `report-template/.build/package.json`
- Modify: `report-template/.build/react-globals.js`
- Modify: `report-template/.build/build.mjs`
- Test: `tests/test_workflow_apd_gauntlet.py`

- [ ] **Step 1: Write the failing contract tests**

Add to `tests/test_workflow_apd_gauntlet.py` (uses the module's existing `REPO`):

```python
def test_build_registers_cytoscape_not_mermaid() -> None:
    rg = (REPO / "report-template" / ".build" / "react-globals.js").read_text(encoding="utf-8")
    assert 'import cytoscape from "cytoscape"' in rg
    assert "cytoscape-dagre" in rg and "cytoscape-fcose" in rg
    assert "window.cytoscape = cytoscape" in rg
    assert "mermaid" not in rg
    pkg = (REPO / "report-template" / ".build" / "package.json").read_text(encoding="utf-8")
    assert "cytoscape" in pkg and "cytoscape-dagre" in pkg and "cytoscape-fcose" in pkg
    assert "mermaid" not in pkg
    build = (REPO / "report-template" / ".build" / "build.mjs").read_text(encoding="utf-8")
    assert "mermaid.min.js" not in build  # no longer vendored
```

- [ ] **Step 2: Run it — expect FAIL**

Run: `.venv/bin/python -m pytest tests/test_workflow_apd_gauntlet.py::test_build_registers_cytoscape_not_mermaid -v`
Expected: FAIL (react-globals still imports mermaid).

- [ ] **Step 3: Update `package.json` deps**

In `report-template/.build/package.json` `devDependencies`, remove the `"mermaid": "10.9.6"` line and add:

```json
    "cytoscape": "3.30.2",
    "cytoscape-dagre": "2.5.0",
    "cytoscape-fcose": "2.2.0",
```

- [ ] **Step 4: Update `react-globals.js`**

Replace `import mermaid from "mermaid";` with:

```js
import cytoscape from "cytoscape";
import dagre from "cytoscape-dagre";
import fcose from "cytoscape-fcose";
cytoscape.use(dagre);
cytoscape.use(fcose);
```

and replace `window.mermaid = mermaid;` with `window.cytoscape = cytoscape;`.

- [ ] **Step 5: Update `build.mjs`**

Delete the "4. Vendor mermaid." block (the `copyFileSync(resolve(HERE, "node_modules/mermaid/dist/mermaid.min.js"), …)` call). In the `vendor-licenses.txt` array, remove the Mermaid line and add:

```js
  "Cytoscape.js 3.30.2 — MIT — https://github.com/cytoscape/cytoscape.js/blob/master/LICENSE",
  "cytoscape-dagre 2.5.0 — MIT — https://github.com/cytoscape/cytoscape.js-dagre/blob/master/LICENSE",
  "cytoscape-fcose 2.2.0 — MIT — https://github.com/iVis-at-Bilkent/cytoscape.js-fcose/blob/master/LICENSE",
```

- [ ] **Step 6: Run it — expect PASS**

Run: `.venv/bin/python -m pytest tests/test_workflow_apd_gauntlet.py::test_build_registers_cytoscape_not_mermaid -v`
Expected: PASS. (The bundle is rebuilt in Task 8; npm install runs there.)

- [ ] **Step 7: Commit**

```bash
git add report-template/.build/package.json report-template/.build/react-globals.js report-template/.build/build.mjs tests/test_workflow_apd_gauntlet.py
git commit -m "build(report): vendor Cytoscape (dagre+fcose) as global; drop Mermaid"
```

---

## Task 2: Transform — asset graph view (Attack-paths `graph`)

**Files:**
- Modify: `tools/apd_gauntlet/report/transform.py`
- Test: `tests/unit/report/test_transform_attack_paths.py`

Reuse the existing `_safe_label` (sanitizes adopter-controlled text) and `_safe_node_id`.

- [ ] **Step 1: Write the failing test**

```python
def test_asset_graph_view_maps_nodes_edges_and_bottlenecks():
    from apd_gauntlet.report.transform import _asset_graph_view
    asset_graph = {
        "nodes": [
            {"node_id": "atk-1", "node_type": "attacker", "name": "external_internet"},
            {"node_id": "a-1", "node_type": "asset", "name": "claim-ingress<api>",
             "provenance": {"artifact": "tech_plan.md", "locator": "§4"}, "confidence": "high"},
            {"node_id": "j-1", "node_type": "crown_jewel", "name": "phi_store"},
        ],
        "edges": [
            {"edge_id": "e-1", "edge_type": "network_reachable", "from": "atk-1", "to": "a-1"},
            {"edge_id": "e-2", "edge_type": "data_resides_on", "from": "a-1", "to": "j-1"},
        ],
    }
    g = _asset_graph_view(asset_graph, bottleneck_ids={"e-2"})
    by_id = {n["id"]: n for n in g["nodes"]}
    assert by_id["atk-1"]["type"] == "attacker"
    assert by_id["j-1"]["type"] == "crown_jewel"
    # adopter label sanitized (no raw < > )
    assert "<" not in by_id["a-1"]["label"] and ">" not in by_id["a-1"]["label"]
    assert by_id["a-1"]["provenance"] == {"artifact": "tech_plan.md", "locator": "§4"}
    edges = {e["id"]: e for e in g["edges"]}
    assert edges["e-1"]["source"] == "atk-1" and edges["e-1"]["target"] == "a-1"
    assert edges["e-1"]["type"] == "network_reachable"
    assert edges["e-2"]["bottleneck"] is True and edges["e-1"]["bottleneck"] is False


def test_asset_graph_view_empty_on_missing():
    from apd_gauntlet.report.transform import _asset_graph_view
    assert _asset_graph_view({}, bottleneck_ids=set()) == {"nodes": [], "edges": []}
    assert _asset_graph_view(None, bottleneck_ids=set()) == {"nodes": [], "edges": []}
```

- [ ] **Step 2: Run it — expect FAIL**

Run: `.venv/bin/python -m pytest tests/unit/report/test_transform_attack_paths.py -k asset_graph_view -v`
Expected: FAIL — `_asset_graph_view` not defined.

- [ ] **Step 3: Implement**

Add to `transform.py` (near the soon-to-be-removed mermaid builders):

```python
def _graph_node(raw: dict[str, Any]) -> dict[str, Any]:
    node: dict[str, Any] = {
        "id": str(raw.get("node_id") or ""),
        "type": str(raw.get("node_type") or "asset"),
        "label": _safe_label(str(raw.get("name") or raw.get("node_id") or "")),
    }
    prov = raw.get("provenance")
    if isinstance(prov, dict) and (prov.get("artifact") or prov.get("locator")):
        node["provenance"] = {"artifact": prov.get("artifact"), "locator": prov.get("locator")}
    if raw.get("confidence"):
        node["confidence"] = raw.get("confidence")
    return node


def _asset_graph_view(
    asset_graph: dict[str, Any] | None, *, bottleneck_ids: set[str]
) -> dict[str, Any]:
    """Structured {nodes, edges} for the Attack-paths graph (replaces Mermaid)."""
    if not isinstance(asset_graph, dict):
        return {"nodes": [], "edges": []}
    nodes = [_graph_node(n) for n in asset_graph.get("nodes", []) if isinstance(n, dict)]
    edges = []
    for e in asset_graph.get("edges", []):
        if not isinstance(e, dict):
            continue
        eid = str(e.get("edge_id") or "")
        edge: dict[str, Any] = {
            "id": eid,
            "type": str(e.get("edge_type") or "edge"),
            "source": str(e.get("from") or ""),
            "target": str(e.get("to") or ""),
            "bottleneck": eid in bottleneck_ids,
        }
        edges.append(edge)
    return {"nodes": nodes, "edges": edges}
```

- [ ] **Step 4: Run it — expect PASS**

Run: `.venv/bin/python -m pytest tests/unit/report/test_transform_attack_paths.py -k asset_graph_view -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add tools/apd_gauntlet/report/transform.py tests/unit/report/test_transform_attack_paths.py
git commit -m "feat(report): structured asset-graph view for Attack-paths (replaces mermaid)"
```

---

## Task 3: Transform — focused graph + threat surface graph; wire data; remove Mermaid builders

**Files:**
- Modify: `tools/apd_gauntlet/report/transform.py`
- Test: `tests/unit/report/test_transform_attack_paths.py`, `tests/unit/report/test_transform_threat_model.py`

- [ ] **Step 1: Write the failing tests**

In `test_transform_attack_paths.py`:

```python
def test_asset_graph_view_focused_subsets_to_path_edges():
    from apd_gauntlet.report.transform import _asset_graph_view_focused
    asset_graph = {
        "nodes": [{"node_id": "a", "node_type": "attacker", "name": "atk"},
                  {"node_id": "b", "node_type": "asset", "name": "svc"},
                  {"node_id": "c", "node_type": "asset", "name": "unused"}],
        "edges": [{"edge_id": "e1", "edge_type": "trust", "from": "a", "to": "b"},
                  {"edge_id": "e9", "edge_type": "trust", "from": "b", "to": "c"}],
    }
    paths = [{"path_id": "p1", "edges": ["e1"]}]
    g = _asset_graph_view_focused(asset_graph, paths)
    assert {n["id"] for n in g["nodes"]} == {"a", "b"}   # only nodes on path edges
    assert {e["id"] for e in g["edges"]} == {"e1"}

def test_asset_graph_view_focused_none_when_no_paths():
    from apd_gauntlet.report.transform import _asset_graph_view_focused
    assert _asset_graph_view_focused({"nodes": [], "edges": []}, []) is None
```

In `test_transform_threat_model.py` (replace the old `surface_mermaid` tests — delete `test_build_threat_surface_mermaid_*`):

```python
def test_threat_surface_graph_clusters_badges_and_hot():
    from apd_gauntlet.report.transform import _threat_surface_graph
    entries = [
        {"asset": "api", "stride_letter": "S", "mitigation": "MFA"},
        {"asset": "api", "stride_letter": "I", "mitigation": ""},     # gap -> hot
        {"asset": "broker", "stride_letter": "T", "mitigation": "x"},
    ]
    inv = {"trust_boundaries": [
        {"name": "internet", "assets": ["api"]},
        {"name": "data-plane", "assets": ["broker"]},
    ]}
    g = _threat_surface_graph(entries, inv)
    nodes = {n["id"]: n for n in g["nodes"]}
    api = next(n for n in g["nodes"] if n.get("label", "").startswith("api"))
    assert api["type"] == "asset" and api["badge"] == "S I" and api["hot"] is True
    assert api.get("parent")  # clustered under a boundary compound node
    assert any(n["type"] == "boundary" for n in g["nodes"])

def test_threat_surface_graph_none_when_no_entries():
    from apd_gauntlet.report.transform import _threat_surface_graph
    assert _threat_surface_graph([], {"trust_boundaries": []}) is None
```

- [ ] **Step 2: Run it — expect FAIL**

Run: `.venv/bin/python -m pytest tests/unit/report/test_transform_attack_paths.py -k focused tests/unit/report/test_transform_threat_model.py -k surface_graph -v`
Expected: FAIL — functions not defined.

- [ ] **Step 3: Implement the focused + surface builders**

Add to `transform.py`:

```python
def _asset_graph_view_focused(
    asset_graph: dict[str, Any] | None, paths: list[dict[str, Any]]
) -> dict[str, Any] | None:
    """Subset of the asset graph containing only nodes/edges on enumerated paths."""
    edge_ids: set[str] = set()
    for p in paths or []:
        edge_ids.update(str(e) for e in (p.get("edges") or []))
    if not edge_ids:
        return None
    full = _asset_graph_view(asset_graph, bottleneck_ids=set())
    edges = [e for e in full["edges"] if e["id"] in edge_ids]
    keep = {e["source"] for e in edges} | {e["target"] for e in edges}
    nodes = [n for n in full["nodes"] if n["id"] in keep]
    return {"nodes": nodes, "edges": edges}


def _threat_surface_graph(
    entries: list[dict[str, Any]], asset_inventory: dict[str, Any]
) -> dict[str, Any] | None:
    """Trust-boundary surface map (block D) as structured nodes/edges. Asset nodes
    badged with STRIDE letters + `hot` on a gap, optionally nested under boundary
    compound parents. No edges fabricated (clusters only) — degrades gracefully."""
    if not entries:
        return None
    assets: dict[str, dict[str, Any]] = {}
    for e in entries:
        a = str(e.get("asset") or "—")
        rec = assets.setdefault(a, {"letters": set(), "hot": False})
        letter = e.get("stride_letter") or e.get("linddun_letter")
        if letter:
            rec["letters"].add(letter)
        if not (e.get("mitigation") or "").strip():
            rec["hot"] = True
    inv = asset_inventory if isinstance(asset_inventory, dict) else {}
    nodes: list[dict[str, Any]] = []
    boundary_ids: dict[str, str] = {}

    def _boundary_of(asset: str) -> str | None:
        for b in inv.get("trust_boundaries") or []:
            if isinstance(b, dict):
                members = b.get("assets") or b.get("members") or []
                if isinstance(members, list) and asset in members:
                    name = b.get("name") or b.get("boundary") or b.get("boundary_id")
                    return str(name) if name else None
        return None

    for a in sorted(assets):
        rec = assets[a]
        letters = " ".join(
            L for L in _STRIDE_LETTERS + _LINDDUN_LETTERS if L in rec["letters"]
        )
        node: dict[str, Any] = {
            "id": _safe_node_id(a, a), "type": "asset",
            "label": _safe_label(a), "badge": letters, "hot": rec["hot"],
        }
        boundary = _boundary_of(a)
        if boundary:
            bid = boundary_ids.get(boundary)
            if bid is None:
                bid = _safe_node_id("boundary:" + boundary, boundary)
                boundary_ids[boundary] = bid
                nodes.append({"id": bid, "type": "boundary", "label": _safe_label(boundary)})
            node["parent"] = bid
        nodes.append(node)
    return {"nodes": nodes, "edges": []}
```

- [ ] **Step 4: Wire the data fields + remove Mermaid builders**

In the attack-paths block (`transform.py` ~1528), replace:

```python
        "mermaid": _build_mermaid(artifacts.asset_graph),
        "mermaid_path_focused": _build_mermaid_path_focused(artifacts.asset_graph, paths),
```

with (compute the bottleneck set from `paths`):

```python
        "graph": _asset_graph_view(
            artifacts.asset_graph,
            bottleneck_ids={
                str(eid) for p in paths for eid in (p.get("bottleneck_edges") or [])
            },
        ),
        "graph_path_focused": _asset_graph_view_focused(artifacts.asset_graph, paths),
```

In the threat-model block (~1913), replace `"surface_mermaid": _build_threat_surface_mermaid(entries, artifacts.asset_inventory),` with:

```python
        "surface_graph": _threat_surface_graph(entries, artifacts.asset_inventory),
```

and the placeholder/fault path (~2019) `"surface_mermaid": None,` → `"surface_graph": None,`.

Delete the now-dead `_build_mermaid`, `_build_mermaid_path_focused`, and `_build_threat_surface_mermaid` functions.

- [ ] **Step 5: Update existing transform tests that referenced the mermaid fields**

Run `rg -n 'mermaid|surface_mermaid' tests/unit/report/` and update any assertions (e.g. tests checking `ap["mermaid"]`) to the new `graph`/`surface_graph` keys; delete the `test_build_threat_surface_mermaid_*` tests (superseded by `test_threat_surface_graph_*`).

- [ ] **Step 6: Run it — expect PASS**

Run: `.venv/bin/python -m pytest tests/unit/report/test_transform_attack_paths.py tests/unit/report/test_transform_threat_model.py -v`
Expected: PASS. Also `rg -n '_build_mermaid|surface_mermaid|"mermaid"' tools/apd_gauntlet/report/transform.py` → no matches.

- [ ] **Step 7: Commit**

```bash
git add tools/apd_gauntlet/report/transform.py tests/unit/report/test_transform_attack_paths.py tests/unit/report/test_transform_threat_model.py
git commit -m "feat(report): structured focused + threat-surface graphs; remove mermaid builders"
```

---

## Task 4: `GraphView` component (Cytoscape) replacing `MermaidGraph`

**Files:**
- Modify: `report-template/components.jsx`
- Modify: `report-template/screens.css`
- Test: `tests/test_workflow_apd_gauntlet.py`

- [ ] **Step 1: Write the failing contract tests** (replace the #78 MermaidGraph tests)

In `tests/test_workflow_apd_gauntlet.py`, delete `test_mermaid_graph_is_shared_component` and `test_attack_paths_uses_shared_mermaid_graph`, and add:

```python
def test_graph_view_is_shared_cytoscape_component() -> None:
    comp = (REPO / "report-template" / "components.jsx").read_text(encoding="utf-8")
    assert "function GraphView(" in comp
    assert "window.cytoscape" in comp
    assert "dagre" in comp and "fcose" in comp           # both layouts supported
    assert "getComputedStyle" in comp                    # token-derived theming
    assert "data-theme" in comp or "MutationObserver" in comp  # re-style on theme change
    assert "GraphView" in comp.split("Object.assign(window")[1]  # exported
    assert "MermaidGraph" not in comp                    # fully replaced
    assert "window.mermaid" not in comp
```

- [ ] **Step 2: Run it — expect FAIL**

Run: `.venv/bin/python -m pytest tests/test_workflow_apd_gauntlet.py::test_graph_view_is_shared_cytoscape_component -v`
Expected: FAIL — `GraphView` not defined.

- [ ] **Step 3: Replace `MermaidGraph` with `GraphView` in `components.jsx`**

Delete the `MermaidGraph` function (and the `GRAPH_ZOOM_*` consts if only it used them; keep them — `GraphView` reuses them) and insert:

```jsx
// ── Shared graph renderer (Cytoscape) — asset graph + threat-model surface map ──
function _cssVar(name, fallback) {
  const v = getComputedStyle(document.body).getPropertyValue(name).trim();
  return v || fallback;
}

function _graphStylesheet() {
  const ink = _cssVar("--ink", "#1a1a1a");
  const ink3 = _cssVar("--ink-3", "#888");
  const paper = _cssVar("--paper", "#fff");
  const paper2 = _cssVar("--paper-2", "#f4f4f4");
  const rule = _cssVar("--rule", "#ddd");
  const accent = _cssVar("--accent", "#3b6cb7");
  const sevHigh = _cssVar("--sev-high", "#c0392b");
  const sevLow = _cssVar("--sev-low", "#3a7d54");
  return [
    { selector: "node", style: {
        "background-color": paper2, "border-color": rule, "border-width": 1,
        "label": "data(label)", "color": ink, "font-size": 10, "text-wrap": "wrap",
        "text-max-width": 120, "text-valign": "center", "text-halign": "center",
        "padding": "6px", "shape": "round-rectangle", "width": "label", "height": "label" } },
    { selector: 'node[type="attacker"]', style: { "shape": "diamond", "border-color": sevHigh, "border-width": 2 } },
    { selector: 'node[type="crown_jewel"]', style: { "shape": "hexagon", "border-color": accent, "border-width": 2, "background-color": paper } },
    { selector: 'node[type="identity"]', style: { "shape": "round-tag" } },
    { selector: 'node[?hot]', style: { "border-color": sevHigh, "background-color": "color-mix(in srgb, " + sevHigh + " 14%, " + paper + ")" } },
    { selector: 'node[type="boundary"]', style: { "background-color": paper, "background-opacity": 0.04, "border-style": "dashed", "border-color": ink3, "label": "data(label)", "text-valign": "top", "text-halign": "center", "font-size": 9, "color": ink3, "shape": "round-rectangle" } },
    { selector: "edge", style: {
        "width": 1.4, "line-color": rule, "target-arrow-color": rule,
        "target-arrow-shape": "triangle", "curve-style": "bezier", "arrow-scale": 0.8 } },
    { selector: 'edge[?bottleneck]', style: { "width": 3, "line-color": sevHigh, "target-arrow-color": sevHigh } },
    { selector: 'edge[type="trust_boundary"]', style: { "line-style": "dashed", "line-color": ink3, "target-arrow-color": ink3 } },
    { selector: 'edge[type="mitigated_by_capability"]', style: { "line-color": sevLow, "target-arrow-color": sevLow } },
    { selector: ".dim", style: { "opacity": 0.15 } },
    { selector: ".hl", style: { "opacity": 1, "z-index": 99 } },
    { selector: 'edge.hl', style: { "width": 3, "line-color": accent, "target-arrow-color": accent } },
    { selector: 'node.hl', style: { "border-color": accent, "border-width": 3 } },
  ];
}

function GraphView({ graph, layout = "dagre", idBase, paths = null, selectedPathId = null, onSelectPath = null, compound = false }) {
  const ref = React.useRef(null);
  const cyRef = React.useRef(null);
  const tipRef = React.useRef(null);

  function buildElements(g) {
    const els = [];
    (g.nodes || []).forEach((n) => {
      const data = { id: n.id, label: n.badge ? `${n.label} [${n.badge}]` : n.label, type: n.type };
      if (n.parent) data.parent = n.parent;
      if (n.hot) data.hot = true;
      if (n.provenance) data._prov = n.provenance;
      els.push({ data });
    });
    (g.edges || []).forEach((e) => {
      els.push({ data: { id: e.id, source: e.source, target: e.target, type: e.type,
        bottleneck: e.bottleneck || undefined, finding_id: e.finding_id, capability_id: e.capability_id } });
    });
    return els;
  }

  function layoutOpts() {
    if (layout === "fcose") return { name: "fcose", animate: false, quality: "default", nodeSeparation: 80, padding: 20 };
    return { name: "dagre", rankDir: "TB", nodeSep: 28, rankSep: 48, padding: 20 };
  }

  // Build / rebuild the graph when data changes.
  React.useEffect(() => {
    if (!graph || !(graph.nodes || []).length || !window.cytoscape || !ref.current) return;
    const cy = window.cytoscape({
      container: ref.current, elements: buildElements(graph),
      style: _graphStylesheet(), layout: layoutOpts(),
      wheelSensitivity: 0.2, boxSelectionEnabled: false, autoungrabify: false,
    });
    cyRef.current = cy;

    // Hover tooltip (text only — no HTML from data).
    const tip = tipRef.current;
    cy.on("mouseover", "node", (ev) => {
      const d = ev.target.data();
      const prov = d._prov ? ` · ${d._prov.artifact || ""}${d._prov.locator ? " " + d._prov.locator : ""}` : "";
      tip.textContent = `${d.label} (${d.type})${prov}`; tip.style.display = "block";
    });
    cy.on("mouseover", "edge", (ev) => {
      const d = ev.target.data();
      const ref2 = d.finding_id || d.capability_id ? ` · ${d.finding_id || d.capability_id}` : "";
      tip.textContent = `${d.type}${ref2}`; tip.style.display = "block";
    });
    cy.on("mousemove", (ev) => {
      if (tip.style.display === "block" && ev.renderedPosition) {
        tip.style.left = ev.renderedPosition.x + 12 + "px";
        tip.style.top = ev.renderedPosition.y + 12 + "px";
      }
    });
    cy.on("mouseout", "node, edge", () => { tip.style.display = "none"; });

    // Click-to-highlight.
    cy.on("tap", "node", (ev) => {
      const nodeId = ev.target.id();
      if (paths && onSelectPath) {
        // pick the first path whose edges touch this node
        const hit = paths.find((p) => (p.edgeIds || []).some((eid) => {
          const e = cy.getElementById(eid);
          return e.nonempty() && (e.source().id() === nodeId || e.target().id() === nodeId);
        }));
        onSelectPath(hit ? hit.id : null);
        if (!hit) highlightNeighborhood(cy, ev.target);
      } else {
        highlightNeighborhood(cy, ev.target);
      }
    });
    cy.on("tap", (ev) => { if (ev.target === cy) { clearHighlight(cy); if (onSelectPath) onSelectPath(null); } });

    return () => { cy.destroy(); cyRef.current = null; };
  }, [graph, layout, compound, idBase]);

  // Controlled path highlight (list ↔ graph cross-link).
  React.useEffect(() => {
    const cy = cyRef.current; if (!cy || !paths) return;
    if (!selectedPathId) { clearHighlight(cy); return; }
    const p = paths.find((x) => x.id === selectedPathId); if (!p) { clearHighlight(cy); return; }
    const edges = cy.collection();
    (p.edgeIds || []).forEach((eid) => { const e = cy.getElementById(eid); if (e.nonempty()) edges.merge(e); });
    const hl = edges.union(edges.connectedNodes());
    cy.elements().addClass("dim").removeClass("hl");
    hl.removeClass("dim").addClass("hl");
  }, [selectedPathId, paths]);

  // Re-style on theme change.
  React.useEffect(() => {
    const obs = new MutationObserver(() => { if (cyRef.current) cyRef.current.style(_graphStylesheet()); });
    obs.observe(document.body, { attributes: true, attributeFilter: ["data-theme", "data-sev"] });
    return () => obs.disconnect();
  }, []);

  function highlightNeighborhood(cy, node) {
    const hood = node.closedNeighborhood();
    cy.elements().addClass("dim").removeClass("hl");
    hood.removeClass("dim").addClass("hl");
  }
  function clearHighlight(cy) { cy.elements().removeClass("dim").removeClass("hl"); }

  if (!graph || !(graph.nodes || []).length) {
    return <div className="empty-state empty-state--info">No graph data for this run.</div>;
  }
  return (
    <div className="report-graph__wrapper" style={{ position: "relative" }}>
      <div className="report-graph__toolbar">
        <button onClick={() => cyRef.current && cyRef.current.zoom(cyRef.current.zoom() * 0.8)} title="Zoom out">−</button>
        <button onClick={() => cyRef.current && cyRef.current.zoom(cyRef.current.zoom() * 1.25)} title="Zoom in">+</button>
        <button onClick={() => cyRef.current && cyRef.current.fit(undefined, 24)} title="Fit">fit</button>
      </div>
      <div ref={ref} className="report-graph__canvas" />
      <div ref={tipRef} className="report-graph__tooltip" style={{ display: "none" }} />
    </div>
  );
}
```

In the `Object.assign(window, { … })` block, replace `MermaidGraph,` with `GraphView,`.

- [ ] **Step 4: Update `screens.css`**

Remove the `.report-graph__canvas svg …` / mermaid-specific rules. Ensure the canvas has a height and add the tooltip:

```css
.report-graph__canvas { width: 100%; height: 520px; background: var(--paper); }
.report-graph__tooltip {
  position: absolute; pointer-events: none; z-index: 50;
  background: var(--ink); color: var(--paper); font-size: 11px;
  font-family: var(--font-mono); padding: 2px 6px; border-radius: 3px; max-width: 280px;
}
```

- [ ] **Step 5: Run it — expect PASS**

Run: `.venv/bin/python -m pytest tests/test_workflow_apd_gauntlet.py::test_graph_view_is_shared_cytoscape_component -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add report-template/components.jsx report-template/screens.css tests/test_workflow_apd_gauntlet.py
git commit -m "feat(report): GraphView (Cytoscape) replaces MermaidGraph; token theming + tooltip + highlight"
```

---

## Task 5: AttackPaths screen — GraphView + click-to-highlight-paths + list↔graph cross-link

**Files:**
- Modify: `report-template/screens/AttackPaths.jsx`
- Test: `tests/test_workflow_apd_gauntlet.py`

- [ ] **Step 1: Write the failing contract test**

```python
def test_attack_paths_uses_graphview_with_path_selection() -> None:
    ap = (REPO / "report-template" / "screens" / "AttackPaths.jsx").read_text(encoding="utf-8")
    assert "GraphView" in ap and "MermaidGraph" not in ap
    assert "ap.graph" in ap and "ap.graph_path_focused" in ap
    assert "selectedPathId" in ap and "onSelectPath" in ap
    # derives a flat paths list (id + edgeIds) for highlighting
    assert "edgeIds" in ap and "path_id" in ap
```

- [ ] **Step 2: Run it — expect FAIL**

Run: `.venv/bin/python -m pytest tests/test_workflow_apd_gauntlet.py::test_attack_paths_uses_graphview_with_path_selection -v`
Expected: FAIL.

- [ ] **Step 3: Wire AttackPaths**

In `AttackPaths.jsx`: add selection state at the top of the component:

```jsx
  const [selectedPathId, setSelectedPathId] = React.useState(null);
  const paths = (ap.pairs || []).flatMap((pair) =>
    (pair.paths || []).map((p) => ({ id: p.path_id, edgeIds: p.edges || [] })));
```

Replace the asset-graph render (`<MermaidGraph source={ap.mermaid} idBase="apd-asset-graph" />`) with:

```jsx
        <GraphView graph={ap.graph} layout="dagre" idBase="apd-asset-graph"
          paths={paths} selectedPathId={selectedPathId} onSelectPath={setSelectedPathId} />
```

Replace the focused block (`{ap.mermaid_path_focused && (… <MermaidGraph … canvasModifier="focused" /> …)}`) with:

```jsx
      {ap.graph_path_focused && (
        <section className="attack-paths__graph">
          <h3 className="attack-paths__section-h">Path-focused graph</h3>
          <GraphView graph={ap.graph_path_focused} layout="dagre" idBase="apd-paths-focused" />
        </section>
      )}
```

Make each enumerated-path row clickable to drive the highlight. On the `<li className={`attack-path …`}>` (keyed by `p.path_id`), add:

```jsx
                  onClick={() => setSelectedPathId(
                    (cur) => cur === p.path_id ? null : p.path_id)}
                  style={{ cursor: "pointer", outline: selectedPathId === p.path_id
                    ? "2px solid var(--accent)" : "none" }}
```

- [ ] **Step 4: Run it — expect PASS**

Run: `.venv/bin/python -m pytest tests/test_workflow_apd_gauntlet.py::test_attack_paths_uses_graphview_with_path_selection -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add report-template/screens/AttackPaths.jsx tests/test_workflow_apd_gauntlet.py
git commit -m "feat(report): Attack-paths uses GraphView with click-to-highlight + list cross-link"
```

---

## Task 6: ThreatModel screen — GraphView surface map

**Files:**
- Modify: `report-template/screens/ThreatModel.jsx`
- Test: `tests/test_workflow_apd_gauntlet.py`

- [ ] **Step 1: Write the failing contract test**

```python
def test_threat_model_uses_graphview_surface_map() -> None:
    tm = (REPO / "report-template" / "screens" / "ThreatModel.jsx").read_text(encoding="utf-8")
    assert "GraphView" in tm and "MermaidGraph" not in tm
    assert "surface_graph" in tm and "surface_mermaid" not in tm
    assert "compound" in tm and 'layout="fcose"' in tm
```

- [ ] **Step 2: Run it — expect FAIL**

Run: `.venv/bin/python -m pytest tests/test_workflow_apd_gauntlet.py::test_threat_model_uses_graphview_surface_map -v`
Expected: FAIL.

- [ ] **Step 3: Wire ThreatModel**

Replace the block-D render:

```jsx
      {tm.surface_mermaid && (
        <section>
          <div className="section-eyebrow" style={{ marginTop: "var(--space-5)" }}>D — Surface map</div>
          <MermaidGraph source={tm.surface_mermaid} idBase="apd-tm-surface" />
        </section>
      )}
```

with:

```jsx
      {tm.surface_graph && (
        <section>
          <div className="section-eyebrow" style={{ marginTop: "var(--space-5)" }}>D — Surface map</div>
          <GraphView graph={tm.surface_graph} layout="fcose" idBase="apd-tm-surface" compound />
        </section>
      )}
```

- [ ] **Step 4: Run it — expect PASS**

Run: `.venv/bin/python -m pytest tests/test_workflow_apd_gauntlet.py::test_threat_model_uses_graphview_surface_map -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add report-template/screens/ThreatModel.jsx tests/test_workflow_apd_gauntlet.py
git commit -m "feat(report): Threat-model surface map uses GraphView (fcose compound)"
```

---

## Task 7: Audit graph assertion + no-Mermaid grep guard

**Files:**
- Modify: `tools/apd_gauntlet/synthesis/audit.py`
- Test: `tests/test_cli_audit_report.py`, `tests/test_workflow_apd_gauntlet.py`

- [ ] **Step 1: Write the failing tests**

In `test_cli_audit_report.py`:

```python
def test_attack_paths_present_checks_structured_graph(tmp_path):
    dst = _copy_example(tmp_path)
    result = audit_report(dst)
    c = [x for x in result.checks if x["name"] == "attack_paths_present"][0]
    assert c["status"] == "pass"
    assert "graph_nodes=" in c["detail"]   # detail now reports structured graph size
```

In `test_workflow_apd_gauntlet.py`:

```python
def test_no_mermaid_references_remain() -> None:
    import subprocess
    out = subprocess.run(
        ["git", "grep", "-il", "mermaid", "--", "report-template", "tools"],
        cwd=REPO, capture_output=True, text=True).stdout
    assert out.strip() == "", f"residual mermaid references:\n{out}"
```

- [ ] **Step 2: Run it — expect FAIL**

Run: `.venv/bin/python -m pytest tests/test_cli_audit_report.py -k attack_paths_present_checks_structured_graph tests/test_workflow_apd_gauntlet.py -k no_mermaid -v`
Expected: FAIL (`graph_nodes=` not in detail; mermaid grep may still match comments).

- [ ] **Step 3: Implement the audit detail**

In `audit.py` `attack_paths_present` final `_check` (the `else` branch around line 268), incorporate the structured graph count. Replace the detail string to include `graph_nodes`:

```python
        graph = ap.get("graph") if isinstance(ap.get("graph"), dict) else {}
        graph_nodes = len(graph.get("nodes") or [])
        ap_ok = ap_ok and (node_count == 0 or graph_nodes > 0)
        _check(result, "attack_paths_present", ap_ok,
               f"node_count={node_count} graph_nodes={graph_nodes} "
               f"total_paths={total_paths} apath_blocked={apath_blocked}",
               klass="structural")
```

- [ ] **Step 4: Scrub residual mermaid mentions**

Run `git grep -il mermaid -- report-template tools` and remove/replace each remaining reference (e.g. comment headers in `AttackPaths.jsx`, `entry.jsx` comment about `window.mermaid`, any leftover docstring). Update `entry.jsx`'s comment to mention `window.cytoscape`.

- [ ] **Step 5: Run it — expect PASS**

Run: `.venv/bin/python -m pytest tests/test_cli_audit_report.py -k attack_paths_present_checks_structured_graph tests/test_workflow_apd_gauntlet.py -k no_mermaid -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add tools/apd_gauntlet/synthesis/audit.py report-template/ tests/test_cli_audit_report.py tests/test_workflow_apd_gauntlet.py
git commit -m "feat(audit): attack_paths_present asserts structured graph; scrub residual mermaid refs"
```

---

## Task 8: Rebuild bundle + regenerate golden/demo/example + full verification

**Files (generated):** `tools/apd_gauntlet/data/report-template/{app.js,.source-hash,vendor-licenses.txt}` (mermaid.min.js removed), `report-template/data.js`, `tests/fixtures/report-html/claim-event-bus-golden-data.js`, `examples/apd-20260601-claim-event-bus/expected/40-synthesis/report-html/`.

- [ ] **Step 1: Install the new deps + rebuild the bundle**

```bash
( cd report-template/.build && npm install )
.venv/bin/python tools/build_report_template.py
```

Expected: `build-report-template: bundle written.` Confirm `tools/apd_gauntlet/data/report-template/mermaid.min.js` is gone and `app.js` shrank substantially:

```bash
ls -la tools/apd_gauntlet/data/report-template/ | rg 'app.js|mermaid'
```

- [ ] **Step 2: Freshness gate**

Run: `.venv/bin/python tools/check_report_template_freshness.py`
Expected: `OK`.

- [ ] **Step 3: Regenerate golden + dev demo + the example's committed report-html**

```bash
EX=examples/apd-20260601-claim-event-bus/expected
.venv/bin/apd-gauntlet build-report "$EX" --out /tmp/cg && cp /tmp/cg/data.js tests/fixtures/report-html/claim-event-bus-golden-data.js && cp /tmp/cg/data.js report-template/data.js
.venv/bin/apd-gauntlet build-report "$EX"   # regenerate the example's committed report-html in place
.venv/bin/python tools/build_report_template.py && .venv/bin/python tools/check_report_template_freshness.py
```

- [ ] **Step 4: Confirm data.js carries graphs, not mermaid**

```bash
rg -c 'surface_mermaid|"mermaid"' tests/fixtures/report-html/claim-event-bus-golden-data.js || echo "no mermaid in golden ✓"
.venv/bin/python -c "import re,json; d=json.loads(re.search(r'window.APD_DATA\s*=\s*(\{.*\});?\s*\$', open('/tmp/cg/data.js').read(), re.S).group(1)); ap=d['attack_paths']; print('graph nodes:', len(ap['graph']['nodes']), 'edges:', len(ap['graph']['edges'])); print('tm surface_graph nodes:', len((d['threat_model'].get('surface_graph') or {}).get('nodes', [])))"
```

Expected: no mermaid; non-zero graph node/edge counts.

- [ ] **Step 5: Lint + full suite**

Run: `.venv/bin/ruff check tools/ tests/ && .venv/bin/python -m mypy tools/ && .venv/bin/python -m pytest -q`
Expected: ruff clean, mypy clean, all tests pass.

- [ ] **Step 6: Manual visual check**

```bash
.venv/bin/apd-gauntlet build-report examples/apd-20260601-claim-event-bus/expected --out /tmp/cg-view && open /tmp/cg-view/index.html
```

Confirm: Attack-paths + Threat-model tabs render Cytoscape graphs; pan/zoom/drag/fit; hover tooltips show provenance; **clicking a node highlights its path(s)** and clicking an "Enumerated paths" row cross-highlights the graph; theme switch (light/paper/dark) recolors the graph.

- [ ] **Step 7: Commit**

```bash
git add tools/apd_gauntlet/data/report-template/ report-template/data.js tests/fixtures/report-html/claim-event-bus-golden-data.js examples/apd-20260601-claim-event-bus/expected/40-synthesis/report-html/
git commit -m "build(report): rebuild Cytoscape bundle + regenerate golden/demo/example report-html"
```

---

## Task 9: Docs + CHANGELOG

**Files:** `docs/html-report.md`, `CHANGELOG.md`

- [ ] **Step 1: Update docs**

In `docs/html-report.md`, update the Attack-paths + Threat-model entries to describe the interactive Cytoscape graphs (pan/zoom/drag, hover provenance, click-to-highlight-paths, list↔graph cross-link) and that Mermaid was removed.

- [ ] **Step 2: CHANGELOG**

Under `## [Unreleased]` → `### Changed`:

```markdown
- **Report graphs are now interactive (Cytoscape.js).** The Attack-paths asset graph and the Threat-model surface map render with Cytoscape (dagre/fcose layouts) instead of static Mermaid — pan/zoom/drag, hover tooltips with provenance, and click-to-highlight-paths with two-way Attack-paths list↔graph cross-highlight. Mermaid was removed from the bundle (smaller `app.js`); the report stays self-contained/offline.
```

- [ ] **Step 3: Lint docs**

Run: `npx --yes markdownlint-cli2 "docs/html-report.md" "CHANGELOG.md"`
Expected: `0 error(s)`.

- [ ] **Step 4: Commit**

```bash
git add docs/html-report.md CHANGELOG.md
git commit -m "docs: interactive Cytoscape report graphs"
```

---

## Self-Review

- **Spec coverage:** vendoring/globals (T1) · asset graph view (T2) · focused + surface graph + remove mermaid builders (T3) · GraphView w/ theming+tooltip+highlight (T4) · AttackPaths click-to-highlight + list cross-link (T5) · ThreatModel surface map (T6) · audit graph assertion + no-mermaid guard (T7) · bundle/golden/example regen + app.js-shrank (T8) · docs (T9). All spec sections mapped.
- **Type consistency:** `data.attack_paths.graph` / `graph_path_focused` and `data.threat_model.surface_graph` are produced in T2–T3 and consumed in T5–T6; node/edge keys (`id,type,label,parent,badge,hot,provenance` / `id,type,source,target,bottleneck`) match between transform output and `GraphView.buildElements`; `GraphView` prop names (`graph,layout,idBase,paths,selectedPathId,onSelectPath,compound`) are identical at definition (T4) and call sites (T5–T6).
- **Placeholders:** none — every step has concrete code/commands.

## Execution handoff

Branch `feat/cytoscape-graph-renderer` (off post-#78 main; spec committed). Implement task-by-task.
