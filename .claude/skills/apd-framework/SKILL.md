---
name: apd-framework
description: Canonical reference for the APD security architecture framework — three tiers (Assure Trustworthiness, Provide Scalability, Demonstrate Auditability) and nine security goals. Use this whenever you need to determine which APD goal a concern belongs to, resolve boundary calls between adjacent goals (e.g. Confidentiality vs Authenticity, Non-Repudiation vs Immutability), or understand the tier dependency structure used by the APD gauntlet. Required reading for every specialist agent in the gauntlet before emitting findings or capabilities.
---

# APD Framework

APD is a goal-based security architecture framework organized into three tiers, each containing three goals. The tiers express what a secure system must do; the goals are the specific properties that compose each tier.

```
Assure Trustworthiness  →  Confidentiality · Integrity · Availability
Provide Scalability     →  Distributed · Resilient · Ephemeral
Demonstrate Auditability →  Authenticity · Non-Repudiation · Immutability
```

The tiers are ordered. Trustworthiness is foundational: a system that cannot be trusted with data cannot meaningfully scale or be audited. Scalability is the operational tier: a trustworthy system that cannot be scaled, distributed, or operated under failure is fragile in production. Auditability is the accountability tier: a trustworthy, scalable system that cannot prove what it did is uninspectable and unreviewable. The gauntlet processes tiers in this order, and tier 2/3 agents may reference tier 1/2 findings via `cross_references`.

## Lens versus scope

Every goal has a **lens** (the analytical perspective) and a **scope** (what counts as in-bounds for that lens). The lens-versus-scope distinction is the most important discipline in the framework. When you see something that concerns a system property, ask: is this in my lens, or am I noticing something an adjacent goal owns? If the latter, add it to `related_concerns` and let that agent write the finding.

The boundary calls in each section below are the operative resolutions for ambiguous cases.

---

## Tier 1: Assure Trustworthiness

### Confidentiality

**Lens.** Is the data hidden from parties not authorized to see it?

**In scope.**

- Encryption at rest (TDE, full-disk, field-level, envelope encryption)
- Encryption in transit (TLS configuration, mTLS, certificate pinning)
- Encryption in use (TEE, confidential computing, homomorphic schemes)
- KMS hierarchy, DEK/KEK separation, key access boundaries
- Masking, tokenization, format-preserving encryption
- Unmasking flows (step-up auth, just-in-time PHI access)
- PHI exposure surface analysis (what fields, what consumers, what minimum-necessary scope)
- Access scoping at data-element granularity

**Out of scope (route to adjacent goal).**

- "Is the identity claiming access verified?" → **Authenticity**
- "Will the credentials granting access expire promptly?" → **Ephemeral**
- "Was the access logged with attribution?" → **Non-Repudiation**
- "Can the access record be altered?" → **Immutability**

**Boundary: Confidentiality vs Authenticity.** Confidentiality asks whether the data is hidden. Authenticity asks whether the identity is verified. A system can leak PHI to a correctly-authenticated user with too-broad scope (Confidentiality finding) or admit an unauthenticated user (Authenticity finding). Encryption with weak access control is Confidentiality; strong access control over plaintext is also Confidentiality; weak identity proof on the access decision is Authenticity.

**Boundary: Confidentiality vs Ephemeral.** What is encrypted is Confidentiality. How long the keys live before rotation is Ephemeral. Both can have findings on the same encryption design.

### Integrity

**Lens.** Is the data what it should be, and unchanged in transit and at rest?

**In scope.**

- Schema enforcement (typed schemas, contract validation)
- Input validation on write paths (range, type, semantic constraints)
- Tamper detection (HMAC, signed payloads, content hashes)
- Transactional guarantees (ACID, idempotency keys, exactly-once semantics where claimed)
- Referential integrity, foreign key enforcement
- Data quality contracts and dead-letter handling
- Write-path authorization (who may mutate what)

**Out of scope (route to adjacent goal).**

- "Is the writer's identity verified?" → **Authenticity**
- "Is the write attributable in audit?" → **Non-Repudiation**
- "Are historical states preserved against alteration?" → **Immutability**

