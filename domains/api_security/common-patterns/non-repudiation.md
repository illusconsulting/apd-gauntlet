# API security common patterns — Non-Repudiation

These are illustrative templates, not all-inclusive. Use them to calibrate analytical style, severity assignment per the API security rubric, and NIST/ATT&CK mapping habits. The specialist agent's analytical checklist still drives the actual analysis — this file calibrates how findings and capabilities should look once written.

## Common finding patterns

**Pattern: Audit entries on consequential actions lack actor attribution — actor field is "system" or a shared service account.**

- Severity: high (consequential-action attribution is the foundation of breach reconstruction and dispute response; SOC 2 CC7.2, PCI-DSS Requirement 10, and GDPR Article 33 all depend on it)
- NIST: AU-3, AU-3(1), AU-10 (non-repudiation), AU-12
- Related concerns: authenticity (the actor field is only as strong as the authentication that produced it; weak auth produces weak attribution), immutability (attribution loss combines with audit-tampering risk)

**Pattern: PII access logging present at table/service level but not record-level — operator queried "users" but the per-record set retrieved is not captured.**

- Severity: high (minimum-necessary attestation impaired; GDPR Article 5(1)(c) data-minimization defense requires evidence of what was actually accessed)
- NIST: AU-2, AU-3, AC-6, AU-12(1)
- Detail: data-protection authorities increasingly expect record-level access logs as the evidence base for "lawful and transparent" processing claims.

**Pattern: Audit shipping is fire-and-forget; consumer-side failure produces silent loss.**

- Severity: high
- NIST: AU-4, AU-5, AU-5(1), AU-5(2)
- Related concerns: availability (audit pipeline reliability), immutability (durability of the audit), resilient (audit-buffer behavior under broker outage)

**Pattern: Audit retention shorter than the longest applicable regulatory minimum or shorter than the longest plausible breach-detection window.**

- Severity: high (renders breach-notification obligations un-meetable for breaches detected after retention expires)
- NIST: AU-11, AU-9, SI-12
- Detail: cite the longest applicable retention — PCI-DSS Requirement 10.7 (1 year online + 1 year archive), SOC 2 (service-organization policy, typically 1–7 years), regulatory anchors per the domain pack.

**Pattern: Audit-read access uncontrolled — any operator role can search audit logs without separate authorization or audit-of-audit-access.**

- Severity: high (audit access is itself a consequential action; uncontrolled access enables an insider to identify what's been observed and adjust behavior)
- NIST: AU-9, AU-9(4), AU-9(6), AC-5 (separation of duties), AC-6
- Related concerns: authenticity (audit-role definition), confidentiality (audit content sensitivity inheritance)

**Pattern: No time-source policy — audit timestamps are local system clocks with no NTP discipline, no drift bounds, no fallback.**

- Disposition: uncertainty or blocked
- prerequisite_evidence: "Audit time-source specification — NTP topology, time-source authority, drift bounds, behavior on time-source failure, and timestamp precision (millisecond, microsecond)"

**Pattern: Audit pipeline single-point-of-failure — single broker, single sink, no buffer between application and broker.**

- Severity: high (audit availability is itself a regulatory requirement under PCI Requirement 10; broker outage produces silent audit loss)
- NIST: AU-5, AU-5(1), CP-7
- Related concerns: availability (audit-pipeline SLO), distributed (audit-broker topology)

**Pattern: Break-glass procedure exists but break-glass actions are not specially audited beyond normal logging.**

- Severity: medium to high
- NIST: AU-3, AU-12(1), AC-6(9), AC-6(10)
- Detail: break-glass actions should produce a distinguishable audit stream that automatically routes to security-review independent of normal audit consumption.

## Common capability patterns

**Pattern: Per-action audit on consequential surfaces with actor, resource, action, purpose, and outcome captured per-record.** Scope must enumerate covered surfaces against the consequential-actions list; caveats for any out-of-evidence.

**Pattern: Cryptographically signed audit entries hash-chained per stream, with chain heads anchored externally (e.g., to a separate trust domain or an external timestamp authority).** Maturity depends on whether the chain is described in tech plan only or implemented in code/IaC; operationalized maturity requires evidence of chain-verification at audit-read time.

**Pattern: Audit-read access gated by a separate role from operational roles, with read events themselves audited (audit-of-audit-access).** Cross-cuts Authenticity for the role definition; mention via `related_concerns`.

**Pattern: Time-source policy with NTP topology specified, drift bounds enforced, and fallback to a secondary stratum on primary failure.** Higher maturity requires monitoring evidence on drift and on time-source-availability events themselves being audited.
