# MITRE Caldera — Technical Plan

MITRE **Caldera** is an open-source adversary-emulation framework
maintained by MITRE Corporation. It is a command-and-control (C2)
platform that uses MITRE ATT&CK techniques as "abilities" and ships
with a default Go-based implant (`sandcat`). Operators stand up the
server, deploy implants to in-scope target hosts, then schedule and
run **operations** — sequenced sets of abilities chosen by a
**planner** — and review the harvested results.

This document is the architect-facing description of what Caldera is,
how the pieces are deployed, where the trust boundaries fall, and —
because Caldera is by intent a weapons platform — what attack surface
is in scope by design. Version under review: **v5.x** (`master`
branch as of 2026-05-27). License: **Apache-2.0**.

## 1. System purpose

Caldera is a single-tenant operator platform that supports two
primary use cases:

- **Red-team automation.** A red-team operator defines an
  **adversary profile** (an ordered collection of ATT&CK-mapped
  abilities), deploys one or more implants to target hosts, and
  runs an **operation** that lets the chosen planner walk the
  profile against the live implants — collecting facts as it goes,
  re-planning around the harvested knowledge, and producing a
  per-step audit trail (`links`) of what ran and what was returned.
- **Detection-engineering validation.** A blue-team operator runs
  the same operations to fire telemetry into sensors (EDR, SIEM,
  MDR pipelines) and confirms that the detections fire as designed.
  The shipped `gameboard` plugin pairs red and blue operations for
  joint validation.

Caldera is **explicitly not** intended for use against systems the
operator does not have authorization to engage. The README ships a
prominent security recommendation:

> The Caldera team highly recommends standing up the Caldera server
> on a secure environment/network, and not exposing it to the
> internet. The Caldera server does not have a hardened and
> thoroughly pentested web application interface, but only basic
> authentication and security features.

Rules-of-engagement (ROE) and target-scope are **operator-declared
and operator-enforced**; the platform does not constrain which hosts
an operator may execute abilities against, nor does it carry an
authoritative engagement-scope artifact.

## 2. Architecture

Caldera is structured as a **single asyncio Python process** that
hosts every server-side responsibility — the REST API, the GraphQL
expansion (via plugin), the operator web UI (Vue, served from
`plugins/magma`), the agent contact listeners, the planner, the
plugin loader, and the in-memory object store. There is no
process-level isolation between any of these. A second process
exists only when the operator opts into the `--uidev` flag (which
spawns a Vue dev server on `:3000`).

### Top-level entrypoint

`server.py` (~330 lines) bootstraps everything:

1. Loads `conf/<env>.yml` (`local`, `default`, or operator-supplied)
   into `BaseWorld`.
2. Instantiates the seven service singletons: `DataService`,
   `KnowledgeService`, `ContactService`, `PlanningService`,
   `RestService`, `AuthService`, `FileSvc`, `LearningService`,
   `EventService`, `AppService`.
3. Constructs the aiohttp `web.Application` and registers
   `/api/v2/*` as a subapp.
4. Restores object-store state from `data/` (pickled YAML and
   JSON), loads each enabled plugin module from `plugins/`, calls
   each plugin's `enable()` to mount its routes and register its
   abilities/payloads/parsers, and registers every configured agent
   **contact** (`http`, `dns`, `ftp`, `gist`, `html`, `slack`,
   `tcp`, `udp`, `websocket`, plus the SSH tunnel).
5. Starts background tasks: untrusted-agent sniffer, operation
   resumer, scheduler, learning-model builder, ability-file
   watcher.

The same Python process services operator REST/UI calls, agent
beacons, plugin-contributed routes, and the planner's outbound
execution loop.

### Component map

