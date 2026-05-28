# authentik — Operator Runbook

This runbook captures what an operator needs to bring authentik up,
keep it healthy, and respond to common incident-shaped events.
authentik's own documentation is rich for normal operations; where
the inputs explicitly cover a procedure, that is noted. Entries
marked **GAP** have no documented procedure in the input set;
specialist reviewers should treat each as a candidate finding
against operational discipline.

## 1. Bring the stack up

### Docker Compose (canonical for small/test deployments)

Per `install-config/install/docker-compose.mdx`:

```shell
wget https://docs.goauthentik.io/compose.yml
echo "PG_PASS=$(openssl rand -base64 36 | tr -d '\n')" >> .env
echo "AUTHENTIK_SECRET_KEY=$(openssl rand -base64 60 | tr -d '\n')" >> .env
echo "AUTHENTIK_ERROR_REPORTING__ENABLED=true" >> .env
docker compose pull
docker compose up -d
```

Visit `http://<host>:9000`. Set the `akadmin` initial password
when prompted.

### Kubernetes (canonical for production)

Per `install-config/install/kubernetes.md`, use the upstream Helm
chart at `https://github.com/goauthentik/helm`:

```shell
helm repo add authentik https://charts.goauthentik.io
helm install authentik authentik/authentik -f values.yaml
```

The Helm values cover the Server replicas, Worker replicas,
PostgreSQL subchart, Redis subchart (if used), ingress, and TLS.

### AWS / DigitalOcean

Per `install-config/install/aws.md`, an official AWS CloudFormation
template is published. DigitalOcean Marketplace offers a one-click
deploy. Both wire `AUTHENTIK_SECRET_KEY` generation at install
time.

## 2. Initial admin Flow

On first visit to `http://<host>:9000`, the user is taken through
the initial-setup Flow which prompts for the `akadmin` password.
After that, the operator should:

1. Sign in as `akadmin`.
2. Open `/if/admin/#/core/users` and create a per-operator User
   record with a personal email; bind to the `authentik Admins`
   group.
3. Sign out and sign back in as the personal admin User.
4. Optionally disable the `akadmin` user (Account Lockdown or
   simple deactivation) so that the shared-credential user is no
   longer reachable.

## 3. Health checks

The Server exposes:

- `GET /-/health/live/` — liveness probe.
- `GET /-/health/ready/` — readiness probe (checks DB connectivity).
- `GET /-/metrics/` — Prometheus metrics (Server).
- `:9300/metrics` — Prometheus metrics per outpost (unauthenticated;
  per the outpost doc not for public exposure).

To probe manually:

| Component | Health endpoint |
|-----------|-----------------|
| Server | `curl -sf http://<host>:9000/-/health/ready/` |
| Worker | inspect `Dashboards > System Tasks` in the Admin UI |
| Postgres | `pg_isready -h <host>` |
| Outposts | `Dashboards > System Tasks` shows outpost connection state via WebSocket |

## 4. Audit log inspection and forwarding

Per `sys-mgmt/events/index.md`:

- Default retention: **365 days** (configurable in
  `System > Settings`).
- Forwarding posture: container stdout. The doc recommends "If
  you want to forward these events to another application, forward
  the log output of all authentik containers. Every event creation
  is logged with the log level info" and combining this with a
  shortened internal retention (`days=1`).

To wire log forwarding, the operator deploys a log shipper
(Fluent Bit, Filebeat, Vector, Promtail) collecting Server and
Worker stdout, ships to the operator's SIEM, applies the SIEM's
event-parsing rules.

**GAP** — the inputs do not enumerate a canonical SIEM-side parser
for authentik Event JSON. Operators must read the Event schema
(visible via `GET /api/v3/events/events/`) and write their own.

## 5. AUTHENTIK_SECRET_KEY rotation

**GAP.** No rotation runbook for `AUTHENTIK_SECRET_KEY` ships in
`sys-mgmt/`. Per ADR-0004, the secret_key is the master decryption
key for every encrypted secret field; rotation requires re-keying
every secret-bearing record.

What an operator would need to do (reconstructed from the
blueprint and crypto documentation):

1. Generate a new secret_key with `openssl rand -base64 60`.
2. Hold both old and new keys simultaneously for the duration of
   the re-key.
