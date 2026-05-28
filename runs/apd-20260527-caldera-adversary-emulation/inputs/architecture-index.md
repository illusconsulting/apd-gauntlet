# Architecture Index — MITRE Caldera

Service-by-service index for the Caldera v5 deployment. Caldera is
**not** a microservice constellation — it is a single asyncio Python
process — so "service" here means an in-process service singleton
(under `app/service/`), an API surface, a listener, or a plugin
module. Use this as the lookup table when correlating findings to
surfaces; the trust-boundary notes follow the §3 inventory in
`tech_plan.md`.

## In-process services

### `AppService` (`app/service/app_svc.py`)

- **Language / runtime:** Python 3.10+, asyncio.
- **Role:** Plugin loader, scheduler, ability-file watcher,
  untrusted-agent sniffer, operation resumer.
- **Inbound:** Called by every other service singleton via the
  `BaseService` registry; no external surface.
- **Outbound:** Filesystem reads on `plugins/`, `data/`,
  `conf/`; `import_module()` calls into plugin packages.
- **Datastores touched:** `data/` (object store backups).
- **Trust boundary:** Loads arbitrary Python code from
  `plugins/<name>/` at server start — this is the single
  highest-privilege operation in the system.
- **Notable surface:** `load_plugins()`, `load_plugin_expansions()`,
  `run_scheduler()`, `start_sniffer_untrusted_agents()`.

### `AuthService` (`app/service/auth_svc.py`)

- **Language / runtime:** Python; uses `aiohttp_security`,
  `aiohttp_session`, `cryptography`.
- **Role:** Session establishment, login dispatch, API-key check
  (`KEY` header), `check_permissions('app', request)` enforcement,
  user-map bootstrap from `conf/<env>.yml`.
- **Inbound:** Every authenticated REST handler via the
  `@check_authorization` decorator.
- **Outbound:** Cookie storage at `data/cookie_storage`;
  pluggable `LoginHandlerInterface` implementations.
- **Datastores touched:** `data/cookie_storage` (Fernet-encrypted).
- **Trust boundary:** Operator authentication. Bootstrap users
  come from `conf/<env>.yml`'s `users:` block; `--insecure`
  loads `conf/default.yml`'s known-credential set.
- **Notable surface:** `check_permissions`, API-key path
  (`HEADER_API_KEY = 'KEY'`), pluggable
  `auth.login.handler.module`. No MFA path in core.

### `DataService` (`app/service/data_svc.py`)

- **Language / runtime:** Python.
- **Role:** First-class object CRUD (`store`, `locate`,
  `remove`); load_data from plugin `data/` directories;
  save_state / restore_state.
- **Inbound:** Every REST manager and the planning service.
- **Outbound:** Filesystem reads/writes against `data/`.
- **Datastores touched:** `data/abilities/`, `data/adversaries/`,
  `data/objectives/`, `data/payloads/`, `data/planners/`,
  `data/results/`, `data/sources/`, `data/backup/`.
- **Trust boundary:** Sole authority over the object store. No
  per-object ACL; group permission is enforced at the REST
  handler, not at the data layer.

### `KnowledgeService` (`app/service/knowledge_svc.py`)

- **Language / runtime:** Python.
- **Role:** Fact store. Holds the per-operation knowledge graph
  (facts harvested by parsers, relationships between facts).
- **Inbound:** PlanningService (reads facts to expand ability
  templates); parsers (write facts as results come in).
- **Outbound:** In-memory; restored from `data/` on start.
- **Datastores touched:** In-memory primary; serialized into
  `data/backup/` periodically.

### `PlanningService` (`app/service/planning_svc.py`)

- **Language / runtime:** Python.
- **Role:** Generates `Link` objects per agent per ability,
  expanding command templates against the knowledge store and
  the agent's local facts. Selects the next ability per the
  active planner's logic.
- **Inbound:** ContactService (on every beacon, for the agent's
  active operation); RestService (manual ability launch).
- **Outbound:** Writes Links into the active Operation; queues
  them for the agent's next beacon.

### `ContactService` (`app/service/contact_svc.py`)

- **Language / runtime:** Python.
- **Role:** Beacon-handling glue. Each contact module
  (`app/contacts/contact_*.py`) calls into `contact_svc` to
  upsert agents, decode bytes per the contact's encoding, and
  retrieve queued instructions.
- **Inbound:** Every agent listener.
- **Outbound:** PlanningService (to refresh queued instructions
  on every beacon).
- **Trust boundary:** First point where attacker-controlled
  (or in this case, implant-controlled — but in a compromise
  scenario, attacker-controlled) bytes hit Caldera's code.

### `FileSvc` (`app/service/file_svc.py`)

- **Language / runtime:** Python; uses `cryptography.Fernet`,
  `subprocess`.
- **Role:** Payload delivery to agents, file encryption at rest,
  agent compilation (Go `ldflags` substitution via
  `subprocess`).
- **Inbound:** Agent download requests; REST payload upload.
- **Outbound:** Filesystem reads on `data/payloads/` and plugin
  payload directories; `subprocess.run` for Go builds.
- **Datastores touched:** `data/payloads/` and plugin payload
  directories.
- **Notable surface:** `URL_SANITIZATION_REGEX`,
  `ALLOWED_LDFLAG_REGEXES` constrain compile-time injection;
  `_SAFE_FILENAME_RE` constrains served filenames.

### `LearningService` (`app/service/learning_svc.py`)

- **Language / runtime:** Python.
- **Role:** Builds parsing models from past operations'
  Link/Result history; trains parsers to extract facts more
  accurately.
