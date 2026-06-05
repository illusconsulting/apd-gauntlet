# Start-here Reading-Guide Tab — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a self-contained "Start here" reading-guide tab to the HTML report that orients a first-time reader, decodes the report's vocabulary in place, gives a reading workflow, and points each role to where to focus — using the run's own live data.

**Architecture:** A new static-JSX screen `report-template/screens/StartHere.jsx` (single-scroll, sticky left rail, four sections) registered on `window`, wired into the data-driven tab list in `app.jsx` as a non-numbered `✦` tab (Overview stays the default), imported in the esbuild entry, styled with existing CSS tokens, and pinned by a source-read unit test mirroring `test_annex_framework_reference.py`. The screen reads `window.APD_DATA` at render time for contextual copy. No Python/transform changes, no new audit check, no `localStorage`.

**Tech Stack:** React via `React.createElement` (no JSX runtime; hooks are window globals from `react-globals.js`), esbuild IIFE bundle (`report-template/.build/build.mjs` via `python tools/build_report_template.py`), pytest source-pin tests, sha256 freshness gate (`tools/check_report_template_freshness.py`).

---

## Spec

Design spec: `docs/superpowers/specs/2026-06-04-html-report-start-here-guide-design.md`. Read it for the locked decisions and the why.

## Critical execution notes (read before starting)

- **The freshness gate is intentionally RED between Task 2 and Task 3.** Editing anything under `report-template/` invalidates `.source-hash`; it only matches again after the bundle is rebuilt in Task 3. Therefore: in Tasks 1–2 run only the *targeted* tests named in each step — do **not** run the full `pytest` suite (the bundle-freshness test will fail until Task 3). The full suite is run in Task 3 after the rebuild.
- **Node 20+ and npm are required for Task 3** (`python tools/build_report_template.py` exits with code 2 if `node`/`npm` are missing). Runtime users of the gauntlet do not need Node; only this rebuild does.
- **Hooks and shared constants are bare identifiers** (`useState`, `TIER_LABELS`), never `React.useState` / `window.TIER_LABELS`, in screen source. `React.Fragment` is fully qualified (no `<>` shorthand). `className`, not `class`. Inline styles are camelCase double-brace objects.
- **Commit after each task.** Branch suggestion: `feat/report-start-here-guide`.

## File Structure

- **Create** `report-template/screens/StartHere.jsx` — the guide screen. One `StartHere({ data, onNavigate })` component plus a small `ShGlossary` helper and three module-local constant maps (`SH_TIER_ORDER`, `SH_PILLAR_VERB`, `SH_TAB_LABEL`, `SH_TAB_BLURB`). Self-registers `window.StartHere`.
- **Modify** `report-template/screens.css` — append a `.guide*` style block (tokens only, so theme/density/severity-palette tweaks still apply).
- **Modify** `report-template/app.jsx` — add the `start_here` entry (first, with a `sigil`), change the numbering map so a sigil tab shows the sigil instead of a number, and add the render block.
- **Modify** `report-template/.build/entry.jsx` — add the `StartHere.jsx` side-effect import in the screens group.
- **Create** `tests/unit/report/test_start_here_guide.py` — source-pin test for the screen + a doc-mention test (added in Task 4).
- **Modify** `tests/test_workflow_apd_gauntlet.py` — add a placement/routing pin for the tab.
- **Regenerate + commit** `tools/apd_gauntlet/data/report-template/*` — the offline bundle (`app.js`, `index.html`, `styles.css`, `screens.css`, `.source-hash`, `vendor-licenses.txt`, `fonts/`).
- **Modify** `docs/html-report.md` and `CHANGELOG.md` — a short note and a changelog entry.

---

## Task 1: Create the Start-here screen and its styles

**Files:**

- Create: `report-template/screens/StartHere.jsx`
- Modify: `report-template/screens.css` (append at end)
- Test: `tests/unit/report/test_start_here_guide.py`

- [ ] **Step 1: Write the failing source-pin test**

Create `tests/unit/report/test_start_here_guide.py`:

```python
"""Static-source pin for the Start-here reading-guide screen.

The Start-here tab is static JSX in report-template/screens/StartHere.jsx; the
bundle-freshness gate separately guarantees the shipped app.js matches this
source, so pinning the source proves the guide's content cannot silently
regress. Mirrors test_annex_framework_reference.py.
"""
from __future__ import annotations

import pathlib

REPO = pathlib.Path(__file__).resolve().parents[3]
SCREEN = REPO / "report-template" / "screens" / "StartHere.jsx"


def _src() -> str:
    return SCREEN.read_text(encoding="utf-8")


def test_screen_registers_on_window() -> None:
    assert "window.StartHere = StartHere;" in _src()


def test_four_sections_present() -> None:
    src = _src()
    for label in ("Orientation", "Vocabulary", "How to use", "For your role"):
        assert label in src, f"missing section: {label}"


def test_glossary_uses_real_atoms() -> None:
    # The glossary renders the SAME atoms used elsewhere so it never drifts.
    src = _src()
    assert "<SeverityPill value=" in src
    assert "<DispositionMark value=" in src
    assert "<MaturityMark value=" in src


def test_decodes_core_vocabulary() -> None:
    src = _src()
    for term in ("Severity", "Disposition", "Confidence", "Maturity", "Coverage cells"):
        assert term in src, f"missing vocabulary term: {term}"
    # The "both is suspicious" insight must be present.
    assert "scope-clarity debt" in src


def test_framework_labels_are_constant_driven() -> None:
    # Pillars/goals come from the shared framework constants, not re-typed.
    src = _src()
    assert "TIER_GOALS" in src
    assert "TIER_LABELS" in src
    assert "GOAL_LABELS" in src


def test_is_contextual_on_run_data() -> None:
    src = _src()
    assert "data.meta" in src
    assert "summary" in src


def test_offline_no_network_calls() -> None:
    src = _src()
    for forbidden in ("fetch(", "XMLHttpRequest", "import(", "https://"):
        assert forbidden not in src, f"network/dynamic call not allowed: {forbidden}"
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python -m pytest tests/unit/report/test_start_here_guide.py -q`
Expected: FAIL — `FileNotFoundError` / errors because `report-template/screens/StartHere.jsx` does not exist yet.

- [ ] **Step 3: Create the screen**

Create `report-template/screens/StartHere.jsx`:

```jsx
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
          <td><strong>risk</strong> present but risky · <strong>uncertainty</strong> needs investigation.</td>
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
```

- [ ] **Step 4: Append the guide styles to `report-template/screens.css`**

Append this block to the END of `report-template/screens.css` (tokens only — no hard-coded colors, so theme/density/severity palette still apply):

```css
/* ── Start-here reading guide ───────────────────────────────────────── */
.guide {
  display: grid;
  grid-template-columns: 180px 1fr;
  gap: var(--space-6);
  align-items: start;
}
.guide__rail {
  position: sticky;
  top: 60px;
  align-self: start;
}
.guide__chip {
  display: flex;
  flex-direction: column;
  gap: 2px;
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  color: var(--ink-3);
  background: var(--paper-2);
  border: 1px solid var(--rule);
  border-radius: var(--radius-sm);
  padding: var(--space-2) var(--space-3);
  margin-bottom: var(--space-4);
}
.guide__chip strong { color: var(--ink); }
.guide__anchors { display: flex; flex-direction: column; gap: 2px; }
.guide__anchor {
  text-align: left;
  background: none;
  border: none;
  border-left: 3px solid transparent;
  padding: var(--space-1) var(--space-2);
  color: var(--ink-3);
  font: inherit;
  cursor: pointer;
  border-radius: 0 var(--radius-sm) var(--radius-sm) 0;
}
.guide__anchor:hover { color: var(--ink); background: var(--paper-2); }
.guide__anchor--active {
  color: var(--ink);
  font-weight: 600;
  border-left-color: var(--accent);
  background: var(--accent-soft);
}
.guide__content { min-width: 0; }
.guide__section {
  padding-bottom: var(--space-6);
  margin-bottom: var(--space-6);
  border-bottom: 1px solid var(--rule);
}
.guide__section:last-child { border-bottom: none; margin-bottom: 0; }
.guide__lead {
  color: var(--ink-2);
  line-height: var(--line-loose);
  max-width: 72ch;
  margin-bottom: var(--space-4);
}
.guide__pillars {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: var(--space-3);
  margin-bottom: var(--space-5);
}
.guide__pillar { padding: var(--space-3); }
.guide__pillar-title {
  font-family: var(--font-display);
  font-size: var(--text-md);
  margin: 0 0 var(--space-2);
}
.guide__pillar ul { margin: 0; padding-left: var(--space-4); color: var(--ink-2); }
.guide__subhead {
  font-family: var(--font-display);
  font-size: var(--text-lg);
  margin: 0 0 var(--space-2);
}
.guide__tabmap {
  display: grid;
  grid-template-columns: max-content 1fr;
  gap: var(--space-1) var(--space-4);
  max-width: 72ch;
  margin: 0;
}
.guide__tabmap dt { font-weight: 600; color: var(--ink); }
.guide__tabmap dd { margin: 0; color: var(--ink-2); }
.guide__note {
  margin-top: var(--space-3);
  color: var(--ink-2);
  font-size: var(--text-sm);
}
.guide-voc { border-collapse: collapse; width: 100%; max-width: 72ch; }
.guide-voc td {
  padding: var(--space-2);
  border-bottom: 1px solid var(--rule);
  vertical-align: top;
  color: var(--ink-2);
  line-height: var(--line-body);
}
.guide-voc td:first-child { white-space: nowrap; width: 1%; }
.guide-do { color: var(--ink-3); }
.guide-cell {
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  padding: 1px var(--space-2);
  border-radius: var(--radius-sm);
}
.guide-cell--covered { background: var(--cell-covered); color: var(--cell-covered-text); }
.guide-cell--both { background: var(--cell-both); color: var(--cell-both-text); }
.guide__steps {
  color: var(--ink-2);
  line-height: var(--line-loose);
  max-width: 72ch;
  padding-left: var(--space-5);
}
.guide__steps li { margin-bottom: var(--space-2); }
.guide__link {
  background: none;
  border: none;
  padding: 0;
  font: inherit;
  color: var(--accent);
  cursor: pointer;
  text-decoration: underline;
}
.guide__roles {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: var(--space-3);
}
.guide__role { padding: var(--space-3); }
.guide__role h3 { font-family: var(--font-display); font-size: var(--text-md); margin: 0 0 var(--space-1); }
.guide__role p { margin: 0; color: var(--ink-2); line-height: var(--line-body); }
@media (max-width: 860px) {
  .guide { grid-template-columns: 1fr; }
  .guide__rail { position: static; }
  .guide__pillars, .guide__roles { grid-template-columns: 1fr; }
}
```

