# Design: OWASP MASVS + MASWE as first-class report taxonomies (mobile pack)

- **Date:** 2026-06-09
- **Status:** Approved (design); pending spec review → implementation plan
- **Framework version at design:** 1.6.0 (main). Target: **1.7.0**.
- **New ADR:** 0014 (ADRs currently run through 0013).
- **Related ADRs:** 0008 (multi-framework taxonomy mappings), 0012 (MITRE ATLAS finding taxonomy — closest precedent), 0003 (pluggable domain packs), 0011 (report completeness gate).

## 1. Problem & goal

When the `mobile-applications` domain pack is included in a run, the HTML report must **explicitly reference and link to OWASP MASWE and OWASP MASVS in the same way it already references and links to MITRE ATT&CK and D3FEND** — i.e. per-finding clickable chips, hover titles, a dedicated Coverage tab, coverage rollups, and the §11 framework-reference card — not merely as prose buried in finding `detail`.

### Current state (the gap)

- The mobile pack already cites MASVS/MASWE/MASTG **densely (~100 hits) but only as prose** in `domain.yaml` `regulatory_anchors`, `severity-rubric.md`, and all nine `common-patterns/*.md`. At runtime these IDs reach the report **only inside finding `detail` strings** — never in structured `control_mappings`. (Verified: `examples/apd-20260602-acme-mobile-banking/expected/10-trustworthiness/confidentiality.findings.yaml` carries `detail: Per MASVS-STORAGE-1…` while its `control_mappings` block holds only `cwe` + `nist_800_53r5`.)
- `schemas/finding.schema.json` `control_mappings` is a **closed set** (`additionalProperties:false`): `nist_800_53r5` (required), `mitre_attack`, `cwe`, `owasp_top10`, `owasp_api_top10`, `owasp_llm_top10`, `atlas`. No `masvs`/`maswe` key exists.
- Taxonomy activation is gated on the **run-level** `taxonomies` list in `.apd-run.yaml` (set via `init-run --taxonomies`), **not** the domain pack. Domain packs have **no** `taxonomies` field.
- `report-template/screens/Annexes.jsx` §11 Sources explicitly labels MASVS/MASTG **"not a mapped taxonomy."**
- The report has **no active-taxonomy / active-pack signal** in `data.meta` beyond the joined `domain_pack.name` string.

### Success criteria

1. A run that includes the `mobile-applications` pack auto-activates the `masvs` and `maswe` taxonomies (no extra operator flag).
2. Findings (and capabilities, for MASVS) carry structured `control_mappings.masvs` / `control_mappings.maswe` ID lists, schema-validated.
3. The report renders per-finding **clickable** MASVS/MASWE chips (links to `mas.owasp.org`), hover titles, and dedicated **MASVS** + **MASWE** Coverage sub-tabs.
4. Deterministic `masvs-coverage.yaml` + `maswe-coverage.yaml` rollups are produced and gated by the run's declared taxonomies.
5. §11 framework-reference card describes MASVS/MASWE as mapped taxonomies (conditional on activation) and is honest about enforcement.
6. Completeness, freshness, and schema gates cover the new families; full test coverage; golden example regenerated and green.

## 2. Approved decisions (from brainstorming)

| # | Decision | Choice |
|---|----------|--------|
| 1 | Activation | **Pack declares → auto-seeds the run.** New `taxonomies` field on the domain-pack schema; mobile pack declares `[masvs, maswe]`; `init_run` unions pack taxonomies into the run's `taxonomies` list. Downstream rollup/report keep gating on the (auto-populated) run list. |
| 2 | Render scope | **Full ATT&CK parity** — per-finding clickable chips + hover titles + dedicated Coverage sub-tab + coverage rollup YAML + audit & freshness gates + §11 card. |
| 3 | Mapping model | **Both, flat ID lists.** `control_mappings.maswe: [MASWE-####]` and `control_mappings.masvs: [MASVS-CAT-N]`. Justification lives in finding `detail`. |
| 3a | Capability-side MASVS | **Included** (confirmed in review). Capabilities carry `control_mappings.masvs` = controls they satisfy → enables NIST-style covered/gapped posture in the MASVS Coverage tab. |
| 4 | Catalog source | **`refresh-mas` CLI + bundled JSON** (mirrors `refresh-atlas`/`refresh-d3fend`), with `_meta` freshness. |
| — | MASTG | **Out of scope** (future third family). |

