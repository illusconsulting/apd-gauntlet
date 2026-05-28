---
methodology: stride
---

# Threat Model — crAPI

STRIDE-organised threat model for crAPI. Each row identifies a threat
class, the surface it lands on, a concrete attack scenario, the impact,
the mitigation present in inputs (if any), and the residual question
the architect cannot answer from the inputs alone. The catalog is
populated from `docs/challenges.md` + `docs/challengeSolutions.md` +
the deployment posture visible in `deploy/docker/docker-compose.yml`.

This is **not** an exhaustive enumeration. crAPI is a vulnerable target
by design; the residual-question column is deliberately rich because
the inputs are silent on most production controls.

## Scope and methodology

- **Methodology:** STRIDE per surface (i.e. each API surface and each
  trust-boundary hop gets walked through the six categories). The
  challenge catalog from `docs/challenges.md` is the ground-truth
  threat library; each numbered challenge maps to one or more STRIDE
  categories below.
- **In scope:** All eight crAPI services in the default compose,
  including the chatbot, mailhog, the simulated dealership gateway
  (`api.mypremiumdealership.com`), and the bundled PKCS12 / JWKS
  material.
- **Out of scope:** Browser-class attacks against the SPA bundle
  shipped by `crapi-web` (a separate review would be needed on the JS
  build); upstream LLM-provider compromise; supply-chain compromise of
  the upstream `chromadb`, `postgres`, `mongo`, `mailhog` images.

Severity tags: **H**igh, **M**edium, **L**ow — reflecting impact only
(crAPI is intentionally vulnerable, so likelihood is irrelevant).

## 1. Spoofing (S)

### S-1 — JWT algorithm-confusion (RS256 → HS256) at identity

- **Surface:** identity JWT verifier; any service that re-verifies
  bearer tokens against the JWKS endpoint.
- **Attack scenario:** Attacker fetches
  `GET /.well-known/jwks.json`, base64-encodes the public modulus, and
  signs a JWT with `alg: HS256` using the encoded public key as the
  HMAC secret. The identity verifier (and any naive downstream
  verifier reusing the same library default) accepts the token. Per
  `docs/challengeSolutions.md` #15, this is the documented exploit.
- **Impact:** **H** — Authentication bypass; full session as any user
  by setting the `sub` claim. Lateral pivot into every service that
  trusts identity-issued tokens.
- **Existing mitigation:** None in evidence. Both `JWT_SECRET=crapi`
  and the RS256 JWKS are present in the identity environment, so the
  verifier supports both algorithms by configuration.
- **Residual question:** Does any downstream service do
  algorithm-pinning (`alg: RS256` only) in its JWT-verification
  library wrapper? The inputs do not say. The challenge solution
  describes the attack as effective without specifying which services
  it bypasses.

### S-2 — `alg: none` acceptance on the dashboard endpoint

- **Surface:** `GET /identity/api/v2/user/dashboard`.
- **Attack scenario:** Per challenge 15 #2, the dashboard endpoint
  accepts a JWT with a missing or unverified signature; the `sub`
  claim alone is treated as authoritative. Attacker mints a token
  with `alg: none` and `sub: victim@example.com` and reads the
  victim's dashboard.
- **Impact:** **H** — Information disclosure of victim's profile,
  vehicles, recent activity.
- **Existing mitigation:** None in evidence.
- **Residual question:** Is this an isolated bug in the dashboard
  handler or does the same code path govern other identity endpoints?

### S-3 — `jku` header misuse

- **Surface:** identity JWT verifier.
- **Attack scenario:** Attacker hosts a JWK at an attacker-controlled
  URL, signs a JWT with `jku: https://attacker.example/jwks` and a
  matching `kid`, and presents it. The verifier fetches the JWK over
  HTTP and accepts the signature.
- **Impact:** **H** — Same as S-1.
- **Existing mitigation:** None in evidence.
- **Residual question:** What is the verifier's `jku` allowlist? No
  configuration is exposed in the inputs.

### S-4 — `kid` path-traversal

- **Surface:** identity JWT verifier.
- **Attack scenario:** Attacker sets `kid: ../../../../../../dev/null`
  and signs with HMAC using the all-zero key (`AA==` in base64). The
  verifier reads `/dev/null` (zero bytes) as the key material and the
  HMAC over zero bytes validates.
- **Impact:** **H** — Same as S-1.
- **Existing mitigation:** None in evidence.
- **Residual question:** Does the verifier sanitize `kid` against a
  fixed allowlist, or does it interpret `kid` as a filesystem path?
  Challenge 15 #4 documents the latter.

