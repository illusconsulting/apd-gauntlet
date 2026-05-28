---
methodology: stride
---

# Threat Model — MITRE Caldera

STRIDE per surface and per component. Each row identifies a threat
class, the surface it lands on, a concrete attack scenario, the
impact (in security-tooling-pack vocabulary — weapons-platform
misuse, ROE violation, harvested-credential disclosure), the
mitigation present in inputs (if any), and the residual question the
architect cannot answer from the inputs alone.

This is **not** an exhaustive enumeration. Caldera is, by design, a
permissive research platform: many of the controls a production
operator would expect (signed plugins, structured audit, enforced
ROE) are intentionally not in scope for the upstream project. The
residual-question column is correspondingly rich.

## Scope and methodology

- **Methodology:** STRIDE per surface. Each external surface
  (operator console, REST v2, agent listener per protocol) and each
  in-process boundary (plugin loader, parser-output ingest, file-
  serving) is walked through the six categories.
- **In scope:** the single-process Caldera server as shipped in the
  `mitre/caldera` `master` branch (`v5.x`), the 17 default plugins,
  `conf/default.yml` defaults, the canonical `docker-compose.yml`
  exposure.
- **Out of scope:** the implant codebases (`sandcat`, `manx`) —
  separate repos; the externally-maintained plugins (`saml`,
  `arsenal`); the Vue SPA browser-class attacks; the third-party
  TTP library safety/legality.
- **Vocabulary:** uses security-tooling-pack terms. *Operator* =
  authenticated console user. *Implant* = deployed agent
  (sandcat / manx / etc.). *Engagement* = a scoped red-team or
  detection-validation effort. *ROE* = rules of engagement (target
  list + permitted action classes). *Harvested data* = files,
  credentials, screenshots returned by an implant.

Severity tags: **H**igh, **M**edium, **L**ow — reflecting impact
on the operator's engagement, on the target environment, and on
the platform's defensibility.

## 1. Spoofing (S)

### S-1 — Operator-console authentication weak by default

- **Surface:** the login form on the operator console; the `KEY`
  header API-key path.
- **Attack scenario:** An attacker reaches the operator console
  (network-reachable). The default-config users (`red/admin`,
  `blue/admin`) and the default API keys (`ADMIN123`,
  `BLUEADMIN123`) ship in `conf/default.yml`. The `--insecure`
  flag explicitly loads this config; absent that flag,
  `ensure_local_config()` auto-generates a `conf/local.yml`, but
  the auto-generation produces credentials only on first start —
  re-runs preserve whatever was on disk. CVE-2025-27364 (Feb
  2025) was an RCE pre-auth in this area.
- **Impact:** **H** — Full operator access = weapons-platform
  control. Attacker can drive every live implant.
- **Existing mitigation:** README warns against internet
  exposure. `ensure_local_config()` generates per-deploy
  credentials when `--insecure` is not used.
- **Residual question:** What is the auto-generated credential
  entropy? Is there a deployment-time check for "credentials
  still match the shipped defaults"? Does the platform refuse to
  bind to `0.0.0.0` without an operator confirmation?

### S-2 — Agent callback impersonation (no mutual auth)

- **Surface:** `POST /beacon` (HTTP contact) and every other
  agent listener.
- **Attack scenario:** An attacker on the same network as a
  Caldera server crafts a beacon with a fabricated `paw` and
  legitimate-looking platform fingerprint. The HTTP contact
  base64-decodes the body and registers the agent via
  `contact_svc.handle_heartbeat`. The attacker is now a "live
  implant" the operator can see and queue commands to — and the
  attacker can post fabricated results back to mislead the
  detection-validation operator.
- **Impact:** **H** — Operator confidence in implant-reported
  state is undermined. In a detection-validation engagement, a
  fake implant returning fabricated success messages causes the
  operator to conclude "sensor X is detecting Y" when in fact
  the sensor never saw anything.
- **Existing mitigation:** None at the platform layer. Contact
  modules vary; some use covert channels (DNS, GIST, HTML)
  whose obscurity is a weak form of authentication. The
  `untrusted_timer` (default 90s) marks silent agents
  untrusted, but does not catch a chatty fake.
- **Residual question:** Does any shipped contact protocol
  enforce per-implant cryptographic identity? `sandcat` is
  built with operator-supplied `ldflags`; do those carry a
  signing key, and does the server verify it?

### S-3 — Plugin source impersonation (no signature verification)