## 3. External reference facts (pinned)

### MASVS (the control / NIST-analog)

- v2.x "MASVS-CATEGORY" model; pin **tag v2.1.0** (the in-file `metadata.version` is a build placeholder `vx.x.x` — record the git tag separately).
- **8 categories** (`MASVS-STORAGE/CRYPTO/AUTH/NETWORK/PLATFORM/CODE/RESILIENCE/PRIVACY`) × **24 controls** (`MASVS-{CAT}-{N}`, N per-category sequential). Counts: STORAGE 2, CRYPTO 2, AUTH 3, NETWORK 2, PLATFORM 3, CODE 4, RESILIENCE 4, PRIVACY 4.
- Canonical machine-readable source: **`OWASP_MASVS.yaml` at repo root** (`OWASP/masvs`, branch `master`). Shape: `metadata` + `groups[]{id,index,title,description, controls[]{id,statement,description}}`. Use `statement` as the control title.
- Deep-link (verified 200): control = `https://mas.owasp.org/MASVS/controls/{CONTROL_ID}/` (stable, regex-derivable). Category overview = `https://mas.owasp.org/MASVS/{NN}-MASVS-{CAT}/` where `{NN}` is a doc-chapter prefix (05=STORAGE…12=PRIVACY) — **less stable; we link controls only**.

### MASWE (the weakness / CWE-analog)

- **Beta / under active development** — IDs/URLs/structure can churn → **pin a commit SHA**. Site label "MASWE (Beta)".
- ID scheme `MASWE-NNNN` (4-digit zero-padded; **gaps + deprecations** exist). ~116 active weaknesses; top observed ~MASWE-0117.
- Organized **under the 8 MASVS categories** — the category is a repo dir, an on-site group, **and a required URL path segment**.
- Source: per-weakness markdown **YAML front-matter** at `weaknesses/<MASVS-CATEGORY>/MASWE-NNNN.md` (`OWASP/maswe`, default branch `main`; `master` also resolves). No consolidated export → a small walker builds the catalog. Front-matter keys: `title, id, alias, platform[], profiles[], mappings{masvs-v1[], masvs-v2[], cwe[](numeric), …}, refs[], status`. Deprecated entries carry `status: deprecated` + `covered_by: [MASWE-XXXX]`.
- Deep-link (verified 200): `https://mas.owasp.org/MASWE/{MASVS-CATEGORY}/MASWE-NNNN/` — **category in path is mandatory**, so the catalog must store the filing category per weakness (use the **filing** category, not a mapped-control category).

## 4. Internal wiring template (what we mirror)

The cleanest precedent is **ATLAS** (ADR-0012, finding-level rollup) for plumbing + the **ATT&CK/D3FEND** clickable-URL treatment. The chain a finding-level taxonomy touches (with current anchors):

