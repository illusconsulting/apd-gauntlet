/* eslint-disable */
// Root app — header + tab nav + screen routing + tweaks panel

const DEFAULTS = /*EDITMODE-BEGIN*/{
  "theme": "light",
  "sevPalette": "default",
  "density": "comfortable",
  "typePairing": "editorial",
  "findingsLayout": "two-pane"
}/*EDITMODE-END*/;

const TABS = [
  { id: "overview",     num: "01", label: "Overview" },
  { id: "findings",     num: "02", label: "Findings" },
  { id: "capabilities", num: "03", label: "Capabilities" },
  { id: "coverage",     num: "04", label: "Coverage" },
  { id: "attack_paths", num: "05", label: "Attack paths" },
  { id: "annexes",      num: "06", label: "Annexes" },
];

function App() {
  const data = window.APD_DATA;
  const [t, setTweak] = useTweaks(DEFAULTS);
  const [activeTab, setActiveTab] = useState("overview");
  const [selectedFinding, setSelectedFinding] = useState(null);

  // Apply tweaks → data attributes on <body>
  useEffect(() => {
    document.body.setAttribute("data-theme", t.theme);
    document.body.setAttribute("data-sev", t.sevPalette);
    document.body.setAttribute("data-density", t.density);
    document.body.setAttribute("data-type", t.typePairing);
  }, [t.theme, t.sevPalette, t.density, t.typePairing]);

  const onOpenFinding = (id) => {
    setSelectedFinding(id);
    setActiveTab("findings");
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
          />
        )}
        {activeTab === "capabilities" && <Capabilities data={data} />}
        {activeTab === "coverage" && <Coverage data={data} />}
        {activeTab === "attack_paths" && <AttackPaths data={data} />}
        {activeTab === "annexes" && (
          <Annexes data={data} onOpenFinding={onOpenFinding} />
        )}
      </main>

      {/* Tweaks panel */}
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

      <ToastHost />
    </div>
  );
}

ReactDOM.createRoot(document.getElementById("root")).render(<App />);
