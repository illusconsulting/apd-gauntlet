---
name: apd-domain
description: Active domain pack content — severity rubric, consequential actions, common patterns. Generated from one or more domain packs at build time; do not edit by hand.
metadata:
  packs:
    - name: pbm
      version: 1.0.0
  framework_version: 1.7.0
  generated: 2026-06-25T02:15:55Z
---

## Domain: pbm — Source: `severity-rubric.md`

# PBM Severity Rubric (impact-to-PBM)

Calibrated against impact-to-PBM, not against generic CVSS. The specialist agent cites the matching clause in finding `detail` fields. Cited examples in each tier are illustrative, not exhaustive.

PBM severities have a **second dimension** beyond classic HIPAA-data-confidentiality and CMS-data-integrity: the **clinical patient-harm dimension**. A finding that exposes PHI or corrupts PDE submission is scored on the data-and-regulatory axis; a finding that affects a clinical-decision pathway — drug-utilization review, prior-authorization decision, formulary-substitution logic, dispense-as-written enforcement, dosage calculation — is scored on the patient-harm axis. Many findings score on both axes; severity is the higher of the two. The PBM-specific implication: a DUR-rule edit that produces a missed drug-interaction alert can be Critical on the patient-harm axis even if the affected member-population is below the 500-member HIPAA breach threshold on the data-and-regulatory axis.

References inline: HIPAA Privacy Rule (45 CFR 164 Subpart E), HIPAA Security Rule (45 CFR 164 Subpart C), NIST SP 800-53r5 control families, NIST SP 800-63B authenticator assurance levels (AAL2/AAL3), MITRE ATT&CK Enterprise techniques, MITRE D3FEND countermeasures, NCPDP Telecommunication Standard D.0, CMS Part D PDE Submission (42 CFR 423.322), HITRUST CSF (healthcare accreditation framework).

## Critical

Any of the following:

- **PHI exfiltration capability affecting >500 members** in a single realistic attack scenario. Triggers HIPAA breach notification per 45 CFR §164.408 (federal, state, and media notification). The 500-member threshold is the legal pivot point for required public disclosure. Maps to T1213 (Data from Information Repositories) for bulk reads against the PHI store, plus T1041 (Exfiltration Over C2 Channel) or T1567 (Exfiltration Over Web Service) depending on the channel the attacker can reach; note that NCPDP D.0 transactional egress (claim-response payloads returned to switches and pharmacy chains) is itself a PHI-carrying channel and must be in scope for the same egress controls. D3FEND counter is D3-OTF (Outbound Traffic Filtering — DLP at the egress boundary) and D3-NTA (Network Traffic Analysis on outbound flows from the PHI tier). NIST 800-53r5 anchor: AC family — AC-3 (Access Enforcement), AC-4 (Information Flow Enforcement), AC-6 (Least Privilege) — plus SI-4 (System Monitoring) and SC-7 (Boundary Protection) on the egress surface.
- **Claim adjudication corruption affecting therapeutic decisions** — wrong drug dispensed, wrong dose, missed Drug Utilization Review (DUR) alert, formulary bypass that exposes patients to harmful drug interactions, missed prior authorization on safety-gated drugs. Direct patient harm risk. Maps to T1565.001 (Stored Data Manipulation) for tampering of the formulary, DUR, or PA-criteria configuration stores that drive the adjudication decision, and T1565.002 (Transmitted Data Manipulation) for in-flight tampering of the NCPDP claim request or response between switch and adjudication engine; D3FEND counter is D3-MAN (Message Authentication) on signed NCPDP D.0 transactions, paired with operational safeguards on the clinical-decision-logic configuration surface (no clean D3FEND ID exists for decision-path runtime validation; rely on the NIST 800-53r5 SI-7 / CM-3 / CM-5 anchors below). NIST 800-53r5 anchor: SI family — SI-7 (Software, Firmware, and Information Integrity) and SI-10 (Information Input Validation) — plus CM-3 (Configuration Change Control) and CM-5 (Access Restrictions for Change) on the clinical-decision-logic configuration surface.
- **Authentication bypass to PHI surfaces or admin functions** — no factor required, or trivially circumventable factor, against any surface that returns claims data, member PHI, prescriber records, or adjudication-engine admin controls. Includes JWT `alg:none` accepted, signature verification skipped, or RS256-verified-as-HS256 key-confusion on pharmacist-portal or prescriber-portal tokens; SAML XML Signature Wrapping (XSW) on pharmacist/prescriber SSO yielding subject substitution into another NPI's session; password-reset bypass via predictable reset tokens, unauthenticated reset endpoints, or reset flows that do not require the prior credential or a possession factor; MFA enrollment endpoints reachable without re-authentication so an attacker with a stolen single-factor session enrolls their own second factor; and session fixation that survives the PHI-access transition so a pre-authentication session ID remains valid after the member, pharmacist, or call-center agent logs in. Maps to T1078 (Valid Accounts) for credential-and-session reuse paths and T1556 (Modify Authentication Process) for the JWT, SAML XSW, and reset-flow primitives that subvert the verification logic itself; D3FEND counter is D3-MFA (Multi-factor Authentication) on the PHI and admin surfaces; reset-flow and MFA-enrollment endpoints additionally require step-up authentication (NIST 800-53r5 IA-2 reauthentication anchor below). NIST 800-53r5 anchor: IA family — IA-2 (Identification and Authentication of Organizational Users) including IA-2(1) and IA-2(2) for MFA, IA-5 (Authenticator Management), IA-8 (Identification and Authentication of Non-Organizational Users) for member and prescriber portals — plus AC-7 (Unsuccessful Logon Attempts) and AC-12 (Session Termination). NIST SP 800-63B anchor: PHI and admin surfaces should be evaluated at AAL2 minimum, with AAL3 (hardware-bound, phishing-resistant authenticator with verifier-impersonation resistance) for adjudication-engine admin and any surface returning bulk PHI.
- **Audit trail loss covering PHI access** — renders breach detection and notification obligations un-meetable; regulatory non-compliance independent of breach occurrence. Includes silent log disable, retention shortened below the HIPAA 6-year floor (45 CFR §164.316(b)(2)(i)), or log-shipping pipeline interrupted without separately-attested record on a forensically isolated channel. Maps to T1070 (Indicator Removal), with T1070.002 (Clear Linux or Mac System Logs) where the underlying audit substrate is OS-level; D3FEND counter is immutable substrate (S3 Object Lock Compliance Mode, Azure Blob immutable storage with legal hold, HSM-anchored hash-chained store) plus D3-LFAM (Local File Access Mediation) on the log substrate. NIST 800-53r5 anchor: AU family — AU-9 (Protection of Audit Information), AU-11 (Audit Record Retention), AU-12 (Audit Record Generation).
- **Total adjudication outage exceeding contractual SLA** — sustained inability to adjudicate claims affecting all plan sponsors simultaneously.
- **Loss of CMS Part D submission integrity / PDE corruption** — PDE (Prescription Drug Event) data submission failures or corruption that exposes the PBM to CMS enforcement action under 42 CFR §423.322, including payment-determination reopening, plan-payment recovery, and potential False Claims Act exposure (31 U.S.C. §3729) when a submission is knowingly false. Maps to T1565 (Data Manipulation), with T1565.002 (Transmitted Data Manipulation) for in-flight PDE tampering between the PBM and CMS and T1565.001 (Stored Data Manipulation) for at-rest corruption of the PDE staging or archive store; D3FEND counter is D3-MAN (Message Authentication) on signed PDE submission batches (per-batch signature verification at CMS ingest is the load-bearing control). NIST 800-53r5 anchor: SI family — SI-7 (Software, Firmware, and Information Integrity) including SI-7(6) for cryptographic protection — plus AU-10 (Non-repudiation) on the submission record and SC-8 (Transmission Confidentiality and Integrity) on the outbound channel to CMS.

## High

Any of the following:

- **PHI exposure beyond minimum-necessary internal audience** — violates 45 CFR §164.502(b). Includes overbroad role assignments, missing field-level controls on PHI elements, or admin tooling that exposes more PHI than the operator's role requires. Maps to T1213 (Data from Information Repositories) for over-broad authenticated reads against PHI stores; NIST 800-53r5 anchor AC-6 (Least Privilege) and AC-4 (Information Flow Enforcement).
- **Claim adjudication errors bounded to a subset** — single plan sponsor, single drug class, single channel (mail order vs retail), or single member population. Erroneous adjudication but blast radius is contained.
- **Authentication weakness short of bypass** — MFA bypass requiring adjacent factor, credential reuse window exceeding policy, session lifetime exceeding policy, weak password requirements on a PHI surface. Maps to T1621 (Multi-Factor Authentication Request Generation) for MFA-fatigue/push-bombing paths and T1078 (Valid Accounts) for credential-reuse paths; NIST 800-53r5 anchor IA-2(1) and IA-2(2) for MFA, IA-5 (Authenticator Management).
- **Partial audit gap on PHI-adjacent surfaces** — admin actions logged but lacking actor attribution, audit logs shipped without integrity protection, audit retention shorter than 6 years (HIPAA minimum). Maps to T1070 (Indicator Removal) where retention or integrity gaps would let an attacker erase or alter their trace; NIST 800-53r5 anchor AU-9 (Protection of Audit Information), AU-11 (Audit Record Retention), AU-12 (Audit Record Generation).
- **Adjudication degradation with manual workaround required** — system functional but requires operator intervention to complete claims, sustained.
- **CMS Part D compliance gap not affecting member dispensing** — formulary update lag, prior authorization workflow gap, transition fill logic gap, that does not currently affect a dispensing decision but is required by CMS-4201-F or equivalent.
- **URAC accreditation-relevant gap** — control absence in a domain URAC evaluates, where the absence would be findable in an accreditation audit.

## Medium

Any of the following:

- **Defense-in-depth gap where a compensating control exists** but is the only barrier — single point of control failure. Encryption at rest absent because TLS terminates inside the trust boundary is the canonical example.
- **Recoverable adjudication delay within SLA** — performance regression that the SLO budget absorbs but consumes headroom.
- **Logging gap on non-PHI surfaces** — operational visibility loss that does not affect breach detection.
- **Hardening weakness exploitable only after adjacent compromise** — requires the attacker to already have a foothold elsewhere. Useful to fix; not catastrophic if deferred.
- **Configuration drift detection gap** on systems where compensating attestation exists.
- **Documentation gap with security-relevant content missing** — architecture decision records, runbooks, or threat models absent in ways that impair operations or future review.

## Low

Any of the following:

- **Hygiene issue with no realistic exploit path** — deprecated cipher with no client support, redundant control with overlapping coverage, configuration verbosity.
- **Documentation deficiency** — non-security-critical content missing, formatting inconsistency, naming convention drift.
- **Defense-in-depth gap fully compensated** by upstream controls — useful to know but architecturally non-urgent.
- **Configuration drift on non-critical path** — dev environment, ephemeral test infrastructure.

## Informational

Observations that do not rise to remediation but are worth surfacing for the architecture record. Used sparingly. Examples: notable architectural choices with security implications worth documenting, parity gaps with industry peers that are not actually risks.

---

## Clinical patient-harm axis

The PBM severity ladder above scores findings on the data-and-regulatory axis (PHI confidentiality, PDE integrity, audit defensibility). The second axis below scores findings on the clinical patient-harm dimension. Assign the severity that is the MAX of the two axes.

### Critical (clinical patient-harm)

- **Wrong drug dispensed at the pharmacy counter** — finding makes it plausible that the PBM's pricing or adjudication response produced a substitution that the prescriber did not approve and that the patient would not have received but for the PBM error. Maps to T1565.002 (Transmitted Data Manipulation) when the corruption is in-flight; T1565.001 when in the formulary store.
- **Missed drug-utilization-review alert leading to harmful drug interaction** — finding makes it plausible that the DUR engine suppressed, did not raise, or routed away a clinically-significant interaction alert (drug-drug, drug-disease, drug-allergy, drug-age, therapeutic duplication). Includes DUR-rule configuration that excludes a class of patient (e.g., pediatric, geriatric, pregnant) from alerts they should receive.
- **Missed prior-authorization on safety-gated drug** — finding makes it plausible that the PA-criteria engine approved or auto-routed-around a request that the PA criteria were explicitly designed to gate for clinical safety reasons (REMS-enrolled drugs, controlled substances above MED thresholds, specialty oncology agents with monitoring requirements). Maps to T1565.001 (Stored Data Manipulation) against the PA-criteria configuration store.
- **Formulary bypass exposing patient to clinically harmful substitution** — finding makes it plausible that a formulary-tier reassignment, generic-substitution rule, or step-therapy-bypass produced a dispense decision that the formulary committee explicitly excluded for clinical-safety reasons. Maps to T1565.001 (Stored Data Manipulation) against the formulary configuration store.
- **Dose calculation error** — finding makes it plausible that the days-supply calculation, the weight-based-dosing logic, or the pediatric/geriatric dosing rule produced an unsafe dose. Particularly load-bearing for opioids (MED calculation), insulin, anticoagulants, and pediatric formulations. Maps to T1565.002 (Transmitted Data Manipulation) on the adjudication response when the dose is computed in-flight; NIST 800-53r5 anchor SI-10 (Information Input Validation) on dose-calculation inputs.

### High (clinical patient-harm)

- **DUR-rule or PA-criteria edit without dual approval** — the editing surface for clinical-decision logic accepts single-operator changes; finding scores High because it creates the capability for any of the Critical-tier clinical-harm scenarios above without an enforcement gate.
- **Formulary tier change applying retroactively** — finding makes it plausible that a tier reassignment alters claims that were already adjudicated, retroactively shifting cost or coverage in ways that destabilize patient adherence or trigger member-confusion-driven non-compliance.
- **DUR alert silently suppressed by operator without attestation** — operator UI permits DUR-alert suppression without recording a clinical-justification field, supervisor attestation, or pharmacist review. Creates a hidden patient-harm capability.
- **PA appeal-decision routing failure** — Medicare Part D requires redetermination decisions within tight timelines (42 CFR §423.590 — 7 calendar days standard, 72 hours expedited); finding makes it plausible that the appeal-routing logic produces missed timelines that convert to coverage denials by default.

### Medium (clinical patient-harm)

- **DUR alert displayed but easily dismissed** — clinically-significant alerts can be dismissed with a single click and no justification; clinical-decision quality depends on operator habit rather than enforcement. Worth raising; not catastrophic.
- **Formulary-update lag affecting non-safety drugs** — formulary changes propagate with a delay that affects copay or coverage but does not affect drug safety.
- **PA criteria documentation drift** — the configured criteria differ from the published formulary documentation in ways that affect member expectations but not safety.

