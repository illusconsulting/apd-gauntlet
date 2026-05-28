# Intake Context Brief — crAPI v1.1.5

- **Run id:** `apd-20260527-crapi-owasp-api-top10`
- **Subject:** OWASP crAPI v1.1.5 — automotive B2C demonstration platform (Apache-2.0)
- **Domain pack:** `api-security` v1.0.0
- **Framework version:** 1.5.0
- **Methodology hint:** STRIDE (declared in `.apd-run.yaml`)

## 1. Artifact index

| Artifact | Type | Provenance | Reliability |
|----------|------|------------|-------------|
| `tech_plan.md` | tech_plan | architect-asserted, candid | high — explicit about intentional vulnerabilities |
| `architecture-index.md` | architecture_doc | service-by-service catalog | high |
| `threat-model.md` | threat_model | STRIDE per surface; mapped to crAPI challenges | high — frontmatter `methodology: stride` |
| `happy-path.md` | design_doc | intended user workflows | high |
| `runbook.md` | runbook | operator-facing; honest about GAPs | high for what is documented; absence-by-design for GAP markers |
| `prior-audit.md` | audit_doc | carry-forward of OWASP-published vulnerability catalog | high — canonical |
| `agents.md` | operator_context | scopes the operator role (single-developer demo, no enterprise operator) | high |
| `invariants.md` | invariant_assertions | architect's intended invariants paired with reviewer notes | high |
| `adrs/0001-microservice-split-by-language.md` | adr | language split for pedagogical breadth | high |
| `adrs/0002-jwt-with-rsa-and-jwks.md` | adr | RS256 JWT + JWKS; documents the multi-algo confusion surface | high |
| `adrs/0003-mailhog-for-otp-delivery.md` | adr | dev-grade SMTP catcher | high |
| `adrs/0004-dual-datastore-postgres-and-mongo.md` | adr | dual datastores with shared admin credential | high |

No code-evidence index (`code_recon: disabled` per run-config — crAPI source at `/tmp/crAPI` is not indexed in any CBM project).

## 2. Capability and surface summary

crAPI is a single-tenant API platform composed of:

- **Public ingress:** OpenResty (Nginx + LuaJIT) on `:8888` (HTTP; `:8443` if `TLS_ENABLED=true`). No WAF, no rate-limiter, no auth at the edge. Backend services trust `Host`/`X-Forwarded-*` headers presented by the web tier.
- **Identity tier:** Spring Boot (Java) `crapi-identity:8080` — JWT mint/verify, JWKS endpoint, OTP issuance, vehicle CRUD, profile videos, password reset, admin video delete (BFLA), outbound to gateway.
- **Workshop tier:** Django (Python) `crapi-workshop:8000` — orders, coupons, mechanic flows, contact-mechanic webhook (SSRF surface), admin-shaped enumeration endpoints.
- **Community tier:** Go `crapi-community:8087` — blog posts/comments, coupon `validate-coupon` (NoSQL injection surface), recent-posts feed that leaks `vehicleid`.
- **Chatbot tier:** Python (LangChain-style) `crapi-chatbot` — RAG over OpenAPI spec via ChromaDB, pluggable LLM providers (OpenAI/Anthropic/Bedrock/Vertex/Groq/Mistral/Cohere/Azure), MCP server on `:5500`; holds `API_USER=admin@example.com / API_PASSWORD=Admin!123` (crAPI admin credential).
- **Mailhog:** Go `mailhog:1025` SMTP catcher + `:8025` web UI (no auth on UI).
- **Datastores:** `postgres:14` (`crapi`/`admin`/`crapisecretpassword`), `mongo:4.4` (same creds), `chromadb` (no auth in default compose).
- **Simulated partner API:** `api.mypremiumdealership.com` — Go gateway, basic-auth-protected, returns deterministically faked PII/payment data seeded from `fnv32a(VIN)`.

### API surface count

41 OpenAPI-spec endpoints + chatbot endpoints (`/genai/init`, `/genai/chat`) + auxiliary (`/.well-known/jwks.json`, per-service health checks). OWASP API Top 10 categories present by design (API1, API2, API3, API4, API5, API6, API7, API8, API9, API10).

## 3. Data inventory (PII / PCI / authentication factors)

### Personal data (GDPR Article 4(1))