### S-5 — Gateway-service basic-auth credential reuse / guessing

- **Surface:** outbound identity → `api.mypremiumdealership.com`.
- **Attack scenario:** Identity authenticates to the gateway with
  HTTP basic-auth. The credential is not documented; if static and
  obtainable (env dump, log leak, or simple guess against `admin /
  Admin!123` — visible in the chatbot env), the attacker can drive
  arbitrary VIN lookups against the gateway and recover seeded PII.
- **Impact:** **M** — PII disclosure for any VIN the attacker can
  enumerate; payment-info return for arbitrary orders.
- **Existing mitigation:** None in evidence.
- **Residual question:** Where is the basic-auth credential
  configured? The compose file does not expose it; presumably hard-
  coded in the identity service binary.

### S-6 — Email-only identity claim for password reset

- **Surface:** `POST /identity/api/auth/forget-password`.
- **Attack scenario:** Attacker enumerates emails (community posts
  carry an author display name; user dashboards are reachable per
  S-2) and initiates a password reset against the victim. With the
  4-digit OTP brute-forced via S-OTP below, account takeover is
  complete.
- **Impact:** **H** — Account takeover.
- **Existing mitigation:** Rate-limit on `v2/check-otp` per
  challenge 3 discussion; not on `v3/check-otp`.
- **Residual question:** Is the OTP delivered out-of-band reliably?
  Default deploy routes everything to mailhog, which an attacker who
  reaches `:8025` can simply read.

## 2. Tampering (T)

### T-1 — Mass-assignment on shop orders (challenge 8 / 9)

- **Surface:** `POST /workshop/api/shop/orders`.
- **Attack scenario:** Caller submits `quantity: -100` (negative).
  The server multiplies `unit_price * quantity` and applies the
  signed delta to the user's credit balance, increasing the balance
  by 100 × price.
- **Impact:** **H** — Arbitrary balance inflation; full marketplace
  economy compromise.
- **Existing mitigation:** None in evidence; no server-side check
  on `quantity >= 1`.
- **Residual question:** Is `unit_price` server-derived or
  client-supplied? Challenge 9 implies the latter is exploitable as
  well.

### T-2 — Mass-assignment on internal video properties (challenge 10)

- **Surface:** `POST /identity/api/v2/user/videos/{video_id}`
  (shadow update path).
- **Attack scenario:** Caller learns the internal property name from
  challenge 5 (excessive data exposure), submits an update payload
  including that property, and the server persists it. The video
  object's `conversion_params` (or equivalent) is now
  attacker-controlled.
- **Impact:** **M** — Persistent influence on downstream processing
  (per challenges, this enables further pivots).
- **Existing mitigation:** None in evidence; no allowlist on the
  update payload.
- **Residual question:** What downstream consumer reads the internal
  property and what is the secondary impact?

### T-3 — Mass-assignment on coupons (challenge 12 / 13)

- **Surface:** `POST /community/api/v2/coupon/validate-coupon`
  (NoSQL) and `POST /workshop/api/shop/apply_coupon` (SQL).
- **Attack scenario:** NoSQL: the request body is interpreted as a
  Mongo query selector; sending `{"coupon_code": {"$ne": ""}}` returns
  arbitrary coupon documents. SQL: the workshop side concatenates the
  coupon code into a SQL fragment, enabling UPDATE injection to
  reset `claimed` flags so already-redeemed coupons are re-redeemable.
- **Impact:** **H** — Free coupon redemption; marketplace economy
  compromise.
- **Existing mitigation:** None in evidence.
- **Residual question:** Are the SQL queries parameterized anywhere
  on the workshop side, or is string concatenation systemic?

### T-4 — Server trusts client price calculation

- **Surface:** `POST /workshop/api/shop/orders` (price field).
- **Attack scenario:** If `unit_price` or `total` is passed in the
  request body and stored verbatim, the attacker pays an arbitrary
  amount.
- **Impact:** **H**.
- **Existing mitigation:** Unclear from inputs.
- **Residual question:** Schema for the orders POST is not in the
  provided OpenAPI extract; needs source-level confirmation.

### T-5 — Chatbot prompt-injection inducing actions

- **Surface:** `POST /chatbot/genai/chat`.
- **Attack scenario:** User crafts a prompt that the chatbot's
  agent loop interprets as a tool call. Because the chatbot holds
  `API_USER=admin@example.com / API_PASSWORD=Admin!123`, the call
  hits identity / workshop as that admin and executes (challenge 18).
