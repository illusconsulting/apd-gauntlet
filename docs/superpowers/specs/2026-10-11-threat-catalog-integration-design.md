# Threat catalog integration — design

**Date:** 2026-10-11
**Status:** Approved 2026-10-11
**Release line:** `next` (2.0)
**Related:** ADR-0008 (multi-framework taxonomy mappings), ADR-0017
(local-only accuracy benchmark), ADR-0020 (tooling-authored derived fields),
ADR-0022 (derived cross-framework views), the program master plan
(`../plans/2026-10-10-program-master-plan.md`), the IaC spec
(`2026-10-10-iac-terraform-opentofu-atmos-design.md`) and the threat catalog
(367 threats in 25 families, built separately in claude.ai).

## 1. Problem

The gauntlet names threats and framework mappings from scratch on every run.
That costs accuracy, consistency and insight in six places:

1. **The threat-model author has no threat vocabulary.** The CLI floor
   (`threat_model/author.py`) builds one stub per (surface, applicable STRIDE)
   cell, and the agent grounds each stub "drawn from the active domain pack's
   `common-patterns/<goal>.md` prose". Two runs on the same system name the
   same threat differently, and a threat the pack prose never mentions is
   never considered.
2. **LINDDUN and MAESTRO have no floor.** The agent adds them "LLM-only — there
   is no CLI-floor cell-set and no deterministic test for them".
3. **Lenses author every mapping by hand.** Each specialist reconstructs
   ATT&CK, CWE and OWASP mappings under the `apd-control-mappings` bar. ADR-0008
   fenced off over-mapping, which leaves omission as the common error, and two
   lenses describing the same threat often map it differently.
4. **The evaluator cannot see what nobody considered.** Rule 7 ("silence")
   fires only for surfaces that specialist findings flagged. A threat that
   applies to the system but that no lens and no TM entry raised leaves no
   trace in the report.
5. **Framework coverage stops at the bundled KBs.** OWASP Agentic, NHI, CI/CD
   and Kubernetes lists, MAESTRO, CSA, HICP, CIS v8 and EMB3D have no view,
   although several matter to the gauntlet's domains (HICP for PBM, Agentic and
   MAESTRO for `agentic-ai`).
6. **Edition skew already exists** (§4, F5 and F6). The bundled OWASP LLM list
   and the `apd-control-mappings` skill use the 2023 edition, while the
   `agentic-ai` pack uses 2025 meanings under the same bare ids.

The catalog already holds what these places lack: normalized threats with
abstraction, kind, STRIDE, LINDDUN, system types, impacts, mitigations and
about 9,800 reviewed framework mappings.

## 2. Goals and non-goals

**Goals**

- Give the TM author a ranked, deterministic candidate set per cell, including
  LINDDUN and MAESTRO cells.
- Let lenses cite catalog threats and inherit reviewed mappings as a separate,
  derived field, so authored and inherited mappings stay distinguishable.
- Report in-scope threats that nothing addressed, and framework coverage for
  frameworks the gauntlet does not ask specialists to emit.
- Align the gauntlet's KB editions with the catalog's and fix the existing
  OWASP LLM skew.
- Keep HITRUST-derived content out of every public artifact.
- Prove the change with the WS2 harness before it becomes the default.

**Non-goals**

- Replacing specialist judgment. The catalog proposes; agents ground, block or
  dismiss, and a finding still needs its own evidence.
- Matching user-supplied threat models to catalog ids. That is a later WS6
  decision task (`threat-match`, §16).
- New attack-path enumeration. Paths gain labels only.
- Editing the catalog from the gauntlet. Gaps are exported for review; the
  catalog repo stays the only place the catalog changes.
- Using catalog mappings for frameworks the gauntlet does not validate. Those
  appear in the coverage view only.

## 3. Decisions

| Question | Decision | Rejected |
|---|---|---|
| Licensing | **Open subset plus local full.** A public open release in which HITRUST-sourced threats are stubs; the full catalog is loaded only from a local path. | Shipping the full catalog (HITRUST redistribution); shipping nothing (no default value). |
| Source | **Own repo, pinned release.** `illusconsulting/threat-catalog` publishes versioned release assets; the gauntlet vendors one open file with provenance. | Git submodule; fetching at run time. |
| Approach | **A: enrichment layer.** The catalog feeds deterministic steps and agent context; the pipeline's shape and agents stay as they are. | B: catalog-driven TM (replaces the STRIDE skeleton); C: catalog-first lenses (per-threat checklists). Both multiply agent work and couple every lens to catalog quality. |
| Default | `threat_catalog: open` on 2.0 only if the §14 gates pass; otherwise `off`. | — |

## 4. Facts that shape the design

Read from the code on `main` at `856ea96` (framework 1.7.0) and from the
catalog's schema.