- **Surface:** `plugins/<name>/` plugin loader; the operator's
  out-of-band process for fetching new plugins.
- **Attack scenario:** A red-team team installs a third-party
  plugin from a GitHub mirror. The mirror was typosquatted; the
  hook.py runs `subprocess.Popen` to exfiltrate operator session
  cookies on first server start. There is no signature, no hash
  pin, no publisher allowlist.
- **Impact:** **H** — Supply-chain compromise of any plugin
  the operator chooses to install = full server compromise.
- **Existing mitigation:** Operator manually trusts the plugin
  by adding it to `conf/<env>.yml`'s `plugins:` list.
- **Residual question:** Does Caldera ship any allowlist of
  trusted plugin sources, or any tooling to verify a plugin's
  authenticity before enabling it?

### S-4 — Login-handler module hijack

- **Surface:** `auth.login.handler.module` config key.
- **Attack scenario:** An attacker with write access to
  `conf/<env>.yml` (e.g. a misconfigured volume mount, a
  compromised CI deploy pipeline) sets
  `auth.login.handler.module: <attacker_plugin>`. On next restart
  the attacker's login handler is invoked for every login
  attempt — credentials are silently exfiltrated.
- **Impact:** **H** — Persistent credential capture.
- **Existing mitigation:** None.
- **Residual question:** Are config-file changes detected at
  runtime? Is there a checksum or signature for the loaded
  login-handler module?

## 2. Tampering (T)

### T-1 — Plugin code execution = unbounded server tampering

- **Surface:** every loaded plugin (`plugins/<name>/hook.py`).
- **Attack scenario:** A plugin's `enable()` method runs with
  full server privilege. It can monkey-patch any service
  singleton, register routes that override built-in handlers,
  rewrite the on-disk YAML object store, replace the encryption
  key in `BaseWorld`, or hand the in-memory `Application`
  object to an external collaborator. There is no boundary.
- **Impact:** **H** — Any plugin can become a persistent
  backdoor.
- **Existing mitigation:** Operator-controlled plugin enablement
  via `conf/<env>.yml`.
- **Residual question:** Does the server perform any integrity
  check on the loaded plugin tree (hash, signature)? Are
  monkey-patched services detectable?

### T-2 — Ability YAML tampering

- **Surface:** `data/abilities/` and plugin
  `data/abilities/`; the ability-file watcher
  (`app_svc.watch_ability_files`).
- **Attack scenario:** An attacker with filesystem write access
  to the ability tree edits a benign ability's `command:` field
  to call out to attacker-controlled infrastructure. The watcher
  reloads the file silently; the next operation that includes
  the ability fires the attacker's payload from every live
  implant.
- **Impact:** **H** — Operator's running operation becomes a
  delivery vector for attacker payloads to every in-scope target.
- **Existing mitigation:** Filesystem permissions on the
  Caldera server's `data/` and `plugins/` directories — that's
  the operator's responsibility.
- **Residual question:** Does the watcher log a diff or a
  notification when an ability file changes mid-operation? Is
  there a "freeze abilities" mode for a running engagement?

### T-3 — Agent-callback payload tampering (MitM)

- **Surface:** HTTP/TCP/UDP contact bytes on the wire (no TLS
  by default; SSL plugin terminates HTTPS optionally).
- **Attack scenario:** A network attacker between the implant
  and the C2 alters command bodies on the wire. With the HTTP
  contact in `base64` obfuscator mode, there is no integrity
  check — the modified base64 body decodes to a different
  command, which the implant runs against the target.
- **Impact:** **H** — Attacker controls what runs on targets.
  Operator audit trail (the Link record) reflects what the
  *server queued*, not what the implant *received*.
- **Existing mitigation:** Operator can enable the `ssl`
  plugin for HTTPS. Some contact protocols carry their own
  obfuscation (e.g. AES via plugin obfuscators) but per-contact.
- **Residual question:** Does any shipped obfuscator provide
  authenticated encryption (MAC over the command body)? The
  shipped `plain-text` and `base64` obfuscators do not.

### T-4 — Audit-log mutability

- **Surface:** the Python `logging` output to stdout / rich
  console; any operator-aggregated log destination.
- **Attack scenario:** An attacker with operator privilege (S-1,
  S-4, T-1) restarts the server, clears stdout, and removes
  the only forensic trace. There is no append-only audit store.
- **Impact:** **H** — Post-incident investigation cannot
  reconstruct the attacker's actions.
- **Existing mitigation:** None at the platform layer.
- **Residual question:** Is there a documented "ship logs
  off-host" pattern for production-grade Caldera operators?

