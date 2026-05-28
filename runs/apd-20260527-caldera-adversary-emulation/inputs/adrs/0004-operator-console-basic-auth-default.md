---
title: 0004 — Operator console basic-auth + static API key default; hardening is operator responsibility
status: accepted
date: 2019-06-14
---

# ADR-0004: Operator console basic-auth + static API key default; hardening is operator responsibility

- **Status:** Accepted
- **Date:** 2019-06-14

## Context

Caldera ships as a self-contained server an operator can stand
up in minutes. The target experience is: `git clone`, `pip
install -r requirements.txt`, `python3 server.py --insecure
--build`, browse to `http://localhost:8888`, log in as
`red/admin`, complete the training plugin's CTF, start working.

The platform is **not** sold as a hardened production
authentication system. It is sold as a research / engagement
platform. Operators who deploy Caldera into a production red-
team workflow are expected to harden it themselves: rotate
credentials, terminate TLS (via the `ssl` plugin), configure
SSO via the externally-maintained `saml` plugin or a custom
`LoginHandlerInterface` implementation, place the server behind
a VPN or behind a network-segregated bastion.

A complex out-of-the-box authentication story (mandatory MFA,
forced password rotation, enforced TLS, mandatory SSO) would
trade off against the "research platform" experience and would
add friction the audience does not want for the lab use case.

## Decision

The operator console ships with **basic credential authentication
plus a static API-key path**, with all defaults configured for
research use and explicit operator action required to harden them.

Specifically:

- **`conf/default.yml`** carries known credentials. The
  `--insecure` flag explicitly loads this config:
  ```yaml
  api_key_blue: BLUEADMIN123
  api_key_red: ADMIN123
  crypt_salt: REPLACE_WITH_RANDOM_VALUE
  encryption_key: ADMIN123
  users:
    blue:
      blue: admin
    red:
      admin: admin
      red: admin
  ```
- **`ensure_local_config()`** runs when `--insecure` is not
  passed and `--environment local` is the default. On first
  start it copies `default.yml` to `local.yml` and rewrites the
  credential / key fields with auto-generated values. On
  subsequent starts it preserves the existing `local.yml`.
- **Session storage** uses
  `aiohttp_session.EncryptedCookieStorage` with a Fernet key
  derived (PBKDF2-HMAC-SHA256) from `encryption_key` +
  `crypt_salt`. Default expiration: `session_expiration_days:
  7`.
- **API-key auth** via the `KEY` HTTP header bypasses the cookie
  pipeline entirely. The two configured keys
  (`api_key_red`, `api_key_blue`) correspond to the two
  built-in permission groups.
- **No MFA** is implemented in core. A `LoginHandlerInterface`
  implementation in a plugin can layer MFA, but no shipped
  plugin does.
- **Pluggable login handler** via
  `auth.login.handler.module` — operators may replace the
  default handler with a plugin (e.g. SAML).
- **TLS** is delivered by the `ssl` plugin, optional and
  off by default. HTTP on `:8888` is the default for both
  operator console and HTTP-contact agent beacons.

## Consequences

**Positive (intended onboarding experience).**

- A new operator is in the training CTF inside five minutes
  with `python3 server.py --insecure --build`.
- The shipped Docker image auto-generates credentials on
  first start (per the Dockerfile / entrypoint), so the
  container case avoids the literal-default-credential
  pitfall by construction.

**Negative / trade-offs.**

- **Weak default posture.** A `--insecure` deploy ships
  known credentials, a known cookie-encryption key, and known
  API keys. CVE-2025-27364 (Feb 2025), an RCE pre-auth, was
  the operationally-significant consequence: a public Caldera
  with default config was reachable by remote attackers.
- **Misconfiguration risk.** An operator who runs
  `python3 server.py --insecure` to "just try it out" and
  then exposes the host (e.g. on a cloud VM with a public IP)
  hands the platform to anyone scanning the internet.
- **No MFA in core** means operator session theft via XSS,
  cookie leak, or credential reuse is unmitigated.
- **No password-rotation policy.** Credentials, once set in
  `local.yml`, never expire.
- **No account-lockout / rate-limit** on the login form
  (threat-model D-1, S-1). Brute-force is fast.
- **`KEY` header API keys are static, long-lived, and bypass
  the session pipeline.** No per-key audit trail beyond
  request logs.
- **Cookie-key derivation is reproducible.** Anyone who
  recovers `encryption_key` and `crypt_salt` (e.g. from a
  default deploy, a config leak, a backup) can forge cookies
  offline.

**Invariants pinned by this ADR (intended, not enforced).**

- Operators replace defaults before exposing the server to
  any untrusted network.
- The two built-in groups (`red`, `blue`) are the coarsest
  unit of permission separation the platform offers.
- TLS, SSO, MFA, and audit-log shipping are operator
  responsibilities (delivered via plugins or off-host).

## Enforcement

- `server.py` requires the explicit `--insecure` flag to load
  `default.yml`.
- `ensure_local_config()` generates a per-deploy `local.yml`
  on first start otherwise.
- The shipped Docker container regenerates credentials on
  first start (per Dockerfile / entrypoint).
- README §Security recommends segregated network deployment.

## Notes

A hardened-by-default future posture would:

1. Refuse to start with shipped default credentials present
   in `local.yml` (no `--insecure` path).
2. Disable the static API-key path unless explicitly enabled.
3. Require TLS on the operator API (HTTP allowed only for
   `/beacon`).
4. Ship a default `LoginHandlerInterface` that enforces
   per-deploy MFA.
5. Add a structured audit-log emitter for every operator
   mutation.

The trade-off — onboarding friction — is the reason this is
not the current direction.