**Boundary: Integrity vs Authenticity.** Integrity asks whether the data is correct. Authenticity asks whether the sender is verified. A signed-but-wrong payload is an Integrity finding; an unsigned-but-correct payload is an Authenticity finding.

**Boundary: Integrity vs Immutability.** Integrity is about correctness at write time. Immutability is about preservation across time. A system that accepts wrong data is an Integrity problem; a system that lets correct historical data be silently altered is an Immutability problem.

### Availability

**Lens.** Will the system be reachable and responsive when needed, within stated targets?

**In scope.**

- SLO/SLI definitions and measurement
- Failure-domain analysis (what's the blast radius of one failure?)
- DR/BCP posture (RTO, RPO, runbooks, backup verification)
- Capacity headroom and load projection
- Dependency reliability (vendor SLAs, internal upstream/downstream)
- Health checks, readiness/liveness signaling
- Adjudication-specific timing constraints (claim response latency targets)

**Out of scope (route to adjacent goal).**

- "Is the system spread across failure domains?" → **Distributed**
- "How does the system behave under partial failure?" → **Resilient**

**Boundary: Availability vs Distributed vs Resilient.** Availability is the *target* (what uptime is promised, measured). Distributed is the *topology* (how the system is spread to make the target achievable). Resilient is the *behavior* (what the system does when a component fails). A single-region system with a 99.9% SLO is an Availability gap if 99.9% is undeliverable, a Distributed gap if multi-region is required, and a Resilient gap if there are no failover patterns.

---

## Tier 2: Provide Scalability

### Distributed

**Lens.** Is the system spread across failure domains and capable of partition tolerance?

**In scope.**

- Single point of failure (SPOF) identification
- Multi-region, multi-AZ topology
- Partition tolerance positioning (CAP-tradeoff explicitness)
- Stateful vs stateless component boundaries
- Data locality, replication topology, read/write splits
- Cross-region consistency model (strong, eventual, causal)
- Load distribution mechanism (DNS, anycast, service mesh)

**Out of scope (route to adjacent goal).**

- "What's the uptime target?" → **Availability**
- "What happens when a partition occurs?" → **Resilient**
- "Are the distributed components ephemeral?" → **Ephemeral**

**Boundary: Distributed vs Resilient.** Distributed is the static topology. Resilient is the dynamic behavior. A multi-AZ deployment with no circuit breakers is Distributed-good but Resilient-poor.

### Resilient

**Lens.** Does the system degrade gracefully under failure and recover automatically?

**In scope.**

- Failure-mode catalog (what fails, how, what's the user-visible effect)
- Retry policies (backoff, jitter, retry budgets)
- Circuit breakers and their thresholds
- Bulkheads and resource isolation
- Timeouts at every network boundary
- Graceful degradation modes (read-only mode, cached-response fallback, queue-and-replay)
- Chaos engineering readiness and recent exercises
- Backpressure handling

**Out of scope (route to adjacent goal).**

- "How is the system spread out?" → **Distributed**
- "What's the SLO?" → **Availability**

### Ephemeral

**Lens.** Are credentials, infrastructure, and access short-lived by design?

**In scope.**

- Credential lifecycle (creation, rotation, revocation)
- Immutable infrastructure (no in-place mutation, no SSH-to-fix)
- Just-in-time access patterns for human operators
- Ephemeral compute (containers, lambdas with bounded lifetime)
- Secret rotation cadence and automation (manual rotation = finding)
- Session lifetimes and refresh boundaries
- Service account credential expiry

**Out of scope (route to adjacent goal).**

- "Are credentials cryptographically verifiable?" → **Authenticity**
- "What's the encryption posture of the credentials?" → **Confidentiality**

**Boundary: Ephemeral vs Authenticity.** Ephemeral is about lifetime. Authenticity is about identity strength. A short-lived password is Ephemeral-good but Authenticity-poor.

---

## Tier 3: Demonstrate Auditability

### Authenticity

**Lens.** Is the claimed identity (of a user, a service, a payload, an artifact) cryptographically verifiable?

**In scope.**

- Identity provenance (who issues identity, what root of trust)
- mTLS, SPIFFE/SPIRE, workload identity
- Signed artifacts (binary signing, container image signing, package signing)
- SBOM generation and consumption
- Supply chain attestation (Sigstore, in-toto, SLSA levels)
- MFA strength and assurance levels (NIST 800-63B AAL)
- Signed payloads on inter-service messages

**Out of scope (route to adjacent goal).**

- "Is the action attributable in audit?" → **Non-Repudiation**
- "Is the credential short-lived?" → **Ephemeral**
- "Is the data hidden from unauthorized identities?" → **Confidentiality**

**Boundary: Authenticity vs Non-Repudiation.** Authenticity asks whether the identity is verifiable at the moment of action. Non-Repudiation asks whether the action, with attribution, was durably recorded. A cryptographically-verified service call that isn't logged is Non-Repudiation-poor; an unverified service call that is logged is Authenticity-poor.

### Non-Repudiation

**Lens.** Can every consequential action be tied to an actor, with sufficient durability and detail to withstand later denial?

**In scope.**

- Audit log completeness (what's logged, what's not, against a defined "consequential action" surface)
- Actor attribution in every entry (subject, on-behalf-of, source)
- Cryptographic event signing (signed audit, hash-chained logs)
- ATNA conformance for healthcare actions (IHE Audit Trail and Node Authentication)
- Time source reliability for event ordering (NTP integrity, monotonic counters)
- Audit log access controls and segregation of duties
- Audit log shipping reliability (no silent loss)

**Out of scope (route to adjacent goal).**

- "Can the audit record be altered after the fact?" → **Immutability**
- "Was the actor's identity verified?" → **Authenticity**

**Boundary: Non-Repudiation vs Immutability.** Non-Repudiation ensures the record exists with attribution. Immutability ensures the record cannot be changed later. A complete audit log written to a mutable store is Non-Repudiation-good but Immutability-poor.

### Immutability

**Lens.** Are records that must not change protected against alteration, with detection if they are?

**In scope.**

- WORM / append-only stores
- Configuration drift detection (declared state vs actual state)
- Hash-chained logs (Merkle trees, blockchain-style anchoring)
- Retention enforcement (legal hold, regulatory retention, automated lifecycle)
- Configuration-as-code with version history and signed commits
- Backup immutability (object lock, vault locks)
- Snapshot integrity

**Out of scope (route to adjacent goal).**

- "Is the record attributable to an actor?" → **Non-Repudiation**
- "Is the record encrypted at rest?" → **Confidentiality**

---

## Cross-tier dependency patterns

These are common patterns where a tier 2 or 3 finding depends on a tier 1 finding. Tier 2/3 agents that encounter these should populate `cross_references` rather than re-litigating the prerequisite.

- **Non-Repudiation depends on Integrity.** An audit log with weak integrity is not durable evidence. If Integrity has flagged write-path tampering risk on audit infrastructure, Non-Repudiation cites it.
- **Immutability depends on Confidentiality.** An immutable but unencrypted audit log over PHI is a Confidentiality problem first. If Confidentiality has flagged audit log encryption, Immutability cites it and frames its own finding around alteration risk specifically.
- **Authenticity depends on Ephemeral.** Strong identity with non-rotating credentials degrades over time. If Ephemeral has flagged a rotation gap, Authenticity may cite it when discussing assurance erosion.
- **Resilient depends on Distributed.** Circuit breakers in a single-region system mask a topology problem. If Distributed has flagged SPOF, Resilient cites it before discussing degradation patterns.

---

## How to use this skill

For specialist agents: before emitting any finding or capability, confirm the concern is inside your lens by checking the "In scope" list and the "Out of scope" list. If the concern is out of scope, populate `related_concerns` with the goal that owns it. Do not write the finding yourself.

For the synthesizer: when clustering findings across agents, use the boundary calls in this document to determine whether two findings represent the same root cause viewed through different lenses (merge candidate) or distinct concerns sharing evidence (link candidate).

For the intake agent: the goal definitions here are the basis for the `relevance_hints` field on each artifact in the artifact index.