- [ ] **Step 5: Run the targeted test to verify it passes**

Run: `python -m pytest tests/unit/report/test_start_here_guide.py -q`
Expected: PASS (8 passed). Do **not** run the full suite yet — the bundle-freshness test will fail until Task 3.

- [ ] **Step 6: Commit**

```bash
git add report-template/screens/StartHere.jsx report-template/screens.css tests/unit/report/test_start_here_guide.py
git commit -m "feat(report): Start-here reading-guide screen + source-pin test"
```

---

## Task 2: Wire the tab into the app shell

**Files:**

- Modify: `report-template/app.jsx` (BASE_TABS/numbering block and the render block)
- Modify: `report-template/.build/entry.jsx`
- Test: `tests/test_workflow_apd_gauntlet.py`

- [ ] **Step 1: Write the failing placement/routing test**

Add this function to `tests/test_workflow_apd_gauntlet.py` (the file already defines `REPO`):

```python
def test_start_here_tab_is_first_and_routed() -> None:
    src = (REPO / "report-template" / "app.jsx").read_text(encoding="utf-8")
    # tab entry present, carries a sigil instead of a number
    assert 'id: "start_here"' in src and 'label: "Start here"' in src
    assert 'sigil: "✦"' in src
    # the numbering map special-cases the sigil so content tabs keep 01..N
    assert "t.sigil" in src
    # routed to the screen
    assert 'activeTab === "start_here"' in src and "<StartHere" in src
    # placed first — before Overview (compare the tab-entry literals)
    assert src.index('id: "start_here"') < src.index('id: "overview"')
    # Overview remains the default landing tab
    assert 'useState("overview")' in src
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python -m pytest tests/test_workflow_apd_gauntlet.py::test_start_here_tab_is_first_and_routed -q`
Expected: FAIL — assertions miss because `app.jsx` has no `start_here` entry yet.

- [ ] **Step 3: Replace the BASE_TABS + numbering block in `report-template/app.jsx`**

Find this exact block (around lines 18–30):

```jsx
  // Tab list is data-driven so the Threat model tab is omitted entirely when no
  // threat model exists; `num` is derived from index so renumbering is automatic.
  const BASE_TABS = [
    { id: "overview", label: "Overview" },
    { id: "findings", label: "Findings" },
    { id: "capabilities", label: "Capabilities" },
    { id: "coverage", label: "Coverage" },
    ...(data.threat_model && data.threat_model.present
      ? [{ id: "threat_model", label: "Threat model" }] : []),
    { id: "attack_paths", label: "Attack paths" },
    { id: "annexes", label: "Annexes" },
  ];
  const TABS = BASE_TABS.map((t, i) => ({ ...t, num: String(i + 1).padStart(2, "0") }));
```

