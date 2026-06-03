# HTML Advisory Report (v1.6)

Every gauntlet run automatically produces an interactive HTML view of the
synthesizer's outputs at:

    runs/<run_id>/40-synthesis/report-html/index.html

Open the file in any recent browser (offline — no network needed). The bundle
contains six tabs (Overview, Findings, Capabilities, Coverage, Attack paths,
Annexes) sourced from the existing `40-synthesis/*.yaml` artifacts plus the
synthesizer-emitted `report-data.yaml`.

The Coverage tab renders taxonomy tooltips for every cited control or technique
ID. Tooltip families include NIST 800-53r5, MITRE ATT&CK, CWE, OWASP (web /
API / LLM), MITRE D3FEND, and — when `mitre_atlas` is declared for the run —
**MITRE ATLAS** (adversarial-ML techniques). A bare ID in a tooltip (title
equals the ID string) means the reference catalog for that family failed to
load; this is caught by the completeness gate's `taxonomy_titles_resolve` check.

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
2. **Enforce 8 completeness checks**, each tagged as either `structural` or
   `editorial`:

**Structural checks** (a failure blocks the run):

- `attack_paths_present` — the attack-paths section must be populated whenever
  `asset-graph.yaml` exists (exempt when attack-path analysis was not activated).
- `d3fend_overlay_present` — D3FEND bottleneck overlays declared in
  `defense-graph.yaml` must all reach `data.js` (exempt when no defense graph
  or zero overlays).
- `apd_matrix_nonempty` — the 9×N APD coverage matrix must have rows whenever
  findings are present.
- `coverage_rollups_nonempty` — rendered NIST and ATT&CK rollups must be
  non-empty when the authoritative coverage YAMLs have rows.
- `taxonomy_titles_resolve` — no cited taxonomy ID may appear as a bare ID
  (title equals ID), which would indicate a failed reference-catalog load.
- `section_errors_empty` — the rendered report must carry no unresolved section
  errors.

Pre-existing cross-checks (`id_coverage_findings`, `id_coverage_capabilities`,
`id_coverage_nist`, `id_coverage_attack`, `count_parity_severity`,
`count_parity_totals`, `nist_rollup_parity`, `data_js_recompute_drift`) are also
structural.

**Editorial checks** (failures are self-healed, not blocking):

- `exec_summary_present` — the executive summary must be present and not the
  placeholder text.
- `editorial_sections_present` — `report-data.yaml` must contain
  `exec_summary`, `posture_summary`, `headline_findings`, and `next_steps`.

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

    audit-report: pass (16 checks, 0 failed; structural_failed=0 editorial_failed=0)

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
via Mermaid) but those edges do not form a traversable chain from any declared
attacker position to any declared crown jewel. The most common cause: specialists
reference prose documents (e.g., `tech_plan.md`) as evidence rather than specific
`asset_id` values, so the analyzer cannot synthesize graph edges from prose. The
"Enumerated paths" panel displays an informative explanation block (blue-bordered)
rather than a blank section. To enable path enumeration, enrich
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
(esbuild 0.21.5 + react 18.3.1 + mermaid 10.9.1) is contributor-only — no
runtime user needs Node.
