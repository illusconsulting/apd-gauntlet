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
