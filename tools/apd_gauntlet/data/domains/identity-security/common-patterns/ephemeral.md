# Identity security common patterns — Ephemeral

These are illustrative templates, not all-inclusive. Use them to calibrate analytical style, severity assignment per the identity security rubric, and NIST/ATT&CK mapping habits. The specialist agent's analytical checklist still drives the actual analysis — this file calibrates how findings and capabilities should look once written.

## Common finding patterns

**Pattern: Access-token lifetime exceeds 1 hour with no refresh-token rotation and no introspection/revocation channel.**

- Severity: high (a stolen access token is valid for its full lifetime with no recovery; short-lifetime-plus-rotation is the proportional control)
- NIST: IA-5, IA-5(13), AC-12 (session termination)
- ATT&CK: T1550.001 (Application Access Token); T1606 (Forge Web Credentials)
- Related concerns: authenticity (revocation requires token-introspection or version-claim discipline), resilient (reuse-detection)

**Pattern: Refresh-token lifetime extends to weeks or months with no rotation-on-use and no reuse-detection.**

- Severity: high (refresh-token theft is the dominant token-loss vector for mobile/SPA clients; OAuth 2.1 §6.1 requires rotation-with-reuse-detection for public clients)
- NIST: IA-5, IA-5(13), SI-4, AC-12
- ATT&CK: T1550.001; T1528 (Steal Application Access Token)
- Related concerns: confidentiality (refresh-token-at-rest storage), resilient (reuse-detection alerting)

**Pattern: OAuth client_secret unrotated since initial issuance; rotation procedure undocumented.**

- Severity: high (client_secret leak is a recurring incident pattern via repository exposure, CI log leak, mobile-app extraction, vendor compromise; without rotation, leak is permanent)
- NIST: IA-5, IA-5(1), SC-12
- ATT&CK: T1552.001 (Credentials in Files); T1078 (Valid Accounts)
- Related concerns: authenticity (client-authentication strength; private_key_jwt and mTLS client auth eliminate the shared-secret class), non_repudiation (audit of client_secret use vs. rotation)

**Pattern: Session lifetime unspecified — no maximum absolute lifetime, no idle timeout, no behavior on credential change, no behavior on AAL elevation.**

- Disposition: uncertainty or blocked
- prerequisite_evidence: "Session management policy — maximum absolute lifetime per AAL tier, idle timeout, behavior on password change (revoke all sessions vs. preserve), behavior on MFA enrollment/removal, behavior on AAL elevation (does step-up issue a new session or upgrade the existing one?), explicit logout semantics including SAML SLO and OIDC front-channel/back-channel logout"

**Pattern: Signing-key rotation cadence absent or longer than the longest token lifetime.**

- Severity: high (the JWKS rotation gives a revocation window for token forgery in the event of key compromise; without rotation, key compromise is permanent)
- NIST: SC-12, SC-12(2), SC-12(3), SR-11
- Related concerns: integrity (JWKS rotation grace window discipline), immutability (key-lifecycle audit), distributed (regional HSM rotation coordination)

**Pattern: Recovery-code set static — recovery codes generated at MFA enrollment and never rotated even when the MFA factor itself rotates.**

- Severity: medium to high (a stolen recovery-code set survives every MFA-factor change; rotation-on-MFA-change is the proportional control)
- NIST: IA-5, IA-5(1)
- Related concerns: authenticity (recovery-flow AAL claim weakens if codes are old)

**Pattern: Service-account / non-human-identity credentials inside the IdP (LDAP bind credentials, database credentials, SMTP credentials, vendor API keys) are static long-lived secrets with no rotation.**

- Severity: high (broad blast radius on credential leak, no automatic invalidation, no detection signal on use of a leaked credential; the IdP backend credential leak pivots from IdP outward to every system the IdP touches)
- NIST: IA-5, IA-5(1), IA-5(7), SC-12(1), AC-2
- ATT&CK: T1078 (Valid Accounts); T1552.001 (Credentials in Files)
- Related concerns: confidentiality (key management around the credential), authenticity (workload identity as the replacement pattern)

**Pattern: Tech plan mentions "secrets stored in vault" without rotation specifics, audit-on-fetch, break-glass procedure, or secret-zero-trust posture for the vault token itself.**

- Disposition: uncertainty or blocked
- prerequisite_evidence: "Secret-management policy — per-secret-class rotation cadence (signing keys, client secrets, bind credentials, recovery-channel credentials), rotation mechanism (automated vs. manual), audit-on-fetch behavior, break-glass procedure, and secret-zero-trust posture (does the vault auth token itself rotate?)"

## Common capability patterns

**Pattern: Short-lived access tokens (≤1 hour, ≤15 minutes for high-privilege scopes) paired with refresh-token rotation and reuse detection.** Maturity ladder: `designed` from tech plan; `implemented` requires OAuth-library configuration evidence; `operationalized` requires evidence of family-revocation events fed to detection.

**Pattern: OAuth client_secret automated rotation with overlap window; private_key_jwt or mTLS client authentication available as the rotation-resilient alternative.** Higher maturity when private_key_jwt or mTLS is the default for new client registrations and client_secret is on a deprecation path.

**Pattern: Signing-key rotation on a documented cadence with JWKS publication discipline (next-key published in JWKS before becoming active; old key retained in JWKS through the longest token lifetime).** Cross-cuts Integrity for the rotation grace window; mention via `related_concerns`. Operationalized maturity requires monitoring on the rotation cadence itself.

**Pattern: Workload identity (SPIFFE/SPIRE, cloud-native workload identity, Kubernetes ServiceAccount projected tokens) replacing static service credentials for IdP-to-backend calls.** Caveats expected on which backends are confirmed onboard; legacy LDAP/AD backends often remain on bind-credentials.

**Pattern: Session lifetime policy declared per AAL tier (AAL3 sessions shorter than AAL1; step-up issues fresh session; credential change revokes all sessions; SLO and front-channel logout work across all federated SPs).** Operational maturity requires evidence the SLO/front-channel logout actually completes for all SPs (the common gap).

**Pattern: JIT human access for the IdP admin console via approval workflow with time-boxed grants and full session recording.** Operational maturity requires runbook evidence plus the recording-retention policy; designed maturity from tech plan only.
