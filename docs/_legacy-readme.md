# APD Gauntlet

Multi-agent security architecture review built on the APD framework — **A**ssure Trustworthiness, **P**rovide Scalability, **D**emonstrate Auditability. Nine specialist agents, one intake agent, one orchestrator, one synthesizer. Runs in Claude Code against a tech plan plus optional supplementary artifacts. Produces an advisory report with confirmed capabilities, findings, contradictions, and coverage matrices.

This is **advisory input to architecture review**, not a gate. The output is structured to help an architect make better decisions, not to replace one.

---

## What the gauntlet does

For a given tech plan and any supplementary artifacts (PRD, code, IaC, diagrams, threat models, ADRs), it produces two output streams:

- **Findings** — gaps, risks, uncertainties, and items blocked on missing evidence
- **Confirmed capabilities** — security properties the design or implementation positively demonstrates, with explicit scope and caveats

Both streams are organized along the nine APD goals:

```
Trustworthiness   →  Confidentiality · Integrity · Availability
Scalability       →  Distributed · Resilient · Ephemeral
Auditability      →  Authenticity · Non-Repudiation · Immutability
```

Every finding and capability carries NIST 800-53r5 control mappings. Findings carry MITRE ATT&CK technique mappings when the agent has high confidence; capabilities carry ATT&CK mitigation mappings. Severity is calibrated against an explicit impact-to-PBM rubric, not generic CVSS.

The synthesizer dedups across lenses, surfaces contradictions between findings and capabilities, and produces three rollups: a NIST 800-53r5 coverage matrix, an ATT&CK exposure summary, and an APD-by-component coverage grid.

---

## Why three tiers, why nine goals

The tier ordering is load-bearing:

- **Trustworthiness is foundational.** A system that cannot be trusted with data cannot meaningfully scale or be audited.
- **Scalability is operational.** A trustworthy system that cannot operate under failure or scale is fragile in production.
- **Auditability is accountability.** A trustworthy, scalable system that cannot prove what it did is uninspectable.

Within each tier, the three goals decompose the tier into distinct lenses. The lens-versus-scope distinction is the most important analytical discipline: every concern belongs to exactly one goal's lens, even when adjacent goals are implicated. The framework's boundary calls (in `.claude/skills/apd-framework/SKILL.md`) resolve ambiguous cases.

---

## Package layout

```
apd-gauntlet/
├── README.md                                # this file
├── .claude/
│   ├── agents/
│   │   ├── apd-orchestrator.md              # phases the run, dispatches specialists
│   │   ├── apd-intake.md                    # builds the artifact-aware context brief
│   │   ├── apd-confidentiality.md           # tier 1
│   │   ├── apd-integrity.md                 # tier 1
│   │   ├── apd-availability.md              # tier 1
│   │   ├── apd-distributed.md               # tier 2
│   │   ├── apd-resilient.md                 # tier 2
│   │   ├── apd-ephemeral.md                 # tier 2
│   │   ├── apd-authenticity.md              # tier 3
│   │   ├── apd-non-repudiation.md           # tier 3
│   │   ├── apd-immutability.md              # tier 3
│   │   └── apd-synthesizer.md               # dedups, reconciles, produces advisory report
│   └── skills/
│       ├── apd-framework/SKILL.md           # canonical framework reference
│       ├── apd-finding-schema/SKILL.md      # YAML contracts for findings and capabilities
│       ├── apd-evidence-discipline/SKILL.md # five rules + impact-to-PBM severity rubric
│       └── apd-control-mappings/SKILL.md    # NIST 800-53r5 and MITRE ATT&CK mapping guidance
└── templates/
    ├── finding.template.yaml
    ├── capability.template.yaml
    ├── context-brief.template.md
    └── advisory-report.template.md
```

---

## Running the gauntlet

### Prerequisites

- Claude Code with subagent and skill support
- A tech plan or design document
- Optional: PRD, source code, IaC, architecture diagrams, threat model, ADRs, runbooks, test reports

