# Design — "Start here" reading-guide tab for the HTML report

Status: draft (brainstormed 2026-06-04)
Owner: APD Gauntlet contributors
Feature branch (suggested): `feat/report-start-here-guide`

## 1. Goal

The APD Gauntlet HTML report renders rich data but never defines its own
vocabulary. The only in-report explainer today is the static §11 "APD Framework
reference" card in `report-template/screens/Annexes.jsx` and per-ID hover
tooltips on `TaxonomyTag`. A first-time reader (engineer, auditor, or risk
professional) can see the colored pills, coverage cells, and attack-path graph
but cannot decode what they mean or know what to do next.

This feature adds a single, self-contained **"Start here" reading-guide tab**
that orients a reader to the report, decodes its vocabulary in place, gives a
reading workflow, and points each role to where it should focus — using the
run's own live data so the guidance is contextual.

## 2. Decisions locked during brainstorm

These were settled with the user and constrain the design:

- **Primary spine: a dedicated "Start here" guide tab** (not an inline glossary,
  guided tour, or role selector). It composes with future enhancements but is
  the deliverable here.
- **Scope: all four content blocks** — Orientation map, Vocabulary glossary,
  How-to-use decision flow, and Role-based reading paths.
- **Data binding: contextual, client-side.** The screen reads the already
  injected `window.APD_DATA` at render time. No Python/transform changes, no
  build-time injection, no new audit check.
- **Layout: single scroll with a sticky section rail** (wireframe "A"). The four
  sections stack in one scroll; a sticky left rail jumps between them.
- **Landing: Overview stays the default tab.** The guide is reached via its tab;
  the report does not change where it opens.
- **Discoverability: the prominent tab only.** No per-screen "new here?" links,
  no banner, no `localStorage`. The change stays concentrated in one new screen
  plus tab wiring — nothing scattered across the other screens.

## 3. Scope

### In scope

- A new screen component `report-template/screens/StartHere.jsx`.
- Tab integration in `report-template/app.jsx` (a non-numbered `✦` tab, leftmost,
  not the default).
- Build registration in `report-template/.build/entry.jsx`.
- Styles for the guide in `report-template/screens.css` (reusing existing tokens
  and atoms wherever possible).
- A source-read unit test mirroring `tests/unit/report/test_annex_framework_reference.py`.
- Rebuild of the committed bundle under `tools/apd_gauntlet/data/report-template/`
  and regeneration of the example report snapshot.
- A `CHANGELOG.md` entry and a short note in the HTML-report doc.

### Out of scope (YAGNI)

- `localStorage` / first-visit logic of any kind.
- Per-screen "new here?" links, info-icon popovers, or a dismissible banner.
- Role-based **reordering of the data** — role cards are static guidance only;
  the report content does not change by role.
- Build-time Python injection of an onboarding block (`transform.py`/`emit.py`
  untouched).
- A new completeness/audit check (`tools/apd_gauntlet/synthesis/audit.py`
  untouched — static help carries no compliance risk and a new check would widen
  the blocking surface).
- Inline glossary tooltips wired across the other screens (possible future
  enhancement, tracked separately).

## 4. Architecture and components

The report is a no-JSX-runtime React SPA (`React.createElement` via
`react-globals.js`) bundled by esbuild into one offline `app.js`. The new screen
follows the exact pattern of the existing screens.

`StartHere.jsx` exports one component, `StartHere({ data, onNavigate })`,
composed of small, single-purpose sub-components defined in the same file (kept
focused, ~250–350 lines, comparable to `Annexes.jsx`):

- `StartHere` — top-level: renders the rail plus the four sections; owns the
  active-section state for the rail.
- `GuideRail` — the sticky left rail: the "this run" context chip and the four
  anchor buttons; highlights the active section.
- `OrientationSection` — what the report is, the 3 pillars → 9 goals, the
  per-tab one-liners, and the contextual empty/missing-tab note.
