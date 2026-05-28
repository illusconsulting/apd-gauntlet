# PBM common patterns — Availability

These are illustrative templates, not all-inclusive. Use them to calibrate analytical style, severity assignment per the PBM rubric, and NIST/ATT&CK mapping habits. The specialist agent's analytical checklist still drives the actual analysis — this file calibrates how findings and capabilities should look once written.

Availability failure in a PBM is felt at the pharmacy counter in real time: claim adjudication is a synchronous transaction with a typical 3-to-5-second budget, and an outage converts directly to dispensing delays, member out-of-pocket exposure when pharmacies fall back to cash-pay, and SLA-penalty exposure under plan-sponsor agreements that commonly stipulate four- or five-nines on the adjudication path. CMS Part D operational standards under 42 CFR §423.505 also tie availability to plan-sponsor downstream-entity oversight, so prolonged outages can escalate into Star Ratings and CMS audit posture, not just contractual penalties. The load-bearing surfaces are pharmacy ingress (NCPDP switch and direct-submit), real-time eligibility and accumulator lookup, and the prior-authorization decision engine — each of which sits on a synchronous dispensing decision.

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
- prerequisite_evidence: "Vendor SLA for [vendor name] eligibility service"

**Pattern: Health checks specified as TCP port checks only.**

- Severity: medium (shallow health checks mask real degradation)
- NIST: SI-13, CP-10

## Common capability patterns

**Pattern: Multi-AZ deployment of the adjudication engine with cross-AZ failover.** Scope must specify which components are multi-AZ; caveats for any that are not.

**Pattern: Backup encryption with daily verification.** Maturity ladder: `designed` from tech plan, `implemented` requires backup configuration, `operationalized` requires backup test runbook and last-test date.

**Pattern: SLO and error budget framework for the claim adjudication path.** Often `designed` from tech plan; higher maturity requires monitoring dashboard evidence.