- **Inbound:** Background task started at server startup
  (`build_model` runs in a loop).
- **Outbound:** In-memory model.

### `RestService` (`app/service/rest_svc.py`)

- **Language / runtime:** Python.
- **Role:** Operator-action glue between v1 REST handlers and
  the data/planning services.
- **Inbound:** v1 REST handlers (`CampaignPack`, `AdvancedPack`).
- **Outbound:** DataService, PlanningService.

### `EventService` (`app/service/event_svc.py`)

- **Language / runtime:** Python.
- **Role:** Pub/sub event bus. `fire_event(exchange, queue,
  ...)` broadcasts platform events; plugins may subscribe.
- **Inbound:** App lifecycle (`fire_event("system", "ready")`),
  operation lifecycle, agent state changes.
- **Outbound:** In-process plugin subscribers.

## API surfaces

### v2 REST (`app/api/v2/`)

- **Path prefix:** `/api/v2/`.
- **Handlers:** `ability_api`, `adversary_api`, `agent_api`,
  `config_api`, `contact_api`, `fact_api`, `fact_source_api`,
  `health_api`, `obfuscator_api`, `objective_api`,
  `operation_api`, `payload_api`, `planner_api`, `plugins_api`,
  `schedule_api`.
- **Middlewares:** `pass_option_middleware`,
  `apispec_request_validation_middleware`,
  `validation_middleware`.
- **Auth:** Per-handler `@check_authorization`. Handlers may
  opt out via `__caldera_unauthenticated__` (`health_api` for
  instance).
- **Docs:** `/api/docs` (Swagger UI), `/api/docs/swagger.json`.
- **Trust boundary:** Operator-facing. Accepts session cookie
  or `KEY` header.

### v1 REST (`app/api/rest_api.py` + `app/api/packs/`)

- **Path prefix:** `/api/rest/` and operator-console HTML at `/`.
- **Handlers:** Legacy. `CampaignPack` (`/plugin/campaign/...`)
  and `AdvancedPack` (`/plugin/advanced/...`) bundle the
  pre-v2 operator workflows.
- **Auth:** `@check_authorization` decorated.
- **Trust boundary:** Operator-facing.

### Agent listener — HTTP contact

- **Path:** `POST /beacon` on the same `:8888` aiohttp server.
- **Handler:** `contact_http.Contact._beacon`.
- **Auth:** **None at the HTTP layer.** Agent identifies itself
  by `paw` in the (base64-decoded) JSON body.
- **Trust boundary:** First point of implant-controlled byte
  ingress; combined with the operator-API surface on the same
  port — the same TCP listener serves both.

### Agent listeners — other contact protocols

| Module | Port (default) | Auth posture |
|--------|----------------|--------------|
| `contact_dns.py` | `:8853/udp` | None — covert |
| `contact_ftp.py` | `:2222` | Static `caldera_user / caldera` from `conf/` |
| `contact_gist.py` | external (GitHub) | GitHub PAT from `conf/` |
| `contact_html.py` | `/weather` on `:8888` | None — covert |
| `contact_slack.py` | external (Slack) | Slack bot token from `conf/` |
| `contact_tcp.py` | `:7010` | None |
| `contact_udp.py` | `:7011/udp` | None |
| `contact_websocket.py` | `:7012` | None |
| `contact_svc/tunnels/...` (SSH) | `:8022` | Static `sandcat / s4ndc4t!` from `conf/` |

## Shipped plugins (`plugins/`)

| Plugin | Role | Notable security surface |
|--------|------|--------------------------|
| `access` | Initial-access tooling | Privileged TTP library |
| `atomic` | Atomic Red Team TTP set | Large external dataset bind-mountable |
| `builder` | Compiles payloads on the server | Invokes Go toolchain via subprocess |
| `compass` | ATT&CK visualisation | UI-only |
| `debrief` | Operation reporting (PDF) | Uses `reportlab`, `lxml`, `svglib` — historically vulnerable parsers |
| `emu` | CTID emulation plans | Large external dataset bind-mountable |
| `fieldmanual` | Sphinx docs | Static |
| `gameboard` | Red/blue joint-op viz | UI-only |
| `human` | Synthesises benign noise | Executes commands on targets |
| `magma` | Vue UI (operator console) | The operator UI itself |
| `manx` | Reverse-shell agent | Alternative implant + listener |
| `response` | IR abilities + parsers | Privileged TTP library |
| `sandcat` | Default Go implant | Compiled by `builder` |
| `ssl` | Terminates HTTPS for server | Operator-supplied TLS material |
| `stockpile` | Bulk TTP / adversary library | Largest single ability source |
| `training` | CTF-style operator training | Self-paced; consumes the live server |

Every plugin runs **in-process** with full server privilege. A
plugin's `hook.py:enable()` is called by `AppService.load_plugins`
at startup.

## Datastores

| Store | Backing | Touched by |
|-------|---------|------------|
| Object store | `data/{abilities,adversaries,objectives,planners,sources}/` (YAML) | DataService |
| Operation/Link/Result store | `data/results/` + in-memory | DataService, planner, parsers |
| Payload store | `data/payloads/` + plugin payload dirs | FileSvc |
| Fact / knowledge store | In-memory primary; serialised to `data/backup/` | KnowledgeService |
| Session cookies | `data/cookie_storage` (Fernet-encrypted) | AuthService |
| Configuration | `conf/<env>.yml`, `conf/agents.yml`, `conf/payloads.yml` | BaseWorld at startup |

There is no relational database. The filesystem is the source of
truth. Backup is operator-driven (`data/backup/` is written by
`DataService.save_state` but rotation/retention are operator
responsibility).