### Low (clinical patient-harm)

- **Clinical-context surface with no realistic harm path** — UI labels for clinical fields use unclear or inconsistent language; no error in computation or routing.
- **Documentation gap on a clinical-decision surface** — operator-facing help text incomplete; clinical logic itself is correct.

---

## Severity calibration discipline

- **Cite the rubric clause in `detail`.** "This is high severity because it falls under 'PHI exposure beyond minimum-necessary internal audience' per the impact-to-PBM rubric, specifically [reasoning]."
- **Do not average across multiple impacts.** A finding that has critical PHI exposure AND medium operational risk is critical.
- **Do not inflate to signal importance.** The synthesizer escalates and reconciles severity disagreements between agents; over-claiming on one agent degrades the cross-agent reconciliation signal.
- **When in doubt, drop one level.** A high-confidence medium is more useful than a low-confidence high.
- **Asymmetric escalation rule.** When a finding sits between two tiers, escalate to the higher tier only if at least one of the following holds: (a) regulator action is plausible given the cited rubric clause — HHS OCR enforcement under 45 CFR §164.408, CMS Part D sponsor compliance action, or state pharmacy-board action against the dispensing channel; (a2) an accreditation-relevant adverse finding is plausible — URAC PBM accreditation, HITRUST CSF certification (the dominant healthcare accreditation framework for which PBMs are commonly certified), or SOC 2 Type II for the service-organization controls relied upon by plan-sponsor customers; (b) the finding affects a clinical-decision pathway — Drug Utilization Review (DUR), formulary determination, prior authorization, or dispensing instruction generation; (c) the blast radius covers more than one plan sponsor, or more than 500 members in a single sponsor. If none of these holds, drop to the lower tier. The default direction at the boundary is down, not up.
- **Capability-vs-exploited equivalence rule.** The rubric scores realistic attack capability, not whether exploitation has been observed. An UNDISCLOSED adjudication-corruption capability — a path through which an attacker could cause wrong-drug-dispensed, missed DUR, or formulary bypass — and an OBSERVED wrong-drug-dispensed event are both Critical when the latent capability would meet the Critical clause if exercised. The rubric basis is the HIPAA Security Rule risk-management standard at 45 CFR §164.308(a)(1)(ii)(B), which obligates the covered entity to address reasonably anticipated risks — not only realized harms — to PHI confidentiality, integrity, and availability.

## Domain: pbm — Source: `consequential-actions.md`

# PBM consequential-action surface

For a PBM, the following actions are consequential and must be auditable. Non-Repudiation findings evaluate logging coverage against this list.

- Any PHI access (read, export, print)
- Any adjudication decision (approve, deny, soft-deny)
- Any administrative configuration change (formulary, plan rules, prior authorization criteria, user role)
- Any authentication event (successful, failed, MFA challenge result)
- Any authorization decision that grants access to PHI or admin functions
- Any data export or report generation containing PHI
- Any vendor or partner API call carrying PHI
- Any change to system configuration affecting security posture
- Any break-glass or emergency override

This list is not exhaustive. Specialists should treat actions outside this list as candidates for inclusion — flagging them as evidence gaps until the operator confirms.

## Audit-of-audit surface

The audit-event store is itself a consequential-action surface. A breach investigation that begins at the audit log is worthless if the log was silently truncated, retention shortened, or shipping redirected by the same insider whose actions are under investigation. Every operation on the audit substrate must be logged in a forensically isolated channel that the operators of the primary log cannot reach with their primary credentials.

The following actions on the audit substrate must produce a distinct, separately-attested audit record on an independent sink (separate credential store, separate retention policy, separate alerting path):

- Administrative read of the audit log (any query that retrieves audit records for reasons other than the live event-review workflow — bulk export, ad-hoc search, regulator-disclosure pull)
- Any change to the audit retention policy (shortening retention, changing the cold-storage tier, altering the legal-hold flag on existing records)
- Any change to log-shipping configuration (sink endpoint, transport credential, batching window, schema-translation rule, redaction policy)
- Any access to the integrity-control mechanism (read or rotation of the hash-chain head, read or rotation of the audit-signing key, any operation on the WORM seal)
- Disable or pause of the audit pipeline (whether explicit, via feature flag, or via dependency-failure short-circuit)
- Any restore from audit backup, replay of audit records, or re-ingest from a secondary substrate

This requirement anchors to HIPAA Security Rule §164.308(a)(1)(ii)(D) (Information System Activity Review — the covered entity must regularly review records of information system activity, which presumes those records are intact) and §164.312(b) (Audit Controls — implementation of hardware, software, and procedural mechanisms that record and examine activity in information systems containing ePHI). The control-family anchor is NIST SP 800-53r5 AU-9 (Protection of Audit Information — protect audit information and audit logging tools from unauthorized access, modification, and deletion) and AU-12 (Audit Record Generation — define audit-record-generation capabilities for events, with appropriate selection of auditable events at organizational discretion).

The practical test: **if the audit log can be silently disabled or its retention shortened by a single operator credential without a separately-attested record landing on the isolated channel, the Non-Repudiation finding should escalate to Critical per the severity rubric.** The same operator who adjudicates claims, configures formularies, or services member calls must not also hold the credential that can erase the evidence of those actions; if the dual-control boundary is not enforced, the entire downstream audit story is suspect.

## Break-glass discipline

Emergency PHI access is a legitimate operational reality for PBMs — a pharmacist needs eligibility data during a network outage, a clinical reviewer needs full member history during a suspected adverse-drug-event investigation, a regulator subpoena demands disclosure outside the normal disclosure path, an after-hours on-call engineer needs raw access to debug an adjudication failure that is blocking time-critical fills. HIPAA §164.510(b)(3) (Emergency Circumstances) provides the lawful basis for use and disclosure outside the routine consent path when the disclosure is in the individual's best interest and cannot reasonably be obtained otherwise. That lawful basis is conditional on a complete, second-party-attested audit trail; an unaudited break-glass invocation is a HIPAA violation regardless of how legitimate the underlying need was.

Every break-glass invocation must produce a high-severity audit event that captures, at minimum:

- The credential used (user identifier, the role held at the moment of invocation, the authentication factor satisfied, the session identifier)
- The patient(s) subject of the access (member identifier or — where the invocation grants pattern-of-access rather than single-record-access — the bounded query that selected the records)
- The clinical or operational justification entered at invocation, in free-text form, attested by the invoker (not a pre-canned dropdown — the text record is the evidence of intent and is itself reviewable)
- The duration of the elevated session (start timestamp, end timestamp, the mechanism that closed the elevation — voluntary termination, idle timeout, absolute timeout, supervisor revocation)
- The supervisor or on-call manager who attested to the access (either pre-attestation at invocation or post-attestation within the review SLA — the role and identity of the second party is part of the record)
- The downstream actions taken within the elevated session (every PHI read, every export, every configuration change made under break-glass scope is itself audited, and those child events are linked back to the parent break-glass event so the full blast radius is reconstructable)

Every break-glass event must be reviewed by the privacy office and signed off **within 24 hours** of invocation. An unreviewed break-glass event past that SLA is itself a Non-Repudiation finding — the lawful-basis posture under §164.510(b)(3) depends on demonstrable oversight, and an aging unreviewed queue is evidence that the oversight is performative rather than real. Specialists should treat a backlog of >5 unreviewed break-glass events older than 24 hours as a High-severity finding on Non-Repudiation; a backlog older than 72 hours escalates to Critical.

The dominant failure mode in early PBM deployments — and the one specialists should look for first — is **self-attested justification with no second-party review**. In this anti-pattern the invoker types their own justification, clicks "I acknowledge this is for emergency care," and the system grants elevated PHI access with no human in the loop and no asynchronous review queue feeding a privacy officer. This is a Critical finding because it allows an insider to manufacture lawful-basis cover for arbitrary PHI access — the §164.510(b)(3) defense collapses the moment a regulator asks "who, other than the accessor, attested that this was an emergency," and the record shows only the accessor's own keystrokes. A break-glass mechanism without a real second party is not a break-glass mechanism; it is an audit-launderer.

## Actor-class differentiation

A PBM's consequential-action surface is not uniform — it is partitioned by actor class, and each class touches a different subset of the surfaces above, under different lawful-basis pillars, with different downstream-effect profiles. Non-Repudiation findings should be evaluated per-actor-class, because the same logging gap (e.g., "the member identifier of the access target is not captured") has radically different severity depending on whether the actor is a member viewing their own data or a vendor pushing eligibility files for a roster of 4 million lives. Specialists should map every consequential action they evaluate to the actor classes below and confirm that the audit record captures actor identity, the role held at the time of action, the target (member-id, claim-id, pricing-record-id, configuration-record-id), the inputs that produced the action, and the downstream effect.

- **Member self-service** (member portal, mobile app) — formulary lookup, prior-authorization status check, claim-history pull, address and payment-method update, member-of-record consent revocation, communication-preference change. Audit must capture: member identifier (self), the session credential used, the operation, the record(s) returned, and the disposition (success, denied, partial). Member self-service is the only actor class where the subject of the access and the actor are the same; a missing self-vs-other distinction in the audit record is a finding because it allows operator views of subject data to be masked as legitimate self-service traffic.
- **Pharmacist and prescriber** (NCPDP-D.0 ingress and provider portal) — claim submission, prior-authorization appeal, eligibility query, drug-utilization-review (DUR) override claim, formulary-exception request, refill-too-soon override, COB carrier identification. Audit must capture: NPI of the prescribing/dispensing provider, NCPDP service provider ID for the pharmacy, the patient member-id, the NDC and quantity/days-supply, the adjudication response code, and any DUR conflict codes returned or overridden. The override surface is the high-value audit anchor — every DUR-conflict override is a clinical decision being made over a safety signal.
- **Call center and member services representative** (internal CSR console) — member impersonation for support workflows, prior-authorization status communication, address change executed on the member's behalf, claim-status lookup, PHI export for member-record-request fulfillment, payment-method update on behalf of member, complaint and grievance intake. Audit must capture: CSR identifier, CSR role, the member-id of the impersonated/served party, the operation, the verification step that confirmed the caller's identity (voice-biometric match, knowledge-based verification questions answered, callback to phone-on-record), and any PHI fields exported. PHI exports by this actor class must additionally produce a HIPAA Accounting-of-Disclosures record per 45 CFR §164.528 whenever the disclosure falls outside the routine treatment-payment-operations exception.
- **Adjudication operator** (internal benefit-configuration console) — formulary configuration change (tier assignment, NDC add/remove, step-therapy rule edit), maximum allowable cost (MAC) pricing update, prior-authorization criteria configuration, drug-utilization-review rule edit, manual claim override, retro-active rate adjustment, copay-accumulator configuration. Audit must capture: operator identifier, role, the configuration record changed (with before/after value), the effective-date window, the plan(s) affected, and the change-control ticket reference. The adjudication operator surface is the highest blast-radius surface in the PBM after vendor credentials — a single MAC pricing update can shift millions of dollars across a plan-year.
- **PDE-submission operator** (internal CMS-reporting console) — prescription drug event (PDE) batch initiation, PDE error-record correction, CMS resubmission, retro-claim adjustment with PDE implications, deletion-record generation, late-enrollment-penalty data transmission, quarterly DIR (direct and indirect remuneration) submission. Audit must capture: operator identifier, the PDE batch identifier, the CMS submission identifier, the count and dollar value of records in the batch, the disposition response from CMS, and any error-records resubmitted. PDE submissions are regulator-facing financial records under Part D — every edit to a previously-accepted PDE is a financial-restatement event and must be auditable as such.
- **Plan sponsor administrator** (external partner portal) — formulary tier review, eligibility roster sync acknowledgment, benefit-design change request, copay-structure review, performance-report retrieval, rebate-statement review, network-pharmacy review. Audit must capture: sponsor entity identifier, the administrator's identifier within that entity, the federation credential or portal credential used, the operation, the records or reports retrieved, and any change-requests submitted. Plan sponsor actions are partner-tier — the audit record must support post-hoc reconstruction of which sponsor employee saw which member-population aggregate.
- **Vendor integration credential** (third-party machine-to-machine) — SCIM-style eligibility push from sponsor HRIS, rebate-aggregator file drop, COB carrier data exchange, mail-order pharmacy fulfillment hand-off, specialty-pharmacy hub data sync, clinical-data-exchange (CCD/CCDA) ingress and egress, manufacturer-rebate utilization-data egress. Audit must capture: vendor entity identifier, credential identifier (mTLS certificate fingerprint, API-key identifier, OAuth client_id), the operation, the record-count and field set transferred, the source-or-destination endpoint identifier, and the schema version of the exchange. Vendor PHI exports must additionally produce a HIPAA Accounting-of-Disclosures record per 45 CFR §164.528; specialists should specifically validate that machine-credentialed disclosures are captured in the accounting just as human-credentialed disclosures are — vendor exports are the most common gap in Accounting-of-Disclosures coverage because operators conflate "covered under the BAA" with "exempt from accounting," which the rule does not support.

Specialists evaluating Non-Repudiation should walk every actor class above against the audit-event store and confirm coverage rather than presuming coverage from a single well-instrumented surface. A PBM that logs member-portal traffic perfectly but cannot reconstruct which CSR pulled which member's claim history three weeks ago does not have an audit story — it has an audit hole the size of its largest internal actor class.

## Claims-adjudication lifecycle events

The claim-adjudication path comprises distinct events, each a consequential action with its own audit requirement. The events below are anchored to NCPDP Telecommunication Standard D.0 transaction codes where applicable.

### Inbound claim submission (NCPDP D.0 B1)

The pharmacy submitter transmits a B1 claim-billing request. Audit content: submitter NCPDP pharmacy ID, submitter NPI, transmitting switch (RelayHealth / Change Healthcare / Surescripts), inbound message digest (for replay-detection), member identifier and group_id, claim_reference_number, RX_number, prescriber NPI, and the NCPDP message body retained for the audit-event retention floor (HIPAA §164.316(b)(2)(i) 6-year). <!-- SME-review: confirm whether the audit needs to retain the raw NCPDP message or whether a normalized projection is sufficient under the PBM's pharmacy-network contract terms. -->

### Eligibility lookup (X12 270/271)

The adjudication engine queries the eligibility surface. Audit content: eligibility-query timestamp, member identifier, group_id, plan_id, the 271 response detail (coverage tier, accumulator state, prior-authorization-required flags), and which downstream decisions were keyed off the lookup. <!-- SME-review: confirm the X12 270/271 use here — some PBMs use NCPDP eligibility transactions (E1) rather than X12; the audit content should follow whichever protocol the PBM actually uses. -->

