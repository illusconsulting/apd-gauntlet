---
name: apd-domain-non-repudiation
description: Goal-scoped domain calibration for the apd-non-repudiation lens — full severity rubric, consequential actions, immutability classes, data taxonomy, and ONLY the non-repudiation common-patterns. Generated at build time; do not edit by hand. The full cross-goal skill is at ../SKILL.md.
metadata:
  packs:
    - name: identity-security
      version: 1.0.0
  framework_version: 1.6.0
  generated: 2026-06-03T00:30:08Z
  pruned:
    scoped_to_goal: non_repudiation
    retained_calibration:
      - consequential-actions
      - data-taxonomy
      - immutability-classes
      - severity-rubric
    omitted_goal_patterns:
      - confidentiality
      - integrity
      - availability
      - distributed
      - resilient
      - ephemeral
      - authenticity
      - immutability
    full_skill: ../SKILL.md
    note: "Per-lens view; other goals' common-patterns are intentionally omitted to bound context. Calibration files and attack-path defaults are retained in full. intake / attack-path / domain-auditor read ../SKILL.md."
---

## Domain: identity-security — Source: `severity-rubric.md`

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

## Domain: identity-security — Source: `consequential-actions.md`

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

## Domain: identity-security — Source: `immutability-classes.md`

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

## Domain: identity-security — Source: `data-taxonomy.md`

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

## Domain: identity-security — Source: `common-patterns/non-repudiation.md`

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

## Domain attack-path defaults (merged across packs)

Unioned and deduplicated from the selected packs' `domain.yaml`. Run-config `crown_jewels` / `attacker_positions` still override these. Each entry's `domains` lists the contributing pack(s).

### Crown jewels

```yaml
crown_jewels:
- pattern: signing_key_material
  description: "Token signing keys \u2014 JWT RS256/ES256/EdDSA private keys, SAML\
    \ 2.0 signing X.509 keys, OIDC ID-token signers, JWE content-encryption keys,\
    \ and the JWKS rotation history that establishes the trust chain. Compromise yields\
    \ universal token forgery: the attacker can mint arbitrary access tokens, refresh\
    \ tokens, ID tokens, and SAML assertions for any subject in any audience, producing\
    \ a global authentication bypass across every relying party that trusts the issuer."
  domains:
  - identity-security
- pattern: password_hash_store
  description: User credential hashes (argon2id, bcrypt, scrypt; legacy PBKDF2/SHA-512crypt
    where present) and the per-user salt set. Dumps enable offline password recovery
    proportional to the hash strength; reused passwords amplify the blast radius to
    every external service the population shares credentials with. Triggers GDPR Article
    33 notification and is the highest-frequency real-world IdP incident class.
  domains:
  - identity-security
- pattern: mfa_secret_store
  description: TOTP shared secrets, HOTP counters, WebAuthn credential records (credential
    ID + public key + signature counter), FIDO2 attestation material, push-MFA enrollment
    tokens, backup/recovery codes, and stored security-question answers. Compromise
    of TOTP seeds or recovery codes effectively eliminates the second factor; WebAuthn
    credential records compromise enables impersonation in flows that do not enforce
    attestation freshness.
  domains:
  - identity-security
- pattern: oauth_client_secret_registry
  description: "Confidential-client credentials \u2014 OAuth/OIDC client_secret values,\
    \ private_key_jwt signing keys, mTLS client certificates registered for client\
    \ authentication, and the registered redirect_uri allowlist that gates token issuance.\
    \ Includes PKCE code_verifier values in flight. Leakage permits impersonation\
    \ of an entire relying-party application and bypass of consent for grants that\
    \ target the impersonated client."
  domains:
  - identity-security
- pattern: session_token_store
  description: Active session records (interactive browser sessions, SAML SLO state,
    OIDC front-channel logout state), refresh tokens (typically stored as hashes with
    rotation chains), OAuth authorization codes in their short-lived pre-exchange
    window, device-code/user-code pairs for the device-authorization grant, and CIBA
    auth_req_id state. Loss enables session hijack at scale; mutation enables silent
    privilege transfer between subjects.
  domains:
  - identity-security
- pattern: federated_identity_mapping
  description: 'IdP-to-IdP attribute mappings, upstream-claim transformations, group/role
    assignment rules, JIT-provisioning policies, SCIM target bindings, and the SAML
    attribute-release statements per service provider. Corruption produces silent
    privilege escalation invisible to per-request authentication: the assertion is
    valid, the mapped attributes are wrong, and the relying party authorizes against
    the wrong identity.'
  domains:
  - identity-security
- pattern: consent_record_store
  description: OAuth user-consent grants with scope set and relying-party identity
    (GDPR Article 6(1)(a) lawful basis evidence), SAML attribute-release acknowledgements,
    OIDC offline_access grant records, and the per-grant lifetime/revocation history.
    Destruction or mutation defeats the proof-of-lawful-basis defense for any processing
    that occurred during the consent window; regulators treat absence as unlawful
    processing.
  domains:
  - identity-security
- pattern: audit_log_store
  description: Authentication event log (success/failure/MFA challenge/lockout), authorization
    decision log, token-issuance and revocation log, OAuth consent-grant log, SAML
    assertion log, administrative-action log, and key-rotation event log. The forensic
    fact base for credential-compromise reconstruction, GDPR Article 33 breach scoping,
    and SOC 2 CC7.2 anomaly evidence. Tampering destroys the breach-detection substrate.
  domains:
  - identity-security
- pattern: service_account_credential_store
  description: "Non-human identity credentials \u2014 internal service tokens used\
    \ by the IdP itself, outbound SCIM provisioning credentials, LDAP/AD bind credentials,\
    \ database credentials, SMTP credentials for the recovery channel, and any vendor\
    \ API keys used by enrichment or risk-scoring integrations. Compromise pivots\
    \ from the IdP outward to every system the IdP provisions or queries."
  domains:
  - identity-security
```

