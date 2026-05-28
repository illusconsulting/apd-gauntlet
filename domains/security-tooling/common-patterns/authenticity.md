# Security tooling common patterns — Authenticity

These are illustrative templates, not all-inclusive. Use them to calibrate analytical style, severity assignment per the security-tooling rubric, and NIST/ATT&CK mapping habits. The specialist agent's analytical checklist still drives the actual analysis — this file calibrates how findings and capabilities should look once written.

Authenticity in security tooling has unusual stakes: identity binding determines whether a command came from an authorized operator (and is therefore lawful), whether a callback came from a legitimate implant (and is therefore trusted with results), and whether a plugin came from a trusted author (and is therefore safe to load with platform privileges).

## Common finding patterns

**Pattern: Operator MFA optional on admin or engagement-initiation roles.**

- Severity: critical (rubric: "Operator authentication bypass to admin or operator console" applies when MFA-optional is paired with admin privilege; admin without MFA is one phish from compromise)
- NIST: IA-2(1), IA-2(2), IA-2(6) (Access to Accounts — Separate Device), AC-6, AC-6(2)
- ATT&CK: T1078 (Valid Accounts); T1556 (Modify Authentication Process); T1621 (MFA Request Generation)
- D3FEND: D3-MFA (Multi-Factor Authentication), specifically FIDO2/WebAuthn for phishing-resistance
- Related concerns: non_repudiation (admin actions without MFA produce weaker actor attribution), ephemeral (session lifetime amplifies any MFA gap)

**Pattern: FIDO2/WebAuthn unavailable for high-privilege operator functions — signing-key access, ROE modification, audit-read, plugin install — TOTP is the strongest available factor.**

- Severity: high (TOTP is phishable; high-privilege functions on a security platform should require phishing-resistant authentication)
- NIST: IA-2(1), IA-2(8), IA-5(2)
- ATT&CK: T1621; T1556.006 (MFA Bypass)
- D3FEND: D3-MFA with phishing-resistance qualifier
- Related concerns: non_repudiation (the actor-attribution chain), ephemeral (step-up authentication for consequential ops)

**Pattern: Implant mutual authentication absent — listener accepts any TLS connection presenting a valid CA-signed certificate; implant trusts any listener with a valid CA-signed certificate.**

- Severity: critical (rubric: "Implant callback channel substitution"; any listener with a valid public CA cert can pose as the platform; any client with a public CA cert can pose as an implant)
- NIST: IA-3 (Device Identification and Authentication), IA-3(1), SC-23, SC-23(5)
- ATT&CK: T1557 (Adversary-in-the-Middle); T1090 (Proxy) abused defensively
- D3FEND: D3-CP (Certificate Pinning), D3-CCSI (Client-Server Payload Profiling)
- Related concerns: confidentiality (channel encryption), integrity (per-command signature as defense-in-depth)

**Pattern: Plugin signature verification not enforced — plugin install accepts unsigned modules, or verifies signature against a list that includes a permissive "any-CA" trust root.**

- Severity: critical (rubric: "Plugin code execution by untrusted source"; supply-chain compromise vector)
- NIST: SI-7, SI-7(1), SI-7(6), SR-4 (Provenance), SR-4(3), SR-11 (Component Authenticity), SR-11(1)
- ATT&CK: T1195.002 (Software Supply Chain Compromise); T1505 (Server Software Component)
- D3FEND: D3-SU (Software Update with verification), D3-EAL (Executable Allowlisting)
- Related concerns: integrity (plugin manifest enforcement), non_repudiation (plugin-load audit), immutability (plugin install records)

**Pattern: Audit log entries are signed by an HMAC key the orchestrator itself controls — operator who compromises the orchestrator can forge entries; signing key not isolated to a separate trust domain.**

- Severity: high (rubric: "Audit log content forgery" — the signature does not protect against the most likely compromise scenario; signing-key-isolation failure)
- NIST: AU-9, AU-9(2), AU-9(3), AU-10 (Non-Repudiation), AU-10(2), SC-12
- D3FEND: D3-MA with key custody in a separate trust domain
- Related concerns: non_repudiation (the merged record carries both), immutability (audit signing key lifecycle)

**Pattern: Engagement-record signature at engagement-start uses the operator's session token as the signing material — the binding to ROE attestation is only as strong as the session.**

- Severity: high (session compromise yields ability to forge engagement-start records retroactively; CFAA-evidence-base weakened)
- NIST: AU-10, SC-12, IA-5
- Related concerns: ephemeral (session lifetime), non_repudiation (engagement-record provenance), immutability (engagement-start records)

**Pattern: SSO integration trusts identity-provider assertions without binding the assertion to the operator's WebAuthn credential or platform-side device-attestation.**

- Severity: high (compromise of the IDP yields full operator impersonation; the platform delegates authenticity entirely to the IDP with no defense-in-depth)
- NIST: IA-2, IA-8 (Identification and Authentication — Non-Organizational Users), IA-5(2)
- ATT&CK: T1199 (Trusted Relationship); T1078.004 (Cloud Accounts) when IDP-side compromise enables cloud-scope impersonation
- Related concerns: ephemeral (IDP-issued token lifetime), distributed (IDP redundancy)

**Pattern: Tech plan describes "authenticated operator console" generically without specifying mechanism, MFA factor classes, step-up authentication for consequential operations, or session-binding posture.**

- Disposition: blocked or uncertainty
- prerequisite_evidence: "Operator authentication specification — primary factor class, MFA factor classes and per-role policy, step-up authentication triggers (engagement initiation, signing-key access, audit-read, plugin install), session-binding mechanism (cookie attributes, device binding, IP binding), SSO integration trust model"

## Common capability patterns

**Pattern: FIDO2/WebAuthn required for admin and engagement-initiation roles; TOTP acceptable for read-only operator roles; recovery flow requires identity-proofing rather than SMS or email link.** Capability scope must enumerate per-role factor requirements; partial coverage by role is a partial-coverage finding.

**Pattern: Mutual TLS with certificate pinning between implant and listener; per-engagement implant certificates issued from a per-engagement CA that is destroyed at engagement closure.** Cross-cuts Ephemeral (engagement-bounded CA lifetime) and Confidentiality (channel encryption); mention via `related_concerns`.

**Pattern: Plugin signing root in HSM or KMS, signatures verified at install AND at load-time, revocation enforced via transparency log or short-lived signature TTL.** Cross-cuts Integrity for the verification half; the signing-root custody is the load-bearing claim.

**Pattern: Audit log signed by a key held in a separate cloud account (or separate KMS in a different trust domain) from the orchestrator's runtime identity.** Cross-cuts Non-Repudiation and Immutability; the cross-trust-domain key custody is the load-bearing claim.

**Pattern: Engagement-record signature at engagement-start uses a per-operator FIDO2/WebAuthn attestation captured at the moment of ROE acceptance — the cryptographic binding includes the operator's possession factor.** Higher maturity than session-token-bound engagement records.

**Pattern: SSO integration with IDP-assertion-to-WebAuthn binding — the platform requires both a valid IDP assertion AND a fresh WebAuthn signature for consequential operations.** Defense-in-depth against IDP compromise.
