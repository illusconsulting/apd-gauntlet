---
name: apd-c4-discipline
description: Required discipline for the code_recon agent when authoring 00-context/c4-recon.yaml (the grounded C4 architecture view). Covers never-invent rules for containers/components and containment (parent) + uses edges, the machine_extracted-vs-hand_read flag, the L3-block-by-default rule, the confidence floor on render, the diagram-size cap, and the not_analyzed-vs-zero-findings honesty rule. Required reading before emitting any container, component, or uses edge.
---

# APD C4 Discipline

The C4 architecture view in the report renders a System / Container / Component /
Code model built from per-run YAML. It looks authoritative — boxes, arrows, badge
counts — so it is only useful if every box and arrow is grounded in an artifact or
a code-evidence citation. An invented container or a guessed "uses" arrow is worse
than an omitted one: it manufactures false structure that engineers and auditors
will trust. Block, do not guess.

Field ownership follows ADR-0020: **you (the agent) emit grounded content BY NAME
only** — container names, component names, edge endpoints by name, labels. You
NEVER mint a `c4-XXXXXXXX` / `c4e-XXXXXXXX` id and you NEVER write a badge count.
The deterministic assembler (`assemble_c4`) is the sole minter of ids and the sole
author of `finding_count` / `capability_count` rollups. If you find yourself
writing an id or a count, stop — that is not your job.

## Hard rules

### 1. Never invent containers or components

Every entry in `containers[]` and `components[]` of `c4-recon.yaml` must cite one
of:

- A code-evidence-index entry whose anchors live in that repo/service
  (`provenance.source: code_evidence`)
- An architecture artifact that names the service/module
  (`provenance.source: artifact`, e.g. `code-architecture-brief.md`)

If a container has no code anchors and no artifact names it, it does not belong in
the model. Do not add a container because "a system like this usually has one."
A repo that was declared but has zero code anchors is still a real container — emit
it with `analysis_state: not_analyzed` (see rule 6), never omit it silently and
never invent its internals.

### 2. Never invent containment (parent) or uses edges

Containment is a node's parent pointer, not an edge: there is no `contains` edge
type in the model. A code node's parent container and a component's parent are
mechanical — they come from the code-evidence-index `c4_container` /
`c4_component` tags, never from judgment. The only edge type the model emits is
`uses`. A `uses_edges[]` entry must cite one of exactly two grounded sources, and
you MUST record which with the `machine_extracted` boolean:

- `machine_extracted: true` — the edge is derived from a CROSS_* code edge
  (`CROSS_HTTP_CALLS` / `CROSS_ASYNC_CALLS` / `CROSS_CHANNEL`) produced by the
  cross-repo index pass. `provenance.locator` points at that edge.
- `machine_extracted: false` — the edge is **hand_read** from code you actually
  read. `provenance.locator` MUST be a concrete `file_path:Lstart-Lend` you can
  point a reviewer at. "The architecture diagram implies A talks to B" is not a
  hand_read edge; cite the call site or do not emit the edge.

Never emit a self-edge (`from == to`) and never emit an edge whose endpoints are
not both present in `containers[]`. If you cannot ground both the existence and the
direction of an edge, drop it.

### 3. L3 component grouping is blocked by default

`components[]` is **empty unless an artifact explicitly groups symbols into a named
component.** There is no heuristic clustering of functions into components — that is
exactly the kind of invented structure this discipline forbids. The default and
expected output is an empty `components[]`, which makes the assembler render the
model as Container -> Code directly (L2 -> L4), skipping L3. Only when a real
artifact (a module map, a documented component decomposition) names a component AND
assigns symbols to it do you emit a `components[]` entry; otherwise leave the code
anchor's `c4_component` null and let the assembler render it under its container.

### 4. Confidence floor on render

A `uses_edges[]` entry is only as trustworthy as its weakest grounding. A
`machine_extracted: false` (hand_read) edge whose locator is a whole-file reference
with no line range, or whose direction you inferred rather than read, MUST be
dropped rather than emitted at the same standing as a CROSS_*-derived edge. When in
doubt between emitting a weak edge and omitting it, omit it: a missing arrow reads
as "not established," an invented arrow reads as "established," and only one of
those is honest. Do not annotate a guess with a hedge and ship it anyway.

### 5. Diagram-size cap

The rendered C4 scene must stay legible. A single rendered level (the set of nodes
visible at once — L1+L2 on load, or one container's expanded L3/L4) targets ≤ 50
nodes, mirroring the attack-path Mermaid cap. If a container genuinely has more
than ~50 grounded code anchors, that is a signal to rely on the click-to-expand
interaction (the scene reveals a container's code on demand) rather than to drop
real anchors — never silently truncate grounded evidence to hit the cap, and never
pad to fill it.

### 6. not_analyzed is not zero findings

A container with `analysis_state: not_analyzed` (a declared repo with zero code
anchors — 14 of the 23 Home Assistant repos are exactly this) MUST render as
"not analyzed," NEVER as "0 findings = clean." Zero badges on a not_analyzed
container means *we did not look here*, not *here is safe*. Set `analysis_state:
not_analyzed` on those containers and let the assembler/report present them
honestly. Separately, a doc-anchored finding that has no `code:` locator is real
but unlocalized — it is surfaced as the model's explicit unlocalized count, never
silently dropped onto (or away from) a node.

## Tier ordering

`c4-recon.yaml` is authored during code reconnaissance (it is `generated_by:
code_recon`), alongside / after the code-evidence-index it cites. It is read-only
input to the deterministic `assemble_c4` step, which mints `c4-*` node ids, `c4e-*`
edge ids, and the `finding_count` / `capability_count` badges in
`40-synthesis/c4-model.yaml`. You never write that canonical file and never write
those ids or counts.

## Out of scope (delegated)

- Badge counts are derived by the assembler from deduped findings/capabilities
  joined on the code locator — do not pre-count them.
- Severity, finding content, and capability maturity are owned by the specialist
  lenses and the synthesizer; the C4 view only *references* their counts.
- The L4 code-node inventory and the per-entry `c4_container` / `c4_component` /
  `c4_level` tags on the code-evidence-index are mechanical/grounded — copy them
  from the index, do not re-derive structure from them.
