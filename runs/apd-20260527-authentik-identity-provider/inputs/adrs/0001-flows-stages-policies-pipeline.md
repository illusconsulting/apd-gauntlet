---
title: 0001 — Configurable authentication via Flow + Stage + Policy + Python expressions
status: accepted
date: 2020-09-01
---

# ADR-0001: Flow + Stage + Policy pipeline with Python-expression Policies

- **Status:** Accepted
- **Date:** 2020-09-01 (approximate; corresponds to the first
  releases of authentik with the Flow concept)

## Context

authentik competes with commercial IdPs (Okta, Auth0, Entra ID,
Ping Identity) where the user-visible flexibility of the
authentication experience is the main differentiator. A
monolithic, fixed "username + password + optional MFA" pipeline
cannot serve the diverse requirements that real deployments hit:

- Some Flows must branch by user attribute (e.g. "show the
  hardware-token stage only for users in the `admin` group").
- Some Flows must integrate Sources mid-stream (e.g. "redirect to
  the corporate IdP if the username matches `*@corp.example.com`").
- Some Flows must enforce policy that the platform cannot
  anticipate (compliance-driven, country-specific, business-rule-driven).
- Enrollment, recovery, unenrollment, user-settings, and
  authorization flows all share the same primitives but differ in
  end goals.

A configurable pipeline of small composable steps was chosen over a
fixed pipeline with extension points, on the grounds that the
extension-point approach inevitably grows leaky abstractions as
real-world deployments push past the anticipated surface.

## Decision

Model every interactive identity journey as a **Flow** — an ordered
sequence of **Stage Bindings**, where each binding ties one **Stage**
(a single interaction or logic step) to a position in the Flow, and
each binding optionally has **Policies** that gate whether the Stage
runs at all.

The Stage taxonomy (per `website/docs/add-secure-apps/flows-stages/stages/`):

- Identification, Password, Authenticator-validate
- Authenticator-{webauthn, totp, sms, static, email, duo,
  endpoint_gdtc}
- CAPTCHA, Consent, Email, Prompt, mTLS, Invitation, Source,
  Redirect, Deny
- User-{login, logout, write, delete}
- Account Lockdown (Enterprise)

The Policy taxonomy (per `customize/policies/types/`):

- Event Matcher, Expression, GeoIP, Password, Password Expiry,
  Reputation, Password Uniqueness (Enterprise)

The Policy of greatest power is the **Expression policy** — a
Python expression evaluated server-side with access to a `request`
object, a `context` dict, and a library of helper functions
(`ak_call_policy`, `ak_is_group_member`, `ak_user_by`,
`ak_create_event`, `ak_create_jwt`, `ak_send_email`,
`regex_match`, `resolve_dns`, etc., per
`expressions/reference/_functions.mdx`).

Property Mappings (used by Sources, OAuth Providers, SAML
Providers, SCIM Providers, RAC Providers, and LDAP Providers) share
the same Python-expression environment. Prompt placeholders also
share it.

## Consequences

**Positive.**

- The user-facing pipeline is end-to-end configurable. Operators
  can author Flows that match arbitrary corporate compliance
  requirements without a code change.
- Stages and Policies are independently composable, supporting
  Flow templates (shipped as Blueprints) for common patterns
  (default-authentication-flow, default-source-enrollment-flow,
  default-invalidation-flow, default-account-lockdown — per the
  Account Lockdown doc).
- Sources, Providers, and SCIM targets all share the
  Property-Mapping mechanism, reducing the number of expression
  environments to learn.

**Negative / trade-offs.**

- **The Expression engine is documented arbitrary Python.** Per
  `SECURITY.md`: "Expressions (property mappings/policies/prompts)
  can execute arbitrary Python code without safeguards." This is
  declared intentional, with the trust boundary placed at "any
  user with permission to create or modify objects containing
  expression fields." Hardening guidance in
  `security/security-hardening.md` recommends blocking
  `/api/v3/policies/expression*`, `/api/v3/propertymappings*`, and
  `/api/v3/managed/blueprints*` at the reverse proxy for
  installations that want a stricter posture — at the cost of
  losing in-platform expression editing.
- **Admin-misconfiguration is the dominant attack surface.** A
  compromised admin or a malicious operator can rewrite the
  default-authentication-flow in a single transaction to skip the
  MFA stage for all users, or insert a Deny stage that targets a
  single user. Both are legitimate platform actions.
- **The Policy-expression engine's `ak_call_policy` allows
  recursion and chained dispatch.** Per the function reference,
  one Expression policy can invoke another with a custom request
  context. A pathological policy chain — accidental or malicious
  — exhausts the Worker pool (see threat-model D-5).
- **`ak_create_event` is opt-in.** Side-effecting helpers
  (`ak_send_email`, `ak_create_jwt`, `ak_call_policy`) do not
  auto-emit audit events; expression authors choose whether to
  call `ak_create_event` explicitly. Audit-completeness becomes a
  code-review property of every expression (see threat-model R-1).
- **The Flow ordering + Policy-binding-mode (Any/All) interaction
  is operator-error-prone.** Default `policy_engine_mode=ANY`
  means a single passing policy advances the stage; operators
  intending defense-in-depth must explicitly choose `ALL`.

**Invariants pinned by this ADR (intended, not all enforced).**

- Every Flow execution emits at least one Event (per `events/`
  doc).
- Expression policies execute in the Server's process context with
  Server-process privilege (no sandbox).
- Stages cannot be reordered or inserted at runtime; Stage Bindings
  are persisted configuration.
- Policy evaluation can occur either at flow-plan time (with
  "Evaluate when flow is planned") or just-before-stage; this is
  per-binding configurable.

## Enforcement

- Stage taxonomy is fixed; new Stage types require a code change
  in `authentik/stages/` (per `pyproject.toml` mypy override
  list — each stage type is a distinct Python module).
- Expression policies are evaluated by `authentik.policies.expression`
  using the standard Python interpreter; no `RestrictedPython` or
  similar sandbox is in use.
- Per `security/security-hardening.md`, Expression and Blueprint
  write API endpoints are the explicit hardening targets.

## Notes

This ADR is reconstructed from the shipped documentation and the
shape of `authentik/` (the per-stage / per-policy / per-provider
module layout in `pyproject.toml`'s mypy override list is the
ground truth). The fundamental decision to treat the expression
engine as "documented arbitrary code, not a sandbox" is explicit
in `SECURITY.md` under "Intended functionality." The IncludeSec
2025-09 audit (per `prior-audit.md`) finding H3 reinforced the
"expected behavior" classification and pointed reviewers at the
hardening doc.