### DUR/COB pre-check

DUR engine evaluates drug-drug, drug-disease, drug-allergy, drug-age, therapeutic-duplication, and refill-too-soon checks; COB engine evaluates primary-vs-secondary insurance and accumulator allocation. Audit content: DUR-rule set version applied, COB tree resolved, the specific alerts raised (or specific reasons no alerts were raised — silence is auditable too), and the pharmacist / operator response if any alert reached the dispensing surface.

### Prior-authorization check

PA-criteria engine evaluates the request against the configured criteria for the drug-and-condition combination. Audit content: PA-criteria version applied, drug NDC and member diagnosis (when available), the criteria-evaluation result (auto-approve, auto-deny, route-to-clinical-review), and any operator override of the auto-decision.

### Formulary and tier resolution

Formulary engine resolves drug-to-formulary-tier, applies step-therapy or quantity-limit rules, evaluates formulary exceptions, and computes the tier-anchored copay basis. Audit content: formulary version applied, tier assigned, exception or override applied (if any), and the tier-anchored copay calculation. <!-- SME-review: formulary-version audit is load-bearing for retroactive-claim-reprocessing disputes; confirm the PBM's formulary-version retention is sufficient to support member appeals filed up to N years post-claim. -->

### Adjudication decision

Adjudication engine emits the response code — paid, rejected with NCPDP reject codes (with reason), captured for audit. The decision is the canonical "consequential action" of the lifecycle; downstream copay-collection, pharmacy-reimbursement, and PDE-submission flows all key off this event.

Audit content: decision code, ingredient cost, dispensing fee, copay calculation, gross amount due, basis-of-reimbursement, prescription origin code, and the full attribution chain (which rule version, which formulary version, which DUR result, which PA result).

### DUR alert raised + operator/pharmacist response

When a DUR alert reaches the dispensing surface, the pharmacist either acknowledges or overrides. Audit content: alert type and severity, the specific clinical issue, the pharmacist NPI overriding, the clinical justification entered (free-text or coded), and whether a supervising-pharmacist attestation was required and recorded.

### Claim reversal (NCPDP D.0 B2)

Pharmacy submits a reversal of a previously-paid claim. Audit content: the original claim_reference_number being reversed, the reversal reason, the reversal timestamp, and the impact on accumulator state. Maps to T1565.001 when the reversal is initiated by an unauthorized actor against an already-paid claim.

### Claim rebill (NCPDP D.0 B3)

Pharmacy submits a rebill of a previously-reversed claim. Audit content: the original claim_reference_number, the rebill's updated fields (typically NDC or quantity), and the linkage between the original, the reversal, and the rebill.

### Mail-order or specialty pathway split

When the formulary or PA criteria route a claim to mail-order or specialty fulfillment, a distinct fulfillment-side audit chain begins. Audit content: which fulfillment partner, the order-routing decision rationale, the shipping address and delivery method, and the partner-side dispensing-event linkage back to the original claim.

## HIPAA patient-rights events (§§164.522–164.528)

The HIPAA Privacy Rule grants individuals specific rights with respect to their PHI. Each exercise of one of these rights is a consequential action with audit and substantive-response requirements.

### Right to request restriction (§164.522)

Member requests restriction on the PBM's use or disclosure of their PHI. Audit content: request, identity verification of the requester, scope of the requested restriction, the PBM's response (granted / partially granted / denied with reasoning), and any downstream propagation of the restriction to vendor partners under §164.504(e) BAA. Note the §164.522(a)(1)(vi) exception: a restriction request related to a service paid for in full by the individual must be granted absent narrow exceptions.

### Right of access (§164.524)

Member requests a copy of their PHI in a designated record set. Audit content: requester identity, identity-verification artifact (especially load-bearing for portal-initiated requests where the verification depth is sometimes weaker than for paper requests), scope of the records requested, the fee charged if any (must conform to §164.524(c)(4) reasonable-cost-based fee), the delivery method (electronic to member, electronic to designated third party, paper), and the response timeline. The 30-day response window (§164.524(b)(2)) is part of the audit-event content because timeliness is itself a §164.524 compliance question.

### Right to amend (§164.526)

Member requests amendment to PHI. Audit content: the amendment request, the PBM's decision (accept / deny with permitted-disagreement-statement), the dissemination of the decision to those who received the unamended record per §164.526(c)(3), and the link between the original PHI item and the amendment.

### Right to an accounting of disclosures (§164.528)

Member requests an accounting of disclosures of their PHI for the preceding 6 years. Audit content: the disclosure-event records covering the 6-year window, the requester identity, the response timeline (60-day default; 30-day extension permissible), and any fee charged for additional accountings within a 12-month window. <!-- SME-review: confirm whether PBM-to-CMS PDE submissions count as "disclosures" required under §164.528 — the Treatment/Payment/Operations exception under §164.506 commonly applies but the determination is fact-specific. -->

### Right to receive PHI via electronic delivery to a designated third party (§164.524(c)(4))

Member directs the PBM to deliver PHI to a designated third party in an electronic format. Audit content: identity verification of the designated third party (a common attack surface), the format requested, the delivery confirmation, and the consent chain authorizing the disclosure.

## Prior-authorization lifecycle

Prior authorization is a distinct PBM workflow with its own audit surface, separate from claim-adjudication.

### PA submission

Prescriber or pharmacist initiates a PA request. Audit content: requesting prescriber NPI, member identifier, drug NDC, requested duration, supporting clinical information attached.

### PA criteria evaluation

PA engine evaluates the request against the configured criteria. Audit content: criteria version applied, evaluation result (auto-approve / auto-deny / route-to-clinical-review with reason), the specific criteria clauses that drove the result.

### Clinical review (when applicable)

Pharmacist or medical director reviews routed requests. Audit content: reviewer NPI / DEA, review timestamp, clinical-justification entered, decision (approve / approve-with-conditions / deny), conditions attached if any.

### PA decision communication

PA decision is communicated to the prescriber and the member. Audit content: decision timestamp, communication channel (fax / electronic / phone), recipient confirmation. Medicare Part D timelines are codified at 42 CFR §423.568 (standard coverage determinations — 72 hours) and §423.572 (expedited coverage determinations — 24 hours), within the broader coverage-determination framework at §423.566.

### Appeals processing

Member appeals a denied PA (Part D redetermination). Audit content: appeal initiation, appeal reviewer (must be different from initial decision-maker per 42 CFR §423.590(g)), appeal decision, appeal timeline tracking per §423.590 (7 calendar days standard, 72 hours expedited). <!-- SME-review: confirm whether the PBM operates as a Medicare-only Part D plan, a commercial-and-Medicare blend, or a primarily-commercial book; the appeals discipline shifts substantially between Medicare-Part-D-enforced timelines and ERISA-governed commercial-plan timelines. -->

### Tier exception decisions

Distinct from PA: member requests a formulary tier exception (drug X covered at lower-cost tier). Audit content: exception-request basis (clinical-necessity argument, comparable-effectiveness argument), reviewer NPI, decision, and the duration of the exception if granted.

## DUR / COB lifecycle

### DUR rule-set authoring

Clinical operator authors or edits a DUR rule. Audit content: rule version, drug-trigger criteria, alert text shown to pharmacist, severity classification, operator NPI, dual-approval attestation (required for safety-class rules; absent = High clinical-harm finding per the severity rubric).

### DUR rule deployment

DUR rule moves from authoring to production. Audit content: deployment timestamp, deployment approver (separate from author), rollback availability, the version range of the rule's effective-date window.

### DUR alert raise / response

(See Claims-adjudication lifecycle — DUR alert raised + operator/pharmacist response above; the lifecycle event is the same.)

### COB tree resolution

Adjudication engine resolves the coordination-of-benefits tree across primary / secondary / tertiary coverage. Audit content: the COB version applied, the resolution path (which insurer was determined primary, secondary, tertiary), the accumulator-state inputs, and the apportionment of payment liability across insurers.

## Domain: pbm — Source: `immutability-classes.md`

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

## Domain: pbm — Source: `data-taxonomy.md`

# PBM PHI/PII data taxonomy

Specialist agents treat the following fields as PHI when they appear in artifacts. The intake brief's PHI/PII inventory MUST enumerate every field; missing fields become evidence gaps.

## PHI identifiers (per 45 CFR §164.514)

- member_id (HICN, MBI, PBM-internal)
- member_dob
- member_address (street, city, ZIP — full ZIP+4 is PHI)
- member_email
- member_phone
- SSN
- account numbers
- biometric identifiers

## PHI clinical data

- drug_ndc (National Drug Code)
- prescriber_npi
- pharmacy_id
- diagnosis codes (ICD-10)
- prior authorization criteria responses
- clinical notes

## PII (non-PHI personally identifying)

- internal user accounts (PBM employee identities)
- plan sponsor contact information

## Financial

- claim payment instructions
- copay calculations
- premium amounts

## Quasi-identifier combinations (Safe Harbor blind spots)

HIPAA Safe Harbor de-identification under 45 CFR §164.514(b)(2)(i) strips the eighteen enumerated identifiers but does NOT account for combinations of residual fields that re-identify in PBM data. The combinations below are recurring re-identification vectors in pharmacy-claims, prior-authorization, and DUR data; their presence in an export pipeline requires Expert Determination per 45 CFR §164.514(b)(1) regardless of whether the export carries a "de-identified" label.

- **(rare_NDC + ZIP3 + age_band)** — for low-prevalence therapeutics (orphan-drug NDCs, specialty oncology regimens, rare-disease biologics, gene therapies), the population dispensed within any 3-digit ZIP and 5-year age band is frequently one individual. Safe Harbor preserves 3-digit ZIP and age in years up to 89; the NDC carries no Safe Harbor restriction, so the combination passes the rule while still uniquely identifying the member.
- **(prescriber_NPI + small-specialty diagnosis + date_band)** — prescriber NPI is not on the Safe Harbor list, and ICD-10 diagnosis categories are not stripped. For narrow-population specialties (gender-affirming hormone therapy, HIV antiretrovirals, certain psychiatric prescriptions, hemophilia factor products), a single prescriber plus diagnosis category plus a coarse dispensing month typically resolves to one member of that prescriber's panel.
- **(plan_sponsor_id + drug_class + month)** — for self-funded plan sponsors under approximately 100 covered lives, the combination of plan sponsor identifier, AHFS or USP drug class, and dispensing month collapses to a single member for any uncommon drug class. Plan sponsor identifiers are not Safe Harbor identifiers, so exports retained for sponsor reporting routinely carry this risk.
- **(pharmacy_NCPDP_id + dispensing_date + drug_class)** — small independent pharmacies and specialty-distribution pharmacies dispense to a handful of patients per day. The NCPDP provider identifier plus exact dispensing date plus drug class produces a candidate set small enough that adversary knowledge of one neighborhood pharmacy and a known dispensing event recovers the member.
- **(member_demographic_band + DUR_alert_type + month)** — Drug Utilization Review alert types (therapeutic duplication, drug-drug interaction at the major-severity tier, high-dose alert for controlled substances) fire sparsely. Combined with demographic banding (age band, sex, 3-digit ZIP) and month, alert-keyed records frequently re-identify, especially for high-severity alerts on uncommon regimens.

When an export pipeline emits two or more of the column sets above together — including derivatives such as masked-but-correlatable surrogates — the Confidentiality specialist must raise a finding requesting Expert Determination per 45 CFR §164.514(b)(1) even when the export is labeled de-identified, and must block on evidence of the statistical-disclosure-risk assessment if none is supplied. This treatment is analogous to the api-security pack's handling of GDPR pseudonymization edge cases where pseudonym plus key combined remain personal data under Recital 26; here, Safe Harbor plus residual quasi-identifiers combined remain a HIPAA disclosure.

## Audit-content sensitivity inheritance

An audit record's sensitivity is the MAX of the sensitivity of (a) the actor identity captured, (b) the action category, and (c) the target referenced. Example: an audit record stating "operator X executed PHI export for member M for purpose Y" inherits PHI-class sensitivity because the target reference (member M, bound to the disclosed dataset) makes the audit record itself a PHI disclosure under the HIPAA Privacy Rule. Consequently the audit store inherits the strongest storage controls of any data class it logs — its encryption-at-rest, encryption-in-transit, key-management, access-control, and retention-floor obligations are the MAX across every contributing class.

Practical implication: audit stores that log PHI-referencing actions cannot be downgraded to an "operational logs" tier and routed through log-shipping infrastructure (SIEM forwarders, log lakes, observability backends) that lacks PHI-class controls — BAA coverage, encryption at rest with managed keys, role-scoped read access, and a retention floor that satisfies §164.530(j)(2)'s six-year minimum. Specialist agents must verify the audit-shipping path and the audit-storage substrate against the controls applied to the most sensitive data class the audit references. When intake evidence shows audit traffic crossing into infrastructure that does not inherit those controls, the Confidentiality, Non-Repudiation, and Immutability lenses must each emit a finding and cross-link via `lens_perspectives` so the synthesizer preserves the joint view rather than collapsing one perspective.

## Consuming APD lenses

This taxonomy is consulted by the following APD specialist lenses; each consumes a defined slice of the taxonomy and is responsible for the controls listed:

- **Confidentiality** — encryption at rest and in transit, field-level masking, deterministic and non-deterministic tokenization, minimum-necessary export gating, and the Expert Determination escalation for the quasi-identifier combinations enumerated above.
- **Integrity** — referential integrity between member, claim, prescriber, and pharmacy records; schema validation on inbound NCPDP D.0 and X12 271/278 messages; write-path authorization on adjudication-affecting fields; and detection of out-of-band mutations on retained claim history.
- **Authenticity** — verification of NCPDP SCRIPT signed-message envelopes for e-prescribing transactions and X12 signed-message verification on inbound enrollment, eligibility, and claims-status traffic, including end-entity certificate trust-chain validation and replay-prevention on signed envelopes.
- **Non-Repudiation** — audit content inheritance per the rule above, signed adjudication-decision records sufficient to bind operator and clinical-reviewer actions to a verifiable identity, and CMS Part D PDE submission attestations.
- **Immutability** — retention floors per data class, including the §164.530(j)(2) six-year minimum on Privacy Rule documentation, CMS Part D PDE retention obligations, and DEA controlled-substance dispensing records under 21 CFR §1304.04.

When a specialist agent cannot determine which data class a given field belongs to from the supplied artifacts, the resulting finding must be marked `disposition: blocked` per apd-evidence-discipline rather than guessed; the intake set must be widened before the finding is downgraded.

## Out of scope

