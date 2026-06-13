# Schema Evolution

APD Gauntlet has three independent versions:

| Thing | Where it lives | Bumped when |
|---|---|---|
| **Framework version** | `pyproject.toml`, git tags, `framework_version` field on context brief and advisory report | The `.claude/` content or schemas change in a way users notice |
| **Schema version** | `schema_version` integer field on each finding and capability record | A schema gets a breaking change |
| **Domain pack version** | `version` field in each pack's `domain.yaml` | Pack-specific rubric or pattern content shifts |

## Schema breaking-change semantics

| Change | Bump |
|---|---|
| Renaming a required field | Major |
| Adding a required field | Major |
| Removing a field (required or optional) | Major |
| Adding an optional field | Minor |
| Tightening a constraint (shorter maxLength, narrower enum) | Minor |
| Loosening a constraint (longer maxLength, wider enum) | Patch |
| Documentation-only changes | Patch |

When bumping the schema_version:

1. Update the `const` value in the schema (e.g., `"schema_version": { "type": "integer", "const": 2 }`).
2. Update existing fixtures, templates, the bundled example, and the apd-finding-schema skill.
3. Document the breaking change in `CHANGELOG.md`.
4. Consider whether old YAML records should be auto-migratable; if so, ship a migration script.

## Domain pack compatibility

Each pack declares a `framework_compat` semver range:

```yaml
framework_compat: ">=1.0.0,<2.0.0"
```

The validator refuses to build the apd-domain skill if the active framework version is outside the declared range. When the framework hits a major bump:

- Pack maintainers update `framework_compat` to include the new range.
- Existing packs continue working on the previous major version; users pin a specific framework version if needed.

## Framework version compatibility

The framework's external surface includes:

- The CLI command set and flag semantics.
- The schema files in `schemas/`.
- The plugin manifest format.
- The expected directory layout of a run.
- The expected frontmatter fields on context-brief and advisory-report.

Changes to any of these surfaces require a version bump. Internal refactors of `tools/apd_gauntlet/` modules don't.

## PyPI trusted publishing

The release workflow publishes to PyPI via trusted publishing. This requires a one-time setup:

1. Create the `apd-gauntlet` project on PyPI (manual; reserved by initial release).
2. In PyPI's "Publishing" tab, add a trusted publisher entry for the GitHub repo `shoveleejoe/apd-gauntlet`, workflow `release.yml`, environment unset.
3. Tag a release (`git tag v1.0.0 && git push origin v1.0.0`). The release workflow publishes automatically.

If trusted publishing isn't set up, the workflow's PyPI step fails; the GitHub Release still succeeds. Set up trusted publishing before the first tag.

## Deprecation policy

When a field or behavior is deprecated:

1. Add a deprecation note to the relevant skill or doc file. Cite the version in which removal will occur.
2. Keep the deprecated surface working through at least one minor release.
3. Remove in a major bump.

## v1.7.0 — Tooling-authored derived fields (id ownership)

Non-breaking (permissive) schema changes; see [ADR-0020](adrs/0020-tooling-authored-derived-fields.md) and [deterministic-field-register.md](deterministic-field-register.md).

- **Record ids are now optional-at-emission** (removed from `required`, marked `readOnly`): `id` on `finding`, `capability`, and `domain-improvement` records, and `asset_id` / `identity_id` / `boundary_id` on asset-inventory records. `schema_version` is likewise optional-at-emission on `finding` and `capability` records (it is the only record types that carry a per-record `schema_version`). The deterministic assembler (`apd-gauntlet canonicalize`, plus `assemble-inventory` for the inventory) is the sole author; agents emit records without them. A present-but-malformed id is still rejected (the patterns are retained).
- **`tmeval_key` added** to the finding schema — an optional object (`flavor` + components) the threat-model evaluator emits in place of a hand-computed `tmeval-` id; `canonicalize` mints the id from it.
- **`trust_boundaries.crosses` relaxed** in the asset-inventory schema from the `asset-<hex8>` pattern to any non-empty string, so intake can author `crosses` by asset name pre-assembly; `assemble-inventory` rewrites names to the minted asset ids (`minItems: 2` retained).

