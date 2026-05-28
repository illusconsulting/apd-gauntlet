---
name: apd-domain
description: Active domain pack content — severity rubric, consequential actions, common patterns. Generated from a domain pack at build time; do not edit by hand.
metadata:
  pack: api-security
  pack_version: 1.0.0
  framework_version: 1.4.0
  generated: 2026-05-27T23:01:41Z
---


## Source: `severity-rubric.md`

# API Security Severity Rubric (impact-to-API-service)

Calibrated against impact-to-the-API-service-and-its-data-subjects, not against generic CVSS. The specialist agent cites the matching clause in finding `detail` fields. Cited examples in each tier are illustrative, not exhaustive. OWASP API Top 10 (2023) categories are referenced inline as API1–API10.

## Critical

Any of the following:

- **Mass PII exfiltration capability** — a realistic attack scenario yields bulk personal data extraction (typically >500 data subjects, but the threshold is the regulator's, not the rubric's). Triggers GDPR Article 33 72-hour breach notification, GDPR Article 34 communication to data subjects when high-risk, state attorney-general notification under US breach-notification statutes, and CCPA §1798.150 statutory damages exposure.
- **Cardholder data exposure within PCI scope** — exposure of PAN with any of {expiry, cardholder name, service code, CAV2/CVC2/CVV2/CID, PIN/PIN block, full magnetic stripe, full track data}. Triggers PCI-DSS forensic investigation, card-brand fines, mandatory cardholder notification, and probable loss of merchant-acquirer status.
- **Authentication bypass to high-privilege functions with no factor required** — OWASP API2 (Broken Authentication) at its sharpest edge. Includes JWT `alg:none` accepted, signature verification skipped, session fixation producing persistent unauthorized access, password-reset bypass that does not require knowledge of the old password or possession of a reset token, and OAuth flows accepting unverified ID tokens.
- **Audit trail loss covering credential or payment events** — renders breach detection and breach-notification obligations un-meetable, renders PCI-DSS Requirement 10 non-compliant, and renders SOC 2 CC7.2 (monitoring of system components for anomalies) un-attestable. Regulators treat absence of audit as presumption of breach.
- **Total auth-service outage** — sustained inability to authenticate any user across the platform; cascading failure to every downstream service. Customer-facing total outage with regulatory and contractual SLA consequences.
- **Forgeable session tokens at platform scope** — signing-key compromise, key-confusion attack (RS256 verified as HS256 using the public key as the HMAC secret), or shared signing key across tenants permitting cross-tenant token forgery. Effectively equivalent to authentication bypass.
- **SQL or NoSQL injection on a PII-bearing endpoint** — direct data exfiltration capability with arbitrary query construction; combine-and-amplify with any logging gap.

## High

Any of the following:

- **BOLA / IDOR exposing PII or payment data bounded to a subset** — OWASP API1 (Broken Object Level Authorization) where the attacker can enumerate identifiers to read other users' data but blast radius is bounded by enumeration rate or non-trivial ID predictability. The dominant real-world API finding class.
- **BFLA exposing admin functions to authenticated low-privilege users** — OWASP API5 (Broken Function Level Authorization). Includes HTTP method swap (POST allowed where only admins should DELETE), undocumented administrative endpoints reachable by regular users, and missing role check on a privilege-altering operation.
- **MFA bypass or weak MFA on PII or payment surfaces** — OWASP API2. SMS fallback that defeats phishing-resistant primary factor, MFA optional on admin surfaces, MFA enrollment endpoint reachable without re-authentication, recovery-code endpoint without rate limiting.
- **BOPLA — excessive property exposure or mass-assignment write-side exposure** — OWASP API3 (Broken Object Property Level Authorization). API responses leak internal fields (`is_admin`, `account_balance`, `internal_user_id`) or accept client-supplied writes to fields the schema should treat as server-managed.
- **Partial audit gap on consequential-action flows** — authentication, authorization, PII access, or payment events logged inconsistently or without actor attribution; impairs incident reconstruction even if breach detection still functions.
- **SSRF reaching internal services or cloud metadata** — OWASP API7 (Server-Side Request Forgery). Severity bounded by what the reachable internal surfaces expose; AWS IMDSv1 reachability is high-trending-critical; bare service-mesh introspection is high.
- **SOC 2 Type I or Type II audit-relevant finding** — control absence in a Trust Services Criteria area an SOC 2 auditor evaluates; absence becomes a qualification on the next service-organization report.
- **OAuth flow accepting implicit grant or missing PKCE on public client** — credential-leakage exposure with a clear migration path; severity is high because exploitation requires only browser-history or referer-leak access.
- **CORS policy with `Access-Control-Allow-Origin: *` plus `Access-Control-Allow-Credentials: true` (or reflective ACAO with credentials)** — cross-origin authenticated read capability; effectively breaks browser same-origin policy on the API.

## Medium

Any of the following:

- **Rate-limiting absent on authentication, password-reset, MFA enrollment, or account-recovery endpoints** — OWASP API4 (Unrestricted Resource Consumption) on the most-abused surfaces. Severity escalates to high if combined with weak credential policy or absent CAPTCHA fallback.
- **API inventory drift — undocumented, deprecated, or unsecured endpoints reachable in production** — OWASP API9 (Improper Inventory Management). Includes shadow APIs in production, deprecated v1 endpoints still routed, staging/test endpoints reachable from production CDN.
- **Unsafe consumption of third-party APIs without response validation** — OWASP API10 (Unsafe Consumption of APIs). Trusting vendor response schemas, accepting vendor-supplied redirects, parsing vendor responses with relaxed JSON/XML parsers.
- **Security misconfiguration with compensating control present** — OWASP API8 (Security Misconfiguration). Default error pages exposing stack traces but WAF redacts; permissive S3 bucket ACL with bucket-level encryption; verbose `Server:` headers without other fingerprintable signals.
- **Logging gap on non-PII operational surfaces** — visibility loss that does not affect breach detection but degrades incident response and capacity planning.
- **Defense-in-depth gap where a single compensating control is the only barrier** — TLS terminates inside the trust boundary so the data tier is in cleartext, single rate-limiter without bot-management fallback, single key wrapping all PII columns.
- **Weak password policy on non-PII surfaces** — minimum length below NIST SP 800-63B guidance, no breached-password check via HIBP-style API, password complexity rules instead of length-and-uniqueness.
- **Hardening weakness exploitable only after adjacent compromise** — requires the attacker to already hold a foothold elsewhere (lateral-only impact). Worth fixing; not catastrophic if deferred.

