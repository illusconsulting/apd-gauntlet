---
name: apd-domain
description: Active domain pack content — severity rubric, consequential actions, common patterns. Generated from a domain pack at build time; do not edit by hand.
metadata:
  pack: pbm
  pack_version: 1.0.0
  framework_version: 1.0.0
  generated: 2026-05-25T00:37:50Z
---


## Source: `severity-rubric.md`

# PBM Severity Rubric (impact-to-PBM)

Calibrated against impact-to-PBM, not against generic CVSS. The specialist agent cites the matching clause in finding `detail` fields. Cited examples in each tier are illustrative, not exhaustive.

### Critical

Any of the following:

- **PHI exfiltration capability affecting >500 members** in a single realistic attack scenario. Triggers HIPAA breach notification per 45 CFR §164.408 (federal, state, and media notification). The 500-member threshold is the legal pivot point for required public disclosure.
- **Claim adjudication corruption affecting therapeutic decisions** — wrong drug dispensed, wrong dose, missed Drug Utilization Review (DUR) alert, formulary bypass that exposes patients to harmful drug interactions, missed prior authorization on safety-gated drugs. Direct patient harm risk.
- **Authentication bypass to PHI surfaces or admin functions** — no factor required, or trivially circumventable factor. Includes session fixation that produces persistent unauthorized access.
- **Audit trail loss covering PHI access** — renders breach detection and notification obligations un-meetable, regulatory non-compliance independent of breach occurrence.
- **Total adjudication outage exceeding contractual SLA** — sustained inability to adjudicate claims affecting all plan sponsors simultaneously.
- **Loss of CMS Part D submission integrity** — PDE (Prescription Drug Event) data submission failures or corruption that exposes the PBM to CMS enforcement action.

### High

Any of the following:

- **PHI exposure beyond minimum-necessary internal audience** — violates 45 CFR §164.502(b). Includes overbroad role assignments, missing field-level controls on PHI elements, or admin tooling that exposes more PHI than the operator's role requires.
- **Claim adjudication errors bounded to a subset** — single plan sponsor, single drug class, single channel (mail order vs retail), or single member population. Erroneous adjudication but blast radius is contained.
- **Authentication weakness short of bypass** — MFA bypass requiring adjacent factor, credential reuse window exceeding policy, session lifetime exceeding policy, weak password requirements on a PHI surface.
- **Partial audit gap on PHI-adjacent surfaces** — admin actions logged but lacking actor attribution, audit logs shipped without integrity protection, audit retention shorter than 6 years (HIPAA minimum).
- **Adjudication degradation with manual workaround required** — system functional but requires operator intervention to complete claims, sustained.
- **CMS Part D compliance gap not affecting member dispensing** — formulary update lag, prior authorization workflow gap, transition fill logic gap, that does not currently affect a dispensing decision but is required by CMS-4201-F or equivalent.
- **URAC accreditation-relevant gap** — control absence in a domain URAC evaluates, where the absence would be findable in an accreditation audit.

### Medium

Any of the following:

- **Defense-in-depth gap where a compensating control exists** but is the only barrier — single point of control failure. Encryption at rest absent because TLS terminates inside the trust boundary is the canonical example.
- **Recoverable adjudication delay within SLA** — performance regression that the SLO budget absorbs but consumes headroom.
- **Logging gap on non-PHI surfaces** — operational visibility loss that does not affect breach detection.
- **Hardening weakness exploitable only after adjacent compromise** — requires the attacker to already have a foothold elsewhere. Useful to fix; not catastrophic if deferred.
- **Configuration drift detection gap** on systems where compensating attestation exists.
- **Documentation gap with security-relevant content missing** — architecture decision records, runbooks, or threat models absent in ways that impair operations or future review.

### Low

Any of the following:

- **Hygiene issue with no realistic exploit path** — deprecated cipher with no client support, redundant control with overlapping coverage, configuration verbosity.
- **Documentation deficiency** — non-security-critical content missing, formatting inconsistency, naming convention drift.
- **Defense-in-depth gap fully compensated** by upstream controls — useful to know but architecturally non-urgent.
- **Configuration drift on non-critical path** — dev environment, ephemeral test infrastructure.

### Informational

Observations that do not rise to remediation but are worth surfacing for the architecture record. Used sparingly. Examples: notable architectural choices with security implications worth documenting, parity gaps with industry peers that are not actually risks.

