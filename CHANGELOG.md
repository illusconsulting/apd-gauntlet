# Changelog

All notable changes to this project will be documented in this file. Format based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versioning per [SemVer](https://semver.org/).

## [Unreleased]

## [1.2.0] - 2026-XX-XX

### Added

- **Multi-framework taxonomy mappings** on findings: CWE, OWASP Top 10 (web), OWASP API Top 10, OWASP LLM Top 10 (all optional, declared per run via `taxonomies:` in `.apd-run.yaml`).
- **MITRE D3FEND mappings on capabilities**, with required `counters_attack` cross-reference to ATT&CK techniques the capability defends against. Sub-technique parent matching: `T1110.001` is satisfied by `T1110` declared in `mitre_attack[]`.
- **`mitre_attack` field on capabilities** (parallel to the one on findings) — documents which ATT&CK techniques the capability defends against. Enables the D3FEND `counters_attack` cross-reference rule.
- **Per-run taxonomy scoping** via `taxonomies:` field in `.apd-run.yaml`. CWE/ATT&CK/D3FEND default-on; OWASP variants opt-in.
- **Intake `taxonomy_suggestions` block** auto-detects relevant surfaces (web routes, OpenAPI specs, LLM SDK imports) and writes advisory suggestions to the context brief.
- **Three new synthesizer coverage rollups**: `cwe-coverage.yaml`, `owasp-coverage.yaml`, `d3fend-coverage.yaml` (the last includes a `counter_coverage` view showing which exposed ATT&CK techniques have D3FEND-backed capabilities countering them).
- **Three new schemas**: `cwe-coverage.schema.json`, `owasp-coverage.schema.json`, `d3fend-coverage.schema.json`.
- **Three new CLI subcommands**: `refresh-cwe`, `refresh-owasp`, `refresh-d3fend` (each applies the v1.0 security-review hardening: 60s timeout, 200 MiB cap, `source_sha256` in projected payload).
- **Seeded reference data** at `tools/apd_gauntlet/data/`: 969 CWEs (live-fetched v4.20), 30 OWASP categories (3 lists × 10, seed-only), 149 D3FEND techniques with 3234 counter relations (live-fetched).
- **`apd-control-mappings` skill** gains per-taxonomy discipline sections (CWE, OWASP Top 10 web/API/LLM, D3FEND).
- **`apd-intake` agent** gains taxonomy auto-detection step.
- **`apd-synthesizer` agent** documents the three new rollup outputs.
- **All 9 specialist agents** reference the v1.2 taxonomy scope.
- **`init-run --taxonomies`** CLI flag pre-populates the run-config.
- **Cross-reference validation**: D3FEND `counters_attack` must intersect the capability's `mitre_attack[].technique` list (with sub-technique parent matching).
- **ADR 0008** — Multi-framework taxonomy mappings.
- **`docs/taxonomy-mappings.md`** operator guide.

### Changed

- `finding.schema.json` — `control_mappings` accepts optional `cwe`, `owasp_top10`, `owasp_api_top10`, `owasp_llm_top10` arrays.
- `capability.schema.json` — `control_mappings` accepts optional `mitre_attack` (parallel to finding's) and `d3fend` arrays.
- `run-config.schema.json` — accepts optional `taxonomies` array.
- D3FEND ID pattern widened from `^D3-[A-Z]{2,5}$` to `^D3-[A-Z]{2,7}$` (real MITRE D3FEND data contains 6- and 7-letter codes like `D3-PHDURA`, `D3-DNSTA`).
- `docs/architecture.md`, `docs/running-the-gauntlet.md`, `docs/schema-evolution.md`, `README.md` — refreshed for v1.2 additions.

### Backward compatibility

- All schema changes additive. v1.1-format runs validate unchanged against v1.2 schemas.
- Minimum-viable run with no `taxonomies:` declaration produces identical output to v1.1.
- PBM domain pack (`framework_compat: ">=1.0.0,<2.0.0"`) consumes v1.2.0 with no changes.

## [1.1.0] - 2026-05-XX

### Added

- Optional `apd-code-recon` intake-tier agent that uses the DeusData [codebase-memory-mcp](https://github.com/DeusData/codebase-memory-mcp) graph to produce a code-grounded view of the system under review. Gated by `code_recon` setting in `.apd-run.yaml` (`enabled` / `auto` / `disabled`). See [ADR 0007](docs/adrs/0007-optional-code-reconnaissance-via-cbm.md).
- New schemas: `schemas/run-config.schema.json` (validates `.apd-run.yaml`) and `schemas/code-evidence-index.schema.json` (validates the code-evidence index).
- New template: `templates/code-architecture-brief.template.md`.
- CLI: `apd-gauntlet validate-run-config <path>` for operator parity with `validate-domain`.
- Validator now schema-validates `00-context/code-evidence-index.yaml` when present and treats it as a known artifact source for specialist evidence pointers.

### Changed

- `scaffold_run` emits `code_recon: auto` and `framework_version: 1.1.0` in the generated `.apd-run.yaml`.
- `apd-evidence-discipline` skill documents code-evidence pointer format and restates the input-trust boundary for CBM-returned content.
- `apd-orchestrator` agent gains a conditional Phase 1.5 dispatching `apd-code-recon`.

### Compatibility

- Backwards-compatible with v1.0 run directories: runs without a `.apd-run.yaml` skip Phase 1.5 entirely.
- Domain packs declaring `framework_compat: ">=1.0.0,<2.0.0"` (e.g. PBM) continue to work unchanged.

## [1.0.0] - 2026-05-XX

First public release.

### Added

- Twelve agents (orchestrator, intake, synthesizer, nine specialists) for APD security architecture reviews.
- Five skills providing framework discipline, schemas, evidence rules, control mappings, and (generated) domain content.
- JSON Schemas for finding, capability, contradiction, severity-disagreement, coverage-matrix, NIST coverage, ATT&CK exposure, and domain pack records.
- `apd-gauntlet` Python CLI with `validate`, `init-run`, `build-domain-skill`, `summarize`, `lint-agents`, `check-ids`, `validate-domain`, and `refresh-mitre` subcommands.
- Pluggable domain pack mechanism with PBM (Pharmacy Benefit Management) shipped as the first pack.
- Curated synthetic claim-event-bus example with CI-validated expected outputs.
- Claude Code plugin manifest.
- CI workflows for validation, Python tests, markdown lint, and release.
