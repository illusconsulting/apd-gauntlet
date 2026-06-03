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

## The 19 agents

The gauntlet ships 19 agents: intake, the nine specialists, the synthesizer and its three decomposed-synthesis agents (cluster adjudicator, report writer, report auditor), and five activation-gated optional agents that the runner dispatches only when their preconditions are met. Coordination is not an agent — the deterministic `apd-gauntlet` workflow runner phases the run.

| Role | Agent | Purpose |
|---|---|---|
| Coordinator | `.claude/workflows/apd-gauntlet.js` (the `apd-gauntlet` runner) | Phases the run, dispatches specialists via receipts, runs the decomposed synthesis + report audit |
| Intake | `apd-intake` | Inventories artifacts, builds a PHI/PII data taxonomy, identifies evidence gaps, produces the context brief |
| Specialist × 9 | `apd-confidentiality`, `apd-integrity`, `apd-availability`, `apd-distributed`, `apd-resilient`, `apd-ephemeral`, `apd-authenticity`, `apd-non-repudiation`, `apd-immutability` | Each analyzes input artifacts through one lens; emits findings and capabilities |
| Synthesis (decomposed) | `apd-cluster-adjudicator`, `apd-report-writer`, `apd-report-auditor` | Adjudicate finding/capability clusters, author the advisory report, and audit it against the corpus — the runner drives these via receipts |
| Synthesis (fallback) | `apd-synthesizer` | One-shot fallback when the decomposed path fails: clusters via merge/link/separate and produces the report and rollups directly |
| Optional intake (v1.1+) | `apd-code-recon` | Produces the code-grounded companion to the intake brief from codebase-memory-mcp call/symbol graphs |
| Optional intake (v1.3+) | `apd-threat-model-recon` | Parses a supplied threat model into a normalized graph; recognized methodologies include STRIDE, LINDDUN, PASTA, and CSA MAESTRO (reduced-fidelity `methodology_hint: maestro`, L1–L7 layers mapped to APD goals) |
| Optional synthesis (v1.3+) | `apd-threat-model-evaluator` | Emits coverage-gap, contradiction, and silence findings against the dedup'd specialist findings |
| Optional synthesis (v1.4+) | `apd-attack-path-analyzer` | Enumerates BloodHound-style attack paths from declared attacker positions to declared crown jewels over a partial graph; recommends D3FEND counters on bottleneck edges that expose ATT&CK techniques |
| Optional post-synthesis (v1.5+) | `apd-domain-auditor` | Captures domain-pack improvement opportunities into an advisory `domain-improvements.yaml` (non-blocking) |

Each agent lives in [.claude/agents/](../.claude/agents/) as a markdown file with YAML frontmatter. The specialists are domain-neutral (the analytical checklist is the same regardless of industry); domain-specific calibration (severity rubric, common patterns, consequential-action surface) loads from the active domain pack — see [Adapting to other domains](adapting-to-other-domains.md). The five activation-gated optional agents (code-recon, threat-model-recon, threat-model-evaluator, attack-path-analyzer, domain-auditor) declare their preconditions in `.apd-run.yaml` or the active domain pack, and the runner skips them silently (or blocks, where the discipline rule demands it) when those preconditions are unmet.

A twentieth file, `apd-orchestrator.md`, remains in [.claude/agents/](../.claude/agents/) as a **deprecated shim** — superseded by the `apd-gauntlet` workflow runner and retained only as a historical-topology reference; it is not a functional agent and is not counted among the 19.

## Tier topology

### Tier-0 (intake)

- apd-intake
- apd-code-recon (optional, v1.1+)
- apd-threat-model-recon (optional, v1.3+)

### Tier-1 (trustworthiness)

- apd-confidentiality
- apd-integrity
- apd-availability

### Tier-2 (scalability)

- apd-distributed
- apd-resilient
- apd-ephemeral

### Tier-3 (auditability)

- apd-authenticity
- apd-non-repudiation
- apd-immutability

### Tier-4 (synthesis)

- apd-cluster-adjudicator
- apd-report-writer
- apd-report-auditor
- apd-synthesizer (fallback)
- apd-threat-model-evaluator (optional, v1.3+)
- apd-attack-path-analyzer (optional, v1.4+)
- apd-domain-auditor (optional, v1.5+)

## The five skills