| # | Fact | Consequence |
|---|---|---|
| F1 | The skeleton is one entry per (surface, applicable STRIDE) cell, from inventory `assets[]` and `identities[]` (`author.py:88-130`). The element matrix is Shostack's (`APPLICABLE_STRIDE`). | Candidates attach to existing cells; the floor's contract (one entry per cell, never invent a surface) is kept. |
| F2 | Inventory `asset_type` is coarse: `service`, `data_store`, `secret_store`, `queue`, `network`, `external_dependency`, `compute`. Identities have `human_role`, `service_account`, `workload_identity`, `external_party`. Assets carry `data_classifications`. | Asset type alone cannot pick catalog system types (`service` could be `web_app`, `api` or `serverless`). Scope intersects asset-type candidates with run-level system types (§8.1). |
| F3 | `threat-model-normalized` entries, `finding`, `capability` and `run-config` all set `additionalProperties: false`. `framework_refs` holds `stride_letter`, `linddun_letter`, `attack_tree_position` and `mitre_attack`. | Every new field is an additive schema change with a `schema-evolution.md` entry. |
| F4 | ADR-0022: derived views are synthesis-authored, "never add a `control_mappings` key, never appear in specialist discipline, never gate specialist emission". ADR-0020: tooling authors every field that is a pure function of authored content. ADR-0008 rejected always-on taxonomies because agents over-map. | Lenses author `threat_refs`; canonicalize derives `catalog_mappings`; rollups count the two sources apart; only active taxonomies are derived. |
| F5 | `owasp_llm_top10.json` is the 2023 list (`LLM02 Insecure Output Handling` … `LLM10 Model Theft`), seed-only, and the `apd-control-mappings` skill teaches 2023 meanings (`LLM06 (Sensitive Information Disclosure)`, `LLM07 (Insecure Plugin Design)`). The `agentic-ai` pack's ten prose files use 2025 meanings (`LLM02 Sensitive Information Disclosure`, `LLM06 Excessive Agency`, `LLM10 Unbounded Consumption`). The finding pattern `^LLM(0[1-9]\|10)$` has no year. | An existing 1.7 defect: in an `agentic-ai` run, a bare `LLM06` can mean either edition, and rollups print the 2023 name. Bare ids in 1.7 runs are ambiguous. Fixed on 2.0 only, in CAT1 (§10); 1.7.x is unchanged. |
| F6 | `owasp_top10.json` is the 2021 seed (`A01:2021`); the `apd-control-mappings` skill teaches 2021 ids. The catalog maps OWASP Top 10 2025. ATT&CK was fetched 2026-05-29 from `mitre/cti` master. | KB refresh plus crosswalks for comparing new runs with 1.7 baselines (§10). |
| F7 | The catalog's LINDDUN codes are `L, I, Nr, D, DD, U, Nc`; the gauntlet's are `L, I, N_repudiation, D_etectability, D_isclosure, U, N_compliance`. | A fixed translation table, pinned by a test (§8.6). |
| F8 | Catalog mapping keys include `attack_enterprise`, `attack_mobile`, `atlas`, `capec`, `cwe`, `maswe`, `owasp_top10`, `owasp_api`, `owasp_llm`, `owasp_llm_2025`, `owasp_agentic`, `owasp_nhi`, `owasp_cicd`, `owasp_k8s`, `maestro`, `csa_top_threats`, `hicp` and others; control keys are `nist_800_53`, `nist_csf2`, `cis_v8`, `d3fend`, `hicp`, `emb3d_mitigations`, `owasp_docker`. Each mapping has `fit: primary\|partial`. | One table maps catalog keys to gauntlet taxonomies (§8.6); everything else goes to the coverage view. |
| F9 | Families include non-architecture sources (`EN` environmental, `FA` facility, `CF` conflict, `PH` physical, `LG` legal). Kinds include `consequence`; abstractions include `outcome`. | Default selection excludes those families, consequences and outcomes from candidates and shortlists; they still appear in the coverage view. |
| F10 | The open release's HITRUST stubs have no `summary`, `description` or `example`, which the full schema requires. | The open edition has its own schema variant. Selection uses only fields both editions carry, so it is edition-invariant (§13). |
| F11 | `run-config` already has `threat_model` (a supplied TM path) and `taxonomies` (opt-in emission). | The new key is `threat_catalog`; derived mappings follow `taxonomies`. |

## 5. Architecture

```text
threat-catalog repo ──release──▶ threat-catalog-open-<v>.json ──vendored──▶ data/threat-catalog/open.json
                                 threat-catalog-full-<v>.json ──local path─┐            │
                                                                           ▼            ▼
                                                              apd_gauntlet.catalog (load, validate, index)
                                                                           │
 intake ─ code-recon ─ [threat-model-author phase]                         │
                         catalog-scope ◀───────────────────────────────────┤  00-context/threat-scope.yaml
                         author-threat-model (candidates per cell) ◀───────┤  skeleton gains catalog_candidates
                         apd-threat-model-author (grounds: catalog_refs)   │
 [canonicalize phase]    canonicalize-threat-model                         │
                         catalog-shortlists ◀──────────────────────────────┤  00-context/threat-shortlists/<goal-stem>.md
 tiers 1–3: lenses cite threat_refs ─▶ canonicalize derives catalog_mappings
 tier 4: tm-candidates gains catalog_silence ─▶ evaluator (catalog_silence findings)
         attack paths: edges carry threat_refs, paths carry a tactic sequence
 rollup: per-taxonomy source split; catalog-coverage.yaml; catalog-gaps.yaml
 report: "Threat coverage" section
```

No phase is added. `catalog-scope` is the first step of the
`threat-model-author` phase; `catalog-shortlists` runs right after WS1's
`canonicalize-threat-model` in the `canonicalize` phase, before tier 1. The
other changes extend existing steps. With `threat_catalog: off`, none of them runs
and every new field is absent.

## 6. Catalog data and distribution

### 6.1 The catalog repo

