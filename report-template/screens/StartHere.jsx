/* eslint-disable */
// Start-here screen — the reading guide (spec 2026-06-04). Orients a first-time
// reader, decodes the report's vocabulary in place, gives a reading workflow,
// and points each role where to focus. Contextual: reads window.APD_DATA at
// render time. Framework labels come from the shared constants (TIER_LABELS /
// TIER_GOALS / GOAL_LABELS in components.jsx). Pillar VERBS are re-declared
// locally because APD_PILLAR_VERB lives only in Annexes.jsx (not on window).

const SH_TIER_ORDER = ["trustworthiness", "scalability", "auditability"];
const SH_PILLAR_VERB = {
  trustworthiness: "Assure",
  scalability: "Provide",
  auditability: "Demonstrate",
};

// Tab labels + one-line descriptions for the orientation map, keyed by the same
// ids used in app.jsx BASE_TABS so the map mirrors the live tab list.
const SH_TAB_LABEL = {
  overview: "Overview",
  findings: "Findings",
  capabilities: "Capabilities",
  coverage: "Coverage",
  threat_model: "Threat model",
  attack_paths: "Attack paths",
  annexes: "Annexes",
};
const SH_TAB_BLURB = {
  overview: "The executive read — posture summary and the priority findings.",
  findings: "Every gap and risk, filterable; this is where you act.",
  capabilities: "What's already done well, with the gaps noted alongside.",
  coverage: "NIST / APD-goal / taxonomy rollups — what's covered vs. missed.",
  threat_model: "STRIDE surface map of the modeled threats (shown when a model exists).",
  attack_paths: "How an attacker could chain findings toward the crown jewels.",
  annexes: "Contradictions, severity disagreements, and the framework reference.",
};

// The vocabulary rows render the live atoms so the glossary matches exactly
// what the reader sees on the other screens.
function ShGlossary() {
  return (
    <table className="guide-voc">
      <tbody>
        <tr>
          <td><SeverityPill value="critical" /> <SeverityPill value="high" /></td>
          <td><strong>Severity</strong> — impact ranking (critical · high · medium · low · info). <span className="guide-do">Act on critical and high first.</span></td>
        </tr>
        <tr>
          <td><DispositionMark value="gap" /></td>
          <td><strong>Disposition: gap</strong> — a missing control. <span className="guide-do">Remediate.</span></td>
        </tr>
        <tr>
          <td><DispositionMark value="blocked" /></td>
          <td><strong>blocked</strong> — couldn't be assessed; prerequisite evidence is missing. <span className="guide-do">Supply the artifact.</span></td>
        </tr>
        <tr>
          <td><DispositionMark value="risk" /> <DispositionMark value="uncertainty" /></td>
          <td><strong>risk</strong> — a control is present but still carries risk · <strong>uncertainty</strong> — needs investigation.</td>
        </tr>
        <tr>
          <td><span className="tag">conf: high</span></td>
          <td><strong>Confidence</strong> — how sure the reviewer is (high · medium · low).</td>
        </tr>
        <tr>
          <td><MaturityMark value="tested" /></td>
          <td><strong>Maturity</strong> (Capabilities) — designed → implemented → tested → operationalized.</td>
        </tr>
        <tr>
          <td>
            <span className="guide-cell guide-cell--covered">covered</span>{" "}
            <span className="guide-cell guide-cell--both">both</span>
          </td>
          <td><strong>Coverage cells</strong> — covered · gapped · <strong>both</strong> (a finding and a capability collide → scope-clarity debt) · silent (not assessed).</td>
        </tr>
      </tbody>
    </table>
  );
}

