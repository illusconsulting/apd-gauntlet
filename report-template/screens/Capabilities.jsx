/* eslint-disable */
// Capabilities screen — three-column tier grid, then strengths-with-caveats

function Capabilities({ data }) {
  // group capabilities by tier+goal
  const grouped = {};
  for (const tier of Object.keys(TIER_GOALS)) {
    grouped[tier] = {};
    for (const goal of TIER_GOALS[tier]) {
      grouped[tier][goal] = data.capabilities.filter((c) => c.tier === tier && c.goal === goal);
    }
  }
  const totalsByMaturity = data.summary.capabilitiesByMaturity;

  return (
    <div>
      <div className="section-eyebrow">§ 2 — Confirmed Security Posture</div>
      <h2 className="section-title">Capabilities by tier</h2>

      <p style={{ color: "var(--ink-2)", maxWidth: "72ch", marginBottom: "var(--space-5)", lineHeight: 1.6 }}>
        {data.summary.capabilities_total} confirmed capabilities cluster into a coherent defense across the three APD tiers — <strong>{totalsByMaturity.tested}</strong> at <em>tested</em> maturity, <strong>{totalsByMaturity.implemented}</strong> at <em>implemented</em>, <strong>{totalsByMaturity.designed}</strong> at <em>designed</em>. Cross-lens merged capabilities are highlighted with an accent border.
      </p>

      <div className="cap-grid">
        {Object.keys(TIER_GOALS).map((tier) => (
          <div key={tier} className="cap-tier">
            <div className="cap-tier__head">{TIER_LABELS[tier]}</div>
            {TIER_GOALS[tier].map((goal) => (
              <div key={goal} className="cap-goal">
                <div className="cap-goal__head">
                  <span>{GOAL_LABELS[goal]}</span>
                  <span>{grouped[tier][goal].length}</span>
                </div>
                {grouped[tier][goal].map((cap) => (
                  <div
                    key={cap.id}
                    className={`cap-card cap-card--${cap.maturity} ${cap.merged ? "cap-card--merged" : ""}`}
                  >
                    <div className="cap-card__rail" />
                    <div>
                      <div className="cap-card__title">{cap.title}</div>
                      <div className="cap-card__id mono">
                        <CopyPill value={cap.id} />
                      </div>
                      <div className="cap-card__scope">{cap.scope}</div>
                      <div className="cap-card__foot">
                        <MaturityMark value={cap.maturity} />
                        {cap.merged && cap.cross_lens && (
                          <div className="cap-card__lenses">
                            {cap.cross_lens.map((l) => (
                              <span key={l} className="cap-card__lens-pill">{GOAL_SHORT[l] || l}</span>
                            ))}
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            ))}
          </div>
        ))}
      </div>

      {/* Strengths-notwithstanding-gaps */}
      <section style={{ marginTop: "var(--space-7)" }}>
        <div className="section-eyebrow">§ 6 — Strengths-Notwithstanding-Gaps</div>
        <h2 className="section-title">Confirmed capabilities with material caveats</h2>
        <p style={{ color: "var(--ink-2)", maxWidth: "72ch", marginBottom: "var(--space-4)", lineHeight: 1.6 }}>
          These capabilities are real but carry caveats reviewers should note — surfaced separately because the caveats bound their scope.
        </p>
        {data.strengths.map((s) => {
          const cap = data.capabilities.find((c) => c.id === s.id);
          return (
            <article key={s.id} className="strength">
              <header className="strength__head">
                <div>
                  <div className="strength__title">{cap?.title || s.id}</div>
                  <div style={{ fontFamily: "var(--font-mono)", fontSize: "var(--text-xs)", color: "var(--ink-3)", marginTop: 2 }}>
                    <CopyPill value={s.id} /> · {GOAL_LABELS[s.goal]} · <MaturityMark value={s.maturity} />
                  </div>
                </div>
              </header>
              <ul className="strength__caveats">
                {s.caveats.map((c, i) => <li key={i}><span /><span>{c}</span></li>)}
              </ul>
            </article>
          );
        })}
      </section>
    </div>
  );
}

window.Capabilities = Capabilities;
