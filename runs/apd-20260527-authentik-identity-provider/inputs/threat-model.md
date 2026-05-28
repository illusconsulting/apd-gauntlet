---
methodology: stride
---

# Threat Model — authentik

STRIDE-organised threat model for authentik. Each row identifies a
threat class, the surface it lands on, a concrete attack scenario,
the impact framed in identity-security vocabulary (NIST 800-63B AAL/IAL/FAL,
OAuth 2.0 Security BCP, SAML, OIDC), the mitigation present in inputs
(if any), and the residual question the architect cannot answer from
the inputs alone.

This is **not** an exhaustive enumeration. authentik is a substantial
identity platform; the residual-question column is deliberately rich
because per-Flow / per-Stage / per-Policy configuration governs many
of the behaviours below. Specialist reviewers should treat the
mitigations as conditional on operator configuration.

## Scope and methodology

- **Methodology:** STRIDE per surface (each protocol surface and each
  trust-boundary hop gets walked through the six categories). Sources:
  `website/docs/add-secure-apps/`, `website/docs/security/`,
  `website/docs/core/architecture.md`,
  `website/docs/install-config/`, `website/docs/expressions/`,
  `website/docs/customize/policies/`, `pyproject.toml`, `go.mod`,
  `SECURITY.md`, and `website/docs/security/audits-and-certs/`.
- **In scope:** Server (Django Core + embedded outpost + Go router),
  Worker, PostgreSQL, optional Redis, proxy/LDAP/RADIUS/RAC outposts,
  Web UI, REST API, OAuth/OIDC endpoints, SAML endpoints, SCIM
  provisioning, Source federation, Flow + Stage + Policy pipeline,
  CertificateKeyPair-secured secrets.
- **Out of scope:** Browser-class attacks on the Lit web UI (covered
  partially by audit history); supply-chain compromise of upstream
  base images; specific social-login provider OAuth source variants
  (each is configured per-Source).

Severity tags: **H**igh, **M**edium, **L**ow — reflecting impact only
(authentik is a production-grade IdP, so likelihood is governed by
operator configuration, which is not in scope for severity).

Identity-security vocabulary:

- **AAL** — Authenticator Assurance Level (NIST SP 800-63B): AAL1 =
  single-factor, AAL2 = MFA, AAL3 = hardware-bound.
- **IAL** — Identity Assurance Level (NIST SP 800-63A).
- **FAL** — Federation Assurance Level (NIST SP 800-63C): FAL1 =
  bearer assertion, FAL2 = encrypted assertion, FAL3 = holder-of-key.
- **RP** — Relying Party (the application consuming an assertion).
- **OP** — OpenID Provider (authentik when issuing tokens).
- **SP** — Service Provider (the SAML term for RP).
- **IdP** — Identity Provider (authentik).

## 1. Spoofing (S)

### S-1 — OAuth implicit-flow legacy public-client token theft

- **Surface:** OAuth provider `/application/o/authorize/` configured
  for implicit grant.
- **Attack scenario:** Per `add-secure-apps/providers/oauth2/index.mdx`,
  implicit flow is still supported despite the OAuth Security BCP
  recommendation against it. An attacker hosting a malicious script
  on a page reachable from a victim's browser can fetch the bearer
  token from the URL fragment if the RP is a SPA without PKCE. The
  RP's configuration determines whether implicit is permitted; the
  provider supports it.
- **Impact:** **H** — FAL bypass: token-theft equivalent to user
  impersonation against the RP. Severity is RP-scoped, not IdP-wide.
- **Existing mitigation:** Implicit can be disabled per-Provider by
  unselecting it in the grant-type configuration. The doc itself
  cites the OAuth BCP recommendation. PKCE (RFC 7636) is supported.
- **Residual question:** Are operators choosing PKCE-required for
  public clients in their Provider configuration? The inputs do not
  enforce this; it's a per-Provider knob.

### S-2 — JWT signing-key compromise (per-Provider)

- **Surface:** Any OAuth Provider with a configured Signing Key
  (CertificateKeyPair).
- **Attack scenario:** If an attacker obtains the Provider's signing
  private key (via secret_key + database snapshot, see ADR-0004; via
  expression-engine arbitrary-code execution, see ADR-0001; via API
  exposure of certificate material per CVE-2024-42490 pre-patch), the
  attacker can mint arbitrary JWTs for any user against that Provider.
- **Impact:** **H** — FAL bypass: complete RP impersonation for the
  affected Provider. Per ADR-0004 the per-installation `secret_key`
  is the master decryption key.
- **Existing mitigation:** Per-Provider signing keys are isolated
  (compromise of one Provider's key does not affect others — see
  INV-AUTH-005 in `invariants.md`). Per
  `sys-mgmt/certificates.md` certificates are rotatable. Per
  `prior-audit.md` CVE-2024-42490 closed the unauthenticated
  private-key download path in 2024.4.4 / 2024.6.4 / 2024.8.0.
