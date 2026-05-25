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

- `required` — without this, the system fails a compliance obligation (HIPAA, CMS, URAC, SOC 2 commitment) or carries unacceptable risk per the active domain's severity rubric. Reserve for severity ≥ high.
- `recommended` — material risk reduction with reasonable engineering cost. Used for medium-severity gaps and for high-severity gaps with reasonable compensating controls.
- `consider` — defense-in-depth or hardening that the architect should weigh against effort. Used for low and informational findings.

Do not inflate posture to signal urgency. The synthesizer reads posture as a load-bearing field for the executive summary.

---

## Severity rubric (domain-loaded)

The severity rubric is domain-specific and lives in the active domain pack at `domains/<active>/severity-rubric.md`. It is bundled into the `apd-domain` skill at run time by `apd-gauntlet build-domain-skill`.

You MUST cite the matching rubric clause in the finding's `detail` field. The synthesizer relies on cited clauses to reconcile severity disagreements between agents.

If no domain pack is loaded for a run, agents emit a single high-severity finding "no severity rubric in scope" and halt; this is intentional — the gauntlet has no fallback default.

---

## Severity calibration discipline

- **Cite the rubric clause in `detail`.** "This is high severity because it falls under [clause name] per the active domain's severity rubric, specifically [reasoning]."
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
4. **Severity.** Does my chosen severity match a specific clause in the active domain's severity rubric, and can I cite that clause in `detail`?
5. **Recommendation.** Does my recommendation name the specific architectural choice it replaces? If not, rewrite it.
6. **Posture.** Is `required` reserved for compliance-forcing or PBM-unacceptable? If not, downgrade to `recommended`.
7. **Maturity.** If this is a capability with `maturity ≥ implemented`, do I have non-tech-plan evidence? If not, downgrade to `designed`.
8. **Title.** Does the title name a specific component AND a specific concern? If not, rewrite.

Findings or capabilities that fail this self-check are rejected by the synthesizer's validator and surfaced back to the agent for revision.
