# ADR-0004: JSON Schema as the Canonical Validation Contract

**Status:** Accepted
**Date:** 2026-05-24

## Context

The gauntlet produces YAML records — findings, capabilities, contradictions, severity disagreements, coverage matrices — that are consumed by a Python synthesizer and by CI validation. LLMs emit these records, which means structural drift is a constant risk: a field might be missing, a required enum value might be misspelled, or a cross-reference might point to a non-existent ID. Without machine enforcement, the synthesizer would need defensive parsing code, and CI would need fragile ad-hoc checks.

The framework also uses these records as the primary artifact in ADR-0005's deterministic ID scheme and in the coverage matrix. If the record structure is ambiguous, both the ID generation and the coverage computation become unreliable. A machine-readable, language-neutral contract is needed.

JSON Schema is the de facto standard for validating JSON/YAML documents and is supported by validators in Python, JavaScript, and most CI environments. It is human-readable enough to serve as documentation and machine-readable enough to drive validation tooling.

## Decision

JSON Schema draft 2020-12 files at `schemas/*.schema.json` are the canonical contract for all gauntlet record types. The skill files describe the schemas in prose; the schemas enforce them. A Python validator (`apd-gauntlet validate`) runs three passes: structural schema validation, semantic lints (deterministic ID verification, excerpt length bounds, maturity-vs-evidence consistency), and cross-file referential integrity. Only the structural pass uses JSON Schema machinery; the semantic and cross-file passes are Python.

Schema files are versioned via a `schema_version` field. Breaking changes require a version bump per the policy in `docs/schema-evolution.md`.

## Consequences

- Structural validation is deterministic and does not require an LLM call to verify.
- LLM-emitted records are auditable — every field is either present and valid or the validator fails with a specific path and error message.
- Non-trivial lints (deterministic ID verification, excerpt length, maturity-vs-evidence) live in Python where they are testable, not in the schema where they would require complex `if/then` constructs.
- The schema files serve dual purpose as documentation and enforcement, but the prose in skill files remains the authoritative explanation.
- Schema evolution requires coordinated updates to skill files, schema files, and the validator, increasing the cost of field renames.

## Alternatives considered

- **Pure LLM validation** — nondeterministic; hard to test; a second LLM call to validate the first's output is expensive and unreliable for structural checks.
- **Pydantic models** — Python-coupled; the schema-as-documentation concern is harder to satisfy; external tool authors in other languages cannot use Pydantic models.
- **No validation** — attempted in early framework iterations; structural drift accumulated quickly and the synthesizer required extensive defensive code.
- **OpenAPI-style schemas** — heavier toolchain; JSON Schema draft 2020-12 is a proper subset of what OpenAPI 3.1 uses and is directly usable without an API server.
