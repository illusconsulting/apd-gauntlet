---
title: 0002 — Django + Postgres-backed queue + optional Redis for the core
status: accepted
date: 2020-09-01
---

# ADR-0002: Django + Postgres-backed queue + optional Redis stack

- **Status:** Accepted
- **Date:** 2020-09-01 (approximate; first releases)

## Context

The Server core needs:

- A web framework with a mature auth/session model, a permission
  model, an ORM, an admin scaffold, and an OpenAPI-aware REST
  layer.
- A background-task runner for long-running work (email send,
  Source sync, SCIM sync, outpost lifecycle, blueprint apply).
- A WebSocket transport for outpost configuration push and live
  admin UI updates.
- A primary persistent store for all identity, configuration, and
  audit data.
- A cache + pub/sub layer for sessions, channel layers, and
  short-lived shared state.

For a Python-leaning team building an enterprise-grade IdP in 2020,
the conventional stack — **Django + Celery + Redis + PostgreSQL** —
is the well-trodden path. Subsequent versions have evolved toward
Postgres-backed alternatives for the queue and channels layers,
reducing the operational footprint by allowing operators to skip
Redis when they wish.

## Decision

Build the Server on **Django 5.2.x** (per `pyproject.toml`:
`django==5.2.14`, `djangorestframework==3.17.1`,
`drf-spectacular==0.29.0`, `django-channels==4.3.2`).

Persist all identity, configuration, audit, session, and secret
data in **PostgreSQL** (per `pyproject.toml`: `psycopg[c,pool]==3.3.4`;
per `core/architecture.md`: "authentik uses PostgreSQL to store all
of its configuration and other data (excluding uploaded files).")

Run background tasks with **`django-dramatiq-postgres`** (workspace
member per `pyproject.toml [tool.uv.workspace]`) — that is, a
Postgres-backed task queue using `django-pglock==1.8.0` and
`django-pgtrigger==4.17.0` for locking and trigger-driven dispatch.
This replaces the Celery + Redis posture used in earlier versions.

Use **`django-channels-postgres`** (workspace member) for WebSocket
pub/sub, with optional Redis fallback configurable per
`AUTHENTIK_REDIS__*` settings.

Use **`django-postgres-cache`** (workspace member) for short-lived
cache. Redis remains a supported alternative.

Multi-tenancy uses **`django-tenants==3.10.1`** with PostgreSQL
schema-per-tenant (per `sys-mgmt/tenancy.md`).

## Consequences

**Positive.**

- Single primary datastore. Operators who want to run authentik
  without Redis can do so; PostgreSQL alone is the supported
  posture.
- Backup story is well-scoped: per `sys-mgmt/ops/backup-restore.md`,
  PostgreSQL backup via `pg_dump` / `pg_restore` /
  continuous-archiving is the documented procedure. Restoring the
  database restores the configuration and identity state.
- Django brings: ORM with migrations (per Makefile `migrate`
  target), admin scaffold, session middleware, CSRF protection,
  template engine, model permissions.
- DRF brings: serializer-based REST API with versioning at
  `/api/v3/...`, OpenAPI schema via `drf-spectacular`.
- `django-pglock` + `django-pgtrigger` make Postgres-backed
  task-queue locking robust enough to replace Celery + Redis for
  the typical workload.

**Negative / trade-offs.**

- **Django CVE inheritance.** Every Django CVE applies (template-injection,
  SQL-injection in raw-sql edges, session-fixation if cookies are
  misconfigured, the perennial password-reset-token-validity edge
  cases). authentik's mitigation cadence depends on Django upstream
  release timing. authentik's own CVE history (per
  `prior-audit.md` and `website/docs/security/cves/`) includes
  several API-authorization gaps (e.g. CVE-2024-42490) that are
  Django-shaped — DRF view permissions, not framework bugs.
- **Postgres becomes the single point of failure.** Loss of the
  database means loss of all identity, audit, session, and
  secret-encrypted material. Per the backup-restore doc:
  "Without it, authentik cannot be restored to a usable state."
- **PostgreSQL-backed task queue load.** Heavy SCIM sync /
  notification dispatch / Source sync all write to the same
  database that serves user-facing auth flows. Per the SCIM
  provider doc, SCIM sync is per-100-objects-batched to spread
  load — but the cost still lands on PostgreSQL.
- **Redis-when-configured ambiguity.** Operators reading older
  documentation, older blog posts, or older config samples may
  configure Redis where it is no longer required. The active
  install state is sometimes Postgres-only and sometimes
  Postgres-plus-Redis depending on operator choices. **GAP** in
  the documentation set: the "is Redis required" question is not
  crisply answered for every release.
- **Channels-layer transport on PostgreSQL.** Outpost-to-Server
  WebSocket signaling traffic ultimately rides PostgreSQL pubsub
  (LISTEN/NOTIFY) when `django-channels-postgres` is in use. A
  slow PostgreSQL impacts outpost responsiveness.
- **Multi-tenancy depends on django-tenants.** Per
  `sys-mgmt/tenancy.md`, the feature is alpha; the tenancy
  boundary leak for Expression policies ("Expression policies
  currently have access to all tenants") is a known caveat tied
  to the choice of schema-per-tenant rather than database-per-tenant.

**Invariants pinned by this ADR (intended, not all enforced).**

- All persistent state lives in PostgreSQL.
- Schema migrations are forward-only and apply via the
  `lifecycle/migrate.py` entry point (per Makefile `migrate` target).
- Worker tasks are at-least-once with the dramatiq-postgres
  semantics.
- The Server can run without Redis if the operator chooses to
  configure the Postgres-backed alternatives.

## Enforcement

- `pyproject.toml` pins all of `django`, `djangorestframework`,
  `django-channels`, `django-pglock`, `django-pgtrigger`,
  `django-tenants`, and the four workspace packages
  (`ak-guardian`, `django-channels-postgres`,
  `django-dramatiq-postgres`, `django-postgres-cache`).
- The `lifecycle/migrate.py` entry point is the canonical
  migration path; the Makefile `migrate` target invokes it.
- `psycopg[c,pool]==3.3.4` with the C extension is the canonical
  PostgreSQL driver.

## Notes

This ADR documents the *current* stack posture. The shift from
Celery+Redis to Postgres-backed queue happened over several
releases; older deployments may still be running mixed configurations.
The choice to keep Redis configurable rather than excised reflects
backwards compatibility with operator runbooks built before the
shift.
