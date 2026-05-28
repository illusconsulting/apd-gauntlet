# Architecture Index — authentik

Service-by-service index for the authentik deployment. Each row is one
deployable component in the canonical docker-compose / Kubernetes
topology (per `install-config/install/docker-compose.mdx` and
`core/architecture.md`). Use this as the lookup table when correlating
findings to surfaces; the trust-boundary inventory follows the §3
inventory in `tech_plan.md`.

## Component index

### `server` (authentik Server)

- **Language / runtime:** Go router (statically compiled) +
  Django 5.2.x Core (Python 3.14) + TypeScript Lit static assets,
  all packaged in a single image (`ghcr.io/goauthentik/server`).
- **Role:** Public-facing identity authority. Serves the REST API,
  OAuth/OIDC endpoints, SAML endpoints, admin and user web UIs, the
  Flow executor, and an embedded proxy outpost. Listens on `:9000`
  (HTTP) and `:9443` (HTTPS) by default per the docker-compose
  install doc.
- **Inbound:** End-user browser; federated relying parties (OAuth
  clients, SAML SPs); outposts (over WebSocket); operators (Admin
  UI); enrolled API clients (Bearer-token-authenticated).
- **Outbound:** PostgreSQL (TCP/TLS); operator-configured Source
  IdPs (OAuth, SAML, LDAP, OIDC, SCIM, Plex, Kerberos,
  social-logins); SCIM-target endpoints (when authentik is the
  provisioning source); email transport (SMTP); Docker socket (when
  the Docker integration is enabled); Kubernetes API (when the K8s
  integration is enabled).
- **Datastores touched:** PostgreSQL (primary), optional Redis (if
  configured for sessions/cache/channels), `/data` filesystem
  (uploaded media), `/certs` (operator-imported certs),
  `/blueprints` (file-system blueprints), `/custom-templates`
  (operator overrides), optional S3 (via `django-storages[s3]`).
- **Trust boundary:** **Internet ↔ identity authority.** This is
  the highest-trust surface in the entire stack — compromise =
  cluster-wide identity bypass. Recommended posture per
  `install-config/reverse-proxy.md` is a TLS-terminating reverse
  proxy in front; the Server itself does not require TLS for inbound
  traffic but supports it.
- **Notable surface:**
  - REST API at `/api/v3/...` (Bearer-auth). Privileged subset per
    `security/security-hardening.md`:
    `/api/v3/policies/expression*`,
    `/api/v3/propertymappings*`,
    `/api/v3/managed/blueprints*`,
    `/api/v3/stages/captcha*` —
    operators are advised to block these at the reverse-proxy
    layer for hardened installs.
  - OAuth endpoints at `/application/o/...` (per the OAuth provider
    doc; cross-provider introspection/revocation requires
    Federated-Provider declaration).
  - SAML endpoints at `/application/saml/<slug>/` (unified SSO+SLO).
  - Flow executor at `/if/flow/<slug>/`.
  - Admin UI at `/if/admin/`; user UI at `/if/user/`.
  - WebSocket at `/ws/outpost/...` (outpost configuration push and
    healthcheck).
  - OpenAPI schema at `/api/v3/schema/`.
- **CertificateKeyPair material:** all signing / encryption keys for
  every Provider; first-startup self-signed `authentik Self-signed
  Certificate` (1-year validity) per `sys-mgmt/certificates.md`.

### `worker` (background task runner)

- **Language / runtime:** same image as the Server, started in a
  worker role (`ak worker`).
- **Role:** Executes background tasks: email send, event-notification
  dispatch, SCIM sync, Source sync (LDAP / SAML / OAuth scheduled
  re-fetch), scheduled outpost deployment, blueprint application,
  background data exports, certificate generation. Per
  `core/architecture.md`: "executes background tasks, such as
  sending emails, the event notification system, and everything you
  can see on the System Tasks page."
- **Inbound:** Task-queue dispatch from the Server (via
  `django-dramatiq-postgres`, Postgres-backed).