| Component | Source | Role |
|-----------|--------|------|
| `server.py` | top-level | Argparse, config loading, service wiring, event loop |
| `app/api/rest_api.py` | RestApi | Legacy v1 REST endpoints + Jinja-rendered HTML console |
| `app/api/v2/` | RestApi v2 | Modern REST (`/api/v2/agents`, `.../abilities`, `.../operations`, etc.) + Swagger docs at `/api/docs` |
| `app/api/packs/` | Campaign / Advanced packs | Bundles of v1 REST endpoints for operator workflows |
| `app/contacts/` | Agent listeners | One module per C2 protocol; each registers its own listener route or socket |
| `app/service/auth_svc.py` | AuthService | Session cookies (encrypted), basic-auth bootstrap from `conf/`, header-based API-key auth (`KEY` header), pluggable login handlers |
| `app/service/app_svc.py` | AppService | Plugin loader, scheduler, ability-file watcher, untrusted-agent sniffer |
| `app/service/data_svc.py` | DataService | First-class object CRUD (abilities, agents, operations, plugins, planners, sources, schedules) backed by `data/` |
| `app/service/knowledge_svc.py` | KnowledgeService | Fact store (harvested data, used by planners) |
| `app/service/planning_svc.py` | PlanningService | Link-generation engine; expands ability templates against agent + fact context |
| `app/service/rest_svc.py` | RestService | Glue between REST handlers and the data/planning services |
| `app/service/file_svc.py` | FileSvc | Payload delivery, agent compilation (Go `ldflags` substitution), `cryptography.Fernet`-based file encryption |
| `app/service/learning_svc.py` | LearningService | Builds parsing models from past operations |
| `app/service/contact_svc.py` | ContactService | Beacon-handling glue; decodes agent payloads (per-contact encoding); queues instructions |
| `app/objects/c_*.py` | First-class objects | `Ability`, `Adversary`, `Agent`, `Operation`, `Plugin`, `Planner`, `Schedule`, `Source`, `Objective`, `Obfuscator` |
| `app/objects/secondclass/c_*.py` | Second-class | `Link`, `Executor`, `Fact`, `Relationship`, `Result`, `Variation`, `Visibility` |
| `plugins/<name>/hook.py` | Plugin module | Each plugin's bootstrap; called by `AppService.load_plugins` at server start |

### Deployment topologies

- **From-source.** `python3 server.py --insecure --build`. The
  `--insecure` flag explicitly loads `conf/default.yml`, which
  ships **known credentials** (`red/admin`, `blue/admin`,
  `api_key_red=ADMIN123`, `api_key_blue=BLUEADMIN123`,
  `crypt_salt=REPLACE_WITH_RANDOM_VALUE`, `encryption_key=ADMIN123`).
- **Docker.** The shipped `Dockerfile` builds either a `slim` or
  `full` variant. `docker-compose.yml` bind-mounts the source
  tree, exposes `:8888` (HTTP console + HTTP contact), `:8443`
  (SSL plugin), `:7010` (TCP contact), `:7011/udp` (UDP contact),
  `:7012` (websocket), `:8853` (DNS), `:8022` (SSH tunnel),
  `:2222` (FTP contact). The container README notes that on first
  start it **auto-generates** keys/usernames/passwords —
  bind-mounting `conf/local.yml` overrides that path.
- **Pre-built image.** `ghcr.io/mitre/caldera:latest` is
  published; the README warns it may lag.

### Process model

One asyncio event loop hosts the aiohttp `web.Application`. Every
incoming request — operator REST call, operator UI page render,
agent beacon, GraphQL query, plugin-contributed route — is dispatched
into the same loop. Plugin code runs as in-process Python modules
imported at startup; there is no sandbox, no subprocess, no
namespace isolation.

The `--build` flag triggers a `subprocess.run(["npm", "run",
"build"], cwd=MAGMA_PATH)` to compile the Vue UI. The `--uidev`
flag spawns a Vue dev server via `asyncio.create_subprocess_exec`.

## 3. Trust boundaries

```
+-----------+   +----------------+   +-------------------+   +---------+
| Operator  |-->| Caldera server |-->| Agent listeners   |<--| Implant |
| (browser) |   | (asyncio)      |   | (HTTP/DNS/FTP/...)|   | (target)|
+-----------+   |                |   +-------------------+   +---------+
                |  +-----------+ |
                |  | Plugin    | |   plugins are loaded as
                |  | modules   | |   *in-process* Python
                |  +-----------+ |
                |  +-----------+ |
                |  | Data /    | |   filesystem-backed object
                |  | Knowledge | |   store and fact store
                |  +-----------+ |
                +----------------+
                        |
                        v
                +----------------+
                | Target hosts   |   (out of platform; operator
                | (engagement    |    is responsible for ROE)
                | scope)         |
                +----------------+
```

