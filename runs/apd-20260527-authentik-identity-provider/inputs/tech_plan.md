# authentik — Technical Plan

authentik is an **open-source Identity Provider (IdP) and Single
Sign-On (SSO) platform**. It centralises user authentication, MFA,
federation, OAuth 2.0 / OIDC / SAML / SCIM token issuance, an LDAP
backend, and a configurable authorization pipeline. This document is
the architect-facing description of what authentik is, how it is
deployed, where the trust boundaries fall, and which surfaces carry
identity-relevant security weight. Version under review: **2026.8.0-rc1**
(per `pyproject.toml`) / supported tracks **2025.2.x** and **2026.5.x**
(per `SECURITY.md`). License: **MIT** core, **CC BY-SA 4.0** docs,
**EE** for enterprise modules under `authentik/enterprise/`.

## 1. System purpose

authentik is the identity authority for a fleet of downstream
applications. Per `website/docs/index.mdx`, it is "an IdP and SSO
platform that is built with security at the forefront of every piece
of code and every feature." It is operated as a self-hostable
alternative to commercial IdPs (Okta, Auth0, Entra ID, Ping
Identity), and supports the following identity-protocol surfaces:

- **OAuth 2.0** (RFC 6749) including authorization-code, implicit,
  hybrid, client-credentials, device-code grants, with optional
  PKCE (RFC 7636).
- **OpenID Connect Core 1.0** layered over OAuth 2.0, including the
  discovery endpoint at
  `/application/o/<slug>/.well-known/openid-configuration` and a
  per-application JWKS endpoint.
- **SAML 2.0** with configurable signing certificates, optional SP
  signature verification, optional assertion encryption, and full
  IdP-initiated + SP-initiated bindings (Redirect, POST).
- **LDAP** acting as a backend directory for legacy applications that
  cannot speak modern federation protocols.
- **RADIUS** for network-equipment authentication.
- **SCIM 2.0** for outbound provisioning of authentik identities into
  downstream applications.
- **Proxy / forward-auth** for applications that lack native
  federation support, served by a Caddy-style forward-auth header
  protocol.
- **RAC** (Remote Access Control) for browser-mediated RDP / SSH /
  VNC sessions through Apache Guacamole.

authentik's distinguishing architectural choice is the **Flow + Stage
+ Policy** pipeline: every interactive authentication, enrollment,
recovery, or unenrollment journey is a configurable sequence of
stages, each gated by zero or more policies. This is the platform's
main expressiveness and its main attack surface.

## 2. Architecture

The server-side runtime is a small set of cooperating processes,
plus an arbitrary number of separately-deployed protocol outposts.
Per `website/docs/core/architecture.md`:

```
        user
         |
         v
+------------------+
| authentik Server | --+--> Core (Django, REST API, Flow executor,
|   (Go router +   |   |      OAuth/OIDC, SAML, all stage logic,
|   embedded outpost)  |      WebSocket pub/sub for outpost signaling)
+------------------+   |
                       +--> Embedded outpost (Proxy provider handler
                            colocated with Server; same image)
                       |
                       v
                  PostgreSQL  <---- Background Worker (Celery-style task
                                    runner: events, notifications, SCIM
                                    sync, Source sync, outpost lifecycle)
```

### Server (`authentik/server`)

The server container is a single binary (Go) that fronts two
sub-components on the same port:

- **Core** — Django 5.2.x application (Python 3.14, per
  `pyproject.toml`). Handles REST API (`/api/v3/...`), OAuth
  endpoints (`/application/o/...`), SAML endpoints
  (`/application/saml/...`), the admin and user web UIs (TypeScript
  Lit components served as static assets), Flow execution, Policy
  evaluation, and all stage logic. Served via `gunicorn` + `uvicorn`
  workers, with `django-channels` (and `django-channels-postgres` per
  workspace) providing WebSocket transport for outpost signaling.
- **Embedded outpost** — a colocated proxy-outpost so that Proxy
  providers work without a separate deployment. Has its own metrics
  endpoint on `:9300`.

A lightweight Go router (statically compiled into the same image)
performs the prefix-match routing between core, embedded outpost,
static assets, and the WebSocket upgrade path.

### Worker (`authentik/worker`)