### T-5 — Operation-results tampering by privileged plugin

- **Surface:** parsers and the Link/Result write path
  (`PlanningService` calls into the active parser; parser
  writes `Fact` records to `KnowledgeService`).
- **Attack scenario:** A malicious or buggy parser writes
  fabricated facts that the planner then uses to chain
  subsequent abilities. Operator sees an operation that "found"
  data the implant never harvested.
- **Impact:** **M** — Operation outputs become unreliable;
  detection-validation conclusions are wrong.
- **Existing mitigation:** None — parsers are trusted code.
- **Residual question:** Are parser outputs attributable
  (parser ID stamped on every fact) for after-the-fact
  forensics?

## 3. Repudiation (R)

### R-1 — No structured operator-action audit log

- **Surface:** every `/api/v2/*` mutation endpoint; every v1
  REST call; every operator UI action.
- **Attack scenario:** Operator A launches a contentious
  operation against an environment that turns out to be
  out-of-scope. After the engagement, the operator denies having
  launched the operation. There is no structured audit record
  attributing the operation-create call to operator A — only
  Python-logging output to stdout, which (a) does not always
  include the session principal, (b) does not survive a server
  restart unless externally captured, (c) is not signed.
- **Impact:** **H** — Cannot attribute weapons-platform actions
  to a specific operator. Regulatory or contractual
  consequences (CFAA, customer engagement terms) cannot be
  reliably defended.
- **Existing mitigation:** None.
- **Residual question:** Are any deployments shipping a
  custom audit middleware? Is there a documented pattern?

### R-2 — Per-command attribution missing on the agent side

- **Surface:** the Link record in an Operation.
- **Attack scenario:** An operation runs an ability against an
  implant. The Link captures *which ability* and *which
  variation* fired, but not *which operator* issued or
  approved it. In a multi-operator team, post-incident
  attribution to a specific human is impossible from the
  Link alone.
- **Impact:** **M** — In a regulated environment, individual
  accountability cannot be established.
- **Existing mitigation:** Operations carry a creator field at
  create time, but ad-hoc manual-launch flows may not.
- **Residual question:** Is the operation-creator field
  immutable post-creation? Is it carried into every derivative
  Link?

### R-3 — Engagement-start consent record absent

- **Surface:** the platform has no `Engagement` object.
- **Attack scenario:** A customer disputes that they consented
  to the red-team engagement that ran against their
  environment. The Caldera server has no record of the ROE
  document, no record of who approved the engagement, no
  signed consent artifact.
- **Impact:** **H** — Legal / contractual defense is
  off-platform; the platform offers no support.
- **Existing mitigation:** None — operators maintain ROE
  documents externally.
- **Residual question:** Has any operator-deployment pattern
  added a "consent record" plugin?

### R-4 — ROE-document attribution lost

- **Surface:** out-of-platform.
- **Attack scenario:** Operator runs an operation that exceeds
  the documented ROE. The Caldera Operation record does not
  reference the ROE document version under which it was
  authorised; reconstructing the deviation requires correlating
  off-platform records.
- **Impact:** **M** — Post-engagement review cannot connect
  Operation to ROE without external records.

## 4. Information Disclosure (I)

### I-1 — Operator console XSS / template injection

- **Surface:** the Jinja-rendered legacy console under `/`; the
  Vue SPA under `/`.
- **Attack scenario:** A field on an Ability (name,
  description, command-template variable name) is rendered
  without escaping into a panel a second operator views. The
  second operator's session cookie is exfiltrated.
- **Impact:** **H** — Operator session takeover.
- **Existing mitigation:** Aiohttp + Jinja2 default escaping;
  Vue's template engine escapes by default. Plugin-contributed
  panels are operator-trusted code, so XSS in a plugin panel is
  effectively "operator A trusted plugin X with operator B's
  session".
- **Residual question:** Are command-template strings (which
  pass through obfuscators that may re-encode) safely
  serialised back into the operator UI?

### I-2 — Harvested-data exfiltration via result store

- **Surface:** `data/results/` directory; every Link's `Result`
  payload.
- **Attack scenario:** An attacker with operator-privilege
  (S-1) reads `data/results/` and recovers every credential
  harvested from every past operation. The platform treats
  harvested data as opaque bytes; sensitive material (Mimikatz
  dumps, browser-saved credentials, Kerberos tickets, SSH
  keys) sits unencrypted unless the operator turned on
  `encrypt_files: true`.
