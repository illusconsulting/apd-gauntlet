---
framework_version: 1.0.0
run_id: apd-20260601-claim-event-bus
domain_pack: { name: pbm, version: 1.0.0 }
artifacts:
  - { filename: tech_plan.md,               type: tech_plan }
  - { filename: claim-events.proto,         type: code }
  - { filename: threat-model.md,            type: threat_model }
  - { filename: adr-001-cap-positioning.md, type: adr }
  - { filename: iac/kafka.tf,               type: iac }
---

# APD Gauntlet Context Brief — Run `apd-20260601-claim-event-bus`

## 1. Artifact Index

| Filename | Type | Notes |
|---|---|---|
| `tech_plan.md` | tech_plan | Claim event bus design, anchor artifact |
| `claim-events.proto` | code | Wire schema for the event payload |
| `threat-model.md` | threat_model | Abbreviated STRIDE on the topic |
| `adr-001-cap-positioning.md` | adr | CAP positioning decision |
| `iac/kafka.tf` | iac | MSK cluster Terraform |

## 2. Capability and Surface Summary

A new Kafka-based event bus emits claim adjudication events to downstream consumers. The change touches the adjudication path and the audit log. PHI flows through the event payloads.

## 3. PHI/PII Data Inventory

| Field | Class | Source | Destinations | Transformations |
|---|---|---|---|---|
| `member_id` | PHI identifier | NCPDP D.0 → claim ingestion | claims DB, claim-events topic, audit log | None |
| `drug_ndc` | PHI clinical | NCPDP D.0 → claim ingestion | claims DB, claim-events topic, audit log | None |
| `prescriber_npi` | PHI clinical | NCPDP D.0 → claim ingestion | claims DB, claim-events topic, audit log | None |
| `pharmacy_id` | PHI clinical | NCPDP D.0 → claim ingestion | claims DB, claim-events topic, audit log | None |

## 4. Trust Boundary Map

| Boundary | Auth | Encryption |
|---|---|---|
| Edge → application | OAuth + MFA | TLS 1.3 |
| Application → Kafka | mTLS | TLS 1.2+ in transit; broker-level at rest |
| Application → RDS | DB user | TLS in transit; field-level envelope encryption on PHI columns |
| Service ↔ service | Shared bearer token | TLS |

## 5. Evidence Gaps

- KMS hierarchy referenced but rotation cadence, automation, and revocation NOT specified (tech_plan.md §3).
- Audit log table mentioned but format and retention NOT specified (tech_plan.md §5.2).
- DR failover not tested in last 12 months (tech_plan.md §6).
