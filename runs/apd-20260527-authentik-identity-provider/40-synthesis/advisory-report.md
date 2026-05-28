---
framework_version: 1.5.0
domain_pack:
  name: identity-security
  version: 1.0.0
run_id: apd-20260527-authentik-identity-provider
specialists_skipped: []
---

# APD Advisory Report — authentik 2026.8.0-rc1

**Run id:** `apd-20260527-authentik-identity-provider`
**Subject:** authentik 2026.8.0-rc1 (open-source Identity Provider, MIT-licensed)
**Domain pack:** identity-security v1.0.0
**Framework version:** 1.5.0
**Date:** 2026-05-27

---

## Executive summary

authentik is a production-grade open-source Identity Provider with a
mature security posture: documented external-audit cadence (Cure53 2023,
Cobalt 2024, IncludeSec 2025), structured CVE pipeline with ~30 published
advisories from 2022–2026, written hardening guide, in-platform Account
Lockdown stage (Enterprise), WebAuthn / FIDO2 phishing-resistant MFA
support, encryption-at-rest for secret-bearing fields via the
`CertificateKeyPair` model. This advisory does not re-derive the
known-fixed CVEs; per the run guidance, the carry-forward posture is the
baseline.

The dominant residual risks cluster in three themes that are themselves
load-bearing architectural facts, not defects:

1. **The Expression engine has NO sandbox by deliberate design.** Per
   `SECURITY.md` and ADR-0001: "Expressions (property mappings / policies
   / prompts) can execute arbitrary Python code without safeguards." The
   trust boundary is permission-to-edit-Expressions. The IncludeSec
   2025-09 finding H3 risk-accepted this as intentional. Per `agents.md`
   and `runbook.md` §10, the recommended hardening is to block
   `/api/v3/policies/expression*`, `/api/v3/propertymappings*`,
   `/api/v3/managed/blueprints*`, `/api/v3/stages/captcha*` at the
   reverse proxy — operator-action-required. The unhardened community
   install presents the Expression engine as in-platform RCE for any
   admin.

2. **The per-installation `AUTHENTIK_SECRET_KEY` is the master decryption
   key.** Per ADR-0004: every per-Provider signing key, OAuth
   `client_secret`, Source credential, and API token in the database is
   encrypted under this key. The key lives in the Server / Worker
   process environment. Combined with theme 1, this means any Expression
   policy can read it via `os.environ`. There is no documented rotation
   procedure (`runbook.md` §5 GAP) and no external-KMS binding for
   community-tier installs.

3. **Tenancy is alpha and Expression policies have access to all
   tenants** (`sys-mgmt/tenancy.md` documented caveat,
   `INV-AUTHZ-004` partially-false). Multi-tenant deployments using the
   alpha tenancy feature should treat the cross-tenant Expression access
   as a known caveat until GA.

The findings in this report are organised around these themes and their
second-order consequences across the nine APD goals. The recommendations
are calibrated to the platform's documented architecture; they do not
suggest reversing the documented design choices (Expression engine
arbitrariness, master-key-in-process-env, blueprint-arbitrary-modification)
but rather propose shipped-default-hardening, observability improvements,
and explicit operator-decision points that move the
operator-action-required hardening surface from "improvised" to
"platform-recommended with defaults."

### Headline statistics

| Category | Count |
|---|---|
| Total findings (deduped) | 66 |
| Critical | 2 |
| High | 42 |
| Medium | 22 |
| Low / Informational | 0 / 0 |
| Findings merged across lenses | 5 |
| Findings linked across lenses | 9 |
| Blocked-on-evidence | 11 |
| Contradictions for human review | 0 |
| Severity disagreements | 0 |
| Capabilities confirmed | 23 |
| Capabilities at maturity `implemented` or higher | 1 |

---

## Critical findings

### conf-a1b2c3d4 — `AUTHENTIK_SECRET_KEY` is single master decryption key for all stored secrets; in-process reachable from any Expression policy

**Confidentiality · risk · critical**

