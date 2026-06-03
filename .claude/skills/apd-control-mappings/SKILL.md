---
name: apd-control-mappings
description: Reference for emitting NIST SP 800-53r5 control mappings and MITRE ATT&CK technique mappings on APD gauntlet findings and capabilities. Use this whenever you need to populate the `control_mappings` block — to determine which 800-53r5 control families and enhancements apply to a finding in your lens, when ATT&CK technique mapping meets the high-confidence bar, and how to write defensible mapping rationales. Covers the per-APD-goal control family guidance and the ATT&CK mapping discipline that prevents shotgun mapping.
---

# Control Mappings

Every finding and capability emits NIST SP 800-53r5 control mappings. ATT&CK technique mappings are emitted only when the agent can write a specific one-sentence rationale.

## NIST 800-53r5 mapping guidance

The control families below are the primary candidates for each APD goal. This is not an exhaustive crosswalk — agents apply judgment based on the specific finding, and should consult the full catalog when a non-listed control is more apt.

Use enhancement notation when an enhancement is the right citation: `SC-8(1)` for "Cryptographic Protection" under "Transmission Confidentiality and Integrity", not just `SC-8`.

### Confidentiality

Primary families: **SC** (System and Communications Protection), **AC** (Access Control), **MP** (Media Protection).

Common citations:

- `SC-8`, `SC-8(1)` — transmission confidentiality
- `SC-12`, `SC-12(1)`, `SC-12(2)`, `SC-12(3)` — key establishment and management
- `SC-13` — cryptographic protection
- `SC-28`, `SC-28(1)`, `SC-28(2)` — protection of information at rest
- `AC-3`, `AC-3(7)` — access enforcement, role-based
- `AC-4`, `AC-4(8)` — information flow enforcement, security policy filters
- `AC-6`, `AC-6(1)`, `AC-6(5)` — least privilege
- `MP-5` — media transport
- `IA-7` — cryptographic module authentication

### Integrity

Primary families: **SI** (System and Information Integrity), **SC** (System and Communications Protection), **CM** (Configuration Management).

Common citations:

- `SI-7`, `SI-7(1)`, `SI-7(7)` — software, firmware, and information integrity
- `SI-10` — information input validation
- `SI-15` — information output filtering
- `SC-8(1)` — transmission integrity
- `SC-16` — transmission of security attributes
- `CM-5` — access restrictions for change

### Availability

Primary families: **CP** (Contingency Planning), **SC** (System and Communications Protection), **SI** (System and Information Integrity).

Common citations:

- `CP-2`, `CP-2(3)`, `CP-2(5)` — contingency plan, resume essential missions
- `CP-7`, `CP-7(1)` — alternate processing site
- `CP-9`, `CP-9(1)`, `CP-9(8)` — system backup, cryptographic protection
- `CP-10`, `CP-10(2)` — system recovery and reconstitution
- `SC-5`, `SC-5(1)` — denial of service protection
- `SC-6` — resource availability

### Distributed

Primary families: **SC** (System and Communications Protection), **CP** (Contingency Planning), **CM** (Configuration Management).

Common citations:

- `SC-7`, `SC-7(5)`, `SC-7(21)` — boundary protection, isolation of components
- `SC-22` — architecture and provisioning for name/address resolution
- `SC-36`, `SC-36(1)` — distributed processing and storage
- `CP-7` — alternate processing site
- `CM-2`, `CM-2(2)` — baseline configuration, automation

### Resilient

Primary families: **SI** (System and Information Integrity), **CP** (Contingency Planning), **SC**.

Common citations:

- `SI-13`, `SI-13(1)`, `SI-13(4)` — predictable failure prevention
- `SI-17` — fail-safe procedures
- `CP-12` — safe mode
- `CP-13` — alternative security mechanisms
- `SC-24` — fail in known state
- `SC-38` — operations security

### Ephemeral

Primary families: **IA** (Identification and Authentication), **AC** (Access Control), **SA** (System and Services Acquisition).

Common citations:

