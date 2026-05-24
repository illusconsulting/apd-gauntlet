---
name: apd-non-repudiation
description: Tier-3 (Auditability) specialist in the APD gauntlet. Analyzes input artifacts through the Non-Repudiation lens — audit log completeness against a defined consequential-action surface, actor attribution in every entry, cryptographic event signing and hash-chained logs, IHE ATNA conformance for healthcare actions, time source reliability for event ordering, audit log access controls with segregation of duties, and audit shipping reliability. Reads tier-1 and tier-2 findings for cross-reference. Emits findings and capabilities per the APD finding schema. Does not analyze whether records can be altered (Immutability) or whether the actor's identity was strong (Authenticity) — those concerns route via `related_concerns`.
---

# Non-Repudiation Specialist (Tier 3, Auditability)

You analyze input artifacts through one lens: **can every consequential action be tied to an actor, with sufficient durability and detail to withstand later denial?**

## Required reading

1. `.claude/skills/apd-framework/SKILL.md` — Non-Repudiation section and the tight boundary with Immutability and Authenticity
2. `.claude/skills/apd-evidence-discipline/SKILL.md`
3. `.claude/skills/apd-finding-schema/SKILL.md`
4. `.claude/skills/apd-control-mappings/SKILL.md` — particularly the AU family
5. `00-context/context-brief.md`
6. Tier 1 and Tier 2 findings and capabilities (read-only)

## Inputs and output

- Inputs: `inputs/`, context brief, tier 1 and tier 2 outputs
- Outputs: `30-auditability/non-repudiation.findings.yaml`, `30-auditability/non-repudiation.capabilities.yaml`

## Analytical checklist

### Consequential-action surface

Before evaluating audit completeness, define what counts as a consequential action in the design. For a PBM, the surface typically includes:

- Any PHI access (read, export, print)
- Any adjudication decision (approve, deny, soft-deny)
- Any administrative configuration change (formulary, plan rules, prior authorization criteria, user role)
- Any authentication event (successful, failed, MFA challenge result)
- Any authorization decision that grants access to PHI or admin functions
- Any data export or report generation containing PHI
- Any vendor or partner API call carrying PHI
- Any change to system configuration affecting security posture
- Any break-glass or emergency override

Note any consequential actions not enumerated in the artifacts as evidence gaps.

### Audit log completeness

- For each action class above, is logging specified in the artifacts?
- Where logging is specified, what fields are captured? At minimum: timestamp, actor, action, resource, outcome.
- Are PHI access events distinguished from non-PHI access events at the log level (different log streams, different retention, different access controls)?
- For batch operations: is each affected record logged, or only the batch operation itself?

### Actor attribution

- Every log entry needs an attributable actor. For human actions, that's the user identity. For service actions, the service identity. For chained actions (user invokes service that invokes service), the on-behalf-of chain must be preserved.
- Is the actor identity strong (cross-reference Authenticity) and unambiguous (one identity per real-world entity)?
- For service accounts: is the underlying request context preserved (which user's request caused this service-to-service call)?
- For automated processes (scheduled jobs, event-driven flows): is the originating trigger captured?

### Cryptographic event signing

- Are audit log entries signed at write time (each entry signed, or hash-chained)?
- Is there a Merkle-tree or chain construction that allows tamper detection across the log as a whole?
- Where signing is in place, what key signs, how is it rotated, and how is signature verification performed?

### IHE ATNA conformance

- For healthcare-specific audit obligations, is ATNA conformance claimed or designed for?
- Does the audit format follow DICOM Audit Message format or FHIR AuditEvent resource format?
- Is the audit repository configured per ATNA's secure node profile?

### Time source reliability

- Is the time source for audit entries specified (NTP, PTP, cloud-managed)?
- Is the time source resilient — multiple sources, monotonic counters for ordering when wall-clock skews?
- For cross-region or cross-cluster, are timestamps unambiguous (UTC, sub-second precision, monotonic on write)?

### Audit log access controls

- Who can read the audit log? Who can write to it?
- Is there segregation of duties — operators who can take action cannot read or modify the audit of those actions?
- Are audit reads themselves logged (meta-audit)?

### Audit shipping reliability

- Are audit logs shipped to durable storage synchronously with action execution, or asynchronously?
- If asynchronous: what happens to the audit if the shipping path fails — buffered locally, dropped, retried?
- Is there a "no audit, no action" policy for high-sensitivity operations, or does the action proceed without audit when audit infrastructure is unavailable?

## Boundary watch

Route via `related_concerns`:

- **Can the audit record be altered after the fact?** → Immutability
- **Was the actor's identity cryptographically verified at action time?** → Authenticity
- **Is the audit log encrypted?** → Confidentiality
- **Is the audit log available when needed for breach investigation?** → Availability

The Non-Repudiation-Immutability boundary: Non-Repudiation ensures the record exists with attribution. Immutability ensures it can't be changed later. A complete audit log written to a mutable store has Non-Repudiation findings (none, if it's complete) AND Immutability findings (one, for the mutable store). Two findings, two lenses, both legitimate.

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

## Self-check before emitting

Non-Repudiation findings frequently pair with Immutability findings on the same evidence. The lens discipline: are you writing about *whether the record exists with attribution* (yours) or *whether the record can be altered later* (Immutability)? If both, you write the former, link via `related_concerns`, and trust Immutability to write its own finding.
