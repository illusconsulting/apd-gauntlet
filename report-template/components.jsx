/* eslint-disable */
// Shared atoms for the APD report interface.

const { useState, useEffect, useRef, useMemo, useCallback } = React;

// ────────────────────────────────────────────────────────────────────────
// Severity / disposition / maturity primitives
// ────────────────────────────────────────────────────────────────────────
function SeverityPill({ value }) {
  if (!value) return null;
  return <span className={`sev sev--${value}`}>{value}</span>;
}

function DispositionMark({ value }) {
  if (!value) return null;
  return (
    <span className={`disposition disposition--${value}`}>
      <span className="disposition__sigil" />
      {value}
    </span>
  );
}

function MaturityMark({ value }) {
  if (!value) return null;
  return <span className={`maturity maturity--${value}`}>{value}</span>;
}

// ────────────────────────────────────────────────────────────────────────
// Copyable ID pill
// ────────────────────────────────────────────────────────────────────────
function CopyPill({ value, label, modifier = "" }) {
  const [copied, setCopied] = useState(false);
  const onClick = (e) => {
    e.stopPropagation();
    navigator.clipboard?.writeText(value);
    setCopied(true);
    window.dispatchEvent(new CustomEvent("apd:toast", { detail: `Copied ${value}` }));
    setTimeout(() => setCopied(false), 800);
  };
  return (
    <span
      className={`pill pill--id pill--copy ${modifier}`}
      onClick={onClick}
      title={`Copy ${value}`}
    >
      {label || value} {copied ? "✓" : ""}
    </span>
  );
}

// ────────────────────────────────────────────────────────────────────────
// Taxonomy tag with hover tooltip
// ────────────────────────────────────────────────────────────────────────
function TaxonomyTag({ id }) {
  const [hover, setHover] = useState(false);
  const [pos, setPos] = useState({ x: 0, y: 0 });
  const entry = window.APD_DATA.taxonomy[id];
  const ref = useRef(null);

  const onEnter = () => {
    if (!ref.current) return;
    const r = ref.current.getBoundingClientRect();
    setPos({ x: r.left, y: r.bottom + 6 });
    setHover(true);
  };
  // When the taxonomy entry carries an authoritative URL (ATT&CK techniques/
  // sub-techniques and D3FEND techniques — computed server-side in transform.py),
  // the tag becomes a link that opens that specific page in a new tab.
  const url = entry && entry.url;
  const tooltip = hover && entry && (
    <span
      className="tag-tooltip"
      style={{ left: pos.x + "px", top: pos.y + "px" }}
    >
      <span className="tag-tooltip__family">{entry.family}</span>
      {entry.title}
    </span>
  );
  if (url) {
    return (
      <a
        ref={ref}
        className="tag tag--link"
        href={url}
        target="_blank"
        rel="noopener noreferrer"
        title={`Open ${id} on the authoritative site`}
        style={{ cursor: "pointer", color: "inherit", textDecoration: "none" }}
        onClick={(e) => e.stopPropagation()}
        onMouseEnter={onEnter}
        onMouseLeave={() => setHover(false)}
      >
        {id}
        {tooltip}
      </a>
    );
  }
  return (
    <span
      ref={ref}
      className="tag"
      onMouseEnter={onEnter}
      onMouseLeave={() => setHover(false)}
    >
      {id}
      {tooltip}
    </span>
  );
}

function TagRow({ ids = [] }) {
  if (!ids.length) return <span style={{ color: "var(--ink-3)", fontSize: "var(--text-xs)" }}>—</span>;
  return (
    <div className="tagrow">
      {ids.map((id) => <TaxonomyTag key={id} id={id} />)}
    </div>
  );
}

// ────────────────────────────────────────────────────────────────────────
// Toast host
// ────────────────────────────────────────────────────────────────────────
function ToastHost() {
  const [toasts, setToasts] = useState([]);
  useEffect(() => {
    const onToast = (e) => {
      const id = Math.random().toString(36).slice(2);
      setToasts((t) => [...t, { id, text: e.detail }]);
      setTimeout(() => setToasts((t) => t.filter((x) => x.id !== id)), 1600);
    };
    window.addEventListener("apd:toast", onToast);
    return () => window.removeEventListener("apd:toast", onToast);
  }, []);
  return toasts.map((t) => (
    <div key={t.id} className="copy-toast">{t.text}</div>
  ));
}

// Diagnostics banner — surfaces build-time signals the Python layer records on
// data.meta but no screen otherwise shows: empty-run, per-section build errors,
// soft warnings, and stale/empty reference catalogs. Renders nothing when clean.
function DiagnosticsBanner({ data }) {
  const meta = (data && data.meta) || {};
  const items = [];

  if (meta.is_empty_run) {
    items.push({
      kind: "empty",
      label: "Empty run",
      text: "This run produced no findings or capabilities. See advisory-report.md for the run summary.",
    });
  }

  const failed = Object.keys(meta.section_errors || {});
  if (failed.length) {
    items.push({
      kind: "error",
      label: "Section error",
      text: `Some report sections could not be built and are shown empty: ${failed.join(", ")}.`,
    });
  }

  const warnings = meta.warnings || [];
  if (warnings.length) {
    const msgs = warnings
      .map((w) => (typeof w === "string" ? w : (w && (w.message || w.detail)) || ""))
      .filter(Boolean);
    const preview = msgs.length ? `: ${msgs.slice(0, 3).join("; ")}${msgs.length > 3 ? "…" : ""}` : "";
    items.push({
      kind: "warn",
      label: "Notice",
      text: `${warnings.length} soft warning${warnings.length === 1 ? "" : "s"} during report build${preview}.`,
    });
  }

  const refs = meta.reference_db_versions || {};
  const STALE_DAYS = 180;
  const now = Date.now();
  const stale = [];
  Object.keys(refs).forEach((fam) => {
    const r = refs[fam] || {};
    if (r.count === 0) { stale.push(`${fam} (empty)`); return; }
    if (r.fetched_at) {
      const t = Date.parse(r.fetched_at);
      if (!isNaN(t) && (now - t) / 86400000 > STALE_DAYS) stale.push(`${fam} (${r.fetched_at})`);
    }
  });
  if (stale.length) {
    items.push({
      kind: "warn",
      label: "Notice",
      text: `Reference catalogs may be stale (>${STALE_DAYS}d) or empty: ${stale.join(", ")}. Re-run the refresh-* commands to update.`,
    });
  }

  if (!items.length) return null;
  return (
    <div className="diagnostics">
      {items.map((it, i) => (
        <div key={i} className={`diagnostics__item diagnostics__item--${it.kind}`}>
          <span className="diagnostics__tag">{it.label}</span>
          <span>{it.text}</span>
        </div>
      ))}
    </div>
  );
}

