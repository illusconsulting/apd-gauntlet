# Agentic AI data taxonomy

Sensitivity tiers and handling, tagged with the APD goals that care.

## Secrets and credentials (Confidentiality, Ephemeral)

Model-provider API keys, tool credentials, signing keys. Highest sensitivity; encryption,
JIT scoping, rotation, and no persistence in traces.

## Held-out evaluation data and ground truth (Confidentiality, Integrity)

The private eval set and labels. Read-scoped away from the agent process; leakage breaks
the optimization signal.

## Generated agent code and artifacts (Integrity, Authenticity)

Self-produced code. Integrity-critical and a backdoor vector; signed and provenance-tracked.

## Agent memory, context, and history (Confidentiality, Integrity)

May contain user PII, prior tool outputs, retrieved documents. Per-session/tenant scoped;
a poisoning target.

## Untrusted tool I/O and external content (Integrity)

Tool outputs, retrieved docs, web content. The injection carrier; provenance-tagged and
never trusted as instructions.

## Training and fine-tune data (Integrity)

A poisoning surface; provenance and validation on ingest.

## Decision and telemetry logs (Non-Repudiation, Confidentiality)

Audit-relevant; may carry sensitive content. Retained, attributable, access-scoped.

## Model weights and configuration (Confidentiality)

IP and an extraction target; encrypted at rest and access-scoped.
