# Example run — Acme Mobile Banking (`mobile-applications` domain pack)

A curated, minimal APD gauntlet run demonstrating the `mobile-applications`
domain pack against a synthetic native mobile banking client (Android + iOS).

It is a teaching fixture, not a full gauntlet run: `expected/` contains a
hand-curated subset of specialist findings and capabilities that exercises the
pack's signature concerns and the validator, not the full 9-lens + synthesis
corpus a live run produces.

## What it shows

The client design in `inputs/tech_plan.md` (plus `AndroidManifest.xml`,
`Info.plist`, `network_security_config.xml`) bakes in the mobile-specific
weaknesses the pack is built to surface:

- **Confidentiality** — auth tokens in `SharedPreferences`/`NSUserDefaults`
  instead of the Keystore/Keychain (MASVS-STORAGE-1); a hardcoded HMAC client
  secret shipped in every install (MASVS-CRYPTO-2 / RESILIENCE-2).
- **Integrity** — the daily transfer limit enforced only client-side while the
  backend accepts any amount (the doctrine Critical: *client-side enforcement of
  a server-side control is not a control*, MASVS-AUTH-1); an unverified
  `acmebank://transfer` deep link (MASVS-PLATFORM-1).
- **Ephemeral** — a 90-day refresh token with no server-side revocation or
  device-binding (MASVS-AUTH-2).
- **Resilient** — a single certificate pin with no backup pin or rotation
  (MASVS-NETWORK-2).
- **Authenticity** — no hardware attestation (MASVS-RESILIENCE-4); a biometric
  *UI gate* rather than a Keystore/Keychain key release (MASVS-AUTH-3).
- **Non-Repudiation** — consequential-action audit kept only on the device,
  which is attacker-erasable (the mobile non-repudiation core).

## Composition

The run uses `domains: [mobile-applications]`. For a full-stack review of the
banking backend the app fronts, add `--domain api-security --domain
identity-security` so server-side authorization and OAuth/OIDC token issuance are
covered alongside the client.

## Validate

```bash
apd-gauntlet validate examples/apd-20260602-acme-mobile-banking/expected/
```
