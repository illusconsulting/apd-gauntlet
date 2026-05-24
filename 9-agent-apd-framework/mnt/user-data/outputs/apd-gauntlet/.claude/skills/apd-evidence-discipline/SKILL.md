---
name: apd-evidence-discipline
description: Cross-cutting analytical discipline for APD gauntlet specialist agents — evidence-pointer requirement, block-on-ambiguity default, lens discipline, reproduce-before-recommend rule, and the impact-to-PBM severity rubric. Use this whenever you are reasoning about whether a concern rises to a finding, what severity to assign, when to mark a finding as blocked rather than speculating, and how to keep your analysis inside your assigned lens. Every specialist agent must internalize these rules before emitting any finding or capability.
---

# Evidence Discipline

The gauntlet produces advisory output that engineering and architecture teams will rely on. The discipline rules below exist to keep that output trustworthy. Agents that drift from these rules produce findings that are dismissed, debated, or — worse — acted on incorrectly.

## The five rules

### 1. Evidence-pointer required

Every finding and every capability cites at least one artifact, with a specific locator and a verbatim excerpt under 25 words.

- "The tech plan describes the encryption design" is not evidence. "§5.3 'Data at Rest', paragraph 2: 'AES-256 at rest with broker-managed keys'" is evidence.
- Locator specificity required: section heading + paragraph, line range, sheet/cell, slide number. Page-only locators are accepted for PDFs without internal structure but discouraged.
- If no specific locator can be produced, the finding is either `blocked` with `prerequisite_evidence` naming what is needed, or it is not a finding at all.

### 2. Block on ambiguity

If the available artifacts are silent on a topic in your lens, or contradict each other, emit `disposition: blocked` with populated `prerequisite_evidence`. Do not infer the property is absent. Do not infer the property is present. Do not write a `low`-confidence finding to "flag for review" — that is what `blocked` is for.

The default disposition under any ambiguity is `blocked`. This rule exists because the cost of a wrongly-asserted finding (engineering pushback, lost gauntlet credibility) is higher than the cost of an explicit unknown. The synthesizer aggregates `blocked` items into a "what we need to complete this assessment" section, which is itself a valuable advisory output.

Acceptable phrasing for `prerequisite_evidence` items: "DEK rotation policy", "Kafka consumer group topology", "Member portal session timeout configuration". Each entry names a specific document or property, not a general topic.

### 3. Stay in your lens

If you notice something in another APD goal's territory, populate `related_concerns` with the goal that owns it. Do not write the finding yourself. The synthesizer relies on lens discipline to distinguish "same root cause, two lenses" (merge) from "two concerns, shared evidence" (link).

The `apd-framework` skill defines the boundary calls between adjacent goals. Consult it when in doubt. The most common drift patterns to avoid:

- Confidentiality writing about identity verification (belongs to Authenticity)
- Integrity writing about historical alteration (belongs to Immutability)
- Availability writing about topology (belongs to Distributed)
- Non-Repudiation writing about record alteration (belongs to Immutability)
- Authenticity writing about credential lifetime (belongs to Ephemeral)

When you catch yourself starting one of these, stop, add the goal to `related_concerns`, and constrain your finding to your own lens.

### 4. Reproduce before you recommend

A recommendation must cite the specific architectural choice it is replacing or augmenting. Generic best-practice prose is rejected.

- Not acceptable: "Use envelope encryption for sensitive data."
- Acceptable: "Replace the broker-level encryption described in §4.2 with field-level envelope encryption applied before producer serialization, using DEKs issued by the existing KMS hierarchy described in §3.1."

The reproduce-before-recommend rule does two things: it forces the agent to confirm it has actually read the design (rather than pattern-matching to generic advice), and it produces remediation guidance the engineer can act on without further interpretation.

### 5. Recommendation posture is calibrated

- `required` — without this, the system fails a compliance obligation (HIPAA, CMS, URAC, SOC 2 commitment) or carries unacceptable PBM risk under the severity rubric below. Reserve for severity ≥ high.
- `recommended` — material risk reduction with reasonable engineering cost. Used for medium-severity gaps and for high-severity gaps with reasonable compensating controls.
- `consider` — defense-in-depth or hardening that the architect should weigh against effort. Used for low and informational findings.

Do not inflate posture to signal urgency. The synthesizer reads posture as a load-bearing field for the executive summary.

---

## Severity rubric — impact-to-PBM

Severity is calibrated against impact-to-PBM, not against generic CVSS. The agent cites the matching clause in the finding's `detail` field. Cited examples in each tier are illustrative, not exhaustive.

### Critical

Any of the following:

- **PHI exfiltration capability affecting >500 members** in a single realistic attack scenario. Triggers HIPAA breach notification per 45 CFR §164.408 (federal, state, and media notification). The 500-member threshold is the legal pivot point for required public disclosure.
- **Claim adjudication corruption affecting therapeutic decisions** — wrong drug dispensed, wrong dose, missed Drug Utilization Review (DUR) alert, formulary bypass that exposes patients to harmful drug interactions, missed prior authorization on safety-gated drugs. Direct patient harm risk.
- **Authentication bypass to PHI surfaces or admin functions** — no factor required, or trivially circumventable factor. Includes session fixation that produces persistent unauthorized access.
- **Audit trail loss covering PHI access** — renders breach detection and notification obligations un-meetable, regulatory non-compliance independent of breach occurrence.
- **Total adjudication outage exceeding contractual SLA** — sustained inability to adjudicate claims affecting all plan sponsors simultaneously.
- **Loss of CMS Part D submission integrity** — PDE (Prescription Drug Event) data submission failures or corruption that exposes the PBM to CMS enforcement action.

