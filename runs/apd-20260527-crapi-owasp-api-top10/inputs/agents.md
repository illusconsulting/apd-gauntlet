# crAPI — Operators

This document scopes the operator context so reviewers do not expect
production-style operational evidence.

## Who operates crAPI

crAPI is an OWASP-maintained, intentionally-vulnerable training
target. In the deployments this review is concerned with, crAPI is
operated by:

- **A single security-engineering practitioner**, running the stack on
  a laptop or a personal lab host for the purpose of API-security
  testing practice.
- **Workshop instructors**, running the stack on a small lab host
  shared across a class.

There is **no enterprise operator**. There is **no on-call rotation**.
There is **no SLO commitment** to anyone using the deployed
instance.

## Intended runtime

- **Default target:** a single host (laptop, t2.micro-class VM, or
  Vagrant guest on the operator's workstation). Per `docs/overview.md`,
  the project explicitly targets 1 vCPU / 1 GB RAM.
- **Supported deploy topologies:** Docker Compose, Helm, Kubernetes
  manifests, Vagrant.
- **Network exposure:** loopback by default (`LISTEN_IP=127.0.0.1`).
  Operator may set `LISTEN_IP=0.0.0.0` to expose to a lab network.

## Operator capabilities

The operator role here is **deploy-and-explore**, not
**administer-and-defend**:

- Bring the stack up / tear it down.
- Read Mailhog to observe OTPs and notifications.
- Inspect Postgres / Mongo directly with the shared `admin` credential.
- Optionally configure a chatbot LLM provider.

The operator is **not** expected to:

- Rotate keys or credentials.
- Configure encryption-at-rest.
- Enable audit logging.
- Configure backups or recovery.
- Respond to security incidents — the *purpose* of the deploy is
  for the operator to *cause* security incidents and study them.

## Implication for the APD review

Specialist reviewers should not produce findings that require
production operator behaviour. They should:

- Treat the absence of an operator-driven control (key rotation,
  log retention, MFA, network policy) as a structural finding
  against the artifact, not a procedural finding against the
  operator.
- Recognize that no operational-evidence artifact (paged-runbook,
  on-call schedule, SLA, incident postmortem) will exist; absence is
  the evidence.

## Related documents

- `runbook.md` — what the operator does at the keyboard.
- `prior-audit.md` — the inherited posture.
- `tech_plan.md` §10 — explicit out-of-scope items.