Boundary inventory:

1. **Operator → Caldera server (HTTPS or HTTP).** Browser-class
   surface. Default deploy is **HTTP on `:8888`** unless the
   `ssl` plugin is enabled, in which case the SSL plugin
   terminates TLS and proxies to the same backend. Authentication
   is either session-cookie (after login form) or `KEY` header
   API-key (`api_key_red` / `api_key_blue` from config). There is
   no MFA in core; no operator-deployment-time SSO except via the
   externally-maintained `saml` plugin.
2. **Caldera server ↔ in-process plugins.** **No boundary.**
   Plugins are Python modules in `plugins/<name>/` loaded by
   `import_module`; the plugin's `enable()` method runs with full
   server privilege and can register routes, mutate any service,
   access the filesystem, and call out to the network. There is
   no signature verification, no allowlist beyond the
   `plugins:` list in `conf/<env>.yml`, no per-plugin permission
   scope.
3. **Caldera server → agent listeners.** Each contact protocol
   (`contact_http`, `contact_dns`, `contact_ftp`, `contact_gist`,
   `contact_html`, `contact_slack`, `contact_tcp`, `contact_udp`,
   `contact_websocket`) registers a listener and defines its own
   on-wire encoding. The shipped HTTP contact handles `POST
   /beacon` with a JSON profile that is *base64-decoded* by
   default; no payload authentication beyond the implant's
   declared `paw` (identifier). Cryptographic authentication of
   the beacon is **per-contact** and varies — DNS exfil is
   covert-channel only, GIST hides traffic in GitHub Gists, Slack
   in a configured channel.
4. **Agent listener → in-memory agent registry.** A beacon
   carrying a new `paw` causes a fresh `Agent` to be registered;
   the platform decides whether the agent is `trusted` or
   `untrusted` based on the configured `untrusted_timer` and
   silence intervals.
5. **Implant → target host.** Out of the platform's enforcement
   scope. The implant runs commands the planner queues for it on
   the target. Whether the target is in operator-authorized scope
   is **operator-declared, not platform-enforced**.

## 4. Authentication & sessions

- **Operator login.** `app/service/auth_svc.py` reads the
  `users:` block from `conf/<env>.yml` and bootstraps a
  `User(username, password, permissions)` map at server start.
  Per `conf/default.yml`, the bootstrap users are:
  - `red / admin` (permissions: `red`)
  - `red / red` (permissions: `red`) — duplicate by design
  - `blue / admin` (permissions: `blue`)
- **Session storage.** `aiohttp_session.EncryptedCookieStorage`
  derives a Fernet key from `encryption_key` + `crypt_salt` via
  PBKDF2-HMAC-SHA256. The default `conf/default.yml` ships
  `encryption_key: ADMIN123` and `crypt_salt:
  REPLACE_WITH_RANDOM_VALUE`. Cookie storage path is
  `data/cookie_storage`. Default `session_expiration_days: 7`.
- **API key.** A request bearing the `KEY` header is matched
  against `api_key_red` or `api_key_blue` (defaults `ADMIN123` /
  `BLUEADMIN123`). API-key callers bypass the cookie / login
  handshake entirely.
- **Login handlers are pluggable.** `auth.login.handler.module`
  defaults to `default`. A plugin can implement
  `LoginHandlerInterface` and replace the default; the shipped
  `saml` and `access` plugins demonstrate alternative auth
  pipelines.
- **Permissions.** Two coarse roles exist in core: `red` and
  `blue`. The `permissions` decorator (`check_authorization` in
  `auth_svc.py`) only checks that the caller belongs to the
  required group — there is no per-resource ACL.
- **MFA.** Not present in core.
- **Per-operator audit.** The auth service does not emit
  structured audit events for login, command issuance,
  ability execution, or agent creation. Operator activity is
  observable only via aiohttp's request logs and per-handler
  `self.log.debug` / `self.log.info` calls.