// Goal labels
const GOAL_LABELS = {
  confidentiality: "Confidentiality",
  integrity: "Integrity",
  availability: "Availability",
  distributed: "Distributed",
  resilient: "Resilient",
  ephemeral: "Ephemeral",
  authenticity: "Authenticity",
  non_repudiation: "Non-Repudiation",
  immutability: "Immutability",
};
const GOAL_SHORT = {
  confidentiality: "Conf",
  integrity: "Intg",
  availability: "Avail",
  distributed: "Dist",
  resilient: "Resil",
  ephemeral: "Ephem",
  authenticity: "Auth",
  non_repudiation: "NonRep",
  immutability: "Immut",
};
const TIER_LABELS = {
  trustworthiness: "Trustworthiness",
  scalability: "Scalability",
  auditability: "Auditability",
};
const TIER_GOALS = {
  trustworthiness: ["confidentiality", "integrity", "availability"],
  scalability: ["distributed", "resilient", "ephemeral"],
  auditability: ["authenticity", "non_repudiation", "immutability"],
};

// ── Shared graph renderer (Cytoscape) — asset graph + threat-model surface map ──
// One self-contained component: renders structured `{nodes, edges}` data keyed by
// `idBase` with dagre (layered) or fcose (compound) layout, a zoom/fit toolbar,
// pan/zoom/drag, hover tooltips (canvas text only — never HTML from adopter data),
// and click-to-highlight (path selection in AttackPaths, neighborhood otherwise).
// All node/edge colors are read from the report CSS tokens via getComputedStyle
// so the graph recolors when the theme changes (MutationObserver on document.body).
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
    // C4 node-kind cues (additive — only fire on nodes carrying data(kind),
    // i.e. the C4 scene; AttackPaths/ThreatModel nodes have no `kind`). A
    // data_store reads as a barrel; an external_system as a dashed cut-corner.
    { selector: 'node[kind="data_store"]', style: { "shape": "barrel", "border-color": accent } },
    { selector: 'node[kind="external_system"]', style: { "shape": "cut-rectangle", "border-style": "dashed", "border-color": ink3 } },
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

// ── C4 deterministic backbone layout (gap-fix 3 — data-driven, replaces the ──
// prototype's hand-curated BACKBONE position map). Partitions CONTAINER nodes
// into connected (in any edge), analyzed (no edge, analysis_state!=="not_analyzed"),
// infra (not_analyzed); assigns the connected subgraph to layered left→right
// columns (longest-path layering; cycles broken by first-seen / N-1 column cap),
// stable-sorts within a column by label, and returns logical {col,row} AND the
// derived pixel positions (x = col*COL_W, y = row*ROW_H) the renderer absolute-
// positions the boxes from. Fully deterministic (no randomness, stable sorts) per
// the framework's determinism contract. Pure: consumes the REAL c4_model shape.
const C4_COL_W = 360, C4_ROW_H = 150;
function c4BackboneLayout(nodes, edges) {
  const containers = (nodes || []).filter(function (n) { return n && n.type === "container"; });
  const byId = {};
  containers.forEach(function (n) { byId[n.id] = n; });
  const lbl = function (id) { return byId[id].label || id; };

  // 1. partition. connected = appears as either endpoint of an edge whose BOTH
  //    ends are containers we know (self-edges + ghost endpoints ignored —
  //    never an invented endpoint).
  const sub = [];
  const endpoints = {};
  (edges || []).forEach(function (e) {
    if (e && byId[e.source] && byId[e.target] && e.source !== e.target) {
      sub.push(e);
      endpoints[e.source] = true;
      endpoints[e.target] = true;
    }
  });
  const connectedIds = containers.filter(function (n) { return endpoints[n.id]; }).map(function (n) { return n.id; });
  const connSet = {};
  connectedIds.forEach(function (id) { connSet[id] = true; });
  const analyzed = containers.filter(function (n) {
    return !connSet[n.id] && n.analysis_state !== "not_analyzed";
  }).map(function (n) { return n.id; }).sort(function (a, b) { return lbl(a).localeCompare(lbl(b)); });
  const infra = containers.filter(function (n) {
    return !connSet[n.id] && n.analysis_state === "not_analyzed";
  }).map(function (n) { return n.id; }).sort(function (a, b) { return lbl(a).localeCompare(lbl(b)); });

  // 2. layered longest-path columns over the connected subgraph.
  const col = {};
  connectedIds.forEach(function (id) { col[id] = 0; }); // col 0 = no incoming (and default)
  // Relax to longest path. Iterate edges in a STABLE order; bounded by node
  // count (longest simple path can't exceed N-1, so a cycle can't inflate
  // columns past the bound and the pass loop terminates cleanly).
  const orderedEdges = sub.filter(function (e) {
    return connSet[e.source] && connSet[e.target];
  }).slice().sort(function (a, b) {
    const ka = a.source + "|" + a.target, kb = b.source + "|" + b.target;
    return ka < kb ? -1 : ka > kb ? 1 : 0;
  });
  const maxPasses = connectedIds.length + 1;
  for (let pass = 0; pass < maxPasses; pass++) {
    let changed = false;
    for (let i = 0; i < orderedEdges.length; i++) {
      const e = orderedEdges[i];
      const want = col[e.source] + 1;
      // cap at N-1 so a cycle can't inflate columns past the bound
      if (want <= connectedIds.length - 1 && col[e.target] < want) {
        col[e.target] = want;
        changed = true;
      }
    }
    if (!changed) break;
  }

  // 2b. Pull each SOURCE (in-degree 0 in the connected subgraph) rightward to
  //     (min target column − 1). Longest-path layering parks every source at
  //     col 0, so a source's edge to a non-adjacent target becomes a column-SKIP
  //     that crosses the intervening column's fan-out (e.g. iOS Companion at col 0
  //     reaching Core at col 2 straight through the Supervisor hub). Seating the
  //     source next to its nearest target removes the skip. Deterministic and a
  //     no-op unless the source actually skips a column; it never changes a
  //     downstream node's column because that column is already the longest path
  //     (>= the pulled source's new column + 1).
  const indeg = {};
  connectedIds.forEach(function (id) { indeg[id] = 0; });
  orderedEdges.forEach(function (e) { indeg[e.target] = (indeg[e.target] || 0) + 1; });
  connectedIds.forEach(function (id) {
    if (indeg[id] !== 0) return;
    const targetCols = orderedEdges
      .filter(function (e) { return e.source === id; })
      .map(function (e) { return col[e.target]; });
    if (!targetCols.length) return;
    const want = Math.min.apply(null, targetCols) - 1;
    if (want > col[id]) col[id] = want;
  });

  // 3. group by column; stable-sort within column: label asc, badge desc, id asc.
  //    Assign a row index + deterministic pixel positions (x = col*COL_W,
  //    y = row*ROW_H) so the renderer can absolute-position the boxes.
  const cmpInCol = function (a, b) {
    const la = lbl(a), lbB = lbl(b);
    const c = la.localeCompare(lbB);
    if (c !== 0) return c;
    const ba = byId[a].badge || 0, bb = byId[b].badge || 0;
    if (ba !== bb) return bb - ba; // foreground hot nodes
    return a < b ? -1 : a > b ? 1 : 0;
  };
  const cols = {};
  connectedIds.forEach(function (id) {
    const c = col[id];
    (cols[c] = cols[c] || []).push(id);
  });
  const connected = [];
  Object.keys(cols).map(Number).sort(function (a, b) { return a - b; }).forEach(function (c) {
    cols[c].slice().sort(cmpInCol).forEach(function (id, row) {
      connected.push({ id: id, col: c, row: row, x: c * C4_COL_W, y: row * C4_ROW_H });
    });
  });

  return { connected: connected, analyzed: analyzed, infra: infra };
}

