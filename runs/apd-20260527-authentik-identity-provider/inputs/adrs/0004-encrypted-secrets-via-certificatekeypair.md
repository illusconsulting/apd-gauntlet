---
title: 0004 — Encrypted secrets via CertificateKeyPair + per-installation secret_key
status: accepted
date: 2020-09-15
---

# ADR-0004: Encrypted secret storage via CertificateKeyPair model

- **Status:** Accepted
- **Date:** 2020-09-15 (approximate; first releases)

## Context

authentik holds a substantial volume of secret material:

- **Per-Provider signing private keys.** Each OAuth/OIDC Provider
  with a Signing Key configured holds an RSA or ECDSA private key
  used to sign issued JWTs. Each SAML Provider holds a signing
  key for assertion signatures, optionally an encryption key for
  assertion encryption. Each Provider with an SP-side verification
  certificate holds the SP public key as well.
- **OAuth client secrets.** Per Provider, the symmetric client
  secret used by the RP when authenticating to the token endpoint.
  Also the fallback-signing key when no Signing Key is configured
  (see threat-model S-3).
- **Source credentials.** Per Source, the credentials used by
  authentik to authenticate to the upstream IdP (OAuth client_secret
  for OAuth Sources, LDAP bind credentials for LDAP Sources, etc.).
- **SCIM target authentication.** Static tokens (default) or OAuth
  client secrets for the outbound provisioning targets.
- **Outpost service-account tokens.** Per outpost, the token used
  by the outpost to authenticate to the Server.
- **API tokens, app passwords, recovery tokens, verification
  tokens.** Per User or per service account.
- **TLS certificates and private keys** used by outposts (LDAPS),
  by the Server (HTTPS), and by the SAML / OAuth signing /
  encryption paths.

This material lives in PostgreSQL. PostgreSQL itself can be
configured with TLS for in-transit protection but does not by
default encrypt rows at rest. authentik therefore needs an
application-layer encryption scheme for secret-bearing fields,
keyed by something operator-controlled.

## Decision

Store all secret-bearing material in PostgreSQL via the
`authentik.crypto.models.CertificateKeyPair` model and analogous
secret-bearing fields elsewhere in the schema (e.g. Provider
`client_secret`, Source credential fields, Token `key`). Encrypt
the secret fields symmetrically using a per-installation key
derived from `AUTHENTIK_SECRET_KEY`.

Per the docker-compose install doc, `AUTHENTIK_SECRET_KEY` is
generated at install time:

```shell
echo "AUTHENTIK_SECRET_KEY=$(openssl rand -base64 60 | tr -d '\n')" >> .env
```

The key lives in the `.env` file (operator-managed) and is loaded
into the Server and Worker process environments at startup. It is
not stored in PostgreSQL.

The CertificateKeyPair model carries the certificate's public
parts (DER + PEM serialization, fingerprint, expiry, subject) plus
the encrypted private key. Per `sys-mgmt/certificates.md`,
authentik generates a self-signed `authentik Self-signed
Certificate` (1-year validity) at first startup, used as the
default for OAuth/OIDC Providers.

Per `pyproject.toml`, the cryptographic primitives are provided by
`cryptography==48.0.0` (Fernet-style symmetric AEAD) and
`jwcrypto==1.5.7` (JWS/JWE for JWT signing/encryption). XML signing
is via `xmlsec==1.3.17`.

## Consequences

**Positive.**

- Database backups are not directly exploitable without the
  `AUTHENTIK_SECRET_KEY`. An attacker stealing a `pg_dump` file
  cannot decrypt the signing keys, the client secrets, or the
  API tokens without also stealing the secret_key.
- The certificate-management surface is unified. Per the
  certificates doc, all certificate-using purposes (SAML signing,
  OAuth/OIDC JWT signing, LDAPS, Docker integration TLS) reach
  for the same `CertificateKeyPair` records.
