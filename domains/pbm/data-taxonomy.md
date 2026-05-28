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