- aggregate analytics with k-anonymity ≥ 5 AND no quasi-identifier combination from the section above present in the export schema
- de-identified per Safe Harbor (45 CFR §164.514(b)(2)) when none of the quasi-identifier combinations above apply; otherwise Expert Determination under §164.514(b)(1) is required
- **Aggregate research-data exports under 45 CFR §164.512(i)** — when a research IRB has approved the use, PHI may be disclosed for research purposes under the §164.512(i) framework (including the optional Waiver of Authorization at §164.512(i)(2)). Out of scope for this taxonomy when the disclosure is governed by an IRB-approved protocol.
- **Limited Data Sets under 45 CFR §164.514(e)** — datasets stripped to the §164.514(e)(2) identifier list and shared under a Data Use Agreement satisfying §164.514(e)(4). Out of scope for the quasi-identifier-combination escalation when the LDS recipient is bound by a §164.514(e)(4)-compliant DUA. Reapplies when the LDS leaves the DUA scope.

## NCPDP D.0 SCRIPT field reference

The NCPDP Telecommunication Standard D.0 is the dominant pharmacy-claim transaction protocol. Each major segment carries fields with distinct sensitivity classifications, masking rules, and retention requirements.

### Transaction header

| Field | Sensitivity | Safe Harbor (§164.514(b)(2)(i)) | Notes |
|---|---|---|---|
| BIN (Bank Identification Number) | Operational | Not an identifier | Identifies the PBM as payer |
| PCN (Processor Control Number) | Operational | Not an identifier | Identifies the PBM's adjudication context |
| Group ID | Operational | Quasi-identifier in combination | Plan-sponsor identifier; combined with NDC and date can re-identify in small groups |
| Cardholder ID | PHI direct identifier | Listed in §164.514(b)(2)(i)(I) (health plan beneficiary number) | Cannot be masked without breaking adjudication |
| Person Code | Quasi-identifier | Combined with Cardholder ID is identifying | Dependent-coverage attribution |

### Claim segment

| Field | Sensitivity | Notes |
|---|---|---|
| Claim Reference Number | Operational | Tokenization breaks PDE submission linkage; do not tokenize |
| RX Number | PHI when combined with member identifier | Cannot be masked for prescriber-attribution audit |
| Days Supply | PHI quasi-identifier | Combined with NDC + member-demo enables re-identification |
| Dispense As Written code | Clinical-decision artifact | Audit-load-bearing; never mask |

### Prescriber segment

| Field | Sensitivity | Notes |
|---|---|---|
| Prescriber NPI | PII (not PHI per §164.514) | Public registry data; never mask |
| DEA Number | Operational + regulated | DEA records subject to 21 CFR §1304.04; state pharmacy-board reporting may extend |
| State License | Public registry data | State-by-state |

### Patient segment

| Field | Sensitivity | Safe Harbor treatment | Notes |
|---|---|---|---|
| First / Last Name | PHI direct identifier | §164.514(b)(2)(i)(A) | Required for adjudication; mask in analytics surfaces |
| Date of Birth | PHI direct identifier | §164.514(b)(2)(i)(C) | Required for DUR age-based rules; year-only safe |
| Gender | Quasi-identifier | Not in §164.514(b)(2)(i) | Combined with rare diagnosis re-identifies |
| Address Fields | PHI direct identifier | §164.514(b)(2)(i)(B) | ZIP3 may be retained per §164.514(b)(2)(i)(B) exception |
| Patient ID Qualifier | Operational | Not an identifier | Specifies the type of patient ID supplied |

### Pharmacy segment

| Field | Sensitivity | Notes |
|---|---|---|
| Pharmacy NCPDP ID | Operational | Network-attribution data |
| Pharmacy NPI | Public registry data | Never mask |
| Pharmacy Address | Operational + quasi-identifier | Small-pharmacy + dispensing date enables re-identification |

### DUR/PPS segment

DUR/PPS fields carry both clinical-decision artifacts and PHI quasi-identifiers. Reason-for-Service, Professional-Service Code, and Result-of-Service must be retained in the audit chain to defend the clinical-decision pathway. None can be masked in the audit retention.

### Pricing segment

Pricing fields (Ingredient Cost, Dispensing Fee, Copay Amount, Gross Amount Due, Basis of Reimbursement) are commercial-confidentiality data. Encryption-at-rest tier-2 with PBM-internal access scoping; export to plan-sponsor surfaces requires contract-defined data-scope enforcement. <!-- SME-review: PBM-pricing-transparency state laws affect which pricing fields can be exposed to which audiences; the per-state matrix is implementation-specific. -->

## X12 transaction reference

The PBM commonly participates in HIPAA-mandated X12 transactions for plan-sponsor and Medicare workflows. Each transaction has distinct PHI-bearing segments and audit requirements.

### 270/271 — Eligibility inquiry/response

The 270 carries patient demographic + member identifier + subscriber relationship; the 271 response carries coverage tier, accumulator state, and benefit detail. Both are PHI under HIPAA. Audit retention floor: HIPAA §164.316(b)(2)(i) 6-year floor; plan-sponsor MSA may extend.

### 837 — Healthcare Claim

The 837 (institutional and professional variants) carries facility-side claims that may be submitted for institutional pharmacy claims and mail-order facility claims. Encryption-in-transit (TLS) and at-rest required; audit retention floor per HIPAA §164.316(b)(2)(i).

### 835 — Healthcare Claim Payment

The 835 carries payment + adjustment reason codes. Payment data is commercial-confidentiality; member identifiers in the 835 are PHI. Audit retention as above.

### 999 — Implementation Acknowledgment

Transaction-level acknowledgment. Operational; minimal PHI exposure. Audit retention follows the parent transaction.

### 277 — Healthcare Claim Status

Claim-status responses to plan-sponsor inquiries. PHI under HIPAA. Audit retention as above.

<!-- SME-review: confirm which X12 transactions the PBM actually originates or terminates versus which it merely passes through; the audit chain depth differs between origination and pass-through. -->

## CMS Part D PDE submission field reference

The CMS Part D Prescription Drug Event submission carries pharmacy-claim data to CMS for payment-determination and risk-adjustment. Field-level handling is anchored to 42 CFR §423.322 and the CMS Plan Communications User Guide (PCUG).

| Field group | Examples | Sensitivity | Notes |
|---|---|---|---|
| Plan attribution | Contract ID, PBP ID | Commercial-confidentiality + CMS-operational | Pinned per CMS Plan Communications User Guide |
| Beneficiary identifier | HICN (legacy) or MBI (Medicare Beneficiary Identifier) | PHI direct identifier | MBI replaced HICN per 42 CFR §423.120 / MACRA mandate |
| Prescription service reference | Prescription Service Reference Number | Operational + PHI when combined | Links to NCPDP claim |
| Date of service | Service date | PHI quasi-identifier (with NDC) | Required for retroactive-claim-reprocessing |
| Drug identifier | NDC | Operational + clinical | Combined with rare-disease NDC + ZIP3 + age band re-identifies |
| Quantity / days supply | Quantity Dispensed, Days Supply | PHI quasi-identifier | Audit-load-bearing for DUR defensibility |
| Brand/generic | Brand-Generic indicator, DAW code | Clinical-decision artifact | Audit-load-bearing |
| Service provider | Service Provider ID (NPI) | Public registry data | Never mask |
| Prescriber | Prescriber ID (NPI) | Public registry data | Never mask |
| Pricing fields | Ingredient Cost, Dispensing Fee, Sales Tax, Gross Drug Cost Below Catastrophic, Gross Drug Cost Above Catastrophic, Patient Liability, Plan-Sponsored Amount, Low-Income Subsidy, Total Amount Paid | CMS-confidential commercial | CMS Data Use Agreement governs |
| Adjustment | Adjustment indicator | Operational | Tracks corrections and resubmissions |
| Prescription origin | Prescription Origin Code | Clinical metadata | Required for audit |

Sensitivity treatment: PDE records contain both PHI (MBI is a PHI element) AND CMS-confidential pricing. They cannot be exported to non-HIPAA-covered analytics surfaces without de-identification AND CMS Data Use Agreement compliance. <!-- SME-review: confirm the current MBI implementation status — the legacy HICN identifier has been phased out per MACRA, but field-name retention in legacy ETL may persist. -->

## Per-field masking and tokenization decision tree

For each major field class, the decision of whether to mask, tokenize, redact, or pass-through depends on the downstream consumer and the audit-defensibility requirement.

### Member-identifier handling

- **Token member_id for analytics surface**: preserve referential integrity within a single analytics tenant only; the token must NOT be reusable across analytics tenants (would enable cross-tenant linkage attack on de-identification).
- **Cannot tokenize for adjudication path**: the live adjudication engine, the PA engine, the DUR engine, and the PDE submission pipeline all need the raw member identifier; tokenization breaks adjudication.
- **Cannot tokenize for HIPAA Right of Access**: the §164.524 request flow needs to resolve the raw member identifier to produce the designated record set.

### Date-of-birth handling

- **Mask DOB to year-only for population-level analysis**: per §164.514(b)(2)(i)(C) exception, year is permissible while month/day are direct identifiers.
- **Cannot mask for DUR age-based rules**: pediatric and geriatric dosing rules need the full DOB.
- **Cannot mask for PA criteria with age gates**: PA criteria referencing pediatric or geriatric thresholds need the full DOB.

### Address handling

- **Retain ZIP3** per §164.514(b)(2)(i)(B) exception when retaining the population covered by that ZIP3 is greater than 20,000 individuals.
- **Mask street address** for analytics; cannot mask for member-fulfillment delivery.

### Prescriber identifier handling

- **Never mask DEA number**: state pharmacy-board reporting requires full DEA, and DEA records have separate retention obligations under 21 CFR §1304.04.
- **Never mask NPI**: public-registry data.

### Quasi-identifier combination suppression

- When two or more of the quasi-identifier combinations enumerated in the Quasi-identifier combinations section above appear in the same export, the Confidentiality specialist raises a finding asking for §164.514(b)(1) Expert Determination before export proceeds. <!-- SME-review: the Expert Determination workflow varies by PBM — some operate an internal qualified statistician, others contract out. The data-taxonomy guidance should reflect the PBM's actual process. -->

### Claim-reference and RX-number handling

- **Never tokenize claim reference number**: PDE submission and pharmacy-network audit both need the raw claim_reference_number.
- **Never mask RX number**: prescriber-attribution audit and pharmacy-attribution audit both need the raw RX number.

### Pricing-field handling

- **Pass-through for plan-sponsor reporting** within the contract-defined scope.
- **Encrypt-at-rest tier-2** for PBM-internal pricing data; CMS PDE pricing is tier-1 under the CMS DUA.
- **Mask for non-contractual analytics** export — the rebate-aggregator surface, the COB-carrier surface, and analytics tenants outside the plan-sponsor scope cannot see ingredient cost, MAC (Maximum Allowable Cost), or dispensing fee.

## Domain: pbm — Source: `common-patterns/confidentiality.md`

# PBM common patterns — Confidentiality

These are illustrative templates, not all-inclusive. Use them to calibrate analytical style, severity assignment per the PBM rubric, and NIST/ATT&CK mapping habits. The specialist agent's analytical checklist still drives the actual analysis — this file calibrates how findings and capabilities should look once written.

Confidentiality failure in a PBM is the dominant regulatory-enforcement vector: any PHI disclosure affecting 500 or more members triggers HHS, media, and individual notification under 45 CFR §164.408, and the OCR Resolution Agreement floor for PBM-scale breaches is in the seven figures before plan-sponsor indemnity claims arrive. Beyond PHI, CMS Part D PDE data carries its own confidentiality envelope under the Part D Data Use Agreement, and rebate-tier and MAC pricing are commercially-confidential under most manufacturer and plan-sponsor master service agreements. The load-bearing surfaces are PHI-store reads (claim history, eligibility, PA decisions), member-portal export and EOB-download paths, and every vendor-egress channel — COB, accumulator, rebate aggregator, mail-order fulfillment, and specialty pharmacy.

## ATT&CK + D3FEND defensive mapping

This goal defends against (or is exploited by) the following MITRE ATT&CK techniques. Each citation is included only where the apd-control-mappings high-confidence-bar discipline is met; we deliberately omit techniques that only adjacently relate to this goal.

**ATT&CK techniques:**

- **T1213** (Data from Information Repositories) — bulk PHI repository reads against claim history, member records, PA decisions, formulary data
- **T1530** (Data from Cloud Storage) — backup-store and object-store reads against snapshot archives, PDE batch archives, audit-log archives
- **T1567** (Exfiltration Over Web Service) — PHI export over outbound HTTPS to attacker-controlled endpoints, including legitimate-looking SaaS targets
- **T1041** (Exfiltration Over C2 Channel) — PHI exfiltration via an established C2 channel after initial compromise
- **T1078** (Valid Accounts) — credential-driven PHI access using legitimate but misused authentication material

**D3FEND counters:**

- **D3-MFA** (Multi-factor Authentication) — counters T1078 by requiring additional factor beyond compromised credential
- **D3-OTF** (Outbound Traffic Filtering) — counters T1567 and T1041 by gating outbound flows from the PHI tier
- **D3-NTA** (Network Traffic Analysis) — counters T1041 and T1567 by detecting anomalous outbound volume or destinations
- **D3-LFAM** (Local File Access Mediation) — counters T1213 by enforcing read-mediation at the data tier

## Common finding patterns

**Pattern: Broker-level encryption only on PHI event stream.**

- Severity: typically high (PHI exposure beyond minimum-necessary; broker compromise yields plaintext)
- NIST: SC-8(1), SC-13, SC-28(1)
- ATT&CK: T1530 (Data from Cloud Storage) with specific rationale

**Pattern: Single KEK protecting heterogeneous data classes.**

- Severity: typically medium (defense-in-depth gap; key compromise broader than necessary)
- NIST: SC-12, SC-12(1)
- Related concerns: ephemeral (rotation cadence amplification)

**Pattern: PHI displayed unmasked by default in admin UI.**

- Severity: high (critical when the admin role can affect >500 members or >1 plan sponsor per the severity rubric Critical clause)
- NIST: AC-3, AC-6, SC-28
- Related concerns: non_repudiation (unmask audit), authenticity (admin identity assurance)

**Pattern: Service-to-service inside cluster relies on network-level trust, payloads contain PHI.**

- Severity: high (PHI exposure beyond minimum-necessary via lateral movement)
- NIST: SC-8(1), SC-23, IA-3
- ATT&CK: T1557 with specific rationale on in-cluster observer

**Pattern: Tech plan describes encryption-in-transit generically without specifying TLS version or cipher suite policy.**

