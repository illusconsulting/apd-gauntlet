# PBM Severity Rubric (impact-to-PBM)

Calibrated against impact-to-PBM, not against generic CVSS. The specialist agent cites the matching clause in finding `detail` fields. Cited examples in each tier are illustrative, not exhaustive.

PBM severities have a **second dimension** beyond classic HIPAA-data-confidentiality and CMS-data-integrity: the **clinical patient-harm dimension**. A finding that exposes PHI or corrupts PDE submission is scored on the data-and-regulatory axis; a finding that affects a clinical-decision pathway — drug-utilization review, prior-authorization decision, formulary-substitution logic, dispense-as-written enforcement, dosage calculation — is scored on the patient-harm axis. Many findings score on both axes; severity is the higher of the two. The PBM-specific implication: a DUR-rule edit that produces a missed drug-interaction alert can be Critical on the patient-harm axis even if the affected member-population is below the 500-member HIPAA breach threshold on the data-and-regulatory axis.

References inline: HIPAA Privacy Rule (45 CFR 164 Subpart E), HIPAA Security Rule (45 CFR 164 Subpart C), NIST SP 800-53r5 control families, NIST SP 800-63B authenticator assurance levels (AAL2/AAL3), MITRE ATT&CK Enterprise techniques, MITRE D3FEND countermeasures, NCPDP Telecommunication Standard D.0, CMS Part D PDE Submission (42 CFR 423.322), HITRUST CSF (healthcare accreditation framework).

## Critical

Any of the following:

- **PHI exfiltration capability affecting >500 members** in a single realistic attack scenario. Triggers HIPAA breach notification per 45 CFR §164.408 (federal, state, and media notification). The 500-member threshold is the legal pivot point for required public disclosure. Maps to T1213 (Data from Information Repositories) for bulk reads against the PHI store, plus T1041 (Exfiltration Over C2 Channel) or T1567 (Exfiltration Over Web Service) depending on the channel the attacker can reach; note that NCPDP D.0 transactional egress (claim-response payloads returned to switches and pharmacy chains) is itself a PHI-carrying channel and must be in scope for the same egress controls. D3FEND counter is D3-OTF (Outbound Traffic Filtering — DLP at the egress boundary) and D3-NTA (Network Traffic Analysis on outbound flows from the PHI tier). NIST 800-53r5 anchor: AC family — AC-3 (Access Enforcement), AC-4 (Information Flow Enforcement), AC-6 (Least Privilege) — plus SI-4 (System Monitoring) and SC-7 (Boundary Protection) on the egress surface.
- **Claim adjudication corruption affecting therapeutic decisions** — wrong drug dispensed, wrong dose, missed Drug Utilization Review (DUR) alert, formulary bypass that exposes patients to harmful drug interactions, missed prior authorization on safety-gated drugs. Direct patient harm risk. Maps to T1565.001 (Stored Data Manipulation) for tampering of the formulary, DUR, or PA-criteria configuration stores that drive the adjudication decision, and T1565.002 (Transmitted Data Manipulation) for in-flight tampering of the NCPDP claim request or response between switch and adjudication engine; D3FEND counter is D3-MAN (Message Authentication) on signed NCPDP D.0 transactions, paired with operational safeguards on the clinical-decision-logic configuration surface (no clean D3FEND ID exists for decision-path runtime validation; rely on the NIST 800-53r5 SI-7 / CM-3 / CM-5 anchors below). NIST 800-53r5 anchor: SI family — SI-7 (Software, Firmware, and Information Integrity) and SI-10 (Information Input Validation) — plus CM-3 (Configuration Change Control) and CM-5 (Access Restrictions for Change) on the clinical-decision-logic configuration surface.
- **Authentication bypass to PHI surfaces or admin functions** — no factor required, or trivially circumventable factor, against any surface that returns claims data, member PHI, prescriber records, or adjudication-engine admin controls. Includes JWT `alg:none` accepted, signature verification skipped, or RS256-verified-as-HS256 key-confusion on pharmacist-portal or prescriber-portal tokens; SAML XML Signature Wrapping (XSW) on pharmacist/prescriber SSO yielding subject substitution into another NPI's session; password-reset bypass via predictable reset tokens, unauthenticated reset endpoints, or reset flows that do not require the prior credential or a possession factor; MFA enrollment endpoints reachable without re-authentication so an attacker with a stolen single-factor session enrolls their own second factor; and session fixation that survives the PHI-access transition so a pre-authentication session ID remains valid after the member, pharmacist, or call-center agent logs in. Maps to T1078 (Valid Accounts) for credential-and-session reuse paths and T1556 (Modify Authentication Process) for the JWT, SAML XSW, and reset-flow primitives that subvert the verification logic itself; D3FEND counter is D3-MFA (Multi-factor Authentication) on the PHI and admin surfaces; reset-flow and MFA-enrollment endpoints additionally require step-up authentication (NIST 800-53r5 IA-2 reauthentication anchor below). NIST 800-53r5 anchor: IA family — IA-2 (Identification and Authentication of Organizational Users) including IA-2(1) and IA-2(2) for MFA, IA-5 (Authenticator Management), IA-8 (Identification and Authentication of Non-Organizational Users) for member and prescriber portals — plus AC-7 (Unsuccessful Logon Attempts) and AC-12 (Session Termination). NIST SP 800-63B anchor: PHI and admin surfaces should be evaluated at AAL2 minimum, with AAL3 (hardware-bound, phishing-resistant authenticator with verifier-impersonation resistance) for adjudication-engine admin and any surface returning bulk PHI.
- **Audit trail loss covering PHI access** — renders breach detection and notification obligations un-meetable; regulatory non-compliance independent of breach occurrence. Includes silent log disable, retention shortened below the HIPAA 6-year floor (45 CFR §164.316(b)(2)(i)), or log-shipping pipeline interrupted without separately-attested record on a forensically isolated channel. Maps to T1070 (Indicator Removal), with T1070.002 (Clear Linux or Mac System Logs) where the underlying audit substrate is OS-level; D3FEND counter is immutable substrate (S3 Object Lock Compliance Mode, Azure Blob immutable storage with legal hold, HSM-anchored hash-chained store) plus D3-LFAM (Local File Access Mediation) on the log substrate. NIST 800-53r5 anchor: AU family — AU-9 (Protection of Audit Information), AU-11 (Audit Record Retention), AU-12 (Audit Record Generation).
- **Total adjudication outage exceeding contractual SLA** — sustained inability to adjudicate claims affecting all plan sponsors simultaneously.
- **Loss of CMS Part D submission integrity / PDE corruption** — PDE (Prescription Drug Event) data submission failures or corruption that exposes the PBM to CMS enforcement action under 42 CFR §423.322, including payment-determination reopening, plan-payment recovery, and potential False Claims Act exposure (31 U.S.C. §3729) when a submission is knowingly false. Maps to T1565 (Data Manipulation), with T1565.002 (Transmitted Data Manipulation) for in-flight PDE tampering between the PBM and CMS and T1565.001 (Stored Data Manipulation) for at-rest corruption of the PDE staging or archive store; D3FEND counter is D3-MAN (Message Authentication) on signed PDE submission batches (per-batch signature verification at CMS ingest is the load-bearing control). NIST 800-53r5 anchor: SI family — SI-7 (Software, Firmware, and Information Integrity) including SI-7(6) for cryptographic protection — plus AU-10 (Non-repudiation) on the submission record and SC-8 (Transmission Confidentiality and Integrity) on the outbound channel to CMS.

## High

Any of the following:

