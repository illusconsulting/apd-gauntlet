# ADR-0011: Report Completeness Gate — Block on Degraded HTML Reports

**Status:** Accepted
**Date:** 2026-06-03
**Supersedes:** —
**Superseded by:** —

## Context

The HTML report builder (`build_apd_data`) uses per-section isolation: when a
section fails, a placeholder is recorded in `meta.section_errors` and the build
still exits 0. It also falls back to a placeholder executive summary when
`report-data.yaml` is absent. The result is that `build-report` can exit 0
while shipping a degraded report — a placeholder exec summary, finding counts
that do not match the deduped corpus, empty attack-paths or D3FEND overlays —
and nothing gated on it.

The existing `audit-report` checker already performs semantic-faithfulness
auditing: it cross-checks the built `data.js` against the authoritative YAMLs.
That checker exits with a status that the workflow's synthesis-audit loop
already reads. Structural completeness — whether the report contains all
required sections and data — is a deterministic concern, not a judgment call,
and the existing checker is the correct home for it.

A constraint shapes the loop-control design: the workflow JavaScript has no
filesystem access and the agent-receipt counts contract is closed, so the loop
branches on `audit.status` only. There is no per-class short-circuit mechanism
available at the workflow layer.

## Decision

Extend the **existing deterministic `audit-report` checker** with completeness
checks rather than introduce a new command or a new gate primitive.

Eight checks are defined, classified by `klass`:

| Check | klass |
|---|---|
| `exec_summary_present` | editorial |
| `editorial_sections_present` | editorial |
| `attack_paths_present` | structural |
| `d3fend_overlay_present` | structural |
| `apd_matrix_nonempty` | structural |
| `coverage_rollups_nonempty` | structural |
| `taxonomy_titles_resolve` | structural |
| `section_errors_empty` | structural |

Each check exempts legitimately-empty states (for example,
`attack_paths_present` passes if the run declared no crown jewels; a run with
no ATLAS taxonomy is exempt from `taxonomy_titles_resolve` for that family).

**Blocking behavior.** The workflow's synthesis-audit loop blocks the run
(throws) when a structural completeness failure is unresolved after the N=2
remediation cap. Editorial gaps do not block: the report-writer reads
`report-audit.yaml` and self-heals editorial shortcomings without
re-triggering the full remediation loop.

**LLM auditing stays non-blocking.** The LLM report-auditor's
semantic-faithfulness residual judgment does not block the run. Deterministic
structural completeness blocks; LLM editorial judgment does not. This preserves
the distinction between machine-verifiable invariants and advisory quality
checks.

**`report-audit.yaml` gains a `klass` field** on each per-check result so
downstream readers (the report-writer, CI tooling) can distinguish structural
from editorial findings without re-implementing the classification.

**Build artifact policy.** `report-html` for `runs/` directories is a
gitignored build artifact. Tests must build the report before auditing it; the
audit cannot read `data.js` from a prior uncommitted build.

## Alternatives considered

### New `check-report-completeness` command

**Rejected.** Adding a standalone command would duplicate the checker's
cross-validation logic (which must already walk the authoritative YAMLs),
introduce a second exit-code contract for the workflow to read, and widen the
set of CLI verbs operators need to understand. Extending the existing checker
keeps one exit-code contract and one command.

### Per-class loop short-circuit

**Rejected.** The workflow JS has no filesystem access and the agent-receipt
counts contract is closed. A per-class short-circuit would require either a
filesystem read in the workflow layer (unavailable) or a second status field
in `audit.status` (widening the contract). Blocking unconditionally on any
unresolved structural failure after the remediation cap is the simplest rule
expressible within the existing contract.

### LLM-audited completeness

**Rejected.** Completeness checks are binary and deterministic — either
`data.js` contains an attack-paths array or it does not. Asking an LLM to
judge structural completeness would introduce non-determinism into a
machine-verifiable invariant and would risk the same per-run judgment variance
that the deterministic checker was designed to eliminate.

## Consequences

- A completed run guarantees a structurally complete report: exec summary
  present, APD matrix populated, coverage rollups non-empty, taxonomy titles
  resolved, no silenced section errors.
- `report-audit.yaml` gains a per-check `klass` field (`structural` |
  `editorial`). Existing consumers that ignore unknown fields are unaffected;
  consumers that enumerate check results gain the classification for free.
- Runs with a structural completeness failure may incur extra remediation
  cycles before hitting the N=2 cap and blocking. Operators see the block as
  an explicit failure rather than a silently degraded report.
- The `report-html` gitignore policy means CI test suites must invoke
  `build-report` before `audit-report`. Test ordering is now a documented
  invariant.
- Editorial gaps (missing exec summary prose, missing editorial section text)
  self-heal via the report-writer reading `report-audit.yaml`, with no
  additional loop iteration required for structural re-audit.