### High

Any of the following:

- **PHI exposure beyond minimum-necessary internal audience** — violates 45 CFR §164.502(b). Includes overbroad role assignments, missing field-level controls on PHI elements, or admin tooling that exposes more PHI than the operator's role requires.
- **Claim adjudication errors bounded to a subset** — single plan sponsor, single drug class, single channel (mail order vs retail), or single member population. Erroneous adjudication but blast radius is contained.
- **Authentication weakness short of bypass** — MFA bypass requiring adjacent factor, credential reuse window exceeding policy, session lifetime exceeding policy, weak password requirements on a PHI surface.
- **Partial audit gap on PHI-adjacent surfaces** — admin actions logged but lacking actor attribution, audit logs shipped without integrity protection, audit retention shorter than 6 years (HIPAA minimum).
- **Adjudication degradation with manual workaround required** — system functional but requires operator intervention to complete claims, sustained.
- **CMS Part D compliance gap not affecting member dispensing** — formulary update lag, prior authorization workflow gap, transition fill logic gap, that does not currently affect a dispensing decision but is required by CMS-4201-F or equivalent.
- **URAC accreditation-relevant gap** — control absence in a domain URAC evaluates, where the absence would be findable in an accreditation audit.

### Medium

Any of the following:

- **Defense-in-depth gap where a compensating control exists** but is the only barrier — single point of control failure. Encryption at rest absent because TLS terminates inside the trust boundary is the canonical example.
- **Recoverable adjudication delay within SLA** — performance regression that the SLO budget absorbs but consumes headroom.
- **Logging gap on non-PHI surfaces** — operational visibility loss that does not affect breach detection.
- **Hardening weakness exploitable only after adjacent compromise** — requires the attacker to already have a foothold elsewhere. Useful to fix; not catastrophic if deferred.
- **Configuration drift detection gap** on systems where compensating attestation exists.
- **Documentation gap with security-relevant content missing** — architecture decision records, runbooks, or threat models absent in ways that impair operations or future review.

### Low

Any of the following:

- **Hygiene issue with no realistic exploit path** — deprecated cipher with no client support, redundant control with overlapping coverage, configuration verbosity.
- **Documentation deficiency** — non-security-critical content missing, formatting inconsistency, naming convention drift.
- **Defense-in-depth gap fully compensated** by upstream controls — useful to know but architecturally non-urgent.
- **Configuration drift on non-critical path** — dev environment, ephemeral test infrastructure.

### Informational

Observations that do not rise to remediation but are worth surfacing for the architecture record. Used sparingly. Examples: notable architectural choices with security implications worth documenting, parity gaps with industry peers that are not actually risks.

---

## Severity calibration discipline

- **Cite the rubric clause in `detail`.** "This is high severity because it falls under 'PHI exposure beyond minimum-necessary internal audience' per the impact-to-PBM rubric, specifically [reasoning]."
- **Do not average across multiple impacts.** A finding that has critical PHI exposure AND medium operational risk is critical.
- **Do not inflate to signal importance.** The synthesizer escalates and reconciles severity disagreements between agents; over-claiming on one agent degrades the cross-agent reconciliation signal.
- **When in doubt, drop one level.** A high-confidence medium is more useful than a low-confidence high.

---

## Maturity discipline (for capabilities)

The capability schema's maturity ladder is governed by the same evidence discipline.

- **`designed`** — tech plan or design doc states the intent. Acceptable evidence: tech plan section, ADR, design doc, threat model.
- **`implemented`** — runtime evidence required. Acceptable evidence: configuration file, IaC resource, code reference, runtime screenshot, deployment manifest.
- **`tested`** — test artifact required. Acceptable evidence: test report, test code reference, audit artifact, control test result.
- **`operationalized`** — operational artifact required. Acceptable evidence: runbook, monitoring dashboard, alert definition, on-call playbook.

For a tech plan review where supplementary artifacts are variable, expect the floor of `designed` to be most common. Do not claim higher maturity than the available artifacts support. The validator (per `apd-finding-schema` skill) enforces this constraint by requiring at least one non-tech-plan evidence entry for `maturity ≥ implemented`.

---

## Self-check before emitting

Before emitting any finding or capability, run this checklist:

1. **Lens.** Is this concern inside my assigned APD goal? If not, add to `related_concerns` instead.
2. **Evidence.** Do I have a specific locator + verbatim excerpt? If not, either find one or mark `blocked`.
3. **Block test.** Am I inferring a property is absent because the doc is silent? If yes, mark `blocked` with prerequisite evidence.
4. **Severity.** Does my chosen severity match a specific clause in the rubric? Can I cite that clause in `detail`?
5. **Recommendation.** Does my recommendation name the specific architectural choice it replaces? If not, rewrite it.
6. **Posture.** Is `required` reserved for compliance-forcing or PBM-unacceptable? If not, downgrade to `recommended`.
7. **Maturity.** If this is a capability with `maturity ≥ implemented`, do I have non-tech-plan evidence? If not, downgrade to `designed`.
8. **Title.** Does the title name a specific component AND a specific concern? If not, rewrite.

Findings or capabilities that fail this self-check are rejected by the synthesizer's validator and surfaced back to the agent for revision.
