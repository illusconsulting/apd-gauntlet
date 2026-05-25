# PBM common patterns — Immutability

These are illustrative templates, not all-inclusive. Use them to calibrate analytical style, severity assignment per the PBM rubric, and NIST/ATT&CK mapping habits. The specialist agent's analytical checklist still drives the actual analysis — this file calibrates how findings and capabilities should look once written.

## Common finding patterns

**Pattern: Audit log written to a mutable RDS table; no append-only enforcement.**
- Severity: high (audit log alteration breaks HIPAA accountability; combines with any Non-Repudiation gap)
- NIST: AU-9, AU-9(2), AU-9(3), AU-11
- Cross-reference: any Non-Repudiation finding on audit completeness; the merged or linked record carries both concerns

**Pattern: Backup retention policy meets minimum but no object lock applied.**
- Severity: high (backups vulnerable to ransomware deletion)
- NIST: CP-9, CP-9(1), CP-9(8), MP-4
- Related concerns: availability (backup recoverability)

**Pattern: Configuration is partly IaC, partly manual; no drift detection.**
- Severity: medium to high depending on what's manually managed
- NIST: CM-2, CM-2(2), CM-3, CM-6
- Related concerns: integrity (configuration correctness), authenticity (signed-commit posture)

**Pattern: Configuration repository allows history rewrite (no protected branches).**
- Severity: medium to high
- NIST: CM-3, CM-3(1), SI-7(8)
- Related concerns: authenticity (signed commits provide attribution but mutable history defeats it)

**Pattern: Formulary configuration history not retained — only current state stored.**
- Severity: high (adjudication decisions cannot be reconstructed against the formulary at decision time; defends regulatory and litigation positions)
- NIST: CM-2(3), AU-11
- Related concerns: non_repudiation (linking decisions to their inputs)

**Pattern: Retention duration not specified in artifacts.**
- Disposition: uncertainty or blocked
- prerequisite_evidence: "Retention policy — duration per data class, regulatory citation, enforcement mechanism, legal-hold override"

## Common capability patterns

**Pattern: S3 object lock with compliance mode on backup buckets, retention period set to regulatory minimum.** Scope must specify which buckets are confirmed.

**Pattern: Hash-chained audit log with daily chain-head anchored to an external trust domain.** Cross-cuts Non-Repudiation; mention via `related_concerns`.

**Pattern: GitOps-driven configuration with signed commits and protected branches.** Maturity ladder: `designed` from tech plan; `implemented` requires repository configuration or pipeline evidence.

**Pattern: Formulary versioning with snapshot-at-decision retention on every adjudication.** Higher maturity requires schema or implementation evidence.