- **PHI exposure beyond minimum-necessary internal audience** — violates 45 CFR §164.502(b). Includes overbroad role assignments, missing field-level controls on PHI elements, or admin tooling that exposes more PHI than the operator's role requires. Maps to T1213 (Data from Information Repositories) for over-broad authenticated reads against PHI stores; NIST 800-53r5 anchor AC-6 (Least Privilege) and AC-4 (Information Flow Enforcement).
- **Claim adjudication errors bounded to a subset** — single plan sponsor, single drug class, single channel (mail order vs retail), or single member population. Erroneous adjudication but blast radius is contained.
- **Authentication weakness short of bypass** — MFA bypass requiring adjacent factor, credential reuse window exceeding policy, session lifetime exceeding policy, weak password requirements on a PHI surface. Maps to T1621 (Multi-Factor Authentication Request Generation) for MFA-fatigue/push-bombing paths and T1078 (Valid Accounts) for credential-reuse paths; NIST 800-53r5 anchor IA-2(1) and IA-2(2) for MFA, IA-5 (Authenticator Management).
- **Partial audit gap on PHI-adjacent surfaces** — admin actions logged but lacking actor attribution, audit logs shipped without integrity protection, audit retention shorter than 6 years (HIPAA minimum). Maps to T1070 (Indicator Removal) where retention or integrity gaps would let an attacker erase or alter their trace; NIST 800-53r5 anchor AU-9 (Protection of Audit Information), AU-11 (Audit Record Retention), AU-12 (Audit Record Generation).
- **Adjudication degradation with manual workaround required** — system functional but requires operator intervention to complete claims, sustained.
- **CMS Part D compliance gap not affecting member dispensing** — formulary update lag, prior authorization workflow gap, transition fill logic gap, that does not currently affect a dispensing decision but is required by CMS-4201-F or equivalent.
- **URAC accreditation-relevant gap** — control absence in a domain URAC evaluates, where the absence would be findable in an accreditation audit.

## Medium

Any of the following:

- **Defense-in-depth gap where a compensating control exists** but is the only barrier — single point of control failure. Encryption at rest absent because TLS terminates inside the trust boundary is the canonical example.
- **Recoverable adjudication delay within SLA** — performance regression that the SLO budget absorbs but consumes headroom.
- **Logging gap on non-PHI surfaces** — operational visibility loss that does not affect breach detection.
- **Hardening weakness exploitable only after adjacent compromise** — requires the attacker to already have a foothold elsewhere. Useful to fix; not catastrophic if deferred.
- **Configuration drift detection gap** on systems where compensating attestation exists.
- **Documentation gap with security-relevant content missing** — architecture decision records, runbooks, or threat models absent in ways that impair operations or future review.

## Low

Any of the following:

- **Hygiene issue with no realistic exploit path** — deprecated cipher with no client support, redundant control with overlapping coverage, configuration verbosity.
- **Documentation deficiency** — non-security-critical content missing, formatting inconsistency, naming convention drift.
- **Defense-in-depth gap fully compensated** by upstream controls — useful to know but architecturally non-urgent.
- **Configuration drift on non-critical path** — dev environment, ephemeral test infrastructure.

## Informational

Observations that do not rise to remediation but are worth surfacing for the architecture record. Used sparingly. Examples: notable architectural choices with security implications worth documenting, parity gaps with industry peers that are not actually risks.

---

## Clinical patient-harm axis

The PBM severity ladder above scores findings on the data-and-regulatory axis (PHI confidentiality, PDE integrity, audit defensibility). The second axis below scores findings on the clinical patient-harm dimension. Assign the severity that is the MAX of the two axes.

### Critical (clinical patient-harm)

- **Wrong drug dispensed at the pharmacy counter** — finding makes it plausible that the PBM's pricing or adjudication response produced a substitution that the prescriber did not approve and that the patient would not have received but for the PBM error. Maps to T1565.002 (Transmitted Data Manipulation) when the corruption is in-flight; T1565.001 when in the formulary store.
- **Missed drug-utilization-review alert leading to harmful drug interaction** — finding makes it plausible that the DUR engine suppressed, did not raise, or routed away a clinically-significant interaction alert (drug-drug, drug-disease, drug-allergy, drug-age, therapeutic duplication). Includes DUR-rule configuration that excludes a class of patient (e.g., pediatric, geriatric, pregnant) from alerts they should receive.
- **Missed prior-authorization on safety-gated drug** — finding makes it plausible that the PA-criteria engine approved or auto-routed-around a request that the PA criteria were explicitly designed to gate for clinical safety reasons (REMS-enrolled drugs, controlled substances above MED thresholds, specialty oncology agents with monitoring requirements). Maps to T1565.001 (Stored Data Manipulation) against the PA-criteria configuration store.
- **Formulary bypass exposing patient to clinically harmful substitution** — finding makes it plausible that a formulary-tier reassignment, generic-substitution rule, or step-therapy-bypass produced a dispense decision that the formulary committee explicitly excluded for clinical-safety reasons. Maps to T1565.001 (Stored Data Manipulation) against the formulary configuration store.
- **Dose calculation error** — finding makes it plausible that the days-supply calculation, the weight-based-dosing logic, or the pediatric/geriatric dosing rule produced an unsafe dose. Particularly load-bearing for opioids (MED calculation), insulin, anticoagulants, and pediatric formulations. Maps to T1565.002 (Transmitted Data Manipulation) on the adjudication response when the dose is computed in-flight; NIST 800-53r5 anchor SI-10 (Information Input Validation) on dose-calculation inputs.

