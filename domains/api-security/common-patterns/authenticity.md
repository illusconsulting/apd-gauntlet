# API security common patterns — Authenticity

These are illustrative templates, not all-inclusive. Use them to calibrate analytical style, severity assignment per the API security rubric, and NIST/ATT&CK mapping habits. The specialist agent's analytical checklist still drives the actual analysis — this file calibrates how findings and capabilities should look once written.

## Common finding patterns

**Pattern: AAL (Authenticator Assurance Level) undeclared — artifacts do not state whether the system targets NIST SP 800-63B AAL1, AAL2, or AAL3, nor on which surfaces.**

- Severity: medium when blocked (cannot evaluate MFA-strength findings without the target); high when the target is implicit and the implementation falls short
- NIST: IA-2, IA-2(1), IA-2(2), IA-2(8)
- Related concerns: ephemeral (authenticator lifetime per AAL), non_repudiation (audit per-AAL-event)

**Pattern: MFA optional on administrative surfaces (OWASP API2).**

- Severity: critical when on PII or payment admin; high when on operational admin
- NIST: IA-2(1), IA-2(2), AC-6, AC-6(2)
- ATT&CK: T1078 (Valid Accounts); T1556 (Modify Authentication Process) when MFA-disable is the attack
- Related concerns: non_repudiation (admin actions without MFA produce weaker actor attribution)

**Pattern: MFA bypass via SMS fallback on a primary phishing-resistant factor.**

- Severity: high (effective AAL downgrade; SMS interception via SIM-swap is a documented incident pattern)
- NIST: IA-2(1), IA-2(2), IA-2(8)
- ATT&CK: T1621 (Multi-Factor Authentication Request Generation); T1556.006 (MFA Bypass)

**Pattern: Service-to-service inside the cluster uses shared bearer tokens, not mTLS or workload identity.**

- Severity: high (lateral-movement amplification; no identity binding on the credential)
- NIST: SC-8(1), SC-23, IA-3, IA-9 (service identification and authentication)
- ATT&CK: T1557 (Adversary-in-the-Middle) with in-cluster rationale; T1078
- Related concerns: ephemeral (shared-token rotation), confidentiality (in-cluster PII in transit)

**Pattern: OAuth flow allows implicit grant or omits PKCE on public client.**

- Severity: high (credential-leakage exposure via browser history, referer headers, or mobile-app interception)
- NIST: IA-2, IA-5, IA-5(2)
- ATT&CK: T1550.001 (Application Access Token); T1528 (Steal Application Access Token)
- Related concerns: integrity (authorization-code interception affecting downstream identity assertions)

**Pattern: Container images deployed without signature verification or admission control.**

- Severity: high (supply-chain compromise vector; OWASP A06:2021 Vulnerable and Outdated Components amplification)
- NIST: SI-7, SR-4, SR-4(3), SR-11
- ATT&CK: T1195.002 (Supply Chain Compromise: Software Supply Chain)
- Related concerns: ephemeral (immutable infra requires authentic images), immutability (artifact provenance history)

**Pattern: Webhook payloads from vendor accepted without signature verification.**

- Severity: high (forged webhook can inject malicious adjudication input — payment confirmations, subscription state, refund triggers)
- NIST: SC-23, IA-3(1), SI-10
- Related concerns: integrity (input validation, route to Integrity finding for the malformed-input concern)

**Pattern: Tech plan describes "authenticated APIs" generically without specifying mechanism, token lifetime, or validation procedure.**

- Disposition: uncertainty or blocked
- prerequisite_evidence: "API authentication specification — mechanism per endpoint (OAuth, mTLS, signed JWT, API key, session cookie), token lifetime, validation procedure including signature algorithm and key source, replay-protection mechanism"

## Common capability patterns

**Pattern: mTLS across service mesh with SPIFFE/SPIRE workload identity.** Scope must enumerate which services are confirmed; expect caveats for legacy services not yet onboarded.

**Pattern: FIDO2/WebAuthn for administrative access plus phishing-resistant MFA for end-user PII surfaces.** Cross-cuts Ephemeral via the credential lifetime; mention via `related_concerns`.

**Pattern: Signed container images with cosign or Notation, enforced by admission control.** Maturity depends on whether the admission-control policy is in evidence and whether the build pipeline produces signatures as part of CI/CD.

**Pattern: SLSA Level 2+ build provenance for production deployments with provenance verification at deploy time.** Higher maturity requires CI/CD configuration evidence plus the verification step at the admission-control or deploy boundary.
