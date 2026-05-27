/* eslint-disable */
// Overview screen — exec summary, headline numbers, posture summary, headline findings, next steps

function Overview({ data, onOpenFinding, onNavigate }) {
  const s = data.summary;

  return (
    <div className="overview">
      {/* Main column */}
      <div className="overview__main">
        {/* Exec summary */}
        <section>
          <div className="section-eyebrow">§ 1 — Executive Summary</div>
          <article className="exec-summary">
            {(data.exec_summary || []).map((p, i) => (
              <p key={i}>{p}</p>
            ))}
          </article>
        </section>

        {/* Headline numbers */}
        <section>
          <div className="headline-grid">
            <div className="headline-grid__cell">
              <div className="headline-grid__label">Findings</div>
              <div className="headline-grid__num">{s.findings_total}</div>
              <div className="headline-grid__breakdown">
                <span>{s.bySeverity.high} high</span>
                <span>·</span>
                <span>{s.bySeverity.medium} med</span>
                <span>·</span>
                <span>{s.bySeverity.low} low</span>
              </div>
            </div>
            <div className="headline-grid__cell">
              <div className="headline-grid__label">Capabilities</div>
              <div className="headline-grid__num">{s.capabilities_total}</div>
              <div className="headline-grid__breakdown">
                <span>{s.capabilitiesByMaturity.tested} tested</span>
                <span>·</span>
                <span>{s.capabilitiesByMaturity.implemented} impl</span>
                <span>·</span>
                <span>{s.capabilitiesByMaturity.designed} design</span>
              </div>
            </div>
            <div className="headline-grid__cell">
              <div className="headline-grid__label">Blocked-on-Evidence</div>
              <div className="headline-grid__num">{s.byDisposition.blocked}</div>
              <div className="headline-grid__breakdown">
                <span>prerequisite artifacts</span>
              </div>
            </div>
            <div className="headline-grid__cell">
              <div className="headline-grid__label">Contradictions</div>
              <div className="headline-grid__num">{s.contradictions} <small>+ {s.severity_disagreements} sev-disagree</small></div>
              <div className="headline-grid__breakdown">
                <span>all scope-clarification</span>
              </div>
            </div>
          </div>
        </section>

        {/* Tier posture */}
        <section>
          <div className="section-eyebrow">§ 2 — Confirmed Security Posture</div>
          <h2 className="section-title">Posture by tier</h2>
          <div className="tier-summary">
            {Object.entries(TIER_GOALS).map(([tier, goals]) => {
              const caps = data.capabilities.filter((c) => c.tier === tier);
              const findings = data.findings.filter((f) => f.tier === tier);
              const high = findings.filter((f) => f.severity === "high").length;
              return (
                <div key={tier} className="tier-card">
                  <div className="tier-card__name">{TIER_LABELS[tier]}</div>
                  <div className="tier-card__goals">
                    {goals.map((g) => GOAL_LABELS[g]).join(" · ")}
                  </div>
                  <div className="tier-card__row">
                    <span>Capabilities</span><span>{caps.length}</span>
                  </div>
                  <div className="tier-card__row">
                    <span>Findings</span><span>{findings.length}</span>
                  </div>
                  <div className="tier-card__row">
                    <span>High severity</span><span>{high}</span>
                  </div>
                </div>
              );
            })}
          </div>
        </section>

        {/* Headline findings */}
        <section>
          <div className="section-eyebrow">§ 4 — Findings · Headline top 10 (severity × confidence)</div>
          <h2 className="section-title">Priority findings</h2>
          <div className="headlines">
            {data.findings
              .filter((f) => f.headline)
              .sort((a, b) => a.headline_rank - b.headline_rank)
              .map((f) => (
                <div
                  key={f.id}
                  className={`headline-row finding-row--${f.severity}`}
                  onClick={() => onOpenFinding(f.id)}
                >
                  <div className="headline-row__rank">{String(f.headline_rank).padStart(2, "0")}</div>
                  <div className="headline-row__id">{f.id}</div>
                  <div><SeverityPill value={f.severity} /></div>
                  <div className="headline-row__title">{f.title}</div>
                  <div className="headline-row__chev">→</div>
                </div>
              ))}
          </div>
        </section>

        {/* Next steps */}
        <section>
          <div className="section-eyebrow">Reviewer priority ordering</div>
          <h2 className="section-title">Next steps</h2>
          <ol className="next-steps">
            {data.next_steps.map((step) => (
              <li key={step.rank} className="next-step">
                <div className="next-step__rank">{String(step.rank).padStart(2, "0")}</div>
                <div className="next-step__text">{step.text}</div>
                <div className="next-step__refs">
                  {step.refs.slice(0, 4).map((id) => (
                    <span
                      key={id}
                      className="pill pill--id pill--clickable"
                      onClick={() => onOpenFinding(id)}
                      style={{ fontSize: "10px" }}
                    >
                      {id}
                    </span>
                  ))}
                </div>
              </li>
            ))}
          </ol>
        </section>
      </div>

      {/* Right rail */}
      <aside className="overview__rail">
        <div className="rail-card">
          <div className="rail-card__head">Run · <small>{data.meta.run_id}</small></div>
          <dl className="kv">
            <dt>Subject</dt><dd>{data.meta.subject}</dd>
            <dt>Date</dt><dd className="mono">{data.meta.date}</dd>
            <dt>Framework</dt><dd className="mono">v{data.meta.framework_version}</dd>
            <dt>Domain pack</dt><dd className="mono">{data.meta.domain_pack.name} v{data.meta.domain_pack.version}</dd>
            <dt>Synthesizer</dt><dd className="mono">v{data.meta.synthesizer_version}</dd>
            <dt>Artifacts</dt><dd>{data.meta.artifact_count} ({data.meta.artifact_types.join(", ")})</dd>
            <dt>Specialists</dt><dd>9 / 9</dd>
          </dl>
        </div>

        <div className="rail-card">
          <div className="rail-card__head">Severity distribution</div>
          <div className="bar" style={{ height: 8, marginBottom: "var(--space-3)" }}>
            <span style={{ flex: s.bySeverity.critical, background: "var(--sev-critical)" }} />
            <span style={{ flex: s.bySeverity.high, background: "var(--sev-high)" }} />
            <span style={{ flex: s.bySeverity.medium, background: "var(--sev-medium)" }} />
            <span style={{ flex: s.bySeverity.low, background: "var(--sev-low)" }} />
            <span style={{ flex: s.bySeverity.info, background: "var(--sev-info)" }} />
          </div>
          <ul className="rail-list">
            <li><SeverityPill value="critical" /><span style={{ marginLeft: "auto" }} className="mono">{s.bySeverity.critical}</span></li>
            <li><SeverityPill value="high" /><span style={{ marginLeft: "auto" }} className="mono">{s.bySeverity.high}</span></li>
            <li><SeverityPill value="medium" /><span style={{ marginLeft: "auto" }} className="mono">{s.bySeverity.medium}</span></li>
            <li><SeverityPill value="low" /><span style={{ marginLeft: "auto" }} className="mono">{s.bySeverity.low}</span></li>
          </ul>
        </div>

        <div className="rail-card">
          <div className="rail-card__head">Posture summary</div>
          <dl className="kv">
            <dt>Trustworthiness</dt><dd>{data.posture_summary?.trustworthiness || "—"}</dd>
            <dt>Scalability</dt><dd>{data.posture_summary?.scalability || "—"}</dd>
            <dt>Auditability</dt><dd>{data.posture_summary?.auditability || "—"}</dd>
          </dl>
        </div>

        <div className="rail-card">
          <div className="rail-card__head">Crown jewels</div>
          <ul className="rail-list">
            {data.meta.crown_jewels.map((cj) => (
              <li key={cj} className="mono" style={{ fontSize: "11px" }}>◆ {cj}</li>
            ))}
          </ul>
        </div>

        <div className="rail-card">
          <div className="rail-card__head">Attacker positions</div>
          <ul className="rail-list">
            {data.meta.attacker_positions.map((ap) => (
              <li key={ap} className="mono" style={{ fontSize: "11px" }}>⌐ {ap}</li>
            ))}
          </ul>
        </div>
      </aside>
    </div>
  );
}

window.Overview = Overview;