### High (clinical patient-harm)

- **DUR-rule or PA-criteria edit without dual approval** — the editing surface for clinical-decision logic accepts single-operator changes; finding scores High because it creates the capability for any of the Critical-tier clinical-harm scenarios above without an enforcement gate.
- **Formulary tier change applying retroactively** — finding makes it plausible that a tier reassignment alters claims that were already adjudicated, retroactively shifting cost or coverage in ways that destabilize patient adherence or trigger member-confusion-driven non-compliance.
- **DUR alert silently suppressed by operator without attestation** — operator UI permits DUR-alert suppression without recording a clinical-justification field, supervisor attestation, or pharmacist review. Creates a hidden patient-harm capability.
- **PA appeal-decision routing failure** — Medicare Part D requires redetermination decisions within tight timelines (42 CFR §423.590 — 7 calendar days standard, 72 hours expedited); finding makes it plausible that the appeal-routing logic produces missed timelines that convert to coverage denials by default.

### Medium (clinical patient-harm)

- **DUR alert displayed but easily dismissed** — clinically-significant alerts can be dismissed with a single click and no justification; clinical-decision quality depends on operator habit rather than enforcement. Worth raising; not catastrophic.
- **Formulary-update lag affecting non-safety drugs** — formulary changes propagate with a delay that affects copay or coverage but does not affect drug safety.
- **PA criteria documentation drift** — the configured criteria differ from the published formulary documentation in ways that affect member expectations but not safety.

### Low (clinical patient-harm)

- **Clinical-context surface with no realistic harm path** — UI labels for clinical fields use unclear or inconsistent language; no error in computation or routing.
- **Documentation gap on a clinical-decision surface** — operator-facing help text incomplete; clinical logic itself is correct.

---

## Severity calibration discipline

- **Cite the rubric clause in `detail`.** "This is high severity because it falls under 'PHI exposure beyond minimum-necessary internal audience' per the impact-to-PBM rubric, specifically [reasoning]."
- **Do not average across multiple impacts.** A finding that has critical PHI exposure AND medium operational risk is critical.
- **Do not inflate to signal importance.** The synthesizer escalates and reconciles severity disagreements between agents; over-claiming on one agent degrades the cross-agent reconciliation signal.
- **When in doubt, drop one level.** A high-confidence medium is more useful than a low-confidence high.
- **Asymmetric escalation rule.** When a finding sits between two tiers, escalate to the higher tier only if at least one of the following holds: (a) regulator action is plausible given the cited rubric clause — HHS OCR enforcement under 45 CFR §164.408, CMS Part D sponsor compliance action, or state pharmacy-board action against the dispensing channel; (a2) an accreditation-relevant adverse finding is plausible — URAC PBM accreditation, HITRUST CSF certification (the dominant healthcare accreditation framework for which PBMs are commonly certified), or SOC 2 Type II for the service-organization controls relied upon by plan-sponsor customers; (b) the finding affects a clinical-decision pathway — Drug Utilization Review (DUR), formulary determination, prior authorization, or dispensing instruction generation; (c) the blast radius covers more than one plan sponsor, or more than 500 members in a single sponsor. If none of these holds, drop to the lower tier. The default direction at the boundary is down, not up.
- **Capability-vs-exploited equivalence rule.** The rubric scores realistic attack capability, not whether exploitation has been observed. An UNDISCLOSED adjudication-corruption capability — a path through which an attacker could cause wrong-drug-dispensed, missed DUR, or formulary bypass — and an OBSERVED wrong-drug-dispensed event are both Critical when the latent capability would meet the Critical clause if exercised. The rubric basis is the HIPAA Security Rule risk-management standard at 45 CFR §164.308(a)(1)(ii)(B), which obligates the covered entity to address reasonably anticipated risks — not only realized harms — to PHI confidentiality, integrity, and availability.