| Skill | Purpose |
|---|---|
| `apd-framework` | Canonical lens definitions, boundary calls between adjacent goals |
| `apd-finding-schema` | YAML contracts for findings and capabilities; the JSON Schema files at `schemas/*.schema.json` are the canonical contract |
| `apd-evidence-discipline` | Five discipline rules (evidence-pointer required, block on ambiguity, stay in your lens, reproduce before recommend, calibrated posture) |
| `apd-control-mappings` | NIST 800-53r5 mapping families per goal; MITRE ATT&CK mapping discipline; MITRE ATLAS adversarial-ML technique IDs (`AML.T####`) for AI/ML surfaces |
| `apd-domain` | **Generated** at runtime from the active domain pack — contains the severity rubric, consequential actions, common patterns |

The first four ship under [.claude/skills/](../.claude/skills/). `apd-domain` is produced by `apd-gauntlet build-domain-skill <pack...>` (the runner runs this in Phase 0). In addition to the full cross-goal `SKILL.md`, the build step emits nine goal-scoped sidecars at `.claude/skills/apd-domain/by-goal/<goal>.md` — one per lens agent. Each sidecar contains only that goal's common-patterns section, which bounds context on multi-domain runs. The full `SKILL.md` is still loaded by the cross-goal consumers: `apd-intake`, `apd-attack-path-analyzer`, and `apd-domain-auditor`.

## Run lifecycle

```
Phase 0  Setup       → runner creates runs/<id>/{00-context,10-trust,20-scale,30-audit,40-synth}
                       and runs `apd-gauntlet build-domain-skill <pack...>`
Phase 1  Intake      → apd-intake produces context-brief.md (frontmatter + typed artifact index + PHI inventory)
Phase 2  Tier 1 (∥)  → confidentiality / integrity / availability emit findings.yaml + capabilities.yaml
                       then `apd-gauntlet validate <run>` over tier-1 outputs
Phase 3  Tier 2 (∥)  → distributed / resilient / ephemeral (read tier 1 outputs); validate
Phase 4  Tier 3 (∥)  → authenticity / non-repudiation / immutability (read tier 1+2); validate
Phase 5  Synthesis   → synthesizer clusters (merge/link/separate), reconciles severities,
                       rolls up NIST/ATT&CK/APD coverage, produces advisory-report.md
Phase 6  Closeout    → runner returns summary; advisory report has frontmatter (framework_version,
                       domain_pack, run_id, specialists_skipped)
```

### Phase 1.5 — Code reconnaissance (optional, v1.1+)

When `.apd-run.yaml: code_recon` is `enabled` or `auto` and the codebase-memory-mcp (CBM) tools are reachable, the runner dispatches the optional `apd-code-recon` agent between Phase 1 (Intake) and Phase 2 (Trustworthiness tier). The agent uses CBM's symbol graph and call-graph tracing to produce a code-grounded companion to the intake brief — `code-architecture-brief.md` for human reviewers and `code-evidence-index.yaml` for specialist citations.

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
6. Produces NIST 800-53r5 coverage, ATT&CK exposure, and APD coverage matrices. When `mitre_atlas` is declared in `.apd-run.yaml`, also produces an ATLAS coverage rollup over adversarial-ML technique IDs.
7. Composes the human-readable advisory report.
8. Runs the `audit-report` completeness gate: cross-checks the built report data against the authoritative YAMLs and enforces eight completeness checks (`structural`: attack_paths_present, d3fend_overlay_present, apd_matrix_nonempty, coverage_rollups_nonempty, taxonomy_titles_resolve, section_errors_empty; `editorial`: exec_summary_present, editorial_sections_present). A structural failure that is still unresolved after two remediation attempts blocks the run — a completed run guarantees a structurally complete report. Editorial gaps self-heal via the report-writer; the LLM auditor's semantic residual (misleading-severity / material-omission / invented-content) stays non-blocking.

Cluster decisions are LLM-driven (no algorithmic clustering code in the validator). See [ADR-0006](adrs/0006-llm-driven-clustering.md).

## Output files

After a successful run:

```
runs/<run-id>/
├── inputs/                       # your artifacts (untouched)
├── 00-context/
│   ├── context-brief.md          # intake output with frontmatter
│   ├── asset-inventory.yaml             (v1.4+, intake rollup)
│   ├── code-evidence-index.yaml         (v1.1+, optional)
│   └── threat-model-normalized.yaml     (v1.3+, optional)
├── 20-findings/
│   ├── 10-trustworthiness/
│   │   ├── confidentiality.findings.yaml     confidentiality.capabilities.yaml
│   │   ├── integrity.findings.yaml           integrity.capabilities.yaml
│   │   └── availability.findings.yaml        availability.capabilities.yaml
│   ├── 20-scalability/               # six files, same shape
│   ├── 30-auditability/              # six files, same shape
│   └── 40-threat-model/                 (v1.3+, optional — tmeval-*.yaml)
└── 40-synthesis/
    ├── deduped-findings.yaml             deduped-capabilities.yaml
    ├── contradictions.yaml               severity-disagreements.yaml
    ├── nist-coverage.yaml                attack-exposure.yaml
    ├── apd-coverage-matrix.yaml          rejected-records.yaml
    ├── cwe-coverage.yaml                 # v1.2+ (when cwe declared)
    ├── owasp-coverage.yaml               # v1.2+ (when any owasp_* declared)
    ├── d3fend-coverage.yaml              # v1.2+ (when d3fend declared)
    ├── atlas-coverage.yaml               # v1.6+ (when mitre_atlas declared)
    ├── threat-model-coverage-report.md  (v1.3+, optional)
    ├── threat-model-coverage.yaml       (v1.3+, optional)
    ├── asset-graph.yaml                 (v1.4+, optional — attack-path analyzer)
    ├── attack-paths.yaml                (v1.4+, optional — attack-path analyzer)
    ├── defense-graph.yaml               (v1.4+, optional — D3FEND overlay)
    ├── attack-path.findings.yaml        (v1.4+, optional — apath-* findings)
    └── attack-path-report.md            (v1.4+, optional — human-readable report)
```

The activation-gated rollups (`cwe-coverage.yaml`, `owasp-coverage.yaml`, `d3fend-coverage.yaml`, `atlas-coverage.yaml`) are emitted only when the corresponding taxonomies are declared in the run's `taxonomies:` field in `.apd-run.yaml`. `atlas-coverage.yaml` (v1.6+) covers MITRE ATLAS adversarial-ML techniques and is gated on `mitre_atlas`. Runs that omit the `taxonomies:` field produce the same output as v1.1. See [docs/taxonomy-mappings.md](taxonomy-mappings.md) for the full operator guide.

## Output schemas

The validator uses the following JSON Schema files (`schemas/*.schema.json`):

- `schemas/finding.schema.json` — YAML contract for findings (all agents).
- `schemas/capability.schema.json` — YAML contract for capabilities (all agents).
- `schemas/run-config.schema.json` — YAML contract for `.apd-run.yaml`.
- `schemas/attack-exposure.schema.json` — Synthesizer ATT&CK rollup.
- `schemas/d3fend-coverage.schema.json` — Synthesizer D3FEND rollup (v1.2+).
- `schemas/cwe-coverage.schema.json` — Synthesizer CWE rollup (v1.2+).
- `schemas/atlas-coverage.schema.json` — Synthesizer MITRE ATLAS adversarial-ML technique rollup (v1.6+).
- `schemas/threat-model-normalized.schema.json` — Recon output (v1.3+).
- `schemas/threat-model-coverage.schema.json` — Evaluator output (v1.3+).
- `schemas/_defs.schema.json` — Shared pattern definitions for ATT&CK/D3FEND/CWE (v1.3+).
- `schemas/asset-inventory.schema.json` — Intake rollup of assets, trust boundaries, and data classifications (v1.4+).
- `schemas/asset-graph.schema.json` — Analyzer-built graph of nodes and typed edges with provenance and confidence (v1.4+).
- `schemas/attack-path.schema.json` — Enumerated attack paths, bottleneck-edge set, and the `enumeration_parameters` block (v1.4+).
- `schemas/defense-graph.schema.json` — D3FEND counter overlay on bottleneck edges that expose ATT&CK techniques (v1.4+).

See [Attack-path analysis](attack-path-analysis.md) for the operator guide to the v1.4 analyzer.

## Domain packs

Severity calibration, consequential-action surface, immutability classes, data taxonomy, and per-goal common patterns are domain-specific. They live in `domains/<name>/` packs. The PBM pack ships in v1.0. The runner builds `.claude/skills/apd-domain/SKILL.md` from the active pack(s) in Phase 0, and also emits nine goal-scoped sidecars (`.claude/skills/apd-domain/by-goal/<goal>.md`) — one per lens agent — so specialists load only their own goal's common patterns (v1.6+). The full `SKILL.md` is retained for `apd-intake`, `apd-attack-path-analyzer`, and `apd-domain-auditor`. See [adapting-to-other-domains.md](adapting-to-other-domains.md) and [ADR-0003](adrs/0003-pluggable-domain-packs.md).