- Operators get a per-Provider isolation story: compromise of one
  Provider's signing key does not affect another Provider's
  signing key, as each is stored separately and each is
  individually rotatable.
- Blueprints can express certificate-rotation declaratively
  (per the blueprints doc); operators can drive rotation via
  configuration-as-code.

**Negative / trade-offs.**

- **`AUTHENTIK_SECRET_KEY` is the master decryption key.** Anyone
  with secret_key + database snapshot can unmask every stored
  secret. The Server's process environment is the canonical
  location for secret_key, so anything that reads Server-process
  env (host compromise, container escape, an expression-engine
  read of `os.environ` per ADR-0001, a sidecar with shared env)
  recovers it.
- **No external secret-manager integration in Core.** SOPS, HashiCorp
  Vault, AWS KMS, GCP KMS — none of these are first-class in the
  community surface. Operators wanting external secret management
  must wrap the secret_key delivery to the Server process (e.g.
  Kubernetes Secret + KMS-encrypted at the etcd layer) but the
  application-layer encryption still uses the in-process secret_key.
  **GAP** in the inputs: no documented procedure ships for binding
  authentik to an external KMS for the per-field encryption.
- **Rotation of `AUTHENTIK_SECRET_KEY` requires re-encrypting
  every secret-bearing field.** The blueprint mechanism supports
  this (per the blueprints doc), but the operational impact is
  non-trivial: every Provider's secret is re-keyed in a single
  transaction. **GAP** in the inputs: the rotation runbook for
  secret_key is not documented in `sys-mgmt/`; reviewers should
  surface this as a finding against operational discipline.
- **CVE-2024-42490 demonstrates the API-exposure risk.** Pre-patch,
  `/api/v3/crypto/certificatekeypairs/<uuid>/view_certificate/` and
  `/view_private_key/` were accessible without correct
  authorization. Anyone who knew the UUID could download the
  private key. The fix shipped in 2024.4.4 / 2024.6.4 / 2024.8.0
  per `prior-audit.md`. The lesson: any API surface that exposes
  the CertificateKeyPair plaintext bypasses the entire
  secret_key-based encryption story.
- **The on-disk certificates under `/certs`** (operator-imported)
  do not benefit from this scheme. Per the certificates doc and
  `core/architecture.md`, `/certs` is for operator-imported certs
  that authentik may then load into the database; the on-disk copy
  is the operator's responsibility.

**Invariants pinned by this ADR (intended, not all enforced).**

- All secret-bearing model fields are encrypted at rest using a
  key derived from `AUTHENTIK_SECRET_KEY`.
- The secret_key is process-env-resident, not in PostgreSQL.
- Per-Provider signing keys are isolated; compromise of one does
  not affect others.
- Certificate rotation is operator-initiated; the platform
  supports it but does not enforce a cadence.

## Enforcement

- The `authentik.crypto` app is the canonical certificate /
  secret-bearing-field manager (per `pyproject.toml` mypy override
  list).
- `cryptography==48.0.0` provides the AEAD primitives.
- `jwcrypto==1.5.7` provides JWT signing/encryption per the
  per-Provider Signing Key and Encryption Key fields.
- The docker-compose install doc explicitly directs the operator
  to generate `AUTHENTIK_SECRET_KEY` with `openssl rand -base64 60`
  at install time.

## Notes

The decision to keep the master key in process env (rather than in
a separate process boundary or external KMS) is a pragmatic
operational choice — it makes the install single-process and the
backup story Postgres-only. The trade-off is that the security of
all stored secrets reduces to the security of the Server process's
environment.

Per `SECURITY.md`, the Expression engine has arbitrary Python — so
in any installation where Expression policies can be edited, the
secret_key is effectively reachable by anyone who can author an
Expression. This is why `security/security-hardening.md`
recommends blocking the Expression / PropertyMapping / Blueprint
write APIs at the reverse proxy: it transitively protects the
secret_key by removing the in-platform code-execution paths.
