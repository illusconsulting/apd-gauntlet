# Identity security common patterns — Confidentiality

These are illustrative templates, not all-inclusive. Use them to calibrate analytical style, severity assignment per the identity security rubric, and NIST/ATT&CK mapping habits. The specialist agent's analytical checklist still drives the actual analysis — this file calibrates how findings and capabilities should look once written.

## Common finding patterns

**Pattern: Token signing key stored in application configuration (env var, mounted Secret, on-disk PEM) rather than HSM/KMS.**

- Severity: critical (signing-key compromise yields universal token forgery — see Critical rubric clause on token signing key compromise)
- NIST: SC-12, SC-12(1), SC-12(3), SC-13, SC-28, SC-28(1)
- ATT&CK: T1552.001 (Credentials in Files); T1606.001 (Forge Web Credentials: Web Cookies); T1606.002 (Forge Web Credentials: SAML Tokens)
- Related concerns: authenticity (the signing key IS the identity assertion trust anchor), ephemeral (key rotation cadence and revocation channel), immutability (key-lifecycle event log)

**Pattern: Password hash algorithm weaker than argon2id / bcrypt with appropriate cost (PBKDF2 below 600k iterations, SHA-512crypt, plain SHA-256, MD5).**

- Severity: high to critical depending on the hash strength and the user-population value (critical when the population would be targeted for credential stuffing across high-value external surfaces)
- NIST: IA-5, IA-5(1)(c), SC-13
- ATT&CK: T1110.002 (Brute Force: Password Cracking); T1003 (OS Credential Dumping) for the hash-extraction precondition
- Related concerns: ephemeral (rotation on algorithm change requires forced password reset), non_repudiation (audit completeness on hash-algorithm migrations)

**Pattern: Refresh tokens stored as cleartext on the IdP side rather than hashed-at-rest.**

- Severity: high (refresh-token store dump is equivalent to long-lived session impersonation for every active user; hashing-at-rest is the proportional control)
- NIST: SC-28, SC-28(1), IA-5
- Related concerns: ephemeral (refresh-token rotation cadence collapses the cleartext-storage window), integrity (hash verification must be constant-time)

**Pattern: SAML assertion encryption absent on attribute-release flows that carry personal data or special-category data.**

- Severity: medium to high (assertion contents visible to any TLS-terminating intermediary, MitM with weak validation, or RP-side log aggregator; SAML Security Considerations §6.2 recommends encryption for sensitive attribute release)
- NIST: SC-8, SC-8(1), SC-12, AC-4
- Related concerns: authenticity (the assertion signature does not protect confidentiality), integrity (JWE/XML-Encrypt configuration affects parser surface)

**Pattern: JWT access tokens or ID tokens carry excessive PII claims — full profile embedded.**

- Severity: medium to high depending on token lifetime, audience scope, and which claims (a 1-hour bearer token carrying email, full name, DOB, employee ID exposes that PII to every downstream RP, log aggregator, proxy, and APM in the request path)
- NIST: SC-8, AC-4, SC-28, AU-11
- Related concerns: ephemeral (token-lifetime amplifies claim exposure), integrity (over-broad claims defeat least-privilege downstream)

**Pattern: Recovery channel (email, SMS) carries the recovery token in cleartext URL parameters.**

- Severity: high (recovery URL appearing in browser history, referer headers, mobile-app interception, mail-server logs, MTA bounce traces; recovery token is single-use-takeover material)
- NIST: SC-8, IA-5, SI-11 (error handling — URL-in-log behavior)
- Related concerns: ephemeral (recovery token lifetime), authenticity (recovery-flow identity-proofing strength)

**Pattern: LDAP/AD bind credentials in IdP application config without rotation, audit-on-fetch, or read-only enforcement.**

- Severity: medium to high depending on bind privilege (read-only bind is medium; bind permitting writes is high)
- NIST: IA-5, IA-5(1), AC-2, SC-12
- ATT&CK: T1078.002 (Valid Accounts: Domain Accounts); T1552 (Unsecured Credentials)
- Related concerns: ephemeral (rotation cadence), authenticity (directory-backend trust)

**Pattern: Tech plan describes "encryption at rest" generically without specifying which crown-jewel classes, KMS/HSM topology, key separation between primary store and backups, or DEK/KEK hierarchy.**

- Disposition: blocked or uncertainty
- prerequisite_evidence: "Encryption-at-rest policy — per-crown-jewel-class encryption posture (signing keys, password hashes, MFA seeds, session store, audit log, backups), KMS/HSM topology, DEK/KEK hierarchy, key-separation discipline between primary store and its backup, rotation cadence per key class, and the audit-on-decrypt control"

## Common capability patterns

**Pattern: Token signing keys held in HSM/KMS (PKCS#11 or cloud KMS) with the IdP holding only key handles; sign-operations go to the HSM.** Maturity ladder: `designed` from tech plan; `implemented` requires HSM/KMS provider evidence; `tested` requires evidence of forced rotation; `operationalized` requires alerting on signing-key-access anomalies.

**Pattern: Password hashes stored with argon2id at parameter set tuned to the threat model (memory cost, time cost, parallelism documented).** Capability scope must state the parameters and the migration discipline for legacy weaker-hash records (rehash-on-login pattern).

**Pattern: Refresh tokens stored as hashes (SHA-256 of token value plus per-token salt) with constant-time comparison on validation.** Higher maturity requires evidence that token-rotation-on-use is paired with reuse-detection.

**Pattern: JWE for sensitive ID-token claims, SAML assertion encryption for personal-data attribute release.** Cross-cuts Authenticity for the encryption-key trust chain.

**Pattern: PII minimization in token claims — tokens carry subject identifier and authorization scope only; full profile resolved via /userinfo on demand.** Capability scope should enumerate which claims are released by issuer policy and which are guarded behind /userinfo.

**Pattern: Recovery channels deliver short-lived single-use tokens via a separate confirmation step (token in email body must be re-entered, not clicked) to avoid URL-leak channels.** Higher maturity requires evidence that recovery completion requires a step-up to AAL2 minimum.
