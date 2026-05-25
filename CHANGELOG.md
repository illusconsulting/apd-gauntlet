# Changelog

All notable changes to this project will be documented in this file. Format based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versioning per [SemVer](https://semver.org/).

## [Unreleased]

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
