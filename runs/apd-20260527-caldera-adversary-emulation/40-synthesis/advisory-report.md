---
framework_version: 1.5.0
domain_pack:
  name: security-tooling
  version: 1.0.0
run_id: apd-20260527-caldera-adversary-emulation
specialists_skipped: []
---

# APD Gauntlet Advisory Report — Apache Caldera v5.x

**Run:** `apd-20260527-caldera-adversary-emulation`
**Framework:** APD v1.5.0 with security-tooling domain pack v1.0.0
**Subject:** Apache Caldera (MITRE, Apache-2.0), master branch as of 2026-05-27
**Date:** 2026-05-27

## Executive summary

Apache Caldera (MITRE, Apache-2.0, v5.x) is an adversary-emulation
framework explicitly positioned by its upstream maintainers as a
research-grade, trusted-environment platform. The README is candid:
"The Caldera server does not have a hardened and thoroughly pentested
web application interface, but only basic authentication and security
features." This APD advisory review treats that documented posture as
accepted starting state and produces findings against its second-order
consequences for trustworthiness, scalability, and auditability —
specifically through the security-tooling pack's lens of
weapons-platform misuse, ROE enforcement, and CFAA defensibility.

The review identifies **41 deduped findings** clustered into 9
cross-lens compounds. **Eight findings score critical** on the
security-tooling severity rubric — four of which engage the
weapons-platform-misuse axis (the rubric's load-bearing legal-exposure
dimension). The platform's documented research posture is internally
consistent: no specialist contradictions and no severity disagreements,
which strengthens confidence that the gaps are intentional in the
upstream model but consequential for any operator deploying outside
MITRE's segregated-lab assumption.

The single load-bearing recommendation across critical clusters is
the introduction of a **first-class Engagement object with
platform-enforced ROE**, paired with a **structured audit emitter
shipped to WORM storage**. Without these, every command issuance is
challengeable as out-of-scope (a CFAA-defensibility failure), every
implant compromise has unbounded blast radius (a
weapons-platform-misuse failure), and incident reconstruction is
impossible (a forensic failure).

## Findings at a glance

| Severity | Count |
|----------|-------|
| Critical | 8 |
| High | 19 |
| Medium | 13 |
| Low | 0 |
| Informational | 1 |
| **Total** | **41** |

| Disposition | Count |
|-------------|-------|
| Gap | 35 |
| Risk | 1 |
| Uncertainty | 0 |
| Blocked-on-evidence | 5 |

| Tier | Findings | Capabilities |
|------|----------|--------------|
| Trustworthiness | 18 | 8 |
| Scalability | 14 | 4 |
| Auditability | 18 | 4 |
| **Total (unique)** | **41** (some cross-linked) | **12** |

## Cross-lens compounds

The synthesizer identified 9 cross-lens compounds — concerns that
multiple specialists landed on independently. Each is a candidate
prioritization unit for remediation.

| Cluster | Severity | Lenses involved |
|---------|----------|-----------------|
| Default-credential / single-factor / lifecycle | **critical** | Confidentiality + Authenticity + Ephemeral |
| Plugin-supply-chain | **critical** | Integrity + Authenticity + Ephemeral + Distributed + Non-Repudiation + Immutability |
| Implant-trust (paw-only + no cert pinning) | **critical** | Authenticity + Integrity + Confidentiality |
| Engagement / ROE / CFAA | **critical** | Integrity + Ephemeral + Non-Repudiation + Confidentiality |
| Audit-vacuum | **critical** | Non-Repudiation + Immutability |
| Single-process SPOF | high | Availability + Distributed + Resilient |
| Result-data lifecycle | high | Confidentiality + Integrity + Immutability + Ephemeral |
| Channel security (default HTTP, no per-command sig) | high | Confidentiality + Integrity + Authenticity |
| Listener resilience | medium | Availability + Resilient |

## Headline findings (top 10)

