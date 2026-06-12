---
name: apd-finding-schema
description: Canonical YAML schemas for APD gauntlet outputs — the `finding` record (gaps, risks, uncertainties, blocked-on-evidence) and the `capability` record (confirmed security capabilities with maturity). Use this whenever you are about to emit a finding or capability from a specialist agent, when the synthesizer dedups records, or when validating that an agent's output conforms to the contract. Includes validation rules, required-field semantics, ID conventions, and the lens_perspectives block used by the synthesizer to preserve merged content.
---

# APD Finding and Capability Schema

Every specialist agent emits two output streams:

- **Findings** — gaps, risks, uncertainties, blocked-on-evidence items
- **Capabilities** — confirmed security capabilities present in the design or implementation

Both streams use strict YAML schemas. Validation is enforced by the synthesizer; records that fail validation are rejected and surfaced to the agent for correction.

---

## Canonical contract

The authoritative contract for each record kind is the JSON Schema file:

- `schemas/finding.schema.json`
- `schemas/capability.schema.json`
- `schemas/contradiction.schema.json`
- `schemas/severity-disagreement.schema.json`
- `schemas/coverage-matrix.schema.json`
- `schemas/nist-coverage.schema.json`
- `schemas/attack-exposure.schema.json`
- `schemas/domain.schema.json`

This skill is the human-readable companion. When they disagree, the JSON Schema wins. Run `apd-gauntlet validate <run-dir>` to enforce.

---

## Output envelope (canonical)

Each output file uses the **singular** root key whose value is a **list of bare records**:

```yaml
finding:                      # singular — never the plural 'findings:'
  - agent: confidentiality    # NO id, NO schema_version — the assembler injects both
    # ... rest of the record, BARE (not wrapped) ...
  - agent: confidentiality
    # ... second record ...
```

Capabilities files use the singular `capability:` root key the same way.

**IDs are tooling-authored.** Do **not** emit `id` or `schema_version`.
`apd-gauntlet canonicalize` is the sole author: it injects `schema_version: 1`
and computes `id` deterministically (`<shortcode>-<sha8(title|first-evidence-locator)>`,
with a `-cap-` infix for capabilities) and rewrites `cross_references` to match.
Emitting an `id` yourself is ignored (overwritten) and now flagged by lint.

### Common mistakes (rejected by `validate`)

- **Plural root key** (`findings:` / `capabilities:`) — use the singular root.
- **Per-record wrapper** — do NOT wrap each record in its own `finding:` /
  `capability:` key. Records in the list are bare maps.
- **`context-brief.md` as evidence** — evidence `artifact` values must be **input
  artifacts** (e.g. `tech_plan.md`, a `.proto`, an IaC file), never the intake
  brief.
- **Over-length** — `title` ≤ 200 characters (the validator rejects longer);
  each evidence `excerpt` ≤ 25 whitespace-separated tokens. Write a tight title
  that names the component and concern; push any longer detail into `summary` /
  `detail`.
- **Unquoted YAML scalars** — QUOTE any scalar (`title`/`summary`/`locator`/
  `excerpt`/`detail` one-liners) that contains a colon-space `": "`, an em-dash,
  or a leading special char (`-`, `?`, `:`, `&`, `*`, `#`, `@`, `[`, `{`, `>`,
  `|`, `%`, `!`). An unquoted colon breaks YAML parsing AND aborts
  canonicalization.
- **Invented output paths** — write each record to the canonical tier path your
  contract specifies; do NOT nest new directories. Example: tmeval findings go to
  `40-threat-model/threat-model.findings.yaml`, NOT
  `20-findings/40-threat-model/...`.

> Note: the `finding:`/`capability:` example blocks elsewhere in this skill show a single record under the root key for brevity. The list form above is the canonical multi-record shape; both the single-record and list forms validate, but agents should emit the list form.

---

## Finding schema

```yaml
finding:
  schema_version: 1
  id: <agent-shortcode>-<sha8>    # (tooling-authored — do not emit)
  agent: confidentiality
  apd_tier: trustworthiness
  apd_goal: confidentiality

  disposition: gap                # gap | risk | uncertainty | blocked
  severity: high                  # critical | high | medium | low | informational
  confidence: medium              # high | medium | low

  title: "Short, specific, architectural — names the component and the concern"
  summary: "One sentence for the synthesizer rollup."
  detail: |
    Multi-paragraph technical analysis. Cite the specific architectural
    decision, the gap or risk it introduces, and the attack or failure
    scenario it enables. Reference the severity rubric clause that
    justifies the chosen severity.

  evidence:
    - artifact: tech_plan.md
      locator: "§4.2 'Event Bus Architecture', paragraph 3"
      excerpt: "Verbatim quote from the source, kept short."
    - artifact: claim-events.proto
      locator: "lines 18-34"
      excerpt: "..."

  prerequisite_evidence:          # required when disposition=blocked or confidence=low
    - "KMS key hierarchy / DEK rotation policy"
    - "Consumer-side decryption boundary documentation"

  control_mappings:
    nist_800_53r5:
      - "SC-8(1)"
      - "SC-13"
      - "AU-9(3)"
    mitre_attack:
      - technique: "T1530"
        sub_technique: null
        tactic: "TA0010"
        rationale: "Unencrypted PHI in Kafka topics enables collection if broker compromise occurs."

  recommendation:
    posture: required             # required | recommended | consider
    summary: "Add field-level envelope encryption before producer serialization."
    detail: |
      Detailed remediation guidance with architectural specificity, not
      generic best-practice prose. Name the components touched and the
      sequence of changes.
    references:
      - "internal: PHI_FIELD_CLASSIFICATION_GUIDE.md §6"
      - "external: NIST SP 800-57 Part 1 Rev. 5 §5.2"

  related_concerns: [integrity, non_repudiation]
  cross_references: []            # finding_ids from earlier tiers, filled in tier 2/3
```

