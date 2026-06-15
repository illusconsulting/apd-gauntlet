---
framework_version: 1.7.0
run_id: apd-20260612-home-assistant
domain_pack: { name: "api-security+mobile-applications", version: 1.7.0 }
artifacts:
  # --- orientation ---
  - { filename: 00-SYSTEM-OVERVIEW.md, type: tech_plan }
  # --- architecture / ADRs (peer repo: architecture) ---
  - { filename: architecture/architecture-overview.md, type: tech_plan }
  - { filename: architecture/dev-core.md, type: tech_plan }
  - { filename: architecture/dev-devices-and-services.md, type: tech_plan }
  - { filename: architecture/adr/0001-record-architecture-decisions.md, type: adr }
  - { filename: architecture/adr/0002-minimum-supported-python-version.md, type: adr }
  - { filename: architecture/adr/0003-monitor-condition-and-data-selectors.md, type: adr }
  - { filename: architecture/adr/0004-webscraping.md, type: adr }
  - { filename: architecture/adr/0005-code-formatting.md, type: adr }
  - { filename: architecture/adr/0006-docker-images.md, type: adr }
  - { filename: architecture/adr/0007-integration-config-yaml-structure.md, type: adr }
  - { filename: architecture/adr/0008-code-owners.md, type: adr }
  - { filename: architecture/adr/0009-translations-2.0.md, type: adr }
  - { filename: architecture/adr/0010-integration-configuration.md, type: adr }
  - { filename: architecture/adr/0011-discovery-requires-unique-id.md, type: adr }
  - { filename: architecture/adr/0012-define-supported-installation-method.md, type: adr }
  - { filename: architecture/adr/0013-home-assistant-container.md, type: adr }
  - { filename: architecture/adr/0014-home-assistant-supervised.md, type: adr }
  - { filename: architecture/adr/0015-home-assistant-os.md, type: adr }
  - { filename: architecture/adr/0016-home-assistant-core.md, type: adr }
  - { filename: architecture/adr/0017-hardware-screening-os.md, type: adr }
  - { filename: architecture/adr/0018-supported-databases.md, type: adr }
  - { filename: architecture/adr/0019-GPIO.md, type: adr }
  - { filename: architecture/adr/0020-minimum-supported-python-version.md, type: adr }
  - { filename: architecture/adr/0021-YAML-integration-configuration-deprecation-policy.md, type: adr }
  - { filename: architecture/adr/0022-integration-quality-scale.md, type: adr }
  # --- API surface (developers docs) ---
  - { filename: api/rest.md, type: other }
  - { filename: api/websocket.md, type: other }
  - { filename: api/instance_discovery.md, type: other }
  - { filename: api/native-app-integration.md, type: other }
  - { filename: api/native-app/setup.md, type: other }
  - { filename: api/native-app/webview.md, type: other }
  - { filename: api/native-app/sensors.md, type: other }
  - { filename: api/native-app/sending-data.md, type: other }
  - { filename: api/native-app/notifications.md, type: other }
  - { filename: api/supervisor/endpoints.md, type: other }
  - { filename: api/supervisor/models.md, type: other }
  - { filename: api/supervisor/examples.md, type: other }
  # --- auth subsystem (developers docs) ---
  - { filename: auth/auth_index.md, type: other }
  - { filename: auth/auth_api.md, type: other }
  - { filename: auth/auth_auth_module.md, type: other }
  - { filename: auth/auth_auth_provider.md, type: other }
  - { filename: auth/auth_permissions.md, type: other }
  - { filename: auth/api_lib_auth.md, type: other }
  - { filename: auth/frontend-external-authentication.md, type: other }
  - { filename: auth/io-authentication.md, type: other }
  # --- mobile + supervisor security ---
  - { filename: mobile/supervisor-apps-security.md, type: other }
  - { filename: mobile/iOS-README.md, type: other }
  - { filename: mobile/iOS-CLAUDE.md, type: other }
  - { filename: mobile/android-README.md, type: other }
  - { filename: mobile/android-CLAUDE.md, type: other }
  - { filename: mobile/mobile-apps-fcm-push-README.md, type: other }
  - { filename: mobile/companion-README.md, type: other }
  - { filename: mobile/companion-CLAUDE.md, type: other }
  # --- repo orientation ---
  - { filename: repos/core-README.rst, type: other }
  - { filename: repos/core-CLAUDE.md, type: other }
  - { filename: repos/core-AGENTS.md, type: other }
  - { filename: repos/supervisor-README.md, type: other }
  - { filename: repos/supervisor-CLAUDE.md, type: other }
  - { filename: repos/frontend-README.md, type: other }
  - { filename: repos/frontend-CLAUDE.md, type: other }
  - { filename: repos/js-websocket-README.md, type: other }
  - { filename: repos/os-agent-README.md, type: other }
  - { filename: repos/operating-system-README.md, type: other }
  - { filename: repos/cli-README.md, type: other }
  # --- infra (Dockerfiles + add-on config) ---
  - { filename: infra/docker-Dockerfile, type: iac }
  - { filename: infra/docker-base-alpine-Dockerfile, type: iac }
  - { filename: infra/docker-base-debian-Dockerfile, type: iac }
  - { filename: infra/supervisor-Dockerfile, type: iac }
  - { filename: infra/operating-system-Dockerfile, type: iac }
  - { filename: infra/core-Dockerfile, type: iac }
  - { filename: infra/addon-mosquitto-config.yaml, type: iac }
  - { filename: infra/addon-mosquitto-build.yaml, type: iac }
  # --- governance ---
  - { filename: org/SECURITY.md, type: other }