`illusconsulting/threat-catalog` (private repo, created by the operator) owns
the source YAML, the build and validation scripts, and two release assets per
version `X.Y.Z`:

- `threat-catalog-open-X.Y.Z.json`, licensed for redistribution, with
  `threat-catalog-open.schema.json` and `SHA256SUMS`, on tag `vX.Y.Z`;
- `threat-catalog-full-X.Y.Z.json`, attached to a private release only.

No full-edition schema is published to or vendored by the gauntlet (§12.1).

**Open-edition stub rule.** For every threat with `source: HITRUST`, the open
file keeps `id`, `name`, `aliases`, `family`, `family_name`, `abstraction`,
`parent`, `children`, `kind`, `intent`, `actors`, `system_types`, `stride`,
`linddun`, `impacts`, `related`, `mappings`, `controls` and `attack_tactics`,
plus `"stub": true`. It removes `summary`, `description`, `example`,
`scope_note`, `preconditions`, `indicators`, `mitigations`, `mapping_notes`,
`references` and the whole `hitrust` block, and drops the top-level
`hitrust_crosswalk`. Threats with `source: added` are complete in both
editions.

### 6.2 What the gauntlet vendors

`tools/apd_gauntlet/data/threat-catalog/`:

| File | Content |
|---|---|
| `open.json` | The pinned open release asset, byte-identical to the download |
| `open.provenance.json` | `source` (release asset URL), `source_sha256`, `fetched_at`, `version` |
| `open.schema.json` | The open schema from the same release |
| `compat.yaml` | `catalog_compat: ">=1.0.0,<2.0.0"` — the catalog versions this gauntlet release accepts |
| `selection.yaml` | Versioned selection parameters (§8.1–8.3) |
| `system-types.yaml` | Asset type and identity type to candidate catalog system types; domain pack and IaC resource-type hints (§8.1) |
| `apd-goals.yaml` | Catalog family to APD goals, completing the STRIDE and LINDDUN mapping (§8.4) |
| `taxonomy-map.yaml` | Catalog mapping keys to gauntlet taxonomies and their KB files (§8.6) |
| `owasp-crosswalks.yaml` | OWASP Top 10 2021↔2025, many-to-many, from OWASP's published mapping (§10) |

`tools/check_kb_cache_freshness.py` adds `threat-catalog/open.json` to
`COVERED`, reading its provenance from the sidecar so that the vendored file
stays byte-identical and its hash checkable.

### 6.3 Refresh

`apd-gauntlet refresh-threat-catalog [--version X.Y.Z] [--dry-run]` downloads
the open asset and its schema from the catalog repo's release, verifies the
release's published SHA-256, validates the file (§12.1), checks the version
against `compat.yaml`, and rewrites `open.json`, `open.schema.json` and
`open.provenance.json`. With `--token-env NAME` (default `GITHUB_TOKEN`) set,
the token is sent only to `github.com`, `api.github.com` and
`objects.githubusercontent.com`; otherwise the download is anonymous. `--dry-run` prints the diff summary (threats added, removed and
changed by id; mapping counts per key) and writes nothing. It follows the
existing `refresh-*` pattern: a fetcher module, a golden fixture under
`tests/fixtures/kb_golden/threat_catalog/`, and no network in tests.

### 6.4 The full catalog

The full file is never committed, vendored or copied into a run. It is loaded
from `threat_catalog.path` (§7). The loader refuses a path inside the
installed package or the run directory, and warns when the path is inside a
git working tree and not ignored. LA3's `doctor` gains a `threat-catalog`
check through `register_doctor_check` (master plan §A3): the vendored file
validates, and a configured full path exists and validates.

## 7. Run-config

`threat_catalog` accepts a string or an object:

```yaml
threat_catalog: open            # off | open | full

threat_catalog:
  edition: full                 # off | open | full
  path: ~/threat-catalog/threat-catalog-full-1.0.0.json      # required for full
  system_types: [api, cloud, b2b_integration]               # optional, added to the run's types
  exclude_system_types: [ot_ics]                            # optional
```

- Absent means the release default: `off` until CAT4 passes, then `open`.
- `edition: full` without a readable, valid file falls back to `open` and
  writes a warning to `00-context/threat-scope.yaml` and the run log; it never
  fails the run.
- The domain pack schema gains an optional `threat_profile`
  (`system_types`, `emphasize_families`, `include_families`,
  `exclude_families`). The six shipped packs get one each in CAT2; for
  example `pbm`: `[web_app, api, mobile, cloud, data_store, identity,
  b2b_integration, third_party]`; `agentic-ai`: `[ai_ml, agentic_ai, api,
  cloud]` emphasizing `AI` and `AG`.

## 8. Units

New package `tools/apd_gauntlet/catalog/`:

| Module | Responsibility |
|---|---|
| `config.py` | `catalog_config_from_run_config(run_cfg: Mapping[str, Any]) -> CatalogConfig \| None`; `load_selection_params()` |
| `load.py` | `load_catalog(cfg: CatalogConfig) -> Catalog`; validation (§12.1); edition fallback |
| `model.py` | `Catalog`, `Threat` (frozen dataclasses); indexes by id, system type, STRIDE letter, LINDDUN code and mapping id |
| `scope.py` | Run and surface system types; eligibility; `threat-scope.yaml` |
| `candidates.py` | Ranked candidates per skeleton cell |
| `goals.py` | Catalog threat to APD goals |
| `shortlists.py` | Per-goal shortlists |
| `derive.py` | `catalog_mappings` on findings, `framework_refs.mitre_attack` fill on TM entries, edge `threat_refs` |
| `coverage.py` | `catalog-coverage.yaml` |
| `gaps.py` | `catalog-gaps.yaml` and the cross-run export |
| `translate.py` | LINDDUN codes; catalog keys to gauntlet taxonomies; NIST id normalization |

