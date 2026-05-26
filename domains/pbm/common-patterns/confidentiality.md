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