- **Outbound:** PostgreSQL; SMTP; Source IdPs (during sync); SCIM
  target endpoints; Docker socket (Docker integration); Kubernetes
  API (K8s integration); external HTTP for blueprint URL fetching;
  HIBP API (when the Password policy's HIBP check is enabled).
- **Datastores touched:** PostgreSQL; `/templates` (custom email
  templates per `core/architecture.md`); `/certs`.
- **Trust boundary:** **Background-task escalation surface.** Holds
  the same Postgres credentials and configuration as the Server, so
  any task-arbitrary-code path (expression-driven, blueprint-driven)
  has full data-plane reach. Email/SCIM/HTTP outbound is governed
  by the network-level egress controls noted in `SECURITY.md`.
- **Notable surface:** Per the certificates doc, certain
  certificate generation happens here. Per the SCIM provider doc,
  SCIM sync is per-100-objects batched to scale across multiple
  worker replicas. Per the events doc, notification-rule evaluation
  fires here.

### `postgresql` (PostgreSQL 14+)

- **Language / runtime:** PostgreSQL 14+ (the development compose
  uses `postgres:16`). Run as `docker.io/library/postgres:16` in
  `scripts/compose.yml`.
- **Role:** Primary persistence. All Users, Groups, Roles,
  Applications, Providers, Sources, Flows, Stages, Stage Bindings,
  Policies, Policy Bindings, Outposts, CertificateKeyPairs, Tokens,
  Sessions, Events, Notifications, Brands, Tenants, Blueprints, and
  the `django-dramatiq-postgres` task queue, plus the
  `django-postgres-cache` cache.
- **Inbound:** Server, Worker. Per `sys-mgmt/tenancy.md`, multi-tenant
  installs use schema-per-tenant via `django-tenants`.
- **Outbound:** None.
- **Datastores touched:** Self.
- **Trust boundary:** **Datastore boundary.** TLS to PostgreSQL is
  configurable per the install reference; not enforced by default.
  The `AUTHENTIK_SECRET_KEY` (set in `.env` per docker-compose
  install) is the symmetric key under which secret fields in the
  database are encrypted — see ADR-0004. Compromise of secret_key
  + database snapshot = mass unmasking of all stored secrets.
- **Notable surface:** Per `sys-mgmt/ops/backup-restore.md`, the
  documented backup posture is `pg_dump` / `pg_restore` /
  continuous-archiving. Backup encryption and offsite storage are
  operator-driven. Per the tenancy doc, the alpha multi-tenancy
  feature carries an explicit "Expression policies currently have
  access to all tenants" caveat — that is, the tenancy boundary is
  not fully enforced at the expression layer.

### `redis` (optional cache / channels / queue transport)

- **Language / runtime:** `redis:alpine` per the upstream
  docker-compose template.
- **Role:** Session cache, channels-layer pub/sub for WebSockets,
  and historically the Celery broker. In current versions the
  Postgres-backed alternatives (`django-postgres-cache`,
  `django-dramatiq-postgres`, `django-channels-postgres`) are
  workspace dependencies; Redis remains supported and configurable.
- **Inbound:** Server, Worker.
- **Outbound:** None.
- **Datastores touched:** Self (in-memory).
- **Trust boundary:** **In-cluster datastore.** Not authenticated
  by default in the bundled compose. **GAP** — the documentation
  does not enumerate which deployments require Redis vs. operate
  purely on Postgres-backed primitives; reviewers should confirm
  against the live install config.
- **Notable surface:** Anyone with network access to Redis can read
  every cached session and, if the channels layer is on Redis, every
  outpost-signaling WebSocket frame.

### `proxy-outpost`

- **Language / runtime:** Go (per `go.mod`: `github.com/gorilla/mux`,
  `github.com/gorilla/sessions`, `github.com/gorilla/websocket`,
  `github.com/coreos/go-oidc/v3`, `golang.org/x/oauth2`). Built from
  `internal/outpost/proxyv2/` (per Makefile).
- **Image:** `ghcr.io/goauthentik/proxy`.
- **Role:** Caddy-style forward-auth reverse-proxy for legacy
  applications. Sets per-user headers (`X-authentik-username`,
  `X-authentik-groups`, `X-authentik-entitlements`,
  `X-authentik-email`, `X-authentik-name`, `X-authentik-uid`) plus
  per-app meta-headers (`X-authentik-meta-outpost`, etc.) per
  `add-secure-apps/providers/proxy/index.md`.
- **Inbound:** End-user browser; protected app's reverse proxy
  (forward-auth mode). Listens on `:9000` (HTTP) and `:9443`
  (HTTPS).
- **Outbound:** Server (`/api/v3/...`, OAuth endpoints; per the
  Proxy provider doc, proxy uses OAuth client-credentials grant for
  authentication); WebSocket to Server (`/ws/outpost/...`) for
  config push.
- **Datastores touched:** None directly; relies on Server for all
  state.
- **Trust boundary:** **Trusted intermediary header-stamper.** The
  protected application trusts the `X-authentik-*` headers. Any
  request that bypasses the outpost (a misconfigured reverse-proxy
  ACL, an attacker pivoting onto the protected app's network)
  reaches the app without an authentik check — header-spoof risk.
- **Notable surface:** Unauthenticated-paths configuration is a
  regex allowlist applied per the operator config; mis-specified
  regex can over-expose. Per the proxy doc, in domain-level mode
  the regex matches against full URL; in single-application mode it
  matches against path only. Metrics on `:9300/metrics` are
  unauthenticated.

### `ldap-outpost`

- **Language / runtime:** Go (per `go.mod`: `beryju.io/ldap`,
  `github.com/go-ldap/ldap/v3`, `github.com/nmcclain/asn1-ber`).
  Built from `internal/outpost/ldap/`.
- **Image:** `ghcr.io/goauthentik/ldap`.
- **Role:** Exposes the authentik User and Group corpus as an LDAP
  backend for legacy applications that cannot speak modern
  federation. Listens on `:389` (LDAP) and `:636` (LDAPS).
- **Inbound:** Legacy LDAP clients. Bind mode is `direct` or
  `cached`; search mode is `direct` or `cached` per the LDAP
  provider doc.
- **Outbound:** Server REST API for bind (Flow execution) and
  search; WebSocket to Server for config push.
- **Datastores touched:** None; relies on Server for all state. The
  cached modes hold user/group data in outpost memory for the
  session-duration cache.
- **Trust boundary:** **Legacy-protocol re-exposure boundary.**
  Cached bind explicitly *does not* honor session revocation or
  credential changes during the cache lifetime — per the provider
  doc: "revoking sessions does not remove them from the outpost,
  and neither will changing a users credentials." This is a known
  trade-off.
- **Notable surface:** Code-based MFA via the bind password is
  available via `password;<code>` syntax; collides with passwords
  that legitimately contain a semicolon (documented). Pre-2024.8
  `Search group` was migrated to a `Search full LDAP directory`
  permission.

### `radius-outpost`

- **Language / runtime:** Go (per `go.mod`: `beryju.io/radius-eap`,
  `layeh.com/radius`). Built from `internal/outpost/radius/`.
- **Image:** `ghcr.io/goauthentik/radius`.
- **Role:** RADIUS authentication for network equipment (Wi-Fi,
  VPN concentrators, etc.). Supports EAP. Per the IncludeSec 2025-09
  audit, the Message-Authenticator validation had an inverted-logic
  bug that was initially fixed and then reverted pending broader
  client testing — the documented in-flight state in
  `prior-audit.md`.
- **Inbound:** RADIUS clients (NAS / Authenticators).
- **Outbound:** Server REST API for auth; WebSocket to Server for
  config push.
- **Datastores touched:** None.
- **Trust boundary:** **Shared-secret RADIUS.** Standard RADIUS
  shared-secret per RFC 2865 / 5176.

### `rac-outpost` (Enterprise)

- **Language / runtime:** Go (per `go.mod`: `github.com/wwt/guac`,
  the Apache Guacamole client library). Built from
  `internal/outpost/rac/`.
- **Image:** `ghcr.io/goauthentik/rac`.
- **Role:** Browser-mediated Remote Access Control. Brokers RDP /
  SSH / VNC sessions through Apache Guacamole between the user's
  browser (WebSocket) and the remote machine (native protocol).
- **Inbound:** End-user browser via WebSocket (proxied through the
  Server).
- **Outbound:** Remote target machines on their native protocols
  (RDP TCP/3389, SSH TCP/22, VNC TCP/5900-range); Server REST API +
  WebSocket for config push and connection lifecycle.
- **Datastores touched:** None; connection state in memory.
- **Trust boundary:** **Privileged credential broker.** Holds (via
  property mappings) the remote machine's username/password or
  SSH private key for the duration of the session. Per the RAC
  provider doc, "Ignore Server certificate" is a per-endpoint
  setting that suppresses RDP TLS verification — a hardening
  misstep if set.
- **Notable surface:** Bi-directional clipboard between user browser
  and remote machine, audio redirection from remote machine to
  browser. Connection settings merge across six precedence layers
  (default, provider, endpoint, provider mapping, endpoint mapping,
  flow plan) — see RAC provider doc §"Connection settings".

### `embedded-outpost` (within `server`)

- **Language / runtime:** Go, sharing the Server image.
- **Role:** Same as `proxy-outpost` but colocated with the Server
  to avoid a separate deployment for simple Proxy provider setups.
  Per `core/architecture.md`: "this outpost allows using Proxy
  providers without deploying a separate outpost."
- **Inbound:** Routed by the Server's lightweight Go router based on
  path / host.
- **Outbound:** Local Server (same process boundary in practice).
- **Trust boundary:** **In-process.** Inherits the Server's network
  posture.

### Web UI (`web/`)

- **Language / runtime:** TypeScript Lit components, built with
  esbuild / Vite. Served by the Server as static assets from the
  same image.
- **Role:** Admin interface, user interface, and Flow executor
  interface.
- **Inbound:** End-user browser.
- **Outbound:** Server REST API (`/api/v3/...`).
- **Datastores touched:** None.
- **Trust boundary:** **Client-side rendering of authentik state.**
  Per `security/security-hardening.md`, CSP is not natively set;
  operators are encouraged to set it via reverse proxy. Per the
  2024-11 Cobalt audit, SVG/HTML-injection paths were closed by
  adding DOMpurify to user-controlled name renderings.
- **Notable surface:** Prompt stages allow raw HTML per
  `SECURITY.md` (intentional). The Lit/Shadow-DOM pattern has a
  documented compatibility-mode toggle per Flow for password-manager
  support.

### Operator-controlled reverse proxy (recommended)

- **Language / runtime:** operator's choice (nginx, Caddy, Traefik,
  HAProxy, etc.).
- **Role:** TLS termination, optional CSP header, optional WAF,
  optional API-endpoint blocklist per `security/security-hardening.md`
  (`/api/v3/policies/expression*`, `/api/v3/propertymappings*`,
  `/api/v3/managed/blueprints*`, `/api/v3/stages/captcha*`).
- **Inbound:** Public internet.
- **Outbound:** Server (`:9000` / `:9443`).
- **Datastores touched:** None.
- **Trust boundary:** **First inbound TLS hop.** Per
  `install-config/reverse-proxy.md`, this is the recommended
  topology.

## Inter-component trust matrix

| From / To           | Server | Worker | Postgres | Redis | Proxy out | LDAP out | RADIUS out | RAC out | Source IdP | SCIM target |
|---------------------|--------|--------|----------|-------|-----------|----------|------------|---------|------------|-------------|
| End user (browser)  | TLS    | -      | -        | -     | TLS       | -        | -          | TLS (WS)| -          | -           |
| OAuth/SAML RP       | TLS    | -      | -        | -     | -         | -        | -          | -       | -          | -           |
| Server              | -      | task   | TCP/TLS  | TCP   | WS push   | WS push  | WS push    | WS push | HTTPS      | HTTPS       |
| Worker              | -      | -      | TCP/TLS  | TCP   | -         | -        | -          | -       | HTTPS      | HTTPS       |
| Proxy outpost       | HTTPS+WS| -     | -        | -     | -         | -        | -          | -       | -          | -           |
| LDAP outpost        | HTTPS+WS| -     | -        | -     | -         | -        | -          | -       | -          | -           |
| RADIUS outpost      | HTTPS+WS| -     | -        | -     | -         | -        | -          | -       | -          | -           |
| RAC outpost         | HTTPS+WS| -     | -        | -     | -         | -        | -          | -       | -          | -           |
| Legacy LDAP client  | -      | -      | -        | -     | -         | LDAP/LDAPS| -         | -       | -          | -           |
| NAS / RADIUS client | -      | -      | -        | -     | -         | -        | RADIUS     | -       | -          | -           |
| Protected app       | -      | -      | -        | -     | header    | LDAP     | -          | -       | -          | -           |