The worker container runs background tasks (email send, event
notification dispatch, SCIM sync, Source sync, scheduled outpost
deployment, blueprint apply). It uses `django-dramatiq-postgres`
(per `pyproject.toml` workspace) — that is, a Postgres-backed task
queue rather than Redis, in current versions. (Older installs may
still reference a Celery + Redis path; the active dependency surface
is Postgres-backed.) The worker also drives the `dev-reset` /
`migrate` lifecycle commands (`lifecycle/migrate.py`,
`lifecycle/ak.py`).

### PostgreSQL

Primary persistence for all configuration, identity, audit, session,
and secret data. Per `core/architecture.md`: "authentik uses
PostgreSQL to store all of its configuration and other data
(excluding uploaded files)." The default deployment expects
PostgreSQL 14+ (the development compose uses `postgres:16`). Tenancy
(per `sys-mgmt/tenancy.md`) is implemented via `django-tenants`
PostgreSQL schemas — one schema per tenant.

### Cache and queue layer

`django-postgres-cache` (workspace) provides Postgres-backed cache
for short-lived items. Operators may still configure a Redis path
for sessions and cache via `AUTHENTIK_REDIS__*` settings, but the
default workspace dependencies favor PostgreSQL-backed primitives.
**GAP** — the boundary between "Postgres-backed by default" and
"Redis when configured" is not crisply described in the in-repo
documentation; reviewers should confirm against the active install
config before asserting which transport is in use.

### Outposts (separate deployment)

Per `add-secure-apps/outposts/index.mdx`, an outpost is "a single
deployment of an authentik component… that can be deployed anywhere
that allows for a connection to the authentik API." Four outpost
types exist:

- **Proxy outpost** — Caddy-style forward-auth listener (Go,
  `internal/outpost/proxyv2/`). Listens on `:9000` (HTTP) and `:9443`
  (HTTPS). Sets `X-authentik-username`, `X-authentik-groups`,
  `X-authentik-entitlements`, `X-authentik-email`, `X-authentik-name`,
  `X-authentik-uid`, plus configurable additional headers
  (`add-secure-apps/providers/proxy/index.md`).
- **LDAP outpost** — exposes the authentik user/group corpus as an
  LDAP backend on port 389 / LDAPS 636. Two bind modes: direct (per
  request) and cached (session-duration cache); two search modes:
  direct and cached. Goes via the same Flow + Stage + Policy
  pipeline as web logins (`add-secure-apps/providers/ldap/index.md`).
- **RADIUS outpost** — Go implementation of RADIUS authentication
  with EAP support (per `go.mod`: `beryju.io/radius-eap`,
  `layeh.com/radius`).
- **RAC outpost** — wraps Apache Guacamole (`github.com/wwt/guac`)
  to broker RDP / SSH / VNC sessions. Browser ↔ outpost is a
  WebSocket; outpost ↔ remote machine is the native protocol.

Each outpost authenticates to the Server via a **service-account
token** auto-generated at outpost creation; configuration is
streamed over WebSocket. Per the outpost docs: "Any change made to
the outpost's associated app or provider immediately triggers an
event to update the configuration data stored on the outpost, via
websockets. Websockets are used also by the outpost to send
healthchecks to the authentik Core."

### Web UI

TypeScript Lit components under `web/`, served as static assets
from the Server image. Two interfaces:

- **Admin interface** — Flow/Stage/Policy management, user/group
  administration, application/provider/source configuration, event
  inspection, system settings. Per `add-secure-apps/flows-stages/...`
  the Admin interface is itself behind an authentik Flow
  (`default-authentication-flow` by default).
- **User interface** — application launcher; user-settings flow.

The web build uses Lit + Shadow DOM. Per `flows-stages/flow/index.md`
there is a "compatibility mode" toggle on each Flow that disables
the Shadow DOM to accommodate password managers on mobile.

## 3. Trust boundaries

```
+------------+        +-----------------+        +--------------+
| Public     | -----> | Reverse proxy   | -----> | Server       |
| internet   |  TLS   | (operator-owned;|  HTTP  | (Django Core |
| (end user, |        | recommended per |  /9000 |  + embedded  |
|  attacker, |        | reverse-proxy.md)        |  outpost)    |
|  enrolled  |        +-----------------+        +------+-------+
|  service,  |                                          |
|  outpost)  |                                          | (TCP/TLS)
+------------+                                          v
                                                  +-----------+
                                                  | Postgres  |
                                                  | (per-     |
                                                  |  tenant   |
                                                  |  schemas) |
                                                  +-----+-----+
                                                        ^
                                                        |
+------------+        WebSocket (mTLS or         +------+-------+
| Outpost    | <----- token-signed)  ----------> | Worker       |
| (proxy /   |                                   | (background  |
|  LDAP /    |                                   |  tasks,      |
|  RADIUS /  |                                   |  Source sync,|
|  RAC)      |                                   |  SCIM sync,  |
+-----+------+                                   |  notify)     |
      |                                          +--------------+
      v
 protected app
 (Bearer header /
  LDAP bind /
  RADIUS Access-Request /
  Guac stream)
```