Replace it with:

```jsx
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
```

- [ ] **Step 4: Add the render block in `report-template/app.jsx`**

Find this exact block (around lines 106–112):

```jsx
        {activeTab === "overview" && (
          <Overview
            data={data}
            onOpenFinding={onOpenFinding}
            onNavigate={setActiveTab}
          />
        )}
```

Insert this block immediately BEFORE it:

```jsx
        {activeTab === "start_here" && (
          <StartHere data={data} onNavigate={setActiveTab} />
        )}
```

- [ ] **Step 5: Add the screen import in `report-template/.build/entry.jsx`**

Find these two lines:

```jsx
import "../components.jsx";
import "../screens/Overview.jsx";
```

Replace with (insert the StartHere import between them):

```jsx
import "../components.jsx";
import "../screens/StartHere.jsx";
import "../screens/Overview.jsx";
```

- [ ] **Step 6: Run the targeted tests to verify they pass**

Run: `python -m pytest tests/test_workflow_apd_gauntlet.py::test_start_here_tab_is_first_and_routed tests/test_workflow_apd_gauntlet.py::test_threat_model_tab_is_conditional_and_routed -q`
Expected: PASS (2 passed). The threat-model order test stays green because `start_here` is added before `coverage`/`threat_model`/`attack_paths`, so their relative `src.index` order is unchanged.

- [ ] **Step 7: Commit**

```bash
git add report-template/app.jsx report-template/.build/entry.jsx tests/test_workflow_apd_gauntlet.py
git commit -m "feat(report): wire Start-here tab (sigil, first; Overview stays default)"
```

---

## Task 3: Rebuild and commit the offline bundle (makes the freshness gate green)

**Files:**

- Regenerate + commit: `tools/apd_gauntlet/data/report-template/` (`app.js`, `index.html`, `styles.css`, `screens.css`, `.source-hash`, `vendor-licenses.txt`, `fonts/`)

- [ ] **Step 1: Rebuild the bundle**

Run: `python tools/build_report_template.py`
Expected: exits 0; prints a build/success line. (If it exits with code 2, install Node 20+ and npm, then re-run.)

- [ ] **Step 2: Verify freshness**

Run: `python tools/check_report_template_freshness.py`
Expected: prints OK / exits 0 (the recomputed sha256 over `report-template/` now matches the committed `.source-hash`).

- [ ] **Step 3: Build the example report and eyeball it (manual verification)**

Run:

```bash
python -m apd_gauntlet build-report examples/apd-20260601-claim-event-bus/expected --out /tmp/sh-check
open /tmp/sh-check/index.html
```

Confirm in the browser (no console errors): the leftmost tab is **✦ Start here**; content tabs read **01 Overview … 06 Annexes** (07 if Threat model present — the fixture has it, so expect Threat model present and numbered); the report still opens on Overview; clicking ✦ Start here shows the four sections; the rail anchors scroll and highlight; the "This run" chip shows the subject and finding count; the glossary pills match the real ones; the role/step links navigate to the right tabs.

- [ ] **Step 4: Run the FULL report test suite (now that the bundle is fresh)**

Run: `python -m pytest tests/unit/report tests/integration/report tests/test_workflow_apd_gauntlet.py -q`
Expected: PASS. The bundle-freshness test and the golden `data.js` test pass (the new tab is JSX config only and does not change `data.js`).

- [ ] **Step 5: (Housekeeping) regenerate the committed example report-html if it is tracked**

Run: `git ls-files examples/apd-20260601-claim-event-bus/expected/40-synthesis/report-html`
- If it lists files (the bundle is tracked): `cp /tmp/sh-check/app.js /tmp/sh-check/index.html /tmp/sh-check/styles.css /tmp/sh-check/screens.css examples/apd-20260601-claim-event-bus/expected/40-synthesis/report-html/` then `git add` those paths.
- If it lists nothing (gitignored): skip.

- [ ] **Step 6: Commit the regenerated bundle**

```bash
git add tools/apd_gauntlet/data/report-template
git add examples/apd-20260601-claim-event-bus/expected/40-synthesis/report-html 2>/dev/null || true
git commit -m "build(report): rebuild bundle with Start-here tab; refresh .source-hash"
```

