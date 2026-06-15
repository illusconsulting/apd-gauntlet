---
framework_version: 1.7.0
domains: [api-security, mobile-applications]
run_id: apd-20260612-home-assistant
synthesizer_version: 1.7.0
specialists_skipped: []
---

# APD Gauntlet Advisory Report — Run `apd-20260612-home-assistant`

> Produced by `apd-report-writer` from the deterministic synthesis rollups and the nine specialist outputs.
> This report is advisory input to architecture review. It does not gate.
> Reviewers should cross-reference the YAML outputs in `40-synthesis/` for the canonical data.
> Authoritative counts render structurally from `40-synthesis/metrics.yaml`; this narrative is qualitative by design.

**Run id:** `apd-20260612-home-assistant`
**Date:** 2026-06-12
**Subject:** Home Assistant — self-hosted home automation (23 repositories, code-recon enabled)
**Domains assessed:** api-security (primary lens), mobile-applications
**Taxonomies:** CWE · MITRE ATT&CK · D3FEND · OWASP Top 10 · OWASP API Top 10 · MASVS · MASWE

---

## 1. Executive Summary

**Scope.** This run assessed Home Assistant as a layered system spanning 23 code-grounded
repositories: a single trusted Python Core process (REST + WebSocket API, the auth subsystem,
the Recorder history DB, and 2,000+ in-process integrations); a host-root-equivalent Supervisor
layer (Docker socket, add-on lifecycle, ingress) with the os-agent D-Bus host bridge beneath it;
and the iOS and Android Companion clients with their on-device secret stores, WebView/JS-bridge,
deep links, and the Firebase push relay. Both declared domain packs are in scope: the
**api-security** pack governs the Core/Supervisor API surface, the add-on role model, and the
token lifecycle; the **mobile-applications** pack governs the mobile clients, on-device secrets,
and the WebView bridge. Code recon was hard-required and ran once per repository with cross-repo
intelligence so attack paths could traverse repository boundaries (mobile → Core API →
integration; add-on → Supervisor → Docker socket → host root).

**Finding posture.** The assessment shows a heavy concentration of high-severity
**trustworthiness** and **auditability** gaps standing against a real but narrowly-scoped set of
confirmed controls. The dominant shape is *blast-radius concentration in a single trust domain*:
the headline gaps converge on three architectural facts — a plaintext-at-rest secret estate
(where one file read forges tokens and one file write rewrites the permission policy undetected),
a container-to-host-root bridge that accepts privileged operations with no caller identity check,
and the complete absence of a security audit log over consequential actions. Scalability findings
are real but largely framed as the intended single-host appliance constraint. The authoritative
severity distribution and per-tier counts render from `metrics.yaml` and the HTML Overview; this
section deliberately does not restate them.

**Capability posture.** Confirmed controls are concentrated at the *verification edge* of
trustworthiness and authenticity — bcrypt password hashing with constant-time login, per-entity
READ enforcement, a revocation-aware HS256 token-validation chokepoint, the non-exportable
Android hardware-Keystore mTLS key, the Supervisor default-deny per-role URL ACL, and fail-closed
permission-policy compilation. Coverage is thinnest exactly where the headline findings sit: there
is essentially no confirmed at-rest protection over the secret estate, no enforced supply-chain
provenance, and no security-audit capability at all. Maturity skews to *implemented* with little
that is *tested* or *operationalized*; the authoritative maturity counts render from `metrics.yaml`.

---

## 2. Confirmed Security Posture

> Affirmative section. Reviewers read this first to contextualize findings as gaps in a partially-built picture.

### Trustworthiness

