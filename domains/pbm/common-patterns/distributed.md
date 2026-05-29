# PBM common patterns — Distributed

These are illustrative templates, not all-inclusive. Use them to calibrate analytical style, severity assignment per the PBM rubric, and NIST/ATT&CK mapping habits. The specialist agent's analytical checklist still drives the actual analysis — this file calibrates how findings and capabilities should look once written.

Distribution in a PBM is not an optimization — it is a contractual SLO and a clinical-safety property. Regional adjudication failures cascade directly to dispensing in the affected pharmacy network, and most plan-sponsor master service agreements require multi-AZ resilience at minimum and multi-region failover for the adjudication path, with CMS Part D §423.505(b) downstream-entity expectations layered on top. The load-bearing surfaces are the claim-router fan-out (pharmacy ingress to adjudication-engine instances), the PDE-submission pipeline (where partition or batch-loss silently breaks CMS reconciliation), and the formulary-update fanout that must reach every adjudication shard before the published effective date.

## ATT&CK + D3FEND defensive mapping

This goal defends against (or is exploited by) the following MITRE ATT&CK techniques. Each citation is included only where the apd-control-mappings high-confidence-bar discipline is met; we deliberately omit techniques that only adjacently relate to this goal.

**ATT&CK techniques:**

- **T1485** (Data Destruction) — destruction of a regional adjudication-state store, audit substrate, or formulary replica
- **T1565.001** (Stored Data Manipulation) — at-rest tampering of cross-region replicated data, including divergent replica states
- **T1078** (Valid Accounts) — lateral movement across regional zones via legitimate cross-region credentials

**D3FEND counters:**

- **D3-NTA** (Network Traffic Analysis) — counters cross-region anomalies (T1078 lateral movement) by detecting baseline-divergent traffic
- **D3-LFAM** (Local File Access Mediation) — counters T1485 / T1565.001 by enforcing tenant-and-region scoping at the data tier

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
- prerequisite_evidence: "Multi-region topology specification — (1) region topology (active-active, active-passive, follow-the-sun) per service; (2) cross-region data-replication strategy and lag SLO; (3) consistency model per data class (strong, eventual, bounded staleness); (4) failover plan including replication-lag tolerance at failover, write conflict policy, and failover trigger"

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

## prerequisite_evidence

When a finding in this lens is dispositioned blocked or uncertainty for missing distribution evidence, the operator unblock-pack should provide multi-clause specifications, not single-line attestations.

**Failure-domain isolation:** (1) blast-radius diagram for a single-region failure of each critical service (adjudication, PHI store, PA engine, eligibility); (2) tenant-and-region isolation guarantees if the PBM is multi-tenant; (3) the load-shedding plan when a regional dependency degrades.
