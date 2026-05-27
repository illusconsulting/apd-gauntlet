# API security common patterns — Availability

These are illustrative templates, not all-inclusive. Use them to calibrate analytical style, severity assignment per the API security rubric, and NIST/ATT&CK mapping habits. The specialist agent's analytical checklist still drives the actual analysis — this file calibrates how findings and capabilities should look once written.

## Common finding patterns

**Pattern: No rate limit on authentication, password-reset, MFA enrollment, or account-recovery endpoints (OWASP API4 + API2 amplifier).**

- Severity: high (credential-stuffing, password-spray, MFA-fatigue, and account-takeover surfaces all open). Escalates to critical when paired with weak password policy or absent CAPTCHA fallback.
- NIST: SC-5, SC-5(1), SC-5(2), AC-7 (unsuccessful login attempts), IA-5
- ATT&CK: T1110 (Brute Force) and sub-techniques T1110.001 (Password Guessing), T1110.003 (Password Spraying), T1110.004 (Credential Stuffing); T1621 (MFA Request Generation)
- Related concerns: authenticity (the credential-policy half), non_repudiation (failed-auth audit completeness)

**Pattern: Unbounded request body size — no `max_request_size` or per-endpoint body cap (OWASP API4).**

- Severity: medium to high depending on parser behavior (a JSON parser allocating proportional to input size is the bigger risk than a streaming parser)
- NIST: SC-5, SC-5(1), SI-10
- Related concerns: integrity (oversize payloads bypassing schema enforcement that runs after parse)

**Pattern: No timeout on outbound calls to third-party APIs; thread-pool exhaustion possible during vendor degradation.**

- Severity: high (vendor slow-down cascades to total request-handler exhaustion; cannot be remediated mid-incident without restart)
- NIST: SC-5, SI-13, CP-13
- Related concerns: resilient (circuit-breaker and bulkhead patterns), distributed (request-handler topology)

**Pattern: SLO and error budget undeclared for consequential paths (authentication, payment, PII-read).**

- Severity: medium (cannot verify the system meets implicit availability commitments; cannot prioritize reliability work)
- NIST: CP-2, CP-2(3), SI-13
- Detail must enumerate which contractual or regulatory commitments imply an SLO (e.g., uptime clauses in subscription agreements, PCI-DSS Requirement 12 on operational availability).

**Pattern: Single-region deployment with 99.9% or higher availability target.**

- Severity: high (target likely undeliverable from single region given typical cloud-provider SLA structure)
- NIST: CP-7, SC-36, CP-9
- Related concerns: distributed (this finding's recommendation points to a topology change owned by Distributed)

**Pattern: Health checks specified as TCP port checks or basic HTTP-200 checks only.**

- Severity: medium (shallow health checks mask dependency degradation; the load balancer continues sending traffic to instances that can accept connections but cannot complete requests)
- NIST: SI-13, CP-10
- Related concerns: resilient (health-check is the input to circuit-breaker decisions)

**Pattern: Tech plan describes "rate limiting" generically without specifying per-endpoint thresholds, identity dimension (per-user, per-IP, per-token), or behavior on limit breach.**

- Disposition: blocked or uncertainty
- prerequisite_evidence: "Rate limit policy specification — per-endpoint thresholds, identity dimension, time window, behavior on breach (reject, queue, degrade), retry-after semantics, and any compensating bot-management layer"

## Common capability patterns

**Pattern: Per-endpoint rate limits with identity-dimensioned thresholds (per-user, per-IP, per-token) and explicit behavior on breach.** Capability scope must enumerate covered endpoints; consequential-action endpoints (auth, password-reset, payment) must all appear in scope or the capability degrades to a partial-coverage finding.

**Pattern: Bounded request size and timeout discipline applied at the edge and re-enforced at each service hop.** Higher maturity when middleware-level enforcement is in evidence rather than per-handler.

**Pattern: SLO and error-budget framework for consequential paths with dashboards and burn-rate alerting.** `designed` from tech plan; `implemented` requires monitoring configuration; `operationalized` requires evidence of error-budget-driven engineering decisions.

**Pattern: Bot-management layer in front of authentication and account-recovery surfaces.** Cross-cuts Authenticity for the credential-policy half; mention via `related_concerns`.
