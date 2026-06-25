# Security tooling common patterns — Ephemeral

These are illustrative templates, not all-inclusive. Use them to calibrate analytical style, severity assignment per the security-tooling rubric, and NIST/ATT&CK mapping habits. The specialist agent's analytical checklist still drives the actual analysis — this file calibrates how findings and capabilities should look once written.

Ephemeral concerns in security tooling include a domain-specific class: **engagement-bounded lifetimes** — credentials, signing material, retention windows, and authorization windows that MUST expire at engagement closure or ROE-window end. Failure to enforce engagement-bounded lifetimes converts a closed engagement into an indefinitely-open one, with the legal and contractual consequences that implies.

## Common finding patterns

**Pattern: Operator API tokens are static long-lived secrets with no rotation, no scope-narrowing, no time-bound — created at operator onboarding and never refreshed.**

- Severity: high (rubric: "Credential leak in operator API tokens"; blast radius is full operator scope until rotation, and detection signal is absent)
- NIST: IA-5, IA-5(1), IA-5(7), SC-12(1), AC-2
- ATT&CK: T1078 (Valid Accounts); T1552.001 (Credentials in Files); T1528 (Steal Application Access Token)
- Related concerns: confidentiality (token storage), authenticity (workload identity as replacement), non_repudiation (audit on token use vs. issuance)

**Pattern: Operator session lifetime unbounded or excessively long — no absolute lifetime, no idle timeout, no re-authentication required for engagement initiation, signing-key access, or audit-read.**

- Severity: high (stolen session usable indefinitely; consequential operations gate is the session, not a step-up factor)
- NIST: IA-5, AC-12 (Session Termination), AC-12(1), IA-11 (Re-Authentication)
- Related concerns: authenticity (step-up MFA for consequential ops), non_repudiation (session-lifetime affects actor-attribution confidence)

**Pattern: Implant credentials (the per-implant authentication tokens) baked into the implant binary at deployment time with no rotation; long-running engagements use the same credential for months.**

- Severity: high (compromise of any single implant via target-side reverse engineering yields a usable callback credential for the implant's lifetime; combine-and-amplify with shared-credential designs)
- NIST: IA-5, IA-5(13), SC-12, SC-12(2)
- ATT&CK: T1078; T1552.004 (Private Keys) if the implant carries asymmetric material
- D3FEND: D3-CR (Credential Rotation), D3-RTSD (Remote Terminal Session Detection) for callback anomaly
- Related concerns: authenticity (implant identity binding), integrity (implant binary signing)

**Pattern: Per-engagement signing keys are issued but not destroyed at engagement closure — closed engagements retain valid signing material indefinitely.**

- Severity: high (a long-closed engagement's leaked signing key remains usable; converts closed engagements into indefinitely-open offensive surfaces; the security-tooling-specific "engagement-bounded lifetime" failure)
- NIST: SC-12, SC-12(2), SC-12(6), SR-12 (Component Disposal)
- Related concerns: immutability (signing-key lifecycle audit must record destruction event), authenticity (engagement-bounded trust)

**Pattern: ROE document and engagement-scope definition have no expiration — authorization windows are declared at engagement start but not enforced at command-issue time.**

- Severity: critical (rubric: "Unauthorized engagement-initiation capability" applies; operator can issue commands outside the authorized window with no enforcement gate; creates CFAA exposure)
- NIST: AC-3, AC-12, CM-7, AU-12
- Related concerns: authenticity (ROE-attestation freshness), non_repudiation (out-of-window command audit), integrity (engagement-scope enforcement)

**Pattern: Result-data retention policy unspecified — captured credentials, screenshots, files retained indefinitely beyond engagement closure and beyond customer-policy windows.**

- Severity: medium to high depending on what's retained (harvested credentials retained beyond engagement closure are high; sanitized command output is medium)
- NIST: SI-12 (Information Management and Retention), MP-6 (Media Sanitization), SR-12
- Related concerns: confidentiality (long-lived result data accumulates exposure surface), immutability (deletion authority must itself be audited)

**Pattern: Plugin runtime credentials (cloud IAM, external-service tokens used by plugins) static and long-lived; plugin retains usable credentials after the plugin is disabled or removed.**

- Severity: high (uninstall does not revoke; lateral persistence after plugin removal)
- NIST: IA-5, AC-2, AC-2(3) (Disable Accounts), SC-12
- Related concerns: confidentiality (plugin credential storage), non_repudiation (credential-use audit)

**Pattern: Tech plan mentions "secrets in vault" without rotation specifics, audit-on-fetch, engagement-bounded scope, or break-glass procedure for the security-tooling-specific signing material.**

- Disposition: uncertainty or blocked
- prerequisite_evidence: "Secret-management policy — per-secret-class rotation cadence (operator credentials, c2 signing key, plugin signing root, implant credentials, listener TLS, audit signing key), rotation mechanism, audit-on-fetch behavior, engagement-bounded scope where applicable, and break-glass procedure for signing-key emergency rotation"

## Common capability patterns

**Pattern: Per-engagement signing material derived at engagement start and cryptographically destroyed at engagement closure, with destruction event in the immutable audit log.** Maturity higher when the derivation is recorded in a tamper-evident lifecycle log; cross-cuts Immutability via signing-key lifecycle events.

**Pattern: Workload identity (SPIFFE/SPIRE, cloud-native workload identity, K8s ServiceAccount projected tokens) replacing static operator API tokens for service-to-service integration.** Caveats expected on which integrations are confirmed onboard.

**Pattern: JIT operator access via approval workflow with time-boxed grants and full session recording for elevated operations (signing-key access, ROE modification, audit-read).** Operational maturity requires runbook evidence plus session-recording retention policy.

**Pattern: Implant credentials rotated mid-engagement on a fixed cadence with rotation events captured in the audit log.** Higher maturity when rotation is automated and rotation failures alert; lower when manual.

**Pattern: ROE authorization window enforced at command-issue time with the orchestrator refusing commands outside the window and the refusal logged as a consequential action.** Cross-cuts Authenticity (window-attestation freshness) and Non-Repudiation (refusal audit).
