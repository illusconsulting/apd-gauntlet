# Identity security common patterns — Authenticity

These are illustrative templates, not all-inclusive. Use them to calibrate analytical style, severity assignment per the identity security rubric, and NIST/ATT&CK mapping habits. The specialist agent's analytical checklist still drives the actual analysis — this file calibrates how findings and capabilities should look once written.

## Common finding patterns

**Pattern: AAL (Authenticator Assurance Level) per surface undeclared — artifacts do not state whether the IdP targets NIST SP 800-63B AAL1, AAL2, or AAL3 for admin, user, and machine surfaces.**

- Severity: medium when blocked (cannot evaluate MFA-strength findings without the target); high when the target is implicit and the implementation falls short (e.g., admin surface implicitly AAL3 but only password+SMS implemented)
- NIST: IA-2, IA-2(1), IA-2(2), IA-2(6), IA-2(8)
- Related concerns: ephemeral (authenticator lifetime per AAL), non_repudiation (audit per-AAL-event), distributed (MFA consistency across regions)

**Pattern: MFA optional on administrative surfaces (IdP admin console, federation-trust editor, signing-key-rotation surface).**

- Severity: critical (admin-tier compromise is the boundary case where Authenticity, Non-Repudiation, and Immutability findings converge — see Critical rubric clause on compromised admin account)
- NIST: IA-2(1), IA-2(2), AC-6, AC-6(2), AC-6(7)
- ATT&CK: T1078 (Valid Accounts); T1556 (Modify Authentication Process)
- Related concerns: non_repudiation (admin actions without MFA produce weaker actor attribution)

**Pattern: SMS or voice fallback permitted on phishing-resistant MFA enrollments.**

- Severity: high (effective AAL downgrade; SMS interception via SIM-swap is a documented incident pattern that defeats the WebAuthn/FIDO2 target)
- NIST: IA-2(1), IA-2(2), IA-2(8) — note 800-63B §5.1.3 specifically deprecates SMS for new AAL3 implementations
- ATT&CK: T1621 (Multi-Factor Authentication Request Generation); T1556.006 (MFA Bypass)
- Related concerns: ephemeral (SMS-channel credential lifetime undefined), resilient (SMS-provider outage and the fallback-to-fallback question)

**Pattern: Service-to-service authentication inside the IdP cluster uses shared bearer tokens, not mTLS or workload identity.**

- Severity: high (lateral-movement amplification; no identity binding on the credential; IdP-tier compromise is the gate to credential-store compromise)
- NIST: SC-8(1), SC-23, IA-3, IA-9 (service identification and authentication)
- ATT&CK: T1557 (Adversary-in-the-Middle) with in-cluster rationale; T1078
- Related concerns: ephemeral (shared-token rotation), confidentiality (in-cluster credential material in transit)

**Pattern: OAuth client authentication is `client_secret_basic` or `client_secret_post` for confidential clients; private_key_jwt, client_secret_jwt, and tls_client_auth (mTLS) not offered as alternatives.**

- Severity: medium to high (shared-secret-only client auth is the rotation-fragile authenticator class; the modern alternatives — RFC 7523 JWT bearer for client auth, RFC 8705 mTLS client auth — eliminate the leak class)
- NIST: IA-2, IA-5, SC-12, IA-3(1)
- Related concerns: ephemeral (client_secret rotation pain motivates the migration), integrity (signature-based client auth provides per-request binding)

**Pattern: OIDC flow allows implicit grant (`response_type=id_token` or `response_type=token`) for new client registrations.**

- Severity: high (implicit grant is deprecated by OAuth 2.1; credential-leakage exposure via browser history, referer headers, mobile-app interception)
- NIST: IA-2, IA-5, IA-5(2)
- ATT&CK: T1550.001 (Application Access Token); T1528 (Steal Application Access Token)
- Related concerns: integrity (authorization-code-with-PKCE is the only secure flow for public clients), confidentiality (token-in-URL-fragment leak surface)

**Pattern: SAML IdP allows unsigned AuthnRequest or unsigned SP metadata; the trust relies on TLS only.**

- Severity: high (SP impersonation surface, downgrade attack surface; SAML 2.0 Security Considerations §6.1 recommends both transport and message-level signature)
- NIST: SI-7, IA-3, IA-3(1), SC-23
- ATT&CK: T1199 (Trusted Relationship)
- Related concerns: integrity (signature validation discipline on the inbound AuthnRequest), distributed (SP metadata refresh and trust-on-first-use risk)

**Pattern: Audit-log entries on consequential actions are not cryptographically signed; integrity rests on storage-substrate controls only.**

- Severity: medium to high depending on the substrate (high when audit is in a multi-tenant store with elevated read access; medium when audit substrate is WORM-locked)
- NIST: AU-9, AU-9(3), AU-10 (non-repudiation), SI-7
- ATT&CK: T1070 (Indicator Removal); T1565 (Data Manipulation)
- Related concerns: non_repudiation (signed audit closes the attribution-tampering gap), immutability (the substrate-controls half)

**Pattern: Federation trust is established without contact attestation, domain-control validation on the redirect_uri host, or human approval workflow — the SP self-asserts its identity at registration.**

- Severity: high (malicious-RP onboarding surface; the registered SP can request scopes from any user lured to /authorize)
- NIST: IA-2, IA-3(1), AC-2, SR-3
- ATT&CK: T1199 (Trusted Relationship); T1078
- Related concerns: non_repudiation (audit on federation-trust establishment), immutability (federation-trust history)

**Pattern: Tech plan describes "authenticated APIs" generically without specifying mechanism per surface, token lifetime, or validation procedure including signature algorithm and key source.**

- Disposition: uncertainty or blocked
- prerequisite_evidence: "Authentication specification per surface — mechanism (OAuth bearer, mTLS, signed JWT, API key, session cookie), token lifetime, signature-algorithm pin, key-source (JWKS endpoint, embedded key, KMS handle), replay-protection mechanism (nonce, jti, timestamp window), and the AAL/FAL claim associated with the surface"

## Common capability patterns

**Pattern: FIDO2/WebAuthn for administrative access plus phishing-resistant MFA for end-user PII surfaces; SMS fallback permitted only as recovery-only step-down, never as primary.** Capability scope must enumerate which surfaces and which user populations; AAL target per surface must be in evidence.

**Pattern: mTLS across the IdP service mesh with SPIFFE/SPIRE workload identity; every IdP-internal call carries cryptographic workload identity, not shared tokens.** Scope must enumerate covered services; legacy services not yet onboarded become caveats.

**Pattern: OAuth client authentication via private_key_jwt or tls_client_auth (mTLS) as the default for new clients; client_secret_basic only for legacy.** Higher maturity when the registration UX defaults to private_key_jwt and client_secret is opt-in with a deprecation notice.

**Pattern: SAML signed AuthnRequest and signed SP metadata required for all federation trust relationships; metadata refresh validates the publisher's signing chain.** Cross-cuts Integrity for the signature-validation discipline.

**Pattern: Cryptographically signed audit entries (per-entry signature plus hash-chained per stream, with chain heads anchored externally to a separate trust domain or external timestamp authority).** Cross-cuts Non-Repudiation and Immutability; mention via `related_concerns`. Maturity ladder: `designed` from tech plan; `implemented` requires code/IaC evidence; `operationalized` requires chain-verification at audit-read time.

**Pattern: Federation trust onboarding via approval workflow with domain-control validation, contact attestation, and per-trust audit anchor; trust modifications require re-approval.** Higher maturity when the workflow integrates with security-team review for trusts with high-blast-radius scope.
