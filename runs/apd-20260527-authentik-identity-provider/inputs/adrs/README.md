# Architectural Decision Records — authentik

Each ADR captures a single architectural decision that authentik's
codebase reflects: context (the constraint that forced the choice),
decision (what was chosen), and consequences (the resulting
security-relevant trade-offs).

The four ADRs below are reconstructed from the shipped artifacts
(`website/docs/`, `pyproject.toml`, `go.mod`, `Makefile`, and the
on-disk app structure visible via the mypy override list in
`pyproject.toml`). They are not the upstream authentik maintainers'
words verbatim — but they reflect what the code and the public docs
commit to.

| #    | Title                                       | Status   |
|------|---------------------------------------------|----------|
| [0001](./0001-flows-stages-policies-pipeline.md) | Configurable authentication via Flow + Stage + Policy + Python expressions | Accepted |
| [0002](./0002-django-celery-redis-postgresql-stack.md) | Django + Postgres-backed queue + optional Redis for the core | Accepted |
| [0003](./0003-outpost-architecture-for-protocol-handlers.md) | Separate Go-based outposts for legacy protocol handlers | Accepted |
| [0004](./0004-encrypted-secrets-via-certificatekeypair.md) | Encrypted secrets in Postgres via CertificateKeyPair + per-installation secret_key | Accepted |