**Confidentiality.**
- *Per-entity READ permission at the state-read API* (`conf-cap-88473a97`) — maturity: implemented. Scope: `check_entity(POLICY_READ)` + deny-all-default policy compilation scope each non-admin user's readable entity set; read-side only.
- *bcrypt password hashing (rounds=12, constant-time login)* (`conf-cap-1044dbb3`) — maturity: implemented. Scope: passwords never persisted in recoverable form; raises offline-cracking cost if the hash store is read.
- *Android mTLS client-cert key in non-exportable hardware Keystore* (`conf-cap-01c47d42`) — maturity: implemented. Scope: the mTLS private key cannot be read out of the TEE; bearer tokens and location PII are NOT covered.
- *Optional NaCl SecretBox webhook-body encryption* (`conf-cap-277b2364`) — maturity: implemented. Scope: opt-in in-transit body confidentiality independent of TLS.

**Integrity.**
- *Single-chokepoint token validation* (`intg-cap-7a54b1a7`) — maturity: implemented. Scope: every authenticated write passes a consistent valid/not-revoked/active-user gate.
- *Fail-closed permission-policy compilation* (`intg-cap-e18bb24c`) — maturity: implemented. Scope: an empty/corrupt policy denies rather than defaulting open; does not stop a directed tamper-to-allow.
- *Supervisor default-deny per-role URL ACL* (`intg-cap-e88c8857`) — maturity: implemented. Scope: add-on calls constrained to their declared role's API surface.

**Availability.**
- *Per-token rate limit on the Firebase push relay* (`avail-cap-f97d3d6b`) — maturity: implemented. Scope: the only rate limit observed anywhere in the availability surface; bounds notification-spam, not Core/Supervisor exhaustion.

### Scalability

**Distributed.**
- *Single-host topology is an explicit, documented choice* (`dist-cap-43ec806f`) — maturity: designed. Scope: an intent/documentation capability; confers no redundancy or failover.
- *Strongly-consistent revocation within the single process* (`dist-cap-827afb47`) — maturity: implemented. Scope: revocation drops the live WS socket with no cross-instance staleness — a benefit of having exactly one node.

**Resilient.**
- See the linked resilience capabilities in `deduped-capabilities.yaml`; the permission engine's fail-closed default (`intg-cap-e18bb24c`) is the one confirmed fail-safe point, not a platform degradation strategy.

**Ephemeral.**
- *Immediate cascade revocation to all access tokens and live sockets* (`ephem-cap-5113fad9`) — maturity: implemented. Scope: a working revocation channel even though tokens do not auto-expire; manual/user-initiated only.
- *Short-lived (1800s) access tokens* (`ephem-cap-f5d582d0`) — maturity: implemented. Scope: 30-minute access-token TTL undercut by the never-expiring refresh token behind it.
- *Digest-pinned Core image layers* (`ephem-cap-32f4a499`) and *short-lived signed paths (30s)* (`ephem-cap-fb2d6d4d`).

### Auditability

**Authenticity.**
- *Revocation-aware HS256 validation chokepoint* (`auth-cap-f01e6108`) — maturity: implemented. Scope: algorithm-pinned, revocation-propagating token verification at one place; verifies a long-lived credential and does not cover the bearer-less webhook path.
- *Supervisor SecurityMiddleware token→role gate* (`auth-cap-e9f55df8`), *ingress X-Remote-User-* strip* (`auth-cap-eba3a527`), *bcrypt enumeration-resistant login* (`auth-cap-8144e2be`), *Android hardware-Keystore mTLS* (`auth-cap-42c6a13f`).

**Non-Repudiation.**
- No capabilities confirmed at this stage. See findings in section 4 for the audit-stream gap; the absence of any security-audit capability is the dominant auditability signal.

**Immutability.**
- *Optional password-based backup protection (default off)* (`immut-cap-5e14aa20`) and *digest-pinned dockerfile frontend* (`immut-cap-937d14c1`) — both narrow, partial controls; no WORM/retention/object-lock on any store.

---

## 3. Blocked-on-Evidence

> Findings where the lens could not be fully assessed without prerequisite evidence. This section is the gauntlet's structured request for more artifacts.

### Distributed

