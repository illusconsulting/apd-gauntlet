# Security tooling common patterns — Immutability

These are illustrative templates, not all-inclusive. Use them to calibrate analytical style, severity assignment per the security-tooling rubric, and NIST/ATT&CK mapping habits. The specialist agent's analytical checklist still drives the actual analysis — this file calibrates how findings and capabilities should look once written.

Immutability in security tooling has an unusual tension: the platform must support customer-deletion-request workflows (engagement-data right-to-be-forgotten, GDPR Article 17 for incidental personal data captured during testing) while simultaneously meeting legal-defensibility retention obligations (CFAA evidence base, ROE-attestation provenance, customer-MSA audit-clause minimums). The reconciliation is at the data-class level: audit metadata is immutable; result-data content can be redacted in place with the redaction event itself becoming an immutable record.

## Common finding patterns

**Pattern: Operator-action audit log written to a mutable RDS table or document collection; no append-only enforcement, no WORM substrate, no hash chaining.**

- Severity: critical (rubric: "Audit trail loss covering operator actions" — mutable audit is functionally absent audit; combines with any Non-Repudiation gap into a single critical-merged record)
- NIST: AU-9, AU-9(2), AU-9(3), AU-11, SI-7
- ATT&CK: T1070 (Indicator Removal); T1070.002 (Clear System Logs); T1565 (Data Manipulation) at the audit layer
- D3FEND: D3-SBV plus immutable storage substrate
- Related concerns: non_repudiation (the merged record), authenticity (audit signing key custody)

**Pattern: Engagement-start records mutable — operator can modify ROE attestation, target inventory, or authorization window after engagement start without retaining the prior version.**

- Severity: critical (rubric: "Audit trail loss" applies to ROE attestation; legal-defensibility for every subsequent command depends on the engagement-start record being tamper-evident)
- NIST: AU-9, AU-11, CM-3, SI-7
- Related concerns: non_repudiation (engagement-record provenance), authenticity (engagement-start signature)

**Pattern: Backup snapshots of engagement archives retained but no object-lock or compliance-mode immutability applied; single admin credential can delete all backups.**

- Severity: high (ransomware resilience absent; the primary recovery control absent; for security-tooling specifically, customer-MSA audit-clause retention is unmeetable if backups are deletable)
- NIST: CP-9, CP-9(1), CP-9(8), MP-4
- ATT&CK: T1485 (Data Destruction); T1490 (Inhibit System Recovery); T1486 (Data Encrypted for Impact) for ransomware case
- D3FEND: D3-FBA (File Block Analysis), D3-RCA (Resource Access Pattern Analysis) for ransomware detection
- Related concerns: availability (backup recoverability), confidentiality (backup encryption)

**Pattern: Plugin install records overwritten on plugin update or removal — historical record of which plugin version ran when is lost.**

- Severity: high (incident reconstruction impossible when a plugin is later discovered backdoored; supply-chain provenance gap)
- NIST: SR-4, SR-4(3), CM-8 (System Component Inventory), AU-11
- Related concerns: authenticity (signing root and signature-verification history), non_repudiation (plugin-load audit)

**Pattern: Result-data store allows operator deletion without retention of the deletion event or the deleted-record manifest.**

- Severity: high (chain-of-custody for customer-deliverable findings broken; an operator can delete embarrassing or contradictory results before customer delivery)
- NIST: AU-11, AU-9, MP-6 (Media Sanitization with audit), SI-12
- Related concerns: non_repudiation (result-harvest log), confidentiality (sensitive deletion still requires audit)

**Pattern: Signing-key lifecycle records (creation, rotation, revocation, destruction) stored in a mutable database; no tamper-evident retention.**

- Severity: high (key-management discipline unprovable; incident scoping impossible when a key is suspected compromised — can't tell when the key was actually in use)
- NIST: AU-9, AU-11, SC-12, SC-12(2)
- Related concerns: authenticity (the keys themselves), non_repudiation (key-lifecycle audit)

**Pattern: Configuration repository for ROE templates, plugin allowlists, engagement-scope policy allows history rewrite — no protected branches, no force-push prevention, no signed-commit requirement.**

- Severity: high (the security-policy-as-code substrate is mutable; policy changes can be retroactively rewritten to hide misuse)
- NIST: CM-3, CM-3(1), SI-7(8), SA-10 (Developer Configuration Management)
- Related concerns: authenticity (signed-commit posture), non_repudiation (commit-attribution loss)

**Pattern: Retention duration for engagement-related classes not specified in artifacts; conflict between regulatory retention and customer-deletion-request workflow not reconciled.**

- Disposition: blocked or uncertainty
- Severity: medium when blocked
- prerequisite_evidence: "Retention and deletion policy — per-data-class duration with regulatory and customer-MSA citation, enforcement mechanism, customer-deletion-request workflow with regulatory-retention reconciliation (redaction-in-place with redaction-event-retained vs. full deletion), legal-hold override procedure, and deletion-verification mechanism with audit"

## Common capability patterns

**Pattern: Operator-action audit log on append-only storage substrate (S3 with object-lock compliance mode, dedicated WORM-mode tier, immutable database like QLDB) with retention period set to the longest applicable customer-MSA minimum or longer.** Scope must specify which audit streams are confirmed on WORM; capabilities should enumerate retention period and lock mode.

**Pattern: Hash-chained audit log with daily chain-head anchored to an external trust domain (separate cloud account, separate KMS, external timestamp authority, transparency log).** Cross-cuts Non-Repudiation and Authenticity; the chain-head anchor is the load-bearing tamper-evidence claim.

**Pattern: Engagement-start records cryptographically sealed at engagement-start time with operator FIDO2/WebAuthn signature, stored on WORM substrate.** Higher maturity when the seal includes both operator attestation and a customer-confirmation event (where customer confirmation is available).

**Pattern: Customer-deletion-request workflow that redacts result-data content in place while retaining the audit metadata (request, redaction event, deleted-record manifest with content hash for proof-of-prior-existence).** Cross-cuts customer-MSA reconciliation; the load-bearing claim is that the redaction event itself is immutable.

**Pattern: Plugin install records retained for the lifetime of audit retention with full version-diff, signature-verification outcome, dependency lockfile, and source registry captured per install.** Higher maturity when the install record is signed by the platform's audit signing key at install time.

**Pattern: GitOps-driven configuration for ROE templates, plugin allowlists, and engagement-scope policies with signed commits, protected branches, force-push prevention, and per-commit audit linkage to engagement records.** Cross-cuts Authenticity (signed commits) and Non-Repudiation (commit attribution).

**Pattern: Signing-key lifecycle records on WORM substrate with creation, rotation, revocation, and destruction events captured with the responsible operator(s), justification, and cryptographic proof of the operation.** Cross-cuts Ephemeral (rotation cadence) and Authenticity (key custody); the WORM substrate is the immutability claim.
