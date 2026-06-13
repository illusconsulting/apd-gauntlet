# ADR-0019: Multi-repo code reconnaissance and the THIS-repo / upstream-CBM boundary

**Status:** Accepted
**Date:** 2026-06-10

> ADR numbers 0016–0018 are reserved for concurrent in-flight design changes and
> may land after this one.

## Context

Code reconnaissance (ADR-0007) is single-repo by construction:
`run-config.schema.json` carries one `cbm_project` string,
`code-evidence-index.schema.json` records one `cbm_project` + one
`indexed_commit_sha`, and `apd-code-recon` called `index_status` without a
`project` argument (which the real CBM tool requires). Real systems are
frequently polyglot — an API service, an async worker, a frontend — each its
own CBM project, with security-relevant control flow that crosses service
boundaries. A single-repo run picks one repo and loses every cross-service
edge, so an attack path that reaches a crown jewel via a cross-repo hop is
invisible. Separately, a CBM provider-discovery defect can leave only a subset
of extraction providers registered (observed as "1/6 providers indexed"),
yielding a partial index that produces confidently-wrong conclusions with no
early signal.

## Decision

Add multi-repo support **additively**, splitting cleanly along the THIS-repo /
upstream boundary. The framework version is held at 1.7.0; all schema changes
are optional and recorded as a dated 1.7.0 entry in `docs/schema-evolution.md`.

**THIS repo (config / schema / agent / docs):**

- `run-config.schema.json` gains an optional `repos[]` array
  (`{cbm_project (required), role?, repo_path?}`). `cbm_project` (singular)
  stays valid for single-repo back-compat; the two are not mutually exclusive.
- `code-evidence-index.schema.json` gains an optional top-level `repos[]`
  provenance array and an optional per-entry `repo`, with an if/then requiring
  `repo` on every entry when top-level `repos[]` is present. Existing
  single-repo indexes stay valid.
- `apd-code-recon` calls `index_status` with `project:` (fixing the
  project-less call), runs per-repo passes tagging entries with `repo:`, and
  **requests** CBM's already-existing
  `index_repository(mode='cross-repo-intelligence', target_projects=[...])`,
  consuming `CROSS_HTTP_CALLS` / `CROSS_ASYNC_CALLS` / `CROSS_CHANNEL` edges as
  `kind: edge` entries. `index_repository` is added to the agent's tool
  allowlist, guarded by an operator-consent note: it is requested **only** when
  the run declares `repos[]`. The grant still excludes `Bash`, `Edit`,
  `WebFetch`, `WebSearch`, and `Agent`, so ADR-0007's no-escalation posture
  holds.
- `validate.py` emits a **non-blocking warning** when a declared repo has zero
  attributed entries (the partial-index signal). A partial index is still
  usable, so this is a warning, never an error.
- The report prefers an explicit `subject:` for multi-repo titles, falling
  back to the `role: primary` repo (else the first).

**Upstream CBM (NOT patchable here — file and track only):**

- The provider-discovery / annotation-registration fix that makes all
  extraction providers register (1/6 → 6/6). This repo can only detect the
  partial result, surface it (the validate warning + the docs caveat box),
  file the upstream issue, and **pin a minimum CBM version once the fix ships**.
- The cross-repo graph primitive (`index_repository` cross-repo-intelligence
  mode) already exists upstream and needs only to be requested — no CBM-side
  schema change.

## Consequences

**Positive:**

- Polyglot systems are declared once; cross-service edges become first-class
  evidence and attack paths can traverse cross-repo hops.
- A previously-silent partial index becomes an explicit, early, non-blocking
  signal.
- Every change is additive: single-repo runs and `framework_compat
  ">=1.0.0,<2.0.0"` packs are unaffected.

**Negative:**

- `apd-code-recon` gains one heavier CBM call (`index_repository`), gated to
  multi-repo runs only and behind the operator-consent note.
- Cross-repo evidence quality is bounded by the upstream provider-discovery
  defect until that fix lands; the validate warning makes that boundary visible
  rather than hiding it.

## Alternatives considered

**A. One polyglot CBM project instead of `repos[]`.** Rejected: conflates
distinct services, loses per-repo provenance, and does not produce the typed
cross-repo edges the attack-path analyzer needs.

**B. Make the partial-index signal a hard error.** Rejected: a partial index is
still usable evidence; blocking the run on it would be worse than surfacing it.

**C. Patch provider discovery here.** Not possible — it is upstream CBM code.
We detect, surface, and track it instead.
