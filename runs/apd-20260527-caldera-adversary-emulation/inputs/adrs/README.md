# Architectural Decision Records — MITRE Caldera

Each ADR captures a single architectural decision that Caldera's
codebase reflects: context (the constraint that forced the choice),
decision (what was chosen), and consequences (the resulting
security-relevant trade-offs).

The four ADRs below are reconstructed from the shipped artifacts
(`server.py`, `app/service/*`, `conf/`, `plugins/`, `Dockerfile`,
`docker-compose.yml`); they are not the upstream MITRE Caldera
maintainers' words, but they reflect what the codebase commits to.

| #    | Title                                       | Status   |
|------|---------------------------------------------|----------|
| [0001](./0001-asyncio-single-process-server.md) | Asyncio single-process server hosting REST, UI, and agent listeners | Accepted |
| [0002](./0002-plugin-runtime-without-signature-verification.md) | Plugins loaded as in-process Python modules without signature verification | Accepted |
| [0003](./0003-agent-callback-encryption-by-protocol.md) | Per-contact agent callback authentication; no platform-wide enforced contract | Accepted |
| [0004](./0004-operator-console-basic-auth-default.md) | Operator console basic-auth + static API key default; hardening is operator responsibility | Accepted |
