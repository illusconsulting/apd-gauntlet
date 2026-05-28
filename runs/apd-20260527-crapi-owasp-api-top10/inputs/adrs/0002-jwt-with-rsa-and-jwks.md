---
title: 0002 — RS256 JWT minted by identity, verified via JWKS
status: accepted
date: 2020-10-08
---

# ADR-0002: RS256 JWT minted by identity, verified via JWKS

- **Status:** Accepted
- **Date:** 2020-10-08

## Context

Every service in the crAPI cluster needs to authenticate inbound
requests. Per ADR-0001 each service is in a different language, so a
shared symmetric secret would either need synchronised distribution to
every service or a central verifier (which would re-introduce a
single point of failure on the hot path). At the same time, a standard
OIDC-style asymmetric posture is what practitioners are likeliest to
see in the wild — and is therefore the right pedagogical model.

## Decision

`crapi-identity` mints **RS256-signed JWTs**. The signing private key
lives in a single JWKS file at `services/identity/jwks.json`
(repo-tracked by default). The corresponding public key is published
at `GET /.well-known/jwks.json` through the web ingress on `:8888`.
Downstream services (`crapi-workshop`, `crapi-community`,
`crapi-chatbot`) verify inbound bearer tokens by fetching the JWKS
from `IDENTITY_SERVICE=crapi-identity:8080` and using their language's
JWT library.

The identity service additionally accepts a `JWT_SECRET=crapi`
environment variable. This is a deliberate vulnerable-by-design
choice: the verifier supports both RS256 and HS256 (and the documented
challenge 15 set demonstrates four ways to forge an accepted JWT
against this multi-algorithm acceptance posture).

## Consequences

**Positive (intended pedagogy).**

- Mirrors a real-world OIDC posture: asymmetric signing, JWKS
  endpoint, per-language verifier libraries.
- Teaches practitioners to inspect the `alg`, `kid`, and `jku`
  headers; teaches operators why algorithm-pinning matters.

**Negative / trade-offs.**

- **Algorithm-confusion (RS256 ↔ HS256) is the headline forgery
  vector.** With both keys present and verifier libraries that
  trust the JWT header's `alg` field, an attacker re-signs a token
  as `alg: HS256` using the base64-encoded public modulus as the
  HMAC key. The token validates. This is challenge 15 #1.
- **`kid` is treated as a filesystem path.** Setting `kid` to
  `../../../../../../dev/null` lets the verifier read zero bytes from
  `/dev/null` as the key material, and an HMAC over zero bytes
  validates. Challenge 15 #4.
- **`jku` is fetched without an allowlist.** A JWT with `jku` pointing
  at an attacker-controlled JWK URL is verified against that JWK.
  Challenge 15 #3.
- **Default JWKS ships private-key components.** `jwks.json` in the
  repo contains `d`, `p`, `q`, `dp`, `dq`, `qi`. Operators are
  advised to drop a replacement into `deploy/<topology>/keys/` but
  the default install ships a known-compromised private key. Anyone
  pulling the published images can mint tokens for any user.
- **No rotation tooling.** There is no key-rotation script, no
  rotation runbook, no `kid` rollover ceremony documented. Once
  deployed, the key in `jwks.json` is effectively static.
- **Dashboard signature-validation bypass.** The dashboard handler
  reads `sub` from the token without verifying the signature
  (challenge 15 #2). Each downstream verifier is independently
  responsible for signature enforcement.

**Invariants pinned by this ADR (intended, not enforced).**

- All authenticated endpoints accept exactly one bearer-format
  scheme: `Bearer <jwt>`.
- All verifiers SHOULD pin `alg: RS256` and reject other algorithms.
  (Not enforced — that's the lesson.)
- The JWKS endpoint MUST publish only public-key components.
  (Trivially holds since the served JSON is filtered; but the
  on-disk file is the unfiltered key material.)

## Enforcement

- Identity-service signing happens in the Spring filter chain.
- Each downstream service has its own verifier; no shared module.
- The JWKS file is mounted into the identity container via the
  `volumes:` block in `deploy/docker/docker-compose.yml`
  (`./keys:/app/keys`).

## Notes

This is the ADR most directly responsible for the JWT challenge set
(challenge 15). A hardened production posture would remove
`JWT_SECRET` from the identity env, generate a fresh JWKS per
deploy, pin `alg: RS256` at every verifier, allowlist `jku`, and
reject `kid` values that do not match a known key ID set.