Packs and consumers need no changes: every change is a relaxation, and post-assembly records carry the same id forms as before.

## v1.7.0 — Static infrastructure intake

Additive within v1.x; framework version held at 1.7.0.

- **2026-06-10** — `run-config.schema.json` gains an optional `infrastructure`
  object (`additionalProperties:false`) with a `mode` enum (`disabled` |
  `static` | `live`; absent == disabled) and a `static` sub-object of
  path-traversal-guarded glob arrays (`k8s`, `istio_linkerd`, `terraform`,
  `helm`, `cert_secret_managers`), each using the same `^(?!/)(?!.*\.\.).+$`
  guard as `threat_model`. Only `mode` + `static` are implemented; the `live`
  sub-block is reserved for a future release. New derived artifact
  `40-synthesis/manual-audit-prompts.md` (from `apd-gauntlet
  manual-audit-prompts`; no schema — a generated markdown report).

## v1.7.0 — Multi-repo code reconnaissance (additive)

Additive within v1.x. The framework version is held at 1.7.0; these are
optional-field additions sequenced by dependency phase, not a release bump.

- `run-config.schema.json` — gains an optional `repos[]` array. Each entry is
  `{cbm_project (required), role? (enum: primary|dependency|peer),
  repo_path? (path-traversal-guarded)}`. Declares a multi-repo system for
  `apd-code-recon`. `cbm_project` (singular) is unchanged and remains valid for
  single-repo runs.
- `code-evidence-index.schema.json` — gains an optional top-level `repos[]`
  provenance array (`{cbm_project, indexed_commit_sha}` per repo) and an
  optional per-entry `repo` string. An `if/then` requires `repo` on every entry
  when top-level `repos[]` is present. Existing single-repo indexes (no
  `repos[]`, no per-entry `repo`) stay valid unchanged.

Nothing removed; no `schema_version` bump (these are optional fields, Minor by
the breaking-change table above). `framework_compat ">=1.0.0,<2.0.0"` packs
consume v1.7.0 without changes. The cross-repo graph edges
(`CROSS_HTTP_CALLS` / `CROSS_ASYNC_CALLS` / `CROSS_CHANNEL`) consumed by
`apd-code-recon` are recorded as `kind: edge` index entries and need no CBM-side
schema. See ADR-0019. The upstream CBM provider-discovery defect (partial
index) is detected via a non-blocking `validate` warning and tracked
out-of-band; pin a minimum CBM version here once the upstream fix ships.

## v1.7.0 — Cross-cutting connective tissue (dated additive entries)

The framework version is held at 1.7.0; these are dated, additive, non-breaking
entries — no schema field is removed and no `framework_compat` range changes.

### 2026-06-11 — `data/*.json` cache `_meta` mini-shape standardized

Every fetched `tools/apd_gauntlet/data/*.json` carries a provenance block — a
`source` (or `source_url`), a `source_sha256` (or, for commit-pinned sources, a
`commit`), and a `fetched_at` — either nested under a `_meta` object or at the
top level. This is a **CI assertion** (`tools/check_kb_cache_freshness.py`, wired
into `python-tests.yml`), not a JSON Schema rule, because the data files are
caches, not run artifacts. The shared `tools/apd_gauntlet/kb_fetch.py`
(`fetch_pinned`) returns this block so the six refreshers populate it uniformly.
Legacy/hand-maintained files are documented exemptions in the gate; backfilling
their provenance is follow-on work. No finding/capability/run-config schema field
is added. See [CI gate model](ci-gate-model.md) and [Infra reuse map](infra-reuse-map.md).

## v1.2.0 — Multi-framework taxonomy mappings (Phase A)

Additive within v1.x. Extensions:

- `finding.schema.json` gains optional `control_mappings.cwe`, `owasp_top10`, `owasp_api_top10`, `owasp_llm_top10`.
- `capability.schema.json` gains optional `control_mappings.d3fend` (with required `counters_attack` cross-reference) AND optional `control_mappings.mitre_attack` (parallel to the field on findings; technique-level claims the capability defends against).
- `run-config.schema.json` gains optional `taxonomies` array.
- New schemas: `cwe-coverage`, `owasp-coverage`, `d3fend-coverage`.