// c4ShortEdgeLabel: deterministic short display label for a C4 edge. Strips a
// leading CROSS_<TYPE> machine token (+ following — / - / : separators) and
// returns the first 3 meaningful words. The FULL rawLabel is kept by the caller
// for the hover tooltip. Replaces the prototype's hand-curated EDGE_SHORT map.
// Pure / deterministic (no run-dependent state); empty/nullish → "".
function c4ShortEdgeLabel(rawLabel) {
  let s = rawLabel == null ? "" : String(rawLabel);
  // strip a leading CROSS_<UPPER/_> token and any run of separator chars after it
  s = s.replace(/^\s*CROSS_[A-Z_]+\s*[—:-]*\s*/, "");
  s = s.trim();
  if (!s) return "";
  const words = s.split(/\s+/).filter(Boolean);
  return words.slice(0, 3).join(" ");
}

function GraphView({ graph, layout = "dagre", idBase, paths = null, selectedPathId = null, onSelectPath = null, onNodeTap = null, compound = false }) {
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
      // Additive C4 typing passthrough: when a node carries a `kind`
      // (data_store/external_system/service/… from the C4 model), expose it so
      // the stylesheet can cue distinctive node kinds. Guarded — callers whose
      // nodes have no `kind` (AttackPaths/ThreatModel) are entirely unaffected.
      if (n.kind) data.kind = n.kind;
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
      // Dedicated node-tap callback (C4 drill-down): report the tapped node's
      // own id so the caller can branch on its level. Additive — does NOT
      // replace the onSelectPath path-resolution contract below.
      if (onNodeTap) { onNodeTap(ev.target.id()); }
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

// ── Per-finding attack-path strip ("subway map") ──
// Renders one enumerated path for an apath risk finding: ordered stations
// (attacker → crown jewel) with edge segments colored by type, and layered
// markers — ⚠ vuln (compromisable edge), 💡 fix-at-source (highest-confidence
// compromisable edge), 🛡 D3FEND choke-point (bottleneck edge with overlay).
// Pure presentational; consumes finding.attack_path built by the transform.
function AttackPathStrip({ attackPath, onOpenPath }) {
  const ap = attackPath;
  const hops = (ap && ap.hops) || [];
  if (!ap || hops.length === 0) return null;

  const SEG = {
    compromisable_via_finding: "var(--sev-high)",
    mitigated_by_capability: "var(--sev-low)",
  };
  const nm = (n) => (n && (n.name || n.id)) || "?";

  function Station({ node, kind }) {
    const big = kind === "attacker" || kind === "jewel";
    const bg = kind === "attacker" ? "var(--sev-high)"
      : kind === "jewel" ? "var(--accent)" : "var(--ink-3)";
    const glyph = kind === "attacker" ? "🌐 " : kind === "jewel" ? "💎 " : "";
    return (
      <div className="apath-strip__station" title={node ? `${nm(node)} (${node.type})` : ""}>
        <span className="apath-strip__dot"
          style={{ background: bg, width: big ? 16 : 11, height: big ? 16 : 11 }} />
        <span className="apath-strip__name">{glyph}{nm(node)}</span>
      </div>
    );
  }

  return (
    <div className="apath-strip">
      <div className="apath-strip__head">
        <span className="apath-strip__pid mono">{ap.path_id}</span>
        <span>{ap.hop_count} hop{ap.hop_count === 1 ? "" : "s"}</span>
        <span>feasibility {ap.feasibility}</span>
        {typeof onOpenPath === "function" && (
          <button type="button" className="apath-strip__open"
            title="Open this path in the Attack Paths tab"
            onClick={() => onOpenPath(ap.path_id)}>view full graph →</button>
        )}
      </div>
      <div className="apath-strip__rail">
        <Station node={ap.attacker} kind="attacker" />
        {hops.map((h, i) => {
          const isLast = i === hops.length - 1;
          const color = SEG[h.edge_type] || "var(--rule)";
          return (
            <React.Fragment key={h.edge_id}>
              <div className="apath-strip__seg" title={`${h.edge_type} · ${h.confidence || "?"}`}>
                <div className="apath-strip__above">
                  {h.is_vuln && (
                    <span style={{ color: "var(--sev-high)" }}>
                      ⚠ vuln{h.finding_id ? ` ${h.finding_id}` : ""}
                    </span>
                  )}
                  {h.chokepoint && (
                    <span style={{ color: "var(--rec)" }}>
                      ⛓ choke{h.chokepoint.paths_traversing ? ` ·${h.chokepoint.paths_traversing}` : ""}
                    </span>
                  )}
                </div>
                <div className="apath-strip__line"
                  style={{ background: color, height: h.is_bottleneck ? 7 : 4 }} />
                <div className="apath-strip__below">
                  {h.is_fix && <span style={{ color: "var(--rec)" }}>💡 fix here</span>}
                  {h.chokepoint && (h.chokepoint.d3fend || []).length > 0 && (
                    <span style={{ color: "var(--rec)" }}>🛡 {h.chokepoint.d3fend.join(" ")}</span>
                  )}
                </div>
              </div>
              <Station node={h.to} kind={isLast ? "jewel" : "mid"} />
            </React.Fragment>
          );
        })}
      </div>
    </div>
  );
}

// ── C4 orthogonal connector router (ported VERBATIM from the design handoff) ──
// docs/superpowers/design_handoff_c4_architecture_view/README.md §204-249 and the
// prototype's anchors()/routeWaypoints()/roundedPath(). Pure functions: no React,
// no Cytoscape, no DOM globals beyond the element handed in. Anchors are measured
// from the LAYOUT box model (offsetLeft/Top/Width/Height walked up to the stage)
// so they are correct regardless of the CSS `transform: scale()` zoom on the stage.
// (c4ShortEdgeLabel — gap-fix 3, the deterministic short-label derivation — already
// ships above; it landed earlier in this milestone and is reused by C4EdgeLayer.)

// 1. layout-space rect of an element relative to the (un-scaled) `stage` element.
function c4Anchors(srcEl, tgtEl, stage) {
  const r = (el) => {
    let x = 0, y = 0, e = el;
    while (e && e !== stage) { x += e.offsetLeft; y += e.offsetTop; e = e.offsetParent; }
    return { x, y, w: el.offsetWidth, h: el.offsetHeight,
             cx: x + el.offsetWidth / 2, cy: y + el.offsetHeight / 2 };
  };
  return [r(srcEl), r(tgtEl)];
}

// 2. orthogonal waypoints: exit/enter on the side facing the target,
//    H-V-H when horizontally dominant, V-H-V otherwise.
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

// 3. polyline with rounded corners (radius ~7px). Dedupes collinear/zero-length
//    points so straight runs stay straight; returns "" for < 2 distinct points.
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

// ── C4 GLOBAL connector router (port distribution + gutter/lane routing) ─────
// The legacy c4RouteWaypoints routes each edge in isolation (single centered
// port per side, mid-point vertical leg) which makes co-terminal edges share a
// port, lets a vertical leg cross an intervening box, and collides labels. The
// global solver below assigns DISTINCT ports per (box,side), routes vertical
// legs inside the clear inter-column GUTTERS and long horizontals inside the
// inter-row BANDS (so no leg crosses a non-endpoint box), offsets parallel legs
// into distinct sub-lanes, and places each label on a clear segment. Pure +
// deterministic (stable sorts; ties resolve on edge index / id). The grid is
// DERIVED from the measured rects (no COL_W/ROW_H constants), so it is correct
// under zoom/theme reflow. c4RouteWaypoints stays as the legality-guard fallback.
const C4_PAD = 8;
const c4Clamp = (v, lo, hi) => Math.max(lo, Math.min(hi, v));
function c4Median(arr) {
  const s = arr.slice().sort((a, b) => a - b);
  return s.length ? s[Math.floor(s.length / 2)] : 0;
}
// sorted-greedy 1-D clustering; joins on the cluster's running MAX (not its first
// value) so a wide column cannot drift-split. Deterministic.
function c4Cluster1D(vals, tol) {
  const u = Array.from(new Set(vals)).sort((a, b) => a - b);
  const cl = [];
  u.forEach((v) => {
    const last = cl[cl.length - 1];
    if (!last || v - last.max > tol) cl.push({ lo: v, max: v });
    else last.max = v;
  });
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
  colCl.forEach((c, i) => {
    const mem = rects.filter((r) => r.x >= c.lo - 0.001 && r.x <= c.max + 0.001);
    colL[i] = Math.min.apply(null, mem.map((r) => r.x));
    colR[i] = Math.max.apply(null, mem.map((r) => r.x + r.w));
  });
  rowCl.forEach((c, i) => {
    const mem = rects.filter((r) => r.y >= c.lo - 0.001 && r.y <= c.max + 0.001);
    rowT[i] = Math.min.apply(null, mem.map((r) => r.y));
    rowB[i] = Math.max.apply(null, mem.map((r) => r.y + r.h));
  });
  const idxBy = (cl, v, tol) => {
    for (let i = 0; i < cl.length; i++) if (v >= cl[i].lo - tol && v <= cl[i].max + tol) return i;
    let bi = 0, bd = Infinity;
    for (let i = 0; i < cl.length; i++) { const d = Math.abs(v - cl[i].lo); if (d < bd) { bd = d; bi = i; } }
    return bi;
  };
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
// axis-aligned segment a-b vs rect inflated by pad; boundary touch does NOT count.
function c4SegHitsRect(a, b, r, pad) {
  const x0 = Math.min(a.x, b.x), x1 = Math.max(a.x, b.x), y0 = Math.min(a.y, b.y), y1 = Math.max(a.y, b.y);
  const rx0 = r.x - pad, rx1 = r.x + r.w + pad, ry0 = r.y - pad, ry1 = r.y + r.h + pad;
  return x0 < rx1 && x1 > rx0 && y0 < ry1 && y1 > ry0;
}
function c4WpHitsAny(wp, obstacles, pad) {
  for (let i = 1; i < wp.length; i++)
    for (let k = 0; k < obstacles.length; k++)
      if (c4SegHitsRect(wp[i - 1], wp[i], obstacles[k], pad)) return true;
  return false;
}
// Global solver. Input: measured backbone rects (each {id,x,y,w,h}), model edges,
// optional liveSet. Returns the per-edge render objects the SVG layer consumes.
function c4SolveRoutes(rects, edges, liveSet) {
  const byId = {};
  rects.forEach((r) => { r.r = r.x + r.w; r.b = r.y + r.h; r.cx = r.x + r.w / 2; r.cy = r.y + r.h / 2; byId[r.id] = r; });
  const E = (edges || []).map((e, idx) => ({ e, idx }))
    .filter((o) => byId[o.e.source] && byId[o.e.target] && o.e.source !== o.e.target);
  if (!E.length) return [];
  const grid = c4Grid(rects);
  const obstaclesFor = (m) => rects.filter((r) => r.id !== m.S.id && r.id !== m.T.id);

  // 1. side classification (H/V dominance on grid indices; ties → horizontal)
  const meta = E.map((o) => {
    const S = byId[o.e.source], T = byId[o.e.target];
    const cs = grid.colOf(S), ct = grid.colOf(T), rs = grid.rowOf(S), rt = grid.rowOf(T);
    const dC = ct - cs, dR = rt - rs;
    const hdom = Math.abs(dC) >= Math.abs(dR);
    const srcSide = hdom ? (dC >= 0 ? "R" : "L") : (dR >= 0 ? "B" : "T");
    const tgtSide = hdom ? (dC >= 0 ? "L" : "R") : (dR >= 0 ? "T" : "B");
    return { ...o, S, T, cs, ct, rs, rt, dC, dR, hdom, srcSide, tgtSide, port: {} };
  });

  // 2. distinct ports per (box,side): order by other endpoint cross-axis (+index),
  //    spread at fractions (k+1)/(n+1) — n=1 → exact side center (legacy-preserving).
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
      const f = (k2 + 1) / (n + 1);
      let p;
      if (side === "R") p = { x: box.r, y: box.y + f * box.h };
      else if (side === "L") p = { x: box.x, y: box.y + f * box.h };
      else if (side === "B") p = { x: box.x + f * box.w, y: box.b };
      else p = { x: box.x + f * box.w, y: box.y };
      req.m.port[req.end] = p;
    });
  });

  // 3. plan corridors per edge (CASE A straight, A-detour, or B), no offsets yet
  meta.forEach((m) => {
    const s = m.port.s, t = m.port.t;
    if (m.hdom) {
      m.gutG = m.dC >= 0 ? m.ct - 1 : m.ct;          // gutter just before the target column
      const vx0 = grid.gutCenter(m.gutG);
      const wp0 = [s, { x: vx0, y: s.y }, { x: vx0, y: t.y }, t];
      // |dC|<2 (adjacent columns) → simple 4-pt route. A MULTI-column span routes
      // its long horizontal through a SUB-LANED band (the Ad branch), never at the
      // port-y: a port-y horizontal that traverses an intervening column collinearly
      // OVERLAPS that column's edges (e.g. iOS->Core's long run at the host-dockerd
      // row landing on the Supervisor->host-dockerd entry). Bands are y-sub-laned so
      // parallel long runs never coincide. (Single-point CROSSINGS with a hub's
      // fan-out remain — those are inherent to a column-skipping edge and normal.)
      if (Math.abs(m.dC) < 2 && !c4WpHitsAny(wp0, obstaclesFor(m), C4_PAD)) { m.case = "A"; m.gutters = [m.gutG]; m.bands = []; }
      else {
        m.case = "Ad";
        m.srcGut = m.dC >= 0 ? m.cs : m.cs - 1;
        let band = m.dR >= 0 ? m.rs : m.rs - 1;
        for (let step = 0; step < grid.R + 1; step++) {
          const by0 = grid.bandCenter(band);
          if (!c4WpHitsAny([{ x: grid.gutCenter(m.srcGut), y: by0 }, { x: vx0, y: by0 }], obstaclesFor(m), C4_PAD)) break;
          band = m.dR >= 0 ? band + 1 : band - 1;
        }
        m.band = band; m.gutters = [m.srcGut, m.gutG]; m.bands = [band];
      }
    } else {
      m.case = "B";
      m.band = m.dR >= 0 ? m.rt - 1 : m.rt;
      m.gutters = []; m.bands = [m.band];
    }
  });

  // 4. two-pass centered sub-lanes so parallel legs in one corridor stay distinct
  const gutMembers = {}, bandMembers = {};
  meta.forEach((m) => {
    m.gutters.forEach((g) => { (gutMembers[g] = gutMembers[g] || []); if (gutMembers[g].indexOf(m.idx) < 0) gutMembers[g].push(m.idx); });
    m.bands.forEach((b) => { (bandMembers[b] = bandMembers[b] || []); if (bandMembers[b].indexOf(m.idx) < 0) bandMembers[b].push(m.idx); });
  });
  const vxFor = (g, idx) => {
    const mem = gutMembers[g] || [idx];
    const CH = c4Clamp((grid.gutHi(g) - grid.gutLo(g)) / (mem.length + 1), 8, 18);
    return c4Clamp(grid.gutCenter(g) + (mem.indexOf(idx) - (mem.length - 1) / 2) * CH, grid.gutLo(g) + C4_PAD, grid.gutHi(g) - C4_PAD);
  };
  const byFor = (b, idx) => {
    const mem = bandMembers[b] || [idx];
    const CH = c4Clamp((grid.bandHi(b) - grid.bandLo(b)) / (mem.length + 1), 8, 16);
    return c4Clamp(grid.bandCenter(b) + (mem.indexOf(idx) - (mem.length - 1) / 2) * CH, grid.bandLo(b) + C4_PAD, grid.bandHi(b) - C4_PAD);
  };

  // 5. build waypoints; final legality guard → legacy fallback (never crosses on
  //    the small planar APD backbones; the guard keeps it honest if it ever would)
  meta.forEach((m) => {
    const s = m.port.s, t = m.port.t;
    let wp;
    if (m.case === "A") {
      const vx = vxFor(m.gutG, m.idx);
      wp = [s, { x: vx, y: s.y }, { x: vx, y: t.y }, t];
    } else if (m.case === "Ad") {
      const vg = vxFor(m.gutG, m.idx), vs = vxFor(m.srcGut, m.idx), by = byFor(m.band, m.idx);
      wp = [s, { x: vs, y: s.y }, { x: vs, y: by }, { x: vg, y: by }, { x: vg, y: t.y }, t];
    } else {
      const by = byFor(m.band, m.idx);
      wp = [s, { x: s.x, y: by }, { x: t.x, y: by }, t];
      if (c4WpHitsAny(wp, obstaclesFor(m), C4_PAD)) {  // intervening same-column box → gutter detour
        const bBelow = grid.bandCenter(m.dR >= 0 ? m.rs : m.rs - 1);
        const bAbove = grid.bandCenter(m.dR >= 0 ? m.rt - 1 : m.rt);
        const tryGut = (gIdx) => {
          const gx = vxFor(gIdx, m.idx);
          const w = [s, { x: s.x, y: bBelow }, { x: gx, y: bBelow }, { x: gx, y: bAbove }, { x: t.x, y: bAbove }, t];
          return c4WpHitsAny(w, obstaclesFor(m), C4_PAD) ? null : w;
        };
        wp = tryGut(m.cs) || tryGut(m.cs - 1) || wp;
      }
    }
    if (c4WpHitsAny(wp, obstaclesFor(m), C4_PAD)) { wp = c4RouteWaypoints(m.S, m.T); m.fellBack = true; }
    m.wp = wp;
  });

  // 6. labels: accept a horizontal segment whose LABEL bbox clears all boxes; then
  //    deterministic de-collision (process in edge order, nudge along the segment).
  const placed = [];
  const estBox = (lx, ly, text) => ({ x: lx - text.length * 3.1, y: ly - 11, w: text.length * 6.2, h: 13 });
  const ov = (a, c) => a.x < c.x + c.w && a.x + a.w > c.x && a.y < c.y + c.h && a.y + a.h > c.y;
  meta.forEach((m) => {
    const text = c4ShortEdgeLabel(m.e.label);
    const cands = [];
    for (let i = 1; i < m.wp.length; i++) {
      const a = m.wp[i - 1], b = m.wp[i];
      if (Math.abs(a.y - b.y) < 0.5 && Math.abs(b.x - a.x) >= 24) cands.push({ y: a.y, x0: Math.min(a.x, b.x), x1: Math.max(a.x, b.x), L: Math.abs(b.x - a.x) });
    }
    cands.sort((a, b) => (b.L - a.L) || (a.y - b.y));
    let lx = null, ly = null;
    const obstacles = text ? rects : [];
    for (let ci = 0; ci < cands.length && lx == null; ci++) {
      const c = cands[ci];
      const fracs = [0.5, 0.35, 0.65, 0.25, 0.75];
      for (let fi = 0; fi < fracs.length; fi++) {
        const cx = c.x0 + (c.x1 - c.x0) * fracs[fi], cy = c.y - 8;
        const lb = estBox(cx, cy, text || "x");
        if (!obstacles.some((o) => ov(lb, o)) && !placed.some((p) => ov(lb, p))) { lx = cx; ly = cy; break; }
      }
    }
    if (lx == null) {  // staggered gutter-center fallback
      lx = (Math.min(m.S.r, m.T.r) + Math.max(m.S.x, m.T.x)) / 2;
      ly = (m.port.s.y + m.port.t.y) / 2 - 8 + (m.idx % 3) * 14;
    }
    if (text) placed.push(estBox(lx, ly, text));
    m.lx = lx; m.ly = ly; m.labelText = text;
  });

  // 7. emit the render objects (label always renders on a horizontal anchor).
  //    _wp/_case/_fellBack are internal diagnostics (ignored by the SVG render;
  //    consumed by the c4_solve_routes node oracle to verify the geometry).
  return meta.map((m) => ({
    id: m.e.id,
    d: c4RoundedPath(m.wp, 7),
    port: m.wp[0],
    live: !!(liveSet && liveSet.has && liveSet.has(m.e.source) && liveSet.has(m.e.target)),
    label: m.labelText,
    title: m.e.label || "",
    lx: m.lx, ly: m.ly, horiz: true,
    _wp: m.wp, _case: m.case, _fellBack: !!m.fellBack,
  }));
}

