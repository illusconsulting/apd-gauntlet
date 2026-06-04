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
  return (
    <span
      ref={ref}
      className="tag"
      onMouseEnter={onEnter}
      onMouseLeave={() => setHover(false)}
    >
      {id}
      {hover && entry && (
        <span
          className="tag-tooltip"
          style={{ left: pos.x + "px", top: pos.y + "px" }}
        >
          <span className="tag-tooltip__family">{entry.family}</span>
          {entry.title}
        </span>
      )}
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

Object.assign(window, {
  SeverityPill, DispositionMark, MaturityMark, CopyPill, TaxonomyTag, TagRow, ToastHost, DiagnosticsBanner,
  GraphView,
  GOAL_LABELS, GOAL_SHORT, TIER_LABELS, TIER_GOALS,
});
