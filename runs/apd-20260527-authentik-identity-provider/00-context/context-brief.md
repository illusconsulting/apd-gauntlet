# Context Brief — authentik 2026.8.0-rc1

Run id: `apd-20260527-authentik-identity-provider`
Domain pack: `identity-security` v1.0.0
Framework version: 1.5.0
Methodology hint: STRIDE (per `threat-model.md` frontmatter)

## Subject

authentik is an open-source Identity Provider and Single Sign-On platform
(MIT-licensed core; CC BY-SA 4.0 docs; EE-licensed enterprise modules).
Version under review is **2026.8.0-rc1**. authentik centralises:

- OAuth 2.0 / OIDC token issuance (authorization-code, implicit, hybrid,
  client-credentials, device-code, refresh-token grants; PKCE supported).
- SAML 2.0 (HTTP-Redirect / HTTP-POST bindings; per-Provider signing and
  optional assertion encryption; configurable NameID policy).
- LDAP backend exposure (LDAP / LDAPS) via the LDAP outpost.
- RADIUS with EAP via the RADIUS outpost.
- SCIM 2.0 outbound provisioning.
- Forward-auth (Caddy-style) via the Proxy outpost / embedded outpost.
- RAC (browser-mediated RDP/SSH/VNC) via the RAC outpost (Enterprise).

The distinguishing architectural primitive is the **Flow + Stage + Policy
pipeline**: every interactive identity journey (authentication, enrollment,
recovery, unenrollment, user settings) is a named ordered sequence of Stage
Bindings, each optionally gated by Policies. Per ADR-0001 the most powerful
Policy type is the **Expression policy** — server-side Python with no
sandbox per the project's own `SECURITY.md`. This is a documented
architectural choice; the trust boundary is permission-to-edit-Expressions.

## Operator profile

Enterprise IT / platform-engineering teams running authentik as the identity
authority for a fleet of downstream applications. Production deployments
run multiple Server replicas, multiple Worker replicas, replicated or
managed PostgreSQL, redundant outposts. Compliance posture commonly
includes SOC 2 / ISO 27001 / GDPR exposure where authentik is the SSO
control. Per `agents.md`, the operator is expected to apply the hardening
guidance from `security-hardening.md`, configure log forwarding, rotate
secrets, and bind the Reputation / GeoIP / Notification primitives that
authentik provides but does not enable out of the box.

## Artifact index

| Artifact | Type | Relevance hints |
|---|---|---|
| `tech_plan.md` (656 lines) | tech_plan | All 9 APD goals; protocol surface enumeration; trust boundaries; data model; CertificateKeyPair posture; per-Provider signing key isolation; Expression engine NO sandbox declaration; default audit retention 365d; HMAC fallback when Signing Key absent. |
| `architecture-index.md` (314 lines) | design_doc | Distributed (component topology); Resilient (failure isolation across outposts); Authenticity (trust boundary inventory); Confidentiality (CertificateKeyPair material catalog per component); Integrity (header-stamp trust model on Proxy outpost). |
| `threat-model.md` (817 lines, STRIDE) | threat_model | All 9 goals; STRIDE per protocol surface; explicit Tenancy alpha caveat; SAML XSW residual question; Expression engine RCE classification; outpost-to-Server WebSocket TLS gap. |
| `happy-path.md` (285 lines) | design_doc | Authenticity (user enrollment + login flow); Integrity (OAuth code-exchange happy path); Confidentiality (LDAP outpost path). |
| `runbook.md` (339 lines, explicit GAP markers) | runbook | Ephemeral (`AUTHENTIK_SECRET_KEY` rotation GAP §5); Availability (outpost token rotation GAP §7); Immutability (backup encryption GAP §8); Authenticity (WebAuthn recovery §11). |
| `prior-audit.md` (196 lines) | audit_artifact | All goals; IncludeSec 2025-09 carry-forward; Cobalt 2024-11 closed findings; ~30 CVE archive themes; explicit risk-acceptance for H1 (blueprint) and H3 (expression engine). |
| `agents.md` (113 lines) | design_doc | Operator capability and expectation surface; configuration-conditional invariants. |
| `invariants.md` (281 lines) | design_doc | All goals; 22 architect-asserted invariants with reviewer-validation notes; explicit `INV-AUTHZ-004` partially-false-in-alpha; `INV-FED-001` not-platform-enforced. |
| `adrs/0001-flows-stages-policies-pipeline.md` (155 lines) | adr | Authenticity, Integrity, Non-Repudiation (Expression engine documented arbitrary Python; `ak_create_event` opt-in). |
| `adrs/0002-django-celery-redis-postgresql-stack.md` (148 lines) | adr | Distributed (Postgres SPOF); Availability (Django CVE inheritance); Resilient (Postgres-backed queue). |
| `adrs/0003-outpost-architecture-for-protocol-handlers.md` (160 lines) | adr | Distributed (outpost deployment); Resilient (failure isolation); Authenticity (outpost service-account tokens); Ephemeral (cached LDAP bind invariant violation). |
| `adrs/0004-encrypted-secrets-via-certificatekeypair.md` (173 lines) | adr | Confidentiality (`AUTHENTIK_SECRET_KEY` master key story); Ephemeral (secret_key rotation GAP); Immutability (CertificateKeyPair audit posture); Authenticity (signing key isolation). |
| `adrs/README.md` (29 lines) | adr | Index; references the four ADRs above. |

