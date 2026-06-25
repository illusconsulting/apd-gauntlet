# Identity security common patterns — Non-Repudiation

These are illustrative templates, not all-inclusive. Use them to calibrate analytical style, severity assignment per the identity security rubric, and NIST/ATT&CK mapping habits. The specialist agent's analytical checklist still drives the actual analysis — this file calibrates how findings and capabilities should look once written.

## Common finding patterns

**Pattern: Audit completeness on the IdP's consequential-action surface unverified — the consequential-actions list contains 50+ event classes; the artifacts confirm logging for only a subset (typically the obvious authn success/failure pair).**

- Severity: high (the IdP is the highest-stakes audit surface on the platform; partial coverage is the dominant real-world finding pattern, and any unaudited event class can hide breach activity)
- NIST: AU-2, AU-3, AU-3(1), AU-12
- Related concerns: authenticity (the actor field is only as strong as the authentication that produced it), immutability (audit storage discipline)

**Pattern: Token issuance audit lacks the token identifier (jti, opaque token ID) — log says "user X received a token" but does not link the token back to a later use.**

- Severity: high (forensic reconstruction of "which token did the attacker use, when did we issue it, and which other tokens were issued in the same session" is impossible without per-token identifiers)
- NIST: AU-3, AU-3(1), AU-12(1), AU-10
- Related concerns: integrity (the token identifier IS the lifecycle anchor), ephemeral (revocation requires the identifier)

**Pattern: Refresh-token rotation chain not auditable — the audit records issuance and revocation but does not link refresh-token generations within a token family.**

- Severity: medium to high (refresh-token reuse-detection investigations require the chain; without it, "which family was compromised" cannot be answered)
- NIST: AU-3, AU-12, IA-5
- Related concerns: resilient (reuse-detection events), ephemeral (rotation cadence)

**Pattern: OAuth consent grants audited at the grant event but not at use — "user X granted scopes S to client C" is logged, but per-use of the granted scope is not.**

- Severity: medium (the IdP can prove consent existed; cannot prove which uses occurred within the consent window without the per-use audit)
- NIST: AU-2, AU-3, AU-12
- Detail: GDPR Article 5(2) accountability defense for processing under the consent basis benefits from per-use audit when consent disputes arise.

**Pattern: SAML assertion log captures assertion issuance but does not capture the attribute-release set per assertion — privacy attestation for "which attributes were released to which SP at which time" is incomplete.**

- Severity: high (GDPR Article 5(1)(c) data-minimization defense requires evidence of what was actually released; this is the equivalent of record-level access logging for federation)
- NIST: AU-2, AU-3, AU-12, AC-21 (information sharing)
- Related concerns: confidentiality (attribute-release-policy enforcement), immutability (assertion-log retention)

**Pattern: Audit-read access uncontrolled — any operator role can search audit logs without separate authorization, and audit-of-audit-access (who searched what) is not recorded.**

- Severity: high (audit access is itself a consequential action — an insider with audit read can identify what's been observed and adjust behavior; SoD on audit access is a SOC 2 CC6.1 expectation)
- NIST: AU-9, AU-9(4), AU-9(6), AC-5 (separation of duties), AC-6
- Related concerns: authenticity (audit-role definition), confidentiality (audit content sensitivity inheritance — the audit carries credentials' worth of metadata)

**Pattern: Audit pipeline single-point-of-failure — single broker, single sink, no buffer between application and broker; broker outage produces silent audit loss.**

- Severity: high (audit availability is itself a regulatory requirement; broker outage produces a gap covering the very moments operators most need to investigate)
- NIST: AU-5, AU-5(1), AU-5(2), CP-7
- Related concerns: availability (audit-pipeline SLO), distributed (audit-broker topology), immutability (durability of the audit)

**Pattern: No time-source policy — audit timestamps are local system clocks with no NTP discipline, no drift bounds, no fallback to a secondary stratum.**

- Disposition: uncertainty or blocked
- prerequisite_evidence: "Audit time-source specification — NTP topology, time-source authority, drift bounds, behavior on time-source failure, timestamp precision (millisecond required for token-issuance audit, microsecond preferred), and the audit anchor on time-source-availability events themselves"

**Pattern: Break-glass procedure exists but break-glass actions are not specially audited beyond normal logging.**

- Severity: medium to high
- NIST: AU-3, AU-12(1), AC-6(9), AC-6(10)
- Detail: break-glass IdP-admin actions (key rotation under incident, mass session invalidation, mass MFA reset) should produce a distinguishable audit stream that automatically routes to security review independent of normal audit consumption.

**Pattern: Audit content sensitivity not classified — the audit log carries credentials, partial PII (request metadata: IP, user agent), and authentication metadata that re-identifies; access controls on the audit do not reflect its highest-sensitivity contents.**

- Severity: medium to high (audit-pipeline egress to SaaS log aggregators is a recurring inadvertent-exposure vector)
- NIST: AU-9, AC-3, SC-28, AC-21
- Related concerns: confidentiality (audit egress encryption and access controls), authenticity (audit-role definition)

## Common capability patterns

**Pattern: Per-action audit on every consequential-action surface (the full consequential-actions list) with actor, resource, action, purpose/justification, AAL/FAL claim, and outcome captured per-event.** Scope must enumerate covered surfaces against the consequential-actions list; caveats for any out-of-evidence — this is the dominant audit-coverage check.

**Pattern: Cryptographically signed audit entries with per-stream hash-chaining; chain heads anchored daily to an external trust domain (separate KMS, separate cloud account, or external timestamp authority).** Maturity depends on whether the chain is described in tech plan only or implemented in code/IaC; operationalized maturity requires evidence of chain verification at audit-read time and an alert on chain-break.

**Pattern: Audit-read access gated by a separate role from operational roles, with read events themselves audited (audit-of-audit-access).** Cross-cuts Authenticity for the role definition; mention via `related_concerns`. Higher maturity when audit-read also requires step-up authentication.

**Pattern: Time-source policy with NTP topology specified, drift bounds enforced, fallback to a secondary stratum on primary failure, time-source-availability events themselves audited, and millisecond-or-better timestamp precision on token-issuance events.** Higher maturity requires monitoring evidence on drift bounds.

**Pattern: Per-token audit linking issuance, refresh, revocation, and use events through the token identifier (jti for JWT, opaque ID for opaque tokens), with the refresh-token family chain explicit.** Cross-cuts Ephemeral; this is the foundational audit anchor for any token-loss investigation.
