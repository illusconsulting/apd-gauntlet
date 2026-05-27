# ADR-0010: Attack-Path Analysis on Partial Graphs

**Status:** Accepted
**Date:** 2026-05-26
**Supersedes:** —
**Superseded by:** —

## Context

APD Gauntlet v1.4 introduces an attack-path analyzer that walks an asset
graph from declared attacker positions to declared crown jewels and emits
ranked path findings with defensive guidance. The obvious mental model is
BloodHound, which enumerates ATT&CK-aligned attack paths across Active
Directory graphs. BloodHound is the right inspiration but the wrong
implementation contract for the gauntlet, for three reasons.

First, BloodHound builds its graph from authoritative AD APIs. The graph
is structurally complete (every relevant principal, group, ACL, and
session is enumerated) and its edges carry ground truth — `MemberOf` is
either present in AD or it isn't. The gauntlet has no equivalent
authoritative source. Its asset graph is constructed by specialist agents
from human-authored artifacts: architecture diagrams, threat models,
code-evidence indexes, intake briefs. Those artifacts are necessarily
partial. A diagram shows the relationships the author thought mattered, not
the full topology. A threat model enumerates the threats the author
considered. The intake brief catalogues the assets the operator chose to
declare.

Second, BloodHound's edges are operationally observable (a session exists
or doesn't; a Kerberos delegation is configured or isn't). The gauntlet's
edges are *interpreted* — a specialist reads an artifact and asserts that
asset A authenticates to asset B, or that service C runs as identity D.
The interpretation can be high-fidelity (the threat model literally says
so) or low-fidelity (the diagram implies it via co-location). Treating
all edges as ground-truth would inflate confidence in paths that depend on
fragile interpretations.

Third, BloodHound knows what its crown jewels are because AD knows what
its domain admins are. The gauntlet has no equivalent universal crown
jewel taxonomy. What counts as a crown jewel is domain-specific (PHI for
PBM, customer PII for fintech, signing keys for code-supply-chain) and
ultimately a scoping decision the operator owns — the same scoping
authority ADR-0008 codified for taxonomy selection.

These three differences mean a naive port of BloodHound's enumerate-from-
authoritative-graph approach would either (a) silently hide its
partial-graph nature behind confident-looking output, or (b) invent edges,
nodes, or crown jewels the operator's artifacts didn't contain. Either
failure mode contradicts the gauntlet's core block-on-ambiguity discipline
(ADR-0002).

## Decision

Adopt **BloodHound-style attack-path enumeration on partial graphs**, with
four discipline rules layered on top.

**1. Provenance and confidence on every node and edge.** The asset graph
schema (`asset-graph.schema.json`, Phase C-2) requires that every node and
every edge carry a `provenance` block (source agent, source artifact,
extraction confidence) and a numeric `confidence` value. Path scoring
multiplies along the edge sequence so that a path through low-confidence
edges produces a low-confidence path finding — visible to the operator,
not silently inflated to "this path exists." Where edge confidence falls
below the gauntlet's uncertainty floor, the path's finding disposition is
capped at `uncertainty` regardless of impact severity (per
`apd-attack-path-discipline` skill).

**2. Crown jewels must be declared. No guessing.** The analyzer's
activation contract requires at least one declared crown jewel in
`.apd-run.yaml`. If no crown jewel is declared, the analyzer emits a
single blocked finding (id prefix `apath-blocked-`) explaining that no
target was scoped, and does not enumerate. The gauntlet does *not* infer
crown jewels from data classifications, asset tags, or domain pack
taxonomy. Operator authority over scope is preserved by the same posture
ADR-0008 took for taxonomy scoping: auto-detect can *suggest*, only the
operator can *declare*.

**3. Bounded enumeration with honest output.** Enumeration is bounded by
two operator-tunable parameters (`max_hops`, `max_paths_per_jewel`) with
sensible defaults (4 and 10 respectively). The output explicitly frames
results as "the top-N highest-confidence paths under K hops," not "all
attack paths." Paths discovered above the cap are summarized in a
truncation note. This matches the framing BloodHound's analytics already
use ("Top 10 Most Privileged Users") and prevents operators from reading
the path list as exhaustive.

**4. D3FEND overlay on bottleneck edges.** For each enumerated path the
analyzer identifies the *bottleneck edge* (the edge whose removal would
break the largest number of remaining paths to the same crown jewel) and
attaches the D3FEND techniques that counter the ATT&CK technique
annotating that edge. The bottleneck-edge concept gives operators a
single, ranked place to invest defensive effort. D3FEND overlay reuses
the `counters_attack` cross-reference rule from ADR-0008: every D3FEND
mapping must cite the ATT&CK technique it counters, and that technique
must annotate the bottleneck edge in question.