## Capability and surface summary

**Identity-provider surfaces (in trust order — most-trusted first):**

1. **REST API** (`/api/v3/...`). Bearer-token authenticated. Privileged
   subset per `security-hardening.md`: `/api/v3/policies/expression*`,
   `/api/v3/propertymappings*`, `/api/v3/managed/blueprints*`,
   `/api/v3/stages/captcha*` — recommended to block at the reverse proxy.
2. **OAuth/OIDC endpoints** (`/application/o/...`). Per-Application slugs;
   per-Provider JWKS at `/application/o/<slug>/jwks/`.
3. **SAML endpoints** (`/application/saml/<slug>/`). Unified SSO+SLO.
4. **LDAP/LDAPS** via LDAP outpost ports 389 / 636.
5. **RADIUS** via RADIUS outpost.
6. **SCIM target callers** (authentik as provisioning source — outbound).
7. **Forward-auth header consumers** (Proxy outpost / embedded outpost).
8. **RAC sessions** via RAC outpost.
9. **WebSocket** (`/ws/outpost/...`) for outpost configuration push.
10. **Web UI** (`/if/admin/`, `/if/user/`, `/if/flow/<slug>/`).

**Crown-jewel localisation:**

- **`signing_key_material`** — per-Provider OAuth and SAML signing private
  keys stored in `CertificateKeyPair` model in PostgreSQL, encrypted under
  `AUTHENTIK_SECRET_KEY`.
- **`password_hash_store`** — User model `password` field; Django default
  hasher augmented by `argon2-cffi==25.1.0` per `pyproject.toml`.
- **`mfa_secret_store`** — TOTP seeds, WebAuthn credential records,
  recovery codes, Duo binding state stored on Authenticator-device models
  in PostgreSQL.
- **`oauth_client_secret_registry`** — per-Provider `client_secret` field
  encrypted under `AUTHENTIK_SECRET_KEY`.
- **`session_token_store`** — Session model rows in PostgreSQL (or
  optionally Redis when configured).
- **`federated_identity_mapping`** — Source-driven attribute mappings;
  upstream-IdP-to-local-User mapping persisted on User model.
- **`consent_record_store`** — OAuth UserConsent records; granted_scopes
  per User per Application.
- **`audit_log_store`** — Event model rows in PostgreSQL; default retention
  365 days; mutable in default deployments (no append-only enforcement,
  no hash chain, no WORM substrate).
- **`service_account_credential_store`** — outpost service-account tokens;
  user API tokens; app passwords; recovery / verification tokens — all
  unified via the `Token` model with an `intent` field.

## PHI / personal-data inventory

authentik is not a PHI processor by design but is a **first-class personal-data
processor** under GDPR Article 4 with substantial Article 9 (special
category) exposure when Sources release biometric / health attributes:

| Field class | Storage | GDPR class |
|---|---|---|
| Password hashes | User model in PostgreSQL | Article 4 (auth data) |
| Email, phone, name, attributes | User model JSON `attributes` | Article 4 |
| TOTP seeds, WebAuthn credentials | Authenticator devices | Article 4 (factor) |
| Federated subject identifier | Source binding | Article 4 |
| Group memberships, role assignments | Group / Role models | Article 4 (re-id risk) |
| Consent grants | UserConsent | Article 6(1)(a) basis |
| Audit content (IP, UA, AAL/FAL, source, attribute set) | Event model | Article 4 + Article 5(2) |
| Recovery email contents | Email transport (not stored long term) | Article 4 |
| Biometric_template (potentially) | FIDO2 attestation only if Source releases it | **Article 9** |

The platform does not by itself store medical, racial, religious, political,
or trade-union data — but Source attribute mappings can release such claims
when an upstream IdP carries them and the operator's property mapping does
not strip them. Specialists should flag the absence of an opinionated
deny-by-default on special-category claim release.

## Trust boundaries (from `architecture-index.md` + `tech_plan.md` §3)