- **Residual question:** Does the platform automatically rotate per-Provider
  signing keys on a cadence? The certificates doc treats rotation
  as operator-initiated. Is there an alert for an old signing key
  still in use? Unclear from inputs.

### S-3 — JWT signing fallback to HMAC-with-client-secret

- **Surface:** OAuth Provider where Signing Key is not selected.
- **Attack scenario:** Per the OAuth provider doc: "When Signing
  Key is not selected, authentik signs JWTs symmetrically with the
  provider Client secret." A leaked client secret (via RP-side
  compromise, log capture, or CI-config exposure) becomes
  signing-key-equivalent. An attacker can forge JWTs claiming any
  user against that RP.
- **Impact:** **H** — FAL bypass for that RP, scoped to the RP's
  trust in symmetric-signed tokens.
- **Existing mitigation:** Operators can (and should) configure a
  Signing Key per Provider. The fallback is the platform default
  posture when none is selected.
- **Residual question:** What proportion of community deployments
  leave Signing Key empty and rely on the client-secret fallback?
  Unclear. Is there a deployment-time warning? Unclear.

### S-4 — SAML signature wrapping (XSW) and signature stripping

- **Surface:** SAML provider receiving signed AuthnRequests / signed
  SP responses.
- **Attack scenario:** Classic SAML signature-wrapping: attacker
  rearranges the XML tree so the signature covers a benign assertion
  but the parser reads attacker-controlled assertions. Variant:
  signature-stripping where the SP signature is removed entirely
  and the IdP processes the request anyway.
- **Impact:** **H** — Authenticity bypass: attacker can submit a
  forged SAML AuthnRequest as if from a trusted SP, potentially
  triggering account linking or IdP-initiated flows for victim
  accounts.
- **Existing mitigation:** `defusedxml==0.7.1` in `pyproject.toml`
  is the conventional Python defense against XXE / XML-bomb (and
  defusedxml-lxml integration). `xmlsec==1.3.17` performs XMLDSig
  verification. Per the SAML provider doc, SP verification certificates
  are per-Provider.
- **Residual question:** Does the SAML processor wrap the libxml2
  parser in a way that prevents XSW? The dependency posture is
  correct; the higher-level signature-validation logic in
  `authentik/providers/saml/` would need code-level review. The
  inputs do not assert XSW protection.

### S-5 — OIDC discovery endpoint enumeration

- **Surface:** `/application/o/<slug>/.well-known/openid-configuration`
  is unauthenticated by design (per OIDC Discovery spec).
- **Attack scenario:** Attacker enumerates Application slugs by
  probing the discovery URL pattern. Each existing slug reveals the
  Provider's `issuer`, `authorization_endpoint`, `token_endpoint`,
  configured grant types, scopes, signing algorithms, JWKS URI.
- **Impact:** **M** — Information disclosure: gives attacker the
  configured surface for that RP. Not directly exploitable, but
  improves attacker map.
- **Existing mitigation:** Application slugs are operator-chosen;
  hard-to-guess slugs reduce enumeration but are not enforced.
- **Residual question:** Is there rate-limiting on the discovery
  endpoint? Per `prior-audit.md` IncludeSec finding L2 noted that
  user-enumeration via response-time variance was fixed in 2025.12;
  no analogous fix for slug enumeration is mentioned.

### S-6 — Outpost-to-Server WebSocket impersonation

- **Surface:** `/ws/outpost/...` WebSocket.
- **Attack scenario:** A second-class attacker on the outpost
  network steals the outpost's service-account token (from outpost
  container env, from a logging sink, from a misconfigured outpost
  image) and impersonates the outpost to the Server, draining
  configuration data including per-Provider client secrets in the
  Provider config that the outpost legitimately needs.
- **Impact:** **H** — Confidentiality breach of OAuth client
  secrets for the affected Provider; potential for an attacker
  outpost to receive and replay user-facing redirects.
- **Existing mitigation:** Per the outpost doc, the service account
  "only has permissions to read the outpost and provider
  configuration." Tokens are stored encrypted in the Server's
  PostgreSQL.
- **Residual question:** Is the outpost-to-Server WebSocket required
  to be over TLS in every topology? Per `architecture.md` the
  WebSocket is mentioned but the TLS requirement is not enumerated.
  Is there outpost-side token rotation? Unclear from inputs.

### S-7 — Source attribute-injection at first login

- **Surface:** Source property mapping (Python expression) processing
  upstream IdP attributes during user-write.
- **Attack scenario:** A malicious upstream IdP (or a compromised
  one) returns attributes claiming the user is `superuser=True`, or
  claims a `username` that collides with an existing admin's. A
  poorly-written property mapping accepts these as-authoritative and
  writes them to the local User.
- **Impact:** **H** — Cross-source admin takeover via attribute
  injection.