---

## Severity calibration discipline

- **Cite the rubric clause in `detail`.** "This is high severity because it falls under 'PHI exposure beyond minimum-necessary internal audience' per the impact-to-PBM rubric, specifically [reasoning]."
- **Do not average across multiple impacts.** A finding that has critical PHI exposure AND medium operational risk is critical.
- **Do not inflate to signal importance.** The synthesizer escalates and reconciles severity disagreements between agents; over-claiming on one agent degrades the cross-agent reconciliation signal.
- **When in doubt, drop one level.** A high-confidence medium is more useful than a low-confidence high.


## Source: `consequential-actions.md`

# PBM consequential-action surface

For a PBM, the following actions are consequential and must be auditable. Non-Repudiation findings evaluate logging coverage against this list.

- Any PHI access (read, export, print)
- Any adjudication decision (approve, deny, soft-deny)
- Any administrative configuration change (formulary, plan rules, prior authorization criteria, user role)
- Any authentication event (successful, failed, MFA challenge result)
- Any authorization decision that grants access to PHI or admin functions
- Any data export or report generation containing PHI
- Any vendor or partner API call carrying PHI
- Any change to system configuration affecting security posture
- Any break-glass or emergency override

This list is not exhaustive. Specialists should treat actions outside this list as candidates for inclusion — flagging them as evidence gaps until the operator confirms.


## Source: `immutability-classes.md`

# PBM required-immutable data classes

For a PBM, the following data classes must not change once written:

- Audit log entries (HIPAA 6-year retention, SOC 2 audit trail)
- Claim adjudication outcomes (regulatory and contractual reconcilability)
- Submitted CMS PDE records (CMS submission integrity)
- Backups (ransomware resilience)
- Configuration history (change traceability, RCA evidence)
- Signed agreements and consent records
- Member communications and notifications (proof of delivery)
- Prior authorization decisions
- Drug formulary historical state at point of adjudication

Specialists raise Immutability findings against any class on this list that has mutable storage or absent retention controls.


## Source: `data-taxonomy.md`

# PBM PHI/PII data taxonomy

Specialist agents treat the following fields as PHI when they appear in artifacts. The intake brief's PHI/PII inventory MUST enumerate every field; missing fields become evidence gaps.

## PHI identifiers (per 45 CFR §164.514)

- member_id (HICN, MBI, PBM-internal)
- member_dob
- member_address (street, city, ZIP — full ZIP+4 is PHI)
- member_email
- member_phone
- SSN
- account numbers
- biometric identifiers

## PHI clinical data

- drug_ndc (National Drug Code)
- prescriber_npi
- pharmacy_id
- diagnosis codes (ICD-10)
- prior authorization criteria responses
- clinical notes

## PII (non-PHI personally identifying)

- internal user accounts (PBM employee identities)
- plan sponsor contact information

## Financial

- claim payment instructions
- copay calculations
- premium amounts

## Out of scope

- aggregate analytics with k-anonymity ≥ 5
- de-identified per Safe Harbor (45 CFR §164.514(b)(2))

This taxonomy is consulted by Confidentiality, Integrity, and Non-Repudiation specialists. The intake agent enumerates fields by reading artifacts against this list.


## Source: `common-patterns/confidentiality.md`

# PBM common patterns — Confidentiality

These are illustrative templates, not all-inclusive. Use them to calibrate analytical style, severity assignment per the PBM rubric, and NIST/ATT&CK mapping habits. The specialist agent's analytical checklist still drives the actual analysis — this file calibrates how findings and capabilities should look once written.

## Common finding patterns

These are illustrative templates, not all-inclusive. Use them to calibrate analytical style and severity.

**Pattern: Broker-level encryption only on PHI event stream.**
- Severity: typically high (PHI exposure beyond minimum-necessary; broker compromise yields plaintext)
- NIST: SC-8(1), SC-13, SC-28(1)
- ATT&CK: T1530 (Data from Cloud Storage) with specific rationale

**Pattern: Single KEK protecting heterogeneous data classes.**
- Severity: typically medium (defense-in-depth gap; key compromise broader than necessary)
- NIST: SC-12, SC-12(1)
- Related concerns: ephemeral (rotation cadence amplification)

