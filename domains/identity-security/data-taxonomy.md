# Identity security data taxonomy

Specialist agents treat the following fields as sensitive when they appear in artifacts. The intake brief's data inventory MUST enumerate every field present; missing fields become evidence gaps surfaced as `blocked-on-evidence` findings against the intake set. The taxonomy is calibrated for identity-provider systems where the IdP both stores credentials and issues assertions about identity to downstream relying parties.

## Authentication factors

- password (cleartext — must never persist beyond hashing; in-memory window must be bounded)
- password_hash (argon2id preferred, bcrypt acceptable, scrypt acceptable; PBKDF2 / SHA-512crypt / MD5-crypt are findings)
- password_salt (per-user, treat as sensitive only insofar as exposure plus algorithm enables targeted attacks)
- totp_seed (HMAC shared secret; equivalent to a long-lived possession factor — compromise enables silent OTP generation by the attacker)
- hotp_counter (paired with totp_seed for counter-based variants; sync state is sensitive)
- webauthn_credential_id (per-credential identifier; treat as sensitive — exposure enables credential enumeration)
- webauthn_public_key (less sensitive — designed to be public-half, but listing per-user enables targeting)
- webauthn_signature_counter (replay-prevention state; mutation enables replay)
- fido2_attestation_certificate (per-authenticator attestation; treat as sensitive metadata)
- recovery_code (single-use bypass — equivalent to a knowledge-factor reset of the authenticator; high-sensitivity)
- backup_codes (set of single-use codes; same sensitivity as recovery codes)
- security_question_answer (often weak entropy; treat as low-entropy credential and prefer to deprecate)
- biometric_template (face print, fingerprint template, voice print) — special-category personal data under GDPR Article 9

## Token material

- access_token (OAuth 2.0 bearer; JWT or opaque; treat as session-equivalent for the token lifetime)
- refresh_token (OAuth 2.0; longer-lived; storage MUST be hashed when at rest on the IdP side; bearer-by-default unless DPoP/mTLS bound)
- id_token (OIDC; signed JWT; contains identity claims about the subject)
- authorization_code (OAuth 2.0; short-lived pre-exchange; sensitive within the seconds-window before exchange)
- device_code, user_code (RFC 8628 device-authorization grant; sensitive within the polling window)
- pkce_code_verifier (per-flow secret; sensitive within the OAuth flow window)
- pkce_code_challenge (server-side stored; sensitive insofar as it binds the verifier)
- oauth_state (CSRF binding; per-flow nonce)
- oauth_nonce, oidc_nonce, c_hash, at_hash (OIDC binding values; sensitive only insofar as they bind tokens)
- session_cookie (browser session identifier; equivalent to bearer token for the session window)
- saml_assertion (signed XML document containing identity claims; sensitive in transit and at rest; assertion_id must be unique to prevent replay)
- saml_request_id, saml_in_response_to (correlation values; replay-prevention binding)
- jwe_encrypted_payload (when sensitive claims warrant encryption beyond signature)
- ciba_auth_req_id (RFC 9126 backchannel authentication state)

## Identity attributes

- username (sensitive when not pseudonymous — username = email reveals personal data)
- email (primary, recovery, verified state)
- phone (SMS-MFA target, recovery)
- display_name (often legal name)
- given_name, family_name
- preferred_username
- locale, zoneinfo
- organizational_unit (org membership reveals affiliation)
- group_memberships (set; combinable for re-identification)
- role_assignments (set; authorization-relevant)
- custom_claims (per-tenant attribute extensions; sensitivity depends on contents)
- subject_identifier (sub claim; per-issuer-per-audience pairwise where supported by OIDC `pairwise` subject type — flag findings on `public` subject type when re-identification risk is in scope)

## Federation metadata

- saml_metadata_xml (per-SP/IdP; contains signing/encryption certs, ACS URLs, entity IDs)
- saml_signing_certificate (public-half, but rotation history is sensitive)
- saml_encryption_certificate (public-half; encryption target)
- oidc_discovery_document (per-issuer; contains JWKS URI, supported flows)
- jwks (JSON Web Key Set; public-half by design; rotation cadence is the sensitive aspect)
- jwks_rotation_history (which kid was active at what time — required for after-the-fact assertion validation)
- federation_trust_record (per-SP trust establishment, including the human approval trail)
- attribute_release_policy (per-SP which attributes are released — privacy-relevant)
- jit_provisioning_rule (per-upstream-IdP mapping expression — authorization-relevant)

