---
title: 0003 — Separate Go-based outposts for legacy protocol handlers
status: accepted
date: 2020-10-01
---

# ADR-0003: Outpost architecture for legacy protocol handlers

- **Status:** Accepted
- **Date:** 2020-10-01 (approximate; corresponds to the
  introduction of the proxy outpost)

## Context

authentik supports federation protocols that are not HTTP:

- **LDAP** for legacy applications expecting a directory backend.
- **RADIUS** for network-equipment authentication (with EAP).
- **RDP / SSH / VNC** for remote-machine access (RAC, Enterprise).
- **Forward-auth headers** for legacy applications behind a
  reverse-proxy that cannot themselves consume OAuth/OIDC.

These protocols have three problems for a Django-Core implementation:

1. They are not HTTP. The Django request/response model doesn't
   apply.
2. Their performance characteristics (LDAP search, RADIUS auth,
   Guacamole tunneling) are sensitive to per-request CPU and
   network latency in ways that a Python WSGI process struggles to
   match.
3. They are often network-positioned closer to the protected
   application than to the Server (Wi-Fi controller deep in a
   branch office; a legacy app in a DMZ; a remote-desktop target
   in a customer's network).

A separate, language-appropriate component for each protocol
addresses all three.

## Decision

Implement a family of **Go-based outposts**, each handling one
protocol family, distinct from the Django Server core:

- **Proxy outpost** — Caddy-style forward-auth listener
  (`internal/outpost/proxyv2/`).
- **LDAP outpost** — LDAP/LDAPS server
  (`internal/outpost/ldap/`).
- **RADIUS outpost** — RADIUS server with EAP support
  (`internal/outpost/radius/`).
- **RAC outpost** — Apache Guacamole client broker (Enterprise,
  `internal/outpost/rac/`).
- **Embedded outpost** — proxy outpost colocated in the Server
  image to simplify simple Proxy provider deployments.

Each outpost is a Go binary built from `go.mod`, with its own image
(`ghcr.io/goauthentik/proxy`, `ldap`, `radius`, `rac`). Outposts
are deployed separately from the Server, anywhere with network
reachability to the Server's API.

Each outpost:

- Authenticates to the Server with a **service-account token**
  auto-generated at outpost creation.
- Receives configuration from the Server over a **WebSocket
  channel** (`/ws/outpost/...`).
- Sends healthchecks back to the Server over the same WebSocket.
- Exposes its own Prometheus metrics at `:9300/metrics` (per the
  outpost doc, unauthenticated and not for public exposure).

Per `add-secure-apps/outposts/index.mdx`: "An outpost is given
permissions to access the authentik API using a service account
and token, both of which are auto-generated when you create a new
outpost. The outpost is granted rights to only the
application/provider pairs configured."

## Consequences

**Positive.**

- Per-protocol language fit. Go's concurrency model suits LDAP
  search load, RADIUS UDP servers, and Guacamole's WebSocket-bridged
  tunneling far better than CPython.
- Outposts can deploy where they are needed. An LDAP outpost in a
  DMZ talks to legacy apps over the local network and to the
  Server over HTTPS+WS; the legacy apps never see Server traffic.
- Failure isolation. An outpost crash does not take down the
  Server. A Server restart does not require simultaneously
  restarting every outpost.
- The forward-auth pattern allows legacy applications to gain
  authentik authentication via a reverse-proxy ACL plus the
  per-user `X-authentik-*` headers, with no application-side code
  change.

**Negative / trade-offs.**

- **The outpost-to-Server trust boundary is a critical hop.** The
  service-account token authorises the outpost to read its
  provider configuration — which includes the OAuth client secret
  for the associated Provider. A leaked outpost token (from
  container env, from a backup, from a misconfigured CI) gives
  an attacker that Provider's client secret (see threat-model S-6).
- **Outpost code paths are separate from Core.** Bugs in
  outpost-side protocol handlers (e.g. the IncludeSec 2025-09 I1
  finding on RADIUS Message-Authenticator validation logic — see
  `prior-audit.md`) are independent of Core security. The
  outpost release cadence is tracked separately from Core (per
  the README badges: `ci-outpost.yml` vs. `ci-main.yml`).
- **Cached modes (LDAP-cached-bind, LDAP-cached-search) break the
  session-revocation invariant.** Per the LDAP provider doc:
  "Sessions are saved independently, meaning that revoking sessions
  does *not* remove them from the outpost, and neither will
  changing a users credentials." Operators who choose cached mode
  for performance trade away session revocation for the cache
  duration.
- **The forward-auth header model trusts the outpost.** The
  protected application reads `X-authentik-username` and treats it
  as authoritative. Any request that bypasses the outpost
  (network-policy mistake, reverse-proxy ACL gap, attacker pivot
  onto the app's network) reaches the app without an authentik
  check — and the app cannot tell.
- **`Ignore Server certificate` on RAC endpoints** suppresses TLS
  verification of the RDP target (see threat-model S-11). A
  hardening misstep at the property-mapping layer disables RDP
  authentication of the remote server entirely.
- **The Prometheus metrics endpoints at `:9300/metrics` are
  unauthenticated.** Per the outpost doc, "This endpoint is not
  mapped via Docker, as the endpoint doesn't have any
  authentication." An operator accidentally exposing it leaks
  per-Application volumetric metrics.

**Invariants pinned by this ADR (intended, not all enforced).**

- Outposts authenticate to the Server via service-account tokens.
- Outposts have no direct PostgreSQL access; all state is via the
  Server's REST API and WebSocket.
- Outpost configuration is push-only from the Server, over
  WebSocket.
- Outpost service-account permission scope is the configured
  Application/Provider pairs plus their certificates.

## Enforcement

- `go.mod` defines the outpost dependency surface
  (`beryju.io/ldap`, `beryju.io/radius-eap`, `github.com/wwt/guac`,
  etc.).
- The outpost-create flow in the Server auto-issues the
  service-account token (per the outpost doc).
- The Server's WebSocket route (`/ws/outpost/...`) authenticates
  the connection by token before propagating configuration.

## Notes

The embedded-outpost variant is a compromise: the Proxy provider's
forward-auth listener is colocated with the Server in the same
image, allowing simple deployments without a second container. The
trade-off is that the embedded outpost does not benefit from the
process-isolation that a separate outpost provides — a bug in the
embedded outpost's HTTP handler lands in the Server process
address space (see threat-model E-8).