Per ADR-0004 the per-installation symmetric key encrypts every signing
key, OAuth client_secret, Source credential, and Token in the database.
Per ADR-0001 any admin with Expression-edit privilege has arbitrary
Python and can read `os.environ['AUTHENTIK_SECRET_KEY']`. The
compensating control — the reverse-proxy API blocklist on
`/api/v3/policies/expression*`, `/api/v3/propertymappings*`,
`/api/v3/managed/blueprints*` per `security-hardening.md` — is
operator-action-required and not enforced at install time.

The severity-rubric anchor is **"Token signing key compromise"**: mass
unmasking of per-Provider signing keys yields universal token forgery
across every RP that trusts authentik, plus lateral movement out to
every SCIM target / Source / downstream system whose credentials the IdP
holds (`service_account_credential_store` crown jewel).

**Recommendation (required):** Ship a default-hardened install profile
that applies the reverse-proxy API blocklist in the published Helm chart
and CloudFormation template; document and supply an external-KMS binding
(AWS KMS, GCP KMS, Vault Transit) for per-field encryption so per-field
DEKs are wrapped by a KMS-held KEK rather than the in-process
`AUTHENTIK_SECRET_KEY`. ADR-0004 itself flags this gap.

### intg-a1b2c3d4 — OAuth Provider with no Signing Key configured silently falls back to HMAC-signing JWTs with the Provider `client_secret`

**Integrity · risk · critical**

Per `tech_plan.md` §6 and INV-AUTH-003: "If no Signing Key is selected,
JWTs are HMAC-signed with the Provider's client secret — the
symmetric-fallback surface." This inverts the modern OAuth Security BCP
posture (RFC 9700 §4 emphasises asymmetric signing). A leaked
`client_secret` (CI log, repo, mobile-app extraction, vendor compromise)
becomes signing-key-equivalent for that RP. Forgery scope is
RP-bounded but for that RP it is universal-subject-impersonation.

The severity-rubric anchor is **"JWT algorithm confusion at the issuer."**

**Recommendation (required):** Make Signing Key required-on-create for
new OAuth Providers; auto-issue a per-Provider asymmetric key at
Provider creation if the operator does not select one. For existing
Providers without a Signing Key, emit a high-severity Event at the next
token issuance and surface it on the Admin UI dashboard until
remediated. Document the deprecation timeline for HMAC-with-client_secret.

---

## High-severity findings by theme

### Theme 1 — Master-key and secret-management hardening pass

The two critical findings above are the head of a cluster of seven
high-severity findings on the secret-management surface that ship as a
coordinated hardening pass:

- **conf-b2c3d4e5** — PostgreSQL transport TLS is operator-configurable
  but not default. The application-layer encryption keyed by
  `AUTHENTIK_SECRET_KEY` is sound, but the transit layer is plaintext on
  every write — including audit content, session cookies, and the
  encrypted-secret rows.
- **conf-c3d4e5f6** — The embedded outpost shares the Server's process
  space; a bug in its HTTP handler reads `os.environ` and recovers the
  master key. ADR-0003 explicitly trades isolation for deployment
  convenience.
- **conf-d4e5f6a7** (merged) — Backup file encryption with an
  operator-managed key distinct from `AUTHENTIK_SECRET_KEY` is not
  specified; backup immutability (object-lock / compliance-mode) is not
  specified. Co-located `pg_dump` + `.env` compromise = total unmasking;
  the IdP backup is the post-breach recovery anchor for every dependent
  application.
- **conf-a7b8c9d0** (merged) — Outpost-to-Server WebSocket TLS
  requirement is unenumerated (INV-OPS-005 GAP). The service-account
  token and the OAuth client_secret configuration payload traverse the
  link. On a plaintext channel a passive observer recovers both.
- **conf-c9d0e1f2** (merged) — `AUTHENTIK_SECRET_KEY` rotation procedure
  is not documented (runbook §5 GAP, ADR-0004 §Negative item 3).
  Effective key lifetime is unbounded; a compromise is permanent.
- **ephem-b2c3d4e5** — Per-Provider signing-key rotation cadence is not
  enforced; runbook §6 explicitly notes no shipped expiry-warning rule.
