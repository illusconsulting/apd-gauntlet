# API security common patterns — Integrity

These are illustrative templates, not all-inclusive. Use them to calibrate analytical style, severity assignment per the API security rubric, and NIST/ATT&CK mapping habits. The specialist agent's analytical checklist still drives the actual analysis — this file calibrates how findings and capabilities should look once written.

## Common finding patterns

**Pattern: Mass assignment — endpoint deserializes the entire request body to the domain object without an explicit allowlist (OWASP API3 write-side, BOPLA).**

- Severity: high to critical depending on which fields can be written (writeable `is_admin`, `account_balance`, `role`, `order_status`, `coupon_amount` is critical; writeable display preferences is medium)
- NIST: SI-10 (information input validation), AC-3, SI-15
- ATT&CK: T1190 (Exploit Public-Facing Application); T1078 (Valid Accounts) when mass assignment yields privilege escalation
- Related concerns: confidentiality (read-side BOPLA on the same endpoints), authenticity (privilege-relevant fields enabling identity forgery)

**Pattern: Webhook signature verification missing or optional on inbound integrations.**

- Severity: high (forged webhook can inject malicious adjudication input — refund triggers, payment confirmations, subscription state changes)
- NIST: SI-7, SI-10, SC-23, IA-3(1)
- ATT&CK: T1190; T1071 (Application Layer Protocol) for the forged-request path
- Related concerns: authenticity (signature verification is the identity-assertion mechanism; mapping cross-cuts)

**Pattern: JWT signature verification skipped, `alg:none` accepted, or algorithm confusion possible (RS256 verified as HS256 using the public key).**

- Severity: critical (forgeable tokens at platform scope — see Critical rubric clause on session-token forgery)
- NIST: SI-7, IA-2, IA-5(2), SC-13
- ATT&CK: T1550.001 (Use Alternate Authentication Material: Application Access Token); T1606 (Forge Web Credentials)
- Related concerns: authenticity (token-issuance trust chain), ephemeral (token lifetime amplifies impact)

**Pattern: Idempotency missing on payment, refund, or order-mutation endpoints; double-submit produces duplicate side effects.**

- Severity: high (financial integrity at risk; combine with rate-limit gap for amplification)
- NIST: SI-10, SC-5
- Related concerns: availability (retry storms triggering duplicate side effects), resilient (client retry policy interaction)

**Pattern: Schema enforcement bypassed by polymorphic deserialization — `type` field on input controls which subclass is instantiated.**

- Severity: high (gadget-chain or unexpected-type vulnerabilities; CVE-class issues like Jackson polymorphic deserialization)
- NIST: SI-10, SI-3
- ATT&CK: T1190; T1059 when deserialization yields code execution
- Related concerns: authenticity (unexpected type enabling impersonation), confidentiality (gadget chains reaching sensitive surfaces)

**Pattern: SQL or NoSQL query construction uses string concatenation or unsafe template interpolation.**

- Severity: critical when on a PII-bearing endpoint, high otherwise
- NIST: SI-10, SI-10(5)
- ATT&CK: T1190; T1213 (Data from Information Repositories)
- Related concerns: confidentiality (data exfiltration), non_repudiation (injection often bypasses application-tier audit)

**Pattern: Tech plan describes "input validation" generically without specifying schema, which fields, what error handling, or rejection-on-fail behavior.**

- Disposition: blocked or uncertainty
- prerequisite_evidence: "Input validation specification — schema source (OpenAPI, JSON Schema, code-first), per-field validation rules, behavior on validation failure (reject vs. coerce vs. log), and dead-letter or quarantine policy for invalid messages"

## Common capability patterns

**Pattern: OpenAPI- or JSON-Schema-driven request validation at the edge, with reject-on-fail behavior.** Capability scope must enumerate which endpoints are confirmed; caveats for any not under schema enforcement.

**Pattern: Allowlist-based deserialization for mutating endpoints, with server-managed fields explicitly stripped from input.** Maturity tied to whether the allowlist is centralized (framework-level) or per-endpoint (drift risk).

**Pattern: Idempotency-key handling on all financial mutating endpoints with the key window and storage durability specified.** Higher maturity requires evidence of the idempotency store's own durability and replay-window enforcement.

**Pattern: JWT validation pinned to a specific algorithm with the verification key rotated through a JWKS endpoint.** Maturity ladder: `designed` from tech plan; `implemented` requires verification-library configuration evidence; `operationalized` requires JWKS rotation runbook evidence.
