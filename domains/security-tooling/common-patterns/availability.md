# Security tooling common patterns — Availability

These are illustrative templates, not all-inclusive. Use them to calibrate analytical style, severity assignment per the security-tooling rubric, and NIST/ATT&CK mapping habits. The specialist agent's analytical checklist still drives the actual analysis — this file calibrates how findings and capabilities should look once written.

Security-tooling availability has an unusual feature: implant retry behavior must NOT impose denial-of-service pressure on TARGET networks during platform outage. Aggressive retry against a target's network during operator-side platform downtime is both an operational and an ethical concern, and frequently a customer-MSA violation.

## Common finding patterns

**Pattern: No rate limit on operator console authentication; credential-stuffing and password-spray surface uncapped.**

- Severity: medium (rubric clause: "Rate-limiting absent on operator console authentication"); escalates to high when paired with weak MFA or absent MFA on admin operators
- NIST: SC-5, SC-5(1), SC-5(2), AC-7 (Unsuccessful Login Attempts), IA-5
- ATT&CK: T1110 (Brute Force) with sub-techniques T1110.003 (Password Spraying), T1110.004 (Credential Stuffing); T1621 (MFA Request Generation) if MFA-fatigue is the goal
- Related concerns: authenticity (operator MFA policy), non_repudiation (failed-auth audit completeness)

**Pattern: Implant callback retry has no jitter and no exponential backoff; listener outage produces synchronized callback storms when the listener returns, with secondary DoS pressure on target networks during the outage.**

- Severity: high (operational AND target-network impact; the latter is the security-tooling-specific concern not present in conventional API domains)
- NIST: SC-5, SI-13, CP-13
- D3FEND: D3-NTSA (Network Traffic Signature Analysis) for catching the storm at the listener
- Related concerns: resilient (the backoff strategy is the resilient-pattern half), distributed (multi-listener topology disperses the storm)

**Pattern: No SLO declared for engagement-active services (operator console, orchestrator, listener); no error budget, no degradation policy.**

- Severity: medium (operational visibility gap; cannot prioritize reliability work on the services that are most critical to an active engagement)
- NIST: CP-2 (Contingency Plan), CP-2(3), SI-13
- Detail must enumerate which customer-MSA uptime commitments imply an SLO, and which regulatory frameworks (SOC 2 CC7.4, NIS2 Article 21) require operational-availability discipline

**Pattern: Single-region deployment for SaaS-delivered tooling with multiple customers in different jurisdictions; regional outage produces total platform outage for all customers.**

- Severity: high (rubric: blast radius is per-customer cumulative; data-residency obligations may also be violated by failover topology)
- NIST: CP-7 (Alternate Processing Site), SC-36, CP-9
- Related concerns: distributed (the topology change is owned by Distributed), confidentiality (residency for failover region)

**Pattern: Audit pipeline single-broker, single-sink, no buffer between application and broker; broker outage produces silent audit loss.**

- Severity: critical (rubric clause: "Audit trail loss"; security-tooling pipeline failure is presumption-of-misuse to regulators and customers)
- NIST: AU-4 (Audit Storage Capacity), AU-5 (Response to Audit Logging Process Failures), AU-5(1), AU-5(2)
- D3FEND: D3-SBV at the audit consumer
- Related concerns: non_repudiation (audit completeness), immutability (audit durability), resilient (audit-buffer behavior under broker outage)

**Pattern: Health checks on the listener are TCP port checks or HTTP-200 checks only; do not verify the listener can accept and authenticate a synthetic implant callback end-to-end.**

- Severity: medium (shallow health checks mask listener degradation; load balancer continues sending implants to instances that can accept connections but cannot complete authentication)
- NIST: SI-13, CP-10, SC-5
- Related concerns: resilient (health-check is the input to circuit-breaker decisions)

**Pattern: Command-execution queue depth unbounded — operator bulk-broadcast can starve the orchestrator's command-issuance path.**

- Severity: medium to high depending on shared-vs-isolated queue topology
- NIST: SC-5, SC-6 (Resource Availability), SI-13
- Related concerns: resilient (bulkhead pattern)

**Pattern: Tech plan describes "highly available C2" generically without specifying listener redundancy, orchestrator failover, audit-pipeline durability, or active-active vs active-passive topology.**

- Disposition: blocked or uncertainty
- prerequisite_evidence: "Availability topology specification — per-component redundancy (listener, orchestrator, audit-pipeline, result-store), active configuration (active-active vs active-passive), failover trigger and RTO/RPO targets, expected behavior of in-flight engagements during failover"

## Common capability patterns

**Pattern: Per-component SLO and error budget for operator console, orchestrator, listener, and audit pipeline, with separate burn-rate alerting per component.** `designed` from tech plan; `implemented` requires monitoring configuration; `operationalized` requires evidence of error-budget-driven engineering decisions on the security-tooling-specific components.

**Pattern: Bounded queue depth on command-execution with explicit backpressure to the operator UI ("bulk broadcast paused — backlog at N").** Higher maturity when bulk-broadcast paths are bulkheaded from interactive command paths.

**Pattern: Implant callback retry with full-jitter exponential backoff, retry budget cap per implant per hour, and aggregate cap per target network per minute.** Cross-cuts Resilient; the target-network-aggregate cap is the security-tooling-specific control.

**Pattern: Listener health-check synthetically exercises the full callback-authenticate-deliver path with a canary implant identity.** Maturity higher when the canary path is itself audited so the canary's check events are distinguishable from real implant traffic.