- Disposition: blocked when no artifact establishes the masking discipline; uncertainty when one artifact references it but the implementation discipline is not enumerated
- Severity: typically medium when blocked, deferred when uncertainty
- prerequisite_evidence: "TLS configuration policy — (1) minimum TLS version per ingress (pharmacy NCPDP, member portal, admin console, vendor egress, CMS outbound); (2) cipher-suite allowlist per ingress; (3) certificate-pinning configuration for pharmacy-network ingress and outbound CMS submission; (4) HSTS enforcement on member-facing surfaces; (5) certificate rotation cadence and CA-trust policy; (6) certificate-revocation handling (OCSP stapling, CRL refresh interval); (7) configuration source-of-truth pointer (Terraform module, NGINX config, ALB listener) and CD pipeline applying it"

## Common capability patterns

**Pattern: Field-level envelope encryption on PHI columns.** Maturity ladder depends on evidence — `designed` for tech plan only; `implemented` requires a config or IaC reference; `tested` requires a test report; `operationalized` requires runbook plus monitoring.

**Pattern: KMS hierarchy with separated DEK/KEK roles.** Capability scope: "Confirmed for [data stores X, Y]. Not addressed: [data store Z, audit log, backups]." Caveats expected.

**Pattern: mTLS across service mesh.** Maturity higher when evidence includes service mesh configuration; `designed` when tech plan asserts intent.

## prerequisite_evidence

When a confidentiality finding is dispositioned `blocked-on-evidence`, the prerequisite_evidence ask must name every sub-element the operator needs to produce to unblock — not a single noun phrase. The seeds below calibrate the depth expected of asks emitted by the Confidentiality specialist. The TLS configuration ask above is the in-line example on the generic-encryption-in-transit pattern; the KMS and field-level seeds below cover the next two most common blocked dispositions.

**KMS hierarchy:** (1) root key location (HSM-backed CMK, customer-managed key, vendor-managed key); (2) KEK (key-encrypting key) hierarchy diagram; (3) DEK (data-encrypting key) rotation cadence per data class; (4) KEK-to-data-class mapping (PHI store, PDE archive, backup store, audit store); (5) key access-control policy (who can use, who can rotate, who can disable); (6) key-material backup and escrow policy.

**Field-level encryption:** (1) per-PHI-field encryption status at rest, in transit, in use; (2) tokenization map for fields not directly encrypted; (3) field-decryption authorization-decision pipeline (who can decrypt, under what authorization); (4) decryption-event audit chain feeding the Non-Repudiation surface.

## Domain: pbm — Source: `common-patterns/integrity.md`

# PBM common patterns — Integrity

These are illustrative templates, not all-inclusive. Use them to calibrate analytical style, severity assignment per the PBM rubric, and NIST/ATT&CK mapping habits. The specialist agent's analytical checklist still drives the actual analysis — this file calibrates how findings and capabilities should look once written.

Integrity in a PBM is the bridge between data and physical dispensing: a corrupted claim-adjudication response can authorize the wrong drug, the wrong quantity, or the wrong copay at the pharmacy counter, and PDE-submission integrity under 42 CFR §423.322 is what CMS audits against for Part D reconciliation, rebate true-up, and risk-adjustment payment accuracy. Formulary configuration is similarly load-bearing — a silent tier or PA-criteria mutation propagates as a clinical-decision defect across the entire dispensing network within the next refresh cycle. The most consequential surfaces are NCPDP D.0 and SCRIPT transaction handlers (request and response), PDE batch files and their reconciliation deltas, and the formulary editor with its publish-and-fanout pipeline.

## ATT&CK + D3FEND defensive mapping

This goal defends against (or is exploited by) the following MITRE ATT&CK techniques. Each citation is included only where the apd-control-mappings high-confidence-bar discipline is met; we deliberately omit techniques that only adjacently relate to this goal.

**ATT&CK techniques:**

- **T1565.001** (Stored Data Manipulation) — at-rest tampering of formulary, PA-criteria, DUR-rule, MAC-pricing, or claim history stores
- **T1565.002** (Transmitted Data Manipulation) — in-flight tampering of NCPDP D.0 messages, X12 transactions, or PDE batch files
- **T1556** (Modify Authentication Process) — bypassing write-path authorization by altering the auth decision that gates formulary, PA, or claim mutations

**D3FEND counters:**

- **D3-MAN** (Message Authentication) — counters T1565.002 on NCPDP / X12 / PDE signed messages via per-message signature verification
- **D3-FIM** (File Integrity Monitoring) — counters T1565.001 by monitoring at-rest formulary, PA-criteria, MAC-pricing, and PDE-batch files for unauthorized modification before consumption by adjudication or fanout

## Common finding patterns

**Pattern: Event bus messages lack producer signatures; consumers trust payload contents.**

- Severity: high if PHI or adjudication input is involved; medium otherwise
- NIST: SI-7, SI-7(1), SC-8(1), SC-16
- Related concerns: authenticity (producer identity)

**Pattern: Idempotency claimed at API but key derivation is request-body hash.**

- Severity: medium (high when the affected dedup path is PDE submission, NCPDP B2 reversal, or formulary fanout — clinical-decision adjudication scope)
- NIST: SI-10, SI-7
- Detail must call out the specific risk: client retry under transient network failure produces double-adjudication if the body changed between attempts.

**Pattern: NCPDP D.0 transactions accepted without field-level validation beyond standard syntax.**

- Severity: medium (downstream errors, possible adjudication errors)
- NIST: SI-10
- Related concerns: availability (malformed input causing cascading failure)

**Pattern: Formulary configuration is application-managed with no integrity check.**

- Severity: critical to high (corruption affects therapeutic decisions)
- NIST: SI-7(7), CM-3, CM-5
- Related concerns: immutability (historical configuration drift), non_repudiation (who changed configuration)

**Pattern: Tech plan describes "data validation" generically without specifying which fields, what rules, or what error handling.**

- Disposition: blocked or uncertainty
- prerequisite_evidence: "Validation rule specification covering (1) the field-level rules for each cross-boundary message (NCPDP D.0 segments, X12 270/271/837/835 transactions, internal RPC contracts); (2) the enforcement point where validation runs (gateway, service edge, data tier); (3) the failure-handling behavior on rule violation (reject, quarantine, log-and-pass); (4) the dead-letter policy including retention, replay, and alerting; and (5) the schema-version negotiation policy across PBM, switch operator, and CMS"

## Common capability patterns

**Pattern: Typed schema (Protobuf or GraphQL) enforced at every service boundary.** Capability scope must enumerate which boundaries are confirmed.

**Pattern: Idempotent claim adjudication keyed by claim ID and submission sequence.** Maturity tied to whether the idempotency window and key retention are specified.

**Pattern: HMAC-signed event payloads on the claim event bus.** Capability scope must specify which topics are confirmed; caveats for any topics not in evidence.

**Pattern: Configuration-as-code for plan rules with reviewed PRs gating changes.** Often `designed` from tech plan; `implemented` or higher requires repository or pipeline evidence.

## prerequisite_evidence

When a tech plan or design document leaves an integrity concern under-specified, the specialist agent should emit a blocked-on-evidence finding whose `prerequisite_evidence` asks for the full multi-clause specification — not a single-line generic ask. The seeds below calibrate the expected depth.

**Schema enforcement:** (1) the canonical schema for each cross-boundary message (NCPDP D.0 segments, X12 270/271/837/835 transactions, internal RPC contracts); (2) the schema-validation enforcement point (gateway, service edge, data tier) for each message class; (3) the schema-validation failure-handling behavior on violation (reject, quarantine, log-and-pass) and the corresponding alerting; and (4) the schema-version negotiation policy across PBM, switch operator, and CMS so version drift cannot silently degrade validation.

**Write-path authorization:** (1) the authorization-decision pipeline for each PHI-writing endpoint (formulary publish, PA-criteria mutation, claim-history backfill, eligibility override); (2) the actor identity and role evaluation at each step in the pipeline; (3) the audit event emitted on grant and on deny, with the fields that allow non-repudiation reconstruction; and (4) the failure mode when the authorization service is unavailable — fail-closed is required for PHI write paths and any fail-open posture must be explicitly justified.

**Tamper detection:** (1) the HMAC or signed-payload protection applied to cross-boundary state-changing messages, including the key-management posture for the signing key; (2) the content-hash verification performed on PDE submission batches and the storage location of the expected hash; and (3) the integrity-check failure handling and the corresponding incident-response playbook, including who is paged, what is quarantined, and how downstream adjudication is held until the failure is resolved.

## Domain: pbm — Source: `common-patterns/availability.md`

# PBM common patterns — Availability

These are illustrative templates, not all-inclusive. Use them to calibrate analytical style, severity assignment per the PBM rubric, and NIST/ATT&CK mapping habits. The specialist agent's analytical checklist still drives the actual analysis — this file calibrates how findings and capabilities should look once written.

Availability failure in a PBM is felt at the pharmacy counter in real time: claim adjudication is a synchronous transaction with a typical 3-to-5-second budget, and an outage converts directly to dispensing delays, member out-of-pocket exposure when pharmacies fall back to cash-pay, and SLA-penalty exposure under plan-sponsor agreements that commonly stipulate four- or five-nines on the adjudication path. CMS Part D operational standards under 42 CFR §423.505 also tie availability to plan-sponsor downstream-entity oversight, so prolonged outages can escalate into Star Ratings and CMS audit posture, not just contractual penalties. The load-bearing surfaces are pharmacy ingress (NCPDP switch and direct-submit), real-time eligibility and accumulator lookup, and the prior-authorization decision engine — each of which sits on a synchronous dispensing decision.

## ATT&CK + D3FEND defensive mapping

This goal defends against (or is exploited by) the following MITRE ATT&CK techniques. Each citation is included only where the apd-control-mappings high-confidence-bar discipline is met; we deliberately omit techniques that only adjacently relate to this goal.

**ATT&CK techniques:**

- **T1499** (Endpoint Denial of Service) — request-volume attacks against pharmacy ingress, member portal, or PA workflow endpoints
- **T1498** (Network Denial of Service) — network-layer attacks against the PBM's public surface area
- **T1485** (Data Destruction) — destruction of formulary, PA-criteria, or adjudication-state data to disrupt claims processing — no clean D3FEND counter is mapped for data-destruction recovery; rely on backup-immutability (see common-patterns/immutability.md) and the AU-9 NIST 800-53r5 anchor in the severity rubric.

**D3FEND counters:**

- **D3-NTA** (Network Traffic Analysis) — counters T1498 by detecting volumetric anomalies
- **D3-RAPA** (Resource Access Pattern Analysis) — counters T1499 by detecting application-level abuse patterns

## Common finding patterns

**Pattern: Adjudication latency target not stated, but contractual SLA exists.**

- Severity: high (cannot verify the system meets contractual obligation)
- NIST: CP-2, CP-2(3)
- Detail must enumerate the contracts the SLA appears in, per intake brief.

**Pattern: DR RTO stated as 4 hours but no tested failover procedure documented.**

- Severity: high (RTO is aspirational without test evidence)
- NIST: CP-2, CP-4 (contingency plan testing), CP-7

**Pattern: Single-region deployment with 99.95% availability target.**