### 8.1 Scope (`apd-gauntlet catalog scope <run-dir>`, step `catalog-scope`)

Runs first in the `threat-model-author` phase, after code recon, so it can read
the inventory, the run config, the domain packs and, when present, the IaC
evidence index.

**Run system types** = the union of:

1. each active domain pack's `threat_profile.system_types`;
2. `threat_catalog.system_types`;
3. evidence-derived types: `system-types.yaml` maps IaC resource types when
   `00-context/iac-evidence-index.yaml` exists (`aws_lambda_function` →
   `serverless`, `aws_eks_cluster` → `container_k8s`, `aws_api_gateway_*` →
   `api`, and so on);

minus `exclude_system_types`. Each type records its sources.

**Surface system types.** `system-types.yaml` gives each asset type and
identity type a candidate list and a default. For example `service:
{candidates: [web_app, api, serverless, saas], default: api}`, `compute:
{candidates: [server, cloud, container_k8s, serverless], default: server}`,
`queue: {candidates: [b2b_integration, cloud, data_store], default:
data_store}`, `workload_identity: {candidates: [identity], default: identity}`.
A surface's types are its candidates intersected with the run types, or the
default when the intersection is empty.

**Eligibility.** A threat is eligible for a surface when all of these hold:

- its family is not excluded (default exclusions in `selection.yaml`: `EN`,
  `FA`, `CF`, `PH`, `LG`; packs may include them back);
- its `kind` is not `consequence` and its `abstraction` is not `outcome`;
- its `system_types` intersect the surface's types;
- and at least one of: a STRIDE letter applicable to the surface's element
  type; a LINDDUN code when the surface carries a PHI or PII classification; a
  `maestro` mapping when the `agentic-ai` pack is active.

**Output** `00-context/threat-scope.yaml` (schema `threat-scope`):

```yaml
schema_version: 1
generated_by: apd-gauntlet
catalog: {edition: open, version: 1.0.0, sha256: "…", fallback_from: null}
selection_version: 1
system_types: [{type: api, sources: [domain:pbm, asset:claims-api]}]
surfaces: [{asset: claims-api, element: process, system_types: [api], stride: [S, T, R, I, D, E], linddun: [I, D_isclosure]}]
threats: [{id: TC-AC-004, surfaces: [claims-api], reasons: [system_type:api, stride:E], goals: [authenticity, integrity]}]
warnings: []
```

### 8.2 Candidates (`author-threat-model`, extended)

When `threat-scope.yaml` exists, each skeleton entry gains
`catalog_candidates: [{id, rank_reason}]`, at most `top_n` (default 3), chosen
from the threats eligible for that surface whose `stride` contains the cell's
letter. The ranking is lexicographic on:

1. abstraction: `technique` before `class`;
2. kind: `event` before `condition` before `hazard`;
3. more shared system types with the surface first;
4. families in the pack's `emphasize_families` first;
5. id.

Two filters run before the cut:

- **Most specific wins.** A parent is dropped when one of its eligible
  children survives.
- **Family diversity.** At most `max_per_family` (default 2) threats per family
  per cell.

**LINDDUN and MAESTRO floors.** For surfaces with PHI or PII classifications,
the floor also writes LINDDUN cells: one per LINDDUN code that has an eligible
threat, each with `methodology: linddun`, `framework_refs.linddun_letter` in
the gauntlet's encoding, and candidates ranked the same way. With `agentic-ai`
active, it writes MAESTRO cells: one per layer id (`L1`–`L7`, and `CL` for
cross-layer) among the eligible threats' `maestro` mappings, with `methodology: maestro` and the layer in the stub
threat text (`(MAESTRO <layer> on <asset>: to be grounded)`), since
`framework_refs` has no MAESTRO slot. The prose-only augments in the agent's
Step 5 become grounding of these cells. LINDDUN adds at most seven cells per
PHI or PII surface (`phi_subset` counts as PHI), and the token gate (§14)
watches the cost. LINDDUN stubs read `(LINDDUN <code> on <asset>: to be
grounded)` so their ids never collide with STRIDE `I` cells. Candidate text for
the agent goes to `00-context/threat-candidates.md`; the skeleton carries only
`{id, rank_reason}`.

### 8.3 TM author agent

Step 3 changes from "drawn from the active domain pack's prose" to: for each
cell, judge each candidate against the cited element. Then:

- **Grounded:** the cell is grounded when at least one candidate is grounded.
  The entry's `threat` names the grounded threat or threats in the system's
  terms, and `catalog_refs` lists the grounded ids in the agent's order of
  relevance.
- **Grounded off-catalog:** a threat no candidate covers is still allowed,
  with `catalog_refs: []` and a `catalog_gap_reason` of at least 20 characters.
- **Blocked:** as today, with candidates left unconfirmed.

