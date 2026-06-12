# pbm Domain Pack — Larger-Efforts Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the 7 medium- and high-effort gaps in the pbm domain pack that the 6-dimension cross-pack audit surfaced and that PR #22 (quick wins) deliberately deferred. Bring pbm's analytical depth to parity with api-security, identity-security, and security-tooling without breaking any existing run, schema, or test.

**Architecture:** Five sequenced pull requests, each scoped to a single conceptual change so reviewers can evaluate independently. Each PR is preceded by reading the relevant comparator-pack files for rhetorical alignment, and followed by an independent reviewer agent pass (one agent per touched file) before commit. ATT&CK and D3FEND citations follow the high-confidence-bar discipline from `superpowers:apd-control-mappings`; no shotgun mapping. Domain-expert-needed sections (NCPDP / X12 protocol fields, claims-lifecycle decomposition) are drafted from publicly-available specification language and flagged with structured `SME-review:` markers so a domain expert can validate without re-doing the structural work.

**Tech Stack:** YAML + Markdown only. Validation via `apd-gauntlet validate-domain pbm`; integration check via `pytest`. No Python edits, no schema changes, no agent changes.

---

## Scope at a glance

| Effort | Files | Wave | PR |
|---|---|---|---|
| 1. Expand domain.yaml content blocks | `domains/pbm/domain.yaml` | 1 | PR-A |
| 2. Patient-harm second axis + ATT&CK/NIST anchors in severity-rubric | `domains/pbm/severity-rubric.md` | 1 | PR-B |
| 3. PBM-specific immutability classes | `domains/pbm/immutability-classes.md` | 1 | PR-C |
| 4. ATT&CK + D3FEND mapping section per common-pattern goal | `domains/pbm/common-patterns/*.md` (×9) | 2 | PR-E |
| 5. Multi-clause prerequisite_evidence asks per common-pattern goal | `domains/pbm/common-patterns/*.md` (×9) | 2 | PR-E |
| 6. Claims-lifecycle + HIPAA patient-rights decomposition in consequential-actions | `domains/pbm/consequential-actions.md` | 1 | PR-D |
| 7. NCPDP / X12 / PDE protocol-element vocabulary in data-taxonomy | `domains/pbm/data-taxonomy.md` | 1 | PR-D |

**Wave 1 (parallel-safe, single-file each):** PRs A, B, C, D ship independently. None of them touch a file another wave-1 PR touches.

**Wave 2 (after wave 1 lands):** PR-E bundles Efforts 4 and 5 because both touch the same 9 common-patterns files. Doing them together avoids double-touching each file and lets a single editor produce one coherent rewrite per goal.

---

## Cross-cutting discipline rules

These apply across every PR in this plan. Each task references back to this section.

**R1 — High-confidence-bar for ATT&CK and D3FEND mapping.** Per `superpowers:apd-control-mappings`: emit a technique ID only when the goal or finding clearly defends against (or is exploited by) that specific technique. Never shotgun-map. Each ATT&CK citation must be accompanied by a one-sentence justification ("this clause covers T1078 because …"). D3FEND counters must reference the ATT&CK technique they counter (per `superpowers:apd-attack-path-discipline`).

**R2 — Comparator-pack rhetorical alignment.** Before writing a new section, read the equivalent section in two of the three newer packs. Match the structure (headings, bullet density, citation style) but translate every concept to PBM language. Never copy-paste comparator text — PHI ≠ personal_data, NCPDP ≠ OAuth, adjudication engine ≠ API gateway.

**R3 — Regulatory citations are pinned with CFR / USC / spec section.** Every regulatory anchor must include the specific CFR or USC section (e.g., "45 CFR §164.408" not "HIPAA"). Spec citations must include the spec name and section ("NCPDP Telecommunication Standard D.0 §B1" not "NCPDP").

**R4 — SME-review markers.** Where the draft uses publicly-available NCPDP / X12 / CMS spec language but the LLM cannot verify whether the spec language matches current real-world implementation, insert an HTML comment of the form `<!-- SME-review: <specific question> -->` immediately after the affected sentence. These markers are surfaced in the PR description so a domain expert can validate without re-writing the structural work. No `TODO:` or bare placeholders.

**R5 — Preserve existing content.** Each task is ADDITIVE unless explicitly noted. Never delete or rewrite an existing pbm section unless the task description says "rewrite" or "replace."

**R6 — Acceptance test for every file edit.** After applying edits, run:
```bash
apd-gauntlet validate-domain pbm
.venv/bin/python -c "import yaml; yaml.safe_load(open('domains/pbm/domain.yaml'))"  # YAML only
.venv/bin/python -m pytest -q
```
All three must pass. If any fails, fix before committing.

**R7 — Independent reviewer pass per file.** After each task's edits land, dispatch a reviewer agent to verify the acceptance criteria. The reviewer reads the file in full and returns `approved` or `needs_revision` with concrete notes. Re-edit and re-review until `approved`.

---

# PR-A — Effort 1: Expand domain.yaml content blocks

**Branch:** `expand-pbm-domain-content-blocks`
**Files:** `domains/pbm/domain.yaml`
**Reference files for style:**
- `domains/api-security/domain.yaml`
- `domains/identity-security/domain.yaml`
- `domains/security-tooling/domain.yaml`

**Goal:** Bring `crown_jewels` from 3 → 9, `attacker_positions` from 5 → 10, and `default_trust_boundaries` from 3 → 7, each with multi-clause descriptions, regulator triggers, and threat-catalog citations where the R1 high-confidence bar is met.

### Task A1: Draft 6 new crown_jewel entries

**Files:**
- Modify: `domains/pbm/domain.yaml`

- [ ] **Step 1: Read the three comparator domain.yaml files to confirm description style and length.**