function StartHere({ data, onNavigate }) {
  const meta = (data && data.meta) || {};
  const summary = (data && data.summary) || {};
  const sev = summary.bySeverity || {};

  const sections = [
    { id: "orient", label: "Orientation" },
    { id: "vocab", label: "Vocabulary" },
    { id: "use", label: "How to use" },
    { id: "role", label: "For your role" },
  ];
  const [active, setActive] = useState("orient");
  const refs = useRef({});
  const setRef = (id) => (el) => { if (el) refs.current[id] = el; };

  const go = (id) => {
    const el = refs.current[id];
    if (el && el.scrollIntoView) el.scrollIntoView({ behavior: "smooth", block: "start" });
    setActive(id);
  };

  // Scrollspy: highlight the rail anchor for the section nearest the top.
  useEffect(() => {
    const els = sections.map((s) => refs.current[s.id]).filter(Boolean);
    if (!("IntersectionObserver" in window) || !els.length) return;
    const obs = new IntersectionObserver(
      (entries) => {
        const vis = entries
          .filter((e) => e.isIntersecting)
          .sort((a, b) => a.boundingClientRect.top - b.boundingClientRect.top)[0];
        if (vis && vis.target && vis.target.dataset && vis.target.dataset.shSection) {
          setActive(vis.target.dataset.shSection);
        }
      },
      { rootMargin: "-70px 0px -60% 0px", threshold: 0 }
    );
    els.forEach((el) => obs.observe(el));
    return () => obs.disconnect();
  }, []);

  // Which tabs exist for THIS run — mirrors the app.jsx BASE_TABS logic.
  const presentTabs = ["overview", "findings", "capabilities", "coverage"];
  if (data && data.threat_model && data.threat_model.present) presentTabs.push("threat_model");
  presentTabs.push("attack_paths", "annexes");

  const findingsTotal = summary.findings_total;
  const criticalCount = sev.critical;
  const hasTM = !!(data && data.threat_model && data.threat_model.present);
  const hasAP = !!(data && data.attack_paths);

  return (
    <div className="guide">
      <aside className="guide__rail">
        <div className="guide__chip">
          This run
          <strong>{meta.subject || "—"}</strong>
          {meta.domain_pack && meta.domain_pack.name ? (
            <span>
              {meta.domain_pack.name} pack
              {typeof findingsTotal === "number" ? ` · ${findingsTotal} findings` : ""}
            </span>
          ) : null}
        </div>
        <nav className="guide__anchors">
          {sections.map((s) => (
            <button
              key={s.id}
              type="button"
              className={`guide__anchor ${active === s.id ? "guide__anchor--active" : ""}`}
              aria-current={active === s.id ? "true" : undefined}
              onClick={() => go(s.id)}
            >{s.label}</button>
          ))}
        </nav>
      </aside>

      <div className="guide__content">
        {/* 1 — Orientation */}
        <section ref={setRef("orient")} data-sh-section="orient" className="guide__section">
          <div className="section-eyebrow">Orientation</div>
          <h2 className="section-title">What this report is &amp; how it's organized</h2>
          <p className="guide__lead">
            An <strong>advisory</strong> security-architecture review — it informs decisions, it
            does not gate releases. It evaluates{" "}
            <em>{meta.subject || "the system under review"}</em>{" "}
            against the APD framework's nine goals across three tiers, drawing on nine
            specialist analyses.
          </p>

          <div className="guide__pillars">
            {SH_TIER_ORDER.map((tier) => (
              <div key={tier} className="card card--inset guide__pillar">
                <h3 className="guide__pillar-title">
                  {SH_PILLAR_VERB[tier]} {TIER_LABELS[tier]}
                </h3>
                <ul>
                  {TIER_GOALS[tier].map((goal) => (
                    <li key={goal}>{GOAL_LABELS[goal]}</li>
                  ))}
                </ul>
              </div>
            ))}
          </div>

          <h3 className="guide__subhead">What each tab is for</h3>
          <dl className="guide__tabmap">
            {presentTabs.map((id) => (
              <React.Fragment key={id}>
                <dt>{SH_TAB_LABEL[id]}</dt>
                <dd>{SH_TAB_BLURB[id]}</dd>
              </React.Fragment>
            ))}
          </dl>

          {(!hasTM || !hasAP) && (
            <p className="empty-state empty-state--info guide__note">
              {!hasTM ? "No Threat-model tab? None was supplied for this run. " : ""}
              {!hasAP ? "Attack-paths empty? No crown jewels were declared, so no paths could be enumerated." : ""}
            </p>
          )}
        </section>

        {/* 2 — Vocabulary */}
        <section ref={setRef("vocab")} data-sh-section="vocab" className="guide__section">
          <div className="section-eyebrow">Vocabulary</div>
          <h2 className="section-title">Decode the pills &amp; states</h2>
          <ShGlossary />
          <p className="guide__note">
            The "⌬ N lens perspectives merged" pill means multiple specialists independently
            agreed — see the{" "}
            <button type="button" className="guide__link" onClick={() => onNavigate && onNavigate("annexes")}>Annexes</button>.
          </p>
        </section>

        {/* 3 — How to use */}
        <section ref={setRef("use")} data-sh-section="use" className="guide__section">
          <div className="section-eyebrow">How to use it</div>
          <h2 className="section-title">A reading workflow</h2>
          <ol className="guide__steps">
            <li>Start at <button type="button" className="guide__link" onClick={() => onNavigate && onNavigate("overview")}>Overview</button> — read the posture summary and the top priorities.</li>
            <li>Open <button type="button" className="guide__link" onClick={() => onNavigate && onNavigate("findings")}>Findings</button>, filter by severity, and scan the {typeof criticalCount === "number" && criticalCount > 0 ? `${criticalCount} ` : ""}critical findings first.</li>
            <li>For each finding, check its <strong>disposition</strong> (what kind of action) and <strong>confidence</strong>.</li>
            <li>Read the <strong>recommendation</strong> and locate the cited evidence (file / line).</li>
            <li>Cross-check <button type="button" className="guide__link" onClick={() => onNavigate && onNavigate("coverage")}>Coverage</button> for systemic gaps and <button type="button" className="guide__link" onClick={() => onNavigate && onNavigate("attack_paths")}>Attack paths</button> for chaining.</li>
          </ol>
        </section>

        {/* 4 — For your role */}
        <section ref={setRef("role")} data-sh-section="role" className="guide__section">
          <div className="section-eyebrow">For your role</div>
          <h2 className="section-title">Where to focus</h2>
          <div className="guide__roles">
            <div className="card guide__role">
              <h3>Engineer</h3>
              <p>Findings → Attack paths. Recommendations, cited evidence, and how issues chain.</p>
            </div>
            <div className="card guide__role">
              <h3>Auditor</h3>
              <p>Coverage → Annexes. NIST / taxonomy mappings, what's silent, contradictions.</p>
            </div>
            <div className="card guide__role">
              <h3>Risk / exec</h3>
              <p>Overview → next steps. Posture, severity distribution, ranked priorities.</p>
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}

window.StartHere = StartHere;