- **Impact:** **H** — Disclosure of customer-environment
  harvested credentials across every prior engagement; the
  platform is a long-tail single point of failure for
  customer-data confidentiality.
- **Existing mitigation:** `encrypt_files: true` toggle wraps
  files with Fernet. Default is on per `FileSvc._get_encryptor`
  unless explicitly disabled. The encryption key is derived
  from operator config (`crypt_salt`, `encryption_key`); the
  default `ADMIN123` values are widely known.
- **Residual question:** Is there a retention policy for
  result data? Is there a per-engagement deletion path?

### I-3 — GraphQL / API enumeration

- **Surface:** `/api/v2/*` (the Swagger spec advertises every
  endpoint), the plugin-contributed GraphQL surface (referenced
  in README but not in core).
- **Attack scenario:** An unauthenticated attacker (S-1) or a
  blue-role operator can enumerate every red-role-owned
  Operation, Adversary, Source, and Fact via the introspectable
  REST surface. The `health_api` is explicitly unauthenticated.
- **Impact:** **M** — Cross-operator engagement enumeration.
  Blue operators can see red engagement structure (and vice
  versa) if permission boundaries are not enforced per-resource.
- **Existing mitigation:** Coarse `red` / `blue` group check via
  `check_permissions`. No per-resource ACL.
- **Residual question:** Does the v2 list endpoint
  (`GET /api/v2/operations`) filter by caller permission? The
  group check is on the route, not on the result set.

### I-4 — Implant inventory disclosure

- **Surface:** `/api/v2/agents`.
- **Attack scenario:** Same as I-3 but specifically for the
  live implant list — which reveals every host the operator
  has compromised, including hostnames, OS fingerprint, and
  last-seen IP.
- **Impact:** **H** — In a multi-tenant or shared-server
  deployment, one tenant's implant inventory leaks to
  another. Combined with S-1, an external attacker recovers
  the full target landscape.
- **Existing mitigation:** Operator-permission check on the
  route.
- **Residual question:** Is the agent list scoped to the
  caller's operations, or is it global?

### I-5 — Engagement-scope leakage via fact store

- **Surface:** `/api/v2/facts`, knowledge-store API.
- **Attack scenario:** Harvested facts (hostnames, AD domain
  names, internal IPs) leak across operations. A second
  operator's planner uses facts from a prior operator's
  engagement to plan abilities against the wrong target.
- **Impact:** **M** — Cross-engagement contamination; ROE
  violation by misadventure.
- **Existing mitigation:** Facts are scoped to a Source; Source
  is scoped to an Operation. Whether the API list endpoints
  enforce that scope at read time is uncertain.

### I-6 — JWKS / TLS material exposure

- **Surface:** `conf/<env>.yml`, `conf/ssh_keys/`.
- **Attack scenario:** Default `conf/default.yml` ships
  `crypt_salt: REPLACE_WITH_RANDOM_VALUE` and
  `encryption_key: ADMIN123`. The SSH tunnel default user
  (`sandcat`) and password (`s4ndc4t!`) are shipped. An
  attacker who reads the config file recovers every secret the
  default deployment uses.
- **Impact:** **H** — Cookie-storage decryption, file-encryption
  bypass, SSH tunnel hijack.
- **Existing mitigation:** Operator is expected to replace
  defaults in `conf/local.yml`. `ensure_local_config()`
  auto-generates on first run.

## 5. Denial of Service (D)

### D-1 — Operator console rate-limiting absent

- **Surface:** every `/api/v2/*` endpoint; every operator UI
  call.
- **Attack scenario:** Repeated login attempts against the
  operator console. There is no rate limiter, no lockout
  threshold, no captcha. With weak defaults (S-1) this is also
  a credential-brute-force path.
- **Impact:** **M** — Server availability; credential
  brute-force.
- **Existing mitigation:** None.

### D-2 — Agent-callback flood

- **Surface:** every contact listener.
- **Attack scenario:** Attacker floods `/beacon` (or
  `:7011/udp` for the UDP contact) with fabricated beacons.
  `contact_svc.handle_heartbeat` upserts an agent for every
  unique `paw`; the in-memory agent registry grows without
  bound. The planner runs over every active operation that
  matches the fabricated agent's `group`.
- **Impact:** **M-H** — Memory pressure, planner-loop
  saturation, eventual server failure during an engagement.
- **Existing mitigation:** Agents transition to `untrusted`
  after `untrusted_timer` (default 90s); but untrusted agents
  remain in the registry.
