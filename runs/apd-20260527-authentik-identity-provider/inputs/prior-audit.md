# authentik — Prior Audit Carry-Forward

This entry records the security-posture context that this APD
review inherits. authentik is a published open-source IdP with a
documented external-audit cadence and a substantial CVE archive;
the "prior audit" here is therefore a synthesis of the three
documented external pentests and the per-CVE write-ups under
`website/docs/security/cves/`.

## Source

- **Audits:** Cure53 (2023-06), Cobalt (2024-11), IncludeSec (2025-09).
  Per `security/audits-and-certs/` in the docs tree.
- **CVE archive:** 30+ CVEs published 2022-09 through 2026-08 under
  `website/docs/security/cves/`.
- **Version under review:** **2026.8.0-rc1** per `pyproject.toml`.
  Supported tracks per `SECURITY.md`: **2025.2.x**, **2026.5.x**.
- **License:** MIT core (with CC BY-SA 4.0 docs and a separate EE
  license for `authentik/enterprise/`).
- **Scope:** Server (Django core + embedded outpost), Worker,
  PostgreSQL, optional Redis, four outpost types (Proxy / LDAP /
  RADIUS / RAC), Web UI, REST API, OAuth/OIDC/SAML/LDAP/SCIM
  provider surfaces, Flow + Stage + Policy pipeline,
  CertificateKeyPair-secured secrets.

## TL;DR

authentik has a **mature security posture for an open-source IdP**:
documented audit cadence, structured CVE pipeline, written
hardening guide, in-platform Account Lockdown stage (Enterprise),
support for WebAuthn / FIDO2, optional GeoIP / Reputation
policies, encryption-at-rest for secret-bearing fields via the
CertificateKeyPair model. The dominant residual risks are
**operator-misconfiguration** (the platform's expressiveness is
also its mis-configuration surface) and **intentional-by-design
arbitrary-code execution** (the Expression engine, blueprints,
prompts-with-HTML), which per `SECURITY.md` are documented and
gated on permission-to-edit but are not sandboxed.

## Carry-forward — external audit findings

### Cure53 (2023-06)

The 2023 Cure53 audit is referenced in
`security/audits-and-certs/` but the full report content was not
re-extracted into the inputs. Reviewers should treat this as a
prior baseline; specific findings are out of scope for this
review.

### Cobalt (2024-11)

Per `security/audits-and-certs/2024-11-cobalt.md`:

- **5 low-severity findings + 1 info-level finding.**
- **All 6 closed in the 2024.10.4 patch release** (early November
  2024).
- Cobalt's overall characterization: "The pentesters found that
  the Authentik Security team implemented robust and up-to-date
  security practices throughout the application."

Findings + fixes:

