// report-template/screens/AttackPaths.jsx
/* eslint-disable */
// Attack Paths screen — Mermaid asset graph + per-pair path list + D3FEND overlay.

function AttackPaths({ data }) {
  const ap = data.attack_paths;
  const taxonomy = data.taxonomy || {};
  const mermaidRef = React.useRef(null);

  React.useEffect(() => {
    if (!ap || !window.mermaid || !mermaidRef.current) return;
    // securityLevel 'strict' makes Mermaid sanitize labels/text via its own
    // dompurify pass before producing SVG. The asset-graph YAML is
    // adopter-controlled, so the SVG mermaid produces can in principle
    // include adversarial markup if we render it raw — 'strict' closes that.
    window.mermaid.initialize({ startOnLoad: false, theme: "neutral", securityLevel: "strict" });
    window.mermaid
      .render("apd-asset-graph", ap.mermaid)
      .then(({ svg }) => {
        // Parse the sanitized SVG string into a DOM node and append it,
        // rather than assigning innerHTML, so any residual script-like
        // attributes are filtered by the SVG parser context.
        const parser = new DOMParser();
        const doc = parser.parseFromString(svg, "image/svg+xml");
        const node = doc.documentElement;
        mermaidRef.current.replaceChildren(node);
      })
      .catch((e) => { mermaidRef.current.textContent = "Graph render failed: " + e.message; });
  }, [ap]);

  if (!ap) {
    return (
      <div className="empty-state">
        <p>Attack paths were not computed for this run. Declare crown_jewels and
        attacker_positions in the domain pack or .apd-run.yaml to enable
        analysis.</p>
      </div>
    );
  }

  return (
    <div className="attack-paths">
      <div className="section-eyebrow">§ Attack paths — §1.4 v1.4 enumeration</div>
      <h2 className="section-title">Attacker → Crown jewel paths · {ap.summary.total_pairs} pairs · {ap.summary.total_paths} paths · {ap.summary.bottleneck_count} bottleneck edges</h2>

      <section className="attack-paths__graph">
        <h3 className="attack-paths__section-h">Asset graph</h3>
        <div ref={mermaidRef} className="attack-paths__mermaid" />
      </section>

      <section className="attack-paths__pairs">
        <h3 className="attack-paths__section-h">Enumerated paths</h3>
        {ap.pairs.length === 0 && (
          <p className="empty-state empty-state--info">
            {ap.pairs_empty_explanation
              ? ap.pairs_empty_explanation
              : "No attacker → crown-jewel paths were enumerated for this run."}
          </p>
        )}
        {ap.pairs.map((pair, idx) => (
          <details key={idx} className="attack-pair">
            <summary>
              <span className="mono">{pair.attacker_position}</span>
              <span className="attack-pair__arrow"> → </span>
              <span className="mono">{pair.crown_jewel}</span>
              <span className="attack-pair__count">{pair.paths.length} path{pair.paths.length === 1 ? "" : "s"}</span>
            </summary>
            <ul className="attack-pair__paths">
              {pair.paths.map((p) => (
                <li key={p.path_id} className={`attack-path attack-path--${p.feasibility || "unknown"}`}>
                  <div className="attack-path__head">
                    <span className="mono">{p.path_id}</span>
                    <span>hop {p.hop_count}</span>
                    <span>sev sum {p.severity_sum}</span>
                    <span>{p.mitigation_count} mitigations</span>
                  </div>
                  <ol className="attack-path__edges">
                    {p.edges.map((eid) => (
                      <li
                        key={eid}
                        className={p.bottleneck_edges.includes(eid) ? "attack-path__edge--bottleneck" : ""}
                      >
                        <span className="mono">{eid}</span>
                      </li>
                    ))}
                  </ol>
                </li>
              ))}
            </ul>
          </details>
        ))}
      </section>

      <section className="attack-paths__overlays">
        <h3 className="attack-paths__section-h">D3FEND defensive overlay</h3>
        {ap.bottleneck_overlays.length === 0 && (
          <p className="empty-state">No bottleneck overlays — no edge crossed the bottleneck threshold.</p>
        )}
        {ap.bottleneck_overlays.map((o) => (
          <div key={o.edge_id} className="overlay-card">
            <div className="overlay-card__head">
              <span className="mono">{o.edge_id}</span>
              <span>{o.paths_traversing} paths traverse</span>
            </div>
            <div className="overlay-card__row">
              <div className="overlay-card__label">Counters ATT&CK</div>
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
