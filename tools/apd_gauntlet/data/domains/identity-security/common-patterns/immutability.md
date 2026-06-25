# Identity security common patterns — Immutability

These are illustrative templates, not all-inclusive. Use them to calibrate analytical style, severity assignment per the identity security rubric, and NIST/ATT&CK mapping habits. The specialist agent's analytical checklist still drives the actual analysis — this file calibrates how findings and capabilities should look once written.

## Common finding patterns

**Pattern: Authentication event log written to a mutable RDS table or document collection; no append-only enforcement, no WORM substrate, no hash-chain.**

- Severity: high (authn log alteration breaks every regulatory accountability claim; combines with any Non-Repudiation gap into a critical-merged record — the authn log is the first thing an attacker tampers with after gaining IdP-admin)
- NIST: AU-9, AU-9(2), AU-9(3), AU-11, SI-7
- ATT&CK: T1070 (Indicator Removal); T1070.001 (Clear Windows Event Logs); T1070.002 (Clear Linux or Mac System Logs); T1565 (Data Manipulation)
- Cross-reference: any Non-Repudiation finding on audit completeness; merged record carries both concerns

**Pattern: OAuth/OIDC consent records mutable — consent revocation overwrites the consent record rather than recording revocation as a new event.**

- Severity: high (the proof-of-consent for processing that occurred during the consent window is destroyed; GDPR Article 6(1)(a) defense fails for any processing that occurred during the consent window)
- NIST: AU-11, AU-9, CM-2(3)
- Related concerns: non_repudiation (consent-event audit completeness), confidentiality (consent records contain personal data)

**Pattern: SAML assertion-ID replay store retention shorter than the longest NotOnOrAfter window in production — the store cannot guarantee replay detection.**

- Severity: high (SAML assertion replay is a documented attack class; the replay-prevention store IS the immutable-during-window security primitive)
- NIST: AU-11, SI-7, IA-2, SC-23
- Related concerns: integrity (the replay store's eviction policy), distributed (cross-region replay-store consistency)

**Pattern: Signing-key rotation history not retained — only the current and previous kid are queryable; older kids are dropped from JWKS-history table.**

- Severity: high (after-the-fact verification of "which kid signed which token at what time" is impossible; post-incident compromise scoping fails)
- NIST: SC-12, SC-12(2), AU-11, SI-7
- Related concerns: ephemeral (rotation cadence), non_repudiation (key-lifecycle audit)

**Pattern: Backup snapshots of the credential store, the session store, and the key-lifecycle records meet retention but no object-lock or compliance-mode immutability is applied.**

- Severity: high (backups vulnerable to ransomware deletion; the IdP backup is the post-breach recovery anchor for every dependent application; deletion-by-single-credential is the canonical ransomware target)
- NIST: CP-9, CP-9(1), CP-9(8), MP-4
- ATT&CK: T1485 (Data Destruction); T1490 (Inhibit System Recovery)
- Related concerns: availability (backup recoverability — can we actually restore?), confidentiality (backup encryption — and the key separation question)

**Pattern: Federation-trust configuration partly IaC, partly manual via admin console; no drift detection between declared and actual federation-trust state.**

- Severity: high (federation-trust mutations are admin-tier consequential actions; manual mutation breaks GitOps attribution, evades signed-commit discipline, and produces "where did this SP entry come from?" forensic gaps)
- NIST: CM-2, CM-2(2), CM-3, CM-6, CM-6(2), CM-8
- Related concerns: integrity (config correctness), authenticity (the signed-commit posture for the IaC half), non_repudiation (admin-action attribution)

**Pattern: Configuration repository allows history rewrite — no protected branches on the IdP-config repo, no force-push prevention, no signed-commit requirement on RBAC / federation-trust / authorization-policy files.**

- Severity: medium to high
- NIST: CM-3, CM-3(1), SI-7(8), SA-10 (developer configuration management)
- Related concerns: authenticity (signed commits provide attribution but mutable history defeats it), non_repudiation (commit-attribution loss)

**Pattern: Identity-proofing artifacts (IAL2/IAL3 verification records) stored mutably or with retention shorter than the lifetime of the proofing claim downstream.**

- Severity: high (the IdP asserts an IAL claim to downstream RPs; if the underlying evidence is gone, the IAL claim cannot be re-verified post-incident, and an IAL-fraud claim cannot be disputed)
- NIST: IA-12 (identity proofing), AU-11, SI-7
- Related concerns: non_repudiation (proofing-event audit)

**Pattern: Retention duration not specified per audit class — the artifacts assert "audit is retained" without per-class duration, regulatory citation, or enforcement mechanism.**

- Disposition: uncertainty or blocked
- prerequisite_evidence: "Retention policy — per-audit-class duration with regulatory citation (authn events, authz events, token-lifecycle events, consent events, federation events, admin actions, key-lifecycle events, data-subject-rights events), enforcement mechanism (storage-tier lifecycle policy, application-level enforcement), legal-hold override procedure, deletion-verification mechanism, and the per-class storage substrate (WORM vs. append-only vs. mutable)"

## Common capability patterns

**Pattern: Append-only authentication and authorization event log with per-stream hash-chaining; chain heads anchored daily to a separate trust domain.** Capability scope must enumerate which event streams are confirmed in scope; cross-cuts Non-Repudiation.

**Pattern: Object-lock with compliance mode on backup buckets for credential store, session store, audit log, and key-lifecycle records; retention period set to the longest applicable regulatory minimum.** Scope must specify which buckets are confirmed and the retention period per bucket.

**Pattern: SAML assertion-ID replay store with TTL ≥ longest NotOnOrAfter window in any active SP relationship; replay events audited as security-relevant.** Cross-cuts Integrity.

**Pattern: Signing-key rotation history immutable and queryable — every kid that has ever been published is retained with its active window, the rotation event, and the revocation event (if any).** Cross-cuts Ephemeral and Non-Repudiation.

**Pattern: GitOps-driven IdP configuration (RBAC, federation-trust, authorization policy, audit-pipeline config) with signed commits, protected branches, force-push prevention, and drift detection against the running configuration.** Maturity ladder: `designed` from tech plan; `implemented` requires repository configuration plus deployment-pipeline evidence; `operationalized` requires evidence of the drift-detection-and-alerting loop closing.

**Pattern: Retention enforcement per audit class via storage-tier lifecycle policy plus application-level legal-hold override; deletion-verification reports on a documented cadence.** Higher maturity when the legal-hold override is itself audited and the retention metrics are dashboarded.
