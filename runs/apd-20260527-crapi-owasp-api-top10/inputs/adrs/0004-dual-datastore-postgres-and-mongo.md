---
title: 0004 — Dual datastores: Postgres for OLTP, Mongo for community content
status: accepted
date: 2020-11-20
---

# ADR-0004: Dual datastores: Postgres for OLTP, Mongo for community content

- **Status:** Accepted
- **Date:** 2020-11-20

## Context

Per `docs/crAPI_architecture.md`, the maintainers wanted practitioners
to "explore to identify the vulnerabilities with SQL and NoSQL
databases" in the same target. A single-datastore deploy would
restrict the challenge catalog to one injection family. The
community-content workload (blog posts, comments) maps naturally to a
document store; the transactional workload (accounts, vehicles,
orders) maps naturally to a relational store. Splitting along that
seam gives both query families a realistic home.

## Decision

Deploy two datastores side-by-side:

- **PostgreSQL 14** (`postgresdb`) — primary OLTP. Owns the `users`,
  `vehicles`, `vehicle_locations`, `profile_videos`, `mechanics`,
  `service_requests`, `mechanic_reports`, `products`, `orders`,
  `credit`, and `coupons` tables.
- **MongoDB 4.4** (`mongodb`) — community + chatbot document store.
  Owns the `posts`, `comments`, `coupon_documents`, and chatbot
  session collections.

Both datastores accept the same admin credential
(`admin / crapisecretpassword`, hardcoded in
`deploy/docker/docker-compose.yml`). Every service that needs either
datastore authenticates as `admin`; there is no per-service user
separation.

## Consequences

**Positive (intended pedagogy).**

- SQL-injection (challenge 13, on the workshop `apply_coupon` flow)
  and NoSQL-injection (challenge 12, on the community
  `validate-coupon` flow) both have realistic homes.
- The `coupons` row in Postgres and the `coupon_documents` doc in
  Mongo show practitioners how the same logical entity can have
  duplicated state across stores with no consistency contract — a
  realistic enterprise anti-pattern.

**Negative / trade-offs.**

- **Two access-control models to reason about.** Postgres RBAC vs.
  MongoDB role-based access. Neither is configured beyond a single
  super-user.
- **Two encryption-at-rest postures to evaluate.** Neither is
  configured in the inputs.
- **Two backup / restore disciplines.** Neither is shipped. A
  consistent point-in-time recovery across both stores would require
  coordinated snapshots; no tooling is provided.
- **Two audit-log pipelines to wire.** Postgres `pgaudit` and
  MongoDB audit logging are independent subsystems. Neither is
  enabled.
- **Cross-store consistency is the application's responsibility.**
  A coupon-redemption flow that touches both stores (community
  validates → workshop applies) can leave the records in
  inconsistent states under partial failure. The challenge catalog
  treats this as an attack surface (challenge 13's
  "re-redeem by modifying the database" wording implies a coupon
  document in Mongo that does not stay in sync with the Postgres
  row).
- **Single shared admin credential collapses both stores under one
  compromise.** Any service compromise yields full Postgres + full
  Mongo. Datastore-level isolation does not constrain blast radius
  (see threat-model I-7, E-5).
- **MongoDB 4.4 is past end-of-life.** Default auth defaults to the
  legacy `SCRAM-SHA-1`. The image tag is pinned in the compose file;
  no upgrade path is documented.

**Invariants pinned by this ADR (intended, not enforced).**

- Each logical entity is owned by exactly one datastore. (Held for
  most entities; coupons span both, by design, to support the
  injection challenges.)
- Service ↔ datastore authentication uses the operator-provisioned
  credential set. (Currently the single shared admin user.)
- Datastore network reachability is service-mesh-internal only.
  (Held in compose by not exposing `:5432` / `:27017` to `LISTEN_IP`;
  not enforced at the network-policy layer in the Helm deploy
  values that are shipped in the input set.)

## Enforcement

- Two `image:` blocks in `deploy/docker/docker-compose.yml`
  (`postgres:14`, `mongo:4.4`).
- Per-service `DB_HOST` / `MONGO_DB_HOST` env wiring.
- Healthchecks gate startup ordering (`depends_on: condition:
  service_healthy`).

## Notes

A production-style remediation would split the shared admin
credential into per-service users with row-level / collection-level
GRANTs, enable encryption-at-rest on both stores, configure backups
with cross-store coordination, enable pgaudit / Mongo audit logging,
upgrade MongoDB off 4.4, and add a network policy restricting
datastore reachability to the named consumers.
