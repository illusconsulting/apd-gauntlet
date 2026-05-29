# PBM common patterns — Immutability

These are illustrative templates, not all-inclusive. Use them to calibrate analytical style, severity assignment per the PBM rubric, and NIST/ATT&CK mapping habits. The specialist agent's analytical checklist still drives the actual analysis — this file calibrates how findings and capabilities should look once written.

Immutability in a PBM is governed by overlapping multi-year retention floors that the architecture must satisfy without depending on operator discipline: HIPAA at 45 CFR §164.316(b)(2) sets a 6-year retention floor on policies, procedures, and audit-relevant records; CMS Part D at 42 CFR §423.505(d) requires PDE and related records to be retained for 10 years; and DEA controlled-substance prescription records under 21 CFR §1304.04 require 2-year retention with chain-of-custody integrity. Object-lock, append-only stores, and tamper-evident hashing are the proportional controls — operator-deletable storage tiers cannot satisfy any of these floors. The load-bearing surfaces are the audit-log store (HIPAA chain), the PDE-submission archive and its CMS-reconciliation deltas (Part D chain), and the claim-adjudication history (which feeds both PDE and DEA chains, plus rebate and member-dispute defense).

## ATT&CK + D3FEND defensive mapping

This goal defends against (or is exploited by) the following MITRE ATT&CK techniques. Each citation is included only where the apd-control-mappings high-confidence-bar discipline is met; we deliberately omit techniques that only adjacently relate to this goal.

**ATT&CK techniques:**

- **T1485** (Data Destruction) — destruction of regulated immutable classes (audit log, PDE archive, formulary history, backup) directly defeats the HIPAA / Part D / DEA retention floors this goal enforces
- **T1490** (Inhibit System Recovery) — disabling snapshot, backup, or hash-chain mechanisms removes the substrate that makes the retention guarantee load-bearing
- **T1078** (Valid Accounts) — privileged-credential use to alter retention policy, object-lock setting, or vault-lock is the dominant path by which immutability is silently downgraded without triggering destruction alerts

**D3FEND counters:**

- **D3-LFAM** (Local File Access Mediation) — counters T1485 / T1490 by enforcing substrate-level write-deny on object-locked buckets, WORM tape, and hash-chained stores so that even a credentialed operator cannot mutate or delete protected classes within the retention window

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
- prerequisite_evidence: "Per-class retention specification — (1) for each immutability class declared (audit log, PDE archive, claim-adjudication history, formulary version history, controlled-substance prescription record, backup), the retention-floor citation (HIPAA §164.316(b)(2)(i), 42 CFR §423.505(d), 21 CFR §1304.04, 21 USC §360eee-1(d), state pharmacy-board floor); (2) the substrate enforcing the floor (S3 Object Lock Compliance Mode, Azure Blob immutable with legal hold, GCS locked retention, WORM tape, HSM-anchored hash-chained store); (3) the operator action that becomes infeasible under that substrate (e.g., root-credentialed delete, retention shortening, legal-hold removal); (4) the drift-detection mechanism that detects substrate misconfiguration (object-lock-disabled bucket, governance-mode downgrade, missing legal hold) and the alert routing for that detection."

**Pattern: Configuration drift between declared and actual immutability posture.**

- Disposition: uncertainty or blocked
- prerequisite_evidence: "Drift control specification — (1) the declared-state source-of-truth (IaC repository path, GitOps catalog, or policy-as-code bundle) for retention, object-lock, and protected-branch settings; (2) the actual-state observability mechanism (config-management agent, cloud-provider config service, periodic policy-sweep job) and the scope of resources it covers; (3) the drift-detection schedule (continuous, hourly, daily) and the alerting destination (SIEM channel, on-call rotation, ticket queue); (4) the reconciliation policy when drift is detected (auto-revert with audit trail, manual review with named approver, or block-on-drift with named escalation)."

## Common capability patterns

**Pattern: S3 object lock with compliance mode on backup buckets, retention period set to regulatory minimum.** Scope must specify which buckets are confirmed.

**Pattern: Hash-chained audit log with daily chain-head anchored to an external trust domain.** Cross-cuts Non-Repudiation; mention via `related_concerns`.

**Pattern: GitOps-driven configuration with signed commits and protected branches.** Maturity ladder: `designed` from tech plan; `implemented` requires repository configuration or pipeline evidence.

**Pattern: Formulary versioning with snapshot-at-decision retention on every adjudication.** Higher maturity requires schema or implementation evidence.
