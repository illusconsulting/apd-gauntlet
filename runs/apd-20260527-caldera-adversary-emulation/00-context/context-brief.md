# Context Brief — Apache Caldera v5.x

**Run id:** apd-20260527-caldera-adversary-emulation
**Domain pack:** security-tooling v1.0.0
**Framework version:** 1.5.0
**Subject:** Apache Caldera (MITRE), Apache-2.0, master branch as of 2026-05-27

## TL;DR for downstream specialists

Caldera is a single-tenant adversary-emulation framework structured as a
single asyncio Python process. Plugin code, operator traffic, agent
beacons, and the result store share one process. The upstream README is
explicit that the platform is **not hardened for internet exposure**;
the operational model is **trusted-environment deployment**. CVE-2025-27364
(Feb 2025) was a pre-auth RCE in this footprint.

Specialists should produce findings against the **second-order
consequences** of these documented postures, not re-discover them. The
finding pattern is: "given that X is documented-acceptable in upstream's
trust model, the following downstream auditability /
weapons-platform-misuse /scalability consequence is the gauntlet
concern."

## Artifact index

| File | Type | Lines | Relevance hints |
|------|------|-------|-----------------|
| `tech_plan.md` | tech_plan | 512 | All 9 APD goals; primary architectural reference |
| `architecture-index.md` | architecture_index | 235 | Component inventory; per-service trust boundary notes |
| `threat-model.md` | threat_model (STRIDE) | 628 | All 9 goals; weapons-platform-misuse threats WP-1..WP-4 explicit |
| `adrs/0001-asyncio-single-process-server.md` | adr | – | Distributed, Resilient, Availability |
| `adrs/0002-plugin-runtime-without-signature-verification.md` | adr | – | Integrity, Authenticity, Non-Repudiation, Immutability |
| `adrs/0003-agent-callback-encryption-by-protocol.md` | adr | – | Confidentiality, Integrity, Authenticity |
| `adrs/0004-operator-console-basic-auth-default.md` | adr | – | Authenticity, Ephemeral, Confidentiality |
| `happy-path.md` | operational | 199 | Distributed, Resilient, Availability |
| `runbook.md` | runbook | 329 | Resilient, Availability, Ephemeral; explicit GAP markers |
| `agents.md` | operator_profile | 121 | All — provides operator profile and engagement profile |
| `invariants.md` | invariants | 244 | All — architect-asserted invariants with reviewer notes |
| `prior-audit.md` | prior_audit | 199 | All — known posture statements; CVE-2025-27364 |

## Capability and surface summary

### Process model

- **One asyncio Python process** hosts: aiohttp web app, all REST
  handlers (`/api/v2/*`, `/api/v1/*`), Jinja-rendered legacy console,
  Vue SPA, agent listener for every contact protocol simultaneously,
  plugin code (in-process Python imports), scheduler, planner,
  file-encryption, builder (subprocess for `go build`).
- **No process-level isolation.** Plugins, operator traffic, agent
  beacons, result store all share the same memory, filesystem, and
  network egress.

### Surfaces

- Operator console (HTTP `:8888` by default; HTTPS `:8443` via `ssl`
  plugin).
- REST `/api/v2/*` (modern), `/api/v1/*` (legacy `CampaignPack`,
  `AdvancedPack`), `/api/docs` (Swagger UI), `/health` (unauthenticated).
- Agent listeners (concurrent): HTTP `/beacon` `:8888`, DNS `:8853/udp`,
  FTP `:2222`, GIST (outbound to GitHub), HTML `/weather`, Slack
  (outbound), TCP `:7010`, UDP `:7011/udp`, websocket `:7012`, SSH
  `:8022`.
- Plugin-contributed routes (any prefix a plugin chooses).

### Authentication

- Session cookie via `aiohttp_session.EncryptedCookieStorage`, Fernet
  key derived from `encryption_key` + `crypt_salt` via PBKDF2-HMAC-SHA256.
- `KEY` header API key — `api_key_red` / `api_key_blue` from
  `conf/<env>.yml`; bypasses login.
- **Default credentials** in `conf/default.yml` loaded by `--insecure`:
  `red/admin`, `blue/admin`, API keys `ADMIN123` / `BLUEADMIN123`,
  `encryption_key=ADMIN123`, `crypt_salt=REPLACE_WITH_RANDOM_VALUE`.
- `ensure_local_config()` auto-generates `conf/local.yml` on first start
  if `--insecure` is not set.
- Two coarse groups: `red`, `blue`. No per-resource ACL. No MFA in core.
- Auth-decision logs are not structured; rely on Python `logging` to
  stdout.

### Persistence

- File-system primary. `data/` tree is the source of truth; no RDBMS,
  no transaction log.
- `data/cookie_storage` — Fernet-encrypted session cookies.
- `data/results/` — per-link captured implant output, optionally
  Fernet-encrypted (`encrypt_files: true` default).
- `data/abilities/`, `data/adversaries/`, `data/objectives/`,
  `data/payloads/`, `data/planners/`, `data/sources/`, `data/backup/`.

### Plugin model

- 17 default plugins. Each subdir of `plugins/` is loaded by
  `AppService.load_plugins` at startup via `import_module`.
- **No signature verification, no sandbox, no per-plugin permissions.**
- Plugins may register routes, mutate any service, run subprocesses,
  read/write the filesystem, reach any network.
- `builder` plugin spawns `go build` (Go toolchain in-process).
- `--build` invokes `npm run build` on `plugins/magma`.

## Data inventory (security-tooling taxonomy)