---

# APD Gauntlet Context Brief — Run `apd-20260612-home-assistant`

> Produced by `apd-intake` from the artifacts in `runs/apd-20260612-home-assistant/inputs/`.
> All specialist agents consume this brief. Do not paraphrase; refer back here for canonical references.
>
> **Code recon is enabled.** A separate `apd-code-recon` pass will add
> `00-context/code-evidence-index.yaml` and `00-context/code-architecture-brief.md`
> across the 23 indexed CBM projects. This brief inventories the **document
> artifacts and the declared surface only** — every finding must still be grounded
> in real call-graph evidence per the run config, not in design-doc intent.

**Run id:** `apd-20260612-home-assistant`
**Subject:** Home Assistant ecosystem (Core + Supervisor/OS + iOS/Android Companion + frontend + push relay)
**Date:** 2026-06-12
**Artifact count:** 74
**Artifact types observed:** tech_plan, adr, iac, other
**Domains:** `api-security` (declared-order primary), `mobile-applications`
**CBM repos:** 23 (1 primary `core`, 14 dependency, 8 peer)

---

## 1. Artifact Index

| Filename | Type | Pages/Lines | Notes |
|----------|------|-------------|-------|
| `00-SYSTEM-OVERVIEW.md` | tech_plan | 131 lines | **Anchor artifact** — authored orientation brief: system framing, repo map, auth/authz model, 8 trust boundaries, sensitive-data inventory, deployment topologies, review framing |
| `architecture/architecture-overview.md` | tech_plan | — | Core architecture narrative (`architecture` repo) |
| `architecture/dev-core.md` | tech_plan | — | Core internals dev doc |
| `architecture/dev-devices-and-services.md` | tech_plan | — | Devices & services (integration model) dev doc |
| `architecture/adr/0001…0022-*.md` | adr | 22 files | ADRs: installation methods (0012–0016), Docker images (0006), supported databases (0018), GPIO (0019), config-yaml structure, quality scale. Topology/supply-chain design intent |
| `api/rest.md` | other | 878 lines | REST API reference: `/api/` endpoints, all bearer-token auth, `/api/states` (read/write), `/api/services/<domain>/<service>` (control), `/api/history`, `/api/template`, `/api/config` (leaks lat/long, config_dir) |
| `api/websocket.md` | other | 120+ lines | WS API: `auth_required`→`auth`→`auth_ok` handshake; access-token auth; command phase with `user_id` context |
| `api/instance_discovery.md` | other | 36 lines | mDNS/Zeroconf `_home-assistant._tcp.local.` advertisement; TXT props (uuid, internal/external_url) |
| `api/native-app-integration.md` | other | 12 lines | Native-app integration intro (connect/auth, send location, call services, webview) |
| `api/native-app/setup.md` | other | 80+ lines | Device registration: IndieAuth OAuth2; `POST /api/mobile_app/registrations`; returns `webhook_id`, `secret`, `cloudhook_url` |
| `api/native-app/{webview,sensors,sending-data,notifications}.md` | other | 4 files | WebView control, sensor reporting, webhook data send (+encryption), push notifications |
| `api/supervisor/{endpoints,models,examples}.md` | other | 3 files | Privileged Supervisor API: `SUPERVISOR_TOKEN` bearer; `/addons`, `/host/logs`, etc. |
| `auth/auth_index.md` | other | 52 lines | Auth model: providers→credentials→users→groups→permission policy; owner=all; 3 refresh-token types (Normal/Long-Lived/System) |
| `auth/auth_api.md` | other | — | IndieAuth authorize flow, token endpoints, revocation |
| `auth/{auth_auth_module,auth_auth_provider}.md` | other | 2 files | Auth module (MFA/TOTP) + auth provider internals |
| `auth/auth_permissions.md` | other | 60+ lines | Permission policy structure (entities/domains/entity_ids; read/control/edit); **flagged experimental "not enforced yet"** |
| `auth/api_lib_auth.md` | other | — | Client-library auth helper |
| `auth/frontend-external-authentication.md` | other | 90+ lines | **JS external-auth bridge**: `window.externalAppV2`/`webkit.messageHandlers`; token passed from native to WebView frontend; callback-name forgery warning |
| `auth/io-authentication.md` | other | — | End-user authentication docs (`home-assistant.io`) |
| `mobile/supervisor-apps-security.md` | other | 48 lines | Add-on API roles (`default<homeassistant<backup<manager<admin`); protection mode; ingress `X-Remote-User-*` header injection; image signing (Cosign) |
| `mobile/iOS-README.md` / `mobile/iOS-CLAUDE.md` | other | 2 files | iOS Companion: Swift, WKWebView, Keychain, CocoaPods, fastlane signing, `Current` DI |
| `mobile/android-README.md` / `mobile/android-CLAUDE.md` | other | 2 files | Android Companion: Kotlin, WebView external bus, Room DB, EncryptedSharedPreferences/Keystore, FCM, `homeassistant://` deep links, Wear/Auto, server-sent commands |
| `mobile/mobile-apps-fcm-push-README.md` | other | 47 lines | Push relay: Firebase Cloud Functions; `firebase deploy`; forwards notifications without exposing device push tokens to instance |
| `mobile/companion-README.md` / `mobile/companion-CLAUDE.md` | other | 2 files | Companion-app docs site orientation |
| `repos/*-README*.md` / `repos/core-AGENTS.md` | other | 11 files | Per-repo orientation (core, supervisor, frontend, js-websocket, os-agent, operating-system, cli) |
| `infra/*-Dockerfile` | iac | 6 files | Container builds: core, supervisor, operating-system, docker, docker-base (alpine/debian). Base-image + wheels supply-chain floor |
| `infra/addon-mosquitto-config.yaml` / `…-build.yaml` | iac | 2 files | Add-on manifest: `auth_api: true`, `map: [ssl, share]`, exposed ports, `startup: system`, plaintext logins option |
| `org/SECURITY.md` | other | 6 lines | Security-policy pointer (links to website); **no embedded vuln-disclosure or hardening content** |

