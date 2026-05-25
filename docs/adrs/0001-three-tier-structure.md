# ADR-0001: Three-Tier Structure (Trustworthiness → Scalability → Auditability)

**Status:** Accepted
**Date:** 2026-05-24

## Context

A multi-agent security architecture review framework needs a way to organize what each specialist examines. Generic "security review" doesn't scale beyond a single reviewer's mental model, and most existing frameworks (NIST CSF, OWASP, MITRE D3FEND) are control-catalog-shaped rather than goal-shaped. The APD framework adopts a goal-based structure with three tiers, each containing three goals, mapped to nine specialist lenses.

The tier *ordering* is not arbitrary. We considered several arrangements and converged on this rationale: trustworthiness is foundational (a system that cannot be trusted with data cannot meaningfully be scaled or audited), scalability is operational (a trustworthy system that cannot operate under failure is fragile), and auditability is accountability (a trustworthy, scalable system that cannot prove what it did is uninspectable).

## Decision

The framework processes tiers in order: Trustworthiness (Confidentiality, Integrity, Availability) first; Scalability (Distributed, Resilient, Ephemeral) second; Auditability (Authenticity, Non-Repudiation, Immutability) third. Tier 2 specialists may cross-reference tier 1 findings; tier 3 may cross-reference tier 1 and 2. Specialists cannot cross-reference later tiers.

## Consequences

- Cross-tier dependencies are unidirectional, making the framework's reasoning graph acyclic and tractable.
- Specialists can rely on prior tiers having been considered, avoiding "did anyone think about X" gaps.
- The advisory report has a natural narrative structure that mirrors the tier order.
- The framework does not capture concerns that genuinely cut across all three tiers (e.g. supply chain) in a single lens — those concerns are split across multiple specialists with `related_concerns`.

## Alternatives considered

- **CIA triad alone (3 specialists)** — too coarse; loses the auditability tier's structural concerns.
- **MITRE ATT&CK as the framework** — control-shaped, not goal-shaped; doesn't fit advisory architecture review.
- **Flat structure (9 specialists, no tier ordering)** — loses the dependency story; harder to compose advisory output narratively.
- **Different tier ordering (e.g. Auditability first)** — auditability is meaningless without underlying trustworthiness.