**Pattern: PHI displayed unmasked by default in admin UI.**
- Severity: high to critical depending on scope of admin role
- NIST: AC-3, AC-6, SC-28
- Related concerns: non_repudiation (unmask audit), authenticity (admin identity assurance)

**Pattern: Service-to-service inside cluster relies on network-level trust, payloads contain PHI.**
- Severity: high (PHI exposure beyond minimum-necessary via lateral movement)
- NIST: SC-8(1), SC-23, IA-3
- ATT&CK: T1557 with specific rationale on in-cluster observer

**Pattern: Tech plan describes encryption-in-transit generically without specifying TLS version or cipher suite policy.**
- Disposition: uncertainty or blocked depending on what else the artifacts say
- Severity: typically medium when blocked, deferred when uncertainty
- prerequisite_evidence: "TLS configuration policy — version floor, cipher suite list, certificate validation behavior"

## Common capability patterns

**Pattern: Field-level envelope encryption on PHI columns.** Maturity ladder depends on evidence — `designed` for tech plan only; `implemented` requires a config or IaC reference; `tested` requires a test report; `operationalized` requires runbook plus monitoring.

**Pattern: KMS hierarchy with separated DEK/KEK roles.** Capability scope: "Confirmed for [data stores X, Y]. Not addressed: [data store Z, audit log, backups]." Caveats expected.

**Pattern: mTLS across service mesh.** Maturity higher when evidence includes service mesh configuration; `designed` when tech plan asserts intent.


## Source: `common-patterns/integrity.md`

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


## Source: `common-patterns/availability.md`

# PBM common patterns — Availability

These are illustrative templates, not all-inclusive. Use them to calibrate analytical style, severity assignment per the PBM rubric, and NIST/ATT&CK mapping habits. The specialist agent's analytical checklist still drives the actual analysis — this file calibrates how findings and capabilities should look once written.

## Common finding patterns

**Pattern: Adjudication latency target not stated, but contractual SLA exists.**
- Severity: high (cannot verify the system meets contractual obligation)
- NIST: CP-2, CP-2(3)
- Detail must enumerate the contracts the SLA appears in, per intake brief.

**Pattern: DR RTO stated as 4 hours but no tested failover procedure documented.**
- Severity: high (RTO is aspirational without test evidence)
- NIST: CP-2, CP-4 (contingency plan testing), CP-7