> **Type note.** The API/auth/mobile/repo docs are developer reference documentation, not a single architectural change-plan; they are classified `other` (the taxonomy has no `reference_doc` type). The authored `00-SYSTEM-OVERVIEW.md` plus the `architecture/` narratives serve as the `tech_plan` anchor set. Dockerfiles and the add-on manifest are `iac`.

---

## 2. Capability and Surface Summary

**What is being reviewed.**
This is not a single-feature change review — it is a **whole-ecosystem architecture review** of the Home Assistant self-hosted home-automation platform across two lenses (`api-security`, `mobile-applications`). The defining trust posture, stated verbatim in `00-SYSTEM-OVERVIEW.md` lines 20-22: *"Core is a single, highly-privileged trust domain — integrations are not sandboxed from each other and run with Core's full privilege — and the Supervisor/OS layer is host-root-equivalent (Docker socket + D-Bus host agent)."* The mobile apps are *"adversary-controllable clients … possibly on rooted/jailbroken devices"* (lines 23-24). The system is *"typically deployed on a home LAN, optionally exposed to the internet via a reverse proxy or the Nabu Casa cloud relay"* (lines 24-25). The review boundary is the full surface: Core REST/WS API and auth/token lifecycle; the Supervisor privileged API + add-on role model + the add-on→supervisor→Docker→host-root escalation chain; integration secret storage and SSRF; the Recorder history DB; backup artifacts; both native mobile clients and their on-device secret stores, WebView/JS-bridge, deep links, and the push relay; the supply chain (base images, wheels, npm, add-on images).

**In-scope components.**
- **HA Core** (`core`, primary) — REST API (`/api/`, port 8123), WebSocket API (`/api/websocket`), auth subsystem (providers/users/groups/permission policy/tokens), Recorder history DB, 2000+ unsandboxed in-process integrations, `.storage/` + `configuration.yaml`.
- **Supervisor** (`supervisor`) — add-on lifecycle, ingress proxy, backups, Core container mgmt, privileged API at `http://supervisor/`; holds Docker socket; injects `X-Remote-User-*`.
- **os-agent** (`os-agent`) — Go D-Bus host daemon (datadisk/AppArmor/system) — container→host-root bridge.
- **Operating System / plugins** (`operating-system`, `plugin-{cli,dns,audio,multicast,observer}`, `cli`) — HAOS appliance + supervisor plugin containers + `ha` CLI control plane.
- **Add-ons** (`addons`) — third-party Docker containers with `config.yaml` role/AppArmor/signing.
- **iOS Companion** (`iOS`) — Swift, WKWebView, Keychain, APNS, biometric app-lock, deep/Universal links.
- **Android Companion** (`android`) — Kotlin, WebView external bus, Room DB, Keystore/EncryptedSharedPreferences, FCM, `homeassistant://` deep links, Wear OS + Android Auto, server-sent commands.
- **Frontend** (`frontend`, `home-assistant-js-websocket`) — Lit/TS SPA served by Core, embedded in mobile WebViews; JS external-auth bridge to native.
- **Push relay** (`mobile-apps-fcm-push`) — Firebase Cloud Functions forwarding notifications to APNS/FCM.
- **Supply chain** (`docker`, `docker-base`, `wheels`) — container build + base images + Python wheel infra.

