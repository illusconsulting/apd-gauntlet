# Home Assistant — System Overview for APD Security Review

> **Purpose.** Orientation brief for an APD-gauntlet security-architecture review of the
> Home Assistant ecosystem, reviewed across the **api-security** and **mobile-applications**
> domain packs with code reconnaissance over **23 separately-indexed repositories**. This
> document frames the system; the per-repo source-of-truth is the codebase-memory (CBM) graph
> of each repository (see `repos[]` in `.apd-run.yaml`). Specialists should ground findings in
> the CBM call-graph evidence and cite the design-intent docs in this `inputs/` set.

## What Home Assistant is

Home Assistant (HA) is a self-hosted, open-source home/building automation platform. A single
trusted Python **Core** process exposes a local-first REST + WebSocket API, runs 2,000+
in-process integrations that talk to devices and cloud services, and persists automation state
and history. Around Core sits an appliance/OS layer (**Operating System** + **Supervisor** +
**os-agent** + **plugins**) that manages the Core container, **add-ons** (arbitrary Docker
containers), backups, and host operations. Two **native mobile apps** (iOS, Android) and a
**web frontend** are the human-facing clients; a **push-relay** service brokers notifications.

The defining trust posture: **Core is a single, highly-privileged trust domain** — integrations
are not sandboxed from each other and run with Core's full privilege — and the **Supervisor/OS
layer is host-root-equivalent** (Docker socket + D-Bus host agent). The mobile apps are
**adversary-controllable clients** (binaries in users' hands, possibly on rooted/jailbroken
devices) that authenticate to Core over the network. Home Assistant is typically deployed on a
home LAN, optionally exposed to the internet via a reverse proxy or the Nabu Casa cloud relay.

## Repository map (23 indexed CBM projects)

### Backend / API surface (api-security pack)

| Repo | Role | What it is | Security relevance |
|------|------|-----------|--------------------|
| `core` | **primary** | HA Core — Python asyncio app. REST API (`/api/…`), WebSocket API (`/api/websocket`), auth subsystem (providers, users, groups, permissions, tokens), Recorder history DB, 2,000+ in-process integrations, `configuration.yaml` + `.storage/`. | The authoritative authentication, authorization, and business-rule enforcement point. Holds user credentials, all tokens, integration secrets, and the privacy-sensitive history DB. Integrations run unsandboxed in-process. |
| `supervisor` | dependency | Manages the HAOS install: add-on lifecycle (Docker containers), backups, Core container, updates, ingress proxy. Privileged Supervisor API at `http://supervisor/`. | Host-root-equivalent: holds the Docker socket; issues per-add-on scoped tokens; ingress injects `X-Remote-User-*` headers. The add-on→supervisor→Docker chain is a primary privilege-escalation surface. |
| `os-agent` | dependency | Go D-Bus daemon on HAOS exposing host operations (datadisk, AppArmor, system) to the Supervisor. | The bridge from container-land to host-root operations. |
| `operating-system` | dependency | HAOS — Buildroot-based minimal appliance Linux; the supported turnkey image. | Boot/update integrity, partition model, OS hardening floor. |
| `cli` / `plugin-cli` | dependency | The `ha` CLI and its plugin container; drives the Supervisor API. | Operator control plane to the privileged Supervisor API. |
| `plugin-dns` | dependency | CoreDNS plugin container (DNS for the HA network). | DNS interception / rebinding surface. |
| `plugin-audio` | dependency | PulseAudio plugin container. | Device/media surface. |
| `plugin-multicast` | dependency | Multicast / mDNS plugin container. | LAN discovery surface (instance_discovery). |
| `plugin-observer` | dependency | Health/observer plugin container. | Availability/observability plane. |
| `addons` | dependency | Official add-on collection; each is a Docker container with a `config.yaml` declaring API role, AppArmor, network/host access, image signing. | The third-party-code-on-the-host model. App-security ratings, protection mode, role grants. |
| `docker` / `docker-base` | dependency | Container build + base images (alpine/debian/ubuntu). | Supply-chain + base-image hardening floor. |
| `wheels` | dependency | Python wheel build infrastructure. | Build/supply-chain surface for Python deps. |

### Clients (mobile-applications + frontend)

| Repo | Role | What it is | Security relevance |
|------|------|-----------|--------------------|
| `iOS` | dependency | Native Swift iOS "Home Assistant Companion" app. Registers as a device via native-app-integration; tokens in iOS Keychain; APNS push; embeds the frontend in a WebView; location/sensors; biometric app-lock. | Adversary-controlled client: on-device token storage, Keychain/Secure-Enclave use, WebView/JS-bridge, deep links/Universal Links, push, biometric gating, embedded secrets. |
| `android` | dependency | Native Kotlin Android Companion app. Encrypted token storage; FCM push; WebView frontend; sensors/location; Wear OS + Android Auto surfaces. | Same client-trust split as iOS plus exported components/intents, App Links, Keystore/StrongBox. |
| `frontend` | dependency | Lit/TypeScript SPA served by Core; also rendered inside the mobile apps' WebViews. Talks WS + REST. | Browser/WebView token handling, external-auth bridge to native, XSS→token-theft surface, the JS bridge boundary. |
| `home-assistant-js-websocket` | peer | JS client library for the WS API (used by the frontend and other clients). | Auth handshake + connection lifecycle logic shared across clients. |
| `mobile-apps-fcm-push` | dependency | Cloud-Function push-relay that forwards notifications from HA instances to APNS/FCM **without** exposing device push tokens to the instance. | Holds push-routing trust; a notification-spoofing / token-confidentiality boundary between instances and the push providers. |
| `companion.home-assistant` | peer | Documentation site for the companion apps. | Design-intent reference (mobile auth, sensors, webhooks). |