// ── C4 SVG edge overlay ──────────────────────────────────────────────────
// Plain React + SVG (no Cytoscape). Covers the stage absolutely, sized to the
// stage's scroll box, pointer-events:none, BEHIND the node boxes (z-index in
// .edge-layer CSS). For each grounded edge it draws: a rounded orthogonal path
// (marker-end arrow), a start port circle, and a short de-collided label with a
// paper-filled background rect (full relation string on hover). Edges whose BOTH
// endpoints are in `liveSet` render "live" (accent + thicker).
//
// Lifecycle (the handoff's redraw contract): measures rendered boxes via
// c4Anchors and redraws on mount, document.fonts.ready, a debounced window
// resize, and a theme MutationObserver (data-theme/data-sev on <body>). It reads
// the box positions by querying `[data-c4id]` inside the passed stage ref, so it
// is agnostic to how Task 6 positions the boxes (absolute backbone or flow).
function C4EdgeLayer({ stageRef, edges, liveSet, redrawKey }) {
  const [paths, setPaths] = React.useState([]);
  const [dims, setDims] = React.useState({ w: 0, h: 0 });
  const labelRefs = React.useRef({});
  const [labelBoxes, setLabelBoxes] = React.useState({});

  const live = liveSet || null;

  const measure = React.useCallback(() => {
    const stage = stageRef && stageRef.current;
    if (!stage) return;
    // Measure the BACKBONE boxes once (the routed set). c4SolveRoutes then solves
    // ALL edges together so connectors attach at distinct ports per side, route in
    // the clear inter-column gutters / inter-row bands, never cross a non-endpoint
    // box, and place labels on clear segments. c4Anchors(el,el,stage)[0] gives one
    // box rect in stage coords (layout-space, transform-invariant).
    const rects = Array.from(stage.querySelectorAll(".l2-backbone [data-c4id]")).map((el) => {
      const r = c4Anchors(el, el, stage)[0];
      r.id = el.getAttribute("data-c4id");
      return r;
    });
    setPaths(c4SolveRoutes(rects, edges || [], live));
    setDims({ w: stage.scrollWidth, h: stage.scrollHeight });
  }, [stageRef, edges, live]);

  // Redraw on: mount + any data/zoom/drill change (redrawKey), fonts.ready,
  // debounced window resize, and a theme MutationObserver.
  React.useEffect(() => {
    measure();
    const raf = requestAnimationFrame(measure);     // after layout settles
    const t = setTimeout(measure, 220);             // after fonts/late shifts
    if (document.fonts && document.fonts.ready) document.fonts.ready.then(measure).catch(() => {});
    let rT;
    const onResize = () => { clearTimeout(rT); rT = setTimeout(measure, 120); };
    window.addEventListener("resize", onResize);
    const obs = new MutationObserver(measure);
    obs.observe(document.body, { attributes: true, attributeFilter: ["data-theme", "data-sev"] });
    return () => {
      cancelAnimationFrame(raf); clearTimeout(t); clearTimeout(rT);
      window.removeEventListener("resize", onResize); obs.disconnect();
    };
  }, [measure, redrawKey]);

  // Size the label background rects from the rendered text bbox (after paint).
  React.useEffect(() => {
    const boxes = {};
    paths.forEach((p) => {
      const node = labelRefs.current[p.id];
      if (!node) return;
      try {
        const b = node.getBBox();
        boxes[p.id] = { x: b.x - 3, y: b.y - 1, width: b.width + 6, height: b.height + 2 };
      } catch (_) { /* getBBox throws on detached/zero-size text — skip */ }
    });
    setLabelBoxes(boxes);
  }, [paths]);

  return (
    <svg
      className="edge-layer"
      aria-hidden="true"
      width={dims.w}
      height={dims.h}
      viewBox={`0 0 ${dims.w} ${dims.h}`}
    >
      <defs>
        <marker id="c4-arw" viewBox="0 0 10 10" refX="8.5" refY="5"
          markerWidth="7" markerHeight="7" orient="auto-start-reverse">
          <path d="M0,0 L10,5 L0,10 z" />
        </marker>
      </defs>
      {paths.map((p) => (
        <g key={p.id} className="eg">
          <title>{p.title}</title>
          {/* Induced member edge (Task 8): an edge is "live" (accent + thicker)
              iff the overlay is active AND BOTH endpoints are in the membership
              set (computed in measure() as p.live). Same both-endpoints-in-set
              rule the deleted GraphView overlayHighlight used, applied here at
              draw time. Only model.edges are ever drawn — never an unmapped hop. */}
          <path className={`edge-layer__path edge${p.live ? " edge-layer__path--live live" : ""}`} d={p.d} markerEnd="url(#c4-arw)" />
          <circle
            className={`edge-layer__port port${p.live ? " edge-layer__port--live" : ""}`}
            cx={p.port.x}
            cy={p.port.y}
            r="3"
            style={p.live ? undefined : { fill: "var(--rule-strong)" }}
          />
          {p.label && labelBoxes[p.id] && (
            <rect className="elabel-bg" rx="2" {...labelBoxes[p.id]} />
          )}
          {p.label && (
            <text
              ref={(el) => { labelRefs.current[p.id] = el; }}
              className="elabel"
              x={p.lx}
              y={p.ly}
              textAnchor="middle"
              dominantBaseline={p.horiz ? "auto" : "middle"}
            >{p.label}</text>
          )}
        </g>
      ))}
    </svg>
  );
}