## 5. Plugin model

Each subdirectory of `plugins/` is a Caldera plugin. The default
distribution ships **17 plugins** (see §6). A plugin's `hook.py`
is imported by `AppService.load_plugins` at server start; its
`enable()` method runs with full server privilege.

A plugin may contribute:

- **Abilities** — YAML descriptions of ATT&CK-mapped command
  sequences, optionally per-platform (Windows / Linux / macOS).
  Stored under the plugin's `data/abilities/` directory.
- **Payloads** — binary files (compiled implants, helper
  utilities, encoded scripts) under the plugin's `payloads/`
  directory. Served via `file_svc` on agent request.
- **Parsers** — Python modules that transform raw command output
  into structured `Fact` records that the planner can chain into
  subsequent abilities.
- **GUI panels** — Vue components that the `magma` UI surfaces.
- **REST routes** — any aiohttp route the plugin chooses to
  register. The plugin can extend `/api/v2`, register entirely
  new prefixes, or replace existing handlers.
- **Login handlers, planners, obfuscators, data encoders,
  contact listeners** — every extension point in the framework
  is plugin-replaceable.

There is **no plugin signature verification.** There is **no
runtime sandbox.** A plugin can `subprocess.Popen` arbitrary
commands, write anywhere on the filesystem the server user can
write, and reach any network the server can reach. The
implicit security model is: **the operator chose to enable this
plugin and therefore trusts the plugin's code.**

## 6. Shipped plugins (default distribution)

| Plugin | Role |
|--------|------|
| `access` | Initial-access tooling and TTPs |
| `atomic` | Atomic Red Team project TTPs (large external dataset) |
| `builder` | Dynamically compiles payloads on the server |
| `compass` | ATT&CK navigator visualisation |
| `debrief` | Operation reporting (reportlab PDF generation) |
| `emu` | CTID emulation plans |
| `fieldmanual` | Sphinx-built documentation |
| `gameboard` | Joint red/blue operation visualisation |
| `human` | Synthesises benign endpoint noise |
| `magma` | Vue UI (default operator console) |
| `manx` | Reverse-shell-style alternative agent |
| `response` | Incident-response abilities and parsers |
| `sandcat` | Default Go-based implant |
| `ssl` | Terminates HTTPS for the server |
| `stockpile` | Bulk ability and adversary-profile library |
| `training` | Capture-the-flag style operator training course |
| `manx` | Reverse-shell agent / shell functionality |

The `builder` plugin notably **compiles payloads on the server**,
meaning it ships and uses a Go toolchain in-process (the
`GoLang 1.24+` requirement in the README is for this). The
`sandcat` plugin's `_build_agent` pathway uses `file_svc`'s
`ldflags` substitution: `URL_SANITIZATION_REGEX` and
`ALLOWED_LDFLAG_REGEXES` in `file_svc.py` constrain what can be
injected, but the build call is `go build` against operator-
supplied configuration.

## 7. Agent communication (C2 channels)

A single Caldera deployment can run **all** of the following
listeners simultaneously, each on its configured port from
`conf/default.yml`:

- **`http`** — `POST /beacon` over the same `:8888` aiohttp
  server. Beacon body is base64-encoded JSON by default
  (`contact_svc.decode_bytes`). No mutual authentication.
- **`dns`** — `:8853/udp`. Covert channel.
- **`ftp`** — `:2222`. Configured user
  `caldera_user / caldera` by default.
- **`gist`** — Outbound to GitHub Gists; the operator supplies a
  GitHub PAT (`app.contact.gist: API_KEY` placeholder in
  `conf/default.yml`).
- **`html`** — Beacons hidden in a benign-looking HTML page at
  `/weather`.
- **`slack`** — Posts to a configured Slack channel using a
  Slack bot token.
- **`tcp`** — `:7010`.
- **`udp`** — `:7011/udp`.
- **`websocket`** — `:7012`.
- **SSH tunnel** — `asyncssh`-backed; default user
  `sandcat / s4ndc4t!`, host key from operator-supplied path.

