# Design: CAPEC bridge — a derived CWE ↔ ATT&CK view

- **Date:** 2026-06-14
- **Status:** Approved (design); implementation in progress
- **Framework version at design:** 1.7.0 (main). No version bump required (additive, derived).
- **New ADR:** [0022](../../adrs/0022-derived-cross-framework-views.md) (derived cross-framework views) — this is its first instance.
- **Related ADRs:** 0008 (multi-framework taxonomy mappings), 0012 (ATLAS — rollup plumbing precedent), 0020 (tooling-authored derived fields).

## 1. Problem & goal

A finding can already carry both a `cwe` weakness and a `mitre_attack` technique in its `control_mappings`, but the two are **unconnected** — nothing tells a reviewer whether "CWE-89 + T1190 on the same finding" is a coherent pairing or two tags that happen to co-occur. MITRE **CAPEC** is the authoritative connective tissue: each attack pattern carries `Related_Weaknesses` (CWE) and, for ~20% of the catalog, an ATT&CK `Taxonomy_Mapping`. CAPEC is the bridge between the weakness view (CWE) and the adversary view (ATT&CK).

**Goal:** derive, at synthesis time, a CAPEC bridge that (a) **corroborates** finding CWE↔technique pairings grounded in a real attack pattern, and (b) **suggests** (advisory) the missing side when a finding has only a CWE or only a technique. Per [ADR-0022](../../adrs/0022-derived-cross-framework-views.md) this is a **derived view (bridge)** — synthesizer-authored, no `control_mappings.capec` key, no specialist discipline, no run-config enum value.

### Success criteria

1. `refresh-capec` produces a bundled `data/capec.json` projecting each CAPEC to `{name, related_cwe[], related_attack[]}` with `_meta` freshness.
2. The synthesizer emits `40-synthesis/capec-bridge.yaml` (schema-validated) **when both `cwe` and `mitre_attack` are declared** and ≥1 finding carries a CWE and/or technique; otherwise no artifact.
3. The bridge reports **corroborated** links (CAPEC relates a finding's CWE *and* its technique) and **suggestions** (CAPEC relates a finding's tagged side to an untagged technique/CWE).
4. CAPEC IDs resolve to titles + `capec.mitre.org` URLs in the report; the bridge renders as a derived Coverage view labeled accordingly.
5. **Silence on absence:** a finding whose CWE/technique have no CAPEC link produces no entry and no negative signal. No audit check blocks on the bridge.
6. Full unit-test coverage; golden example regenerated; all gates green.

## 2. Approved decisions

| # | Decision | Choice |
|---|----------|--------|
| 1 | Authorship | **Derived (synthesizer).** No `control_mappings.capec` key; findings/capabilities unchanged. |
| 2 | Gating | Auto-emit when `cwe` **and** `mitre_attack` ∈ declared taxonomies (both default-on). Not added to the `taxonomies` enum. |
| 3 | Signals | **Corroboration + suggestion only.** Explicit "incoherence/mismatch" flagging is **out of scope for v1** (false-positive-prone; deferred). |
| 4 | Catalog source | `refresh-capec` CLI + bundled `data/capec.json` (mirrors `refresh-cwe`/`refresh-atlas`), `_meta` freshness. |
| 5 | Artifact shape | Single-file rollup (`cwe-coverage.schema.json` convention): `bridges[]` + `suggestions[]`. |
| 6 | Report | A compact derived view rendered alongside the CWE/ATT&CK coverage; CAPEC chips clickable to `capec.mitre.org`. |

## 3. External reference facts (pinned)

