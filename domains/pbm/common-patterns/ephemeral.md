# PBM common patterns — Ephemeral

These are illustrative templates, not all-inclusive. Use them to calibrate analytical style, severity assignment per the PBM rubric, and NIST/ATT&CK mapping habits. The specialist agent's analytical checklist still drives the actual analysis — this file calibrates how findings and capabilities should look once written.

Ephemerality is the single most leveraged control on PBM vendor-integration breach surface: long-lived service-account credentials — SCIM tokens to plan-sponsor IdPs, PDE-submission API keys, COB and accumulator integration credentials, mail-order and specialty fulfillment service accounts — are the dominant root cause in published PBM and healthcare-clearinghouse breach post-mortems, and HIPAA Security Rule §164.308(a)(4) access-management expectations bite hardest on credentials that outlive the personnel and contractual relationships that justified them. Long-lived operator sessions create a parallel problem on the audit side: actor attribution decays as a session ages across shift changes and role transitions. The load-bearing surfaces are vendor SCIM and provisioning tokens, PDE-submission API keys and CMS-side credentials, and the COB and accumulator integration credentials that touch member-level PHI.

## ATT&CK + D3FEND defensive mapping

This goal defends against (or is exploited by) the following MITRE ATT&CK techniques. Each citation is included only where the apd-control-mappings high-confidence-bar discipline is met; we deliberately omit techniques that only adjacently relate to this goal.

**ATT&CK techniques:**

- **T1552.001** (Credentials in Files) — long-lived PBM service-account credentials (SCIM tokens, PDE-submission API keys, COB and accumulator integration secrets) materialized in config, env vars, or vault paths exposed to over-broad readership
- **T1078** (Valid Accounts) — vendor-integration credentials and operator sessions outliving the personnel, contractual, or rotation cadence that justified them, which is the dominant root cause in published PBM and clearinghouse breach post-mortems
- **T1098** (Account Manipulation) — credential reactivation after intended rotation, or scope expansion on a service account (for example a COB integration credential gaining PDE-submission scope) without re-attestation

**D3FEND counters:**

- **D3-LFAM** (Local File Access Mediation) — counters T1552.001 by mediating filesystem and secret-store access to PBM credential locations so that compromise of an application tier does not yield the underlying long-lived secret
- **D3-RAPA** (Resource Access Pattern Analysis) — detects long-lived PBM service-account credentials being used at anomalous rates, from anomalous workloads, or against anomalous CMS / plan-sponsor endpoints, which is the operational signal for both T1078 and post-T1098 credential abuse

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
- prerequisite_evidence: "Credential lifecycle specification covering: (1) credential class taxonomy that distinguishes operator session credentials, service-account credentials, vendor integration credentials, and signing keys for NCPDP / PDE submission; (2) per-class lifetime expressed as a maximum age and rotation cadence; (3) per-class rotation automation pointer (Vault dynamic secrets, AWS Secrets Manager rotation lambda, IAM role assumption, SPIFFE/SPIRE workload identity) showing what executes the rotation; (4) per-class revocation pipeline including the emergency revocation path used when a credential is suspected compromised mid-cycle; (5) audit chain recording creation, rotation, suspension, and destruction events sufficient to reconstruct credential provenance during a HIPAA §164.308(a)(4) access-management review or a breach post-mortem"

**Pattern: Member portal session lifetime not specified.**

- Disposition: uncertainty
- prerequisite_evidence: "Session management policy covering: (1) maximum absolute session lifetime before forced re-authentication; (2) idle timeout that terminates an inactive session independent of absolute lifetime; (3) step-up authentication bounds — which member-portal actions (refill order placement, address change, payment-instrument change, mail-order pharmacy change) require a fresh authentication factor and what the freshness window is; (4) logout behavior including server-side session invalidation, refresh-token revocation, and propagation to downstream PBM systems that cached the session"

## Common capability patterns

**Pattern: Dynamic database credentials via vault.** Maturity depends on whether tech plan asserts (designed) or vault configuration is in evidence (implemented).

**Pattern: Workload identity via SPIFFE for service-to-service authentication.** Caveats expected on which services are confirmed.

**Pattern: JIT access for production via approval workflow with time-boxed grants.** Operational maturity requires runbook evidence; designed maturity from tech plan only.

**Pattern: Immutable container deployment via signed image references in IaC.** Cross-cuts Authenticity for the signing aspect; Ephemeral confirms the replace-don't-patch posture.

## prerequisite_evidence

When a finding pattern above is marked blocked-on-evidence rather than emitted as a gap, the operator must supply the multi-clause specifications below. Anything less and the specialist should keep the disposition as blocked rather than downgrade to uncertainty.

**Just-in-time access for production:** (1) the JIT access mechanism for human operators (broker name, ticket-driven elevation, ChatOps approval bot, cloud-native PIM) and the workloads it covers; (2) elevation requirements including approver identity (named role, not group), required justification entry, and the maximum time-bounded session length granted per elevation; (3) audit trail of every elevation event sufficient to answer "who approved which operator into which production scope for how long, on which date, against which change ticket"; (4) automatic expiry behavior on session timeout including credential revocation, in-flight session termination, and downstream notification to PBM systems that cached the elevated identity