Boundary inventory:

1. **End-user browser → Server.** TLS-terminated at an
   operator-owned reverse proxy (per `install-config/reverse-proxy.md`,
   reverse-proxy fronting is the recommended posture). The Server
   itself listens on `:9000` (HTTP) and `:9443` (HTTPS) internally;
   the docker-compose default exposes those ports directly.
2. **Federated relying party → Server (OAuth / OIDC / SAML).** TLS
   to `/application/o/...` (OAuth) or `/application/saml/...`
   (SAML). The Server signs assertions / tokens with the
   per-provider signing certificate (RS256 default for OIDC; RSA-SHA256
   / ECDSA-SHA256 / digest configurable for SAML, per the SAML
   provider doc).
3. **Outpost → Server.** WebSocket (`/ws/outpost/.../`). The outpost
   authenticates with a service-account token issued by the Server
   at outpost creation. The outpost has read-only API permission
   scoped to its configured providers and certificates. **GAP** —
   the in-repo docs describe websocket signaling and a service-account
   token but do not enumerate whether the websocket is required to
   be over TLS in every deployment topology; reviewers should
   confirm from `lifecycle/` configuration.
4. **Outpost → protected app.** Native protocol: HTTP
   (proxy/forward-auth), LDAP/LDAPS (LDAP outpost), RADIUS (RADIUS
   outpost), or Guacamole-tunneled RDP / SSH / VNC (RAC outpost).
   The forward-auth headers are server-set; the protected app
   trusts them.
5. **Server → upstream IdP (Source).** When authentik acts as the
   relying party / consumer in federation, it makes outbound calls
   to the upstream IdP per the Source configuration (OAuth, SAML,
   LDAP, OIDC, SCIM, Plex, Kerberos, social-login providers). Per
   `SECURITY.md`: "Outgoing network requests are not filtered…
   these requests should be restricted at the network level using
   appropriate firewall or network policies." This is explicitly
   declared not-a-vulnerability by the project.
6. **Server → downstream SCIM endpoint.** When authentik is the
   provisioning source, it pushes user/group state to a configured
   SCIM 2.0 endpoint per `add-secure-apps/providers/scim/index.md`.
   Authentication is static-token (default) or OAuth (Enterprise).
7. **Worker → Docker / Kubernetes API.** When the
   Docker-integration or Kubernetes-integration is enabled, the
   Worker drives outpost lifecycle by calling the local Docker
   socket or the cluster API. Per
   `install-config/install/docker-compose.mdx`: "Mounting the Docker
   socket to a container comes with some inherent security risks."
   A Docker socket proxy is recommended but not required.
8. **All processes → PostgreSQL.** TCP (TLS if configured per the
   PostgreSQL configuration reference). Schema-per-tenant under
   `django-tenants`.

## 4. Authentication and sessions

### Interactive flow

User-interactive authentication is always a **Flow**. A Flow is a
named, ordered sequence of **Stage Bindings**, each of which can be
gated by a **Policy** (or by user/group binding). Per
`add-secure-apps/flows-stages/flow/index.md`, the default
authentication flow is:

```
Identification stage → (Password OR WebAuthn) → Authenticator validation → User Login
```

Stage types shipped (per `add-secure-apps/flows-stages/stages/`):

- `identification` — username/email/UPN prompt; can also gate by
  Source.
- `password` — hashed-password verification against the User
  record.
- `authenticator_validate` — MFA validation; supports TOTP, WebAuthn
  (FIDO2 via `fido2==2.2.0`), Duo (`duo-client==5.6.1`), static
  recovery codes, email-OTP, SMS-OTP (Twilio), Duo, endpoint
  device (Enterprise), GDTC (Enterprise).
- `authenticator_webauthn` — FIDO2 / passkey enrollment.
- `authenticator_totp`, `authenticator_sms`, `authenticator_static`,
  `authenticator_email`, `authenticator_duo`,
  `authenticator_endpoint_gdtc` — corresponding enrollment stages.
