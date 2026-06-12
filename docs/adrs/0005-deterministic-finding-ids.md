# ADR-0005: Deterministic Finding and Capability IDs

> **Amended by [ADR-0020](0020-tooling-authored-derived-fields.md)** (2026-06-12): agents no longer author a best-effort `id`; the assembler (`apd-gauntlet canonicalize`) is the sole author. The ID algorithm described in this ADR is unchanged.

**Status:** Accepted (amended by ADR-0020)
**Date:** 2026-05-24

## Context

The gauntlet may be run multiple times against the same architecture as artifacts are added or updated. Without stable finding IDs, diffing two runs to see what changed is intractable — every finding appears as a deletion paired with an insertion, and deduplication requires expensive semantic comparison. CI gates that check "are there new Critical findings since last run?" cannot function without stable IDs.

Additionally, the synthesizer needs to cross-reference findings from multiple specialists to identify merges, links, and duplicates (ADR-0006). Cross-referencing requires stable addresses. Using display titles as references is fragile (titles change during editorial review); using positional indices is fragile (ordering can change).

The ID must be deterministic (same inputs produce same ID), stable across re-runs against unchanged artifacts, and short enough to embed in prose reports without disrupting readability.

## Decision

Finding and capability IDs are computed as:

```
<prefix>-<first-8-hex-of-SHA-256(title + "|" + first_evidence_locator)>
```

Where `prefix` is the specialist code (e.g. `CONF`, `INTG`, `AVAIL`, `DIST`, `RESL`, `EPHL`, `AUTH`, `NREP`, `IMUT`) and `first_evidence_locator` is the first entry in the `evidence` array's `locator` field. The synthesizer and validator both regenerate the expected ID from the record fields and verify it matches the emitted ID.

## Consequences

- IDs are stable across re-runs against unchanged artifacts, enabling diff and dedup workflows.
- Changing the finding title or moving the first evidence locator changes the ID — this is intentional: treat a renamed finding as a new finding, not the same finding edited.
- 8 hex characters (32 bits) provides adequate collision resistance for any realistic finding volume; collisions would only appear at billions of findings per run.
- The validator's ID-check pass can detect LLM-emitted IDs that drift from the deterministic formula, catching copy-paste errors and hallucinated IDs.
- The ID does not encode severity or disposition, so those fields can be updated (e.g. during severity reconciliation) without changing the ID.

## Alternatives considered

- **UUIDs (v4)** — random; not stable across re-runs; a re-run against the same artifact set produces different IDs, making diff impossible.
- **Sequential numbering** — requires global state (a counter) that must be persisted and coordinated across agents; breaks in parallel specialist runs.
- **Content-hash of full record** — changes on any field edit, including severity reconciliation and editorial title changes; too volatile for use as a stable reference.
- **Human-assigned IDs** — requires a review step that slows the automated gauntlet pipeline and introduces inconsistency.
