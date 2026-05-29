# PBM common patterns — Non-Repudiation

These are illustrative templates, not all-inclusive. Use them to calibrate analytical style, severity assignment per the PBM rubric, and NIST/ATT&CK mapping habits. The specialist agent's analytical checklist still drives the actual analysis — this file calibrates how findings and capabilities should look once written.

Non-repudiation in a PBM is a direct regulatory obligation, not a defense-in-depth nice-to-have. HIPAA Security Rule §164.312(b) (Audit Controls) requires actor-attributed records of activity on systems containing PHI, and §164.528 (Accounting of Disclosures) requires the PBM to produce defensible disclosure records to members on request — both fail open if the audit chain attributes actions to a shared system account, a sidecar identity, or an unbound session. CMS Part D PDE submission additionally requires auditable provenance for every claim record reconciled against rebate and risk-adjustment payments. The load-bearing surfaces are the PHI-access audit (record-level, not table-level), the PA-decision audit (which clinician, on which member, with what override rationale), and the configuration-change audit (formulary, PA criteria, MAC list, contract pricing).

## ATT&CK + D3FEND defensive mapping

This goal defends against (or is exploited by) the following MITRE ATT&CK techniques. Each citation is included only where the apd-control-mappings high-confidence-bar discipline is met; we deliberately omit techniques that only adjacently relate to this goal.

**ATT&CK techniques:**

- **T1070** (Indicator Removal) — audit-log deletion, retention shortening, or shipping-pipeline disable
- **T1036** (Masquerading) — audit-attribution falsification, including action attribution to a shared service-account rather than the human operator
- **T1562.008** (Impair Defenses: Disable or Modify Cloud Logs) — cloud-native audit-pipeline suppression

**D3FEND counters:**

- **D3-LFAM** (Local File Access Mediation) — counters T1070 by enforcing write-deny on the audit substrate
- **D3-MAN** (Message Authentication) — counters T1036 by binding the audit record to a per-actor signature

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
- prerequisite_evidence: "Time-source reliability specification — (1) authoritative time source (NTP server or NTS source), naming the upstream and topology; (2) clock-skew SLO with numeric bound; (3) clock-drift monitoring and remediation procedure (who is paged when drift exceeds SLO, and how the audit pipeline is quarantined); (4) timestamp inclusion in audit records (UTC, monotonic, or both) with the field name and precision"

**Pattern: Break-glass procedure exists but break-glass actions are not specially audited beyond normal logging.**

- Severity: medium to high
- NIST: AU-3, AU-12(1), AC-6(9)

## Common capability patterns

**Pattern: Per-action PHI access audit with actor, resource, purpose, and outcome captured.** Scope must specify which surfaces are confirmed; caveats for any out-of-evidence.

**Pattern: Cryptographically signed audit entries hash-chained per stream.** Maturity depends on whether the chain is described in tech plan only or implemented in code/IaC.

**Pattern: ATNA-conformant audit format for clinical actions.** Often `designed` from tech plan; higher maturity requires implementation evidence.

**Pattern: Audit log read access gated by separate role from operational roles, with read events themselves audited.** Cross-cuts Authenticity for the role definition.

## prerequisite_evidence

When a non-repudiation finding is blocked-on-evidence, the operator must supply the following multi-clause specifications to unblock. Single-line answers ("we have audit logging") are insufficient; each clause below names a sub-element the synthesizer expects to see resolved before the finding's disposition can move off blocked.

**Audit-coverage matrix:**

  (1) consequential-action surface mapped to audit-event taxonomy (each consequential action emits at least one audit event of the named class, with the mapping enumerated rather than asserted);
  (2) actor-attribution policy on each audit event class (which identity claim is captured, and whether it resolves to a human operator versus a shared service principal);
  (3) signing or hash-chaining mechanism per class (algorithm, key custody, and chain-verification cadence);
  (4) audit-shipping pipeline (queue, transit, sink) with availability target (numeric SLO and what happens to the action when the pipeline is degraded);
  (5) audit-of-audit pipeline (audit reads, retention changes, log-shipping disable) on a forensically isolated channel (named substrate, separate IAM, and separate retention floor);
  (6) retention-floor enforcement substrate per class (the technical control that prevents an operator from shortening retention below the regulatory floor).

**Time-source reliability:**

  (1) authoritative time source (NTP server or NTS source), naming the upstream and topology;
  (2) clock-skew SLO with numeric bound;
  (3) clock-drift monitoring and remediation procedure (who is paged when drift exceeds SLO, and how the audit pipeline is quarantined);
  (4) timestamp inclusion in audit records (UTC, monotonic, or both) with the field name and precision.

**Audit-access segregation:**

  (1) read access policy on the audit substrate (who can query, against which retention window, and with what query-audit obligation);
  (2) separation of audit-read and audit-write privileges from operator-action privileges (no role that performs consequential actions may also redact, retire, or query its own audit trail);
  (3) audit-of-audit emitter capturing every administrative read (with actor, query, and result-set fingerprint) on a forensically isolated channel.
