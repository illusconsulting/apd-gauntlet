// report-template/screens/C4.jsx
/* eslint-disable */
// C4 architecture scene — grounded System/Container/Component/Code view.
//
// Levels: L1 System Context · L2 Container · L3 Component · L4 Code. On load we
// show L1 (system/person/external_system) + L2 (containers). Clicking a container
// drills to its L3 components — or straight to its L4 code when L3 was blocked
// (the never-invent default: components are OMITTED unless an artifact grouped
// symbols, so most runs render L2 -> L4). Clicking a component shows its L4 code.
//
// Every node carries a FINDINGS badge (finding_count) plus a separate CAPABILITY
// badge in the per-node drill list. The honest banner surfaces unlocalized
// doc-anchored findings (no code locator) and "not_analyzed" containers (repos
// with zero code anchors) — never rendered as "0 findings = clean". The
// interactive render is the deterministic tiered system-map C4TierGraph
// (components.jsx): plain-React+SVG tiers (System → Container → Component →
// Code) laid out by c4BackboneLayout, with orthogonal connectors drawn by the
// C4EdgeLayer SVG overlay. data_store / external_system kind cues + the
// kind chip are rendered by C4TierGraph itself off node.kind.

function C4({ data, onOpenFinding }) {
  const c4 = data.c4_model;

  if (!c4 || !c4.present) {
    return (
      <div className="empty-state">
        <p>No grounded C4 architecture model was assembled for this run. The
        container/code tiers require a code-evidence index
        (<code>00-context/code-evidence-index.yaml</code>) produced by
        code-recon; the system/container tiers require
        <code>40-synthesis/asset-graph.yaml</code>. Enable code_recon in the run
        config to populate this view.</p>
      </div>
    );
  }

  const allNodes = c4.nodes || [];
  // c4.edges is consumed by C4TierGraph (via model={c4}) / C4EdgeLayer, not here.
  const nodeById = React.useMemo(() => {
    const m = {};
    allNodes.forEach((n) => { m[n.id] = n; });
    return m;
  }, [c4]);
  const childrenOf = React.useMemo(() => {
    const m = {};
    allNodes.forEach((n) => {
      if (!n.parent) return;
      (m[n.parent] = m[n.parent] || []).push(n.id);
    });
    return m;
  }, [c4]);

  // Drill state. selectedContainer null = L1+L2 default; clicking a container
  // node selects it (revealing its components, or its code when components are
  // absent). selectedComponent narrows further to that component's L4 code.
  const [selectedContainer, setSelectedContainer] = React.useState(null);
  const [selectedComponent, setSelectedComponent] = React.useState(null);

  // ── Attack-path overlay (stretch) ──────────────────────────────────────
  // Select an enumerated attack path and highlight the C4 elements it traverses
  // WHERE a grounded asset->C4 join exists. The join is the assembler's
  // deterministic c4_model.asset_to_c4 (asset node id -> c4 node id) plus
  // finding_to_c4 (code-bearing finding id -> code c4 node id). Hops with no
  // mapping are NEVER invented onto the C4 graph — they go on a parallel strip.
  const ap = data.attack_paths;
  const assetToC4 = (c4 && c4.asset_to_c4) || {};
  const findingToC4 = (c4 && c4.finding_to_c4) || {};
  const overlayPaths = React.useMemo(() => {
    const pairs = (ap && ap.pairs) || [];
    return pairs.flatMap((pair) => (pair.paths || []).map((p) => ({
      id: p.path_id,
      label: `${pair.attacker_position_name || pair.attacker_position} → ${pair.crown_jewel_name || pair.crown_jewel} · ${p.path_id}`,
      hops: p.edges_detailed || (p.edges || []).map((eid) => ({ edge_id: eid })),
    })));
  }, [ap]);
  const [selectedOverlayPath, setSelectedOverlayPath] = React.useState(null);

  // Resolve one selected path into (a) c4 node ids to highlight, and
  // (b) the unmapped hops that belong on the parallel asset strip.
  const overlay = React.useMemo(() => {
    if (!selectedOverlayPath) return { c4NodeIds: [], unmappedHops: [] };
    const sel = overlayPaths.find((p) => p.id === selectedOverlayPath);
    if (!sel) return { c4NodeIds: [], unmappedHops: [] };
    const c4NodeIds = new Set();
    const unmappedHops = [];
    sel.hops.forEach((h) => {
      let mapped = false;
      // Asset endpoints -> container join. The hops come from the transform's
      // edges_detailed, which emit from_id/to_id (the asset-graph node ids);
      // those are the assetToC4 lookup keys — the bare from/to keys do not exist
      // on the hop objects, so the old lookup silently never fired.
      [h.from_id, h.to_id].forEach((aid) => {
        if (aid && assetToC4[aid]) { c4NodeIds.add(assetToC4[aid]); mapped = true; }
      });
      // Code-bearing finding -> code node join.
      if (h.finding_id && findingToC4[h.finding_id]) {
        c4NodeIds.add(findingToC4[h.finding_id]); mapped = true;
      }
      if (!mapped) {
        unmappedHops.push({
          edge_id: h.edge_id,
          from_name: h.from_name || h.from_id || "?",
          to_name: h.to_name || h.to_id || "?",
          finding_id: h.finding_id || null,
        });
      }
    });
    return { c4NodeIds: [...c4NodeIds], unmappedHops };
  }, [selectedOverlayPath, overlayPaths, assetToC4, findingToC4]);

  // Drill reducer — a tiered node-box click drills exactly like the NodeRow
  // buttons. The c4 node id is the DOM box's data-id. Null-safe: a tap on a
  // node with no drill target (code/system/person/external_system) is a NO-OP
  // and never resets the view to nowhere. Passed to C4TierGraph as onDrill and
  // reused by NodeRow.onClick below.
  const onDrill = React.useCallback((nodeId) => {
    if (!nodeId) return;
    const n = nodeById[nodeId];
    if (!n) return;
    if (n.type === "container") { setSelectedContainer(nodeId); setSelectedComponent(null); }
    else if (n.type === "component") { setSelectedContainer(n.parent || selectedContainer); setSelectedComponent(nodeId); }
    // code/system/person/external_system taps do not change the drill level (no-op).
  }, [nodeById, selectedContainer]);

  const containers = allNodes.filter((n) => n.type === "container");
  const notAnalyzed = containers.filter((n) => n.analysis_state === "not_analyzed");
  // Authoritative not_analyzed count comes off the contracted rollup
  // (transform's not_analyzed_count, sourced from build_summary). Fall back to
  // the node-derived list length when the rollup is absent.
  const notAnalyzedCount =
    c4.not_analyzed_count != null ? c4.not_analyzed_count : notAnalyzed.length;
  const levelsPresent = c4.levels_present || [];

  // Per-node drill-list row: name, finding badge (deep-links to Findings),
  // capability badge, and a not_analyzed marker. Mirrors the AttackPaths chip idiom.
  function NodeRow({ n }) {
    const na = n.analysis_state === "not_analyzed";
    const findingId = n.provenance && n.provenance.first_finding_id;
    return (
      <li className={`c4-node-row ${na ? "c4-node-row--not-analyzed" : ""}`}>
        <button
          type="button"
          className="c4-node-row__name"
          onClick={() => onDrill(n.id)}
          title={na ? "Not analyzed — no code anchors in this repo" : `Drill into ${n.label}`}
        >
          <span className={`c4-level-chip c4-level-chip--${n.type}`}>{n.type}</span>
          {n.label}
        </button>
        {/* EN2: C4-style typing chip. Containers render their kind
            (service / data_store / external_system / app / library / compute);
            code rows render theirs (function / class / route / module). Omitted
            when the model carries no kind — never invents a type. */}
        {n.kind && (
          <span
            className={`c4-kind-chip c4-kind-chip--${n.kind}`}
            title={`C4 kind: ${n.kind}`}
          >{n.kind}</span>
        )}
        {na && <span className="c4-badge c4-badge--not-analyzed" title="No code anchors — analysis_state: not_analyzed (NOT '0 findings = clean')">not analyzed</span>}
        {/* Deep-link ⚑ badge: RENDERED only when FX1 recorded a first_finding_id
            on this node (provenance.first_finding_id). Calls onOpenFinding with
            that id to jump into the Findings tab. */}
        {!na && n.badge != null && n.badge > 0 && findingId && onOpenFinding && (
          <button
            type="button"
            className="c4-badge c4-badge--finding"
            title={`${n.badge} finding${n.badge === 1 ? "" : "s"} on this element — open in Findings`}
            onClick={() => onOpenFinding(findingId)}
          >⚑ {n.badge}</button>
        )}
        {/* Honest fallback: a finding count with no resolvable first_finding_id
            still shows the count (never hidden as "clean"), but is not a link. */}
        {!na && n.badge != null && n.badge > 0 && !(findingId && onOpenFinding) && (
          <span
            className="c4-badge c4-badge--finding c4-badge--finding-static"
            title={`${n.badge} finding${n.badge === 1 ? "" : "s"} on this element`}
          >⚑ {n.badge}</span>
        )}
        {!na && n.badge != null && n.badge === 0 && (
          <span className="c4-badge c4-badge--clean" title="Analyzed, zero findings">0</span>
        )}
        {n.capability_badge != null && n.capability_badge > 0 && (
          <span className="c4-badge c4-badge--capability" title={`${n.capability_badge} confirmed capabilit${n.capability_badge === 1 ? "y" : "ies"}`}>🛡 {n.capability_badge}</span>
        )}
      </li>
    );
  }

  const drillCrumb = !selectedContainer
    ? "L1 System context + L2 Containers"
    : !selectedComponent
      ? `Container: ${(nodeById[selectedContainer] || {}).label}`
      : `Component: ${(nodeById[selectedComponent] || {}).label}`;

  const visibleContainerChildren = selectedContainer
    ? (childrenOf[selectedContainer] || []).map((id) => nodeById[id]).filter(Boolean)
    : [];

  return (
    <div className="c4-scene">
      <div className="section-eyebrow">§ Architecture — grounded C4 model</div>
      <h2 className="section-title">
        System → Container → Component → Code · {(c4.levels_present || []).join(" · ") || "context"}
      </h2>

      {/* Honest banner — never hide doc-only findings or not-analyzed repos. */}
      <div className="c4-banner">
        <strong>Grounded view.</strong>{" "}
        {containers.length} container{containers.length === 1 ? "" : "s"}
        {notAnalyzedCount > 0 && (
          <>
            {" · "}
            <span className="c4-banner__warn">
              {notAnalyzedCount} not analyzed
            </span>{" "}
            (no code anchors — shown as <em>not_analyzed</em>, never &ldquo;0 findings = clean&rdquo;)
          </>
        )}
        {c4.unlocalized_findings > 0 && (
          <>
            {" · "}
            <span className="c4-banner__warn">
              {c4.unlocalized_findings} unlocalized finding{c4.unlocalized_findings === 1 ? "" : "s"}
            </span>{" "}
            (doc-anchored, no <code>code:</code> locator — surfaced, not dropped)
          </>
        )}
      </div>

      {/* Drill breadcrumb + reset. */}
      <div className="c4-crumbs">
        <button
          type="button"
          className={`chip ${!selectedContainer ? "chip--active" : ""}`}
          onClick={() => { setSelectedContainer(null); setSelectedComponent(null); }}
        >⌂ System</button>
        <span className="c4-crumbs__sep">/</span>
        <span className="c4-crumbs__here">{drillCrumb}</span>
        {selectedContainer && (
          <button
            type="button"
            className="chip"
            onClick={() => setSelectedComponent(null)}
            disabled={!selectedComponent}
            style={{ marginLeft: "var(--space-2)" }}
          >↑ Up one level</button>
        )}
      </div>

      {/* Attack-path overlay control (stretch) — honest partial highlight. */}
      {overlayPaths.length > 0 && (
        <div className="c4-overlay">
          <label className="c4-overlay__label" htmlFor="c4-overlay-select">
            Overlay attack path:
          </label>
          <select
            id="c4-overlay-select"
            className="c4-overlay__select"
            value={selectedOverlayPath || ""}
            onChange={(e) => setSelectedOverlayPath(e.target.value || null)}
          >
            <option value="">— none —</option>
            {overlayPaths.map((p) => (
              <option key={p.id} value={p.id}>{p.label}</option>
            ))}
          </select>
          {selectedOverlayPath && (
            <button
              type="button"
              className="chip"
              onClick={() => setSelectedOverlayPath(null)}
            >clear</button>
          )}
        </div>
      )}

      {selectedOverlayPath && overlay.unmappedHops.length > 0 && (
        <div className="c4-overlay-strip">
          <div className="c4-overlay-strip__head">
            Parallel asset hops — <strong>no C4 mapping</strong> (shown here, never
            invented onto the architecture graph):
          </div>
          <ol className="c4-overlay-strip__hops">
            {overlay.unmappedHops.map((h) => (
              <li key={h.edge_id} className="c4-overlay-strip__hop c4-overlay-strip__hop--unmapped">
                <span className="mono">{h.from_name}</span>
                <span className="c4-overlay-strip__arrow">→</span>
                <span className="mono">{h.to_name}</span>
                {h.finding_id && (
                  <button
                    type="button"
                    className="c4-badge c4-badge--finding"
                    onClick={() => onOpenFinding && onOpenFinding(h.finding_id)}
                    disabled={!onOpenFinding}
                    style={{ cursor: onOpenFinding ? "pointer" : "default" }}
                  >⚑ {h.finding_id}</button>
                )}
              </li>
            ))}
          </ol>
        </div>
      )}

      <section className="c4-scene__graph">
        <h3 className="c4-scene__section-h">Architecture graph</h3>
        <C4TierGraph
          model={c4}
          selectedContainer={selectedContainer}
          selectedComponent={selectedComponent}
          overlayC4NodeIds={overlay.c4NodeIds}
          onDrill={onDrill}
          onOpenFinding={onOpenFinding}
        />
      </section>

      {selectedContainer && (
        <section className="c4-scene__drill">
          <h3 className="c4-scene__section-h">
            {visibleContainerChildren.some((c) => c.type === "component")
              ? "Components"
              : "Code elements"}
          </h3>
          {visibleContainerChildren.length === 0 ? (
            <p className="empty-state empty-state--info">
              No grounded components or code elements under this container. L3
              components are blocked by default unless an artifact groups symbols;
              this container renders L2 → L4 with no code anchors indexed.
            </p>
          ) : (
            <ul className="c4-node-list">
              {visibleContainerChildren.map((n) => <NodeRow key={n.id} n={n} />)}
            </ul>
          )}
        </section>
      )}
    </div>
  );
}

window.C4 = C4;
