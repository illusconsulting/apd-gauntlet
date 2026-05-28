# PBM common patterns — Resilient

These are illustrative templates, not all-inclusive. Use them to calibrate analytical style, severity assignment per the PBM rubric, and NIST/ATT&CK mapping habits. The specialist agent's analytical checklist still drives the actual analysis — this file calibrates how findings and capabilities should look once written.

Resilience in a PBM is sized around predictable demand spikes that hit the pharmacy ingress path: seasonal flu and vaccination surges, COVID and respiratory-virus waves, and the structural Jan-1 / Oct-15 open-enrollment transitions when tens of millions of members move between plans and refill their entire chronic regimen in the first weeks of new coverage. Brittle behavior at the ingress queue, the eligibility cache, or the PA workflow engine under these spikes converts directly to denied or delayed dispensing and to SLA penalties under plan-sponsor agreements aligned with 42 CFR §423.505. The load-bearing surfaces are the pharmacy-submission queue and its backpressure semantics, the eligibility-and-accumulator cache layer (cold-cache behavior on Jan-1 is the canonical failure mode), and the PA workflow engine where retry storms on vendor degradation are the dominant outage shape.

## Common finding patterns

**Pattern: No circuit breaker on PHI-containing vendor call (eligibility, drug pricing).**

- Severity: high (vendor degradation can cascade to total adjudication outage)
- NIST: SI-13, SC-5, CP-13
- Cross-reference: any Availability finding on vendor SLA

**Pattern: Retry policy without jitter on the event bus consumer.**

- Severity: medium (thundering herd risk on partial broker failure)
- NIST: SI-13(4), SC-5(1)

**Pattern: Timeout missing on database call in adjudication path.**

- Severity: high (single slow query can hang adjudication threads, cascading to thread pool exhaustion)
- NIST: SI-13, SC-5

**Pattern: No graceful degradation specified for eligibility vendor outage.**

- Severity: high (vendor outage produces total adjudication outage)
- NIST: CP-12, CP-13, SI-17
- Detail must specify what would happen today (system errors) and what should happen (cached eligibility, fail-open with downstream verification, or explicit soft-deny with patient communication).

**Pattern: Tech plan describes "retries" without specifying backoff, jitter, or budget.**

- Disposition: uncertainty
- prerequisite_evidence: "Retry policy specification — backoff curve, jitter, total budget per dependency, idempotency interaction"

## Common capability patterns

**Pattern: Circuit breaker on every external dependency with documented thresholds.** Capability scope must enumerate which dependencies are covered; caveats for any not in evidence.

**Pattern: Read-only degraded mode for portal during write-tier outage.** Maturity ladder: `designed` from tech plan, `implemented` requires application code or feature flag evidence, `tested` requires test report or game day evidence.

**Pattern: Bulkheaded thread pools separating adjudication from reporting.** Often higher confidence when application configuration is in evidence.
