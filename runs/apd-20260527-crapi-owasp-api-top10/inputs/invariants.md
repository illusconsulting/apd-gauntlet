# crAPI — Architect-Asserted Invariants

This is the architect's belief about what the system holds true. Each
entry pairs an invariant with the surface that should enforce it and a
note on whether the inputs confirm enforcement. **Many of these
invariants do not hold in crAPI by design** — the project's value as a
teaching target is exposing the gap between the intended invariant and
the enforced behaviour. Specialist reviewers should validate each
invariant against the inputs and surface the gap where it exists.

## Authentication and tokens

### INV-AUTH-001 — Every authenticated endpoint requires a valid bearer JWT

- **Asserted in:** OpenAPI `bearerAuth` security scheme on every
  non-signup/login/forget-password path.
- **Enforced by:** per-service JWT verifier middleware.
- **Reviewer note:** Challenge 14 explicitly contradicts this — at
  least one privileged endpoint accepts unauthenticated callers.
  Reviewer should identify it.

### INV-AUTH-002 — Every JWT must be RS256-signed by the identity service

- **Asserted in:** ADR-0002.
- **Enforced by:** identity-service signing logic; per-service
  verifiers.
- **Reviewer note:** Challenge 15 #1 contradicts — HS256 tokens
  signed with the public modulus as the HMAC key are accepted.

### INV-AUTH-003 — JWTs are validated for signature, expiration, and audience

- **Asserted in:** standard OIDC posture implied by ADR-0002.
- **Enforced by:** per-service verifier.
- **Reviewer note:** Challenge 15 #2 contradicts on the dashboard
  handler (signature not validated). No `aud` claim is mentioned in
  the OpenAPI bearer scheme — verifier audience-pinning is unknown
  but presumed absent.

### INV-AUTH-004 — Admin endpoints require an admin-role token

- **Asserted in:** the `/admin/` URL prefix convention.
- **Enforced by:** the identity / workshop role-check middleware.
- **Reviewer note:** Challenge 7 contradicts on
  `DELETE /identity/api/v2/admin/videos/{video_id}`.

### INV-AUTH-005 — Password reset OTPs are 4-digit numeric and expire on a short TTL

- **Asserted in:** Mailhog-observed OTP format; challenge 3
  discussion implies a TTL on the order of ~10 minutes.
- **Enforced by:** identity-service OTP generator and check handler.
- **Reviewer note:** Holds for OTP format. Brute-force protection
  does *not* hold on `v3/check-otp` per challenge 3.

## Authorization

### INV-AUTHZ-001 — Every object access is authorized against the caller's identity

- **Asserted in:** standard B2C semantics.
- **Enforced by:** per-service authorization checks.
- **Reviewer note:** Challenges 1 and 2 contradict (vehicle location,
  mechanic reports).

### INV-AUTHZ-002 — Vehicle IDs are UUIDs and must not be enumerable across users

- **Asserted in:** the `vehicleId: GUID` shape in the OpenAPI spec.
- **Enforced by:** UUIDv4 randomness at vehicle creation.
- **Reviewer note:** UUIDs are non-sequential but **leak** via the
  community recent-posts feed (challenge 1). The randomness invariant
  holds; the non-disclosure invariant does not.

### INV-AUTHZ-003 — Mechanic report IDs are not predictable

- **Asserted in:** general API hygiene.
- **Enforced by:** the workshop report-creation handler.
- **Reviewer note:** Challenge 2 contradicts — sequential integers.

## Input handling

### INV-INPUT-001 — Order quantity is a positive integer (>= 1)

- **Asserted in:** marketplace semantics.
- **Enforced by:** workshop order-create handler.
- **Reviewer note:** Challenges 8 and 9 contradict — negative
  quantities accepted, balance inflated.

### INV-INPUT-002 — Order unit price is server-derived from the product record

- **Asserted in:** standard e-commerce posture.
- **Enforced by:** workshop order-create handler.
- **Reviewer note:** Not confirmed from inputs. Challenge 9 suggests
  the field is at least partially client-controlled.

### INV-INPUT-003 — Coupon redemption is idempotent per user

- **Asserted in:** general loyalty-program semantics.
- **Enforced by:** workshop `apply_coupon` claimed-state check.
- **Reviewer note:** Challenge 13 contradicts via SQL injection
  on the claimed-state UPDATE.

### INV-INPUT-004 — User-supplied URLs are not server-fetched without an allowlist

- **Asserted in:** general SSRF hygiene.
- **Enforced by:** outbound-HTTP layer of each service.
- **Reviewer note:** Challenge 11 contradicts on
  `contact_mechanic`.

## Data exposure

### INV-DATA-001 — Response payloads omit fields the UI does not consume

- **Asserted in:** standard API serialiser discipline.
- **Enforced by:** per-endpoint serialiser allowlists.
- **Reviewer note:** Challenges 4 and 5 contradict — internal video
  property and excessive user fields exposed.

### INV-DATA-002 — No PII appears in URL paths or query strings

- **Asserted in:** general logging hygiene.
- **Enforced by:** URL-design discipline.
- **Reviewer note:** Holds for the documented endpoints (`vehicleId`
  is a UUID, not an email; `order_id` is an integer). The gateway-
  service VIN query (`?vin=...`) carries a VIN which is owner-
  identifying when combined with the deterministic
  faker-seeded record set.

## Operational

### INV-OPS-001 — Service credentials are unique per service

- **Asserted in:** least-privilege posture.
- **Enforced by:** datastore RBAC configuration.
- **Reviewer note:** Contradicted — single shared `admin /
  crapisecretpassword` for Postgres and Mongo (ADR-0004).

### INV-OPS-002 — Signing keys can be rotated without downtime

- **Asserted in:** standard JWKS posture (multi-`kid` support).
- **Enforced by:** identity-service `jwks.json` reload logic.
- **Reviewer note:** No rotation procedure ships (runbook §5). Multi-
  `kid` support is not confirmed.

### INV-OPS-003 — Every authentication and authorization event is audit-logged

- **Asserted in:** standard compliance posture.
- **Enforced by:** per-service audit emitter.
- **Reviewer note:** No audit log exists; only INFO-level service
  logs to stdout (threat-model R-1, R-3).

### INV-OPS-004 — Mailhog is loopback-only in any unattended deploy

- **Asserted in:** ADR-0003.
- **Enforced by:** `LISTEN_IP=127.0.0.1` default.
- **Reviewer note:** `LISTEN_IP=0.0.0.0` override is documented in
  setup.md without a warning. Operator-enforced; not technically
  pinned.

### INV-OPS-005 — TLS protects all in-cluster service-to-service traffic

- **Asserted in:** general defense-in-depth.
- **Enforced by:** `TLS_ENABLED=true` mode.
- **Reviewer note:** `TLS_ENABLED=false` by default; shipped certs
  are self-signed development material.