- **Existing mitigation:** Per the SECURITY.md classification, the
  expression engine is intentionally arbitrary-Python; the
  property-mapping authoring discipline is the control. The
  authentik docs include sample expressions for safe attribute
  handling.
- **Residual question:** Is there a documented invariant that
  Source-driven user-write cannot mutate the `is_superuser` field
  without explicit allowlist? Per `invariants.md` this is asserted;
  the inputs do not confirm enforcement.

### S-8 — Password recovery brute-force / spray

- **Surface:** Recovery Flow (per Brand configuration).
- **Attack scenario:** Attacker enumerates valid user emails via
  recovery-flow timing (a known historical issue addressed per
  IncludeSec L2 in 2025.12) and dispatches password-reset emails at
  scale to flood inboxes or to triangulate which accounts exist.
- **Impact:** **M** — Account-recovery DoS; user enumeration.
- **Existing mitigation:** The Reputation policy and Password
  Expiry policy can be bound. Per IncludeSec H2 the TOTP rate-limit
  was added to test infrastructure in 2025.12. Per
  `security-hardening.md`, a WAF is recommended.
- **Residual question:** Is there an out-of-the-box recovery-flow
  rate-limit? The Reputation policy must be explicitly bound.
  Operators not deliberately binding it will run without that
  defense.

### S-9 — SCIM endpoint static-token theft

- **Surface:** Outbound SCIM provisioning when the SCIM target is
  configured with Static-token auth.
- **Attack scenario:** If the SCIM target's static token leaks (via
  the Provider config in PostgreSQL, via API exposure, via Worker
  log capture), an attacker can directly call the SCIM endpoint with
  the token to provision or deprovision arbitrary users at the
  target — bypass of authentik entirely.
- **Impact:** **H** — Lateral compromise: the SCIM target
  (e.g. Slack, Salesforce, AWS Identity Center) is now controllable
  with the leaked token.
- **Existing mitigation:** OAuth-token mode is available for SCIM
  in Enterprise per `add-secure-apps/providers/scim/index.md` —
  short-lived tokens retrieved through OAuth replace the static
  token.
- **Residual question:** Community-tier installs cannot use the
  OAuth-token mode and must rely on static tokens. There is no
  documented in-platform rotation cadence for SCIM static tokens.

### S-10 — LDAP outpost simple-bind credential capture (cached bind)

- **Surface:** LDAP outpost in cached-bind mode.
- **Attack scenario:** A network-positioned attacker observing
  LDAP/389 traffic captures simple-bind passwords (not LDAPS).
  Cached bind means the credentials live in outpost memory for
  session duration. A memory-disclosure flaw or a misconfigured
  outpost with debug logging would surface them.
- **Impact:** **H** — Mass credential capture for any user binding
  to the LDAP outpost.
- **Existing mitigation:** LDAPS via SSL or StartTLS is supported
  per the LDAP provider doc; certificate selection by TLS Server
  Name. StartTLS occurs before bind to ensure credentials are
  transmitted over TLS.
- **Residual question:** Is LDAPS the default or operator-opt-in?
  Per the provider doc the operator must configure the Certificate
  + TLS Server Name; the default is plaintext :389.

### S-11 — RAC outpost RDP server-certificate verification bypass

- **Surface:** RAC Endpoint with "Ignore Server certificate" set
  true.
- **Attack scenario:** Per the RAC provider doc, "Ignore Server
  certificate" is a per-endpoint property-mapping setting. With it
  enabled, the RAC outpost does not verify the RDP server's TLS
  certificate, enabling on-path attackers to MITM the user-to-
  remote-machine session.
- **Impact:** **H** — MITM on remote desktop session; capture of
  remote-machine credentials and session content.
- **Existing mitigation:** Default is to verify; this is an opt-in
  hardening misstep. The setting is documented.
- **Residual question:** Is there a dashboard alert for
  Endpoints with "Ignore Server certificate" enabled? Unclear.

## 2. Tampering (T)

### T-1 — Expression-policy or property-mapping sandbox escape

- **Surface:** Any Expression policy, Property Mapping, or Prompt
  stage placeholder expression. Per `SECURITY.md`: "Expressions
  (property mappings/policies/prompts) can execute arbitrary
  Python code without safeguards."
- **Attack scenario:** Per the SECURITY.md classification this is
  not a sandbox at all — it's documented arbitrary Python under the
  Server's process privileges. An attacker with permission to
  create/edit Expressions has full code execution on the Server
  host, including: reading the `AUTHENTIK_SECRET_KEY` from the
  process env, reading any file the Server can read, making
  arbitrary outbound HTTP calls, modifying any model in PostgreSQL.
- **Impact:** **H** — Full Server-host code execution; full data
  exfiltration; cluster-wide identity bypass.
- **Existing mitigation:** Per `security/security-hardening.md`,
  the recommended hardening is to block the Expression /
  PropertyMapping / Blueprint write APIs at the reverse proxy,
  forcing changes through filesystem blueprints. This reduces the
  exposure surface to filesystem write access.