PBM domain pack (`framework_compat: ">=1.0.0,<2.0.0"`) consumes v1.2.0 without changes.

## v1.3.0 — Methodology-aware threat-model evaluator (Phase B)

Additive within v1.x. Extensions:

- `finding.schema.json` — `agent` enum gains `threat_model_evaluator`;
  `id` pattern extended to accept `tmeval-<sha8>` prefix; same extension
  on `cross_references` and `merged_from` patterns.
- `run-config.schema.json` — accepts optional `threat_model: <path>` and
  `methodology_hint: <name>` fields. Methodology hint enum:
  stride / linddun / attack_tree / pasta / vast / trike / free_form.
- New: `threat-model-normalized.schema.json` (recon output).
- New: `threat-model-coverage.schema.json` (evaluator output).

Shared `$defs` extraction (Task B-4): `schemas/_defs.schema.json` holds
the canonical regex patterns for ATT&CK technique IDs, D3FEND IDs, and
CWE IDs. The four existing schemas (finding, capability, d3fend-coverage,
attack-exposure) `$ref` into `_defs.schema.json`. Validator builds a
jsonschema `Registry` so refs resolve. Behavior preserved (same patterns
enforced).

PBM domain pack (`framework_compat: ">=1.0.0,<2.0.0"`) consumes v1.3.0
with no changes.

## v1.6.0 — MITRE ATLAS taxonomy, MAESTRO methodology, and report completeness gate

Additive within v1.x. Extensions:

- `schemas/_defs.schema.json` — gains `atlas_technique_id` def (`^AML\.T[0-9]{4}(\.[0-9]{3})?$`),
  shared by `finding.schema.json` and `atlas-coverage.schema.json`.
- `finding.schema.json` — `control_mappings` gains optional `atlas` array of
  `atlas_technique_id` refs; validates MITRE ATLAS technique IDs emitted by specialists.
- New: `schemas/atlas-coverage.schema.json` — synthesizer rollup of ATLAS technique
  coverage: entries carry `atlas_id`, `name`, `finding_count`, `finding_ids`, and optional
  `surfaces`. Gated by `mitre_atlas` in the run's `taxonomies:` list.
- `run-config.schema.json` — `taxonomies` enum gains `mitre_atlas`; `methodology_hint`
  enum gains `maestro` (alongside the existing stride/linddun/attack_tree/pasta/vast/trike/free_form values).
- `threat-model-normalized.schema.json` — `methodology` and per-entry `methodology` enums
  gain `maestro`.
- `threat-model-coverage.schema.json` — `methodology` enum gains `maestro`.
- `report-audit.schema.json` — per-check `klass` field added (optional `enum: ["structural", "editorial"]`),
  classifying each completeness check for the workflow's block-on-structural-failure gate.

Nothing removed. `framework_compat: ">=1.0.0,<2.0.0"` packs consume v1.6.0 without changes;
all additions are optional fields or new rollup schemas.

## v1.5.0 — HTML report, workflow runner, multi-domain runs, and deduplication pipeline (Phases A/B + report)

Additive within v1.x. Extensions:

- New: `schemas/agent-receipt.schema.json` — compact structured value an APD agent emits
  as its final message; carries `agent`, `status`, `outputs` (path + schema_valid per file),
  `counts` (findings_by_severity, capabilities_by_maturity, blocked), and optional `errors`.
  Used by the workflow runner (Subsystem A).
- `run-config.schema.json` — `domain` (single string) replaced by `domains` (array,
  `minItems: 1`) to support multi-domain runs; first element is the declared-order primary.
- New doc-envelope schemas wrapping existing per-record schemas (all added in Subsystem A):
  `nist-coverage-doc.schema.json`, `attack-exposure-doc.schema.json`,
  `coverage-matrix-doc.schema.json`, `severity-disagreements-doc.schema.json`,
  `contradictions-doc.schema.json`. Each wraps the corresponding record schema in a
  top-level array property.
- New: `schemas/cluster-candidates.schema.json` — mechanical candidate groups emitted by
  the `cluster-candidates` command; entries carry `group_id`, `kind`, `signals`
  (evidence_locator_overlap / title_similarity / related_concerns), and `members` (with
  full finding/capability snapshot per member).
