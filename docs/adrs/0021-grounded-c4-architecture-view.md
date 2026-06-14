# ADR-0021: Grounded C4 architecture view from code reconnaissance

**Status:** Accepted
**Date:** 2026-06-13

> ADR-0016 and -0018 are reserved for concurrent in-flight design changes and
> may land after this one.

## Context

The APD gauntlet produces a self-contained, offline HTML report. It already
renders an asset graph and per-finding attack-path strips, but it has no
architecture view: a reader cannot see the system as a structured set of
containers and components, cannot see where the findings and capabilities land
in that structure, and cannot drill from "the system" down to "this function."
Engineers and auditors reason about systems in C4 terms (System Context →
Container → Component → Code); the report should meet them there.

Two feasibility questions framed the decision:

1. **Where does the structure come from?** The gauntlet has no live code graph at
   view time — the report is a static bundle built by a Python pipeline from
   per-run YAML. The only grounded sources of structure are the code-evidence
   index (ADR-0007, multi-repo per ADR-0019) and hand-read code evidence with a
   `file_path`. A *feasibility analysis* against the real Home Assistant run
   confirmed this is enough for L1/L2/L4: 9 of 23 repos carry code anchors
   (40 code anchors total), plus 6 hand-read `kind: edge` cross-boundary
   entries (the cross-repo auto-linker found **zero** CROSS_* edges, so all six
   were read by hand), of which 5 resolve to container `uses` edges — the sixth
   points at a host socket (`/run/docker.sock`) rather than a repo container and
   is dropped. The asset graph already names the system and its data stores. It
   also confirmed the honest
   limit: 14 of 23 repos have **zero** code anchors, so any view must distinguish
   "analyzed, no findings" from "not analyzed." L3 (Component) has **no** grounded
   source unless an artifact explicitly groups symbols — the index gives us
   symbols and their container, not a defensible component decomposition.

2. **Build or adopt an extractor?** A *build-vs-adopt analysis* weighed pulling in
   a third-party C4/architecture extractor (e.g. a Structurizr-style DSL importer
   or a static-analysis architecture-recovery tool) against composing the view
   from data we already produce. Adopting an extractor would (a) introduce a live
   code-analysis dependency at build time, breaking the offline/static contract,
   (b) produce structure not traceable to a citable artifact, violating the
   never-invent discipline, and (c) add a heavy dependency for a view whose
   inputs the gauntlet already computes.

## Decision

Build a **grounded** C4 view from data the gauntlet already produces, reusing the
report's existing graph renderer, and adopting no third-party extractor.

**Grounded from code reconnaissance + a deterministic assembler.** The
`code_recon` agent authors a content-only `00-context/c4-recon.yaml` (containers,
optional components, `uses_edges`) where every entry cites an artifact or a
code-evidence locator, and every edge carries a `machine_extracted` (CROSS_*
edge) vs hand_read (`file_path`) flag. Per ADR-0020, the agent emits names only;
the deterministic `assemble_c4` step is the sole minter of the `c4-*` node ids,
`c4e-*` edge ids, and the `finding_count` / `capability_count` badge rollups in
the canonical `40-synthesis/c4-model.yaml`. No invented value at agent or render
time. The `apd-c4-discipline` skill is required reading before the agent emits any
container, component, or edge.

**L3-block-by-default.** Components are emitted ONLY when an artifact explicitly
groups symbols into a named component. With no such artifact — the common case —
`components[]` is empty and the model renders Container → Code directly (L2 → L4),
skipping L3 entirely. There is no heuristic clustering of functions into
components; that would manufacture exactly the kind of invented structure this
feature exists to avoid.

**Honesty about coverage.** Containers backed by a declared-but-empty repo render
`analysis_state: not_analyzed` — never "0 findings = clean." Doc-anchored findings
with no code locator are surfaced as an explicit unlocalized count in the model's
`build_summary`, never silently dropped.

**Reuse Cytoscape; adopt nothing.** The view reuses the report's existing
compound-capable Cytoscape `GraphView` (the same fcose/compound renderer used by
the asset graph), with a new C4 scene that shows L1+L2 on load and reveals L3/L4
on click. No new graph library, no third-party extractor, no build-time code
analysis is introduced — the offline/static contract (ADR-0007's no-network
posture) is preserved.

**Gating.** `assemble_c4` runs whenever `40-synthesis/asset-graph.yaml` exists; it
includes the code tiers (L4 code, and any L3 components) ONLY when
`00-context/code-evidence-index.yaml` exists. The C4 scene renders whatever
`c4-model.yaml` contains and is shown only when that model is present. The feature
is therefore effectively `code_recon`-gated for the code tiers and additive
everywhere else.

## Consequences

**Positive:**

- The report gains a structured, drill-down architecture view whose every box and
  arrow is traceable to a citation — the same trustworthiness bar as findings.
- Reusing the existing Cytoscape renderer keeps the bundle offline and adds no new
  runtime dependency; adopting no extractor keeps the build deterministic.
- The not_analyzed and unlocalized-count rules make the gauntlet's coverage gaps
  *visible* rather than papering over them with a falsely clean diagram.
- Every change is additive: schemas are optional and presence-gated, so single-repo
  and no-code-recon runs are unaffected.

**Negative:**

- L3 is usually absent (block-by-default), so most runs render L2 → L4 with a
  "components not decomposed" character. This is intentional honesty, but readers
  expecting a full four-level C4 may find L3 sparse.
- The view's fidelity is bounded by code-recon coverage: in a run where most repos
  are not_analyzed, the architecture view is mostly not_analyzed containers. The
  honesty rules make that boundary explicit rather than hiding it.

## Alternatives considered

**A. Adopt a third-party C4/architecture extractor.** Rejected: it would require
live code analysis at build time (breaking the offline/static contract), produce
structure not traceable to a citable artifact (violating never-invent), and add a
heavy dependency for inputs the gauntlet already computes.

**B. Heuristically cluster code symbols into L3 components.** Rejected: function
co-location or call-graph clustering is not a defensible, citable component
decomposition. It would manufacture invented structure — exactly what this feature
forbids. L3 is blocked by default and emitted only from an explicit artifact.

**C. Render not_analyzed containers as "0 findings."** Rejected as actively
misleading: a declared repo with no code anchors was not examined, not found
clean. The model distinguishes the two via `analysis_state`.

**D. Introduce a new graph library for the C4 scene.** Rejected: the existing
compound-capable Cytoscape `GraphView` already supports parented/compound nodes
and an fcose layout, so a second library would add bundle weight for no capability
the renderer lacks.
