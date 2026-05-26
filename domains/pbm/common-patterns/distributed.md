# PBM common patterns — Distributed

These are illustrative templates, not all-inclusive. Use them to calibrate analytical style, severity assignment per the PBM rubric, and NIST/ATT&CK mapping habits. The specialist agent's analytical checklist still drives the actual analysis — this file calibrates how findings and capabilities should look once written.

## Common finding patterns

**Pattern: Stateful component (e.g. Valkey, RDS primary) in single AZ.**

- Severity: high (PBM SLA contracts typically require AZ resilience)
- NIST: SC-7, CP-7, SC-36
- Cross-reference: any Availability finding on SLO consistency

**Pattern: Hidden SPOF in CI/CD — emergency deployment depends on single pipeline.**

- Severity: medium to high depending on RTO sensitivity
- NIST: CM-2(2), CP-2
- Related concerns: ephemeral (immutable infra readiness for redeployment)

**Pattern: Tech plan claims multi-region but artifacts don't specify topology — active-active versus active-passive versus standby.**

- Disposition: uncertainty or blocked
- prerequisite_evidence: "Multi-region topology specification — active configuration, write conflict policy, failover trigger"

**Pattern: Cross-region replication for audit logs is asynchronous with unspecified lag.**

- Severity: medium to high (cross-references Non-Repudiation tier 3)
- NIST: AU-9(2), SC-36
- Related concerns: non_repudiation, immutability

**Pattern: Adjudication CAP positioning unstated.**

- Disposition: uncertainty
- Detail: in pharmacy adjudication, the CAP choice has clinical consequences (continuing to adjudicate with stale formulary versus stopping adjudication). The artifacts must state the choice.

## Common capability patterns

**Pattern: Multi-AZ active-active adjudication engine with automated AZ failover.** Scope must specify which dependencies are also multi-AZ (database, cache, broker) and which are not.

**Pattern: Read replica topology across AZ with bounded replication lag.** Capability requires specifying the replication-lag bound and what enforces it.

**Pattern: Stateless application tier with all state externalized.** Maturity ladder typically `designed` from tech plan; `implemented` requires service configuration or IaC evidence.