1. **nonrep-a1b2c3d4** — No structured audit emitter exists; operator actions are unattributable in a defensible record.
2. **intg-b2c3d4e5** — Engagement scope (ROE) is not platform-enforced; commands proceed without a target-attestation gate (CFAA exposure).
3. **intg-a1b2c3d4** — Plugin modules load with no signature verification, no manifest pinning, no hash check.
4. **conf-a1b2c3d4** — Default cookie-encryption key and salt enable session takeover when --insecure is used.
5. **conf-b2c3d4e5** — Default operator API keys ship in conf/default.yml.
6. **auth-c3d4e5f6** — No certificate pinning at implant; listener TLS termination yields command-substitution.
7. **auth-b2c3d4e5** — Implant has no cryptographic identity; paw alone is the registration token.
8. **immut-a1b2c3d4** — No append-only / WORM substrate for operator-action audit log (the audit log itself does not exist).
9. **nonrep-b2c3d4e5** — Command-issued events not audited; every implant command lacks defensible attribution.
10. **conf-c3d4e5f6** — Harvested credentials accumulate across engagements with a single platform-wide Fernet key.

## Recommended next-step roadmap

Sequenced by dependency and impact.

1. **Introduce first-class Engagement object** with target-inventory enforcement at command-issue time; emit engagement_start / scope_change / close events. Closes the CFAA-defensibility gap and unblocks per-engagement ACL, keys, and sessions.
2. **Stand up a structured audit emitter** covering the security-tooling consequential-action surface (24 event classes); ship to WORM storage (S3 object-lock or transparency-log-anchored hash chain).
3. **Add plugin signature verification** at load time with a community-maintained signing root; deprecate the implicit-operator-trust model. Combine with subprocess-per-plugin sandbox for defense-in-depth.
4. **Fail-closed on default credentials / default Fernet key**; add an admin rotate-keys flow that re-derives encryption_key + crypt_salt and re-encrypts data/cookie_storage and data/results/.
5. **Ship implants with pinned listener certificate and per-command signature verification**; refuse to beacon on pinning failure.
6. **Add MFA to the core login pipeline** (TOTP minimum, WebAuthn preferred); migrate API-key path from per-group to per-operator tokens with TTL and deny-list.
7. **Adopt per-engagement DEK derivation** for result-data encryption with KEK in operator-supplied KMS; destroy DEK on engagement closure.
8. **Split agent listener path into a separate process** from operator UI; bulkhead the asyncio event loop; document at least one multi-host topology.
9. **Refuse to bind a non-loopback address without TLS configured**; move TLS termination into core (drop ssl-plugin-optional framing).
10. **Move data/results/ to WORM storage** with per-record signature held by an orchestrator-only key; document retention policy per data class with legal-hold support.

## Strengths

Caldera ships with the following confirmed capabilities (each with caveats):

- **Per-deploy credential bootstrap** via `ensure_local_config()` — generates per-deploy `conf/local.yml` when `--insecure` is not used.
- **Request validation middleware** on `/api/v2` handlers (aiohttp_apispec). Coverage limited to /api/v2.
- **Optional Fernet at-rest encryption** for `data/results/` via FileSvc. Single platform-wide key.
- **Encrypted session cookie storage** via `aiohttp_session`. 7-day default TTL with no deny-list.
- **Pluggable LoginHandlerInterface** — allows operator-installed MFA or SSO without forking core.
- **Operation creator attribution** on Link records (in-memory only; no durable audit).
- **Per-engagement-instance deployment pattern** documented as preferred.
- **Optional TLS termination via ssl plugin** for the operator console.
- **Untrusted-agent sniffer** demotes silent agents in the registry (demote, not evict).
- **Operation resumer** rehydrates active operations from `data/` on restart.
- **Health endpoint** at `/api/v2/health` (unauthenticated).
- **ldflags sanitization** in FileSvc for sandcat builder.

## Tier posture

### Trustworthiness

18 findings (4 critical, 6 high, 7 medium, 1 risk). Default-credential
surface (encryption_key, crypt_salt, API keys, login creds), absent
plugin signature verification, absent platform-enforced ROE, default
HTTP transport, single platform-wide Fernet key for harvested data.
CVE-2025-27364 (pre-auth RCE, Feb 2025) was an example of the
documented trust model's load-bearing nature.

### Scalability

14 findings (4 high, 10 medium). Single-asyncio-process architecture
is dominant constraint. No multi-host topology, no DR/BCP, no per-tenant
or per-engagement residency binding. Long-lived team-server pattern
accumulates harvested credentials indefinitely. API keys and
encryption keys require restart to rotate. Session cookies remain
valid 7 days regardless of credential change.

### Auditability

