# Asset Graph — Template

> Emit this artifact as `30-graph/asset-graph.yaml`. Schema:
> `asset-graph.schema.json`.
>
> Produced by the `apd-attack-path-analyzer` agent (tier-4) during graph
> construction. Consumes the intake `asset-inventory.yaml`, the normalized
> threat model, the code-evidence index (when present), every emitted
> `finding`, every emitted `capability`, plus run-config and active
> domain-pack defaults.

## When this artifact is produced

The analyzer emits this file whenever:

- `.apd-run.yaml` declares a non-empty `crown_jewels:` list (or the active
  domain pack supplies defaults), AND
- at least one `attacker_position` is declared (run-config or domain pack).

When neither precondition holds, the analyzer skips silently and no
asset graph is written.

## Output shape

Placeholder syntax — `<sha8>`, `<canonical name>`, `<file path>` — is
illustrative; replace each with concrete values during emission.
Bracketed placeholders are quoted so the skeleton is itself valid YAML
(an emitter can `yaml.safe_load` this skeleton to validate shape before
substitution).

```yaml
schema_version: 1
generated_by: attack_path_analyzer

nodes:
  - node_id: "asset-<sha8>"              # asset | idn | atk | jewel prefix
    node_type: asset                     # asset | identity | attacker_position | crown_jewel
    name: "<canonical name>"
    asset_type: service                  # optional; service | data_store | secret_store | queue | network | external_dependency | compute
    data_classifications: [phi, internal]  # optional
    provenance:
      source: artifact                   # artifact | domain_default | threat_model | code_evidence | run_config | asset_inventory
      artifact: "<file path>"
      locator: "<file#region>"
    confidence: high                     # high | medium | low

edges:
  - edge_id: "edge-<sha8>"
    edge_type: network_reachable         # 7 edge types — see Field semantics
    from: "asset-<sha8>"
    to: "asset-<sha8>"
    provenance:
      source: artifact
      artifact: "<file path>"
      locator: "<file#region>"
    confidence: high
    traversal_cost: 1                    # integer 1–100; lower = easier traversal
    # finding_id: "<conf|intg|avail|...>-<sha8>"     # required when edge_type=compromisable_via_finding
    # capability_id: "<conf|intg|...>-cap-<sha8>"    # required when edge_type=mitigated_by_capability

build_summary:
  node_count: 0
  edge_count: 0
  attacker_position_count: 0
  crown_jewel_count: 0
  finding_edges_count: 0
  capability_edges_count: 0
  sources_used: [asset_inventory, findings, capabilities]
```

## Field semantics

### `nodes[*].node_type`

One of:

- `asset` — service / data store / network / compute / etc. surfaced
  from `asset-inventory.yaml`, the threat model, or the code-evidence
  index
- `identity` — a principal lifted from the inventory's `identities[]`
  block (human role, service account, workload identity, external party)
- `attacker_position` — an attacker start point declared in run-config
  or the domain pack
- `crown_jewel` — a high-value target declared in run-config or the
  domain pack

### `nodes[*].asset_type`

Optional. Set only when `node_type=asset`. Mirrors the inventory enum
(`service | data_store | secret_store | queue | network |
external_dependency | compute`).

### `nodes[*].provenance.source`

- `artifact` — explicitly named in a supplied input artifact
- `domain_default` — supplied by the active domain pack's defaults
- `threat_model` — named in the normalized threat-model
- `code_evidence` — surfaced by the `apd-code-recon` evidence index
- `run_config` — declared in `.apd-run.yaml`
- `asset_inventory` — lifted from `00-context/asset-inventory.yaml`

### `nodes[*].confidence`

- `high` — IaC-declared, schema-declared, or otherwise structurally
  asserted
- `medium` — prose-described in an artifact with a clear name
- `low` — inferred from ambiguous prose; the analyzer treats
  low-confidence nodes as bounded contributors to path feasibility, not
  as authoritative graph entries

### `edges[*].edge_type`

Seven canonical edge types:

- `network_reachable` — the source can open a network connection to the
  target (IaC routes, security groups, declared peers)
- `authn_required` — authenticating to the target requires the identity
  named at `from` (or vice-versa, per edge orientation)
- `authz_grants` — the policy at `from` grants `to` the listed
  permissions on a target
- `data_resides_on` — sensitive data lives on the target asset
- `trusts` — the source node trusts the target node's assertions (token
  issuer, OIDC trust, cross-account trust)
- `compromisable_via_finding` — the edge is enabled because a tier-1/2/3
  specialist finding documents a gap. Requires `finding_id`.
- `mitigated_by_capability` — the edge has a confirmed defensive
  capability backing it. Requires `capability_id`.

### `edges[*].traversal_cost`

Integer 1–100. Default `1` when the edge is structurally asserted with
no friction. Increase when the edge depends on stolen credentials,
human social-engineering, or other elevated effort. The enumerator
uses cost as a tie-break and as the basis for feasibility floor
computation alongside the edge confidence.

### `build_summary.sources_used`

An array drawn from `asset_inventory | threat_model_normalized |
code_evidence_index | findings | capabilities | domain_defaults |
run_config`. Records which run-level artifacts the analyzer pulled to
build the graph. Used by the report's "Scope → Sources used" line.

## Discipline reminders for the analyzer agent

See `apd-attack-path-discipline` and the activation contract in
`.claude/agents/apd-attack-path-analyzer.md`. Critical rules:

- **Never invent nodes.** Every node cites a `provenance` block with a
  concrete artifact and locator. Crown jewels and attacker positions
  trace to run-config or the domain pack.
- **Never invent edges.** Every edge cites provenance. Findings-backed
  edges name a real `finding_id`; capability-backed edges name a real
  `capability_id`.
- **Low-confidence is honest.** When provenance is ambiguous, set
  `confidence: low`. Low-confidence paths cap at
  `disposition: uncertainty` regardless of severity_sum.
- **No invented `from`/`to`.** Use schema field names exactly — `from`
  and `to`, not `from_node` / `to_node`.
