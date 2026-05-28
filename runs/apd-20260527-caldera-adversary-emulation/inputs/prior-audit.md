# MITRE Caldera — Prior Audit Carry-Forward

This entry records the security-posture context that this APD
review inherits. The "prior audit" here is synthesised from the
upstream project's own honest disclosure (the README's `Security`
section, `SECURITY.md` vulnerability-disclosure policy, the
CVE-2025-27364 advisory), the shipped configuration defaults
(`conf/default.yml`), and the structural observations a reviewer
should expect to carry forward from a code reading of `server.py`
+ `app/`.

## Source

- **Auditor:** synthesised from the upstream MITRE Caldera
  documentation and the shipped artifacts at `server.py`,
  `conf/`, `app/service/auth_svc.py`, `app/service/app_svc.py`,
  `app/service/file_svc.py`, `app/contacts/`, `app/api/v2/`,
  and the published CVE-2025-27364 advisory.
- **Version under review:** v5.x (master, 2026-05-27).
- **License:** Apache-2.0.
- **Scope:** the single-process server with the 17 default
  plugins enabled per `conf/default.yml`.

## TL;DR

Caldera is a weapons-grade adversary-emulation platform
maintained by MITRE. The upstream project is explicit that
the platform is intended for trusted-environment deployment
and is not a hardened production authentication system. Its
posture deliberately optimises for research flexibility:
in-process plugin loading without signature verification,
operator-declared (not platform-enforced) rules of engagement,
no production-grade audit pipeline. A recent pre-auth RCE
(CVE-2025-27364, Feb 2025) underscored the operator's
responsibility to patch and to keep the server off the public
internet. The accumulation of harvested customer-environment
credentials across engagements is a long-tail single point of
failure with weak default at-rest encryption.

## Findings carried forward

Each entry below is a known-true posture statement. Specialist
reviewers should treat these as accepted starting state and
produce findings against the **second-order consequences**
(impact to auditability, scalability, trustworthiness) rather
than re-discovering the underlying posture.

### Carried — Deployment posture

- **README explicitly recommends segregated-network deployment.**
  > The Caldera server does not have a hardened and thoroughly
  > pentested web application interface, but only basic
  > authentication and security features.
- **MITRE and US Government sponsors run Caldera on segregated
  environments** — the upstream operational model is not
  internet-exposed.
- **CVE-2025-27364 (Feb 2025) — pre-auth RCE.** A public
  Caldera with default config was reachable by remote
  attackers. Operators must patch to v5.1.0+. The advisory
  underscores that the trusted-environment posture is
  load-bearing.

### Carried — Default-credential posture

- **`conf/default.yml` ships static known credentials:**
  - `users.red.red = admin`, `users.red.admin = admin`
  - `users.blue.blue = admin`
  - `api_key_red = ADMIN123`
  - `api_key_blue = BLUEADMIN123`
  - `encryption_key = ADMIN123`
  - `crypt_salt = REPLACE_WITH_RANDOM_VALUE`
- **`--insecure` is required to load `default.yml`.** Otherwise
  `ensure_local_config()` generates a per-deploy `local.yml`
  with auto-generated values on first start.
- **Other shipped defaults:**
  - SSH tunnel user `sandcat`, password `s4ndc4t!`
  - FTP contact user `caldera_user`, password `caldera`

### Carried — Plugin runtime posture

- **Plugins load as in-process Python modules** via
  `importlib.import_module` at server start
  (`AppService.load_plugins`).
- **No signature verification, no publisher allowlist, no
  hash pin.**
- **Plugins run with full server privilege** — can register
  routes, monkey-patch services, spawn subprocesses, read /
  write the filesystem the server user owns, reach any
  network the server can reach.
- **The `builder` plugin invokes the Go toolchain via
  subprocess** to compile sandcat implants; the Go toolchain
  on the server host is in the trust boundary.
- **`auth.login.handler.module` is plugin-replaceable** —
  a plugin can take over the login pipeline (S-4 in the
  threat model).

