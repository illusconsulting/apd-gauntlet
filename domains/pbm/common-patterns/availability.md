# PBM common patterns — Availability

These are illustrative templates, not all-inclusive. Use them to calibrate analytical style, severity assignment per the PBM rubric, and NIST/ATT&CK mapping habits. The specialist agent's analytical checklist still drives the actual analysis — this file calibrates how findings and capabilities should look once written.

Availability failure in a PBM is felt at the pharmacy counter in real time: claim adjudication is a synchronous transaction with a typical 3-to-5-second budget, and an outage converts directly to dispensing delays, member out-of-pocket exposure when pharmacies fall back to cash-pay, and SLA-penalty exposure under plan-sponsor agreements that commonly stipulate four- or five-nines on the adjudication path. CMS Part D operational standards under 42 CFR §423.505 also tie availability to plan-sponsor downstream-entity oversight, so prolonged outages can escalate into Star Ratings and CMS audit posture, not just contractual penalties. The load-bearing surfaces are pharmacy ingress (NCPDP switch and direct-submit), real-time eligibility and accumulator lookup, and the prior-authorization decision engine — each of which sits on a synchronous dispensing decision.

## ATT&CK + D3FEND defensive mapping

This goal defends against (or is exploited by) the following MITRE ATT&CK techniques. Each citation is included only where the apd-control-mappings high-confidence-bar discipline is met; we deliberately omit techniques that only adjacently relate to this goal.

**ATT&CK techniques:**

- **T1499** (Endpoint Denial of Service) — request-volume attacks against pharmacy ingress, member portal, or PA workflow endpoints
- **T1498** (Network Denial of Service) — network-layer attacks against the PBM's public surface area
- **T1485** (Data Destruction) — destruction of formulary, PA-criteria, or adjudication-state data to disrupt claims processing

**D3FEND counters:**

- **D3-NTA** (Network Traffic Analysis) — counters T1498 by detecting volumetric anomalies
- **D3-RAPA** (Resource Access Pattern Analysis) — counters T1499 by detecting application-level abuse patterns

## Common finding patterns

**Pattern: Adjudication latency target not stated, but contractual SLA exists.**

- Severity: high (cannot verify the system meets contractual obligation)
- NIST: CP-2, CP-2(3)
- Detail must enumerate the contracts the SLA appears in, per intake brief.

**Pattern: DR RTO stated as 4 hours but no tested failover procedure documented.**

- Severity: high (RTO is aspirational without test evidence)
- NIST: CP-2, CP-4 (contingency plan testing), CP-7

**Pattern: Single-region deployment with 99.95% availability target.**

- Severity: high (target likely undeliverable from single region)
- NIST: CP-7, SC-36
- Related concerns: distributed (this finding's recommendation will point to a topology change owned by Distributed)

**Pattern: Vendor dependency (e.g. eligibility lookup) has no stated SLA in artifacts.**

- Disposition: blocked or uncertainty
- prerequisite_evidence: "Vendor SLA for [vendor name] eligibility service — (1) availability target (e.g. 99.95%) with measurement window and exclusion list; (2) per-transaction latency budget at p50 / p95 / p99; (3) error-rate ceiling and what counts as an error vs. a degraded-mode response; (4) credit / remedy schedule when targets are missed; (5) maintenance-window policy and notification SLA; (6) incident-communication SLA (time-to-first-notification, status-page commitment); (7) right-to-audit clause and last vendor SOC 2 / HITRUST attestation date; (8) the PBM-side fallback or degraded-mode plan when the vendor breaches the SLA, including the dispensing-decision policy at the pharmacy counter."

**Pattern: Health checks specified as TCP port checks only.**

- Severity: medium (shallow health checks mask real degradation)
- NIST: SI-13, CP-10

## Common capability patterns

**Pattern: Multi-AZ deployment of the adjudication engine with cross-AZ failover.** Scope must specify which components are multi-AZ; caveats for any that are not.

**Pattern: Backup encryption with daily verification.** Maturity ladder: `designed` from tech plan, `implemented` requires backup configuration, `operationalized` requires backup test runbook and last-test date.

**Pattern: SLO and error budget framework for the claim adjudication path.** Often `designed` from tech plan; higher maturity requires monitoring dashboard evidence.

## prerequisite_evidence

When an availability concern cannot be resolved from the artifacts in evidence, the specialist agent should mark the finding as blocked rather than speculating, and emit a prerequisite_evidence ask. The asks below are seeds — each one names every sub-element an operator must provide to unblock the finding. Use them verbatim or adapt them to the specific surface area in question, but preserve the multi-clause depth.

**SLO/SLI definition:** (1) each SLO defined for pharmacy ingress, member portal, PA workflow, PDE submission, and eligibility lookup, with the SLI that operationalizes it (request-success ratio, latency-at-percentile, freshness) and the measurement window; (2) error-budget definition per SLO, including how it is computed and over what rolling window; (3) burn-rate alerting thresholds at both fast-burn and slow-burn windows, and the on-call routing for each; (4) escalation chain when an SLO is at risk, including the decision authority for invoking degraded-mode policy at the pharmacy counter; (5) plan-sponsor contractual SLA mapping — which SLO maps to which contractual obligation, the gap between the internal SLO and the external SLA, and the credit-exposure model when the SLA is breached.

**Failure-domain analysis:** (1) failure-domain diagram showing which services share which fate (which workloads share a control plane, a database primary, a regional egress, a single vendor dependency, or a single identity provider); (2) blast-radius analysis per AZ, region, and zonal service (managed databases, managed Kafka, managed cache, managed object store), naming which user-facing workflows degrade and which fail closed; (3) DR plan with RTO and RPO stated per data class — PHI store, PDE pipeline, audit / non-repudiation store, formulary and PA-criteria store — and the last DR-test date for each, including a tabletop or live-failover artifact.

**Capacity headroom:** (1) headroom posture per critical path (pharmacy ingress, adjudication engine, eligibility lookup, PA decision engine), expressed as the ratio of provisioned capacity to observed peak and the alert threshold for utilization; (2) load-test artifacts that demonstrate the headroom at expected peak load — open-enrollment cutover (Jan 1), flu-season surge, and a mass-vaccination drive — including test methodology, scenario mix, and observed degradation points; (3) auto-scaling configuration with scaling-event audit, including the scale-up and scale-down policy, the cooldown window, the upper bound (so a surge cannot exhaust a regional quota), and the last 30 days of scaling-event logs showing the configuration behaves as expected under real traffic.
