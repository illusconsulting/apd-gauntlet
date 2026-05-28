# crAPI — Technical Plan

OWASP **crAPI** (completely ridiculous API) is a self-hosted, intentionally
vulnerable car-servicing B2C web application. It exists to demonstrate
and let practitioners exercise the OWASP API Security Top 10. This
document is the architect-facing description of what crAPI is, how the
pieces are deployed, where the trust boundaries fall, and — because the
project's purpose is to model vulnerable APIs — what attack surface is
known to be in scope by design. Version under review: **1.1.5** (per
`/VERSION`). License: **Apache-2.0**.

## 1. System purpose

crAPI is a single-tenant lab/learning target modeling an automotive
business-to-consumer service. The conceptual workflows it supports are:

- **Car owner** signs up, verifies their email via an OTP delivered to a
  development SMTP catcher (Mailhog), then adds one or more **vehicles**
  by VIN + pincode.
- The owner can request **mechanic service** for a vehicle, populating a
  service request and a downstream "mechanic report".
- The owner can shop a small **marketplace** for car accessories, place
  **orders**, return items, and apply **coupons** to reduce a stored
  balance.
- The owner can post **blog entries** and **comments** in a community
  area.
- The owner can upload **profile videos** with metadata; an admin role
  exists for video management.
- A **chatbot** assistant is available against an embedded vector store,
  with pluggable LLM backends (OpenAI, Anthropic, Bedrock, Vertex,
  Groq, Mistral, Cohere, Azure OpenAI).

crAPI is explicitly *not* aiming to be a faithful e-commerce platform.
The README and `docs/overview.md` are clear: the project is designed to
run on a single t2.micro-class host and is structured to expose the
OWASP API Top 10 categories for practice.

## 2. Architecture

crAPI is structured as a small microservice constellation — eight
containers (or nine, depending on chatbot configuration) coordinated by
Docker Compose, Helm, or Vagrant. The services are heterogeneous in
language by design (Java, Python, Go, JavaScript, plus the
LangChain-style Python chatbot) so practitioners can study attack
patterns across runtime ecosystems.

### Services

| Service        | Language     | Container               | Role                                                                |
|----------------|--------------|-------------------------|---------------------------------------------------------------------|
| web            | JS/OpenResty | `crapi-web`             | Public ingress; reverse-proxies to backend services on a shared host port (`8888`) |
| identity       | Java (Spring)| `crapi-identity`        | Account creation, login, JWT mint + verify, JWKS, OTP, vehicle CRUD, profile videos, password reset |
| workshop       | Python (Django) | `crapi-workshop`     | Mechanic, service request, shop / orders, coupons, contact-mechanic webhook |
| community      | Go           | `crapi-community`       | Blog posts, comments, recent-posts feed; coupon `new-coupon` / `validate-coupon` endpoints |
| chatbot        | Python       | `crapi-chatbot`         | RAG chatbot over the OpenAPI spec via ChromaDB; pluggable LLM backends; MCP server on `:5500` |
| mailhog        | Go           | `mailhog`               | SMTP catcher for OTP and notification delivery (dev-grade) |
| postgresdb     | -            | `postgresdb` (postgres:14) | Primary OLTP store: identity, vehicles, orders, mechanics |
| mongodb        | -            | `mongodb` (mongo:4.4)   | Document store for community blogs, comments, coupon metadata |
| chromadb       | -            | `chromadb` (chromadb/chroma:latest) | Vector store backing the chatbot's retrieval layer |
| gateway-service| Go           | `api.mypremiumdealership.com` | Simulated **external** API for vehicle-owner lookup and payment processing. Basic-auth protected; returns deterministically-faked PII (name, SSN, address, card numbers) seeded from a VIN hash. Modeled as a third-party dealership API the identity service contacts outbound. |

The `crapi-web` container fronts everything on `:8888` (HTTP) using
**OpenResty** (Nginx + LuaJIT). Backend services are not directly
exposed to `LISTEN_IP` in the default compose — only the web ingress
and Mailhog (`:8025`) are. In Kubernetes (`deploy/helm/`) the same
shape holds, with services exposed via a single LoadBalancer.

### Deployment topologies supported

- **Docker Compose** — `deploy/docker/docker-compose.yml`, supports
  `--compatibility` mode; per-service `healthcheck:` blocks invoke
  per-service `health.sh`.
- **Helm chart** — `deploy/helm/`, `values.yaml` and
  `values-pv.yaml` (persistent-volume variant).