### Carried — Agent-callback posture

- **10 contact protocols ship** (`http`, `dns`, `ftp`,
  `gist`, `html`, `slack`, `tcp`, `udp`, `websocket`, SSH
  tunnel).
- **No platform-wide beacon-authentication contract.** Each
  contact protocol defines its own (often none).
- **Shipped obfuscators are `plain-text` and `base64`.**
  Neither provides authentication or integrity.
- **HTTP contact (`POST /beacon`) shares the operator API
  port `:8888`.**

### Carried — Operator-action audit posture

- **No structured audit log.** Python `logging` to stdout /
  `rich` console is the only trail.
- **Session principal is not consistently logged with
  per-action events.**
- **No append-only or signed audit store.**
- **Per-command attribution to a human operator is not
  guaranteed on every Link** (Operations carry a creator
  field at create time; ad-hoc / manual flows may not).

### Carried — Engagement-scope (ROE) posture

- **No `Engagement` object in the data model.**
- **No target-host allowlist on agent deployment.**
- **No scope check before launching an operation.**
- **ROE is documented off-platform**; reconciling an
  operation against a ROE document is a manual review task.

### Carried — Data-at-rest posture

- **File system is primary persistence;** no relational
  database.
- **Fernet encryption is on by default** for files written
  by `FileSvc` (`encrypt_files: true`), but the key derives
  from `encryption_key` + `crypt_salt`, both of which ship
  as known defaults in `default.yml`.
- **No retention or deletion policy** for results,
  facts, payloads.
- **No per-engagement partitioning** — every operator with
  filesystem access (or operator-API access) can read every
  engagement's harvested data.

### Carried — Configuration secrets in plain YAML

- `conf/default.yml` carries every key in plaintext.
- No secret-manager integration (no Vault, no AWS Secrets
  Manager, no Kubernetes Secret bind in core).
- The `gist`, `slack`, `chatbot LLM` style credentials all
  ship as `API_KEY` / `SLACK_TOKEN` placeholders in
  `default.yml`; operator-supplied values land in the same
  plaintext file.

### Carried — TLS / transport posture

- **HTTP is the default.** TLS is delivered by the `ssl`
  plugin and is off by default.
- **Self-signed material in `conf/ssh_keys/`** — development
  defaults.
- **No mTLS** between the C2 and implants.

### Carried — Resource-limit posture

- **`client_max_size_mb` (default 1 MB)** for non-v2 endpoints.
- **`api_upload_max_size_mb` (default 100 MB)** for v2.
- **No rate limiter** on the login endpoint.
- **No per-source-IP rate limit** on agent beacons.
- **No max-agent-count bound** in the agent registry.

### Carried — Operational gaps (no procedure in the input set)

- No documented operator API-key rotation procedure.
- No documented cookie / file encryption key rotation procedure.
- No signed plugin update channel.
- No audit-log retention or schema.
- No structured backup / restore procedure (the `data/backup/`
  directory exists but no rotation / retention is documented).
- No network policy in shipped deploy artifacts.
- No MFA at any authentication surface in core.
- No session revocation; default 7-day cookie TTL.
- No production-grade alerting on "your Caldera version is N
  releases behind".

## Reviewer guidance

The specialist agents in this gauntlet should:

1. **Not re-derive the upstream posture.** It is canonical and
   honestly disclosed.
2. **Produce findings against the second-order consequences** —
   the gaps in trustworthiness, scalability, and auditability
   that the above posture creates for an operator running
   Caldera in a real red-team or detection-engineering
   programme.
3. **Treat any silence in the inputs about operational controls
   as "control absent"** and surface the corresponding finding
   (per the APD evidence-discipline rule on block-on-ambiguity).
4. **Use security-tooling-pack vocabulary** (operator, implant,
   engagement, ROE, weapons-platform misuse, harvested
   credentials). Avoid vocabulary from other domain packs.
