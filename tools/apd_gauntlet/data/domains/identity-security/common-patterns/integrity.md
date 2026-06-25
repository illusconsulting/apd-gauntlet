# Identity security common patterns — Integrity

These are illustrative templates, not all-inclusive. Use them to calibrate analytical style, severity assignment per the identity security rubric, and NIST/ATT&CK mapping habits. The specialist agent's analytical checklist still drives the actual analysis — this file calibrates how findings and capabilities should look once written.

## Common finding patterns

**Pattern: JWT signature verification accepts multiple algorithms by default; algorithm pinning absent (the library's allowlist is the union of all configured signers' algorithms).**

- Severity: critical when `alg:none` is reachable or HS256 verification is permitted against an RS256-issued token using the JWKS public key as the HMAC secret (the canonical RS256/HS256 confusion attack); high when the alg allowlist is broader than the issuing alg.
- NIST: SI-7, IA-2, IA-5(2), SC-13
- ATT&CK: T1606.001 (Forge Web Credentials: Web Cookies); T1550.001 (Use Alternate Authentication Material: Application Access Token)
- Related concerns: authenticity (the alg pin IS the token trust anchor), confidentiality (key-confusion turns a public key into a forgery oracle)

**Pattern: SAML signature verification susceptible to signature wrapping (XSW) — the validation library returns the parsed inner element after validating an outer envelope; the SP/IdP processes the inner element without re-verifying it is the signed region.**

- Severity: critical (arbitrary subject impersonation — see Critical rubric clause on SAML XSW)
- NIST: SI-7, SI-10, SC-13
- ATT&CK: T1606.002 (Forge Web Credentials: SAML Tokens)
- Related concerns: authenticity (the signature is the federation trust anchor), non_repudiation (XSW destroys assertion attribution)

**Pattern: JWKS rotation grace window unspecified — the verifier flips from old kid to new kid without overlap, producing a window during which in-flight tokens fail verification.**

- Severity: medium to high (availability impact during rotation; security risk when operators are tempted to extend old-kid lifetime to recover, defeating revocation discipline)
- NIST: SC-12, SC-12(2), SI-7, AU-12
- Related concerns: availability (rotation-window outage), ephemeral (rotation cadence), immutability (JWKS rotation history)

**Pattern: OAuth `state` parameter not validated, not bound to session, or omitted entirely on the authorization-code callback.**

- Severity: high (CSRF on OAuth authorization flow — RFC 9700 §4.7)
- NIST: SI-10, IA-2, AC-3
- ATT&CK: T1606 (Forge Web Credentials)
- Related concerns: authenticity (state binds the flow to the user agent), availability (CSRF can be used to fixate sessions)

**Pattern: OIDC nonce / c_hash / at_hash validation skipped — the ID token is accepted without binding to the authorization request or the issued access token.**

- Severity: high (token substitution attacks — an attacker-procured ID token from another user can be played to the RP if the nonce is not validated)
- NIST: SI-10, IA-2, SI-7
- Related concerns: authenticity (the nonce is the user-agent-to-ID-token binding)

**Pattern: SAML assertion-ID uniqueness store absent or insufficient retention — the SP/IdP cannot detect assertion replay within the NotOnOrAfter window.**

- Severity: high (assertion replay attacks — SAML 2.0 Security Considerations §6.4)
- NIST: SI-7, IA-2, SC-23, AU-12
- Related concerns: ephemeral (assertion lifetime tightening reduces the replay window), immutability (the assertion-ID store is itself an immutable-during-window class)

**Pattern: Idempotency missing on token-revocation endpoint — double-submit of revoke produces different observable outcomes (200 vs. 404 differential exposes which tokens were valid).**

- Severity: medium (information leak about token state; primary concern is the differential)
- NIST: SI-10, SC-5, AU-12
- Related concerns: availability (retry storms on revocation), non_repudiation (revocation event audit)

**Pattern: Mass-assignment on the user profile / self-service endpoint accepts writes to `is_admin`, `groups`, `roles`, `email_verified`, `mfa_enrolled`, or `email` without server-managed-field enforcement.**

- Severity: high to critical (writing `is_admin` is critical privilege escalation; writing `email` without re-verification enables account-recovery hijack; writing `email_verified=true` bypasses the verification gate)
- NIST: SI-10, AC-3, AC-6, AU-2
- ATT&CK: T1078 (Valid Accounts); T1098 (Account Manipulation); T1556 (Modify Authentication Process)
- Related concerns: authenticity (privilege-relevant fields enabling identity forgery), non_repudiation (mutation audit)

**Pattern: Federation attribute-mapping expression vulnerable to operator-precedence or string-concatenation injection — upstream claim `email_domain` is interpolated into a group-mapping rule string without parsing discipline.**

- Severity: high (privilege escalation via group/role mapping bug — see High rubric clause)
- NIST: SI-10, AC-3, AC-6
- ATT&CK: T1098 (Account Manipulation)
- Related concerns: authenticity (the claim-transformation is the federation trust chain in practice)

**Pattern: Tech plan describes "input validation" generically without specifying which claim/attribute fields, what schema, what error handling, and what behavior on schema-fail in the federation-claim ingestion path.**

- Disposition: blocked or uncertainty
- prerequisite_evidence: "Federation-claim ingestion specification — per-upstream-IdP claim allowlist, transformation expression language and its security posture, behavior on missing required claim, behavior on excess unrecognized claim, behavior on claim-type mismatch, and the audit anchor on transformation rule changes"

## Common capability patterns

**Pattern: JWT verification with explicit algorithm pin per issuer and explicit kid pin per JWKS rotation generation.** Capability scope: enumerate which RPs and which internal verifiers are confirmed; library defaults are typically the failure mode.

**Pattern: SAML signature validation using XSW-resistant library (e.g., python3-saml, OneLogin SAML toolkits in current versions) with the canonical-region re-verified against the parsed assertion.** Maturity tied to the library version and the explicit re-verification step in code review evidence.

**Pattern: OAuth state, nonce, c_hash, and at_hash all validated; PKCE enforced on every client class.** Higher maturity requires evidence that the validation is library-default-on rather than opt-in.

**Pattern: SAML assertion-ID replay store backed by a TTL-keyed cache with TTL ≥ assertion NotOnOrAfter window; replay events audited.** Cross-cuts Non-Repudiation and Immutability.

**Pattern: Server-managed-field allowlist on user profile mutations; the framework strips writes to `is_admin`, `groups`, `roles`, `email_verified` regardless of client input.** Capability scope must state whether the allowlist is centralized (framework-level) or per-endpoint (drift risk).

**Pattern: Federation claim-transformation rules expressed in a sandboxed, side-effect-free DSL with explicit allowlist of operations; transformation-rule changes require admin-tier approval and audit.** Higher maturity when changes go through GitOps with signed commits.