**Out-of-scope components mentioned in artifacts.**
- **Nabu Casa cloud relay** — named as the optional internet-exposure path (`00-SYSTEM-OVERVIEW.md` line 25, `api/native-app/setup.md` `cloudhook_url`), but the Nabu Casa cloud service itself is not in the `repos[]` set; treated as an external dependency, not a reviewed component.
- **APNS / FCM push providers** — terminal external push endpoints; the relay is in scope, the providers are not.
- **Individual third-party integrations** (of the 2000+) — the integration *runtime/model* is in scope; specific vendor integrations are not individually enumerated.

**External systems touched.**
- Nabu Casa cloud relay / cloudhook (remote access).
- APNS (Apple) + FCM (Google/Firebase) push providers, via the Firebase Cloud Functions relay.
- External devices + cloud services reached by integrations (outbound LAN + internet; SSRF surface).
- Container registries / PyPI / npm / GitHub Actions (supply chain).
- mDNS/Zeroconf LAN discovery.

**Data classes in flow.** (PHI-equivalent here = high-privacy home-occupancy/geolocation data — see §3.)
- **Secrets/credentials** — password hashes + MFA/TOTP seeds (`.storage/auth*`); refresh/access/long-lived/system tokens; `SUPERVISOR_TOKEN`; integration OAuth tokens/API keys/device creds; on-device tokens (Keychain/Keystore); mTLS client key; bundled Firebase config secrets; app signing identity.
- **Privacy-sensitive home telemetry** — Recorder history of entity state: presence, geolocation/zones, camera/voice events, lock/alarm state.
- **PII** — `person`/`device_tracker` GPS + zone data; on-device location/entity caches; ingress-injected user identity headers.
- **Operational/config** — `configuration.yaml`, add-on options, logs/logbook, instance lat/long in `/api/config`.

**User personas.**
- **Owner** — onboarding user, always all permissions (`auth_index.md` lines 27-29).
- **Non-admin / low-privilege user** — group-scoped permission policy (BOLA/IDOR target surface on `entity_id`/`device_id`).
- **Long-Lived Access Token holder** — user-generated long-horizon API client.
- **Add-on / app principal** — `SUPERVISOR_TOKEN` + declared API role.
- **Ingress-authenticated user** — identified to add-ons via `X-Remote-User-*` headers.
- **Registered mobile device** — `webhook_id`/cloudhook holder; can push data + call services.
- **System user** — HAOS/Supervisor system tokens (never exposed).
- **External integrator / device** — third-party device/cloud whose responses Core consumes.

**Adjudication impact.**
Not applicable — there is no PBM claim-adjudication path in this system. The analogous **consequential-action path** is **device control + state mutation**: `POST /api/services/<domain>/<service>` and `POST /api/states/<entity_id>` (`api/rest.md` lines 581-792) actuate physical devices (locks, alarms, switches), and the mobile `webhook_call_service` / server-sent commands path drives in-app and device actions. Authz on this path is server-enforced in Core (permission policy + `SecurityMiddleware`), and the permission engine is flagged **experimental / "not enabled or enforced yet"** in `auth/auth_permissions.md` lines 5-6 — a material gap specialists must weigh (see Evidence Gaps and Notes).

---

## 3. PHI/PII Data Inventory

> Home Assistant handles no PHI/PCI. The HIPAA-equivalent sensitivity class here is **high-privacy home-occupancy + geolocation telemetry** plus **a dense secret/token estate**. The table enumerates the data elements the artifacts name; where the artifacts describe categories rather than field-level schemas, that is noted and recorded as an evidence gap (§6). Field-level schemas live in the per-repo CBM graphs (code recon).

