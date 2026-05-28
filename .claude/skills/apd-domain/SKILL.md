---
name: apd-domain
description: Active domain pack content — severity rubric, consequential actions, common patterns. Generated from a domain pack at build time; do not edit by hand.
metadata:
  pack: identity-security
  pack_version: 1.0.0
  framework_version: 1.4.0
  generated: 2026-05-28T04:08:25Z
---


## Source: `severity-rubric.md`

# Identity Security Severity Rubric (impact-to-identity-service-and-its-relying-parties)

Calibrated against impact-to-the-identity-provider-and-every-application-that-federates-with-it, not against generic CVSS. The specialist agent cites the matching clause in finding `detail` fields. Cited examples in each tier are illustrative, not exhaustive. NIST SP 800-63B Authenticator Assurance Levels (AAL1/AAL2/AAL3), NIST SP 800-63C Federation Assurance Levels (FAL1/FAL2/FAL3), the OAuth 2.0 Security BCP (RFC 9700), OIDC Core 1.0 §16, and the SAML 2.0 Security Considerations profile are referenced inline.

## Critical

Any of the following:

- **Token signing key compromise** — attacker can mint arbitrary access tokens, refresh tokens, ID tokens, or SAML assertions for any subject in any audience. Yields universal authentication bypass across every relying party that trusts the issuer. Recovery requires JWKS rotation, mass session invalidation, and (for asymmetric SAML signing keys) re-establishment of trust at every SP. Maps to NIST SP 800-63C §4.7 (assertion signing keys must be protected at the highest assurance level used).
- **Authentication bypass on the primary login** — no credential required: JWT `alg:none` accepted, signature verification skipped, SAML signature wrapping (XSW) yielding identity substitution, OIDC ID-token accepted without signature check, password-grant accepting empty password against legacy backends, or LDAP anonymous-bind producing authenticated session. The defining critical case under NIST SP 800-63B §4.
- **Mass credential exfiltration** — password hash dump from the credential store, MFA seed table export, WebAuthn credential record dump, or recovery-code table exfil. Triggers GDPR Article 33 72-hour notification, mass password-reset enforcement, mandatory MFA re-enrollment, and downstream credential-stuffing exposure across every external service the user population shares passwords with.
- **MFA bypass for high-AAL surface** — any path that silently downgrades a NIST 800-63B AAL3-required surface to AAL1 (password only) or AAL2 (SMS, knowledge-based) without policy decision, alert, or audit. Includes WebAuthn-enrollment endpoints reachable without re-authentication, MFA-disable through profile-edit injection, and recovery flows that bypass possession factors entirely.
- **Audit trail loss for authentication or authorization events** — destroys the forensic fact base for credential-compromise reconstruction, renders GDPR Article 33 breach scoping un-meetable, renders SOC 2 CC7.2 un-attestable, and produces the regulatory presumption-of-breach default. Includes audit pipeline silent-loss, audit-shipping fire-and-forget under broker outage, and audit-store deletion-by-single-credential.
- **Total IdP outage exceeding contractual SLA** — sustained inability to authenticate any user; every dependent application loses auth simultaneously. Cascading total platform outage with contractual SLA breach across every customer organization. Severity is critical regardless of cause (region outage, signing-key unavailability, database failure, session-store wipe).
- **OAuth confused deputy / relying-party impersonation** — relying party can act as another user via token misuse: unbound assertion accepted across audiences, OAuth client_id mix-up attack (RFC 9700 §4.4.2), missing audience claim validation, or token exchange (RFC 8693) without authorization-server-side scope reduction. The compromise unit is "any user of any RP via any RP."
- **SAML signature wrapping (XSW) accepted** — an SAML SP/IdP that processes assertions without canonicalizing the signed region and re-validating against the parsed assertion: attacker can substitute a forged inner assertion while preserving the outer signature. Yields arbitrary subject impersonation. Maps to SAML 2.0 Security Considerations §6.3 and the foundational SAML implementation flaw class.
- **JWT algorithm confusion at the issuer** — `alg:none` accepted, asymmetric public key used as HMAC secret (RS256 verified as HS256), key-ID confusion via JWKS URL injection, or kid-header path traversal yielding key substitution. Yields forgeable tokens at platform scope.

## High

Any of the following:

- **AAL downgrade** — high-AAL surface accepts low-AAL evidence: WebAuthn-required admin surface accepts password-only via a back-door endpoint, AAL3-target tenant accepts AAL2 SMS-fallback on a subset of flows, or step-up authentication is offered but bypassable. Maps to NIST SP 800-63B §4.4 (AAL boundary discipline) and §5.1 (authenticator types per AAL).
- **Open redirect on OAuth callback** — `redirect_uri` allowlist permissive (suffix match, wildcard, missing path check), permitting authorization-code or token leak via redirect manipulation. Includes covert-redirect / parameter-pollution variants (RFC 9700 §4.1).
- **CSRF on OAuth authorization flow** — `state` parameter not validated, not bound to session, or omitted entirely; permits authorization-code injection / session fixation in OAuth (RFC 9700 §4.7).
- **PKCE bypass or absence** — confidential clients accepting authorization codes without PKCE verification when configured, or public clients (native, SPA) onboarded without PKCE requirement. Authorization-code interception on public clients is the canonical OAuth 2.1 hardening.
- **Session fixation in interactive login** — the IdP issues a session identifier before authentication that survives the authentication step, permitting the attacker to plant a session ID the victim later authenticates into. Maps to OWASP ASVS V3.2.
- **SAML signature wrapping (XSW) partially mitigated** — the SP validates signatures but the canonical-region resolution is library-default and known to be bypassable (e.g., XML namespace tricks, Comment injection in subject NameID). High rather than critical when exploitation requires non-trivial wrapping variants.
- **JWT alg confusion on a downstream RP** — relying party rather than IdP accepts `alg:none` or HMAC-with-public-key; severity tracks the RP's blast radius. Cross-cutting RP-hardening guidance, not the IdP's exclusive concern, but the IdP-issued tooling and SDK posture drives the outcome.
- **Brute force / password spray without rate-limit + lockout** — credential-stuffing surface open. The OWASP API Top 10 calls this out as API4 (Unrestricted Resource Consumption) on the most-abused identity surface. NIST SP 800-63B §5.2.2 requires throttling.
- **Refresh token replay without proof-of-possession or rotation** — refresh tokens long-lived, bearer-only, no rotation-with-reuse-detection, no DPoP/mTLS binding. A stolen refresh token grants the attacker the lifetime of the token plus all subsequent rotations.
- **Privilege escalation via group/role mapping bug** — federation attribute mapping, JIT-provisioning logic, or claim-transformation expression permits a user to declare or influence their own group membership (self-attestable `groups` claim accepted, mapping expression with operator precedence flaw, attribute-collision yielding admin-group membership).
- **OAuth dynamic client registration without rate-limit or identity proofing** — open or weakly-gated client registration permits attacker-registered clients with attacker-controlled redirect_uri, enabling malicious-RP attacks against any user who can be lured to /authorize for the attacker's client_id.
- **Mass-assignment on user profile / consent surface** — self-service profile-edit accepts writes to `is_admin`, `groups`, `roles`, `email_verified`, or `mfa_enrolled` fields that should be server-managed. The mass-assignment class on the IdP itself is high-trending-critical.
- **Audit gap on token issuance, MFA enrollment, or consent grant** — partial loss of the consequential-action fact base. The merged finding with any Non-Repudiation gap on the same event class commonly escalates to critical.
- **Cross-tenant token bleed** — multi-tenant IdP issues a token with one tenant's scope that decodes against another tenant's audience, or a session cookie scoped too broadly (parent-domain Cookie with tenant subdomains).
- **Service account token long-lived and unrotated** — non-human identities authenticating to the IdP backend via static credentials (LDAP bind, SMTP, database, vendor APIs). The IdP's own backend-credential hygiene is in scope because IdP-tier compromise pivots outward.

## Medium

Any of the following:

- **Missing rate-limit on credential-recovery endpoints** — password-reset request, MFA recovery, recovery-code regeneration, email-change-confirmation. Severity escalates to high if combined with weak email-channel trust or absent re-authentication on the receiving end.
- **Session lifetime exceeds policy without justification** — absolute session > 24h without step-up, refresh-token lifetime > 30 days without rotation discipline, OAuth `offline_access` grants with no expiry.
- **OAuth client registration without strong identity proofing** — manual review present but human-only, no domain-control validation for redirect_uri host, no contact attestation. The compensating control exists but is human-velocity.
- **Misconfigured CORS on token endpoint** — token endpoint should generally not need CORS at all (browser-to-token is not the OAuth contract for public clients in OAuth 2.1); permissive ACAO on /token is a finding even if not directly exploitable.
- **Missing audit on OAuth client registration changes** — administrative-tier audit gap on the federation-trust surface; cross-references Non-Repudiation and Immutability findings on the consent/grant table.
- **Recovery flow weaker than primary login** — primary login enforces AAL2 with WebAuthn, recovery flow accepts email-only knowledge factor. The attacker takes the weakest path; recovery weakness silently downgrades the primary AAL claim.
- **Verbose error messages on /authorize or /token** — error responses differentiate "unknown client_id" vs. "invalid redirect_uri" vs. "unknown user," enabling enumeration.
- **Anonymous LDAP bind permitted by upstream directory** — IdP-to-directory boundary accepts unauthenticated reads; medium because typically the IdP itself enforces bind, but the latent posture is a finding.
- **Defense-in-depth gap on signing-key access** — signing key in HSM/KMS but the wrapping-key access is broad (every IdP pod can decrypt); the inner layer is strong but the outer layer is single-credential.
- **Weak password policy on non-admin surfaces** — minimum length below NIST SP 800-63B §5.1.1.2 guidance (8 chars min, 64 max permitted), no breached-password check via HIBP-style API, password complexity rules instead of length-and-uniqueness.
- **SAML metadata mutable without re-attestation** — federation-trust metadata can be edited inline by tenant admins without an approval workflow or re-attestation of the SP's identity.

