# PBM common patterns — Resilient

These are illustrative templates, not all-inclusive. Use them to calibrate analytical style, severity assignment per the PBM rubric, and NIST/ATT&CK mapping habits. The specialist agent's analytical checklist still drives the actual analysis — this file calibrates how findings and capabilities should look once written.

Resilience in a PBM is sized around predictable demand spikes that hit the pharmacy ingress path: seasonal flu and vaccination surges, COVID and respiratory-virus waves, and the structural Jan-1 / Oct-15 open-enrollment transitions when tens of millions of members move between plans and refill their entire chronic regimen in the first weeks of new coverage. Brittle behavior at the ingress queue, the eligibility cache, or the PA workflow engine under these spikes converts directly to denied or delayed dispensing and to SLA penalties under plan-sponsor agreements aligned with 42 CFR §423.505. The load-bearing surfaces are the pharmacy-submission queue and its backpressure semantics, the eligibility-and-accumulator cache layer (cold-cache behavior on Jan-1 is the canonical failure mode), and the PA workflow engine where retry storms on vendor degradation are the dominant outage shape.

## ATT&CK + D3FEND defensive mapping

This goal defends against (or is exploited by) the following MITRE ATT&CK techniques. Each citation is included only where the apd-control-mappings high-confidence-bar discipline is met; we deliberately omit techniques that only adjacently relate to this goal.

**ATT&CK techniques:**

- **T1499** (Endpoint Denial of Service) — backpressure exploitation against pharmacy ingress or PA workflow, where a flood of submission or status-poll requests forces the resilience surface (queue, cache, breaker) into its failure mode
- **T1499.003** (Application Exhaustion Flood) — adjudication-thread or PA-worker exhaustion via legitimate-shape requests (eligibility lookups, claim submits) that bypass network-layer rate limits and consume application capacity
- **T1496** (Resource Hijacking) — capacity drain via legitimate-looking traffic from a compromised pharmacy account or partner integration, where the abusive workload is indistinguishable from peak-season load at the network layer

**D3FEND counters:**

- **D3-RAPA** (Resource Access Pattern Analysis) — counters T1496 / T1499 / T1499.003 by detecting abusive request patterns at the application layer (per-pharmacy submission rates, per-member status-poll cadence) that backpressure and circuit-breaker controls then act on
- **D3-NTA** (Network Traffic Analysis) — counters T1499 at the ingress edge by characterizing the shape of submission and PA-status traffic and feeding rate-limit and shed-load decisions upstream of the application tier

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
- prerequisite_evidence: "Retry-policy specification covering: (1) the retry policy per service-to-service edge (which caller, which callee, which request class); (2) the retry budget per request class (max attempts, max total elapsed, max concurrent in-flight retries); (3) the backoff strategy (fixed, exponential, jittered) and the jitter distribution; (4) idempotency-key handling for retry-safe operations (eligibility re-check, PA-status poll, claim resubmit) and the safe-to-retry classification per operation; (5) the interaction with circuit-breaker state — whether retries are suppressed when the breaker is half-open or open, and how breaker state is observed by the retry layer"

## Common capability patterns

**Pattern: Circuit breaker on every external dependency with documented thresholds.** Capability scope must enumerate which dependencies are covered; caveats for any not in evidence.

**Pattern: Read-only degraded mode for portal during write-tier outage.** Maturity ladder: `designed` from tech plan, `implemented` requires application code or feature flag evidence, `tested` requires test report or game day evidence.

**Pattern: Bulkheaded thread pools separating adjudication from reporting.** Often higher confidence when application configuration is in evidence.

## prerequisite_evidence

These are the canonical multi-clause asks that unblock blocked-on-evidence findings in the Resilient lens. An operator MUST provide every sub-element listed; partial answers leave the finding blocked.

**Circuit-breaker specification:**

- **prerequisite_evidence:** "Circuit-breaker specification covering: (1) each circuit-breaker location in the topology (inbound at API gateway, outbound at every external-dependency client — eligibility vendor, drug-pricing vendor, PBM-to-PBM coordination, e-prescribing intermediary); (2) the trip threshold (failure rate, latency percentile, consecutive-failure count) and the recovery threshold (success-probe count, half-open admission rate) for each location; (3) the trip-event audit pipeline (which subsystem records the trip, which dashboard surfaces it, which on-call rotation is paged) so that breaker events are observable and not silent; (4) the downstream-failure-isolation behavior when the breaker is open — whether the caller fails fast, falls back to a cached or degraded response, or surfaces an explicit soft-deny to the pharmacy/member"

**Graceful-degradation modes:**

- **prerequisite_evidence:** "Graceful-degradation specification covering: (1) the per-feature degradation plan — read-only adjudication mode on write-tier outage, cached-eligibility mode on eligibility-vendor outage with cache-age bound, deferred PA queueing on PA-engine outage with member-facing status messaging, and the equivalent plan for any other ingress-critical surface; (2) the SLO impact of each degraded mode (claim-decision latency, eligibility-staleness bound, PA-decision latency) so plan-sponsor SLA exposure under degradation is quantified; (3) the operator surface that activates and deactivates each mode (feature flag, runbook step, automatic trigger), the authentication/authorization required to flip it, and the audit record produced when it is flipped"
