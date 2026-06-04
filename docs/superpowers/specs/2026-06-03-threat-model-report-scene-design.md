# Threat-model report scene — design

## Context

The APD gauntlet now authors an always-on baseline threat model
(`apd-threat-model-author` → `00-context/threat-model-normalized.yaml`), optionally
parses a user-supplied TM into the sibling
`00-context/threat-model-supplied-normalized.yaml`, and evaluates coverage
(`apd-threat-model-evaluator` → `40-synthesis/threat-model-coverage.yaml`). None of
this is visible in the HTML report: `transform.threat_model_block` emits only a
metadata stub (`present`/`authored`/`supplied_present`/`comparator`/`entry_count`/
`generated_by`) and **no report screen renders it**.

This adds a dedicated **Threat model** scene to the report that surfaces the threat
model and its coverage, with relevant visualizations — and gracefully omits itself when
no threat model exists at all (no user-supplied TM and the author produced none, e.g.
degraded or legacy runs).

## Goals

- A dedicated top-level report tab placed **after Coverage, before Attack paths**
  (`… 04 Coverage · 05 Threat model · 06 Attack paths · 07 Annexes`).
- Five content blocks: (A) STRIDE×asset matrix, (B) entries table, (C) coverage by
  surface, (D) trust-boundary surface map (Mermaid), (E) supplied-vs-authored comparator.
- **Graceful omit**: when `data.threat_model.present` is false, the tab is absent
  entirely (no empty tab, no placeholder). Within the scene, block C appears only when
  the evaluator ran; block E only when a supplied TM *and* the authored baseline exist.
- Follow the repo convention: all block data is shaped + tested in Python
  (`transform.py`); JSX only renders.

## Non-goals

- No change to how the threat model is authored, parsed, or evaluated (those agents and
  their YAML outputs are inputs here, unchanged).
