# APD Gauntlet Context Brief — Run `<run-id>`

> Produced by `apd-intake` from the artifacts in `runs/<run-id>/inputs/`.
> All specialist agents consume this brief. Do not paraphrase; refer back here for canonical references.

**Run id:** `<run-id>`
**Date:** `YYYY-MM-DD`
**Artifact count:** `<n>`
**Artifact types observed:** tech_plan, prd, code, iac, threat_model, ...

---

## 1. Artifact Index

| Filename | Type | Pages/Lines | Notes |
|----------|------|-------------|-------|
| `tech_plan.md` | tech_plan | 47 sections | Primary architectural design for the change |
| `claim-events.proto` | code | 89 lines | Protocol buffer schema for the new event bus topic |
| `infra/atmos/components/kafka/` | iac | 14 files | Terraform/Atmos manifests for the Kafka cluster |
| `threat-model-v3.md` | threat_model | 12 pages | Engineering team's threat model, not yet reviewed |
| ... | | | |

---

## 2. Capability and Surface Summary

**What is being built or changed.**
One paragraph describing the architectural intent. Identify the change boundary
clearly — what is new, what is modified, what is touched but unchanged.

**In-scope components.**
- Component A — purpose, owner team
- Component B — purpose, owner team
- ...

**Out-of-scope components mentioned in artifacts.**
- Component X — referenced in §X.X as a dependency; not modified by this change
- ...

**External systems touched.**
- Vendor Y — for purpose Z
- Internal service W — owned by team T
- ...

**Data classes in flow.**
- PHI — specifically: member demographics, claim transactions, prescriber data
- PII — internal user accounts, plan sponsor contact info
- Financial — claim payment instructions
- Operational telemetry — metrics, traces, logs

**User personas.**
- Member — accesses portal and mobile app
- Plan sponsor administrator — accesses B2B portal
- Internal operations — accesses admin tooling
- Vendor integration — submits NCPDP D.0 transactions

**Adjudication impact.**
Explicit statement: does this change affect the claim adjudication path?
If yes: how. If no: "No adjudication path impact per [evidence pointer]."

---

## 3. PHI/PII Data Inventory

> If no PHI/PII is in scope, state explicitly here with an evidence pointer and skip the table.

| Field | Class | Source | Destinations | Transformations |
|-------|-------|--------|--------------|-----------------|
| `member_id` | PHI identifier | NCPDP D.0 transaction (field AM01) | claims DB, claim-events Kafka topic, audit log | None |
| `drug_ndc` | PHI clinical | NCPDP D.0 transaction (field 407-D7) | claims DB, claim-events Kafka topic, formulary lookup, audit log | None |
| `prescriber_npi` | PHI clinical | NCPDP D.0 transaction (field 411-DB) | claims DB, claim-events Kafka topic, prescriber lookup, audit log | None |
| `member_dob` | PHI demographic | member portal registration | member_demographics DB | Encrypted at field level per tech_plan.md §5.3 |
| ... | | | | |

> If the tech plan does not enumerate data elements explicitly, populate this table from the schema artifacts (proto, FHIR, X12) and note in section 6.

---

## 4. Trust Boundary Map

| Boundary | Crosses | Upstream trust | Downstream trust | Auth posture | Encryption posture |
|----------|---------|----------------|------------------|--------------|--------------------|
| Internet → edge | Data, control | Untrusted | Edge-trusted (post-WAF) | OAuth + MFA | TLS 1.3 |
| Edge → application tier | Data, control | Edge-trusted | Internal-trusted | Cookie-based session | TLS 1.2+ (per §X.X) |
| Application → claims DB | Data | Internal-trusted | DB-trusted | DB user with role | TLS in transit; encryption at rest per §5.3 |
| Application → Kafka | Data | Internal-trusted | Broker-trusted | SASL or mTLS (see §4.2) | TLS in transit; broker-level at rest |
| Application → eligibility vendor | Data | Internal-trusted | Vendor-trusted | Vendor API key | TLS 1.2+ |
| Backup tier ← production | Data | Production-trusted | Backup-trusted | IAM role | Customer-managed KMS |
| ... | | | | | |

---

## 5. Evidence Gaps

These items are not in the input artifacts and would be required for a complete architectural picture. Specialist agents draw from this list when populating `prerequisite_evidence` on `blocked` findings.

- **KMS hierarchy and DEK rotation policy.** Tech plan §3.1 names the KMS but does not specify DEK lifetime, rotation cadence, or rotation automation.
- **TLS configuration policy.** Multiple sections reference "TLS"; no policy document specifies minimum version, cipher suite allow-list, or certificate validation behavior.
- **Service-to-service authentication design.** Internal service calls described in §4.4 do not specify whether mTLS, signed JWTs, or shared secrets are used.
- **Audit log schema and retention.** §6.1 mentions audit logging; format, retention period, storage tier, and access controls not specified.
- **Vendor SLAs.** Eligibility vendor (§4.6) and drug pricing vendor (§4.7) are named but their SLAs are not in artifacts.
- **Session management policy.** Member portal session lifetime, idle timeout, and step-up bounds not specified.
- **Disaster recovery RTO/RPO.** §7 references "DR capability" but does not state RTO, RPO, or last-tested date.
- ...

---

## 6. Per-Goal Relevance Table

Specialist agents use this table to decide which artifacts to deep-read versus skim.

| Artifact | Conf | Intg | Avail | Dist | Resil | Ephem | Auth | NonRep | Immut |
|----------|------|------|-------|------|-------|-------|------|--------|-------|
| `tech_plan.md` | primary | primary | primary | primary | primary | primary | primary | primary | primary |
| `claim-events.proto` | primary | primary | unlikely | unlikely | unlikely | unlikely | primary | secondary | unlikely |
| `infra/atmos/components/kafka/` | secondary | secondary | secondary | primary | secondary | secondary | secondary | secondary | secondary |
| `threat-model-v3.md` | secondary | secondary | secondary | secondary | secondary | secondary | secondary | secondary | secondary |
| ... | | | | | | | | | |

Legend: `primary` (this artifact is a primary source for this goal), `secondary` (likely supporting evidence), `unlikely` (no obvious material).

---

## 7. Notes for Specialists

Free-form section for the intake agent to flag anything specialists should know that doesn't fit the structured sections above. Example:

> The threat model `threat-model-v3.md` is dated three months before this tech plan and predates the Kafka topology decision in §4.2. Specialists should weight tech plan content over threat model content where they conflict.

> The PRD mentions a "PHI unmasking flow" (line 47) that is not addressed in the tech plan. Confidentiality and Non-Repudiation specialists should consider this an evidence gap unless a separate unmasking-flow document is provided.
