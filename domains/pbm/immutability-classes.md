# PBM required-immutable data classes

For a PBM adjudicating pharmacy claims, submitting CMS Part D PDE records, and operating under HIPAA/HITECH plus state-board-of-pharmacy and DEA constraints, the following data classes must not change once written. Immutability findings test storage substrate, retention enforcement, and deletion controls against this list.

- **Audit log entries** — HIPAA Security Rule §164.312(b) audit-controls obligation and §164.316(b)(2)(i) 6-year documentation retention. SOC 2 typically 1–7 years per service-organization policy. Loss converts every adjudication-integrity claim into "we cannot verify."
- **Claim adjudication outcomes** — the per-claim accept/reject/reverse decision, the formulary state at adjudication time, the cost-share computation, and the plan-design rules applied. Required for reconcilability against pharmacy submissions, plan-sponsor invoicing, and member appeals under 42 CFR §423.128. Reversal must be recorded as a new event, never as overwriting the prior outcome.
- **Submitted CMS Part D PDE records** — CMS submission integrity and reconciliation against the Part D Reporting Requirements. CMS retention floor is 10 years per 42 CFR §423.505(d) and the Part D Reporting Requirements. Resubmission must preserve the prior PDE as historical record.
- **Prior authorization decisions** — approval/denial, clinical criteria applied, prescriber attestations, and member-notification timestamps. Required for CMS coverage-determination compliance under 42 CFR §423.566 and for state external-review proceedings.
- **Drug formulary historical state at point of adjudication** — the formulary tier, prior-auth requirement, step-therapy gate, and quantity limit live at the moment a claim adjudicated. Required to defend or reconstruct any past adjudication outcome; loss makes every retroactive audit indeterminate.
- **NCPDP SCRIPT and Telecom transactions** — the inbound pharmacy submission and the outbound PBM response, retained in their wire form with signatures intact. Required for after-the-fact "which message did the pharmacy actually send" reconstruction during dispute resolution and DEA inspection.
- **DEA controlled-substance prescription records** — for CII–CV dispensings touched by the PBM workflow, 21 CFR §1304.04 requires 2-year retention of prescription records; many states extend to 5 or 7 years. The transmission record, prescriber DEA number validation, and refill history are immutable to the regulatory floor.
- **Signed agreements and consent records** — pharmacy network contracts, plan-sponsor agreements, business associate agreements under 45 CFR §164.504(e), and member consents for data sharing. Retention floor matches the longest of HIPAA 6-year, contract term plus statute of limitations, and any state-specific obligation.
- **Member communications and notifications** — explanation-of-benefits delivery, prior-auth determination notices, formulary-change notifications, and breach notifications under 45 CFR §164.404. Proof-of-delivery is the immutable artifact; the notification body and the delivery timestamp must reconcile.
- **Backup snapshots** — ransomware resilience for the claims store, adjudication-engine state, member-eligibility cache, formulary store, and the audit log itself. Immutability via object-lock (compliance mode), WORM media, or write-locked tape. Mutability or deletion-by-single-credential is a critical finding because the backup is the post-breach recovery anchor for plan-sponsor reporting obligations.
- **Configuration history** — formulary rule changes, plan-design changes, adjudication-engine version history, RBAC policy changes, and clinical-criteria definitions. Required for root-cause analysis after adjudication-defect incidents and for SOC 2 CC8.1 change-management evidence.
- **Cryptographic key lifecycle records** — every CMS PDE signing key, NCPDP SCRIPT message-signing key, and key-encrypting key in the PBM's custody. Creation, rotation, suspension, and destruction events, each capturing the operator and the system clock at the event. Required because CMS audit defensibility, NCPDP signed-message non-repudiation, and breach-investigation forensics all depend on proving which key signed which artifact at which time. Retention is pinned to the longest of (a) HIPAA 6-year per 45 CFR §164.316(b)(2)(i), (b) CMS Part D 10-year PDE retention per 42 CFR §423.505(d), and (c) any signed-artifact retention floor that outlives both.

## Elaborated PBM-specific classes

The classes above appear in compact bullet form because each is anchored to a single dominant regulator. The classes below operate at the intersection of multiple regulators, multiple contract surfaces, and multi-year dispute windows, so each is elaborated separately with WHAT / WHY immutable / RETENTION framing.

### Rebate calculation history