**`dist-a0ea311c` — DNS resolution topology (plugin-dns CoreDNS) as a potential single dependency is undocumented**
- **Prerequisite evidence:** CoreDNS upstream-resolver redundancy and forwarding config; whether Core/add-ons have a fallback resolver; how a DNS-plane failure propagates.
- **Apparent severity if resolved:** low (would escalate only if confirmed a single non-redundant resolver with no fallback).
- **Brief:** A single DNS plane is a classic hidden SPOF, but presence alone is not asserted as a SPOF; its redundancy posture is unknown.

### Ephemeral

**`ephem-db8641be` — Web/portal session absolute lifetime, idle timeout, and behavior on credential change are unspecified**
- **Prerequisite evidence:** portal session-management policy; whether a password/MFA change revokes existing refresh tokens; explicit logout semantics.
- **Apparent severity if resolved:** medium.
- **Brief:** Given non-expiring refresh tokens, a password reset after a suspected compromise may not actually log the attacker out — the load-bearing question to confirm.

### Non-Repudiation

**`nonrep-d23de889` — Time-source discipline (NTP topology, drift bounds, precision) is unspecified across Core/Supervisor/os-agent**
- **Prerequisite evidence:** NTP topology, drift bound, time-source-failure behavior, timestamp precision, UTC/monotonic ordering across tiers.
- **Apparent severity if resolved:** medium.
- **Brief:** Any future audit stream depends on a trustworthy, disciplined time source to make records orderable and correlatable across tiers.

> Additional blocked/uncertainty items (e.g. `merged-4f0fe6c1` Supervisor watchdog/health-check depth) are recorded in `deduped-findings.yaml`.

---

## 4. Findings

> Non-blocked findings sorted by severity descending, then by APD tier ascending. Full detail, evidence, and control mappings for every finding live in `40-synthesis/deduped-findings.yaml`; the entries below are the headline-ranked material.

### Critical

#### `auth-6924f467` — os-agent D-Bus host-root methods verify no caller identity before host-root ops

- **APD goal:** Authenticity (tier: Auditability)
- **Severity:** Critical — api-security "authentication bypass to high-privilege functions with no factor required," escalated because the functions are host-root SSH-key injection and device wipe.
- **Confidence:** high

**Summary.** os-agent exposes host-root D-Bus methods (`AddSSHAuthKey`, `ScheduleWipeDevice`) that perform privileged operations with no cryptographic or platform verification of the caller.

**Detail.** Neither method authenticates the D-Bus caller — no bus-name, uid, PID, or attested-token check — so any process able to reach the system D-Bus (a compromised add-on that has escaped to the container→host bridge per the `internal_lateral_attacker` / `malicious_or_compromised_addon` positions) is indistinguishable from the genuine Supervisor. `AddSSHAuthKey` appends an attacker key to root's `authorized_keys`; `ScheduleWipeDevice` schedules a destructive datadisk/factory wipe. This is the single most consequential privilege boundary in the system, and it is reachable with no identity factor.

**Recommendation (required).** Authenticate the caller in each method (polkit / bus-name + uid check) and bind the privileged interface to a restricted system bus name before acting. Do not rely on socket filesystem permissions as the identity proof for host-root primitives.

**Control mappings.** NIST 800-53r5: IA-3, IA-9, IA-2, SC-23, AC-6. ATT&CK: T1543 (Create or Modify System Process). CWE-306, CWE-862.

---

#### `merged-1119b0be` — Core `.storage` is plaintext JSON with no content MAC, version history, or drift detection

- **APD goal:** Immutability (tier: Auditability) — converged Integrity + Immutability
- **Severity:** Critical — severity disagreement resolved highest-wins (integrity: critical / immutability: high).
- **Confidence:** high
- **Lens perspectives:** integrity, immutability (merged from `intg-4768c0f0`, `intg-5df46115`, `intg-3b33966f`, `intg-d5c5bca5`, `immut-165d9547`, `immut-1e09d798`, `immut-8eb14ea4`, `immut-95c2660e`)

