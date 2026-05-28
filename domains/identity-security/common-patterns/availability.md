# Identity security common patterns — Availability

These are illustrative templates, not all-inclusive. Use them to calibrate analytical style, severity assignment per the identity security rubric, and NIST/ATT&CK mapping habits. The specialist agent's analytical checklist still drives the actual analysis — this file calibrates how findings and capabilities should look once written.

## Common finding patterns

**Pattern: No rate limit on /authorize, /token, password-grant, MFA-challenge, MFA-enrollment, or credential-recovery endpoints.**

- Severity: high (credential stuffing, password spray, MFA fatigue / push bombing, and account-takeover surfaces all open). Escalates to critical when paired with weak password policy, absent breached-password check, or absent CAPTCHA fallback.
- NIST: SC-5, SC-5(1), SC-5(2), AC-7 (unsuccessful login attempts), IA-5
- ATT&CK: T1110 (Brute Force) and sub-techniques T1110.001 (Password Guessing), T1110.003 (Password Spraying), T1110.004 (Credential Stuffing); T1621 (Multi-Factor Authentication Request Generation)
- Related concerns: authenticity (the credential-policy half), non_repudiation (failed-auth audit completeness)

**Pattern: Session-store backpressure absent — Redis/PostgreSQL session store can be saturated by authentication storm, taking the entire IdP offline.**

- Severity: high (session-store DoS is the dominant IdP-availability failure mode; saturation cascades to every dependent application losing auth)
- NIST: SC-5, SC-6 (resource availability), SI-13
- Related concerns: distributed (session-store topology), resilient (degraded-mode auth)

**Pattern: Queue depth unbounded on the authentication-flow pipeline (async event publication on authn events, async session-write, async audit-emit).**

- Severity: medium to high (queue saturation produces silent loss of either audit, session state, or downstream provisioning — all three are different findings depending on which queue is saturated)
- NIST: AU-4, AU-5, SC-5, SI-13
- Related concerns: non_repudiation (audit queue), distributed (queue topology)

**Pattern: No degraded-mode authentication specified — if the credential-verification path (LDAP, database, upstream IdP) is unavailable, the IdP returns 500 to every request.**

- Severity: high (cascading total outage; IdP is the topmost availability dependency for every RP — no graceful fallback path defined)
- NIST: CP-12, CP-13, SI-13, IA-2
- Related concerns: resilient (this finding's recommendation overlaps the IdP-outage degradation pattern in Resilient), distributed (backend topology)

**Pattern: Single-region IdP deployment with a 99.9%+ availability target asserted to downstream RPs.**

- Severity: high (target undeliverable from a single region under typical cloud-provider zone SLA; the IdP becomes the platform's lowest-SLO dependency)
- NIST: CP-7, SC-36, CP-9
- Related concerns: distributed (multi-region topology), resilient (failover orchestration)

**Pattern: Signing-key availability vs. latency tradeoff unaddressed — HSM in one region, IdP serves traffic from three; signing-operation latency drives p99 token-issuance latency through the floor.**

- Severity: medium to high depending on token-issuance SLO (high when sub-second p99 is asserted)
- NIST: SC-12, SC-12(3), CP-7
- Related concerns: distributed (HSM topology), resilient (caching of recent signatures is rarely safe — the tradeoff is regional HSMs)

**Pattern: Health checks on the IdP are shallow — TCP-port check or basic HTTP 200, not "can sign a test token" / "can verify a test password" / "can reach LDAP backend."**

- Severity: medium (shallow health checks mask backend degradation; load balancer continues routing to instances that cannot complete auth)
- NIST: SI-13, CP-10
- Related concerns: resilient (health-check is the input to circuit-breaker decisions)

**Pattern: Tech plan describes "rate limiting" generically without specifying per-endpoint thresholds, identity dimension, time window, or behavior on breach.**

- Disposition: blocked or uncertainty
- prerequisite_evidence: "Rate-limit policy specification — per-endpoint thresholds for /authorize, /token, password-grant, MFA-challenge, recovery endpoints; identity dimension (per-user, per-client_id, per-IP, per-tenant); time window; behavior on breach (reject vs. queue vs. CAPTCHA escalation vs. lockout); retry-after semantics; and any compensating bot-management layer"

## Common capability patterns

**Pattern: Per-endpoint rate limits with identity-dimensioned thresholds, separate limits per IP and per identity, explicit behavior on breach.** Capability scope must enumerate covered endpoints; all credential-touching surfaces in the consequential-actions list must appear in scope or the capability degrades to a partial-coverage finding.

**Pattern: Externalized session store with horizontal scale and backpressure (Redis Cluster with maxmemory-policy noeviction on session keys, plus circuit-breaker on writes).** Higher maturity when chaos-engineering evidence shows the IdP survives session-store partial unavailability.

**Pattern: Degraded-mode authentication: read-only auth using cached session tokens when backend directory is unavailable, with explicit user notification.** Cross-cuts Resilient; mention via `related_concerns`. Maturity ladder requires a documented runbook plus tested failover.

**Pattern: Multi-region IdP topology with regional HSMs, regional session stores, and active-active token issuance.** Higher maturity requires evidence of cross-region session replication policy, regional-failover RTO/RPO targets, and audit-pipeline cross-region durability.

**Pattern: SLO and error-budget framework with separate SLOs for /authorize, /token, /userinfo, and SAML SSO endpoints; burn-rate alerting wired to oncall.** `designed` from tech plan; `implemented` requires monitoring configuration; `operationalized` requires evidence of error-budget-driven engineering decisions.