- **Impact:** **H** — Privileged actions on behalf of an admin
  triggered by an unprivileged user.
- **Existing mitigation:** None in evidence.
- **Residual question:** Is there any allowlist on the chatbot's
  tool surface? Inputs are silent.

## 3. Repudiation (R)

### R-1 — Absence of an audit log for financial actions

- **Surface:** workshop (orders, coupons, returns, refunds), identity
  (password reset, email change), community (posts, comments).
- **Attack scenario:** A user disputes a refund / balance-inflation
  event. There is no immutable record of who initiated the action,
  from what IP, with what token. Forensic reconstruction is impossible.
- **Impact:** **M** — Cannot attribute fraud; cannot prove non-
  repudiation in disputes.
- **Existing mitigation:** None in evidence. `LOG_LEVEL=INFO` env is
  set but there is no audit-log spec.
- **Residual question:** Are application logs at INFO level kept, and
  for how long? No retention policy is shipped. Are they immutable,
  signed, or shipped to a separate aggregator? Unspecified.

### R-2 — Absence of a token-revocation list

- **Surface:** identity-issued JWTs with `JWT_EXPIRATION=604800000`
  (7-day TTL).
- **Attack scenario:** After an account takeover via S-1 / S-6, the
  legitimate owner regains access (e.g. resets their password) but
  the attacker's old token remains valid for the rest of the 7-day
  window.
- **Impact:** **M** — Compromise persists beyond owner-initiated
  remediation.
- **Existing mitigation:** None.
- **Residual question:** Is there a JTI deny-list anywhere? Inputs
  are silent.

### R-3 — Chatbot actions are not attributable to the originating user

- **Surface:** chatbot → identity / workshop with admin credentials.
- **Attack scenario:** A chatbot-triggered action lands at workshop
  with `Authorization: Bearer <admin-jwt>`. The action's audit trail
  (if any exists at workshop) attributes it to `admin@example.com`,
  not the user whose chat session triggered it.
- **Impact:** **M** — Forensic attribution void.
- **Existing mitigation:** None.
- **Residual question:** Does the chatbot propagate a `caller_id`
  header or session context that workshop logs? Unspecified.

## 4. Information Disclosure (I)

### I-1 — BOLA #1: Vehicle location across users

- **Surface:** `GET /identity/api/v2/vehicle/{vehicleId}/location`
  + `GET /community/api/v2/community/posts/recent`.
- **Attack scenario:** The community recent-posts response carries
  the author's `vehicleid` as a sibling field. Calling `/location`
  for that UUID returns the owner's full name, latitude, and
  longitude.
- **Impact:** **H** — Geolocation disclosure of arbitrary users.
- **Existing mitigation:** None.
- **Residual question:** Is the vehicle-location enrichment on the
  community-posts response present in all deploy variants or only the
  default? Inputs do not differentiate.

### I-2 — BOLA #2: Mechanic reports across users

- **Surface:** `GET /workshop/api/mechanic/mechanic_report?report_id=N`.
- **Attack scenario:** Reports are keyed by sequential integer; no
  ownership check against the bearer token. The report URL is
  returned to the report submitter via `report_link`, but the integer
  ID makes enumeration trivial.
- **Impact:** **M-H** — Mechanic-report disclosure (vehicle issue
  narrative, owner identifying info if reports include it).
- **Existing mitigation:** None.
- **Residual question:** What fields does a mechanic report carry?
  PII surface depends on schema.

### I-3 — Excessive data exposure in user dashboard / videos

- **Surface:** `GET /identity/api/v2/user/dashboard`,
  `GET /identity/api/v2/user/videos/{video_id}`.
- **Attack scenario:** Endpoint serialises the underlying ORM
  object. Internal fields (challenge 5: `conversion_params` on
  videos; unspecified for the dashboard) reach the client.
- **Impact:** **M** — Internal-field disclosure; enables T-2 via
  field-name discovery.
- **Existing mitigation:** None.
- **Residual question:** Are there serialiser allowlists anywhere?
  Per the challenge framing, no.

### I-4 — SSRF #11 enables internal metadata exfiltration

- **Surface:** `POST /workshop/api/merchant/contact_mechanic`.
- **Attack scenario:** Caller submits a webhook URL pointing at
  `http://169.254.169.254/latest/meta-data/`, `http://localhost:8025`,
  `http://postgresdb:5432`, etc. The workshop service fetches and
  echoes the response body to the caller.