- **Residual question:** Is there a max-agent-count bound? Is
  there a per-source-IP rate limit on beacons?

### D-3 — Plugin can hang or crash the server

- **Surface:** every plugin `enable()` and any
  plugin-contributed route handler.
- **Attack scenario:** A plugin's startup blocks indefinitely
  or raises an uncaught exception. Because the server is
  single-process / single-event-loop, the entire server
  stalls or exits.
- **Impact:** **M** — Active operations may lose state at
  unexpected shutdown.
- **Existing mitigation:** `try/except` around plugin loading
  in `app_svc.load_plugins`, but in-loop plugin code can still
  block the event loop (synchronous I/O, infinite loops).

### D-4 — Result-store fill

- **Surface:** `data/results/` and the harvested-payload
  ingest path.
- **Attack scenario:** An implant (real or impersonated, see
  S-2) returns enormous result blobs. The
  `api_upload_max_size_mb` config (default 100 MB) bounds
  individual uploads but not aggregate. Disk fills; server
  loses ability to record subsequent Links.
- **Impact:** **M** — Operation continuity loss.
- **Existing mitigation:** `api_upload_max_size_mb`,
  `client_max_size_mb` (default 1 MB for non-v2). No retention.

### D-5 — Untrusted-agent sniffer race

- **Surface:** `app_svc.start_sniffer_untrusted_agents`.
- **Attack scenario:** A beacon-fabricator (S-2) sends a beacon
  every (untrusted_timer + 1) seconds to keep an agent
  trusted-state-flapping; the sniffer's recheck loop produces
  log spam at scale.
- **Impact:** **L** — Noise in operator's view; in extremis,
  log-disk fill.

## 6. Elevation of Privilege (E)

### E-1 — Group → all-operator privilege

- **Surface:** the coarse `red` / `blue` group check.
- **Attack scenario:** A blue-role operator (detection
  engineer) needs only the API key `BLUEADMIN123` (default) to
  authenticate. Endpoints that gate on `blue` are unauthorised
  for red traffic, but any endpoint that gates on either group
  (or that takes the catch-all check) lets a low-privilege user
  perform operator actions.
- **Impact:** **M** — Privilege boundary between red and blue
  is fragile.
- **Existing mitigation:** `check_permissions('app', request)`
  enforces *some* group; per-handler scoping varies.
- **Residual question:** Is there an inventory of which
  handlers gate which group? Are there handlers that gate
  neither (i.e. any-authenticated)?

### E-2 — Agent → server pivot

- **Surface:** every parser; the `Result` ingest path.
- **Attack scenario:** A compromised implant (or an
  impersonator, S-2) returns crafted output that exploits a
  parser's parsing logic. Caldera parsers are Python code;
  a parser that uses `eval`, `yaml.load` (unsafe), `pickle`,
  or shells out via `subprocess` on parsed bytes lets the
  attacker run code on the C2 server.
- **Impact:** **H** — Implant compromise extends to C2
  compromise; the C2 then has every other implant.
- **Existing mitigation:** Parser authors are trusted (they
  ship as part of plugins or operator-authored).
- **Residual question:** Are there automated checks for
  parser code that uses unsafe deserialisation?

### E-3 — Plugin → host privilege escalation

- **Surface:** any plugin's ability to spawn subprocesses or
  load C extensions.
- **Attack scenario:** A plugin uses a Python C extension
  with a known kernel-driver-installation step (e.g. a
  privileged debugger module). Caldera server runs the
  extension as whatever user owns the Python process — often
  root in a Docker container. Local privilege escalation on
  the host follows.
- **Impact:** **H** — Container escape; host takeover.
- **Existing mitigation:** None at the platform layer; relies
  on operator container-hardening (rootless containers,
  read-only root filesystem, seccomp).

### E-4 — Cross-engagement data access

- **Surface:** every read endpoint that doesn't filter by
  caller.
- **Attack scenario:** Operator A's harvested credentials
  (`data/results/`) and facts are accessible to operator B
  via the API surface. The platform does not partition data
  per-operator.
- **Impact:** **H** — Customer-A's credentials handed to
  customer-B's red team.
- **Existing mitigation:** Coarse `red`/`blue` group check;
  no per-engagement partitioning.
- **Residual question:** Does any operator-deployment pattern
  shard Caldera instances per-customer to avoid this?

### E-5 — Compile-time payload injection via `ldflags`

- **Surface:** `FileSvc` agent-compile path
  (`subprocess.run(["go", "build", "-ldflags", ...])`).