### Required vs optional fields

**Always required:** `id`, `agent`, `apd_tier`, `apd_goal`, `disposition`, `severity`, `confidence`, `title`, `summary`, `detail`, `evidence` (≥1 entry), `control_mappings.nist_800_53r5` (may be empty list with rationale in detail), `recommendation`.

**Required conditionally:**

- `prerequisite_evidence` — required when `disposition: blocked` or `confidence: low`
- `control_mappings.mitre_attack` — emit only when the agent is highly confident the technique applies; empty list is the default
- `cross_references` — required for tier 2 and tier 3 findings that build on tier 1/2 findings
- `recommendation.detail` — required when `posture: required` or `posture: recommended`; may be a single sentence when `posture: consider`

**Optional:** `related_concerns` (default empty list), `recommendation.references` (default empty list).

### Field semantics

**`id`** — deterministic identifier of the form `<shortcode>-<sha8>`. Shortcodes by agent: `conf` (Confidentiality), `intg` (Integrity), `avail` (Availability), `dist` (Distributed), `resil` (Resilient), `ephem` (Ephemeral), `auth` (Authenticity), `nonrep` (Non-Repudiation), `immut` (Immutability). The sha8 is the first 8 hex characters of SHA-256 over `title + first evidence locator`.

**`disposition`** — what kind of finding this is.

- `gap` — required control or property is absent.
  - Example: "Audit log is not encrypted at rest." (Property absent.)
  - Example: "No retry policy specified for the eligibility vendor call." (Control absent.)
  - Example: "MFA not required on the admin portal." (Control absent.)
- `risk` — present but inadequate, or with material weakness.
  - Example: "TLS configured but cipher suite allows 3DES." (Present but weak.)
  - Example: "Retries present but no jitter; thundering herd risk." (Present but inadequate.)
  - Example: "Audit log written but actor attribution is the system account." (Present but inadequate.)
- `uncertainty` — concern identified but evidence is incomplete; partial reasoning still possible.
  - Example: "Tech plan mentions 'TLS' without specifying version." (Partial evidence — TLS is intended.)
  - Example: "Retention is described as 'meets regulatory' without citation." (Partial.)
  - Example: "Backup encryption mentioned generally without key-management detail." (Partial.)
- `blocked` — cannot assess in this lens without prerequisite evidence. Must populate `prerequisite_evidence`.
  - Example: "No documentation of KMS hierarchy at all; cannot assess key separation."
  - Example: "Tech plan silent on vendor SLAs."
  - Example: "Audit format unspecified; cannot evaluate ATNA conformance."

**`severity`** — calibrated against the impact-to-PBM rubric (see `apd-evidence-discipline` skill). Justified in `detail`.

**`confidence`** — agent's confidence in the finding given available evidence.

- `high` — direct evidence in artifacts, unambiguous interpretation.
- `medium` — strong inference from artifacts, minor interpretive judgment.
- `low` — significant inference required; consider `disposition: uncertainty` instead.

**`title`** — must name a component and a concern. "Encryption is weak" is rejected. "PHI fields in Kafka claim-events topic lack envelope encryption" is accepted.

**`evidence`** — at least one entry. Each entry is `{artifact, locator, excerpt}`. Locators must be specific enough to find again (section heading + paragraph, line range, sheet/cell, slide number). Excerpts must be brief — ≤ 25 whitespace-separated tokens — and verbatim from the source.

**`control_mappings.nist_800_53r5`** — control IDs with enhancements where applicable (e.g. `SC-8(1)`, not just `SC-8`). At minimum the agent should consider AC, AU, IA, SC, SI, CM families for relevance.

**`control_mappings.mitre_attack`** — high-confidence only. The `rationale` field must justify the mapping in one sentence; vague mappings ("could enable lateral movement") are rejected. If the agent cannot write a specific rationale, the technique does not belong on the finding.

**`recommendation.posture`** —