- **Impact:** **H** — Cloud metadata theft (in cloud deploy); internal
  network probing; reads on co-located internal services (mailhog UI,
  ChromaDB, gateway-service basic-auth realm headers).
- **Existing mitigation:** None.
- **Residual question:** Is there any URL allowlist or DNS-based
  filter on the outbound request? Inputs say no.

### I-5 — Public JWKS endpoint leaks key + algorithm

- **Surface:** `GET /.well-known/jwks.json`.
- **Attack scenario:** Endpoint publishes the RS256 public key. This
  is **normal** for OIDC-style JWKS but in the presence of S-1 (HS256
  confusion) it is the attack enabler.
- **Impact:** **L** in isolation; **H** combined with S-1.
- **Existing mitigation:** None — the endpoint is designed to be
  public.
- **Residual question:** Should the response include cache headers
  that allow CDN poisoning? Unspecified.

### I-6 — Mailhog `:8025` exposes every OTP

- **Surface:** mailhog web UI on port `:8025`.
- **Attack scenario:** Anyone on the same network as the deployed
  stack can read every signup OTP, password-reset OTP, and
  notification email by visiting `http://<host>:8025/`. No auth on
  the UI.
- **Impact:** **H** (in any non-loopback deploy).
- **Existing mitigation:** Default `LISTEN_IP=127.0.0.1` keeps it on
  the loopback, but `LISTEN_IP=0.0.0.0` (documented in setup.md)
  removes that bound.
- **Residual question:** Production email path is unconfigured (see
  tech_plan §7); there is no documented alternative.

### I-7 — Postgres / Mongo / ChromaDB plaintext credentials

