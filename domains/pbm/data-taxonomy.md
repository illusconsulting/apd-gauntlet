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

This taxonomy is consulted by Confidentiality, Integrity, Authenticity, Non-Repudiation, and Immutability specialists. The intake agent enumerates fields by reading artifacts against this list.

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
- **Mask for non-contractual analytics** export — the rebate-aggregator surface, the COB-carrier surface, and analytics tenants outside the plan-sponsor scope cannot see ingredient cost, MAC, or dispensing fee.