- Severity: high (target likely undeliverable from single region)
- NIST: CP-7, SC-36
- Related concerns: distributed (this finding's recommendation will point to a topology change owned by Distributed)

**Pattern: Vendor dependency (e.g. eligibility lookup) has no stated SLA in artifacts.**

- Disposition: blocked or uncertainty
- prerequisite_evidence: "Vendor SLA for [vendor name] eligibility service — (1) availability target (e.g. 99.95%) with measurement window and exclusion list; (2) per-transaction latency budget at p50 / p95 / p99; (3) error-rate ceiling and what counts as an error vs. a degraded-mode response; (4) credit / remedy schedule when targets are missed; (5) maintenance-window policy and notification SLA; (6) incident-communication SLA (time-to-first-notification, status-page commitment); (7) right-to-audit clause and last vendor SOC 2 / HITRUST attestation date; (8) the PBM-side fallback or degraded-mode plan when the vendor breaches the SLA, including the dispensing-decision policy at the pharmacy counter."

**Pattern: Health checks specified as TCP port checks only.**

- Severity: medium (shallow health checks mask real degradation)
- NIST: SI-13, CP-10

## Common capability patterns

**Pattern: Multi-AZ deployment of the adjudication engine with cross-AZ failover.** Scope must specify which components are multi-AZ; caveats for any that are not.

**Pattern: Backup encryption with daily verification.** Maturity ladder: `designed` from tech plan, `implemented` requires backup configuration, `operationalized` requires backup test runbook and last-test date.

**Pattern: SLO and error budget framework for the claim adjudication path.** Often `designed` from tech plan; higher maturity requires monitoring dashboard evidence.

## prerequisite_evidence

When an availability concern cannot be resolved from the artifacts in evidence, the specialist agent should mark the finding as blocked rather than speculating, and emit a prerequisite_evidence ask. The asks below are seeds — each one names every sub-element an operator must provide to unblock the finding. Use them verbatim or adapt them to the specific surface area in question, but preserve the multi-clause depth.

**SLO/SLI definition:** (1) each SLO defined for pharmacy ingress, member portal, PA workflow, PDE submission, and eligibility lookup, with the SLI that operationalizes it (request-success ratio, latency-at-percentile, freshness) and the measurement window; (2) error-budget definition per SLO, including how it is computed and over what rolling window; (3) burn-rate alerting thresholds at both fast-burn and slow-burn windows, and the on-call routing for each; (4) escalation chain when an SLO is at risk, including the decision authority for invoking degraded-mode policy at the pharmacy counter; (5) plan-sponsor contractual SLA mapping — which SLO maps to which contractual obligation, the gap between the internal SLO and the external SLA, and the credit-exposure model when the SLA is breached.

**Failure-domain analysis:** (1) failure-domain diagram showing which services share which fate (which workloads share a control plane, a database primary, a regional egress, a single vendor dependency, or a single identity provider); (2) blast-radius analysis per AZ, region, and zonal service (managed databases, managed Kafka, managed cache, managed object store), naming which user-facing workflows degrade and which fail closed; (3) DR plan with RTO and RPO stated per data class — PHI store, PDE pipeline, audit / non-repudiation store, formulary and PA-criteria store — and the last DR-test date for each, including a tabletop or live-failover artifact.

**Capacity headroom:** (1) headroom posture per critical path (pharmacy ingress, adjudication engine, eligibility lookup, PA decision engine), expressed as the ratio of provisioned capacity to observed peak and the alert threshold for utilization; (2) load-test artifacts that demonstrate the headroom at expected peak load — open-enrollment cutover (Jan 1), flu-season surge, and a mass-vaccination drive — including test methodology, scenario mix, and observed degradation points; (3) auto-scaling configuration with scaling-event audit, including the scale-up and scale-down policy, the cooldown window, the upper bound (so a surge cannot exhaust a regional quota), and the last 30 days of scaling-event logs showing the configuration behaves as expected under real traffic.

## Domain: pbm — Source: `common-patterns/distributed.md`

# PBM common patterns — Distributed

These are illustrative templates, not all-inclusive. Use them to calibrate analytical style, severity assignment per the PBM rubric, and NIST/ATT&CK mapping habits. The specialist agent's analytical checklist still drives the actual analysis — this file calibrates how findings and capabilities should look once written.

Distribution in a PBM is not an optimization — it is a contractual SLO and a clinical-safety property. Regional adjudication failures cascade directly to dispensing in the affected pharmacy network, and most plan-sponsor master service agreements require multi-AZ resilience at minimum and multi-region failover for the adjudication path, with CMS Part D §423.505(b) downstream-entity expectations layered on top. The load-bearing surfaces are the claim-router fan-out (pharmacy ingress to adjudication-engine instances), the PDE-submission pipeline (where partition or batch-loss silently breaks CMS reconciliation), and the formulary-update fanout that must reach every adjudication shard before the published effective date.

## ATT&CK + D3FEND defensive mapping

This goal defends against (or is exploited by) the following MITRE ATT&CK techniques. Each citation is included only where the apd-control-mappings high-confidence-bar discipline is met; we deliberately omit techniques that only adjacently relate to this goal.

**ATT&CK techniques:**

- **T1485** (Data Destruction) — destruction of a regional adjudication-state store, audit substrate, or formulary replica
- **T1565.001** (Stored Data Manipulation) — at-rest tampering of cross-region replicated data, including divergent replica states
- **T1078** (Valid Accounts) — lateral movement across regional zones via legitimate cross-region credentials

**D3FEND counters:**

- **D3-NTA** (Network Traffic Analysis) — counters cross-region anomalies (T1078 lateral movement) by detecting baseline-divergent traffic
- **D3-LFAM** (Local File Access Mediation) — counters T1485 / T1565.001 by enforcing tenant-and-region scoping at the data tier

## Common finding patterns

**Pattern: Stateful component (e.g. Valkey, RDS primary) in single AZ.**

- Severity: high (PBM SLA contracts typically require AZ resilience)
- NIST: SC-7, CP-7, SC-36
- Cross-reference: any Availability finding on SLO consistency

**Pattern: Hidden SPOF in CI/CD — emergency deployment depends on single pipeline.**

- Severity: medium (high when the RTO commitment in the plan-sponsor MSA is ≤4 hours or covers PDE submission)
- NIST: CM-2(2), CP-2
- Related concerns: ephemeral (immutable infra readiness for redeployment)

**Pattern: Tech plan claims multi-region but artifacts don't specify topology — active-active versus active-passive versus standby.**

- Disposition: uncertainty or blocked
- prerequisite_evidence: "Multi-region topology specification — (1) region topology (active-active, active-passive, follow-the-sun) per service; (2) cross-region data-replication strategy and lag SLO; (3) consistency model per data class (strong, eventual, bounded staleness); (4) failover plan including replication-lag tolerance at failover, write conflict policy, and failover trigger"

**Pattern: Cross-region replication for audit logs is asynchronous with unspecified lag.**

- Severity: medium (escalates to high when the missing audit attribution falls under HIPAA §164.312(b) audit-controls)
- NIST: AU-9(2), SC-36
- Related concerns: non_repudiation, immutability

**Pattern: Adjudication CAP positioning unstated.**

- Disposition: uncertainty
- Detail: in pharmacy adjudication, the CAP choice has clinical consequences (continuing to adjudicate with stale formulary versus stopping adjudication). The artifacts must state the choice.

## Common capability patterns

**Pattern: Multi-AZ active-active adjudication engine with automated AZ failover.** Scope must specify which dependencies are also multi-AZ (database, cache, broker) and which are not.

**Pattern: Read replica topology across AZ with bounded replication lag.** Capability requires specifying the replication-lag bound and what enforces it.

**Pattern: Stateless application tier with all state externalized.** Maturity ladder typically `designed` from tech plan; `implemented` requires service configuration or IaC evidence.

## prerequisite_evidence

When a finding in this lens is dispositioned blocked or uncertainty for missing distribution evidence, the operator unblock-pack should provide multi-clause specifications, not single-line attestations.

**Failure-domain isolation:** (1) blast-radius diagram for a single-region failure of each critical service (adjudication, PHI store, PA engine, eligibility); (2) tenant-and-region isolation guarantees if the PBM is multi-tenant; (3) the load-shedding plan when a regional dependency degrades.

**Cross-region replication and CAP-positioning evidence:** (1) per-data-class replication topology (sync vs async) and lag SLO for PHI store, adjudication-state, audit substrate, formulary cache, PDE staging; (2) consistency model declared per critical operation (strong consistency on claim adjudication and PA decisions; eventual on analytics replicas; bounded staleness on member-portal reads); (3) the explicit CAP-positioning choice when a network partition severs cross-region replication — which operations continue (read-only adjudication against cached formulary, eligibility cache, accumulator deferral) and which fail-closed (PDE submission, PA-criteria configuration changes); (4) the recovery-validation procedure when partition heals (replication-divergence detection, conflict resolution, audit chain reconciliation).

## Domain: pbm — Source: `common-patterns/resilient.md`

# PBM common patterns — Resilient

These are illustrative templates, not all-inclusive. Use them to calibrate analytical style, severity assignment per the PBM rubric, and NIST/ATT&CK mapping habits. The specialist agent's analytical checklist still drives the actual analysis — this file calibrates how findings and capabilities should look once written.

Resilience in a PBM is sized around predictable demand spikes that hit the pharmacy ingress path: seasonal flu and vaccination surges, COVID and respiratory-virus waves, and the structural Jan-1 / Oct-15 open-enrollment transitions when tens of millions of members move between plans and refill their entire chronic regimen in the first weeks of new coverage. Brittle behavior at the ingress queue, the eligibility cache, or the PA workflow engine under these spikes converts directly to denied or delayed dispensing and to SLA penalties under plan-sponsor agreements aligned with 42 CFR §423.505. The load-bearing surfaces are the pharmacy-submission queue and its backpressure semantics, the eligibility-and-accumulator cache layer (cold-cache behavior on Jan-1 is the canonical failure mode), and the PA workflow engine where retry storms on vendor degradation are the dominant outage shape.

## ATT&CK + D3FEND defensive mapping

This goal defends against (or is exploited by) the following MITRE ATT&CK techniques. Each citation is included only where the apd-control-mappings high-confidence-bar discipline is met; we deliberately omit techniques that only adjacently relate to this goal.

**ATT&CK techniques:**

- **T1499** (Endpoint Denial of Service) — backpressure exploitation against pharmacy ingress or PA workflow, where a flood of submission or status-poll requests forces the resilience surface (queue, cache, breaker) into its failure mode
- **T1499.003** (Application Exhaustion Flood) — adjudication-thread or PA-worker exhaustion via legitimate-shape requests (eligibility lookups, claim submits) that bypass network-layer rate limits and consume application capacity
- **T1496** (Resource Hijacking) — capacity drain via legitimate-looking traffic from a compromised pharmacy account or partner integration, where the abusive workload is indistinguishable from peak-season load at the network layer

**D3FEND counters:**

- **D3-RAPA** (Resource Access Pattern Analysis) — counters T1496 / T1499 / T1499.003 by detecting abusive request patterns at the application layer (per-pharmacy submission rates, per-member status-poll cadence) that backpressure and circuit-breaker controls then act on
- **D3-NTA** (Network Traffic Analysis) — counters T1499 at the ingress edge by characterizing the shape of submission and PA-status traffic and feeding rate-limit and shed-load decisions upstream of the application tier

## Common finding patterns

**Pattern: No circuit breaker on PHI-containing vendor call (eligibility, drug pricing).**

- Severity: high (vendor degradation can cascade to total adjudication outage)
- NIST: SI-13, SC-5, CP-13
- Cross-reference: any Availability finding on vendor SLA

**Pattern: Retry policy without jitter on the event bus consumer.**

- Severity: medium (thundering herd risk on partial broker failure)
- NIST: SI-13(4), SC-5(1)

**Pattern: Timeout missing on database call in adjudication path.**

- Severity: high (single slow query can hang adjudication threads, cascading to thread pool exhaustion)
- NIST: SI-13, SC-5

**Pattern: No graceful degradation specified for eligibility vendor outage.**

- Severity: high (vendor outage produces total adjudication outage)
- NIST: CP-12, CP-13, SI-17
- Detail must specify what would happen today (system errors) and what should happen (cached eligibility, fail-open with downstream verification, or explicit soft-deny with patient communication).

**Pattern: Tech plan describes "retries" without specifying backoff, jitter, or budget.**

- Disposition: uncertainty
- prerequisite_evidence: "Retry-policy specification covering: (1) the retry policy per service-to-service edge (which caller, which callee, which request class); (2) the retry budget per request class (max attempts, max total elapsed, max concurrent in-flight retries); (3) the backoff strategy (fixed, exponential, jittered) and the jitter distribution; (4) idempotency-key handling for retry-safe operations (eligibility re-check, PA-status poll, claim resubmit) and the safe-to-retry classification per operation; (5) the interaction with circuit-breaker state — whether retries are suppressed when the breaker is half-open or open, and how breaker state is observed by the retry layer"

## Common capability patterns

**Pattern: Circuit breaker on every external dependency with documented thresholds.** Capability scope must enumerate which dependencies are covered; caveats for any not in evidence.

**Pattern: Read-only degraded mode for portal during write-tier outage.** Maturity ladder: `designed` from tech plan, `implemented` requires application code or feature flag evidence, `tested` requires test report or game day evidence.

**Pattern: Bulkheaded thread pools separating adjudication from reporting.** Often higher confidence when application configuration is in evidence.

## prerequisite_evidence

These are the canonical multi-clause asks that unblock blocked-on-evidence findings in the Resilient lens. An operator MUST provide every sub-element listed; partial answers leave the finding blocked.

**Circuit-breaker specification:**

- **prerequisite_evidence:** "Circuit-breaker specification covering: (1) each circuit-breaker location in the topology (inbound at API gateway, outbound at every external-dependency client — eligibility vendor, drug-pricing vendor, PBM-to-PBM coordination, e-prescribing intermediary); (2) the trip threshold (failure rate, latency percentile, consecutive-failure count) and the recovery threshold (success-probe count, half-open admission rate) for each location; (3) the trip-event audit pipeline (which subsystem records the trip, which dashboard surfaces it, which on-call rotation is paged) so that breaker events are observable and not silent; (4) the downstream-failure-isolation behavior when the breaker is open — whether the caller fails fast, falls back to a cached or degraded response, or surfaces an explicit soft-deny to the pharmacy/member"

**Graceful-degradation modes:**

- **prerequisite_evidence:** "Graceful-degradation specification covering: (1) the per-feature degradation plan — read-only adjudication mode on write-tier outage, cached-eligibility mode on eligibility-vendor outage with cache-age bound, deferred PA queueing on PA-engine outage with member-facing status messaging, and the equivalent plan for any other ingress-critical surface; (2) the SLO impact of each degraded mode (claim-decision latency, eligibility-staleness bound, PA-decision latency) so plan-sponsor SLA exposure under degradation is quantified; (3) the operator surface that activates and deactivates each mode (feature flag, runbook step, automatic trigger), the authentication/authorization required to flip it, and the audit record produced when it is flipped"

## Domain: pbm — Source: `common-patterns/ephemeral.md`

# PBM common patterns — Ephemeral

These are illustrative templates, not all-inclusive. Use them to calibrate analytical style, severity assignment per the PBM rubric, and NIST/ATT&CK mapping habits. The specialist agent's analytical checklist still drives the actual analysis — this file calibrates how findings and capabilities should look once written.

Ephemerality is the single most leveraged control on PBM vendor-integration breach surface: long-lived service-account credentials — SCIM tokens to plan-sponsor IdPs, PDE-submission API keys, COB and accumulator integration credentials, mail-order and specialty fulfillment service accounts — are the dominant root cause in published PBM and healthcare-clearinghouse breach post-mortems, and HIPAA Security Rule §164.308(a)(4) access-management expectations bite hardest on credentials that outlive the personnel and contractual relationships that justified them. Long-lived operator sessions create a parallel problem on the audit side: actor attribution decays as a session ages across shift changes and role transitions. The load-bearing surfaces are vendor SCIM and provisioning tokens, PDE-submission API keys and CMS-side credentials, and the COB and accumulator integration credentials that touch member-level PHI.

## ATT&CK + D3FEND defensive mapping

This goal defends against (or is exploited by) the following MITRE ATT&CK techniques. Each citation is included only where the apd-control-mappings high-confidence-bar discipline is met; we deliberately omit techniques that only adjacently relate to this goal.

**ATT&CK techniques:**

- **T1552.001** (Credentials in Files) — long-lived PBM service-account credentials (SCIM tokens, PDE-submission API keys, COB and accumulator integration secrets) materialized in config, env vars, or vault paths exposed to over-broad readership
- **T1078** (Valid Accounts) — vendor-integration credentials and operator sessions outliving the personnel, contractual, or rotation cadence that justified them, which is the dominant root cause in published PBM and clearinghouse breach post-mortems
- **T1098** (Account Manipulation) — credential reactivation after intended rotation, or scope expansion on a service account (for example a COB integration credential gaining PDE-submission scope) without re-attestation

**D3FEND counters:**

- **D3-LFAM** (Local File Access Mediation) — counters T1552.001 by mediating filesystem and secret-store access to PBM credential locations so that compromise of an application tier does not yield the underlying long-lived secret
- **D3-RAPA** (Resource Access Pattern Analysis) — detects long-lived PBM service-account credentials being used at anomalous rates, from anomalous workloads, or against anomalous CMS / plan-sponsor endpoints, which is the operational signal for both T1078 and post-T1098 credential abuse

## Common finding patterns

**Pattern: Service account credentials are static long-lived secrets in application config.**

- Severity: high (broad blast radius on credential leak, no automatic invalidation)
- NIST: IA-5, IA-5(1), IA-5(7), SC-12(1)
- ATT&CK: T1078 (Valid Accounts) with sub-technique by environment

**Pattern: Database credentials shared across services; no rotation.**

- Severity: high
- NIST: IA-5, AC-2(2)
- Related concerns: confidentiality (key management around the shared credential)

**Pattern: Production access via standing admin role with no JIT.**

- Severity: high (excessive standing privilege, no time-boxing)
- NIST: AC-6, AC-2(2), AC-2(3)
- Related concerns: non_repudiation (audit of admin actions), authenticity (admin identity strength)

**Pattern: Container images mutable in production — `:latest` tags, in-place container updates.**

- Severity: medium (high when the mutable surface includes signing keys for NCPDP SCRIPT, PDE submission, or formulary configuration)
- NIST: CM-2, CM-3, SA-15(7)
- Related concerns: authenticity (image signing), integrity (configuration drift)

**Pattern: Tech plan mentions "secrets stored in vault" without rotation specifics.**

- Disposition: uncertainty or blocked
- prerequisite_evidence: "Credential lifecycle specification covering: (1) credential class taxonomy that distinguishes operator session credentials, service-account credentials, vendor integration credentials, and signing keys for NCPDP / PDE submission; (2) per-class lifetime expressed as a maximum age and rotation cadence; (3) per-class rotation automation pointer (Vault dynamic secrets, AWS Secrets Manager rotation lambda, IAM role assumption, SPIFFE/SPIRE workload identity) showing what executes the rotation; (4) per-class revocation pipeline including the emergency revocation path used when a credential is suspected compromised mid-cycle; (5) audit chain recording creation, rotation, suspension, and destruction events sufficient to reconstruct credential provenance during a HIPAA §164.308(a)(4) access-management review or a breach post-mortem"

**Pattern: Member portal session lifetime not specified.**

- Disposition: uncertainty
- prerequisite_evidence: "Session management policy covering: (1) maximum absolute session lifetime before forced re-authentication; (2) idle timeout that terminates an inactive session independent of absolute lifetime; (3) step-up authentication bounds — which member-portal actions (refill order placement, address change, payment-instrument change, mail-order pharmacy change) require a fresh authentication factor and what the freshness window is; (4) logout behavior including server-side session invalidation, refresh-token revocation, and propagation to downstream PBM systems that cached the session"

## Common capability patterns

**Pattern: Dynamic database credentials via vault.** Maturity depends on whether tech plan asserts (designed) or vault configuration is in evidence (implemented).

**Pattern: Workload identity via SPIFFE for service-to-service authentication.** Caveats expected on which services are confirmed.

**Pattern: JIT access for production via approval workflow with time-boxed grants.** Operational maturity requires runbook evidence; designed maturity from tech plan only.

**Pattern: Immutable container deployment via signed image references in IaC.** Cross-cuts Authenticity for the signing aspect; Ephemeral confirms the replace-don't-patch posture.

## prerequisite_evidence

When a finding pattern above is marked blocked-on-evidence rather than emitted as a gap, the operator must supply the multi-clause specifications below. Anything less and the specialist should keep the disposition as blocked rather than downgrade to uncertainty.

**Just-in-time access for production:** (1) the JIT access mechanism for human operators (broker name, ticket-driven elevation, ChatOps approval bot, cloud-native PIM) and the workloads it covers; (2) elevation requirements including approver identity (named role, not group), required justification entry, and the maximum time-bounded session length granted per elevation; (3) audit trail of every elevation event sufficient to answer "who approved which operator into which production scope for how long, on which date, against which change ticket"; (4) automatic expiry behavior on session timeout including credential revocation, in-flight session termination, and downstream notification to PBM systems that cached the elevated identity

## Domain: pbm — Source: `common-patterns/authenticity.md`

# PBM common patterns — Authenticity

These are illustrative templates, not all-inclusive. Use them to calibrate analytical style, severity assignment per the PBM rubric, and NIST/ATT&CK mapping habits. The specialist agent's analytical checklist still drives the actual analysis — this file calibrates how findings and capabilities should look once written.

Authenticity in a PBM gates both PHI access and the lawfulness of prescription transmission. Pharmacist credential strength is the upstream control on every PHI surface a clinical user touches — SAML/OIDC federation against the pharmacy or health-system SSO is the dominant authentication path, and HIPAA Security Rule §164.312(d) person-or-entity authentication is the regulatory anchor. Separately, NCPDP SCRIPT digital signatures gate the lawfulness of electronic prescription transmission under DEA EPCS rules at 21 CFR §1311, and PDE submission signing is what CMS uses to bind a Part D claim record to its submitting sponsor. The load-bearing surfaces are the pharmacist-portal SSO path (including step-up for PHI export and PA override), the NCPDP signed-message path for SCRIPT transactions, and the PDE-submission signing chain.

## ATT&CK + D3FEND defensive mapping

This goal defends against (or is exploited by) the following MITRE ATT&CK techniques. Each citation is included only where the apd-control-mappings high-confidence-bar discipline is met; we deliberately omit techniques that only adjacently relate to this goal.

**ATT&CK techniques:**

- **T1621** (Multi-Factor Authentication Request Generation) — push-bombing or MFA fatigue against pharmacist or admin portals
- **T1556.006** (Modify Authentication Process: Multi-Factor Authentication) — bypassing MFA via fallback channel, recovery flow, or enrollment abuse
- **T1078** (Valid Accounts) — credentials are valid but the holder is unauthorized to use them
- **T1110.003** (Brute Force: Password Spraying) — low-volume spraying against pharmacist and member portals
- **T1110.004** (Brute Force: Credential Stuffing) — reused-credential attempts from breach corpora against member portal

**D3FEND counters:**

- **D3-MFA** (Multi-factor Authentication) — counters T1621 indirectly and T1078 directly via factor requirement
- **D3-CR** (Credential Revocation) — counters T1078 by permanently revoking compromised credentials on detection so they cannot be reused for further PHI access
- **D3-MAN** (Message Authentication) — counters NCPDP SCRIPT and X12 signed-message tampering at the protocol layer

## Common finding patterns

**Pattern: Service-to-service inside cluster uses shared secret tokens, not mTLS.**

- Severity: high (lateral movement amplification)
- NIST: SC-8(1), SC-23, IA-3
- ATT&CK: T1557 with specific in-cluster rationale
- Related concerns: ephemeral (shared-secret rotation), confidentiality (in-cluster PHI in transit)

**Pattern: MFA bypass via SMS fallback on PHI surfaces.**

- Severity: high (effective AAL downgrade)
- NIST: IA-2(1), IA-2(2), IA-2(8)
- ATT&CK: T1621 (Multi-Factor Authentication Request Generation) with rationale

**Pattern: Container images deployed without signature verification.**

- Severity: high (supply chain compromise vector)
- NIST: SI-7, SR-4, SR-11
- Related concerns: ephemeral (immutable infra requires authentic images)

**Pattern: Webhook payloads from vendor accepted without signature verification.**

- Severity: high (forged webhook can inject malicious adjudication input)
- NIST: SC-23, IA-3(1), SI-10
- Related concerns: integrity (input validation, route to Integrity finding for the malformed-input concern)

**Pattern: SBOM not generated; no vulnerability attribution path.**

- Severity: medium (high when the PBM has a HITRUST CSF or URAC commitment that explicitly requires SBOM)
- NIST: SR-4, SR-4(3), SR-11

**Pattern: Tech plan describes "authenticated APIs" generically.**

- Disposition: uncertainty or blocked
- prerequisite_evidence: "API authentication specification — (1) mechanism per API surface (OAuth 2.0 client-credentials, OAuth 2.0 authorization-code with PKCE, mTLS with workload identity, signed JWT with named issuer); (2) token lifetime per token class (access, refresh, step-up) with rotation cadence; (3) token-validation procedure (signature algorithm, key-discovery via JWKS endpoint or pinned key, issuer/audience/scope checks, clock-skew tolerance); (4) revocation mechanism on credential compromise (introspection endpoint, deny-list, or short-TTL strategy); (5) audit event emitted on authentication success, failure, and step-up challenge"

## Common capability patterns

**Pattern: mTLS across service mesh with SPIFFE identity.** Scope must enumerate which services are confirmed; expect caveats for legacy services not yet onboarded.

**Pattern: FIDO2/WebAuthn for internal admin access to PHI surfaces.** Cross-cuts Ephemeral via the credential lifetime; mention via `related_concerns`.

**Pattern: Signed container images with admission control enforcement.** Maturity depends on whether admission policy is in evidence.

**Pattern: SLSA Level 2 build provenance for production deployments.** Higher maturity requires CI/CD configuration evidence.

## prerequisite_evidence

When an authenticity concern cannot be confirmed from the available evidence, the specialist agent should mark the finding `blocked-on-evidence` and name the specific artifacts required to unblock. The asks below are multi-clause on purpose — a single-line ask like "tell me about MFA" is not enough to unblock a blocked finding, because the operator will return a partial answer and the cycle repeats.

**MFA implementation:** (1) factor-mix per actor class (pharmacist, member, admin, vendor-integration); (2) AAL level per actor class per NIST 800-63B (AAL1/2/3) with evidence of the determination; (3) enrollment flow security (re-auth required at enrollment, identity-proofing artifact retained, FIDO2 attestation level where applicable); (4) recovery flow security (rate-limited, supervisor-attested, out-of-band channel distinct from primary factor); (5) MFA-fatigue mitigation (push-rate-limit, number-matching, geographic-anomaly detection); (6) phishing-resistance posture (SMS forbidden as a factor on PHI surfaces, WebAuthn or equivalent as the primary factor for privileged actors); (7) audit event emitted on MFA challenge, response, success, and failure with sufficient context to reconstruct the attempt.

**Signed-message verification:** (1) signing-key location per signed-message channel (NCPDP SCRIPT, X12 271/278/837, PDE outbound) including HSM, KMS, or in-process key material; (2) signature-verification implementation pointer (library name and version, with a code or config reference); (3) replay-protection mechanism (nonce, timestamp window, message-ID dedup store, or sequence number); (4) failure handling on signature-verification failure (reject and audit vs. quarantine vs. fail-open) including downstream alerting path.

**Federation configuration:** (1) IdP relationship per actor class (pharmacist SSO against pharmacy or health-system IdP, prescriber SSO, member portal IdP) including IdP name and trust establishment artifact; (2) SAML or OIDC configuration with assertion-validation scope (signature algorithm, audience restriction, attribute mapping, NotBefore/NotOnOrAfter enforcement, ID-token claim validation); (3) trust-chain validation including certificate-pinning where applicable to mobile or thick-client federation paths, and the policy for IdP-signing-certificate rotation.

## Domain: pbm — Source: `common-patterns/non-repudiation.md`

# PBM common patterns — Non-Repudiation

These are illustrative templates, not all-inclusive. Use them to calibrate analytical style, severity assignment per the PBM rubric, and NIST/ATT&CK mapping habits. The specialist agent's analytical checklist still drives the actual analysis — this file calibrates how findings and capabilities should look once written.

Non-repudiation in a PBM is a direct regulatory obligation, not a defense-in-depth nice-to-have. HIPAA Security Rule §164.312(b) (Audit Controls) requires actor-attributed records of activity on systems containing PHI, and §164.528 (Accounting of Disclosures) requires the PBM to produce defensible disclosure records to members on request — both fail open if the audit chain attributes actions to a shared system account, a sidecar identity, or an unbound session. CMS Part D PDE submission additionally requires auditable provenance for every claim record reconciled against rebate and risk-adjustment payments. The load-bearing surfaces are the PHI-access audit (record-level, not table-level), the PA-decision audit (which clinician, on which member, with what override rationale), and the configuration-change audit (formulary, PA criteria, MAC list, contract pricing).

## ATT&CK + D3FEND defensive mapping

This goal defends against (or is exploited by) the following MITRE ATT&CK techniques. Each citation is included only where the apd-control-mappings high-confidence-bar discipline is met; we deliberately omit techniques that only adjacently relate to this goal.

**ATT&CK techniques:**

- **T1070** (Indicator Removal) — audit-log deletion, retention shortening, or shipping-pipeline disable
- **T1036** (Masquerading) — audit-attribution falsification, including action attribution to a shared service-account rather than the human operator
- **T1562.008** (Impair Defenses: Disable or Modify Cloud Logs) — cloud-native audit-pipeline suppression

**D3FEND counters:**

- **D3-LFAM** (Local File Access Mediation) — counters T1070 by enforcing write-deny on the audit substrate
- **D3-MAN** (Message Authentication) — counters T1036 by binding the audit record to a per-actor signature

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
- prerequisite_evidence: "Time-source reliability specification — (1) authoritative time source (NTP server or NTS source), naming the upstream and topology; (2) clock-skew SLO with numeric bound; (3) clock-drift monitoring and remediation procedure (who is paged when drift exceeds SLO, and how the audit pipeline is quarantined); (4) timestamp inclusion in audit records (UTC, monotonic, or both) with the field name and precision"

**Pattern: Break-glass procedure exists but break-glass actions are not specially audited beyond normal logging.**

- Severity: medium (high when the audit gap covers PHI access — §164.312(b) audit-controls obligation)
- NIST: AU-3, AU-12(1), AC-6(9)

## Common capability patterns

**Pattern: Per-action PHI access audit with actor, resource, purpose, and outcome captured.** Scope must specify which surfaces are confirmed; caveats for any out-of-evidence.

**Pattern: Cryptographically signed audit entries hash-chained per stream.** Maturity depends on whether the chain is described in tech plan only or implemented in code/IaC.

**Pattern: ATNA-conformant audit format for clinical actions.** Often `designed` from tech plan; higher maturity requires implementation evidence.

**Pattern: Audit log read access gated by separate role from operational roles, with read events themselves audited.** Cross-cuts Authenticity for the role definition.

## prerequisite_evidence

When a non-repudiation finding is blocked-on-evidence, the operator must supply the following multi-clause specifications to unblock. Single-line answers ("we have audit logging") are insufficient; each clause below names a sub-element the synthesizer expects to see resolved before the finding's disposition can move off blocked.

**Audit-coverage matrix:**

  (1) consequential-action surface mapped to audit-event taxonomy (each consequential action emits at least one audit event of the named class, with the mapping enumerated rather than asserted);
  (2) actor-attribution policy on each audit event class (which identity claim is captured, and whether it resolves to a human operator versus a shared service principal);
  (3) signing or hash-chaining mechanism per class (algorithm, key custody, and chain-verification cadence);
  (4) audit-shipping pipeline (queue, transit, sink) with availability target (numeric SLO and what happens to the action when the pipeline is degraded);
  (5) audit-of-audit pipeline (audit reads, retention changes, log-shipping disable) on a forensically isolated channel (named substrate, separate IAM, and separate retention floor);
  (6) retention-floor enforcement substrate per class (the technical control that prevents an operator from shortening retention below the regulatory floor).

**Time-source reliability:**

  (1) authoritative time source (NTP server or NTS source), naming the upstream and topology;
  (2) clock-skew SLO with numeric bound;
  (3) clock-drift monitoring and remediation procedure (who is paged when drift exceeds SLO, and how the audit pipeline is quarantined);
  (4) timestamp inclusion in audit records (UTC, monotonic, or both) with the field name and precision.

**Audit-access segregation:**

  (1) read access policy on the audit substrate (who can query, against which retention window, and with what query-audit obligation);
  (2) separation of audit-read and audit-write privileges from operator-action privileges (no role that performs consequential actions may also redact, retire, or query its own audit trail);
  (3) audit-of-audit emitter capturing every administrative read (with actor, query, and result-set fingerprint) on a forensically isolated channel.

## Domain: pbm — Source: `common-patterns/immutability.md`

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

- Severity: medium (high when the manually-managed retention covers HIPAA §164.316(b)(2)(i) 6-year or CMS §423.505(d) 10-year floors)
- NIST: CM-2, CM-2(2), CM-3, CM-6
- Related concerns: integrity (configuration correctness), authenticity (signed-commit posture)

**Pattern: Configuration repository allows history rewrite (no protected branches).**

- Severity: medium (high when the affected retention floor is regulator-mandated rather than contractual)
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

## Domain attack-path defaults (merged across packs)

Unioned and deduplicated from the selected packs' `domain.yaml`. Run-config `crown_jewels` / `attacker_positions` still override these. Each entry's `domains` lists the contributing pack(s).

### Crown jewels

```yaml
crown_jewels:
- pattern: phi_store
  description: Member PHI store carrying demographics, claims history, prescriber/diagnosis
    associations subject to HIPAA breach-notification thresholds.
  domains:
  - pbm
- pattern: pde_submission_pipeline
  description: "CMS Part D Prescription Drug Event submission pipeline \u2014 submission\
    \ integrity is regulator-anchored under CMS rules and material to plan revenue."
  domains:
  - pbm
- pattern: claim_adjudication_engine
  description: "Real-time claim adjudication engine \u2014 pricing accuracy and decision\
    \ integrity drive member out-of-pocket and pharmacy reimbursement."
  domains:
  - pbm
- pattern: audit_log_store
  description: "Security and consequential-action event log spanning PHI access, claim-adjudication\
    \ decisions, prior-authorization decisions, configuration changes, break-glass\
    \ invocations, and CMS PDE submission events. HIPAA Security Rule \xA7164.312(b)\
    \ (Audit Controls) treats this store as the breach-detection and breach-notification\
    \ fact base \u2014 regulators treat absence or alteration as presumption of breach.\
    \ Compromise enables both attack-concealment (T1070 Indicator Removal) and post-incident\
    \ liability \u2014 without defensible audit, the PBM cannot satisfy HIPAA breach-notification\
    \ rules even when an attack is otherwise detected. NIST SP 800-66 Rev 2 provides\
    \ \xA7164.312(b) implementation guidance for the audit-controls obligation."
  domains:
  - pbm
- pattern: backup_artifact_store
  description: "Database snapshots (adjudication, member, claim history), object-store\
    \ backups (PDE batch archives, audit-log archives), configuration backups, and\
    \ key-material escrow copies. Frequently the weakest crown jewel because encryption-at-rest,\
    \ access controls, and immutability protections are typically weaker than the\
    \ primary stores they protect against. A successful exfiltration of a backup commonly\
    \ bypasses the controls applied to live PHI surfaces and produces the same regulatory\
    \ consequences under 45 CFR \xA7164.408."
  domains:
  - pbm
- pattern: prescriber_directory
  description: "Provider attribution surface \u2014 NPI, DEA registration number,\
    \ state pharmacy/medical license, prescriber specialty, prescriber demographics,\
    \ controlled-substance authority. Compromise enables both prescription-fraud campaigns\
    \ (forge prescriptions in a real prescriber's name) and clinical-decision misattribution\
    \ (DUR alerts routed to wrong prescriber). DEA records are subject to 21 CFR \xA7\
    1304.04 retention; state-license records are commonly subject to state pharmacy-board\
    \ reporting requirements separate from HIPAA."
  domains:
  - pbm
- pattern: rebate_formulary_pricing_data
  description: "Manufacturer rebate calculations, Maximum Allowable Cost (MAC) lists,\
    \ formulary tier assignments, pharmacy-network reimbursement schedules, and accumulator\
    \ history. Compromise yields commercial-confidentiality exposure (master-service-agreement\
    \ breach, manufacturer-rebate-contract breach) and competitive-intelligence harm;\
    \ tampering yields plan-payment fraud and pharmacy-reimbursement disputes that\
    \ commonly trigger litigation. Retention requirements typically derive from contract\
    \ terms rather than statute, but the contract floors are routinely 7\u201310 years\
    \ to cover audit and statute-of-limitations windows."
  domains:
  - pbm
- pattern: member_authentication_credentials
  description: "Member portal authentication store \u2014 password hashes, MFA enrollments,\
    \ recovery email and phone, security questions, account-lockout state. Compromise\
    \ yields member-account takeover at scale, which converts directly to PHI exposure\
    \ under HIPAA (every claim record and PA history for the affected member becomes\
    \ readable). Authentication factor strength and recovery-flow integrity gate both\
    \ the \xA7164.524 (Right of Access) surface and the \xA7164.502 (Minimum Necessary)\
    \ surface."
  domains:
  - pbm
- pattern: vendor_integration_secrets
  description: "Service-account credentials, API tokens, and signing keys used for\
    \ outbound integrations \u2014 rebate aggregators, COB carriers, eligibility partners,\
    \ mail-order fulfillment pharmacies, accumulator vendors, and analytics partners.\
    \ Long-lived service-account credentials are the dominant root cause of vendor-channel\
    \ PHI exposure incidents; compromise of one integration credential commonly yields\
    \ lateral PHI access across the entire vendor surface. Each credential's blast\
    \ radius equals the data scope granted in the underlying Business Associate Agreement."
  domains:
  - pbm
```

### Attacker positions

```yaml
attacker_positions:
- position: external_internet
  description: Untrusted external internet client; the default external attacker position
    for any internet-facing surface.
  domains:
  - pbm
- position: compromised_pharmacy_credential
  description: An attacker holding a valid pharmacy-submitter credential through phishing,
    credential stuffing, or insider abuse at a pharmacy partner.
  domains:
  - pbm
- position: compromised_vendor_integration
  description: An attacker who has compromised a third-party vendor's integration
    credentials (e.g., a benefits-management vendor or analytics partner).
  domains:
  - pbm
- position: insider_with_member_service_role
  description: An insider holding a legitimate member-services role but acting outside
    their minimum-necessary scope (e.g., bulk PHI export, unauthorized member lookups).
  domains:
  - pbm
- position: compromised_dev_workstation
  description: An attacker who has compromised a developer or operator workstation
    with production deployment or break-glass access.
  domains:
  - pbm
- position: unauthenticated_internet_against_member_portal
  description: "Untrusted external attacker targeting the member-portal authentication\
    \ surface specifically (distinct from the generic external_internet position,\
    \ which models any internet-facing surface). Models credential-stuffing campaigns,\
    \ OWASP API1 (BOLA) on member-id-keyed endpoints, OWASP API5 (BFLA) on tier-distinct\
    \ endpoints (member vs admin), enumeration of member identifiers via login or\
    \ password-reset response oracles (T1110.003 Password Spraying, T1110.004 Credential\
    \ Stuffing), and SAML/OIDC misconfiguration on federated member access. The defining\
    \ threat: a successful authentication compromise here converts directly to PHI\
    \ exposure under HIPAA \xA7164.508 (Authorization) without further escalation."
  domains:
  - pbm
- position: authenticated_member_seeking_cross_member_phi
  description: "A member with valid credentials attempting horizontal escalation to\
    \ another member's PHI \u2014 typically via IDOR on member-id parameters, predictable\
    \ claim-reference URLs, parameter tampering on dependent-coverage endpoints, or\
    \ session re-use across logical member contexts (T1078.004 Cloud Accounts applied\
    \ to member portal). The most common PBM-specific manifestation is dependent-coverage\
    \ scope: a primary subscriber attempting to access an adult dependent's PHI. Adult\
    \ dependents are not within the \xA7164.502(g) personal-representative scope,\
    \ so the access falls under the \xA7164.502(a) general use-and-disclosure rule\
    \ and requires \xA7164.508 authorization from the adult dependent before disclosure."
  domains:
  - pbm
- position: compromised_cms_submission_credential
  description: "Attacker holding the credential or signing key used to authenticate\
    \ the PBM's outbound CMS Part D PDE submission channel. Distinct from compromised_pharmacy_credential\
    \ (which models inbound NCPDP claim submission) and compromised_vendor_integration\
    \ (which models third-party vendor egress). Maps to T1078 (Valid Accounts) for\
    \ credential-holding abuse of the held CMS submission credential, T1565.002 (Transmitted\
    \ Data Manipulation) when the held signing key is used to inject falsified PDE\
    \ records into the outbound submission channel, and T1565.001 (Stored Data Manipulation)\
    \ for altering PDE retroactive corrections in the submission staging store. Compromise\
    \ yields the ability to submit falsified PDE records, suppress legitimate PDE\
    \ records, or alter PDE retroactive corrections \u2014 each producing 42 CFR \xA7\
    423.322 PDE-data-integrity consequence (CMS payment-determination reopening, plan-payment\
    \ recovery, potential False Claims Act exposure under 31 U.S.C. \xA73729 if the\
    \ submission was knowingly false)."
  domains:
  - pbm
- position: compromised_admin_workstation
  description: 'Attacker who has compromised an operator or administrator workstation
    with privileged access to formulary configuration, PA-criteria configuration,
    MAC pricing, contract-pricing tables, or audit-log retention settings. Distinct
    from compromised_dev_workstation (which models pre-production tooling). Models
    the post-phishing escalation path where a compromised admin can silently disable
    audit shipping (T1070), backdate audit entries (T1036 Masquerading at the audit
    layer), or alter the formulary configuration to produce clinical-decision harm
    at scale. The defining feature: actions taken from this position attribute to
    a legitimate operator credential, so defensibility depends entirely on the audit-of-audit
    surface.'
  domains:
  - pbm
- position: internal_lateral_attacker_in_adjudication_tier
  description: "Attacker who has already established a foothold in the internal network\
    \ \u2014 typically through the dev_workstation position, an exposed admin-console\
    \ session, or a vendor-integration compromise \u2014 and is now attempting lateral\
    \ movement to reach the PHI store, the adjudication engine, or the PDE submission\
    \ pipeline. Models the post-breach window where the attacker has time and access\
    \ to enumerate internal services, abuse in-cluster trust assumptions (T1078 Valid\
    \ Accounts on service-account credentials, T1213 Data from Information Repositories\
    \ on internal PHI replicas), and escape from a low-value tier to a high-value\
    \ tier. The defining test for this position: would mTLS, network segmentation,\
    \ and credential-scoping prevent the attacker from reaching the crown jewel from\
    \ their established foothold?"
  domains:
  - pbm
```

### Default trust boundaries

```yaml
default_trust_boundaries:
- boundary: pharmacy_submission_ingress
  description: Boundary between external pharmacy submitters and the claim-ingress
    API; first authentication/authorization checkpoint for claim submission.
  domains:
  - pbm
- boundary: member_portal_ingress
  description: Boundary between internet members and the member-facing portal; second
    external ingress with PHI-read scope after authentication.
  domains:
  - pbm
- boundary: internal_to_pde_submission
  description: Boundary between internal services and the CMS Part D submission pipeline;
    outbound regulatory channel with submission-integrity guarantees.
  domains:
  - pbm
- boundary: adjudication_engine_to_phi_data_tier
  description: Service-to-datastore crossing between the claim-adjudication engine
    and the underlying PHI store (PostgreSQL, MongoDB, or vendor-specific adjudication-engine
    database). Frequently the weakest link under 'in-cluster trust' assumptions; enforcement
    requires in-cluster mTLS, query parameterization to prevent NoSQL/SQL injection
    on member-id or claim-reference parameters, and least-privilege datastore credentials
    scoped to the specific adjudication operation. A successful boundary failure here
    reaches the largest PHI scope in the PBM.
  domains:
  - pbm
- boundary: pbm_to_third_party_vendor
  description: "Outbound egress from PBM services to third-party vendors with whom\
    \ the PBM has a Business Associate Agreement under HIPAA \xA7164.504(e) \u2014\
    \ rebate aggregators, accumulator vendors, COB carriers, analytics partners, mail-order\
    \ fulfillment pharmacies, specialty-pharmacy fulfillment, and switch operators\
    \ (RelayHealth, Change Healthcare). The boundary is multi-channel (HTTPS APIs,\
    \ SFTP file drops, IBM MQ enterprise messaging) and each channel needs its own\
    \ authentication, encryption-in-transit, and data-scope-enforcement. Vendor-credential\
    \ compromise (see compromised_vendor_integration attacker position) is the dominant\
    \ breach vector here."
  domains:
  - pbm
- boundary: phi_subject_zone
  description: "HIPAA-anchored PHI segmentation boundary, analogous to api-security's\
    \ personal_data_subject_zone for GDPR. Crossings into or out of this zone trigger\
    \ HIPAA Privacy Rule disclosure analysis (45 CFR \xA7164.502 Uses and Disclosures,\
    \ \xA7164.514(b)(1) Expert Determination and \xA7164.514(b)(2)(i) Safe Harbor\
    \ identifier enumeration). Includes the de-identification gate for analytics surfaces,\
    \ the minimum-necessary gate for internal cross-team data sharing (\xA7164.502(b)),\
    \ and the lawful-basis gate for any disclosure outside the Treatment / Payment\
    \ / Operations exception (\xA7164.506)."
  domains:
  - pbm
- boundary: admin_console_to_pbm_backend
  description: "Privileged-administration crossing between the operator admin console\
    \ (formulary editor, PA criteria editor, MAC list editor, contract-pricing editor,\
    \ audit-retention configuration) and the corresponding backend services and configuration\
    \ stores. The blast radius of any boundary failure here is the entire PBM \u2014\
    \ admin actions silently affect every subsequent claim adjudicated against the\
    \ modified configuration. Enforcement requires step-up authentication (per the\
    \ severity rubric's authentication-bypass clause), four-eyes / dual-approval workflows\
    \ on configuration-changing actions, and an audit chain attributing the action\
    \ to the human operator (not the operator's session token or sidecar identity)."
  domains:
  - pbm
```
