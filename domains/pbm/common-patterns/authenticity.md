# PBM common patterns — Authenticity

These are illustrative templates, not all-inclusive. Use them to calibrate analytical style, severity assignment per the PBM rubric, and NIST/ATT&CK mapping habits. The specialist agent's analytical checklist still drives the actual analysis — this file calibrates how findings and capabilities should look once written.

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
- prerequisite_evidence: "API authentication specification — mechanism (OAuth, mTLS, signed JWT), token lifetime, validation procedure"

## Common capability patterns

**Pattern: mTLS across service mesh with SPIFFE identity.** Scope must enumerate which services are confirmed; expect caveats for legacy services not yet onboarded.

**Pattern: FIDO2/WebAuthn for internal admin access to PHI surfaces.** Cross-cuts Ephemeral via the credential lifetime; mention via `related_concerns`.

**Pattern: Signed container images with admission control enforcement.** Maturity depends on whether admission policy is in evidence.

**Pattern: SLSA Level 2 build provenance for production deployments.** Higher maturity requires CI/CD configuration evidence.