## Low

Any of the following:

- **Hygiene issue with no realistic exploit path** — deprecated TLS cipher with no client support, redundant control with overlapping coverage, verbose response headers that don't materially aid fingerprinting.
- **Documentation deficiency** — OpenAPI specification drift from implemented behavior in non-security-critical surfaces, runbook formatting inconsistency, naming convention drift.
- **Defense-in-depth gap fully compensated by upstream controls** — useful to know but architecturally non-urgent.
- **Configuration drift on non-production environments** — dev, ephemeral test infrastructure, sandbox tenants without production data.

## Informational

Observations that do not rise to remediation but are worth surfacing for the architecture record. Used sparingly. Examples: notable architectural choices with security implications worth documenting (e.g., chosen JWT library, chosen authorization model), parity gaps with industry peers that are not actually risks, OWASP API Top 10 categories the system meaningfully addresses that the specialist should record as a confirmed capability rather than a finding.

---

## Severity calibration discipline

- **Cite the rubric clause in `detail`.** "This is high severity because it falls under 'BOLA / IDOR exposing PII or payment data bounded to a subset' per the API security rubric, specifically because the `/api/v1/vehicles/{id}` endpoint accepts arbitrary vehicle GUIDs without authorization check, and vehicle GUIDs are recoverable through endpoint X enumeration."
- **Cite the matching OWASP API Top 10 category** when one applies. Multiple categories may apply; cite all that fit (API1 + API3 for an IDOR that also exposes internal fields).
- **Do not average across multiple impacts.** A finding that has critical PII exposure AND medium operational risk is critical.
- **Do not inflate to signal importance.** The synthesizer escalates and reconciles severity disagreements between agents; over-claiming on one agent degrades the cross-agent reconciliation signal.
- **When in doubt, drop one level.** A high-confidence medium is more useful than a low-confidence high. The synthesizer can escalate based on cross-lens corroboration; it cannot reliably de-escalate a confidently-asserted critical.
- **Distinguish capability from exploited.** The rubric scores realistic attack capability, not whether exploitation has been observed. An undisclosed authentication bypass and an actively-exploited one are both critical.

## Source: `consequential-actions.md`

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

## Source: `immutability-classes.md`

# API security required-immutable data classes

For an API-backed system handling PII, payment data, credentials, or session tokens, the following data classes must not change once written. Immutability findings test storage substrate, retention enforcement, and deletion controls against this list.

- **Audit log entries** — regulatory retention varies by anchor. GDPR has no fixed retention for audit, but Article 30 records-of-processing demands defensible retention with documented rationale. PCI-DSS Requirement 10.7 requires 1 year online plus 1 year retrievable archive (effective 2-year retention). SOC 2 typically 1–7 years per service-organization policy. FedRAMP requires 1 year online plus retrievable archive per the agency baseline.
- **Authentication events** — forensic evidence for credential-compromise reconstruction; retention should match or exceed the credential lifetime plus the longest plausible detection window.
- **Payment transactions** — reconciliation, dispute, and chargeback windows. Card networks require 18 months minimum; many merchants retain longer for analytics and risk modeling.
- **OAuth/OIDC consent records** — proof of user consent under GDPR Article 6(1)(a); consent withdrawal does not eliminate the obligation to retain the proof-of-consent for the processing that occurred during the consent window.
- **Data-subject rights request and response records** — GDPR Article 12 obligation to respond and to demonstrate the response. Records of the request, the response, and the records affected.
- **Backup snapshots** — ransomware resilience. Immutability via object-lock, WORM media, or write-locked tape; mutability or deletion-by-single-credential is a finding.
- **Configuration history** — audit and root-cause analysis. Includes RBAC role definitions, ABAC policy bundles, feature-flag state at any point in time, WAF rule sets, TLS configuration.
- **Cryptographic key lifecycle events** — key creation, rotation, revocation, destruction. Required for proving key-management discipline under PCI-DSS Requirement 3.6 and SOC 2 CC6.7.
- **Security incident records** — incident detection, classification, response actions, and closure. Retention typically matches the longest applicable regulatory retention.
- **Code and artifact deployment records** — SBOM, signed image digests, deploy approvals, rollback events. Required for supply-chain attribution and for SLSA-style provenance claims; the deployment record is the link between source-code commit and production behavior at a given time.
- **Webhook receipt records** — when the webhook is a financial event (payment notification, refund, dispute) or a consent event (subscription confirmation). Replays must reconcile against the recorded receipt.
- **Session-token revocation records** — proof that a token was revoked at time T; required when revocation is a security-event boundary (post-breach revocation, mandatory rotation).

Specialists raise Immutability findings against any class on this list that has mutable storage, absent retention controls, deletion-by-single-credential, or unspecified retention. The synthesizer cross-references Non-Repudiation findings on the same data class so the merged record carries both concerns.

## Source: `data-taxonomy.md`

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

## Source: `common-patterns/confidentiality.md`

# API security common patterns — Confidentiality

These are illustrative templates, not all-inclusive. Use them to calibrate analytical style, severity assignment per the API security rubric, and NIST/ATT&CK mapping habits. The specialist agent's analytical checklist still drives the actual analysis — this file calibrates how findings and capabilities should look once written.

## Common finding patterns

**Pattern: API response includes excessive properties — internal fields leak to clients (OWASP API3 read-side, BOPLA).**

- Severity: typically high (PII or authorization-relevant fields exposed; combine-and-amplify when `is_admin`, `internal_user_id`, `account_balance`, or video file paths leak)
- NIST: SC-8, AC-3, AC-4, SI-15 (information output filtering)
- ATT&CK: T1530 (Data from Cloud Storage Object) when the leaked field unlocks bucket access; T1213 (Data from Information Repositories) for general property exposure
- Related concerns: integrity (write-side mass assignment of the same fields commonly co-occurs), authenticity (leaked `is_admin` flags often enable authentication-bypass chains)