Each contact module decides its own on-wire format. The HTTP
contact uses `base64` decode by default; some contacts use
encrypted obfuscators (`plain-text`, `base64` are registered at
server start; plugins may add more, e.g. AES).

Agent → server beacon flow:

1. Implant beacons with its `paw` (identifier), platform fingerprint,
   architecture, current working facts.
2. Server's `contact_svc.handle_heartbeat` upserts the agent in
   the in-memory registry, marks it trusted (or untrusted if the
   timer has expired), runs the planner over any active operation
   that targets the agent's `group`, and returns a JSON response
   containing `sleep`, `watchdog`, and a list of queued
   `instructions` (each is a base64-encoded command, optionally
   with a parser to apply to the result).
3. Implant executes the instructions on the target, captures
   stdout/stderr/exit-code, and posts the results in the next
   beacon.
4. Server records the executed `Link` against the active
   `Operation`, runs configured parsers, and persists harvested
   `Fact` records to the knowledge store.

## 8. Data model

First-class objects (each backed by a YAML schema under
`app/objects/`):

- **Ability** — an ATT&CK-mapped command sequence with
  per-platform executors, optional payloads, optional parsers,
  required/optional facts. Stored as YAML under
  `data/abilities/<tactic>/<uuid>.yml` or under a plugin's
  `data/abilities/`.
- **Adversary** — an ordered list of abilities (an
  "adversary profile" — emulating a specific threat actor).
- **Agent** — a live implant, identified by `paw`.
- **Operation** — a running scenario binding an adversary + a
  planner + a fact source + a set of agents.
- **Planner** — orchestration logic (e.g. `atomic` walks
  abilities in order; `batch` runs them in parallel).
- **Plugin** — metadata for a loaded plugin module.
- **Schedule** — operator-defined recurring operation
  (`croniter`-backed).
- **Source** — a starting fact set (named facts the planner can
  reference).
- **Objective** — a success condition the planner checks against.
- **Obfuscator** — output-encoding module (`plain-text`,
  `base64`, plus plugin-contributed).

Second-class objects:

- **Link** — one executed step in an operation (the audit grain).
- **Executor** — per-platform command-binding for an ability.
- **Fact** — a discovered key/value pair (harvested data).
- **Relationship** — a fact-graph edge.
- **Result** — raw output captured from an agent.
- **Variation** — an alternate phrasing of a command.
- **Visibility** — defender-visibility scoring (how loud the
  ability is).

## 9. Persistence

Caldera is **file-system primary**. There is no relational
database; the `data/` directory tree is the store:

```
data/
├── abilities/      # plugin- and operator-contributed abilities (YAML)
├── adversaries/    # adversary profiles (YAML)
├── backup/         # periodic state dumps
├── objectives/     # YAML
├── payloads/       # binary payloads (served to agents)
├── planners/       # planner modules (YAML metadata)
├── results/        # per-link captured output
└── sources/        # starting fact sets (YAML)
```

`DataService.restore_state` and `KnowledgeService.restore_state`
re-hydrate the in-memory object graph from this tree at server
start; `DataService.save_state` writes it back. There is **no
persistent transaction log**; the file system is the source of
truth between restarts.

The encrypted cookie storage lives in `data/cookie_storage`
(Fernet-encrypted with the key derived from `crypt_salt` +
`encryption_key`).

The `FileSvc` can also encrypt arbitrary files (payload at-rest)
with Fernet (`encrypt_files: true`).

## 10. API surfaces

- **`/` and `/{path}`** — Jinja-rendered operator HTML console
  (legacy `rest_api.py`) and the Vue SPA (`plugins/magma/dist`).
  Require an active session cookie.
- **`/api/v2/*`** — the modern REST surface. Handlers in
  `app/api/v2/handlers/` cover every first-class object plus
  `health`, `config`, `contact`, `payload`, `plugins`.
  Documented via `aiohttp_apispec`; Swagger UI at `/api/docs`.
  All handlers go through `pass_option_middleware` +
  `apispec_request_validation_middleware` +
  `validation_middleware`; auth is enforced per-handler by
  `@check_authorization` or by exempting a handler with
  `__caldera_unauthenticated__`.
