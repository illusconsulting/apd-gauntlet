# API Security Severity Rubric (impact-to-API-service)

Calibrated against impact-to-the-API-service-and-its-data-subjects, not against generic CVSS. The specialist agent cites the matching clause in finding `detail` fields. Cited examples in each tier are illustrative, not exhaustive. OWASP API Top 10 (2023) categories are referenced inline as API1–API10.

## Critical

Any of the following:

- **Mass PII exfiltration capability** — a realistic attack scenario yields bulk personal data extraction (typically >500 data subjects, but the threshold is the regulator's, not the rubric's). Triggers GDPR Article 33 72-hour breach notification, GDPR Article 34 communication to data subjects when high-risk, state attorney-general notification under US breach-notification statutes, and CCPA §1798.150 statutory damages exposure.
- **Cardholder data exposure within PCI scope** — exposure of PAN with any of {expiry, cardholder name, service code, CAV2/CVC2/CVV2/CID, PIN/PIN block, full magnetic stripe, full track data}. Triggers PCI-DSS forensic investigation, card-brand fines, mandatory cardholder notification, and probable loss of merchant-acquirer status.
- **Authentication bypass to high-privilege functions with no factor required** — OWASP API2 (Broken Authentication) at its sharpest edge. Includes JWT `alg:none` accepted, signature verification skipped, session fixation producing persistent unauthorized access, password-reset bypass that does not require knowledge of the old password or possession of a reset token, and OAuth flows accepting unverified ID tokens.
- **Audit trail loss covering credential or payment events** — renders breach detection and breach-notification obligations un-meetable, renders PCI-DSS Requirement 10 non-compliant, and renders SOC 2 CC7.2 (monitoring of system components for anomalies) un-attestable. Regulators treat absence of audit as presumption of breach.
- **Total auth-service outage** — sustained inability to authenticate any user across the platform; cascading failure to every downstream service. Customer-facing total outage with regulatory and contractual SLA consequences.
- **Forgeable session tokens at platform scope** — signing-key compromise, key-confusion attack (RS256 verified as HS256 using the public key as the HMAC secret), or shared signing key across tenants permitting cross-tenant token forgery. Effectively equivalent to authentication bypass.
- **SQL or NoSQL injection on a PII-bearing endpoint** — direct data exfiltration capability with arbitrary query construction; combine-and-amplify with any logging gap.

## High

Any of the following:

- **BOLA / IDOR exposing PII or payment data bounded to a subset** — OWASP API1 (Broken Object Level Authorization) where the attacker can enumerate identifiers to read other users' data but blast radius is bounded by enumeration rate or non-trivial ID predictability. The dominant real-world API finding class.
- **BFLA exposing admin functions to authenticated low-privilege users** — OWASP API5 (Broken Function Level Authorization). Includes HTTP method swap (POST allowed where only admins should DELETE), undocumented administrative endpoints reachable by regular users, and missing role check on a privilege-altering operation.
- **MFA bypass or weak MFA on PII or payment surfaces** — OWASP API2. SMS fallback that defeats phishing-resistant primary factor, MFA optional on admin surfaces, MFA enrollment endpoint reachable without re-authentication, recovery-code endpoint without rate limiting.
- **BOPLA — excessive property exposure or mass-assignment write-side exposure** — OWASP API3 (Broken Object Property Level Authorization). API responses leak internal fields (`is_admin`, `account_balance`, `internal_user_id`) or accept client-supplied writes to fields the schema should treat as server-managed.
- **Partial audit gap on consequential-action flows** — authentication, authorization, PII access, or payment events logged inconsistently or without actor attribution; impairs incident reconstruction even if breach detection still functions.
- **SSRF reaching internal services or cloud metadata** — OWASP API7 (Server-Side Request Forgery). Severity bounded by what the reachable internal surfaces expose; AWS IMDSv1 reachability is high-trending-critical; bare service-mesh introspection is high.
- **SOC 2 Type I or Type II audit-relevant finding** — control absence in a Trust Services Criteria area an SOC 2 auditor evaluates; absence becomes a qualification on the next service-organization report.
- **OAuth flow accepting implicit grant or missing PKCE on public client** — credential-leakage exposure with a clear migration path; severity is high because exploitation requires only browser-history or referer-leak access.
- **CORS policy with `Access-Control-Allow-Origin: *` plus `Access-Control-Allow-Credentials: true` (or reflective ACAO with credentials)** — cross-origin authenticated read capability; effectively breaks browser same-origin policy on the API.

