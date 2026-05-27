# API security common patterns — Distributed

These are illustrative templates, not all-inclusive. Use them to calibrate analytical style, severity assignment per the API security rubric, and NIST/ATT&CK mapping habits. The specialist agent's analytical checklist still drives the actual analysis — this file calibrates how findings and capabilities should look once written.

## Common finding patterns

**Pattern: Single-AZ deployment of the authentication service, session store, or payment service.**

- Severity: high (the single AZ is the failure domain for the entire platform's authentication; a zonal incident produces total authentication outage)
- NIST: SC-7, CP-7, SC-36
- Cross-reference: any Availability finding on SLO consistency; the merged finding carries both the topology constraint and the SLA consequence

**Pattern: Sticky session dependency — load balancer pinned to instance because session state is in-process.**

- Severity: medium to high (impairs horizontal scale, deploy-time rolling restarts produce session loss, AZ failover invalidates all sessions in the failed AZ)
- NIST: SC-7, CP-7, SC-36
- Related concerns: ephemeral (in-process state survives until process recycle — undermines the immutable-infra story)

**Pattern: In-process state in the application tier preventing horizontal scale.**

- Severity: medium to high depending on what's in-process (cached authorization decisions, partial OAuth flows, rate-limiter counters)
- NIST: SC-7, CP-7
- Related concerns: integrity (cache coherency across instances), authenticity (cached authorization decisions stale across instances)

**Pattern: GDPR data-residency unstated — artifacts describe multi-region capability without specifying which data classes are bound to which regions.**

- Disposition: uncertainty or blocked
- prerequisite_evidence: "Data-residency policy — per-data-class region binding, cross-region replication policy with lawful-basis attestation for any extra-EEA flow, residency-enforcement mechanism (application-tier routing, database-level constraints, or compensating contractual control)"

**Pattern: Tech plan claims multi-region but artifacts don't specify topology — active-active vs. active-passive vs. standby, write-conflict policy, failover trigger.**

- Disposition: uncertainty or blocked
- Severity: medium when blocked
- prerequisite_evidence: "Multi-region topology specification — active configuration, write-conflict policy, failover trigger, expected failover RTO/RPO, and which data classes replicate cross-region"

**Pattern: Cross-region replication for audit logs is asynchronous with unspecified lag.**

- Severity: medium to high (cross-references Non-Repudiation; audit gap during regional failover is a breach-detection blind spot)
- NIST: AU-9(2), SC-36
- Related concerns: non_repudiation, immutability

**Pattern: Service mesh topology unspecified — artifacts assert mTLS without describing identity issuance, certificate rotation, or trust-domain boundaries.**

- Disposition: uncertainty
- prerequisite_evidence: "Service mesh topology — identity issuance (SPIFFE/SPIRE or equivalent), trust-domain boundary, certificate lifetime and rotation, mesh-to-non-mesh edge behavior"

## Common capability patterns

**Pattern: Multi-AZ active-active for the authentication service with stateless application tier and externalized session store.** Scope must specify which dependencies are also multi-AZ (database, cache, broker, secrets store) and which are not.

**Pattern: Stateless application tier with all session state externalized to a redundant store.** Maturity ladder typically `designed` from tech plan; `implemented` requires service configuration or IaC evidence; `operationalized` requires evidence of successful AZ failover.

**Pattern: Region-pinned PII storage with explicit cross-region replication policy.** Higher maturity requires evidence of the policy enforcement mechanism (database-level residency, application-tier routing) plus residency monitoring.

**Pattern: Service mesh with SPIFFE workload identity and per-namespace trust-domain isolation.** Cross-cuts Authenticity for the identity-issuance half; mention via `related_concerns`.