- **Kubernetes manifests** — `deploy/k8s/`.
- **Vagrant + VirtualBox** — `deploy/vagrant/`, exposed on
  `192.168.33.20:80` and `:8025`.

Optional flags: `LISTEN_IP=0.0.0.0` to expose the stack on all
interfaces, `TLS_ENABLED=true` to switch services into HTTPS-backed
mode using PKCS12 keystores shipped under each service's `certs/`
directory.

## 3. Trust boundaries

```
+-------------+    +--------+    +-------------+    +-----------+
| Public      | -> |  web   | -> | identity    | -> | postgres  |
| internet    |    | (8888) |    | workshop    |    | mongo     |
| (operator/  |    |        |    | community   |    | chromadb  |
| attacker)   |    +--------+    | chatbot     |    +-----------+
+-------------+                  +-------------+
                                       |
                                       v
                                  +-----------+    +--------------+
                                  | mailhog   |    | gateway-svc  |
                                  | (smtp/web)|    | (mypremium-  |
                                  +-----------+    | dealership)  |
                                                   +--------------+
```

Boundary inventory:

1. **Public internet → web ingress.** Single shared host port `8888`.
   No WAF, no rate limiter, no auth. All path prefixes (`/identity/`,
   `/workshop/`, `/community/`, `/chatbot/`, `/.well-known/jwks.json`)
   land here and are proxied based on Nginx prefix-matching rules in
   `nginx.conf.template`.
2. **web → backend services.** Plain HTTP inside the Compose network
   unless `TLS_ENABLED=true`. No mutual TLS. Backend services trust the
   `Host` and `X-Forwarded-*` headers as the web tier presents them.
3. **identity ↔ peers.** Other services consume `IDENTITY_SERVICE=crapi-identity:8080`
   to validate bearer JWTs against the JWKS endpoint
   `http://crapi-identity:8080/.well-known/jwks.json` (also republished
   externally at `http://localhost:8888/.well-known/jwks.json`).
4. **identity → mailhog.** Plaintext SMTP on `mailhog:1025` for the
   email-validation domain `example.com`. Production SMTP credentials
   (`SMTP_HOST=smtp.example.com`, `SMTP_PASS=xxxxxxxxxxxxxx`,
   `SMTP_FROM=no-reply@example.com`) are placeholder values; outside
   the `example.com` test domain there is no functional mail path.
5. **identity → gateway-service.** Outbound HTTPS to
   `https://api.mypremiumdealership.com` (basic-auth) for VIN owner
   lookup and payment dispatch.
6. **chatbot → ChromaDB and LLM provider.** ChromaDB is in-cluster on
   `:8000`. LLM providers are external; credentials are passed via
   environment, except OpenAI/Anthropic which also accept a per-session
   key via `POST /genai/init`.
7. **All services → datastores.** Postgres (`postgresdb:5432`,
   `admin/crapisecretpassword`) and MongoDB (`mongodb:27017`,
   `admin/crapisecretpassword`) credentials are hardcoded in the
   compose file. No row-level security, no schema-level GRANTs beyond
   default.

## 4. Authentication and sessions

The identity service mints and verifies JWTs. The default algorithm is
**RS256** with a single signing key whose JWKS is published at
`/.well-known/jwks.json`. crAPI ships a **default `jwks.json` containing
the private key components** (`d`, `p`, `q`, `dp`, `dq`, `qi`) checked
into the repo at `services/identity/jwks.json`; operators are advised
in `docs/setup.md` to drop a replacement `jwks.json` into the
`deploy/<topology>/keys` directory. **No rotation tooling is provided.**

Concurrently, the identity container also sets `JWT_SECRET=crapi` in
its environment. That symmetric secret is the basis of multiple JWT
challenges in `docs/challenges.md` (challenge 15): the documented
attacks include RS256→HS256 algorithm confusion using the public JWK as
the HMAC key, `alg:none` acceptance on some endpoints, `jku` header
abuse pointing at attacker-controlled JWK sets, and `kid` path
traversal pointing at filesystem byte sources.

Authentication endpoints (paths drawn from the OpenAPI spec at
`openapi-spec/crapi-openapi-spec.json`):

