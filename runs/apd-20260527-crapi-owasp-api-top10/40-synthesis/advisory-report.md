---
framework_version: 1.5.0
domain_pack:
  name: api-security
  version: 1.0.0
run_id: apd-20260527-crapi-owasp-api-top10
specialists_skipped: []
---

# APD Advisory Report — OWASP crAPI v1.1.5

- **Run id:** `apd-20260527-crapi-owasp-api-top10`
- **Subject:** OWASP crAPI v1.1.5 — automotive B2C demonstration platform (Apache-2.0)
- **Domain pack:** `api-security` v1.0.0
- **Framework version:** 1.5.0
- **Methodology hint:** STRIDE (declared in `.apd-run.yaml`; corroborated by `inputs/threat-model.md` frontmatter)
- **Specialists skipped:** none

## 1. Executive summary

This APD gauntlet run reviews OWASP crAPI v1.1.5, an intentionally
vulnerable automotive B2C demonstration platform built around the OWASP
API Security Top 10 (2023). The api-security domain pack applies. The
9-artifact intake is candid about the 18+ vulnerabilities crAPI ships
by design (BOLA on vehicle and mechanic-report endpoints, BFLA on admin
video delete, mass-assignment on orders and videos, SQL/NoSQL
injection on coupons, SSRF on contact_mechanic, JWT forgery via four
documented patterns, broken OTP brute-force, chatbot prompt-injection).
The gauntlet's role is to assess the operational consequences across
all 9 APD goals — Trustworthiness (Confidentiality, Integrity,
Availability), Scalability (Distributed, Resilient, Ephemeral),
Auditability (Authenticity, Non-Repudiation, Immutability) — rather
than re-derive the vulnerability catalog.

Across 9 specialists, **62 deduped findings** emerged after merging
**4 cross-lens clusters** (the JWT trust chain, the chatbot admin
credential, the SSRF on contact_mechanic, and the shared datastore
credential). The severity distribution is **5 critical, 25 high, 32
medium**; zero contradictions; zero severity disagreements. **20
findings (32%) are dispositioned `blocked` on prerequisite evidence**
— consistent with the demo-intent gap-rich nature of the inputs
(no audit pipeline, no backups, no SLO commitment, no rotation
procedures, no MFA, no production SMTP path).

The single highest-leverage architectural concern is the **JWT trust
chain**: the default install ships an RSA private key checked into
the repo and the verifier accepts at least four documented forgery
patterns (algorithm confusion, alg:none on dashboard, jku abuse, kid
path-traversal). The combination produces cluster-wide forge-any-
identity capability. The most strategically urgent operational gap is
the **total absence of audit logging** on consequential actions across
every service, which prevents forensic reconstruction of any incident
and renders breach detection and notification obligations un-meetable.

## 2. Scope and methodology

crAPI is operated, per `agents.md`, by "a single security-engineering
practitioner" or workshop instructor on a single host — not by an
enterprise operator. There is no on-call rotation, no SLO commitment,
no production hardening. Specialist findings against the artifacts
(structural) are in scope; procedural findings against the operator
are not.

Threat-model evidence: `inputs/threat-model.md` is STRIDE-organized
with a frontmatter `methodology: stride` and maps each entry to one
or more challenges from the crAPI catalog. The threat-model normalizer
(Phase 1.6) extracted 33 threats across the six STRIDE categories;
their normalized form is at `00-context/threat-model-normalized.yaml`.

Code reconnaissance: per `.apd-run.yaml`, `code_recon: disabled`
because the crAPI source at `/tmp/crAPI` is not indexed in any CBM
project for this environment. Findings are grounded in artifact
evidence only.

Active taxonomies: `cwe`, `mitre_attack`, `d3fend`, `owasp_api_top10`,
`owasp_top10`. The OWASP LLM Top 10 surface (chatbot prompt-injection
per challenges 16/17/18) is discussed but not explicitly mapped
because the run-config did not declare it.

## 3. Headline findings

The synthesizer's editorial top-10, ordered by reviewer priority.
Full detail in `40-synthesis/deduped-findings.yaml`.

### 3.1 `merged-c829ffc8` — CRITICAL — Cluster-wide forge-any-identity capability

The default install ships an RSA private key in `services/identity/jwks.json`
and the verifier accepts at least four documented JWT forgery patterns
(alg:none on dashboard, RS256↔HS256 algorithm confusion, jku-fetch
from attacker-controlled URLs, kid as filesystem path). Each pattern
independently breaks the identity trust chain; together they yield
forge-any-identity capability against every service that trusts
identity's JWKS.

