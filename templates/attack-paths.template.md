# Attack Paths — Template

> Emit this artifact as `30-graph/attack-paths.yaml`. Schema:
> `attack-path.schema.json`.
>
> Produced by the `apd-attack-path-analyzer` agent (tier-4) after the
> asset graph (`30-graph/asset-graph.yaml`) is built. The enumerator
> walks every (attacker_position, crown_jewel) pair and emits the top-N
> bounded paths between them.

## When this artifact is produced

The analyzer emits this file whenever it produces an asset graph (see
`asset-graph.template.md`). Both artifacts are emitted as a pair: the
report and the defense overlay both consume `attack-paths.yaml`.

## Output shape

Placeholder syntax — `<sha8>`, `<N>`, `<level>` — is illustrative;
replace with concrete values during emission. Integer placeholders use
literal numerals so the skeleton is itself valid YAML.

```yaml
schema_version: 1
generated_by: attack_path_analyzer

enumeration_parameters:
  max_hop: 8                    # integer 2–12; cap on path length
  max_paths_per_pair: 50        # integer 1–200; top-N per (attacker, jewel) pair
  bottleneck_threshold: 5       # integer 2–50; min paths-through-edge for bottleneck

paths:
  - path_id: "path-<sha8>"
    attacker_position: "atk-<sha8>"
    crown_jewel: "jewel-<sha8>"
    edges:
      - "edge-<sha8>"
      - "edge-<sha8>"
    hop_count: 2                # integer 1–12; len(edges)
    feasibility: high           # high | medium | low; floor of edge confidences
    severity_sum: 0             # integer; sum of severities of findings on this path
    mitigation_count: 0         # integer; count of capabilities mitigating this path
    bottleneck_edges: []        # edges from this path that ≥ bottleneck_threshold

summary:
  pairs_enumerated: 0
  total_paths: 0
  truncated_pairs: 0            # pairs where the enumerator hit max_paths_per_pair
  bottleneck_edge_count: 0
```

## Field semantics

### `enumeration_parameters.max_hop`

Integer 2–12. Bounds the path length so enumeration is finite on dense
graphs. Default `8`. Values outside the bound are a schema error.

### `enumeration_parameters.max_paths_per_pair`

Integer 1–200. Caps the per-pair output to the top-N paths under the
analyzer's sort order (descending `severity_sum`, ascending
`hop_count`, descending `feasibility`). Pairs that hit this cap are
recorded in `summary.truncated_pairs`. Default `50`.

### `enumeration_parameters.bottleneck_threshold`

Integer 2–50. Minimum number of distinct paths that must share an edge
for that edge to count as a bottleneck. Default `5`. The defense-graph
overlay enumerates D3FEND counters only for edges meeting this
threshold.

### `paths[*].path_id`

Stable `path-<sha8>` of the canonical edge-id sequence. Two identical
paths across runs share the same id; reordering edges in the path
produces a different id.

### `paths[*].feasibility`

Computed as the **floor** of the edge confidences along the path.
Per the discipline skill (`confidence-floors-severity` rule), a path
that traverses any low-confidence edge is itself low-feasibility,
regardless of how short the hop count is.

### `paths[*].severity_sum`

Integer ≥ 0. The sum of severity weights of any `finding_id`-backed
edge on the path. Mapping per `apd-evidence-discipline`'s
impact-to-PBM severity rubric:

- `critical` → 8
- `high`     → 4
- `medium`   → 2
- `low`      → 1

### `paths[*].mitigation_count`

Integer ≥ 0. The count of edges on this path whose `edge_type` is
`mitigated_by_capability`. Reflects defensive depth on the path. A
high `mitigation_count` does **not** absolve the path; it is reported
for context alongside `severity_sum`.

### `paths[*].bottleneck_edges`

Subset of `paths[*].edges` whose paths-through count meets or exceeds
`enumeration_parameters.bottleneck_threshold`. Populated after global
bottleneck analysis completes; bottleneck membership is what the
defense overlay (`defense-graph.yaml`) attacks.

### `summary.truncated_pairs`

Number of `(attacker_position, crown_jewel)` pairs for which the
enumerator hit `max_paths_per_pair`. Reported in the narrative so the
human reader knows the output is bounded — never "all paths."

## Discipline reminders for the analyzer agent

See `apd-attack-path-discipline` and the activation contract in
`.claude/agents/apd-attack-path-analyzer.md`. Critical rules:

- **Bounded enumeration.** Never emit "all paths." Always report
  truncation counts when pairs hit `max_paths_per_pair`.
- **Block on missing crown jewels.** If no crown jewel is declared,
  emit a `blocked-on-evidence` finding and halt — do not invent.
- **Confidence floors severity.** Low-feasibility paths cap at
  `disposition: uncertainty` regardless of how high `severity_sum`
  climbs.