| Field | Location | Producing surface | Consuming surface |
|-------|----------|-------------------|-------------------|
| `email` | postgres `users.email` (primary natural key) | signup, login, password-reset, dashboard | identity, workshop (token claim), mailhog (OTP delivery) |
| `name` | postgres `users.name`; gateway-service response | signup, dashboard, vehicle location response | identity, workshop, community (post display) |
| `phone` | postgres `users.phone`; gateway-service response | signup, dashboard | identity |
| `vehicleId` (UUID) | postgres `vehicles.id`; mongo `posts.vehicleid` | vehicle add, community recent-posts (LEAK vector for BOLA #1) | identity, community |
| `VIN` | postgres `vehicles.vin`; gateway-service input | vehicle add | identity → gateway-service |
| `vehicle_locations.latitude/longitude` | postgres | vehicle location endpoint | identity (returns to caller per BOLA #1) |
| `ssn` | gateway-service response (faker-seeded from VIN) | gateway-service `GetOwners` | identity (returned to caller depending on path) |
| `address` | gateway-service response | gateway-service `GetOwners` | identity |
| `mechanic_report.body` | postgres `mechanic_reports.text` (sequential integer ID) | mechanic flow | workshop |
| `profile_videos.conversion_params` | postgres `profile_videos` (internal field) | video CRUD | identity (leaks per EDE #5) |
| `posts.author/title/body` | mongo `posts` | community | community |
| `chatbot.history` | mongo (chatbot session) | chatbot | chatbot |

### Cardholder data (PCI-DSS scope)

| Field | Location | Notes |
|-------|----------|-------|
| `card_number` | gateway-service response (faker-seeded from VIN) | Deterministic but representative of real PAN handling; in PCI scope as modeled |
| `card_owner_name` | gateway-service response | |
| `card_expiry` | gateway-service response | |
| `cvv` | not modeled in inputs | — |

### Authentication factors

| Field | Location | Notes |
|-------|----------|-------|
| `password` | postgres `users.password` | Storage scheme **unspecified** — gap |
| `OTP` (4-digit numeric) | identity ephemeral; mailhog delivery | `v3/check-otp` unthrottled |
| JWT (RS256 minted by identity) | `Authorization: Bearer ...`; 7-day TTL (`JWT_EXPIRATION=604800000`) | No refresh-rotation, no revocation |
| `JWT_SECRET=crapi` env | identity container | HS256 confusion surface |
| `services/identity/jwks.json` | repo-tracked file | Ships **private-key components** by default |
| `API_PASSWORD=Admin!123` (chatbot embedded) | chatbot container env | crAPI admin credential |
| Postgres/Mongo `admin / crapisecretpassword` | compose env | Plaintext |
| `AWS_ACCESS_KEY_ID`, `AZURE_OPENAI_API_KEY`, `GROQ_API_KEY`, etc. | chatbot container env | Long-lived LLM provider credentials |
| Gateway-service basic-auth credential | hard-coded in identity binary (per S-5) | Undocumented |

### Special category personal data (GDPR Article 9)

Not modeled (no health/biometric/genetic fields).

## 4. Trust boundaries

1. **Public internet → web ingress** (`:8888`). No WAF/rate-limit/auth at the boundary. All path prefixes proxied by Nginx prefix-match.
2. **web → backend services** (in-cluster). Plaintext HTTP by default. No mTLS. Header-trust posture (Host, X-Forwarded-*).
3. **identity ↔ peers** — all other services verify bearer JWTs against identity's JWKS endpoint. Compromise of identity = cluster-wide auth bypass.
4. **identity → mailhog** — plaintext SMTP `:1025`.
5. **identity → gateway-service** — outbound HTTPS basic-auth (cross-organization boundary in the threat model; co-located in lab).
6. **chatbot → ChromaDB + external LLM provider** — internal HTTP + external HTTPS; chatbot holds admin credential and acts on user behalf.
7. **All services → datastores** — single shared `admin` credential, plaintext.

## 5. Evidence gaps (block-on-evidence candidates)

These are properties on which the inputs are silent. Specialists encountering them should emit `disposition: blocked` with the listed prerequisite. The intake brief surfaces them once so specialists do not each re-discover them.

- **Password hashing scheme** — `users.password` storage is unspecified. (Confidentiality, Authenticity.)
- **TLS configuration policy when `TLS_ENABLED=true`** — version floor, cipher suite, certificate validation behavior, mTLS topology. (Confidentiality.)
- **JWT verifier configuration per service** — algorithm-pinning policy, `jku` allowlist, `kid` allowlist, audience-pin (`aud`). (Authenticity, Integrity.)
- **Audit log schema, retention, and pipeline** — no audit log exists; only `LOG_LEVEL=INFO` stdout. (Non-Repudiation, Immutability.)
- **Audit shipping and aggregator** — operator-provided per runbook §8. (Non-Repudiation.)
- **Backup / restore procedure** — none shipped. (Availability, Immutability.)
- **SLO/SLI commitments** — none. crAPI is a demo; per `agents.md` no enterprise operator. (Availability.)
- **Multi-AZ / multi-region topology** — single-host by intent; per `agents.md`. (Distributed.)
- **Network policy for in-cluster service-to-service reach** — not in shipped Helm values. (Distributed, Authenticity.)
- **Datastore per-service credential separation** — single shared admin. (Confidentiality, Authenticity.)
- **Encryption-at-rest on Postgres, Mongo, ChromaDB** — not configured. (Confidentiality.)
- **Key rotation procedures (JWT, JWT_SECRET, datastore creds, gateway-service basic-auth, chatbot embedded)** — none documented. (Ephemeral.)
- **Session lifetime policy beyond 7-day JWT** — no idle timeout, no logout, no password-change-revokes-sessions semantics. (Ephemeral.)
- **Refresh-token rotation / reuse-detection** — no refresh tokens. (Ephemeral, Resilient.)
- **Rate-limit policy on most endpoints** — only `v2/check-otp` is rate-limited per challenge 3 discussion. (Availability.)
- **Outbound timeout / circuit-breaker discipline on identity → gateway-service, workshop → contact_mechanic, chatbot → LLM** — not specified. (Resilient.)
- **Chatbot tool-call allowlist** — per T-5 / E-4 not specified. (Authenticity, Integrity.)
- **Image-signing / admission control** — not mentioned. (Authenticity, Immutability.)
- **CORS policy on the web ingress** — not specified. (Confidentiality.)
- **`unit_price` server-derivation policy** — per T-4 not confirmed. (Integrity.)
- **OTP TTL precision and re-issuance rate-limit** — implied ~10 minutes but not asserted. (Ephemeral, Authenticity.)

## 6. Taxonomy suggestions (run-config declared)

Active taxonomies per `.apd-run.yaml`:

- `cwe` — applicable broadly to most findings.
- `mitre_attack` — high-confidence only per discipline.
- `d3fend` — on capabilities, cross-linked to ATT&CK.
- `owasp_api_top10` — primary categorical anchor; crAPI is purpose-built around this taxonomy.
- `owasp_top10` — secondary; web-surface findings on the SPA / ingress may map (e.g., A05 Security Misconfiguration on Mailhog UI exposure).

No additional auto-suggestions; OWASP LLM Top 10 would be applicable (chatbot is an LLM-integrated surface), but it is not declared in the run-config so specialists must not emit `llm_<NN>` mappings.

## 7. Relevance hints per artifact

| Artifact | Primary lenses | Secondary lenses |
|----------|---------------|-------------------|
| `tech_plan.md` | All 9 goals — architectural baseline | — |
| `architecture-index.md` | Distributed, Authenticity, Confidentiality | Resilient, Integrity |
| `threat-model.md` | All 9 goals — STRIDE coverage | — |
| `happy-path.md` | Integrity (write-path semantics), Confidentiality (intended data flow) | Authenticity (intended identity claims) |
| `runbook.md` | Ephemeral (rotation GAPs), Non-Repudiation (audit GAPs), Resilient (degraded-mode GAPs) | Availability, Immutability |
| `prior-audit.md` | All 9 — accepted starting state | — |
| `agents.md` | Availability (no SLO), Resilient (no on-call), Distributed (single-host intent) | Ephemeral (no rotation expected) |
| `invariants.md` | Integrity (input invariants), Authenticity (auth invariants), Authorization-touching goals | All 9 — invariant violations are findings |
| `adrs/0001` | Distributed (language split), Integrity (per-language verifier heterogeneity), Authenticity (no shared verifier module) | — |
| `adrs/0002` | Authenticity (JWT mint/verify), Integrity (algorithm-pinning) | Confidentiality (JWKS posture), Ephemeral (rotation absent) |
| `adrs/0003` | Confidentiality (Mailhog UI access), Authenticity (OTP delivery posture), Ephemeral (OTP TTL) | Non-Repudiation (OTP dispatch audit gap) |
| `adrs/0004` | Confidentiality (dual-store encryption posture), Authenticity (shared admin), Integrity (cross-store consistency), Immutability (audit pipeline gap) | Availability, Ephemeral (credential rotation) |

## 8. Notable cross-cutting facts

- **No PHI scope.** crAPI does not handle health data; the API-security domain pack applies, not the PBM pack.
- **PCI scope is modeled, not real.** The gateway-service produces `card_number`/`card_owner_name`/`card_expiry`; this is faker-seeded but architecturally indistinguishable from a real partner integration — findings on the gateway-service path should treat it as in-PCI-scope.
- **Single-tenant by design.** No multi-tenant isolation work expected. Cross-tenant findings reduce to cross-user findings.
- **Operator is "deploy-and-explore", not "administer-and-defend"** per `agents.md`. Specialists should not write findings that demand production operator behavior; they should write findings against the artifact (structural) rather than the operator (procedural).
- **18 publicly-documented vulnerabilities + 3 secret challenges** are in scope by design per `prior-audit.md`. Specialists must produce findings against the **operational consequences** of these (impact to trustworthiness/scalability/auditability) rather than re-discovering the underlying issue.
- **OWASP LLM Top 10 surfaces** (chatbot prompt-injection per challenges 16/17/18) — not in the active taxonomy set; specialists should still discuss the architectural concerns (admin credential embedding, unbounded tool surface) without emitting `llm_<NN>` mappings.

## 9. Asset graph signal (for Phase 5.6 attack-path analyzer)

The `api-security` domain pack declares 8 crown_jewels and 9 attacker_positions; these flow into Phase 5.6 automatically. The intake brief enumerates per-asset locator data above to support graph construction. A machine-readable rollup is at `00-context/asset-inventory.yaml`.
