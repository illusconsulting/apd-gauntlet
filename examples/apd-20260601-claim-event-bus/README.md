# APD Gauntlet Example — Claim Event Bus

A synthetic PBM tech plan exercising every framework feature without leaking real PHI or proprietary architecture. Used both as documentation (see what a run looks like) and as a CI integration test (the validator runs against `expected/` on every PR).

## Files

- `inputs/tech_plan.md` — Kafka-based claim event bus design
- `inputs/claim-events.proto` — protobuf schema with PHI fields
- `inputs/threat-model.md` — abbreviated STRIDE
- `inputs/adr-001-cap-positioning.md` — CAP-positioning decision
- `inputs/iac/kafka.tf` — Terraform stub (gives some capabilities `implemented` maturity)
- `expected/` — frozen reference outputs

## What this run demonstrates

- `disposition: blocked` with populated `prerequisite_evidence`
- Cross-tier references (tier 2 citing tier 1 findings)
- Synthesizer merge (Non-Repudiation + Immutability on the audit log)
- Contradiction (capability claims at-rest encryption; finding disputes scope)
- High-confidence ATT&CK rationales

## v1.4 — attack-path analysis

Phase C added an attack-path analyzer that builds an asset/identity/trust-boundary graph from intake artifacts and enumerates bounded attacker → crown-jewel paths. The example exercises this pipeline end-to-end:

- `expected/.apd-run.yaml` — declares `crown_jewels`, `attacker_positions`, and `attack_path_analysis` enumeration bounds (curated subset of the PBM domain pack defaults)
- `expected/00-context/asset-inventory.yaml` — intake artifact: 8 assets, 3 identities, 5 trust boundaries
- `expected/40-synthesis/asset-graph.yaml` — built graph (16 nodes, 43 edges) with per-edge provenance
- `expected/40-synthesis/attack-paths.yaml` — 75 bounded attack paths across 3 productive (attacker, jewel) pairs; 3 pairs truncated at `max_paths_per_pair=25`; 24 bottleneck edges
- `expected/40-synthesis/defense-graph.yaml` — D3FEND overlay (zero net-new candidates: demonstrates the "no high-confidence ATT&CK on bottleneck edges" disposition)
- `expected/40-synthesis/attack-path.findings.yaml` — 75 deterministic `apath-*` findings (all `disposition: uncertainty` per the confidence-floors-severity rule)
- `expected/40-synthesis/attack-path-report.md` — hand-authored human-reviewable narrative with inline Mermaid

Regenerate the four deterministic outputs with:

```bash
apd-gauntlet analyze-attack-paths examples/apd-20260601-claim-event-bus/expected/
```

## Running the example

```bash
apd-gauntlet validate examples/apd-20260601-claim-event-bus/expected/
```

Exit code 0 means the example is consistent with the current schemas.