- **Attack scenario:** Operator-supplied compile-time variables
  flow into `ldflags`. The `URL_SANITIZATION_REGEX` and
  `ALLOWED_LDFLAG_REGEXES` constrain inputs, but the regex set
  is finite; an unknown ldflag key path or a regex that admits
  unexpected characters could let an attacker inject a Go
  build directive that runs at compile time on the server.
- **Impact:** **M** — RCE on the C2 server at agent-compile
  time.
- **Existing mitigation:** Allowlist regex per ldflag key
  (`ALLOWED_LDFLAG_REGEXES`).
- **Residual question:** Are all consumed ldflag keys covered
  by the allowlist, or does an unlisted key fall through to
  `ALLOWED_DEFAULT_LDFLAG_REGEX`?

### E-6 — Session-cookie key recovery

- **Surface:** the Fernet key derived from
  `crypt_salt` + `encryption_key`.
- **Attack scenario:** With default config values
  (`encryption_key: ADMIN123`, `crypt_salt:
  REPLACE_WITH_RANDOM_VALUE`), an attacker who acquires a
  cookie value (e.g. via XSS, log leak, MitM on
  TLS-less deploy) decrypts it offline and recovers session
  state. With `--insecure` this is trivial.
- **Impact:** **H** — Operator-session forgery.
- **Existing mitigation:** `ensure_local_config()` regenerates
  these for non-insecure deploys.

## 7. Cross-cutting / weapons-platform-specific

These do not fit cleanly into one STRIDE category but are the
most security-tooling-pack-relevant risks.

### WP-1 — Weapons-platform misuse (full compromise)

- **Composition of:** S-1 (or S-3 or S-4) + T-1.
- **Scenario:** Attacker gains operator-equivalent access (via
  default credentials, plugin supply chain, or login-handler
  hijack). They now:
  - Issue commands to every live implant (deployed against
    real customer environments).
  - Compile and deploy new implants attributable to the
    legitimate operator.
  - Recover every harvested credential.
  - Modify the audit trail (T-4).
- **Impact:** **H — catastrophic.** This is a CFAA
  exposure: unauthorised access by the attacker, possibly
  flowing through to unauthorised access of customer systems
  via the platform's implants.
- **Existing mitigation:** Trusted-environment-only deployment
  posture (README).

### WP-2 — ROE violation by operator error

- **Scenario:** Operator launches an operation that includes
  an out-of-scope target. Platform offers no scope-policy
  enforcement (no target allowlist, no host-fingerprint
  matching against an Engagement object — because there is no
  Engagement object). Operator's mistake becomes a
  customer-side incident.
- **Impact:** **H** — Customer trust, contractual exposure.
- **Existing mitigation:** ROE is operator-managed
  off-platform.

### WP-3 — Implant deployment to attacker-chosen targets

- **Scenario:** Combination of WP-1 + the `builder` plugin's
  on-server compile path. Attacker builds a fresh implant
  carrying the operator's signing material (if any), points
  it at attacker-chosen victim infrastructure, and the
  operator's reputation backs the resulting activity.
- **Impact:** **H** — Attribution of attacker activity to the
  legitimate operator.

### WP-4 — Customer-environment harvested-credential exposure

- **Scenario:** I-2 / E-4 in aggregate. The platform's
  long-tail accumulation of every credential ever harvested
  from every customer engagement, with no per-engagement
  partition and weak default at-rest encryption.
- **Impact:** **H** — One compromise of the C2 = breach
  notification for every customer whose environment ever
  hosted an implant.

## STRIDE → APD-goal mapping (handoff to specialists)

Per the methodology pack mapping table:

- **S** findings map to: Authenticity (operator/agent identity),
  Confidentiality (cookie / key material).
- **T** findings map to: Integrity (audit-trail, results,
  abilities), Authenticity (signed plugins).
- **R** findings map to: Non-Repudiation (operator-action audit,
  per-command attribution), Auditability (engagement records).
- **I** findings map to: Confidentiality (harvested data,
  inventory), Privacy (customer-environment data).
- **D** findings map to: Availability (operator console, agent
  listeners, result store).
- **E** findings map to: Authorization (red/blue boundary,
  cross-engagement partition), Authenticity (parser-output
  trust, plugin trust).

Cross-cutting WP-* findings map to: weapons-platform-misuse
impact severity per the security-tooling pack rubric — these
are the highest-priority concerns for the synthesiser to
elevate.
