# PBM Severity Rubric (impact-to-PBM)

Calibrated against impact-to-PBM, not against generic CVSS. The specialist agent cites the matching clause in finding `detail` fields. Cited examples in each tier are illustrative, not exhaustive.

## Critical

Any of the following:

- **PHI exfiltration capability affecting >500 members** in a single realistic attack scenario. Triggers HIPAA breach notification per 45 CFR §164.408 (federal, state, and media notification). The 500-member threshold is the legal pivot point for required public disclosure.
- **Claim adjudication corruption affecting therapeutic decisions** — wrong drug dispensed, wrong dose, missed Drug Utilization Review (DUR) alert, formulary bypass that exposes patients to harmful drug interactions, missed prior authorization on safety-gated drugs. Direct patient harm risk.
- **Authentication bypass to PHI surfaces or admin functions** — no factor required, or trivially circumventable factor, against any surface that returns claims data, member PHI, prescriber records, or adjudication-engine admin controls. Includes JWT `alg:none` accepted, signature verification skipped, or RS256-verified-as-HS256 key-confusion on pharmacist-portal or prescriber-portal tokens; SAML XML Signature Wrapping (XSW) on pharmacist/prescriber SSO yielding subject substitution into another NPI's session; password-reset bypass via predictable reset tokens, unauthenticated reset endpoints, or reset flows that do not require the prior credential or a possession factor; MFA enrollment endpoints reachable without re-authentication so an attacker with a stolen single-factor session enrolls their own second factor; and session fixation that survives the PHI-access transition so a pre-authentication session ID remains valid after the member, pharmacist, or call-center agent logs in.
- **Audit trail loss covering PHI access** — renders breach detection and notification obligations un-meetable, regulatory non-compliance independent of breach occurrence.
- **Total adjudication outage exceeding contractual SLA** — sustained inability to adjudicate claims affecting all plan sponsors simultaneously.
- **Loss of CMS Part D submission integrity** — PDE (Prescription Drug Event) data submission failures or corruption that exposes the PBM to CMS enforcement action.

## High

Any of the following:

- **PHI exposure beyond minimum-necessary internal audience** — violates 45 CFR §164.502(b). Includes overbroad role assignments, missing field-level controls on PHI elements, or admin tooling that exposes more PHI than the operator's role requires.
- **Claim adjudication errors bounded to a subset** — single plan sponsor, single drug class, single channel (mail order vs retail), or single member population. Erroneous adjudication but blast radius is contained.
- **Authentication weakness short of bypass** — MFA bypass requiring adjacent factor, credential reuse window exceeding policy, session lifetime exceeding policy, weak password requirements on a PHI surface.
- **Partial audit gap on PHI-adjacent surfaces** — admin actions logged but lacking actor attribution, audit logs shipped without integrity protection, audit retention shorter than 6 years (HIPAA minimum).
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

## Severity calibration discipline

- **Cite the rubric clause in `detail`.** "This is high severity because it falls under 'PHI exposure beyond minimum-necessary internal audience' per the impact-to-PBM rubric, specifically [reasoning]."
- **Do not average across multiple impacts.** A finding that has critical PHI exposure AND medium operational risk is critical.
- **Do not inflate to signal importance.** The synthesizer escalates and reconciles severity disagreements between agents; over-claiming on one agent degrades the cross-agent reconciliation signal.
- **When in doubt, drop one level.** A high-confidence medium is more useful than a low-confidence high.
- **Asymmetric escalation rule.** When a finding sits between two tiers, escalate to the higher tier only if at least one of the following holds: (a) regulator action is plausible given the cited rubric clause — HHS OCR enforcement under 45 CFR §164.408, CMS Part D sponsor compliance action, or state pharmacy-board action against the dispensing channel; (b) the finding affects a clinical-decision pathway — Drug Utilization Review (DUR), formulary determination, prior authorization, or dispensing instruction generation; (c) the blast radius covers more than one plan sponsor, or more than 500 members in a single sponsor. If none of these holds, drop to the lower tier. The default direction at the boundary is down, not up.
- **Capability-vs-exploited equivalence rule.** The rubric scores realistic attack capability, not whether exploitation has been observed. An UNDISCLOSED adjudication-corruption capability — a path through which an attacker could cause wrong-drug-dispensed, missed DUR, or formulary bypass — and an OBSERVED wrong-drug-dispensed event are both Critical when the latent capability would meet the Critical clause if exercised. The rubric basis is the HIPAA Security Rule risk-management standard at 45 CFR §164.308(a)(1)(ii)(B), which obligates the covered entity to address reasonably anticipated risks — not only realized harms — to PHI confidentiality, integrity, and availability.