- **Source:** the CAPEC comprehensive catalog XML, `https://capec.mitre.org/data/xml/capec_latest.xml` (single file; also available per-view). License: free, MITRE.
- **ID scheme:** `CAPEC-<n>` (no zero-pad). Catalog has ~560 attack patterns (Meta / Standard / Detailed abstractions).
- **CWE edge:** `<Related_Weaknesses><Related_Weakness CWE_ID="89"/></Related_Weaknesses>` → store as `CWE-89`.
- **ATT&CK edge:** `<Taxonomy_Mappings><Taxonomy_Mapping Taxonomy_Name="ATTACK"><Entry_ID>1190</Entry_ID><Entry_Name>Exploit Public-Facing Application</Entry_Name></Taxonomy_Mapping></Taxonomy_Mappings>` → store as `T1190`. Only ~112/560 CAPECs carry an ATTACK mapping; a sub-technique maps as `Entry_ID = 1059.001` → `T1059.001`.
- **Deep-link (stable, regex-derivable):** `https://capec.mitre.org/data/definitions/<n>.html`.
- **Coverage caveat (load-bearing for the honesty rule):** CWE↔CAPEC and CAPEC↔ATT&CK are both partial. Absence of a bridge for a finding is **expected and silent**, never a defect.

## 4. Internal wiring (mirrors the ATLAS/CWE finding-level rollup template; see the MASVS spec §4 for the same map)

| Layer | File | Action |
|-------|------|--------|
| Catalog refresh | **new** `tools/apd_gauntlet/refresh_capec.py` + `refresh-capec` verb in `cli.py` (near the other `refresh-*`) | fetch XML → project → `data/capec.json` |
| Title/URL catalog | `tools/apd_gauntlet/report/taxonomy.py` (loaders ~111–307; `reference_db_versions` 278–307; invalidation map ~338) | add `capec_titles()`, `capec_url()`, register freshness + invalidation |
| Rollup | `tools/apd_gauntlet/synthesis/rollup.py` (`RollupResult` ~47–56; `_declared_taxonomies` ~230; `build_rollups` ~267–310; `_write` ~480–502; model on `_cwe_rollup` ~313–340) | add `_capec_bridge_rollup`, `RollupResult.capec`, gated dispatch + write |
| Coverage helpers | `tools/apd_gauntlet/synthesis/coverage_logic.py` (`extract_ids_from_mapping`) | reuse to pull `cwe` + `mitre_attack` technique IDs off a finding |
| Rollup schema | **new** `schemas/capec-bridge.schema.json` (single-file convention) | validate the artifact |
| Validate registration | `tools/apd_gauntlet/validate.py` (`SYNTHESIS_ROLLUPS` ~234–274) | `capec-bridge.yaml` → schema |
| Report load | `tools/apd_gauntlet/report/loader.py` (`load_run` ~486–629) | load `capec-bridge.yaml` when present (optional) |
| Report transform | `tools/apd_gauntlet/report/transform.py` (`_FAMILY_DISPLAY` ~1916; `_collect_referenced_ids` ~1992–2117; `taxonomy_dict` ~2120–2185; `sections` ~1798–1870) | `MITRE CAPEC` family; harvest CAPEC ids **from the bridge artifact** (not `control_mappings`); a `capec_bridge` scene |
| Report template | `report-template/screens/Coverage.jsx` (+ rebuild `app.js`/`.source-hash`) | a compact "CWE ↔ ATT&CK (CAPEC)" derived panel |
| Audit | `tools/apd_gauntlet/synthesis/audit.py` (`taxonomy_titles_resolve` ~363–375) | titles resolve for CAPEC ids; **advisory** — no blocking check |
| Reference catalog | **new** `tools/apd_gauntlet/data/capec.json` | bundled, refreshed |

**Structural note (differs from emission taxonomies):** CAPEC IDs appear **only in the bridge artifact**, never in `control_mappings`. So the report harvests CAPEC ids for the taxonomy dict from the loaded `capec-bridge.yaml`, not from findings — the inverse of how CWE/ATT&CK chips are harvested.

## 5. Component design

### 5.1 Reference catalog (`refresh_capec.py` + `data/capec.json`)

`data/capec.json`:

```json
{ "_meta": { "fetched_at": "...", "source": "https://capec.mitre.org/data/xml/capec_latest.xml",
             "source_sha256": "...", "version": "3.9", "count": 559 },
  "attack_patterns": {
    "CAPEC-66": { "name": "SQL Injection", "related_cwe": ["CWE-89", "CWE-1286"], "related_attack": ["T1190"] },
    "CAPEC-63": { "name": "Cross-Site Scripting (XSS)", "related_cwe": ["CWE-79"], "related_attack": [] }
  } }
```

`refresh_capec.py` mirrors `refresh_cwe.py`: `fetch_capec_xml()` (hardened: `DEFAULT_TIMEOUT_SECONDS`, `MAX_RESPONSE_BYTES`), `project_capec_xml_to_json(xml_bytes)` (parse `Attack_Pattern` entries; pull `Related_Weaknesses` → `CWE-n`, `Taxonomy_Mappings[Taxonomy_Name=ATTACK]` → `T<entry>`; drop deprecated/`Status=Deprecated`), `refresh_capec(output_path=None)` → writes `data/capec.json`. Wire `refresh_capec_cmd()` into `cli.py`.

### 5.2 Bridge rollup (`synthesis/rollup.py`)

`_capec_bridge_rollup(findings, catalog)` — catalog loaded once (`{capec_id: {name, related_cwe set, related_attack set}}`):

For each finding, extract `fcwe = set(control_mappings.cwe)` and `fatt = {technique for each mitre_attack entry}` (sub-technique parent-folded: `T1059.001` also counts as `T1059` for matching, mirroring the D3FEND `counters_attack` parent rule).

- **bridge (corroboration):** for each CAPEC where `related_cwe ∩ fcwe ≠ ∅` **and** `related_attack ∩ fatt ≠ ∅` → emit a `bridges[]` entry `{finding_id, capec_id, capec_name, cwe: sorted(related_cwe ∩ fcwe), attack: sorted(related_attack ∩ fatt)}`.
- **suggestion (advisory fill):** only for findings missing one side —
  - finding has CWE, no technique: CAPECs with `related_cwe ∩ fcwe ≠ ∅` **and** non-empty `related_attack` → `suggestions[]` `{finding_id, direction: "cwe_to_attack", via_capec[], suggested: sorted(union related_attack)}`.
  - finding has technique, no CWE: symmetric, `direction: "attack_to_cwe"`, `suggested` = CWEs.
- A finding with **both** sides but **no** corroborating CAPEC → **no entry** (silence-on-absence; no suggestion, no mismatch). This is the common case and is correct.

Ordering: bridges sorted by `(finding_id, capec_id-numeric)`; suggestions by `finding_id`. Deterministic.

`RollupResult` gains `capec: dict | None`. `build_rollups` gates: `if "cwe" in declared and "mitre_attack" in declared: result.capec = _capec_bridge_rollup(findings, _capec_catalog())`. `_write` writes `capec-bridge.yaml` only when `result.capec` has ≥1 bridge or suggestion (empty → no file, matching the ATLAS "skip on empty" rule).

### 5.3 Schema (`schemas/capec-bridge.schema.json`)

Single-file convention (no `-doc` envelope):

```yaml
{ schema_version: 1, generated_by: 'synthesizer',
  bridges: [ { finding_id, capec_id: ^CAPEC-[0-9]+$, capec_name,
               cwe: [^CWE-[0-9]+$], attack: [^T[0-9]{4}(\.[0-9]{3})?$] } ],
  suggestions: [ { finding_id, direction: cwe_to_attack|attack_to_cwe,
                   via_capec: [^CAPEC-[0-9]+$], suggested: [string] } ] }
```

`bridges` + `suggestions` both required (may be empty arrays). Register in `validate.py` `SYNTHESIS_ROLLUPS`.

### 5.4 Report (`taxonomy.py`, `transform.py`, `loader.py`, `Coverage.jsx`)

