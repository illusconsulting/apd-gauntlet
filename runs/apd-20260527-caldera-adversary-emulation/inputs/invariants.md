# MITRE Caldera — Architect-Asserted Invariants

This is the architect's belief about what the system holds true.
Each entry pairs an invariant with the surface that should enforce
it and a note on whether the inputs confirm enforcement. **Many
of these invariants are implicit and may not actually hold** —
the gauntlet's job is to flag the gap between intended and
enforced behaviour.

## Authentication and sessions

### INV-AUTH-001 — Every operator authentication event is recorded

- **Asserted in:** general weapons-platform-due-diligence
  posture.
- **Enforced by:** AuthService login / logout / API-key
  validation paths.
- **Reviewer note:** Not confirmed. Python `logging` may emit
  a line for login success / failure depending on log level;
  there is no structured audit emitter, no signed event
  record, no operator-attributable trail beyond aiohttp
  access logs.

### INV-AUTH-002 — Every operator API call is attributable to a specific user

- **Asserted in:** standard operator-platform posture.
- **Enforced by:** session cookie + `KEY` header check.
- **Reviewer note:** Session-cookie path attributes to a
  username; `KEY` header path attributes only to a group
  (`red` or `blue`) — multiple humans share a single key.
  Per-request emitted logs may not include the session
  principal.

### INV-AUTH-003 — Operator session can be invalidated immediately on credential change

- **Asserted in:** standard incident-response posture.
- **Enforced by:** session-store invalidation API.
- **Reviewer note:** Not enforced. `EncryptedCookieStorage`
  cookies remain valid until their TTL
  (`session_expiration_days`, default 7) regardless of
  credential changes. No JTI / session-deny list in core.

### INV-AUTH-004 — MFA is available at the operator login

- **Asserted in:** general weapons-platform expectation.
- **Enforced by:** AuthService login pipeline.
- **Reviewer note:** Not present in core. A plugin
  implementing `LoginHandlerInterface` may layer MFA, but no
  shipped plugin does.

### INV-AUTH-005 — API keys are rotatable without operator downtime

- **Asserted in:** standard secret-hygiene posture.
- **Enforced by:** AuthService API-key lookup.
- **Reviewer note:** Not enforced. `conf/<env>.yml` holds
  exactly one key per group; rotation requires restart.

## Authorization

### INV-AUTHZ-001 — Every command issued to an implant carries operator audit attribution

- **Asserted in:** weapons-platform-due-diligence posture.
- **Enforced by:** Operation / Link creator metadata.
- **Reviewer note:** Operation carries a creator field at
  create time; Link inherits it via the Operation reference.
  Ad-hoc manual flows (REST POSTs that bypass the standard
  operation pipeline) may not. The Link record does not
  emit a structured audit event when the command is queued
  to the implant.

### INV-AUTHZ-002 — Cross-engagement (cross-operator) data access is prevented

- **Asserted in:** least-privilege / per-engagement
  isolation posture.
- **Enforced by:** per-resource ACL on list endpoints.
- **Reviewer note:** Not enforced. The coarse `red` /
  `blue` group check is the only partition. Operator B in
  group `red` can read every operation, agent, fact, and
  harvested-credential record that operator A in the same
  group created.

### INV-AUTHZ-003 — Plugins cannot access services they were not granted

- **Asserted in:** plugin-sandbox posture.
- **Enforced by:** plugin runtime.
- **Reviewer note:** Not enforced. Plugins run in-process
  with full server privilege. There is no per-plugin
  permission scope.

## Plugin trust

### INV-PLUGIN-001 — Plugin code is operator-trusted

- **Asserted in:** ADR-0002 (load-bearing trust assumption).
- **Enforced by:** operator's manual enablement in
  `conf/<env>.yml`.
- **Reviewer note:** This is the trust assumption the
  platform's plugin model rests on. Reviewer should test
  whether operators have any tooling to validate it (e.g.
  hash pin, signature check) — none ships.

### INV-PLUGIN-002 — Plugin tampering on-disk is detectable

- **Asserted in:** general code-integrity posture.
- **Enforced by:** plugin loader.
- **Reviewer note:** Not enforced. The loader calls
  `import_module` against the on-disk directory; whatever
  Python is there runs.

## Agent / implant communication

### INV-AGENT-001 — Agent callback authentication is enforced per-protocol

- **Asserted in:** ADR-0003 — per-contact authentication
  posture.
- **Enforced by:** the chosen contact module.
- **Reviewer note:** Variability is real. SSH tunnel and
  FTP have static credentials; HTTP / TCP / UDP /
  websocket / DNS / HTML have no authentication. Operator
  choice determines posture.

### INV-AGENT-002 — Beacon body integrity is verified at the server

