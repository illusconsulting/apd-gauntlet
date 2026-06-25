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
