# Defense Graph — Template

> Emit this artifact as `30-graph/defense-graph.yaml`. Schema:
> `defense-graph.schema.json`.
>
> Produced by the `apd-attack-path-analyzer` agent (tier-4) as a
> defensive overlay on the attack-paths output. For every bottleneck
> edge (an edge appearing on ≥ `bottleneck_threshold` paths) the
> analyzer looks up the ATT&CK techniques exposed on that edge, then
> emits the D3FEND techniques that counter those ATT&CK techniques per
> the MITRE D3FEND attack-counter table.

## When this artifact is produced

The analyzer emits this file whenever the attack-paths output contains
at least one bottleneck edge. When no bottleneck edges exist (the
graph is wide rather than narrow), the analyzer still emits the file
with `bottleneck_overlays: []` so downstream consumers can rely on a
stable artifact set.

## Output shape

Placeholder syntax — `<sha8>`, `<≥20 chars: ...>`, technique IDs — is
illustrative; replace with concrete values during emission. Integer
placeholders use literal numerals so the skeleton is itself valid
YAML.

```yaml
schema_version: 1
generated_by: attack_path_analyzer

bottleneck_overlays:
  - edge_id: "edge-<sha8>"
    paths_traversing: 2                # integer ≥ 2; min for bottleneck
    exposed_attack_techniques:
      - "T1078"                        # ATT&CK technique IDs traversing this edge
    candidate_d3fend:
      - d3fend_id: "D3-AA"
        counters:
          - "T1078"                    # ATT&CK techniques this D3FEND counters
        rationale: "<≥20 chars: why this D3FEND technique counters the exposed ATT&CK per the D3FEND attack-counter table>"
    existing_capability_backing:
      - d3fend_id: "D3-AA"
        capability_ids:
          - "auth-cap-<sha8>"          # confirmed capability already implementing this D3FEND
    net_new_d3fend:
      - "D3-AL"                        # candidate D3FEND IDs with no existing capability backing
      - "D3-AM"

summary:
  bottleneck_edge_count: 0
  total_candidate_d3fend: 0
  total_net_new_d3fend: 0
```

## Field semantics

### `bottleneck_overlays[*].edge_id`

The `edge-<sha8>` id of a bottleneck edge from
`attack-paths.yaml.paths[*].bottleneck_edges`. Each bottleneck edge
appears at most once in this array.

### `bottleneck_overlays[*].paths_traversing`

Integer ≥ 2. The number of enumerated attack paths that traverse this
edge. Equal to or greater than
`enumeration_parameters.bottleneck_threshold` from the attack-paths
artifact. (The schema enforces a minimum of 2 because a "bottleneck of
one" is not a bottleneck.)

### `bottleneck_overlays[*].exposed_attack_techniques`

ATT&CK technique IDs (e.g. `T1078`, `T1190`, `T1078.004`) that
traverse this edge. The analyzer derives these from the
`finding_id`-backed edges along the paths through this bottleneck:
each finding cites an `attack_technique_id` in its `control_mappings`
block, and those technique IDs aggregate up to the edge.

### `bottleneck_overlays[*].candidate_d3fend`

D3FEND techniques that could counter one or more of the exposed
ATT&CK techniques. Sourced exclusively from the MITRE D3FEND
attack-counter table shipped at `tools/apd_gauntlet/data/d3fend.json`.

- `d3fend_id` — the D3FEND identifier (e.g. `D3-AA`, `D3-AL`).
- `counters[]` — the subset of `exposed_attack_techniques` this
  D3FEND technique counters. Must intersect non-empty with
  `exposed_attack_techniques`; if it does not, the candidate is not
  emitted.
- `rationale` — ≥ 20 chars. Plain-language explanation citing the
  D3FEND attack-counter row. D3FEND-by-name-similarity is forbidden
  by the `apd-attack-path-discipline` skill — the rationale must
  reflect the table row that justifies the counter.

### `bottleneck_overlays[*].existing_capability_backing`

For each `candidate_d3fend` entry, the confirmed capabilities (from
the run's `findings-and-capabilities/*-cap-*.yaml` artifacts) that
already implement that D3FEND technique.

- `d3fend_id` — the same D3FEND id appearing under `candidate_d3fend`.
- `capability_ids[]` — at least one full capability ID per the
  `capability.schema.json` pattern (e.g. `auth-cap-<sha8>`,
  `intg-cap-<sha8>`).

### `bottleneck_overlays[*].net_new_d3fend`

D3FEND IDs from `candidate_d3fend` that have **no** entry in
`existing_capability_backing`. These are the highest-leverage
defensive investments — a single implementation of any one of these
breaks every path traversing the bottleneck. Reported as the
report's "High-leverage findings" section.

### `summary` block

Aggregates across all bottlenecks:

- `bottleneck_edge_count` — `len(bottleneck_overlays)`.
- `total_candidate_d3fend` — count of unique D3FEND IDs appearing in
  any `candidate_d3fend[].d3fend_id` across all bottlenecks.
- `total_net_new_d3fend` — count of unique D3FEND IDs appearing in
  any `net_new_d3fend[]` across all bottlenecks.

## Discipline reminders for the analyzer agent

See `apd-attack-path-discipline` and the activation contract in
`.claude/agents/apd-attack-path-analyzer.md`. Critical rules:

- **D3FEND must counter ATT&CK.** Every `candidate_d3fend[]` entry
  must intersect non-empty with `exposed_attack_techniques`. The
  analyzer does not propose D3FEND techniques on similarity of name.
- **The D3FEND table is the only source.** D3FEND candidates are
  pulled from `tools/apd_gauntlet/data/d3fend.json` (the refreshed
  attack-counter table). Other sources are not permitted.
- **Net-new is the leverage signal.** `net_new_d3fend[]` is what the
  report's "High-leverage findings" table surfaces. The empty case
  (every bottleneck already backed) is a valid outcome — it means the
  existing capability surface already covers the narrow points of the
  graph.
