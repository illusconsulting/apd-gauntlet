# Agentic AI required-immutable data classes

Each class must be tamper-evident and retained. For each, the pack expects a retention
basis and a tamper-evidence mechanism (WORM, hash chain, signed commit, object lock).

## Agent execution and decision traces

Per-step tool calls, inputs, outputs, and the reasoning record. Basis: forensics and
attribution. Mechanism: append-only / hash-chained.

## Generation provenance and lineage

Which generation produced which agent code, under which model, prompt, and parent hash.
Basis: self-improvement accountability. Mechanism: append-only Merkle/git-style chain.

## Prompt, policy, and tool-manifest version history

The system prompts, guardrail config, and tool manifests that governed each decision.
Basis: drift detection and audit. Mechanism: config-as-code with signed commits.

## Evaluation results and scores

The held-out evaluation outcomes per generation. Basis: anti-gaming of the optimization
metric. Mechanism: scores hash-committed at compute time; WORM preservation.

## Model, tool, and SBOM provenance

Which model version and tool/dependency hashes were in play. Basis: supply-chain
attestation. Mechanism: signed SBOM / attestation store.

## Human and HITL approval records

Sign-offs on consequential actions. Basis: accountability and segregation of duties.
Mechanism: signed, append-only.
