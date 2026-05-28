# MITRE Caldera — Operator Runbook

This runbook captures what an operator needs to bring Caldera up,
keep it healthy, and respond to common incident-shaped events. The
upstream project is explicit that Caldera is **not** a hardened
production system; entries marked **GAP** have no documented
procedure in the input set, and specialist reviewers should treat
each as a candidate finding.

## 1. Bring the stack up

### From source

```sh
git clone https://github.com/mitre/caldera.git --recursive
cd caldera
python3 -m venv .calderavenv
source .calderavenv/bin/activate
pip3 install -r requirements.txt
python3 server.py --insecure --build
```

Browse to `http://localhost:8888`. Default login: `red / admin`.

**Caution:** the `--insecure` flag loads `conf/default.yml` —
**known credentials**, **known cookie-encryption key**, **known
API keys** (`ADMIN123`, `BLUEADMIN123`). Use `--insecure` only on
loopback / isolated lab. For any non-trivial deploy, omit
`--insecure`; the server will create `conf/local.yml` with
auto-generated values on first start.

### Docker

```sh
git clone https://github.com/mitre/caldera.git --recursive
cd caldera
docker build --build-arg VARIANT=full -t caldera .
docker run -it -p 8888:8888 caldera
```

The shipped container regenerates keys/usernames/passwords on
first start. Bind-mount `conf/local.yml` to override.

To run all contact-protocol ports (see `docker-compose.yml`):

```sh
docker compose up
```

This exposes `:8888` (HTTP API + HTTP contact + console),
`:8443` (HTTPS via `ssl` plugin), `:7010` (TCP contact),
`:7011/udp` (UDP contact), `:7012` (websocket), `:8853` (DNS
contact), `:8022` (SSH tunnel), `:2222` (FTP contact).

## 2. Health checks

The server exposes a health endpoint via the v2 API:

```sh
curl -s http://localhost:8888/api/v2/health
```

This is one of the few `__caldera_unauthenticated__` handlers and
returns a basic liveness JSON.

For deeper checks:

- Process status: `ps aux | grep server.py` (single process).
- Plugin load errors: server stdout at INFO level shows any
  plugin whose `enable()` raised; aggregated under
  `AppService.errors` (`GET /api/v2/health` exposes them as
  `errors:` in the response).
- Agent registry: `GET /api/v2/agents` (auth required).
- Active operations: `GET /api/v2/operations` (auth required).

## 3. Inspect captured operation evidence

Operation results, including every implant's command output, live
under `data/results/`:

```sh
ls -la data/results/
cat data/results/<link_id>
```

Files are Fernet-encrypted if `encrypt_files: true` (the default
unless explicitly disabled). The decryption key is derived from
`encryption_key` + `crypt_salt`.

Programmatic access via API:

```sh
curl -s -H "KEY: <api_key_red>" \
  http://localhost:8888/api/v2/operations/{op_id}/output | jq
```

## 4. Inspect harvested facts

```sh
curl -s -H "KEY: <api_key_red>" \
  http://localhost:8888/api/v2/facts | jq
```

Facts are the planner's knowledge store. Sensitive material
(credentials, paths, IP addresses) accumulates here across
operations.

## 5. Rotate the operator API keys

**GAP.** No documented rotation procedure ships in the input
set.

What an operator would need to do:

1. Edit `conf/local.yml` and replace `api_key_red` and
   `api_key_blue` with new values.
2. Restart the server (`SIGTERM` is converted to
   `KeyboardInterrupt` by `server.py:_handle_sigterm`, which
   triggers `teardown` and a state save).
3. Re-issue the new keys to every operator and every external
   tool that uses the `KEY` header.

Open questions the inputs do not answer:

- Is there an audit trail of which key was used for which
  request? The `KEY` header is matched in `AuthService`; only
  the matched group (`red` / `blue`) is logged.
- Is there a key-rotation window during which both old and new
  keys are valid? No — the config file holds exactly one key per
  group at a time.

## 6. Rotate the cookie / file encryption key

**GAP.** No documented rotation procedure.

`encryption_key` and `crypt_salt` derive the Fernet key used for
both session-cookie encryption and at-rest file encryption. Rotating
them:

1. Invalidates every existing session cookie (every operator
   logged out).
2. Renders every previously-Fernet-encrypted file under
   `data/` undecryptable unless the operator re-encrypts before
   the rotation.

There is no documented two-key-window or graceful re-encryption
script.

## 7. Plugin update process

**GAP.** No signed plugin update channel.

What an operator does in practice:

1. `cd plugins/<name> && git pull` to update from upstream.
2. Inspect the diff manually (no signature, no hash).
3. Restart Caldera.

Open questions the inputs do not answer:

- How does an operator detect that a plugin has been tampered
  with on-disk (e.g. by a compromised plugin from a
  typosquatted source)?
- Is there an inventory of which plugins are enabled and what
  versions they shipped?

## 8. Inspect audit data

**GAP.** No application-level structured audit log is shipped.

The server emits Python `logging` calls to stdout / `rich`
formatted console output. The aiohttp access log is on by
default (request method, path, status, duration).

