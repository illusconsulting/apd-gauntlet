# Identity security common patterns — Distributed

These are illustrative templates, not all-inclusive. Use them to calibrate analytical style, severity assignment per the identity security rubric, and NIST/ATT&CK mapping habits. The specialist agent's analytical checklist still drives the actual analysis — this file calibrates how findings and capabilities should look once written.

## Common finding patterns

**Pattern: Single-AZ deployment of the IdP application tier, the session store, or the signing-key backend (HSM/KMS).**

- Severity: high (the single AZ is the failure domain for the entire platform's authentication; a zonal incident produces total auth outage for every downstream RP)
- NIST: SC-7, CP-7, SC-36
- Cross-reference: any Availability finding on SLO consistency; the merged finding carries both the topology constraint and the SLA consequence

**Pattern: Session-store replication lag affects MFA-challenge consistency — user MFA-enrolls in region A, immediately authenticates in region B, MFA-required flag has not propagated.**

- Severity: medium to high (security-relevant inconsistency; the user can briefly bypass MFA via region race; severity escalates when the inconsistency window exceeds typical authentication latency)
- NIST: SC-36, SI-7, IA-2(1)
- Related concerns: authenticity (MFA enforcement consistency), resilient (region-failover behavior)

**Pattern: CAP positioning for credential changes unspecified — when network partitions split the IdP topology, the artifacts do not specify whether the system prefers consistency (reject auth on minority partition) or availability (accept auth on minority partition with stale credentials).**

- Disposition: blocked
- Severity: medium when blocked, high when "availability wins" is documented without compensating controls
- prerequisite_evidence: "Multi-region consistency policy for credential mutations — behavior of password changes, MFA-enrollment changes, and account-suspension during a partition; replication-conflict resolution policy; tombstone propagation for account deletion under partition"

**Pattern: Data residency for personal data unstated — artifacts describe multi-region capability without specifying which user populations or tenants are bound to which regions.**

- Disposition: uncertainty or blocked
- prerequisite_evidence: "Data-residency policy — per-tenant region binding, lawful-basis attestation for any cross-EEA flow (SCCs, adequacy decision, BCRs), residency-enforcement mechanism (application-tier routing, database-level constraints), and the audit-log residency posture (does EU-user audit stay in EU?)"

**Pattern: Multi-region topology asserted but failover behavior unspecified — active-active vs. active-passive vs. standby, write-conflict policy on the credential store, failover trigger, RTO/RPO targets.**

- Disposition: uncertainty or blocked
- Severity: medium when blocked
- prerequisite_evidence: "Multi-region topology specification — active configuration, write-conflict policy for the credential store and the session store, failover trigger, expected failover RTO/RPO per data class, and which data classes replicate cross-region (audit yes; credentials yes; ephemeral PKCE state typically no)"

**Pattern: Cross-region replication for the audit log is asynchronous with unspecified lag.**

- Severity: medium to high (cross-references Non-Repudiation; audit gap during regional failover is a breach-detection blind spot — and the IdP's audit is the highest-stakes audit on the platform)
- NIST: AU-9(2), SC-36
- Related concerns: non_repudiation, immutability

**Pattern: Session affinity / sticky sessions on the IdP load balancer because state is in-process (interactive auth flow state cached in pod memory).**

- Severity: medium to high (impairs horizontal scale, deploy-time rolling restarts produce mid-flow session loss, AZ failover invalidates all in-flight authentications)
- NIST: SC-7, CP-7, SC-36
- Related concerns: ephemeral (in-process state undermines the immutable-infra story)

**Pattern: Service mesh topology unspecified — artifacts assert mTLS between IdP components without describing workload-identity issuance, certificate rotation, or trust-domain boundary between the IdP namespace and other namespaces.**

- Disposition: uncertainty
- prerequisite_evidence: "Service-mesh topology — workload identity issuance (SPIFFE/SPIRE, cloud-native), trust-domain boundary between IdP namespace and adjacent service namespaces, certificate lifetime and rotation cadence, mesh-to-non-mesh edge behavior (legacy LDAP backend not in mesh)"

## Common capability patterns

**Pattern: Multi-region active-active IdP with regional HSMs, regional session stores, and stateless application tier.** Capability scope must specify which dependencies are also multi-region (credential store, audit pipeline, federation-trust store) and which are single-region by design.

**Pattern: Region-pinned credential storage with explicit cross-region replication policy and per-tenant residency binding.** Higher maturity requires evidence of the policy enforcement mechanism (database-level residency, application-tier routing) plus residency monitoring on egress.

**Pattern: Session-store replication topology documented with replication-lag SLO and MFA-consistency rule (e.g., "MFA-enrollment writes are synchronously replicated to the user's home region before /authorize returns").** Cross-cuts Authenticity.

**Pattern: Service mesh with SPIFFE workload identity and per-namespace trust-domain isolation around the IdP backend.** Cross-cuts Authenticity for the identity-issuance half; mention via `related_concerns`. The IdP namespace should be a distinct trust domain from RP-tier namespaces.

**Pattern: Cross-region audit replication synchronous with bounded lag SLO; regional failover preserves audit continuity.** Cross-cuts Non-Repudiation; the audit replication is the highest-priority cross-region replicated data class.
