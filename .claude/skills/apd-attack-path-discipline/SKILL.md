---
name: apd-attack-path-discipline
description: Required discipline for the apd-attack-path-analyzer agent. Covers never-invent rules for nodes and edges, confidence floors severity rule, bounded-enumeration discipline, block-on-missing-crown-jewels rule, D3FEND-must-counter-ATT&CK mapping rule, and Mermaid diagram constraints. Required reading before emitting any apath-* finding or asset-graph node/edge.
---

# APD Attack-Path Discipline

The attack-path analyzer operates on a partial graph built from human-authored
artifacts — incomplete, ambiguous, sometimes contradictory. Output is honest
about that or it is harmful: paths that look authoritative on a partial graph
become false confidence in shipping designs.

## Hard rules

### 1. Never invent nodes
Every node in the asset graph must cite one of:
- An asset/identity/trust-boundary record in `00-context/asset-inventory.yaml`
- A normalized threat-model entry whose `asset` field is the node name
- A code-evidence-index entry naming the service/component
- A domain-pack `crown_jewels[]` or `attacker_positions[]` declaration
- A run-config `crown_jewels[]` or `attacker_positions[]` override

If a node has no citation, it does not exist. Do not add it because "it
probably should be there."

### 2. Never invent edges
Every edge must cite one of:
- An IaC/architecture artifact declaring network reachability
- A finding whose evidence describes attacker traversal (edge_type =
  `compromisable_via_finding`, finding_id required)
- A capability whose evidence describes mitigation along a known path
  (edge_type = `mitigated_by_capability`, capability_id required)
- A normalized threat-model entry naming both endpoints
- A code-evidence-index cross-service call
- A trust boundary declared in asset-inventory or domain-pack defaults

### 3. Confidence floors severity
- Paths whose feasibility floor is `low` MUST cap at `disposition: uncertainty`
  and `severity ∈ {low, medium}`. Never escalate to `risk` on a low-confidence
  path.
- Paths whose feasibility floor is `high` and whose severity_sum ≥ 3 with no
  mitigations along the path SHOULD emit `disposition: risk` at `severity:
  high` or `critical`.
- When in doubt between two severity levels, take the lower. The path is
  interesting either way; over-escalating destroys signal in the rest of the
  advisory report.

### 4. Bounded enumeration; honest output
- `max_hop` caps at 12 (schema-enforced). Default 8.
- `max_paths_per_pair` caps at 200 (schema-enforced). Default 50.
- When truncation occurs, the `attack-paths.yaml` summary records
  `truncated_pairs > 0` and the report says so explicitly.
- Never claim "all paths" — output language is always "top-N paths under K
  hops."

### 5. Block on missing crown jewels
No declared targets → analyzer emits a single `disposition: blocked` finding
and does not enumerate. Do not guess. The block-finding must list
`prerequisite_evidence: ["domain pack or run-config must declare
crown_jewels[]"]`.

### 6. D3FEND must counter ATT&CK
A D3FEND technique appearing in `candidate_d3fend[]` MUST have a non-empty
`counters[]` array drawn from the bottleneck edge's `exposed_attack_techniques`.
The MITRE D3FEND attack-counter table is the authoritative source; never map
by name similarity ("the names sound related" is not evidence). The
`tools/apd_gauntlet/data/d3fend.json` reference data is the projection of
that table; always use it.

See [d3fend-mapping-pattern.md](references/d3fend-mapping-pattern.md) for the
walk-through.

### 7. Mermaid diagram cap
Single diagram ≤ 50 nodes. Graphs above this cap partition by attacker_position
into multiple inline `flowchart LR` diagrams in the report. The
`tools/apd_gauntlet/attack_path/mermaid.py` module enforces this — do not
bypass it.

## Tier ordering

The analyzer runs in tier-4 AFTER `apd-synthesizer` has dedup'd specialist
findings and capabilities. Inputs are read-only from the analyzer's
perspective: it never modifies specialist records. Its own findings are
appended to a separate file (`40-synthesis/attack-path.findings.yaml`) that
the synthesizer's final coverage-matrix pass includes in the 9×N rollup.

## Out of scope (delegated)

- Edge confidence is a property of the source artifact, not a judgment call —
  IaC says high, free-form prose says low, code-evidence with a clear file
  path says high.
- Severity scoring uses the standard APD rubric (`apd-evidence-discipline`).
  Do not re-derive — apply.
- Identity/authz semantics that ARE in scope for specialists (apd-authenticity,
  apd-ephemeral) MUST NOT be re-litigated. The analyzer reads their findings
  as edge attributes, not as its own analysis.
