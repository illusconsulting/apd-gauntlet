---
title: 0001 — Microservice split by host language
status: accepted
date: 2020-09-15
---

# ADR-0001: Microservice split by host language

- **Status:** Accepted
- **Date:** 2020-09-15

## Context

crAPI is an educational target for the OWASP API Security Top 10. A
single-language monolith would model one runtime's pitfalls — Python
WSGI patterns, or Spring Boot's filter chain, or Express middleware —
but the Top 10 manifests differently in each ecosystem. Mass-assignment
in a Django serializer looks unlike mass-assignment in a Go struct
binder; JWT mishandling in `jjwt` differs from `golang-jwt`.

Per `docs/overview.md`, the project's intent is to "demonstrate the
OWASP API Top 10 vulnerabilities" with "minimal tech" on a single
t2.micro host. The split therefore needs to be wide enough to teach
language-specific failure modes but narrow enough to run on a 1-vCPU
host.

## Decision

Implement each functional area in a different mainstream API language,
deployed as an independent container behind a single OpenResty ingress:

| Service     | Language      | Framework        |
|-------------|---------------|------------------|
| `crapi-web` | JavaScript    | OpenResty (Nginx + LuaJIT) |
| `crapi-identity` | Java     | Spring Boot      |
| `crapi-workshop` | Python   | Django           |
| `crapi-community` | Go      | Standard `net/http` + custom router |
| `crapi-chatbot` | Python    | LangChain-style RAG |
| `gateway-service` | Go      | Standard `net/http` (simulated third-party API) |

Datastores (`postgres:14`, `mongo:4.4`, `chromadb`, `mailhog`) run as
standard upstream images.

## Consequences

**Positive.**

- Practitioners see the same vulnerability class (e.g. mass-assignment)
  manifest in three different ORMs and binding layers.
- Per-language idioms for JWT handling, request parsing, and SQL/NoSQL
  query construction are all directly observable.
- Each service has its own `Dockerfile`, `health.sh`, and build
  toolchain; failure modes don't bleed between services.

**Negative / trade-offs.**

- **JWT verification surface is heterogeneous.** Every service has to
  pick a JWT library in its native ecosystem and configure
  algorithm-pinning, `kid` handling, `jku` allowlisting, and signature
  enforcement consistently. The challenges page (#15) documents that
  this consistency does not hold — different services accept
  different forged tokens. There is no shared verification module.
- **Three HTTP-client libraries to harden.** Workshop (Python
  `requests`) makes the SSRF call (challenge 11); community (Go
  `net/http`) calls identity for JWKS; chatbot makes outbound LLM
  calls. SSRF mitigations, redirect policies, and DNS-rebinding
  defenses must be applied per-language.
- **Three SQL / NoSQL query construction styles.** Workshop's Django
  ORM, community's Go SQL driver, and the Mongo driver each have
  their own injection footguns. The catalog includes both
  challenge 12 (NoSQL on community) and challenge 13 (SQL on
  workshop).
- **Build-time complexity.** Compose pulls / builds five language
  toolchains. The `deploy/docker/build-all.sh` script is
  load-bearing for any from-source operator workflow.
- **Resource limits are uniformly tight.** `cpus: 0.8, memory: 384M`
  per service to meet the t2.micro target; little room to absorb
  bursts.

**Invariants pinned by this ADR (intended, not all enforced).**

- Each service has exactly one language runtime — no in-process
  polyglot.
- Inter-service authentication is JWT-only, validated against the
  identity service's JWKS.
- The web ingress is the only externally-bound port in the default
  compose (plus Mailhog `:8025`, by exception).

## Enforcement

- `services/<svc>/Dockerfile` per language.
- `services/<svc>/health.sh` per language; compose `healthcheck:`
  blocks invoke them.
- No shared library is imported across services; each service vendors
  its dependencies.

## Notes

This ADR is reconstructed from the codebase shape; the upstream
project's design discussion is not committed to the repo. The
decision's consequences are observable in the challenge catalog: every
challenge that touches authentication touches a language-specific
implementation choice.