- `captcha` — pluggable CAPTCHA (Google reCAPTCHA, hCaptcha,
  Cloudflare Turnstile). Per `security-hardening.md`, the
  JavaScript-URL for the chosen provider can be modified, which is a
  noted hardening target.
- `consent` — OAuth scope consent prompt.
- `email` — sends an email (verification / recovery / notification).
- `prompt` — arbitrary form field; supports HTML rendering (per
  `SECURITY.md`: "Prompt HTML is not escaped" is an intentional
  design choice).
- `mtls` — mutual TLS client-certificate stage.
- `user_login`, `user_logout`, `user_write`, `user_delete` —
  session-mutating stages.
- `redirect` — redirect-only stage (with the constraint per
  `SECURITY.md` that open redirects without token leakage are
  declared not-a-vulnerability).
- `invitation` — invitation-code consumption.
- `source` — handoff to an external Source.
- `deny` — explicit deny terminal stage.
- `account_lockdown` (Enterprise, per `security/account-lockdown.md`)
  — single-action lockdown stage (deactivates user, voids password,
  revokes all sessions and tokens, emits audit event).

### Sessions

Sessions are stored in PostgreSQL (per `core/architecture.md`).
Session cookie scope and lifetime are configured per-Flow. The
`user_login` stage materialises the session; `user_logout` and the
`account_lockdown` stage tear it down. Per the Lockdown doc the
single-action Lockdown stage "Terminates all active sessions" and
"Revokes all tokens" including API, app password, recovery,
verification, and OAuth2 tokens and grants.

### MFA assurance

authentik does not expose a single AAL knob; assurance is composed
by the Flow author from the available authenticator-validate stage
configuration. A "high-assurance" Flow is one that requires WebAuthn
(possession + user-verification) plus a password (knowledge). The
`AuthnContextClassRef` SAML claim and the OIDC `acr` claim are
populated based on which authenticators the user actually used,
unless an explicit property mapping overrides (per the SAML and
OAuth provider docs).

### Account lockdown

Per `security/account-lockdown.md` (Enterprise, 2025.5+), the
account lockdown feature provides a single-action panic button that:

- Deactivates the user.
- Sets an unusable password.
- Terminates all active sessions.
- Revokes all API tokens, app passwords, recovery tokens,
  verification tokens, and OAuth2 grants.
- Creates an audit event with the operator-provided reason.

Self-service lockdown is supported via a Flow on the Brand.

## 5. Authorization model

Authorization in authentik happens at three layers:

1. **Application access.** Each Application has an access policy
   binding. The user must pass the binding (group/user/policy) to
   see the application in the launcher and to be issued a token for
   it. Per `add-secure-apps/applications/`, this is the coarse-grained
   "can this user reach this Provider at all" check.
2. **Flow-level policies.** A Flow can have pre-flow policies that
   deny the entire authentication attempt before any Stage runs.
