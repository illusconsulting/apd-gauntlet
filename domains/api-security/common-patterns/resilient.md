# API security common patterns — Resilient

These are illustrative templates, not all-inclusive. Use them to calibrate analytical style, severity assignment per the API security rubric, and NIST/ATT&CK mapping habits. The specialist agent's analytical checklist still drives the actual analysis — this file calibrates how findings and capabilities should look once written.

## Common finding patterns

**Pattern: No circuit breaker on outbound calls to third-party APIs — payment processor, OAuth identity provider, vendor SaaS, mail relay.**

- Severity: high (vendor degradation cascades to user-facing latency and request-handler exhaustion; OWASP API10 amplification)
- NIST: SI-13, SC-5, CP-13
- Cross-reference: any Availability finding on outbound timeout discipline; merged finding carries both concerns

**Pattern: Retry policy without jitter on the event-bus consumer or webhook delivery.**

- Severity: medium (thundering-herd risk on partial broker failure; failed-webhook retry storm during partner-side incident)
- NIST: SI-13(4), SC-5(1)
- Related concerns: integrity (idempotency interaction — retry without idempotency is duplicate side-effect risk)

**Pattern: No bulkhead between consumer-facing API paths and administrative or batch paths.**

- Severity: high (an admin bulk-export or analytics query can starve the customer-facing thread pool; CDE-scope batch jobs can starve interactive payment paths)
- NIST: SC-5, SC-6 (resource availability), SI-13
- Related concerns: availability (bulkhead-less topology amplifies any availability finding), distributed (bulkhead implementation often requires distinct deployment unit)

**Pattern: Third-party API failure cascades to user-facing 5xx response (OWASP API10).**

- Severity: high (graceful-degradation absence converts vendor incident to platform incident; user-facing error rate tracks vendor uptime)
- NIST: CP-12, CP-13, SI-17
- Detail must specify what would happen today (unhandled exception, generic 500, vendor error proxied) and what should happen (cached fallback, queued retry with user notification, explicit feature-disable with degraded-mode banner)

**Pattern: No detection of refresh-token reuse — replay of an already-rotated refresh token produces a new access token instead of revoking the entire token family.**

- Severity: high (refresh-token theft is the dominant token-loss vector in mobile and SPA contexts; reuse-detection is the OAuth2.1 hardening that converts the attack into a detection signal)
- NIST: IA-5, IA-5(13), SI-4
- Related concerns: authenticity (token-issuance trust chain), ephemeral (refresh-token lifetime)

**Pattern: No graceful degradation specified for identity-provider outage.**

- Severity: critical to high (IDP outage produces total authentication outage if no fallback; high if degraded read-only mode is documented but not implemented)
- NIST: CP-12, CP-13, IA-2
- Related concerns: availability (IDP-dependency SLO), distributed (IDP replication)

**Pattern: Tech plan describes "retries" without specifying backoff, jitter, budget, or idempotency-key interaction.**

- Disposition: uncertainty
- prerequisite_evidence: "Retry policy specification — backoff curve, jitter strategy, total budget per dependency, idempotency-key interaction, behavior on budget exhaustion (fail-fast vs. queue vs. dead-letter)"

## Common capability patterns

**Pattern: Circuit breaker on every outbound dependency with documented thresholds and half-open recovery behavior.** Capability scope must enumerate covered dependencies; absent dependencies become partial-coverage findings.

**Pattern: Retry-with-jitter and explicit per-dependency retry budget on inter-service and outbound calls.** Maturity ladder: `designed` from tech plan; `implemented` requires client-library configuration; `tested` requires chaos-engineering or game-day evidence.

**Pattern: Bulkheaded thread pools or deployment-level isolation between customer-facing and administrative paths.** Higher maturity when deployment topology evidences the bulkhead boundary.

**Pattern: Refresh-token reuse detection with full-family revocation on reuse signal.** Cross-cuts Authenticity for the token-issuance half and Ephemeral for the rotation cadence; mention via `related_concerns`.
