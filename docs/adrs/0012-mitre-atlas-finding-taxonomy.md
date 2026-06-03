# ADR-0012: MITRE ATLAS as a First-Class Finding Taxonomy

**Status:** Accepted
**Date:** 2026-06-03
**Supersedes:** —
**Superseded by:** —

## Context

APD Gauntlet v1.6.0 ships the `agentic-ai` domain pack, which targets
autonomous LLM-agent systems: tool-use agents, multi-agent topologies, and
self-improving loops. The adversary techniques relevant to these systems —
model inversion, prompt injection via retrieval, membership inference, training
data poisoning, adversarial example transfer — are not captured by MITRE
ATT&CK (Enterprise). ATT&CK Enterprise models post-exploitation movement in
general-purpose IT infrastructure; it has no technique vocabulary for
adversarial-ML attacks at the model layer.

NIST 800-53r5 and D3FEND address the defensive control and countermeasure
layers. They do not provide an attacker-technique taxonomy for ML/AI-specific
adversarial behavior. Without a shared vocabulary for ML adversary techniques,
`agentic-ai` domain findings that reference adversarial-ML attacks can only
express them in prose, losing the structured cross-referencing and coverage
rollups that taxonomy IDs enable.

The multi-framework taxonomy mapping approach codified in ADR-0008 provides
the pattern: optional, per-run-scoped taxonomy IDs in `control_mappings`,
coverage rollups synthesized from them, reference data maintained via a
`refresh-*` CLI verb. ADR-0008 was designed around the finding/capability
split — offensive techniques on findings, defensive mappings on capabilities.
ATLAS fits the finding side of that split: its technique IDs describe what an
adversary does, not what a defender deploys.

## Decision

Adopt **MITRE ATLAS as a findings-only (offensive) taxonomy**, extending the
multi-framework taxonomy-mapping approach of ADR-0008.

**Schema placement.** Specialists emit ATLAS technique IDs in
`control_mappings.atlas` as an ID list. IDs match the pattern
`AML.T####[.###]` (base technique or sub-technique). This is parallel to the
existing `control_mappings.mitre_attack` list on findings. ATLAS is
offensive-only: it does not appear in `control_mappings` on capabilities
(which carry defensive mappings: D3FEND, NIST 800-53r5). This preserves the
finding/capability split ADR-0008 established.

**Relationship to ATT&CK.** ATLAS and ATT&CK coexist on the same finding.
A finding that describes a prompt-injection vector might carry both an
ATT&CK technique for the initial-access phase and an ATLAS technique for
the adversarial-ML attack method. The two IDs are complementary, not
mutually exclusive.

**Activation.** Declare `mitre_atlas` in the `taxonomies:` list of
`.apd-run.yaml`. Default-off (like OWASP variants in ADR-0008). The
`agentic-ai` domain pack activates it by default; operators on other
domain packs opt in explicitly.

**Reference data.** A bundled `data/atlas-techniques.json` catalog ships with
the gauntlet, maintained by a new `apd-gauntlet refresh-atlas` CLI verb.
Refresh cadence follows the same quarterly pattern as `refresh-d3fend` and
`refresh-cwe` (ADR-0008).

**Coverage rollup.** A gated `atlas-coverage` synthesis rollup
(`atlas-coverage.schema.json`) aggregates technique-level coverage across all
findings in the run. The synthesizer emits it when `mitre_atlas` is in scope;
the HTML report renders it as a "MITRE ATLAS" taxonomy family alongside the
ATT&CK and D3FEND families.

**Mapping discipline.** ATLAS IDs in `control_mappings.atlas` carry the same
high-confidence bar as ATT&CK IDs in `control_mappings.mitre_attack`: the
mapping must reflect the actual adversary technique the finding demonstrates,
not a superficial name-similarity match. The `apd-control-mappings` skill
gains an ATLAS discipline section. ATLAS IDs belong in findings (per the
finding-schema's evidence-grounded mapping discipline), not in pattern prose
or skill narratives.

## Alternatives considered

### ATLAS IDs in narrative prose only (no structured field)

**Rejected.** Prose references cannot drive coverage rollups, validator
cross-checks, or the HTML report's taxonomy family rendering. The structured
`control_mappings.atlas` field enables all three with zero changes to the
finding schema's outer shape (the field is additive within `control_mappings`,
consistent with ADR-0008's additive-only policy).

### New top-level finding field `mitre_atlas[]` instead of `control_mappings.atlas`

**Rejected.** Placing ATLAS at the top level of the finding schema would
diverge from the ADR-0008 pattern (all taxonomy IDs live inside
`control_mappings`) and would require all nine specialists to update their
mental model of where taxonomy IDs go. The `control_mappings` envelope is the
correct home for structured offensive-technique vocabulary.

### ATLAS on capabilities as well as findings

**Rejected.** ATLAS describes adversarial-ML attack techniques — what an
adversary does. Capabilities describe what a defender provides. Adding ATLAS
to `control_mappings` on capabilities would blur the finding/capability split
that ADR-0008 established and that the D3FEND `counters_attack` cross-reference
rule depends on. Keeping ATLAS findings-only preserves the split cleanly.

### Always-on (not per-run-scoped)

**Rejected.** ATLAS is relevant only to AI/ML-bearing systems. Making it
default-on would prompt specialists to map ATLAS IDs on findings for
infrastructure and API-only systems where no adversarial-ML surface exists,
diluting signal in the same way always-on OWASP variants would (per
ADR-0008's reasoning for OWASP as opt-in).

## Consequences

- Adversarial-ML findings in `agentic-ai` domain runs carry precise, shared
  ATLAS technique IDs rather than prose descriptions. The `atlas-coverage`
  rollup quantifies which ATLAS techniques the run's findings address.
- Schema additions are fully additive within v1.x: `control_mappings.atlas`
  is a new optional array on the finding schema. v1.5-format findings validate
  unchanged against v1.6 schemas.
- `report-audit.yaml`'s `taxonomy_titles_resolve` check (ADR-0011) covers
  ATLAS IDs: the audit checker resolves `AML.T####[.###]` against the bundled
  `atlas-techniques.json`. Runs without `mitre_atlas` in scope are exempt.
- A new `refresh-atlas` CLI verb and `atlas-techniques.json` catalog join the
  quarterly refresh cadence alongside `refresh-d3fend` and `refresh-cwe`.
  Operators who never declare `mitre_atlas` are unaffected by the catalog.
- The `apd-control-mappings` skill gains an ATLAS discipline section; all
  specialists that handle agentic-ai or other AI/ML surfaces read it as part of
  their standard skill loading.
- Domain packs that target non-AI/ML systems (`api-security`, `mobile-
  applications`) do not declare `mitre_atlas` and produce no ATLAS output.
  The additive-only schema change means their existing runs and validators
  require no modification.