- **immut-d4e5f6a7** — Signing-key rotation history retention is not
  enumerated. After a signing-key compromise the operator cannot scope
  blast radius by kid + time window.

**Coordinated remediation:** ship a default-hardened deployment profile
(API blocklist + PG TLS + WebSocket TLS + outpost separation +
external-KMS binding option) and a secret-key-rotation runbook with a
shipped re-key blueprint. The seven findings ship together as the
master-key hardening pass.

### Theme 2 — Identity and authentication assurance

Seven high-severity findings cover the per-surface authentication
assurance story:

- **auth-a1b2c3d4** — MFA enforcement on admin Groups is
  operator-action-required per runbook §10. Default
  `default-authentication-flow` does not bind MFA for admins. The
  critical-rubric clause "MFA optional on administrative surfaces" is
  bordered.
- **auth-b2c3d4e5** — Authenticator Validation stage allows SMS-OTP and
  email-OTP fallback on a Flow whose `acr` claim would assert AAL3 to
  RPs; no platform-enforced minimum-AAL-per-Flow policy.
- **auth-e5f6a7b8** — Federation-trust onboarding has no domain-control
  validation on redirect_uri hosts, no contact attestation, no approval
  workflow. The malicious-RP onboarding surface is open to operators
  who self-service Provider creation.
- **auth-f6a7b8c9** — RAC `Ignore Server certificate` per-Endpoint
  setting suppresses RDP TLS verification; an opt-in misstep yields
  MITM on remote-machine sessions.
- **auth-a7b8c9d0** — Service-to-service auth inside the IdP cluster
  (Server / Worker → PostgreSQL) is static-credential bearer-token, not
  SPIFFE / workload identity / mTLS.
- **intg-c3d4e5f6** — Source attribute mapping can write
  `is_superuser=True` to the local User. `INV-FED-001` is not
  platform-enforced — it relies on operator property-mapping discipline.
- **ephem-c3d4e5f6 / auth-c3d4e5f6** (merged) — OAuth client
  authentication defaults to `client_secret_basic`; modern alternatives
  (`private_key_jwt` RFC 7523, `tls_client_auth` RFC 8705) are not
  first-class at registration. Client_secret rotation cadence and
  procedure are undocumented.

**Coordinated remediation:** ship a hardened default authentication
flow that binds MFA for admin Groups by default, enforces minimum-AAL
per Flow on the authenticator_validate stage, and presents modern
client-auth options at OAuth Provider creation. Add a Federation Trust
Establishment workflow.

### Theme 3 — Audit and accountability

Eight high-severity findings cover the audit / Non-Repudiation /
Immutability surface:

- **nonrep-a1b2c3d4** — Expression-policy side-effecting helpers
  (`ak_send_email`, `ak_create_jwt`, `ak_call_policy`) do not auto-emit
  audit Events. The `ak_create_event` helper is opt-in. Per ADR-0001
  this is the documented behavior.
- **nonrep-b2c3d4e5** — Audit pipeline is operator-driven via container
  stdout aggregation; absent log forwarding the Postgres-resident
  Event log is the sole substrate and an attacker with DB write
  (or Expression-policy RCE) can edit it.
- **nonrep-c3d4e5f6** — Per-token audit anchor (linking issuance,
  refresh, revocation, use via JWT `jti` or opaque token-ID) is not
  enumerated; forensic reconstruction of token theft cannot answer
  "which token was used when."
- **nonrep-d4e5f6a7** — Cached LDAP outpost binds are audited only on
  cache-miss; per-bind audit during the cache lifetime is incomplete.
- **nonrep-a7b8c9d0** — OAuth consent grant is audited; per-use of the
  granted scope is not — GDPR Article 5(2) accountability gap.
- **nonrep-b8c9d0e1** — SAML assertion issuance is audited; per-assertion
  attribute-release set is not enumerated as captured. Pairs with
  conf-e5f6a7b8 (default SAML attribute over-release).
- **immut-a1b2c3d4** — Event records are mutable PostgreSQL rows; no
  hash-chain, no WORM substrate, no append-only enforcement.
