# Agentic AI Severity Rubric (impact-to-agent-system)

Severity calibrates impact using four agentic modifiers: **autonomy** (acted without human
confirmation), **reversibility**, **blast radius** (single session vs cross-tenant or
cross-generation persistence), and **data sensitivity**. Raise severity when an outcome is
autonomous, irreversible, persists across sessions or generations, or crosses a tenant or
provider boundary.

> **Excessive Agency is cross-cutting.** OWASP LLM06 (Excessive Agency) is not a single
> goal here. It decomposes across goals: read-scope under Confidentiality, side-effecting
> tool/write authorization under Integrity, just-in-time permission lifetime under
> Ephemeral, and blast-radius isolation under Resilient. Each goal's patterns own their
> facet; there is no separate "confinement" goal.

## Critical

- Attacker-controlled code or tool execution against production from a prompt-injected or
  poisoned agent (autonomous, irreversible).
- Exfiltration of model-provider API keys or held-out evaluation ground truth.
- A self-improvement loop propagating a backdoor or unsafe behavior across generations.
- Takeover of the orchestration control plane (system prompts, tool manifests, routing).

## High

- Prompt injection driving a single high-privilege tool misuse (funds, data deletion,
  outbound comms) within one session.
- Disclosure of one principal's memory/context across a session or tenant boundary.
- Memory or RAG poisoning that alters future agent decisions.
- Unbounded consumption (tokens, generations, sub-agents) causing cost blow-up or DoS.

## Medium

- Injection that degrades output quality or leaks non-sensitive information.
- A consequential tool action caught by a guardrail or human-in-the-loop check.
- Observability gaps that materially delay detection of agent misbehavior.

## Low

- Missing rate limit on a low-risk read-only tool.
- Verbose logging of non-sensitive agent traces.
- A missing but non-critical guardrail with no demonstrated exposure.
