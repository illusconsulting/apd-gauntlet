# PBM common patterns — Authenticity

These are illustrative templates, not all-inclusive. Use them to calibrate analytical style, severity assignment per the PBM rubric, and NIST/ATT&CK mapping habits. The specialist agent's analytical checklist still drives the actual analysis — this file calibrates how findings and capabilities should look once written.

Authenticity in a PBM gates both PHI access and the lawfulness of prescription transmission. Pharmacist credential strength is the upstream control on every PHI surface a clinical user touches — SAML/OIDC federation against the pharmacy or health-system SSO is the dominant authentication path, and HIPAA Security Rule §164.312(d) person-or-entity authentication is the regulatory anchor. Separately, NCPDP SCRIPT digital signatures gate the lawfulness of electronic prescription transmission under DEA EPCS rules at 21 CFR §1311, and PDE submission signing is what CMS uses to bind a Part D claim record to its submitting sponsor. The load-bearing surfaces are the pharmacist-portal SSO path (including step-up for PHI export and PA override), the NCPDP signed-message path for SCRIPT transactions, and the PDE-submission signing chain.

## ATT&CK + D3FEND defensive mapping

This goal defends against (or is exploited by) the following MITRE ATT&CK techniques. Each citation is included only where the apd-control-mappings high-confidence-bar discipline is met; we deliberately omit techniques that only adjacently relate to this goal.

**ATT&CK techniques:**

- **T1621** (Multi-Factor Authentication Request Generation) — push-bombing or MFA fatigue against pharmacist or admin portals
- **T1556.006** (Modify Authentication Process: Multi-Factor Authentication) — bypassing MFA via fallback channel, recovery flow, or enrollment abuse
- **T1078** (Valid Accounts) — credentials are valid but the holder is unauthorized to use them
- **T1110.003** (Brute Force: Password Spraying) — low-volume spraying against pharmacist and member portals
- **T1110.004** (Brute Force: Credential Stuffing) — reused-credential attempts from breach corpora against member portal

**D3FEND counters:**

- **D3-MFA** (Multi-factor Authentication) — counters T1621 indirectly and T1078 directly via factor requirement
- **D3-CR** (Credential Revocation) — counters T1078 by permanently revoking compromised credentials on detection so they cannot be reused for further PHI access
- **D3-MAN** (Message Authentication) — counters NCPDP SCRIPT and X12 signed-message tampering at the protocol layer

## Common finding patterns

**Pattern: Service-to-service inside cluster uses shared secret tokens, not mTLS.**

- Severity: high (lateral movement amplification)
- NIST: SC-8(1), SC-23, IA-3
- ATT&CK: T1557 with specific in-cluster rationale
- Related concerns: ephemeral (shared-secret rotation), confidentiality (in-cluster PHI in transit)

**Pattern: MFA bypass via SMS fallback on PHI surfaces.**

- Severity: high (effective AAL downgrade)
- NIST: IA-2(1), IA-2(2), IA-2(8)
- ATT&CK: T1621 (Multi-Factor Authentication Request Generation) with rationale

**Pattern: Container images deployed without signature verification.**

- Severity: high (supply chain compromise vector)
- NIST: SI-7, SR-4, SR-11
- Related concerns: ephemeral (immutable infra requires authentic images)

**Pattern: Webhook payloads from vendor accepted without signature verification.**

- Severity: high (forged webhook can inject malicious adjudication input)
- NIST: SC-23, IA-3(1), SI-10
- Related concerns: integrity (input validation, route to Integrity finding for the malformed-input concern)

**Pattern: SBOM not generated; no vulnerability attribution path.**

- Severity: medium to high depending on regulatory commitments
- NIST: SR-4, SR-4(3), SR-11

**Pattern: Tech plan describes "authenticated APIs" generically.**

- Disposition: uncertainty or blocked
- prerequisite_evidence: "API authentication specification — (1) mechanism per API surface (OAuth 2.0 client-credentials, OAuth 2.0 authorization-code with PKCE, mTLS with workload identity, signed JWT with named issuer); (2) token lifetime per token class (access, refresh, step-up) with rotation cadence; (3) token-validation procedure (signature algorithm, key-discovery via JWKS endpoint or pinned key, issuer/audience/scope checks, clock-skew tolerance); (4) revocation mechanism on credential compromise (introspection endpoint, deny-list, or short-TTL strategy); (5) audit event emitted on authentication success, failure, and step-up challenge"

## Common capability patterns

**Pattern: mTLS across service mesh with SPIFFE identity.** Scope must enumerate which services are confirmed; expect caveats for legacy services not yet onboarded.

**Pattern: FIDO2/WebAuthn for internal admin access to PHI surfaces.** Cross-cuts Ephemeral via the credential lifetime; mention via `related_concerns`.

**Pattern: Signed container images with admission control enforcement.** Maturity depends on whether admission policy is in evidence.

**Pattern: SLSA Level 2 build provenance for production deployments.** Higher maturity requires CI/CD configuration evidence.

## prerequisite_evidence

When an authenticity concern cannot be confirmed from the available evidence, the specialist agent should mark the finding `blocked-on-evidence` and name the specific artifacts required to unblock. The asks below are multi-clause on purpose — a single-line ask like "tell me about MFA" is not enough to unblock a blocked finding, because the operator will return a partial answer and the cycle repeats.

**MFA implementation:** (1) factor-mix per actor class (pharmacist, member, admin, vendor-integration); (2) AAL level per actor class per NIST 800-63B (AAL1/2/3) with evidence of the determination; (3) enrollment flow security (re-auth required at enrollment, identity-proofing artifact retained, FIDO2 attestation level where applicable); (4) recovery flow security (rate-limited, supervisor-attested, out-of-band channel distinct from primary factor); (5) MFA-fatigue mitigation (push-rate-limit, number-matching, geographic-anomaly detection); (6) phishing-resistance posture (SMS forbidden as a factor on PHI surfaces, WebAuthn or equivalent as the primary factor for privileged actors); (7) audit event emitted on MFA challenge, response, success, and failure with sufficient context to reconstruct the attempt.

**Signed-message verification:** (1) signing-key location per signed-message channel (NCPDP SCRIPT, X12 271/278/837, PDE outbound) including HSM, KMS, or in-process key material; (2) signature-verification implementation pointer (library name and version, with a code or config reference); (3) replay-protection mechanism (nonce, timestamp window, message-ID dedup store, or sequence number); (4) failure handling on signature-verification failure (reject and audit vs. quarantine vs. fail-open) including downstream alerting path.

**Federation configuration:** (1) IdP relationship per actor class (pharmacist SSO against pharmacy or health-system IdP, prescriber SSO, member portal IdP) including IdP name and trust establishment artifact; (2) SAML or OIDC configuration with assertion-validation scope (signature algorithm, audience restriction, attribute mapping, NotBefore/NotOnOrAfter enforcement, ID-token claim validation); (3) trust-chain validation including certificate-pinning where applicable to mobile or thick-client federation paths, and the policy for IdP-signing-certificate rotation.
