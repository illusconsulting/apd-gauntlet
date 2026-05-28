# crAPI — Operator Runbook

This runbook captures what an operator would need to bring crAPI up,
keep it healthy, and respond to common incident-shaped events. Because
crAPI is an educational target, the runbook deliberately surfaces the
gaps in the project's operational story — entries marked **GAP** have
no documented procedure in the source set; specialist reviewers should
treat each as a candidate finding.

## 1. Bring the stack up

### Docker Compose (canonical)

```sh
cd deploy/docker
docker compose pull
docker compose -f docker-compose.yml --compatibility up -d
```

Visit `http://localhost:8888`. Mailhog (OTP catcher) is on
`http://localhost:8025`.

To expose on all interfaces (e.g. on a remote lab host):

```sh
LISTEN_IP=0.0.0.0 docker compose -f docker-compose.yml --compatibility up -d
```

### Helm

```sh
cd deploy/helm
helm install --namespace crapi crapi . --values values.yaml
```

For persistent volumes, use `values-pv.yaml`.

### Vagrant

```sh
cd deploy/vagrant && vagrant up
```

VM exposes the stack on `192.168.33.20:80` and Mailhog on
`192.168.33.20:8025`.

## 2. Health checks

Each service ships a `health.sh` invoked by the compose `healthcheck:`
block. To probe manually from the host:

| Service     | Health endpoint                                          |
|-------------|----------------------------------------------------------|
| identity    | `curl -sk http://localhost:8888/identity/health_check`   |
| workshop    | `curl -sk http://localhost:8888/workshop/health_check/`  |
| community   | `curl -sk http://localhost:8888/community/home`          |
| chatbot     | container internal; no documented external health endpoint |
| postgresdb  | `pg_isready -h localhost -p 5432 -U admin` (when port exposed) |
| mongodb     | `mongosh --eval 'db.runCommand({ping:1})'`               |
| mailhog     | `curl -sf http://localhost:8025/api/v2/messages \| head` |

Compose-level health: `docker compose ps`. A `(unhealthy)` row is the
signal — see the per-service `health.sh` and `entrypoint.sh` for the
underlying check.

## 3. Inspect captured email (OTPs, password-reset)

Mailhog catches every message sent to the `example.com` domain (or any
domain when `SMTP_HOST` is unset). Browse `http://localhost:8025` to
read. Programmatic access:

```sh
curl -s http://localhost:8025/api/v2/messages | jq '.items[].Content.Body'
```

## 4. Extract the OpenAPI spec

For compliance / inventory review:

```sh
curl -sk http://localhost:8888/workshop/openapi-spec/ -o crapi-openapi.json
```

This is the same artifact as `openapi-spec/crapi-openapi-spec.json` in
the repo (used by the chatbot for RAG retrieval at boot).

## 5. Rotate the JWT signing key

**GAP.** No documented procedure ships in the input set.

What an operator would need to do:

1. Generate a new RSA key pair.
2. Render a JWKS containing the new public key.
3. Drop the file into `deploy/<topology>/keys/jwks.json`.
4. Restart `crapi-identity` so it reloads.
5. Decide on the cutover policy for tokens minted under the old key
   (revoke immediately → all sessions invalidated; or grace period →
   need a JTI deny-list, which the project does not implement).

Open questions the inputs do not answer:

- Does the verifier support multiple active `kid`s? (Required for a
  graceful rotation.)
- Does the JWT_SECRET also need to rotate? It is present in the
  identity env and used for one of the documented forge paths
  (challenge 15 #1).
- How is the gateway-service basic-auth credential rotated? The
  credential is not documented in compose; presumably hard-coded in
  the binary.

## 6. Rotate datastore credentials

**GAP.** The Postgres and Mongo passwords (`crapisecretpassword`) are
hardcoded in `deploy/docker/docker-compose.yml`. The Helm values may
override, but no rotation script is provided.

What an operator would need to do:

1. Connect to each datastore as `admin` and `ALTER USER` (Postgres) /
   `db.changeUserPassword` (Mongo).
2. Update the relevant env vars in every consuming service.
3. Restart every consuming service.

The single shared `admin` credential means **every** service has to
restart simultaneously to avoid a window of broken connectivity.

## 7. Rotate the chatbot's embedded credentials

**GAP.** The chatbot container holds:

- `API_USER=admin@example.com / API_PASSWORD=Admin!123` — the crAPI
  identity-service credential the chatbot impersonates when acting on
  user prompts.
- Provider-specific LLM credentials (`CHATBOT_OPENAI_API_KEY`,
  `ANTHROPIC_API_KEY`, `AZURE_OPENAI_API_KEY`, `GROQ_API_KEY`, etc.).
- AWS / Azure / GCP credentials when using the corresponding LLM
  provider.

No rotation procedure ships. Compromise of any of these is silent —
there is no audit trail that distinguishes legitimate chatbot calls
from prompt-injection-driven calls (see threat-model R-3).

## 8. Inspect audit data

**GAP.** No application-level audit log is shipped. Containers emit
to stdout at `LOG_LEVEL=INFO`; aggregation is operator-provided.

What an operator would need:

- A log shipper (Fluent Bit, Filebeat) collecting per-container stdout.
- A retention policy.
- A schema for what counts as an audit event (currently none — see
  threat-model R-1, R-3).
- Tamper-evidence on stored logs (currently none).

## 9. Respond to a "balance went wrong" report

If a user reports an unexpected `credit` balance:

1. Inspect Postgres directly:
   ```sh
   docker compose exec postgresdb psql -U admin -d crapi \
     -c "SELECT * FROM credit WHERE user_email='<email>'"
   ```
2. Inspect the user's order history:
   ```sql
   SELECT id, product, quantity, total, status, created_at
     FROM orders WHERE user_email='<email>' ORDER BY created_at DESC;
   ```
3. **Expect** to find a row with negative `quantity` — this is the
   challenge 8/9 mass-assignment exploit. crAPI does not constrain
   `quantity >= 1` server-side.

There is no rollback procedure beyond manual `UPDATE`. There is no
ledger to reconstruct the intended state.

## 10. Respond to "user reports their account was taken over"

Probable cause: one of the JWT forgery vectors (challenge 15) or the
OTP brute-force (challenge 3). Steps:

1. **Cannot invalidate the attacker's session.** No JTI revocation
   list. The attacker's bearer JWT remains valid until its 7-day
   expiry.
2. Force the user to reset their password — this changes the
   stored credential but does not invalidate outstanding tokens.
3. Inspect the identity Postgres for recent `password_reset` events;
   correlate against the Mailhog inbox for the OTP-delivery records.
4. There is no source IP / user-agent in the audit trail (no audit
   trail exists; see runbook §8).

## 11. Tear down

```sh
cd deploy/docker
docker compose -f docker-compose.yml --compatibility down -v
```

The `-v` flag wipes the named volumes (Postgres data, Mongo data,
ChromaDB embeddings). Without it, restart preserves accounts and
orders.

For Vagrant: `cd deploy/vagrant && vagrant destroy`.

## 12. Troubleshooting reference

The upstream `docs/troubleshooting.md` covers common compose-startup
issues (port conflicts, docker-compose version mismatch). For
in-depth issues, the operator is referred to the upstream
GitHub Issues; no internal escalation path is defined.
