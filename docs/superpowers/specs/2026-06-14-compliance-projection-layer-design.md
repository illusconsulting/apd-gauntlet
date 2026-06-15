# Design: compliance projection layer — derive HIPAA + CSF 2.0 from 800-53r5 coverage

- **Date:** 2026-06-14
- **Status:** Implemented — crosswalks **CPRT-grounded**. `apd-gauntlet refresh-crosswalks --csf2-json <export> --hipaa-json <export>` grounds the control-level crosswalks against operator-downloaded NIST CPRT JSON exports. **Data finding (from the real exports):** the CPRT **CSF 2.0** 800-53 references are *family-level* (a subcategory → 8-20 control families) — too coarse to project raw — and the **800-66r2** HIPAA export has *no control-level* 800-53 mapping (it uses a "relevant publications" model; the control-level crosswalk lives only in 800-66 **r1** Appendix D). So `refresh-crosswalks` does not import raw — it **validates** that each curated control-level mapping is a subset of NIST's stated references (dropping any that exceed scope — it caught 3), enriches titles, and records provenance (`source` + `source_sha256` in `_meta`, so the files are now freshness-`COVERED`). The raw CPRT exports are git-ignored inputs (download from `csrc.nist.gov/projects/cprt`); the grounded crosswalk JSON is committed.
- **Framework version at design:** 1.7.0 (main). No version bump (additive, derived).
- **New ADR:** none — instance of [ADR-0022](../../adrs/0022-derived-cross-framework-views.md) (derived cross-framework views, kind = *projection*).
- **Related ADRs:** 0008 (multi-framework taxonomy mappings), 0011 (report completeness gate), 0022 (derived views).

## 1. Problem & goal

The gauntlet anchors compliance on **NIST 800-53r5** and already produces `nist-coverage.yaml` (every cited control, with finding/capability provenance and posture). But the SUTs answer to **healthcare auditors**, who do not speak 800-53 natively — they speak the **HIPAA Security Rule** and, increasingly, **NIST CSF 2.0**. NIST publishes authoritative, machine-readable crosswalks between 800-53r5 and both vocabularies. We can therefore **project** our existing 800-53r5 coverage into HIPAA and CSF 2.0 with **no new specialist work**.

**Goal:** derive `hipaa-coverage.yaml` + `csf2-coverage.yaml` from `nist-coverage.yaml` × the NIST crosswalks, and render a **"Compliance Crosswalk"** Coverage family — explicitly a *derived projection, not an audit attestation*, carrying per-mapping fidelity. Per [ADR-0022](../../adrs/0022-derived-cross-framework-views.md) this is a **derived view (projection)**.

**Targets for v1:** HIPAA Security Rule + NIST CSF 2.0 (per scoping decision). HITRUST / ISO 27001 are deferred — they are additional catalogs, not new mechanism.

### Success criteria

1. `refresh-crosswalks` produces `data/hipaa-800-53-crosswalk.json` + `data/csf2-800-53-crosswalk.json` from NIST sources, each row carrying the STRM relationship where published.
2. The synthesizer emits `hipaa-coverage.yaml` + `csf2-coverage.yaml` by projecting `nist-coverage.yaml`; gated on `projections:` run-config (default `[hipaa, csf2]`).
3. Each HIPAA standard / CSF subcategory row aggregates the 800-53 controls mapping to it, inherits posture + finding/capability provenance, and carries mapping fidelity.
4. A "Compliance Crosswalk" Coverage family renders both, labeled **derived projection — not an audit attestation**, with the STRM relationship visible.
5. Advisory only; **silence on absence**; full test coverage; golden regen; gates green.

## 2. Approved decisions

| # | Decision | Choice |
|---|----------|--------|
| 1 | Authorship | **Derived (synthesizer).** Pure projection of `nist-coverage.yaml`; no emission key, no specialist work. |
| 2 | Targets (v1) | **HIPAA Security Rule + NIST CSF 2.0.** HITRUST/ISO deferred. |
| 3 | Gating | New run-config `projections: [hipaa, csf2]` (default on). Not part of `taxonomies` (that enum = emission only). |
| 4 | Fidelity | Carry **NIST IR 8477 STRM** relationship (`subset`/`superset`/`intersect`/`equal`) per mapping; render it; never present an `intersect` as full coverage. |
| 5 | Framing | Report family labeled **"derived projection — not an audit attestation."** Load-bearing disclaimer. |
| 6 | Catalog source | `refresh-crosswalks` CLI + two bundled JSON catalogs from NIST CPRT / CSRC. |

## 3. External reference facts (pinned) — spike result

Both crosswalks are **published by NIST as machine-readable artifacts** (spike, 2026-06-14):

- **HIPAA Security Rule → 800-53r5 (+ CSF):** NIST **SP 800-66r2** (Feb 2024). Its mappings are in the **Cybersecurity & Privacy Reference Tool (CPRT)** with JSON + Excel export, mapping each HIPAA standard/implementation-specification to CSF subcategories **and** 800-53r5 controls. (CPRT: `https://csrc.nist.gov/projects/cprt`.) **Preferred ingestion:** the CPRT JSON dataset for 800-66r2; XLSX crosswalk as fallback. *Confirm the exact CPRT dataset identifier at implementation time.*
- **CSF 2.0 → 800-53r5:** direct NIST files — JSON via the CPRT/NUDP endpoint (`https://csrc.nist.gov/extensions/nudp/services/json/csf/download?olirids=all`) and XLSX (`https://csrc.nist.gov/files/pubs/sp/800/53/r5/upd1/final/docs/csf-pf-to-sp800-53r5-mappings.xlsx`).
- **STRM relationship types** (NIST IR 8477): `subset_of`, `superset_of`, `intersects_with`, `equal_to`, `not_related_to`. Where the source crosswalk supplies a relationship, carry it; where it supplies only an unqualified mapping, record `relationship: unspecified` and render conservatively (treat as `intersects_with` for posture).

