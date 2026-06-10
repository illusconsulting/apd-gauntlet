/* eslint-disable */
// Root app — header + tab nav + screen routing + tweaks panel

const DEFAULTS = /*EDITMODE-BEGIN*/{
  "theme": "light",
  "sevPalette": "default",
  "density": "comfortable",
  "typePairing": "editorial",
  "findingsLayout": "two-pane"
}/*EDITMODE-END*/;

function App() {
  const data = window.APD_DATA;
  const [t, setTweak] = useTweaks(DEFAULTS);
  const [activeTab, setActiveTab] = useState("overview");
  const [selectedFinding, setSelectedFinding] = useState(null);
  const [focusPathId, setFocusPathId] = useState(null);

  // Tab list is data-driven so the Threat model tab is omitted entirely when no
  // threat model exists. The Start-here guide carries a sigil instead of a
  // number; numeric content tabs are numbered from 01 so existing section
  // numbers are unchanged.
  const BASE_TABS = [
    { id: "start_here", label: "Start here", sigil: "✦" },
    { id: "overview", label: "Overview" },
    { id: "findings", label: "Findings" },
    { id: "capabilities", label: "Capabilities" },
    { id: "coverage", label: "Coverage" },
    ...(data.threat_model && data.threat_model.present
      ? [{ id: "threat_model", label: "Threat model" }] : []),
    { id: "attack_paths", label: "Attack paths" },
    { id: "annexes", label: "Annexes" },
  ];
  let _tabNum = 0;
  const TABS = BASE_TABS.map((t) => {
    if (t.sigil) return { ...t, num: t.sigil };
    _tabNum += 1;
    return { ...t, num: String(_tabNum).padStart(2, "0") };
  });

  // Apply tweaks → data attributes on <body>
  useEffect(() => {
    document.body.setAttribute("data-theme", t.theme);
    document.body.setAttribute("data-sev", t.sevPalette);
    document.body.setAttribute("data-density", t.density);
    document.body.setAttribute("data-type", t.typePairing);
  }, [t.theme, t.sevPalette, t.density, t.typePairing]);

  // Listen for findings-layout changes dispatched by the header-right select
  React.useEffect(() => {
    const onLayout = (e) => setTweak("findingsLayout", e.detail);
    window.addEventListener("apd:setLayout", onLayout);
    return () => window.removeEventListener("apd:setLayout", onLayout);
  }, [setTweak]);

  const onOpenFinding = (id) => {
    setSelectedFinding(id);
    setActiveTab("findings");
  };

  const onOpenPath = (pathId) => {
    setFocusPathId(pathId);
    setActiveTab("attack_paths");
  };

  return (
    <div className="app">
      {/* Header */}
      <header className="report-header">
        <div className="report-header__inner">
          <div>
            <div className="report-header__brand">
              <span className="report-header__mark" aria-hidden="true" />
              <span>APD Gauntlet · Advisory Report</span>
            </div>
            <h1 className="report-header__title">
              <em>{data.meta.subject}</em> — {data.meta.subject_tagline}
            </h1>
            <div className="report-header__subtitle">
              Synthesis of nine specialist outputs against the {data.meta.domain_pack.name} domain pack — produced by apd-synthesizer.
            </div>
          </div>
          <dl className="report-header__meta">
            <dt>Run id</dt><dd>{data.meta.run_id}</dd>
            <dt>Date</dt><dd>{data.meta.date}</dd>
            <dt>Framework</dt><dd>v{data.meta.framework_version}</dd>
            <dt>Pack</dt><dd>{data.meta.domain_pack.name} v{data.meta.domain_pack.version}</dd>
            <dt>Inputs</dt><dd>{data.meta.artifact_count} artifacts</dd>
            <dt>Specialists</dt><dd>9 / 9</dd>
          </dl>
        </div>
      </header>

      <DiagnosticsBanner data={data} />

      {/* Tab nav */}
      <nav className="tabnav">
        <div className="tabnav__inner">
          {TABS.map((tab) => (
            <button
              key={tab.id}
              className={`tabnav__item ${activeTab === tab.id ? "tabnav__item--active" : ""}`}
              onClick={() => setActiveTab(tab.id)}
              data-screen-label={`${tab.num} ${tab.label}`}
            >
              <span className="num">{tab.num}</span>
              {tab.label}
            </button>
          ))}
          <div className="tabnav__spacer" />
          <div className="tabnav__status">
            <span className="tabnav__dot" />
            <span>advisory · review-only · does not gate</span>
          </div>
        </div>
      </nav>

      {/* Main content */}
      <main className="main" data-screen-label={`${TABS.find(x => x.id === activeTab).num} ${TABS.find(x => x.id === activeTab).label}`}>
        {activeTab === "start_here" && (
          <StartHere data={data} onNavigate={setActiveTab} />
        )}
        {activeTab === "overview" && (
          <Overview
            data={data}
            onOpenFinding={onOpenFinding}
            onNavigate={setActiveTab}
          />
        )}
        {activeTab === "findings" && (
          <Findings
            data={data}
            selectedId={selectedFinding}
            onSelect={setSelectedFinding}
            layout={t.findingsLayout}
            onOpenPath={onOpenPath}
          />
        )}
        {activeTab === "capabilities" && <Capabilities data={data} />}
        {activeTab === "coverage" && <Coverage data={data} />}
        {activeTab === "threat_model" && <ThreatModel data={data} />}
        {activeTab === "attack_paths" && (
          <AttackPaths data={data} onOpenFinding={onOpenFinding} focusPathId={focusPathId} />
        )}
        {activeTab === "annexes" && (
          <Annexes data={data} onOpenFinding={onOpenFinding} />
        )}
      </main>

      {/* Tweaks panel — dev only. Precompiled bundle omits tweaks-panel.jsx
          entirely; this guard keeps app.jsx safe to bundle. */}
      {typeof TweaksPanel !== "undefined" && (
        <TweaksPanel title="Tweaks">
          <TweakSection label="Theme" />
          <TweakRadio
            label="Theme"
            value={t.theme}
            options={[
              { value: "light", label: "Light" },
              { value: "paper", label: "Paper" },
              { value: "dark",  label: "Dark" },
            ]}
            onChange={(v) => setTweak("theme", v)}
          />
          <TweakRadio
            label="Severity palette"
            value={t.sevPalette}
            options={[
              { value: "default",  label: "Default" },
              { value: "contrast", label: "Contrast" },
              { value: "mono",     label: "Mono" },
            ]}
            onChange={(v) => setTweak("sevPalette", v)}
          />

          <TweakSection label="Type" />
          <TweakSelect
            label="Type pairing"
            value={t.typePairing}
            options={[
              { value: "editorial", label: "Editorial — Newsreader + Plex" },
              { value: "technical", label: "Technical — IBM Plex Sans only" },
              { value: "classic",   label: "Classic — Source Serif + Inter" },
              { value: "modern",    label: "Modern — Instrument + Manrope" },
            ]}
            onChange={(v) => setTweak("typePairing", v)}
          />

          <TweakSection label="Density" />
          <TweakRadio
            label="Density"
            value={t.density}
            options={[
              { value: "compact",     label: "Compact" },
              { value: "comfortable", label: "Comfy" },
              { value: "roomy",       label: "Roomy" },
            ]}
            onChange={(v) => setTweak("density", v)}
          />

          <TweakSection label="Findings layout" />
          <TweakRadio
            label="Layout"
            value={t.findingsLayout}
            options={[
              { value: "two-pane", label: "Two-pane" },
              { value: "stacked",  label: "Stacked" },
              { value: "table",    label: "Table" },
            ]}
            onChange={(v) => setTweak("findingsLayout", v)}
          />
          <div style={{ fontSize: 11, color: "var(--ink-3)", lineHeight: 1.5, padding: "4px 14px 12px" }}>
            Switch to the Findings tab to see the layout change.
          </div>
        </TweaksPanel>
      )}

      <ToastHost />
    </div>
  );
}

ReactDOM.createRoot(document.getElementById("root")).render(<App />);