| Finding | Fix |
|---------|-----|
| HTML injection in Flow diagram names | DOMpurify added (PR #11783) |
| SVG icon stored-XSS | CSP header added on `/media` (PR #12092) |
| Footer-link stored XSS | DOMpurify added (PR #11773) |
| Weak password policy (test env) | Strong default password policy added (PR #11793) |
| Lack of CSP header | CSP added in test env; native CSP is operator-driven (per `security-hardening.md`) |
| Unauth private-key download (pre-2024.8) | Fixed in 2024.8.0; tracked as CVE-2024-42490 |

### IncludeSec (2025-09)

Per `security/audits-and-certs/2025-09-includesec.md`:

- **3 highs + 2 mediums + 4 lows + 1 informational** over an
  8-day grey-box assessment.
- Retest completed January/February 2026; all findings either
  fixed, risk-accepted as intentional, or improvements applied.

Findings + responses:

| Finding | authentik response |
|---------|-------------------|
| H1 — Blueprint import allows arbitrary modification | Risk-accepted as intentional behavior; warning banner added in 2025.12 to flow imports (PR #19288) |
| H2 — TOTP brute-force | Closed; stricter rate-limit added to test infrastructure; WAF recommended |
| H3 — Arbitrary Python code execution via expressions | Risk-accepted as intentional behavior per `SECURITY.md`; documented in hardening guide |
| M1 — Anti-brute-force race condition bypass | Fixed in 2025.12 by replacing session-based retries with reputation-driven counters (PR #18643) |
| M2 — Password hashes disclosed via Application launch URL | Closed; Application launch URL format improved (PR #18076) |
| L1 — Unpinned FROM tags in Dockerfiles | Closed; switched to image digests (PR #17795) |
| L2 — User account enumeration via response timing | Improved; replaced randomized sleep with make_password (PR #18883) |
| L3 — Shell command execution without absolute path | Closed; OpenSSL call uses absolute path (PR #17856) |
| L4 — Slowloris DoS via missing server timeouts | Closed; default HTTP server timeouts added (PR #17858); reverse-proxy recommended in production |
| I1 — RADIUS Message-Authenticator validation inversion | In-flight: initially fixed (PR #17855), reverted pending broader client testing |

The risk-accepted intentional findings (H1, H3) reinforce
`SECURITY.md`'s "Intended functionality" section: blueprints and
expressions are documented to allow arbitrary modification /
arbitrary code when the editing permission is held. The platform
treats permission-to-edit as the privilege boundary, not the
expression engine itself.

## Carry-forward — CVE archive themes

The 30+ CVEs under `website/docs/security/cves/` fall into a small
set of recurring patterns. Specialist reviewers should expect
these classes when assessing the codebase:

### Class 1 — API authorization gaps

- **CVE-2024-42490** — Unauthenticated access to
  `/api/v3/crypto/certificatekeypairs/<uuid>/view_certificate/`,
  `/view_private_key/`, and `/.../used_by/`. Mitigated by UUID
  un-guessability; closed by adding authorization checks. Fixed
  in 2024.4.4 / 2024.6.4 / 2024.8.0.

This pattern (DRF view-level permission gaps) is the dominant
authorization-shaped CVE class. The mitigation is consistent: add
the per-object permission check, ship a patch release.

### Class 2 — Token-handling bugs

Token lifecycle, app-password handling, recovery-token handling,
service-account-token handling — multiple CVEs across the 2022–2026
window. Reviewers should treat the Token model and its lifecycle
as a high-frequency-bug area.

### Class 3 — Blueprint-driven exposure

Blueprints can create any object and read any filesystem path. When
blueprint apply is exposed to lesser-privileged actors (e.g.
through an exposed `/api/v3/managed/blueprints*` endpoint), the
exposure compounds. The hardening guide treats this as a top-tier
mitigation target.

### Class 4 — Outpost protocol-handler bugs

The proxy / LDAP / RADIUS outposts each have their own protocol
parsing surface. Bugs here are isolated from Core (per ADR-0003)
but still impact identity assurance for the affected protocol —
e.g. the IncludeSec I1 RADIUS finding above.

## Carry-forward — operational hygiene observations

The following are not vulnerabilities but are visible in the inputs
as operator-driven hardening targets:

- **`AUTHENTIK_SECRET_KEY` rotation procedure is not documented**
  in `sys-mgmt/` (see runbook §5 GAP). Per ADR-0004, secret_key
  is the master decryption key for every stored secret.
- **External secret-manager integration (Vault, SOPS, KMS) is not
  first-class** in the Community surface. Operators must wrap the
  secret_key delivery at the orchestration layer (Kubernetes
  Secret + etcd encryption-at-rest, etc.).
- **Native CSP is not set by authentik**; operators must set it at
  the reverse proxy per `security/security-hardening.md`.
- **Outpost `:9300/metrics` is unauthenticated** by design; not
  for public exposure (per the outpost doc).
- **Outgoing network requests are not filtered** by authentik;
  egress control is operator's responsibility (per `SECURITY.md`).
- **Tenancy is alpha** with explicit cross-tenant Expression access
  caveat (per `sys-mgmt/tenancy.md`).
- **Docker socket mount** is on by default in the compose template
  to support automatic outpost deployment (per
  `install-config/install/docker-compose.mdx`); operators not
  needing the Docker integration should remove it.
- **Cached LDAP outpost bind mode** explicitly does not honor
  session revocation or credential changes for the cache lifetime
  (per the LDAP provider doc).
- **`Ignore Server certificate` on RAC endpoints** is a per-endpoint
  hardening misstep that suppresses RDP-target TLS verification
  (per the RAC provider doc).

## Reviewer guidance

The specialist agents in this gauntlet should:

1. **Not re-derive the known-fixed CVEs.** The CVE archive is
   canonical; treat the post-patch state as the baseline.
2. **Treat the SECURITY.md "Intended functionality" items as
   structural** rather than vulnerabilities — they are documented
   trust-boundary decisions and the right finding is "is the
   operator hardening guidance being followed?", not "is the
   expression engine arbitrary?"
3. **Surface findings against the second-order consequences** —
   the gaps in trustworthiness, scalability, and auditability that
   the platform's expressiveness creates when operators
   under-configure.
4. **Treat silence in the inputs about operational controls as
   "operator-action-required"**, not "control absent" — authentik
   provides the primitives (Reputation policy, GeoIP policy,
   Notification Rules, Brand-based Flow defaults) but does not
   ship every recommended binding out of the box.
5. **Match the identity-security vocabulary** of the active domain
   pack: AAL/IAL/FAL (NIST 800-63), OAuth Security BCP, SAML
   profile considerations, OIDC core, SCIM 2.0, LDAP, RADIUS.
