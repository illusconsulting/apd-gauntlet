# Asset Inventory — Template

> Emit this artifact as `00-context/asset-inventory.yaml`. Schema:
> `asset-inventory.schema.json`.
>
> Produced by the `apd-intake` agent (tier-0) whenever the run-config or
> the active domain pack declares any `crown_jewels`. Consumed by the
> `apd-attack-path-analyzer` agent (tier-4) as the asset-graph seed.

## When this artifact is produced

`apd-intake` emits this file alongside `00-context/context-brief.md` when:

- `.apd-run.yaml` declares a non-empty `crown_jewels:` list, OR
- the active domain pack declares any `crown_jewels`

When neither is declared (v1.1 / v1.2 / v1.3 back-compat runs), the
inventory is optional and may be omitted. The analyzer skips silently in
that case.

## Output shape

Placeholder syntax — `<sha8>`, `<canonical name>`, `<file path>` — is
illustrative; replace each with concrete values during emission. Bracketed
placeholders are quoted so the skeleton is itself valid YAML (an emitter
can `yaml.safe_load` this skeleton to validate shape before substitution).

```yaml
schema_version: 1
generated_by: intake

assets:
  - asset_id: "asset-<sha8>"             # sha8 of (name|primary_locator)
    name: "<canonical name>"
    asset_type: service                  # service | data_store | secret_store | queue | network | external_dependency | compute
    data_classifications: [phi, internal]   # optional
    provenance:
      source: artifact                   # artifact | domain_default | threat_model | code_evidence
      artifact: "<file path>"
      locator: "<file#region>"
    confidence: high

identities:
  - identity_id: "idn-<sha8>"
    name: "<canonical name>"
    identity_type: service_account       # human_role | service_account | workload_identity | external_party
    provenance:
      source: artifact
      artifact: "<file path>"
      locator: "<file#region>"
    confidence: high

trust_boundaries:
  - boundary_id: "tb-<sha8>"
    name: "<boundary description>"
    crosses:
      - "asset-<sha8>"
      - "asset-<sha8>"
    provenance:
      source: artifact
      artifact: "<file path>"
      locator: "<file#region>"

extraction_summary:
  asset_count: 0                         # populate with the actual count on emission
  identity_count: 0
  trust_boundary_count: 0
  high_confidence_count: 0
  medium_confidence_count: 0
  low_confidence_count: 0
```

## Field semantics

### `assets[*].asset_type`

One of:

- `service` — a named running service or application component
- `data_store` — database, object store, file store, cache used as persistence
- `secret_store` — KMS, secrets manager, parameter store, vault
- `queue` — message broker topic, queue, stream, event bus channel
- `network` — VPC, subnet, network segment, peering or transit boundary
- `external_dependency` — third-party vendor, SaaS, partner API, external system
- `compute` — VM, container host, function runtime, edge worker

### `assets[*].data_classifications`

Free-form list drawn from the run's data taxonomy. Common entries: `phi`,
`pii`, `pci`, `secret`, `internal`, `public`. Optional — omit when the
intake agent has no evidence basis for classification.

### `assets[*].provenance.source`

- `artifact` — explicitly named in a supplied input artifact
- `domain_default` — supplied by the active domain pack's default-assets list
- `threat_model` — named in a normalized threat-model entry's `asset` field
- `code_evidence` — surfaced by the optional `apd-code-recon` agent's evidence index

### `assets[*].confidence`

- `high` — IaC-declared, schema-declared, or otherwise structurally asserted
- `medium` — prose-described in an artifact with a clear name
- `low` — inferred from ambiguous prose; the analyzer treats low-confidence
  nodes as bounded contributors to path feasibility, not as authoritative
  graph entries

### `identities[*].identity_type`

- `human_role` — a named role for human actors (operator, member, sponsor)
- `service_account` — a service-level account or robot identity
- `workload_identity` — workload-bound identity (instance profile, pod identity, OIDC workload)
- `external_party` — an external system or partner principal

### `trust_boundaries[*].crosses`

An array of `asset_id` values that the boundary partitions. The boundary
asserts that data or control passing between these assets traverses a
trust-domain transition (e.g., internet→edge, application→data tier,
internal→external vendor). The markdown trust-boundary map in the
context-brief is for human review; this YAML structure is for the
analyzer.

## Discipline reminders for the intake agent

See `apd-evidence-discipline` and the activation contract in
`.claude/agents/apd-intake.md`. Critical rules:

- **Never invent assets.** If no supplied artifact mentions an asset, it
  does not appear in the inventory.
- **Low-confidence is honest.** When an asset is described ambiguously,
  set `confidence: low`. Do not optimistically claim `medium` or `high`.
- **No findings here.** The inventory is structural; security concerns
  surface as findings from the tier-1 / tier-2 / tier-3 specialists or
  from the attack-path analyzer.