**Path enumeration is deterministic graph traversal.** The enumeration
algorithm itself is plain BFS over the typed asset graph — no LLM in the
hot path. The LLM contribution is upstream: specialists author the nodes
and edges (with provenance and confidence) from artifact evidence during
their normal lens-driven analysis. By the time the analyzer runs, the
graph is fully materialized as data. This keeps path output reproducible,
testable, and free of the "the LLM invented a step" failure mode that
plagues LLM-driven attack-path generation.

## Consequences

- The analyzer ships behind an activation gate (`attack_path:` block in
  `.apd-run.yaml` or per-domain-pack default). v1.1-style runs with no
  attack-path declaration produce identical output to v1.3 — no
  regression risk for existing operators.
- Path findings are honest about uncertainty. Where the chain of edges
  contains low-confidence interpretations, the finding disposition is
  capped at `uncertainty`. Operators see the path *and* see that the
  gauntlet is not asserting it as ground truth.
- Operators get actionable D3FEND guidance keyed to the bottleneck-edge
  concept — a single defensive investment that breaks multiple paths is
  more useful than a long catalog of per-edge mitigations.
- D3FEND reference data refresh cadence applies. The analyzer reuses the
  D3FEND reference data introduced in ADR-0008 (`tools/apd_gauntlet/data/
  d3fend.json`) and the same quarterly `apd-gauntlet refresh-d3fend`
  cadence documented there.
- Crown-jewel declaration becomes a first-class gating concern. Operators
  who run the analyzer without declaring a crown jewel see a blocked
  finding, not an empty enumeration. This is intentional: silently empty
  output is worse than an explicit "you didn't tell me what to find."
- The bounded-enumeration framing requires every operator-facing artifact
  (CLI summary, synthesis rollup, operator doc at
  `docs/attack-path-analysis.md`) to use the "top-N under K hops" wording
  rather than "all paths." Drift on this framing would re-introduce the
  exhaustive-implication failure mode.
- The asset graph becomes a reusable substrate. Other tier-3+ specialists
  can consume the same graph for cross-lens reasoning (e.g.,
  authentication-flow analysis, blast-radius estimation in future
  phases) without re-deriving the topology.

## Alternatives considered

### Graph database backing (Neo4j / Memgraph)

**Rejected.** BloodHound's reference implementation uses Neo4j because AD
graphs at enterprise scale exceed comfortable in-memory limits. The
gauntlet operates on partial, human-authored graphs at bounded sizes —
typical runs are well under 1000 nodes. An in-memory graph (the Phase C
`Graph` primitive) is sufficient, has zero deployment overhead, and keeps
the gauntlet runnable as a single Python process. A graph-DB backing
would add operational complexity (a separate service to run, version, and
secure) for a scale problem we don't have.

### LLM-driven path inference

**Rejected.** Asking an LLM "given this graph, what attack paths exist?"
is exactly the failure mode the gauntlet's evidence discipline is built
to prevent. LLMs invent plausible-looking paths under enumeration
pressure — fabricated intermediate steps, hallucinated edge labels,
confident assertions that an unsupported attack technique applies. Plain
BFS over typed edges is deterministic, testable, and audit-friendly.
Specialists already contribute LLM judgment at the right layer — authoring
edge provenance and ATT&CK annotations from artifact evidence — where the
LLM's strength (semantic interpretation of human prose) is the relevant
capability. The path traversal itself should not be an LLM task.

### Crown-jewel guessing from data classifications

**Rejected.** A naive heuristic ("any asset tagged `pii` is a crown
jewel") would let the analyzer enumerate without requiring an explicit
operator declaration, at the cost of two failure modes: (1) the heuristic
will sometimes promote assets the operator did not consider crown-jewel-
worthy in this run, producing irrelevant findings; (2) the heuristic will
sometimes miss assets the operator *does* consider crown jewels (a
custom-tagged signing oracle, a regulatory-sensitive batch job) because
no general tag taxonomy catches every domain. Operator authority over
scope is the same design principle ADR-0008 invoked for taxonomy
selection: auto-detect can suggest (intake's `crown_jewel_suggestions:`
block in the context brief), but only operator declaration is binding.
This preserves the gauntlet's reviewer-not-author posture and keeps the
output relevant to the operator's actual concerns.