**Pattern: Single-region deployment with 99.95% availability target.**
- Severity: high (target likely undeliverable from single region)
- NIST: CP-7, SC-36
- Related concerns: distributed (this finding's recommendation will point to a topology change owned by Distributed)

**Pattern: Vendor dependency (e.g. eligibility lookup) has no stated SLA in artifacts.**
- Disposition: blocked or uncertainty
- prerequisite_evidence: "Vendor SLA for [vendor name] eligibility service"

**Pattern: Health checks specified as TCP port checks only.**
- Severity: medium (shallow health checks mask real degradation)
- NIST: SI-13, CP-10

## Common capability patterns

**Pattern: Multi-AZ deployment of the adjudication engine with cross-AZ failover.** Scope must specify which components are multi-AZ; caveats for any that are not.

**Pattern: Backup encryption with daily verification.** Maturity ladder: `designed` from tech plan, `implemented` requires backup configuration, `operationalized` requires backup test runbook and last-test date.

**Pattern: SLO and error budget framework for the claim adjudication path.** Often `designed` from tech plan; higher maturity requires monitoring dashboard evidence.


## Source: `common-patterns/distributed.md`

# PBM common patterns — Distributed

These are illustrative templates, not all-inclusive. Use them to calibrate analytical style, severity assignment per the PBM rubric, and NIST/ATT&CK mapping habits. The specialist agent's analytical checklist still drives the actual analysis — this file calibrates how findings and capabilities should look once written.

## Common finding patterns

**Pattern: Stateful component (e.g. Valkey, RDS primary) in single AZ.**
- Severity: high (PBM SLA contracts typically require AZ resilience)
- NIST: SC-7, CP-7, SC-36
- Cross-reference: any Availability finding on SLO consistency

**Pattern: Hidden SPOF in CI/CD — emergency deployment depends on single pipeline.**
- Severity: medium to high depending on RTO sensitivity
- NIST: CM-2(2), CP-2
- Related concerns: ephemeral (immutable infra readiness for redeployment)

**Pattern: Tech plan claims multi-region but artifacts don't specify topology — active-active versus active-passive versus standby.**
- Disposition: uncertainty or blocked
- prerequisite_evidence: "Multi-region topology specification — active configuration, write conflict policy, failover trigger"

**Pattern: Cross-region replication for audit logs is asynchronous with unspecified lag.**
- Severity: medium to high (cross-references Non-Repudiation tier 3)
- NIST: AU-9(2), SC-36
- Related concerns: non_repudiation, immutability

**Pattern: Adjudication CAP positioning unstated.**
- Disposition: uncertainty
- Detail: in pharmacy adjudication, the CAP choice has clinical consequences (continuing to adjudicate with stale formulary versus stopping adjudication). The artifacts must state the choice.

## Common capability patterns

**Pattern: Multi-AZ active-active adjudication engine with automated AZ failover.** Scope must specify which dependencies are also multi-AZ (database, cache, broker) and which are not.

**Pattern: Read replica topology across AZ with bounded replication lag.** Capability requires specifying the replication-lag bound and what enforces it.

**Pattern: Stateless application tier with all state externalized.** Maturity ladder typically `designed` from tech plan; `implemented` requires service configuration or IaC evidence.


## Source: `common-patterns/resilient.md`

# PBM common patterns — Resilient

These are illustrative templates, not all-inclusive. Use them to calibrate analytical style, severity assignment per the PBM rubric, and NIST/ATT&CK mapping habits. The specialist agent's analytical checklist still drives the actual analysis — this file calibrates how findings and capabilities should look once written.

## Common finding patterns

**Pattern: No circuit breaker on PHI-containing vendor call (eligibility, drug pricing).**
- Severity: high (vendor degradation can cascade to total adjudication outage)
- NIST: SI-13, SC-5, CP-13
- Cross-reference: any Availability finding on vendor SLA

**Pattern: Retry policy without jitter on the event bus consumer.**
- Severity: medium (thundering herd risk on partial broker failure)
- NIST: SI-13(4), SC-5(1)

**Pattern: Timeout missing on database call in adjudication path.**
- Severity: high (single slow query can hang adjudication threads, cascading to thread pool exhaustion)
- NIST: SI-13, SC-5

**Pattern: No graceful degradation specified for eligibility vendor outage.**
- Severity: high (vendor outage produces total adjudication outage)
- NIST: CP-12, CP-13, SI-17
- Detail must specify what would happen today (system errors) and what should happen (cached eligibility, fail-open with downstream verification, or explicit soft-deny with patient communication).

**Pattern: Tech plan describes "retries" without specifying backoff, jitter, or budget.**
- Disposition: uncertainty
- prerequisite_evidence: "Retry policy specification — backoff curve, jitter, total budget per dependency, idempotency interaction"

## Common capability patterns

**Pattern: Circuit breaker on every external dependency with documented thresholds.** Capability scope must enumerate which dependencies are covered; caveats for any not in evidence.

**Pattern: Read-only degraded mode for portal during write-tier outage.** Maturity ladder: `designed` from tech plan, `implemented` requires application code or feature flag evidence, `tested` requires test report or game day evidence.

**Pattern: Bulkheaded thread pools separating adjudication from reporting.** Often higher confidence when application configuration is in evidence.


## Source: `common-patterns/ephemeral.md`

# PBM common patterns — Ephemeral

These are illustrative templates, not all-inclusive. Use them to calibrate analytical style, severity assignment per the PBM rubric, and NIST/ATT&CK mapping habits. The specialist agent's analytical checklist still drives the actual analysis — this file calibrates how findings and capabilities should look once written.

## Common finding patterns

**Pattern: Service account credentials are static long-lived secrets in application config.**
- Severity: high (broad blast radius on credential leak, no automatic invalidation)
- NIST: IA-5, IA-5(1), IA-5(7), SC-12(1)
- ATT&CK: T1078 (Valid Accounts) with sub-technique by environment

**Pattern: Database credentials shared across services; no rotation.**
- Severity: high
- NIST: IA-5, AC-2(2)
- Related concerns: confidentiality (key management around the shared credential)

**Pattern: Production access via standing admin role with no JIT.**
- Severity: high (excessive standing privilege, no time-boxing)
- NIST: AC-6, AC-2(2), AC-2(3)
- Related concerns: non_repudiation (audit of admin actions), authenticity (admin identity strength)

**Pattern: Container images mutable in production — `:latest` tags, in-place container updates.**
- Severity: medium to high depending on what's mutable
- NIST: CM-2, CM-3, SA-15(7)
- Related concerns: authenticity (image signing), integrity (configuration drift)

**Pattern: Tech plan mentions "secrets stored in vault" without rotation specifics.**
- Disposition: uncertainty or blocked
- prerequisite_evidence: "Secret rotation policy — cadence, mechanism, automation, exception process"

**Pattern: Member portal session lifetime not specified.**
- Disposition: uncertainty
- prerequisite_evidence: "Session management policy — max lifetime, idle timeout, step-up bounds, logout behavior"

## Common capability patterns

**Pattern: Dynamic database credentials via vault.** Maturity depends on whether tech plan asserts (designed) or vault configuration is in evidence (implemented).

**Pattern: Workload identity via SPIFFE for service-to-service authentication.** Caveats expected on which services are confirmed.

**Pattern: JIT access for production via approval workflow with time-boxed grants.** Operational maturity requires runbook evidence; designed maturity from tech plan only.

**Pattern: Immutable container deployment via signed image references in IaC.** Cross-cuts Authenticity for the signing aspect; Ephemeral confirms the replace-don't-patch posture.


## Source: `common-patterns/authenticity.md`

# PBM common patterns — Authenticity

These are illustrative templates, not all-inclusive. Use them to calibrate analytical style, severity assignment per the PBM rubric, and NIST/ATT&CK mapping habits. The specialist agent's analytical checklist still drives the actual analysis — this file calibrates how findings and capabilities should look once written.

## Common finding patterns

**Pattern: Service-to-service inside cluster uses shared secret tokens, not mTLS.**
- Severity: high (lateral movement amplification)
- NIST: SC-8(1), SC-23, IA-3
- ATT&CK: T1557 with specific in-cluster rationale
- Related concerns: ephemeral (shared-secret rotation), confidentiality (in-cluster PHI in transit)

**Pattern: MFA bypass via SMS fallback on PHI surfaces.**
- Severity: high (effective AAL downgrade)
- NIST: IA-2(1), IA-2(2), IA-2(8)
- ATT&CK: T1621 (Multi-Factor Authentication Request Generation) with rationale

**Pattern: Container images deployed without signature verification.**
- Severity: high (supply chain compromise vector)
- NIST: SI-7, SR-4, SR-11
- Related concerns: ephemeral (immutable infra requires authentic images)

**Pattern: Webhook payloads from vendor accepted without signature verification.**
- Severity: high (forged webhook can inject malicious adjudication input)
- NIST: SC-23, IA-3(1), SI-10
- Related concerns: integrity (input validation, route to Integrity finding for the malformed-input concern)

**Pattern: SBOM not generated; no vulnerability attribution path.**
- Severity: medium to high depending on regulatory commitments
- NIST: SR-4, SR-4(3), SR-11

**Pattern: Tech plan describes "authenticated APIs" generically.**
- Disposition: uncertainty or blocked
- prerequisite_evidence: "API authentication specification — mechanism (OAuth, mTLS, signed JWT), token lifetime, validation procedure"

## Common capability patterns

**Pattern: mTLS across service mesh with SPIFFE identity.** Scope must enumerate which services are confirmed; expect caveats for legacy services not yet onboarded.

**Pattern: FIDO2/WebAuthn for internal admin access to PHI surfaces.** Cross-cuts Ephemeral via the credential lifetime; mention via `related_concerns`.

**Pattern: Signed container images with admission control enforcement.** Maturity depends on whether admission policy is in evidence.

**Pattern: SLSA Level 2 build provenance for production deployments.** Higher maturity requires CI/CD configuration evidence.


## Source: `common-patterns/non-repudiation.md`

# PBM common patterns — Non-Repudiation

These are illustrative templates, not all-inclusive. Use them to calibrate analytical style, severity assignment per the PBM rubric, and NIST/ATT&CK mapping habits. The specialist agent's analytical checklist still drives the actual analysis — this file calibrates how findings and capabilities should look once written.

## Common finding patterns

**Pattern: Admin configuration changes logged but actor attribution is system account, not the human operator.**
- Severity: high (configuration corruption is not attributable; URAC and SOC 2 expose)
- NIST: AU-3, AU-3(1), AU-12, AU-10
- Related concerns: authenticity (admin identity strength), immutability (configuration history)

**Pattern: PHI access logging present but only at table/service level, not record level.**
- Severity: high (minimum-necessary attestation impaired)
- NIST: AU-2, AU-3
- Detail: HIPAA Security Rule and minimum-necessary doctrine require attribution at the level needed to prove appropriate use, not just access.

**Pattern: Audit shipping is fire-and-forget; consumer-side failure produces silent loss.**
- Severity: high
- NIST: AU-4, AU-5
- Related concerns: availability (audit pipeline reliability), immutability (durability of the audit)

**Pattern: No cryptographic protection on audit entries; mutable database table.**
- Severity: high
- NIST: AU-9, AU-9(2), AU-9(3)
- Related concerns: immutability (this finding's recommendation will couple to an immutability finding)

**Pattern: Time source unspecified.**
- Disposition: uncertainty
- prerequisite_evidence: "Audit time source specification — NTP topology, drift bounds, fallback"

**Pattern: Break-glass procedure exists but break-glass actions are not specially audited beyond normal logging.**
- Severity: medium to high
- NIST: AU-3, AU-12(1), AC-6(9)

## Common capability patterns

**Pattern: Per-action PHI access audit with actor, resource, purpose, and outcome captured.** Scope must specify which surfaces are confirmed; caveats for any out-of-evidence.

**Pattern: Cryptographically signed audit entries hash-chained per stream.** Maturity depends on whether the chain is described in tech plan only or implemented in code/IaC.

**Pattern: ATNA-conformant audit format for clinical actions.** Often `designed` from tech plan; higher maturity requires implementation evidence.

**Pattern: Audit log read access gated by separate role from operational roles, with read events themselves audited.** Cross-cuts Authenticity for the role definition.


## Source: `common-patterns/immutability.md`

# PBM common patterns — Immutability

These are illustrative templates, not all-inclusive. Use them to calibrate analytical style, severity assignment per the PBM rubric, and NIST/ATT&CK mapping habits. The specialist agent's analytical checklist still drives the actual analysis — this file calibrates how findings and capabilities should look once written.

## Common finding patterns

**Pattern: Audit log written to a mutable RDS table; no append-only enforcement.**
- Severity: high (audit log alteration breaks HIPAA accountability; combines with any Non-Repudiation gap)
- NIST: AU-9, AU-9(2), AU-9(3), AU-11
- Cross-reference: any Non-Repudiation finding on audit completeness; the merged or linked record carries both concerns

**Pattern: Backup retention policy meets minimum but no object lock applied.**
- Severity: high (backups vulnerable to ransomware deletion)
- NIST: CP-9, CP-9(1), CP-9(8), MP-4
- Related concerns: availability (backup recoverability)

**Pattern: Configuration is partly IaC, partly manual; no drift detection.**
- Severity: medium to high depending on what's manually managed
- NIST: CM-2, CM-2(2), CM-3, CM-6
- Related concerns: integrity (configuration correctness), authenticity (signed-commit posture)

**Pattern: Configuration repository allows history rewrite (no protected branches).**
- Severity: medium to high
- NIST: CM-3, CM-3(1), SI-7(8)
- Related concerns: authenticity (signed commits provide attribution but mutable history defeats it)

**Pattern: Formulary configuration history not retained — only current state stored.**
- Severity: high (adjudication decisions cannot be reconstructed against the formulary at decision time; defends regulatory and litigation positions)
- NIST: CM-2(3), AU-11
- Related concerns: non_repudiation (linking decisions to their inputs)

**Pattern: Retention duration not specified in artifacts.**
- Disposition: uncertainty or blocked
- prerequisite_evidence: "Retention policy — duration per data class, regulatory citation, enforcement mechanism, legal-hold override"

## Common capability patterns

**Pattern: S3 object lock with compliance mode on backup buckets, retention period set to regulatory minimum.** Scope must specify which buckets are confirmed.

**Pattern: Hash-chained audit log with daily chain-head anchored to an external trust domain.** Cross-cuts Non-Repudiation; mention via `related_concerns`.

**Pattern: GitOps-driven configuration with signed commits and protected branches.** Maturity ladder: `designed` from tech plan; `implemented` requires repository configuration or pipeline evidence.

**Pattern: Formulary versioning with snapshot-at-decision retention on every adjudication.** Higher maturity requires schema or implementation evidence.