| Field / element | Class | Source | Destinations | Transformations |
|-----------------|-------|--------|--------------|-----------------|
| Password hashes + MFA/TOTP seeds | secret / PII | homeassistant auth provider (onboarding/login) | `.storage/auth_provider.homeassistant`, `.storage/auth`; backup archives | bcrypt hash (per run-config crown-jewel note; confirm in code) |
| Refresh / access / long-lived / system tokens | secret | IndieAuth authorize flow; `/profile` (long-lived); Supervisor (system) | Core auth store; on-device Keychain/Keystore; backups; mobile WebView via JS bridge | access token = HS256 JWT signed w/ per-refresh-token `jwt_key` (run-config); refresh = opaque |
| `SUPERVISOR_TOKEN` | secret | Supervisor (issued per add-on) | add-on container env; Supervisor API auth header | scoped to declared API role |
| Integration secrets (OAuth tokens, API keys, device creds) | secret / confidential | 2000+ integrations (config flows) | `.storage` config_entries + OAuth2 token storage; backups | stored in `.storage` (confirm at-rest protection in code) |
| Recorder entity-state history (presence, geolocation, camera/voice, lock/alarm) | confidential / PII | entity state changes (devices, `person`, `device_tracker`) | Recorder DB (SQLite/MariaDB/Postgres); `/api/history`, `/api/logbook`; backups | none stated (raw state persisted) |
| Instance latitude / longitude / `config_dir` | PII / internal | `configuration.yaml` | `/api/config` (any bearer holder) | none — returned in cleartext (`api/rest.md` lines 110-128) |
| `person` / `device_tracker` GPS + zone data | PII | mobile-app location reporting; device trackers | Core state; Recorder DB; on-device location cache | none stated |
| On-device location/entity cache | PII / confidential | mobile app (Room `location_history` / iOS AppEntityRegistry) | device storage at rest | EncryptedSharedPreferences/DataStore (Android intent; confirm at-rest in code) |
| iOS-bundled Firebase config secrets | secret | `GoogleService-Info-*.plist` compiled into IPA | iOS app bundle | none — recoverable from any IPA (run-config crown-jewel) |
| mTLS client-cert private key (Android) | secret | AndroidKeyStore | hardware-backed Keystore | non-exportable (StrongBox/AndroidKeyStore) |
| App signing identity (Android keystore/cert; iOS provisioning) | secret | CI signing (fastlane / Gradle signingConfig) | release artifacts | non-exportable signing key (confirm storage) |
| Ingress-injected user identity | PII / internal | Supervisor ingress | `X-Remote-User-Id/Name/Display-Name` headers to add-on | none — trusted headers |
| `webhook_id` / `secret` / `cloudhook_url` | secret | `POST /api/mobile_app/registrations` response | mobile app persistent storage; cloudhook URL | optional payload encryption (`supports_encryption`) |

---

## 4. Taxonomy Scope (v1.2+)

```yaml
declared_in_run_config: [cwe, mitre_attack, d3fend, owasp_top10, owasp_api_top10, masvs, maswe]

suggested_additional: []

note: >
  All taxonomies warranted by the detected surface are already declared in run-config.
  Detected surfaces that CONFIRM the declared set (advisory corroboration only — no new
  suggestions): owasp_top10 (Lit/TS SPA frontend + Core REST web surface at /api/ + XSS->token-theft
  via WebView, CSRF, SSRF via integrations); owasp_api_top10 (Core REST/WS bearer API + privileged
  Supervisor API: BOLA on entity_id/device_id, broken-auth/token, function-level authz via API role,
  SSRF via integration unsafe-consumption); masvs + maswe (native iOS Swift + Android Kotlin clients,
  on-device secret storage, WebView/JS-bridge, deep links). No LLM/agentic/ML surface present
  (no owasp_llm_top10 / mitre_atlas warranted) and no PCI/healthcare regulatory surface.
```

---

## 5. Trust Boundary Map

> Source of record: `00-SYSTEM-OVERVIEW.md` §"Trust boundaries (review focus)" (lines 83-92), corroborated by the API/auth/mobile docs. The machine-readable equivalent (with asset-id `crosses[]`) is in `00-context/asset-inventory.yaml`.

| Boundary | Crosses | Upstream trust | Downstream trust | Auth posture | Encryption posture |
|----------|---------|----------------|------------------|--------------|--------------------|
| Internet/LAN edge → Core REST+WS API | Data, control | Untrusted (internet) / semi-trusted (LAN) | Core (single privileged domain) | `Authorization: Bearer` access token; WS `auth_required`→`auth` handshake | TLS terminated at reverse-proxy / Nabu Casa; HA itself serves HTTP on 8123 (TLS posture **not specified** — gap) |
| Mobile app (untrusted, possibly rooted) → Core API | Data, control | Adversary-controlled client | Core | bearer token from IndieAuth flow; device `webhook_id`/`secret` | TLS; no fixed-server cert pinning possible (self-hosted); custom-CA/self-signed trust (gap) |
| Browser/WebView frontend → Core WS/REST + JS bridge to native | Data, control | Browser/WebView (token in client storage) | Core + native app | access token in client storage; JS external-auth bridge passes token native→WebView; callback-name forgery warning | TLS in transit; **token crosses the JS bridge in cleartext within the WebView** |
| Add-on container → Supervisor API & Core proxy | Data, control | Add-on (third-party code) | Supervisor (host-root-equiv) / Core | `SUPERVISOR_TOKEN` + declared API role; **protection mode on by default**; AppArmor | not specified at boundary |
| Supervisor → Docker socket (host root) & os-agent (D-Bus) | Control | Supervisor | Host root | Docker socket access; D-Bus host ops | n/a (local socket/IPC) |
| Core integration → external device/cloud | Data, control | Core (trusts integration) | Untrusted device/cloud | per-integration credential | per-integration (SSRF + untrusted-response surface; **not centrally enforced** — gap) |
| HA instance ↔ push relay ↔ APNS/FCM | Data | HA instance | Firebase Cloud Functions → APNS/FCM | relay forwards without exposing device push tokens to instance | TLS to push providers (confirm in code) |
| Backup artifact ↔ storage/restore | Data | Production (full snapshot: secrets+tokens+DB) | Backup/restore tier | optional backup password (`backup.set_password`) | optional password-based encryption; **default-unprotected** (gap — "weakest-protected copy") |
| Supply-chain ingestion → Core/Supervisor/mobile builds | Code/artifact | Upstream (PyPI/npm/registries/GH Actions/add-on images/base images) | Build + runtime | image signing (Cosign) for add-ons; **not uniformly enforced** | n/a |