Compare how each comparator pack handles a non-data-store crown jewel (e.g., api-security's `audit_log_store`, identity-security's `identity_provider_admin_console`, security-tooling's `c2_signing_authority`). Each comparator entry runs 2–4 sentences naming what the asset holds, the compromise consequence, the regulator trigger, and the forensic implication.

- [ ] **Step 2: Draft the 6 new entries in YAML.**

Append the following entries to the `crown_jewels:` list (after the existing 3 entries). Each multi-clause description follows the comparator-pack arc per R2:

```yaml
  - pattern: audit_log_store
    description: "Security and consequential-action event log spanning PHI access, claim-adjudication decisions, prior-authorization decisions, configuration changes, break-glass invocations, and CMS PDE submission events. HIPAA Security Rule §164.312(b) (Audit Controls) treats this store as the breach-detection and breach-notification fact base — regulators treat absence or alteration as presumption of breach. Compromise enables both attack-concealment (T1070 Indicator Removal) and post-incident liability — without defensible audit, the PBM cannot satisfy HIPAA breach-notification rules even when an attack is otherwise detected."
  - pattern: backup_artifact_store
    description: "Database snapshots (adjudication, member, claim history), object-store backups (PDE batch archives, audit-log archives), configuration backups, and key-material escrow copies. Frequently the weakest crown jewel because encryption-at-rest, access controls, and immutability protections are typically weaker than the primary stores they protect against. A successful exfiltration of a backup commonly bypasses the controls applied to live PHI surfaces and produces the same regulatory consequences under 45 CFR §164.408."
  - pattern: prescriber_directory
    description: "Provider attribution surface — NPI, DEA registration number, state pharmacy/medical license, prescriber specialty, prescriber demographics, controlled-substance authority. Compromise enables both prescription-fraud campaigns (forge prescriptions in a real prescriber's name) and clinical-decision misattribution (DUR alerts routed to wrong prescriber). DEA records are subject to 21 CFR §1304.04 retention; state-license records are commonly subject to state pharmacy-board reporting requirements separate from HIPAA."
  - pattern: rebate_formulary_pricing_data
    description: "Manufacturer rebate calculations, Maximum Allowable Cost (MAC) lists, formulary tier assignments, pharmacy-network reimbursement schedules, and accumulator history. Compromise yields commercial-confidentiality exposure (master-service-agreement breach, manufacturer-rebate-contract breach) and competitive-intelligence harm; tampering yields plan-payment fraud and pharmacy-reimbursement disputes that commonly trigger litigation. Retention requirements typically derive from contract terms rather than statute, but the contract floors are routinely 7–10 years to cover audit and statute-of-limitations windows."
  - pattern: member_authentication_credentials
    description: "Member portal authentication store — password hashes, MFA enrollments, recovery email and phone, security questions, account-lockout state. Compromise yields member-account takeover at scale, which converts directly to PHI exposure under HIPAA (every claim record and PA history for the affected member becomes readable). Authentication factor strength and recovery-flow integrity gate both the §164.524 (Right of Access) surface and the §164.502 (Minimum Necessary) surface."
  - pattern: vendor_integration_secrets
    description: "Service-account credentials, API tokens, and signing keys used for outbound integrations — rebate aggregators, COB carriers, eligibility partners, mail-order fulfillment pharmacies, accumulator vendors, and analytics partners. Long-lived service-account credentials are the dominant root cause of vendor-channel PHI exposure incidents; compromise of one integration credential commonly yields lateral PHI access across the entire vendor surface. Each credential's blast radius equals the data scope granted in the underlying Business Associate Agreement."
```

- [ ] **Step 3: Apply the edit using the Edit tool.**

Add the 6 entries to the `crown_jewels:` list immediately after the existing 3 entries. Preserve the existing entries verbatim.

- [ ] **Step 4: Verify YAML still parses.**

Run:
```bash
.venv/bin/python -c "import yaml; d=yaml.safe_load(open('domains/pbm/domain.yaml')); assert len(d['crown_jewels'])==9, f'expected 9, got {len(d[\"crown_jewels\"])}'; print('OK')"
```
Expected output: `OK`.

- [ ] **Step 5: Commit.**

```bash
git add domains/pbm/domain.yaml
git commit -m "feat(domain-pack/pbm): expand crown_jewels with 6 PBM-specific assets

Adds audit_log_store, backup_artifact_store, prescriber_directory,
rebate_formulary_pricing_data, member_authentication_credentials, and
vendor_integration_secrets. Each entry follows the comparator-pack
multi-clause description pattern (asset content, compromise consequence,
regulator trigger, forensic implication). Closes part 1 of the larger-
efforts plan, Effort 1."
```

### Task A2: Draft 5 new attacker_position entries

**Files:**
- Modify: `domains/pbm/domain.yaml`

- [ ] **Step 1: Read the comparator domain.yaml attacker_positions sections to confirm threat-catalog citation style.**

Each comparator pack cites ATT&CK techniques (e.g., T1621 push-bombing), RFC sections (e.g., RFC 9700 §4.2), and OWASP IDs (e.g., API1 BOLA, API5 BFLA) inline where the R1 high-confidence bar is met.

- [ ] **Step 2: Draft the 5 new entries in YAML.**

Append to `attacker_positions:` after the existing 5 entries:

```yaml
  - position: unauthenticated_internet_against_member_portal
    description: "Untrusted external attacker targeting the member-portal authentication surface specifically (distinct from the generic external_internet position, which models any internet-facing surface). Models credential-stuffing campaigns, OWASP API1 (BOLA) on member-id-keyed endpoints, OWASP API5 (BFLA) on tier-distinct endpoints (member vs admin), enumeration of member identifiers via login or password-reset response oracles (T1110.003 Password Spraying, T1110.004 Credential Stuffing), and SAML/OIDC misconfiguration on federated member access. The defining threat: a successful authentication compromise here converts directly to PHI exposure under HIPAA §164.508 (Authorization) without further escalation."
  - position: authenticated_member_seeking_cross_member_phi
    description: "A member with valid credentials attempting horizontal escalation to another member's PHI — typically via IDOR on member-id parameters, predictable claim-reference URLs, parameter tampering on dependent-coverage endpoints, or session re-use across logical member contexts (T1078.004 Cloud Accounts applied to member portal). The most common PBM-specific manifestation is dependent-coverage scope: a primary subscriber attempting to access an adult dependent's PHI without the adult's authorization, which §164.502(g) treats as a non-routine disclosure requiring specific authorization."
  - position: compromised_cms_submission_credential
    description: "Attacker holding the credential or signing key used to authenticate the PBM's outbound CMS Part D PDE submission channel. Distinct from compromised_pharmacy_credential (which models inbound NCPDP claim submission) and compromised_vendor_integration (which models third-party vendor egress). Compromise yields the ability to submit falsified PDE records, suppress legitimate PDE records, or alter PDE retroactive corrections — each producing 42 CFR §423.322 PDE-data-integrity consequence (CMS payment-determination reopening, plan-payment recovery, potential False Claims Act exposure under 31 U.S.C. §3729 if the submission was knowingly false)."
  - position: compromised_admin_workstation
    description: "Attacker who has compromised an operator or administrator workstation with privileged access to formulary configuration, PA-criteria configuration, MAC pricing, contract-pricing tables, or audit-log retention settings. Distinct from compromised_dev_workstation (which models pre-production tooling). Models the post-phishing escalation path where a compromised admin can silently disable audit shipping (T1070), backdate audit entries (T1036 Masquerading at the audit layer), or alter the formulary configuration to produce clinical-decision harm at scale. The defining feature: actions taken from this position attribute to a legitimate operator credential, so defensibility depends entirely on the audit-of-audit surface."
  - position: internal_lateral_attacker_in_adjudication_tier
    description: "Attacker who has already established a foothold in the internal network — typically through the dev_workstation position, an exposed admin-console session, or a vendor-integration compromise — and is now attempting lateral movement to reach the PHI store, the adjudication engine, or the PDE submission pipeline. Models the post-breach window where the attacker has time and access to enumerate internal services, abuse in-cluster trust assumptions (T1078 Valid Accounts on service-account credentials, T1213 Data from Information Repositories on internal PHI replicas), and escape from a low-value tier to a high-value tier. The defining test for this position: would mTLS, network segmentation, and credential-scoping prevent the attacker from reaching the crown jewel from their established foothold?"
```

- [ ] **Step 3: Apply the edit.**

- [ ] **Step 4: Verify YAML.**

```bash
.venv/bin/python -c "import yaml; d=yaml.safe_load(open('domains/pbm/domain.yaml')); assert len(d['attacker_positions'])==10; print('OK')"
```

- [ ] **Step 5: Commit.**

```bash
git commit -am "feat(domain-pack/pbm): expand attacker_positions with 5 PBM-specific positions

Adds unauthenticated_internet_against_member_portal,
authenticated_member_seeking_cross_member_phi,
compromised_cms_submission_credential, compromised_admin_workstation,
and internal_lateral_attacker_in_adjudication_tier. Each entry
follows comparator-pack threat-catalog citation discipline (ATT&CK
technique IDs and OWASP API references where the high-confidence bar
is met)."
```

### Task A3: Draft 4 new default_trust_boundary entries

**Files:**
- Modify: `domains/pbm/domain.yaml`

- [ ] **Step 1: Read comparator domain.yaml trust-boundary sections.**

api-security has `application_to_data_tier`, `application_to_third_party`, `personal_data_subject_zone`. identity-security has `admin_console_to_idp_backend`. Each description names what crosses the boundary and what control enforces it.

- [ ] **Step 2: Draft the 4 new entries.**

Append to `default_trust_boundaries:`:

```yaml
  - boundary: adjudication_engine_to_phi_data_tier
    description: "Service-to-datastore crossing between the claim-adjudication engine and the underlying PHI store (PostgreSQL, MongoDB, or vendor-specific adjudication-engine database). Frequently the weakest link under 'in-cluster trust' assumptions; enforcement requires in-cluster mTLS, query parameterization to prevent NoSQL/SQL injection on member-id or claim-reference parameters, and least-privilege datastore credentials scoped to the specific adjudication operation. A successful boundary failure here reaches the largest PHI scope in the PBM."
  - boundary: pbm_to_third_party_vendor
    description: "Outbound egress from PBM services to third-party vendors with whom the PBM has a Business Associate Agreement under HIPAA §164.504(e) — rebate aggregators, accumulator vendors, COB carriers, analytics partners, mail-order fulfillment pharmacies, specialty-pharmacy fulfillment, and switch operators (RelayHealth, Change Healthcare). The boundary is multi-channel (HTTPS APIs, SFTP file drops, IBM MQ enterprise messaging) and each channel needs its own authentication, encryption-in-transit, and data-scope-enforcement. Vendor-credential compromise (see compromised_vendor_integration attacker position) is the dominant breach vector here."
  - boundary: phi_subject_zone
    description: "HIPAA-anchored PHI segmentation boundary, analogous to api-security's personal_data_subject_zone for GDPR. Crossings into or out of this zone trigger HIPAA Privacy Rule disclosure analysis (45 CFR §164.502 Uses and Disclosures, §164.514(b) De-identification). Includes the de-identification gate for analytics surfaces, the minimum-necessary gate for internal cross-team data sharing (§164.502(b)), and the lawful-basis gate for any disclosure outside the Treatment / Payment / Operations exception (§164.506)."
  - boundary: admin_console_to_pbm_backend
    description: "Privileged-administration crossing between the operator admin console (formulary editor, PA criteria editor, MAC list editor, contract-pricing editor, audit-retention configuration) and the corresponding backend services and configuration stores. The blast radius of any boundary failure here is the entire PBM — admin actions silently affect every subsequent claim adjudicated against the modified configuration. Enforcement requires step-up authentication (per the severity rubric's authentication-bypass clause), four-eyes / dual-approval workflows on configuration-changing actions, and an audit chain attributing the action to the human operator (not the operator's session token or sidecar identity)."
```

- [ ] **Step 3: Apply, verify, commit.**

```bash
.venv/bin/python -c "import yaml; d=yaml.safe_load(open('domains/pbm/domain.yaml')); assert len(d['default_trust_boundaries'])==7; print('OK')"
git commit -am "feat(domain-pack/pbm): expand default_trust_boundaries with 4 PBM-specific crossings"
```

### Task A4: Open PR-A

- [ ] Push the branch, open PR, request review.

**Acceptance criteria for PR-A:**
- crown_jewels has exactly 9 entries; each has a multi-clause description
- attacker_positions has exactly 10 entries; each cites at least one threat-catalog reference where the R1 bar is met
- default_trust_boundaries has exactly 7 entries; each names the crossing and the enforcement
- `apd-gauntlet validate-domain pbm` passes
- All 619 tests pass
- Independent reviewer agent approves the file

---

# PR-B — Effort 2: Two-axis severity rubric + ATT&CK / NIST anchors

**Branch:** `pbm-severity-rubric-two-axis-attck-anchors`
**Files:** `domains/pbm/severity-rubric.md`
**Reference files for style:**
- `domains/security-tooling/severity-rubric.md` (canonical two-axis pattern)
- `domains/identity-security/severity-rubric.md` (NIST 800-63B inline-citation pattern)

**Goal:** Adopt the security-tooling two-axis pattern with a PBM-specific second axis (clinical patient-harm), and add inline ATT&CK technique IDs + NIST 800-53r5 family anchors on attack-mechanic-driven clauses, applying R1 discipline.

### Task B1: Add the second-axis preamble

**Files:**
- Modify: `domains/pbm/severity-rubric.md`

- [ ] **Step 1: Read security-tooling's preamble carefully.**

Security-tooling's preamble explains that severity has two axes (CIA + weapons-platform-misuse) and that the assigned severity is the MAX of the two. Match this rhetorical arc, substituting PBM-specific terms.

- [ ] **Step 2: Draft the new preamble paragraph.**

Insert after the existing preamble (the "Calibrated against impact-to-PBM" paragraph), before the `## Critical` heading:

```markdown
PBM severities have a **second dimension** beyond classic HIPAA-data-confidentiality and CMS-data-integrity: the **clinical patient-harm dimension**. A finding that exposes PHI or corrupts PDE submission is scored on the data-and-regulatory axis; a finding that affects a clinical-decision pathway — drug-utilization review, prior-authorization decision, formulary-substitution logic, dispense-as-written enforcement, dosage calculation — is scored on the patient-harm axis. Many findings score on both axes; severity is the higher of the two. The PBM-specific implication: a DUR-rule edit that produces a missed drug-interaction alert can be Critical on the patient-harm axis even if the affected member-population is below the 500-member HIPAA breach threshold on the data-and-regulatory axis.

References inline: HIPAA Privacy Rule (45 CFR 164 Subpart E), HIPAA Security Rule (45 CFR 164 Subpart C), NIST SP 800-53r5 control families, MITRE ATT&CK Enterprise techniques, MITRE D3FEND countermeasures, NCPDP Telecommunication Standard D.0, CMS Part D PDE Submission (42 CFR 423.322).
```

- [ ] **Step 3: Apply the edit.**

- [ ] **Step 4: Commit.**

```bash
git commit -am "feat(severity-rubric): add two-axis preamble (data/regulatory + clinical patient-harm)"
```

### Task B2: Add ATT&CK technique IDs to Critical-tier attack-mechanic clauses

**Files:**
- Modify: `domains/pbm/severity-rubric.md`

- [ ] **Step 1: Identify each Critical-tier bullet whose underlying mechanic clearly maps to a single ATT&CK technique under R1.**

Apply the high-confidence-bar discipline. The following mappings meet R1:

| Critical clause (current) | ATT&CK mapping | D3FEND counter |
|---|---|---|
| Authentication bypass to PHI surfaces or admin functions | T1078 (Valid Accounts), T1556 (Modify Authentication Process) | D3-OTF (One-time Token Verification), D3-MFA (Multi-factor Authentication) |
| Audit trail loss covering PHI access | T1070 (Indicator Removal), T1070.002 (Clear Linux or Mac System Logs) when applicable | D3-SBV (System Behavior Validation), D3-LFAM (Local File Permissions) on log substrate |
| Loss of CMS Part D submission integrity (PDE corruption) | T1565 (Data Manipulation), T1565.002 (Transmitted Data Manipulation) for in-flight PDE tampering; T1565.001 (Stored Data Manipulation) for at-rest PDE corruption | D3-MA (Message Authentication) on signed PDE submission |
| Claim adjudication corruption affecting therapeutic decisions | T1565.001 (Stored Data Manipulation) for formulary-config edits; T1565.002 (Transmitted Data Manipulation) for in-flight claim manipulation | D3-SBV (System Behavior Validation), D3-MA (Message Authentication) on NCPDP signed messages |
| PHI exfiltration capability affecting >500 members | T1213 (Data from Information Repositories), T1213.003 (CRM/PHI repos); T1041 (Exfil Over C2 Channel) or T1567 (Exfil Over Web Service) depending on channel | D3-EDD (Encrypted Data Detection — DLP), D3-NTA (Network Traffic Analysis) |

- [ ] **Step 2: Rewrite each Critical bullet to embed the mapping inline.**

Pattern (matches security-tooling's style): "… mechanic description. Maps to <T-IDs with names>; D3FEND counter is <D3-IDs with names>. NIST 800-53r5 anchor: <control family + key control IDs>."

Example rewrite for the audit-trail-loss bullet:

```markdown
- **Audit trail loss covering PHI access** — renders breach detection and notification obligations un-meetable; regulatory non-compliance independent of breach occurrence. Includes silent log disable, retention shortened below the HIPAA 6-year floor (45 CFR §164.316(b)(2)(i)), or log-shipping pipeline interrupted without separately-attested record on a forensically isolated channel. Maps to T1070 (Indicator Removal); D3FEND counter is D3-SBV (System Behavior Validation) plus immutable substrate (S3 Object Lock Compliance Mode, HSM-anchored hash-chained store). NIST 800-53r5 anchor: AU family — AU-9 (Protection of Audit Information), AU-11 (Audit Record Retention), AU-12 (Audit Record Generation).
```

Apply the same pattern to the other four Critical clauses listed in the mapping table above. Preserve the existing wording structure; embed the mappings inline rather than appending them as a separate paragraph.

- [ ] **Step 3: Apply edits and verify.**

After all 5 Critical-clause rewrites:
```bash
grep -c "Maps to T" domains/pbm/severity-rubric.md  # expected: 5
grep -c "D3FEND counter is" domains/pbm/severity-rubric.md  # expected: 5
grep -c "NIST 800-53r5 anchor:" domains/pbm/severity-rubric.md  # expected: 5
```

- [ ] **Step 4: Commit.**

```bash
git commit -am "feat(severity-rubric): add ATT&CK + D3FEND + NIST 800-53r5 anchors to Critical-tier clauses

Following the apd-control-mappings high-confidence-bar discipline, adds
inline technique IDs to the 5 attack-mechanic-driven Critical bullets:
authentication bypass (T1078/T1556 + D3-OTF/D3-MFA), audit trail loss
(T1070 + D3-SBV), PDE submission corruption (T1565 + D3-MA), claim
adjudication corruption (T1565.001/T1565.002 + D3-SBV/D3-MA), and PHI
exfiltration (T1213/T1041/T1567 + D3-EDD/D3-NTA). Each clause also
gains a NIST 800-53r5 family anchor (AU/IA/AC/SI)."
```

### Task B3: Add the clinical patient-harm second-axis ladder

**Files:**
- Modify: `domains/pbm/severity-rubric.md`

- [ ] **Step 1: Draft the second-axis content.**

Insert a new section AFTER the existing Informational tier and BEFORE the Severity calibration discipline section:

```markdown
## Clinical patient-harm axis

The PBM severity ladder above scores findings on the data-and-regulatory axis (PHI confidentiality, PDE integrity, audit defensibility). The second axis below scores findings on the clinical patient-harm dimension. Assign the severity that is the MAX of the two axes.

### Critical (clinical patient-harm)

- **Wrong drug dispensed at the pharmacy counter** — finding makes it plausible that the PBM's pricing or adjudication response produced a substitution that the prescriber did not approve and that the patient would not have received but for the PBM error. Maps to T1565.002 (Transmitted Data Manipulation) when the corruption is in-flight; T1565.001 when in the formulary store.
- **Missed drug-utilization-review alert leading to harmful drug interaction** — finding makes it plausible that the DUR engine suppressed, did not raise, or routed away a clinically-significant interaction alert (drug-drug, drug-disease, drug-allergy, drug-age, therapeutic duplication). Includes DUR-rule configuration that excludes a class of patient (e.g., pediatric, geriatric, pregnant) from alerts they should receive.
- **Missed prior-authorization on safety-gated drug** — finding makes it plausible that the PA-criteria engine approved or auto-routed-around a request that the PA criteria were explicitly designed to gate for clinical safety reasons (REMS-enrolled drugs, controlled substances above MED thresholds, specialty oncology agents with monitoring requirements).
- **Formulary bypass exposing patient to clinically harmful substitution** — finding makes it plausible that a formulary-tier reassignment, generic-substitution rule, or step-therapy-bypass produced a dispense decision that the formulary committee explicitly excluded for clinical-safety reasons.
- **Dose calculation error** — finding makes it plausible that the days-supply calculation, the weight-based-dosing logic, or the pediatric/geriatric dosing rule produced an unsafe dose. Particularly load-bearing for opioids (MED calculation), insulin, anticoagulants, and pediatric formulations.

### High (clinical patient-harm)

- **DUR-rule or PA-criteria edit without dual approval** — the editing surface for clinical-decision logic accepts single-operator changes; finding scores High because it creates the capability for any of the Critical-tier clinical-harm scenarios above without an enforcement gate.
- **Formulary tier change applying retroactively** — finding makes it plausible that a tier reassignment alters claims that were already adjudicated, retroactively shifting cost or coverage in ways that destabilize patient adherence or trigger member-confusion-driven non-compliance.
- **DUR alert silently suppressed by operator without attestation** — operator UI permits DUR-alert suppression without recording a clinical-justification field, supervisor attestation, or pharmacist review. Creates a hidden patient-harm capability.
- **PA appeal-decision routing failure** — Medicare Part D requires PA appeal decisions within tight timelines (42 CFR §423.578 ff.); finding makes it plausible that the appeal-routing logic produces missed timelines that convert to coverage denials by default.

### Medium (clinical patient-harm)

- **DUR alert displayed but easily dismissed** — clinically-significant alerts can be dismissed with a single click and no justification; clinical-decision quality depends on operator habit rather than enforcement. Worth raising; not catastrophic.
- **Formulary-update lag affecting non-safety drugs** — formulary changes propagate with a delay that affects copay or coverage but does not affect drug safety.
- **PA criteria documentation drift** — the configured criteria differ from the published formulary documentation in ways that affect member expectations but not safety.

### Low (clinical patient-harm)

- **Clinical-context surface with no realistic harm path** — UI labels for clinical fields use unclear or inconsistent language; no error in computation or routing.
- **Documentation gap on a clinical-decision surface** — operator-facing help text incomplete; clinical logic itself is correct.
```

- [ ] **Step 2: Apply the edit.**

Insert the new section in the position specified above. Preserve all other content.

- [ ] **Step 3: Verify section ordering.**

```bash
grep -nE "^## " domains/pbm/severity-rubric.md
```
Expected order: Critical, High, Medium, Low, Informational, Clinical patient-harm axis, Severity calibration discipline.

- [ ] **Step 4: Commit.**

```bash
git commit -am "feat(severity-rubric): add clinical patient-harm second axis

Adds a second-axis ladder (Critical/High/Medium/Low) covering wrong-drug,
missed DUR alert, missed PA on safety-gated drug, formulary clinical
bypass, dose calculation error, DUR/PA criteria edit without dual
approval, etc. Severity = max(data-and-regulatory axis, clinical
patient-harm axis), matching security-tooling's two-axis precedent."
```

### Task B4: Open PR-B

- [ ] Open PR with description naming the three changes (preamble, ATT&CK anchors on Critical clauses, second-axis ladder).

**Acceptance criteria for PR-B:**
- The two-axis preamble paragraph is present after the existing preamble
- 5 Critical-clause bullets carry inline ATT&CK + D3FEND + NIST 800-53r5 anchors (verified by `grep -c`)
- The clinical patient-harm section is positioned after Informational and before Severity calibration discipline
- Existing severity-rubric content is preserved verbatim (no clause from the original was deleted)
- `apd-gauntlet validate-domain pbm` passes
- All 619 tests pass

---

# PR-C — Effort 3: PBM-specific immutability classes

**Branch:** `pbm-immutability-classes-pbm-specific`
**Files:** `domains/pbm/immutability-classes.md`
**Reference files for style:**
- `domains/api-security/immutability-classes.md`
- `domains/identity-security/immutability-classes.md`

**Goal:** Add 5 PBM-specific immutability classes beyond the structural quick wins already landed (4-trigger rubric, substrate enforcement, cryptographic key lifecycle): rebate-calculation history, MAC pricing history, network-pharmacy contract terms at adjudication, DSCSA track-and-trace records, state-pharmacy-board reportable events.

### Task C1: Draft the 5 new class entries

**Files:**
- Modify: `domains/pbm/immutability-classes.md`

- [ ] **Step 1: Re-read the file after PR #22 landed.**

Identify the section break after the cryptographic key lifecycle class. The 5 new classes will be inserted at the end of the class list, before the closing cross-reference section.

- [ ] **Step 2: Draft the 5 entries.**

```markdown
### Rebate calculation history

WHAT: Manufacturer rebate calculations, plan-sponsor remit allocations, accumulator-state snapshots used to compute rebate eligibility, and the rebate-recovery audit trail. Includes the exact rebate-contract version applied to each claim cohort and the calculation inputs (utilization data, formulary tier at calculation time, manufacturer rebate-contract terms in effect).

WHY immutable: Rebate disputes routinely arise years after a calculation — manufacturer audits, plan-sponsor disputes, and government inquiries (DOJ False Claims Act investigations naming alleged rebate-pass-through fraud have been litigated against PBMs). The defensibility of any rebate calculation depends on being able to reconstruct exactly which contract version, which utilization data, and which formulary state produced the calculation. Mutable rebate calculation history makes plaintiff allegations of rebate manipulation effectively unrebuttable.

RETENTION: Pinned to the longest of (a) 7 years to cover most plan-sponsor MSA audit windows, (b) the term of the underlying manufacturer rebate contract plus 3 years for dispute, (c) any state insurance-department retention requirement for PBM business records. Practical floor is commonly 10 years for major-market plans.

### MAC pricing history

WHAT: Maximum Allowable Cost list versions over time, the source data informing each version (compendia inputs, pharmacy-acquisition cost samples), the publication dates and effective-date windows, the per-pharmacy MAC variants where the PBM operates differentiated networks, and the pharmacy-appeal history (claims appealed under MAC-appeal rights granted by state law).

WHY immutable: State MAC-transparency laws (~40 states have such statutes as of this writing) routinely grant pharmacies the right to appeal MAC-priced claims and require the PBM to retain MAC source data for audit. Pharmacy-network reimbursement disputes turn on which MAC was in effect when a specific claim adjudicated. <!-- SME-review: confirm the current state-by-state retention requirements; this draft uses 7 years as a generic floor but several state statutes specify different retention windows. -->

RETENTION: Pinned to the longest of (a) the underlying contract retention floor, (b) state MAC-transparency law retention (varies by state), (c) any pharmacy-appeal window plus statute-of-limitations grace period.

### Network-pharmacy contract terms at adjudication

WHAT: The actual contract terms in effect at the moment of each claim adjudication — pharmacy-network tier (preferred / standard / out-of-network), dispensing-fee schedule, ingredient-cost basis (AWP-discount, WAC-discount, NADAC-discount), copay-collection rules, generic-substitution rules. Critically: NOT the current contract terms; the historical contract terms at the moment that specific claim was adjudicated.

WHY immutable: Pharmacy networks renegotiate constantly; contract terms drift by quarter. Pharmacy-claim disputes (and the related litigation surface) are routinely scoped to the contract version in effect at adjudication, not the current contract version. Pharmacy-network audit programs require the PBM to demonstrate that each claim was priced under the correct contract version at the correct effective date. Mutable contract-terms-at-adjudication history collapses the PBM's defensibility against systematic-overcharge or systematic-underpayment allegations.

RETENTION: Pinned to (a) the longest pharmacy-network contract retention floor across the PBM's contract base, typically 7+ years, (b) any state insurance-department audit window. Practical floor commonly 10 years.

### DSCSA track-and-trace records

WHAT: Drug Supply Chain Security Act dispensing-event records — the chain-of-custody data for each prescription dispensed, including transaction history (TH), transaction information (TI), and transaction statement (TS) per 21 USC §360eee-1. Includes the manufacturer-of-record, the wholesale-distributor lineage, the lot-and-expiration data, and the dispensing-pharmacy attribution.

WHY immutable: DSCSA §582 requires dispensing entities (which includes mail-order and specialty pharmacies operated by or under contract with the PBM) to retain transaction information for 6 years from the date of the transaction. Mutable TI/TS data destroys the chain-of-custody integrity that DSCSA was enacted to protect; FDA inspections rely on reconstructable DSCSA records to investigate suspect products. <!-- SME-review: confirm whether the PBM's specialty-pharmacy and mail-order operations are themselves §582-regulated dispensing entities or whether DSCSA exposure is limited to the pharmacy partners. -->

RETENTION: 6 years from transaction date per 21 USC §360eee-1(d). State pharmacy-board reporting requirements may extend this floor.

### State pharmacy-board reportable events

WHAT: Events that trigger state pharmacy-board reporting obligations — adverse drug events identified through PBM-side DUR processing, controlled-substance dispensing anomalies surfaced through PMP integration, pharmacy-licensure-relevant findings (counterfeit-drug suspicion, diversion patterns), and any event that the PBM is required to report to a state board under the licensure framework governing its mail-order or specialty operations.

WHY immutable: State pharmacy boards investigate practice complaints with multi-year lookback windows; the PBM's ability to demonstrate timely and accurate reporting depends on having an immutable record of what was reported, when, and to which board. Mutable reportable-events history converts a routine state-board inquiry into a documentation failure independent of the underlying clinical question. <!-- SME-review: state pharmacy-board retention requirements vary substantially; confirm the floor for the PBM's primary operating states. -->

RETENTION: Pinned to the longest applicable state pharmacy-board retention floor across the PBM's operating footprint; typically 5–10 years depending on state.
```

- [ ] **Step 3: Apply the edit.**

Insert the 5 new class entries at the end of the class list (after the cryptographic-key lifecycle class added by PR #22), before any closing cross-reference section.

- [ ] **Step 4: Verify.**

```bash
grep -cE "^### " domains/pbm/immutability-classes.md  # count of class headings; expected to grow by 5
apd-gauntlet validate-domain pbm
```

- [ ] **Step 5: Commit.**

```bash
git commit -am "feat(immutability-classes): add 5 PBM-specific class entries

Adds rebate calculation history, MAC pricing history, network-pharmacy
contract terms at adjudication, DSCSA track-and-trace records (21 USC
§360eee-1), and state pharmacy-board reportable events. Each class has
WHAT / WHY-immutable / RETENTION framing matching the comparator-pack
rhetorical style. SME-review markers flag the state-by-state retention
floors and DSCSA dispensing-entity classification for domain-expert
validation."
```

### Task C2: Open PR-C

- [ ] Open PR with description naming the 5 new classes and the SME-review markers.

**Acceptance criteria for PR-C:**
- 5 new `### ` class headings present, in the order specified
- Each new class has WHAT / WHY-immutable / RETENTION sub-paragraphs
- Existing classes (including the ones landed by PR #22) are preserved verbatim
- SME-review markers are present where the draft cannot verify spec details independently
- Pack validation + tests pass

---

# PR-D — Efforts 6 + 7: Claims-lifecycle + NCPDP/X12 vocabulary

**Branch:** `pbm-consequential-actions-and-data-taxonomy-protocol-vocab`
**Files:**
- `domains/pbm/consequential-actions.md`
- `domains/pbm/data-taxonomy.md`

**Reference files for style:**
- `domains/api-security/consequential-actions.md`
- `domains/identity-security/consequential-actions.md`
- `domains/api-security/data-taxonomy.md`

**Goal:** Decompose the claims-adjudication lifecycle into NCPDP-anchored event classes; add the HIPAA patient-rights event surface (§§164.522-528); add the prior-authorization and DUR/COB lifecycle surfaces; add NCPDP D.0, X12, and CMS PDE protocol-element vocabularies to data-taxonomy.md with per-field sensitivity and handling rules.

**SME-review disposition:** This PR carries the largest concentration of SME-review markers in the larger-efforts plan. The draft is built from publicly-available NCPDP D.0, X12, and CMS PDE specification documentation, but the LLM cannot verify which sub-fields a specific PBM implements, which transaction subsets a switch operator passes through, or which CMS PDE field changes have shipped in recent regulatory updates. The PR description must enumerate every SME-review marker so a domain expert can validate the draft without re-doing the structural work.

### Task D1: Decompose the claims-adjudication lifecycle in consequential-actions.md

**Files:**
- Modify: `domains/pbm/consequential-actions.md`

- [ ] **Step 1: Draft the Claims-lifecycle events section.**

Insert as a new section after the existing content (which includes the audit-of-audit, break-glass, and actor-class sections landed by PR #22):

```markdown
## Claims-adjudication lifecycle events

The claim-adjudication path comprises distinct events, each a consequential action with its own audit requirement. The events below are anchored to NCPDP Telecommunication Standard D.0 transaction codes where applicable.

### Inbound claim submission (NCPDP D.0 B1)

The pharmacy submitter transmits a B1 claim-billing request. Audit content: submitter NCPDP pharmacy ID, submitter NPI, transmitting switch (RelayHealth / Change Healthcare / Surescripts), inbound message digest (for replay-detection), member identifier and group_id, claim_reference_number, RX_number, prescriber NPI, and the NCPDP message body retained for the audit-event retention floor (HIPAA §164.316(b)(2)(i) 6-year). <!-- SME-review: confirm whether the audit needs to retain the raw NCPDP message or whether a normalized projection is sufficient under the PBM's pharmacy-network contract terms. -->

### Eligibility lookup (X12 270/271)

The adjudication engine queries the eligibility surface. Audit content: eligibility-query timestamp, member identifier, group_id, plan_id, the 271 response detail (coverage tier, accumulator state, prior-authorization-required flags), and which downstream decisions were keyed off the lookup. <!-- SME-review: confirm the X12 270/271 use here — some PBMs use NCPDP eligibility transactions (E1) rather than X12; the audit content should follow whichever protocol the PBM actually uses. -->

### DUR/COB pre-check

DUR engine evaluates drug-drug, drug-disease, drug-allergy, drug-age, therapeutic-duplication, and refill-too-soon checks; COB engine evaluates primary-vs-secondary insurance and accumulator allocation. Audit content: DUR-rule set version applied, COB tree resolved, the specific alerts raised (or specific reasons no alerts were raised — silence is auditable too), and the pharmacist / operator response if any alert reached the dispensing surface.

### Prior-authorization check

PA-criteria engine evaluates the request against the configured criteria for the drug-and-condition combination. Audit content: PA-criteria version applied, drug NDC and member diagnosis (when available), the criteria-evaluation result (auto-approve, auto-deny, route-to-clinical-review), and any operator override of the auto-decision.

### Formulary and tier resolution

Formulary engine resolves drug-to-formulary-tier, applies step-therapy or quantity-limit rules, evaluates formulary exceptions, and computes the tier-anchored copay basis. Audit content: formulary version applied, tier assigned, exception or override applied (if any), and the tier-anchored copay calculation. <!-- SME-review: formulary-version audit is load-bearing for retroactive-claim-reprocessing disputes; confirm the PBM's formulary-version retention is sufficient to support member appeals filed up to N years post-claim. -->

### Adjudication decision

Adjudication engine emits the response code — paid, rejected with NCPDP reject codes (with reason), captured for audit. The decision is the canonical "consequential action" of the lifecycle; downstream copay-collection, pharmacy-reimbursement, and PDE-submission flows all key off this event.

Audit content: decision code, ingredient cost, dispensing fee, copay calculation, gross amount due, basis-of-reimbursement, prescription origin code, and the full attribution chain (which rule version, which formulary version, which DUR result, which PA result).

### DUR alert raised + operator/pharmacist response

When a DUR alert reaches the dispensing surface, the pharmacist either acknowledges or overrides. Audit content: alert type and severity, the specific clinical issue, the pharmacist NPI overriding, the clinical justification entered (free-text or coded), and whether a supervising-pharmacist attestation was required and recorded.

### Claim reversal (NCPDP D.0 B2)

Pharmacy submits a reversal of a previously-paid claim. Audit content: the original claim_reference_number being reversed, the reversal reason, the reversal timestamp, and the impact on accumulator state. Maps to T1565.001 when the reversal is initiated by an unauthorized actor against an already-paid claim.

### Claim rebill (NCPDP D.0 B3)

Pharmacy submits a rebill of a previously-reversed claim. Audit content: the original claim_reference_number, the rebill's updated fields (typically NDC or quantity), and the linkage between the original, the reversal, and the rebill.

### Mail-order or specialty pathway split

When the formulary or PA criteria route a claim to mail-order or specialty fulfillment, a distinct fulfillment-side audit chain begins. Audit content: which fulfillment partner, the order-routing decision rationale, the shipping address and delivery method, and the partner-side dispensing-event linkage back to the original claim.
```

- [ ] **Step 2: Draft the HIPAA patient-rights events section.**

Add another section after the Claims-adjudication lifecycle section:

```markdown
## HIPAA patient-rights events (§§164.522–164.528)

The HIPAA Privacy Rule grants individuals specific rights with respect to their PHI. Each exercise of one of these rights is a consequential action with audit and substantive-response requirements.

### Right to request restriction (§164.522)

Member requests restriction on the PBM's use or disclosure of their PHI. Audit content: request, identity verification of the requester, scope of the requested restriction, the PBM's response (granted / partially granted / denied with reasoning), and any downstream propagation of the restriction to vendor partners under §164.504(e) BAA. Note the §164.522(a)(1)(vi) exception: a restriction request related to a service paid for in full by the individual must be granted absent narrow exceptions.

### Right of access (§164.524)

Member requests a copy of their PHI in a designated record set. Audit content: requester identity, identity-verification artifact (especially load-bearing for portal-initiated requests where the verification depth is sometimes weaker than for paper requests), scope of the records requested, the fee charged if any (must conform to §164.524(c)(4) reasonable-cost-based fee), the delivery method (electronic to member, electronic to designated third party, paper), and the response timeline. The 30-day response window (§164.524(b)(2)) is part of the audit-event content because timeliness is itself a §164.524 compliance question.

### Right to amend (§164.526)

Member requests amendment to PHI. Audit content: the amendment request, the PBM's decision (accept / deny with permitted-disagreement-statement), the dissemination of the decision to those who received the unamended record per §164.526(c)(3), and the link between the original PHI item and the amendment.

### Right to an accounting of disclosures (§164.528)

Member requests an accounting of disclosures of their PHI for the preceding 6 years. Audit content: the disclosure-event records covering the 6-year window, the requester identity, the response timeline (60-day default; 30-day extension permissible), and any fee charged for additional accountings within a 12-month window. <!-- SME-review: confirm whether PBM-to-CMS PDE submissions count as "disclosures" required under §164.528 — the Treatment/Payment/Operations exception under §164.506 commonly applies but the determination is fact-specific. -->

### Right to receive PHI via electronic delivery to a designated third party (§164.524(c)(4))

Member directs the PBM to deliver PHI to a designated third party in an electronic format. Audit content: identity verification of the designated third party (a common attack surface), the format requested, the delivery confirmation, and the consent chain authorizing the disclosure.
```

- [ ] **Step 3: Draft the Prior-authorization lifecycle section.**

```markdown
## Prior-authorization lifecycle

Prior authorization is a distinct PBM workflow with its own audit surface, separate from claim-adjudication.

### PA submission

Prescriber or pharmacist initiates a PA request. Audit content: requesting prescriber NPI, member identifier, drug NDC, requested duration, supporting clinical information attached.

### PA criteria evaluation

PA engine evaluates the request against the configured criteria. Audit content: criteria version applied, evaluation result (auto-approve / auto-deny / route-to-clinical-review with reason), the specific criteria clauses that drove the result.

### Clinical review (when applicable)

Pharmacist or medical director reviews routed requests. Audit content: reviewer NPI / DEA, review timestamp, clinical-justification entered, decision (approve / approve-with-conditions / deny), conditions attached if any.

### PA decision communication

PA decision is communicated to the prescriber and the member. Audit content: decision timestamp, communication channel (fax / electronic / phone), recipient confirmation. Medicare Part D has specific timeline rules per 42 CFR §423.566 (standard requests: 72 hours; expedited: 24 hours).

### Appeals processing

Member appeals a denied PA. Audit content: appeal initiation, appeal reviewer (must be different from initial decision-maker per Medicare Part D §423.578), appeal decision, appeal timeline tracking (Medicare Part D §423.590 strict timelines). <!-- SME-review: confirm whether the PBM operates as a Medicare-only Part D plan, a commercial-and-Medicare blend, or a primarily-commercial book; the appeals discipline shifts substantially between Medicare-Part-D-enforced timelines and ERISA-governed commercial-plan timelines. -->

### Tier exception decisions

Distinct from PA: member requests a formulary tier exception (drug X covered at lower-cost tier). Audit content: exception-request basis (clinical-necessity argument, comparable-effectiveness argument), reviewer NPI, decision, and the duration of the exception if granted.
```

- [ ] **Step 4: Draft the DUR / COB lifecycle section.**

```markdown
## DUR / COB lifecycle

### DUR rule-set authoring

Clinical operator authors or edits a DUR rule. Audit content: rule version, drug-trigger criteria, alert text shown to pharmacist, severity classification, operator NPI, dual-approval attestation (required for safety-class rules; absent = High clinical-harm finding per the severity rubric).

### DUR rule deployment

DUR rule moves from authoring to production. Audit content: deployment timestamp, deployment approver (separate from author), rollback availability, the version range of the rule's effective-date window.

### DUR alert raise / response

(See Claims-adjudication lifecycle — DUR alert raised + operator/pharmacist response above; the lifecycle event is the same.)

### COB tree resolution

Adjudication engine resolves the coordination-of-benefits tree across primary / secondary / tertiary coverage. Audit content: the COB version applied, the resolution path (which insurer was determined primary, secondary, tertiary), the accumulator-state inputs, and the apportionment of payment liability across insurers.
```

- [ ] **Step 5: Apply edits and verify.**

```bash
grep -cE "^## " domains/pbm/consequential-actions.md  # should grow by 4 (new top-level sections)
apd-gauntlet validate-domain pbm
```

- [ ] **Step 6: Commit.**

```bash
git commit -am "feat(consequential-actions): decompose claims-lifecycle, PA, DUR/COB, and HIPAA patient-rights surfaces

Adds four new top-level sections to consequential-actions.md:
- Claims-adjudication lifecycle events (NCPDP-anchored, 9 sub-events)
- HIPAA patient-rights events (§§164.522-528 surface)
- Prior-authorization lifecycle (6 sub-events including appeals)
- DUR/COB lifecycle (rule authoring, deployment, alert handling, COB tree)

Each sub-event names the required audit content. NCPDP D.0 transaction
codes (B1/B2/B3), X12 transactions (270/271), and 42 CFR Part 423 CMS
rules are cited inline.

SME-review markers are present where the draft uses public spec
language but cannot verify implementation specifics (raw-vs-normalized
NCPDP audit retention, NCPDP-E1-vs-X12-270 eligibility protocol,
formulary-version retention floor, PDE-as-§164.528-disclosure question,
Medicare-vs-commercial appeals discipline)."
```

### Task D2: Add NCPDP / X12 / PDE protocol vocabulary to data-taxonomy.md

**Files:**
- Modify: `domains/pbm/data-taxonomy.md`

- [ ] **Step 1: Draft the NCPDP D.0 field reference section.**

Insert after the existing content (which includes the quasi-identifier combinations + audit-sensitivity inheritance sections landed by PR #22):

```markdown
## NCPDP D.0 SCRIPT field reference

The NCPDP Telecommunication Standard D.0 is the dominant pharmacy-claim transaction protocol. Each major segment carries fields with distinct sensitivity classifications, masking rules, and retention requirements.

### Transaction header

| Field | Sensitivity | Safe Harbor (§164.514(b)(2)(i)) | Notes |
|---|---|---|---|
| BIN (Bank Identification Number) | Operational | Not an identifier | Identifies the PBM as payer |
| PCN (Processor Control Number) | Operational | Not an identifier | Identifies the PBM's adjudication context |
| Group ID | Operational | Quasi-identifier in combination | Plan-sponsor identifier; combined with NDC and date can re-identify in small groups |
| Cardholder ID | PHI direct identifier | Listed in §164.514(b)(2)(i)(B) | Cannot be masked without breaking adjudication |
| Person Code | Quasi-identifier | Combined with Cardholder ID is identifying | Dependent-coverage attribution |

### Claim segment

| Field | Sensitivity | Notes |
|---|---|---|
| Claim Reference Number | Operational | Tokenization breaks PDE submission linkage; do not tokenize |
| RX Number | PHI when combined with member identifier | Cannot be masked for prescriber-attribution audit |
| Days Supply | PHI quasi-identifier | Combined with NDC + member-demo enables re-identification |
| Dispense As Written code | Clinical-decision artifact | Audit-load-bearing; never mask |

### Prescriber segment

| Field | Sensitivity | Notes |
|---|---|---|
| Prescriber NPI | PII (not PHI per §164.514) | Public registry data; never mask |
| DEA Number | Operational + regulated | DEA records subject to 21 CFR §1304.04; state pharmacy-board reporting may extend |
| State License | Public registry data | State-by-state |

### Patient segment

| Field | Sensitivity | Safe Harbor treatment | Notes |
|---|---|---|---|
| First / Last Name | PHI direct identifier | §164.514(b)(2)(i)(A) | Required for adjudication; mask in analytics surfaces |
| Date of Birth | PHI direct identifier | §164.514(b)(2)(i)(C) | Required for DUR age-based rules; year-only safe |
| Gender | Quasi-identifier | Not in §164.514(b)(2)(i) | Combined with rare diagnosis re-identifies |
| Address Fields | PHI direct identifier | §164.514(b)(2)(i)(B) | ZIP3 may be retained per §164.514(b)(2)(i)(B) exception |
| Patient ID Qualifier | Operational | Not an identifier | Specifies the type of patient ID supplied |

### Pharmacy segment

| Field | Sensitivity | Notes |
|---|---|---|
| Pharmacy NCPDP ID | Operational | Network-attribution data |
| Pharmacy NPI | Public registry data | Never mask |
| Pharmacy Address | Operational + quasi-identifier | Small-pharmacy + dispensing date enables re-identification |

### DUR/PPS segment

DUR/PPS fields carry both clinical-decision artifacts and PHI quasi-identifiers. Reason-for-Service, Professional-Service Code, and Result-of-Service must be retained in the audit chain to defend the clinical-decision pathway. None can be masked in the audit retention.

### Pricing segment

Pricing fields (Ingredient Cost, Dispensing Fee, Copay Amount, Gross Amount Due, Basis of Reimbursement) are commercial-confidentiality data. Encryption-at-rest tier-2 with PBM-internal access scoping; export to plan-sponsor surfaces requires contract-defined data-scope enforcement. <!-- SME-review: PBM-pricing-transparency state laws affect which pricing fields can be exposed to which audiences; the per-state matrix is implementation-specific. -->
```

- [ ] **Step 2: Draft the X12 transaction reference section.**

```markdown
## X12 transaction reference

The PBM commonly participates in HIPAA-mandated X12 transactions for plan-sponsor and Medicare workflows. Each transaction has distinct PHI-bearing segments and audit requirements.

### 270/271 — Eligibility inquiry/response

The 270 carries patient demographic + member identifier + subscriber relationship; the 271 response carries coverage tier, accumulator state, and benefit detail. Both are PHI under HIPAA. Audit retention floor: HIPAA §164.316(b)(2)(i) 6-year floor; plan-sponsor MSA may extend.

### 837 — Healthcare Claim

The 837 (institutional and professional variants) carries facility-side claims that may be submitted for institutional pharmacy claims and mail-order facility claims. Encryption-in-transit (TLS) and at-rest required; audit retention floor per HIPAA §164.316(b)(2)(i).

### 835 — Healthcare Claim Payment

The 835 carries payment + adjustment reason codes. Payment data is commercial-confidentiality; member identifiers in the 835 are PHI. Audit retention as above.

### 999 — Implementation Acknowledgment

Transaction-level acknowledgment. Operational; minimal PHI exposure. Audit retention follows the parent transaction.

### 277 — Healthcare Claim Status

Claim-status responses to plan-sponsor inquiries. PHI under HIPAA. Audit retention as above.

<!-- SME-review: confirm which X12 transactions the PBM actually originates or terminates versus which it merely passes through; the audit chain depth differs between origination and pass-through. -->
```

- [ ] **Step 3: Draft the CMS PDE field reference section.**

```markdown
## CMS Part D PDE submission field reference

The CMS Part D Prescription Drug Event submission carries pharmacy-claim data to CMS for payment-determination and risk-adjustment. Field-level handling is anchored to 42 CFR §423.322 and the CMS Plan Communications User Guide (PCUG).

| Field group | Examples | Sensitivity | Notes |
|---|---|---|---|
| Plan attribution | Contract ID, PBP ID | Commercial-confidentiality + CMS-operational | Pinned per CMS Plan Communications User Guide |
| Beneficiary identifier | HICN (legacy) or MBI (Medicare Beneficiary Identifier) | PHI direct identifier | MBI replaced HICN per 42 CFR §423.120 / MACRA mandate |
| Prescription service reference | Prescription Service Reference Number | Operational + PHI when combined | Links to NCPDP claim |
| Date of service | Service date | PHI quasi-identifier (with NDC) | Required for retroactive-claim-reprocessing |
| Drug identifier | NDC | Operational + clinical | Combined with rare-disease NDC + ZIP3 + age band re-identifies |
| Quantity / days supply | Quantity Dispensed, Days Supply | PHI quasi-identifier | Audit-load-bearing for DUR defensibility |
| Brand/generic | Brand-Generic indicator, DAW code | Clinical-decision artifact | Audit-load-bearing |
| Service provider | Service Provider ID (NPI) | Public registry data | Never mask |
| Prescriber | Prescriber ID (NPI) | Public registry data | Never mask |
| Pricing fields | Ingredient Cost, Dispensing Fee, Sales Tax, Gross Drug Cost Below Catastrophic, Gross Drug Cost Above Catastrophic, Patient Liability, Plan-Sponsored Amount, Low-Income Subsidy, Total Amount Paid | CMS-confidential commercial | CMS Data Use Agreement governs |
| Adjustment | Adjustment indicator | Operational | Tracks corrections and resubmissions |
| Prescription origin | Prescription Origin Code | Clinical metadata | Required for audit |

Sensitivity treatment: PDE records contain both PHI (MBI is a PHI element) AND CMS-confidential pricing. They cannot be exported to non-HIPAA-covered analytics surfaces without de-identification AND CMS Data Use Agreement compliance. <!-- SME-review: confirm the current MBI implementation status — the legacy HICN identifier has been phased out per MACRA, but field-name retention in legacy ETL may persist. -->
```

- [ ] **Step 4: Draft the per-field masking / tokenization decision-tree section.**

```markdown
## Per-field masking and tokenization decision tree

For each major field class, the decision of whether to mask, tokenize, redact, or pass-through depends on the downstream consumer and the audit-defensibility requirement.

### Member-identifier handling

- **Token member_id for analytics surface**: preserve referential integrity within a single analytics tenant only; the token must NOT be reusable across analytics tenants (would enable cross-tenant linkage attack on de-identification).
- **Cannot tokenize for adjudication path**: the live adjudication engine, the PA engine, the DUR engine, and the PDE submission pipeline all need the raw member identifier; tokenization breaks adjudication.
- **Cannot tokenize for HIPAA Right of Access**: the §164.524 request flow needs to resolve the raw member identifier to produce the designated record set.

### Date-of-birth handling

- **Mask DOB to year-only for population-level analysis**: per §164.514(b)(2)(i)(C) exception, year is permissible while month/day are direct identifiers.
- **Cannot mask for DUR age-based rules**: pediatric and geriatric dosing rules need the full DOB.
- **Cannot mask for PA criteria with age gates**: PA criteria referencing pediatric or geriatric thresholds need the full DOB.

### Address handling

- **Retain ZIP3** per §164.514(b)(2)(i)(B) exception when retaining the population covered by that ZIP3 is greater than 20,000 individuals.
- **Mask street address** for analytics; cannot mask for member-fulfillment delivery.

### Prescriber identifier handling

- **Never mask DEA number**: state pharmacy-board reporting requires full DEA, and DEA records have separate retention obligations under 21 CFR §1304.04.
- **Never mask NPI**: public-registry data.

### Quasi-identifier combination suppression

- When two or more of the quasi-identifier combinations enumerated in the Quasi-identifier combinations section above appear in the same export, the Confidentiality specialist raises a finding asking for §164.514(b)(1) Expert Determination before export proceeds. <!-- SME-review: the Expert Determination workflow varies by PBM — some operate an internal qualified statistician, others contract out. The data-taxonomy guidance should reflect the PBM's actual process. -->

### Claim-reference and RX-number handling

- **Never tokenize claim reference number**: PDE submission and pharmacy-network audit both need the raw claim_reference_number.
- **Never mask RX number**: prescriber-attribution audit and pharmacy-attribution audit both need the raw RX number.

### Pricing-field handling

- **Pass-through for plan-sponsor reporting** within the contract-defined scope.
- **Encrypt-at-rest tier-2** for PBM-internal pricing data; CMS PDE pricing is tier-1 under the CMS DUA.
- **Mask for non-contractual analytics** export — the rebate-aggregator surface, the COB-carrier surface, and analytics tenants outside the plan-sponsor scope cannot see ingredient cost, MAC, or dispensing fee.
```

- [ ] **Step 5: Apply edits and verify.**

```bash
grep -cE "^## " domains/pbm/data-taxonomy.md  # should grow substantially
apd-gauntlet validate-domain pbm
.venv/bin/python -m pytest -q
```

- [ ] **Step 6: Commit.**

```bash
git commit -am "feat(data-taxonomy): add NCPDP D.0, X12, CMS PDE field references + masking decision tree

Adds four new sections to data-taxonomy.md:
- NCPDP D.0 SCRIPT field reference (transaction header, claim,
  prescriber, patient, pharmacy, DUR/PPS, pricing segments)
- X12 transaction reference (270/271, 837, 835, 999, 277)
- CMS Part D PDE submission field reference (anchored to 42 CFR
  §423.322 and the CMS Plan Communications User Guide)
- Per-field masking / tokenization decision tree

Each field group identifies sensitivity class, Safe Harbor treatment
under §164.514(b)(2)(i) where applicable, and masking / tokenization
guidance with the rationale for each rule.

SME-review markers flag PBM-pricing-transparency state-law variability,
X12-origination-vs-pass-through audit chain depth, MBI implementation
status, and Expert Determination workflow variation."
```

### Task D3: Open PR-D

- [ ] Open PR. The PR description must enumerate every SME-review marker (one bullet per marker) so a domain expert can validate without reading the entire diff.

**Acceptance criteria for PR-D:**
- 4 new top-level sections in consequential-actions.md (Claims-lifecycle, HIPAA patient-rights, PA lifecycle, DUR/COB lifecycle)
- 4 new top-level sections in data-taxonomy.md (NCPDP, X12, PDE, masking decision tree)
- Existing content preserved verbatim in both files
- All SME-review markers use the `<!-- SME-review: ... -->` HTML comment form, never `TODO:` or bare placeholder text
- The PR description enumerates every SME-review marker with file path and question
- Pack validation + tests pass

---

# PR-E — Efforts 4 + 5: ATT&CK/D3FEND + prerequisite_evidence across 9 common-patterns files

**Branch:** `pbm-common-patterns-attck-and-prereq-evidence`
**Files:** all 9 files under `domains/pbm/common-patterns/`
**Reference files for style:**
- `domains/api-security/common-patterns/confidentiality.md` (compact ATT&CK mapping example)
- `domains/identity-security/common-patterns/authenticity.md` (NIST 800-63B + ATT&CK in same section)
- `domains/security-tooling/common-patterns/non-repudiation.md` (D3FEND counter discipline)

**Goal:** Add an "ATT&CK + D3FEND mapping" section AND expand `prerequisite_evidence` asks to multi-clause specifications across all 9 common-patterns files. Bundled into one PR because both touch the same 9 files; coordinated rewriting per file is cleaner than two passes.

### Strategy

For each of the 9 goal files, the editor agent (one per file, dispatched in parallel) does TWO things:

1. **Add an ATT&CK + D3FEND mapping section.** The section identifies the techniques this APD goal defends against (or is exploited by, for goals like Authenticity), with R1 high-confidence-bar justification per citation.

2. **Expand existing `prerequisite_evidence` asks.** Each single-line ask in the current file is rewritten as a multi-clause specification naming every sub-element an operator must provide to unblock a blocked-on-evidence finding.

Both happen in the same edit pass per file because the agent has already loaded the file context.

### Per-goal ATT&CK + D3FEND mapping content

Each agent's prompt receives the per-goal mapping content below. R1 applies to every citation.

#### confidentiality.md

**ATT&CK techniques the goal defends against:**
- T1213 (Data from Information Repositories), T1213.003 (CRM / PHI repositories) — direct PHI store reads
- T1530 (Data from Cloud Storage) — backup-store and object-store reads
- T1567 (Exfiltration Over Web Service), T1041 (Exfiltration Over C2 Channel) — PHI export channels
- T1078 (Valid Accounts) — credential-driven PHI access
- T1071 (Application Layer Protocol) — exfiltration over HTTPS/DNS

**D3FEND counters:**
- D3-AT (Authentication) for access-gate enforcement
- D3-EDD (Encrypted Data Detection) and D3-EHB (Encrypted Header Block) for outbound DLP
- D3-CL (Code Logging) for audit-of-access
- D3-OS (Operating System Hardening) on the PHI host

#### integrity.md

**ATT&CK:**
- T1565 (Data Manipulation), T1565.001 (Stored) for at-rest tampering, T1565.002 (Transmitted) for in-flight tampering of NCPDP messages or PDE batch files
- T1556 (Modify Authentication Process) when used to bypass write authorization

**D3FEND:**
- D3-MA (Message Authentication) for NCPDP / X12 signed messages
- D3-SBV (System Behavior Validation) for adjudication-logic integrity
- D3-SRA (Schema-Based File Validation) for PDE batch validation

#### availability.md

**ATT&CK:**
- T1499 (Endpoint Denial of Service)
- T1498 (Network Denial of Service)
- T1485 (Data Destruction) when used to disrupt adjudication

**D3FEND:**
- D3-NL (Network Layer Defense) for rate-limiting at pharmacy ingress
- D3-EAL (Executable Allowlisting) for adjudication-binary protection
- D3-ANCI (Authentication Cache Invalidation) for credential-revocation paths

#### distributed.md

**ATT&CK:**
- T1485 (Data Destruction) on a regional data store
- T1565 sub-techniques on cross-region replicated data
- T1078 lateral movement across regions

**D3FEND:**
- D3-OS (OS Hardening) per regional zone
- D3-NTA (Network Traffic Analysis) for cross-region traffic baseline

#### resilient.md

**ATT&CK:**
- T1499 (Endpoint Denial of Service) — backpressure exploitation
- T1496 (Resource Hijacking) when capacity is drained intentionally

**D3FEND:**
- D3-PA (Process Analysis) for resource-exhaustion detection
- D3-DENCR (Decryption) is NOT a counter — caution: do not map this; resilient does not require decryption discipline

#### ephemeral.md

**ATT&CK:**
- T1552 (Unsecured Credentials), T1552.001 (Credentials in Files) — long-lived credentials in config
- T1078 (Valid Accounts) — credentials outliving their intended lifetime
- T1098 (Account Manipulation) — credential reactivation after rotation

**D3FEND:**
- D3-OTF (One-time Token Verification) for short-lived workload credentials
- D3-DR (Decryption Resistance) for credential storage hardening

#### authenticity.md

**ATT&CK:**
- T1621 (MFA Request Generation) — push-bombing / MFA fatigue
- T1556.006 (MFA Interception) — sub-technique
- T1078 (Valid Accounts) when credentials are valid but the holder is unauthorized
- T1110 sub-techniques — credential brute force

**D3FEND:**
- D3-MFA (Multi-factor Authentication)
- D3-OTF (One-time Token Verification)
- D3-AC (Authentication Cache) when designed defensively

#### non-repudiation.md

**ATT&CK:**
- T1070 (Indicator Removal), T1070.002 (Clear Logs)
- T1036 (Masquerading) at the audit-attribution layer
- T1562.008 (Disable or Modify Cloud Logging)

**D3FEND:**
- D3-SBV (System Behavior Validation) on the audit pipeline
- D3-LFAM (Local File Permissions) on the audit substrate
- D3-MA (Message Authentication) for signed audit events

#### immutability.md

**ATT&CK:**
- T1485 (Data Destruction)
- T1490 (Inhibit System Recovery) — disabling backup/snapshot mechanisms
- T1078 used to alter retention or object-lock settings

**D3FEND:**
- D3-FRL (File Removal Limitation) — substrate-enforced
- D3-SBV (System Behavior Validation) for retention-policy drift detection

### Per-goal prerequisite_evidence expansion content

For each goal, the editor agent rewrites the existing single-line `prerequisite_evidence` asks as multi-clause specifications. The content below is the seed for each goal; the agent reads the current asks in the file and expands them.

#### confidentiality.md (seed)

**TLS configuration evidence** (replaces "TLS configuration policy"):
1. Minimum TLS version supported across each ingress (pharmacy NCPDP, member portal, admin console, vendor egress)
2. Cipher-suite allowlist per ingress
3. Certificate-pinning configuration for pharmacy-network ingress and outbound CMS submission
4. HSTS enforcement on member-facing surfaces
5. Certificate rotation cadence and CA-trust policy
6. Certificate-revocation handling (OCSP stapling, CRL refresh interval)
7. Configuration source-of-truth pointer (Terraform module, NGINX config, ALB listener configuration) and CD pipeline applying it

**KMS hierarchy evidence:**
1. Root key location (HSM-backed CMK, customer-managed key, vendor-managed key)
2. KEK (key-encrypting-key) hierarchy diagram
3. DEK (data-encrypting-key) rotation cadence
4. KEK-to-tenant or KEK-to-data-class mapping
5. Key access-control policy (who can use, who can rotate, who can disable)
6. Key-material backup and escrow policy

**Field-level encryption evidence:**
1. Per-PHI-field encryption status (at-rest, in-flight, in-use)
2. Tokenization map for fields not directly encrypted
3. Field-decryption authorization-decision pipeline (who can decrypt, under what authorization)
4. Decryption-event audit chain

#### integrity.md (seed)

**Schema enforcement evidence:**
1. The canonical schema for each cross-boundary message (NCPDP D.0 segments, X12 transactions, internal RPC contracts)
2. Schema-validation enforcement point in the request pipeline (gateway? service-edge? data-tier?)
3. Schema-validation failure handling (reject? quarantine? log-and-pass?)
4. Schema-version negotiation policy

**Write-path authorization evidence:**
1. The authorization-decision pipeline for each PHI-writing endpoint
2. The actor identity and role evaluation at each step
3. The audit-event emitted on grant and on deny
4. Failure mode if the authorization service is unavailable (fail-closed required for PHI write paths)

#### availability.md (seed)

**SLO/SLI definition evidence:**
1. Each SLO defined for pharmacy ingress, member portal, PA workflow, PDE submission
2. The error budget definition
3. The burn-rate alerting thresholds
4. The escalation chain when an SLO is at risk

**Failure-domain evidence:**
1. The failure-domain diagram (which services share which fate)
2. The blast-radius analysis per AZ / region / zonal-service
3. The DR plan with RTO/RPO per data class

#### distributed.md (seed)

**Multi-region topology evidence:**
1. Region topology (active-active, active-passive, follow-the-sun)
2. Cross-region data-replication strategy
3. Consistency model per data class (strong, eventual, bounded staleness)
4. Failover plan including replication-lag tolerance

#### resilient.md (seed)

**Retry-policy evidence:**
1. Retry policy per service-to-service edge
2. Retry budget per request class
3. Backoff strategy
4. Idempotency key handling for retry-safe operations

**Circuit-breaker evidence:**
1. Each circuit-breaker location (inbound, outbound)
2. Trip threshold and recovery threshold
3. Trip-event audit pipeline

#### ephemeral.md (seed)

**Credential lifecycle evidence:**
1. Credential class taxonomy (operator session, service-account, vendor integration, signing key)
2. Per-class lifetime
3. Per-class rotation automation pointer
4. Per-class revocation pipeline
5. The audit chain that records creation, rotation, suspension, destruction

#### authenticity.md (seed)

**MFA implementation evidence:**
1. Factor-mix per actor class (pharmacist, member, admin, vendor-integration)
2. AAL level claimed per actor class per NIST 800-63B (AAL1/2/3) with evidence for the claim
3. Enrollment flow security (re-auth required? identity-proofing artifact? FIDO2-level?)
4. Recovery flow security (rate-limited? supervisor-attested? out-of-band?)
5. MFA-fatigue mitigation (push-rate-limit, number-matching, geographic-anomaly detection)
6. Phishing-resistance posture (SMS forbidden? WebAuthn primary?)
7. The audit event emitted on MFA challenge, response, success, failure

**Signed-message-verification evidence (NCPDP / X12 / PDE):**
1. The signing-key location for each signed-message channel
2. The signature-verification implementation pointer (library, version)
3. The replay-protection mechanism
4. The failure handling on signature verification failure

#### non-repudiation.md (seed)

**Audit-coverage evidence:**
1. The consequential-action surface mapped to the audit-event taxonomy (each consequential action above must emit at least one audit event of the named class)
2. The actor-attribution policy on each audit event class
3. The signing or hash-chaining mechanism per audit-event class
4. The audit-shipping pipeline (queue, transit, sink) with availability target
5. The audit-of-audit pipeline (audit reads, retention-policy changes, log-shipping disable) on a forensically isolated channel
6. The retention-floor enforcement substrate per class

#### immutability.md (seed)

**Per-class retention evidence:**
1. For each immutability class declared above, the retention-floor citation
2. The substrate enforcing the floor (S3 Object Lock Compliance Mode, Azure Blob immutable with legal hold, GCS locked retention, WORM tape, HSM-anchored hash chain)
3. The operator action that becomes infeasible under the substrate
4. The drift-detection mechanism that detects substrate misconfiguration

### Task E1: Editor agents dispatched in parallel — one per file

**Files:**
- Modify: each of the 9 files under `domains/pbm/common-patterns/`

For each file, dispatch an editor agent with:
- The current file contents (it reads via the Read tool)
- The ATT&CK + D3FEND mapping content for that goal (from the per-goal lists above)
- The prerequisite_evidence expansion seed for that goal (from the per-goal seeds above)
- R1, R2, R3, R5 discipline notes

The agent produces an Edit per file:
1. Inserts an "ATT&CK + D3FEND defensive mapping" section AFTER the PBM-stakes paragraph landed by PR #22 and BEFORE the first finding-pattern section
2. Rewrites each existing prerequisite_evidence ask into the multi-clause form

- [ ] Dispatch all 9 editor agents in parallel.
- [ ] Each agent returns a structured edit summary (file, status, list of changes_applied).
- [ ] Verify per file: `grep -E "^## (ATT|D3FEND|MITRE)" domains/pbm/common-patterns/<file>` confirms the new section is present.

### Task E2: Reviewer agents dispatched in parallel — one per file

For each of the 9 files, dispatch an independent reviewer agent with the file path and the acceptance criteria:
- ATT&CK + D3FEND mapping section present in the position specified
- Each ATT&CK citation backed by a one-sentence justification (R1 discipline)
- Each D3FEND citation paired with the ATT&CK it counters
- prerequisite_evidence asks rewritten to multi-clause form
- No file-wide content deletion
- No bare TODO / placeholder text

- [ ] Re-edit any file where the reviewer returned `needs_revision`.
- [ ] Re-review until all 9 files are `approved`.

### Task E3: Commit and open PR

- [ ] One commit per file (so the reviewer can scope per-goal diffs), or a single coordinated commit — coordinator's choice. Single commit is recommended given the cross-file coherence:

```bash
git commit -am "feat(common-patterns): add ATT&CK + D3FEND mapping section and expand prerequisite_evidence asks across all 9 goal files

For each of the 9 APD goals (confidentiality, integrity, availability,
distributed, resilient, ephemeral, authenticity, non-repudiation,
immutability):

  • Inserts an 'ATT&CK + D3FEND defensive mapping' section after the
    PBM-stakes paragraph. Each ATT&CK citation follows the
    apd-control-mappings high-confidence-bar discipline (one-sentence
    justification per citation, no shotgun mapping). Each D3FEND counter
    cites the ATT&CK technique it counters per apd-attack-path-discipline.

  • Rewrites each existing single-line prerequisite_evidence ask as a
    multi-clause specification naming every sub-element an operator
    must provide to unblock a blocked-on-evidence finding.

Each file edited by an independent editor agent (one per file,
dispatched in parallel) with an independent reviewer pass.
All 9 files approved by the reviewer phase before commit."
```

- [ ] Open PR. The PR description enumerates the 9 files touched, the ATT&CK technique IDs added per file, and any SME-review markers (none expected in this PR since the mappings are framework-grounded, not domain-specific).

**Acceptance criteria for PR-E:**
- All 9 common-patterns files have the new ATT&CK + D3FEND section in the specified position
- All 9 files have expanded prerequisite_evidence asks (no remaining single-line asks)
- Each ATT&CK citation has a justification (verified by reviewer-agent diff inspection)
- Each D3FEND citation references its ATT&CK counter
- Existing finding-pattern bullets preserved verbatim
- Pack validation + tests pass

---

## Cross-cutting verification at the end of the plan

After all 5 PRs land on main, run the full integration check:

- [ ] **Step 1: Re-pull main and verify cumulative state.**

```bash
git checkout main
git pull --ff-only
apd-gauntlet validate-domain pbm
.venv/bin/python -m pytest -q
```

- [ ] **Step 2: Re-run the cross-pack audit workflow (the same 6-dimension audit that produced the original gap list).**

The expected outcome: the new audit shows the originally-high-severity gaps as closed (or moved to do_nothing_zones), with possibly some new low-severity polish gaps surfaced. This validates that the larger-efforts work actually addressed what the audit identified.

- [ ] **Step 3: Re-run an example gauntlet against a synthetic PBM tech plan.**

The bundled `examples/apd-20260601-claim-event-bus/` example or a freshly scaffolded run. Confirm that:
- Specialist agents cite the new crown_jewels and attacker_positions
- Severity assignments use the new two-axis rubric
- Common-patterns ATT&CK / D3FEND mappings are referenced in findings
- Consequential-actions decomposition shows up in non-repudiation findings

Document any specialist behavior that did not pick up the new content as a follow-up issue (likely a prompt update in the relevant specialist agent's instructions, not a pack change).

---

## Follow-up backlog (post-implementation)

These are NOT in this plan but become tractable once it lands:

1. **Domain-expert SME pass.** Resolve all `<!-- SME-review: ... -->` markers introduced in PRs D. A PBM SME reviews each marker and either replaces it with the verified content or files a follow-up ticket. Filter: `grep -RIn 'SME-review:' domains/pbm/`.

2. **Specialist-agent prompt updates.** Where specialist agents do not pick up the new pack content (verified in cross-cutting verification step 3), update the agent prompts to explicitly reference the new sections.

3. **Run the framework against a real PBM tech plan.** When the user is ready to use the gauntlet against a non-synthetic PBM, the strengthened pack should produce richer findings than pre-pack-update runs.

4. **Re-evaluate `do_nothing_zones`.** Some areas the original audit marked as do_nothing_zones may have shifted; re-audit annually.

5. **Cross-pack drift detection.** Now that pbm is on par with the other three packs, consider adding a CI check that fails if pbm grows substantially smaller than the average comparator pack in any single dimension.

---

## Self-review

**Spec coverage check.** Cross-walking the 7 efforts against the PRs:
- ✅ Effort 1 (domain.yaml expansion) → PR-A tasks A1, A2, A3
- ✅ Effort 2 (severity-rubric two-axis + anchors) → PR-B tasks B1, B2, B3
- ✅ Effort 3 (immutability classes — re-scoped given PR #22 landed substrate + key-lifecycle already) → PR-C task C1
- ✅ Effort 4 (ATT&CK + D3FEND in common-patterns) → PR-E task E1 ATT&CK content
- ✅ Effort 5 (prerequisite_evidence expansion) → PR-E task E1 prerequisite_evidence content
- ✅ Effort 6 (claims-lifecycle + HIPAA patient-rights decomposition) → PR-D task D1
- ✅ Effort 7 (NCPDP/X12 vocabulary) → PR-D task D2

**Placeholder scan.** Searched for: TBD / TODO / "implement later" / "fill in" / "add appropriate" / "similar to" → none in the plan. All draft content blocks are complete YAML and complete Markdown ready to apply.

**Type consistency check.** The plan uses these names consistently throughout: `crown_jewels`, `attacker_positions`, `default_trust_boundaries` (YAML keys); `prerequisite_evidence` (lowercase underscore); `ATT&CK` and `D3FEND` (canonical capitalization); `SME-review` markers using HTML comment form. No inconsistencies.

**Scope check.** Each PR touches files that no other PR in this plan touches in the same wave. PR-E touches 9 files in a single bundled effort to avoid double-touching them across separate PRs.

**Domain-expertise honesty check.** PR-D explicitly carries SME-review markers wherever the LLM cannot verify NCPDP / X12 / Medicare-specific implementation details. The plan does not pretend an LLM substitutes for a domain expert; it scaffolds the structural work so a domain expert can validate without re-doing it.

Plan complete.