3. **Stage-level policies.** Each Stage Binding can have a policy
   that conditionally skips, branches, or denies that specific
   Stage (e.g. "only present the MFA stage if the user is in
   `g_high_risk`").

Policy types (per `customize/policies/types/index.mdx`):

- **Event Matcher** — pattern-match against the Event audit stream.
- **Expression** — Python expression evaluated with a request /
  context / pending_user environment. The expression engine is the
  authentik power feature and the dominant escape-vector concern
  (see ADR-0001).
- **GeoIP** — country, ASN, impossible-travel checks using MaxMind
  GeoLite databases.
- **Password** — complexity, HIBP check (per
  `security/security-hardening.md` the default is NIST 800-63
  aligned).
- **Password Expiry** — fixed-day password expiration.
- **Password Uniqueness** (Enterprise) — block password reuse.
- **Reputation** — login-success / -failure scoring (per the
  IncludeSec 2025-09 audit, in 2025.12 session-based retry counters
  were replaced with reputation-driven counters).

Per the hardening doc, Expression policies are the privileged
surface: "Expression policies execute server-side Python inside
authentik. Treat the ability to create or edit them as a highly
privileged permission." The recommended hardening is to block
write access to `/api/v3/policies/expression*`,
`/api/v3/propertymappings*`, and `/api/v3/managed/blueprints*` at
the reverse proxy, forcing expression changes to come only via
on-disk blueprints.

### RBAC

Per `users-sources/access-control/` and `users-sources/roles/`,
authentik has a Django-Guardian-backed RBAC layer (per `pyproject.toml`:
`ak-guardian==3.2.0` workspace dependency). Roles bundle
permissions; permissions are object-level (e.g. "edit this specific
Provider"). The historical LDAP provider "Search group" was
migrated in 2024.8 to a `Search full LDAP directory` permission
that can be granted by Role (per the LDAP provider doc).

## 6. Token issuance

### OAuth 2.0 / OIDC

Per `add-secure-apps/providers/oauth2/index.mdx`:

- Endpoints: `/application/o/authorize/`, `/application/o/token/`,
  `/application/o/userinfo/`, `/application/o/revoke/`,
  `/application/o/introspect/`, `/application/o/device/`,
  `/application/o/<slug>/end-session/`,
  `/application/o/<slug>/jwks/`,
  `/application/o/<slug>/.well-known/openid-configuration`.
- Grant types: authorization-code, implicit (with the note that the
  OAuth Security BCP recommends against it), hybrid, client-credentials,
  device-code, refresh-token.
- Default scopes: `openid`, `profile`, `email`, `entitlements`,
  `offline_access`. authentik-specific: `goauthentik.io/api`.
  GitHub-compatible: `user`, `read:user`, `user:email`, `read:org`.
- Signing keys are per-Provider. JWTs are signed with the Provider's
  configured Signing Key (asymmetric RS256 default; clients verify
  via the per-application JWKS). If no Signing Key is selected,
  JWTs are HMAC-signed with the Provider's client secret — the
  symmetric-fallback surface.
- Optional JWE encryption: `RSA-OAEP-256` key wrapping plus
  `A256CBC-HS512` content encryption when an Encryption Key is
  configured on the Provider.
- `email_verified` claim defaults to `False` since 2025.10; prior
  versions defaulted to `True` regardless of actual verification
  state (per the OAuth provider doc, this was a known
  conservative-default tightening).

The token introspection / revocation endpoints are global; access
to tokens is scoped per Provider. Cross-Provider introspection
requires explicit Federated OAuth2/OpenID Providers selection.

### SAML

Per `add-secure-apps/providers/saml/index.md`:

- Endpoints: `/application/saml/<slug>/` (unified SSO + SLO),
  `/application/saml/<slug>/init/` (IdP-initiated),
  `/application/saml/<slug>/metadata/`. Legacy binding-specific
  endpoints remain available.
- Bindings: HTTP Redirect, HTTP POST. Operation type is detected
  from the SAML message.
- Signing certificates are per-Provider; algorithms RSA-SHA256 or
  ECDSA-SHA256; digest SHA-1 or SHA-256 (configurable). Note that
  SHA-1 is configurable but is widely deprecated — picking it is a
  hardening misstep.
- SP-side signature verification certificates and assertion
  encryption certificates are per-Provider (verification certificate
  for incoming SAML from SP; encryption certificate for outgoing
  assertions).
- NameID policy is configurable per-Provider, including
  Persistent (hashed user ID), x509-subject, Windows
  (UPN), Transient (session-bound), Email (with the warning in the
  doc that email-as-NameID is unstable because users can change
  their email).
- XML processing uses `lxml==6.1.1` + `xmlsec==1.3.17`. The
  `defusedxml==0.7.1` dependency is in `pyproject.toml`, which is
  the conventional Python posture against XXE / XML-bomb attacks.

### LDAP

Per `add-secure-apps/providers/ldap/index.md`:

- Base DN defaults `DC=ldap,DC=goauthentik,DC=io`; configurable per
  Provider.
- Users at `ou=users,<base>`; groups at `ou=groups,<base>`; each
  user has a virtual primary group at `ou=virtual-groups,<base>`.
- Standard LDAP attribute mapping (`cn`, `uid`, `uidNumber`, `mail`,
  `memberOf`, etc.); `ak-active` and `ak-superuser` booleans.
- LDAPS / StartTLS via per-Provider Certificate + TLS Server Name.
- Code-based MFA via the bind password: append `;<code>`. Note the
  outpost doc explicitly warns this can mis-fire if a password
  contains a semicolon.
- Cached search and cached bind modes — explicitly documented as
  *not* honoring session revocation or credential changes during
  the cache lifetime.

### RADIUS / RAC

RADIUS provider via the RADIUS outpost; RAC provider brokers
Guacamole sessions per `add-secure-apps/providers/rac/index.md`.

### SCIM provisioning

Per `add-secure-apps/providers/scim/index.md`, SCIM is outbound
provisioning (authentik → downstream app), authenticated with
static token (default) or OAuth (Enterprise). Sync triggers on
user/group write events and on a one-hour full reconcile cycle.
Compatibility modes for AWS, Slack, Salesforce, Webex, vCenter
adjust for vendor-specific SCIM dialects.

## 7. Federation (Source)

Per `users-sources/sources/`, a Source is an upstream identity
provider that authentik consumes. Source protocols supported:

- OAuth (generic OAuth 2.0 / OIDC)
- SAML
- LDAP (read-only or read-write directory sync)
- SCIM (inbound)
- Plex
- Kerberos (via `python-kadmin-rs==0.7.2`)
- Social-login (Apple, Discord, Twitch, Twitter, GitHub, GitLab,
  Google, Facebook, etc.)

Source attribute mapping is via Python expression property
mappings; the same expression engine that powers Policies. A
Source's User-write behaviour (create-on-first-login, link by
email, etc.) is configurable per Source. Per the SECURITY.md
notes, expressions execute arbitrary Python; the trust transitively
extends to anyone who can create / edit a Source property mapping.

## 8. Data model

Per the per-app structure under `authentik/` (visible via `pyproject.toml`
mypy override list), the principal models are:

- **User** — credentials, profile, attributes (free-form JSON).
- **Group** — hierarchical, with attributes (free-form JSON).
- **Role** — RBAC role; bundles object/permission grants.
- **Application** — façade for Providers; carries the access policy
  binding.
- **Provider** — protocol implementation (one per Application as a
  rule, with the backchannel-provider exception for SCIM-plus-SSO).
  Subtypes: OAuth2Provider, SAMLProvider, LDAPProvider,
  ProxyProvider, RadiusProvider, RACProvider, SCIMProvider, also
  `entra`, `gws`, `ssf`, `wsfed` (per the providers index).
- **Source** — upstream IdP; subtypes mirror provider list.
- **Flow** — named pipeline.
- **Stage** — pipeline step; ~25 subtypes (see §4).
- **Policy** — gating predicate; ~7 subtypes (see §5).
- **FlowStageBinding** — n-m between Flow and Stage with ordering
  and policy bindings.
- **PolicyBinding** — generic binding from Policy to target
  (Application, Flow, Stage, Source).
- **Outpost** — protocol-handler deployment; has service-account
  token; lists Provider associations.
- **CertificateKeyPair** — secret-bearing object; see ADR-0004.
- **Token** — API token, app password, recovery token, verification
  token. Distinguished by intent field.
- **Session** — Django session; user FK plus expiration plus
  authenticator info.
- **Event** — append-only audit record. Action, app, context (JSON),
  user, client_ip. Created by Flow execution, by direct API
  actions, and by `ak_create_event(...)` calls from Expression
  policies (per `expressions/reference/_functions.mdx`).
- **Notification, NotificationRule, NotificationTransport** —
  delivery of Event-triggered alerts.
- **Brand** — per-domain branding + default-flow selection (per
  `sys-mgmt/brands/index.md`).
- **Tenant** — Enterprise multi-tenancy; PostgreSQL schema-per-tenant
  via `django-tenants`. **GAP** — per `sys-mgmt/tenancy.md`, "This
  feature is in alpha. Use at your own risk." and "Expression
  policies currently have access to all tenants." is explicitly
  documented as a tenancy boundary leak risk.
- **Blueprint** — declarative configuration apply unit; can create
  any object type. Per `SECURITY.md` blueprints "can access all
  files on the filesystem" by design.

## 9. Persistence and storage

- **PostgreSQL** — primary store. Per `sys-mgmt/ops/backup-restore.md`:
  "The PostgreSQL database is the most important part of an
  authentik backup. Without it, authentik cannot be restored to a
  usable state." Standard `pg_dump` / `pg_restore` / continuous
  archiving are the documented backup approach. The reference
  configuration covers TLS, replicas, and pooler compatibility.
  Encryption-at-rest is operator's responsibility (filesystem
  encryption, volume encryption, etc.).
