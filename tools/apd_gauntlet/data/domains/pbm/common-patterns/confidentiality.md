# PBM common patterns — Confidentiality

These are illustrative templates, not all-inclusive. Use them to calibrate analytical style, severity assignment per the PBM rubric, and NIST/ATT&CK mapping habits. The specialist agent's analytical checklist still drives the actual analysis — this file calibrates how findings and capabilities should look once written.

Confidentiality failure in a PBM is the dominant regulatory-enforcement vector: any PHI disclosure affecting 500 or more members triggers HHS, media, and individual notification under 45 CFR §164.408, and the OCR Resolution Agreement floor for PBM-scale breaches is in the seven figures before plan-sponsor indemnity claims arrive. Beyond PHI, CMS Part D PDE data carries its own confidentiality envelope under the Part D Data Use Agreement, and rebate-tier and MAC pricing are commercially-confidential under most manufacturer and plan-sponsor master service agreements. The load-bearing surfaces are PHI-store reads (claim history, eligibility, PA decisions), member-portal export and EOB-download paths, and every vendor-egress channel — COB, accumulator, rebate aggregator, mail-order fulfillment, and specialty pharmacy.

## ATT&CK + D3FEND defensive mapping

This goal defends against (or is exploited by) the following MITRE ATT&CK techniques. Each citation is included only where the apd-control-mappings high-confidence-bar discipline is met; we deliberately omit techniques that only adjacently relate to this goal.

**ATT&CK techniques:**

- **T1213** (Data from Information Repositories) — bulk PHI repository reads against claim history, member records, PA decisions, formulary data
- **T1530** (Data from Cloud Storage) — backup-store and object-store reads against snapshot archives, PDE batch archives, audit-log archives
- **T1567** (Exfiltration Over Web Service) — PHI export over outbound HTTPS to attacker-controlled endpoints, including legitimate-looking SaaS targets
- **T1041** (Exfiltration Over C2 Channel) — PHI exfiltration via an established C2 channel after initial compromise
- **T1078** (Valid Accounts) — credential-driven PHI access using legitimate but misused authentication material

**D3FEND counters:**

- **D3-MFA** (Multi-factor Authentication) — counters T1078 by requiring additional factor beyond compromised credential
- **D3-OTF** (Outbound Traffic Filtering) — counters T1567 and T1041 by gating outbound flows from the PHI tier
- **D3-NTA** (Network Traffic Analysis) — counters T1041 and T1567 by detecting anomalous outbound volume or destinations
- **D3-LFAM** (Local File Access Mediation) — counters T1213 by enforcing read-mediation at the data tier

## Common finding patterns

**Pattern: Broker-level encryption only on PHI event stream.**

- Severity: typically high (PHI exposure beyond minimum-necessary; broker compromise yields plaintext)
- NIST: SC-8(1), SC-13, SC-28(1)
- ATT&CK: T1530 (Data from Cloud Storage) with specific rationale

**Pattern: Single KEK protecting heterogeneous data classes.**

- Severity: typically medium (defense-in-depth gap; key compromise broader than necessary)
- NIST: SC-12, SC-12(1)
- Related concerns: ephemeral (rotation cadence amplification)

**Pattern: PHI displayed unmasked by default in admin UI.**

- Severity: high (critical when the admin role can affect >500 members or >1 plan sponsor per the severity rubric Critical clause)
- NIST: AC-3, AC-6, SC-28
- Related concerns: non_repudiation (unmask audit), authenticity (admin identity assurance)

**Pattern: Service-to-service inside cluster relies on network-level trust, payloads contain PHI.**

- Severity: high (PHI exposure beyond minimum-necessary via lateral movement)
- NIST: SC-8(1), SC-23, IA-3
- ATT&CK: T1557 with specific rationale on in-cluster observer

**Pattern: Tech plan describes encryption-in-transit generically without specifying TLS version or cipher suite policy.**

- Disposition: blocked when no artifact establishes the masking discipline; uncertainty when one artifact references it but the implementation discipline is not enumerated
- Severity: typically medium when blocked, deferred when uncertainty
- prerequisite_evidence: "TLS configuration policy — (1) minimum TLS version per ingress (pharmacy NCPDP, member portal, admin console, vendor egress, CMS outbound); (2) cipher-suite allowlist per ingress; (3) certificate-pinning configuration for pharmacy-network ingress and outbound CMS submission; (4) HSTS enforcement on member-facing surfaces; (5) certificate rotation cadence and CA-trust policy; (6) certificate-revocation handling (OCSP stapling, CRL refresh interval); (7) configuration source-of-truth pointer (Terraform module, NGINX config, ALB listener) and CD pipeline applying it"

## Common capability patterns

**Pattern: Field-level envelope encryption on PHI columns.** Maturity ladder depends on evidence — `designed` for tech plan only; `implemented` requires a config or IaC reference; `tested` requires a test report; `operationalized` requires runbook plus monitoring.

**Pattern: KMS hierarchy with separated DEK/KEK roles.** Capability scope: "Confirmed for [data stores X, Y]. Not addressed: [data store Z, audit log, backups]." Caveats expected.

**Pattern: mTLS across service mesh.** Maturity higher when evidence includes service mesh configuration; `designed` when tech plan asserts intent.

## prerequisite_evidence

When a confidentiality finding is dispositioned `blocked-on-evidence`, the prerequisite_evidence ask must name every sub-element the operator needs to produce to unblock — not a single noun phrase. The seeds below calibrate the depth expected of asks emitted by the Confidentiality specialist. The TLS configuration ask above is the in-line example on the generic-encryption-in-transit pattern; the KMS and field-level seeds below cover the next two most common blocked dispositions.

**KMS hierarchy:** (1) root key location (HSM-backed CMK, customer-managed key, vendor-managed key); (2) KEK (key-encrypting key) hierarchy diagram; (3) DEK (data-encrypting key) rotation cadence per data class; (4) KEK-to-data-class mapping (PHI store, PDE archive, backup store, audit store); (5) key access-control policy (who can use, who can rotate, who can disable); (6) key-material backup and escrow policy.

**Field-level encryption:** (1) per-PHI-field encryption status at rest, in transit, in use; (2) tokenization map for fields not directly encrypted; (3) field-decryption authorization-decision pipeline (who can decrypt, under what authorization); (4) decryption-event audit chain feeding the Non-Repudiation surface.