One entry per cell stays the rule, so the STRIDE cells, the TM's shape and
every downstream join are unchanged. The LINDDUN and MAESTRO cells replace
entries the agent already wrote from prose. Catalog text reaches the agent as
described in §12.2.

### 8.4 Goals and shortlists (`apd-gauntlet catalog shortlists <run-dir>`, step `catalog-shortlists`)

Runs in the `canonicalize` phase, right after WS1's
`canonicalize-threat-model` and before tier 1, so grounded threats rank first.

A threat's APD goals are the union of:

- `stride_letter_to_apd_goals` over its STRIDE letters;
- `linddun_letter_to_apd_goals` over its translated LINDDUN codes;
- `apd-goals.yaml[family]`, which reaches the goals STRIDE cannot (for
  example `IA` → `ephemeral`; `LD` → `non_repudiation`, `immutability`; `AV`,
  `OP` → `availability`, `resilient`, `distributed`);
- `impacts` of `availability` → `availability`.

For each of the nine goals, `00-context/threat-shortlists/<goal>.md` lists the
in-scope threats with that goal. They are ordered by grounded threats (by
number of TM entries citing them), then the §8.2 rank, then id, and capped at
`shortlist_cap` (default 40).

Each row holds:

- id and name;
- one line of at most 160 characters: the `summary` when the loaded edition
  has one (every threat in full, `source: added` threats in open), otherwise
  the family name;
- the surfaces it applies to;
- its primary mappings in the run's active taxonomies.

The file opens with the provenance line and the §12.2 data fence.

### 8.5 Lenses

Lens agents read their shortlist with the rest of their context.
`apd-evidence-discipline` and `apd-control-mappings` gain one section:

- A finding or capability may cite `threat_refs`: catalog ids from the
  shortlist or the scope file that the finding is an instance of, or that the
  capability mitigates.
- Citing a threat does not replace evidence.
- `control_mappings` stays the lens's own judgment. Canonicalize copies
  nothing into it.

### 8.6 Derivations (canonicalize, ADR-0020)

**`catalog_mappings` on findings.** For each finding with `threat_refs`, the
derived field is built as follows:

- **Sources:** the primary mappings of the cited threats. `mitre_attack` and
  `nist_800_53r5` (from `controls.nist_800_53`) are always derived, as lens
  ATT&CK and NIST always are; every other taxonomy in `taxonomy-map.yaml` only
  when the run's `taxonomies` activates it (`mitre_atlas` activates `atlas`).
- **Validation:** each id must exist in the gauntlet's KB for that taxonomy.
  An id that does not is dropped and counted in `catalog-gaps.yaml` as
  `unverified_mapping`.
- **Shape:** `{<taxonomy>: [{id, via: [TC-…]}]}`, sorted.

| Catalog key | Gauntlet taxonomy | KB |
|---|---|---|
| `attack_enterprise`, `attack_mobile` | `mitre_attack` | `mitre-attack-techniques.json` |
| `atlas` | `atlas` | `atlas-techniques.json` |
| `cwe` | `cwe` | `cwe.json` |
| `owasp_top10` | `owasp_top10` | `owasp_top10.json` (2025 after §10) |
| `owasp_api` | `owasp_api_top10` | `owasp_api_top10.json` |
| `owasp_llm_2025` | `owasp_llm_top10` | `owasp_llm_top10.json` (2025 after §10) |
| `maswe` | `maswe` | `maswe.json` |
| `capec` | (CAPEC bridge input) | `capec.json` |
| controls `nist_800_53` | `nist_800_53r5` | `nist-controls.json` |
| controls `d3fend` | (defense graph) | `d3fend.json` |

**LINDDUN translation:**

| Catalog | Gauntlet |
|---|---|
| `L` | `L` |
| `I` | `I` |
| `Nr` | `N_repudiation` |
| `D` | `D_etectability` |
| `DD` | `D_isclosure` |
| `U` | `U` |
| `Nc` | `N_compliance` |

**TM entries.** When `framework_refs.mitre_attack` is empty and `catalog_refs`
is not, canonicalize fills it from the cited threats' primary ATT&CK mappings
(techniques only; KB-checked). An agent-authored value is never overwritten.

**Validator.** These rules are errors:

- a `threat_refs` or `catalog_refs` id that is not in the loaded catalog;
- `threat_refs` when `threat_catalog` is `off`;
- a grounded TM entry with neither `catalog_refs` nor `catalog_gap_reason`
  whose skeleton cell (same asset and cell key) had candidates. Agent-built
  data flows and cells without candidates are exempt.

The tier repair loop fixes them as it fixes schema errors.

These rules are warnings:

- a cited threat outside the run's scope;
- a lens-authored mapping in a validated taxonomy that none of the cited
  threats maps (primary or partial). This is also recorded as an
  `unsupported_mapping` gap.

The derived fields (`catalog_mappings`, the `framework_refs.mitre_attack`
fill, edge `threat_refs` and `tactic_sequence`) are entered in
`docs/deterministic-field-register.md`.

**Registrations in `validate.py`.**

- `threat-scope.yaml` joins `CONTEXT_DERIVED_STEMS`, so `catalog_silence`
  findings can cite it as evidence. Shortlists are context, not evidence, and
  are not added.
- `catalog-coverage.yaml` and `catalog-gaps.yaml` join `SYNTHESIS_ROLLUPS`.

### 8.7 Threat-model evaluator