- **Residual question:** Without the reverse-proxy hardening
  applied, the default Server install treats "create Expression"
  as an admin permission. Is there an in-platform warning that
  superusers can RCE? Per the IncludeSec H3 finding, this is
  declared "expected behavior" and documented in hardening.

### T-2 — Blueprint-driven arbitrary-object modification

- **Surface:** Blueprint apply (`/api/v3/managed/blueprints*` API or
  filesystem `/blueprints/`).
- **Attack scenario:** Per `SECURITY.md`: "Importing blueprints
  allows arbitrary modification of application objects… It is
  'exploitable' when importing blueprints from untrusted sources."
  An attacker who can write to `/blueprints/` (filesystem write,
  e.g. via a Worker-side file-write bug) or who can call the
  blueprint apply API can create / modify / delete arbitrary
  Users, Groups, Providers, Policies, etc.
- **Impact:** **H** — Cluster-wide identity bypass; can create a
  superuser and a Flow that grants admin access to that user.
- **Existing mitigation:** Same as T-1: block the blueprint API at
  the reverse proxy. Filesystem access to `/blueprints/` is
  operator-controlled. Per the IncludeSec 2025-09 audit (H1) a
  warning banner was added in 2025.12 to flow imports.
- **Residual question:** Is there an audit event for every
  blueprint apply? If so, who reads it? Per the events doc,
  blueprint apply does emit events; review cadence is
  operator-driven.

### T-3 — SAML signature wrapping / signature stripping

(See S-4 — XSW is both spoofing and tampering by classical STRIDE,
listed once under S-4 for brevity.)

### T-4 — OAuth state / nonce / c_hash / at_hash validation gaps

- **Surface:** OAuth authorization-code flow, hybrid flow.
- **Attack scenario:** authentik IS the OP / IdP, so it generates
  these values. The tampering risk lands when the OP fails to
  enforce them on incoming requests where appropriate: e.g. PKCE
  `code_verifier` validation, redirect-URI exact-match
  enforcement, `state` round-trip (the OP is RP-trusted for state
  echo but the redirect URI must be allowlisted).
- **Impact:** **H** — Open-redirect-style code interception; PKCE
  bypass.
- **Existing mitigation:** Per the OAuth provider doc, redirect
  URIs are operator-configured per Provider; regex support is
  available with the caveat that `.` must be escaped (a common
  authoring mistake — `https://app.example.com` regex without
  escaping matches `https://appXexample.com`).
- **Residual question:** Is there a default-deny on regex-shaped
  redirect URIs without an escape audit? Unclear from inputs.

### T-5 — Stage/Flow modification by compromised admin

- **Surface:** REST API `/api/v3/flows/*`, `/api/v3/stages/*`,
  `/api/v3/policies/*` (admin-only).
- **Attack scenario:** A compromised admin account modifies the
  default authentication Flow to skip the MFA stage, or modifies a
  Policy to silently grant access. Per the platform model, this is
  legitimate admin authority — but it is also the privileged-action
  surface that an attacker who compromises an admin will exercise.
- **Impact:** **H** — Authentication bypass; can disable MFA for
  all users.
- **Existing mitigation:** Per `customize/policies/index.md`,
  every Flow/Stage/Policy change emits a write event. Per
  `sys-mgmt/events/index.md`, events have 365-day default retention.
  Account Lockdown (Enterprise) provides a single-action panic
  button per `security/account-lockdown.md`.
- **Residual question:** Is there a four-eyes / dual-control for
  Flow modifications affecting the default-authentication-flow? Not
  in the input set. Is there an alerting rule out-of-the-box for
  Flow modification? Operator must configure a Notification Rule
  bound to an Event Matcher policy.

### T-6 — Cached LDAP outpost stale-credential acceptance

- **Surface:** LDAP outpost in cached-bind mode.
- **Attack scenario:** A user's password is changed (forced by
  admin, or self-service after suspected compromise). The LDAP
  outpost cached bind continues accepting the old password for the
  cache lifetime. Per the provider doc: "Sessions are saved
  independently, meaning that revoking sessions does not remove
  them from the outpost, and neither will changing a users
  credentials."
- **Impact:** **H** — Credential-rotation invariant violated for
  legacy LDAP clients.
- **Existing mitigation:** Direct-bind mode is an alternative;
  there is no cache. Documentation explicitly notes the trade-off.
- **Residual question:** What is the cache TTL? "Session duration"
  is mentioned but the default value is not enumerated in the
  inputs.

## 3. Repudiation (R)

### R-1 — Audit-log completeness for Expression-policy actions

- **Surface:** Event model.
- **Attack scenario:** A malicious Expression policy or property
  mapping makes a side-effect call (an outbound HTTP request, a
  database UPDATE via a helper, an `ak_send_email`) without
  emitting a corresponding Event. The audit trail is incomplete
  with respect to what the expression actually did.