### Step 1: Set up the run directory

```
runs/<run-id>/
└── inputs/
    ├── tech_plan.md           # required
    ├── prd.md                 # optional
    ├── claim-events.proto     # optional
    ├── threat-model-v3.md     # optional
    └── ...
```

Use any `run-id` that makes sense — common pattern: `apd-YYYYMMDD-<short-slug>` (e.g. `apd-20260519-claim-event-bus`).

### Step 2: Invoke the orchestrator

In Claude Code, invoke the `apd-orchestrator` agent with the path to the run directory. The orchestrator coordinates the rest.

```
> Run apd-orchestrator on runs/apd-20260519-claim-event-bus/
```

### Step 3: Wait for output

The orchestrator produces the directory structure:

```
runs/<run-id>/
├── inputs/                    # your artifacts
├── 00-context/
│   └── context-brief.md       # intake output
├── 10-trustworthiness/
│   ├── confidentiality.findings.yaml      confidentiality.capabilities.yaml
│   ├── integrity.findings.yaml            integrity.capabilities.yaml
│   └── availability.findings.yaml         availability.capabilities.yaml
├── 20-scalability/
│   ├── distributed.findings.yaml          distributed.capabilities.yaml
│   ├── resilient.findings.yaml            resilient.capabilities.yaml
│   └── ephemeral.findings.yaml            ephemeral.capabilities.yaml
├── 30-auditability/
│   ├── authenticity.findings.yaml         authenticity.capabilities.yaml
│   ├── non-repudiation.findings.yaml      non-repudiation.capabilities.yaml
│   └── immutability.findings.yaml         immutability.capabilities.yaml
└── 40-synthesis/
    ├── deduped-findings.yaml              deduped-capabilities.yaml
    ├── contradictions.yaml                severity-disagreements.yaml
    ├── nist-coverage.yaml                 attack-exposure.yaml
    ├── apd-coverage-matrix.yaml           rejected-records.yaml
    └── advisory-report.md                 # the deliverable
```

The advisory report is your starting point. The YAML files are the canonical data; the report is composed from them.

---

## Run lifecycle

1. **Intake.** Inventories artifacts, builds a capability and trust-boundary surface, enumerates PHI/PII data elements, identifies evidence gaps, and produces a per-goal relevance table. Output: `00-context/context-brief.md`.

2. **Tier 1 (parallel).** Confidentiality, Integrity, and Availability specialists read the inputs and the context brief, each through their lens. Output: six YAML files in `10-trustworthiness/`.

3. **Tier 2 (parallel).** Distributed, Resilient, and Ephemeral specialists read inputs, brief, and tier 1 outputs. They cross-reference tier 1 findings rather than re-litigating them. Output: six YAML files in `20-scalability/`.

4. **Tier 3 (parallel).** Authenticity, Non-Repudiation, and Immutability specialists read inputs, brief, and tier 1+2 outputs. Same cross-reference discipline. Output: six YAML files in `30-auditability/`.

5. **Synthesis.** Synthesizer validates structurally, dedups via cluster-and-merge/link/separate, checks finding-versus-capability contradictions, reconciles severity disagreements, rolls up NIST and ATT&CK coverage, builds the APD coverage matrix, and composes the advisory report. Output: eight files in `40-synthesis/`.

6. **Closeout.** Orchestrator reports run summary to the user.

---

## Discipline anchors

Three rules that govern every specialist's output. Internalize before running.

**Evidence-pointer required.** Every finding and capability cites at least one artifact with a specific locator and a verbatim excerpt under 25 words. "The tech plan describes encryption" is not evidence. "§5.3 paragraph 2: 'AES-256 at rest with broker-managed keys'" is evidence.

**Block on ambiguity.** If artifacts are silent or contradictory, emit `disposition: blocked` with prerequisite evidence named. Do not infer a property is absent because the doc doesn't mention it. Do not infer it's present because the doc gestures at it. The synthesizer collects blocked items into a structured request for more artifacts.