18 findings (4 critical, 9 high, 5 medium) — highest-density tier.
**No structured audit log at all.** Zero of 24 consequential-action
classes have structured coverage. No append-only / WORM substrate.
Plugins, implants, and operator API tokens carry weak or no
cryptographic identity. The platform cannot produce defensible
evidence to distinguish authorized testing from unauthorized
intrusion under CFAA.

## Blocked-on-evidence (5 findings)

These findings could not be fully scored from available artifacts and
are surfaced for clarification by the operator. They are first-class
output, not failures.

- **conf-f6a7b8c9** — Backup snapshot encryption posture undocumented for `data/backup/`.
- **avail-a1b2c3d4** — No declared SLO or availability target.
- **dist-e5f6a7b8** — Containerized deployment isolation posture undocumented.
- **resil-d4e5f6a7** — Timeout posture on contact decoders unspecified.
- **auth-f6a7b8c9** — Some `/api/v2` handlers may be exempt from `@check_authorization` via `__caldera_unauthenticated__`.

Each carries a `prerequisite_evidence` list naming the documents or
properties needed to close the finding.

## Synthesis annexes

- `deduped-findings.yaml` — all 41 deduped findings with cluster IDs and cross-references
- `deduped-capabilities.yaml` — 12 confirmed capabilities with maturity
- `contradictions.yaml` — empty (no specialist contradictions)
- `severity-disagreements.yaml` — empty (no severity disagreements)
- `nist-coverage.yaml` — 56 unique NIST 800-53r5 controls cited across findings + capabilities
- `attack-exposure.yaml` — 18 MITRE ATT&CK techniques + D3FEND counter recommendations
- `apd-coverage-matrix.yaml` — 9 APD goals x N taxonomies coverage rollup
- `report-data.yaml` — v1.5.0 report supplement contract (executive paragraphs, headline-finding ranks, strengths with caveats, sequenced next steps, per-tier posture summary)
- `threat-model-coverage.yaml` and `threat-model-coverage-report.md` — Phase 5.5 evaluator output (see below)

## Threat-model evaluator note

The threat-model evaluator (Phase 5.5) ran against the normalized
threat model and confirmed:

- 21 STRIDE+WP threats covered with at least one corresponding APD finding.
- No silences (threats with no finding coverage).
- No contradictions between threat-model severities and synthesizer severities.

## Attack-path analyzer note

The attack-path analyzer (Phase 5.6) is structurally enabled
(`crown_jewels[]` and `attacker_positions[]` declared in
`.apd-run.yaml`). It runs as a CLI step; this report is generated
before the analyzer's `apath-*` findings are merged into the coverage
matrix. Operators wanting attack-path enumeration should run
`apd-gauntlet attack-paths runs/apd-20260527-caldera-adversary-emulation`
after this advisory.

## Methodology

- **Framework:** APD v1.5.0 (three tiers, nine goals).
- **Domain pack:** security-tooling v1.0.0 — provides severity rubric (CIA × weapons-platform-misuse), consequential-action surface (24 classes), immutability data classes (12 classes), data taxonomy.
- **Methodology hint:** STRIDE per surface (operator console, REST v2, agent listener per protocol, plugin loader, contact decoder, file serving).
- **Taxonomies in scope:** NIST 800-53r5, MITRE ATT&CK, MITRE D3FEND, OWASP API Top 10, OWASP Top 10, CWE.
- **Code recon:** disabled per `.apd-run.yaml` (Caldera source at `/tmp/caldera` not indexed; specialists used only artifact-derived evidence).

## Caveats

- This advisory is **not a vulnerability disclosure**; specific exploitation paths are not enumerated beyond the architectural-detail level required to justify severity.
- Findings reflect the input artifact set as of 2026-05-27. Upstream Caldera evolves; specific code paths may have changed.
- Out of scope: the implant codebases (sandcat, manx — separate repos); externally-maintained plugins (saml, arsenal, bountyhunter, caltack); Vue SPA browser-class attacks; upstream Docker base image supply-chain posture; Go toolchain integrity for builder plugin; third-party TTP library safety/legality.
- For operators deploying Caldera per the upstream-recommended segregated-environment pattern, many of these findings are mitigated by the deployment topology rather than the platform itself. The advisory is most actionable for operators contemplating production-grade deployment, multi-tenant SaaS delivery, or customer-deliverable engagement evidence requirements.
