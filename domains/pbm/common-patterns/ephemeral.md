# PBM common patterns — Ephemeral

These are illustrative templates, not all-inclusive. Use them to calibrate analytical style, severity assignment per the PBM rubric, and NIST/ATT&CK mapping habits. The specialist agent's analytical checklist still drives the actual analysis — this file calibrates how findings and capabilities should look once written.

## Common finding patterns

**Pattern: Service account credentials are static long-lived secrets in application config.**
- Severity: high (broad blast radius on credential leak, no automatic invalidation)
- NIST: IA-5, IA-5(1), IA-5(7), SC-12(1)
- ATT&CK: T1078 (Valid Accounts) with sub-technique by environment

**Pattern: Database credentials shared across services; no rotation.**
- Severity: high
- NIST: IA-5, AC-2(2)
- Related concerns: confidentiality (key management around the shared credential)

**Pattern: Production access via standing admin role with no JIT.**
- Severity: high (excessive standing privilege, no time-boxing)
- NIST: AC-6, AC-2(2), AC-2(3)
- Related concerns: non_repudiation (audit of admin actions), authenticity (admin identity strength)

**Pattern: Container images mutable in production — `:latest` tags, in-place container updates.**
- Severity: medium to high depending on what's mutable
- NIST: CM-2, CM-3, SA-15(7)
- Related concerns: authenticity (image signing), integrity (configuration drift)

**Pattern: Tech plan mentions "secrets stored in vault" without rotation specifics.**
- Disposition: uncertainty or blocked
- prerequisite_evidence: "Secret rotation policy — cadence, mechanism, automation, exception process"

**Pattern: Member portal session lifetime not specified.**
- Disposition: uncertainty
- prerequisite_evidence: "Session management policy — max lifetime, idle timeout, step-up bounds, logout behavior"

## Common capability patterns

**Pattern: Dynamic database credentials via vault.** Maturity depends on whether tech plan asserts (designed) or vault configuration is in evidence (implemented).

**Pattern: Workload identity via SPIFFE for service-to-service authentication.** Caveats expected on which services are confirmed.

**Pattern: JIT access for production via approval workflow with time-boxed grants.** Operational maturity requires runbook evidence; designed maturity from tech plan only.

**Pattern: Immutable container deployment via signed image references in IaC.** Cross-cuts Authenticity for the signing aspect; Ephemeral confirms the replace-don't-patch posture.