## Consent records

- oauth_consent_grant (per-user-per-RP-per-scope; GDPR Article 6(1)(a) lawful-basis evidence)
- oauth_grant_revocation_event (separate event; consent withdrawal does not eliminate the proof-of-prior-consent obligation)
- saml_attribute_release_acknowledgement (analogous for SAML federation flows)
- oidc_offline_access_grant (long-lived authorization for refresh-token issuance)
- device_authorization_user_approval (RFC 8628 device-flow consent action)

## Audit content

- authn_event (success, failure with reason, MFA challenge, MFA success, MFA failure, lockout, recovery)
- authz_event (allow/deny on consequential operation, role-based decision, scope-based decision)
- token_lifecycle_event (issue, refresh, revoke, expire, reuse-detected)
- consent_event (grant, revoke, scope change)
- federation_event (SAML assertion issued, attribute released, IdP-initiated SSO, SLO)
- admin_event (role change, policy change, signing-key rotation, federation-trust change, audit-config change)
- credential_lifecycle_event (password change, MFA enrollment, WebAuthn registration, recovery-code regeneration)
- account_lifecycle_event (creation, deletion, suspension, reactivation, identity-proofing upgrade)
- key_lifecycle_event (creation, rotation, revocation, destruction; required for proving 800-63B §5.1.4 key-management discipline)
- before_state / after_state on attribute mutations (may contain PII; audit storage inherits highest field sensitivity)
- actor_identifier (user ID, service identity, workload identity, federated subject)
- request_metadata (IP, user agent, request ID, correlation ID, AAL claim, FAL claim)

## Cryptographic material

- jwt_signing_private_key (RS256/ES256/EdDSA; the universal-forgery key)
- jwt_signing_public_key (JWKS public set — public-half by design)
- saml_signing_private_key (X.509 private; per-IdP-entity)
- saml_signing_certificate (public-half)
- saml_encryption_private_key (decryption of inbound encrypted assertions)
- jwe_content_encryption_key (per-assertion symmetric key, key-wrapped under recipient public key)
- kms_wrapping_key_handle (the upper-tier KMS/HSM root that protects the above; sensitive even though the IdP holds only a handle)
- mtls_client_certificate_private_key (for IdP-to-RP outbound or RP-to-IdP inbound client auth)
- jwks_rotation_history (which signing key was active in which window — required for after-the-fact assertion validation and revocation)

## Personal data (GDPR Article 4(1))

The IdP frequently stores personal data as identity attributes. The api-security domain pack's taxonomy applies for the secondary classification; this pack adds the identity-specific factors above.

- name, email, phone, address, date_of_birth, national_id_equivalent, ip_address, device_identifier, geolocation
- account_username when not pseudonymous

## Special category personal data (GDPR Article 9)

- biometric_data used for unique identification (FIDO2 attestation that conveys biometric class, voice/face/fingerprint templates)
- health_data, genetic_data, racial_or_ethnic_origin, religious_or_philosophical_belief, political_opinion, trade_union_membership, sexual_orientation_or_sex_life — typically not stored by the IdP, but custom claims and attribute-release policies CAN convey these from upstream sources; flag any case where the IdP is in the path of special-category claim release without an Article 9(2) basis.

## Out of scope

- public_half cryptographic material (JWKS public set, SAML metadata public certs, OIDC discovery document) — public by protocol design
- well-known issuer URLs, /.well-known/openid-configuration — public by design
- public OIDC client_id values for registered RPs (the secret is sensitive; the ID itself is not)
- fully pseudonymous subject identifiers under the OIDC `pairwise` subject type with the pseudonymization mapping held in a separately-accessible trust zone

This taxonomy is consulted by Confidentiality, Integrity, Authenticity, and Non-Repudiation specialists. The intake agent enumerates fields by reading artifacts against this list and surfaces missing-field declarations as `blocked-on-evidence` findings.
