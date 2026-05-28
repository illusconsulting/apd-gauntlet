---
title: 0003 — Mailhog as the OTP / notification delivery target
status: accepted
date: 2020-11-02
---

# ADR-0003: Mailhog as the OTP / notification delivery target

- **Status:** Accepted
- **Date:** 2020-11-02

## Context

Several crAPI flows require out-of-band email delivery:

- Signup OTP / pincode (used to verify a new vehicle's owner).
- Password-reset OTP.
- Email-change confirmation.
- Generic notifications (order confirmations, mechanic-report alerts).

For an educational target intended to run on a single host, requiring
a real SMTP service would (a) introduce a deploy dependency the
project explicitly tries to avoid (per `docs/overview.md` — "minimal
tech"), and (b) risk operators sending real email to real third-party
addresses by mistake. At the same time, the security model around
OTPs is itself a teaching topic; the email path needs to be
introspectable.

## Decision

Use **Mailhog** as a development-grade SMTP catcher. Identity sends
SMTP traffic to `mailhog:1025`; Mailhog stores every captured message
in an in-memory ring buffer and exposes a web UI on `:8025`.

The `MAILHOG_DOMAIN=example.com` env trap on `crapi-identity` means
**all** mail to any `example.com` address is silently delivered to
Mailhog, regardless of the `SMTP_HOST` override. The shipped
`SMTP_HOST=smtp.example.com`, `SMTP_PASS=xxxxxxxxxxxxxx`,
`SMTP_FROM=no-reply@example.com` values are placeholder; there is no
production SMTP path configured in the default compose.

The Mailhog UI port `:8025` is the only non-`crapi-web` port exposed
to `LISTEN_IP` by default. With `LISTEN_IP=127.0.0.1` (the default),
it is loopback-only; with `LISTEN_IP=0.0.0.0` (the documented "expose
to all interfaces" override), it is network-reachable.

## Consequences

**Positive (intended pedagogy).**

- Trainees can see the OTP arrive instantly without any external
  email account.
- The OTP brute-force challenge (challenge 3) is pedagogically clean:
  the OTP itself is observable via Mailhog so that students who
  cannot brute-force can still complete the happy-path flow.

**Negative / trade-offs.**

- **Production-grade email is not configured.** There is no
  documented procedure for swapping Mailhog out for a real SMTP
  service such that the `example.com` trap is also removed.
  Misconfiguration would either leak OTPs to the real internet (if
  the domain trap is removed but real credentials are wrong) or
  silently swallow them (if the trap stays in place).
- **OTP confidentiality depends on Mailhog UI access control —
  which is none.** Mailhog has no built-in authentication on `:8025`.
  Anyone reachable on that port can read every captured OTP and
  password-reset email.
- **No TLS on the SMTP hop.** Identity → Mailhog runs plaintext on
  `:1025`. The `SMTP_STARTTLS=true` env on identity has no effect
  because Mailhog does not advertise STARTTLS.
- **OTP delivery is unattributed at the application layer.** Mailhog
  records the SMTP envelope but the identity service does not
  audit-log the dispatch event (see threat-model R-1).
- **No bounce / delivery-failure handling.** If a real SMTP path is
  swapped in and the destination MTA rejects (4xx / 5xx), the
  identity service's behaviour is undefined in the inputs.
- **No replay or throttling discipline on OTP issuance.** A single
  account can request password-reset OTPs as fast as it can dial the
  `forget-password` endpoint; each issuance adds a captured email to
  Mailhog and resets the OTP value (see challenge 3 discussion).

**Invariants pinned by this ADR (intended, not all enforced).**

- The default deploy MUST NOT send real email to non-`example.com`
  addresses.
- Mailhog MUST NOT be exposed beyond loopback in any unattended
  deploy. (Operator-enforced; the `LISTEN_IP=0.0.0.0` override
  violates this and the documentation does not warn about it.)

## Enforcement

- `MAILHOG_DOMAIN=example.com` env on `crapi-identity`.
- Compose port mapping `LISTEN_IP:8025:8025` on the `mailhog`
  service.
- Healthcheck on the Mailhog container.

## Notes

A production-style replacement would require: a real SMTP relay
(SES, SendGrid, Postmark), removal of the `example.com` domain trap,
an audit-logged dispatch event per email sent, retry / bounce
handling, and an authenticated UI for operator inspection (if any
inspection UI is shipped at all).