- **immut-c3d4e5f6** — OAuth UserConsent records appear mutable;
  consent revocation as a new event vs. overwrite is not asserted.
  GDPR Article 6(1)(a) accountability fails for in-window processing.

**Coordinated remediation:** ship per-stream hash-chaining for Event
records with daily chain-head anchoring to a separate trust domain;
make Expression helpers auto-emit Events with operator opt-out only;
add per-token audit fields covering the full token lifecycle; ship
default SIEM-forwarding deployment artifacts.

### Theme 4 — Availability and topology

Eight high-severity findings cover the operational scale story:

- **avail-a1b2c3d4** — Default flows do not bind Reputation /
  Password / GeoIP policies; rate-limiting is operator-action-required
  on every credential-touching endpoint (/authorize, /token, MFA
  challenge, recovery).
- **avail-b2c3d4e5** — Per-endpoint SLO targets and burn-rate alerts
  are not shipped (blocked-on-evidence).
- **avail-c3d4e5f6** — PostgreSQL is the universal SPOF for identity /
  session / audit / secret material. Per ADR-0002 the loss = total
  platform unavailability.
- **dist-a1b2c3d4** — Multi-region active-active topology, cross-region
  replication policy, RPO targets, and per-tenant residency are not
  specified.
- **dist-b2c3d4e5** — Embedded outpost shares the Server's failure
  domain (paired with conf-c3d4e5f6 from the Confidentiality lens).
- **dist-c3d4e5f6** — Postgres carries primary state + task queue
  (dramatiq) + channels-layer (pub/sub) + cache; a single substrate
  incident degrades every subsystem simultaneously.
- **resil-a1b2c3d4** — OAuth refresh-token reuse detection (OAuth 2.1
  §6.1 rotation-with-family-revocation) is not asserted.
- **resil-b2c3d4e5** — Circuit breakers on outbound Source / SCIM /
  webhook calls are not enumerated.
- **resil-c3d4e5f6** — Bulkheading between user-facing auth and
  admin/background paths is absent; an admin bulk operation can
  starve user-facing auth.
- **resil-e5f6a7b8** — Cached LDAP outpost mode violates session-
  revocation invariant for cache lifetime; no fail-closed mechanism on
  credential change.

**Coordinated remediation:** ship a multi-region reference architecture
document; document Postgres HA topology (managed multi-AZ, Patroni
patterns); document the trade-off between Postgres-only and
Redis-for-cache-and-channels-layer; implement OAuth 2.1 refresh-token
reuse detection by default; add circuit-breaker and bulkhead patterns
on the outbound call surface.

### Theme 5 — Operational-lifecycle hygiene

The remaining high-severity findings cover operational discipline gaps:

- **intg-d4e5f6a7** — Account Lockdown atomic-revocation is
  Enterprise-only; Community-tier operators run a five-step manual
  procedure with race-condition exposure during compromise response.
- **ephem-d4e5f6a7** — SCIM target static tokens (community-tier
  default) have no documented rotation procedure; OAuth-token mode is
  Enterprise.
- **intg-e5f6a7b8** — OAuth redirect-URI regex permits `.` un-escaped
  matching; permissive allowlist class.
- **intg-c9d0e1f2** — Forward-auth header trust model: the protected
  app reads `X-authentik-username` as authoritative; any request that
  bypasses the outpost reaches the app un-checked.
- **intg-d0e1f2a3** — SAML NameID email-policy is documented as
  unstable (users can change email) but remains a per-Provider option.
- **immut-e5f6a7b8** — Federation-trust changes are admin-tier
  consequential actions without GitOps drift detection between
  blueprint-declared and live state.
- **conf-e5f6a7b8** — Default SAML attribute mappings release UPN +
  Group + Email + Name + User ID + Username + WindowsAccountName to
  every SP unless operator strips them.

**Coordinated remediation:** ship Account Lockdown atomicity for
Community tier (or a single-API-call equivalent); ship SCIM target
static-token rotation (or community-tier OAuth-token mode); validate
redirect_uri regexes at save time; deprecate Email NameID in new SAML
Providers; add a `Configuration Drift Detected` dashboard / Event class;
default SAML attribute release to minimum-necessary on new Provider
creation.