---

## Task 4: Docs, changelog, and the doc-mention test

**Files:**

- Modify: `docs/html-report.md`
- Modify: `CHANGELOG.md`
- Test: `tests/unit/report/test_start_here_guide.py` (append one test)

- [ ] **Step 1: Add the failing doc-mention test**

Append this function to `tests/unit/report/test_start_here_guide.py`:

```python
def test_html_report_doc_mentions_start_here_guide() -> None:
    doc = (REPO / "docs" / "html-report.md").read_text(encoding="utf-8")
    assert "start here" in doc.lower()
```

- [ ] **Step 2: Run it to verify it fails**

Run: `python -m pytest tests/unit/report/test_start_here_guide.py::test_html_report_doc_mentions_start_here_guide -q`
Expected: FAIL — `docs/html-report.md` does not yet mention the guide.

- [ ] **Step 3: Add the doc section to `docs/html-report.md`**

Add this as a new top-level (`##`) section in `docs/html-report.md` (place it near the top, after the report overview / before the per-tab sections). Keep the blank lines exactly as shown (the `docs/**` markdownlint gate requires blank lines around the heading and list):

```markdown
## Start-here reading guide

The report opens with a **Start here** tab (marked `✦`, leftmost in the tab
bar). It is a reading guide for first-time readers and provides:

- an orientation map — what the report is, the three pillars and nine goals,
  and a one-line description of every tab;
- a vocabulary glossary that decodes the severity, disposition, confidence,
  maturity, and coverage-cell pills in place;
- a short reading workflow; and
- per-role focus paths for engineers, auditors, and risk reviewers.

The guide reads the run's own data, so its examples reflect the system under
review. Overview remains the default landing tab.
```

- [ ] **Step 4: Add the changelog entry to `CHANGELOG.md`**

Add this bullet under the `### Added` subsection of the most recent (top) version block — or under a top `## [Unreleased]` section, creating one in the file's existing heading style if none exists:

```markdown
- HTML report: a new "Start here" reading-guide tab (`✦`, leftmost) that orients first-time readers with an orientation map, a vocabulary glossary, a reading workflow, and per-role focus paths, reading the run's live data for contextual guidance. Overview remains the default tab.
```

- [ ] **Step 5: Verify the doc-mention test and markdownlint**

Run: `python -m pytest tests/unit/report/test_start_here_guide.py -q`
Expected: PASS (9 passed).

Run: `npx --yes markdownlint-cli2 docs/html-report.md CHANGELOG.md`
Expected: `Summary: 0 error(s)`.

- [ ] **Step 6: Final full run**

Run: `python -m pytest -q`
Expected: PASS (full suite green; coverage ≥ 85% on `tools/apd_gauntlet/`). Also run `ruff check .` and `mypy` if part of the local gate.

- [ ] **Step 7: Commit**

```bash
git add docs/html-report.md CHANGELOG.md tests/unit/report/test_start_here_guide.py
git commit -m "docs(report): document the Start-here reading-guide tab"
```

---

## Definition of Done (final checklist)

- [ ] `report-template/screens/StartHere.jsx` exists, registers `window.StartHere`, and renders the four sections from `window.APD_DATA` with defensive fallbacks.
- [ ] `app.jsx` has the `start_here` sigil tab first, the sigil-aware numbering map, and the render block; `useState("overview")` unchanged.
- [ ] `entry.jsx` imports `../screens/StartHere.jsx` in the screens group.
- [ ] `python tools/build_report_template.py` run; `python tools/check_report_template_freshness.py` prints OK; regenerated bundle committed.
- [ ] `tests/unit/report/test_start_here_guide.py` (9 tests) and `tests/test_workflow_apd_gauntlet.py::test_start_here_tab_is_first_and_routed` pass; existing `test_threat_model_tab_is_conditional_and_routed` still passes.
- [ ] Full `pytest` green, coverage ≥ 85% on `tools/apd_gauntlet/`; `ruff`/`mypy` clean.
- [ ] `markdownlint-cli2` clean on `docs/html-report.md` and `CHANGELOG.md`.
- [ ] Example report renders at `file://` with no console errors; ✦ tab leftmost; content tabs keep their numbers; Overview is the default; rail anchors scroll + highlight; role/step links navigate.
- [ ] No new audit/completeness check added; `transform.py`/`emit.py`/`audit.py` untouched.
```