---

## 6. Evidence Gaps

These items are not resolvable from the document artifacts and would be needed for a complete picture. Specialist agents draw from this list when populating `prerequisite_evidence` on `blocked` findings. **Many are expected to be closed by the `apd-code-recon` pass** across the 23 CBM graphs — where a gap is a runtime/code property, the specialist should prefer a code-grounded finding over a `blocked` once `code-evidence-index.yaml` is present.

- **Permission-policy enforcement status.** `auth/auth_permissions.md` lines 5-6 flag the policy engine *"experimental … not enabled or enforced yet."* Whether per-entity allow/deny (`filter_entity_ids_by_permission`) is enforced at runtime for non-owner users is the single most load-bearing authz unknown (BOLA/function-level authz). Needs code evidence.
- **TLS posture at the Core boundary.** `api/rest.md` / `api/websocket.md` show plain `http://…:8123`. Whether HA serves TLS itself, mandates a reverse proxy, minimum TLS version, and cipher policy are unspecified.
- **Mobile TLS trust / cert validation.** Run-config notes a custom SSL factory + self-signed/custom-CA trust (`TLSHelper`); the artifacts do not specify cert-validation behavior or whether any pinning exists. Needs code evidence (iOS/android repos).
- **At-rest protection of `.storage` (auth, config_entries, integration secrets).** Artifacts state secrets are persisted to `.storage`; encryption-at-rest mechanism (if any) and key handling are not specified.
- **Backup encryption default.** Backup password is *optional* (`backup.set_password`); default-unprotected behavior and whether the recorder DB + secrets are encrypted in the archive are unconfirmed.
- **Access-token (JWT) parameters.** Run-config asserts HS256 access JWT with per-refresh-token `jwt_key`; the artifacts do not state token TTL, clock-skew, `jwt_key` length/rotation, or revocation propagation. Needs code evidence.
- **Token revocation + expiry semantics.** `auth_index.md` says refresh tokens *"remain valid until a user deletes it"*; access-token lifetime and revocation latency unspecified (Ephemeral lens).
- **Add-on protection-mode + AppArmor enforcement.** Roles/protection mode are documented as policy; whether `SecurityMiddleware` actually gates the Supervisor API and Docker-socket route per role at runtime needs code evidence (supervisor repo).
- **os-agent D-Bus authorization.** Which host operations os-agent exposes and how it authorizes Supervisor callers (container→host-root) is described only at a high level.
- **mobile_app webhook authN/authZ.** `webhook_call_service` / `handle_webhook` accept a `webhook_id` (and optional `secret`) rather than a bearer; the validation, rate-limiting, and authorization scope of the webhook path need code evidence (leaked-`webhook_id` attacker position).
- **SSRF controls on integration outbound + `/api/template` / webscraping.** `/api/template` renders server-side templates and ADR-0004 covers webscraping; allow-listing / SSRF guards on integration outbound and template rendering are unspecified.
- **`whitelist_external_dirs` / file-path exposure.** `/api/config` returns `whitelist_external_dirs`; the path-traversal / file-serving boundary is not detailed.
- **Audit log.** Run-config records (and EXCLUDED `audit_log_store` confirms) there is **no security audit log** — only `logbook`/`logger`. This is a Non-Repudiation **gap**, not a protectable asset; specialists should treat the absence as a finding surface, not infer a log exists.
- **JS-bridge message authentication.** `frontend-external-authentication.md` warns callback names must be verified to avoid forgery; whether origin/integrity of `handleExternalBusMessage` is enforced needs code evidence (frontend + iOS/android).
- **Deep-link / exported-component validation.** `homeassistant://` deep links + Android exported components + iOS Universal Links: input validation on `IncomingURLHandler`/`CallServiceIntentHandler`/`LaunchActivity` needs code evidence.
- **Push-relay token confidentiality.** The relay claims to forward "without exposing device push tokens to the instance"; the mechanism (relay-held mapping, auth) needs code evidence (`mobile-apps-fcm-push`).
- **Supply-chain signing/verification.** Add-on image signing (Cosign) is recommended best-practice; whether base images, wheels, and add-on images are signed AND verified at install is unconfirmed.
- **DR/RTO/RPO + availability targets.** No SLO/RTO/RPO; HA is single-Core single-host by design (Distributed/Resilient/Availability are largely topology-bound to one node — confirm there is no clustering claim).
- **Backup immutability / retention.** No object-lock/WORM/retention policy stated for backups (Immutability lens).
- **`org/SECURITY.md` content.** The file is a 6-line pointer to the website; the actual disclosure policy and hardening guidance are out-of-band (not in `inputs/`).