**Pattern: Service-to-service traffic inside the cluster relies on network-level trust; payloads contain PII or session tokens.**

- Severity: high (PII exposed to any in-cluster observer; lateral-movement amplification)
- NIST: SC-8, SC-8(1), SC-23, IA-3
- ATT&CK: T1557 (Adversary-in-the-Middle) with specific rationale on in-cluster observer; T1040 (Network Sniffing) for compromised-node case
- Related concerns: authenticity (mTLS provides the identity half; this finding's recommendation should couple to an Authenticity capability), distributed (service-mesh topology)

**Pattern: PII appears in application logs, error responses, or stack traces.**

- Severity: high if production logs are widely accessible or shipped to a SaaS log aggregator; medium if logs are tightly scoped
- NIST: SI-11 (error handling), AU-3, AC-4
- ATT&CK: T1213 with specific rationale on log-aggregator search interface
- Related concerns: non_repudiation (audit content sensitivity inheritance — see data-taxonomy), authenticity (log-aggregator access controls)

**Pattern: JWT carries excessive claims — full PII profile embedded in access tokens.**

- Severity: medium to high depending on token lifetime and audience scope (a 1-hour bearer token carrying email, full name, and DOB exposes that PII to every downstream service, log aggregator, and proxy in the request path)
- NIST: SC-8, AC-4, SC-28
- Related concerns: ephemeral (token-lifetime amplification of claim exposure), integrity (over-broad claims defeat least-privilege downstream)

**Pattern: Backup artifacts unencrypted at rest, or encrypted with a key the primary-store team controls.**

- Severity: high (backups frequently the weakest crown jewel; key-separation failure means primary-store compromise yields backup compromise)
- NIST: SC-28, SC-28(1), CP-9, CP-9(8), SC-12
- ATT&CK: T1530 (Data from Cloud Storage Object); T1567.002 (Exfiltration to Cloud Storage) when backups are exfiltrated as a unit
- Related concerns: immutability (backup mutability), ephemeral (backup-key rotation cadence)

**Pattern: Tokenization claimed for cardholder data but detokenization vault accessible from the application tier.**

- Severity: high (PCI scope collapse claimed but not delivered; the detokenization path is the de facto cardholder-data path)
- NIST: SC-28, SC-12, AC-3, AC-6
- Related concerns: ephemeral (detokenization credentials and rotation), authenticity (workload identity to the vault)

**Pattern: Tech plan describes "encryption in transit" generically without specifying TLS version floor, cipher suite policy, or certificate validation behavior on outbound connections.**

- Disposition: uncertainty or blocked
- Severity: typically medium when blocked, deferred when uncertainty
- prerequisite_evidence: "TLS configuration policy — version floor (TLS 1.2 minimum, 1.3 preferred), cipher suite allowlist, certificate-validation behavior on outbound, mTLS topology if claimed, certificate-pinning posture for mobile clients"

## Common capability patterns

**Pattern: Field-level envelope encryption on PII columns with KMS-managed DEKs.** Maturity ladder depends on evidence — `designed` for tech plan only; `implemented` requires a config or IaC reference; `tested` requires a test report; `operationalized` requires runbook plus rotation monitoring.

**Pattern: Response field-filtering by role with explicit allowlist per endpoint (anti-BOPLA read-side).** Capability scope: "Confirmed for endpoints [X, Y]. Not addressed: [Z]." Caveats expected; the absence of an allowlist on any endpoint converts the capability to a finding.

**Pattern: mTLS across the service mesh with SPIFFE/SPIRE workload identity.** Maturity higher when service-mesh configuration is in evidence; `designed` when tech plan asserts intent without topology.

**Pattern: Tokenized payment instruments with detokenization gated by a separate trust zone.** Higher maturity requires evidence of vault network segmentation, separate IAM, and per-detokenization audit.

## Source: `common-patterns/integrity.md`

# API security common patterns — Integrity

These are illustrative templates, not all-inclusive. Use them to calibrate analytical style, severity assignment per the API security rubric, and NIST/ATT&CK mapping habits. The specialist agent's analytical checklist still drives the actual analysis — this file calibrates how findings and capabilities should look once written.

## Common finding patterns

**Pattern: Mass assignment — endpoint deserializes the entire request body to the domain object without an explicit allowlist (OWASP API3 write-side, BOPLA).**

- Severity: high to critical depending on which fields can be written (writeable `is_admin`, `account_balance`, `role`, `order_status`, `coupon_amount` is critical; writeable display preferences is medium)
- NIST: SI-10 (information input validation), AC-3, SI-15
- ATT&CK: T1190 (Exploit Public-Facing Application); T1078 (Valid Accounts) when mass assignment yields privilege escalation
- Related concerns: confidentiality (read-side BOPLA on the same endpoints), authenticity (privilege-relevant fields enabling identity forgery)

**Pattern: Webhook signature verification missing or optional on inbound integrations.**

- Severity: high (forged webhook can inject malicious adjudication input — refund triggers, payment confirmations, subscription state changes)
- NIST: SI-7, SI-10, SC-23, IA-3(1)
- ATT&CK: T1190; T1071 (Application Layer Protocol) for the forged-request path
- Related concerns: authenticity (signature verification is the identity-assertion mechanism; mapping cross-cuts)

**Pattern: JWT signature verification skipped, `alg:none` accepted, or algorithm confusion possible (RS256 verified as HS256 using the public key).**

- Severity: critical (forgeable tokens at platform scope — see Critical rubric clause on session-token forgery)
- NIST: SI-7, IA-2, IA-5(2), SC-13
- ATT&CK: T1550.001 (Use Alternate Authentication Material: Application Access Token); T1606 (Forge Web Credentials)
- Related concerns: authenticity (token-issuance trust chain), ephemeral (token lifetime amplifies impact)

**Pattern: Idempotency missing on payment, refund, or order-mutation endpoints; double-submit produces duplicate side effects.**

- Severity: high (financial integrity at risk; combine with rate-limit gap for amplification)
- NIST: SI-10, SC-5
- Related concerns: availability (retry storms triggering duplicate side effects), resilient (client retry policy interaction)

**Pattern: Schema enforcement bypassed by polymorphic deserialization — `type` field on input controls which subclass is instantiated.**

- Severity: high (gadget-chain or unexpected-type vulnerabilities; CVE-class issues like Jackson polymorphic deserialization)
- NIST: SI-10, SI-3
- ATT&CK: T1190; T1059 when deserialization yields code execution
- Related concerns: authenticity (unexpected type enabling impersonation), confidentiality (gadget chains reaching sensitive surfaces)

**Pattern: SQL or NoSQL query construction uses string concatenation or unsafe template interpolation.**

- Severity: critical when on a PII-bearing endpoint, high otherwise
- NIST: SI-10, SI-10(5)
- ATT&CK: T1190; T1213 (Data from Information Repositories)
- Related concerns: confidentiality (data exfiltration), non_repudiation (injection often bypasses application-tier audit)

**Pattern: Tech plan describes "input validation" generically without specifying schema, which fields, what error handling, or rejection-on-fail behavior.**

- Disposition: blocked or uncertainty
- prerequisite_evidence: "Input validation specification — schema source (OpenAPI, JSON Schema, code-first), per-field validation rules, behavior on validation failure (reject vs. coerce vs. log), and dead-letter or quarantine policy for invalid messages"

## Common capability patterns

**Pattern: OpenAPI- or JSON-Schema-driven request validation at the edge, with reject-on-fail behavior.** Capability scope must enumerate which endpoints are confirmed; caveats for any not under schema enforcement.

**Pattern: Allowlist-based deserialization for mutating endpoints, with server-managed fields explicitly stripped from input.** Maturity tied to whether the allowlist is centralized (framework-level) or per-endpoint (drift risk).

**Pattern: Idempotency-key handling on all financial mutating endpoints with the key window and storage durability specified.** Higher maturity requires evidence of the idempotency store's own durability and replay-window enforcement.

**Pattern: JWT validation pinned to a specific algorithm with the verification key rotated through a JWKS endpoint.** Maturity ladder: `designed` from tech plan; `implemented` requires verification-library configuration evidence; `operationalized` requires JWKS rotation runbook evidence.

## Source: `common-patterns/availability.md`

# API security common patterns — Availability

These are illustrative templates, not all-inclusive. Use them to calibrate analytical style, severity assignment per the API security rubric, and NIST/ATT&CK mapping habits. The specialist agent's analytical checklist still drives the actual analysis — this file calibrates how findings and capabilities should look once written.

## Common finding patterns

**Pattern: No rate limit on authentication, password-reset, MFA enrollment, or account-recovery endpoints (OWASP API4 + API2 amplifier).**

- Severity: high (credential-stuffing, password-spray, MFA-fatigue, and account-takeover surfaces all open). Escalates to critical when paired with weak password policy or absent CAPTCHA fallback.
- NIST: SC-5, SC-5(1), SC-5(2), AC-7 (unsuccessful login attempts), IA-5
- ATT&CK: T1110 (Brute Force) and sub-techniques T1110.001 (Password Guessing), T1110.003 (Password Spraying), T1110.004 (Credential Stuffing); T1621 (MFA Request Generation)
- Related concerns: authenticity (the credential-policy half), non_repudiation (failed-auth audit completeness)

**Pattern: Unbounded request body size — no `max_request_size` or per-endpoint body cap (OWASP API4).**

- Severity: medium to high depending on parser behavior (a JSON parser allocating proportional to input size is the bigger risk than a streaming parser)
- NIST: SC-5, SC-5(1), SI-10
- Related concerns: integrity (oversize payloads bypassing schema enforcement that runs after parse)

**Pattern: No timeout on outbound calls to third-party APIs; thread-pool exhaustion possible during vendor degradation.**

- Severity: high (vendor slow-down cascades to total request-handler exhaustion; cannot be remediated mid-incident without restart)
- NIST: SC-5, SI-13, CP-13
- Related concerns: resilient (circuit-breaker and bulkhead patterns), distributed (request-handler topology)

**Pattern: SLO and error budget undeclared for consequential paths (authentication, payment, PII-read).**

- Severity: medium (cannot verify the system meets implicit availability commitments; cannot prioritize reliability work)
- NIST: CP-2, CP-2(3), SI-13
- Detail must enumerate which contractual or regulatory commitments imply an SLO (e.g., uptime clauses in subscription agreements, PCI-DSS Requirement 12 on operational availability).

**Pattern: Single-region deployment with 99.9% or higher availability target.**

- Severity: high (target likely undeliverable from single region given typical cloud-provider SLA structure)
- NIST: CP-7, SC-36, CP-9
- Related concerns: distributed (this finding's recommendation points to a topology change owned by Distributed)

**Pattern: Health checks specified as TCP port checks or basic HTTP-200 checks only.**

- Severity: medium (shallow health checks mask dependency degradation; the load balancer continues sending traffic to instances that can accept connections but cannot complete requests)
- NIST: SI-13, CP-10
- Related concerns: resilient (health-check is the input to circuit-breaker decisions)

**Pattern: Tech plan describes "rate limiting" generically without specifying per-endpoint thresholds, identity dimension (per-user, per-IP, per-token), or behavior on limit breach.**

- Disposition: blocked or uncertainty
- prerequisite_evidence: "Rate limit policy specification — per-endpoint thresholds, identity dimension, time window, behavior on breach (reject, queue, degrade), retry-after semantics, and any compensating bot-management layer"

## Common capability patterns

**Pattern: Per-endpoint rate limits with identity-dimensioned thresholds (per-user, per-IP, per-token) and explicit behavior on breach.** Capability scope must enumerate covered endpoints; consequential-action endpoints (auth, password-reset, payment) must all appear in scope or the capability degrades to a partial-coverage finding.

**Pattern: Bounded request size and timeout discipline applied at the edge and re-enforced at each service hop.** Higher maturity when middleware-level enforcement is in evidence rather than per-handler.

**Pattern: SLO and error-budget framework for consequential paths with dashboards and burn-rate alerting.** `designed` from tech plan; `implemented` requires monitoring configuration; `operationalized` requires evidence of error-budget-driven engineering decisions.

**Pattern: Bot-management layer in front of authentication and account-recovery surfaces.** Cross-cuts Authenticity for the credential-policy half; mention via `related_concerns`.

## Source: `common-patterns/distributed.md`

# API security common patterns — Distributed

These are illustrative templates, not all-inclusive. Use them to calibrate analytical style, severity assignment per the API security rubric, and NIST/ATT&CK mapping habits. The specialist agent's analytical checklist still drives the actual analysis — this file calibrates how findings and capabilities should look once written.

## Common finding patterns

**Pattern: Single-AZ deployment of the authentication service, session store, or payment service.**

- Severity: high (the single AZ is the failure domain for the entire platform's authentication; a zonal incident produces total authentication outage)
- NIST: SC-7, CP-7, SC-36
- Cross-reference: any Availability finding on SLO consistency; the merged finding carries both the topology constraint and the SLA consequence

**Pattern: Sticky session dependency — load balancer pinned to instance because session state is in-process.**

- Severity: medium to high (impairs horizontal scale, deploy-time rolling restarts produce session loss, AZ failover invalidates all sessions in the failed AZ)
- NIST: SC-7, CP-7, SC-36
- Related concerns: ephemeral (in-process state survives until process recycle — undermines the immutable-infra story)

**Pattern: In-process state in the application tier preventing horizontal scale.**

- Severity: medium to high depending on what's in-process (cached authorization decisions, partial OAuth flows, rate-limiter counters)
- NIST: SC-7, CP-7
- Related concerns: integrity (cache coherency across instances), authenticity (cached authorization decisions stale across instances)

**Pattern: GDPR data-residency unstated — artifacts describe multi-region capability without specifying which data classes are bound to which regions.**

- Disposition: uncertainty or blocked
- prerequisite_evidence: "Data-residency policy — per-data-class region binding, cross-region replication policy with lawful-basis attestation for any extra-EEA flow, residency-enforcement mechanism (application-tier routing, database-level constraints, or compensating contractual control)"

**Pattern: Tech plan claims multi-region but artifacts don't specify topology — active-active vs. active-passive vs. standby, write-conflict policy, failover trigger.**

- Disposition: uncertainty or blocked
- Severity: medium when blocked
- prerequisite_evidence: "Multi-region topology specification — active configuration, write-conflict policy, failover trigger, expected failover RTO/RPO, and which data classes replicate cross-region"

**Pattern: Cross-region replication for audit logs is asynchronous with unspecified lag.**

- Severity: medium to high (cross-references Non-Repudiation; audit gap during regional failover is a breach-detection blind spot)
- NIST: AU-9(2), SC-36
- Related concerns: non_repudiation, immutability

**Pattern: Service mesh topology unspecified — artifacts assert mTLS without describing identity issuance, certificate rotation, or trust-domain boundaries.**

- Disposition: uncertainty
- prerequisite_evidence: "Service mesh topology — identity issuance (SPIFFE/SPIRE or equivalent), trust-domain boundary, certificate lifetime and rotation, mesh-to-non-mesh edge behavior"

## Common capability patterns

**Pattern: Multi-AZ active-active for the authentication service with stateless application tier and externalized session store.** Scope must specify which dependencies are also multi-AZ (database, cache, broker, secrets store) and which are not.

**Pattern: Stateless application tier with all session state externalized to a redundant store.** Maturity ladder typically `designed` from tech plan; `implemented` requires service configuration or IaC evidence; `operationalized` requires evidence of successful AZ failover.

**Pattern: Region-pinned PII storage with explicit cross-region replication policy.** Higher maturity requires evidence of the policy enforcement mechanism (database-level residency, application-tier routing) plus residency monitoring.

**Pattern: Service mesh with SPIFFE workload identity and per-namespace trust-domain isolation.** Cross-cuts Authenticity for the identity-issuance half; mention via `related_concerns`.

## Source: `common-patterns/resilient.md`

# API security common patterns — Resilient

These are illustrative templates, not all-inclusive. Use them to calibrate analytical style, severity assignment per the API security rubric, and NIST/ATT&CK mapping habits. The specialist agent's analytical checklist still drives the actual analysis — this file calibrates how findings and capabilities should look once written.

## Common finding patterns

**Pattern: No circuit breaker on outbound calls to third-party APIs — payment processor, OAuth identity provider, vendor SaaS, mail relay.**

- Severity: high (vendor degradation cascades to user-facing latency and request-handler exhaustion; OWASP API10 amplification)
- NIST: SI-13, SC-5, CP-13
- Cross-reference: any Availability finding on outbound timeout discipline; merged finding carries both concerns

**Pattern: Retry policy without jitter on the event-bus consumer or webhook delivery.**

- Severity: medium (thundering-herd risk on partial broker failure; failed-webhook retry storm during partner-side incident)
- NIST: SI-13(4), SC-5(1)
- Related concerns: integrity (idempotency interaction — retry without idempotency is duplicate side-effect risk)

**Pattern: No bulkhead between consumer-facing API paths and administrative or batch paths.**

- Severity: high (an admin bulk-export or analytics query can starve the customer-facing thread pool; CDE-scope batch jobs can starve interactive payment paths)
- NIST: SC-5, SC-6 (resource availability), SI-13
- Related concerns: availability (bulkhead-less topology amplifies any availability finding), distributed (bulkhead implementation often requires distinct deployment unit)

**Pattern: Third-party API failure cascades to user-facing 5xx response (OWASP API10).**

- Severity: high (graceful-degradation absence converts vendor incident to platform incident; user-facing error rate tracks vendor uptime)
- NIST: CP-12, CP-13, SI-17
- Detail must specify what would happen today (unhandled exception, generic 500, vendor error proxied) and what should happen (cached fallback, queued retry with user notification, explicit feature-disable with degraded-mode banner)

**Pattern: No detection of refresh-token reuse — replay of an already-rotated refresh token produces a new access token instead of revoking the entire token family.**

- Severity: high (refresh-token theft is the dominant token-loss vector in mobile and SPA contexts; reuse-detection is the OAuth2.1 hardening that converts the attack into a detection signal)
- NIST: IA-5, IA-5(13), SI-4
- Related concerns: authenticity (token-issuance trust chain), ephemeral (refresh-token lifetime)

**Pattern: No graceful degradation specified for identity-provider outage.**

- Severity: critical to high (IDP outage produces total authentication outage if no fallback; high if degraded read-only mode is documented but not implemented)
- NIST: CP-12, CP-13, IA-2
- Related concerns: availability (IDP-dependency SLO), distributed (IDP replication)

**Pattern: Tech plan describes "retries" without specifying backoff, jitter, budget, or idempotency-key interaction.**

- Disposition: uncertainty
- prerequisite_evidence: "Retry policy specification — backoff curve, jitter strategy, total budget per dependency, idempotency-key interaction, behavior on budget exhaustion (fail-fast vs. queue vs. dead-letter)"

## Common capability patterns

**Pattern: Circuit breaker on every outbound dependency with documented thresholds and half-open recovery behavior.** Capability scope must enumerate covered dependencies; absent dependencies become partial-coverage findings.

**Pattern: Retry-with-jitter and explicit per-dependency retry budget on inter-service and outbound calls.** Maturity ladder: `designed` from tech plan; `implemented` requires client-library configuration; `tested` requires chaos-engineering or game-day evidence.

**Pattern: Bulkheaded thread pools or deployment-level isolation between customer-facing and administrative paths.** Higher maturity when deployment topology evidences the bulkhead boundary.

**Pattern: Refresh-token reuse detection with full-family revocation on reuse signal.** Cross-cuts Authenticity for the token-issuance half and Ephemeral for the rotation cadence; mention via `related_concerns`.

## Source: `common-patterns/ephemeral.md`

# API security common patterns — Ephemeral

These are illustrative templates, not all-inclusive. Use them to calibrate analytical style, severity assignment per the API security rubric, and NIST/ATT&CK mapping habits. The specialist agent's analytical checklist still drives the actual analysis — this file calibrates how findings and capabilities should look once written.

## Common finding patterns

**Pattern: Service account tokens or API keys are static long-lived secrets in application configuration with no rotation.**

- Severity: high (broad blast radius on credential leak, no automatic invalidation, no detection signal on use of a leaked credential)
- NIST: IA-5, IA-5(1), IA-5(7), SC-12(1), AC-2
- ATT&CK: T1078 (Valid Accounts) with sub-technique by environment — T1078.001 default accounts, T1078.004 cloud accounts; T1552.001 (Credentials in Files)
- Related concerns: confidentiality (key management around the shared credential), authenticity (workload identity as the replacement pattern)

**Pattern: JWT access-token lifetime exceeds 1 hour with no refresh-token rotation and no revocation channel.**

- Severity: high (a stolen token is valid for its full lifetime with no recovery; refresh-rotation collapses the window)
- NIST: IA-5, IA-5(13), AC-12 (session termination)
- ATT&CK: T1550.001 (Application Access Token); T1606 (Forge Web Credentials)
- Related concerns: authenticity (revocation channel implies token-introspection or version-claim discipline)

**Pattern: OAuth client_secret unrotated since initial issuance; rotation procedure undocumented.**

- Severity: high (client_secret leak is a recurring incident pattern via repository exposure, CI logs, mobile-app extraction)
- NIST: IA-5, IA-5(1), SC-12
- Related concerns: authenticity (client_credentials grant trust), non_repudiation (audit of client_secret use vs. rotation)

**Pattern: Session lifetime unspecified — no maximum absolute lifetime, no idle timeout, no behavior on credential change.**

- Disposition: uncertainty or blocked
- prerequisite_evidence: "Session management policy — maximum absolute lifetime, idle timeout, behavior on password change (revoke all sessions vs. preserve), behavior on MFA enrollment change, step-up bounds, explicit logout semantics"

**Pattern: Refresh-token reuse not detected — reused refresh token issues a new access token instead of revoking the family.**

- Severity: high (the foundational OAuth2.1 hardening pattern; reuse detection converts refresh-token theft into a detection event)
- NIST: IA-5, IA-5(13), SI-4
- ATT&CK: T1550.001
- Related concerns: resilient (the reuse-detection event is also a recovery signal)

**Pattern: Container images mutable in production — `:latest` tags, in-place container patches, or persistent volumes carrying production state across restarts.**

- Severity: medium to high depending on what's mutable
- NIST: CM-2, CM-3, SA-15(7), SI-7
- Related concerns: authenticity (image-signing posture), integrity (configuration drift detection)

**Pattern: Tech plan mentions "secrets stored in vault" without rotation specifics, audit-on-fetch, or break-glass procedure.**

- Disposition: uncertainty or blocked
- prerequisite_evidence: "Secret-management policy — per-secret-class rotation cadence, rotation mechanism (automated vs. manual), audit-on-fetch behavior, break-glass procedure, and secret-zero-trust posture (does the vault token itself rotate?)"

## Common capability patterns

**Pattern: Dynamic credentials via vault — per-session database credentials, short-lived cloud IAM credentials, just-in-time service tokens.** Maturity depends on whether tech plan asserts (designed) or vault configuration is in evidence (implemented).

**Pattern: Workload identity (SPIFFE/SPIRE, cloud-native workload identity, Kubernetes ServiceAccount projected tokens) replacing static service credentials.** Caveats expected on which services are confirmed onboard.

**Pattern: JIT human access for production via approval workflow with time-boxed grants and full session recording.** Operational maturity requires runbook evidence plus the recording-retention policy; designed maturity from tech plan only.

**Pattern: Refresh-token rotation with family-revocation on reuse detection.** Cross-cuts Authenticity for the token-issuance pipeline; mention via `related_concerns`.

## Source: `common-patterns/authenticity.md`

# API security common patterns — Authenticity

These are illustrative templates, not all-inclusive. Use them to calibrate analytical style, severity assignment per the API security rubric, and NIST/ATT&CK mapping habits. The specialist agent's analytical checklist still drives the actual analysis — this file calibrates how findings and capabilities should look once written.

## Common finding patterns

**Pattern: AAL (Authenticator Assurance Level) undeclared — artifacts do not state whether the system targets NIST SP 800-63B AAL1, AAL2, or AAL3, nor on which surfaces.**

- Severity: medium when blocked (cannot evaluate MFA-strength findings without the target); high when the target is implicit and the implementation falls short
- NIST: IA-2, IA-2(1), IA-2(2), IA-2(8)
- Related concerns: ephemeral (authenticator lifetime per AAL), non_repudiation (audit per-AAL-event)

**Pattern: MFA optional on administrative surfaces (OWASP API2).**

- Severity: critical when on PII or payment admin; high when on operational admin
- NIST: IA-2(1), IA-2(2), AC-6, AC-6(2)
- ATT&CK: T1078 (Valid Accounts); T1556 (Modify Authentication Process) when MFA-disable is the attack
- Related concerns: non_repudiation (admin actions without MFA produce weaker actor attribution)

**Pattern: MFA bypass via SMS fallback on a primary phishing-resistant factor.**

- Severity: high (effective AAL downgrade; SMS interception via SIM-swap is a documented incident pattern)
- NIST: IA-2(1), IA-2(2), IA-2(8)
- ATT&CK: T1621 (Multi-Factor Authentication Request Generation); T1556.006 (MFA Bypass)

**Pattern: Service-to-service inside the cluster uses shared bearer tokens, not mTLS or workload identity.**

- Severity: high (lateral-movement amplification; no identity binding on the credential)
- NIST: SC-8(1), SC-23, IA-3, IA-9 (service identification and authentication)
- ATT&CK: T1557 (Adversary-in-the-Middle) with in-cluster rationale; T1078
- Related concerns: ephemeral (shared-token rotation), confidentiality (in-cluster PII in transit)

**Pattern: OAuth flow allows implicit grant or omits PKCE on public client.**

- Severity: high (credential-leakage exposure via browser history, referer headers, or mobile-app interception)
- NIST: IA-2, IA-5, IA-5(2)
- ATT&CK: T1550.001 (Application Access Token); T1528 (Steal Application Access Token)
- Related concerns: integrity (authorization-code interception affecting downstream identity assertions)

**Pattern: Container images deployed without signature verification or admission control.**

- Severity: high (supply-chain compromise vector; OWASP A06:2021 Vulnerable and Outdated Components amplification)
- NIST: SI-7, SR-4, SR-4(3), SR-11
- ATT&CK: T1195.002 (Supply Chain Compromise: Software Supply Chain)
- Related concerns: ephemeral (immutable infra requires authentic images), immutability (artifact provenance history)

**Pattern: Webhook payloads from vendor accepted without signature verification.**

- Severity: high (forged webhook can inject malicious adjudication input — payment confirmations, subscription state, refund triggers)
- NIST: SC-23, IA-3(1), SI-10
- Related concerns: integrity (input validation, route to Integrity finding for the malformed-input concern)

**Pattern: Tech plan describes "authenticated APIs" generically without specifying mechanism, token lifetime, or validation procedure.**

- Disposition: uncertainty or blocked
- prerequisite_evidence: "API authentication specification — mechanism per endpoint (OAuth, mTLS, signed JWT, API key, session cookie), token lifetime, validation procedure including signature algorithm and key source, replay-protection mechanism"

## Common capability patterns

**Pattern: mTLS across service mesh with SPIFFE/SPIRE workload identity.** Scope must enumerate which services are confirmed; expect caveats for legacy services not yet onboarded.

**Pattern: FIDO2/WebAuthn for administrative access plus phishing-resistant MFA for end-user PII surfaces.** Cross-cuts Ephemeral via the credential lifetime; mention via `related_concerns`.

**Pattern: Signed container images with cosign or Notation, enforced by admission control.** Maturity depends on whether the admission-control policy is in evidence and whether the build pipeline produces signatures as part of CI/CD.

**Pattern: SLSA Level 2+ build provenance for production deployments with provenance verification at deploy time.** Higher maturity requires CI/CD configuration evidence plus the verification step at the admission-control or deploy boundary.

## Source: `common-patterns/non-repudiation.md`

# API security common patterns — Non-Repudiation

These are illustrative templates, not all-inclusive. Use them to calibrate analytical style, severity assignment per the API security rubric, and NIST/ATT&CK mapping habits. The specialist agent's analytical checklist still drives the actual analysis — this file calibrates how findings and capabilities should look once written.

## Common finding patterns

**Pattern: Audit entries on consequential actions lack actor attribution — actor field is "system" or a shared service account.**

- Severity: high (consequential-action attribution is the foundation of breach reconstruction and dispute response; SOC 2 CC7.2, PCI-DSS Requirement 10, and GDPR Article 33 all depend on it)
- NIST: AU-3, AU-3(1), AU-10 (non-repudiation), AU-12
- Related concerns: authenticity (the actor field is only as strong as the authentication that produced it; weak auth produces weak attribution), immutability (attribution loss combines with audit-tampering risk)

**Pattern: PII access logging present at table/service level but not record-level — operator queried "users" but the per-record set retrieved is not captured.**

- Severity: high (minimum-necessary attestation impaired; GDPR Article 5(1)(c) data-minimization defense requires evidence of what was actually accessed)
- NIST: AU-2, AU-3, AC-6, AU-12(1)
- Detail: data-protection authorities increasingly expect record-level access logs as the evidence base for "lawful and transparent" processing claims.

**Pattern: Audit shipping is fire-and-forget; consumer-side failure produces silent loss.**

- Severity: high
- NIST: AU-4, AU-5, AU-5(1), AU-5(2)
- Related concerns: availability (audit pipeline reliability), immutability (durability of the audit), resilient (audit-buffer behavior under broker outage)

**Pattern: Audit retention shorter than the longest applicable regulatory minimum or shorter than the longest plausible breach-detection window.**

- Severity: high (renders breach-notification obligations un-meetable for breaches detected after retention expires)
- NIST: AU-11, AU-9, SI-12
- Detail: cite the longest applicable retention — PCI-DSS Requirement 10.7 (1 year online + 1 year archive), SOC 2 (service-organization policy, typically 1–7 years), regulatory anchors per the domain pack.

**Pattern: Audit-read access uncontrolled — any operator role can search audit logs without separate authorization or audit-of-audit-access.**

- Severity: high (audit access is itself a consequential action; uncontrolled access enables an insider to identify what's been observed and adjust behavior)
- NIST: AU-9, AU-9(4), AU-9(6), AC-5 (separation of duties), AC-6
- Related concerns: authenticity (audit-role definition), confidentiality (audit content sensitivity inheritance)

**Pattern: No time-source policy — audit timestamps are local system clocks with no NTP discipline, no drift bounds, no fallback.**

- Disposition: uncertainty or blocked
- prerequisite_evidence: "Audit time-source specification — NTP topology, time-source authority, drift bounds, behavior on time-source failure, and timestamp precision (millisecond, microsecond)"

**Pattern: Audit pipeline single-point-of-failure — single broker, single sink, no buffer between application and broker.**

- Severity: high (audit availability is itself a regulatory requirement under PCI Requirement 10; broker outage produces silent audit loss)
- NIST: AU-5, AU-5(1), CP-7
- Related concerns: availability (audit-pipeline SLO), distributed (audit-broker topology)

**Pattern: Break-glass procedure exists but break-glass actions are not specially audited beyond normal logging.**

- Severity: medium to high
- NIST: AU-3, AU-12(1), AC-6(9), AC-6(10)
- Detail: break-glass actions should produce a distinguishable audit stream that automatically routes to security-review independent of normal audit consumption.

## Common capability patterns

**Pattern: Per-action audit on consequential surfaces with actor, resource, action, purpose, and outcome captured per-record.** Scope must enumerate covered surfaces against the consequential-actions list; caveats for any out-of-evidence.

**Pattern: Cryptographically signed audit entries hash-chained per stream, with chain heads anchored externally (e.g., to a separate trust domain or an external timestamp authority).** Maturity depends on whether the chain is described in tech plan only or implemented in code/IaC; operationalized maturity requires evidence of chain-verification at audit-read time.

**Pattern: Audit-read access gated by a separate role from operational roles, with read events themselves audited (audit-of-audit-access).** Cross-cuts Authenticity for the role definition; mention via `related_concerns`.

**Pattern: Time-source policy with NTP topology specified, drift bounds enforced, and fallback to a secondary stratum on primary failure.** Higher maturity requires monitoring evidence on drift and on time-source-availability events themselves being audited.

## Source: `common-patterns/immutability.md`

# API security common patterns — Immutability

These are illustrative templates, not all-inclusive. Use them to calibrate analytical style, severity assignment per the API security rubric, and NIST/ATT&CK mapping habits. The specialist agent's analytical checklist still drives the actual analysis — this file calibrates how findings and capabilities should look once written.

## Common finding patterns

**Pattern: Audit log written to a mutable RDS table or document collection; no append-only enforcement, no WORM substrate.**

- Severity: high (audit-log alteration breaks every regulatory accountability claim; combines with any Non-Repudiation gap into a single critical-merged record)
- NIST: AU-9, AU-9(2), AU-9(3), AU-11, SI-7
- ATT&CK: T1070 (Indicator Removal); T1070.002 (Clear Linux or Mac System Logs); T1070.004 (File Deletion)
- Cross-reference: any Non-Repudiation finding on audit completeness; the merged record carries both concerns

**Pattern: Backup retention meets minimum but no object-lock or compliance-mode immutability applied.**

- Severity: high (backups vulnerable to ransomware deletion; the primary ransomware-resilience control absent)
- NIST: CP-9, CP-9(1), CP-9(8), MP-4
- ATT&CK: T1485 (Data Destruction); T1490 (Inhibit System Recovery)
- Related concerns: availability (backup recoverability), confidentiality (backup encryption)

**Pattern: Configuration is partly IaC, partly manual; no drift detection between declared and actual state.**

- Severity: medium to high depending on what's manually managed (RBAC roles manually managed is high; deploy parameters manually managed is medium)
- NIST: CM-2, CM-2(2), CM-3, CM-6, CM-6(2)
- Related concerns: integrity (configuration correctness), authenticity (signed-commit posture for the IaC half)

**Pattern: Configuration repository allows history rewrite — no protected branches, no force-push prevention, no signed-commit requirement.**

- Severity: medium to high
- NIST: CM-3, CM-3(1), SI-7(8) (auditable events for transmitted unauthorized changes), SA-10 (developer configuration management)
- Related concerns: authenticity (signed commits provide attribution but mutable history defeats it), non_repudiation (commit-attribution loss)

**Pattern: OAuth/OIDC consent records mutable — consent revocation overwrites the consent record rather than recording revocation as a new event.**

- Severity: high (the proof-of-consent for processing that occurred during the consent window is destroyed; GDPR Article 6(1)(a) defense fails)
- NIST: AU-11, AU-9, CM-2(3)
- Related concerns: non_repudiation (consent-event audit completeness)

**Pattern: SBOM and artifact-provenance history not retained — only current SBOM stored.**

- Severity: medium to high depending on regulatory commitments (high when supply-chain attestation is contractually required)
- NIST: SR-4, SR-4(3), CM-8 (system component inventory), AU-11
- Related concerns: authenticity (artifact signing and the SLSA provenance chain)

**Pattern: Retention duration not specified in artifacts.**

- Disposition: uncertainty or blocked
- prerequisite_evidence: "Retention policy — per-data-class duration, regulatory citation, enforcement mechanism (storage-tier policy, application-level enforcement), legal-hold override procedure, and deletion-verification mechanism"

## Common capability patterns

**Pattern: Object-lock with compliance mode on backup buckets, retention period set to the regulatory minimum or longer.** Scope must specify which buckets are confirmed; capabilities should enumerate the retention period and the lock mode (compliance vs. governance).

**Pattern: Hash-chained audit log with daily chain-head anchored to an external trust domain (separate cloud account, separate KMS, or external timestamp authority).** Cross-cuts Non-Repudiation; mention via `related_concerns`.

**Pattern: GitOps-driven configuration with signed commits, protected branches, and force-push prevention.** Maturity ladder: `designed` from tech plan; `implemented` requires repository configuration or pipeline evidence; `operationalized` requires evidence of the drift-detection-and-alerting loop.

**Pattern: SBOM versioning with per-deployment retention, linking deployed artifact digest to source-commit hash through the build pipeline.** Higher maturity requires evidence of the deploy-time provenance verification.
