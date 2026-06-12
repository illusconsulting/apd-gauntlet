# Deterministic Field Register

This register records every **derived** field in an APD gauntlet run — a field that
is a pure function of authored content — and names the single deterministic owner
that authors it, the enforcement that verifies it, and the agent-side contract.

The governing principle ([ADR-0020](adrs/0020-tooling-authored-derived-fields.md)):
**agents author content only; a deterministic assembler authors every derived
field.** "Authored" content (titles, evidence, severity, which controls apply,
the structured inputs an ID is derived from) is the agent's job. Identity and
other pure-function-of-content fields are the tooling's job.

## Record IDs

Every ID is `<prefix>-<sha8>` (SHA-256, first 8 hex). The owner is the function
in `tools/apd_gauntlet/` that computes it; the enforcement is the linter/pass
that recomputes and flags drift. Agents never author these.

| Field / family | Owner (script function) | Computed from | Enforcement | Agent contract |
|---|---|---|---|---|
| `id` on finding (`conf-`, `intg-`, `avail-`, `dist-`, `resil-`, `ephem-`, `auth-`, `nonrep-`, `immut-`) | `linters.compute_id` via `canonicalize._recompute_ids_for_file` | `title \| first_evidence_locator` | `linters.check_finding_id` + `linters.check_id_present` (semantic pass) | emits NO `id` |
| `id` on capability (`*-cap-…`) | `linters.compute_capability_id` via `canonicalize._recompute_ids_for_file` | `title \| first_evidence_locator` | `linters.check_capability_id` + `linters.check_id_present` | emits NO `id` |
| `tmeval-*` (threat-model evaluator) | `linters.compute_tmeval_id` via `canonicalize._recompute_ids_for_file` | structured `tmeval_key` (flavor + components) | `linters.check_tmeval_id` (semantic pass) | emits a `tmeval_key`, NO `id` |
| `dimpr-*` (domain-improvement auditor) | `linters.compute_improvement_id` via `canonicalize._mint_dimpr_ids` | `improvement_type \| target_pack \| target_file \| evidence[0].ref` (lowercased) | `linters.check_domain_improvement_id` + `validate._validate_domain_improvements_cross_refs` | emits content, NO `id` |
| `asset-*` (inventory assets) | `linters.compute_asset_id` via `assemble_inventory.assemble_inventory` | `name \| provenance.locator` | inventory cross-ref pass in `validate` | emits NO `asset_id`; authors `crosses` by name |
| `idn-*` (inventory identities) | `linters.compute_identity_id` via `assemble_inventory.assemble_inventory` | `name \| provenance.locator` | schema pattern (post-assembly) | emits NO `identity_id` |
| `tb-*` (inventory trust boundaries) | `linters.compute_boundary_id` via `assemble_inventory.assemble_inventory` | `name \| provenance.locator` | schema pattern (post-assembly) | emits NO `boundary_id` |
| `apath-*` (attack-path analyzer) | `attack_path/findings.py` (Python emitter) | `sha8(path_id)` | emitter is deterministic | n/a — emitted by the deterministic analyzer floor |
| `merged-*` (dedup) | `synthesis/apply.py` (apply-clusters) | cluster membership | apply-clusters is deterministic | n/a — minted by the synthesizer apply step |

## Other derived fields

| Field / task | Owner | Notes |
|---|---|---|
| `schema_version` on finding / capability | `canonicalize._recompute_ids_for_file` (`setdefault(1)`) | agents emit NO `schema_version` |
| `control_mappings` normalization (lift/relocate taxonomy keys) | `canonicalize._normalize_control_mappings` | self-heals common specialist-output frictions |
| `cross_references` rewrite (old→new id map) | `canonicalize.canonicalize_run` (pass 2) | follows the global id remap |
| `cross_references` / `merged_from` / `linked_perspectives` (dedup provenance) | `synthesis/apply.py` | synthesizer-authored, post-assembly |
| NIST 800-53r5 / ATT&CK / APD-matrix / coverage rollups | `synthesis/rollup.py` | unions deduped + `apath-*` + `tmeval-*` findings |
| `metrics.yaml` | `synthesis/metrics.py` | the report loader's required input |
| run-directory scaffold (`inputs/`, tier dirs, `.apd-run.yaml`) | `init_run.scaffold_run` | the `apd-gauntlet init-run` floor |

## Where the assembler runs

The workflow runner (`.claude/workflows/apd-gauntlet.js`) invokes the assembler
at each point a phase has just emitted records and before the next consumer reads
their IDs:

- **intake phase** — `assemble-inventory` after intake emits and before the
  `00-context` schema-gate (so the gate sees the canonical, id-bearing form), and
  well before specialists cite inventory IDs.
- **per tier** — `canonicalize` after the tier's specialists and before the tier
  validate gate.
- **after the tmeval/apath barrier** — `canonicalize` before `rollup` (which
  unions `tmeval-*` IDs into coverage).
- **after the domain-improvements phase** — `canonicalize` before the closeout
  validate.

Standalone callers must run `canonicalize` (and `assemble-inventory`) before
`validate`'s semantic pass, which enforces ID presence for in-scope records via
`check_id_present`.

## Maintaining this register

Every `compute_*_id` helper in `tools/apd_gauntlet/linters.py` must appear in this
register. `tests/test_register_consistency.py` enforces that invariant — when you
add a new deterministic ID helper, add its row here.
