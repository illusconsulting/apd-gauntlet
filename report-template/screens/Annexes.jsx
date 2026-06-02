/* eslint-disable */
// Annexes screen — contradictions + severity disagreements (and link back to strengths)

function Annexes({ data, onOpenFinding }) {
  return (
    <div>
      <div className="section-eyebrow">§ 5 + § 10 — Annexes</div>
      <h2 className="section-title">Contradictions &amp; severity disagreements</h2>

      <section className="annex">
        <header className="annex__head">
          <div>
            <div className="section-eyebrow" style={{ margin: 0 }}>§ 5 — Contradiction annex</div>
            <h3 style={{ fontFamily: "var(--font-display)", fontSize: "var(--text-xl)", marginTop: 4 }}>Finding ⇄ Capability conflicts</h3>
          </div>
          <span className="pill">{data.contradictions.length} surfaced</span>
        </header>
        {data.contradictions.length > 0 && (
          <p style={{ color: "var(--ink-2)", maxWidth: "72ch", marginBottom: "var(--space-4)", lineHeight: 1.6 }}>
            Cases where a finding asserts a property is absent and a capability confirms it is present, or vice versa. In all three cases here, the recommended disposition is <strong>scope clarification of the capability</strong>, not capability downgrade — these indicate language that could be over-read by a reviewer outside the architectural context.
          </p>
        )}
        {data.contradictions.length === 0 && (
          <p className="empty-state">
            {data.contradictions_notes
              ? data.contradictions_notes
              : "No contradictions surfaced."}
          </p>
        )}

        {data.contradictions.map((c) => (
          <div key={c.id} className="contradiction">
            <div className="contradiction__id"><CopyPill value={c.id} /></div>
            <div className="contradiction__col">
              <div className="contradiction__label">Finding asserts</div>
              <CopyPill value={c.finding.id} />
              <div className="contradiction__assertion">"{c.finding.assertion}"</div>
            </div>
            <div className="contradiction__col">
              <div className="contradiction__label">Capability asserts</div>
              {(c.capability.ids || [c.capability.id]).map((cid) => (
                <CopyPill key={cid} value={cid} />
              ))}
              <div className="contradiction__assertion">"{c.capability.assertion}"</div>
            </div>
            <div className="contradiction__resolution">
              <div className="contradiction__label" style={{ marginBottom: 4 }}>Comparison &amp; resolution</div>
              <div>{c.comparison}</div>
              <div style={{ marginTop: "var(--space-2)", color: "var(--ink)" }}><strong>→</strong> {c.resolution}</div>
            </div>
          </div>
        ))}
      </section>

      <section className="annex">
        <header className="annex__head">
          <div>
            <div className="section-eyebrow" style={{ margin: 0 }}>§ 10 — Severity disagreement annex</div>
            <h3 style={{ fontFamily: "var(--font-display)", fontSize: "var(--text-xl)", marginTop: 4 }}>Within-cluster lens disagreements</h3>
          </div>
          <span className="pill">{data.severity_disagreements.length} clusters</span>
        </header>
        {data.severity_disagreements.length > 0 && (
          <p style={{ color: "var(--ink-2)", maxWidth: "72ch", marginBottom: "var(--space-4)", lineHeight: 1.6 }}>
            Records where two agents agreed on the concern but disagreed on severity. The merged finding takes the higher severity per the synthesis rule; the disagreement is preserved here for transparency.
          </p>
        )}
        {data.severity_disagreements.length === 0 && (
          <p className="empty-state">
            {data.severity_disagreements_notes
              ? data.severity_disagreements_notes
              : "No severity disagreements surfaced."}
          </p>
        )}

        {data.severity_disagreements.map((d) => (
          <div key={d.id} className="sev-disagreement">
            <header className="sev-disagreement__head">
              <span
                className="pill pill--id pill--clickable"
                onClick={() => onOpenFinding(d.id)}
                style={{ fontSize: "var(--text-sm)" }}
              >{d.id} →</span>
              <span style={{ fontFamily: "var(--font-mono)", fontSize: "var(--text-xs)", color: "var(--ink-3)" }}>
                chosen → <SeverityPill value={d.chosen} />
              </span>
            </header>
            <dl className="sev-disagreement__lenses">
              {d.agents.map((a) => (
                <React.Fragment key={a.lens}>
                  <dt>{a.lens}</dt>
                  <dd><SeverityPill value={a.severity} /></dd>
                </React.Fragment>
              ))}
            </dl>
            <div className="sev-disagreement__rationale">"{d.rationale}"</div>
          </div>
        ))}
      </section>

      {/* Domain-pack calibration caveat */}
      {data.domain_pack_caveat && (
        <section className="annex">
          <header className="annex__head">
            <div>
              <div className="section-eyebrow" style={{ margin: 0 }}>Domain-pack calibration caveat</div>
              <h3 style={{ fontFamily: "var(--font-display)", fontSize: "var(--text-xl)", marginTop: 4 }}>{data.domain_pack_caveat.title || "Domain-pack scope"}</h3>
            </div>
            <span className="pill" style={{ borderColor: "var(--sev-medium)", color: "var(--sev-medium)" }}>
              quick-path tradeoff
            </span>
          </header>
          <p style={{ color: "var(--ink-2)", maxWidth: "72ch", lineHeight: 1.65 }}>
            {data.domain_pack_caveat.body}
          </p>
        </section>
      )}
    </div>
  );
}

window.Annexes = Annexes;
