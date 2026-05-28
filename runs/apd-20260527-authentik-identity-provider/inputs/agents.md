# authentik — Operators

This document scopes the operator context so reviewers can calibrate
their expectations of operational evidence.

## Who operates authentik

authentik is operated by **enterprise IT or platform-engineering
teams** that have made authentik the identity authority for an
organisation. Typical operator shapes:

- **Self-hosted on-prem.** Platform-engineering team running the
  Server + Worker + PostgreSQL + outposts in the org's own
  Kubernetes or Docker infrastructure. Most production deployments
  fall here.
- **Self-hosted in a public-cloud account.** Same shape, deployed
  to EKS / GKE / AKS or to an EC2/Compute-Engine VM via the
  documented CloudFormation / DigitalOcean templates.
- **authentik Security hosted offering.** Operated by the upstream
  vendor on the customer's behalf (per the upstream
  `https://goauthentik.io/pricing` enterprise offering).

There is **not** typically a "single hobbyist on a laptop" operator
in production — authentik is the identity authority, so an outage
means a total auth outage for every downstream Application.
Laboratory / homelab operators exist (and authentik supports
that posture per the Docker Compose install guide), but the
threat-model framing in `threat-model.md` assumes the
production-grade operator.

## Operator characteristics

- **High-availability expectations.** Production deployments run
  multiple Server replicas behind a load balancer; multiple Worker
  replicas; PostgreSQL with replication or managed-Postgres (RDS,
  Cloud SQL); outposts deployed redundantly per protocol.
- **On-call discipline.** Authentication outages cascade — every
  downstream Application that uses authentik for SSO breaks at the
  same moment. Production operators have a paging policy with the
  IdP as a top-tier dependency.
- **Customer-data sensitivity: high.** authentik holds:
  - User PII (name, email, phone, optional profile fields).
  - Authenticator factors (FIDO2 credentials, TOTP secrets, etc.).
  - Federated-identity attribute sets (from Sources).
  - Consent records (relevant to GDPR Article 7).
  - Audit trail of authentication / authorization events
    (relevant to SOC 2, ISO 27001, HITRUST audit scope).
- **Compliance posture.** Many authentik operators are subject to
  SOC 2 / ISO 27001 audits where authentik is the SSO control. The
  per-Brand audit event stream, the Account Lockdown stage, and
  the Source-attribute mapping discipline all map to compliance
  evidence requirements.

## Operator capabilities

The operator role is **administer-and-defend**:

- Bring the platform up and keep it healthy across upgrade cycles.
- Configure Flows / Stages / Policies for organizational
  requirements.
- Configure Providers (OAuth/SAML/LDAP/Proxy/RAC) for each
  downstream Application.
- Configure Sources for upstream federation (corporate IdP, social
  logins).
- Configure SCIM provisioning for outbound user-state push.
- Rotate certificates and secrets.
- Forward Events to the operator's SIEM.
- Respond to security incidents (suspicious-login alerts, lost
  authenticator workflows, account compromise via Account
  Lockdown).
- Audit Flow / Stage / Policy changes (the platform's own
  configuration is identity-critical).

The operator is **expected** to:

- Front authentik with a TLS-terminating reverse proxy.
- Configure native CSP at the reverse proxy.
- Apply the API-endpoint blocklist for the Expression /
  PropertyMapping / Blueprint write paths if the hardened posture
  is desired.
- Configure log forwarding to a SIEM.
- Configure backups of PostgreSQL with off-site retention and
  encryption.
- Rotate `AUTHENTIK_SECRET_KEY` on a documented cadence (which
  the platform does not document — see `runbook.md` §5 GAP).
- Enforce MFA on the default-authentication-flow for admin Groups.
- Apply network-level egress controls to constrain outbound calls
  from Server and Worker (per the `SECURITY.md` "Outgoing network
  requests are not filtered" note).

## Implication for the APD review

Specialist reviewers should:

- Treat the absence of operator-applied hardening (CSP, API
  blocklist, log forwarding, secret_key rotation, MFA enforcement
  on admin Flows) as structural risk against the deployment
  posture, not as a defect in the artifact.
- Recognise that authentik provides the primitives (Reputation
  policy, GeoIP policy, Notification Rules, per-Brand flow
  defaults, Account Lockdown stage) but does not ship every
  recommended binding out of the box.
- Treat operational-evidence artifacts (incident-response runbooks,
  on-call schedules, SLA commitments, backup-restore test results)
  as operator-provided; the upstream project ships the platform,
  not the operator's runbook.

## Related documents

- `runbook.md` — what the operator does at the keyboard.
- `prior-audit.md` — the inherited posture from external audits
  and the CVE archive.
- `tech_plan.md` §12 — explicit out-of-scope items.
