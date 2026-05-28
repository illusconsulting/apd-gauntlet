# crAPI — Prior Audit Carry-Forward

This entry records the security-posture context that this APD review
inherits. crAPI is a published, intentionally-vulnerable training
target maintained by OWASP; its vulnerabilities are not a defect but
the artifact. The "prior audit" here is therefore a synthesis of the
upstream project's own honest disclosure (`docs/challenges.md`,
`docs/challengeSolutions.md`) plus the operational-posture
observations a reviewer should expect to carry forward, not the
output of a third-party assessment.

## Source

- **Auditor:** synthesised from the upstream OWASP crAPI documentation
  and the shipped artifacts at `docs/`, `openapi-spec/`,
  `deploy/docker/docker-compose.yml`, and `services/*/`.
- **Version under review:** crAPI v1.1.5 (per `/VERSION`).
- **License:** Apache-2.0.
- **Scope:** the eight-container default compose deploy (web,
  identity, workshop, community, chatbot, mailhog, postgresdb,
  mongodb), plus chromadb and the simulated gateway-service.

## TL;DR

crAPI ships with **18 publicly-documented vulnerabilities** across the
OWASP API Security Top 10 categories, plus three undisclosed "secret"
challenges. Operational hardening (key rotation, audit logging,
encryption-at-rest, backup, network policy, MFA) is not in scope for
the project and is uniformly absent. All credentials in the default
compose are static literals and known.

## Findings carried forward

Each entry below is a known-true posture statement. Specialist
reviewers should treat these as accepted starting state and produce
findings against the **operational consequences** (e.g. impact to
auditability, scalability, trustworthiness) rather than re-discovering
the underlying issue.

### Carried — Broken Object-Level Authorization

- **BOLA on vehicle location.** `GET /identity/api/v2/vehicle/{vehicleId}/location`
  accepts any UUID and returns owner identifiers + GPS. UUIDs leak
  via the community recent-posts feed. (Challenge 1.)
- **BOLA on mechanic reports.** `GET /workshop/api/mechanic/mechanic_report`
  uses sequential integer report IDs and does not authorize the
  requester. (Challenge 2.)

### Carried — Broken Authentication

- **OTP brute-force.** 4-digit numeric OTP, `v3/check-otp` variant is
  unthrottled. (Challenge 3.)
- **JWT algorithm-confusion (RS256↔HS256).** Identity accepts HS256
  tokens signed with the public modulus as the HMAC key.
  (Challenge 15 #1.)
- **JWT signature-validation bypass on dashboard.** The dashboard
  endpoint reads `sub` without verifying the signature.
  (Challenge 15 #2.)
- **JWT `jku` abuse.** The verifier fetches JWKs from attacker-
  controlled `jku` URLs. (Challenge 15 #3.)
- **JWT `kid` path traversal.** `kid: ../../../../../../dev/null`
  with the all-zero HMAC key is accepted. (Challenge 15 #4.)

### Carried — Excessive Data Exposure

- **Sensitive user data in profile responses.** (Challenge 4.)
- **Internal video property leakage.** `conversion_params` (or
  equivalent) reaches the client; field name drives the mass-
  assignment in challenge 10. (Challenge 5.)

### Carried — Lack of Resources & Rate Limiting

- **No rate limit on `contact_mechanic`.** Layer-7 DoS surface.
  (Challenge 6.)
- **No rate limit on `v3/check-otp`.** Enables brute-force (carried
  with challenge 3).

### Carried — Broken Function-Level Authorization

- **Admin video-delete reachable by non-admin.**
  `DELETE /identity/api/v2/admin/videos/{video_id}` does not check
  role. (Challenge 7.)

### Carried — Mass Assignment

- **Negative-quantity refund on `POST /workshop/api/shop/orders`.**
  Server applies `unit_price × quantity` unconditionally,
  enabling balance inflation. (Challenges 8 and 9.)
- **Internal video property tampering on `POST /identity/api/v2/user/videos/{video_id}`.**
  Allows write to fields not exposed in the documented schema.
  (Challenge 10.)

### Carried — SSRF

- **Outbound HTTP from `contact_mechanic` is attacker-controlled.**
  No URL allowlist, no DNS filter; reaches internal services, cloud
  metadata, arbitrary external hosts. (Challenge 11.)

### Carried — Injection

- **NoSQL injection on coupon validation.**
  `POST /community/api/v2/coupon/validate-coupon` parses request body
  into a Mongo selector. (Challenge 12.)
- **SQL injection on coupon application.**
  `POST /workshop/api/shop/apply_coupon` concatenates SQL; UPDATE
  injection re-arms claimed coupons. (Challenge 13.)

### Carried — Unauthenticated Access

- **At least one privileged endpoint accepts unauthenticated
  callers.** Specific endpoint not named in the catalog.
  (Challenge 14.)

### Carried — LLM-specific (OWASP LLM Top 10 overlap)

- **Chatbot prompt-injection enabling client-side rendering
  injection.** (Challenge 16.)
- **Chatbot prompt-injection extracts another user's credentials.**
  (Challenge 17.)
- **Chatbot acts on behalf of another user.** The chatbot holds an
  admin crAPI credential and can be coerced into privileged actions.
  (Challenge 18.)

### Carried — Operational hygiene (out of upstream challenge catalog,
visible in the inputs)

- **Postgres + Mongo credentials are hardcoded in compose**
  (`admin / crapisecretpassword`).
- **`JWT_SECRET=crapi` ships alongside RS256 keys** — the multi-
  algorithm acceptance surface enabling challenge 15 #1.
- **Default JWKS contains private-key components.** `jwks.json` in
  `services/identity/` carries `d`, `p`, `q`, `dp`, `dq`, `qi`.
  Operators must override; the default install ships a known-
  compromised signing key.
- **Self-signed certificates shipped under each service's `certs/`
  directory.** Development-only; TLS is off by default.
- **`ENABLE_LOG4J=false` toggle wired into identity.** Implies a
  deliberate log4shell-style injection sink exists behind the
  flag.
- **`ENABLE_SHELL_INJECTION=false` toggle wired into identity.**
  Implies a deliberate command-injection sink exists behind the
  flag.
- **Gateway-service basic-auth credentials are not documented.**
  The credential lives in the binary; rotation is undefined.

### Carried — Operational gaps (no procedure in the input set)

- No key rotation runbook.
- No audit-log retention or schema.
- No backup / restore procedure.
- No network policy in shipped Helm values.
- No MFA at any authentication surface.
- No session revocation; 7-day JWT TTL without a JTI deny-list.
- No production-grade SMTP path.

## Reviewer guidance

The specialist agents in this gauntlet should:

1. **Not re-derive the vulnerability catalog.** It is canonical.
2. **Produce findings against the second-order consequences** — the
   gaps in trustworthiness, scalability, and auditability that the
   above posture creates.
3. **Treat any silence in the inputs about operational controls as
   "control absent"** and surface the corresponding finding (per the
   APD evidence-discipline rule on block-on-ambiguity).
