# PBM common patterns — Integrity

These are illustrative templates, not all-inclusive. Use them to calibrate analytical style, severity assignment per the PBM rubric, and NIST/ATT&CK mapping habits. The specialist agent's analytical checklist still drives the actual analysis — this file calibrates how findings and capabilities should look once written.

## Common finding patterns

**Pattern: Event bus messages lack producer signatures; consumers trust payload contents.**
- Severity: high if PHI or adjudication input is involved; medium otherwise
- NIST: SI-7, SI-7(1), SC-8(1), SC-16
- Related concerns: authenticity (producer identity)

**Pattern: Idempotency claimed at API but key derivation is request-body hash.**
- Severity: medium to high depending on adjudication impact (a malicious or accidental change to a single field defeats dedup)
- NIST: SI-10, SI-7
- Detail must call out the specific risk: client retry under transient network failure produces double-adjudication if the body changed between attempts.

**Pattern: NCPDP D.0 transactions accepted without field-level validation beyond standard syntax.**
- Severity: medium (downstream errors, possible adjudication errors)
- NIST: SI-10
- Related concerns: availability (malformed input causing cascading failure)

**Pattern: Formulary configuration is application-managed with no integrity check.**
- Severity: critical to high (corruption affects therapeutic decisions)
- NIST: SI-7(7), CM-3, CM-5
- Related concerns: immutability (historical configuration drift), non_repudiation (who changed configuration)

**Pattern: Tech plan describes "data validation" generically without specifying which fields, what rules, or what error handling.**
- Disposition: blocked or uncertainty
- prerequisite_evidence: "Validation rule specification — fields, rules, error handling, dead-letter policy"

## Common capability patterns

**Pattern: Typed schema (Protobuf or GraphQL) enforced at every service boundary.** Capability scope must enumerate which boundaries are confirmed.

**Pattern: Idempotent claim adjudication keyed by claim ID and submission sequence.** Maturity tied to whether the idempotency window and key retention are specified.

**Pattern: HMAC-signed event payloads on the claim event bus.** Capability scope must specify which topics are confirmed; caveats for any topics not in evidence.

**Pattern: Configuration-as-code for plan rules with reviewed PRs gating changes.** Often `designed` from tech plan; `implemented` or higher requires repository or pipeline evidence.