- `required` — without this, the system fails a compliance obligation or carries unacceptable PBM risk.
- `recommended` — material risk reduction with reasonable cost.
- `consider` — defense-in-depth or hardening that the architect should weigh against effort.

**`related_concerns`** — other APD goals the agent suspects are implicated but did not analyze. Do not write findings outside your lens; populate this field instead.

---

## Capability schema

```yaml
capability:
  schema_version: 1
  id: <agent-shortcode>-cap-<sha8>    # (tooling-authored — do not emit)
  agent: confidentiality
  apd_tier: trustworthiness
  apd_goal: confidentiality

  title: "Field-level envelope encryption on PHI columns at rest"
  description: |
    What's in place, how it's implemented per the artifact. Specific to
    what the doc says, not generic framing.

  maturity: designed              # designed | implemented | tested | operationalized
  scope: |
    Confirmed for member_demographics and claims tables.
    Not addressed: audit_log, event_payloads in Kafka. See related findings.

  evidence:
    - artifact: tech_plan.md
      locator: "§5.3 'Data at Rest'"
      excerpt: "..."

  control_mappings:
    nist_800_53r5: ["SC-12", "SC-12(1)", "SC-13", "SC-28(1)"]
    mitre_attack_mitigations:
      - id: "M1041"
        rationale: "Field-level encryption mitigates collection from data store compromise."

  caveats:
    - "Key rotation cadence not specified in tech plan."
    - "DEK access boundary on application side unconfirmed."

  related_concerns: [non_repudiation]
```

### Capability required vs optional fields

**Always required:** `id`, `agent`, `apd_tier`, `apd_goal`, `title`, `description`, `maturity`, `scope`, `evidence` (≥1 entry), `control_mappings.nist_800_53r5`.

**Required conditionally:**

- `caveats` — required when any aspect of the capability is unconfirmed or partially scoped; recommended in nearly all cases for tech plan reviews.

**Optional:** `control_mappings.mitre_attack_mitigations`, `related_concerns`.

### Maturity ladder and the tech-plan validator constraint

- **`designed`** — intent stated in tech plan or design doc. Floor for tech plan reviews.
- **`implemented`** — non-tech-plan evidence required: config file, code reference, infrastructure-as-code resource, runtime screenshot.
- **`tested`** — non-tech-plan evidence required: test report, test code reference, audit artifact.
- **`operationalized`** — non-tech-plan evidence required: runbook, monitoring dashboard, alert definition.

**Validator rule.** If `maturity` is `implemented`, `tested`, or `operationalized`, at least one `evidence` entry must reference an artifact whose type is NOT `tech_plan` (per the intake artifact index). Violations are rejected.

### Scope honesty

The `scope` field is the most important truth-telling mechanism. A capability without an explicit scope statement is rejected. Acceptable scope statements name what is confirmed AND what is not addressed in the same paragraph.

### Caveats over silence

If you want to confirm a capability but see gaps in the evidence, emit it *with caveats*, not silently. Caveats preserve coverage signal and let the synthesizer reconcile against findings.

---

## ID generation

IDs are deterministic so that re-runs produce stable identifiers and the synthesizer can detect when an agent re-emits an identical finding.

```
finding.id    = <shortcode>-<sha8(title + "|" + first_evidence_locator)>
capability.id = <shortcode>-cap-<sha8(title + "|" + first_evidence_locator)>
```

Use a deterministic SHA-256, take the first 8 hex characters. If the title or first evidence locator changes between runs, the ID changes — this is intentional, treat it as a different finding.

---

## The lens_perspectives block (synthesizer-only)

When the synthesizer merges two findings from different agents into a single record, it preserves each agent's analytical content in a `lens_perspectives` block on the merged finding:

```yaml
lens_perspectives:
  confidentiality:
    summary: "Original summary from Confidentiality agent."
    detail: "Original detail from Confidentiality agent."
  non_repudiation:
    summary: "Original summary from Non-Repudiation agent."
    detail: "Original detail from Non-Repudiation agent."
```

Specialist agents do not emit `lens_perspectives` — it is added only at synthesis. The merged finding's top-level `summary` and `detail` are rewritten by the synthesizer to address all lenses; `lens_perspectives` keeps the originals available for traceability.

---

## Validation checklist (agents run this before emitting)

1. Required fields all present
2. `disposition: blocked` ⇒ `prerequisite_evidence` populated
3. `confidence: low` ⇒ `prerequisite_evidence` populated OR `disposition: uncertainty`
4. Every `evidence` entry has artifact + locator + excerpt ≤ 25 whitespace-separated tokens
5. Every `mitre_attack` entry has a specific one-sentence rationale (no vague verbs)
6. `recommendation.posture: required` ⇒ severity ≥ high (typically) AND `recommendation.detail` populated
7. Capability `maturity` ≥ `implemented` ⇒ at least one non-tech-plan evidence entry
8. Capability `scope` statement is explicit about what is and is not confirmed
9. `title` names a component and a concern (not generic property statement)
10. ID is **absent** in agent output (the assembler authors it)
