# Inputs — Claim Event Bus example

This directory holds the synthetic intake artifacts the example exercises end-to-end:

- `tech_plan.md` — Kafka-based claim event bus design
- `claim-events.proto` — protobuf schema with PHI fields
- `threat-model.md` — abbreviated STRIDE narrative
- `threat-model.json` — machine-readable threat model the intake parser consumes
- `adr-001-cap-positioning.md` — CAP-positioning decision
- `iac/` — Terraform stubs used by the implemented-maturity gating

## How this differs from a real run

In a real run, `inputs/` is where the engineering team drops the artifacts they
want the gauntlet to review (architecture docs, ADRs, threat model, IaC,
sometimes runbooks). The intake agent extracts assets/identities/trust
boundaries from them into `00-context/`. The specialist agents then read both
intake artifacts and the extracted context.

For the example, the artifacts here are hand-authored and the matching
extracted context lives at `../expected/00-context/`. The root-level
`../00-context/asset-inventory.yaml` is a scaffold sufficient to satisfy
`apd-gauntlet validate` against the example root; the full curated context
remains in the `expected/` subtree.

## Regenerating

These files are intentionally hand-maintained — they are the canonical input
shape the framework tests against, so changing them is a deliberate update to
the example contract, not a regenerable build artifact.