1. **Internet → operator reverse proxy → Server** (TLS terminated).
2. **Federated RP → Server** (OAuth/OIDC TLS; SAML over TLS).
3. **Outpost → Server** (WebSocket; service-account token; **TLS not
   explicitly required by docs** — `INV-OPS-005` flagged as GAP).
4. **Outpost → protected app** (HTTP forward-auth headers; LDAP/LDAPS;
   RADIUS shared-secret; native RDP/SSH/VNC via Guacamole).
5. **Server → upstream Source IdP** (egress not filtered by authentik
   per `SECURITY.md`; operator network policy is the control).
6. **Server → downstream SCIM endpoint** (static-token by default;
   OAuth-token Enterprise-only).
7. **Worker → Docker / Kubernetes API** (Docker socket mount on by
   default in compose template).
8. **All processes → PostgreSQL** (TLS configurable, not default).
9. **Embedded outpost ↔ Server core** — **no process isolation**, same
   image, same process space (see threat-model E-8).

## Methodology context

The included threat model uses STRIDE per protocol surface (6 STRIDE
categories × 11+ surfaces). Tier-3 specialists should expect:

- Spoofing items map heavily to Authenticity (signing-key compromise,
  XSW, fallback HMAC-with-client_secret).
- Tampering items map to Integrity (Expression-driven mutation,
  blueprint-induced object writes, SAML XSW also lands here).
- Repudiation items map to Non-Repudiation (`ak_create_event` opt-in;
  R-2 audit-immutability in mutable PostgreSQL; cached-LDAP no-bind-event).
- Info Disclosure maps to Confidentiality (token over-disclosure,
  scope abuse, tenant boundary leak per I-8).
- DoS maps to Availability (TOTP brute-force, session-store fill,
  XML billion-laughs surface).
- EoP maps across Authenticity / Integrity / Non-Repudiation depending
  on the escalation channel.

## Evidence gaps (intake-identified)

The following are explicit GAPs in the inputs that specialist agents
should treat as load-bearing block-on-evidence candidates rather than
inferring presence or absence:

- `INV-OPS-005` — Outpost-to-Server WebSocket TLS requirement not enumerated.
  Reviewers should treat the boundary as MUST-CONFIRM.
- `INV-OPS-004` / runbook §5 — `AUTHENTIK_SECRET_KEY` rotation procedure
  not documented.
- `INV-AUTH-004` — "Removing the last MFA factor requires proof-of-possession
  of an alternate factor" not explicitly asserted in inputs.
- `INV-OUTPOST-002` — `gorm.io/driver/postgres` in `go.mod` suggests
  outpost-local PostgreSQL access for some outpost type (likely RAC);
  outpost-to-Postgres boundary unconfirmed.
- runbook §7 — outpost service-account token rotation UI control not
  enumerated; rotation procedure may require outpost recreation.
- runbook §8 — `pg_dump` encryption not documented; off-site backup
  encryption is operator-driven.
- threat-model T-1 / E-1 — Expression engine arbitrary Python is
  documented as intentional; the residual finding is whether operators
  have applied the reverse-proxy API blocklist hardening.
- threat-model I-8 — Tenancy alpha + cross-tenant Expression access is
  explicitly documented as known caveat; specialists should treat this
  as documented architectural state, not a defect.
- threat-model S-3 — HMAC-with-client_secret fallback when Provider's
  Signing Key is empty is documented; what proportion of community
  deployments rely on the fallback is unclear.
- threat-model I-1 — Whether introspection responses are scope-filtered
  the same way userinfo responses are is unclear from inputs.
- threat-model D-5 — Per-Flow execution timeout not enumerated.
- threat-model R-1 — Whether every side-effecting Expression helper
  (`ak_send_email`, `ak_create_jwt`, `ak_call_policy`) auto-emits an
  audit Event is unclear; per the function reference these helpers do
  not all auto-emit.

## Taxonomy declarations

Per `.apd-run.yaml`:

```
taxonomies: [cwe, mitre_attack, d3fend, owasp_api_top10, owasp_top10]
```

All five are in scope. Specialists should map per the discipline in
`apd-control-mappings`:

- **CWE** — base/variant only; one CWE per finding except when weakness
  composes. authentik exposes substantial OWASP Top 10 surface (web UI),
  OWASP API Top 10 surface (REST API), authentication primitives (CWE-287,
  CWE-345, CWE-347, CWE-384, CWE-613), and crypto (CWE-321 if HMAC fallback
  with leaked client_secret comes up).
- **OWASP Top 10** — web surface in scope; map to A03:2021 (Injection)
  where Expression / Blueprint user-controlled paths land, A07:2021
  (Identification/Auth Failures) for the AAL surfaces, A09:2021 (Logging)
  for audit gaps.