- **Impact:** **M** — Auditability gap: post-incident
  reconstruction misses expression-driven side effects.
- **Existing mitigation:** Per
  `expressions/reference/_functions.mdx`, the `ak_create_event`
  helper exists, but its use is not mandatory. The Flow itself
  emits an event for each stage execution and each policy
  evaluation.
- **Residual question:** Is there an enforced invariant that every
  helper with side effects (`ak_send_email`, `ak_create_jwt`,
  `ak_call_policy`) emits an event? Per the function reference
  these helpers do not all auto-emit. The audit trail relies on
  authors choosing to call `ak_create_event`.

### R-2 — Audit-log immutability and tamper-evidence

- **Surface:** Event records in PostgreSQL.
- **Attack scenario:** An attacker with database write access (or
  expression-engine code execution per T-1) deletes or modifies
  Event records to hide their tracks. PostgreSQL has no
  cryptographic tamper-evidence by default; the rows are mutable.
- **Impact:** **H** — Audit-trail destruction; full repudiation
  capability.
- **Existing mitigation:** Per `sys-mgmt/events/index.md`, event
  forwarding is recommended: "If you want to forward these events
  to another application, forward the log output of all authentik
  containers." Combined with `days=1` internal retention, the
  source-of-truth becomes the operator's SIEM / log store.
- **Residual question:** Out-of-the-box, what fraction of operators
  configure log forwarding? The shipped configuration does not
  enable it. Without forwarding, the database-resident Event log is
  mutable and there is no tamper-evidence.

### R-3 — Audit-event coverage for outpost actions

- **Surface:** Proxy / LDAP / RADIUS / RAC outpost actions.
- **Attack scenario:** Outposts perform authentication decisions
  locally (cached bind in particular). The Server may not see
  every bind as a discrete event. An attacker exercising the LDAP
  outpost may have actions visible only in the outpost's stdout,
  not in the Server's Event log.
- **Impact:** **M** — Auditability gap for legacy-protocol
  exposures.
- **Existing mitigation:** Outposts emit metrics via Prometheus
  `:9300/metrics`. Direct-bind LDAP forwards each bind to the
  Server (where it does materialise as an event via Flow
  execution).
- **Residual question:** Are cached-bind successes audited
  per-bind or only per-cache-miss? The provider doc strongly
  implies per-cache-miss only.

### R-4 — Account Lockdown event provenance

- **Surface:** Account Lockdown stage (Enterprise).
- **Attack scenario:** Per `security/account-lockdown.md`, lockdown
  is configurable per Brand. The reason field is operator-supplied
  free-text. There is no field for "actor authentication assurance"
  — i.e. the audit event records *who* locked the account but not
  *under what assurance level* the actor was authenticated.
- **Impact:** **L** — Non-repudiation gap for a high-impact
  consequential action.
- **Existing mitigation:** The Event records the actor, the
  reason, and the timestamp. The Account Lockdown Stage explicitly
  creates an audit event.
- **Residual question:** Does the actor authentication context
  (auth_method, MFA used, source IP, geographic location) get
  written into the lockdown event context? The doc says "an audit
  event with the provided reason" but does not enumerate the
  context fields.

## 4. Information Disclosure (I)

### I-1 — Token introspection response over-disclosure

- **Surface:** `/application/o/introspect/`.
- **Attack scenario:** A confidential client introspects tokens it
  legitimately holds; the response includes claims (`sub`, `aud`,
  `exp`, scope, and any scope-claim payload like email, groups).
  An RP introspecting a third-party-issued token (via cross-Provider
  introspection in authentik) sees claims it has no business
  consuming.
- **Impact:** **M** — User-attribute disclosure to RPs that should
  not see them.
- **Existing mitigation:** Per the OAuth provider doc, cross-provider
  introspection requires explicit Federated-Provider declaration.
  The default is per-Provider scoping.
- **Residual question:** Are introspection responses scope-filtered
  the same way userinfo responses are? Unclear from inputs.

### I-2 — User enumeration via authentication-error variance

- **Surface:** Authentication Flow.
- **Attack scenario:** Differentiated error messages or response
  timing distinguishes "user exists, wrong password" from "user
  does not exist". Per `prior-audit.md` IncludeSec L2 (2025-09) the
  password timing variance was fixed in 2025.12 via replacing a
  randomized `sleep` with `make_password`.
- **Impact:** **M** — Username enumeration enabling targeted
  attacks.
- **Existing mitigation:** Fixed in 2025.12 per the audit. Note
  that older installs (2025.2.x branch) may not have the fix.
- **Residual question:** Are there other surfaces (recovery flow,
  invitation flow, source-driven first-login) with similar
  variance? Not all are covered by the cited fix.

### I-3 — Admin API over-permissive scope