| Class | Present? | Locator |
|-------|----------|---------|
| operator_password | Yes (cleartext bootstrap in `conf/default.yml`) | tech_plan §4 |
| operator_password_hash | No — cleartext stored, no hashing path documented | tech_plan §4 |
| operator_mfa_seed | No — MFA not in core | tech_plan §4 |
| operator_api_token | Yes (`api_key_red`, `api_key_blue`) | tech_plan §4 |
| operator_session_cookie | Yes (`aiohttp_session.EncryptedCookieStorage`) | tech_plan §4 |
| c2_signing_key | No dedicated key; channel auth = TLS only | tech_plan §7 |
| listener_tls_certificate_chain | Yes (via `ssl` plugin only) | tech_plan §6 |
| plugin_signing_root | No — no plugin signing exists | tech_plan §5 |
| audit_log_signing_key | No — no audit log exists | tech_plan §4 |
| implant_authentication_token | No — `paw` only (operator-generated, not cryptographic) | threat-model S-2 |
| implant_callback_url | Yes (per-contact configuration) | tech_plan §7 |
| implant_unique_identifier | Yes (`paw`) | tech_plan §7 |
| target_inventory | No first-class object; operator-declared off-platform | invariants AUTHZ |
| roe_document | No first-class object; operator-declared off-platform | tech_plan §11 |
| engagement_scope_definition | No first-class object | tech_plan §11 |
| customer_identification | No first-class object | agents.md |
| harvested_credentials | Yes (in `data/results/` per-link Fernet-encrypted) | tech_plan §9 |
| harvested_files | Yes (in `data/results/`) | tech_plan §9 |
| captured_screenshots | Yes (in `data/results/` if ability produces them) | tech_plan §9 |
| command_outputs | Yes (`Result` objects) | tech_plan §8 |
| pivoted_access_tokens | Yes (as Facts in `KnowledgeService`) | tech_plan §8 |
| plugin_source_code | Yes (in `plugins/`) | tech_plan §5 |
| plugin_signature | No | tech_plan §5 |
| plugin_manifest | Implicit (`hook.py` + `conf/<env>.yml` enablement list) | tech_plan §5 |
| operator_action_event | Partial — Python `logging` only, no structured audit | tech_plan §4 |
| command_issued_event | Partial — Link record exists in-memory; no audit emit | tech_plan §8 |
| result_access_event | No — no audit emit on read | invariants AUDIT |
| plugin_lifecycle_event | No — no structured audit on plugin enable/load | tech_plan §5 |
| audit_access_event | N/A — there is no audit log to access | tech_plan §11 |

**No PHI scope declared by the platform itself**, but result data
**inherits** sensitivity from target environments. A screenshot of a
HIPAA-covered EHR places that screenshot in PHI scope. The platform
treats all such data as generic `Result` records.

## Trust boundaries (numbered for cross-reference)

1. **Operator → Caldera server.** Browser/CLI to aiohttp at `:8888`
   (or `:8443` via `ssl` plugin). Default HTTP; basic-auth or
   `KEY` header.
2. **Caldera server ↔ plugins.** **NO BOUNDARY.** Plugins are
   in-process Python imports running with full server privilege.
3. **Caldera server → agent listeners.** Each contact module has its
   own on-wire encoding. No mutual auth at the platform layer.
4. **Listener → in-memory agent registry.** Beacon-driven; new `paw`
   creates new `Agent`. Trust based on `untrusted_timer`, not on
   cryptographic identity.
5. **Implant → target host.** Out of platform enforcement entirely.

## Evidence gap list (what specialists should expect to mark `blocked`)

- **Key rotation cadence.** No documented rotation for
  `encryption_key`, `crypt_salt`, API keys, or session-cookie Fernet
  key. Runbook §6 explicitly marks this as GAP.
- **Audit pipeline.** No structured audit emitter, no audit log
  destination, no audit retention policy. Runbook §8 marks GAP.
- **Multi-tenant isolation.** Caldera is single-tenant; multi-customer
  deployment patterns are operator-improvised. Runbook §10 marks GAP.
- **ROE enforcement.** No first-class `Engagement` or `ROE` object;
  operator-declared off-platform. Runbook §7 marks GAP.
- **Plugin signature verification.** Not implemented; ADR-0002
  documents the acceptance.
- **Per-resource ACL.** Group-level only (`red` / `blue`); no per-
  engagement, per-operation, or per-record permission scope.
- **Backup integrity.** `data/backup/` exists but no documented
  integrity verification, signing, or off-platform replication.
- **SLO/SLA targets.** No declared availability targets for any service.
- **DR/BCP.** No documented disaster recovery or business continuity plan.

## Taxonomies in scope for this run

Declared in `.apd-run.yaml`:

- `cwe`
- `mitre_attack`
- `d3fend`
- `owasp_api_top10` (REST surface present at `/api/v2/*`)
- `owasp_top10` (HTML console + Vue SPA browser surface present)

Specialists may emit mappings only for these taxonomies. The
`owasp_llm_top10` taxonomy is **not** in scope (no LLM integration).

## Methodology hint

`stride` — the threat model (`threat-model.md`) is structured per
STRIDE category, per surface. Specialists should consult it to map
their lens-specific findings onto the documented STRIDE entries; the
threat-model evaluator (Phase 5.5) will cross-check coverage.

## Specialists skipped

None.

## Code recon

`code_recon: disabled` per `.apd-run.yaml`. Caldera source at
`/tmp/caldera` is not indexed; specialists should NOT cite
`code-evidence-index.yaml` (it does not exist) and should not
attempt CBM lookups.
