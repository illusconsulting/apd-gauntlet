# PBM common patterns — Integrity

These are illustrative templates, not all-inclusive. Use them to calibrate analytical style, severity assignment per the PBM rubric, and NIST/ATT&CK mapping habits. The specialist agent's analytical checklist still drives the actual analysis — this file calibrates how findings and capabilities should look once written.

Integrity in a PBM is the bridge between data and physical dispensing: a corrupted claim-adjudication response can authorize the wrong drug, the wrong quantity, or the wrong copay at the pharmacy counter, and PDE-submission integrity under 42 CFR §423.322 is what CMS audits against for Part D reconciliation, rebate true-up, and risk-adjustment payment accuracy. Formulary configuration is similarly load-bearing — a silent tier or PA-criteria mutation propagates as a clinical-decision defect across the entire dispensing network within the next refresh cycle. The most consequential surfaces are NCPDP D.0 and SCRIPT transaction handlers (request and response), PDE batch files and their reconciliation deltas, and the formulary editor with its publish-and-fanout pipeline.

## ATT&CK + D3FEND defensive mapping

This goal defends against (or is exploited by) the following MITRE ATT&CK techniques. Each citation is included only where the apd-control-mappings high-confidence-bar discipline is met; we deliberately omit techniques that only adjacently relate to this goal.

**ATT&CK techniques:**

- **T1565.001** (Stored Data Manipulation) — at-rest tampering of formulary, PA-criteria, DUR-rule, MAC-pricing, or claim history stores
- **T1565.002** (Transmitted Data Manipulation) — in-flight tampering of NCPDP D.0 messages, X12 transactions, or PDE batch files
- **T1556** (Modify Authentication Process) — bypassing write-path authorization by altering the auth decision that gates formulary, PA, or claim mutations

**D3FEND counters:**

- **D3-MAN** (Message Authentication) — counters T1565.002 on NCPDP / X12 / PDE signed messages via per-message signature verification
- **D3-FIM** (File Integrity Monitoring) — counters T1565.001 by monitoring at-rest formulary, PA-criteria, MAC-pricing, and PDE-batch files for unauthorized modification before consumption by adjudication or fanout

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
- prerequisite_evidence: "Validation rule specification covering (1) the field-level rules for each cross-boundary message (NCPDP D.0 segments, X12 270/271/837/835 transactions, internal RPC contracts); (2) the enforcement point where validation runs (gateway, service edge, data tier); (3) the failure-handling behavior on rule violation (reject, quarantine, log-and-pass); (4) the dead-letter policy including retention, replay, and alerting; and (5) the schema-version negotiation policy across PBM, switch operator, and CMS"

## Common capability patterns

**Pattern: Typed schema (Protobuf or GraphQL) enforced at every service boundary.** Capability scope must enumerate which boundaries are confirmed.

**Pattern: Idempotent claim adjudication keyed by claim ID and submission sequence.** Maturity tied to whether the idempotency window and key retention are specified.

**Pattern: HMAC-signed event payloads on the claim event bus.** Capability scope must specify which topics are confirmed; caveats for any topics not in evidence.

**Pattern: Configuration-as-code for plan rules with reviewed PRs gating changes.** Often `designed` from tech plan; `implemented` or higher requires repository or pipeline evidence.

## prerequisite_evidence

When a tech plan or design document leaves an integrity concern under-specified, the specialist agent should emit a blocked-on-evidence finding whose `prerequisite_evidence` asks for the full multi-clause specification — not a single-line generic ask. The seeds below calibrate the expected depth.

**Schema enforcement:** (1) the canonical schema for each cross-boundary message (NCPDP D.0 segments, X12 270/271/837/835 transactions, internal RPC contracts); (2) the schema-validation enforcement point (gateway, service edge, data tier) for each message class; (3) the schema-validation failure-handling behavior on violation (reject, quarantine, log-and-pass) and the corresponding alerting; and (4) the schema-version negotiation policy across PBM, switch operator, and CMS so version drift cannot silently degrade validation.

**Write-path authorization:** (1) the authorization-decision pipeline for each PHI-writing endpoint (formulary publish, PA-criteria mutation, claim-history backfill, eligibility override); (2) the actor identity and role evaluation at each step in the pipeline; (3) the audit event emitted on grant and on deny, with the fields that allow non-repudiation reconstruction; and (4) the failure mode when the authorization service is unavailable — fail-closed is required for PHI write paths and any fail-open posture must be explicitly justified.

**Tamper detection:** (1) the HMAC or signed-payload protection applied to cross-boundary state-changing messages, including the key-management posture for the signing key; (2) the content-hash verification performed on PDE submission batches and the storage location of the expected hash; and (3) the integrity-check failure handling and the corresponding incident-response playbook, including who is paged, what is quarantined, and how downstream adjudication is held until the failure is resolved.