This is a 3-lens merged finding (Confidentiality key disclosure,
Integrity verifier tamper-detection, Authenticity identity
provenance). The single fix touches all three.

### 3.2 `auth-0925a719` — CRITICAL — No MFA on any authentication surface

Per `tech_plan.md` §4 explicitly: "There is no MFA." Every
authentication surface — signup, login, password reset, admin actions
— relies on a single factor. Admin surfaces (BFLA notwithstanding)
execute against the same single-factor token. Per the API-security
rubric's MFA-on-admin clause, this is critical when on PII surfaces;
crAPI's admin paths reach user-record enumeration and the
gateway-service VIN-to-PII oracle.

### 3.3 `intg-e7ebcc95` — CRITICAL — Mass assignment on /shop/orders → arbitrary credit inflation

Negative quantity is accepted by the order-create handler; the server
multiplies `unit_price × quantity` and applies the signed delta to
the user's credit balance. Single-request balance manipulation.
Structurally the same allowlist-free deserialization that drives the
broader BOPLA cluster (intg-62ebf664, intg-a6b6d147).

### 3.4 `intg-b7417f91` — CRITICAL — NoSQL injection on /community/api/v2/coupon/validate-coupon

Request body parsed directly into a Mongo query selector; `$ne` /
`$regex` operators yield arbitrary document read. Coupons collection
itself is low-sensitivity, but the same shared-admin Mongo
credential reaches the `posts` and chatbot-history collections —
PII-bearing.

### 3.5 `intg-2aeb03f1` — CRITICAL — SQL injection on /workshop/api/shop/apply_coupon

Coupon code concatenated into a SQL UPDATE; UPDATE injection re-arms
claimed flags. UNION SELECT against the same Postgres connection
(shared admin credential) reads the `users` table — PII + password
hashes.

### 3.6 `merged-d2e871f5` — HIGH — Chatbot prompt-injection → admin actions, attribution void

The chatbot container holds `API_USER=admin@example.com /
API_PASSWORD=Admin!123` and uses it to act on user behalf. Prompt-
injection (challenges 16/17/18) drives privileged actions under that
admin authority. Downstream audit (when introduced per nonrep-7fad26d8)
would attribute to `admin@example.com`, not the prompt author.

This is a 4-lens merged finding (Integrity write-path, Authenticity
credential-binding, Non-Repudiation attribution, Ephemeral rotation).

### 3.7 `merged-514507e6` — HIGH — SSRF + no rate limit + cloud-metadata exfiltration

`POST /workshop/api/merchant/contact_mechanic` fetches an arbitrary
user-supplied URL server-side and returns the response body. No
allowlist, no IP-resolution check, no rate limit. Reads cloud
metadata (169.254.169.254), internal services (mailhog UI :8025,
ChromaDB, JWKS), and arbitrary external hosts as a reflective DoS.

This is a 3-lens merged finding (Confidentiality data exfiltration,
Integrity input validation, Availability rate limit).

### 3.8 `merged-44bdb663` — HIGH — Plaintext admin/crapisecretpassword everywhere

Single shared credential in compose env collapses datastore tier into
one trust domain. Direct database access bypasses every service-layer
control — including the BOLA/BFLA/mass-assignment controls if they
were fixed.

2-lens merge (Confidentiality credential disclosure, Distributed
topology-of-trust).

### 3.9 `nonrep-7fad26d8` — HIGH — No application-level audit log

Per `runbook.md` §8: "GAP. No application-level audit log is
shipped." Authentication, authorization decisions, PII access,
payment events, session lifecycle, admin configuration — every
consequential-action category enumerated in the api-security domain
pack's `consequential-actions.md` is uncovered. Forensic
reconstruction is impossible; breach-notification obligations are
un-meetable; SOC 2 CC7.2 is un-attestable.

### 3.10 `resil-776fc650` — HIGH — 7-day session theft has no recovery signal