WHAT: Manufacturer rebate calculations, plan-sponsor remit allocations, accumulator-state snapshots used to compute rebate eligibility, and the rebate-recovery audit trail. Includes the exact rebate-contract version applied to each claim cohort and the calculation inputs (utilization data, formulary tier at calculation time, manufacturer rebate-contract terms in effect).

WHY immutable: Rebate disputes routinely arise years after a calculation — manufacturer audits, plan-sponsor disputes, and government inquiries (DOJ False Claims Act investigations naming alleged rebate-pass-through fraud have been litigated against PBMs). The defensibility of any rebate calculation depends on being able to reconstruct exactly which contract version, which utilization data, and which formulary state produced the calculation. Mutable rebate calculation history makes plaintiff allegations of rebate manipulation effectively unrebuttable.

RETENTION: Pinned to the longest of (a) 7 years to cover most plan-sponsor MSA audit windows, (b) the term of the underlying manufacturer rebate contract plus 3 years for dispute, (c) any state insurance-department retention requirement for PBM business records. Practical floor is commonly 10 years for major-market plans.

### MAC pricing history

WHAT: Maximum Allowable Cost list versions over time, the source data informing each version (compendia inputs, pharmacy-acquisition cost samples), the publication dates and effective-date windows, the per-pharmacy MAC variants where the PBM operates differentiated networks, and the pharmacy-appeal history (claims appealed under MAC-appeal rights granted by state law).

WHY immutable: State MAC-transparency laws (~40 states have such statutes as of this writing) routinely grant pharmacies the right to appeal MAC-priced claims and require the PBM to retain MAC source data for audit. Pharmacy-network reimbursement disputes turn on which MAC was in effect when a specific claim adjudicated. <!-- SME-review: confirm the current state-by-state retention requirements; this draft uses 7 years as a generic floor but several state statutes specify different retention windows. -->

RETENTION: Pinned to the longest of (a) the underlying contract retention floor, (b) state MAC-transparency law retention (varies by state), (c) any pharmacy-appeal window plus statute-of-limitations grace period.

### Network-pharmacy contract terms at adjudication

WHAT: The actual contract terms in effect at the moment of each claim adjudication — pharmacy-network tier (preferred / standard / out-of-network), dispensing-fee schedule, ingredient-cost basis (AWP-discount, WAC-discount, NADAC-discount), copay-collection rules, generic-substitution rules. Critically: NOT the current contract terms; the historical contract terms at the moment that specific claim was adjudicated.

WHY immutable: Pharmacy networks renegotiate constantly; contract terms drift by quarter. Pharmacy-claim disputes (and the related litigation surface) are routinely scoped to the contract version in effect at adjudication, not the current contract version. Pharmacy-network audit programs require the PBM to demonstrate that each claim was priced under the correct contract version at the correct effective date. Mutable contract-terms-at-adjudication history collapses the PBM's defensibility against systematic-overcharge or systematic-underpayment allegations.

RETENTION: Pinned to (a) the longest pharmacy-network contract retention floor across the PBM's contract base, typically 7+ years, (b) any state insurance-department audit window. Practical floor commonly 10 years.

### DSCSA track-and-trace records

WHAT: Drug Supply Chain Security Act dispensing-event records — the chain-of-custody data for each prescription dispensed, including transaction history (TH), transaction information (TI), and transaction statement (TS) per 21 USC §360eee-1. Includes the manufacturer-of-record, the wholesale-distributor lineage, the lot-and-expiration data, and the dispensing-pharmacy attribution.

WHY immutable: DSCSA §582 requires dispensing entities (which includes mail-order and specialty pharmacies operated by or under contract with the PBM) to retain transaction information for 6 years from the date of the transaction. Mutable TI/TS data destroys the chain-of-custody integrity that DSCSA was enacted to protect; FDA inspections rely on reconstructable DSCSA records to investigate suspect products. <!-- SME-review: confirm whether the PBM's specialty-pharmacy and mail-order operations are themselves §582-regulated dispensing entities or whether DSCSA exposure is limited to the pharmacy partners. -->

RETENTION: 6 years from transaction date per 21 USC §360eee-1(d). State pharmacy-board reporting requirements may extend this floor.

### State pharmacy-board reportable events

WHAT: Events that trigger state pharmacy-board reporting obligations — adverse drug events identified through PBM-side DUR processing, controlled-substance dispensing anomalies surfaced through PMP integration, pharmacy-licensure-relevant findings (counterfeit-drug suspicion, diversion patterns), and any event that the PBM is required to report to a state board under the licensure framework governing its mail-order or specialty operations.

