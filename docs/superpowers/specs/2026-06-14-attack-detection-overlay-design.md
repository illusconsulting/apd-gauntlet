# Design: ATT&CK detection overlay — a derived technique → data-component view

- **Date:** 2026-06-14
- **Status:** Implemented. **Build note:** the live ATT&CK bundle is now v17+ — `detects` runs `detection-strategy → technique`, and data components are reached via `strategy.x_mitre_analytic_refs → analytic.x_mitre_log_source_references[].x_mitre_data_component_ref` (the old `x-mitre-data-source` / `x_mitre_data_source_ref` model is gone). `project_detection` walks the v17 chain; the projection is keyed on `DC####` data-component ids (stable across the restructure), per the §3 pin-to-data-components guidance.
- **Framework version at design:** 1.7.0 (main). No version bump (additive, derived).
- **New ADR:** none — instance of [ADR-0022](../../adrs/0022-derived-cross-framework-views.md) (derived cross-framework views, kind = *overlay*).
- **Related ADRs:** 0008 (multi-framework taxonomy mappings), 0022 (derived views).

## 1. Problem & goal

The gauntlet maps ATT&CK **mitigations** (M-codes) onto capabilities — the *prevention* side — but says nothing about **detection**. For each technique a finding exposes, ATT&CK already publishes the **data components** (and parent data sources) whose telemetry is required to detect that technique. Today that information never reaches the report, so a reviewer cannot ask "we are exposed to T1530 — do we even have the logging needed to *see* it?"

**Goal:** derive a detection overlay that, for each ATT&CK technique a finding exposes, surfaces the **data components ATT&CK says are needed to detect it**, and flags the telemetry **gap**. Per [ADR-0022](../../adrs/0022-derived-cross-framework-views.md) this is a **derived view (overlay)** — synthesizer-authored, no new `control_mappings` key, gated on `mitre_attack` already being declared.

This view is the natural companion to the **Non-Repudiation** goal (what audit/telemetry must exist) and complements the existing ATT&CK exposure rollup.

### Success criteria

1. `refresh-mitre` (extended) projects, per technique, its detecting data components → `data/mitre-attack-detection.json` (reusing the enterprise-attack STIX bundle it already fetches).
2. The synthesizer emits `40-synthesis/detection-coverage.yaml` (schema-validated) when `mitre_attack` is declared and ≥1 finding exposes a technique.
3. Per exposed technique: the required data components + a `telemetry` posture (`required` in v1; `covered`/`uncovered` deferred to v2).
4. The report surfaces "needed telemetry" inside the ATT&CK exposure view, tagged to Non-Repudiation.
5. Advisory only — never blocks; **silence on absence** (a technique ATT&CK lists no data component for produces no gap claim).
6. Full unit-test coverage; golden example regenerated; gates green.

## 2. Approved decisions

| # | Decision | Choice |
|---|----------|--------|
| 1 | Authorship | **Derived (synthesizer).** No emission key. |
| 2 | Gating | Auto-emit when `mitre_attack` ∈ declared (default-on) and ≥1 technique exposed. |
| 3 | v1 scope | **Detection *requirements* + gap surfacing.** "Covered/uncovered" (does a capability provide the telemetry) is **v2**. |
| 4 | Catalog source | **Extend** `refresh-mitre` (same STIX bundle already used for `mitre-mitigations.json`) → `data/mitre-attack-detection.json`. No new upstream source. |
| 5 | Artifact shape | Single-file rollup: `entries[]` keyed by exposed technique. |

## 3. External reference facts (pinned)

- **Source:** the enterprise-attack STIX bundle already fetched by `refresh-mitre` (`mitre/cti` enterprise-attack). It contains `x-mitre-data-component` and `x-mitre-data-source` objects and `relationship` objects of type **`detects`** linking a data component → a technique (`attack-pattern`).
- **ID scheme:** data sources `DS####` (e.g. `DS0015` Application Log); data components are named children (e.g. "Application Log Content"). Project each technique → `[{data_source_id, data_source_name, data_component_name}]`.
- **Version churn caveat:** ATT&CK v17+ restructured detections into *Detection Strategies* + *Analytics* on top of data components. **Pin to data components** (stable across v16→v18) and record the ATT&CK version in `_meta`; do not project the moving analytic layer in v1.
- **Coverage caveat:** not every technique lists data components. Absence → silent (honesty rule).