**Summary.** All `.storage` (refresh-token `jwt_keys`, user/group policy, integration secrets) plus `configuration.yaml` is mutable plaintext gated only by 0600 file permissions, with no content MAC, no required version history or signed-commit path, and no declared-vs-actual drift detection.

**Detail.** A single file-write primitive forges a refresh-token `jwt_key` (minting valid HS256 access tokens) or rewrites the user/group permission policy (escalating a principal) with no detection at read time, and leaves no immutable record that the change occurred. The fail-closed policy compilation (`intg-cap-e18bb24c`) protects against accidental corruption but explicitly not against a directed tamper-to-allow — see the contradiction annex.

**Recommendation (required).** Add a keyed MAC / signed-content envelope over each `.storage` record (key held outside the `.storage` tree, verified on read), and route config-affecting changes through a versioned, signed-commit/GitOps-only path with declared-vs-actual drift detection. Pair with at-rest encryption (linked record `merged-a49cb674`).

**Control mappings.** NIST 800-53r5: SI-7, SI-7(1), CM-5, CM-2/CM-3, SC-28, AU-9. ATT&CK: T1606.001 (Forge Web Credentials), T1098.004, T1565.001. CWE referenced via merged sources.

---

#### `merged-a49cb674` — Recorder history DB (and the `.storage` secret estate) persists home-occupancy/geolocation state with neither encryption nor tamper-evidence at rest

- **APD goal:** Confidentiality (tier: Trustworthiness) — converged Confidentiality + Immutability
- **Severity:** Critical — severity disagreement resolved highest-wins (confidentiality: high / ephemeral: high / distributed: medium).
- **Confidence:** high
- **Lens perspectives:** confidentiality, immutability (merged from `conf-d814d818`, `conf-fdf0fb06`, `conf-fec577ec`, `dist-658bd883`, `dist-b4e9697a`, `ephem-b9625c61`, `ephem-cf71612d`, `ephem-e6671d41`)

**Summary.** The Recorder store (an ordinary mutable SQLite/MariaDB/Postgres DB) holds raw presence, geolocation/zones, and lock/alarm history with no encryption-at-rest and no append-only/WORM/content-hash; this record also carries the plaintext `.storage/auth` + `jwt_key` confidentiality face, where an at-rest read forges HS256 tokens.

**Detail.** Any filesystem or DB read both discloses where occupants are and were, and can silently rewrite or delete that history undetected. The merged record carries the cross-tier Conf+Immutability convergence on one mutable plaintext store; the `.storage`-at-rest read that forges tokens (the former `conf-fdf0fb06`, critical) is the highest-consequence face. The default-unencrypted Supervisor backup bundles this estate as the weakest-protected copy of everything.

**Recommendation (required).** Apply encryption-at-rest AND tamper-evidence to the Recorder store as one program (full-disk/DB-native TDE plus field-level protection of presence/geo columns; append-only/WORM or content-hash anchoring). Sequence the at-rest encryption first (it gates the Immutability-over-PHI cross-tier dependency), then layer integrity anchoring.

**Control mappings.** NIST 800-53r5: SC-28, SC-28(1), SC-13, AU-9(2/3), SI-7, CP-9(8). ATT&CK: T1005, T1530, T1552.001, T1606.001.

> The remaining two Critical findings are attack-path `risk` findings (`apath-5390f103` physical-thief → user_credentials_store; `apath-89ebba8a` internal-lateral → supervisor_docker_control_plane), backed by the two critical specialist findings above. See `attack-path-report.md`.

### High

The 40 high-severity findings span all three tiers; the headline-ranked subset (full detail in
`deduped-findings.yaml`):

