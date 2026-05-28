# Architecture Index — crAPI

Service-by-service index for the crAPI deployment. Each row is one
container in the canonical `deploy/docker/docker-compose.yml`. Use this
as the lookup table when correlating findings to surfaces; the trust
boundary notes follow the §3 inventory in `tech_plan.md`.

## Service index

### `crapi-web`

- **Language / runtime:** JavaScript SPA + **OpenResty** (Nginx core
  + LuaJIT) as the reverse-proxy front door.
- **Image:** `crapi/crapi-web:${VERSION}`.
- **Role:** Public ingress on port `:8888` (HTTP) or `:8443` when
  `TLS_ENABLED=true`. Serves the SPA bundle; routes
  `/identity/*`, `/workshop/*`, `/community/*`, `/chatbot/*`,
  `/.well-known/jwks.json`, and `/openapi-spec/*` to the
  corresponding backend services by Nginx prefix-match.
- **Inbound:** End-user browser, attacker tooling, anything that can
  reach the host. No WAF, no auth, no rate-limiter.
- **Outbound:** `crapi-identity:8080`, `crapi-workshop:8000`,
  `crapi-community:8087`, `crapi-chatbot:5002`.
- **Datastores touched:** None directly.
- **Trust boundary:** Public-internet ↔ internal-service-mesh hop.
  Backend services trust the `Host` and `X-Forwarded-*` headers
  presented here.
- **Notable surface:** Nginx config templates under `services/web/`
  (`nginx.conf.template`, `nginx.ssl.conf.template`); a `package.json`
  for the SPA build; `certs/` for development TLS material.

### `crapi-identity`

- **Language / runtime:** Java (Spring Boot, Gradle-built).
- **Image:** `crapi/crapi-identity:${VERSION}`.
- **Role:** Authentication, JWT minting (RS256), JWKS publication,
  OTP issuance, password reset, vehicle CRUD, vehicle location,
  profile-video CRUD, and an admin video endpoint. Bridges to the
  external dealership API (`api.mypremiumdealership.com`) for VIN
  owner lookup and payment.
- **Inbound:** Through `crapi-web` only in default deploy. Listens on
  `:8080` (override: `IDENTITY_SERVER_PORT`).
- **Outbound:** `postgresdb:5432`, `mongodb:27017`, `mailhog:1025`
  (SMTP), `https://api.mypremiumdealership.com` (gateway-service),
  outbound LLM providers (none — chatbot does that).
- **Datastores touched:** Postgres (users, vehicles, profile videos),
  Mongo (community joins only in some flows).
- **Trust boundary:** All other services treat identity as the JWT
  authority. Compromise of identity → cluster-wide auth bypass.
- **Notable surface:** Static JWKS shipped at
  `services/identity/jwks.json` includes **private-key components**
  by default. `JWT_SECRET=crapi` env coexists with RS256 keys
  (algorithm-confusion surface; see ADR-0002). Health probe:
  `GET /identity/health_check`. `ENABLE_LOG4J` and the historical
  log4shell-style switch are wired here.

### `crapi-workshop`

- **Language / runtime:** Python (Django).
- **Image:** `crapi/crapi-workshop:${VERSION}`.
- **Role:** Mechanic registration and lookup, service requests,
  contact-mechanic webhook (SSRF surface), shop products and orders,
  return / QR-code flows, coupon application, admin order
  enumeration (`/management/users/all`, `/shop/orders/all`).
- **Inbound:** Through `crapi-web` only in default deploy. Listens on
  `:8000` (override: `WORKSHOP_SERVER_PORT`).
- **Outbound:** `postgresdb:5432`, `crapi-identity:8080` (JWT
  validation), arbitrary HTTP — `merchant/contact_mechanic` accepts a
  webhook URL and fetches it server-side.
- **Datastores touched:** Postgres (mechanics, service_requests,
  mechanic_reports, products, orders, credit, coupons).
- **Trust boundary:** Outbound HTTP from `contact_mechanic` crosses
  into arbitrary external destinations including the cluster
  loopback, metadata services, and the public internet. No allowlist.
- **Notable surface:** Health probe: `GET /workshop/health_check/`.
  OpenAPI passthrough: `GET /workshop/openapi-spec/`.

### `crapi-community`

- **Language / runtime:** Go.
- **Image:** `crapi/crapi-community:${VERSION}`.
- **Role:** Blog posts, post comments, recent-posts feed (leaks
  `vehicleid` of authors — BOLA pivot), coupon `new-coupon` /
  `validate-coupon` (NoSQL injection surface). Authenticates by
  calling identity's JWKS-backed verifier.
- **Inbound:** Through `crapi-web` only in default deploy. Listens on
  `:8087` (override: `COMMUNITY_SERVER_PORT`).
- **Outbound:** `postgresdb:5432`, `mongodb:27017`,
  `crapi-identity:8080`.
- **Datastores touched:** Postgres (coupons table), Mongo (posts,
  comments, coupon_documents).