- **Asserted in:** general MitM-defence posture.
- **Enforced by:** contact-svc obfuscator-decode path.
- **Reviewer note:** Not enforced. The shipped `plain-text`
  and `base64` obfuscators carry no MAC. A network attacker
  between implant and C2 can alter the body undetectably
  (unless the operator enables a plugin-contributed
  authenticated obfuscator and uses TLS via the `ssl`
  plugin).

### INV-AGENT-003 — Mutual authentication of the C2 to the implant

- **Asserted in:** general C2-channel-hardening posture.
- **Enforced by:** implant verifier of server identity.
- **Reviewer note:** Not enforced at the platform level.
  Implants trust whoever answers at the configured callback
  URL.

## Engagement scope (ROE)

### INV-ROE-001 — ROE is operator-declared and operator-enforced

- **Asserted in:** ADR-0004 / operator-runbook §9 (explicit).
- **Enforced by:** the operator manually.
- **Reviewer note:** Held by definition. The reviewer's
  question is: does the platform offer any guardrail (a
  target allowlist, an Engagement object the operation
  must reference)? Answer: no.

### INV-ROE-002 — Out-of-scope implant deployment is prevented

- **Asserted in:** weapons-platform-safety posture.
- **Enforced by:** ROE-aware deployment workflow.
- **Reviewer note:** Not enforced. Operator may run the
  `sandcat` deploy command against any host they can reach;
  the platform does not validate the deployed implant's
  callback-IP against any allowlist.

### INV-ROE-003 — Cross-engagement implant deployment is prevented

- **Asserted in:** per-engagement isolation posture.
- **Enforced by:** per-operation agent group scoping.
- **Reviewer note:** Partially. Operations bind to a `group`
  (e.g. `red`), and the planner only queues abilities to
  agents in the operation's group. But group membership is
  declared by the implant at registration; an implant can
  declare any group string.

## Data retention and lifecycle

### INV-DATA-001 — Result data is retained per-operation lifecycle

- **Asserted in:** standard engagement-archive posture.
- **Enforced by:** retention policy.
- **Reviewer note:** Not enforced. `data/results/`
  accumulates indefinitely. There is no platform retention
  policy, no per-operation deletion, no GDPR-style erasure
  path.

### INV-DATA-002 — Harvested-credential data is encrypted at rest

- **Asserted in:** general sensitive-data posture.
- **Enforced by:** `FileSvc` + `encrypt_files: true`.
- **Reviewer note:** Holds when `encrypt_files: true`
  (default unless explicitly disabled). The encryption key
  derives from `encryption_key` + `crypt_salt`; default
  values (`ADMIN123`, `REPLACE_WITH_RANDOM_VALUE`) ship
  publicly. Effective protection depends on operator
  rotating these.

### INV-DATA-003 — C2 signing material is operator-controlled

- **Asserted in:** general secret-control posture.
- **Enforced by:** operator config.
- **Reviewer note:** Held — signing material (such as it
  exists, e.g. cookie / file encryption key, SSH host key)
  lives in operator-controlled files. Rotation procedure is
  undocumented (runbook §6).

## Operational

### INV-OPS-001 — Operator API-key rotation is non-disruptive

- **Asserted in:** standard secret-rotation posture.
- **Enforced by:** dual-key acceptance during rotation.
- **Reviewer note:** Not enforced. Single key per group;
  rotation requires restart and re-distribution.

### INV-OPS-002 — Server upgrades are non-disruptive to in-flight operations

- **Asserted in:** standard service-upgrade posture.
- **Enforced by:** state-save / state-restore.
- **Reviewer note:** Partially. `DataService.save_state` and
  `restore_state` persist most object state; in-memory
  facts and pending Links are best-effort. SIGTERM is
  converted to KeyboardInterrupt to trigger teardown
  (server.py:_handle_sigterm).

### INV-OPS-003 — Health endpoint reflects plugin-load errors

- **Asserted in:** standard observability posture.
- **Enforced by:** `health_api` / `app_svc._errors`.
- **Reviewer note:** Held. `GET /api/v2/health` is one of
  the few `__caldera_unauthenticated__` handlers and surfaces
  `app_svc.errors`.

### INV-OPS-004 — The server refuses to start with shipped default credentials in `local.yml`

- **Asserted in:** safe-by-default posture.
- **Enforced by:** startup credential check.
- **Reviewer note:** Not enforced. `ensure_local_config()`
  generates `local.yml` on first start; on subsequent
  starts it accepts whatever is there. Manual edits that
  reintroduce defaults are not rejected.

### INV-OPS-005 — TLS is the default for the operator API

- **Asserted in:** standard transport-security posture.
- **Enforced by:** TLS configuration.
- **Reviewer note:** Not enforced. HTTP on `:8888` is the
  default. TLS is delivered by the `ssl` plugin and is
  off by default.