- `VocabularySection` — the decode table.
- `HowToUseSection` — the numbered reading workflow.
- `RoleSection` — the Engineer / Auditor / Risk-exec focus cards.

At end of file: `window.StartHere = StartHere;` (matching every other screen).

Interfaces:

- **Input:** `data` (= `window.APD_DATA`, read-only, immutable post-inject) and
  `onNavigate` (= the App's `setActiveTab`, already threaded to Overview and
  Annexes). The guide uses `onNavigate` for outbound jumps (e.g. "see the full
  framework reference" → Annexes; role cards → the relevant tab).
- **Dependencies:** the shared atoms and constants already on `window`
  (see §7). No new globals, no new event types, no network.

## 5. Data flow and contextual binding

All values are read defensively from `window.APD_DATA` with fallbacks; a missing
field never throws (an unguarded access would surface as a `section_errors`
entry via `DiagnosticsBanner`). Fields consumed:

- `data.meta.subject`, `data.meta.subject_tagline` — name the system under review
  in the lead sentence and the "this run" chip.
- `data.meta.domain_pack.name`, `data.meta.framework_version` — chip detail.
- `data.summary.findings_total` and `data.summary.bySeverity` — the chip's count
  and a contextual nudge in How-to-use ("scan the N critical findings first");
  both optional, omitted cleanly when absent.
- `data.threat_model.present` — whether the Threat-model tab exists; drives the
  orientation tab-map (only list tabs that are actually present) and the
  empty-tab note.
- `data.attack_paths` presence and `data.meta.crown_jewels` — explain why the
  Attack-paths tab may be empty ("no crown jewels were declared").
- `data.meta.is_empty_run` — degrade the whole chip to "This run" with no counts.

Graceful degradation rule: every dynamic fragment is wrapped so that, on an
empty or partial run, the guide still renders its static teaching content; only
the run-specific embellishments drop out.

The orientation tab-map mirrors the live tab logic in `app.jsx` `BASE_TABS`: it
lists exactly the tabs that exist for this run (Threat model appears only when
`threat_model.present`), so the map never advertises a tab the reader can't see.

## 6. Layout and section content

Single scroll. A sticky left rail (`position: sticky`) holds the "this run" chip
and four anchor buttons (Orientation, Vocabulary, How to use, For your role).
Clicking an anchor scrolls its section into view via a `ref` + `scrollIntoView`
(no `href="#"`, no inline handler — CSP-clean). The active anchor is highlighted;
a lightweight `IntersectionObserver` scrollspy updating the active anchor is an
optional enhancement, not required for v1.

### Section 1 — Orientation

- Lead: the report is **advisory** (informs, does not gate); it evaluates
  `{subject}` against the APD framework's 9 goals across 3 tiers from nine
  specialist analyses.
- Three pillar cards (Assure Trustworthiness / Provide Scalability / Demonstrate
  Auditability), each listing its three goals — rendered from the framework
  constants on `window` (§7), not hardcoded.
- "What each tab is for" — a one-line description per present tab.
- Contextual note: why the Threat-model tab may be absent (none supplied) and
  why Attack paths may be empty (no crown jewels declared).

### Section 2 — Vocabulary

A decode table: term + the **real rendered atom** + meaning + what-to-do.

- Severity (critical/high/medium/low/info) via `SeverityPill`.
- Disposition (gap / blocked / risk / uncertainty / ok) via `DispositionMark`,
  each with its implied next action.
- Confidence (high / medium / low).
- Maturity (designed → implemented → tested → operationalized) via `MaturityMark`.
- Coverage cells (covered / gapped / both / silent) via the Coverage cell classes
  and `--cell-*` tokens — including the insight that **both** is suspicious
  (a finding and capability collide → scope-clarity debt) and **silent** means
  not assessed.
- The "⌬ N lens perspectives merged" pill — multiple specialists independently
  agreed; cross-link to Annexes §10.

Using the actual atoms (not re-styled look-alikes) guarantees the glossary stays
faithful to what the reader sees on the other screens.

### Section 3 — How to use it

A numbered workflow (5 steps): Overview posture → Findings filtered by severity →
check each finding's disposition and confidence → read recommendation and locate
cited evidence → cross-check Coverage and Attack paths. Steps that name a tab use
`onNavigate` to jump there.

### Section 4 — For your role

Three static cards — Engineer (Findings → Attack paths), Auditor (Coverage →
Annexes), Risk/exec (Overview → next steps) — each a short focus statement.
These tailor *guidance only*; they do not change the data.

## 7. Reuse and single source of truth

The guide must not duplicate framework taxonomy or pill styling:

- Atoms from `report-template/components.jsx`: `SeverityPill`, `DispositionMark`,
  `MaturityMark`, `TaxonomyTag`, `TagRow` — reused directly for the glossary.
- Constants already exported to `window` (`components.jsx` `Object.assign(window, …)`):
  `GOAL_LABELS`, `GOAL_SHORT`, `TIER_LABELS`, `TIER_GOALS` — drive the pillars →
  goals map. The guide references these; it does not redeclare the 9 goals.
- Coverage cell classes / `--cell-covered|gapped|both|silent` tokens
  (`styles.css`) — reused for the coverage-cell glossary row.
- Design tokens (`--sev-*`, `--ink-*`, `--paper-*`, `--accent`, `--space-*`,
  `--text-*`, `--radius-*`, `--shadow-*`) — the guide adds no new palette; it
  inherits theme, density, and severity-palette tweaks automatically.

If the pillar verb/intro strings currently living only in `Annexes.jsx`
(`APD_PILLAR_VERB`, `APD_PILLAR_INTRO`) are needed by the guide and are not
reliably on `window`, the guide defines a minimal local pillar-verb map (three
entries) rather than triggering a refactor of `Annexes.jsx` and its test. A
single-source promotion of those constants into `components.jsx` is a possible
follow-up but is explicitly out of scope here to keep the diff and risk small.

## 8. Tab integration and numbering

The guide is a non-numbered, leftmost tab so it does not renumber the content
sections (which stay 01…N today).

- Add `{ id: "start_here", label: "Start here", sigil: "✦" }` as the first entry
  of `BASE_TABS` in `app.jsx`.
- Change the numbering map so a tab with a `sigil` shows the sigil instead of a
  number, and numeric tabs are numbered from 01 (so Overview stays 01):

  ```jsx
  let n = 0;
  const TABS = BASE_TABS.map((tab) => {
    if (tab.sigil) return { ...tab, num: tab.sigil };
    n += 1;
    return { ...tab, num: String(n).padStart(2, "0") };
  });
  ```

- Leave `useState("overview")` unchanged (Overview remains the default).
- Add the render block:
  `{activeTab === "start_here" && <StartHere data={data} onNavigate={setActiveTab} />}`.
- Register `report-template/screens/StartHere.jsx` in `report-template/.build/entry.jsx`
  alongside the other screen imports (after `react-globals`).

The existing `data-screen-label` / `.num` rendering already handles a string
`num`, so the sigil renders where the number normally sits.

## 9. Accessibility and CSP

- React `onClick` / `onMouseEnter` only; no inline handlers, no `href="#"`.
- Rail anchors are `<button>`s; the active section uses `aria-current`.
- Section headers use the existing `.section-eyebrow` / `.section-title`
  semantics so heading order and contrast match the rest of the report.
- Works at `file://` with no console errors; copy/toast/keyboard navigation
  elsewhere is unaffected.

## 10. Error handling and graceful degradation

- Every `data.*` access uses optional chaining and a fallback; the static
  teaching content renders even on an empty run.
- The screen catches nothing itself; correctness is by defensive reads. A thrown
  error would be caught by the report's per-section error isolation and shown in
  `DiagnosticsBanner`, but the design's intent is that it never throws.
- No new failure modes are introduced into the build or synthesis pipeline.

## 11. Testing

- New `tests/unit/report/test_start_here_guide.py`, mirroring
  `test_annex_framework_reference.py` (source-read assertions on
  `report-template/screens/StartHere.jsx`):
  - `window.StartHere` registration is present.
  - All four section labels are present (Orientation, Vocabulary, How to use,
    For your role).
  - The glossary references the real atoms (`SeverityPill`, `DispositionMark`,
    `MaturityMark`) and the coverage-cell states.
  - It reads contextual data (`data.meta.subject`) and contains no `fetch`/
    network/`import(` calls.
- `app.jsx` wiring assertion: `start_here` is in `BASE_TABS` and has a render
  block (extend the existing app-shell test or the freshness/golden path).
- Update any test that snapshots the tab list or the example report HTML to
  include the new tab; regenerate committed fixtures.
- Keep coverage ≥ 85% on `tools/apd_gauntlet/`.

## 12. Build, freshness gate, and definition of done

Because `report-template/` changed, the bundle must be regenerated and committed.

Commands:

- Rebuild: `python tools/build_report_template.py`
- Verify freshness: `python tools/check_report_template_freshness.py` (prints OK)
- Then commit the regenerated bundle under `tools/apd_gauntlet/data/report-template/`
  (`app.js`, `index.html`, `styles.css`, `screens.css`, `.source-hash`,
  `vendor-licenses.txt`).

Definition of done:

1. `StartHere.jsx` added, registered on `window`, imported in `entry.jsx`.
2. `app.jsx` tab entry + sigil numbering + render block wired; Overview still
   default; content tabs keep their numbers.
3. `python tools/build_report_template.py` run; regenerated bundle committed.
4. `python tools/check_report_template_freshness.py` prints OK.
5. New source-read test green; tab-list/example snapshots updated.
6. `pytest` green, ≥ 85% coverage on `tools/apd_gauntlet/`; `ruff`, `mypy` clean.
7. Full-glob `markdownlint` clean (this spec and any doc edits included).
8. `apd-gauntlet validate examples/apd-20260601-claim-event-bus/expected/` passes;
   build-report → audit-report on the fixture shows no new/failing checks (no new
   audit check added).
9. Renders at `file://` with no console errors; honors theme/density/palette.

## 13. Docs and changelog

- `CHANGELOG.md`: an entry under the next version describing the Start-here tab.
- The HTML-report doc (`docs/.../html-report*.md`): a short note that the report
  opens with a Start-here reading guide tab. No ADR — this is an additive UI
  feature, not an architectural decision that reverses a prior one.

## 14. Risks and mitigations

- **Freshness gate forgotten** → CI red. Mitigation: DoD steps 3–4 and a local
  `check_report_template_freshness.py` run before push.
- **Tab-list snapshot drift** → existing tests fail. Mitigation: §11 explicitly
  updates fixtures and the example report.
- **Glossary drifts from real semantics** → reusing the actual atoms and the
  `--cell-*` tokens keeps it faithful; source-read test asserts the atoms.
- **Bundle-scope assumption about cross-file constants** → guide relies only on
  `window`-exported constants (or a tiny local map), never on another screen's
  file-scoped consts.
- **Scope creep toward a full tour/role engine** → §3 "out of scope" fixes the
  boundary; role cards are static.

## 15. Files touched

- `report-template/screens/StartHere.jsx` (new).
- `report-template/app.jsx` (tab entry, sigil numbering, render block).
- `report-template/.build/entry.jsx` (import).
- `report-template/screens.css` (guide styles).
- `tools/apd_gauntlet/data/report-template/*` (regenerated bundle — committed).
- `examples/apd-20260601-claim-event-bus/expected/...` (regenerated report).
- `tests/unit/report/test_start_here_guide.py` (new) and any tab-list snapshot test.
- `CHANGELOG.md`, HTML-report doc (notes).