WS5's `tm-candidates.yaml` gains `catalog_silence: [{threat_id, surfaces,
goals, kind, abstraction, crown_jewel_surface: bool}]`. These are in-scope
threats that no TM `catalog_refs`, finding `threat_refs` or capability
`threat_refs` cites, ordered by crown-jewel surface first, then the §8.2 rank,
and capped at `silence_cap` (default 15).

The evaluator still reads only `tm-candidates.yaml`. For each entry it either:

- **emits** a `catalog_silence` finding, when the context it was given
  supports applicability: `tmeval_key: {flavor: catalog_silence, threat_id,
  surface}`, `disposition: uncertainty`, `severity: low` (`medium` on a
  crown-jewel surface), and a title naming the threat and surface;
- or **dismisses** it with a one-line reason in
  `40-threat-model/catalog-silence-dismissals.yaml` (schema
  `catalog-silence-dismissals`: `threat_id`, `surface`, `reason`), which feeds
  the coverage view.

The existing Rule 7 is unchanged.

### 8.8 Attack paths

- **Edges:** asset-graph edges built from findings gain a derived `threat_refs`,
  copied from the finding.
- **Paths:** each path gains `tactic_sequence`, the ordered ATT&CK tactics of
  its edges' cited threats, deduplicated in order.
- **Defense graph:** it adds the cited threats' `controls.d3fend` primary
  entries as `source: catalog` countermeasures beside the KB-inferred ones.
  The D3FEND-must-counter-ATT&CK rule still applies to both.
- **Enumeration** is unchanged.

### 8.9 Rollups, coverage view and report

**Source split.** `attack-exposure`, `cwe-coverage`, `owasp-coverage`,
`atlas-coverage`, `maswe-coverage` and `nist-coverage` entries gain
`catalog_finding_ids`, the findings that reach the entry only through
`catalog_mappings`. Existing counts stay lens-authored, so this layer changes
no current number and no comparison gate.

**`40-synthesis/catalog-coverage.yaml`** (schema `catalog-coverage`, ADR-0022
derived view) contains:

- the catalog provenance and selection version;
- `threats`: every in-scope threat with a `status`, plus its finding, capability
  and TM ids. The status is the first that applies:
  - `finding`: a finding cites it;
  - `capability`: a capability cites it and no finding does;
  - `grounded`: only a TM entry cites it;
  - `blocked`: only blocked cells list it as a candidate, read from
    `threat-model-skeleton.yaml`;
  - `dismissed`: the evaluator dismissed it;
  - `silent`: none of the above.
- `frameworks`: for each catalog framework, the items reached through in-scope
  threats, each with a `posture` from the threats' statuses and a `fidelity`
  of `exact` when every contributing link is `primary`, otherwise `partial`.
  This covers OWASP Agentic, NHI, CI/CD and Kubernetes, MAESTRO, CSA, HICP,
  CIS v8 and EMB3D. The view says what the review examined, not an
  attestation.

**Report.** `build-report` adds a "Threat coverage" section when the file
exists:

- counts by status;
- the silent and blocked threats on crown-jewel surfaces;
- framework tables;
- tactic sequences on the attack-path scene.

Threat rows show id and name; summaries appear only for `source: added`
threats. The report writer's metrics input gains the status counts.

### 8.10 Gaps

`40-synthesis/catalog-gaps.yaml`, written at rollup, holds:

- **`off_catalog_threat`**: grounded TM entries with `catalog_gap_reason`
  (exempt entries are never counted);
- **`unmapped_finding`**: findings with no `threat_refs` whose lens mappings
  match no in-scope threat's mappings;
- **`unsupported_mapping`**;
- **`unverified_mapping`**;
- **`system_type_gap`**: surfaces whose type list fell back to the default.

`apd-gauntlet catalog export-gaps <run-dir>… --out <file>` merges these
across runs into a proposal file for the catalog repo:

- **Kept:** kinds, counts, catalog ids, framework ids, and the agents' gap
  reasons.
- **Removed:** evidence pointers, asset, identity and surface names, repo
  paths and finding text.

The export is written locally and never sent anywhere. Its header says it
needs operator review before it leaves the machine.

## 9. Schemas (all additive)

| Schema | Change | Plan |
|---|---|---|
| `run-config` | `threat_catalog` (string or object, §7) | CAT1 |
| `domain` | `threat_profile` | CAT2 |
| `threat-scope` | New | CAT2 |
| `threat-model-normalized` | Entries gain `catalog_refs` (array of catalog ids) and `catalog_gap_reason` (string, at least 20 characters) | CAT2 |
| `finding` | Gains `threat_refs` and `catalog_mappings`; `tmeval_key.flavor` gains `catalog_silence`, `tmeval_key` gains `threat_id`; `owasp_llm_top10` items accept `LLM01:2025` as well as `LLM01` | CAT1 (pattern), CAT3 |
| `capability` | Gains `threat_refs` | CAT3 |
| `tm-candidates` | Gains `catalog_silence` | CAT3 |
| `asset-graph`, `attack-path` | Edges gain `threat_refs`; paths gain `tactic_sequence` | CAT3 |
| `catalog-coverage`, `catalog-gaps`, `catalog-silence-dismissals` | New | CAT3 |
| Coverage rollups (§8.9) | Entries gain `catalog_finding_ids` | CAT3 |
| `eval-labels` (WS2) | Gains `threats`: applicable catalog ids per corpus system, and expected mappings per labelled finding | CAT4 |

The catalog id pattern `^TC-[A-Z]{2}-\d{3}$` goes into `_defs.schema.json`.

## 10. Edition alignment

1. **OWASP LLM** (the F5 defect). `refresh-owasp` gains the 2025 list as the
   LLM source, and the `apd-control-mappings` skill teaches 2025 meanings with
   year-qualified ids (`LLM06:2025`). Every 2.0 source of guidance then agrees,
   so `canonicalize` rewrites a bare `LLMnn` to `LLMnn:2025` on runs made with
   framework 2.0 or later. Bare ids in runs older than 2.0 are ambiguous (F5):
   rollups show them as `edition: unknown` with both names, and `compare-runs`
   reports the OWASP LLM taxonomy as `not_comparable` across that boundary
   rather than guessing.
2. **OWASP Top 10.** The KB moves to the 2025 list, and the
   `apd-control-mappings` skill teaches 2025 ids. 2021 ids stay valid: they
   match the existing pattern. Rollups translate them through the crosswalk
   and mark them `crosswalked: true`.
3. **ATT&CK and the rest.** `refresh-mitre`, `refresh-atlas`, `refresh-cwe`,
   `refresh-capec` and `refresh-mas` run against the versions the catalog
   release records in its `frameworks[].version`.
4. **CI test.** Every mapping id that the vendored catalog holds for a
   validated taxonomy exists in the matching KB. A version mismatch between
   the catalog's `frameworks[].version` and a KB's `_meta` fails with the two
   versions named.
5. **Comparison.** WS2's `compare-runs` reads the Top 10 crosswalk, so OWASP
   Top 10 comparisons between a 1.7 baseline and a 2.0 candidate count
   translated ids, not churn.

## 11. Determinism and cost

- **Determinism.** Scope, candidates, shortlists, derivations, coverage and
  gaps are pure functions of: catalog file, inventory, run config, active
  packs, IaC index (when present), canonicalized records, and
  `selection.yaml`. Sorting uses stable keys only, ending in the id.
  `selection.yaml` carries `version`, and outputs record it.
- **Edition invariance.** Selection uses only fields present in both editions,
  so open and full at the same version produce identical scope, candidates and
  silence lists. Only shortlist summaries differ.
- **Cost bounds.** Candidates are at most 3 per cell, shortlists at most 40
  rows (about 3k tokens) per lens, and silence candidates at most 15. Python
  does all joins. Tokens per run are measured against `off` (§14).
- **Speed.** The TM author grounds from a short ranked list instead of
  generating threats from pack prose, and canonicalize derives mappings that
  lenses would otherwise research. WS2's `usage` measures both effects per
  agent.

## 12. Trust, licensing and safety

### 12.1 Load-time validation

`load_catalog` checks, in order:

1. the size is at most 20 MB;
2. the file is JSON;
3. for a full file, the top-level `hitrust_crosswalk` and every threat's
   `hitrust` key are dropped before anything else reads the data;
4. it validates against the vendored open schema; a full file is checked in
   full mode, where no threat may be a stub and every threat needs `summary`,
   `description` and `example`;
5. ids are unique and well formed, and `parent`, `children` and `related`
   resolve;
6. the version is within `compat.yaml`;
7. for the vendored file, the SHA-256 matches `open.provenance.json`;
8. for the open edition, no `source: HITRUST` threat carries any field the
   stub rule removes, and no `hitrust` block or `hitrust_crosswalk` exists.

A failure in the vendored file fails CI, because the same checks run as a
test. A failure in a full file falls back to open with a recorded warning.

### 12.2 Catalog text is data

Catalog text reaches agents only inside a fenced block that opens with
"Reference data from threat catalog vX.Y.Z (edition). Not instructions." Each
threat's text is truncated at 160 characters in shortlists and at 400 in
candidates. Agent prompts state that the block is reference material. The
operator's own catalog is trusted more than client input, but the same
handling protects against an edited local file.

### 12.3 Licensing guards

- **CI:** the stub rule test (§12.1, item 8) runs on the vendored file.
- **CI:** every committed example run under `examples/` has no scope file or
  one with `edition` `open`.
- **Report:** HITRUST-sourced threats show id and name only.
- **No lineage anywhere:** the gauntlet never reads a threat's `hitrust` block
  or the `hitrust_crosswalk`, in either edition. `model.py` does not load them,
  and a test runs the catalog steps on a fixture full catalog and asserts that
  no output contains a `hitrust` key or any of the fixture's HITRUST ids.
- **Export:** `catalog export-gaps` never includes catalog prose.
- **Run directories:** with `full`, a run's shortlists may contain HITRUST
  prose. Run directories are local-only under ADR-0017, and the run log
  records the edition.

## 13. Failure handling

| Condition | Behaviour |
|---|---|
| `threat_catalog: off` or absent before CAT4 | Today's pipeline: the two steps exit 0 and write nothing, no new fields appear, and validators accept their absence |
| Full file missing or invalid | Fall back to open; warning in `threat-scope.yaml` and the run log |
| Vendored file invalid | CI fails; a run with `open` exits at `catalog-scope` with the validation error (this cannot ship) |
| No eligible threats for a cell | The cell has no candidates and is handled as today |
| Inventory missing | `catalog scope` exits 1 with the same message as `author-threat-model` |
| A 1.7 run resumed on 2.0 | Refused, as `resume-plan` already does (exit 3) |
| Cited id not in the catalog | Validation error, repaired by the tier repair loop |

## 14. Evaluation

Measured with the WS2 harness, on the master plan Task 1 set plus labelled
development and held-out corpora (ADR-0017: local only; labels and results
never committed).

**Labels (CAT4).** For each corpus system, the operator labels the catalog
threats that apply (with surfaces), and for a sample of findings, the correct
ATT&CK, CWE and 800-53 ids. `eval-labels` gains a `threats` section.

**Runs.** Each corpus system is run twice with `off` and twice with `open`,
plus `full` locally.

**Evaluators**, registered through `apd_gauntlet.eval.evaluators.register`:

| Evaluator | Measures |
|---|---|
| `catalog-tm-recall` | Labelled applicable threats covered by a TM entry (via `catalog_refs`, or judged equivalent for `off` runs by the labeller's mapping) |
| `catalog-mapping-precision` | Precision of `control_mappings` (lens) and `catalog_mappings` (derived), scored apart |
| `catalog-silence-precision` | Share of `catalog_silence` findings the labels mark applicable |
| `catalog-grounding` | Candidates grounded, blocked and unconfirmed per cell; off-catalog entries |

**Proposed gates**, added to `eval/gates.yaml` as proposals:

- TM coverage recall with `open` not below `off`;
- lens mapping precision with `open` not below `off`;
- derived mapping precision at least 0.9;
- silence precision at least 0.8;
- tokens per run with `open` at most 1.05 × `off`;
- the existing gates all pass.

**Tuning.** `top_n`, `max_per_family`, `shortlist_cap`, `silence_cap`, the
family exclusions and `system-types.yaml` are tuned on the development set
only. They are then frozen (`selection.yaml` `version` bumped) and measured
once on held-out. A held-out failure means `off` stays the default for 2.0.

**Metamorphic suite `catalog`** (CI, deterministic, through `metamorphic
run`):

| Id | Transformation | Expected |
|---|---|---|
| C1 | Rename assets and identities consistently | Candidate ids per cell unchanged under the renaming |
| C2 | Reorder inventory records | Scope and candidate sets unchanged |
| C3 | Add an asset of an unrelated type | Other surfaces' candidates unchanged |
| C4 | Change one asset's type | That surface's candidates change (sensitivity) |
| C5 | Reorder threats in the catalog file | Byte-identical outputs |
| C6 | Swap the open edition for a full file of the same version | Identical scope, candidates and silence lists |

## 15. Delivery

New workstream **WS10, threat catalog**, four plans:

| Plan | Scope | Depends on | Milestone |
|---|---|---|---|
| CAT1 — data, loader, editions | §6, §7 (`threat_catalog` key), §8 `config`/`load`/`model`/`translate`, §10, §12.1, §12.3 CI tests, LA3 doctor check, ADR-0030 | WS2 (`compare-runs` crosswalk hook) | M4; may start in M3 alongside LA1 |
| CAT2 — scope and TM author | §8.1–8.3, domain `threat_profile` for the six packs, TM schema, `catalog-scope` step in workflow, `plan_run.py` and `runner/flow.py`, and the §14 metamorphic suite `catalog` (C4 as a unit test, since it checks sensitivity rather than invariance) | CAT1, WS1 (`canonicalize-threat-model`, `resume-plan`), LA2 | M5 |
| CAT3 — lenses, evaluator, paths, report, gaps | §8.4–8.10, `catalog-shortlists` step, schemas, skills, report section | CAT2, WS5 Task 8 (`tm-candidates`) | M5 |
| CAT4 — evaluation | §14 except the metamorphic suite: labels, evaluators, gates, tuning and freeze, and the default | CAT3, WS2 | M6, before feature freeze |

Registry additions (master plan R1–R10) land with this spec. The catalog takes
ADR-0030; code-flow moves to 0031 onward.

**Operator work.**

- Publish catalog release `1.0.0` with both assets and the open schema.
- Confirm the HITRUST position: open stubs keep names and mappings.
- Label threats for the corpora (CAT4).

## 16. Risks and open questions

1. **The OWASP LLM defect predates this work** (F5). Decided 2026-10-11: it is
   fixed on 2.0 only (CAT1, §10). 1.7.x keeps the 2023 list and skill text, so
   `agentic-ai` runs on 1.7.x may still carry ambiguous bare ids.
2. **Catalog quality bounds derived mappings.** The catalog's residual mapping
   error is about 1–2%. Derived mappings are a separate field and are counted
   apart, so an error never changes a lens-authored count. The precision gate
   watches it.
3. **System-type precision.** Coarse asset types may over-select. Mitigations:
   intersection with run types; the C3 and C4 checks; tuning on development
   data. Inventory gaining a `technology` field would help and is out of
   scope.
4. **Shortlist anchoring.** Lenses may confine themselves to shortlisted
   threats. The prompts say the shortlist is a floor, not a boundary, and the
   recall evaluator compares against `off`.
5. **Supplied threat models** are not matched to catalog ids in this design.
   The later WS6 task `threat-match` would propose `catalog_refs` for
   `tm-recon` entries, as a calibrated decision task.
6. **Name drift.** A catalog rename changes shortlist text but not ids. Ids are
   stable across catalog minor versions; removed ids are listed in the refresh
   diff, and the validator reports them on old runs as warnings.
