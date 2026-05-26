# ADR-0007: Optional code reconnaissance via codebase-memory-mcp

**Status:** Accepted
**Date:** 2026-05-25

## Context

APD specialists in v1.0 cite evidence from documents under `inputs/`: tech plans, PRDs, threat models, ADRs, IaC, and code files. When the artifact set includes source code, specialists must either treat each file as a document (cumbersome for codebases of thousands of files) or fall back to "the tech plan says X" — which is design intent, not runtime reality.

The end-to-end security review of v1.0 surfaced this as the highest-leverage gap for findings whose lens depends on call-graph behavior — Non-Repudiation (does every consequential write hit the audit emitter?), Authenticity (does every entry point pass through identity verification?), Integrity (do all write paths validate inputs?), and Distributed/Resilient (what are the outbound edges, and do they share retry/timeout policy?).

## Decision

Add an **optional** intake-tier agent, `apd-code-recon`, that uses the DeusData [codebase-memory-mcp](https://github.com/DeusData/codebase-memory-mcp) (CBM) graph to produce a code-grounded view. The agent emits two artifacts under `00-context/`:

1. `code-architecture-brief.md` — narrative for human reviewers.
2. `code-evidence-index.yaml` — machine-readable index that specialists cite via `evidence[].artifact: code-evidence-index.yaml`.

Activation is gated by `code_recon` in `.apd-run.yaml`:

- `enabled` — hard-fail if CBM not reachable.
- `auto` (default) — skip with a note if CBM not reachable.
- `disabled` — never dispatch.

The validator recognizes `code-evidence-index.yaml` as a known artifact source automatically when present, so no specialist needs to know whether CBM ran.

## Consequences

**Positive:**

- Findings citing call-graph reality become possible without making every specialist CBM-aware.
- Code evidence counts as non-tech-plan evidence, so capabilities can validly reach `maturity: implemented`.
- Bifurcation between CBM-enabled and CBM-disabled runs is contained to the brief header, which records `code_recon: enabled|auto|disabled` and the indexed commit SHA.

**Negative:**

- Adds an external soft-dependency. Operators who want code-grounded reviews must provision a CBM server (documented in `docs/running-the-gauntlet.md`).
- Advisory output quality bifurcates: CBM-enabled runs produce richer evidence than CBM-disabled runs. Mitigated by surfacing the `code_recon` state in the synthesizer's run header.
- Per-specialist code-introspection patterns (e.g., "Authenticity always traces inbound from entry points") are out of scope for v1.1. Specialists treat code-evidence-index entries as opaque artifact-evidence pointers in this release; a future v1.2 skill (`apd-code-introspection`) is the natural follow-up.

**Trust posture:**

- CBM-returned content is artifact data under the same input-trust-boundary rule as text under `inputs/`. The `apd-evidence-discipline` skill restates this explicitly in the new "Code-evidence pointers" subsection.
- The recon agent's tool allowlist excludes `Bash`, `Edit`, `WebFetch`, `WebSearch`, and `Agent`; it can only `Read`/`Glob`/`Grep`/`Write` plus the seven CBM MCP tools. Prompt injection in indexed source code cannot escalate to network or subprocess access.

## Alternatives considered

**A. Make CBM a required runtime dependency.** Rejected: forces every operator to provision CBM, including users running the gauntlet against tech-plan-only artifact sets.

**B. Make every specialist CBM-aware.** Rejected for v1.1: duplicates code-query logic across the nine lenses, and the per-lens patterns aren't fleshed out yet. Deferred to v1.2 as `apd-code-introspection` skill.

**C. Both A and B.** Rejected for v1.0 reasons above.
