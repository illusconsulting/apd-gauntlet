# API security required-immutable data classes

For an API-backed system handling PII, payment data, credentials, or session tokens, the following data classes must not change once written. Immutability findings test storage substrate, retention enforcement, and deletion controls against this list.

- **Audit log entries** — regulatory retention varies by anchor. GDPR has no fixed retention for audit, but Article 30 records-of-processing demands defensible retention with documented rationale. PCI-DSS Requirement 10.7 requires 1 year online plus 1 year retrievable archive (effective 2-year retention). SOC 2 typically 1–7 years per service-organization policy. FedRAMP requires 1 year online plus retrievable archive per the agency baseline.
- **Authentication events** — forensic evidence for credential-compromise reconstruction; retention should match or exceed the credential lifetime plus the longest plausible detection window.
- **Payment transactions** — reconciliation, dispute, and chargeback windows. Card networks require 18 months minimum; many merchants retain longer for analytics and risk modeling.
- **OAuth/OIDC consent records** — proof of user consent under GDPR Article 6(1)(a); consent withdrawal does not eliminate the obligation to retain the proof-of-consent for the processing that occurred during the consent window.
- **Data-subject rights request and response records** — GDPR Article 12 obligation to respond and to demonstrate the response. Records of the request, the response, and the records affected.
- **Backup snapshots** — ransomware resilience. Immutability via object-lock, WORM media, or write-locked tape; mutability or deletion-by-single-credential is a finding.
- **Configuration history** — audit and root-cause analysis. Includes RBAC role definitions, ABAC policy bundles, feature-flag state at any point in time, WAF rule sets, TLS configuration.
- **Cryptographic key lifecycle events** — key creation, rotation, revocation, destruction. Required for proving key-management discipline under PCI-DSS Requirement 3.6 and SOC 2 CC6.7.
- **Security incident records** — incident detection, classification, response actions, and closure. Retention typically matches the longest applicable regulatory retention.
- **Code and artifact deployment records** — SBOM, signed image digests, deploy approvals, rollback events. Required for supply-chain attribution and for SLSA-style provenance claims; the deployment record is the link between source-code commit and production behavior at a given time.
- **Webhook receipt records** — when the webhook is a financial event (payment notification, refund, dispute) or a consent event (subscription confirmation). Replays must reconcile against the recorded receipt.
- **Session-token revocation records** — proof that a token was revoked at time T; required when revocation is a security-event boundary (post-breach revocation, mandatory rotation).

Specialists raise Immutability findings against any class on this list that has mutable storage, absent retention controls, deletion-by-single-credential, or unspecified retention. The synthesizer cross-references Non-Repudiation findings on the same data class so the merged record carries both concerns.
