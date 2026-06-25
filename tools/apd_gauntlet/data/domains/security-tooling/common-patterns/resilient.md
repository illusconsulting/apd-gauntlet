# Security tooling common patterns — Resilient

These are illustrative templates, not all-inclusive. Use them to calibrate analytical style, severity assignment per the security-tooling rubric, and NIST/ATT&CK mapping habits. The specialist agent's analytical checklist still drives the actual analysis — this file calibrates how findings and capabilities should look once written.

Resilience in security tooling is asymmetric: degradation should fail SAFE for the offensive surface (no commands issued without authorization gates) and should fail OPEN for the audit surface (no command issued without audit; if audit cannot record, the command should not run).

## Common finding patterns

**Pattern: No circuit breaker on the result-data store from the orchestrator; result-store degradation blocks operator console reads and may block new command issuance.**

- Severity: high (operational impact during an active engagement is severe; cross-references Availability for the SLO consequence)
- NIST: SI-13, SC-5, CP-13
- D3FEND: D3-SBV at the orchestrator for store-health monitoring
- Related concerns: availability (orchestrator-to-store SLO), distributed (store topology)

**Pattern: Implant callback retry policy is fixed-interval without jitter, exponential backoff, or per-target-network aggregate cap; listener outage produces synchronized callback storms that DoS target networks.**

- Severity: high (rubric: operational AND target-network impact; the latter is the security-tooling-specific ethical/contractual concern)
- NIST: SI-13(4), SC-5(1), SC-5(2)
- Related concerns: availability (the implant-side half), distributed (multi-listener disperses the storm)

**Pattern: No bulkhead between interactive operator command paths and batch/scheduled operations (scheduled scans, BAS campaign runs, scheduled implant heartbeat polling) — a runaway batch can starve interactive command issuance during an active engagement.**

- Severity: high (interactive engagement quality directly affected; latency-sensitive operations like real-time pivoting are blocked)
- NIST: SC-5, SC-6, SI-13
- Related concerns: availability (bulkhead-less topology amplifies any availability finding), distributed (bulkhead often requires distinct deployment unit)

**Pattern: Plugin failure cascades to platform failure — an exception in plugin code unwinds the orchestrator process; no per-plugin restart, no plugin-failure isolation.**

- Severity: high (plugin reliability is the platform's reliability; plugin-supply-chain quality drift becomes a platform-availability concern)
- NIST: SI-13, SC-5, SC-39, CP-12 (Safe Mode)
- Related concerns: confidentiality (plugin sandbox), authenticity (plugin signing), availability (per-plugin SLO)

**Pattern: No replay protection on commands — implant accepts a replayed command (captured by target-side observer, replayed by attacker) as new and re-executes.**

- Severity: high (target-side defender can replay sensitive operations; insider attacker with channel access can re-trigger destructive operations)
- NIST: SC-23 (Session Authenticity), SI-7, SC-23(3)
- ATT&CK: T1557 (Adversary-in-the-Middle) for replay capture; T1078 for replay-as-valid-account
- D3FEND: D3-MA (Message Authentication) with replay nonces
- Related concerns: authenticity (command signature with replay nonce), integrity (command-execution idempotency)

**Pattern: Audit-pipeline back-pressure absent — when the audit consumer is unreachable, the orchestrator continues issuing commands; audit entries are dropped or held in unbounded in-memory buffer.**

- Severity: high to critical (depending on whether the rubric's "Audit trail loss" critical clause applies — if commands continue while audit cannot record, the platform is operating outside legal-defensibility envelope)
- NIST: AU-5, AU-5(1), AU-5(2), CP-13
- D3FEND: D3-SBV for audit-availability monitoring
- Related concerns: non_repudiation (audit completeness), immutability (audit durability), availability (audit-pipeline SLO)

**Pattern: No graceful degradation specified for orchestrator-to-listener communication failure during an active engagement — operator sees errors, no queued-for-retry behavior, in-flight commands lost.**

- Severity: high (operational; engagement-quality impact; potential for command duplication if operator retries manually without idempotency)
- NIST: CP-12, CP-13, SI-17
- Related concerns: integrity (idempotency on command issuance), availability (component SLO)

**Pattern: Tech plan describes "retries" without specifying backoff, jitter, budget, idempotency-key interaction, or target-network aggregate-rate caps.**

- Disposition: uncertainty or blocked
- prerequisite_evidence: "Retry policy specification — per-component backoff curve, jitter strategy, total budget per dependency, idempotency-key interaction, target-network aggregate-rate caps for implant-side retry, behavior on budget exhaustion (fail-fast, queue, dead-letter)"

## Common capability patterns

**Pattern: Circuit breaker on every outbound dependency from the orchestrator (result-store, audit-pipeline, listener, plugin runtime, customer-egress endpoints) with documented thresholds and half-open recovery behavior.** Capability scope must enumerate covered dependencies; absent dependencies become partial-coverage findings.

**Pattern: Audit-pipeline backpressure with the orchestrator refusing new command issuance when the audit consumer is unreachable beyond a bounded buffer.** This is the security-tooling-specific resilience pattern — failing CLOSED for the offensive surface when audit is unavailable. Cross-cuts Non-Repudiation; mention via `related_concerns`.

**Pattern: Per-plugin process isolation with supervisor-based restart on plugin failure; plugin failure does not unwind the orchestrator.** Higher maturity when plugin-failure rate is monitored as a supply-chain-quality signal.

**Pattern: Command replay protection via per-command nonces verified at the implant.** Cross-cuts Authenticity and Integrity; the nonce is the load-bearing replay-prevention mechanism.

**Pattern: Bulkheaded thread pools or deployment-level isolation between interactive command paths and scheduled/batch paths.** Higher maturity when chaos-engineering or game-day evidence exercises the bulkhead boundary.

**Pattern: Implant retry policy with full-jitter exponential backoff, per-implant retry budget, AND per-target-network aggregate-rate cap.** Cross-cuts Availability and the security-tooling-specific target-network impact concern; mention via `related_concerns`.
