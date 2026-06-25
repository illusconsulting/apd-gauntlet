# API security common patterns — Immutability

These are illustrative templates, not all-inclusive. Use them to calibrate analytical style, severity assignment per the API security rubric, and NIST/ATT&CK mapping habits. The specialist agent's analytical checklist still drives the actual analysis — this file calibrates how findings and capabilities should look once written.

## Common finding patterns

**Pattern: Audit log written to a mutable RDS table or document collection; no append-only enforcement, no WORM substrate.**

- Severity: high (audit-log alteration breaks every regulatory accountability claim; combines with any Non-Repudiation gap into a single critical-merged record)
- NIST: AU-9, AU-9(2), AU-9(3), AU-11, SI-7
- ATT&CK: T1070 (Indicator Removal); T1070.002 (Clear Linux or Mac System Logs); T1070.004 (File Deletion)
- Cross-reference: any Non-Repudiation finding on audit completeness; the merged record carries both concerns

**Pattern: Backup retention meets minimum but no object-lock or compliance-mode immutability applied.**

- Severity: high (backups vulnerable to ransomware deletion; the primary ransomware-resilience control absent)
- NIST: CP-9, CP-9(1), CP-9(8), MP-4
- ATT&CK: T1485 (Data Destruction); T1490 (Inhibit System Recovery)
- Related concerns: availability (backup recoverability), confidentiality (backup encryption)

**Pattern: Configuration is partly IaC, partly manual; no drift detection between declared and actual state.**

- Severity: medium to high depending on what's manually managed (RBAC roles manually managed is high; deploy parameters manually managed is medium)
- NIST: CM-2, CM-2(2), CM-3, CM-6, CM-6(2)
- Related concerns: integrity (configuration correctness), authenticity (signed-commit posture for the IaC half)

**Pattern: Configuration repository allows history rewrite — no protected branches, no force-push prevention, no signed-commit requirement.**

- Severity: medium to high
- NIST: CM-3, CM-3(1), SI-7(8) (auditable events for transmitted unauthorized changes), SA-10 (developer configuration management)
- Related concerns: authenticity (signed commits provide attribution but mutable history defeats it), non_repudiation (commit-attribution loss)

**Pattern: OAuth/OIDC consent records mutable — consent revocation overwrites the consent record rather than recording revocation as a new event.**

- Severity: high (the proof-of-consent for processing that occurred during the consent window is destroyed; GDPR Article 6(1)(a) defense fails)
- NIST: AU-11, AU-9, CM-2(3)
- Related concerns: non_repudiation (consent-event audit completeness)

**Pattern: SBOM and artifact-provenance history not retained — only current SBOM stored.**

- Severity: medium to high depending on regulatory commitments (high when supply-chain attestation is contractually required)
- NIST: SR-4, SR-4(3), CM-8 (system component inventory), AU-11
- Related concerns: authenticity (artifact signing and the SLSA provenance chain)

**Pattern: Retention duration not specified in artifacts.**

- Disposition: uncertainty or blocked
- prerequisite_evidence: "Retention policy — per-data-class duration, regulatory citation, enforcement mechanism (storage-tier policy, application-level enforcement), legal-hold override procedure, and deletion-verification mechanism"

## Common capability patterns

**Pattern: Object-lock with compliance mode on backup buckets, retention period set to the regulatory minimum or longer.** Scope must specify which buckets are confirmed; capabilities should enumerate the retention period and the lock mode (compliance vs. governance).

**Pattern: Hash-chained audit log with daily chain-head anchored to an external trust domain (separate cloud account, separate KMS, or external timestamp authority).** Cross-cuts Non-Repudiation; mention via `related_concerns`.

**Pattern: GitOps-driven configuration with signed commits, protected branches, and force-push prevention.** Maturity ladder: `designed` from tech plan; `implemented` requires repository configuration or pipeline evidence; `operationalized` requires evidence of the drift-detection-and-alerting loop.

**Pattern: SBOM versioning with per-deployment retention, linking deployed artifact digest to source-commit hash through the build pipeline.** Higher maturity requires evidence of the deploy-time provenance verification.