### Documentation / governance

| Repo | Role | What it is |
|------|------|-----------|
| `architecture` | peer | Architecture Decision Records (ADRs 0001–0022): installation methods, container/OS/Core/Supervised topology, supported databases, Docker images. |
| `developers.home-assistant` | peer | Developer docs: REST/WS API, auth subsystem, native-app integration, supervisor API, app security. |
| `home-assistant.io` | peer | End-user docs incl. authentication and companion-app guides. |

## Authentication & authorization model (Core)

- **Auth providers** authenticate users (built-in homeassistant provider stores users in the
  config dir; also trusted-networks, command-line, legacy-api-password). Multiple instances
  per type are possible.
- **Credentials → Users → Groups → Permission policy.** The onboarding user is the **owner**
  (all permissions). Group membership grants permissions; a permission policy scopes resource
  access. (See `auth/auth_permissions.md`.)
- **Tokens.** An IndieAuth-style authorize flow yields an authorization code exchanged for an
  **access token** (short-lived) + **refresh token** (valid until deleted). Three refresh-token
  types: **Normal** (apps), **Long-Lived Access Token** (user-generated, long horizon),
  **System** (for HAOS/Supervisor system users; never exposed). Access tokens are presented as
  `Authorization: Bearer …` to REST/WS.
- **Supervisor / add-on auth.** Add-ons receive a `SUPERVISOR_TOKEN` and a declared **API role**
  (`default` < `homeassistant` < `backup` < `manager` < `admin`). **Protection mode** is on by
  default and must be explicitly disabled for elevated host rights. **Ingress** authenticates
  the user and injects `X-Remote-User-Id/Name/Display-Name` headers to the add-on.

## Trust boundaries (review focus)

1. **Internet/LAN → Core REST+WS API** — bearer-token auth; reverse-proxy or Nabu Casa relay; the primary external attack surface.
2. **Mobile app (untrusted, possibly rooted) → Core API** — client-to-backend; every authz/business rule must be server-enforced; client-side controls are defense-in-depth only.
3. **Browser/WebView frontend → Core WS/REST** — token in client storage; external-auth bridge into the native app; JS-bridge to native capability.
4. **Add-on container → Supervisor API & Core proxy** — scoped token + role; protection mode; AppArmor; the privilege-escalation chain toward the Docker socket.
5. **Supervisor → Docker socket (host root) & → os-agent (D-Bus host ops)** — the container-to-host-root boundary.
6. **Core integration → external device/cloud** — outbound LAN + internet; SSRF, credential storage, untrusted device/cloud responses.
7. **HA instance ↔ mobile-apps-fcm-push ↔ APNS/FCM** — push-routing confidentiality and notification integrity.
8. **Backup artifact ↔ storage/restore** — full snapshots contain secrets, tokens, and the history DB.

## Sensitive-data inventory (PII / secrets / privacy)

- **Credentials & tokens** — password hashes and auth records in `.storage/auth*`; refresh /
  access / long-lived / system tokens; `SUPERVISOR_TOKEN`; on-device tokens (Keychain/Keystore).
- **Integration secrets** — OAuth tokens, API keys, and device credentials for 2,000+
  integrations persisted in `.storage/` (cloud accounts, cameras, locks, alarms, energy, etc.).
- **History / state DB (Recorder)** — SQLite/MariaDB/PostgreSQL of entity state + history:
  **presence, geolocation, camera/voice events, lock/alarm state** — high-privacy home-occupancy
  data.
- **Location** — `device_tracker` + mobile-app GPS/zone data.
- **Mobile-cached PII** — entity state cached on device; biometric-gated app-lock secrets;
  push tokens; embedded app config.
- **Backups** — full snapshots (secrets + tokens + DB), frequently the weakest-protected copy.

## Deployment topologies (ADR 0012–0016)

- **Home Assistant OS** (appliance image; Supervisor + add-ons; the supported turnkey path).
- **Home Assistant Supervised** (Supervisor on a user-managed Debian host).
- **Home Assistant Container** (Core-only Docker; no Supervisor/add-ons).
- **Home Assistant Core** (bare Python venv).

The Supervisor/add-on/OS surface applies to OS + Supervised; the Container/Core surface is
Core-only. The mobile apps and frontend apply to all topologies.

## Review framing

- **api-security** → Core REST/WS API authn/authz and token lifecycle; Supervisor privileged
  API + add-on role model; integration-secret storage; Recorder DB exposure; backup artifacts;
  the add-on→supervisor→Docker→host-root escalation chain; SSRF via integrations; supply chain
  (add-ons, base images, wheels, npm/PyPI).
- **mobile-applications** → iOS + Android client trust split; on-device token/secret storage
  (Keychain/Keystore/StrongBox); WebView + JS-bridge; deep links / App Links / Universal Links /
  exported components; OTA/bundle integrity; biometric gating; push-relay confidentiality;
  embedded secrets recoverable from the IPA/APK; client-as-untrusted on the client→backend
  boundary.

Treat every client-side control as defense-in-depth behind a server-side invariant in Core.
Ground each finding in the relevant repo's CBM graph; this brief is orientation, not evidence.