- New: `schemas/cluster-decisions.schema.json` — disposition + merged prose emitted by the
  cluster-adjudicator; entries carry `group_id`, `disposition` (merge/link/separate),
  optional merged title/summary/detail/recommendation, and optional `contradictions` array.
- New: `schemas/rejected-records.schema.json` — records excluded from clustering and
  stale-capability maturity downgrades; entries carry `id`, `reason`, `category`
  (failed_validation / stale_capability_downgrade), and optional `from_maturity`/`to_maturity`.
- New: `schemas/report-data.schema.json` — synthesizer editorial supplement for the HTML
  report; carries `exec_summary` (1–6 paragraphs), `headline_findings`, `strengths`
  (with `caveats`), `next_steps`, `posture_summary` (per-tier text), and optional
  `domain_pack_caveat`.
- New: `schemas/report-audit.schema.json` — compact structural audit emitted by
  `audit-report`; carries `status`, `checks` (name/status/detail), `counts`
  (id-coverage/count-parity/nist_rollup_parity/recompute-drift counts), and `drift` (hash
  mismatches). Initial version ships without per-check `klass`; that field is added in v1.6.0.
- New: `schemas/domain-improvement.schema.json` and `schemas/domain-improvements-doc.schema.json`
  (Subsystem B) — capture domain-pack improvement opportunities identified during a run;
  entries carry `id` (`dimpr-<sha8>`), `improvement_type` (9 enum values including
  missing_crown_jewel, missing_severity_clause, missing_common_pattern), `target_pack`,
  `target_file`, `source`, `priority`, `evidence`, `rationale`, `suggested_action`,
  `draft_snippet`, and optional `insertion_hint`.
- New: `schemas/domain-coverage-delta-doc.schema.json` (Subsystem B) — paired with
  domain-improvements-doc for the domain-improvement capture step.

Nothing removed. `framework_compat: ">=1.0.0,<2.0.0"` packs consume v1.5.0 without changes.

## v1.4.0 — Attack-path enumeration and D3FEND defense graph (Phase C)

Additive within v1.x. Extensions:

- `finding.schema.json` — `agent` enum gains `attack_path_analyzer`; `id`
  pattern extended to accept `apath-<sha8>` prefix; same extension on
  `cross_references` and `merged_from` patterns.
- `run-config.schema.json` — accepts optional top-level `crown_jewels`
  and `attacker_positions` arrays of strings (per-run overrides) and an
  optional `attack_path_analysis` block with `max_hop`, `max_paths_per_pair`,
  and `bottleneck_threshold` numeric knobs.
- `domain.schema.json` — accepts optional `crown_jewels` and
  `attacker_positions` arrays of `{pattern|position, description}` entries,
  plus an optional `default_trust_boundaries` array of
  `{name, description}` entries. All three are optional; a pack that omits
  them remains v1.4-compatible.
- New: `asset-inventory.schema.json` — intake rollup of assets, trust
  boundaries, and data classifications.
- New: `asset-graph.schema.json` — analyzer-built graph of nodes and typed
  edges with provenance and confidence.
- New: `attack-path.schema.json` — enumerated attack paths plus the
  bottleneck-edge set plus the `enumeration_parameters` block that records
  the knobs the run was bounded by.
- New: `defense-graph.schema.json` — D3FEND counter overlay on the
  bottleneck edges that expose ATT&CK techniques.

Nothing removed. `framework_compat` unchanged (PBM and any other
`>=1.0.0,<2.0.0` packs consume v1.4.0 without changes; packs that want to
declare crown jewels, attacker positions, or default trust boundaries
should bump their `framework_compat` floor to `>=1.4.0,<2.0.0`).

See [docs/attack-path-analysis.md](attack-path-analysis.md) for the operator
guide and [docs/adrs/0010-attack-path-analysis-on-partial-graphs.md](adrs/0010-attack-path-analysis-on-partial-graphs.md) for the design rationale.

## See also

- [Architecture](architecture.md)
- [Extending agents](extending-agents.md)
- [CONTRIBUTING](../CONTRIBUTING.md)