### Attacker positions

```yaml
attacker_positions:
- position: unauthenticated_attacker_at_login_endpoint
  description: 'Untrusted external client at the primary login surface: the OAuth
    /authorize endpoint, the SAML SSO endpoint, the OIDC userinfo endpoint, the password-grant
    endpoint where supported, and the credential-recovery endpoints. Models credential
    stuffing, password spraying, account enumeration via timing or error-message differential,
    and unauthenticated SAML/OIDC discovery abuse.'
  domains:
  - identity-security
- position: authenticated_user_seeking_horizontal_escalation
  description: Valid user holding a verified credential and an active session, attempting
    cross-tenant, cross-organization, or cross-realm reads/writes via group-mapping
    bugs, scope confusion in OAuth grants, SAML NameID collision, or SCIM-target overlap.
    The dominant authenticated-attack vector against multi-tenant IdPs.
  domains:
  - identity-security
- position: authenticated_user_seeking_vertical_escalation
  description: "Valid user attempting privilege elevation within their own tenant\
    \ \u2014 admin-role assignment via group-mapping injection, RBAC-policy injection\
    \ through self-service profile fields, abuse of approval workflows, or OIDC scope\
    \ upgrade through token exchange (RFC 8693) without authorization-server-side\
    \ scope reduction."
  domains:
  - identity-security
- position: compromised_user_credential
  description: Attacker holding a valid password (phishing, breach reuse, infostealer)
    but no possession factor. Models MFA bypass attempts, MFA fatigue / push-bombing
    (T1621), SMS-fallback SIM-swap downgrade, recovery-flow abuse to register attacker-controlled
    factors, and WebAuthn-enrollment bypass via unprotected enrollment endpoints.
  domains:
  - identity-security
- position: compromised_user_session_token
  description: "Attacker holding a stolen JWT, session cookie, refresh token, or OAuth\
    \ bearer token \u2014 via XSS on a relying party, malware exfil from the user's\
    \ device, MitM where TLS validation is weak, or token leak via referer/log/analytics.\
    \ Models the consequences of session-lifetime, token-binding, sender-constrained\
    \ tokens (DPoP, mTLS), and revocation latency."
  domains:
  - identity-security
- position: compromised_oauth_client_credentials
  description: Attacker holding a valid OAuth client_id + client_secret (or private_key_jwt
    key, or mTLS client cert) via repository exposure, CI log leak, mobile-app extraction,
    or vendor compromise. Permits impersonation of the relying party against the IdP,
    including silent token issuance for any grant the client is authorized for and
    consent bypass for previously-granted scopes.
  domains:
  - identity-security
- position: compromised_third_party_relying_party
  description: "A downstream application that consumes our tokens has been compromised.\
    \ The attacker can now harvest every access token, refresh token, and ID token\
    \ presented to that RP, exercise any granted scope on the user's behalf, and inject\
    \ malicious behavior into the consent flow for users who arrive at the compromised\
    \ RP. Models OAuth 'compromised relying party' threat (RFC 9700 \xA74.2)."
  domains:
  - identity-security
- position: compromised_admin_account
  description: "Attacker holding IdP administrator or superuser credentials \u2014\
    \ total-compromise scenario. Models the resulting authorization-policy mutation,\
    \ signing-key exfiltration, MFA-disable for arbitrary users, federation-trust\
    \ injection, and audit-tampering attempts. The boundary case where Authenticity,\
    \ Non-Repudiation, and Immutability findings converge into a single critical-merged\
    \ record."
  domains:
  - identity-security
- position: malicious_relying_party
  description: "Attacker-registered or attacker-controlled OAuth/OIDC client targeting\
    \ end-user redirect/consent flows \u2014 open-registration abuse, lookalike client_name\
    \ spoofing, redirect_uri manipulation via path/fragment variants, scope-upgrade\
    \ requests against weak consent UX, and the OAuth covert-redirect / mix-up attacks\
    \ (RFC 9700 \xA74.4). The threat model assumes registration is reachable; severity\
    \ depends on the registration-gate strength."
  domains:
  - identity-security
- position: internal_lateral_attacker_in_idp_tier
  description: "Post-breach attacker pivoting inside the IdP's trust zone \u2014 has\
    \ shell on a worker pod, a database read replica credential, a Redis session-store\
    \ credential, or a Kubernetes ServiceAccount in the IdP namespace. Models east-west\
    \ exposure of credential hashes, signing keys, session state, and the audit pipeline;\
    \ the 'assume compromise' position for the IdP's own infrastructure."
  domains:
  - identity-security
```

