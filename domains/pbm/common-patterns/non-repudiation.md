# PBM common patterns — Non-Repudiation

These are illustrative templates, not all-inclusive. Use them to calibrate analytical style, severity assignment per the PBM rubric, and NIST/ATT&CK mapping habits. The specialist agent's analytical checklist still drives the actual analysis — this file calibrates how findings and capabilities should look once written.

## Common finding patterns

**Pattern: Admin configuration changes logged but actor attribution is system account, not the human operator.**
- Severity: high (configuration corruption is not attributable; URAC and SOC 2 expose)
- NIST: AU-3, AU-3(1), AU-12, AU-10
- Related concerns: authenticity (admin identity strength), immutability (configuration history)

**Pattern: PHI access logging present but only at table/service level, not record level.**
- Severity: high (minimum-necessary attestation impaired)
- NIST: AU-2, AU-3
- Detail: HIPAA Security Rule and minimum-necessary doctrine require attribution at the level needed to prove appropriate use, not just access.

**Pattern: Audit shipping is fire-and-forget; consumer-side failure produces silent loss.**
- Severity: high
- NIST: AU-4, AU-5
- Related concerns: availability (audit pipeline reliability), immutability (durability of the audit)

**Pattern: No cryptographic protection on audit entries; mutable database table.**
- Severity: high
- NIST: AU-9, AU-9(2), AU-9(3)
- Related concerns: immutability (this finding's recommendation will couple to an immutability finding)

**Pattern: Time source unspecified.**
- Disposition: uncertainty
- prerequisite_evidence: "Audit time source specification — NTP topology, drift bounds, fallback"

**Pattern: Break-glass procedure exists but break-glass actions are not specially audited beyond normal logging.**
- Severity: medium to high
- NIST: AU-3, AU-12(1), AC-6(9)

## Common capability patterns

**Pattern: Per-action PHI access audit with actor, resource, purpose, and outcome captured.** Scope must specify which surfaces are confirmed; caveats for any out-of-evidence.

**Pattern: Cryptographically signed audit entries hash-chained per stream.** Maturity depends on whether the chain is described in tech plan only or implemented in code/IaC.

**Pattern: ATNA-conformant audit format for clinical actions.** Often `designed` from tech plan; higher maturity requires implementation evidence.

**Pattern: Audit log read access gated by separate role from operational roles, with read events themselves audited.** Cross-cuts Authenticity for the role definition.
