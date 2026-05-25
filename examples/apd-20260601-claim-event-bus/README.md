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

## Running the example

```bash
apd-gauntlet validate examples/apd-20260601-claim-event-bus/expected/
```

Exit code 0 means the example is consistent with the current schemas.