---

## 7. Per-Goal Relevance Table

Specialists use this to decide which artifacts to deep-read versus skim. (The 22 ADRs and 11 repo-orientation files are grouped; per-file deep-reads are rarely needed beyond the topology/install/database/docker ADRs.)

| Artifact | Conf | Intg | Avail | Dist | Resil | Ephem | Auth | NonRep | Immut |
|----------|------|------|-------|------|-------|-------|------|--------|-------|
| `00-SYSTEM-OVERVIEW.md` | primary | primary | primary | primary | primary | primary | primary | primary | primary |
| `architecture/architecture-overview.md` | secondary | primary | secondary | primary | secondary | unlikely | secondary | unlikely | unlikely |
| `architecture/dev-core.md` | secondary | primary | secondary | secondary | secondary | unlikely | secondary | secondary | unlikely |
| `architecture/dev-devices-and-services.md` | secondary | primary | unlikely | unlikely | unlikely | unlikely | secondary | unlikely | unlikely |
| `architecture/adr/0012…0016` (install/topology) | secondary | secondary | primary | primary | primary | unlikely | unlikely | unlikely | secondary |
| `architecture/adr/0018-supported-databases.md` | primary | secondary | secondary | secondary | secondary | unlikely | unlikely | secondary | secondary |
| `architecture/adr/0006-docker-images.md` | secondary | secondary | unlikely | unlikely | unlikely | secondary | primary | unlikely | secondary |
| `architecture/adr/*` (other) | unlikely | secondary | unlikely | unlikely | unlikely | unlikely | unlikely | unlikely | unlikely |
| `api/rest.md` | primary | primary | secondary | unlikely | unlikely | secondary | primary | secondary | unlikely |
| `api/websocket.md` | primary | primary | secondary | unlikely | unlikely | secondary | primary | secondary | unlikely |
| `api/instance_discovery.md` | secondary | secondary | unlikely | unlikely | unlikely | unlikely | primary | unlikely | unlikely |
| `api/native-app-integration.md` | secondary | secondary | unlikely | unlikely | unlikely | secondary | primary | secondary | unlikely |
| `api/native-app/setup.md` | primary | primary | unlikely | unlikely | unlikely | secondary | primary | secondary | unlikely |
| `api/native-app/{webview,sensors,sending-data,notifications}.md` | primary | primary | unlikely | unlikely | unlikely | secondary | primary | secondary | unlikely |
| `api/supervisor/{endpoints,models,examples}.md` | primary | primary | secondary | unlikely | secondary | secondary | primary | secondary | secondary |
| `auth/auth_index.md` | primary | secondary | unlikely | unlikely | unlikely | primary | primary | secondary | unlikely |
| `auth/auth_api.md` | primary | secondary | unlikely | unlikely | unlikely | primary | primary | secondary | unlikely |
| `auth/{auth_auth_module,auth_auth_provider}.md` | primary | secondary | unlikely | unlikely | unlikely | primary | primary | secondary | unlikely |
| `auth/auth_permissions.md` | primary | primary | unlikely | unlikely | unlikely | secondary | primary | secondary | unlikely |
| `auth/api_lib_auth.md` | secondary | secondary | unlikely | unlikely | unlikely | secondary | primary | unlikely | unlikely |
| `auth/frontend-external-authentication.md` | primary | primary | unlikely | unlikely | unlikely | primary | primary | secondary | unlikely |
| `auth/io-authentication.md` | secondary | secondary | unlikely | unlikely | unlikely | secondary | primary | unlikely | unlikely |
| `mobile/supervisor-apps-security.md` | primary | primary | unlikely | unlikely | secondary | secondary | primary | secondary | secondary |
| `mobile/iOS-{README,CLAUDE}.md` | primary | primary | unlikely | unlikely | unlikely | secondary | primary | secondary | secondary |
| `mobile/android-{README,CLAUDE}.md` | primary | primary | unlikely | unlikely | unlikely | secondary | primary | secondary | secondary |
| `mobile/mobile-apps-fcm-push-README.md` | primary | primary | secondary | unlikely | secondary | unlikely | primary | primary | unlikely |
| `mobile/companion-{README,CLAUDE}.md` | secondary | secondary | unlikely | unlikely | unlikely | unlikely | secondary | unlikely | unlikely |
| `repos/core-{README,CLAUDE,AGENTS}.*` | secondary | secondary | secondary | secondary | secondary | secondary | secondary | secondary | secondary |
| `repos/supervisor-{README,CLAUDE}.md` | secondary | secondary | secondary | secondary | secondary | secondary | primary | secondary | secondary |
| `repos/frontend-{README,CLAUDE}.md` | secondary | secondary | unlikely | unlikely | unlikely | unlikely | secondary | unlikely | unlikely |
| `repos/{js-websocket,os-agent,operating-system,cli}-README.md` | secondary | secondary | secondary | secondary | secondary | secondary | secondary | unlikely | secondary |
| `infra/*-Dockerfile` | secondary | secondary | secondary | unlikely | unlikely | secondary | primary | unlikely | primary |
| `infra/addon-mosquitto-{config,build}.yaml` | primary | primary | unlikely | unlikely | unlikely | secondary | primary | secondary | secondary |
| `org/SECURITY.md` | unlikely | unlikely | unlikely | unlikely | unlikely | unlikely | unlikely | secondary | unlikely |