- **Surface:** REST API.
- **Attack scenario:** An admin-scoped API token issued for a
  narrow task (e.g. user lookup) is over-scoped and grants
  read/write to unrelated objects. Per the RBAC posture
  (Django-Guardian-based), permissions are object-level — but the
  default admin token is full-access.
- **Impact:** **H** — Lateral admin compromise via leaked or
  excessive token.
- **Existing mitigation:** Per `users-sources/roles/`, Roles are
  the mechanism for least-privilege admin scoping. Service-account
  tokens (per `sys-mgmt/service-accounts.md`) are the recommended
  posture for automation.
- **Residual question:** Is there a default-deny posture for
  service-account tokens? Per the docs, an outpost service-account
  is auto-scoped read-only; admin-issued service-accounts are
  whatever the operator binds.

### I-4 — OAuth scope abuse for over-release of user data

- **Surface:** OAuth scope mapping; userinfo endpoint.
- **Attack scenario:** An RP requests `email profile groups` and
  receives more group memberships than the RP needs. The user's
  consent screen shows the scope name but not the resolved data.
- **Impact:** **M** — User-attribute over-release; minor
  confidentiality.
- **Existing mitigation:** Per `add-secure-apps/providers/oauth2/index.mdx`,
  scope mappings are property mappings (Python expressions). An
  operator can write a custom mapping that filters group memberships
  per-application. The default `profile` scope includes username,
  name, and group membership.
- **Residual question:** Is there a documented default that
  excludes superuser-shaped groups from federated `profile` claims?
  Unclear.

### I-5 — SAML attribute over-release via default mappings

- **Surface:** SAML provider default property mappings.
- **Attack scenario:** Per the SAML provider doc, the default
  property mappings include UPN, Group, Email, Name, User ID,
  Username, WindowsAccountName. An SP that should only see Email
  receives all of these unless the operator removes them per-Provider.
- **Impact:** **M** — Over-release of user attributes to SPs.
- **Existing mitigation:** Default mappings can be removed
  per-Provider. The doc enumerates each.
- **Residual question:** Is there a templating posture that ships
  per-application "scope" presets? Per the inputs, no.

### I-6 — LDAP outpost full-directory disclosure

- **Surface:** LDAP outpost search.
- **Attack scenario:** A user with the `Search full LDAP
  directory` permission (per the post-2024.8 RBAC) can enumerate
  every user and group in authentik via LDAP. A legacy app
  accidentally bound with broad-search rights mass-exfiltrates
  the directory.
- **Impact:** **M** — Mass directory disclosure.
- **Existing mitigation:** Per the LDAP provider doc, the default
  is that an authorized user "will return information about
  themselves" only. The `Search full LDAP directory` permission is
  the gate.
- **Residual question:** When pre-2024.8 deployments upgrade,
  what is the migration default for "Search group" memberships?
  Per the doc, they are migrated to the new permission — so
  existing membership grants the permission post-upgrade, which is
  the conservative choice for compatibility but may surprise
  operators expecting tightening.

### I-7 — Recovery email enumeration

(See S-8 — recovery brute-force and enumeration overlap.)

### I-8 — Tenant boundary leak via Expression policies

- **Surface:** Tenancy (Enterprise alpha) per `sys-mgmt/tenancy.md`.
- **Attack scenario:** Per the tenancy doc: "Expression policies
  currently have access to all tenants." An Expression policy in
  tenant A can read User / Group data from tenant B by querying
  with the right ORM call.
- **Impact:** **H** — Tenancy boundary breach for the alpha
  multi-tenancy feature.
- **Existing mitigation:** None — the doc explicitly flags it as a
  known caveat. The feature is marked alpha.
- **Residual question:** Will this be addressed before GA? Unclear
  from inputs.

### I-9 — Prometheus metrics exposure

- **Surface:** `:9300/metrics` on every outpost and the Server.
- **Attack scenario:** Per the outpost doc: "This endpoint is not
  mapped via Docker, as the endpoint doesn't have any authentication."
  An operator who naively exposes `:9300` to the internet leaks
  request counts, error rates, possibly per-Application metric
  labels.
- **Impact:** **L** — Reconnaissance aid; per-Application
  request-volume disclosure.
- **Existing mitigation:** Documented as not-for-public-exposure.
- **Residual question:** Default network posture (compose vs.
  Helm) — does it accidentally expose? Per the compose default
  the endpoint is not mapped, so the boundary is in-cluster.

## 5. Denial of Service (D)

### D-1 — TOTP brute-force via parallelism

- **Surface:** TOTP validation in the authenticator_validate stage.
- **Attack scenario:** Per `prior-audit.md` IncludeSec H2 (2025-09):
  "TOTP could in theory be brute-forced for login given knowledge
  of a target user's password, enough time, and no WAF/altering on
  high amounts of requests." Fixed in test infrastructure via
  stricter rate-limit.
