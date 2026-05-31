# Agentic AI consequential-action surface

These are the actions an agentic system can take that must be authorized, attributable,
and audited. Specialists treat each as a write/decision whose absence from the audit log
or whose missing authorization is a finding.

## Tool and code execution

- Side-effecting tool invocation: shell, file write, network/API mutate, financial
  transaction, outbound communication, database write.
- Execution of agent-generated code.

## Self-modification

- Generating or rewriting agent code, prompts, or policies.
- Promoting or committing a new generation in a self-improvement loop.

## Credential and data access

- Retrieving or using secrets and model-provider/tool credentials.
- Reading held-out evaluation data or training ground truth.

## Memory and delegation

- Writing to long-term memory or the RAG/vector store.
- Spawning or delegating to a sub-agent.

## Configuration and escalation

- Switching model or provider.
- Acquiring new tools, scopes, or privileges at runtime.
- Merging agent output into a system of record.