- **`merged-66801b1b`** — Core and Supervisor emit **no attributable security-audit record** over the consequential-action surface (device actuation, the auth lifecycle, privileged Supervisor API). Non-Repudiation, high. *Recommendation (required):* one security-audit stream with actor attribution on every entry, logging ALLOWED privileged operations, not only DENIED ones.
- **`auth-3f2314a4`** — the mobile_app webhook authenticates by **possession of a 32-hex `webhook_id` alone**, no caller identity or signature; the bearer-less path calls arbitrary services (locks/alarms). Authenticity, high. *(required)* Make the per-request NaCl signature mandatory; bind to a verifiable device identity. Pairs with `ephem-053957f3` (permanent, never-rotated `webhook_id`).
- **`auth-8f0d8172`** — add-on image signing (Cosign) is a **developer recommendation, not enforced by admission control**, and base images are pinned to a mutable tag, so an unsigned/tampered image runs unverified and can escalate to the host-root Docker plane. Authenticity, high. *(required)* Enforce signature verification at install/run; pin by digest.
- **`ephem-f19f24f9`** — refresh tokens **never expire and are not rotated**; a stolen refresh token is replayable indefinitely. Ephemeral, high. Pairs with `ephem-9915ab91` (10-year Long-Lived Access Tokens, no rotation).
- **`conf-3060c50e`** — the access token crosses the **native↔WebView JS bridge in cleartext** to a remotely-served frontend, with no origin allowlisting. Confidentiality, high. Pairs with `auth-ea69d3a2` (bridge dispatches on remote-frontend messages with only doc-only callback-origin verification).
- **`conf-2029ce78` / `auth-1787eae1`** — the Android Companion **trusts user-installed CAs with no certificate pinning**, exposing tokens and PII in transit to a MitM and making the backend identity forgeable.
- **`auth-7162fd48`** — **MFA/TOTP is optional and opt-in** with no enforced AAL, so the all-access owner account can be password-only.
- **`dist-66e3e208`** — single-host, single-process Core is a **platform-wide SPOF** with no replication; **`merged-0ccd3ea6`** — 2000+ integrations and the recorder write path share one event loop with **no timeout, bulkhead, or circuit breaker**.
- Further high findings: `auth-23048c0c` (inter-service calls carry no payload-level signing), `auth-3794d338` (no hardware device attestation), `auth-3dbf15e7` (IndieAuth flow omits PKCE), `intg-8b158cfe` (unsandboxed integrations consume untrusted responses at Core's full privilege), `nonrep-af1c55d3` (logbook entries carry null `context_user_id`), `dist-b98dc00a`, plus the 15 high attack-path `risk` findings in `attack-path.findings.yaml`.

### Medium

16 medium findings (full detail in `deduped-findings.yaml`), including `conf-ef49b4b0` (GET /api/config
leaks precise geolocation + filesystem paths to any bearer), `conf-7a74a4a0` (git-tracked Firebase
config in the IPA), `conf-a30cca33` (iOS Keychain default accessibility), `ephem-9c322627` /
`immut-5a5ef5bd` (mutable floating base tags), `ephem-a879a34b` (standing owner all-access, no JIT),
`auth-4e7d1059` / `auth-dfed90e4` / `auth-8a380b11` (header-trust identity, IP-as-identity providers,
no SBOM/SLSA), `dist-69bbaf5c` / `dist-d08ed969` (no replication; control/data-plane co-location),
and `resil-93866115` (no failure-mode catalog).

### Low

4 low findings: `avail-a2cfd41c` (single Firebase push relay, no SLA), `intg-2b80f92e` (encrypted
webhook payload validation asymmetry), and the two remaining low-severity records (including the
attack-path aggregate `apath-98522141`).

### Informational

None.

---

## 5. Contradiction Annex

> Cases where a finding asserts a property is absent and a capability confirms it is present, or vice versa. Reviewers determine the correct interpretation.

### `contra-067769c7`
- **Finding:** `intg-4768c0f0` (now in `merged-1119b0be`) — `.storage` records have no MAC, so a directed file-write forges `jwt_keys` or escalates a user.
- **Capability:** `intg-cap-e18bb24c` — policy compilation fails closed to deny-all on an empty/corrupt policy.
- **Evidence comparison:** The capability protects against ACCIDENTAL corruption (malformed → deny) and self-admits it does NOT protect against a DIRECTED tamper-to-True/allow-all. Disjoint threat models on the same artifact.
- **Recommended resolution:** Keep both. The fail-closed property is a genuine safe-default; the MAC/content-hash remediation is what would close the directed-tamper gap.

### `contra-7dcf3d1e`
- **Finding:** `intg-5df46115` (now in `merged-1119b0be`) — webhook `webhook_call_service` actuates arbitrary services with no per-entity write authorization, routing around the permission engine.
- **Capability:** `intg-cap-ecebb879` — per-entity READ permission is enforced at the state view (deny-all default).
- **Evidence comparison:** The capability's scope is the READ path; the finding's scope is the webhook WRITE path. The capability never claims write-path coverage.
- **Recommended resolution:** Keep both. The capability resolves READ-side doc staleness; the WRITE-side/webhook-bypass gaps remain open.

### `contra-f45409a0`
- **Finding:** `intg-d6c5e666` (now in `merged-66801b1b`) — POST /api/states enforces only `is_admin` with no per-entity write policy.
- **Capability:** `conf-cap-88473a97` — `APIEntityStateView.get` enforces per-entity `check_entity(POLICY_READ)`.
- **Evidence comparison:** Capability cites the GET path; finding cites the POST path. Per-entity on read, coarse admin-or-deny on write — an asymmetry both records independently observe.
- **Recommended resolution:** Keep both. The asymmetry itself is the actionable signal — extend per-entity policy to the write path.

> One threat-model contradiction is also recorded: `tmeval-5c02d052` — the authored baseline cell
> `tm-f8db6c3a` asserts standard X509 validation mitigates Android server spoofing, which
> `conf-2029ce78` and `auth-1787eae1` contradict (user-CA trust, no pinning). Resolution: drop
> "standard X509 validation" as the mitigation or add trust-on-first-use pinning.

---

## 6. Strengths-Notwithstanding-Gaps

> Confirmed capabilities with material caveats. Real, but not yet complete.

### Revocation-aware HS256 token-validation chokepoint (`auth-cap-f01e6108`)
- **APD goal:** Authenticity — **Maturity:** implemented
- **Confirmed scope:** Algorithm-pinned (HS256), revocation-propagating token verification at one chokepoint for both REST and WS.
- **Caveats:** Verifies a long-lived credential (jwt_key never rotates; refresh/LLATs effectively non-expiring); does not cover the bearer-less webhook path; a leaked/forged jwt_key from plaintext `.storage` produces a token it accepts.
- **Related findings:** `ephem-f19f24f9`, `ephem-9915ab91`, `merged-1119b0be`, `auth-3f2314a4`.

### Per-entity READ permission enforcement (`conf-cap-88473a97`)
- **APD goal:** Confidentiality — **Maturity:** implemented
- **Confirmed scope:** `check_entity(POLICY_READ)` + deny-all-default scope each non-admin user's readable set.
- **Caveats:** Read-side only (WRITE is admin-or-deny; webhook path has no per-entity check); admin/owner short-circuit to allow-all; `/api/config` unscoped.
- **Related findings:** `merged-66801b1b`, `conf-ef49b4b0`, `auth-3f2314a4`.

### Android mTLS client key in hardware Keystore (`conf-cap-01c47d42`)
- **APD goal:** Confidentiality — **Maturity:** implemented
- **Confirmed scope:** Non-exportable mTLS private key custody in the AndroidKeyStore.
- **Caveats:** Bearer tokens + location PII are in the UNENCRYPTED Room DB; no in-place-use protection on a rooted device; opt-in, client-identity-only (no server pinning).
- **Related findings:** `conf-205c53a5`, `conf-2029ce78`, `auth-3794d338`.

### Supervisor token→role default-deny ACL (`auth-cap-e9f55df8`)
- **APD goal:** Authenticity — **Maturity:** implemented
- **Confirmed scope:** SUPERVISOR_TOKEN→add-on identity + per-role URL allow-list with default-deny.
- **Caveats:** An admin-role / protection-disabled add-on matches `.*` and reaches the host-root Docker plane; token lifecycle unspecified; the os-agent hop downstream does no caller authz.
- **Related findings:** `auth-6924f467`, `auth-8f0d8172`, `merged-66801b1b`.

### bcrypt password hashing (`conf-cap-1044dbb3`)
- **APD goal:** Confidentiality — **Maturity:** implemented
- **Caveats:** The strong hash is persisted to plaintext `.storage` alongside recoverable MFA seeds and jwt_keys; MFA opt-in.
- **Related findings:** `merged-a49cb674`, `auth-7162fd48`.

### Fail-closed policy compilation (`intg-cap-e18bb24c`) and immediate cascade revocation (`ephem-cap-5113fad9`)
- See the contradiction annex (`contra-067769c7`) and caveats in `report-data.yaml` — both are genuine safe-default / recovery controls, both undercut by the absence of an integrity MAC and of automatic expiry respectively.

---

## 7. NIST 800-53r5 Coverage Matrix

> Per-control rollup (highlighted rows are `gapped` or `gapped_and_covered`). Authoritative version in `40-synthesis/nist-coverage.yaml`.

| Control | Family | Title | Findings | Capabilities | Posture |
|---------|--------|-------|----------|--------------|---------|
| SC-5 | SC | Denial-of-service Protection | 9 | 2 | gapped_and_covered |
| SC-6 | SC | Resource Availability | 6 | 2 | gapped_and_covered |
| SI-13 | SI | Predictable Failure Prevention | 6 | 2 | gapped_and_covered |
| SC-28 | SC | Protection of Information at Rest | (see file) | (see file) | gapped |
| AU-9 / AU-10 / AU-12 | AU | Audit protection / Non-Repudiation / Audit generation | (see file) | 0 | gapped |
| IA-9 | IA | Service Identification and Authentication | (see file) | (see file) | gapped_and_covered |

> The AU-family controls are gapped with zero capabilities — the structural signature of the
> no-security-audit-log finding (`merged-66801b1b`). Consult `nist-coverage.yaml` for the full matrix.

---

## 8. ATT&CK Technique Exposure

> Techniques mapped by findings, with any mitigating capabilities. Authoritative version in `40-synthesis/attack-exposure.yaml`.

| Technique | Sub | Tactic | Name | Exposure | Mitigated by |
|-----------|-----|--------|------|----------|--------------|
| T1557 | — | TA0006 | Adversary-in-the-Middle | 3 findings | M1041 (3 caps) |
| T1499 | T1499.002 | TA0040 | Endpoint Denial of Service | 2 findings | — |
| T1606 | T1606.001 | TA0006 | Forge Web Credentials | (see file) | — |
| T1543 | — | TA0003 | Create or Modify System Process | 1 finding | — |
| T1417 | — | TA0006 | Input Capture (JS bridge) | 1 finding | — |
| T1409 | — | TA0035 | Stored Application Data | 1 finding | — |

> The token-forgery (T1606.001) and host-root persistence (T1543/T1098.004) exposures carry no
> mitigating capability — they are the critical-finding ATT&CK signatures.

---

## 9. APD Coverage Matrix

> Per-component coverage across the nine APD goals. Authoritative version in `40-synthesis/apd-coverage-matrix.yaml`.

| Component | Conf | Intg | Avail | Dist | Resil | Ephem | Auth | NonRep | Immut |
|-----------|------|------|-------|------|-------|-------|------|--------|-------|
| Core `.storage` secret estate | gapped | gapped_and_covered | silent | gapped | silent | gapped | gapped_and_covered | gapped | gapped |
| Recorder history DB | gapped | silent | gapped | gapped | gapped | silent | silent | gapped | gapped |
| Supervisor / os-agent host plane | silent | gapped | silent | gapped | silent | silent | gapped_and_covered | gapped | gapped |
| mobile_app webhook path | covered | gapped | gapped | silent | gapped | gapped | gapped | gapped | silent |
| Mobile on-device stores | gapped_and_covered | silent | silent | silent | silent | gapped | gapped_and_covered | silent | silent |

Legend: `covered` (capabilities, no gaps), `gapped` (findings, no capabilities), `gapped_and_covered` (both — review scope alignment), `silent` (no findings or capabilities in this cell). Indicative rows only — consult the authoritative file.

### Framework Coverage (taxonomies declared)

- **CWE coverage** — `40-synthesis/cwe-coverage.yaml`. Developer-facing weakness exposure (CWE-306/862 host-root authz, CWE-312/922 plaintext storage, CWE-613 token lifetime, CWE-295 pinning, CWE-749 JS bridge, CWE-778 missing audit).
- **OWASP coverage** — `40-synthesis/owasp-coverage.yaml`. API2 (Broken Authentication, 4), API3 (BOPLA), API4 (Unrestricted Resource Consumption, 2), API10 (Unsafe Consumption); web Top-10 entries for the Lit/TS frontend + Core web surface.
- **D3FEND defensive coverage** — `40-synthesis/d3fend-coverage.yaml`. `defensive_entries` from confirmed capabilities (D3-CH credential hardening via bcrypt, D3-CBAN certificate-based auth via the hardware mTLS key); the attack-path D3FEND overlay is honestly empty because all bottlenecks are structural edges.
- **MASVS / MASWE coverage** — `40-synthesis/masvs-coverage.yaml`, `maswe-coverage.yaml`. MASVS-STORAGE-1 (unencrypted Room DB, default Keychain), MASVS-NETWORK-2 (no pinning), MASVS-PLATFORM-2 (JS bridge), MASVS-AUTH-1 (no PKCE), MASVS-RESILIENCE-4 (no attestation).

---

## 10. Severity Disagreement Annex

> Records where two agents agreed on the concern but disagreed on severity. The merged finding takes the higher severity; the disagreement is preserved here for transparency.

### `merged-1119b0be`
- **Agents and severities:** immutability: high · integrity: critical
- **Chosen severity:** critical
- **Rationale:** Highest-severity-wins across the merged lens severities (the directed-tamper-to-forge-jwt_key integrity face drives critical).

### `merged-a49cb674`
- **Agents and severities:** confidentiality: high · distributed: medium · ephemeral: high
- **Chosen severity:** critical
- **Rationale:** Highest-severity-wins across the merged lens severities (the at-rest read forging HS256 tokens over the home-occupancy fact base drives critical).

### `merged-66801b1b`
- **Agents and severities:** integrity: medium · non_repudiation: high
- **Chosen severity:** high
- **Rationale:** Highest-severity-wins across the merged lens severities.

---

## Appendix: Specialist Output Index

For drill-down beyond this synthesis-level view, consult the per-specialist and synthesis files:

```
10-trustworthiness/  confidentiality.*  integrity.*  availability.*
20-scalability/      distributed.*  resilient.*  ephemeral.*
30-auditability/     authenticity.*  non-repudiation.*  immutability.*
40-threat-model/     threat-model.findings.yaml (tmeval-*)
40-synthesis/        deduped-findings.yaml  deduped-capabilities.yaml
                     metrics.yaml (authoritative counts)
                     contradictions.yaml  severity-disagreements.yaml
                     nist-coverage.yaml  attack-exposure.yaml  apd-coverage-matrix.yaml
                     cwe-coverage.yaml  owasp-coverage.yaml  d3fend-coverage.yaml
                     masvs-coverage.yaml  maswe-coverage.yaml
                     attack-path.findings.yaml  attack-path-report.md
                     report-data.yaml  advisory-report.md
```