## Low

Any of the following:

- **Hygiene issue with no realistic exploit path** — deprecated TLS cipher with no client population that requires it, redundant audit redaction overlapping a stronger upstream filter, verbose Server header on the IdP edge.
- **Documentation deficiency** — SAML metadata XML drift from federation-partner contract on a non-security-critical attribute, OAuth scope documentation lag, runbook formatting drift.
- **Defense-in-depth gap fully compensated by upstream controls** — useful to know but architecturally non-urgent.
- **Configuration drift on non-production realms** — sandbox tenants, ephemeral test realms, dev IdP instances without production credential mirror.

## Informational

Observations that do not rise to remediation but are worth surfacing for the architecture record. Used sparingly. Examples: notable architectural choices with security implications worth documenting (chosen JWT library and its alg-pinning posture, chosen OAuth library and its PKCE default, chosen federation topology — hub-and-spoke vs. mesh), parity gaps with industry peers that are not actually risks, NIST 800-63 / OAuth 2.1 capabilities the system meaningfully addresses that the specialist should record as a confirmed capability rather than a finding.

---

## Severity calibration discipline

- **Cite the rubric clause in `detail`.** "This is high severity because it falls under 'Privilege escalation via group/role mapping bug' per the identity security rubric, specifically because the `attributes.groups` claim from the upstream IdP is mapped through an expression that uses string concatenation with a user-controllable `email_domain` field."
- **Cite the matching NIST 800-63B AAL / 800-63C FAL clause** when the finding turns on assurance-level mismatch. Multiple anchors may apply — cite the OAuth/OIDC Security BCP section and the NIST clause together when an OAuth flow weakens an AAL claim.
- **Cite the SAML XSW class explicitly when applicable.** "This matches SAML 2.0 Security Considerations §6.3 (signature wrapping); the assertion is signed but the signature-validation library returns the parsed inner assertion after validating an outer envelope."
- **Do not average across multiple impacts.** A finding that yields signing-key exposure AND has a partial-rotation runbook is critical (signing-key exposure dominates).
- **Do not inflate to signal importance.** The synthesizer escalates and reconciles severity disagreements between agents; over-claiming on one agent degrades cross-agent reconciliation signal.
- **When in doubt, drop one level.** A high-confidence medium is more useful than a low-confidence high. The synthesizer can escalate based on cross-lens corroboration; it cannot reliably de-escalate a confidently-asserted critical.
- **Distinguish capability from exploited.** The rubric scores realistic attack capability, not whether exploitation has been observed. An undisclosed authentication bypass and an actively-exploited one are both critical.
- **AAL/FAL downgrade is the dominant high-severity pattern.** Anchor every authentication-related finding to the AAL/FAL claim the surface is meant to meet; the gap between target AAL/FAL and effective AAL/FAL is the severity dial.

## Source: `consequential-actions.md`

# Identity security consequential-action surface

For an identity provider issuing tokens, assertions, and session credentials to downstream relying parties, the following actions are consequential and must be auditable. Non-Repudiation findings evaluate logging coverage against this list; gaps become findings against AU-2 (Auditable Events) and against NIST SP 800-63B §5.2.2 on event recording.

## Authentication events

- Authentication success (interactive, machine-to-machine via client_credentials, federated via upstream IdP, device-flow user approval)
- Authentication failure with reason categorization (bad password, unknown user, locked, expired, MFA required, MFA failed, AAL-policy denial)
- MFA challenge issued, MFA succeeded, MFA failed, MFA bypass via recovery code (the bypass event is the high-value audit anchor)
- WebAuthn assertion issued, WebAuthn signature counter incremented (counter-reset is a finding signal)
- Account lockout, lockout-reset, lockout-override (admin override is distinct event)
- Step-up authentication (re-authentication for sensitive operations; AAL elevation events distinct from initial auth)
- Account-recovery initiation and completion (separately — token-issuance event linked to completion event)
- Anomalous authentication (impossible travel, new-device, new-geography, after-hours) when risk-scoring is in path

## Authorization decisions

