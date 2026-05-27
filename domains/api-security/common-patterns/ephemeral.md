# API security common patterns — Ephemeral

These are illustrative templates, not all-inclusive. Use them to calibrate analytical style, severity assignment per the API security rubric, and NIST/ATT&CK mapping habits. The specialist agent's analytical checklist still drives the actual analysis — this file calibrates how findings and capabilities should look once written.

## Common finding patterns

**Pattern: Service account tokens or API keys are static long-lived secrets in application configuration with no rotation.**

- Severity: high (broad blast radius on credential leak, no automatic invalidation, no detection signal on use of a leaked credential)
- NIST: IA-5, IA-5(1), IA-5(7), SC-12(1), AC-2
- ATT&CK: T1078 (Valid Accounts) with sub-technique by environment — T1078.001 default accounts, T1078.004 cloud accounts; T1552.001 (Credentials in Files)
- Related concerns: confidentiality (key management around the shared credential), authenticity (workload identity as the replacement pattern)

**Pattern: JWT access-token lifetime exceeds 1 hour with no refresh-token rotation and no revocation channel.**

- Severity: high (a stolen token is valid for its full lifetime with no recovery; refresh-rotation collapses the window)
- NIST: IA-5, IA-5(13), AC-12 (session termination)
- ATT&CK: T1550.001 (Application Access Token); T1606 (Forge Web Credentials)
- Related concerns: authenticity (revocation channel implies token-introspection or version-claim discipline)

**Pattern: OAuth client_secret unrotated since initial issuance; rotation procedure undocumented.**

- Severity: high (client_secret leak is a recurring incident pattern via repository exposure, CI logs, mobile-app extraction)
- NIST: IA-5, IA-5(1), SC-12
- Related concerns: authenticity (client_credentials grant trust), non_repudiation (audit of client_secret use vs. rotation)

**Pattern: Session lifetime unspecified — no maximum absolute lifetime, no idle timeout, no behavior on credential change.**

- Disposition: uncertainty or blocked
- prerequisite_evidence: "Session management policy — maximum absolute lifetime, idle timeout, behavior on password change (revoke all sessions vs. preserve), behavior on MFA enrollment change, step-up bounds, explicit logout semantics"

**Pattern: Refresh-token reuse not detected — reused refresh token issues a new access token instead of revoking the family.**

- Severity: high (the foundational OAuth2.1 hardening pattern; reuse detection converts refresh-token theft into a detection event)
- NIST: IA-5, IA-5(13), SI-4
- ATT&CK: T1550.001
- Related concerns: resilient (the reuse-detection event is also a recovery signal)

**Pattern: Container images mutable in production — `:latest` tags, in-place container patches, or persistent volumes carrying production state across restarts.**

- Severity: medium to high depending on what's mutable
- NIST: CM-2, CM-3, SA-15(7), SI-7
- Related concerns: authenticity (image-signing posture), integrity (configuration drift detection)

**Pattern: Tech plan mentions "secrets stored in vault" without rotation specifics, audit-on-fetch, or break-glass procedure.**

- Disposition: uncertainty or blocked
- prerequisite_evidence: "Secret-management policy — per-secret-class rotation cadence, rotation mechanism (automated vs. manual), audit-on-fetch behavior, break-glass procedure, and secret-zero-trust posture (does the vault token itself rotate?)"

## Common capability patterns

**Pattern: Dynamic credentials via vault — per-session database credentials, short-lived cloud IAM credentials, just-in-time service tokens.** Maturity depends on whether tech plan asserts (designed) or vault configuration is in evidence (implemented).

**Pattern: Workload identity (SPIFFE/SPIRE, cloud-native workload identity, Kubernetes ServiceAccount projected tokens) replacing static service credentials.** Caveats expected on which services are confirmed onboard.

**Pattern: JIT human access for production via approval workflow with time-boxed grants and full session recording.** Operational maturity requires runbook evidence plus the recording-retention policy; designed maturity from tech plan only.

**Pattern: Refresh-token rotation with family-revocation on reuse detection.** Cross-cuts Authenticity for the token-issuance pipeline; mention via `related_concerns`.
