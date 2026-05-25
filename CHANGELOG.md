# Changelog

All notable changes to this project will be documented in this file. Format based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versioning per [SemVer](https://semver.org/).

## [Unreleased]

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