What an operator would need for production-grade audit:

- A log shipper (Fluent Bit, Filebeat, Vector) capturing
  per-host stdout to an off-host sink.
- A retention policy on the off-host sink (the platform retains
  nothing).
- A schema for what counts as an audit event (currently none —
  see threat-model R-1).
- Tamper-evidence on stored logs (currently none).
- Per-operator-action correlation (currently the session
  principal is not always emitted with each log line).

## 9. Engagement rules-of-engagement enforcement

**GAP.** ROE is **operator-declared, not platform-enforced**.

The platform has:

- No `Engagement` object.
- No target-host allowlist on agent deployment.
- No geofencing on implant callbacks.
- No scope check before launching an operation against
  a given set of agents.

What an operator does in practice:

- Maintains the ROE document outside Caldera.
- Manually verifies that the agents selected for an operation
  are deployed to in-scope hosts before launching.
- Relies on post-operation review of the Link record to catch
  any out-of-scope execution.

## 10. Multi-tenant isolation

**GAP.** Single-operator pattern dominant; no per-engagement or
per-customer partition.

If multiple operators share a Caldera server:

- Both can see every agent in the registry.
- Both can see every operation, every adversary, every fact.
- The coarse `red` / `blue` group split is the only
  partition; no per-operator scoping.
- Compromise of one operator's credentials exposes every
  other operator's harvested data.

The documented production pattern (where it exists) is
**per-engagement Caldera instances** — stand up a fresh
Caldera per customer, tear it down after the engagement.

## 11. Respond to "implant went rogue / unexpected callback"

If an unexpected implant appears in the registry:

1. Check `GET /api/v2/agents/{paw}` for `hostname`, `architecture`,
   `last_seen` to identify the source.
2. If unrecognised, kill it: `DELETE /api/v2/agents/{paw}`. The
   implant exits at its next beacon.
3. Cross-reference the deploy command history (no platform
   record exists; operator must check shell history on every
   target).
4. If the rogue implant was deployed via S-2 (impersonation),
   the kill instruction reaches a fabricated implant that
   ignores it — there is no out-of-band remediation.

## 12. Respond to "operator credential suspected compromised"

Probable cause: leaked `conf/local.yml`, leaked API key, or
operator-host compromise.

1. **Cannot revoke the existing session immediately.** The
   `EncryptedCookieStorage` cookie is valid until its TTL
   (`session_expiration_days`, default 7) regardless of
   credential change.
2. Edit `conf/local.yml`:
   - Change the password for the affected `users:` entry.
   - Rotate the affected `api_key_<group>`.
   - Optionally rotate `encryption_key` + `crypt_salt` (which
     invalidates all sessions — see §6).
3. Restart Caldera.
4. There is no source-IP / user-agent in the audit trail (no
   structured audit trail exists; see §8).
5. Inspect `data/cookie_storage` if needed — it is Fernet-
   encrypted with the operator's `encryption_key`.

## 13. Respond to "out-of-scope target was engaged"

Probable cause: ROE-enforcement gap (§9), operator mistake.

1. **Cannot undo executed Links** — they have run on the target.
2. Identify the operation: `GET /api/v2/operations` and
   correlate by start time.
3. Identify the implants involved: `GET
   /api/v2/operations/{op_id}/agents`.
4. Identify the executed abilities: `GET
   /api/v2/operations/{op_id}/links` filtered by `state:
   success`.
5. Kill the implants (§11).
6. Initiate the customer-notification process **off-platform**.
   The Caldera server has no notification hooks, no incident
   record, no customer-engagement metadata to attach.

## 14. Patch CVE-2025-27364 (or future CVEs)

The README notes the Feb 2025 RCE CVE-2025-27364 and directs
operators to pull v5.1.0+. Operator workflow:

```sh
cd caldera
git fetch --tags
git checkout v5.1.0   # or latest release tag
pip3 install -r requirements.txt --upgrade
# rebuild Vue UI if present
python3 server.py --build
```

There is no platform-level alerting on "your Caldera version
is N releases behind".

## 15. Tear down

```sh
# Graceful (triggers state save):
kill -TERM <pid>
# Or, in foreground: Ctrl+C
```

Docker:

```sh
docker compose down -v
```

The `-v` wipes the bind-mounted volume; without it the
`data/`, `conf/local.yml`, and `plugins/` state survive
restart.

## 16. Troubleshooting reference

- Plugin failed to load: check `app_svc._errors` via
  `GET /api/v2/health`.
- Agent not appearing: check the contact-listener port is
  open and reachable from the target; check the implant's
  callback URL is correct; check the `untrusted_timer`
  hasn't expired silently.
- Operation stuck: check the planner's selected ability is
  satisfiable against the current fact set (a planner with
  no satisfiable ability simply waits).
- Server stalled: a synchronous plugin call is blocking the
  event loop. Strace / py-spy the process to find the
  offending plugin.

In-depth issues escalate to the upstream MITRE Caldera GitHub
Issues — no internal escalation path is defined in the input
set.