| Layer | File | Note |
|-------|------|------|
| ID regexes | `schemas/_defs.schema.json` (~8–37) | central `$defs`; others `$ref` in |
| Finding mapping | `schemas/finding.schema.json` (61–105) | `control_mappings`, `additionalProperties:false` |
| Capability mapping | `schemas/capability.schema.json` (26–75) | defensive side |
| Run declaration | `schemas/run-config.schema.json` (15–22) | `taxonomies` enum |
| Specialist discipline | `.claude/skills/apd-control-mappings/SKILL.md` (10–12, 152–291) | allowed-keys + per-taxonomy bar |
| Rollup | `tools/apd_gauntlet/synthesis/rollup.py` (`_cwe_rollup` 313–340; `_nist_rollup` 95–127; `_declared_taxonomies` 230–232; `build_rollups` 267–310; `_write` 480–502) | finding-level vs control-posture templates; gated `if x in declared` |
| Coverage helpers | `tools/apd_gauntlet/synthesis/coverage_logic.py` (1–112) | `extract_ids_from_mapping`, `posture`, no report import |
| Validation | `tools/apd_gauntlet/validate.py` (`SYNTHESIS_ROLLUPS` 234–274) | filename→schema |
| Report load | `tools/apd_gauntlet/report/loader.py` (`load_run` 486–629; pack-name 254–357) | which coverage YAMLs reach the report |
| Report transform | `tools/apd_gauntlet/report/transform.py` (`meta_block` 155–213; `_FAMILY_DISPLAY` 1916–1920; `findings_array` 333–415; `sections` 1798–1870; `_collect_referenced_ids` 1992–2117; `taxonomy_dict` 2120–2185) | builds `window.APD_DATA` |
| Title/URL catalog | `tools/apd_gauntlet/report/taxonomy.py` (loaders 111–307; `attack_technique_url` 214; `d3fend_url` 225; `reference_db_versions` 278–307; invalidation map ~338) | only ATT&CK + D3FEND build URLs today |
| Per-finding chips | `report-template/screens/Findings.jsx` (151–152 preview; 299–321 detail mapping-groups) | one `<dl class=mapping-group>` per family |
| Coverage tab | `report-template/screens/Coverage.jsx` (1–170; `AttackTable` 82–124; `NistTable`; `APDMatrix`) | sub-tabs |
| Shared chip | `report-template/components.jsx` (`TaxonomyTag` 55–110, `TagRow` 112) | url→`<a>` else `<span>`; **no change needed** |
| §11 card | `report-template/screens/Annexes.jsx` (203–279; Sources line 265; enforcement note 276) | static; MASVS/MASTG = "not a mapped taxonomy" today |
| Refresh | `tools/apd_gauntlet/refresh_d3fend.py`, `refresh_atlas.py`; `cli.py` `refresh-*` verbs (590–602) | hardened fetch pattern |
| Build/freshness | `tools/build_report_template.py` → `report-template/.build/build.mjs` → `data/report-template/app.js` + `.source-hash`; `tools/check_report_template_freshness.py`; CI `.github/workflows/python-tests.yml` (26–27) | any JSX edit → rebuild+commit or CI fails |
| Completeness gate | `tools/apd_gauntlet/synthesis/audit.py` (`id_coverage_attack` 166–172; `coverage_rollups_nonempty` 348–361; `taxonomy_titles_resolve` 363–375) | structural/blocking checks |

**Two structural facts that shape the design:**

- Per-finding **chips render whenever the IDs are present** (ungated), because `findings_array`/`_collect_referenced_ids`/`taxonomy_dict` harvest from `control_mappings` directly. CWE/ATT&CK chips work this way. → MAS chips will appear on any finding that carries MAS IDs.
- The coverage **rollup YAML is gated** on the declared taxonomies, and today **no finding-level coverage YAML reaches the report** (CWE/OWASP/ATLAS coverage YAMLs exist only for validation/external use; the report re-derives chips from mappings). Because we want a real **Coverage tab**, MASVS/MASWE will be the **first finding-level coverage YAMLs the report loads** (`report/loader.py` change).

## 5. Component design

### 5.1 Schemas

**`schemas/_defs.schema.json`** — add `$defs`:

- `maswe_id`: `^MASWE-[0-9]{4}$`
- `masvs_control_id`: `^MASVS-(STORAGE|CRYPTO|AUTH|NETWORK|PLATFORM|CODE|RESILIENCE|PRIVACY)-[1-9][0-9]*$`
- `masvs_category_id`: `^MASVS-(STORAGE|CRYPTO|AUTH|NETWORK|PLATFORM|CODE|RESILIENCE|PRIVACY)$`

**`schemas/finding.schema.json`** (`control_mappings`, ~84–99, additive) — add:

- `maswe`: array of `maswe_id` (uniqueItems)
- `masvs`: array of `masvs_control_id` (uniqueItems)

**`schemas/capability.schema.json`** (`control_mappings`) — add:

- `masvs`: array of `masvs_control_id` (controls the capability satisfies). *(No `maswe` on capabilities — weaknesses aren't "satisfied".)*

**`schemas/run-config.schema.json`** (`taxonomies` enum, line ~20) — add `masvs`, `maswe`.

**`schemas/domain.schema.json`** (additive; `additionalProperties:false` so it must be declared) — add optional:

```yaml
taxonomies:        # taxonomies this pack activates when selected
  type: array
  items: { enum: [cwe, mitre_attack, d3fend, owasp_top10, owasp_api_top10, owasp_llm_top10, mitre_atlas, masvs, maswe] }
  uniqueItems: true
```

(Enum kept in sync with run-config `taxonomies`. Not required → existing packs unaffected.)

**New `schemas/masvs-coverage.schema.json`** — both new coverage schemas follow the **single-file `cwe-coverage.schema.json` convention** (the YAML is itself the validated document; no separate `-doc` envelope wrapper, unlike `nist-coverage-doc`/`attack-exposure-doc`). MASVS uses the NIST-coverage *content* shape but the CWE *packaging* (one schema, registered directly in `SYNTHESIS_ROLLUPS`):

```yaml
{ schema_version: 1, generated_by: 'synthesizer',
  controls: [ { masvs_id, name, category, category_title,
                finding_count, finding_ids[], surfaces[],
                capability_count, capability_ids[],
                posture: covered|gapped|both|silent } ] }
```

**New `schemas/maswe-coverage.schema.json`** — CWE-coverage-shaped:

```yaml
{ schema_version: 1, generated_by: 'synthesizer',
  entries: [ { maswe_id, name, category, status, parent_masvs[],
               finding_count, finding_ids[], surfaces[] } ] }
```

### 5.2 Activation: pack-declared → auto-seeded

- `domains/mobile-applications/domain.yaml`: add `taxonomies: [masvs, maswe]`.
- `tools/apd_gauntlet/init_run.py` `scaffold_run` (~32–60): **union each selected pack's declared `taxonomies` into the run's `taxonomies` list** (read each `domains/<name>/domain.yaml`), then merge any operator `--taxonomies`. Dedupe, stable order. Result is written verbatim into `.apd-run.yaml` `taxonomies:` (the existing gate). *No downstream rollup/report gating change needed — the run list is now auto-populated.*
- `tools/apd_gauntlet/build_domain_skill.py`: surface the merged pack `taxonomies` into the generated `apd-domain` SKILL.md frontmatter (alongside `metadata.packs`) so specialists know MAS emission is in-scope.
- **`data.meta.active_taxonomies`** — new field. `report/loader.py` lifts `run_cfg['taxonomies']` into `RunArtifacts`; `transform.meta_block` (155–213) emits it into `data.meta`. This is the explicit signal the §11 card and Coverage sub-tabs gate on. (Today nothing surfaces the run taxonomies into the report.)

**Gating policy (consistent with existing families):**

- Per-finding/per-capability **chips + hover** render whenever MAS IDs are present (ungated) — matches CWE/ATT&CK.
- **Rollup YAML** gated on `masvs`/`maswe` ∈ declared taxonomies.
- **Coverage sub-tab** visible iff `data.meta.active_taxonomies` contains the family **and** the coverage data is non-empty.
- **§11 "mapped taxonomy" framing** conditional on `active_taxonomies` (non-mobile reports keep the accurate "informs the pack" wording).

### 5.3 Reference catalog + `refresh-mas`

**New `tools/apd_gauntlet/refresh_mas.py`** (+ `refresh-mas` verb in `cli.py`, mirroring `refresh_atlas`/`refresh_d3fend`; hardened: 60s timeout, size cap, content-length check):

- `data/masvs.json` from `OWASP_MASVS.yaml @ v2.1.0`:

  ```json
  { "_meta": {"fetched_at","source","source_sha256","version":"v2.1.0","count":24},
    "controls": { "MASVS-STORAGE-1": {"title":"<statement>","category":"MASVS-STORAGE","category_title":"Storage"}, ... } }
  ```

- `data/maswe.json` from `OWASP/maswe @ <pinned commit>`, walking `weaknesses/<CAT>/MASWE-*.md` front-matter:

  ```json
  { "_meta": {"fetched_at","source","commit","count"},
    "weaknesses": { "MASWE-0001": {"title","category":"MASVS-STORAGE","status":"new",
                                   "masvs_v2":["MASVS-STORAGE-2","MASVS-PRIVACY-1"],"cwe":[209,532]}, ... } }
  ```

  - **Deprecation:** keep `status`; for `status: deprecated` follow `covered_by` — do not deep-link dead weaknesses (skip from coverage `entries` or render as superseded).
  - **Category is the filing dir**, used for the URL path.

**`tools/apd_gauntlet/report/taxonomy.py`** — add (lru-cached + registered for invalidation):

- `masvs_titles()` / `maswe_titles()` from the bundled JSON.
- `masvs_url(id)` → `https://mas.owasp.org/MASVS/controls/{id}/` (pure regex).
- `maswe_url(id)` → `https://mas.owasp.org/MASWE/{category}/{id}/` — **reads the catalog** for the category; returns `None` if unknown (renders as a non-clickable span rather than a broken link).
- Register both catalogs in `reference_db_versions()` (286–307) → report meta shows "MASVS v2.1.0" + "MASWE @ <commit/date>".

### 5.4 Rollups (`synthesis/rollup.py`)

- **`_masvs_rollup(findings, caps)`** — model on `_nist_rollup` (95–127): per MASVS control, union finding IDs (exposure) + capability IDs (satisfaction) via `coverage_logic.extract_ids_from_mapping`, compute `posture` via `coverage_logic.posture(has_findings, has_caps)`, look up `name`/`category` from the catalog. First-appearance-then-id ordering. → `masvs-coverage.yaml`.
- **`_maswe_rollup(findings)`** — model on `_cwe_rollup` (313–340): per MASWE weakness, finding IDs + surfaces, name/category/status/parent-MASVS from catalog. → `maswe-coverage.yaml`.
- `RollupResult` (47–56): add `masvs`, `maswe` fields. `build_rollups` (282–290): gate each `if 'masvs'/'maswe' in declared`. `_write` (491–502): conditional writes.
- `tools/apd_gauntlet/validate.py` `SYNTHESIS_ROLLUPS` (234–274): register `masvs-coverage.yaml`→schema, `maswe-coverage.yaml`→schema.
- Phase order unchanged — `rollup` already runs after tier-4 (`plan_run.py` step 15), so tier-4 findings' MAS mappings union in automatically.

### 5.5 Report transform (`report/transform.py`)

- `_MASVS_FAMILY_DISPLAY = 'OWASP MASVS'`, `_MASWE_FAMILY_DISPLAY = 'OWASP MASWE'` (near 1916–1920).
- `findings_array` mappings dict (377–407): add `masvs`, `maswe` via `_extract_ids_from_mapping`.
- `_collect_referenced_ids` (1992–2117): add `masvs`/`maswe` buckets, harvested from finding **and** capability `control_mappings`, **and** from the loaded coverage rollups (so coverage-only ids still get titles).
- `taxonomy_dict` (2120–2185): add `masvs`/`maswe` branches setting `family`, `title` (from catalog), and **`url`** (clickable). *(Note: OWASP families currently have no hover entry; we are adding MAS the right way — with hover + url.)*
- `meta_block`: emit `active_taxonomies`.
- **New coverage scenes** `masvs_coverage` + `maswe_coverage`: row-builder transforms (tolerant of missing artifacts) registered in the `sections` list (1798–1870).

### 5.6 Report load (`report/loader.py`)

- Load `40-synthesis/masvs-coverage.yaml` and `maswe-coverage.yaml` into `RunArtifacts` **when present** (optional artifacts — absent on non-mobile runs). These are the first finding-level coverage YAMLs the report consumes; include them in the source-hash set used by the freshness gate.

### 5.7 Report template (JSX → bundle rebuild)

- `report-template/screens/Findings.jsx` (299–321 + 151–152): add **OWASP MASVS** and **OWASP MASWE** `<dl class=mapping-group>` blocks with `<TagRow ids={f.mappings.masvs/maswe}/>`; extend the outer guard. Chips are clickable because `taxonomy_dict` supplies `url`.
- `report-template/screens/Coverage.jsx`: add two sub-tabs after ATT&CK — **MASVS** (control table: control id chip, name, posture, exposed-finding count, satisfying-capability count) and **MASWE** (weakness table: id chip, name, category, finding count). Tab buttons gated on `data.meta.active_taxonomies` + non-empty data. Renumber sub-tabs accordingly.
- `report-template/screens/Annexes.jsx` (§11, 265 + 276): make the MASVS/MASWE Sources line + enforcement-note membership **conditional on `active_taxonomies`** — when active, describe them as mapped (with honest "descriptive, not a compliance score" caveat for MASWE-Beta); when inactive, keep the existing "informs the pack" wording.
- `report-template/components.jsx`: **no change** (`TaxonomyTag` reads `url` generically).
- After edits: `python tools/build_report_template.py`, commit regenerated `tools/apd_gauntlet/data/report-template/app.js` + `.source-hash` (CI freshness gate).

### 5.8 Specialist discipline + pack content

- `.claude/skills/apd-control-mappings/SKILL.md`: add `masvs`, `maswe` to the allowed `control_mappings` keys (line 12); add a discipline section after ATLAS — **emit MAS mappings only when the run declares masvs/maswe (mobile pack active)**; MASVS = the control the finding violates (or the capability satisfies); MASWE = the specific weakness; ground every ID in the pack's pattern prose; MASWE-Beta caveat; accepted/rejected examples; flat-list (IDs only, justification in `detail`).
- `domains/mobile-applications/`: the pack already cites MASVS/MASWE in prose — make the per-pattern linkage explicit in `common-patterns/*.md` + `severity-rubric.md` so specialists can confidently emit structured `control_mappings.masvs/maswe`. Keep `regulatory_anchors` unchanged (still consumed by `draft.py`).

### 5.9 Gates / audit / linters / freshness

- `taxonomy_titles_resolve` (audit 363–375): auto-covers MAS ids — catalog must resolve real titles (no bare ids) or the build blocks.
- Add `id_coverage_masvs` / `id_coverage_maswe` (mirror `id_coverage_attack` 166–172): every cited MAS id is a `taxonomy_dict` key.
- Extend `coverage_rollups_nonempty` (348–361): when `masvs`/`maswe` ∈ active_taxonomies **and** findings cite MAS ids, the coverage rows must be present in `data.js` (structural/blocking — the "full parity" gate). Zero MAS findings → exempt.
- Optional warn-level linter in `tools/apd_gauntlet/linters.py`: a finding's `maswe` parents (`masvs_v2` from catalog) should be consistent with its `masvs` ids.
- `refresh_mas` writes `_meta` so `reference_db_versions` surfaces freshness (also sidesteps the known D3FEND `_meta` gap).

### 5.10 Docs / ADR / version

- **ADR `docs/adrs/0014-owasp-mas-mobile-taxonomy.md`**: MASVS+MASWE finding/capability taxonomy + the new pack-declared→auto-seeded activation mechanism; additive-only schema policy; MASWE-Beta pinning.
- `docs/taxonomy-mappings.md`: add MASVS/MASWE rows (which side, when emitted, URL patterns, rollup artifacts, `refresh-mas`).
- `docs/html-report.md`: new families, Coverage sub-tabs, gate checks, `active_taxonomies`.
- `docs/adapting-to-other-domains.md`: document the new pack `taxonomies` field + pack→run auto-seed.
- `docs/running-the-gauntlet.md`: `refresh-mas` + mobile-run behavior.
- `CHANGELOG.md`; bump **1.6.0 → 1.7.0** in `pyproject.toml`, `plugin.json`, `tools/apd_gauntlet/__init__.py` (plugin.json/pyproject skew test asserts equality; `framework_version` in generated `apd-domain` frontmatter updates on rebuild).

### 5.11 Golden example

- `examples/apd-20260602-acme-mobile-banking/`: rely on auto-seed for `taxonomies` (regenerate `.apd-run.yaml` or assert auto-seed); add MAS `control_mappings` to a representative set of expected findings + at least one capability (MASVS); regenerate `masvs-coverage.yaml`/`maswe-coverage.yaml`, the report `data.js`, and rebuild the HTML report. Keeps the shipped-run audit + freshness CI green and demonstrates the feature.

### 5.12 Tests

- Schema: new `control_mappings` keys accept valid / reject invalid MAS ids; `domain.schema.json` `taxonomies` field; run-config enum.
- `refresh_mas`: parse `OWASP_MASVS.yaml` (24 controls); parse MASWE front-matter incl. deprecation/`covered_by`; MASWE URL uses filing category.
- `taxonomy.py`: `masvs_url`/`maswe_url` builders (incl. unknown-category → `None`); titles loaders.
- `rollup.py`: `_masvs_rollup` posture (covered/gapped/both/silent, finding+capability union); `_maswe_rollup` shape + ordering; gating on declared.
- `transform.py`: `taxonomy_dict` MAS branches (family/title/url); `findings_array` mappings; `active_taxonomies` in meta.
- `audit.py`: `id_coverage_masvs/maswe`, extended `coverage_rollups_nonempty`, `taxonomy_titles_resolve` with MAS.
- `init_run`: pack `taxonomies` auto-seed (mobile selected → run taxonomies include masvs+maswe; non-mobile unaffected).
- Bundle freshness after JSX edits.

## 6. Sequencing (for the implementation plan)

1. **Catalog + refresh** — `refresh_mas.py`, `refresh-mas` verb, bundled `data/masvs.json`/`maswe.json`, `taxonomy.py` loaders + URL builders. (No downstream dep; unblocks titles/URLs for everything.)
2. **Schemas** — `_defs`, finding/capability `control_mappings`, run-config enum, `domain.schema.json` `taxonomies`, two coverage schemas.
3. **Activation** — `init_run` auto-seed, `build_domain_skill` frontmatter, `mobile-applications/domain.yaml` `taxonomies`.
4. **Rollups** — `_masvs_rollup`/`_maswe_rollup` + `RollupResult` + `_write` + `validate` registration.
5. **Report data** — `loader` (load coverage YAMLs + `active_taxonomies`), `transform` (families, chips, collect, `taxonomy_dict`, scenes, meta).
6. **Report template** — `Findings.jsx`, `Coverage.jsx`, `Annexes.jsx`; rebuild `app.js` + `.source-hash`.
7. **Discipline + pack content** — `apd-control-mappings` SKILL, mobile pattern prose.
8. **Gates** — audit checks, optional linter.
9. **Docs + ADR-0014 + version bump.**
10. **Golden example regen + tests** (TDD throughout — tests precede each impl unit).

## 7. Risks & mitigations

- **MASWE Beta churn** → pin a commit SHA; catalog drives titles/URLs; report meta shows the pin; unknown category → non-clickable span (no broken links).
- **Closed `control_mappings` / `domain.schema.json`** are `additionalProperties:false` → purely additive new keys; no removals (schema-evolution policy preserved).
- **Freshness gate** → every JSX touch requires `build_report_template.py` + committing `app.js`/`.source-hash`; run the full markdownlint glob before push (per project CI lesson).
- **Specialist over-emission** → discipline gates MAS emission on declared taxonomies (mobile active) + pack-prose grounding; non-mobile runs never emit MAS.
- **Report consuming finding-level coverage YAMLs is new** → MASVS/MASWE are the first; keep load optional/tolerant so absence on non-mobile runs is graceful.

## 8. Out of scope

- MASTG (testing guide) as a third family.
- Per-mapping rationale fields / hedge-word linting on MAS mappings (flat-list model).
- Retrofitting OWASP Top-10 families with hover/url (separate consistency cleanup).
- A tier-4 path-overlay for MAS (D3FEND-style) — MAS is finding/capability-level only.