`JWT_EXPIRATION=604800000` (7 days) with no refresh-token rotation,
no JTI deny-list, no /logout endpoint. Per `runbook.md` §10 ("Respond
to user account takeover"): "Cannot invalidate the attacker's
session." The runbook explicitly documents that legitimate
remediation does not invalidate outstanding tokens.

## 4. Cross-cutting clusters

The synthesizer identified four notable clusters that an architect
should weigh together.

### 4.1 The JWT authentication chain (7 findings)

`merged-c829ffc8`, `ephem-30d38360` (no rotation),
`dist-0a56c5f0` (heterogeneous verifiers), `resil-776fc650` (no
revocation), `ephem-96d3befb` (7-day TTL, no logout), `auth-b57f022f`
(single-factor account recovery), `conf-fffef009` (excessive claims).

The single highest-leverage fix area. Closing the verifier multi-algo
acceptance and adding rotation tooling are the primary moves; the
session-lifetime and revocation work is the operational follow-up.

### 4.2 The audit-pipeline absence (8 findings)

`nonrep-7fad26d8` (no audit), `nonrep-fa2c351c` (no OTP audit),
`nonrep-304b32af` (no source IP attribution), `nonrep-9faa010e`
(shipping reliability unspecified), `nonrep-c32e3967` (time-source
unspecified), `nonrep-b9ba65ab` (no audit-of-audit), `nonrep-af88acb6`
(no break-glass), `immut-e50364e4` (substrate would be mutable).

The audit pipeline must be designed from first principles, not
retrofitted. The recommendation in `nonrep-7fad26d8` sketches the
schema and emit-points; `immut-e50364e4` provides the substrate
choice (object-lock S3 or hash-chained Postgres audit-table).

### 4.3 The shared-credential cascade (4 findings)

`merged-44bdb663`, `ephem-22c2358c` (no rotation),
`ephem-2c1c7ecf` (no JIT human access), `dist-bc4789b6` (no
NetworkPolicy in Helm).

Together these mean any service compromise yields full datastore
access. Per-service users + Vault dynamic secrets + NetworkPolicy
is the architecturally consistent fix.

### 4.4 The chatbot privileged-proxy (3 findings)

`merged-d2e871f5`, `avail-004444b5` (LLM cost
amplification), `ephem-3ad94819` (per-session key handling
undocumented).

The architectural fix in `merged-d2e871f5` (chatbot acts
under the prompt author's bearer; tool-call allowlist per user role)
is the primary move. Cost amplification and per-session key handling
are secondary hardening.

## 5. Coverage by APD goal

| Tier             | Goal            | Critical | High | Medium | Blocked | Capabilities |
|------------------|-----------------|---------:|-----:|-------:|--------:|-------------:|
| Trustworthiness  | Confidentiality |        1 |    7 |      4 |       3 |            5 |
| Trustworthiness  | Integrity       |        3 |    5 |      2 |       1 |            4 |
| Trustworthiness  | Availability    |        0 |    2 |      7 |       3 |            3 |
| Scalability      | Distributed     |        0 |    2 |      4 |       1 |            3 |
| Scalability      | Resilient       |        0 |    2 |      5 |       2 |            2 |
| Scalability      | Ephemeral       |        0 |    3 |      5 |       1 |            1 |
| Auditability     | Authenticity    |        1 |    3 |      2 |       1 |            2 |
| Auditability     | Non-Repudiation |        0 |    3 |      4 |       2 |            1 |
| Auditability     | Immutability    |        0 |    2 |      5 |       3 |            1 |
| **Totals**       |                 |    **5** |**25**|  **32**|   **20**|       **22** |

Full matrix at `40-synthesis/apd-coverage-matrix.yaml`.

## 6. Capabilities and strengths

This section follows the "scope honesty" discipline — every
capability is recorded with caveats, none is asserted unqualified.

- **Datastores not exposed externally by default compose**
  (`conf-cap-545144bc`). Compose does not publish Postgres/Mongo
  ports. Caveats: Helm NetworkPolicy absent; SSRF on contact_mechanic
  bypasses; shared admin credential defeats segmentation.
- **OpenAPI specification published**
  (`intg-cap-4212a616`). Workshop serves the canonical spec; chatbot
  RAG indexes it. Caveats: spec ≠ enforced schema; no CI gate.
- **OIDC-style RS256 JWT + JWKS publication**
  (`auth-cap-125067f9`). Asymmetric signing means verifiers don't
  hold signing capability. Caveats: default private key in repo;
  verifier accepts multiple algorithms; no rotation procedure.
- **Stateless application tier via JWT**
  (`dist-cap-452d749b`). Session state in bearer token; horizontally
  replicable in principle. Caveats: chatbot per-session state via
  /genai/init; single-host SPOF unresolved.
- **`depends_on: service_healthy` startup gating**
  (`resil-cap-35c0088d`). Healthchecks gate startup. Caveats: checks
  are shallow; Helm equivalents not in input set.
- **Coupon claim-state column** (`intg-cap-a070072a`). Idempotency
  mechanism designed. Caveats: SQL injection defeats the check; no
  DB-level unique constraint backing it.
- **Image version pinning on Postgres+Mongo**
  (`ephem-cap-fd22b084`). Not `:latest`. Caveats: ChromaDB uses
  `:latest`; Mongo 4.4 past upstream EOL; digests not pinned.

Full capability list with maturity ladder placement at
`40-synthesis/deduped-capabilities.yaml`.

## 7. Blocked-on-evidence findings

20 findings (32% of total) are dispositioned `blocked`. Resolving
these requires additional artifacts or operator decisions, not
re-running the gauntlet.

Highest-impact blocked items:

- `conf-b7aaa1e7` — Password storage scheme: requires identity-service
  password-encoder bean review.
- `conf-bd613330` — Encryption at rest: requires deploy substrate
  declaration.
- `conf-5f25ca4e` — TLS configuration policy: requires version floor,
  cipher allowlist, certificate validation policy.
- `avail-8ad04f0e` — Backup/restore procedure: requires deploy intent
  and RPO/RTO target.
- `avail-470902f0` — SLO/SLI declaration: requires production-intent
  determination.
- `avail-4f60016d` — Request-size guard: requires nginx.conf.template
  content.
- `dist-bc4789b6` — NetworkPolicy in Helm: requires shipped values.yaml.
- `resil-01a11294` — Retry policy: requires per-service client wrapper code.
- `resil-592113d0` — Chaos/game-day evidence: requires deploy intent.
- `ephem-6020f861` — OTP TTL precision: requires identity OTP-handler source.
- `auth-c990b0ff` — AAL target: requires deploy intent.
- `nonrep-9faa010e` — Audit shipping reliability: contingent on nonrep-7fad26d8.
- `nonrep-c32e3967` — Time-source policy: contingent on nonrep-7fad26d8.
- `immut-a6c69999` — Backup immutability: contingent on avail-8ad04f0e.
- `immut-c97f668f` — Repo-protected branches: requires upstream repo settings.
- `immut-56949f0a` — Retention policy: requires deploy intent.

Plus 4 more on individual evidence prerequisites. Full list with
prerequisite_evidence on each at
`40-synthesis/deduped-findings.yaml`.

## 8. Severity disagreements and contradictions

No specialist-to-specialist severity disagreements were emitted in
this run; the inputs (especially `prior-audit.md`'s vulnerability
catalog and `threat-model.md`'s STRIDE-mapped impacts) provided
enough shared anchoring that severity calibration was consistent
across the 9 lenses. See `severity-disagreements.yaml`.

No contradictions were emitted. The closest adjacent-lens pair is
on the single-host topology (Distributed: high SPOF vs Availability:
blocked-no-SLO) — these are not contradictions because they cover
different facets of the same architectural decision with explicit
rubric citations. See `contradictions.yaml`.

## 9. Taxonomy coverage

- **CWE:** 38 distinct CWEs cited across 62 findings; CWE-89, CWE-798,
  CWE-915, CWE-918, CWE-347, CWE-639 are the most frequent.
- **OWASP API Top 10 (2023):** All 10 categories present.
  - API1 (BOLA): 3 findings
  - API2 (Broken Auth): 17 findings — the largest category
  - API3 (BOPLA): 7 findings
  - API4 (Unrestricted Resource Consumption): 17 findings
  - API5 (BFLA): 3 findings
  - API6 (Server-Side Request Forgery): 4 findings under business-logic abuse
  - API7 (SSRF — server-side request forgery): 1 merged finding
  - API8 (Security Misconfiguration): 24 findings — second-largest
  - API9 (Improper Inventory Management / Audit gaps): 10 findings
  - API10 (Unsafe Consumption of APIs): 10 findings
- **MITRE ATT&CK:** 13 distinct techniques cited across 7 tactics
  (Initial Access, Privilege Escalation, Defense Evasion, Credential
  Access, Lateral Movement, Collection, Impact). Headline: T1606
  (Forge Web Credentials), T1552.001 (Credentials in Files), T1190
  (Exploit Public-Facing Application), T1213 (Data from Information
  Repositories), T1078 (Valid Accounts).
- **D3FEND:** 1 capability mapping (`auth-cap-125067f9` → D3-IAA),
  countering T1606. Sparse coverage reflects the run's
  capability-light reality.

Full coverage data at `nist-coverage.yaml`, `attack-exposure.yaml`,
`apd-coverage-matrix.yaml`.

## 10. Recommended next steps

Reviewer-priority ordering. Full text in `report-data.yaml`.

1. **Close the JWT trust chain.** Fresh per-install JWKS, pin
   alg:RS256 in every verifier, remove JWT_SECRET, allowlist jku.
   (`merged-c829ffc8`, `ephem-30d38360`, `dist-0a56c5f0`)
2. **Add MFA.** TOTP for users, WebAuthn step-up for admin; declare
   AAL target in `tech_plan.md`. (`auth-0925a719`, `auth-b57f022f`,
   `auth-c990b0ff`)
3. **Fix the BOPLA cluster.** Allowlist serializers on /shop/orders,
   /user/videos/{id}, any user-update path; quantity ≥ 1; server-
   derived unit_price; strip role. (`intg-e7ebcc95`, `intg-62ebf664`,
   `intg-a6b6d147`, `intg-6d98c520`)
4. **Parameterize SQL/Mongo.** Apply_coupon parameterized UPDATE;
   validate-coupon typed-struct unmarshal; CI lint on
   string-concatenated SQL. (`intg-2aeb03f1`, `intg-b7417f91`,
   `intg-ab3edc7a`)
5. **Remove the chatbot's admin credential.** Chatbot acts under
   prompt author's bearer; tool-call allowlist per user role.
   (`merged-d2e871f5`)
6. **Add SSRF defenses on contact_mechanic.** Typed URL allowlist +
   IP-resolution check + per-token rate limit + drop response body.
   (`merged-514507e6`)
7. **Per-service datastore credentials with rotation.** Provision
   per-service Postgres+Mongo users; remove static creds from
   compose; rotate per-deploy. (`merged-44bdb663`,
   `ephem-22c2358c`)
8. **Define audit pipeline.** Schema; emit per consequential action
   with actor attribution; ship to WORM substrate (S3 object-lock).
   (`nonrep-7fad26d8`, `immut-e50364e4`, `nonrep-fa2c351c`,
   `nonrep-304b32af`)
9. **Short-lived sessions.** Drop JWT TTL to 1 hour; introduce
   refresh-token rotation with reuse-detection; expose /logout backed
   by JTI deny-list. (`resil-776fc650`, `ephem-96d3befb`)
10. **Uniform rate limits on auth surfaces.** Every check-otp
    variant, forget-password, login. Increase OTP entropy to
    ≥6 digits. (`avail-e96ad7ff`, `avail-c1ffcf8e`)

## 11. What we did not cover

This advisory focuses on the artifact-grounded review. Specifically:

- The crAPI SPA bundle shipped by `crapi-web` (a separate browser-
  surface review would be needed on the JS build).
- The upstream LLM provider's own security posture (out of scope per
  `threat-model.md` §Scope).
- The upstream supply chain of `chromadb`, `postgres`, `mongo`,
  `mailhog` images (out of scope per same).
- OWASP LLM Top 10 mappings (not declared in the active taxonomy
  set; LLM-surface concerns discussed without `llm_NN` mappings).
- The Phase 5.6 attack-path analysis is a follow-up CLI step (the
  api-security pack declares 8 crown_jewels and 9 attacker_positions
  that feed it; the asset graph for that analysis is at
  `00-context/asset-inventory.yaml`).

## 12. Reference index

- `00-context/context-brief.md` — intake brief (artifact index, data
  inventory, trust boundaries, evidence gaps)
- `00-context/asset-inventory.yaml` — machine-readable asset graph
  for Phase 5.6
- `00-context/threat-model-normalized.yaml` — STRIDE entries
  normalized
- `10-trustworthiness/<goal>.findings.yaml` — tier 1 specialist outputs
- `10-trustworthiness/<goal>.capabilities.yaml`
- `20-scalability/<goal>.findings.yaml` — tier 2 specialist outputs
- `20-scalability/<goal>.capabilities.yaml`
- `30-auditability/<goal>.findings.yaml` — tier 3 specialist outputs
- `30-auditability/<goal>.capabilities.yaml`
- `40-synthesis/deduped-findings.yaml` — authoritative finding set
- `40-synthesis/deduped-capabilities.yaml`
- `40-synthesis/contradictions.yaml`
- `40-synthesis/severity-disagreements.yaml`
- `40-synthesis/nist-coverage.yaml`
- `40-synthesis/attack-exposure.yaml`
- `40-synthesis/apd-coverage-matrix.yaml`
- `40-synthesis/report-data.yaml` — supplementary editorial blocks
  (v1.5.0 emission)
- `40-synthesis/advisory-report.md` — this document

End of advisory report.