- **Surface:** `deploy/docker/docker-compose.yml` env stanzas.
- **Attack scenario:** Credentials (`admin /
  crapisecretpassword`) are world-readable in any clone of the
  repo, in any container's `/proc/1/environ`, and through `docker
  inspect` to anyone with Docker access.
- **Impact:** **H** — Direct datastore access bypassing all service-
  layer controls.
- **Existing mitigation:** None.
- **Residual question:** Helm `values.yaml` may or may not override
  these in production deploys; the values file content was not in
  the source set.

### I-8 — Gateway-service VIN-to-PII oracle

- **Surface:** `api.mypremiumdealership.com/owners?vin=...`
  (basic-auth protected).
- **Attack scenario:** Combined with S-5, an attacker iterates VINs
  (or learns them from BOLA-1 vehicle leaks) and pulls the
  faker-seeded `SSN`, `address`, `card_number`, `card_owner_name` for
  each. Outputs are deterministic (FNV-32a seed), so the same VIN
  always returns the same identity record — useful as a fingerprint /
  re-identification oracle even across deploys.
- **Impact:** **H** — Bulk PII / payment-data disclosure.
- **Existing mitigation:** Basic-auth; no rate limit visible.
- **Residual question:** Where the basic-auth credential lives (see
  S-5).

## 5. Denial of Service (D)

### D-1 — No rate limit on `contact_mechanic`

- **Surface:** `POST /workshop/api/merchant/contact_mechanic`
  (challenge 6).
- **Attack scenario:** Caller submits a high-volume burst of
  contact-mechanic requests, each triggering an outbound HTTP fetch.
  Service exhausts its outbound socket pool / worker pool; identity
  + community degrade as workshop's JWT verifier latency climbs.
- **Impact:** **H** — Application-layer DoS for crAPI; outbound
  burst is also a reflective-DoS launchpad against arbitrary
  external hosts.
- **Existing mitigation:** None.
- **Residual question:** Are there pod-level resource limits in the
  k8s/Helm deploy? Compose has `cpus: 0.8, memory: 384M` per
  service — small limits, easily exhausted.

### D-2 — Unbounded OTP brute force

- **Surface:** `POST /identity/api/auth/v3/check-otp` (per challenge
  3 discussion).
- **Attack scenario:** 4-digit OTP space is 10,000 entries; the
  un-throttled `v3` endpoint accepts repeated guesses until success.
- **Impact:** **H** — Account takeover; also a probe-storm DoS
  against the identity service.
- **Existing mitigation:** `v2/check-otp` has a documented rate
  limit; `v3` does not.
- **Residual question:** Are there other OTP-check variants beyond
  `v2` and `v3`? The challenge solution hints at predictable
  versioning (`/v4`, `/v5`, …).

### D-3 — Chatbot LLM cost amplification

- **Surface:** `POST /chatbot/genai/chat`.
- **Attack scenario:** Caller submits very long prompts that the
  chatbot forwards to the configured LLM provider. Each call bills
  the operator's API key. No prompt-length cap, no per-user rate
  limit, no token-budget check are mentioned.
- **Impact:** **M** — Operational-cost denial-of-wallet.
- **Existing mitigation:** None.
- **Residual question:** Per-session token budget configuration?
  Unspecified.

### D-4 — Compose `cpus/memory` limits encourage easy resource
exhaustion

- **Surface:** Every service has `cpus: 0.8, memory: 384M` (workshop
  and community in particular).
- **Attack scenario:** Any of D-1, D-2, D-3 lands on a thin pod; the
  pod OOMs or CPU-throttles cluster-wide before backpressure can
  apply.
- **Impact:** **M-H** depending on which service tips first.
- **Existing mitigation:** None.
- **Residual question:** Is the Helm deploy's `resources:` block
  identical?

## 6. Elevation of Privilege (E)

### E-1 — BFLA #7: non-admin reaches admin video delete

- **Surface:** `DELETE /identity/api/v2/admin/videos/{video_id}`.
- **Attack scenario:** Non-admin caller hits the admin path with a
  normal user token; identity does not check the role claim. The
  video deletes.
- **Impact:** **M-H** — Cross-user resource destruction; pattern
  generalises if other `/admin/*` paths exist.
- **Existing mitigation:** None.
- **Residual question:** What other `/admin/*` endpoints exist?
  `/workshop/api/shop/orders/all` and
  `/workshop/api/management/users/all` are also admin-shaped per
  naming; their auth posture is not stated.

### E-2 — Unauthenticated access (challenge 14)

- **Surface:** Per challenge 14, at least one endpoint has no auth
  check at all; the challenge does not name it.
- **Attack scenario:** Caller invokes it without a token; the action
  succeeds.
- **Impact:** **Unknown — depends on endpoint.** If it is
  `POST /community/api/v2/coupon/new-coupon`, the impact is **H**
  (coupon mint without auth).
- **Existing mitigation:** None.
- **Residual question:** Which endpoint? The reviewer is expected to
  enumerate.

### E-3 — Mass-assignment to `role` field on user update

- **Surface:** identity user-update path (exact path unspecified in
  inputs; likely a hidden field on a known endpoint).
- **Attack scenario:** Caller submits `{"role": "admin"}` alongside
  benign fields on a self-update; the field is bound to the user
  record.
- **Impact:** **H** — Self-elevation to admin.
- **Existing mitigation:** None visible.
- **Residual question:** Is the role enum even exposed via a
  user-update endpoint? Not in the OpenAPI extract; would need
  source-level confirmation.

### E-4 — Chatbot admin-credential abuse (challenge 18 / T-5)

- **Surface:** `POST /chatbot/genai/chat`.
- **Attack scenario:** Prompt-injection convinces the chatbot's
  agent loop to call privileged endpoints using the chatbot's
  embedded admin credentials.
- **Impact:** **H** — Arbitrary admin actions.
- **Existing mitigation:** None.
- **Residual question:** What is the chatbot's tool-call surface?

### E-5 — Postgres / Mongo plaintext creds → bypass to admin

- **Surface:** Operator with network reach to `postgresdb:5432` or
  `mongodb:27017` (see I-7).
- **Attack scenario:** Direct DB connection with the leaked
  credentials; flip `users.role = 'admin'` for the attacker's row.
- **Impact:** **H**.
- **Existing mitigation:** None — credentials are in compose.
- **Residual question:** Network policy in k8s/Helm? Not described.

## 7. Cross-cutting residual questions

- **Key rotation.** No procedure is shipped for rotating the JWKS,
  the `JWT_SECRET`, the postgres/mongo credentials, the gateway-
  service basic-auth credential, or the chatbot's `API_PASSWORD`.
  See `runbook.md`.
- **Backup / restore.** Not described.
- **Audit log retention.** Not described (R-1, R-3).
- **Per-service principle-of-least-privilege at the datastore
  layer.** Every service authenticates to Postgres / Mongo as the
  same admin user.
- **TLS posture.** `TLS_ENABLED` is `false` by default; the certs
  shipped under each service's `certs/` are self-signed and
  development-only.
- **Inbound WAF / rate-limit at the web ingress.** Not present in
  the Nginx templates per the input set.