---

## Medium-severity findings (summary)

Twenty-two medium-severity findings cover the secondary surface: per-Flow
timeouts (avail-d4e5f6a7), shallow health probes (avail-e5f6a7b8), SCIM
worker-pool starvation (avail-f6a7b8c9), session-affinity (dist-e5f6a7b8),
session-lifetime-per-AAL defaults (ephem-f6a7b8c9), default self-signed
certificate validity (ephem-a7b8c9d0), Account Lockdown audit context
(nonrep-f6a7b8c9), per-audit-class retention (immut-f6a7b8c9), and the
documentation-deficiency cluster on cache TTLs, Slowloris timeouts in
current branch, OIDC pairwise subject support, audit time-source
discipline, and outpost-local Postgres boundary. These are listed in
`40-synthesis/deduped-findings.yaml` with their full evidence and
recommendation context.

---

## Blocked-on-evidence findings (11)

These findings cannot be assessed without specific additional artifacts.
They are first-class output: a "what we need to complete this assessment"
posture, not failures.

1. **intg-b2c3d4e5** — Code-level SAML XSW resistance confirmation
   (defusedxml + xmlsec dependency stack is correct; higher-level
   re-parse-and-compare discipline not asserted).
2. **intg-f6a7b8c9** — OAuth `state` / OIDC `nonce` / PKCE per-Provider
   validation matrix.
3. **avail-b2c3d4e5** — Per-endpoint SLO targets and burn-rate alert
   definitions.
4. **avail-a7b8c9d0** — Current default HTTP timeout values in the
   2026.x branch (IncludeSec L4 fix shipped 2025.12; carry-forward
   confirmation needed).
5. **avail-b8c9d0e1** — Source-IdP outage degraded-mode behavior.
6. **dist-d4e5f6a7** — Outpost-local Postgres boundary
   (`gorm.io/driver/postgres` in `go.mod`; INV-OUTPOST-002 GAP).
7. **dist-e5f6a7b8** — Flow-executor sticky-session requirement across
   replicas.
8. **ephem-b8c9d0e1** — Cached LDAP outpost bind cache TTL default.
9. **auth-b8c9d0e1** — OIDC `pairwise` subject type support.
10. **nonrep-e5f6a7b8** — Audit time-source posture (NTP, drift bounds,
    precision).
11. **immut-f6a7b8c9** — Per-audit-class retention policy.

Resolving these would tighten the assessment by converting
block-on-evidence findings to either gap / risk / uncertainty (or to
capability records, if the evidence supports the property holding).

---

## Capabilities — confirmed

The platform has 23 deduped capabilities at the documented-design
maturity floor (22 `designed`, 1 `implemented`). The single
`implemented`-grade capability is the post-IncludeSec 2025.12 reputation-
driven anti-brute-force counter (`resil-cap-a1b2c3d4`) — the prior-audit
remediation evidence supports the higher maturity.

The full capability list spans every APD goal. Highlighted clusters:

- **Crypto and key handling**: field-level encryption under
  `AUTHENTIK_SECRET_KEY` (conf-cap-a1b2c3d4), per-Provider signing-key
  isolation (conf-cap-b2c3d4e5), argon2-cffi password hashing
  (conf-cap-c3d4e5f6), defusedxml + xmlsec SAML stack (intg-cap-a1b2c3d4),
  JWE for sensitive ID-token claims (intg-cap-c3d4e5f6).
- **Identity and authenticator strength**: WebAuthn / FIDO2 phishing-
  resistant authenticator support (auth-cap-a1b2c3d4),
  AuthnContextClassRef / acr claim from authenticators used
  (auth-cap-c3d4e5f6).
- **Audit and accountability primitives**: Flow-execution audit Events
  (nonrep-cap-a1b2c3d4), Notification Rules bound to Event Matcher
  policies (nonrep-cap-b2c3d4e5), 365-day retention default
  (nonrep-cap-c3d4e5f6).