## 4. Internal wiring (mirrors the ATT&CK exposure rollup)

| Layer | File | Action |
|-------|------|--------|
| Catalog refresh | `tools/apd_gauntlet/refresh_mitre.py` (extend; existing `refresh-mitre` verb) | also project technique→data-components → `data/mitre-attack-detection.json` |
| Title/URL catalog | `tools/apd_gauntlet/report/taxonomy.py` | `data_component_titles()`; data-source URL `attack.mitre.org/datasources/<DS>` |
| Rollup | `tools/apd_gauntlet/synthesis/rollup.py` (`_attack_rollup` ~ exposure; new `_detection_rollup`) | from the exposed-technique set in the ATT&CK exposure rollup, attach required data components |
| Rollup schema | **new** `schemas/detection-coverage.schema.json` | validate |
| Validate | `tools/apd_gauntlet/validate.py` (`SYNTHESIS_ROLLUPS`) | register |
| Report load/transform | `report/loader.py`, `report/transform.py` (ATT&CK scene) | a "needed telemetry" column on the exposure table; Non-Repudiation tie-in |
| Report template | `report-template/screens/Coverage.jsx` (ATT&CK sub-tab) + rebuild | render telemetry requirements |
| Audit | `synthesis/audit.py` | advisory note only |

## 5. Component design (sketch)

- **`refresh_mitre.py`** — in the existing STIX walk, collect `x-mitre-data-component` objects and `detects` relationships; invert to `technique_id → [{data_source_id, data_source_name, data_component_name}]`; write `data/mitre-attack-detection.json` with `_meta` (incl. `attack_version`). Reuses the already-fetched bundle — one extra projection pass, no new fetch.
- **`_detection_rollup(findings, detection_catalog)`** — take the set of techniques exposed across findings (the same extraction the ATT&CK exposure rollup uses), and for each, attach its required data components and the finding IDs that expose it. Emit `detection-coverage.yaml`:

  ```yaml
  { schema_version: 1, generated_by: 'synthesizer',
    entries: [ { technique: 'T1530', technique_name: 'Data from Cloud Storage',
                 exposure_finding_ids: ['conf-...'],
                 required_data_components: [ { data_source_id: 'DS0010', data_source_name: 'Cloud Storage',
                                               data_component_name: 'Cloud Storage Access' } ],
                 telemetry: 'required' } ] }
  ```

- **Report** — add a "needed telemetry" column to the ATT&CK exposure table (Coverage.jsx) and a Non-Repudiation cross-reference. Labeled derived.

### v2 (noted, not built now): telemetry *coverage*

Deciding `covered` vs `uncovered` needs a capability→data-component signal. Two candidate sources, both deferred:

- **Derive from D3FEND** — a capability's D3FEND technique acts on digital artifacts that map (via the shared artifact ontology) to ATT&CK data sources, implying observed telemetry.
- **A capability `detects[]` field** — explicit, but that would be an *emission* addition (new ADR), against the grain of this view.

## 6. Sequencing

1. Extend `refresh_mitre.py` + `data/mitre-attack-detection.json` + `taxonomy.py` loader.
2. `detection-coverage.schema.json` + `validate.py` registration.
3. `_detection_rollup` + `RollupResult` + gated dispatch/write.
4. Report data (loader/transform) + Coverage.jsx column + bundle rebuild.
5. Advisory audit note; docs; golden regen.

## 7. Risks & mitigations

- **ATT&CK detection restructure (v17+)** → pin to data components, record `attack_version`, ignore the analytic layer in v1.
- **Over-claiming a telemetry "gap"** when v1 only knows *requirements* → label the column "needed telemetry," not "missing"; defer covered/uncovered to v2.
- **Bundle freshness gate** on the Coverage.jsx edit → rebuild + commit `app.js`/`.source-hash`.

## 8. Out of scope

- Telemetry **coverage** (covered/uncovered) — v2.
- MITRE CAR / Sigma analytic mapping — separate, SOC-oriented, later.
- A capability-side `detects[]` emission field — would be an emission taxonomy (different ADR).