- `taxonomy.py`: `capec_titles()` (lru-cached from `data/capec.json`), `capec_url(id)` → `https://capec.mitre.org/data/definitions/{n}.html` (pure regex). Register the catalog in `reference_db_versions()` + the cache-invalidation map.
- `loader.py`: load `40-synthesis/capec-bridge.yaml` into `RunArtifacts.capec_bridge` when present (optional, tolerant). Add to the freshness source-hash set.
- `transform.py`: `_CAPEC_FAMILY_DISPLAY = 'MITRE CAPEC'`; in `_collect_referenced_ids`, harvest CAPEC ids **from `capec_bridge`** (bridges + suggestions); `taxonomy_dict` CAPEC branch sets `family`, `title` (catalog), `url`; a `capec_bridge` scene builder (tolerant of a missing artifact) feeding a derived panel.
- `Coverage.jsx`: a compact derived panel ("CWE ↔ ATT&CK · CAPEC") listing corroborated bridges (finding → CAPEC chip → CWE/ATT&CK chips) and an advisory "suggested links" sub-list. Labeled **derived** per ADR-0022. Rebuild bundle + commit `app.js`/`.source-hash`.

### 5.5 Gates / audit

- `taxonomy_titles_resolve` auto-covers CAPEC ids once they enter the taxonomy dict (catalog must resolve real titles).
- **No new blocking check.** Optionally a warn-level `capec_bridge_present` editorial note ("N corroborated CWE↔ATT&CK links") — non-blocking, omitted when zero.

## 6. Sequencing (TDD throughout — test precedes each unit)

1. **Catalog + refresh** — `refresh_capec.py`, `refresh-capec` verb, bundled `data/capec.json` (committed seed projected from the live catalog), `taxonomy.py` loaders + `capec_url`.
2. **Schema** — `capec-bridge.schema.json`; `validate.py` registration.
3. **Rollup** — `_capec_bridge_rollup`, `RollupResult.capec`, gated dispatch + `_write`.
4. **Report data** — `loader` (load artifact), `transform` (family, harvest-from-artifact, `taxonomy_dict`, scene).
5. **Report template** — `Coverage.jsx` derived panel; rebuild `app.js` + `.source-hash`.
6. **Audit** — advisory note; `taxonomy_titles_resolve` coverage.
7. **Docs** — `docs/taxonomy-mappings.md` (a "Derived views" section), `docs/html-report.md`; CHANGELOG.
8. **Golden example** — regenerate a run that carries co-tagged CWE+ATT&CK findings; assert `capec-bridge.yaml`; rebuild report; gates green.

## 7. Risks & mitigations

- **Sparse CAPEC↔ATT&CK coverage** → most findings get no bridge. **Mitigation:** silence-on-absence (ADR-0022); advisory-only; never a mismatch. Tests assert that a both-sides finding with no CAPEC link yields *no* entry.
- **Sub-technique matching** → `T1059.001` must corroborate a CAPEC mapped to `T1059`. **Mitigation:** parent-fold technique IDs before set-intersect (same rule as D3FEND `counters_attack`).
- **Catalog churn / size** → CAPEC XML is ~MBs. **Mitigation:** `MAX_RESPONSE_BYTES` cap; pin `version` in `_meta`; quarterly refresh.
- **Report freshness gate** → any `Coverage.jsx` edit needs `build_report_template.py` + committed `app.js`/`.source-hash`. **Mitigation:** rebuild + commit in the report-template step; run the full markdownlint glob before push.

## 8. Out of scope

- **Incoherence / mismatch flagging** (a finding's CWE and technique are each CAPEC-mapped but to *different* families). Deferred — false-positive-prone; revisit once corroboration data is observed on real runs.
- A `control_mappings.capec` emission key (this is a derived view, by decision).
- Capability-side CAPEC (capabilities have no CWE/technique-exposure pairing to bridge).
- Specialist confirm-loop for suggestions (ADR-0022 "both" option) — later, no schema change needed.