Legend: `primary` (primary source for this goal), `secondary` (likely supporting evidence), `unlikely` (no obvious material).

---

## 8. Notes for Specialists

- **Ground every finding in code (code recon is enabled).** This brief and the `inputs/` docs are **design intent**. The run config requires findings grounded in real call-graph behavior across the relevant repo's CBM graph, tagged with `repo:`. Once `00-context/code-evidence-index.yaml` exists, prefer a code-evidence pointer over a `blocked` for any gap in §6 that is a code/runtime property. Cross-repo attack paths (mobile→Core API→integration; add-on→supervisor→docker→host root) are explicitly in scope (cross-repo-intelligence pass).

- **The permission engine may not be enforced.** `auth/auth_permissions.md` lines 5-6 state verbatim: *"This is an experimental feature that is not enabled or enforced yet."* The run-config crown-jewel note, by contrast, describes a *"Real policy engine … compile_policy."* These can both be true (code exists, default-off). Confidentiality, Authenticity, and Integrity specialists should resolve enforcement status from code before asserting either BOLA-present or BOLA-absent. Do not infer; treat as `blocked` until code-grounded.

- **`owner` = unconditional all-access.** Any account-takeover of the owner (or owner-equivalent long-lived token) bypasses the entire permission model (`auth_index.md` lines 27-29; `auth_permissions.md` line 11). This is the dominant Confidentiality/Authenticity blast-radius fact.

- **The webhook path is a bearer-less control surface.** `webhook_id`/cloudhook holders push data and call services into Core *without a bearer token* (`api/native-app/setup.md`; `leaked_device_webhook_id` attacker position). Authenticity/Integrity should scrutinize this path independently of the OAuth bearer path.

- **JS external-auth bridge handles cleartext tokens.** Tokens cross native→WebView via `window.externalAppV2`/`webkit.messageHandlers` (`frontend-external-authentication.md`); the doc itself warns callback names must be verified against forgery. This is the key mobile↔frontend Confidentiality/Authenticity boundary; pair with the `compromised_backend_or_response` attacker position (hostile server response reaching native via the bridge).

- **No audit log exists.** The run-config EXCLUDED `audit_log_store` (only `logbook`/`logger`). Non-Repudiation should frame this as a definite gap finding (absence of attributable security-event logging), not a `blocked` — the absence is itself the evidence. Note `/api/logbook` entries show `"context_user_id": null` in the sample (`api/rest.md` lines 360-383), suggesting attribution is frequently absent.

- **Availability/Distributed/Resilient are topology-bounded.** HA Core is a single process on a single host by design (no clustering claim in artifacts). Distributed/Resilient specialists should frame findings around the single-host SPOF and the host-root blast radius rather than expecting multi-region patterns; confirm no HA/cluster mode before asserting.

- **Backups are the "weakest-protected copy of everything."** `00-SYSTEM-OVERVIEW.md` line 106 + run-config: full snapshots bundle config + recorder DB + secrets, with backup password *optional*. Confidentiality (default-unencrypted) and Immutability (no object-lock/retention stated) both have material surface here.

- **Type-classification caveat.** API/auth/mobile/repo reference docs are typed `other` (no `reference_doc` type in the taxonomy). They are nonetheless primary evidence for the api-security and mobile lenses — read them as such; do not down-weight on the `other` type alone.

- **Trust-boundary YAML vs markdown.** §5 (markdown) is for human review; `00-context/asset-inventory.yaml` `trust_boundaries[]` (asset-id `crosses[]`) is for the `apd-attack-path-analyzer`. Both derive from the same `00-SYSTEM-OVERVIEW.md` §"Trust boundaries". All 13 run-config crown jewels are mapped to concrete assets via `realizes_crown_jewels[]` in the inventory.