// ── C4 node box (in-node badge rules, REAL c4_model names — gap-fix 2) ────────
// Renders one node as a .nb box with the headline in-node badge row. Consumes the
// authentic window.APD_DATA.c4_model field names — NEVER the prototype-fixture
// abbreviations (cap/state/ff/me). Badge rules (mirror the handoff §174-189):
//   analysis_state === "not_analyzed" -> single dashed italic "not analyzed" pill, NO counts.
//   else:
//     badge > 0  -> "⚑ {badge}" sev-high, CLICKABLE -> onOpenFinding(provenance.first_finding_id)
//                   (static, non-link when no first_finding_id — never hidden).
//     badge == null (analyzed, 0) and container/component/code -> muted "⚑ 0".
//     capability_badge > 0 -> "🛡 {capability_badge}" sev-low.
// Drill: clicking a drillable box calls onDrill(n.id); clicking the ⚑ badge
// stops propagation so it deep-links WITHOUT drilling.
function NodeBox({ n, model, opts = {}, selected, onDrill, onOpenFinding }) {
  const childrenOf = model.__childrenOf;
  const byId = model.__byId;
  const codeOf = (id) => (childrenOf[id] || []).map((c) => byId[c]).filter((x) => x && x.type === "code");
  const compsOf = (id) => (childrenOf[id] || []).map((c) => byId[c]).filter((x) => x && x.type === "component");
  const na = n.analysis_state === "not_analyzed";
  const findingId = n.provenance && n.provenance.first_finding_id;
  const isExt = n.type === "external_system" || n.kind === "external_system";
  const drillable =
    (n.type === "container" && (compsOf(n.id).length > 0 || codeOf(n.id).length > 0)) ||
    (n.type === "component" && codeOf(n.id).length > 0);
  const isSelected = n.id === selected.container || n.id === selected.component;

  const cls = [
    "nb",
    n.kind ? `nb--${n.kind}` : "",
    n.type === "system" ? "nb--system" : "",
    isExt ? "nb--external" : "",
    !na && n.badge ? "nb--hot" : "",
    na ? "nb--na" : "",
    opts.mini ? "nb--mini" : "",
    opts.big ? "nb--big" : "",
    drillable ? "nb--clickable" : "",
    isSelected ? "nb--selected" : "",
    // Attack-path overlay dimming (Task 8): when an overlay path is selected,
    // C4TierGraph passes opts.dim=true for every box NOT in the resolved
    // membership set (overlayC4NodeIds). Class-based (not inline opacity) so the
    // CSS var-driven theme recolors live and the rule composes with tier styles.
    opts.dim ? "nb--dim" : "",
  ].filter(Boolean).join(" ");

  const dim = opts.dim ? "1" : undefined;
  const kindTxt = (n.kind || "").replace(/_/g, " ");
  const showKind = n.kind && !opts.noKind;

  // text-only tooltip (never inject HTML from adopter data)
  const lvlName = ({ system: "L1 system", person: "L1 person", external_system: "L1 external",
    container: "L2 container", component: "L3 component", code: "L4 code" })[n.type] || n.type;
  let tip = `${n.label}\n${lvlName}${n.kind ? " · " + kindTxt : ""}`;
  if (na) tip += "\n⚠ not analyzed (no code anchors)";
  else {
    if (n.badge) tip += `\n⚑ ${n.badge} finding${n.badge === 1 ? "" : "s"}`;
    if (n.capability_badge) tip += `\n🛡 ${n.capability_badge} capabilit${n.capability_badge === 1 ? "y" : "ies"}`;
  }
  if (drillable) {
    const c = compsOf(n.id).length, k = codeOf(n.id).length;
    tip += c ? `\n↳ click to drill (${c} component${c === 1 ? "" : "s"})`
             : `\n↳ click to drill (${k} code)`;
  }

  const onClick = drillable ? (e) => { if (e.target.closest(".bdg--find")) return; onDrill(n.id); } : undefined;

  // badges
  const badges = [];
  if (na) {
    badges.push(
      <span key="na" className="bdg bdg--na"
        title="No code anchors — analysis_state: not_analyzed (not '0 = clean')">not analyzed</span>
    );
  } else {
    if (n.badge != null && n.badge > 0) {
      const canLink = findingId && typeof onOpenFinding === "function";
      badges.push(
        <span
          key="find"
          className="bdg bdg--find"
          role={canLink ? "button" : undefined}
          title={`${n.badge} finding${n.badge === 1 ? "" : "s"} on this element${canLink ? " — open in Findings" : ""}`}
          style={{ cursor: canLink ? "pointer" : "default" }}
          onClick={canLink ? (e) => { e.stopPropagation(); onOpenFinding(findingId); } : undefined}
        >⚑ {n.badge}</span>
      );
    } else if (n.type === "container" || n.type === "component" || n.type === "code") {
      badges.push(
        <span key="clean" className="bdg bdg--clean" title="Analyzed · zero findings">⚑ 0</span>
      );
    }
    if (n.capability_badge != null && n.capability_badge > 0) {
      badges.push(
        <span key="cap" className="bdg bdg--cap"
          title={`${n.capability_badge} confirmed capabilit${n.capability_badge === 1 ? "y" : "ies"}`}>🛡 {n.capability_badge}</span>
      );
    }
  }

  return (
    <div
      className={cls}
      data-c4id={n.id}
      data-dim={dim}
      title={tip}
      style={opts.style}
      onClick={onClick}
    >
      <div className="nb__head">
        {showKind && <span className="nb__kind">{kindTxt}</span>}
      </div>
      <div className="nb__name">{n.label}</div>
      {n.type === "system" && <div className="nb__sub">software system</div>}
      {!opts.noBadges && badges.length > 0 && <div className="nb__badges">{badges}</div>}
    </div>
  );
}