- `IA-5`, `IA-5(1)`, `IA-5(7)`, `IA-5(13)` — authenticator management, rotation
- `AC-2`, `AC-2(2)`, `AC-2(3)` — account management, automated removal of temporary accounts
- `AC-12`, `AC-12(1)` — session termination
- `SC-10` — network disconnect
- `CM-7(5)` — least functionality, authorized software allow-by-exception
- `SA-15(7)` — development process, automated vulnerability analysis

### Authenticity

Primary families: **IA** (Identification and Authentication), **SC** (System and Communications Protection), **SR** (Supply Chain Risk Management).

Common citations:

- `IA-2`, `IA-2(1)`, `IA-2(2)`, `IA-2(6)`, `IA-2(8)` — identification and authentication, MFA, replay-resistant
- `IA-3`, `IA-3(1)` — device identification and authentication
- `IA-5(2)` — PKI-based authentication
- `IA-8`, `IA-8(1)`, `IA-8(4)` — identification and authentication, non-organizational users
- `SC-17` — public key infrastructure certificates
- `SC-23`, `SC-23(3)` — session authenticity
- `SR-4`, `SR-4(3)`, `SR-4(4)` — provenance
- `SR-10`, `SR-11` — inspection and validation of supply chain elements

### Non-Repudiation

Primary families: **AU** (Audit and Accountability), **IA** (Identification and Authentication).

Common citations:

- `AU-2` — event logging
- `AU-3`, `AU-3(1)`, `AU-3(3)` — content of audit records, additional information
- `AU-6`, `AU-6(1)`, `AU-6(3)` — audit review, analysis, and reporting
- `AU-8` — time stamps
- `AU-9`, `AU-9(2)`, `AU-9(3)`, `AU-9(4)` — protection of audit information, cryptographic protection, access by subset
- `AU-10`, `AU-10(1)`, `AU-10(2)` — non-repudiation, association of identities, validate binding
- `AU-12`, `AU-12(1)`, `AU-12(3)` — audit record generation

### Immutability

Primary families: **AU** (Audit and Accountability), **CM** (Configuration Management), **MP** (Media Protection), **SI**.

Common citations:

- `AU-9(2)` — store on separate physical systems or components
- `AU-9(3)` — cryptographic protection
- `AU-11`, `AU-11(1)` — audit record retention, long-term retrieval
- `CM-2`, `CM-2(2)`, `CM-2(3)` — baseline configuration, automation, retention
- `CM-3`, `CM-3(1)` — configuration change control
- `CM-6`, `CM-6(1)` — configuration settings
- `MP-4` — media storage
- `SI-7(8)` — software and information integrity, auditing for integrity violations

### How to write a defensible NIST mapping

- Map to the most specific applicable control or enhancement. `SC-12(1)` beats `SC-12` when key management *availability* is the concern.
- A finding may have multiple control mappings. Three to five is typical; more than ten suggests the finding is too broad and should be decomposed.
- A finding may have zero NIST mappings if the concern is genuinely outside the catalog. This is rare; agents emitting empty `nist_800_53r5` lists must explain in `detail` why no control applies.

---

## MITRE ATT&CK mapping discipline

ATT&CK mappings are emitted on findings (`mitre_attack`, techniques) and on capabilities (`mitre_attack_mitigations`, mitigations). Both require the high-confidence bar.

### Crosswalk source

The mitigation→technique crosswalk is derived from MITRE's enterprise-attack STIX bundle:
`https://raw.githubusercontent.com/mitre/cti/master/enterprise-attack/enterprise-attack.json`

A projected JSON snapshot ships at `tools/apd_gauntlet/data/mitre-mitigations.json`. Refresh with `apd-gauntlet refresh-mitre`. The synthesizer's ATT&CK exposure rollup uses this snapshot to correlate mitigation IDs (M-numbers) with the technique IDs (T-numbers) they mitigate.

### The high-confidence bar

A technique mapping is emitted only if you can complete this sentence non-trivially:

> The architectural concern in this finding enables [technique] specifically because [one-sentence rationale tying the architectural detail to the technique's procedure].

If the rationale you can write is vague ("could enable lateral movement", "may allow data theft"), the technique does not belong on the finding. Emit an empty list and explain in `detail` if the absence is surprising.

### Examples — accepted mappings

**Finding: Unencrypted PHI in Kafka topics with broker-level encryption only.**

```yaml
mitre_attack:
  - technique: "T1530"           # Data from Cloud Storage
    sub_technique: null
    tactic: "TA0010"             # Exfiltration
    rationale: "Broker-level encryption leaves PHI in plaintext at the Kafka storage layer, enabling collection if broker filesystem access is obtained."
```

Accepted: the rationale ties the specific architectural choice (broker-level encryption) to the specific technique (data collected from the storage system).

**Finding: Service-to-service calls inside the cluster lack mTLS, payloads contain PHI.**

```yaml
mitre_attack:
  - technique: "T1557"           # Adversary-in-the-Middle
    sub_technique: "T1557.003"   # DHCP Spoofing — illustrative; pick the right sub-technique
    tactic: "TA0006"             # Credential Access
    rationale: "Unauthenticated cluster traffic allows in-cluster lateral observers to intercept PHI in service-to-service calls."
```

### Examples — rejected mappings

**Finding: Audit log retention is 90 days instead of required 6 years.**

- Rejected mapping: `T1070 - Indicator Removal`. The architectural choice (short retention) does not *enable* the adversary technique; it limits the defender's evidence horizon. Map to NIST `AU-11` instead and explain in `detail` why no ATT&CK technique applies.

**Finding: No multi-region failover for the adjudication engine.**

- Rejected mapping: `T1499 - Endpoint Denial of Service`. Availability gaps are not adversary-enabling unless the architectural choice specifically aids DoS. Map to NIST `CP-7` instead.

### Sub-techniques

When a sub-technique applies, emit the sub-technique. `T1078.004 - Valid Accounts: Cloud Accounts` is more useful than `T1078`. Set `sub_technique` to the full ID (e.g. `T1078.004`); `technique` remains the parent (`T1078`).

### Tactic field

The `tactic` is the ATT&CK tactic ID (`TA0001` through `TA0043`). When a technique appears in multiple tactics, pick the one most aligned with the finding's risk framing. List only one tactic per technique entry.

### Mitigations (capabilities)

Capabilities map to ATT&CK *mitigations* (M-numbers), not techniques. The same high-confidence bar applies: emit only when you can specifically tie the capability to the mitigation.

```yaml
mitre_attack_mitigations:
  - id: "M1041"                  # Encrypt Sensitive Information
    rationale: "Field-level envelope encryption mitigates data collection from data store compromise (T1005, T1530)."
```

Tying the mitigation back to the technique(s) it covers in the rationale is recommended but not required.

---

## Defensible rationale style

- Name the specific architectural detail in the finding/capability — not the general topic.
- Name the technique's actual procedure or the mitigation's actual mechanism.
- One sentence. Two is acceptable for capabilities with broad mitigation surface. Three or more suggests the mapping is forced.
- Avoid hedge words ("could", "may", "potentially") unless the uncertainty is the point — in which case the technique probably doesn't meet the high-confidence bar.

---

## When mappings disagree across agents

If two agents map the same architectural concern to different 800-53r5 controls or ATT&CK techniques, the synthesizer takes the union — both mappings appear on the merged finding. The synthesizer does not arbitrate which control is "more correct"; that is for human reviewers.

If two agents emit *contradictory* mappings (one maps to a mitigation, the other to a technique, on what becomes a merged finding), the synthesizer surfaces the contradiction in the contradiction annex.

---

## Per-taxonomy discipline (v1.2+)

A run may declare additional taxonomies in `.apd-run.yaml` (`taxonomies: [cwe, owasp_top10, owasp_api_top10, owasp_llm_top10, d3fend, mitre_atlas]`). The intake brief lists which are in scope plus any taxonomies intake auto-suggested. **Only emit mappings for taxonomies declared in the run.** Auto-suggestions that the operator did not adopt do not authorize emission.

### CWE (on findings, optional)

- Map only when the finding describes a specific weakness pattern that matches a CWE entry's **Demonstrative Examples** or **Observed Examples**.
- Use **base** or **variant** abstractions only. **Pillar** and **category** entries (e.g., CWE-693 "Protection Mechanism Failure") are too abstract for actionable mapping and must not be used.
- Each `cwe` mapping is just the ID string (no rationale field on the schema — but the finding's `detail` text must justify the weakness-pattern match. Reviewers should be able to read the detail and see why CWE-79 applies.)
- One finding may carry multiple CWE IDs when the weakness composes.

### OWASP Top 10 (web — on findings, optional)

- Map only when the SUT has a web surface (HTML routes, browser-rendered templates, session cookies). Intake auto-suggests this taxonomy when those surfaces are detected.
- Use the current edition format `A<NN>:<YYYY>` (e.g., A03:2021). Do not silently re-map findings to newer editions when they ship — the edition year is part of the ID.
- Limit one OWASP Top 10 ID per finding except when the finding genuinely spans categories (e.g., a single misconfiguration that's both A05 and A07). Multiple IDs require the `detail` text to walk through each.

### OWASP API Top 10 (on findings, optional)

- Map when the SUT exposes an API (OpenAPI/Swagger spec, REST/GraphQL endpoints, API gateway config).
- Format `API<N>:<YYYY>` (e.g., API3:2023).
- Same per-finding multiplicity discipline as OWASP Top 10.

### OWASP LLM Top 10 (on findings, optional)

- Map only when the SUT integrates an LLM (SDK imports of `openai`, `anthropic`, `langchain`, etc.; vector store usage; prompt templates).
- Format `LLM<NN>` (e.g., LLM01).
- LLM01 (Prompt Injection), LLM06 (Sensitive Information Disclosure), LLM07 (Insecure Plugin Design) are most often-cited; map only when the finding actually describes the categorized risk pattern.

### D3FEND (on capabilities, optional)

- D3FEND attaches to **capabilities**, not findings. A capability earns a D3FEND mapping when its design demonstrably implements the technique.
- Each D3FEND entry **must** cite which ATT&CK techniques it counters via `counters_attack`. The cited ATT&CK technique(s) must also appear in the same capability's `mitre_attack` block (the `mitre_attack` field documents which techniques the capability defends against). Schema validates the format; cross-reference is checked by the validator. Map-by-name-similarity is forbidden.
- Each D3FEND entry requires `rationale` (≥30 chars) explaining how the capability implements the D3FEND technique.
- Use the format `D3-<short_code>` (e.g., D3-NTA for Network Traffic Analysis, D3-NTF for Network Traffic Filtering, D3-PHDURA for Process Hierarchy Database Update Restriction Analysis — codes can be 2 to 7 letters). Reference data with the full set of valid codes is at `tools/apd_gauntlet/data/d3fend.json`.

### MITRE ATLAS (on findings, optional)

- ATLAS is the adversarial-ML technique taxonomy (the AI/ML analog of ATT&CK). Declare it as `mitre_atlas` in `.apd-run.yaml`. Map only when the SUT has an AI/ML surface (a model in the trust boundary, a training/inference pipeline, an agent, a RAG/vector store, an ML supply chain).
- ATLAS attaches to **findings**, not capabilities — it names an offensive technique a finding's weakness exposes, mirroring the `mitre_attack` field. A finding earns an ATLAS mapping when its weakness pattern matches a specific ATLAS technique's description.
- Each `atlas` mapping is just the ID string (no rationale field on the schema — but the finding's `detail` text must justify the technique match, exactly as for CWE). One finding may carry multiple ATLAS IDs when the weakness composes.
- Use the format `AML.T####` for a top-level technique or `AML.T####.###` for a sub-technique (e.g., AML.T0051 LLM Prompt Injection, AML.T0051.000 Direct, AML.T0043 Craft Adversarial Data, AML.T0020 Poison Training Data). Reference data with the full set of valid IDs and names ships at `tools/apd_gauntlet/data/atlas-techniques.json`; refresh with `apd-gauntlet refresh-atlas`.
- ATLAS and the `agentic-ai` domain pack pair naturally — but ATLAS is a taxonomy, not a pack: declare it on any run with an ML surface, regardless of domain.

## High-confidence-only rule (extends unchanged)

The existing high-confidence-only rule applies to all six new taxonomies. When uncertain whether a CWE matches the weakness pattern, when uncertain whether the SUT actually exposes the OWASP-categorized surface, when uncertain whether a capability truly implements a D3FEND technique, when uncertain whether an ATLAS technique matches the finding's weakness — **do not map**. Leave the field absent.