| Endpoint                                                | Notes |
|---------------------------------------------------------|-------|
| `POST /identity/api/auth/signup`                        | Email + name + phone + password; no rate-limit annotation |
| `POST /identity/api/auth/login`                         | Returns bearer JWT |
| `POST /identity/api/auth/forget-password`               | OTP email dispatch (per `docs/challenges.md` #3, this path is rate-limited but neighboring `/v3/check-otp` variants are not) |
| `POST /identity/api/auth/v2/check-otp`                  | 4-digit OTP verification (vulnerable per challenge 3) |
| `POST /identity/api/auth/v3/check-otp`                  | A successor endpoint; per challenge 3 solution discussion, rate-limiting on `v2` was added but `v3` and other variants remain bypassable |
| `POST /identity/api/auth/v4.0/user/login-with-token`    | Token-based re-login |
| `POST /identity/api/auth/v2.7/user/login-with-token`    | Older variant |
| `POST /identity/api/v2/user/reset-password`             | Auth required |
| `POST /identity/api/v2/user/change-email`               | Auth required |
| `POST /identity/api/v2/user/verify-email-token`         | Email verification token |

The session token (a JWT) is included as `Authorization: Bearer <token>`
per the OpenAPI `bearerAuth` security scheme. No refresh-token rotation
is specified. Expiration defaults to `JWT_EXPIRATION=604800000`
milliseconds (7 days).

There is no MFA. There is no documented session-revocation surface
(no /logout endpoint in the OpenAPI spec).

## 5. Data model

Per-service ownership of records:

- **identity / postgres**
  - `users` — email (primary natural key), name, phone, password
    (storage scheme unspecified in inputs), role
  - `vehicles` — owner FK, **UUID `vehicleId`** (per challenge 1, IDs
    are GUIDs but they leak via the community recent-posts endpoint),
    VIN, model, year, last-known latitude/longitude
  - `vehicle_locations` — `latitude`, `longitude`, captured by the
    `/vehicle/{vehicleId}/location` endpoint
  - `profile_videos` — bound to a user; carries a hidden
    `conversion_params` internal property (per challenge 5) and is
    deletable through an admin endpoint (per challenge 7)
- **workshop / postgres**
  - `mechanics` — username, email, branch
  - `service_requests` — owner FK, vehicle FK, mechanic FK, status
  - `mechanic_reports` — sequential integer `report_id` (per challenge
    2 solution: enumerable), report text, related service request
  - `products`, `orders` — order has owner, product, quantity (no
    server-side non-negative check per challenge 8/9), unit price
    (client-supplied per challenge 9), total
  - `credit` — per-user stored balance, initialized to $100, decremented
    by orders; can be increased by submitting negative quantity (mass
    assignment; challenges 8/9)
- **community / postgres + mongo**
  - `coupons` (postgres) — code, claimed_by FK; redemption tracked via
    a separate flag that the challenge 13 SQL-injection path can update
  - `coupon_documents` (mongo) — coupon metadata fetched via the
    `validate-coupon` flow vulnerable to NoSQL injection (challenge 12)
  - `posts` (mongo) — author display name, title, body, attached
    `vehicleid` field (which is the leak vector for challenge 1)
  - `comments` (mongo) — author, body, post FK
- **chatbot / mongo + chromadb**
  - chat history (mongo) — keyed by user
  - retrieval index (chromadb) — embeddings derived from the OpenAPI
    spec at boot

## 6. Persistence and storage

- **PostgreSQL 14** (`postgresdb`). Single database `crapi`,
  user/password `admin / crapisecretpassword` (hardcoded in
  `deploy/docker/docker-compose.yml`). No encryption-at-rest
  configuration is shipped; volume is host-mounted in the persistent
  Helm variant. No row-level security is configured.
- **MongoDB 4.4** (`mongodb`). Same fixed credentials
  (`admin / crapisecretpassword`). Auth method is the legacy
  `SCRAM-SHA-1` default for 4.4 unless overridden. No
  encryption-at-rest.
- **ChromaDB** (`chromadb/chroma:latest`). Stateful service; not
  authenticated in the default compose.
- Backups: **unspecified**. No backup, restore, or PITR procedure ships
  in `docs/setup.md` or `docs/troubleshooting.md`.

## 7. Email subsystem

OTP delivery and notification email is routed to **Mailhog** at
`mailhog:1025` (SMTP) and exposed via web UI on `:8025`. The
`MAILHOG_DOMAIN=example.com` env trap means any address at
`example.com` is silently delivered to Mailhog regardless of
`SMTP_HOST` overrides. Production-grade SMTP delivery is **not
configured** — the env vars `SMTP_HOST=smtp.example.com`,
`SMTP_PASS=xxxxxxxxxxxxxx` are placeholder. Operators wanting real
email delivery for non-`example.com` recipients must override at
deploy time; the documentation does not describe an authoritative
production setup.

OTP format: **4-digit numeric** (per the documented brute-force in
challenge 3). TTL: per challenge 3 solution discussion, the OTP
expiry is short (~10 minutes) but the per-OTP attempt count on the
`v3` variant is unbounded.

## 8. API surfaces

Drawn from `openapi-spec/crapi-openapi-spec.json` (paths summarised;
verbs and exact request shapes available in the spec). 41 endpoints.

### Identity surface

```
POST /identity/api/auth/signup
POST /identity/api/auth/login
POST /identity/api/auth/forget-password
POST /identity/api/auth/v3/check-otp
POST /identity/api/auth/v2/check-otp
POST /identity/api/auth/v4.0/user/login-with-token
POST /identity/api/auth/v2.7/user/login-with-token
POST /identity/api/v2/user/reset-password
POST /identity/api/v2/user/change-email
POST /identity/api/v2/user/verify-email-token
GET  /identity/api/v2/user/dashboard
POST /identity/api/v2/user/pictures
GET  /identity/api/v2/user/videos
GET  /identity/api/v2/user/videos/{video_id}
POST /identity/api/v2/user/videos/{video_id}
POST /identity/api/v2/user/videos/convert_video
DEL  /identity/api/v2/admin/videos/{video_id}     <-- admin role required
GET  /identity/api/v2/vehicle/vehicles
POST /identity/api/v2/vehicle/add_vehicle
GET  /identity/api/v2/vehicle/{vehicleId}/location
POST /identity/api/v2/vehicle/resend_email
```

### Workshop surface

```
GET  /workshop/api/shop/products
GET  /workshop/api/shop/orders
POST /workshop/api/shop/orders
GET  /workshop/api/shop/orders/{order_id}
PUT  /workshop/api/shop/orders/{order_id}            <-- shadow update; mass-assignment surface (challenge 8/9)
GET  /workshop/api/shop/orders/all                   <-- admin-shaped enumeration
POST /workshop/api/shop/orders/return_order
POST /workshop/api/shop/apply_coupon
GET  /workshop/api/shop/return_qr_code
GET  /workshop/api/management/users/all              <-- admin enumeration
GET  /workshop/api/mechanic/
POST /workshop/api/merchant/contact_mechanic         <-- SSRF webhook (challenge 11), no rate limit (challenge 6)
POST /workshop/api/mechanic/receive_report
GET  /workshop/api/mechanic/mechanic_report          <-- sequential report_id (challenge 2)
GET  /workshop/api/mechanic/service_requests
POST /workshop/api/mechanic/signup
```

### Community surface

```
GET  /community/api/v2/community/posts/{postId}
POST /community/api/v2/community/posts
POST /community/api/v2/community/posts/{postId}/comment
GET  /community/api/v2/community/posts/recent         <-- leaks vehicleid alongside author (challenge 1)
POST /community/api/v2/coupon/new-coupon              <-- admin-shaped, no auth on every variant (challenge 14)
POST /community/api/v2/coupon/validate-coupon         <-- NoSQL injection surface (challenge 12)
```

### Auxiliary

```
GET  /.well-known/jwks.json                            <-- published; also leaks the algorithm and key
GET  /identity/health_check, /workshop/health_check/, /community/home
GET  /workshop/openapi-spec/                           <-- OpenAPI passthrough
```

Chatbot endpoints (not in the canonical OpenAPI spec; documented in
`docs/setup.md` and the chatbot service):

```
POST /genai/init       <-- per-session LLM provider key bootstrap (OpenAI/Anthropic only)
POST /genai/chat       <-- chat completion against the embedded RAG
                          (vulnerable to prompt injection, challenge 16;
                          credential extraction, challenge 17;
                          unauthorized-action-on-behalf-of-user, challenge 18)
```

## 9. Known security posture (intentional)

crAPI is candid about its design. Per `docs/challenges.md`, the
following attack surfaces are present **by intent** and are the things
specialist reviewers should expect to surface as findings:

- **BOLA #1 — Vehicle location disclosure across users.** The
  `/identity/api/v2/vehicle/{vehicleId}/location` endpoint accepts any
  UUID and returns latitude, longitude, and the owner's full name. The
  UUID is leaked via the `/community/.../posts/recent` response, so
  enumeration is unnecessary.
- **BOLA #2 — Mechanic report disclosure across users.** Mechanic
  report IDs are sequential integers exposed in the `report_link`
  field returned by `/workshop/api/merchant/contact_mechanic`. The
  `/workshop/api/mechanic/mechanic_report?report_id=N` endpoint does
  not authorise the requester against the report owner.
- **Broken Authentication #3 — Password reset OTP brute-force.** The
  `v2` OTP-check has a rate limit; sibling variants
  (`v3/check-otp`, undocumented paths) do not. A 4-digit numeric OTP
  is trivially brute-forceable absent throttling.
- **Excessive Data Exposure #4 — Sensitive user data in profile
  responses.** The user dashboard / profile endpoints serialize fields
  the UI does not display.
- **Excessive Data Exposure #5 — Internal video property leakage.**
  The video object response includes an internal property
  (`conversion_params`) that the UI never uses; its value drives
  challenge 10.
- **No Rate Limit #6 — Layer-7 DoS via `contact_mechanic`.** No
  throttle on the contact-mechanic submission endpoint; arbitrary
  outbound webhook fan-out.
- **BFLA #7 — Cross-user video deletion via admin endpoint.** The
  admin path `DELETE /identity/api/v2/admin/videos/{video_id}` does
  not check the caller's role; non-admin tokens are accepted.
- **Mass Assignment #8/#9 — Negative-quantity refund and balance
  inflation.** `POST /workshop/api/shop/orders` allows negative
  `quantity`. The server applies the credit delta unconditionally,
  letting the caller mint balance.
- **Mass Assignment #10 — Internal video property tampering.** A
  shadow update endpoint accepts arbitrary internal video fields,
  reachable by leveraging the leaked field name from #5.
- **SSRF #11 — Outbound HTTP from contact-mechanic webhook.** The
  `mechanic_api` URL submitted to `/workshop/api/merchant/contact_mechanic`
  is fetched server-side, returning the HTTP response body to the
  caller. No allowlist; works against `localhost`, `169.254.169.254`,
  and arbitrary external hosts.
- **NoSQL Injection #12 — Coupon validation bypass.** The
  `/community/api/v2/coupon/validate-coupon` endpoint parses the
  request body directly into a Mongo query selector.
- **SQL Injection #13 — Coupon re-redemption via direct SQL.** The
  workshop `apply_coupon` flow concatenates SQL; UPDATE statements can
  be injected to clear `claimed` flags.
- **Unauthenticated Access #14 — At least one privileged endpoint
  lacks auth.** Specific endpoint left as an exercise to discover.
- **JWT vulnerabilities #15.** Four documented variants:
  1. RS256↔HS256 algorithm confusion (public JWK as HMAC key).
  2. Signature-validation bypass on the dashboard endpoint (`sub`
     accepted without signature check).
  3. `jku` header trust — JWT accepted if it points to an
     attacker-controlled JWKS URL.
  4. `kid` path traversal — `kid=../../../../../../dev/null` plus
     `Hex(00)` HMAC accepted.
- **LLM #16/17/18.** Chatbot prompt-injection allowing client-side
  rendering injection (#16), credential extraction of another user
  (#17), and action-on-behalf-of (#18) flows.
- **Implicit posture facts visible in `deploy/docker/docker-compose.yml`:**
  - Postgres + Mongo creds are static literals in the compose file
    (`crapisecretpassword`, account `admin`).
  - `JWT_SECRET=crapi` shipped alongside the RS256 keys (multi-algo
    confusion surface).
  - `services/identity/jwks.json` is shipped containing private-key
    material (`d`, `p`, `q`, `dp`, `dq`, `qi`); operators are expected
    to override but the default install ships with a known-compromised
    key.
  - `ENABLE_LOG4J=false` flag exists, implying a deliberate
    log4j-injection toggle is wired into the identity service.
  - `ENABLE_SHELL_INJECTION=false` flag exists in the identity env,
    implying a deliberate command-injection sink is wired behind a
    toggle.
  - Gateway-service (`api.mypremiumdealership.com`) hosts deterministic
    PII (`SSN`, card number, address) seeded from a VIN hash; if the
    basic-auth credential is captured (or guessable), VIN enumeration
    becomes a PII oracle.

## 10. Out-of-scope for this plan

- **Operational hardening.** crAPI does not target production
  deployment. No on-call posture, no SLO commitments, no key
  rotation, no log retention, no observability stack ships in the
  default deploy. See `agents.md` for context.
- **Multi-tenant isolation.** Single-tenant by design.
- **Encryption at rest.** Not configured anywhere in the inputs.

For the residual-risk register and per-component-level threat model,
see `threat-model.md`. For per-service detail, see
`architecture-index.md`. For the four foundational decisions, see
`adrs/`.
