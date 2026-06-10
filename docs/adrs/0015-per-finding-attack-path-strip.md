# ADR-0015: Per-finding attack-path strip in the advisory report

**Status:** Accepted
**Date:** 2026-06-10
**Supersedes:** —
**Superseded by:** —

## Context

Attack-path (`apath-*`) findings rendered as prose only in the Findings tab; a
reader could not see the path, the vuln position, or where a defense applies.
The path data already existed (asset-graph / attack-paths / defense-graph) and
was drawn on the path-centric Attack Paths tab, but was not attached to the
individual finding.

## Decision

Embed a deterministic "hop-strip" in each `apath-*` **risk** finding's detail
card, derived at report-transform time from the synthesis YAML via the
`id == "apath-" + sha256(path_id)[:8]` join (no `finding.schema.json` change,
no agent/skill/LLM at build or render time). Markers are layered: an
`compromisable_via_finding`-edge vuln marker, a fix marker on the
highest-confidence such edge — the edge the per-path risk recommendation itself
names — and a D3FEND choke-point marker on bottleneck edges that carry a `defense-graph`
overlay (degrading to fix-only). Scope is strictly `disposition == "risk"`;
aggregate / per-path-uncertainty / gap findings keep prose-only rendering. A
reverse "view full graph" link focuses the Attack Paths tab. The completeness
check is editorial (non-blocking).

## Consequences

- No schema change; the linkage is recomputed deterministically and is
  byte-stable (guarded by a test), preserving the audit recompute-drift contract.
- The strip reuses the existing CSS token system (one new `--rec` token) and
  adds no runtime dependency (no Cytoscape for the per-finding view).
- Specialist (`conf-*`/`avail-*`) on-path context and an Attack-Paths-tab
  recommendation overlay are deliberately out of scope (future work).