**Many-to-many caveat (load-bearing):** one 800-53 control maps to several HIPAA standards / CSF subcategories and vice-versa. A projected row's posture is the **aggregate** of its contributing controls' postures; a row with only `intersects_with` contributors is **partial**, and must render as such.

## 4. Internal wiring (projection of an existing rollup — lighter than a finding-level taxonomy)

| Layer | File | Action |
|-------|------|--------|
| Crosswalk refresh | **new** `tools/apd_gauntlet/refresh_crosswalks.py` + `refresh-crosswalks` verb | fetch CPRT/CSRC → `data/hipaa-800-53-crosswalk.json`, `data/csf2-800-53-crosswalk.json` |
| Title/URL catalog | `report/taxonomy.py` | `hipaa_titles()` (§164.3xx standard names), `csf2_titles()` (subcategory names); URLs to the CSF tool / HIPAA reg |
| Rollup | `synthesis/rollup.py` (`_nist_rollup` is the input) | `_framework_projection_rollup(nist_rollup, crosswalk)` → two artifacts |
| Rollup schema | **new** `schemas/hipaa-coverage.schema.json`, `schemas/csf2-coverage.schema.json` | validate |
| Run-config | `schemas/run-config.schema.json` | add `projections` array (`enum: [hipaa, csf2]`); default applied in `init_run` |
| Validate | `validate.py` (`SYNTHESIS_ROLLUPS`) | register both |
| Report load/transform | `report/loader.py`, `report/transform.py` | new "Compliance Crosswalk" family + scenes |
| Report template | `report-template/screens/Coverage.jsx` (+ rebuild) | HIPAA + CSF2 sub-tabs, derived/fidelity labeling |
| Audit | `synthesis/audit.py` | advisory; `taxonomy_titles_resolve` covers the projected ids |

**Cheapest compute of the three derived views** — it consumes `nist-coverage.yaml` (already built) and two static crosswalk tables; it never touches findings/capabilities directly.

## 5. Component design (sketch)

- **`refresh_crosswalks.py`** — two hardened fetches. Project to:

  ```json
  // hipaa-800-53-crosswalk.json
  { "_meta": { "source": "NIST CPRT SP 800-66r2", "fetched_at": "...", "source_sha256": "..." },
    "mappings": [ { "hipaa": "164.312(a)(1)", "hipaa_title": "Access Control",
                    "nist": "AC-3", "relationship": "intersects_with" } ] }
  ```

  (CSF2 analogous: `{ "csf": "PR.AA-05", "csf_title": "...", "nist": "AC-3", "relationship": "..." }`.)

- **`_framework_projection_rollup(nist_rollup, crosswalk)`** — invert the crosswalk to `nist_control → [target_id]`; for each control in `nist_rollup.controls`, fan its posture + finding/cap ids out to each target it maps to; aggregate per target:

  ```yaml
  { schema_version: 1, generated_by: 'synthesizer',
    entries: [ { target_id: '164.312(a)(1)', target_title: 'Access Control',
                 source_controls: [ { id: 'AC-3', relationship: 'intersects_with' } ],
                 finding_ids: [...], capability_ids: [...],
                 posture: 'covered|gapped|both|silent',
                 fidelity: 'exact|partial' } ] }   # 'partial' if any contributor is intersects/subset/unspecified
  ```

  `posture` via the existing `coverage_logic.posture(has_findings, has_caps)`; `fidelity = exact` only when all contributing relationships are `equal_to`/`superset_of`, else `partial`.

- **Report** — a "Compliance Crosswalk" family with HIPAA + CSF2 sub-tabs; each row shows the target, contributing 800-53 controls (with relationship), posture, fidelity; a prominent **"derived projection — not an audit attestation"** banner.

## 6. Sequencing

1. **Spike confirm** the CPRT 800-66r2 dataset id + JSON shape (the one open data detail) — small.
2. `refresh_crosswalks.py` + two `data/*.json` + `taxonomy.py` titles.
3. Two coverage schemas + `validate.py` registration; `run-config` `projections`.
4. `_framework_projection_rollup` + `RollupResult` + gated dispatch/write.
5. Report data + Coverage.jsx family + bundle rebuild.
6. Advisory audit; docs (`taxonomy-mappings.md` derived-views section, `html-report.md`); golden regen.

## 7. Risks & mitigations

- **Compliance misread** (a projection mistaken for certification) → mandatory derived/fidelity/"not an attestation" labeling; STRM relationship rendered per row; `partial` fidelity visible.
- **Many-to-many dilution** → aggregate posture honestly; a target touched only by `intersects_with` controls is `partial`, never shown as fully covered.
- **HIPAA CPRT dataset id uncertainty** → the one residual data unknown; a §6.1 spike resolves it; XLSX crosswalk is the fallback ingestion path.
- **Crosswalk staleness** → `_meta` + `reference_db_versions` surface the pin; quarterly refresh.

## 8. Out of scope

- HITRUST CSF, ISO 27001/27002 (additional catalogs, same mechanism — later).
- Privacy Framework / 800-171 projections.
- Any claim of compliance *status* — this is a coverage view in another vocabulary, full stop.
