// report-template/screens/AttackPaths.jsx
/* eslint-disable */
// Attack Paths screen — Cytoscape asset graph + per-pair path list + D3FEND overlay.
// The interactive graph render + zoom toolbar live in the shared GraphView component
// (components.jsx, exported on window). Clicking a node highlights its path(s);
// clicking an "Enumerated paths" row cross-highlights the graph (two-way link).

function AttackPaths({ data, onOpenFinding }) {
  const ap = data.attack_paths;
  const taxonomy = data.taxonomy || {};

  const [selectedPathId, setSelectedPathId] = React.useState(null);
  const paths = (ap && ap.pairs || []).flatMap((pair) =>
    (pair.paths || []).map((p) => ({ id: p.path_id, edgeIds: p.edges || [] })));

  if (!ap) {
    return (
      <div className="empty-state">
        <p>Attack paths were not computed for this run. Declare crown_jewels and
        attacker_positions in the domain pack or .apd-run.yaml to enable
        analysis.</p>
      </div>
    );
  }

  // Compute asset graph summary line.
  const gs = ap.asset_graph_summary || {};
  const nodeCount = gs.node_count || 0;
  const edgeCount = gs.edge_count || 0;
  const atkCount  = gs.attacker_position_count || 0;
  const jewCount  = gs.crown_jewel_count || 0;
  const astCount  = gs.asset_count || 0;
  const idnCount  = gs.identity_count || 0;
  const otherCount = nodeCount - atkCount - jewCount - astCount - idnCount;
  const tbEdges   = gs.trust_boundary_edge_count || 0;
  const findEdges = gs.finding_derived_edge_count || 0;
  const capEdges  = gs.capability_derived_edge_count || 0;

  // Edge type chip. When `onActivate` is supplied (finding-derived edges, given a
  // finding id + a navigation handler) the chip becomes a button that opens the
  // associated finding in the Findings view; otherwise it is a static label.
  function EdgeTypeChip({ type, onActivate }) {
    const styles = {
      trust_boundary:          { background: "var(--paper-2)", color: "var(--ink-3)", border: "1px solid var(--rule)" },
      compromisable_via_finding: { background: "color-mix(in srgb, var(--sev-high) 15%, var(--paper))", color: "var(--sev-high)", border: "1px solid var(--sev-high)" },
      mitigated_by_capability: { background: "color-mix(in srgb, var(--sev-low) 15%, var(--paper))", color: "var(--sev-low)", border: "1px solid var(--sev-low)" },
    };
    const labels = {
      trust_boundary: "trust",
      compromisable_via_finding: "finding",
      mitigated_by_capability: "capability",
    };
    const style = styles[type] || styles.trust_boundary;
    const label = labels[type] || type;
    const clickable = typeof onActivate === "function";
    return (
      <span
        role={clickable ? "button" : undefined}
        tabIndex={clickable ? 0 : undefined}
        title={clickable ? "Open this finding in the Findings view" : undefined}
        onClick={clickable ? (e) => { e.stopPropagation(); onActivate(); } : undefined}
        onKeyDown={clickable ? (e) => {
          if (e.key === "Enter" || e.key === " ") { e.preventDefault(); e.stopPropagation(); onActivate(); }
        } : undefined}
        style={{
        ...style,
        fontFamily: "var(--font-mono)",
        fontSize: "10px",
        padding: "1px 5px",
        borderRadius: "3px",
        whiteSpace: "nowrap",
        letterSpacing: "0.03em",
        cursor: clickable ? "pointer" : "default",
        textDecoration: clickable ? "underline" : "none",
      }}>{label}</span>
    );
  }

  return (
    <div className="attack-paths">
      <div className="section-eyebrow">§ Attack paths — §1.4 v1.4 enumeration</div>
      <h2 className="section-title">Attacker → Crown jewel paths · {ap.summary.total_pairs} pairs · {ap.summary.total_paths} paths · {ap.summary.bottleneck_count} bottleneck edges</h2>

      {/* Asset graph summary banner */}
      <div style={{
        fontFamily: "var(--font-mono)",
        fontSize: "var(--text-xs)",
        color: "var(--ink-3)",
        background: "var(--paper-2)",
        border: "1px solid var(--rule)",
        borderRadius: "var(--radius-sm)",
        padding: "var(--space-2) var(--space-3)",
        lineHeight: 1.6,
      }}>
        <strong style={{ color: "var(--ink)" }}>Asset graph:</strong>{" "}
        {nodeCount} node{nodeCount !== 1 ? "s" : ""}{" "}
        ({atkCount} attacker{atkCount !== 1 ? "s" : ""} · {jewCount} crown jewel{jewCount !== 1 ? "s" : ""} · {astCount} asset{astCount !== 1 ? "s" : ""} · {idnCount} ident{idnCount !== 1 ? "ities" : "ity"}{otherCount > 0 ? ` · ${otherCount} other` : ""}),{" "}
        {edgeCount} edge{edgeCount !== 1 ? "s" : ""}{" "}
        ({tbEdges} trust-boundary, {findEdges} finding-derived, {capEdges} capability-derived)
      </div>

      <section className="attack-paths__graph">
        <h3 className="attack-paths__section-h">Asset graph</h3>
        <GraphView graph={ap.graph} layout="dagre" idBase="apd-asset-graph"
          paths={paths} selectedPathId={selectedPathId} onSelectPath={setSelectedPathId} />
      </section>

      {ap.graph_path_focused && (
        <section className="attack-paths__graph">
          <h3 className="attack-paths__section-h">Path-focused graph</h3>
          <GraphView graph={ap.graph_path_focused} layout="dagre" idBase="apd-paths-focused" />
        </section>
      )}

      <section className="attack-paths__pairs">
        <h3 className="attack-paths__section-h">Enumerated paths</h3>
        {ap.pairs.length === 0 && (
          <p className="empty-state empty-state--info">
            {ap.pairs_empty_explanation
              ? ap.pairs_empty_explanation
              : "No attacker → crown-jewel paths were enumerated for this run."}
          </p>
        )}
        {ap.pairs.map((pair, idx) => {
          const atkName  = pair.attacker_position_name || pair.attacker_position;
          const jewName  = pair.crown_jewel_name || pair.crown_jewel;
          const atkId    = pair.attacker_position;
          const jewId    = pair.crown_jewel;
          const showSub  = atkId !== atkName || jewId !== jewName;
          return (
            <details key={idx} className="attack-pair">
              <summary>
                <div style={{ display: "flex", flexDirection: "column", gap: "1px", flex: 1, minWidth: 0 }}>
                  <div style={{ display: "flex", alignItems: "center", gap: "var(--space-2)" }}>
                    <span style={{ fontWeight: 600, color: "var(--ink)" }}>{atkName}</span>
                    <span className="attack-pair__arrow"> → </span>
                    <span style={{ fontWeight: 600, color: "var(--ink)" }}>{jewName}</span>
                  </div>
                  {showSub && (
                    <div style={{ fontFamily: "var(--font-mono)", fontSize: "10px", color: "var(--ink-3)" }}>
                      {atkId} → {jewId}
                    </div>
                  )}
                </div>
                <span className="attack-pair__count">{pair.paths.length} path{pair.paths.length === 1 ? "" : "s"}</span>
              </summary>
              <ul className="attack-pair__paths">
                {pair.paths.map((p) => {
                  // Distinct findings this path traverses (finding-derived edges).
                  const pathFindingIds = [...new Set(
                    (p.edges_detailed || [])
                      .map((e) => e.finding_id)
                      .filter(Boolean)
                  )];
                  return (
                  <li
                    key={p.path_id}
                    className={`attack-path attack-path--${p.feasibility || "unknown"}`}
                    onClick={() => setSelectedPathId(
                      (cur) => cur === p.path_id ? null : p.path_id)}
                    style={{ cursor: "pointer", outline: selectedPathId === p.path_id
                      ? "2px solid var(--accent)" : "none" }}
                  >
                    <div className="attack-path__head">
                      <span
                        style={{
                          fontFamily: "var(--font-mono)",
                          fontSize: "10px",
                          background: "var(--paper-2)",
                          border: "1px solid var(--rule)",
                          borderRadius: "3px",
                          padding: "1px 5px",
                          color: "var(--ink-3)",
                        }}
                      >{p.path_id}</span>
                      <span>hop {p.hop_count}</span>
                      <span>sev sum {p.severity_sum}</span>
                      <span>{p.mitigation_count} mitigations</span>
                      {pathFindingIds.length > 0 && (
                        <span
                          title={`${pathFindingIds.length} associated finding${pathFindingIds.length === 1 ? "" : "s"}: ${pathFindingIds.join(", ")}`}
                          style={{
                            fontFamily: "var(--font-mono)",
                            fontSize: "10px",
                            padding: "1px 6px",
                            borderRadius: "3px",
                            background: "color-mix(in srgb, var(--sev-high) 15%, var(--paper))",
                            color: "var(--sev-high)",
                            border: "1px solid var(--sev-high)",
                            whiteSpace: "nowrap",
                          }}
                        >⚑ {pathFindingIds.length} finding{pathFindingIds.length === 1 ? "" : "s"}</span>
                      )}
                    </div>
                    <ol className="attack-path__edges">
                      {(p.edges_detailed && p.edges_detailed.length > 0
                        ? p.edges_detailed
                        : (p.edges || []).map((eid) => ({ edge_id: eid, from_name: null, to_name: null, edge_type: null, finding_id: null, capability_id: null, is_bottleneck: (p.bottleneck_edges || []).includes(eid) }))
                      ).map((ed) => (
                        <li
                          key={ed.edge_id}
                          className={ed.is_bottleneck ? "attack-path__edge--bottleneck" : ""}
                          style={{
                            display: "flex",
                            flexDirection: "column",
                            gap: "2px",
                            padding: "var(--space-1) 0",
                            borderLeft: ed.is_bottleneck ? "3px solid var(--sev-high)" : "3px solid transparent",
                            paddingLeft: "var(--space-2)",
                          }}
                        >
                          {ed.from_name ? (
                            <div style={{ display: "flex", alignItems: "center", gap: "var(--space-2)", flexWrap: "wrap" }}>
                              <span style={{ fontSize: "var(--text-sm)", color: "var(--ink)" }}>
                                {ed.from_name}
                              </span>
                              <span style={{ color: "var(--ink-3)", fontSize: "var(--text-xs)" }}>→</span>
                              <span style={{ fontSize: "var(--text-sm)", color: "var(--ink)" }}>
                                {ed.to_name}
                              </span>
                              {ed.edge_type && (
                                <EdgeTypeChip
                                  type={ed.edge_type}
                                  onActivate={
                                    ed.edge_type === "compromisable_via_finding" && ed.finding_id && onOpenFinding
                                      ? () => onOpenFinding(ed.finding_id)
                                      : undefined
                                  }
                                />
                              )}
                              {ed.finding_id && <CopyPill value={ed.finding_id} />}
                              {ed.capability_id && <CopyPill value={ed.capability_id} />}
                            </div>
                          ) : (
                            <span className="mono" style={{ fontSize: "var(--text-xs)" }}>{ed.edge_id}</span>
                          )}
                          <span style={{ fontFamily: "var(--font-mono)", fontSize: "10px", color: "var(--ink-3)" }}>
                            {ed.edge_id}
                          </span>
                        </li>
                      ))}
                    </ol>
                  </li>
                  );
                })}
              </ul>
            </details>
          );
        })}
      </section>

      <section className="attack-paths__overlays">
        <h3 className="attack-paths__section-h">D3FEND defensive overlay</h3>
        {ap.bottleneck_overlays.length === 0 && (() => {
          const threshold = ap.bottleneck_threshold;
          const maxTraversal = ap.max_edge_traversal_count != null ? ap.max_edge_traversal_count : null;
          return (
            <div style={{
              background: "var(--paper-2)",
              border: "1px solid var(--rule)",
              borderLeft: "3px solid var(--ink-3)",
              borderRadius: "0 var(--radius-sm) var(--radius-sm) 0",
              padding: "var(--space-3) var(--space-4)",
              fontSize: "var(--text-sm)",
              color: "var(--ink-2)",
              lineHeight: "var(--line-loose)",
            }}>
              <strong style={{ color: "var(--ink)" }}>
                Bottleneck threshold: {threshold != null ? threshold : "N/A"} paths-traversing-same-edge.
              </strong>{" "}
              The maximum edge-traversal count in this run was{" "}
              <strong>{maxTraversal != null ? maxTraversal : 0}</strong>
              {threshold != null && maxTraversal != null && maxTraversal < threshold
                ? " (well below threshold)"
                : ""}
              , so no edge qualifies as a bottleneck for D3FEND overlay generation.
              This is expected for runs with sparse path enumeration — when the analyzer
              finds 1–2 distinct paths, no edge is traversed enough to qualify as a
              chokepoint.
            </div>
          );
        })()}
        {ap.bottleneck_overlays.map((o) => (
          <div key={o.edge_id} className="overlay-card">
            <div className="overlay-card__head">
              <span className="mono">{o.edge_id}</span>
              <span>{o.paths_traversing} paths traverse</span>
            </div>
            <div className="overlay-card__row">
              <div className="overlay-card__label">Counters ATT&amp;CK</div>
              <div className="tagrow">
                {(o.exposed_attack_techniques || []).map((t) => (
                  <TaxonomyTag key={t} id={t} />
                ))}
              </div>
            </div>
            <div className="overlay-card__row">
              <div className="overlay-card__label">Candidate D3FEND</div>
              <div className="tagrow">
                {(o.candidate_d3fend || []).map((d) => (
                  <TaxonomyTag key={d.d3fend_id} id={d.d3fend_id} />
                ))}
              </div>
            </div>
            <div className="overlay-card__row">
              <div className="overlay-card__label">Net-new D3FEND</div>
              <div className="tagrow">
                {(o.net_new_d3fend || []).map((d) => (
                  <TaxonomyTag key={d.d3fend_id} id={d.d3fend_id} />
                ))}
                {!o.net_new_d3fend?.length && <span className="mono" style={{ color: "var(--ink-3)" }}>(all candidates backed)</span>}
              </div>
            </div>
          </div>
        ))}
      </section>
    </div>
  );
}

window.AttackPaths = AttackPaths;
