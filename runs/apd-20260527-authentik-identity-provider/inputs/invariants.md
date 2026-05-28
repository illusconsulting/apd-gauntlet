# authentik — Architect-Asserted Invariants

This is the architect's belief about what the system holds true,
based on the shipped documentation and the dependency posture.
Each entry pairs an invariant with the surface that should enforce
it and a note on whether the inputs confirm enforcement. Specialist
reviewers should validate each invariant against the inputs and
surface the gap where it exists. Several invariants are
**configuration-conditional** — they hold when the operator has
applied the recommended hardening, and not otherwise.

## Authentication and tokens

### INV-AUTH-001 — Every Flow execution emits at least one audit Event

- **Asserted in:** `sys-mgmt/events/index.md` ("Every event is
  logged, whether it is initiated by a user or by authentik.").
- **Enforced by:** the Flow executor's event emitter.
- **Reviewer note:** Holds for Flow-mediated actions. Per
  threat-model R-1, side-effecting Expression-policy helpers
  (`ak_send_email`, `ak_create_jwt`) do not auto-emit; the
  `ak_create_event` helper exists but is opt-in.

### INV-AUTH-002 — Per-Provider signing keys are isolated

- **Asserted in:** ADR-0004; OAuth provider doc (each Provider has
  its own Signing Key); SAML provider doc (each Provider has its
  own certificates).
- **Enforced by:** the `CertificateKeyPair` per-Provider FK in the
  Provider model.
- **Reviewer note:** Holds. Compromise of one Provider's signing
  key does not directly affect another's; both are individually
  encrypted under the master `AUTHENTIK_SECRET_KEY`. Compromise of
  secret_key compromises all.

### INV-AUTH-003 — OAuth tokens are signed with the per-Provider Signing Key

- **Asserted in:** OAuth provider doc ("JWTs created by authentik
  will always be signed").
- **Enforced by:** the OAuth2 Provider token-issuance code path.
- **Reviewer note:** Holds when Signing Key is configured. When
  Signing Key is **not** configured, the OAuth provider falls back
  to HMAC signing with the client_secret (per the doc) — see
  threat-model S-3. Operators relying on the fallback have a
  fundamentally weaker signing posture.

### INV-AUTH-004 — WebAuthn factors cannot be silently removed

- **Asserted in:** standard FIDO2 posture; implied by the
  Authenticator-WebAuthn stage's enrollment ceremony.
- **Enforced by:** the User Settings flow's authenticator-removal
  paths.
- **Reviewer note:** The default-user-settings-flow gates
  authenticator removal behind a re-authentication. **GAP** — the
  inputs do not explicitly assert "removing the last MFA factor
  requires proof-of-possession of an alternate factor." In
  out-of-the-box configurations a user with only one WebAuthn
  factor who loses it requires operator-mediated recovery
  (runbook §11).

### INV-AUTH-005 — Session lifetime, idle timeout, max-age are enforced per Flow

- **Asserted in:** the User Login stage configuration in
  `add-secure-apps/flows-stages/stages/user_login/`.
- **Enforced by:** the session cookie middleware bound to the User
  Login stage's settings.
- **Reviewer note:** Holds. Operators configure per-Flow.

### INV-AUTH-006 — MFA assurance is composed from authenticator types used

- **Asserted in:** the Authenticator Validation stage; the SAML
  AuthnContextClassRef populated from method used.
- **Enforced by:** the Flow executor and the SAML / OAuth claim
  generation paths.
- **Reviewer note:** Holds for downstream-claim-aware RPs. The
  platform does not expose a single AAL knob; the Flow author
  composes assurance from the available stages and the
  AuthnContextClassRef / `acr` claim is set accordingly.

## Authorization

### INV-AUTHZ-001 — Application access requires passing the Application's policy binding

- **Asserted in:** the Application model's policy_binding;
  `add-secure-apps/applications/`.
- **Enforced by:** the Application access gate before any Provider
  endpoint serves a request.
- **Reviewer note:** Holds. Per the SCIM provider doc, SCIM sync
  respects application access policies for filtering.

### INV-AUTHZ-002 — Expression / PropertyMapping / Blueprint edit is a privileged permission

- **Asserted in:** `security/security-hardening.md` ("Editing /
  creating these expressions is, by default, limited to super-users
  and any related events are fully logged.")
- **Enforced by:** the per-endpoint DRF permission class on the
  affected API routes.
- **Reviewer note:** Holds for the standard permission model.
  Per the IncludeSec H3 risk-acceptance, the corollary is that
  super-users have RCE on the Server host by design; hardening
  guidance recommends blocking the write API at the reverse proxy
  for stricter posture.

### INV-AUTHZ-003 — RBAC permissions are object-level

- **Asserted in:** `users-sources/roles/`,
  `users-sources/access-control/`.
- **Enforced by:** Django-Guardian (`ak-guardian==3.2.0` workspace
  member) and DRF view permission classes.
- **Reviewer note:** Holds. Roles bundle object-level permissions;
  service accounts can be scoped tightly per the
  `sys-mgmt/service-accounts.md` documentation.

### INV-AUTHZ-004 — Tenant boundaries isolate User and Group data

- **Asserted in:** `sys-mgmt/tenancy.md` (schema-per-tenant via
  `django-tenants`).
- **Enforced by:** `django-tenants==3.10.1` schema routing.
- **Reviewer note:** **Partially false in alpha.** Per the
  tenancy doc explicit caveat: "Expression policies currently
  have access to all tenants." See threat-model I-8 / E-3.

## Federation

### INV-FED-001 — Source attribute mapping cannot escalate to superuser without explicit operator decision

- **Asserted in:** standard SSO posture; implied by the Source
  property mapping discipline in the inputs.
- **Enforced by:** the Source property mapping author (operator).
- **Reviewer note:** **Not platform-enforced.** Per ADR-0001 and
  the SECURITY.md classification, property mappings are arbitrary
  Python; an operator who writes a mapping that sets
  `is_superuser=True` from an upstream attribute will see exactly
  that behavior. See threat-model S-7 / E-6.

### INV-FED-002 — SAML assertions are signed with the per-Provider signing certificate

- **Asserted in:** SAML provider doc ("A signing certificate
  allows authentik to digitally sign SAML assertions and
  responses").
- **Enforced by:** `xmlsec==1.3.17` invoked by the SAML provider
  code path.
- **Reviewer note:** Holds. Algorithm selection (RSA-SHA256 /
  ECDSA-SHA256, SHA-1 / SHA-256 digest) is per-Provider; SHA-1 is
  configurable and is a hardening misstep if chosen.

### INV-FED-003 — OAuth scope is enforced at token issuance and at protected-resource access

- **Asserted in:** OAuth provider doc.
- **Enforced by:** the OAuth2 token endpoint (scope reconciliation)
  and the userinfo endpoint (scope-filtered claim release).
- **Reviewer note:** Holds. Per the doc, scope-restriction at
  authorization time can be customised via an Expression policy
  bound to the Application that inspects
  `request.context["oauth_scopes"]`.

## Persistence and crypto

### INV-PERSIST-001 — All secret-bearing fields are encrypted at rest

- **Asserted in:** ADR-0004.
- **Enforced by:** `authentik.crypto` field-level encryption using
  `cryptography==48.0.0` keyed by `AUTHENTIK_SECRET_KEY`.
- **Reviewer note:** Holds for in-database storage. Operator
  responsibility for backup encryption (per
  `sys-mgmt/ops/backup-restore.md` — the doc does not enumerate
  dump-file encryption; backups inherit only the
  database-level encryption, which is the symmetric AES-GCM under
  the secret_key).

### INV-PERSIST-002 — `AUTHENTIK_SECRET_KEY` is process-env-resident, not in the database

- **Asserted in:** `install-config/install/docker-compose.mdx`
  (secret_key generated to `.env`).
- **Enforced by:** operator (`.env` is operator-managed; not in
  PostgreSQL).
- **Reviewer note:** Holds. Per ADR-0004 the corollary is that any
  process-env read (Expression engine, sidecar with shared env,
  host compromise) recovers it.

### INV-PERSIST-003 — All persistent state lives in PostgreSQL

- **Asserted in:** `core/architecture.md`,
  `sys-mgmt/ops/backup-restore.md`.
- **Enforced by:** the Django ORM with `django-tenants` schema
  routing.
- **Reviewer note:** Holds. File uploads live under `/data` and
  are separately backup-managed; everything else is in PostgreSQL.

## Outposts

### INV-OUTPOST-001 — Outposts authenticate to the Server via service-account tokens

- **Asserted in:** `add-secure-apps/outposts/index.mdx`.
- **Enforced by:** the WebSocket route's token validation.
- **Reviewer note:** Holds. Service-account permission scope is
  the outpost's configured Application/Provider pairs.

### INV-OUTPOST-002 — Outposts have no direct PostgreSQL access

- **Asserted in:** ADR-0003.
- **Enforced by:** outposts' Go binaries do not include a
  PostgreSQL client (per `go.mod`); they consume only the Server
  REST API and WebSocket. (Note: `gorm.io/driver/postgres` is in
  `go.mod` for the outpost-side session/state store via
  `gorm.io/gorm`; reviewers should confirm whether this is for
  outpost-local state or for shared-database access.)
- **Reviewer note:** **GAP** — `go.mod` lists
  `gorm.io/driver/postgres v1.6.0`, which suggests outpost-local
  PostgreSQL access for some outpost type (likely RAC for session
  persistence). Reviewers should confirm the boundary; the
  documentation states outposts go through the Server API for
  configuration but the GORM/PG dependency suggests an exception.

### INV-OUTPOST-003 — Cached LDAP outpost modes are documented to NOT honor session revocation

- **Asserted in:** LDAP provider doc.
- **Enforced by:** explicit operator opt-in.
- **Reviewer note:** Holds. The doc is candid: "revoking sessions
  does not remove them from the outpost, and neither will
  changing a users credentials."

## Operational

### INV-OPS-001 — Account Lockdown atomically deactivates user + sessions + tokens

- **Asserted in:** `security/account-lockdown.md`.
- **Enforced by:** the Account Lockdown stage (Enterprise, 2025.5+).
- **Reviewer note:** Holds for Enterprise installs. Community
  installs require the manual multi-step procedure in runbook §12.

### INV-OPS-002 — Event audit trail retention default is 365 days

- **Asserted in:** `sys-mgmt/events/index.md`.
- **Enforced by:** the System Settings retention configuration.
- **Reviewer note:** Holds for in-platform retention. Log
  forwarding is operator-driven; absent forwarding, the
  Postgres-resident Event records are mutable by anyone with
  database write (or per threat-model T-1, Expression engine
  RCE).

### INV-OPS-003 — Certificate rotation is supported but not enforced

- **Asserted in:** `sys-mgmt/certificates.md`.
- **Enforced by:** operator action; no enforced cadence.
- **Reviewer note:** Holds. The doc notes the default self-signed
  certificate is 1-year-valid and may need rotation for SPs that
  enforce expiry (Slack is cited).

### INV-OPS-004 — `AUTHENTIK_SECRET_KEY` rotation is supported via blueprint update

- **Asserted in:** ADR-0004 (reconstructed from the blueprint docs).
- **Enforced by:** operator action.
- **Reviewer note:** **GAP** — no rotation runbook ships in
  `sys-mgmt/` (see runbook §5). The capability exists; the
  procedure is undocumented.

### INV-OPS-005 — TLS for outpost-to-Server WebSocket

- **Asserted in:** standard production posture.
- **Enforced by:** operator network config + Server TLS setup.
- **Reviewer note:** **GAP** — `architecture.md` describes the
  WebSocket transport without enumerating whether TLS is mandatory
  vs. operator-configured. Reviewers should confirm against the
  active config.

### INV-OPS-006 — Outpost Prometheus metrics endpoint (`:9300/metrics`) is not exposed publicly

- **Asserted in:** outpost doc.
- **Enforced by:** operator network config.
- **Reviewer note:** Holds when the operator does not publish
  `:9300`. The compose default does not map it; Helm values do
  not enable a Service for it by default.

### INV-OPS-007 — Reverse proxy fronts authentik for production

- **Asserted in:** `install-config/reverse-proxy.md`.
- **Enforced by:** operator deployment choice.
- **Reviewer note:** Holds when the operator follows the
  recommendation. The Server can serve directly on `:9000` /
  `:9443` for development.