- **OWASP API Top 10** — REST API surface in scope; map to API2:2023
  (Broken Authentication) for service-account token gaps, API3:2023
  (Broken Object Property-Level Authorization) for mass-assignment surface,
  API4:2023 (Unrestricted Resource Consumption) for rate-limit gaps.
- **MITRE ATT&CK** — high-confidence-only.
- **D3FEND** — attached to capabilities, not findings; each entry must
  cite which ATT&CK techniques it counters.

## Specialist routing notes

- **Confidentiality** owns: encryption at rest of secret_key-protected
  fields; PHI/personal-data exposure surface; token claim minimization;
  TLS-not-default on PostgreSQL connection; the embedded outpost
  shared-process-space concern (process-boundary read of
  `AUTHENTIK_SECRET_KEY`).
- **Integrity** owns: input validation on Source attribute mappings;
  SAML XSW protection (defusedxml + xmlsec stack); mass-assignment on
  user profile (the OAuth client `client_secret` fallback and the
  `is_superuser` settable-via-Source surface); Expression-driven
  arbitrary mutation; transactional safety on Account Lockdown
  multi-step procedure (Community-tier).
- **Availability** owns: rate-limit posture per endpoint; TOTP brute-force
  rate-limit default; signing-key availability vs latency; per-Flow
  execution timeout; SLO definitions per protocol surface.
- **Distributed** owns: Postgres SPOF; multi-region story; outpost
  topology; channels-layer transport choice; session-store replication;
  embedded-outpost process-isolation.
- **Resilient** owns: outpost circuit-breakers; refresh-token reuse
  detection; graceful degradation under Source-IdP outage; bulkhead
  between user-facing auth and admin paths; chaos-engineering posture.
- **Ephemeral** owns: `AUTHENTIK_SECRET_KEY` rotation GAP; per-Provider
  signing-key rotation cadence; OAuth client-secret rotation; refresh-token
  lifetime + rotation; outpost service-account token rotation; cached LDAP
  outpost bind mode session-revocation invariant violation; Account
  Lockdown atomic-revocation availability (Community-tier).
- **Authenticity** owns: per-Provider signing key isolation; HMAC fallback
  when Signing Key absent; SAML signature verification discipline; MFA
  enforcement on admin Flows; SMS-fallback discipline; outpost-to-Server
  WebSocket TLS requirement; OAuth client-auth mechanism options
  (private_key_jwt / mTLS availability); RAC "Ignore Server certificate"
  RDP-target verification bypass.
- **Non-Repudiation** owns: audit completeness against the
  identity-security consequential-action surface; `ak_create_event`
  opt-in for side-effecting Expression helpers; cached-LDAP-bind
  no-Event problem; audit-pipeline silent-loss when log forwarding
  unconfigured; per-token audit anchor (jti for JWT, opaque ID for
  opaque); time-source posture; break-glass / Account Lockdown
  audit distinguishability.
- **Immutability** owns: Event-log mutability in PostgreSQL (no
  append-only, no hash chain, no WORM); backup immutability (object-lock
  not described); signing-key rotation-history retention; consent-record
  mutation discipline (revocation as new event vs overwrite);
  configuration-history / GitOps drift detection (Flow / Stage / Policy
  / Provider changes are admin-tier consequential).

## Specialist context preamble

Three load-bearing facts every specialist should preserve in framing:

1. **The Expression engine has NO sandbox by deliberate design.**
   Per `SECURITY.md`: "Expressions (property mappings/policies/prompts)
   can execute arbitrary Python code without safeguards." This is
   declared "Intended functionality." The IncludeSec 2025-09 audit
   classified the related finding (H3) as risk-accepted. Specialists
   should treat the Expression engine as a documented architectural
   trust-boundary choice (the boundary is permission-to-edit), NOT as
   a defect. Findings on the Expression engine should focus on second-order
   consequences — what hardening the operator must apply, what
   downstream auditability/immutability properties suffer, what
   compensating controls (the reverse-proxy API blocklist) are
   recommended but not enforced.
2. **Tenancy is alpha.** Per `sys-mgmt/tenancy.md`: "This feature is in
   alpha. Use at your own risk." and "Expression policies currently
   have access to all tenants." This is documented; the residual
   finding is whether operators are using the alpha feature in
   production despite the warning, and whether the cross-tenant
   Expression access caveat is surfaced loudly enough.
3. **`AUTHENTIK_SECRET_KEY` is the master decryption key.** Per
   ADR-0004, anyone with `secret_key + pg_dump` can unmask every
   signing key, every client_secret, every Source credential, every
   API token. The Server's process environment is the canonical
   secret_key location; anything that reads `os.environ` from the
   Server process recovers it — which transitively includes any
   Expression policy that an admin can edit. The reverse-proxy API
   blocklist for `/api/v3/policies/expression*` exists precisely to
   protect the secret_key by removing in-platform code-execution.
