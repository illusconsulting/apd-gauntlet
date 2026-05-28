# Architectural Decision Records — crAPI

Each ADR captures a single architectural decision that crAPI's
codebase reflects: context (the constraint that forced the choice),
decision (what was chosen), and consequences (the resulting
security-relevant trade-offs).

The four ADRs below are reconstructed from the shipped artifacts
(`docs/`, `deploy/docker/docker-compose.yml`, the per-service
`Dockerfile` / `entrypoint.sh`); they are not the upstream OWASP
maintainers' words, but they reflect what the code commits to.

| #    | Title                                       | Status   |
|------|---------------------------------------------|----------|
| [0001](./0001-microservice-split-by-language.md) | Microservice split by host language | Accepted |
| [0002](./0002-jwt-with-rsa-and-jwks.md)          | RS256 JWT minted by identity, verified via JWKS | Accepted |
| [0003](./0003-mailhog-for-otp-delivery.md)       | Mailhog as the OTP / notification delivery target | Accepted |
| [0004](./0004-dual-datastore-postgres-and-mongo.md) | Dual datastores: Postgres for OLTP, Mongo for community content | Accepted |
