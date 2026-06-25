# API security consequential-action surface

For an API-backed system handling PII, payment data, credentials, or session tokens, the following actions are consequential and must be auditable. Non-Repudiation findings evaluate logging coverage against this list; gaps become findings against AU-2 (Auditable Events).

## Authentication events

- Authentication success (interactive, machine-to-machine, federated)
- Authentication failure (with failure categorization — bad password, expired account, locked, unknown user)
- MFA challenge issued, succeeded, failed, bypassed via recovery
- Password change (by the user, by an administrator, via password-reset flow)
- Password-reset request and password-reset completion (separately, with the token-issuance event linked to the completion event)
- Account lockout, lockout-reset, and lockout-override
- Session step-up authentication (re-authentication for sensitive operations)
- Account-recovery initiation and completion (security questions, recovery email, recovery phone, recovery code)

## Authorization decisions

- Allow and deny decisions on consequential operations (every decision, not just denials)
- Privilege escalation (role assignment, role removal, group membership change)
- Session privilege elevation (sudo-equivalent, break-glass, step-up to admin scope)
- Policy evaluation outcomes when the policy engine itself is the trust anchor (OPA, Cedar, ABAC engines)

## PII and personal-data access

- Read access to PII fields (per-record, with the field set retrieved)
- Bulk export (CSV, PDF, API streaming) — capture record count and field set
- Search operations returning PII results — capture query terms and result count
- Profile mutation (any write to a PII field, with before/after when permitted by policy)
- Data-subject-initiated views of their own data versus operator views of subject data

## Payment events

- Card-on-file addition, replacement, and removal
- Transaction authorization, capture, refund, partial refund, void
- BIN-range change for accepted cards (operational risk surface)
- 3-D Secure challenge issued and outcome
- Tokenization request and detokenization request (the detokenization event is the high-value audit anchor)
- Chargeback receipt and dispute response

## Session lifecycle

- Token issuance (access token, refresh token, ID token) with the token identifier captured (not the token itself)
- Token refresh — capture the refresh-token identifier and the new access-token identifier
- Token revocation (user-initiated logout, administrative revocation, automatic revocation on credential change)
- Session expiry (idle timeout, absolute timeout)

## OAuth and OIDC events

- User consent grant (with the scope set and the relying party identified)
- Consent revocation
- Authorization code issuance and exchange
- Scope change on existing grant
- OAuth client registration, modification, and deletion (administrative surface)
- Client-credentials grant issuance (machine-to-machine)

## Administrative configuration

- RBAC role definition change (role creation, permission change, role deletion)
- Policy modification (ABAC policy bundle change, OPA policy push)
- Feature flag toggle on any security-relevant flag (authentication path changes, authorization gates, rate-limit thresholds, audit-pipeline configuration)
- Audit-pipeline configuration change (sink, retention, schema, redaction policy)
- Rate-limit policy change
- WAF rule change
- TLS configuration change (cipher suite, version floor, certificate)

## Third-party integration

- Webhook receipt (with the signature-verification outcome captured)
- Outbound API call carrying PII or payment data (URL, payload field set — typically not the full payload)
- Partner credential rotation
- New partner onboarding and offboarding
- Vendor SLA-event receipt (vendor-initiated incident notification)

## Break-glass and emergency actions

- Break-glass authentication (with the justification captured)
- Emergency policy override (with the policy bundle change captured)
- Emergency credential rotation
- Disaster-recovery failover initiation

## Data-subject rights events (GDPR Article 15–22)

- Access request (Article 15) — receipt, response, and the data provided
- Rectification request (Article 16) — receipt, response, and the change applied
- Erasure request (Article 17, "right to be forgotten") — receipt, response, and the records affected
- Restriction of processing request (Article 18)
- Portability request (Article 20) — receipt, response, and the export delivered
- Objection (Article 21) and automated-decision objection (Article 22)

This list is not exhaustive. Specialists should treat actions outside this list as candidates for inclusion — flagging them as evidence gaps until the operator confirms whether the action is in scope for auditing.