- **Cache / queue** — `django-postgres-cache` (Postgres-backed cache)
  and `django-dramatiq-postgres` (Postgres-backed task queue) per
  the `pyproject.toml` workspace. A Redis path is configurable for
  sessions / cache / channels but is not required by default.
- **File storage** — `/data` volume holds uploaded files (icons,
  flow backgrounds, CSV reports); `/certs` holds operator-imported
  TLS material; `/custom-templates` holds operator overrides;
  `/blueprints` holds on-disk blueprints. S3 external storage is
  supported via `django-storages[s3]==1.14.6`.
- **Secret material** — all secret-bearing objects (signing keys,
  encryption keys, OAuth client secrets, Source credentials,
  token-bound material) are stored in PostgreSQL via the
  `CertificateKeyPair` model and the secret-field cryptography in
  `authentik.crypto`. See ADR-0004 for the rotation surface.

## 10. API surfaces

- **REST API** at `/api/v3/...`, OpenAPI/Swagger schema at
  `/api/v3/schema/` (per `drf-spectacular==0.29.0`). Bearer token
  authentication (User-issued API tokens, App passwords,
  service-account tokens). The hardening doc identifies the
  Expression / PropertyMapping / Blueprint endpoints as the
  privileged subset to lock down.
- **OAuth endpoints** at `/application/o/...` (see §6).
- **SAML endpoints** at `/application/saml/...` (see §6).
- **WebSocket** at `/ws/...` for outpost signaling and for the
  admin UI's live updates.