- Allow and deny decisions on consequential operations (every decision, not just denials)
- Privilege escalation (role assignment, role removal, group-membership change — including JIT-provisioning-driven mutations from upstream IdP attributes)
- Session privilege elevation (step-up to admin scope, sudo-equivalent, break-glass)
- Policy evaluation outcomes when the policy engine is the trust anchor (e.g., OPA, Cedar, or the IdP's native rule engine)
- Scope evaluation on token issuance (which scopes were requested, which were granted, which were denied)

## Token lifecycle

- Access-token issuance (with the token identifier — jti when JWT, opaque token ID otherwise — and the client_id, audience, scope set, AAL claim, and FAL claim captured)
- Refresh-token issuance (token-family identifier captured; refresh-token rotation chain trackable)
- ID-token issuance (with subject identifier, audience, nonce, and the claims released)
- Token refresh (linking the inbound refresh-token identifier to the outbound new access-token identifier)
- Token revocation (user-initiated logout, administrative revocation, automatic revocation on credential change, refresh-token reuse-detected family revocation)
- Token introspection request (per RFC 7662; the introspection event itself is consequential)
- Token expiry (idle timeout, absolute timeout, scope-driven expiry)
- DPoP / mTLS-bound token issuance (the binding metadata is auditable)

## OAuth and OIDC events

- User consent grant (with the scope set, the relying-party identifier, the user identifier, and the lifetime)
- Consent revocation (separate event from grant)
- Authorization-code issuance and exchange (linkable; the code's identifier captured at both events)
- Scope change on existing grant (incremental authorization)
- OAuth client registration (whether dynamic per RFC 7591 or administrative)
- OAuth client modification (any change to redirect_uri allowlist, scope allowlist, client authentication method, or grant-type allowlist — the federation-trust surface)
- OAuth client deletion
- Client-credentials grant issuance (machine-to-machine token issuance)
- Device-authorization grant initiation and user-approval (RFC 8628)
- Backchannel authentication request (CIBA, RFC 9126)
- Token-exchange request (RFC 8693 — including the actor/subject claim relationship)

## SAML events

- SAML assertion issuance (with assertion_id, audience SP entity ID, subject NameID, attribute set released, signing-key kid)
- SAML attribute-release event (per-SP attribute disclosure — privacy-relevant audit)
- IdP-initiated SSO event (unsolicited response to SP)
- SP-initiated SSO event (AuthnRequest received, validated, responded)
- Single Logout (SLO) initiation and completion across all federated SPs
- SAML assertion-ID reuse rejection (replay-prevention store hit — itself a high-value security event)

## Account lifecycle

- Account creation (with the provisioning channel: self-service, admin-created, JIT from upstream IdP, SCIM-provisioned)
- Account deletion (with the deletion channel and the retention policy applied to associated audit/consent records)
- Account suspension, reactivation
- Identity-proofing upgrade (NIST SP 800-63A IAL elevation event — e.g., from IAL1 self-assertion to IAL2 with verified attributes)
- Email-change and email-verification events (separately; the verification event is the trust-elevation anchor)
- Phone-change and phone-verification events

## Credential lifecycle

- Password change (by user, by admin, via password-reset flow — three distinct actor classes)
- Password-reset request and password-reset completion (separately, linkable)
- MFA enrollment (per-factor; new factor added)
- MFA removal (per-factor; factor de-registered)
- WebAuthn credential registration and deregistration
- Recovery-code regeneration (the old set invalidated event distinct from new set issued)
- TOTP seed rotation

## Federation events

- IdP-to-SP trust establishment (federation onboarding — admin-tier action, high-blast-radius)
- IdP-to-SP trust modification (signing-key rotation, encryption-key rotation, attribute-release-policy change, NameID format change)
- IdP-to-SP trust deletion (federation offboarding)
- Upstream-IdP registration (this IdP acting as SP to a peer)
- Attribute-mapping rule change (JIT-provisioning expression edit)
- SCIM-target binding change

## Administrative actions

- Role definition change (role created, permission added/removed, role deleted)
- Policy modification (RBAC policy, ABAC policy, OPA bundle push, the IdP's native expression-language policy)
- Signing-key rotation (the rotation event itself plus the JWKS-publication event)
- Signing-key revocation (with the affected window for after-the-fact verification)
- Audit-pipeline configuration change (sink, retention, schema, redaction policy)
- Rate-limit policy change
- Feature flag toggle on any security-relevant flag (alg allowlist, MFA enforcement, AAL policy, consent UX)
- TLS configuration change (cipher suite, version floor, certificate)
- Email/SMS provider change (the recovery-channel substrate)

## Data-subject rights events (GDPR Articles 15–22)

- Access request (Article 15) — receipt, response, and the data provided
- Erasure request (Article 17 "right to be forgotten") — receipt, response, retention-conflict resolution, the records affected including audit trail of the deletion
- Portability request (Article 20) — receipt, response, the export delivered (token-history, consent-history, identity-attribute set)
- Restriction of processing (Article 18), objection (Article 21), automated-decision objection (Article 22)
- Consent withdrawal (cross-cuts the OAuth consent-revocation event above; the GDPR-anchored audit record may be a distinct view)

## Break-glass and emergency actions

- Break-glass authentication (with justification captured; routes to a distinguishable audit stream)
- Emergency policy override (the policy bundle change captured)
- Emergency credential rotation (mass signing-key rotation, mass session invalidation, mass MFA reset)
- Disaster-recovery failover initiation
- Audit-pipeline emergency reroute (failover to backup sink)

This list is not exhaustive. Specialists should treat actions outside this list as candidates for inclusion — flagging them as evidence gaps until the operator confirms whether the action is in scope for auditing. The IdP's audit surface is the most evidentiary in the platform: every regulator presumes it works, and every breach investigation starts here.

## Source: `immutability-classes.md`

# Identity security required-immutable data classes

For an identity provider issuing tokens and assertions to downstream relying parties, the following data classes must not change once written. Immutability findings test storage substrate, retention enforcement, and deletion controls against this list.

- **Authentication event log** — credential-compromise reconstruction depends on a tamper-evident authn record. NIST SP 800-92 retention guidance applies; PCI-DSS Requirement 10.7 (where in scope) requires 1 year online + 1 year archive; SOC 2 typically 1–7 years per service-organization policy; FedRAMP Moderate per agency baseline. Retention floor must match or exceed the longest plausible breach-detection window.
- **Authorization decision log** — proof of who was permitted what at time T. Required for SOC 2 CC6.3 control attestation and for GDPR Article 5(2) accountability defense. Loss converts every authorization-bug claim into "we cannot verify."
- **Consent grant records (OAuth/OIDC and SAML attribute-release acknowledgements)** — GDPR Article 6(1)(a) lawful-basis evidence for the processing that occurred during the consent window. Consent withdrawal must be recorded as a new event, never as overwriting the prior grant. The proof-of-prior-consent obligation outlives the grant itself.
- **Token issuance log** — per-token audit anchor: JWT `jti` deduplication, refresh-token rotation-chain tracking, ID-token nonce recording. Required for after-the-fact "which key signed which token at what time" verification when investigating signing-key compromise. The audit must outlive the longest token lifetime issued during the window.
- **Cryptographic key lifecycle records** — key creation, rotation, revocation, and destruction events. Required for proving NIST SP 800-63B §5.1.4 key-management discipline, PCI-DSS Requirement 3.6 / 3.7, SOC 2 CC6.7, and FedRAMP SC-12 control attestation. The JWKS rotation history specifically must be queryable for after-the-fact assertion validation.
- **SAML assertion log and assertion-ID replay store** — replay prevention requires recording every assertion ID seen within the assertion's NotOnOrAfter window. The replay-prevention store is immutable-during-window by design; the audit copy of "this assertion ID was issued at time T" is immutable beyond the window for compromise reconstruction.
- **Backup snapshots** — ransomware resilience for the credential store, the session store, the consent store, the audit log, and the key-lifecycle records. Immutability via object-lock (compliance mode), WORM media, or write-locked tape. Mutability or deletion-by-single-credential is a critical finding because the IdP backup is the post-breach recovery anchor for every dependent application.
- **Configuration history** — RBAC policy changes, ABAC policy changes, federation-trust changes (signing-key rotation, attribute-release-policy mutation, redirect_uri allowlist edits), audit-pipeline configuration. Required for root-cause analysis after authorization-bug incidents and for SOC 2 CC8.1 change-management evidence.
- **Identity-proofing artifacts** — NIST SP 800-63A IAL3 in-person verification records, IAL2 attribute-verification records (driver's-license image, attribute-source attestation). Required for proving the IAL claim that the IdP asserts to downstream RPs.
- **Federation-trust establishment records** — the human approval trail for SP/IdP onboarding, the metadata-validation evidence, the contact attestation. Required for post-compromise attribution if a federated party turns out to be malicious or compromised.
- **Account-deletion records** — proof of GDPR Article 17 compliance. The deletion event itself is immutable; the deleted-account audit trail is retained per the longest applicable retention even after the account row is gone (pseudonymized record-of-deletion).

Specialists raise Immutability findings against any class on this list that has mutable storage, absent retention controls, deletion-by-single-credential, or unspecified retention. The synthesizer cross-references Non-Repudiation findings on the same data class so the merged record carries both concerns. Audit-tampering plus audit-completeness gaps merge into a critical finding under almost every regulatory anchor.

## Source: `data-taxonomy.md`

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

## Source: `common-patterns/confidentiality.md`

# Identity security common patterns — Confidentiality

These are illustrative templates, not all-inclusive. Use them to calibrate analytical style, severity assignment per the identity security rubric, and NIST/ATT&CK mapping habits. The specialist agent's analytical checklist still drives the actual analysis — this file calibrates how findings and capabilities should look once written.

## Common finding patterns

**Pattern: Token signing key stored in application configuration (env var, mounted Secret, on-disk PEM) rather than HSM/KMS.**

- Severity: critical (signing-key compromise yields universal token forgery — see Critical rubric clause on token signing key compromise)
- NIST: SC-12, SC-12(1), SC-12(3), SC-13, SC-28, SC-28(1)
- ATT&CK: T1552.001 (Credentials in Files); T1606.001 (Forge Web Credentials: Web Cookies); T1606.002 (Forge Web Credentials: SAML Tokens)
- Related concerns: authenticity (the signing key IS the identity assertion trust anchor), ephemeral (key rotation cadence and revocation channel), immutability (key-lifecycle event log)

**Pattern: Password hash algorithm weaker than argon2id / bcrypt with appropriate cost (PBKDF2 below 600k iterations, SHA-512crypt, plain SHA-256, MD5).**

- Severity: high to critical depending on the hash strength and the user-population value (critical when the population would be targeted for credential stuffing across high-value external surfaces)
- NIST: IA-5, IA-5(1)(c), SC-13
- ATT&CK: T1110.002 (Brute Force: Password Cracking); T1003 (OS Credential Dumping) for the hash-extraction precondition
- Related concerns: ephemeral (rotation on algorithm change requires forced password reset), non_repudiation (audit completeness on hash-algorithm migrations)

**Pattern: Refresh tokens stored as cleartext on the IdP side rather than hashed-at-rest.**

- Severity: high (refresh-token store dump is equivalent to long-lived session impersonation for every active user; hashing-at-rest is the proportional control)
- NIST: SC-28, SC-28(1), IA-5
- Related concerns: ephemeral (refresh-token rotation cadence collapses the cleartext-storage window), integrity (hash verification must be constant-time)

**Pattern: SAML assertion encryption absent on attribute-release flows that carry personal data or special-category data.**

- Severity: medium to high (assertion contents visible to any TLS-terminating intermediary, MitM with weak validation, or RP-side log aggregator; SAML Security Considerations §6.2 recommends encryption for sensitive attribute release)
- NIST: SC-8, SC-8(1), SC-12, AC-4
- Related concerns: authenticity (the assertion signature does not protect confidentiality), integrity (JWE/XML-Encrypt configuration affects parser surface)

**Pattern: JWT access tokens or ID tokens carry excessive PII claims — full profile embedded.**

- Severity: medium to high depending on token lifetime, audience scope, and which claims (a 1-hour bearer token carrying email, full name, DOB, employee ID exposes that PII to every downstream RP, log aggregator, proxy, and APM in the request path)
- NIST: SC-8, AC-4, SC-28, AU-11
- Related concerns: ephemeral (token-lifetime amplifies claim exposure), integrity (over-broad claims defeat least-privilege downstream)

**Pattern: Recovery channel (email, SMS) carries the recovery token in cleartext URL parameters.**

- Severity: high (recovery URL appearing in browser history, referer headers, mobile-app interception, mail-server logs, MTA bounce traces; recovery token is single-use-takeover material)
- NIST: SC-8, IA-5, SI-11 (error handling — URL-in-log behavior)
- Related concerns: ephemeral (recovery token lifetime), authenticity (recovery-flow identity-proofing strength)

**Pattern: LDAP/AD bind credentials in IdP application config without rotation, audit-on-fetch, or read-only enforcement.**

- Severity: medium to high depending on bind privilege (read-only bind is medium; bind permitting writes is high)
- NIST: IA-5, IA-5(1), AC-2, SC-12
- ATT&CK: T1078.002 (Valid Accounts: Domain Accounts); T1552 (Unsecured Credentials)
- Related concerns: ephemeral (rotation cadence), authenticity (directory-backend trust)

**Pattern: Tech plan describes "encryption at rest" generically without specifying which crown-jewel classes, KMS/HSM topology, key separation between primary store and backups, or DEK/KEK hierarchy.**

- Disposition: blocked or uncertainty
- prerequisite_evidence: "Encryption-at-rest policy — per-crown-jewel-class encryption posture (signing keys, password hashes, MFA seeds, session store, audit log, backups), KMS/HSM topology, DEK/KEK hierarchy, key-separation discipline between primary store and its backup, rotation cadence per key class, and the audit-on-decrypt control"

## Common capability patterns

**Pattern: Token signing keys held in HSM/KMS (PKCS#11 or cloud KMS) with the IdP holding only key handles; sign-operations go to the HSM.** Maturity ladder: `designed` from tech plan; `implemented` requires HSM/KMS provider evidence; `tested` requires evidence of forced rotation; `operationalized` requires alerting on signing-key-access anomalies.

**Pattern: Password hashes stored with argon2id at parameter set tuned to the threat model (memory cost, time cost, parallelism documented).** Capability scope must state the parameters and the migration discipline for legacy weaker-hash records (rehash-on-login pattern).

**Pattern: Refresh tokens stored as hashes (SHA-256 of token value plus per-token salt) with constant-time comparison on validation.** Higher maturity requires evidence that token-rotation-on-use is paired with reuse-detection.

**Pattern: JWE for sensitive ID-token claims, SAML assertion encryption for personal-data attribute release.** Cross-cuts Authenticity for the encryption-key trust chain.

**Pattern: PII minimization in token claims — tokens carry subject identifier and authorization scope only; full profile resolved via /userinfo on demand.** Capability scope should enumerate which claims are released by issuer policy and which are guarded behind /userinfo.

**Pattern: Recovery channels deliver short-lived single-use tokens via a separate confirmation step (token in email body must be re-entered, not clicked) to avoid URL-leak channels.** Higher maturity requires evidence that recovery completion requires a step-up to AAL2 minimum.

## Source: `common-patterns/integrity.md`

# Identity security common patterns — Integrity

These are illustrative templates, not all-inclusive. Use them to calibrate analytical style, severity assignment per the identity security rubric, and NIST/ATT&CK mapping habits. The specialist agent's analytical checklist still drives the actual analysis — this file calibrates how findings and capabilities should look once written.

## Common finding patterns

**Pattern: JWT signature verification accepts multiple algorithms by default; algorithm pinning absent (the library's allowlist is the union of all configured signers' algorithms).**

- Severity: critical when `alg:none` is reachable or HS256 verification is permitted against an RS256-issued token using the JWKS public key as the HMAC secret (the canonical RS256/HS256 confusion attack); high when the alg allowlist is broader than the issuing alg.
- NIST: SI-7, IA-2, IA-5(2), SC-13
- ATT&CK: T1606.001 (Forge Web Credentials: Web Cookies); T1550.001 (Use Alternate Authentication Material: Application Access Token)
- Related concerns: authenticity (the alg pin IS the token trust anchor), confidentiality (key-confusion turns a public key into a forgery oracle)

**Pattern: SAML signature verification susceptible to signature wrapping (XSW) — the validation library returns the parsed inner element after validating an outer envelope; the SP/IdP processes the inner element without re-verifying it is the signed region.**

- Severity: critical (arbitrary subject impersonation — see Critical rubric clause on SAML XSW)
- NIST: SI-7, SI-10, SC-13
- ATT&CK: T1606.002 (Forge Web Credentials: SAML Tokens)
- Related concerns: authenticity (the signature is the federation trust anchor), non_repudiation (XSW destroys assertion attribution)

**Pattern: JWKS rotation grace window unspecified — the verifier flips from old kid to new kid without overlap, producing a window during which in-flight tokens fail verification.**

- Severity: medium to high (availability impact during rotation; security risk when operators are tempted to extend old-kid lifetime to recover, defeating revocation discipline)
- NIST: SC-12, SC-12(2), SI-7, AU-12
- Related concerns: availability (rotation-window outage), ephemeral (rotation cadence), immutability (JWKS rotation history)

**Pattern: OAuth `state` parameter not validated, not bound to session, or omitted entirely on the authorization-code callback.**

- Severity: high (CSRF on OAuth authorization flow — RFC 9700 §4.7)
- NIST: SI-10, IA-2, AC-3
- ATT&CK: T1606 (Forge Web Credentials)
- Related concerns: authenticity (state binds the flow to the user agent), availability (CSRF can be used to fixate sessions)

**Pattern: OIDC nonce / c_hash / at_hash validation skipped — the ID token is accepted without binding to the authorization request or the issued access token.**

- Severity: high (token substitution attacks — an attacker-procured ID token from another user can be played to the RP if the nonce is not validated)
- NIST: SI-10, IA-2, SI-7
- Related concerns: authenticity (the nonce is the user-agent-to-ID-token binding)

**Pattern: SAML assertion-ID uniqueness store absent or insufficient retention — the SP/IdP cannot detect assertion replay within the NotOnOrAfter window.**

- Severity: high (assertion replay attacks — SAML 2.0 Security Considerations §6.4)
- NIST: SI-7, IA-2, SC-23, AU-12
- Related concerns: ephemeral (assertion lifetime tightening reduces the replay window), immutability (the assertion-ID store is itself an immutable-during-window class)

**Pattern: Idempotency missing on token-revocation endpoint — double-submit of revoke produces different observable outcomes (200 vs. 404 differential exposes which tokens were valid).**

- Severity: medium (information leak about token state; primary concern is the differential)
- NIST: SI-10, SC-5, AU-12
- Related concerns: availability (retry storms on revocation), non_repudiation (revocation event audit)

**Pattern: Mass-assignment on the user profile / self-service endpoint accepts writes to `is_admin`, `groups`, `roles`, `email_verified`, `mfa_enrolled`, or `email` without server-managed-field enforcement.**

- Severity: high to critical (writing `is_admin` is critical privilege escalation; writing `email` without re-verification enables account-recovery hijack; writing `email_verified=true` bypasses the verification gate)
- NIST: SI-10, AC-3, AC-6, AU-2
- ATT&CK: T1078 (Valid Accounts); T1098 (Account Manipulation); T1556 (Modify Authentication Process)
- Related concerns: authenticity (privilege-relevant fields enabling identity forgery), non_repudiation (mutation audit)

**Pattern: Federation attribute-mapping expression vulnerable to operator-precedence or string-concatenation injection — upstream claim `email_domain` is interpolated into a group-mapping rule string without parsing discipline.**

- Severity: high (privilege escalation via group/role mapping bug — see High rubric clause)
- NIST: SI-10, AC-3, AC-6
- ATT&CK: T1098 (Account Manipulation)
- Related concerns: authenticity (the claim-transformation is the federation trust chain in practice)

**Pattern: Tech plan describes "input validation" generically without specifying which claim/attribute fields, what schema, what error handling, and what behavior on schema-fail in the federation-claim ingestion path.**

- Disposition: blocked or uncertainty
- prerequisite_evidence: "Federation-claim ingestion specification — per-upstream-IdP claim allowlist, transformation expression language and its security posture, behavior on missing required claim, behavior on excess unrecognized claim, behavior on claim-type mismatch, and the audit anchor on transformation rule changes"

## Common capability patterns

**Pattern: JWT verification with explicit algorithm pin per issuer and explicit kid pin per JWKS rotation generation.** Capability scope: enumerate which RPs and which internal verifiers are confirmed; library defaults are typically the failure mode.

**Pattern: SAML signature validation using XSW-resistant library (e.g., python3-saml, OneLogin SAML toolkits in current versions) with the canonical-region re-verified against the parsed assertion.** Maturity tied to the library version and the explicit re-verification step in code review evidence.

**Pattern: OAuth state, nonce, c_hash, and at_hash all validated; PKCE enforced on every client class.** Higher maturity requires evidence that the validation is library-default-on rather than opt-in.

**Pattern: SAML assertion-ID replay store backed by a TTL-keyed cache with TTL ≥ assertion NotOnOrAfter window; replay events audited.** Cross-cuts Non-Repudiation and Immutability.

**Pattern: Server-managed-field allowlist on user profile mutations; the framework strips writes to `is_admin`, `groups`, `roles`, `email_verified` regardless of client input.** Capability scope must state whether the allowlist is centralized (framework-level) or per-endpoint (drift risk).

**Pattern: Federation claim-transformation rules expressed in a sandboxed, side-effect-free DSL with explicit allowlist of operations; transformation-rule changes require admin-tier approval and audit.** Higher maturity when changes go through GitOps with signed commits.

## Source: `common-patterns/availability.md`

# Identity security common patterns — Availability

These are illustrative templates, not all-inclusive. Use them to calibrate analytical style, severity assignment per the identity security rubric, and NIST/ATT&CK mapping habits. The specialist agent's analytical checklist still drives the actual analysis — this file calibrates how findings and capabilities should look once written.

## Common finding patterns

**Pattern: No rate limit on /authorize, /token, password-grant, MFA-challenge, MFA-enrollment, or credential-recovery endpoints.**

- Severity: high (credential stuffing, password spray, MFA fatigue / push bombing, and account-takeover surfaces all open). Escalates to critical when paired with weak password policy, absent breached-password check, or absent CAPTCHA fallback.
- NIST: SC-5, SC-5(1), SC-5(2), AC-7 (unsuccessful login attempts), IA-5
- ATT&CK: T1110 (Brute Force) and sub-techniques T1110.001 (Password Guessing), T1110.003 (Password Spraying), T1110.004 (Credential Stuffing); T1621 (Multi-Factor Authentication Request Generation)
- Related concerns: authenticity (the credential-policy half), non_repudiation (failed-auth audit completeness)

**Pattern: Session-store backpressure absent — Redis/PostgreSQL session store can be saturated by authentication storm, taking the entire IdP offline.**

- Severity: high (session-store DoS is the dominant IdP-availability failure mode; saturation cascades to every dependent application losing auth)
- NIST: SC-5, SC-6 (resource availability), SI-13
- Related concerns: distributed (session-store topology), resilient (degraded-mode auth)

**Pattern: Queue depth unbounded on the authentication-flow pipeline (async event publication on authn events, async session-write, async audit-emit).**

- Severity: medium to high (queue saturation produces silent loss of either audit, session state, or downstream provisioning — all three are different findings depending on which queue is saturated)
- NIST: AU-4, AU-5, SC-5, SI-13
- Related concerns: non_repudiation (audit queue), distributed (queue topology)

**Pattern: No degraded-mode authentication specified — if the credential-verification path (LDAP, database, upstream IdP) is unavailable, the IdP returns 500 to every request.**

- Severity: high (cascading total outage; IdP is the topmost availability dependency for every RP — no graceful fallback path defined)
- NIST: CP-12, CP-13, SI-13, IA-2
- Related concerns: resilient (this finding's recommendation overlaps the IdP-outage degradation pattern in Resilient), distributed (backend topology)

**Pattern: Single-region IdP deployment with a 99.9%+ availability target asserted to downstream RPs.**

- Severity: high (target undeliverable from a single region under typical cloud-provider zone SLA; the IdP becomes the platform's lowest-SLO dependency)
- NIST: CP-7, SC-36, CP-9
- Related concerns: distributed (multi-region topology), resilient (failover orchestration)

**Pattern: Signing-key availability vs. latency tradeoff unaddressed — HSM in one region, IdP serves traffic from three; signing-operation latency drives p99 token-issuance latency through the floor.**

- Severity: medium to high depending on token-issuance SLO (high when sub-second p99 is asserted)
- NIST: SC-12, SC-12(3), CP-7
- Related concerns: distributed (HSM topology), resilient (caching of recent signatures is rarely safe — the tradeoff is regional HSMs)

**Pattern: Health checks on the IdP are shallow — TCP-port check or basic HTTP 200, not "can sign a test token" / "can verify a test password" / "can reach LDAP backend."**

- Severity: medium (shallow health checks mask backend degradation; load balancer continues routing to instances that cannot complete auth)
- NIST: SI-13, CP-10
- Related concerns: resilient (health-check is the input to circuit-breaker decisions)

**Pattern: Tech plan describes "rate limiting" generically without specifying per-endpoint thresholds, identity dimension, time window, or behavior on breach.**

- Disposition: blocked or uncertainty
- prerequisite_evidence: "Rate-limit policy specification — per-endpoint thresholds for /authorize, /token, password-grant, MFA-challenge, recovery endpoints; identity dimension (per-user, per-client_id, per-IP, per-tenant); time window; behavior on breach (reject vs. queue vs. CAPTCHA escalation vs. lockout); retry-after semantics; and any compensating bot-management layer"

## Common capability patterns

**Pattern: Per-endpoint rate limits with identity-dimensioned thresholds, separate limits per IP and per identity, explicit behavior on breach.** Capability scope must enumerate covered endpoints; all credential-touching surfaces in the consequential-actions list must appear in scope or the capability degrades to a partial-coverage finding.

**Pattern: Externalized session store with horizontal scale and backpressure (Redis Cluster with maxmemory-policy noeviction on session keys, plus circuit-breaker on writes).** Higher maturity when chaos-engineering evidence shows the IdP survives session-store partial unavailability.

**Pattern: Degraded-mode authentication: read-only auth using cached session tokens when backend directory is unavailable, with explicit user notification.** Cross-cuts Resilient; mention via `related_concerns`. Maturity ladder requires a documented runbook plus tested failover.

**Pattern: Multi-region IdP topology with regional HSMs, regional session stores, and active-active token issuance.** Higher maturity requires evidence of cross-region session replication policy, regional-failover RTO/RPO targets, and audit-pipeline cross-region durability.

**Pattern: SLO and error-budget framework with separate SLOs for /authorize, /token, /userinfo, and SAML SSO endpoints; burn-rate alerting wired to oncall.** `designed` from tech plan; `implemented` requires monitoring configuration; `operationalized` requires evidence of error-budget-driven engineering decisions.

## Source: `common-patterns/distributed.md`

# Identity security common patterns — Distributed

These are illustrative templates, not all-inclusive. Use them to calibrate analytical style, severity assignment per the identity security rubric, and NIST/ATT&CK mapping habits. The specialist agent's analytical checklist still drives the actual analysis — this file calibrates how findings and capabilities should look once written.

## Common finding patterns

**Pattern: Single-AZ deployment of the IdP application tier, the session store, or the signing-key backend (HSM/KMS).**

- Severity: high (the single AZ is the failure domain for the entire platform's authentication; a zonal incident produces total auth outage for every downstream RP)
- NIST: SC-7, CP-7, SC-36
- Cross-reference: any Availability finding on SLO consistency; the merged finding carries both the topology constraint and the SLA consequence

**Pattern: Session-store replication lag affects MFA-challenge consistency — user MFA-enrolls in region A, immediately authenticates in region B, MFA-required flag has not propagated.**

- Severity: medium to high (security-relevant inconsistency; the user can briefly bypass MFA via region race; severity escalates when the inconsistency window exceeds typical authentication latency)
- NIST: SC-36, SI-7, IA-2(1)
- Related concerns: authenticity (MFA enforcement consistency), resilient (region-failover behavior)

**Pattern: CAP positioning for credential changes unspecified — when network partitions split the IdP topology, the artifacts do not specify whether the system prefers consistency (reject auth on minority partition) or availability (accept auth on minority partition with stale credentials).**

- Disposition: blocked
- Severity: medium when blocked, high when "availability wins" is documented without compensating controls
- prerequisite_evidence: "Multi-region consistency policy for credential mutations — behavior of password changes, MFA-enrollment changes, and account-suspension during a partition; replication-conflict resolution policy; tombstone propagation for account deletion under partition"

**Pattern: Data residency for personal data unstated — artifacts describe multi-region capability without specifying which user populations or tenants are bound to which regions.**

- Disposition: uncertainty or blocked
- prerequisite_evidence: "Data-residency policy — per-tenant region binding, lawful-basis attestation for any cross-EEA flow (SCCs, adequacy decision, BCRs), residency-enforcement mechanism (application-tier routing, database-level constraints), and the audit-log residency posture (does EU-user audit stay in EU?)"

**Pattern: Multi-region topology asserted but failover behavior unspecified — active-active vs. active-passive vs. standby, write-conflict policy on the credential store, failover trigger, RTO/RPO targets.**

- Disposition: uncertainty or blocked
- Severity: medium when blocked
- prerequisite_evidence: "Multi-region topology specification — active configuration, write-conflict policy for the credential store and the session store, failover trigger, expected failover RTO/RPO per data class, and which data classes replicate cross-region (audit yes; credentials yes; ephemeral PKCE state typically no)"

**Pattern: Cross-region replication for the audit log is asynchronous with unspecified lag.**

- Severity: medium to high (cross-references Non-Repudiation; audit gap during regional failover is a breach-detection blind spot — and the IdP's audit is the highest-stakes audit on the platform)
- NIST: AU-9(2), SC-36
- Related concerns: non_repudiation, immutability

**Pattern: Session affinity / sticky sessions on the IdP load balancer because state is in-process (interactive auth flow state cached in pod memory).**

- Severity: medium to high (impairs horizontal scale, deploy-time rolling restarts produce mid-flow session loss, AZ failover invalidates all in-flight authentications)
- NIST: SC-7, CP-7, SC-36
- Related concerns: ephemeral (in-process state undermines the immutable-infra story)

**Pattern: Service mesh topology unspecified — artifacts assert mTLS between IdP components without describing workload-identity issuance, certificate rotation, or trust-domain boundary between the IdP namespace and other namespaces.**

- Disposition: uncertainty
- prerequisite_evidence: "Service-mesh topology — workload identity issuance (SPIFFE/SPIRE, cloud-native), trust-domain boundary between IdP namespace and adjacent service namespaces, certificate lifetime and rotation cadence, mesh-to-non-mesh edge behavior (legacy LDAP backend not in mesh)"

## Common capability patterns

**Pattern: Multi-region active-active IdP with regional HSMs, regional session stores, and stateless application tier.** Capability scope must specify which dependencies are also multi-region (credential store, audit pipeline, federation-trust store) and which are single-region by design.

**Pattern: Region-pinned credential storage with explicit cross-region replication policy and per-tenant residency binding.** Higher maturity requires evidence of the policy enforcement mechanism (database-level residency, application-tier routing) plus residency monitoring on egress.

**Pattern: Session-store replication topology documented with replication-lag SLO and MFA-consistency rule (e.g., "MFA-enrollment writes are synchronously replicated to the user's home region before /authorize returns").** Cross-cuts Authenticity.

**Pattern: Service mesh with SPIFFE workload identity and per-namespace trust-domain isolation around the IdP backend.** Cross-cuts Authenticity for the identity-issuance half; mention via `related_concerns`. The IdP namespace should be a distinct trust domain from RP-tier namespaces.

**Pattern: Cross-region audit replication synchronous with bounded lag SLO; regional failover preserves audit continuity.** Cross-cuts Non-Repudiation; the audit replication is the highest-priority cross-region replicated data class.

## Source: `common-patterns/resilient.md`

# Identity security common patterns — Resilient

These are illustrative templates, not all-inclusive. Use them to calibrate analytical style, severity assignment per the identity security rubric, and NIST/ATT&CK mapping habits. The specialist agent's analytical checklist still drives the actual analysis — this file calibrates how findings and capabilities should look once written.

## Common finding patterns

**Pattern: No circuit breaker on the IdP-to-user-store path (LDAP, AD, upstream IdP for federation chains, user database).**

- Severity: high (user-store degradation cascades to user-facing latency and request-handler exhaustion; without circuit-breaker, a slow LDAP backend takes down every IdP worker by tying up its connection pool)
- NIST: SI-13, SC-5, CP-13
- Cross-reference: any Availability finding on outbound timeout discipline; merged finding carries both concerns

**Pattern: Password-reset endpoint retry storm — no rate-limit + no exponential backoff + email-provider degradation produces unbounded retry pressure on the mail-relay credential and SMTP gateway.**

- Severity: medium to high (operational outage of the recovery channel; cascades to user-reported "cannot recover account" support flood)
- NIST: SI-13(4), SC-5, SC-5(1)
- Related concerns: availability (mail-relay SLO), integrity (idempotency on reset-token issuance)

**Pattern: No detection of refresh-token reuse — replay of an already-rotated refresh token produces a new access token instead of revoking the entire token family.**

- Severity: high (refresh-token theft is the dominant token-loss vector in mobile and SPA contexts; reuse-detection per OAuth 2.1 §6.1 converts the attack into a detection signal that fully revokes the token family)
- NIST: IA-5, IA-5(13), SI-4
- ATT&CK: T1550.001 (Use Alternate Authentication Material: Application Access Token); T1528 (Steal Application Access Token)
- Related concerns: authenticity (token-issuance trust chain), ephemeral (refresh-token lifetime)

**Pattern: No graceful degradation specified for upstream-IdP outage during federation flows — the artifacts do not describe what happens to in-flight SAML/OIDC federation when the upstream IdP is unreachable.**

- Severity: high (the IdP becomes the failure proxy for every upstream; the user sees an opaque error and has no fallback path)
- NIST: CP-12, CP-13, IA-2
- Related concerns: availability (federation-hop SLO), distributed (upstream-IdP redundancy)

**Pattern: Chaos-engineering or game-day evidence on federation flows absent — no documented test of "what happens when SAML metadata refresh fails," "what happens when JWKS endpoint returns stale keys," "what happens when SCIM provisioning lags by 1 hour."**

- Severity: medium (resilience is asserted but not tested; the synthesizer escalates if combined with high-severity findings on availability or distributed)
- NIST: CP-4, CP-4(1), IR-3 (incident-response testing)
- Related concerns: availability (SLO under failure), distributed (failover validation)

**Pattern: Retry policy on outbound calls (to upstream IdPs, to SCIM targets, to webhook subscribers) without jitter or budget.**

- Severity: medium (thundering-herd risk on partial failure; webhook-retry storm during subscriber-side incident)
- NIST: SI-13(4), SC-5(1)
- Related concerns: integrity (idempotency on retried operations — federation provisioning duplication risk)

**Pattern: Bulkhead absent between user-facing auth paths and administrative paths — admin bulk-export, audit-log query, or federation-config edit can starve the customer-facing thread pool.**

- Severity: high (admin operations should not be able to take down user-facing auth; bulkhead-less topology means an admin running a wide audit query during peak login can degrade /authorize latency)
- NIST: SC-5, SC-6, SI-13
- Related concerns: availability (bulkhead-less topology amplifies any availability finding), distributed (bulkhead implementation often requires distinct deployment unit)

**Pattern: Tech plan describes "retries" without specifying backoff, jitter, budget, or idempotency-key interaction for federation-provisioning calls.**

- Disposition: uncertainty
- prerequisite_evidence: "Retry policy specification — backoff curve, jitter strategy, total budget per dependency (per-upstream-IdP, per-SCIM-target, per-webhook-subscriber), idempotency-key interaction, behavior on budget exhaustion (fail-fast vs. queue vs. dead-letter), and any compensating-action on permanent failure"

## Common capability patterns

**Pattern: Circuit breaker on every outbound dependency from the IdP (user-store backend, upstream IdP, SCIM target, webhook subscriber, email/SMS provider) with documented thresholds and half-open recovery.** Capability scope must enumerate covered dependencies; absent dependencies become partial-coverage findings.

**Pattern: Refresh-token rotation with family-revocation on reuse detection per OAuth 2.1 §6.1.** Cross-cuts Authenticity for the token-issuance half and Ephemeral for the rotation cadence; mention via `related_concerns`. Higher maturity requires evidence of the reuse-detection alerting wired into incident response.

**Pattern: Graceful degradation for backend-directory unavailability — IdP serves cached authentications with a degraded-mode banner, refuses new credential changes, and notifies the user.** Cross-cuts Availability; mention via `related_concerns`. Maturity requires runbook plus tested degraded-mode behavior.

**Pattern: Bulkheaded thread pools or deployment-level isolation between user-facing auth, admin console, and federation-provisioning workers.** Higher maturity when deployment topology evidences the bulkhead boundary at the pod/process level.

**Pattern: Chaos-engineering game days exercising signing-key rotation, JWKS-endpoint failure, upstream-IdP outage, and SCIM-target outage on a regular cadence.** `designed` from runbook only; `tested` requires postmortem evidence; `operationalized` requires the cadence to be on the SRE calendar.

## Source: `common-patterns/ephemeral.md`

# Identity security common patterns — Ephemeral

These are illustrative templates, not all-inclusive. Use them to calibrate analytical style, severity assignment per the identity security rubric, and NIST/ATT&CK mapping habits. The specialist agent's analytical checklist still drives the actual analysis — this file calibrates how findings and capabilities should look once written.

## Common finding patterns

**Pattern: Access-token lifetime exceeds 1 hour with no refresh-token rotation and no introspection/revocation channel.**

- Severity: high (a stolen access token is valid for its full lifetime with no recovery; short-lifetime-plus-rotation is the proportional control)
- NIST: IA-5, IA-5(13), AC-12 (session termination)
- ATT&CK: T1550.001 (Application Access Token); T1606 (Forge Web Credentials)
- Related concerns: authenticity (revocation requires token-introspection or version-claim discipline), resilient (reuse-detection)

**Pattern: Refresh-token lifetime extends to weeks or months with no rotation-on-use and no reuse-detection.**

- Severity: high (refresh-token theft is the dominant token-loss vector for mobile/SPA clients; OAuth 2.1 §6.1 requires rotation-with-reuse-detection for public clients)
- NIST: IA-5, IA-5(13), SI-4, AC-12
- ATT&CK: T1550.001; T1528 (Steal Application Access Token)
- Related concerns: confidentiality (refresh-token-at-rest storage), resilient (reuse-detection alerting)

**Pattern: OAuth client_secret unrotated since initial issuance; rotation procedure undocumented.**

- Severity: high (client_secret leak is a recurring incident pattern via repository exposure, CI log leak, mobile-app extraction, vendor compromise; without rotation, leak is permanent)
- NIST: IA-5, IA-5(1), SC-12
- ATT&CK: T1552.001 (Credentials in Files); T1078 (Valid Accounts)
- Related concerns: authenticity (client-authentication strength; private_key_jwt and mTLS client auth eliminate the shared-secret class), non_repudiation (audit of client_secret use vs. rotation)

**Pattern: Session lifetime unspecified — no maximum absolute lifetime, no idle timeout, no behavior on credential change, no behavior on AAL elevation.**

- Disposition: uncertainty or blocked
- prerequisite_evidence: "Session management policy — maximum absolute lifetime per AAL tier, idle timeout, behavior on password change (revoke all sessions vs. preserve), behavior on MFA enrollment/removal, behavior on AAL elevation (does step-up issue a new session or upgrade the existing one?), explicit logout semantics including SAML SLO and OIDC front-channel/back-channel logout"

**Pattern: Signing-key rotation cadence absent or longer than the longest token lifetime.**

- Severity: high (the JWKS rotation gives a revocation window for token forgery in the event of key compromise; without rotation, key compromise is permanent)
- NIST: SC-12, SC-12(2), SC-12(3), SR-11
- Related concerns: integrity (JWKS rotation grace window discipline), immutability (key-lifecycle audit), distributed (regional HSM rotation coordination)

**Pattern: Recovery-code set static — recovery codes generated at MFA enrollment and never rotated even when the MFA factor itself rotates.**

- Severity: medium to high (a stolen recovery-code set survives every MFA-factor change; rotation-on-MFA-change is the proportional control)
- NIST: IA-5, IA-5(1)
- Related concerns: authenticity (recovery-flow AAL claim weakens if codes are old)

**Pattern: Service-account / non-human-identity credentials inside the IdP (LDAP bind credentials, database credentials, SMTP credentials, vendor API keys) are static long-lived secrets with no rotation.**

- Severity: high (broad blast radius on credential leak, no automatic invalidation, no detection signal on use of a leaked credential; the IdP backend credential leak pivots from IdP outward to every system the IdP touches)
- NIST: IA-5, IA-5(1), IA-5(7), SC-12(1), AC-2
- ATT&CK: T1078 (Valid Accounts); T1552.001 (Credentials in Files)
- Related concerns: confidentiality (key management around the credential), authenticity (workload identity as the replacement pattern)

**Pattern: Tech plan mentions "secrets stored in vault" without rotation specifics, audit-on-fetch, break-glass procedure, or secret-zero-trust posture for the vault token itself.**

- Disposition: uncertainty or blocked
- prerequisite_evidence: "Secret-management policy — per-secret-class rotation cadence (signing keys, client secrets, bind credentials, recovery-channel credentials), rotation mechanism (automated vs. manual), audit-on-fetch behavior, break-glass procedure, and secret-zero-trust posture (does the vault auth token itself rotate?)"

## Common capability patterns

**Pattern: Short-lived access tokens (≤1 hour, ≤15 minutes for high-privilege scopes) paired with refresh-token rotation and reuse detection.** Maturity ladder: `designed` from tech plan; `implemented` requires OAuth-library configuration evidence; `operationalized` requires evidence of family-revocation events fed to detection.

**Pattern: OAuth client_secret automated rotation with overlap window; private_key_jwt or mTLS client authentication available as the rotation-resilient alternative.** Higher maturity when private_key_jwt or mTLS is the default for new client registrations and client_secret is on a deprecation path.

**Pattern: Signing-key rotation on a documented cadence with JWKS publication discipline (next-key published in JWKS before becoming active; old key retained in JWKS through the longest token lifetime).** Cross-cuts Integrity for the rotation grace window; mention via `related_concerns`. Operationalized maturity requires monitoring on the rotation cadence itself.

**Pattern: Workload identity (SPIFFE/SPIRE, cloud-native workload identity, Kubernetes ServiceAccount projected tokens) replacing static service credentials for IdP-to-backend calls.** Caveats expected on which backends are confirmed onboard; legacy LDAP/AD backends often remain on bind-credentials.

**Pattern: Session lifetime policy declared per AAL tier (AAL3 sessions shorter than AAL1; step-up issues fresh session; credential change revokes all sessions; SLO and front-channel logout work across all federated SPs).** Operational maturity requires evidence the SLO/front-channel logout actually completes for all SPs (the common gap).

**Pattern: JIT human access for the IdP admin console via approval workflow with time-boxed grants and full session recording.** Operational maturity requires runbook evidence plus the recording-retention policy; designed maturity from tech plan only.

## Source: `common-patterns/authenticity.md`

# Identity security common patterns — Authenticity

These are illustrative templates, not all-inclusive. Use them to calibrate analytical style, severity assignment per the identity security rubric, and NIST/ATT&CK mapping habits. The specialist agent's analytical checklist still drives the actual analysis — this file calibrates how findings and capabilities should look once written.

## Common finding patterns

**Pattern: AAL (Authenticator Assurance Level) per surface undeclared — artifacts do not state whether the IdP targets NIST SP 800-63B AAL1, AAL2, or AAL3 for admin, user, and machine surfaces.**

- Severity: medium when blocked (cannot evaluate MFA-strength findings without the target); high when the target is implicit and the implementation falls short (e.g., admin surface implicitly AAL3 but only password+SMS implemented)
- NIST: IA-2, IA-2(1), IA-2(2), IA-2(6), IA-2(8)
- Related concerns: ephemeral (authenticator lifetime per AAL), non_repudiation (audit per-AAL-event), distributed (MFA consistency across regions)

**Pattern: MFA optional on administrative surfaces (IdP admin console, federation-trust editor, signing-key-rotation surface).**

- Severity: critical (admin-tier compromise is the boundary case where Authenticity, Non-Repudiation, and Immutability findings converge — see Critical rubric clause on compromised admin account)
- NIST: IA-2(1), IA-2(2), AC-6, AC-6(2), AC-6(7)
- ATT&CK: T1078 (Valid Accounts); T1556 (Modify Authentication Process)
- Related concerns: non_repudiation (admin actions without MFA produce weaker actor attribution)

**Pattern: SMS or voice fallback permitted on phishing-resistant MFA enrollments.**

- Severity: high (effective AAL downgrade; SMS interception via SIM-swap is a documented incident pattern that defeats the WebAuthn/FIDO2 target)
- NIST: IA-2(1), IA-2(2), IA-2(8) — note 800-63B §5.1.3 specifically deprecates SMS for new AAL3 implementations
- ATT&CK: T1621 (Multi-Factor Authentication Request Generation); T1556.006 (MFA Bypass)
- Related concerns: ephemeral (SMS-channel credential lifetime undefined), resilient (SMS-provider outage and the fallback-to-fallback question)

**Pattern: Service-to-service authentication inside the IdP cluster uses shared bearer tokens, not mTLS or workload identity.**

- Severity: high (lateral-movement amplification; no identity binding on the credential; IdP-tier compromise is the gate to credential-store compromise)
- NIST: SC-8(1), SC-23, IA-3, IA-9 (service identification and authentication)
- ATT&CK: T1557 (Adversary-in-the-Middle) with in-cluster rationale; T1078
- Related concerns: ephemeral (shared-token rotation), confidentiality (in-cluster credential material in transit)

**Pattern: OAuth client authentication is `client_secret_basic` or `client_secret_post` for confidential clients; private_key_jwt, client_secret_jwt, and tls_client_auth (mTLS) not offered as alternatives.**

- Severity: medium to high (shared-secret-only client auth is the rotation-fragile authenticator class; the modern alternatives — RFC 7523 JWT bearer for client auth, RFC 8705 mTLS client auth — eliminate the leak class)
- NIST: IA-2, IA-5, SC-12, IA-3(1)
- Related concerns: ephemeral (client_secret rotation pain motivates the migration), integrity (signature-based client auth provides per-request binding)

**Pattern: OIDC flow allows implicit grant (`response_type=id_token` or `response_type=token`) for new client registrations.**

- Severity: high (implicit grant is deprecated by OAuth 2.1; credential-leakage exposure via browser history, referer headers, mobile-app interception)
- NIST: IA-2, IA-5, IA-5(2)
- ATT&CK: T1550.001 (Application Access Token); T1528 (Steal Application Access Token)
- Related concerns: integrity (authorization-code-with-PKCE is the only secure flow for public clients), confidentiality (token-in-URL-fragment leak surface)

**Pattern: SAML IdP allows unsigned AuthnRequest or unsigned SP metadata; the trust relies on TLS only.**

- Severity: high (SP impersonation surface, downgrade attack surface; SAML 2.0 Security Considerations §6.1 recommends both transport and message-level signature)
- NIST: SI-7, IA-3, IA-3(1), SC-23
- ATT&CK: T1199 (Trusted Relationship)
- Related concerns: integrity (signature validation discipline on the inbound AuthnRequest), distributed (SP metadata refresh and trust-on-first-use risk)

**Pattern: Audit-log entries on consequential actions are not cryptographically signed; integrity rests on storage-substrate controls only.**

- Severity: medium to high depending on the substrate (high when audit is in a multi-tenant store with elevated read access; medium when audit substrate is WORM-locked)
- NIST: AU-9, AU-9(3), AU-10 (non-repudiation), SI-7
- ATT&CK: T1070 (Indicator Removal); T1565 (Data Manipulation)
- Related concerns: non_repudiation (signed audit closes the attribution-tampering gap), immutability (the substrate-controls half)

**Pattern: Federation trust is established without contact attestation, domain-control validation on the redirect_uri host, or human approval workflow — the SP self-asserts its identity at registration.**

- Severity: high (malicious-RP onboarding surface; the registered SP can request scopes from any user lured to /authorize)
- NIST: IA-2, IA-3(1), AC-2, SR-3
- ATT&CK: T1199 (Trusted Relationship); T1078
- Related concerns: non_repudiation (audit on federation-trust establishment), immutability (federation-trust history)

**Pattern: Tech plan describes "authenticated APIs" generically without specifying mechanism per surface, token lifetime, or validation procedure including signature algorithm and key source.**

- Disposition: uncertainty or blocked
- prerequisite_evidence: "Authentication specification per surface — mechanism (OAuth bearer, mTLS, signed JWT, API key, session cookie), token lifetime, signature-algorithm pin, key-source (JWKS endpoint, embedded key, KMS handle), replay-protection mechanism (nonce, jti, timestamp window), and the AAL/FAL claim associated with the surface"

## Common capability patterns

**Pattern: FIDO2/WebAuthn for administrative access plus phishing-resistant MFA for end-user PII surfaces; SMS fallback permitted only as recovery-only step-down, never as primary.** Capability scope must enumerate which surfaces and which user populations; AAL target per surface must be in evidence.

**Pattern: mTLS across the IdP service mesh with SPIFFE/SPIRE workload identity; every IdP-internal call carries cryptographic workload identity, not shared tokens.** Scope must enumerate covered services; legacy services not yet onboarded become caveats.

**Pattern: OAuth client authentication via private_key_jwt or tls_client_auth (mTLS) as the default for new clients; client_secret_basic only for legacy.** Higher maturity when the registration UX defaults to private_key_jwt and client_secret is opt-in with a deprecation notice.

**Pattern: SAML signed AuthnRequest and signed SP metadata required for all federation trust relationships; metadata refresh validates the publisher's signing chain.** Cross-cuts Integrity for the signature-validation discipline.

**Pattern: Cryptographically signed audit entries (per-entry signature plus hash-chained per stream, with chain heads anchored externally to a separate trust domain or external timestamp authority).** Cross-cuts Non-Repudiation and Immutability; mention via `related_concerns`. Maturity ladder: `designed` from tech plan; `implemented` requires code/IaC evidence; `operationalized` requires chain-verification at audit-read time.

**Pattern: Federation trust onboarding via approval workflow with domain-control validation, contact attestation, and per-trust audit anchor; trust modifications require re-approval.** Higher maturity when the workflow integrates with security-team review for trusts with high-blast-radius scope.

## Source: `common-patterns/non-repudiation.md`

# Identity security common patterns — Non-Repudiation

These are illustrative templates, not all-inclusive. Use them to calibrate analytical style, severity assignment per the identity security rubric, and NIST/ATT&CK mapping habits. The specialist agent's analytical checklist still drives the actual analysis — this file calibrates how findings and capabilities should look once written.

## Common finding patterns

**Pattern: Audit completeness on the IdP's consequential-action surface unverified — the consequential-actions list contains 50+ event classes; the artifacts confirm logging for only a subset (typically the obvious authn success/failure pair).**

- Severity: high (the IdP is the highest-stakes audit surface on the platform; partial coverage is the dominant real-world finding pattern, and any unaudited event class can hide breach activity)
- NIST: AU-2, AU-3, AU-3(1), AU-12
- Related concerns: authenticity (the actor field is only as strong as the authentication that produced it), immutability (audit storage discipline)

**Pattern: Token issuance audit lacks the token identifier (jti, opaque token ID) — log says "user X received a token" but does not link the token back to a later use.**

- Severity: high (forensic reconstruction of "which token did the attacker use, when did we issue it, and which other tokens were issued in the same session" is impossible without per-token identifiers)
- NIST: AU-3, AU-3(1), AU-12(1), AU-10
- Related concerns: integrity (the token identifier IS the lifecycle anchor), ephemeral (revocation requires the identifier)

**Pattern: Refresh-token rotation chain not auditable — the audit records issuance and revocation but does not link refresh-token generations within a token family.**

- Severity: medium to high (refresh-token reuse-detection investigations require the chain; without it, "which family was compromised" cannot be answered)
- NIST: AU-3, AU-12, IA-5
- Related concerns: resilient (reuse-detection events), ephemeral (rotation cadence)

**Pattern: OAuth consent grants audited at the grant event but not at use — "user X granted scopes S to client C" is logged, but per-use of the granted scope is not.**

- Severity: medium (the IdP can prove consent existed; cannot prove which uses occurred within the consent window without the per-use audit)
- NIST: AU-2, AU-3, AU-12
- Detail: GDPR Article 5(2) accountability defense for processing under the consent basis benefits from per-use audit when consent disputes arise.

**Pattern: SAML assertion log captures assertion issuance but does not capture the attribute-release set per assertion — privacy attestation for "which attributes were released to which SP at which time" is incomplete.**

- Severity: high (GDPR Article 5(1)(c) data-minimization defense requires evidence of what was actually released; this is the equivalent of record-level access logging for federation)
- NIST: AU-2, AU-3, AU-12, AC-21 (information sharing)
- Related concerns: confidentiality (attribute-release-policy enforcement), immutability (assertion-log retention)

**Pattern: Audit-read access uncontrolled — any operator role can search audit logs without separate authorization, and audit-of-audit-access (who searched what) is not recorded.**

- Severity: high (audit access is itself a consequential action — an insider with audit read can identify what's been observed and adjust behavior; SoD on audit access is a SOC 2 CC6.1 expectation)
- NIST: AU-9, AU-9(4), AU-9(6), AC-5 (separation of duties), AC-6
- Related concerns: authenticity (audit-role definition), confidentiality (audit content sensitivity inheritance — the audit carries credentials' worth of metadata)

**Pattern: Audit pipeline single-point-of-failure — single broker, single sink, no buffer between application and broker; broker outage produces silent audit loss.**

- Severity: high (audit availability is itself a regulatory requirement; broker outage produces a gap covering the very moments operators most need to investigate)
- NIST: AU-5, AU-5(1), AU-5(2), CP-7
- Related concerns: availability (audit-pipeline SLO), distributed (audit-broker topology), immutability (durability of the audit)

**Pattern: No time-source policy — audit timestamps are local system clocks with no NTP discipline, no drift bounds, no fallback to a secondary stratum.**

- Disposition: uncertainty or blocked
- prerequisite_evidence: "Audit time-source specification — NTP topology, time-source authority, drift bounds, behavior on time-source failure, timestamp precision (millisecond required for token-issuance audit, microsecond preferred), and the audit anchor on time-source-availability events themselves"

**Pattern: Break-glass procedure exists but break-glass actions are not specially audited beyond normal logging.**

- Severity: medium to high
- NIST: AU-3, AU-12(1), AC-6(9), AC-6(10)
- Detail: break-glass IdP-admin actions (key rotation under incident, mass session invalidation, mass MFA reset) should produce a distinguishable audit stream that automatically routes to security review independent of normal audit consumption.

**Pattern: Audit content sensitivity not classified — the audit log carries credentials, partial PII (request metadata: IP, user agent), and authentication metadata that re-identifies; access controls on the audit do not reflect its highest-sensitivity contents.**

- Severity: medium to high (audit-pipeline egress to SaaS log aggregators is a recurring inadvertent-exposure vector)
- NIST: AU-9, AC-3, SC-28, AC-21
- Related concerns: confidentiality (audit egress encryption and access controls), authenticity (audit-role definition)

## Common capability patterns

**Pattern: Per-action audit on every consequential-action surface (the full consequential-actions list) with actor, resource, action, purpose/justification, AAL/FAL claim, and outcome captured per-event.** Scope must enumerate covered surfaces against the consequential-actions list; caveats for any out-of-evidence — this is the dominant audit-coverage check.

**Pattern: Cryptographically signed audit entries with per-stream hash-chaining; chain heads anchored daily to an external trust domain (separate KMS, separate cloud account, or external timestamp authority).** Maturity depends on whether the chain is described in tech plan only or implemented in code/IaC; operationalized maturity requires evidence of chain verification at audit-read time and an alert on chain-break.

**Pattern: Audit-read access gated by a separate role from operational roles, with read events themselves audited (audit-of-audit-access).** Cross-cuts Authenticity for the role definition; mention via `related_concerns`. Higher maturity when audit-read also requires step-up authentication.

**Pattern: Time-source policy with NTP topology specified, drift bounds enforced, fallback to a secondary stratum on primary failure, time-source-availability events themselves audited, and millisecond-or-better timestamp precision on token-issuance events.** Higher maturity requires monitoring evidence on drift bounds.

**Pattern: Per-token audit linking issuance, refresh, revocation, and use events through the token identifier (jti for JWT, opaque ID for opaque tokens), with the refresh-token family chain explicit.** Cross-cuts Ephemeral; this is the foundational audit anchor for any token-loss investigation.

## Source: `common-patterns/immutability.md`

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