**Stay in your lens.** If you notice something in another goal's territory, populate `related_concerns`. Do not write findings outside your lens. The synthesizer relies on lens discipline to distinguish "same root cause, two lenses" (merge candidate) from "two concerns sharing evidence" (link candidate).

---

## Severity rubric — impact-to-PBM

Severity is calibrated against PBM-specific impact, not generic CVSS. Brief version below; full version in `.claude/skills/apd-evidence-discipline/SKILL.md`.

- **Critical.** PHI exfiltration >500 members (HIPAA breach notification threshold); claim adjudication corruption affecting therapeutic decisions; authentication bypass to PHI; audit trail loss covering PHI access; total adjudication outage exceeding SLA; CMS Part D submission integrity loss.
- **High.** PHI exposure beyond minimum-necessary; bounded adjudication errors (single sponsor / drug class / channel); authentication weakness short of bypass; partial audit gap on PHI surfaces; CMS-relevant compliance gap not affecting dispensing; URAC-relevant gap.
- **Medium.** Defense-in-depth gap with single compensating control; recoverable adjudication delay within SLA; logging gap on non-PHI surfaces; exploitable-only-after-adjacent-compromise.
- **Low.** Hygiene without realistic exploit path; documentation gap; defense-in-depth fully compensated.
- **Informational.** Architectural observation worth recording but not actionable.

Severities must cite their matching rubric clause in the finding's `detail`. The synthesizer reconciles disagreements between agents — when two agents merge a finding with different severities, the higher severity wins and the disagreement is recorded in `severity-disagreements.yaml`.

---

## Maturity ladder for capabilities

- **`designed`** — intent stated in tech plan or design doc. Floor for tech plan reviews.
- **`implemented`** — runtime evidence required (config, IaC, code, screenshot).
- **`tested`** — test artifact required (test report, audit result, control test).
- **`operationalized`** — operational artifact required (runbook, monitoring dashboard, alert).

The validator rejects capabilities at maturity ≥ `implemented` without at least one non-tech-plan evidence entry. For tech plan reviews specifically, expect most capabilities to land at `designed`. Higher maturity claims require additional artifacts.

---

## Scope hints

The orchestrator accepts optional scope hints at invocation:

- `Emphasize PHI exposure` — pass-through framing for the executive summary.
- `Skip Distributed` — omit a specialist; note the skip in the run summary.
- `Focus on the Kafka design` — pass component focus to every specialist.

Scope hints do not override the gauntlet's structural integrity. Skipping multiple specialists or restricting analysis to a single component degrades the advisory report; the orchestrator warns before proceeding.

---

## What the gauntlet does not do

- It does not gate deployment or production change.
- It does not produce remediation tickets or assign owners.
- It does not analyze runtime behavior — only artifacts presented at the time of run.
- It does not arbitrate disagreements among specialists; it surfaces them for human review.
- It does not retry blocked findings without additional artifacts. Closing blocked items requires another run.
- It does not replace threat modeling, penetration testing, or formal security review. It complements them by providing a structured architectural lens at design time.

---

## Extending the gauntlet

The four skills in `.claude/skills/` are the framework's load-bearing references. Modifying them affects every specialist:

- Adjusting the severity rubric → edit `apd-evidence-discipline/SKILL.md`.
- Adding a control framework crosswalk → edit `apd-control-mappings/SKILL.md`.
- Refining a goal's lens definition or boundary call → edit `apd-framework/SKILL.md`.
- Changing the finding or capability schema → edit `apd-finding-schema/SKILL.md` and update the templates.

Specialist agent files in `.claude/agents/` are lens-specific. To add a new analytical pattern for a goal, edit that goal's agent and add a new entry under "Common finding patterns" or "Common capability patterns."

The synthesizer's clustering and reconciliation logic is in `apd-synthesizer.md`. Changes to merge-vs-link discipline, contradiction handling, or report structure live there.