3. For each secret-bearing model field (Provider client_secret,
   Source credential, Token key, CertificateKeyPair private_key),
   decrypt with the old key and re-encrypt with the new key.
4. Swap the Server process environment to the new key.
5. Restart Server and Worker processes.

This is a non-trivial procedure not documented in the input set —
surface as a finding against operational discipline.

## 6. Provider signing-key rotation

Per `sys-mgmt/certificates.md`, certificates are rotatable per
Provider. To rotate an OAuth/SAML Provider's signing key:

1. Open `/if/admin/#/crypto/certificates`.
2. Generate a new `CertificateKeyPair` (or import).
3. Edit the affected Provider; switch the **Signing Key** field to
   the new certificate.
4. For OAuth providers, the JWKS endpoint at
   `/application/o/<slug>/jwks/` automatically reflects the new
   key. RPs that fetch the JWKS will pick up the new key on next
   refresh.
5. For SAML providers, re-export the IdP metadata
   (`/application/saml/<slug>/metadata/`) and re-import it at the
   SP. Notify SPs in advance; SAML SPs typically pin certificates
   manually.
6. Verify the cutover by inspecting Events for token issuance
   under the new key.

The platform does not enforce a rotation cadence.
**GAP** — there is no shipped alerting rule for "Provider signing
key approaching expiry"; operators must configure their own via
Event Matcher policies.

## 7. Outpost certificate / token rotation

Per the outpost doc, outpost service-account tokens are
auto-generated at outpost creation. Token rotation:

1. Open `/if/admin/#/outpost/outposts`.
2. Edit the outpost. **GAP** — the inputs do not enumerate a
   rotation control on the outpost edit form. Reviewers should
   confirm against the live admin UI whether the operator can
   regenerate the service-account token without recreating the
   outpost. If not, the rotation procedure is to recreate the
   outpost (re-deploy outpost containers with the new token), which
   is a brief outage.

LDAPS / RAC TLS certificates on outposts:

1. Generate or import a new CertificateKeyPair as in §6.
2. Edit the Provider; switch the **Certificate** field.
3. Restart the outpost so it re-fetches configuration.

## 8. Backup and restore

Per `sys-mgmt/ops/backup-restore.md`:

**PostgreSQL** is the critical-path backup target. Documented
tools:

- `pg_dump` for single-database dump.
- `pg_dumpall` for cluster-level dump.
- Continuous archiving for PITR.

Restore via `pg_restore` or `psql` per how the backup was created.

**Static directories** to back up alongside the database:

| Directory | Purpose |
|-----------|---------|
| `/data` | Uploaded files (icons, flow backgrounds, CSV reports). Skip if using S3 external storage. |
| `/certs` | Filesystem-imported TLS certificates. Skip if all certs are in PostgreSQL. |
| `/custom-templates` | Operator-customized UI templates. |
| `/blueprints` | Filesystem blueprints. |

**GAP** — the backup-restore doc does not describe encryption of
the dump file. Per ADR-0004, the dump contains encrypted secret
material; the encryption is keyed by the secret_key. Off-site dump
storage should be additionally encrypted with operator-controlled
keys, but the procedure for that is operator-driven and not in the
input set.

**GAP** — the secret_key itself is operator-managed in `.env` /
Kubernetes Secret / equivalent. The backup procedure for
secret_key is operator-defined. A dump without the secret_key is
useless; a dump with the secret_key is total compromise.

## 9. Multi-tenant isolation (Brands feature)

Per `sys-mgmt/brands/index.md`, Brands map domains to default-Flow
configuration. Brand isolation is a soft boundary (different
landing experience, different default flows) — not a hard
data-isolation boundary. For real per-tenant data isolation, the
alpha Tenancy feature (per `sys-mgmt/tenancy.md`) uses
schema-per-tenant PostgreSQL via `django-tenants`.

**GAP** — per the tenancy doc: "This feature is in alpha. Use at
your own risk." and "Expression policies currently have access to
all tenants." Reviewers should treat Tenancy as not-yet-production
for hard-isolation requirements.

## 10. Production hardening checklist

Per `security/security-hardening.md`:

- [ ] Set a strong Password policy (minimum length ≥ 15, enable
      HIBP check).