## Medium

Any of the following:

- **Rate-limiting absent on authentication, password-reset, MFA enrollment, or account-recovery endpoints** — OWASP API4 (Unrestricted Resource Consumption) on the most-abused surfaces. Severity escalates to high if combined with weak credential policy or absent CAPTCHA fallback.
- **API inventory drift — undocumented, deprecated, or unsecured endpoints reachable in production** — OWASP API9 (Improper Inventory Management). Includes shadow APIs in production, deprecated v1 endpoints still routed, staging/test endpoints reachable from production CDN.
- **Unsafe consumption of third-party APIs without response validation** — OWASP API10 (Unsafe Consumption of APIs). Trusting vendor response schemas, accepting vendor-supplied redirects, parsing vendor responses with relaxed JSON/XML parsers.
- **Security misconfiguration with compensating control present** — OWASP API8 (Security Misconfiguration). Default error pages exposing stack traces but WAF redacts; permissive S3 bucket ACL with bucket-level encryption; verbose `Server:` headers without other fingerprintable signals.
- **Logging gap on non-PII operational surfaces** — visibility loss that does not affect breach detection but degrades incident response and capacity planning.
- **Defense-in-depth gap where a single compensating control is the only barrier** — TLS terminates inside the trust boundary so the data tier is in cleartext, single rate-limiter without bot-management fallback, single key wrapping all PII columns.
- **Weak password policy on non-PII surfaces** — minimum length below NIST SP 800-63B guidance, no breached-password check via HIBP-style API, password complexity rules instead of length-and-uniqueness.
- **Hardening weakness exploitable only after adjacent compromise** — requires the attacker to already hold a foothold elsewhere (lateral-only impact). Worth fixing; not catastrophic if deferred.

## Low

Any of the following:

- **Hygiene issue with no realistic exploit path** — deprecated TLS cipher with no client support, redundant control with overlapping coverage, verbose response headers that don't materially aid fingerprinting.
- **Documentation deficiency** — OpenAPI specification drift from implemented behavior in non-security-critical surfaces, runbook formatting inconsistency, naming convention drift.
- **Defense-in-depth gap fully compensated by upstream controls** — useful to know but architecturally non-urgent.
- **Configuration drift on non-production environments** — dev, ephemeral test infrastructure, sandbox tenants without production data.

## Informational

Observations that do not rise to remediation but are worth surfacing for the architecture record. Used sparingly. Examples: notable architectural choices with security implications worth documenting (e.g., chosen JWT library, chosen authorization model), parity gaps with industry peers that are not actually risks, OWASP API Top 10 categories the system meaningfully addresses that the specialist should record as a confirmed capability rather than a finding.

---

## Severity calibration discipline

- **Cite the rubric clause in `detail`.** "This is high severity because it falls under 'BOLA / IDOR exposing PII or payment data bounded to a subset' per the API security rubric, specifically because the `/api/v1/vehicles/{id}` endpoint accepts arbitrary vehicle GUIDs without authorization check, and vehicle GUIDs are recoverable through endpoint X enumeration."
- **Cite the matching OWASP API Top 10 category** when one applies. Multiple categories may apply; cite all that fit (API1 + API3 for an IDOR that also exposes internal fields).
- **Do not average across multiple impacts.** A finding that has critical PII exposure AND medium operational risk is critical.
- **Do not inflate to signal importance.** The synthesizer escalates and reconciles severity disagreements between agents; over-claiming on one agent degrades the cross-agent reconciliation signal.
- **When in doubt, drop one level.** A high-confidence medium is more useful than a low-confidence high. The synthesizer can escalate based on cross-lens corroboration; it cannot reliably de-escalate a confidently-asserted critical.
- **Distinguish capability from exploited.** The rubric scores realistic attack capability, not whether exploitation has been observed. An undisclosed authentication bypass and an actively-exploited one are both critical.
