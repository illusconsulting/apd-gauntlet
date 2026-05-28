---
title: 0001 — Asyncio single-process server hosting REST, UI, and agent listeners
status: accepted
date: 2018-10-01
---

# ADR-0001: Asyncio single-process server hosting REST, UI, and agent listeners

- **Status:** Accepted
- **Date:** 2018-10-01

## Context

Caldera is a research / adversary-emulation framework intended to
run on a single host owned by a red-team or detection-engineering
operator. The audience is small (single operator or a small team),
the deploy target is unprivileged (laptop, VM, container), and the
operational surface area must stay tractable for a single
maintainer team. A multi-process or distributed-services
architecture (separate processes for REST, agent listeners, planner,
plugin host) would buy isolation but at the cost of operator
complexity and deployment dependencies.

Per the README, Caldera "highly recommends" deployment on a
"secure environment/network, and not exposing it to the internet".
The expectation is that the entire platform lives in a trust zone
that the operator already controls; defence-in-depth between
in-process components is therefore a low priority.

## Decision

Run Caldera as a **single asyncio Python process** built on
aiohttp. The single `web.Application` hosts:

- The legacy `/api/rest/*` REST surface (`app/api/rest_api.py`).
- The modern `/api/v2/*` REST subapp (`app/api/v2/`).
- The operator HTML / Vue UI (Jinja templates for legacy console;
  `plugins/magma/dist` for v5).
- Every agent contact listener (`app/contacts/contact_*.py`) —
  `POST /beacon` on the same port as the operator API, plus the
  per-protocol sockets on dedicated ports (DNS `:8853/udp`, FTP
  `:2222`, TCP `:7010`, UDP `:7011/udp`, websocket `:7012`, SSH
  `:8022`).
- The planner, the parser execution path, the ability-file
  watcher, the operation scheduler, the untrusted-agent sniffer,
  the learning model.
- Every loaded plugin's `enable()` method and any routes the
  plugin registers.

All of these share the same event loop, the same Python process,
the same filesystem permissions, the same network egress.

## Consequences

**Positive.**

- One process to start, one process to stop, one process to
  monitor. Operator complexity stays low.
- No IPC overhead between components — the planner can hold
  references to the in-memory object store directly.
- Plugin-contributed UI panels, abilities, and routes attach to
  the same `Application` instance without cross-process
  coordination.

**Negative / trade-offs.**

- **No isolation between operator traffic, agent traffic, and
  plugin code.** A bug or compromise in any component reaches
  every other component. A blocking call in a plugin's
  request handler stalls the agent listener; a memory leak in
  the planner takes the operator UI down with it.
- **Same TCP listener for operator REST and agent beacon.**
  `:8888` carries both the operator console (cookie-auth or
  API-key) and the `POST /beacon` endpoint (no operator auth).
  Network filtering that would otherwise separate operator and
  agent traffic must be applied off-host.
- **Plugin compromise = full server compromise.** See ADR-0002.
- **Single point of failure for the platform.** Restart loses
  in-memory state (knowledge facts, in-flight planner decisions)
  unless the periodic `save_state` ran in time.
- **No horizontal scaling.** Vertical scaling only (more
  RAM / CPU on the single host). The asyncio loop is one OS
  thread; CPU-bound operations (the `learning_svc` model
  build, the `debrief` PDF rendering) block the loop unless
  the plugin explicitly offloads.

**Invariants pinned by this ADR (intended, not all enforced).**

- The server runs as a single OS process.
- Every component shares one `BaseWorld` config namespace and
  one `aiohttp.web.Application` instance.
- Plugin code executes in the same Python interpreter as core
  services.

## Enforcement

- `server.py` constructs a single `web.Application` and a
  single asyncio loop.
- `--build` and `--uidev` may spawn child processes (`npm run
  build`, `npm run dev`), but only at startup; the server
  itself remains single-process.

## Notes

A future "distributed Caldera" topology (separate operator-API
process, separate agent-listener process, separate planner
worker) would address the WP-* findings in the threat model,
but would invert the deployment-simplicity property the project
explicitly values. This ADR documents the chosen trade-off.