- **Metrics** at `:9300/metrics` (Prometheus); per the outpost doc
  the metrics endpoint has no authentication and should not be
  exposed publicly.
- **Admin UI** at `/if/admin/`; user UI at `/if/user/`; Flow
  executor at `/if/flow/<slug>/`.

## 11. Known security posture (per documentation)

- **All secrets are encrypted at rest in PostgreSQL** via the
  `CertificateKeyPair` model + per-installation `AUTHENTIK_SECRET_KEY`
  (set in `.env` per the docker-compose install doc). Rotation is
  blueprint-driven.
- **WebAuthn / FIDO2 supported as MFA** via `webauthn==2.7.1`.
- **Expression engine runs server-side Python**. Per `SECURITY.md`:
  "Expressions (property mappings/policies/prompts) can execute
  arbitrary Python code without safeguards." This is **declared
  intentional**; the trust boundary is "any user with permission
  to create or modify objects containing expression fields can
  write code that is executed within authentik." Privilege
  escalation only counts as a vulnerability if it bypasses the
  permission check.
- **Blueprints can read any file on the filesystem** by design.
  Similarly declared intentional.
- **Prompt HTML is not escaped** by design; intentional to support
  rich interactive prompts.
- **Open redirects without token leakage** are declared
  not-a-vulnerability.
- **Outgoing network requests are not filtered** by authentik;
  network-level egress filtering is operator's responsibility.
- **Audit log retention defaults to 365 days** per
  `sys-mgmt/events/index.md`; configurable in System > Settings.
  Event forwarding is via container-stdout aggregation.
- **External pentests and audits**: Cure53 (2023-06), Cobalt
  (2024-11; 5 lows + 1 info, all fixed), IncludeSec (2025-09; 3
  highs of which 2 risk-accepted as intentional, 2 medium, 4 low,
  all fixed or risk-accepted). See `prior-audit.md` for the
  carried-forward posture.
- **CVE pipeline**: ~30+ assigned CVEs from 2022 through 2026, with
  per-CVE write-ups under `website/docs/security/cves/`. Notable
  patterns: API-authorization gaps (CVE-2024-42490), token-handling
  bugs, blueprint-induced exposure, RADIUS / LDAP outpost
  protocol-handler bugs.

## 12. Out of scope (for this review)

- Browser-class attacks on the Lit web UI (separate review).
- Supply-chain compromise of `python:3.14`, `postgres:16`,
  upstream Go modules (governed by `cargo deny` for Rust,
  `pyproject.toml` pinning for Python, `go.mod` pinning for Go,
  `package.json` pinning for the web).
- The Enterprise-tier-only features marked
  `authentik_enterprise: true` in their doc frontmatter (Account
  Lockdown, Password Uniqueness, Tenancy, RAC, Endpoint GDTC,
  SCIM-OAuth) are described for context, but the review focuses on
  the community surface.
- The specific Source social-login providers (Discord, Twitch,
  etc.) are catalogued but not individually re-audited; each is a
  pre-built OAuth Source.
