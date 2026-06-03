/* eslint-disable */
// Findings screen — two-pane mail-app style with filters + search.
// Tweakable layout: 'two-pane' | 'stacked' | 'table'

function Findings({ data, selectedId, onSelect, layout = "two-pane", initialFilter = null }) {
  const [q, setQ] = useState("");
  const [sevFilter, setSevFilter] = useState(initialFilter?.severity || new Set());
  const [tierFilter, setTierFilter] = useState(new Set());
  const [dispFilter, setDispFilter] = useState(new Set());

  const findings = data.findings;

  const toggle = (setter) => (val) => setter((cur) => {
    const next = new Set(cur);
    next.has(val) ? next.delete(val) : next.add(val);
    return next;
  });

  const filtered = useMemo(() => {
    let list = findings;
    if (sevFilter.size) list = list.filter((f) => sevFilter.has(f.severity));
    if (tierFilter.size) list = list.filter((f) => tierFilter.has(f.tier));
    if (dispFilter.size) list = list.filter((f) => dispFilter.has(f.disposition));
    if (q.trim()) {
      const term = q.trim().toLowerCase();
      list = list.filter((f) =>
        (f.id + " " + f.title + " " + (f.summary || "") + " " + (f.detail || "") + " " +
          Object.values(f.mappings || {}).flat().join(" ")
        ).toLowerCase().includes(term)
      );
    }
    return list.sort((a, b) => {
      const sevOrder = { critical: 0, high: 1, medium: 2, low: 3, info: 4 };
      if (sevOrder[a.severity] !== sevOrder[b.severity]) return sevOrder[a.severity] - sevOrder[b.severity];
      const tierOrder = { trustworthiness: 0, scalability: 1, auditability: 2 };
      return (tierOrder[a.tier] || 99) - (tierOrder[b.tier] || 99);
    });
  }, [findings, q, sevFilter, tierFilter, dispFilter]);

  const selected = filtered.find((f) => f.id === selectedId) || filtered[0];

  // Toolbar (shared by all layouts)
  const Toolbar = () => (
    <div className="findings__toolbar">
      <div className="findings__search">
        <input
          className="input"
          placeholder="Search findings, IDs, mappings…"
          value={q}
          onChange={(e) => setQ(e.target.value)}
        />
      </div>
      <div className="findings__filters">
        <span className="findings__filter-label">Severity</span>
        {["high", "medium", "low"].map((sev) => (
          <button
            key={sev}
            className={`chip ${sevFilter.has(sev) ? "chip--active" : ""}`}
            onClick={() => toggle(setSevFilter)(sev)}
          >{sev}</button>
        ))}
      </div>
      <div className="findings__filters">
        <span className="findings__filter-label">Tier</span>
        {Object.keys(TIER_LABELS).map((t) => (
          <button
            key={t}
            className={`chip ${tierFilter.has(t) ? "chip--active" : ""}`}
            onClick={() => toggle(setTierFilter)(t)}
          >{TIER_LABELS[t]}</button>
        ))}
      </div>
      <div className="findings__filters">
        <span className="findings__filter-label">Disposition</span>
        {["gap", "blocked", "risk", "ok"].map((d) => (
          <button
            key={d}
            className={`chip ${dispFilter.has(d) ? "chip--active" : ""}`}
            onClick={() => toggle(setDispFilter)(d)}
          >{d}</button>
        ))}
      </div>
      <div className="findings__layout-select">
        <label>
          Layout&nbsp;
          <select
            value={layout}
            onChange={(e) => {
              const ev = new CustomEvent("apd:setLayout", { detail: e.target.value });
              window.dispatchEvent(ev);
            }}
          >
            <option value="two-pane">Two-pane</option>
            <option value="stacked">Stacked</option>
            <option value="table">Table</option>
          </select>
        </label>
      </div>
    </div>
  );

  // ── Stacked layout ──
  if (layout === "stacked") {
    return (
      <div className="findings findings--stacked">
        <div className="findings__pane" style={{ marginBottom: "var(--space-4)" }}>
          <Toolbar />
          <div className="findings__count">
            Showing {filtered.length} of {findings.length} findings — stacked detail
          </div>
        </div>
        <div className="findings-stack">
          {filtered.map((f) => <FindingDetail key={f.id} finding={f} embedded />)}
        </div>
      </div>
    );
  }

  // ── Table layout ──
  if (layout === "table") {
    return (
      <div className="findings findings--table">
        <div className="findings__pane" style={{ marginBottom: "var(--space-4)" }}>
          <Toolbar />
          <div className="findings__count">
            Showing {filtered.length} of {findings.length} findings — table view
          </div>
        </div>
        <div className="findings-table-wrap">
          <table className="findings-table">
            <thead>
              <tr>
                <th>ID</th>
                <th>Sev</th>
                <th>Goal · Tier</th>
                <th>Disp</th>
                <th>Title</th>
                <th>Mappings</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((f) => (
                <tr key={f.id} onClick={() => onSelect(f.id)} style={{ cursor: "pointer" }}>
                  <td className="mono">{f.id}</td>
                  <td><SeverityPill value={f.severity} /></td>
                  <td>{GOAL_LABELS[f.goal]} <span style={{ color: "var(--ink-3)" }}>· {TIER_LABELS[f.tier]}</span></td>
                  <td><DispositionMark value={f.disposition} /></td>
                  <td>{f.title}</td>
                  <td>
                    <div className="tagrow">
                      {(f.mappings?.nist || []).slice(0, 3).map((id) => <TaxonomyTag key={id} id={id} />)}
                      {(f.mappings?.attack || []).slice(0, 2).map((id) => <TaxonomyTag key={id} id={id} />)}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    );
  }

  // ── Two-pane (default) ──
  return (
    <div className="findings">
      <div className="findings__pane">
        <Toolbar />
        <div className="findings__count">
          {filtered.length} of {findings.length} findings
        </div>
        <div className="findings__list">
          {filtered.map((f) => (
            <div
              key={f.id}
              className={`finding-row finding-row--${f.severity} ${selected?.id === f.id ? "finding-row--active" : ""}`}
              onClick={() => onSelect(f.id)}
            >
              <div className="finding-row__rail" />
              <div className="finding-row__body">
                <div className="finding-row__topline">
                  <span className="finding-row__id">{f.id}</span>
                  <span>{GOAL_SHORT[f.goal]}</span>
                </div>
                <div className="finding-row__title">{f.title}</div>
                <div className="finding-row__meta">
                  <SeverityPill value={f.severity} />
                  <DispositionMark value={f.disposition} />
                  {f.headline && <span className="pill" style={{ borderColor: "var(--accent)", color: "var(--accent)" }}>headline #{f.headline_rank}</span>}
                </div>
              </div>
            </div>
          ))}
          {!filtered.length && <div className="empty-state">No findings match these filters.</div>}
        </div>
      </div>

      <div className="finding-detail">
        {selected ? <FindingDetail finding={selected} /> : <div className="empty-state">Select a finding</div>}
      </div>
    </div>
  );
}

// ── Reusable finding detail (used by two-pane, stacked, and from Overview) ─
function FindingDetail({ finding, embedded = false }) {
  const f = finding;
  const Wrapper = embedded ? "div" : React.Fragment;
  const wrapperProps = embedded ? { className: "finding-detail" } : {};

  return (
    <Wrapper {...wrapperProps}>
      <div className="finding-detail__head">
        <div className="finding-detail__head-row">
          <CopyPill value={f.id} modifier="finding-detail__id" />
          <span>·</span>
          <span>{GOAL_LABELS[f.goal]}</span>
          <span>·</span>
          <span>{TIER_LABELS[f.tier]}</span>
          {f.headline && (
            <>
              <span>·</span>
              <span style={{ color: "var(--accent)" }}>headline #{f.headline_rank}</span>
            </>
          )}
        </div>
        <h2 className="finding-detail__title">{f.title}</h2>
        <div className="finding-detail__chips">
          <SeverityPill value={f.severity} />
          <span className="pill"><strong style={{ color: "var(--ink)" }}>{f.confidence}</strong>&nbsp;confidence</span>
          <DispositionMark value={f.disposition} />
          {f.lens_perspectives?.length > 0 && (
            <span className="pill" style={{ borderColor: "var(--accent)", color: "var(--accent)" }}>
              ⌬ {f.lens_perspectives.length} lens perspectives
            </span>
          )}
        </div>
      </div>

      <div className="finding-detail__body">
        {f.rubric_clause && (
          <section className="finding-detail__block">
            <div className="finding-detail__block-head"><span>Rubric clause</span></div>
            <p style={{ color: "var(--ink-2)", fontSize: "var(--text-sm)", fontStyle: "italic", lineHeight: 1.55 }}>{f.rubric_clause}</p>
          </section>
        )}

        {f.summary && (
          <section className="finding-detail__block">
            <div className="finding-detail__block-head"><span>Summary</span></div>
            <p>{f.summary}</p>
          </section>
        )}

        {f.detail && (
          <section className="finding-detail__block">
            <div className="finding-detail__block-head"><span>Detail</span></div>
            <p>{f.detail}</p>
          </section>
        )}

        {f.disposition === "blocked" && f.prerequisite_evidence?.length > 0 && (
          <section className="finding-detail__block">
            <div className="finding-detail__block-head"><span>Prerequisite evidence</span><span className="disposition disposition--blocked"><span className="disposition__sigil" />blocked</span></div>
            <ul style={{ margin: 0, paddingLeft: 18, fontSize: "var(--text-sm)", color: "var(--ink-2)", lineHeight: 1.6 }}>
              {f.prerequisite_evidence.map((p, i) => <li key={i}>{p}</li>)}
            </ul>
          </section>
        )}

        {f.evidence?.length > 0 && (
          <section className="finding-detail__block">
            <div className="finding-detail__block-head"><span>Evidence</span><span style={{ color: "var(--ink-3)" }}>{f.evidence.length}</span></div>
            <div className="finding-detail__evidence">
              {f.evidence.map((e, i) => (
                <div key={i} className="evidence-item">
                  <div className="evidence-item__where">
                    <strong>{e.artifact}</strong><br />{e.locator}
                  </div>
                  <div className="evidence-item__excerpt">"{e.excerpt}"</div>
                </div>
              ))}
            </div>
          </section>
        )}

        {f.recommendation && (
          <section className="finding-detail__block">
            <div className="finding-detail__block-head"><span>Recommendation</span></div>
            <div className="recommendation">
              {f.recommendation.posture && (
                <div className="recommendation__posture">{f.recommendation.posture}</div>
              )}
              <p style={{ color: "var(--ink-2)", fontSize: "var(--text-sm)", lineHeight: 1.55 }}>{f.recommendation.detail}</p>
            </div>
          </section>
        )}

        {(f.mappings?.nist?.length || f.mappings?.attack?.length || f.mappings?.cwe?.length || f.mappings?.owasp_api?.length || f.mappings?.owasp?.length || f.mappings?.atlas?.length) > 0 && (
          <section className="finding-detail__block">
            <div className="finding-detail__block-head"><span>Control mappings</span></div>
            {f.mappings?.nist?.length > 0 && (
              <dl className="mapping-group"><dt>NIST 800-53r5</dt><dd><TagRow ids={f.mappings.nist} /></dd></dl>
            )}
            {f.mappings?.attack?.length > 0 && (
              <dl className="mapping-group"><dt>MITRE ATT&CK</dt><dd><TagRow ids={f.mappings.attack} /></dd></dl>
            )}
            {f.mappings?.cwe?.length > 0 && (
              <dl className="mapping-group"><dt>CWE</dt><dd><TagRow ids={f.mappings.cwe} /></dd></dl>
            )}
            {f.mappings?.owasp_api?.length > 0 && (
              <dl className="mapping-group"><dt>OWASP API</dt><dd><TagRow ids={f.mappings.owasp_api} /></dd></dl>
            )}
            {f.mappings?.owasp?.length > 0 && (
              <dl className="mapping-group"><dt>OWASP Top 10</dt><dd><TagRow ids={f.mappings.owasp} /></dd></dl>
            )}
            {f.mappings?.atlas?.length > 0 && (
              <dl className="mapping-group"><dt>MITRE ATLAS</dt><dd><TagRow ids={f.mappings.atlas} /></dd></dl>
            )}
          </section>
        )}

        {f.lens_perspectives?.length > 0 && (
          <section className="finding-detail__block">
            <div className="finding-detail__block-head"><span>Lens perspectives merged</span></div>
            <div className="tagrow">
              {f.lens_perspectives.map((id) => (
                <span key={id} className="pill" style={{ fontSize: "10.5px" }}>{id}</span>
              ))}
            </div>
          </section>
        )}
      </div>
    </Wrapper>
  );
}

window.Findings = Findings;
window.FindingDetail = FindingDetail;
