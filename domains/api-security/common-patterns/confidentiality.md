# API security common patterns — Confidentiality

These are illustrative templates, not all-inclusive. Use them to calibrate analytical style, severity assignment per the API security rubric, and NIST/ATT&CK mapping habits. The specialist agent's analytical checklist still drives the actual analysis — this file calibrates how findings and capabilities should look once written.

## Common finding patterns

**Pattern: API response includes excessive properties — internal fields leak to clients (OWASP API3 read-side, BOPLA).**

- Severity: typically high (PII or authorization-relevant fields exposed; combine-and-amplify when `is_admin`, `internal_user_id`, `account_balance`, or video file paths leak)
- NIST: SC-8, AC-3, AC-4, SI-15 (information output filtering)
- ATT&CK: T1530 (Data from Cloud Storage Object) when the leaked field unlocks bucket access; T1213 (Data from Information Repositories) for general property exposure
- Related concerns: integrity (write-side mass assignment of the same fields commonly co-occurs), authenticity (leaked `is_admin` flags often enable authentication-bypass chains)

**Pattern: Service-to-service traffic inside the cluster relies on network-level trust; payloads contain PII or session tokens.**

- Severity: high (PII exposed to any in-cluster observer; lateral-movement amplification)
- NIST: SC-8, SC-8(1), SC-23, IA-3
- ATT&CK: T1557 (Adversary-in-the-Middle) with specific rationale on in-cluster observer; T1040 (Network Sniffing) for compromised-node case
- Related concerns: authenticity (mTLS provides the identity half; this finding's recommendation should couple to an Authenticity capability), distributed (service-mesh topology)

**Pattern: PII appears in application logs, error responses, or stack traces.**

- Severity: high if production logs are widely accessible or shipped to a SaaS log aggregator; medium if logs are tightly scoped
- NIST: SI-11 (error handling), AU-3, AC-4
- ATT&CK: T1213 with specific rationale on log-aggregator search interface
- Related concerns: non_repudiation (audit content sensitivity inheritance — see data-taxonomy), authenticity (log-aggregator access controls)

**Pattern: JWT carries excessive claims — full PII profile embedded in access tokens.**

- Severity: medium to high depending on token lifetime and audience scope (a 1-hour bearer token carrying email, full name, and DOB exposes that PII to every downstream service, log aggregator, and proxy in the request path)
- NIST: SC-8, AC-4, SC-28
- Related concerns: ephemeral (token-lifetime amplification of claim exposure), integrity (over-broad claims defeat least-privilege downstream)

**Pattern: Backup artifacts unencrypted at rest, or encrypted with a key the primary-store team controls.**

- Severity: high (backups frequently the weakest crown jewel; key-separation failure means primary-store compromise yields backup compromise)
- NIST: SC-28, SC-28(1), CP-9, CP-9(8), SC-12
- ATT&CK: T1530 (Data from Cloud Storage Object); T1567.002 (Exfiltration to Cloud Storage) when backups are exfiltrated as a unit
- Related concerns: immutability (backup mutability), ephemeral (backup-key rotation cadence)

**Pattern: Tokenization claimed for cardholder data but detokenization vault accessible from the application tier.**

- Severity: high (PCI scope collapse claimed but not delivered; the detokenization path is the de facto cardholder-data path)
- NIST: SC-28, SC-12, AC-3, AC-6
- Related concerns: ephemeral (detokenization credentials and rotation), authenticity (workload identity to the vault)

**Pattern: Tech plan describes "encryption in transit" generically without specifying TLS version floor, cipher suite policy, or certificate validation behavior on outbound connections.**

- Disposition: uncertainty or blocked
- Severity: typically medium when blocked, deferred when uncertainty
- prerequisite_evidence: "TLS configuration policy — version floor (TLS 1.2 minimum, 1.3 preferred), cipher suite allowlist, certificate-validation behavior on outbound, mTLS topology if claimed, certificate-pinning posture for mobile clients"

## Common capability patterns

**Pattern: Field-level envelope encryption on PII columns with KMS-managed DEKs.** Maturity ladder depends on evidence — `designed` for tech plan only; `implemented` requires a config or IaC reference; `tested` requires a test report; `operationalized` requires runbook plus rotation monitoring.

**Pattern: Response field-filtering by role with explicit allowlist per endpoint (anti-BOPLA read-side).** Capability scope: "Confirmed for endpoints [X, Y]. Not addressed: [Z]." Caveats expected; the absence of an allowlist on any endpoint converts the capability to a finding.

**Pattern: mTLS across the service mesh with SPIFFE/SPIRE workload identity.** Maturity higher when service-mesh configuration is in evidence; `designed` when tech plan asserts intent without topology.

**Pattern: Tokenized payment instruments with detokenization gated by a separate trust zone.** Higher maturity requires evidence of vault network segmentation, separate IAM, and per-detokenization audit.