WHY immutable: State pharmacy boards investigate practice complaints with multi-year lookback windows; the PBM's ability to demonstrate timely and accurate reporting depends on having an immutable record of what was reported, when, and to which board. Mutable reportable-events history converts a routine state-board inquiry into a documentation failure independent of the underlying clinical question. <!-- SME-review: state pharmacy-board retention requirements vary substantially; confirm the floor for the PBM's primary operating states. -->

RETENTION: Pinned to the longest applicable state pharmacy-board retention floor across the PBM's operating footprint; typically 5–10 years depending on state.

## Failure-mode triggers

Specialists raise an Immutability finding against any class on this list when any one of the following four conditions is met. Any single trigger is sufficient; multiple triggers compound the severity.

1. **Mutable storage** — the class is held in a substrate that supports in-place update without a tamper-evident audit trail. Default RDBMS rows holding adjudication outcomes, S3 objects holding PDE submissions without object-lock, in-place overwrite of formulary-history files, and any "UPDATE claims SET status = ..." path on a regulated class all qualify.
2. **Absent retention floor** — no retention period is declared or enforced on the class. Deletion can happen on operator whim before the regulatory floor (HIPAA 6-year, CMS Part D 10-year PDE retention per 42 CFR §423.505(d), DEA 2-year controlled-substance prescription retention per 21 CFR §1304.04). The absence of a documented retention policy is itself the finding; "we just keep everything" without enforcement does not satisfy the trigger.
3. **Deletion-by-single-credential** — a single operator credential can delete or alter the class without two-party control, dual approval, vault-lock policy, or compliance-mode object-lock. The PBM's database administrator, cloud-account root, or backup-system operator must not be able to single-handedly destroy regulated records.
4. **Unspecified retention** — the class is declared immutable but the retention duration is not pinned to a regulatory anchor or a contractual obligation. "Retain forever" without policy is itself a finding because the absence of a pinned floor makes the class indistinguishable from a class with no retention at all under audit.

**Cross-reference.** When the failing class is also an audit-event class (operator-action log, audit-of-audit records, adjudication-decision audit), the Non-Repudiation lens should be notified via `related_concerns` on the finding so the synthesizer can merge the records. When the failing class is encrypted-at-rest PHI (member records, claim payloads, PA clinical attachments), the Confidentiality lens should be cross-referenced. Specialists must use the `lens_perspectives` block on the finding so that if both lenses surface the same root cause the synthesizer preserves each lens's framing in the merged record rather than discarding one.

## Substrate enforcement

The four failure-mode triggers above are satisfied by concrete storage substrates. Specialists should name the substrate when emitting an Immutability finding so the remediation pointer is actionable.

- **S3 Object Lock in Compliance Mode** — satisfies HIPAA 6-year audit-log retention, CMS Part D 10-year PDE retention, and SOC 2 retention floors. Makes infeasible: shortening the retention period, deleting the object, or modifying the object — even by the AWS root account. Governance Mode is **not** sufficient because privileged operators can bypass it; Compliance Mode is the required configuration.
- **Azure Blob immutable storage with legal-hold policy** — satisfies HIPAA, CMS Part D, and customer-contract retention floors. Makes infeasible: blob deletion, content modification, and policy shortening for the duration of the legal hold or time-based retention.
- **GCS bucket retention policy with locked configuration** — satisfies the same regulatory floors. Makes infeasible: shortening the retention period and deleting objects within the retention window, even by project owners; the locked configuration cannot be reverted once applied.
- **WORM-mode tape or optical media for offsite archives** — satisfies CMS Part D 10-year retention and disaster-recovery obligations under HIPAA §164.308(a)(7). Makes infeasible: in-place overwrite at the physical-media layer; tampering requires physical destruction, which is detectable through chain-of-custody.
- **HSM-anchored hash-chained log stores** — for example, AWS QLDB for the adjudication-decision journal, or GCP Cloud Audit Logs with a sink to a separate immutable GCS bucket whose write credentials are not held by the source-account operators. Satisfies the tamper-evidence requirement of HIPAA §164.312(c)(1) integrity controls and the audit-controls obligation of §164.312(b). Makes infeasible: rewriting historical entries without producing a hash-chain discontinuity that subsequent verification will detect.

A substrate that does not appear on this list is not automatically a finding, but the specialist must articulate which of the four triggers it defeats and how. "Encrypted at rest" alone does not satisfy any immutability trigger; encryption protects confidentiality, not against authorized in-place mutation.