### Default trust boundaries

```yaml
default_trust_boundaries:
- boundary: public_internet_to_login_endpoint
  description: "First crossing from untrusted client to the IdP's external surface\
    \ \u2014 /authorize, /token, /userinfo, /jwks.json, /.well-known/openid-configuration,\
    \ the SAML SSO/SLO endpoints, the WebAuthn enrollment/assertion endpoints, the\
    \ credential-recovery surface. TLS termination, edge rate-limit, bot management,\
    \ and IP-reputation enforcement happen here; downstream tiers must not re-trust\
    \ client-supplied identity."
  domains:
  - identity-security
- boundary: login_endpoint_to_credential_store
  description: "Authentication front-end to the credential backend \u2014 password\
    \ hash store, MFA secret store, WebAuthn credential store, recovery-code store.\
    \ Carries plaintext credentials in the request window; hashing and comparison\
    \ must happen on the backend side of this boundary, never on the edge. Compromise\
    \ scope: every credential that crosses during the compromise window."
  domains:
  - identity-security
- boundary: oauth_authorization_endpoint_to_token_endpoint
  description: "Internal crossing between the user-interactive /authorize surface\
    \ (browser-driven, consent UX, redirect flow) and the machine-to-machine /token\
    \ surface (back-channel, client-authenticated, returns tokens). Authorization\
    \ codes, PKCE verifiers, request_uri references, and DPoP proofs cross this boundary;\
    \ mix-up between the two surfaces is RFC 9700 \xA74.4 territory."
  domains:
  - identity-security
- boundary: idp_to_relying_party
  description: "Federation hop \u2014 the IdP issues a SAML assertion, an OIDC ID\
    \ token, or an OAuth access token to a downstream relying party. Trust expressed\
    \ via signature on the artifact and audience binding; weak signature validation,\
    \ missing audience check, or assertion-injection across the boundary collapses\
    \ the federation trust model."
  domains:
  - identity-security
- boundary: idp_to_directory_backend
  description: IdP to LDAP/Active Directory, IdP to user-database backend, IdP to
    upstream IdP for federation chains. Carries directory bind credentials, user-attribute
    reads, group-membership lookups, and SCIM writes. Often the legacy-protocol edge
    where TLS posture and bind-credential rotation lag the rest of the platform.
  domains:
  - identity-security
- boundary: idp_to_session_store
  description: "IdP application tier to the session-state datastore \u2014 Redis,\
    \ PostgreSQL session table, distributed cache. Carries session identifiers, refresh-token\
    \ records, OAuth grant codes pre-exchange, and CIBA auth_req_id state. The 'in-cluster\
    \ trust' assumption commonly hides here; session-store compromise yields impersonation\
    \ of every active session."
  domains:
  - identity-security
- boundary: admin_console_to_idp_backend
  description: Administrator-only surface for tenant configuration, RBAC policy edits,
    federation-trust registration, signing-key rotation, and audit-config changes.
    Highest-blast-radius boundary in the IdP; mandates phishing-resistant MFA, separate
    network path where possible, per-action audit, and ideally an out-of-band approval
    gate for irreversible actions (key rotation, trust deletion, audit-config change).
  domains:
  - identity-security
```
