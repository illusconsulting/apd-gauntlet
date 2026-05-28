# Security tooling common patterns — Non-Repudiation

These are illustrative templates, not all-inclusive. Use them to calibrate analytical style, severity assignment per the security-tooling rubric, and NIST/ATT&CK mapping habits. The specialist agent's analytical checklist still drives the actual analysis — this file calibrates how findings and capabilities should look once written.

Non-repudiation in security tooling is the load-bearing pattern for legal defensibility under CFAA, ROE attestation under customer MSAs, and customer-deliverable provenance for engagement findings. "We can't prove who issued that command" is not just an audit gap — it's a presumption-of-misuse signal to regulators and customers.

## Common finding patterns

**Pattern: Command-issued log entries attribute commands to a service account or "system" rather than to the human operator who initiated the command via the orchestrator.**

- Severity: critical (rubric: "Audit trail loss covering operator actions" — without per-human attribution, the consequential-action log is unusable for after-action review, dispute resolution, or CFAA defensibility)
- NIST: AU-3, AU-3(1), AU-10 (Non-Repudiation), AU-12, AU-12(1)
- ATT&CK: T1070 (Indicator Removal) applied to attribution erasure
- Related concerns: authenticity (the operator-identity chain), immutability (the attribution must survive log retention)

**Pattern: Result-data access logging present at engagement level but not per-record — operator queried "all credentials for engagement X" but the per-record set retrieved is not captured.**

- Severity: high (minimum-necessary attestation impaired; customer-deliverable provenance gaps; can't prove which records the operator actually saw vs. which were available)
- NIST: AU-2, AU-3, AC-6, AU-12(1)
- Related concerns: confidentiality (audit content sensitivity inherited from result data), immutability (per-record access log retention)

**Pattern: Audit shipping is fire-and-forget — orchestrator emits to broker without acknowledgement; broker outage produces silent audit loss while the platform continues issuing commands.**

- Severity: critical (rubric: "Audit trail loss" applies; security-tooling-specific: the orchestrator should refuse new command issuance when audit cannot record, per the Resilient pattern)
- NIST: AU-4, AU-5, AU-5(1), AU-5(2), CP-13
- D3FEND: D3-SBV at the audit consumer; D3-MA for entry-level acknowledgement
- Related concerns: availability (audit-pipeline SLO), immutability (audit durability), resilient (audit-buffer behavior)

**Pattern: Audit retention shorter than the longest customer-MSA audit-clause window or shorter than the longest plausible legal-discovery window.**

- Severity: high (renders dispute-resolution obligations un-meetable for disputes raised after retention expires; customer-MSA breach if MSA specifies a minimum)
- NIST: AU-11, AU-9, SI-12
- Detail: cite the longest applicable retention — customer MSA commonly 3–7 years for engagement records, SOC 2 typically 1–7 years per service-organization policy, sectoral NIS2 requirements where applicable

**Pattern: Audit-read access uncontrolled — any operator role can search audit logs without separate authorization and without audit-of-audit-access.**

- Severity: high (rubric: audit access is itself a consequential action; uncontrolled access enables an insider to identify what's been observed and adjust behavior)
- NIST: AU-9, AU-9(4), AU-9(6), AC-5 (Separation of Duties), AC-6
- Related concerns: authenticity (audit-role definition), confidentiality (audit content inheritance)

**Pattern: No time-source policy — audit timestamps are local system clocks with no NTP discipline, no drift bounds, no fallback. Cross-component event-ordering ambiguous.**

- Disposition: uncertainty or blocked
- prerequisite_evidence: "Audit time-source specification — NTP topology, time-source authority, drift bounds, behavior on time-source failure (fail-closed vs. fail-open), timestamp precision (millisecond, microsecond), cross-component clock-synchronization mechanism"

**Pattern: Multi-tenant SaaS platform with shared audit storage — operator A can see audit entries describing operator B's actions against customer C's environment.**

- Severity: critical (rubric: "Cross-tenant data exposure" applies to audit content; customer C's engagement metadata leaks across tenants via the audit substrate)
- NIST: AU-9, AC-3, AC-4, SC-7
- Related concerns: distributed (per-tenant audit storage), confidentiality (audit content inherits engagement classification)

**Pattern: Break-glass procedure exists for emergency engagement-termination or out-of-cycle key rotation, but break-glass actions are not specially audited beyond normal logging.**

- Severity: high (break-glass should produce a distinguishable audit stream that automatically routes to security-review independent of normal audit consumption)
- NIST: AU-3, AU-12(1), AC-6(9), AC-6(10)
- Related concerns: authenticity (break-glass authentication strength), immutability (break-glass audit must be specifically retained)

## Common capability patterns

**Pattern: Per-action audit on every consequential operation per the consequential-actions list with operator-attribution, target-attribution, engagement-attribution, and outcome captured per-record.** Capability scope must enumerate covered surfaces against the consequential-actions list; out-of-coverage actions become partial-coverage findings.

**Pattern: Cryptographically signed audit entries hash-chained per stream, with chain heads anchored externally (separate trust domain, external timestamp authority, transparency log).** Maturity depends on whether the chain is described in tech plan only or implemented; operationalized maturity requires evidence of chain-verification at audit-read time.

**Pattern: Audit-read gated by a separate role from operational roles, with read events themselves audited (audit-of-audit-access).** Cross-cuts Authenticity for the role definition; the audit-of-audit recursion is the load-bearing SoD claim.

**Pattern: Time-source policy with NTP topology specified, drift bounds enforced, fallback to a secondary stratum on primary failure, and the time-source-failure event itself audited.** Higher maturity requires monitoring evidence on drift, and on the time-source-availability events being audited.

**Pattern: Per-tenant audit storage with cryptographic isolation — operator A cannot decrypt operator B's audit entries even if storage-layer ACLs are bypassed.** Cross-cuts Confidentiality and Distributed; the cryptographic-isolation half is the load-bearing claim for SaaS-delivered platforms.

**Pattern: Break-glass actions emit a distinguished audit stream that mandatorily routes to security-review, with the orchestrator refusing to operate if the break-glass-audit channel is unreachable.** Cross-cuts Resilient (fail-closed for audit) and Authenticity (break-glass MFA strength).
