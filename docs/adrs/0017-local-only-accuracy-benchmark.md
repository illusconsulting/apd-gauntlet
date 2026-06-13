# ADR-0017: Local-only accuracy benchmark, CI structural gates only

**Status:** Accepted
**Date:** 2026-06-10
**Supersedes:** —
**Superseded by:** —

## Context

The report-accuracy/UX remediation program needs a Definition of Done that
measures real accuracy gains (false-uncertainty promotion, redundancy collapsed,
chokepoint surfacing). Those gains are only observable on a real gauntlet run.
`runs/` is gitignored by policy because a run "may contain a sensitive security
review — never commit them" (`.gitignore`). Gating CI on a real run is therefore
unexecutable for anyone but the maintainer, and committing a real run to satisfy
CI would publish a sensitive review and leak real-subject data.

## Decision

Split the Definition of Done into two tracks (see
[CI gate model](../ci-gate-model.md)):

1. **CI-enforceable** gates run for everyone against **hand-authored synthetic
   fixtures only** (`examples/*/expected/`, `tests/fixtures/`). They check
   structure, schema, byte-stability, and provenance — never holistic accuracy.
2. **Holistic accuracy is measured locally and stays fully out-of-band.** The
   maintainer reads `40-synthesis/metrics.yaml` from their own gitignored run,
   records a baseline `B0` in private notes outside the repository, and judges
   deltas against it. **No run-derived data — not the run, not the report, not
   even a bare count, not `B0` itself — is ever committed.**

The framework version stays at 1.7.0; this is a process/measurement decision,
not a schema change.

## Consequences

- CI stays fast, deterministic, and shareable; it never depends on a real run.
- Accuracy claims are honest but not machine-verifiable in CI by design; they are
  the maintainer's locally-recorded judgment.
- Every workstream's "Acceptance" section is split into CI-enforceable and local
  rows that point here.
- The committed synthetic fixtures must be maintained as the sole CI basis; if a
  workstream needs a new structural assertion, it adds a synthetic fixture, never
  a captured run.
