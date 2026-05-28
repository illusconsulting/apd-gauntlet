# Identity security common patterns — Resilient

These are illustrative templates, not all-inclusive. Use them to calibrate analytical style, severity assignment per the identity security rubric, and NIST/ATT&CK mapping habits. The specialist agent's analytical checklist still drives the actual analysis — this file calibrates how findings and capabilities should look once written.

## Common finding patterns

**Pattern: No circuit breaker on the IdP-to-user-store path (LDAP, AD, upstream IdP for federation chains, user database).**

- Severity: high (user-store degradation cascades to user-facing latency and request-handler exhaustion; without circuit-breaker, a slow LDAP backend takes down every IdP worker by tying up its connection pool)
- NIST: SI-13, SC-5, CP-13
- Cross-reference: any Availability finding on outbound timeout discipline; merged finding carries both concerns

**Pattern: Password-reset endpoint retry storm — no rate-limit + no exponential backoff + email-provider degradation produces unbounded retry pressure on the mail-relay credential and SMTP gateway.**

- Severity: medium to high (operational outage of the recovery channel; cascades to user-reported "cannot recover account" support flood)
- NIST: SI-13(4), SC-5, SC-5(1)
- Related concerns: availability (mail-relay SLO), integrity (idempotency on reset-token issuance)

**Pattern: No detection of refresh-token reuse — replay of an already-rotated refresh token produces a new access token instead of revoking the entire token family.**

- Severity: high (refresh-token theft is the dominant token-loss vector in mobile and SPA contexts; reuse-detection per OAuth 2.1 §6.1 converts the attack into a detection signal that fully revokes the token family)
- NIST: IA-5, IA-5(13), SI-4
- ATT&CK: T1550.001 (Use Alternate Authentication Material: Application Access Token); T1528 (Steal Application Access Token)
- Related concerns: authenticity (token-issuance trust chain), ephemeral (refresh-token lifetime)

**Pattern: No graceful degradation specified for upstream-IdP outage during federation flows — the artifacts do not describe what happens to in-flight SAML/OIDC federation when the upstream IdP is unreachable.**

- Severity: high (the IdP becomes the failure proxy for every upstream; the user sees an opaque error and has no fallback path)
- NIST: CP-12, CP-13, IA-2
- Related concerns: availability (federation-hop SLO), distributed (upstream-IdP redundancy)

**Pattern: Chaos-engineering or game-day evidence on federation flows absent — no documented test of "what happens when SAML metadata refresh fails," "what happens when JWKS endpoint returns stale keys," "what happens when SCIM provisioning lags by 1 hour."**

- Severity: medium (resilience is asserted but not tested; the synthesizer escalates if combined with high-severity findings on availability or distributed)
- NIST: CP-4, CP-4(1), IR-3 (incident-response testing)
- Related concerns: availability (SLO under failure), distributed (failover validation)

**Pattern: Retry policy on outbound calls (to upstream IdPs, to SCIM targets, to webhook subscribers) without jitter or budget.**

- Severity: medium (thundering-herd risk on partial failure; webhook-retry storm during subscriber-side incident)
- NIST: SI-13(4), SC-5(1)
- Related concerns: integrity (idempotency on retried operations — federation provisioning duplication risk)

**Pattern: Bulkhead absent between user-facing auth paths and administrative paths — admin bulk-export, audit-log query, or federation-config edit can starve the customer-facing thread pool.**

- Severity: high (admin operations should not be able to take down user-facing auth; bulkhead-less topology means an admin running a wide audit query during peak login can degrade /authorize latency)
- NIST: SC-5, SC-6, SI-13
- Related concerns: availability (bulkhead-less topology amplifies any availability finding), distributed (bulkhead implementation often requires distinct deployment unit)

**Pattern: Tech plan describes "retries" without specifying backoff, jitter, budget, or idempotency-key interaction for federation-provisioning calls.**

- Disposition: uncertainty
- prerequisite_evidence: "Retry policy specification — backoff curve, jitter strategy, total budget per dependency (per-upstream-IdP, per-SCIM-target, per-webhook-subscriber), idempotency-key interaction, behavior on budget exhaustion (fail-fast vs. queue vs. dead-letter), and any compensating-action on permanent failure"

## Common capability patterns

**Pattern: Circuit breaker on every outbound dependency from the IdP (user-store backend, upstream IdP, SCIM target, webhook subscriber, email/SMS provider) with documented thresholds and half-open recovery.** Capability scope must enumerate covered dependencies; absent dependencies become partial-coverage findings.

**Pattern: Refresh-token rotation with family-revocation on reuse detection per OAuth 2.1 §6.1.** Cross-cuts Authenticity for the token-issuance half and Ephemeral for the rotation cadence; mention via `related_concerns`. Higher maturity requires evidence of the reuse-detection alerting wired into incident response.

**Pattern: Graceful degradation for backend-directory unavailability — IdP serves cached authentications with a degraded-mode banner, refuses new credential changes, and notifies the user.** Cross-cuts Availability; mention via `related_concerns`. Maturity requires runbook plus tested degraded-mode behavior.

**Pattern: Bulkheaded thread pools or deployment-level isolation between user-facing auth, admin console, and federation-provisioning workers.** Higher maturity when deployment topology evidences the bulkhead boundary at the pod/process level.

**Pattern: Chaos-engineering game days exercising signing-key rotation, JWKS-endpoint failure, upstream-IdP outage, and SCIM-target outage on a regular cadence.** `designed` from runbook only; `tested` requires postmortem evidence; `operationalized` requires the cadence to be on the SRE calendar.