- **Topology and resilience**: outposts as separate failure domains
  (dist-cap-a1b2c3d4, resil-cap-b2c3d4e5), Reputation-policy primitive
  for rate-limiting (avail-cap-b2c3d4e5, resil-cap-a1b2c3d4),
  Account Lockdown atomic compromise-response Enterprise feature
  (resil-cap-c3d4e5f6), multi-replica + managed-Postgres HA story
  (avail-cap-c3d4e5f6).
- **Configuration**: blueprint-driven declarative configuration
  (immut-cap-a1b2c3d4), per-Provider signing-key rotation via blueprint
  (ephem-cap-a1b2c3d4), object-level RBAC via Django-Guardian
  (intg-cap-d4e5f6a7).

Capability caveats are extensive — most capabilities carry explicit
notes about operator-action-required default-binding (Reputation
policy not bound on default flows, Notification Rules not shipped
defaults, MFA-on-admin not default, etc.). The capability+caveat
record is the right place to find the "what authentik provides" view;
the findings are the "what operators must do to make it work" view.

---

## NIST 800-53r5 coverage summary

92 unique controls cited across the corpus. The SC, AU, IA families
dominate (cryptography + audit + identification — expected for an IdP).
SI is significant due to input-validation and resilience findings. CP
and CM are moderately cited via DR and configuration-management findings.

Most-cited controls:

- SC-12 (Cryptographic Key Establishment and Management): 12 findings —
  the key-management surface
- SI-13 (Predictable Failure Prevention): 11 findings — the
  resilience / availability cluster
- IA-5 (Authenticator Management): 9 findings — credential lifecycle
- SC-5 (Denial of Service Protection): 8 findings — rate-limit + bulkhead
- SI-10 (Information Input Validation): 8 findings — validation /
  XSW / mass-assignment
- AU-12 (Audit Record Generation): 7 findings — audit completeness
- SI-7 (Software and Information Integrity): 7 findings —
  tamper-evidence / signature verification

The full per-control mapping is in `40-synthesis/nist-coverage.yaml`.

---

## MITRE ATT&CK exposure summary

24 unique techniques cited across the corpus. The Credential Access
tactic (TA0006) dominates (25 finding-mappings vs. 5 capability-mitigations
= net exposure 20). The pattern is identity-provider-shaped: token-
forgery (T1606), MFA-bypass (T1556 / T1621), credential exposure
(T1552 / T1040). Impact (TA0040) is second (audit tampering + backup
destruction + endpoint DoS).

Highest net-exposure techniques:

- **T1606.001 — Forge Web Credentials: Web Cookies** — 4 findings, 1
  mitigation. The JWT-forgery cluster: HMAC fallback + master-key
  reachability + redirect-URI regex + rotation cadence + rotation
  history. Substantial uncovered exposure.
- **T1485 — Data Destruction** — 3 findings, 0 mitigations.
  PostgreSQL SPOF + backup mutability + missing multi-region.
- **T1070 — Indicator Removal** — 3 findings, 0 mitigations. Audit
  pipeline + helper non-emission + Event-log mutability.
- **T1078 — Valid Accounts** — 5 findings, 3 mitigations. Admin MFA +
  Source attribute injection + SCIM static token + forward-auth header
  trust + federation onboarding.

The full ATT&CK exposure rollup is in `40-synthesis/attack-exposure.yaml`.

---

## CWE / OWASP cross-references

CWE base / variant mappings appear on 24 of 66 findings, primarily:

- **CWE-321** (Hard-coded Cryptographic Key) — master-key in process env
- **CWE-347** (Improper Verification of Cryptographic Signature) — SAML
  XSW uncertainty
- **CWE-345** (Insufficient Verification of Data Authenticity) —
  forward-auth header trust
- **CWE-287** (Improper Authentication) — admin MFA, OAuth client auth
- **CWE-307** (Improper Restriction of Excessive Authentication Attempts)
  — default rate-limit gap
- **CWE-294** (Authentication Bypass by Capture-replay) —
  refresh-token reuse
- **CWE-613** (Insufficient Session Expiration) — cached LDAP, session
  lifetime defaults
- **CWE-798** (Use of Hard-coded Credentials) — SCIM static tokens, PG
  bind credentials