- Block A is **TM-native** (derived from the TM's own `mitigation` field); it does **not**
  cross-reference gauntlet capabilities — the evaluator's capability view is block C, so
  the two don't double-count.
- No new severity/risk scoring of threats beyond what the TM/evaluator already carry.

## Inputs (already produced by the pipeline)

- `00-context/threat-model-normalized.yaml` — `generated_by` (`threat_model_author` |
  `threat_model_recon`), `methodology`, `source_artifact`, `extraction_summary`,
  `entries[]`. Each entry: `entry_id`, `asset`, `threat`, `mitigation`, `methodology`,
  `source_locator`, `extraction_confidence`, `framework_refs.{stride_letter,
  linddun_letter, attack_tree_position, mitre_attack[]}`, `inferred_apd_goals[]`.
- `00-context/threat-model-supplied-normalized.yaml` — same shape; present only when the
  user supplied a TM (recon sibling).
- `40-synthesis/threat-model-coverage.yaml` — `methodology`, `surface_coverage`,
  `summary` (evaluator output).
- `00-context/asset-inventory.yaml` — `assets[]`, `trust_boundaries[]` /
  `default_trust_boundaries` (used to cluster surface-map nodes).

## `data.threat_model` contract

`transform.threat_model_block(artifacts)` is extended (same function, same key
`data.threat_model`) to return:

```
present: bool                 # a normalized TM exists (gates the tab)
authored: bool                # generated_by == "threat_model_author"
supplied_present: bool
comparator: bool              # authored AND supplied_present
generated_by: str | null
methodology: str | null       # e.g. "stride" | "linddun"
source_artifact: str | null
entry_count: int
grounded_count: int           # entries with non-empty mitigation
gap_count: int                # entries with empty mitigation
entries: [ {asset, threat, stride_letter, linddun_letter, mitigation,
            confidence, source_locator, apd_goals[]} ]          # block B
stride_matrix: {                                                # block A
  letters_present: ["S","T","R","I","D","E"]  # methodology letters actually modeled (cols)
  rows: [ {asset, cells: {S: status, T: status, ...}} ]
}
surface_coverage: {                                             # block C; null if absent
  rows: [ {surface, covered, partial, gap, notes} ], summary: {...}
} | null
surface_mermaid: str | null   # block D Mermaid source; null if no assets
comparator_delta: {                                            # block E; null unless comparator
  authored_only: [ {threat, asset} ],
  supplied_only: [ {threat, asset} ],
  corroborated:  [ {threat, asset} ]
} | null
```

When `present` is false, all scene fields are null/empty and `present:false` is the only
thing consumers need.

### Block A — STRIDE × asset matrix cell semantics

For each row `asset` and column letter `L ∈ {S,T,R,I,D,E}`, let
`E(asset,L)` = TM entries whose `asset` matches and `framework_refs.stride_letter == L`:

- `silent` — `E(asset,L)` empty (that STRIDE category was not modeled for the asset).
- `gap` — `E(asset,L)` non-empty and **no** entry has a non-empty `mitigation`.
- `covered` — `E(asset,L)` non-empty and **every** entry has a non-empty `mitigation`.
- `partial` — `E(asset,L)` non-empty and **some but not all** entries are mitigated.

Rows are the distinct assets across all entries, sorted by descending threat count then
name. `letters_present` lists only the letters that appear in ≥1 entry so the matrix never
shows an all-silent column. (For a LINDDUN methodology TM, the matrix keys on
`linddun_letter` and the columns are the LINDDUN letters; the cell logic is identical.)

### Block D — trust-boundary surface map (Mermaid)

`_build_threat_surface_mermaid(entries, asset_inventory)` emits a Mermaid `graph TD`:

- One node per distinct asset; label = `"<asset> [<letters>]"` where `<letters>` are the
  asset's modeled STRIDE letters. IDs via the existing `_mermaid_safe_id`.
- Nodes grouped into Mermaid `subgraph` clusters by trust boundary, resolved from
  `asset-inventory` (asset → boundary). Assets with no resolvable boundary go in an
  "unbounded" cluster. When the inventory provides no boundary mapping at all, emit a
  flat node list (no subgraphs).
- Node class `hot` (red) when the asset has ≥1 `gap` cell, else neutral; class defs via
  Mermaid `classDef`, rendered strict-mode.
- Edges drawn from `asset-inventory` data-flow / boundary-adjacency entries when present;
  otherwise nodes/clusters only (graceful degrade — no fabricated edges).
- Reuses the JS render/zoom path that `AttackPaths.jsx` uses for its Mermaid graph.

## Loader change (`tools/apd_gauntlet/report/loader.py`)

`load_run` already reads `threat_model_normalized` + `threat_model_supplied` (optional,
`00-context`). Add one optional artifact:
`40-synthesis/threat-model-coverage.yaml` → `RunArtifacts.threat_model_coverage:
dict | None` (None when absent → block C hidden). No required-artifact change, so runs
without an evaluator pass still load.

## Report wiring / JSX

- `build_apd_data` already calls `threat_model_block`; `data.threat_model` now carries the
  full payload. Add `meta.has_threat_model = data.threat_model["present"]` for convenience.
- New `report-template/screens/ThreatModel.jsx` renders blocks A–E; C and E are guarded on
  their data (`surface_coverage`, `comparator_delta`) being non-null.
- `report-template/app.jsx`:
  - Build `TABS` so the `{ id:"threat_model", num:"05", label:"Threat model" }` entry is
    included **only when `data.threat_model.present`**; numbering is derived from array
    position so Attack paths/Annexes renumber automatically.
  - Route `activeTab === "threat_model"` to `<ThreatModel data={data} />`.
- Block D reuses the Mermaid render/zoom helpers from `AttackPaths.jsx` (extract a shared
  helper if cleaner). Blocks A & C reuse the Coverage tab's matrix/bar CSS; block E reuses
  the contradiction-panel styling. New CSS kept minimal in `screens.css`.

## Completeness gate (`tools/apd_gauntlet/synthesis/audit.py`)

Add one **structural** check `threat_model_scene_coherent`:

- when `data.threat_model.present` is true → pass iff `entries` and `stride_matrix.rows`
  are both non-empty;
- when `present` is false → **pass (exempt)**, matching the gate's existing
  legitimately-empty-state philosophy.
- `report-audit.yaml` gains the check with `klass: structural`.

## Build, fixtures, tests, docs

- **Bundle**: new JSX ⇒ run `python tools/build_report_template.py`; commit the rebuilt
  `tools/apd_gauntlet/data/report-template/app.js` + `.source-hash` (freshness CI gate).
- **Golden**: the canonical example
  (`examples/apd-20260601-claim-event-bus/expected/`) has a normalized TM (recon) +
  `threat-model-coverage.yaml` and **no** supplied sibling — so it exercises A/B/C/D (not
  E). Regenerate `tests/fixtures/report-html/claim-event-bus-golden-data.js` and
  `report-template/data.js`; the `threat_model` block grows.
- **Tests** (TDD):
  - `transform` unit tests — present/absent gating; authored vs recon vs comparator;
    matrix cell semantics incl. `partial`; `goals_present` excludes all-silent columns;
    `_build_threat_surface_mermaid` shape (subgraph clusters; `hot` class; graceful
    no-edge / no-boundary degrade); coverage parsing; comparator_delta only when both TMs.
  - JSX text-contract test (mirrors `tests/test_workflow_apd_gauntlet.py` style) —
    `ThreatModel` screen exists and is routed; `TABS` gating omits the tab when not
    present; block C/E guards present.
  - `audit` tests — present→coherent pass with data, present-but-empty→fail,
    absent→exempt pass.
  - An omit test — `threat_model_block` with `normalized=None` ⇒ `present:false`; a JSX
    contract assertion that the tab entry is conditional.
- **Docs**: `docs/html-report.md` (document the new scene + omit behavior); CHANGELOG
  `### Added` under `[Unreleased]`.

## Files to change (representative)

- `tools/apd_gauntlet/report/transform.py` — extend `threat_model_block`; add
  `_build_threat_surface_mermaid`, matrix + coverage + comparator helpers.
- `tools/apd_gauntlet/report/loader.py` — load `threat-model-coverage.yaml`; add
  `RunArtifacts.threat_model_coverage`.
- `tools/apd_gauntlet/synthesis/audit.py` — `threat_model_scene_coherent` check.
- `report-template/screens/ThreatModel.jsx` (new); `report-template/app.jsx` (TABS gate +
  route); `report-template/screens.css` (minimal additions).
- Rebuilt bundle: `tools/apd_gauntlet/data/report-template/{app.js,.source-hash}`.
- Regenerated demo/golden: `report-template/data.js`,
  `tests/fixtures/report-html/claim-event-bus-golden-data.js`.
- Tests under `tests/unit/report/` + `tests/test_workflow_apd_gauntlet.py`-style contract;
  `docs/html-report.md`; `CHANGELOG.md`.

## Verification

1. `ruff check tools/ tests/` + `mypy tools/` clean.
2. `pytest -q` green; new transform/audit/JSX-contract tests pass.
3. `python tools/check_report_template_freshness.py` OK (bundle rebuilt).
4. Build the example report and open the **Threat model** tab — A/B/C/D render, E absent
   (no supplied TM); Mermaid surface map shows trust-boundary clusters.
5. Negative check: a run whose `threat-model-normalized.yaml` is absent builds a report
   with **no** Threat-model tab and a passing audit (`threat_model_scene_coherent` exempt).
6. Golden byte-comparison passes against the regenerated golden.

## Risks / watch-items

- **Golden churn** — regenerate deterministically; eyeball the `threat_model` diff.
- **Mermaid degrade** — assert the no-edge / no-trust-boundary path renders valid Mermaid
  (clusters or flat nodes), since not every run's `asset-inventory` carries flow edges.
- **LINDDUN methodology** — the matrix/diagram key on the methodology's letter set; verify
  a LINDDUN TM doesn't render an all-empty STRIDE matrix.
- **Bundle determinism** — the rebuild must touch only `app.js` + `.source-hash` (no
  unrelated churn), per the report-template build pattern.
