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

## Out of scope

- aggregate analytics with k-anonymity ≥ 5
- de-identified per Safe Harbor (45 CFR §164.514(b)(2))

This taxonomy is consulted by Confidentiality, Integrity, and Non-Repudiation specialists. The intake agent enumerates fields by reading artifacts against this list.
