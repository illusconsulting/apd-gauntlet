# Architecture

How the APD Gauntlet works under the hood. Read this if you want to understand the framework's reasoning structure, the agent dispatch lifecycle, the role of the validator, and the discipline anchors that govern specialist behavior.

## The framework

APD is a goal-based security architecture framework organized into three tiers, each containing three goals:

```
Assure Trustworthiness   →  Confidentiality · Integrity · Availability
Provide Scalability      →  Distributed · Resilient · Ephemeral
Demonstrate Auditability →  Authenticity · Non-Repudiation · Immutability
```

The tier ordering is load-bearing:

- **Trustworthiness is foundational.** A system that cannot be trusted with data cannot meaningfully scale or be audited.
- **Scalability is operational.** A trustworthy system that cannot operate under failure or scale is fragile in production.
- **Auditability is accountability.** A trustworthy, scalable system that cannot prove what it did is uninspectable.

The gauntlet processes tiers in order. Tier 2 specialists may cite tier 1 findings via `cross_references`; tier 3 may cite tier 1 and 2. Specialists never cite *later* tiers. This dependency direction makes the framework's reasoning graph acyclic.

See [ADR-0001](adrs/0001-three-tier-structure.md) for the full rationale.

## The twelve agents

| Role | Agent | Purpose |
|---|---|---|
| Coordinator | `apd-orchestrator` | Phases the run, dispatches specialists, invokes the validator and synthesizer |
| Intake | `apd-intake` | Inventories artifacts, builds a PHI/PII data taxonomy, identifies evidence gaps, produces the context brief |
| Specialist × 9 | `apd-confidentiality`, `apd-integrity`, `apd-availability`, `apd-distributed`, `apd-resilient`, `apd-ephemeral`, `apd-authenticity`, `apd-non-repudiation`, `apd-immutability` | Each analyzes input artifacts through one lens; emits findings and capabilities |
| Synthesizer | `apd-synthesizer` | Reads all nine specialist outputs; clusters via merge/link/separate; produces the advisory report and rollups |

Each agent lives in [.claude/agents/](../.claude/agents/) as a markdown file with YAML frontmatter. The specialists are domain-neutral (the analytical checklist is the same regardless of industry); domain-specific calibration (severity rubric, common patterns, consequential-action surface) loads from the active domain pack — see [Adapting to other domains](adapting-to-other-domains.md).

## The five skills

| Skill | Purpose |
|---|---|
| `apd-framework` | Canonical lens definitions, boundary calls between adjacent goals |
| `apd-finding-schema` | YAML contracts for findings and capabilities; the JSON Schema files at `schemas/*.schema.json` are the canonical contract |
| `apd-evidence-discipline` | Five discipline rules (evidence-pointer required, block on ambiguity, stay in your lens, reproduce before recommend, calibrated posture) |
| `apd-control-mappings` | NIST 800-53r5 mapping families per goal; MITRE ATT&CK mapping discipline |
| `apd-domain` | **Generated** at runtime from the active domain pack — contains the severity rubric, consequential actions, common patterns |

The first four ship under [.claude/skills/](../.claude/skills/). `apd-domain` is produced by `apd-gauntlet build-domain-skill <pack>` (the orchestrator runs this in Phase 0).

## Run lifecycle

```
Phase 0  Setup       → orchestrator creates runs/<id>/{00-context,10-trust,20-scale,30-audit,40-synth}
                       and runs `apd-gauntlet build-domain-skill <pack>`
Phase 1  Intake      → apd-intake produces context-brief.md (frontmatter + typed artifact index + PHI inventory)
Phase 2  Tier 1 (∥)  → confidentiality / integrity / availability emit findings.yaml + capabilities.yaml
                       then `apd-gauntlet validate <run>` over tier-1 outputs
Phase 3  Tier 2 (∥)  → distributed / resilient / ephemeral (read tier 1 outputs); validate
Phase 4  Tier 3 (∥)  → authenticity / non-repudiation / immutability (read tier 1+2); validate
Phase 5  Synthesis   → synthesizer clusters (merge/link/separate), reconciles severities,
                       rolls up NIST/ATT&CK/APD coverage, produces advisory-report.md
Phase 6  Closeout    → orchestrator returns summary; advisory report has frontmatter (framework_version,
                       domain_pack, run_id, specialists_skipped)
```

### Phase 1.5 — Code reconnaissance (optional, v1.1+)

When `.apd-run.yaml: code_recon` is `enabled` or `auto` and the codebase-memory-mcp (CBM) tools are reachable, the orchestrator dispatches the optional `apd-code-recon` agent between Phase 1 (Intake) and Phase 2 (Trustworthiness tier). The agent uses CBM's symbol graph and call-graph tracing to produce a code-grounded companion to the intake brief — `code-architecture-brief.md` for human reviewers and `code-evidence-index.yaml` for specialist citations.