- **Trust boundary:** Dual-datastore access in one service (see
  ADR-0004 for the consequences); the JSON request body for
  `validate-coupon` is forwarded into a Mongo query selector.
- **Notable surface:** Health probe: `GET /community/home`.

### `crapi-chatbot`

- **Language / runtime:** Python (LangChain-style RAG).
- **Image:** `crapi/crapi-chatbot:${VERSION}`.
- **Role:** Embeddings over the OpenAPI spec, chat completion against
  pluggable LLM providers (`openai`, `anthropic`, `azure_openai`,
  `bedrock`, `vertex`, `groq`, `mistral`, `cohere`). Exposes an MCP
  server on `:5500`. Holds `API_USER=admin@example.com /
  API_PASSWORD=Admin!123` — a privileged crAPI credential used to act
  on behalf of users when handling chatbot actions.
- **Inbound:** Through `crapi-web` for `/chatbot/*`; MCP port mapped
  externally to `127.0.0.1:5500` by default.
- **Outbound:** ChromaDB (`chromadb:8000`), Postgres, Mongo,
  `crapi-identity:8080` (admin actions), plus the configured LLM
  provider over the public internet.
- **Datastores touched:** ChromaDB (embeddings), Postgres + Mongo for
  user/action context.
- **Trust boundary:** Holds an admin credential; LLM input is
  user-controlled; **prompt-injection allows the chatbot to perform
  actions as that admin** against other services (challenges 16–18).
- **Notable surface:** Provider-specific env vars carry long-lived
  cloud credentials (`AWS_ACCESS_KEY_ID`, `AZURE_OPENAI_API_KEY`,
  `GROQ_API_KEY`, etc.). OpenAI/Anthropic accept per-session keys via
  `POST /genai/init`.

### `mailhog`

- **Language / runtime:** Go (vendored upstream Mailhog).
- **Image:** `crapi/mailhog:${VERSION}`.
- **Role:** SMTP catcher for OTP and notification delivery in
  development. SMTP on `:1025`; web UI on `:8025` (the only
  non-`crapi-web` port exposed to `LISTEN_IP` by default).
- **Inbound:** Identity service via SMTP; operator browser via the
  web UI (no auth on the UI).
- **Outbound:** None (catcher only).
- **Datastores touched:** In-memory ring buffer.
- **Trust boundary:** Operator-only consumption; any user reachable
  on `:8025` can read every OTP and password-reset email sent to the
  `example.com` domain.
- **Notable surface:** No production-grade SMTP path is configured
  by default; `SMTP_HOST=smtp.example.com / SMTP_PASS=xxxxxxxxxxxxxx`
  are placeholders.

### `postgresdb`

- **Image:** `postgres:14`.
- **Role:** Primary OLTP store. Database `crapi`, user `admin`,
  password `crapisecretpassword`.
- **Inbound:** identity, workshop, community, chatbot.
- **Outbound:** None.
- **Datastores touched:** Self.
- **Trust boundary:** Plaintext credentials in compose; no
  encryption-at-rest configured; no row-level security; no per-service
  user separation.
- **Notable surface:** Volume mount in the persistent-Helm variant;
  no backup/restore tooling shipped.

### `mongodb`

- **Image:** `mongo:4.4`.
- **Role:** Document store for community blog posts, comments, coupon
  metadata, and chatbot session state. Same credentials shape as
  Postgres.
- **Inbound:** community, chatbot.
- **Outbound:** None.
- **Trust boundary:** Same as Postgres — plaintext creds in compose,
  legacy auth defaults for 4.4, no per-service users.

### `chromadb`

- **Image:** `chromadb/chroma:latest`.
- **Role:** Vector store for the chatbot's RAG retrieval over the
  OpenAPI spec.
- **Inbound:** chatbot.
- **Outbound:** None.
- **Trust boundary:** No authentication in the default compose;
  inside the cluster network only.

### `api.mypremiumdealership.com` (gateway-service)

- **Language / runtime:** Go.
- **Image:** `crapi/gateway-service:${VERSION}`.
- **Role:** **Simulated external partner API.** Modeled as a
  third-party dealership: VIN owner lookup (`GetOwners`) and payment
  dispatch. Uses HTTP basic-auth. Returns deterministically faked PII
  (`name`, `phone`, `ssn`, `address`, `card_number`,
  `card_owner_name`, `card_expiry`) seeded from `fnv32a(VIN)`.
- **Inbound:** crapi-identity (configured via
  `API_GATEWAY_URL=https://api.mypremiumdealership.com`).
- **Outbound:** None.
- **Trust boundary:** Models a cross-organisation boundary in the
  threat model; in the lab is co-located in the same compose network
  with a self-signed certificate (`server.crt`, `server.key` shipped
  in the repo).
- **Notable surface:** Deterministic VIN-to-PII mapping means
  enumeration via any leaked VIN list yields stable identity records.