- **CWE-916** (Use of Password Hash With Insufficient Computational
  Effort) — none cited; the platform uses argon2-cffi
- **CWE-117** (Improper Output Neutralization for Logs) — audit
  mutability
- **CWE-778** (Insufficient Logging) — audit-completeness cluster

OWASP Top 10 (web — 18 mappings, primarily A02 / A07 / A09) and
OWASP API Top 10 (9 mappings, primarily API2 / API3 / API4 / API8 / API9)
are anchored to the appropriate surfaces.

---

## Recommended next steps

Three coordinated changes would close the largest share of the
high-severity surface:

1. **Ship a hardened default install profile.** Apply the reverse-proxy
   API blocklist by default in the published Helm chart and
   CloudFormation template; default PostgreSQL TLS to required; default
   the outpost-to-Server WebSocket to TLS-required; bind Reputation
   policy + Password policy + MFA-on-admin policy on the shipped
   default-authentication-flow. Operators who want the unhardened
   posture (development, single-server lab) explicitly disable.

2. **Ship the secret-key rotation runbook plus external-KMS binding
   option.** Author `sys-mgmt/ops/secret-key-rotation.md` with a tested
   re-key blueprint; document the external-KMS binding pattern for
   per-field encryption (AWS KMS, GCP KMS, Vault Transit); ship per-
   Provider signing-key rotation cadence default with shipped Notification
   Rule.

3. **Ship audit-pipeline hardening.** Per-stream hash-chaining for
   Event records with daily chain-head anchoring; default log-forwarding
   deployment artifacts (Fluent Bit / Vector configurations for common
   SIEM targets); make Expression-policy side-effecting helpers
   auto-emit Events with operator opt-out only; add per-token audit
   anchor fields (JWT `jti`, opaque ID, refresh-token family).

Together these three changes close the master-key reachability theme,
the audit-tampering theme, and the default-rate-limit theme — which
collectively cover the largest share of the high-severity findings.

The remaining findings are operational and architectural improvements
that the upstream project can prioritise per its own roadmap. The
blocked-on-evidence findings should be resolved by the next gauntlet
re-run with the additional artifacts in place.

---

## Out-of-scope reminders

Per `tech_plan.md` §12 and the run config, the following are explicitly
out of scope for this advisory:

- Browser-class attacks on the Lit web UI (covered partially by the
  carry-forward Cobalt 2024 audit findings).
- Supply-chain compromise of upstream base images.
- Specific social-login provider OAuth Source variants (each is a
  pre-built OAuth Source; the platform-side ingestion is the in-scope
  surface).
- The Enterprise-tier-only features (Account Lockdown, Password
  Uniqueness, Tenancy, RAC, Endpoint GDTC, SCIM-OAuth) are described
  for context; finding analysis emphasises the community-tier surface
  but does not exclude the Enterprise observations where relevant.

The IncludeSec 2025-09 audit findings H1 (blueprint arbitrary
modification) and H3 (Expression engine arbitrary Python) are
classified as risk-accepted intentional by the upstream project per
`SECURITY.md`. This advisory treats them as documented architectural
choices and focuses on second-order consequences and the hardening
guidance.

---

## Run metadata

- Run id: `apd-20260527-authentik-identity-provider`
- Run directory:
  `runs/apd-20260527-authentik-identity-provider/`
- Total artifacts: 13 inputs (3,653 lines)
- Phases complete: Intake, Threat Model Recon, Trustworthiness,
  Scalability, Auditability, Synthesis
- Specialists skipped: none
- Code reconnaissance: disabled (per run config)
- Threat-model evaluator (Phase 5.5): available but not invoked in this
  delivery
- Attack-path analyzer (Phase 5.6): available but not invoked in this
  delivery
- Synthesis outputs: `deduped-findings.yaml`, `deduped-capabilities.yaml`,
  `contradictions.yaml`, `severity-disagreements.yaml`,
  `nist-coverage.yaml`, `attack-exposure.yaml`,
  `apd-coverage-matrix.yaml`, `report-data.yaml`, `advisory-report.md`