- **Impact:** **H** — AAL2 bypass given AAL1 breach (password
  known).
- **Existing mitigation:** Per the audit response, rate-limiting
  was added; WAF is recommended.
- **Residual question:** Is the in-platform rate-limit on-by-default
  or operator-opt-in?

### D-2 — Login-flow race-condition reputation bypass

- **Surface:** Default authentication flow.
- **Attack scenario:** Per IncludeSec M1 (2025-09): "The
  anti-brute force mechanism could be bypassed by triggering a race
  condition using the default-authentication-flow." Fixed in
  2025.12 by replacing session-based retry counters with reputation
  scores.
- **Impact:** **H** — Brute-force protection bypass.
- **Existing mitigation:** Fixed in 2025.12.
- **Residual question:** 2025.2.x branch operators on the older
  supported track — is the fix backported to 2025.2?

### D-3 — SAML XML billion-laughs / XXE

- **Surface:** SAML AuthnRequest / SP-response parsing.
- **Attack scenario:** Classic XML-bomb / entity-expansion attack.
- **Impact:** **H** — Server-side resource exhaustion.
- **Existing mitigation:** `defusedxml==0.7.1` in `pyproject.toml`
  is the canonical Python defense.
- **Residual question:** Is `defusedxml` actually invoked on every
  SAML XML parse path? Dependency-level only; code path requires
  review.

### D-4 — Session-store fill via mass-anonymous Flow execution

- **Surface:** Flow executor (`/if/flow/<slug>/`).
- **Attack scenario:** An attacker initiates millions of Flow
  executions against the default-authentication-flow without
  completing them; partial-flow-plan state accumulates in
  PostgreSQL or Redis.
- **Impact:** **M** — Database fill; degraded performance.
- **Existing mitigation:** Reputation policy can throttle; WAF
  recommended.
- **Residual question:** Is there a per-IP request budget at the
  Flow-executor layer out of the box?

### D-5 — Worker queue depth via expensive policies

- **Surface:** Worker tasks executing Expression policies via
  `ak_call_policy` chains.
- **Attack scenario:** An attacker triggers a Flow that contains
  Expression policies that themselves trigger more Expression
  policies via `ak_call_policy` (per the function reference). A
  pathological chain — accidental or malicious — exhausts the
  Worker pool.
- **Impact:** **M** — Background-task starvation; delayed SCIM
  sync, delayed notifications, delayed Source sync.
- **Existing mitigation:** Worker pool concurrency is configurable.
- **Residual question:** Is there a per-Flow execution timeout?
  Unclear from inputs.

### D-6 — Email-stage flood

- **Surface:** Recovery flow, invitation flow, password-reset
  flow, custom flows with an email stage.
- **Attack scenario:** Attacker iterates over user emails,
  triggering a recovery email per iteration. SMTP outbound queue
  fills; legitimate recovery emails delayed.
- **Impact:** **M** — Recovery-channel degradation.
- **Existing mitigation:** Reputation policy; rate-limiting at the
  reverse proxy.
- **Residual question:** Out-of-the-box default? Operator-configured.

### D-7 — SCIM cycle stalls on slow target

- **Surface:** SCIM provider sync running in the Worker.
- **Attack scenario:** A SCIM target endpoint slows or hangs;
  Worker tasks queue. Per the SCIM provider doc: "the workload can
  be distributed across multiple workers" by batching, but a
  single slow target ties up workers from each batch.
- **Impact:** **M** — Worker pool starvation; impacts other SCIM
  targets and unrelated background tasks.
- **Existing mitigation:** Per-batch task distribution is the
  documented scale strategy. Per-task timeouts are not enumerated.
- **Residual question:** What is the default SCIM-call timeout?

## 6. Elevation of Privilege (E)

### E-1 — Expression-engine code execution (see T-1)

(Cross-listed. E-1 = T-1 reframed: Expression engine arbitrary
Python is the principal escalation path for any actor who can
create or edit an Expression / Property Mapping / Prompt placeholder.
Per SECURITY.md this is intentional behaviour; the privilege check
is "permission to create/edit" — Expression editing is a privileged
permission per `security/security-hardening.md`.)

### E-2 — Blueprint-induced superuser creation (see T-2)

(Cross-listed. E-2 = T-2 reframed: blueprint apply can create a
User with `is_superuser=True` and bind that user into a group with
admin Roles. Same mitigation as T-1/T-2.)

### E-3 — Tenant-boundary EOP via cross-tenant Expression read

(Cross-listed. E-3 = I-8 reframed: cross-tenant data read by
Expression policy is also an EOP for the alpha tenancy feature.)

### E-4 — OAuth confused-deputy via client_id mix-up

- **Surface:** OAuth token endpoint.
- **Attack scenario:** Attacker registers an RP with a client_id
  similar to a high-trust RP's; relies on partial-match in the
  Provider's redirect-URI regex (per T-4) to receive codes intended
  for the other RP.