// ── C4 tiered "system-map" scene (the fcose force-graph replacement) ─────────
// Four stacked tiers with left-gutter labels:
//   L1 System context — Actors (person) | system (center) | External systems
//   L2 Containers      — backbone (c4BackboneLayout, absolute-positioned + the
//                        C4EdgeLayer SVG overlay) + "analyzed · no traced relation"
//                        shelf + "infrastructure · not analyzed" shelf
//   L3 Components      — data-driven; honest empty/blocked states
//   L4 Code            — the active parent's code grid
// Plus a zoom/fit toolbar (transform: scale on the stage inner). No Cytoscape.
// overlayC4NodeIds dims non-members and renders the induced backbone edges "live".
function C4TierGraph({ model, selectedContainer, selectedComponent, overlayC4NodeIds, onDrill, onOpenFinding }) {
  const nodes = (model && model.nodes) || [];
  const edges = (model && model.edges) || [];

  const byId = React.useMemo(() => {
    const m = {}; nodes.forEach((n) => { m[n.id] = n; }); return m;
  }, [model]);
  const childrenOf = React.useMemo(() => {
    const m = {};
    nodes.forEach((n) => { if (n.parent) (m[n.parent] = m[n.parent] || []).push(n.id); });
    return m;
  }, [model]);
  // hand byId/childrenOf to NodeBox without prop-drilling each lookup
  const mdl = React.useMemo(() => Object.assign({}, model, { __byId: byId, __childrenOf: childrenOf }), [model, byId, childrenOf]);

  const codeOf = (id) => (childrenOf[id] || []).map((c) => byId[c]).filter((x) => x && x.type === "code");
  const compsOf = (id) => (childrenOf[id] || []).map((c) => byId[c]).filter((x) => x && x.type === "component");

  const layout = React.useMemo(() => c4BackboneLayout(nodes, edges), [model]);

  const stageRef = React.useRef(null);
  const [zoom, setZoom] = React.useState(1);
  const selected = { container: selectedContainer, component: selectedComponent };
  const ovSet = (overlayC4NodeIds && overlayC4NodeIds.length) ? new Set(overlayC4NodeIds) : null;
  // redrawKey forces C4EdgeLayer to re-measure when the visible layout changes.
  const redrawKey = `${selectedContainer || ""}|${selectedComponent || ""}|${zoom}|${(overlayC4NodeIds || []).join(",")}`;

  const persons = nodes.filter((n) => n.type === "person");
  const exts = nodes.filter((n) => n.type === "external_system");
  const sys = nodes.find((n) => n.type === "system");
  const containers = nodes.filter((n) => n.type === "container");

  const box = (n, opts) => (
    <NodeBox key={n.id} n={n} model={mdl} opts={Object.assign({ dim: ovSet ? !ovSet.has(n.id) : false }, opts)}
      selected={selected} onDrill={onDrill} onOpenFinding={onOpenFinding} />
  );

  // backbone edges visible = grounded edges whose endpoints are both backbone nodes
  const backboneIds = new Set(layout.connected.map((p) => p.id));
  const backboneEdges = edges.filter((e) => backboneIds.has(e.source) && backboneIds.has(e.target));

  // ── L3 / L4 active-parent resolution ──
  const compsOfSel = selectedContainer ? compsOf(selectedContainer) : [];
  const activeParentId = selectedComponent
    ? selectedComponent
    : (selectedContainer && compsOfSel.length === 0 ? selectedContainer : null);

  // zoom/fit
  const zIn = () => setZoom((z) => Math.min(2, +(z + 0.15).toFixed(2)));
  const zOut = () => setZoom((z) => Math.max(0.4, +(z - 0.15).toFixed(2)));
  const fit = () => {
    const stage = stageRef.current; if (!stage) return;
    const wrap = stage.parentElement; if (!wrap) return;
    const avail = wrap.clientWidth - 4;
    setZoom(Math.min(1, +(avail / stage.scrollWidth).toFixed(3)));
  };

  return (
    <div className="archx-stage-wrap">
      <div className="archx-toolbar">
        <button type="button" onClick={zOut} title="Zoom out">−</button>
        <span className="zoom-level">{Math.round(zoom * 100)}%</span>
        <button type="button" onClick={zIn} title="Zoom in">+</button>
        <button type="button" onClick={fit} title="Fit">fit</button>
      </div>

      <div className="archx-stage" ref={stageRef} style={{ transform: `scale(${zoom})`, transformOrigin: "0 0" }}>
        <C4EdgeLayer stageRef={stageRef} edges={backboneEdges} liveSet={ovSet} redrawKey={redrawKey} />

        {/* L1 — System context */}
        <section className="tier" data-level="system">
          <div className="tier-gutter">
            <div className="t-l1">L1</div>
            <div className="t-l2">System context</div>
            <div className="t-l3">person · system · external</div>
          </div>
          <div className="tier-body">
            <div className="l1-body">
              <div className="l1-group">
                <div className="l1-group__h">Actors · {persons.length}</div>
                <div className="l1-grid">
                  {persons.map((p) => box(p, { mini: true, noKind: true }))}
                </div>
              </div>
              <div className="l1-center">{sys && box(sys, { big: true })}</div>
              <div className="l1-group">
                <div className="l1-group__h" style={{ textAlign: "right" }}>External systems · {exts.length}</div>
                <div className="l1-grid l1-grid--ext">
                  {exts.map((x) => box(x, { mini: true, noKind: true }))}
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* L2 — Containers */}
        <section className="tier" data-level="container">
          <div className="tier-gutter">
            <div className="t-l1">L2</div>
            <div className="t-l2">Containers</div>
            <div className="t-l3">{containers.length} containers</div>
          </div>
          <div className="tier-body">
            <div className="l2-cap">Traced relationships</div>
            <div className="l2-backbone" style={{ minHeight: (Math.max(1, ...layout.connected.map((p) => p.row + 1)) * C4_ROW_H) + "px" }}>
              {layout.connected.map((p) => (
                <div key={p.id} className="nb-pos" style={{ position: "absolute", left: p.x + "px", top: p.y + "px" }}>
                  {byId[p.id] && box(byId[p.id])}
                </div>
              ))}
            </div>
            <div className="l2-cap">Analyzed · no traced relation</div>
            <div className="shelf">
              {layout.analyzed.map((id) => byId[id] && box(byId[id]))}
            </div>
            {layout.infra.length > 0 && <>
              <div className="l2-cap">Infrastructure · not analyzed</div>
              <div className="shelf shelf--infra">
                {layout.infra.map((id) => byId[id] && box(byId[id], { noKind: true }))}
              </div>
            </>}
          </div>
        </section>

        {/* L3 — Components (data-driven; honest empty states) */}
        <section className="tier" data-level="component">
          <div className="tier-gutter">
            <div className="t-l1">L3</div>
            <div className="t-l2">Components</div>
            <div className="t-l3">{!selectedContainer ? "—" : `${byId[selectedContainer].label} · ${compsOfSel.length || "none"}`}</div>
          </div>
          <div className="tier-body">
            {!selectedContainer ? (
              <div className="code-hint">L3 components appear here when a run grounds them via <code>c4-recon.components[]</code>. They are <b>blocked by default</b>, so most runs drill <b>L2 → L4</b>. Select a container above.</div>
            ) : compsOfSel.length === 0 ? (
              <div className="code-hint">No grounded L3 components under <b>{byId[selectedContainer].label}</b> — L3 is blocked unless an artifact groups symbols. This container renders <b>L2 → L4</b> (code parents directly to the container).</div>
            ) : (
              <div className="code-wrap">
                <div className="code-parent">{box(byId[selectedContainer])}</div>
                <div className="code-grid">{compsOfSel.map((c) => box(c))}</div>
              </div>
            )}
          </div>
        </section>

        {/* L4 — Code */}
        <section className="tier" data-level="code">
          <div className="tier-gutter">
            <div className="t-l1">L4</div>
            <div className="t-l2">Code</div>
            <div className="t-l3">{activeParentId ? `${byId[activeParentId].label} · ${codeOf(activeParentId).length}` : "select a container"}</div>
          </div>
          <div className="tier-body">
            {!selectedContainer ? (
              <div className="code-hint">Select a container (or an L3 component, when present) to expand its grounded L4 code elements — each with its own ⚑ finding and 🛡 capability counts.</div>
            ) : compsOfSel.length > 0 && !selectedComponent ? (
              <div className="code-hint">Select an L3 component above to expand its code elements.</div>
            ) : (
              <div className="code-wrap">
                <div className="code-parent">{box(byId[activeParentId])}</div>
                <div className="code-grid">{codeOf(activeParentId).map((c) => box(c))}</div>
              </div>
            )}
          </div>
        </section>
      </div>
    </div>
  );
}

Object.assign(window, {
  SeverityPill, DispositionMark, MaturityMark, CopyPill, TaxonomyTag, TagRow, ToastHost, DiagnosticsBanner,
  GraphView, AttackPathStrip,
  c4BackboneLayout, c4ShortEdgeLabel,
  c4Anchors, c4RouteWaypoints, c4RoundedPath, C4EdgeLayer,
  c4Grid, c4SolveRoutes, c4SegHitsRect,
  NodeBox, C4TierGraph,
  GOAL_LABELS, GOAL_SHORT, TIER_LABELS, TIER_GOALS,
});