- **`/beacon`** — HTTP contact agent-listener endpoint
  (`POST`). Bypasses operator auth — agent traffic.
- **`/api/v1/...`** — legacy REST endpoints (`CampaignPack`,
  `AdvancedPack`) for operator workflows that pre-date v2.
- **`/api/docs`** — Swagger UI.
- **GraphQL** — provided by plugin, not by core; the README and
  several plugins reference a GraphQL surface but it is not
  registered in `server.py`.
- **Plugin-contributed routes** — any aiohttp prefix a plugin
  chooses (e.g. `/plugin/training/...`,
  `/plugin/debrief/...`).

The aiohttp `Application` is initialised with
`client_max_size=client_max_size_mb * 1024 * 1024` (default
1 MB) for non-`/api/v2` calls; the `/api/v2` subapp uses
`api_upload_max_size_mb` (default 100 MB).

CORS is configured globally (`enable_cors`) and allows
credentials from `http://<uiDevHost>:3000` — i.e. when
`--uidev` is set, the dev-server origin is trusted.

## 11. Known security posture (explicitly stated or self-evident)

- **Trusted-environment-only deployment.** The README is
  explicit: Caldera is not hardened for internet exposure. MITRE
  and its sponsors run Caldera on segregated lab networks.
- **Single-process, single-tenant.** Plugin code, operator
  traffic, and agent traffic all share the same Python process,
  same filesystem, same network egress.
- **Plugin loading is privileged.** Any plugin that ships
  `hook.py` runs with full server privilege at startup. The
  default plugin set includes the `builder` plugin which invokes
  the Go toolchain to compile payloads — i.e. compromise of the
  Go toolchain or its dependencies on the server host extends
  to compromise of every implant the server builds.
- **Known default credentials.** `conf/default.yml` carries
  static credentials (`red/admin`, `blue/admin`,
  `api_key_red=ADMIN123`, `api_key_blue=BLUEADMIN123`,
  `encryption_key=ADMIN123`). The `--insecure` flag is required
  to load `default.yml`; otherwise `ensure_local_config()`
  generates a `conf/local.yml` with auto-generated keys on
  first start.
- **The platform is a weapons system.** Compromise of a Caldera
  server gives the attacker:
  - The ability to issue arbitrary commands to every live
    implant (every host the legitimate operator has compromised).
  - All harvested credentials, files, and screenshots from past
    operations (`data/results/`).
  - Access to every planner / parser / ability the operator has
    authored or loaded.
  - The ability to compile and sign new implants and deploy them
    to attacker-chosen targets, attributable to the operator.
- **No production-grade audit story.** The platform emits
  Python `logging` calls to stdout/`rich`; there is no
  structured audit log, no operator-action attribution beyond
  the session cookie, no immutable event store. CVE-2025-27364
  (Feb 2025) was disclosed against the platform — remote code
  execution — underscoring the operator's responsibility to
  patch and to avoid public exposure.
- **Engagement scope (ROE) is operator-declared.** The platform
  has no `Engagement` object, no scope policy enforcement, no
  rate-limit on agent deployment, no geofencing on implant
  callbacks. An operator who points an implant at an
  out-of-scope host has no platform-level guardrail.
- **The implant codebases (sandcat, manx, etc.) are separate
  repositories** with their own posture; this document treats
  them as opaque from the server's perspective.

## 12. Out of scope for this APD review

- The implant codebases (`sandcat`, `manx`) — separate repos,
  separate review.
- The externally-maintained plugins (`arsenal`, `bountyhunter`,
  `caltack`, `saml`) — not bundled in the default distribution.
- The Vue UI bundle (`plugins/magma/dist`) browser-class
  attacks — a separate review of the SPA would be needed.
- The upstream Docker base images (Python, Debian) supply-chain
  posture.
- The Go toolchain that the `builder` plugin invokes.
- The third-party ability TTP libraries (`atomic`, `stockpile`)
  for the safety / legality of the commands they would execute.