- [ ] Block `/api/v3/policies/expression*`,
      `/api/v3/propertymappings*`, `/api/v3/managed/blueprints*`,
      `/api/v3/stages/captcha*` at the reverse proxy. Force changes
      through filesystem blueprints in `/blueprints/`.
- [ ] Set Content Security Policy headers at the reverse proxy
      (authentik does not natively set CSP).
- [ ] Front authentik with a reverse proxy that terminates TLS,
      sets sensible timeouts, and optionally provides WAF.
- [ ] Configure global email and verify Mailhog-style throwaway
      domains are not in the mail path.
- [ ] Configure MFA enforcement on the default-authentication-flow
      for admin Groups; consider a separate flow for non-admin
      users with relaxed MFA.
- [ ] Configure session inactivity timeout and absolute timeout per
      the User Login stage settings.
- [ ] Configure the GeoIP policy if location-based gating is
      relevant.
- [ ] Configure log forwarding to a SIEM; reduce internal Event
      retention to a short window if the SIEM is the source of
      truth.
- [ ] Disable Docker socket mount if the Docker integration is not
      needed; otherwise use a Docker Socket Proxy per
      `install-config/install/docker-compose.mdx`.
- [ ] Restrict outbound network egress from the Server and Worker
      to known Source IdP destinations and SCIM target endpoints
      (per `SECURITY.md`: "Outgoing network requests are not
      filtered… these requests should be restricted at the network
      level").
- [ ] Do not expose outpost `:9300/metrics` to the internet.

## 11. WebAuthn enrollment recovery (lost-authenticator workflow)

A user has lost their only WebAuthn authenticator and cannot log
in. The operator workflow:

1. Verify the user's identity out-of-band (organisationally-defined
   process).
2. Open `/if/admin/#/core/users` and click the user.
3. Open the **Authenticators** tab.
4. Remove the lost authenticator device(s).
5. Issue a recovery link via `Create Recovery Link` so the user can
   re-enroll a new authenticator on first login.

**GAP** — the inputs do not describe an automated self-service
"lost device" flow. The Account Lockdown stage is for
disabling accounts, not for recovering them.

## 12. Account compromise response (Lockdown)

Per `security/account-lockdown.md` (Enterprise, 2025.5+):

1. Open `/if/admin/#/core/users` and click the user.
2. Click **Account Lockdown**.
3. Enter a reason; click **Continue**.

This single action deactivates the user, sets an unusable
password, terminates all active sessions, revokes all API /
app-password / recovery / verification / OAuth2 tokens, and
creates an audit Event.

For Community-tier installs without the Lockdown stage, the
equivalent manual procedure is:

1. Edit the user; set Inactive.
2. Use the Set Password control to set an unusable password.
3. Navigate to the user's Sessions tab and revoke each session.
4. Navigate to the user's Tokens tab and revoke each token.
5. Create an Event manually (or rely on the model-write events for
   each of the above actions).

The manual procedure is multi-step and racy; the Enterprise
Lockdown stage is single-action and atomic.

## 13. CVE response and patch cadence

Per `SECURITY.md`:

- Supported tracks: **2025.2.x** and **2026.5.x** (current at
  time of writing per the `SECURITY.md` table).
- Security advisories are published per CVE under
  `website/docs/security/cves/` with patch versions.
- Subscribe to `authentik-security-announcements@googlegroups.com`
  or the Discord for advisories.

Operator action on a CVE:

1. Check the affected versions in the advisory.
2. Apply the patch release (per `install-config/upgrade.mdx`).
3. For Docker Compose: download a new `compose.yml`, `docker
   compose pull`, `docker compose up -d`.
4. For Kubernetes: `helm upgrade` with the new chart version.
5. Verify post-upgrade per the Events log and per the
   per-component health endpoints in §3.

## 14. Tear down

Docker Compose:

```shell
docker compose down -v
```

The `-v` flag wipes the named volumes (PostgreSQL data, Redis
data, uploaded media). Without it, restart preserves all
configuration and identity state.

Kubernetes:

```shell
helm uninstall authentik
kubectl delete pvc -l app.kubernetes.io/name=authentik
```

PVC deletion is separate; without it the PostgreSQL data persists
for reinstall.