Phase 1.5 is **optional** by design: gauntlet runs without CBM still work end-to-end. Specialists treat code-evidence-index entries as ordinary `evidence[].artifact` references; the validator recognizes the filename automatically. See [ADR 0007](adrs/0007-optional-code-reconnaissance-via-cbm.md) for rationale.

## The validator's three passes

The Python `apd-gauntlet` CLI runs three passes over a run directory:

1. **Schema validation** — every record against `schemas/*.schema.json` (JSON Schema draft 2020-12).
2. **Semantic lints** — checks JSON Schema cannot express:
   - Evidence excerpts ≤ 25 whitespace-separated tokens.
   - Deterministic IDs match `SHA-256(title + "|" + first_evidence_locator)[:8]`.
   - Capability `maturity ≥ implemented` requires at least one non-tech-plan evidence entry.
   - MITRE ATT&CK rationale must avoid hedge words (`could`, `may`, `potentially`) — warning, not error.
3. **Cross-file resolution** — `cross_references` and `merged_from` IDs exist; `evidence.artifact` appears in the intake brief's frontmatter; `contradictions.yaml` references resolve.

See [ADR-0004](adrs/0004-json-schema-validation.md) for why JSON Schema, and [ADR-0005](adrs/0005-deterministic-finding-ids.md) for the deterministic ID rule.

## Three discipline anchors

These three rules govern every specialist's output:

1. **Evidence-pointer required.** Every finding cites at least one artifact with a specific locator and a verbatim excerpt under 25 words. Generic citation ("the tech plan describes encryption") is rejected; specific citation ("§5.3 ¶2: 'AES-256 at rest with broker-managed keys'") is required.

2. **Block on ambiguity.** If artifacts are silent or contradictory in your lens, emit `disposition: blocked` with `prerequisite_evidence` naming what's needed. Do not infer presence or absence. See [ADR-0002](adrs/0002-block-on-ambiguity-default.md).

3. **Stay in your lens.** If a concern is in another goal's territory, populate `related_concerns` rather than writing the finding yourself. The synthesizer relies on lens discipline to distinguish "same root cause, two lenses" (merge) from "two concerns sharing evidence" (link).

## Synthesizer logic

The synthesizer:

1. Runs `apd-gauntlet validate` over the full run; rejected records go to `rejected-records.yaml`.
2. Clusters findings using three signals: evidence locator overlap, title similarity, `related_concerns` intersection.
3. Applies merge / link / separate per cluster:
   - **Merge** when findings describe the same root cause through different lenses. Take max severity; union NIST and ATT&CK mappings; preserve each agent's `summary`/`detail` in a `lens_perspectives` block.
   - **Link** when findings share evidence but address distinct concerns. Both records stand; each gets a `cross_references` entry.
   - **Separate** when initial clustering signals were spurious.
4. Detects finding-vs-capability contradictions (finding asserts absence, capability asserts presence) and writes them to `contradictions.yaml`.
5. Reconciles severity disagreements; highest severity wins on merged records; disagreement preserved in `severity-disagreements.yaml`.
6. Produces NIST 800-53r5 coverage, ATT&CK exposure, and APD coverage matrices.
7. Composes the human-readable advisory report.

Cluster decisions are LLM-driven (no algorithmic clustering code in the validator). See [ADR-0006](adrs/0006-llm-driven-clustering.md).

## Output files

After a successful run:

```
runs/<run-id>/
├── inputs/                       # your artifacts (untouched)
├── 00-context/
│   └── context-brief.md          # intake output with frontmatter
├── 10-trustworthiness/
│   ├── confidentiality.findings.yaml     confidentiality.capabilities.yaml
│   ├── integrity.findings.yaml           integrity.capabilities.yaml
│   └── availability.findings.yaml        availability.capabilities.yaml
├── 20-scalability/               # six files, same shape
├── 30-auditability/              # six files, same shape
└── 40-synthesis/
    ├── deduped-findings.yaml             deduped-capabilities.yaml
    ├── contradictions.yaml               severity-disagreements.yaml
    ├── nist-coverage.yaml                attack-exposure.yaml
    ├── apd-coverage-matrix.yaml          rejected-records.yaml
    └── advisory-report.md                # the deliverable
```

## Domain packs

Severity calibration, consequential-action surface, immutability classes, data taxonomy, and per-goal common patterns are domain-specific. They live in `domains/<name>/` packs. The PBM pack ships in v1.0. The orchestrator builds `.claude/skills/apd-domain/SKILL.md` from the active pack in Phase 0. See [adapting-to-other-domains.md](adapting-to-other-domains.md) and [ADR-0003](adrs/0003-pluggable-domain-packs.md).
