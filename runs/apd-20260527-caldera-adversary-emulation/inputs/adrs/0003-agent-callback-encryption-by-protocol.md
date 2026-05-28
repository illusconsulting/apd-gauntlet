---
title: 0003 — Per-contact agent callback authentication; no platform-wide enforced contract
status: accepted
date: 2019-04-22
---

# ADR-0003: Per-contact agent callback authentication; no platform-wide enforced contract

- **Status:** Accepted
- **Date:** 2019-04-22

## Context

Caldera supports a deliberately wide range of agent callback
("contact") protocols to model real-world adversary tradecraft:
plain HTTP, DNS exfiltration, FTP, GitHub Gists (covert), HTML
(beacons hidden in a `/weather` page), Slack channels, raw TCP,
raw UDP, websockets, and SSH tunnels. Each protocol has different
on-wire constraints — DNS has tight payload limits, HTTP is
firewall-friendly, GIST piggy-backs on a public service, Slack
uses bot tokens.

A platform-wide authentication contract (e.g. every implant
presents a per-deploy signing key in every beacon, verified by
the contact module) would simplify the threat-model story
materially. But it would also constrain the protocols Caldera
can model — DNS exfiltration cannot easily carry a 256-bit
HMAC in every label, and Slack channels do not let the bot
verify the poster's identity beyond the workspace's own auth.

## Decision

Each agent **contact protocol defines its own on-wire format
and its own (optional) authentication / obfuscation scheme.**
The platform does not enforce a universal beacon-authentication
contract. Specifically:

- **HTTP contact** (`contact_http.py`): `POST /beacon` with
  JSON body, base64-decoded by default. The implant's `paw`
  field identifies it; no cryptographic authentication of the
  beacon body beyond the operator-selected obfuscator
  (`plain-text` or `base64` ship in core; plugins may add AES).
- **DNS contact**: covert exfiltration via DNS queries to the
  `app.contact.dns.domain` (default `mycaldera.caldera`). No
  per-query authentication.
- **FTP contact**: static username/password from
  `conf/<env>.yml` (`caldera_user / caldera`).
- **GIST contact**: outbound to GitHub Gists using an
  operator-supplied PAT.
- **HTML contact**: beacons hidden in a benign-looking
  `/weather` HTML page. No authentication.
- **Slack contact**: posts to a configured Slack channel
  using a bot token from `conf/<env>.yml`.
- **TCP / UDP / websocket contacts**: raw sockets on dedicated
  ports. No transport-layer authentication.
- **SSH tunnel** (`asyncssh`): static user
  (`sandcat / s4ndc4t!`) and host-key file from
  `conf/<env>.yml`.

The `Obfuscator` first-class object is the platform's hook for
*encoding* beacon bodies. Two obfuscators ship in core:
`plain-text` (no obfuscation) and `base64` (no authentication).
Plugins may register additional obfuscators (e.g. AES-GCM),
but **none ship by default**, and the platform does not require
any.

## Consequences

**Positive (intended flexibility).**

- Caldera can model the on-wire diversity of real adversary C2
  channels: covert (DNS, HTML, GIST), commodity (HTTP, TCP),
  trust-leveraging (Slack, gist).
- Operators evaluating EDR / network-sensor coverage get
  realistic detection-validation scenarios across a wide range
  of protocols.

**Negative / trade-offs.**

- **No platform-wide guarantee that an inbound beacon
  originated from a Caldera-deployed implant.** An attacker
  posing as an implant (`POST /beacon` with a fabricated
  `paw`) can register itself with the server (threat-model
  S-2). The platform has no per-implant signing material it
  could check the beacon against.
- **Quality varies across contact modules.** The SSH tunnel
  has at least a configurable host-key; the TCP / UDP
  contacts have nothing. Operators may inadvertently choose a
  contact whose authentication posture is unsuitable for
  the engagement.
- **Beacon downgrade.** With the default `base64` obfuscator,
  beacons carry no integrity protection. A network attacker
  between the implant and the C2 can re-encode commands or
  fabricate results (threat-model T-3).
- **No mutual authentication of the C2 to the implant.** A
  malicious endpoint impersonating the C2 (DNS poisoning,
  network-redirect) can receive a real implant's beacons and
  send arbitrary commands; the implant trusts whoever answers
  on the configured callback URL.

**Invariants pinned by this ADR (intended, not enforced).**

- The set of available contact protocols is pluggable.
- Per-contact authentication / encryption choices are
  operator-selected via configuration and plugin enablement.
- The platform makes no claim that any contact protocol
  guarantees implant identity.

## Enforcement

- `app/contacts/contact_*.py` modules each implement their own
  protocol handling.
- `ContactService.handle_heartbeat` upserts agents on first
  contact without checking implant-identity material.
- The shipped `Obfuscator` set is `plain-text` and `base64`;
  plugin-contributed obfuscators may add stronger encoding.

## Notes

A future "authenticated beacons" posture would require:

1. A per-implant signing key, baked into the implant at build
   time (`ldflags` extension on `sandcat` build).
2. A server-side verifier that checks every beacon against
   the registered key for the claimed `paw`.
3. Some contact protocols (DNS in particular) would need a
   redesigned wire format to carry the signature.

This was considered but is not the project's current direction.
