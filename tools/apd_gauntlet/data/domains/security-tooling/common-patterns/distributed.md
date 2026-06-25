# Security tooling common patterns — Distributed

These are illustrative templates, not all-inclusive. Use them to calibrate analytical style, severity assignment per the security-tooling rubric, and NIST/ATT&CK mapping habits. The specialist agent's analytical checklist still drives the actual analysis — this file calibrates how findings and capabilities should look once written.

Distributed concerns in security tooling have two security-specific dimensions absent in conventional API domains: (1) **data residency for engagement results** is constrained by the target's jurisdiction, not just the operator's; (2) **listener topology** is observable to target-side defenders and shapes target-detection signal.

## Common finding patterns

**Pattern: Single-region listener deployment; implants from engagements in multiple jurisdictions all callback to the same region, putting target-environment-derived data in a region the target's data-residency policy may not allow.**

- Severity: high (for SaaS-delivered or multi-customer platforms, customer's regulatory residency on harvested data — including any incidental PII captured in screenshots — may be violated by listener placement)
- NIST: SC-7, SC-36, AC-4
- Related concerns: confidentiality (residency for captured data), authenticity (per-region listener TLS topology)

**Pattern: Multi-tenant SaaS platform with shared orchestrator process per tenant — tenant A's compromised plugin or tenant A's runaway engagement affects tenant B's availability.**

- Severity: high (tenant-isolation boundary leaks at the process level; escalates to critical if plugin sandbox escape is also possible)
- NIST: SC-7, SC-39 (Process Isolation), AC-4
- ATT&CK: T1611 (Escape to Host) when container-based isolation fails
- Related concerns: authenticity (per-tenant workload identity), confidentiality (cross-tenant data exposure), resilient (per-tenant bulkhead)

**Pattern: Listener topology is single-point-of-presence per region — implants discover the listener via a single DNS record and a single static IP, making target-side defender blocking trivial.**

- Severity: medium operationally (engagement quality and stealth); medium-to-high for availability (single point of failure)
- NIST: CP-7, SC-36
- Related concerns: availability (single-point-of-presence outage), authenticity (listener TLS cert reuse signals)

**Pattern: Audit-log replication across regions is asynchronous with unspecified lag; regional failover loses audit content for the failover window.**

- Severity: high (rubric: "Audit trail loss" for the failover window; cross-references Non-Repudiation; critical if the failover window is unbounded)
- NIST: AU-9(2) (Audit Backup on Separate System), SC-36, CP-7
- Related concerns: non_repudiation, immutability, resilient (audit-buffer behavior during regional failover)

**Pattern: In-cluster service-to-service trust based on Kubernetes namespace boundaries only; no mTLS, no workload identity. Compromise of any pod in the cluster (including plugin runtime if it co-locates) yields lateral access to orchestrator and listener.**

- Severity: high (lateral-movement amplification; converts plugin sandbox escape into full platform takeover)
- NIST: SC-8(1), SC-23, IA-3, IA-9 (Service Identification and Authentication), SC-7(13)
- ATT&CK: T1557 (Adversary-in-the-Middle) in-cluster; T1078 with shared SA tokens
- Related concerns: authenticity (workload identity is the replacement pattern), confidentiality (in-cluster sensitive payloads in transit)

**Pattern: Cross-region replication for result-data store unspecified — artifacts assert multi-region capability without per-customer or per-engagement data-residency binding.**

- Disposition: blocked or uncertainty
- prerequisite_evidence: "Data-residency policy — per-customer region binding, per-engagement region binding, cross-region replication policy with lawful-basis attestation for any extra-jurisdiction flow, residency-enforcement mechanism (application-tier routing vs storage-layer constraints)"

**Pattern: Tech plan claims multi-region C2 but does not specify orchestrator topology — active-active with shared signing material, active-passive with replicated signing material, regionally-independent with per-region signing keys.**

- Disposition: uncertainty or blocked
- prerequisite_evidence: "C2 topology specification — orchestrator configuration (active-active, active-passive, region-independent), signing-material sharing model across regions, in-flight-engagement failover semantics, audit-pipeline cross-region durability"

## Common capability patterns

**Pattern: Per-tenant orchestrator processes (or per-tenant K8s namespaces) with per-tenant workload identity for cross-tier authentication; plugin runtime additionally per-tenant.** Capability scope must enumerate which services are confirmed per-tenant vs. shared; shared services become partial-coverage findings.

**Pattern: Multi-region listener topology with implants supporting callback-domain pools and per-region certificate pinning.** Higher maturity when target-side defender-observability of regional listener placement is explicitly considered (e.g., per-engagement listener allocation).

**Pattern: Region-pinned result-data store with explicit per-customer residency declaration, enforced at storage-layer policy plus application-tier routing.** Cross-cuts Confidentiality for residency-as-confidentiality; mention via `related_concerns`.

**Pattern: Service mesh with SPIFFE/SPIRE workload identity, per-namespace trust domains, and explicit mesh-to-non-mesh edge policy.** Cross-cuts Authenticity for the identity-issuance half.

**Pattern: Audit-log multi-region replication via streaming pipeline with backpressure, bounded lag SLO, and per-region durable buffer.** Cross-cuts Non-Repudiation and Immutability; the bounded-lag SLO is the load-bearing claim.
