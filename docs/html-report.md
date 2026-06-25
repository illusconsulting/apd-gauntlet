# HTML Advisory Report (v1.7)

Every gauntlet run automatically produces an interactive HTML view of the
synthesizer's outputs at:

    runs/<run_id>/40-synthesis/report-html/index.html

Open the file in any recent browser (offline — no network needed). The bundle
contains six core tabs (Overview, Findings, Capabilities, Coverage, Attack paths,
Annexes) sourced from the existing `40-synthesis/*.yaml` artifacts plus the
synthesizer-emitted `report-data.yaml`. A seventh **Threat model** tab appears
between Coverage and Attack paths only when a threat model exists for the run
(see [Threat model tab](#threat-model-tab)); it is omitted entirely otherwise. An
**Architecture (C4)** tab appears between Attack paths and Annexes only when a
grounded C4 model exists for the run (see
[Architecture (C4) tab](#architecture-c4-tab)); it is omitted entirely otherwise.

The Coverage tab renders taxonomy tooltips for every cited control or technique
ID. Tooltip families include NIST 800-53r5, MITRE ATT&CK, CWE, OWASP (web /
API / LLM), MITRE D3FEND, — when `mitre_atlas` is declared for the run —
**MITRE ATLAS** (adversarial-ML techniques), and — when the
`mobile-applications` pack auto-seeds `masvs`/`maswe` — **OWASP MASVS** and
**OWASP MASWE** (mobile verification controls and weaknesses). A bare ID in a
tooltip (title equals the ID string) means the reference catalog for that family
failed to load; this is caught by the completeness gate's
`taxonomy_titles_resolve` check.

When `masvs` or `maswe` is active, the Coverage tab adds two sub-tabs — an
**OWASP MASVS** control-coverage view (sourced from
`40-synthesis/masvs-coverage.yaml`, one row per control with finding/capability
counts, surfaces, and a posture pill) and an **OWASP MASWE** weakness view
(sourced from `maswe-coverage.yaml`, one row per weakness with finding count,
filing category/status, and parent MASVS controls). Both sub-tabs are omitted
when the taxonomy is not active. The transform exposes the active taxonomy set
as `data.meta.active_taxonomies` (lifted from the run-config `taxonomies:`
list), which the Coverage tab reads to decide which family sub-tabs to render.

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

## Findings tab

The Findings tab renders each deduped finding's full detail card: rubric, summary,
detail, evidence, recommendation, mappings, and lens perspectives. For `apath-*`
**risk** findings that resolve to an attack path, the card additionally renders a
compact **per-finding hop-strip** — a horizontal "subway map" showing the attacker
through to the crown jewel, the vulnerable hop, a fix-at-source marker, and any
D3FEND choke-point markers — immediately after the summary and before the detail.
A "view full graph" link in the strip focuses the Attack Paths tab on that path.
See [Attack-path analysis — Per-finding attack-path strip](attack-path-analysis.md#per-finding-attack-path-strip)
for the full marker semantics.

The hop-strip is rendered by the `AttackPathStrip` JSX component in
`report-template/components.jsx`. As with any JSX or CSS change, edits require
re-running `python tools/build_report_template.py` and committing the regenerated
`app.js` and `.source-hash`.

## Interactive graphs

The **Attack paths** asset graph and the **Threat model** surface map are drawn
with [Cytoscape.js](https://js.cytoscape.org/) (dagre layout for the directed
asset graph, fcose compound layout for the trust-boundary surface map). Both are
fully interactive: **pan, zoom, drag** nodes, a toolbar **fit** control, and
**hover tooltips** (the asset-graph tooltip shows a node's provenance — source
artifact and locator — and an edge's finding/capability reference). All colors
are read from the report's CSS tokens via `getComputedStyle`, so the graphs
**recolor automatically when the theme changes** (light / paper / dark).

On the Attack-paths graph, **clicking a node highlights the attack path(s) that
pass through it** (dimming the rest), and the graph cross-links both ways with the
"Enumerated paths" list — **clicking a path row highlights that path on the
graph**, and clicking it again (or clicking empty canvas) clears the selection.
A path-focused subgraph showing only the nodes and edges on enumerated paths
renders below the full graph when paths exist.

These graphs replace the previous static Mermaid diagrams; Mermaid was removed
from the bundle entirely (a smaller `app.js`), and the report remains
self-contained and offline-openable with no network or Node toolchain on the
consumer side.

## Threat model tab

When the run has a threat model — either user-supplied or authored by the
gauntlet's baseline threat-model author — the report adds a **Threat model** tab
between Coverage and Attack paths. It surfaces the modeled threats and how well
they are mitigated, in the report's existing design language (it reuses the
shared interactive `GraphView` component and the `apd-matrix`, `coverage-bar`,
and `contradiction` classes — no bespoke styling). When no threat model exists (no
user-supplied TM and none authored), the tab is **omitted entirely** rather than
rendered empty, and the remaining tabs renumber automatically.

A provenance banner at the top of the scene states whether the model is an
authored baseline or user-supplied, which agent generated it, and — for an
authored model — the source artifact it was grounded from.

The scene is composed of up to five blocks:

- **Block A — STRIDE × asset matrix.** A matrix with assets/surfaces as rows and
  the modeled STRIDE (or LINDDUN) categories as columns. Each cell is `covered`
  (every threat in the cell is mitigated), `partial` (some mitigated), `gap`
  (none mitigated), or `silent` (the category was not modeled for that asset).
  Rows are ordered by descending threat count.
- **Block B — Threat entries.** A table of every modeled threat: asset, threat,
  STRIDE/LINDDUN letter, mitigation (or a `— none` marker for gaps), extraction
  confidence, inferred APD goals, and the source locator.
- **Block C — Coverage by surface.** Per-surface STRIDE-category coverage from
  the threat-model evaluator (present categories, absent categories, entry count,
  and a proportion bar), plus a summary of coverage gaps, contradictions, and
  silences the evaluator emitted. **Requires the evaluator** — this block is
  absent when only the author ran (no `threat-model-coverage.yaml`).
- **Block D — Surface map.** An interactive trust-boundary map (Cytoscape, fcose
  compound layout): assets are nodes badged with their STRIDE letters, nested
  under trust-boundary compound parents when the asset inventory provides
  boundaries (degrading to a flat node list otherwise), and marked `hot` when an
  asset has an unmitigated (gap) threat. No edges are fabricated — clusters and
  nodes only. Pan/zoom/drag, hover tooltips, and a fit control are available; the
  graph recolors when the report theme changes.
- **Block E — Supplied vs authored.** A comparator shown only when **both** a
  user-supplied TM and the authored baseline exist. It groups threats into
  authored-only, supplied-only, and corroborated (present in both, matched
  case-insensitively on asset + threat).

The completeness gate's `threat_model_scene_coherent` structural check guards the
scene: it is exempt when the scene is legitimately omitted (no threat model), and
fails if the scene is marked present but carries no entries or matrix rows.

## Architecture (C4) tab

When the run has a grounded C4 model (`data.c4_model.present`), the report adds an
**Architecture (C4)** tab between Attack paths and Annexes. It is `code_recon`-gated:
the model is authored only when source-code reconnaissance ran, and the tab is
**omitted entirely** otherwise, with the remaining tabs renumbering automatically.
The view is governed by the `apd-c4-discipline` never-invent constraints — every
container, component, and `uses`/containment edge must be grounded in observed code,
flagged `machine_extracted` versus `hand_read`, with L3 components blocked by
default (see ADR-0021).

## Manual regeneration

If you change a 40-synthesis file by hand or want to regenerate without
re-running the gauntlet:

    apd-gauntlet build-report runs/<run_id>

## Report completeness gate (v1.6+)

Every gauntlet workflow run passes the finished HTML report through a
deterministic completeness gate before completing. The gate gives you a strong
guarantee: **the report you open is either complete or the run failed** — a
degraded report (placeholder executive summary, mismatched finding counts,
empty attack-path section, missing D3FEND overlays, bare taxonomy IDs) cannot
ship silently.

### What the gate checks

The `audit-report` step (step 5g in the workflow, also available standalone as
`apd-gauntlet audit-report <run_dir>`) does two things in one pass:

1. **Cross-check data.js against the authoritative YAMLs.** It parses the
   rendered `report-html/data.js` bundle back to a dict and verifies its records
   match `40-synthesis/deduped-findings.yaml`, `deduped-capabilities.yaml`,
   `attack-path.findings.yaml`, `nist-coverage.yaml`, and `attack-exposure.yaml`
   — so a build that dropped or corrupted records is caught before you read the
   report. (The APD coverage matrix is checked for non-emptiness and bundle-hash
   drift rather than record-by-record equality.)
2. **Enforce completeness checks**, each tagged as either `structural` or
   `editorial`. There are 8 core checks (6 structural, 2 editorial) plus one
   additional editorial check:

**Structural checks** (a failure blocks the run):

- `attack_paths_present` — the attack-paths section must be populated whenever
  `asset-graph.yaml` exists (exempt when attack-path analysis was not activated).
- `d3fend_overlay_present` — D3FEND bottleneck overlays declared in
  `defense-graph.yaml` must all reach `data.js` (exempt when no defense graph
  or zero overlays).
- `apd_matrix_nonempty` — the 9×N APD coverage matrix must have rows whenever
  findings are present.
- `coverage_rollups_nonempty` — rendered NIST and ATT&CK rollups must be
  non-empty when the authoritative coverage YAMLs have rows; this also covers the
  MASVS and MASWE rollups when those taxonomies are active and cited.
- `id_coverage_masvs` — every MASVS control cited on a finding or capability must
  appear in the rendered `masvs-coverage.yaml` (exempt when `masvs` is not active).
- `id_coverage_maswe` — every MASWE weakness cited on a finding must appear in the
  rendered `maswe-coverage.yaml` (exempt when `maswe` is not active).
- `taxonomy_titles_resolve` — no cited taxonomy ID may appear as a bare ID
  (title equals ID), which would indicate a failed reference-catalog load.
- `section_errors_empty` — the rendered report must carry no unresolved section
  errors.

Pre-existing cross-checks (`id_coverage_findings`, `id_coverage_capabilities`,
`id_coverage_nist`, `id_coverage_attack`, `id_coverage_masvs`,
`id_coverage_maswe`, `count_parity_severity`, `count_parity_totals`,
`nist_rollup_parity`, `data_js_recompute_drift`) are also structural.

**Editorial checks** (failures are self-healed, not blocking):

- `exec_summary_present` — the executive summary must be present and not the
  placeholder text.
- `editorial_sections_present` — `report-data.yaml` must contain
  `exec_summary`, `posture_summary`, `headline_findings`, and `next_steps`.
- `attack_path_finding_strip_present` — when at least one `disposition == "risk"`
  `apath-*` finding resolves to a path, at least one finding in `data.js` must
  carry an `attack_path` block (i.e. the hop-strip transform ran). Non-blocking;
  surfaces drift without gating the workflow.

### How the workflow uses the gate

The workflow runs the gate in a loop (cap: 2 remediation attempts, 3 total).
On each iteration:

- If both the structural check and the LLM semantic-faithfulness auditor pass,
  the loop exits and the run completes normally.
- On a failure, the report-writer is re-invoked with the full `report-audit.yaml`
  output. The report-writer addresses every failed **editorial** check
  (regenerating `report-data.yaml` blocks) and the semantic critique; then
  `build-report` rebuilds `data.js` and the gate runs again.
- If a **structural** failure is still unresolved after 2 remediations, the
  workflow **blocks the run** with an error. The rendered HTML is not delivered.
- A residual semantic discrepancy after 2 remediations is surfaced as a
  non-blocking log entry; it does not block the run.

The `audit-report` CLI prints a summary line:

    audit-report: pass (17 checks, 0 failed; structural_failed=0 editorial_failed=0)

It exits 1 on any failure, making it usable as a CI gate independently of the
workflow.

### The `report-audit.yaml` artifact

Every `audit-report` run writes `40-synthesis/report-audit.yaml` with per-check
results including `name`, `status`, `detail`, and `klass`. The report-writer
reads this file when remediating editorial failures.

### Legitimately empty states

The gate exempts states that are accurate run outcomes rather than build gaps:

- **No asset-graph.yaml** — attack-path analysis was not activated; the
  `attack_paths_present` check passes automatically.
- **No defense-graph.yaml or zero overlays** — the `d3fend_overlay_present`
  check passes automatically.
- **`is_empty_run: true`** in report metadata — all completeness checks are
  exempted (an empty run has no findings to summarize).
- **"Graph exists but no traversable chain"** — the attack-paths section renders
  an informative explanation block rather than path data; this is not a
  completeness failure (see [Empty-state interpretation](#empty-state-interpretation)).

## When `report-data.yaml` is absent

Older runs (pre-1.5) and partial runs may lack `report-data.yaml`. The HTML
report falls back to algorithmic equivalents:

- Headline findings: top 10 by (severity desc, confidence desc, id asc).
- Next steps: empty list.
- Executive summary: placeholder paragraph naming the run id.
- Posture summary: placeholder per-tier statements.

The Findings tab, Capabilities tab, Coverage tabs, Attack paths tab, and
Annexes tab all render fully from existing YAMLs in either case.

## Empty-state interpretation

Some report tabs show zero counts without further explanation in earlier versions.
The following empty states are **accurate run outcomes**, not rendering bugs:

**Attack Paths — "0 pairs / 0 paths / 0 bottleneck edges"**
This occurs when the asset graph exists (nodes and edges are present and rendered
in the interactive Cytoscape graph) but those edges do not form a traversable
chain from any declared attacker position to any declared crown jewel. The most
common cause: specialists reference prose documents (e.g., `tech_plan.md`) as
evidence rather than specific `asset_id` values, so the analyzer cannot
synthesize graph edges from prose. The "Enumerated paths" panel displays an
informative explanation block (blue-bordered) rather than a blank section. To
enable path enumeration, enrich
`00-context/asset-inventory.yaml` with explicit trust-boundary edges connecting
attacker positions to crown jewels, or have specialists tag finding evidence with
the `asset_id` of the affected component.

**Annexes — "0 surfaced" / "0 clusters"**
Contradictions and severity disagreements are only recorded when specialists
genuinely disagree. A run where all specialists operated from a shared baseline
(same rubric, same scope) will legitimately produce zero entries in both annexes.
When the synthesizer includes a `notes:` field in `contradictions.yaml` or
`severity-disagreements.yaml` explaining the absence, those notes are surfaced
directly in the Annexes tab beneath the count pill.

If either of these tabs is blank with no explanation, that is a template
rendering bug — check that `build-report` was run against the current
`report-template/` bundle.

## APD framework reference (Annexes §11)

The Annexes tab ends with a static **§11 — APD framework reference** card titled
"Three pillars, nine goals". It is always present (it does not depend on run data)
and explains the framework's **three pillars and nine goals** for readers new to
APD — software engineers, information-systems and cybersecurity auditors, and
risk-management professionals.

Each goal is shown with its lens question, a plain-language explanation and a
concrete example, and its primary NIST SP 800-53 Rev 5 control families. A
consolidated **Sources** block lists the standards the framework draws on (NIST
800-53r5, NIST CSF 2.0, NIST SP 800-160 Vol. 2, NIST SP 800-204, NIST SP 800-63B,
ISO/IEC 27001:2022, OWASP ASVS / Top 10 / API / LLM, The Open Group Open FAIR,
CSA Cloud Controls Matrix, MITRE ATT&CK / D3FEND / ATLAS, CWE, and others).

The card is deliberate about **what the gauntlet enforces versus what it cites for
context**: only NIST 800-53r5 is mapped on every finding and capability; MITRE
ATT&CK, CWE, and D3FEND are available on every run under a high-confidence
mapping discipline; OWASP Top 10 / API / LLM and MITRE ATLAS are opt-in per run;
and the remaining bodies are educational cross-references, not compliance
measurements.

The content is static JSX in `report-template/screens/Annexes.jsx` (labels are
pulled from the framework constants in `components.jsx`), so it does not interact
with the report completeness gate. As with any template change, edits require
rebuilding the bundle (`python tools/build_report_template.py`) and committing the
regenerated `app.js` and `.source-hash`.

## Contributing template changes

The JSX source lives in `report-template/`. After editing any JSX or CSS,
rebuild the precompiled bundle and commit the result:

    python tools/build_report_template.py
    git add tools/apd_gauntlet/data/report-template/
    git commit

CI gates that the precompiled bundle matches the JSX source
(`tools/check_report_template_freshness.py`). The Node toolchain
(esbuild 0.28.1 + react 18.3.1 + cytoscape 3.30.2 with cytoscape-dagre 2.5.0
and cytoscape-fcose 2.2.0) is contributor-only — no runtime user needs Node.
