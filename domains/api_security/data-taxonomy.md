# API security data taxonomy

Specialist agents treat the following fields as sensitive when they appear in artifacts. The intake brief's data inventory MUST enumerate every field present; missing fields become evidence gaps surfaced as `blocked-on-evidence` findings against the intake set.

## Personal data (GDPR Article 4(1))

- name (legal name, given/family separately or combined)
- email (primary, recovery, secondary)
- phone (mobile, home, work, SMS-verified)
- postal address (street, locality, region, postal code, country)
- date_of_birth and age-band derivations
- national_id equivalents (SSN, NIN, passport, driver's license number, tax ID)
- ip_address (client IP, X-Forwarded-For-derived, geolocated)
- device_identifier (advertising ID, push token, persistent cookie, fingerprint)
- geolocation (latitude/longitude, place identifiers, BSSID-derived)
- vehicle_identifier and other quasi-identifiers that re-identify in combination
- profile_picture and other biometric-adjacent media
- account_username when not pseudonymous and reusable across services

## Special category personal data (GDPR Article 9)

- health_data (medical conditions, prescriptions, fitness telemetry that reveals condition)
- biometric_data used for unique identification (face print, fingerprint template, voice print)
- genetic_data
- racial_or_ethnic_origin
- religious_or_philosophical_belief
- political_opinion
- trade_union_membership
- sexual_orientation_or_sex_life
- data_concerning_children when subject is under the age of digital consent (varies 13–16 by jurisdiction)

Special-category data carries stricter lawful-basis requirements under GDPR Article 9(2); processing without an Article 9(2) basis is unlawful regardless of Article 6 basis.

## Cardholder data (PCI-DSS scope)

- PAN (Primary Account Number) — the scope-defining element
- cardholder_name when stored, processed, or transmitted with PAN
- expiration_date when stored with PAN
- service_code when stored with PAN
- full_magnetic_stripe / full_track_data (Sensitive Authentication Data — must never be stored post-authorization)
- CAV2 / CVC2 / CVV2 / CID (Sensitive Authentication Data — must never be stored post-authorization)
- PIN / PIN_block (Sensitive Authentication Data — must never be stored post-authorization)

Tokenized PAN is NOT cardholder data **only if** the tokenization scheme meets PCI Council guidance (tokens are not derivable from PAN, the detokenization vault is itself PCI-scope and segmented, and the token-to-PAN mapping is the only reversal path). Format-preserving encryption is typically still in PCI scope.

## Authentication factors

- password (cleartext — must never persist beyond hashing)
- password_hash (argon2, scrypt, bcrypt; treat as sensitive even though irreversible)
- mfa_seed (TOTP shared secret; equivalent to a long-lived credential)
- mfa_recovery_code (single-use bypass; equivalent to a knowledge-factor reset)
- webauthn_credential (public key plus credential ID; less sensitive than seeds but still attributable)
- security_question_answer (often weak; treat as low-entropy credential)
- oauth_client_secret (confidential-client credential)
- api_key (bearer secret; treat as long-lived credential)
- signing_key (JWT/PASETO HMAC keys, RSA/EdDSA private keys, KMS-wrapped DEKs)

## Session state

- jwt (header + claims considered sensitive even if signature is verifiable; claims often include PII)
- refresh_token (bearer; longer-lived than access token)
- session_cookie (browser session identifier; equivalent to bearer token for the session window)
- oauth_bearer_token (access token; same handling as JWT)
- pkce_verifier (short-lived but sensitive within the OAuth flow window)
- csrf_token (typically per-session, sensitive only to its origin)

## Service credentials

- service_account_token (Kubernetes ServiceAccount JWT, cloud IAM credentials, workload identity tokens)
- kubeconfig (contains cluster CA, user credentials, context bindings)
- database_connection_string with embedded credentials (URI-format DSNs are a recurring leakage vector)
- ssh_key (private half)
- ci_cd_token (GitHub Actions OIDC, GitLab CI tokens; treat as service credentials)
- container_registry_pull_secret

## Audit content

- actor_identifier (user ID, service identity, workload identity)
- resource_identifier (object ID being acted on; may be a sensitive identifier itself)
- action_descriptor (CRUD verb, business action name)
- before_state and after_state snapshots — may contain PII or payment data; audit storage often inherits the highest sensitivity of any field it captures
- request_metadata (IP, user agent, request ID, correlation ID)
- decision_outcome (allow/deny, success/failure, error categorization)

Audit content inherits the sensitivity of the highest-sensitivity field it captures. Audit storage policies must reflect this — encrypting audit at rest, restricting audit-read roles, and applying PII-redaction policies on audit egress.

## Out of scope

- fully anonymized aggregates with k-anonymity ≥ 5 and no quasi-identifier combination that re-identifies
- de-identified per HIPAA Safe Harbor (45 CFR §164.514(b)(2)) when the system is in scope for HIPAA
- pseudonymous identifiers with the pseudonymization key held separately and inaccessible from the production data path (GDPR Recital 26 — but the pseudonym + key combined are personal data)

This taxonomy is consulted by Confidentiality, Integrity, and Non-Repudiation specialists. The intake agent enumerates fields by reading artifacts against this list and surfaces missing-field declarations as `blocked-on-evidence` findings.