- **Impact:** **H** — RP-to-RP confused deputy; can impersonate
  high-trust RP to a user.
- **Existing mitigation:** Per-Provider redirect URIs are
  exact-match by default; regex is opt-in.
- **Residual question:** Are operators auditing regex redirect URI
  matches?

### E-5 — Horizontal escalation across Brands

- **Surface:** Brand (per `sys-mgmt/brands/index.md`).
- **Attack scenario:** Brand is per-domain; a user with cross-Brand
  visibility (via a misconfigured Default Application or
  cross-Brand Source) can land in a brand's Flow that doesn't
  expect them. Brand-default Flow selection (per the brand doc) is
  the first applicable Flow sorted by slug.
- **Impact:** **M** — Brand-isolation leak; not the same as
  tenant-isolation (see I-8 for tenant).
- **Existing mitigation:** Brand binds Default Application,
  Authentication Flow, Recovery Flow, etc. The bindings are
  explicit.
- **Residual question:** How is cross-Brand access governed for
  operator-shared accounts (e.g. an admin who manages multiple
  Brands)?

### E-6 — Source-attribute privilege injection (see S-7)

(Cross-listed. E-6 = S-7 reframed: a Source-side attacker
escalating a federated user to admin in authentik.)

### E-7 — RAC unauthorized remote-machine takeover via property mapping

- **Surface:** RAC property mapping setting Username / Password /
  private-key for the remote machine.
- **Attack scenario:** An attacker with permission to edit RAC
  property mappings can set the Username/Password to a credential
  they own, then connect through the user-facing RAC flow and
  authenticate to the remote machine as a different identity than
  the user expects — or worse, set the credentials to a
  privileged remote-machine identity that the user's authentik
  account would not normally hold.
- **Impact:** **H** — Remote-machine takeover via authentik-mediated
  RAC.
- **Existing mitigation:** Per the RAC provider doc, property
  mappings are restricted to users with the permission to edit
  them. Endpoint-binding policies can constrain which users reach
  which endpoint.
- **Residual question:** Is there an audit event for RAC property
  mapping changes? Per the events doc, model writes generally emit
  events; specifics unconfirmed.

### E-8 — Embedded outpost / Server boundary breach

- **Surface:** The embedded outpost runs in the same Server image
  as the Core. There is no process-isolation between them.
- **Attack scenario:** A bug in the embedded outpost's HTTP handler
  that allows arbitrary file read in the Server-process address
  space leaks `AUTHENTIK_SECRET_KEY` from process env, which is
  master-decryption-key-equivalent (see ADR-0004).
- **Impact:** **H** — Master-secret disclosure via co-resident
  outpost bug.
- **Existing mitigation:** Per `core/architecture.md` the Go
  router routes between Core and embedded outpost; both are in the
  same image. No process-isolation is described.
- **Residual question:** Are separate-outpost deployments
  recommended over embedded for hardened installs? Unclear from
  inputs.

## Threat-class summary

| STRIDE | Surface count | High-impact items | Identity-security framing |
|--------|---------------|-------------------|---------------------------|
| Spoofing | 11 | S-1, S-2, S-3, S-4, S-6, S-7, S-9, S-10, S-11 | FAL bypass (S-1/-2/-3); IAL bypass (S-7); MITM (S-10, S-11) |
| Tampering | 6 | T-1, T-2, T-4, T-5, T-6 | Audit-trail tampering, Policy modification |
| Repudiation | 4 | R-2 | Audit-completeness (R-1, R-3); audit-immutability (R-2); actor-context (R-4) |
| Info Disclosure | 9 | I-3, I-8 | Token over-disclosure (I-1, I-4, I-5); enumeration (I-2, I-7); tenant leak (I-8) |
| DoS | 7 | D-1, D-2, D-3 | AAL bypass via brute-force (D-1, D-2); resource exhaustion (D-3, D-4, D-5, D-6, D-7) |
| EoP | 8 | E-1, E-2, E-3, E-4, E-7, E-8 | Sandbox escape (E-1); privilege injection (E-2, E-6); cross-tenant (E-3, E-5); confused deputy (E-4); credential broker (E-7); process-boundary (E-8) |

The high-impact threats cluster around three themes:

1. **The Expression engine** is documented arbitrary Python. Any
   permission-bearing actor who can create/edit Expressions has
   code execution on the Server. Hardening guide recommends
   blocking the write APIs at the reverse proxy.
2. **The CertificateKeyPair + secret_key architecture** localises
   all decryption to the per-installation `AUTHENTIK_SECRET_KEY`.
   Anything that exfiltrates secret_key + database snapshot =
   global secret unmasking.
3. **The Flow + Stage + Policy expressiveness** is also the
   admin-misconfiguration surface. A compromised admin can rewire
   authentication globally; default-flow modification is one
   transaction away from disabling MFA platform-wide.
