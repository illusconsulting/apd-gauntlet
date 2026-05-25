---
framework_version: 1.0.0
domain_pack: { name: pbm, version: 1.0.0 }
run_id: apd-20260601-claim-event-bus
synthesizer_version: 1.0.0
specialists_skipped: []
---

# APD Gauntlet Advisory Report — Run `apd-20260601-claim-event-bus`

## 1. Executive Summary

This run analyzed a Kafka-based claim event bus design for a PBM system. The architecture introduces PHI flow through Kafka topics, a new audit log, and service-to-service communication patterns. The review identified **16 findings** (2 critical when merged, 8 high, 4 medium, 2 low) and **10 capabilities** across all 9 APD goals.

The most urgent gaps are: (1) PHI in Kafka event payloads protected only at the broker level, (2) the audit log being both unsigned and mutable — a critical merged finding — and (3) DR failover untested for over 12 months. Two blocked findings require additional artifacts before a definitive risk posture can be established: KMS rotation policy and consumer backpressure configuration.

**Recommendation:** Do not promote this system to production until the three required-posture findings are resolved and the two blocked findings are unblocked.

## 2. Confirmed Security Posture

The following capabilities are confirmed as designed or implemented:

- **MSK cluster KMS-managed at-rest encryption** (implemented, via Terraform): Broker-level encryption is in place for all Kafka data at rest.
- **TLS 1.2+ on all Kafka transport paths** (implemented, via Terraform): All producer-broker-consumer communication is encrypted in transit.
- **Field-level envelope encryption on PHI columns** (designed): RDS PHI columns use envelope encryption, though audit_log and Kafka payloads are out of scope.
- **Okta SAML SSO with mandatory MFA** (designed): Internal admin tooling has centralized SSO with MFA enforcement.
- **Multi-AZ active-passive topology** (designed): The system tolerates single-AZ failures within us-east-1.

## 3. Blocked-on-Evidence

Two findings require additional artifacts before a full risk posture can be established:

- `conf-98a543cd`: KMS DEK rotation cadence — no rotation policy document exists.
- `resil-0173b90b`: Consumer-side backpressure — no consumer lag policy or dead-letter topic configuration documented.

These findings are marked `disposition: blocked`. They cannot be resolved or accepted until the prerequisite artifacts are provided.

## 4. Findings

### Critical (merged)

- **`merged-4dd83f6a`** — Audit log is unsigned and stored in a mutable table with no WORM enforcement. Merged from Non-Repudiation (`nonrep-62124087`) and Immutability (`immut-e09e4945`) agents. The combination of no HMAC signing and no WORM enforcement means the audit log cannot serve as reliable evidence in regulatory proceedings.

### High

- `conf-7aa376c5` — PHI fields in Kafka topic lack envelope encryption (gap, required)
- `conf-98a543cd` — KMS DEK rotation cadence not specified (blocked, required)
- `intg-42a3ebbd` — Kafka event messages lack payload signing (gap, required)
- `avail-ce35b2ed` — DR failover not tested in 12 months (gap, required)
- `avail-4e08f6d8` — 99.95% SLO with single-region topology (risk, recommended)
- `dist-d697bb34` — Single-region limits availability under region failure (risk, recommended)
- `ephem-bff0e958` — KMS key rotation disabled in Terraform (gap, required)
- `auth-dbba3dea` — SMS MFA fallback weakens PHI surface auth assurance (risk, required)
- `nonrep-cf99a733` — Audit log omits on-behalf-of user identity (gap, required)

### Medium

- `conf-e443de8b` — Service-to-service shared bearer tokens (risk, recommended)
- `ephem-eb51a236` — Static shared bearer tokens (gap, recommended)
- `auth-8d386c2f` — Service-to-service uses bearer tokens not mTLS (gap, recommended)
- `resil-0173b90b` — Consumer backpressure not specified (blocked, recommended)
- `immut-067a7391` — Backup immutability not specified (blocked, recommended)

## 5. Contradiction Annex

One contradiction was identified:

- `contra-a1b2c3d4`: Confidentiality finding `conf-7aa376c5` asserts PHI in Kafka topics is broker-level only. Capability `conf-cap-89e19793` asserts field-level envelope encryption on PHI columns at rest. These are not contradictory if the scopes are clearly delimited (Kafka vs. RDS), but the capability scope statement should explicitly exclude Kafka payloads to avoid ambiguity.

## 6. Strengths Notwithstanding Gaps

The architecture shows deliberate security thinking in several areas:

- Broker-level KMS encryption is implemented and confirmed via Terraform (not just planned).
- TLS is enforced both client-to-broker and in-cluster, confirmed via IaC.
- HashiCorp Vault is used for secret storage, providing a revocation control plane even if dynamic secrets are not yet leveraged.
- The ADR-001 CAP positioning decision is documented and accepted, showing architectural discipline.

## 7. NIST Coverage Matrix

| Control | Family | Posture | Finding Count | Capability Count |
|---|---|---|---|---|
| SC-8(1) | SC | gapped_and_covered | 3 | 1 |
| SC-12 | SC | gapped | 3 | 0 |
| SC-28 | SC | gapped_and_covered | 1 | 2 |
| AU-9 | AU | gapped | 3 | 0 |
| AU-12 | AU | gapped_and_covered | 2 | 1 |
| IA-2(1) | IA | gapped_and_covered | 1 | 1 |
| CP-4 | CP | gapped | 1 | 0 |
| CP-7 | CP | gapped_and_covered | 2 | 1 |
| SI-7 | SI | gapped | 1 | 0 |
| IA-3 | IA | gapped | 2 | 0 |

Key gap families: AU (audit protection), SC-12 (key management), SI-7 (integrity verification).

## 8. ATT&CK Exposure

| Technique | Name | Tactic | Exposed Findings |
|---|---|---|---|
| T1530 | Data from Cloud Storage | TA0010 | conf-7aa376c5 |
| T1565 | Data Manipulation | TA0040 | intg-42a3ebbd |
| T1621 | MFA Request Generation | TA0006 | auth-dbba3dea |
| T1562 | Impair Defenses | TA0005 | nonrep-cf99a733 |

Highest-priority ATT&CK mitigations: M1041 (Encrypt Sensitive Information) for T1530; M1032 (Multi-factor Authentication) for T1621.

## 9. APD Coverage Matrix

All 9 APD goals have at least one finding for the Kafka claim-events topic component. The ephemeral goal has no capability coverage — only findings — indicating a gap in implemented controls for credential lifecycle management.

The RDS audit_log table has silent coverage for distributed, resilient, ephemeral, and authenticity goals, reflecting the narrow scope of the audit log as a storage artifact rather than a service.

## 10. Severity Disagreement Annex

One severity disagreement was adjudicated by the synthesizer:

- `merged-4dd83f6a`: Non-Repudiation assessed high; Immutability assessed high. Synthesizer chose **critical** because the combined gap means the audit log cannot serve as evidence in HIPAA breach investigations, triggering regulatory breach-notification exposure beyond what either agent's rubric captured individually.
