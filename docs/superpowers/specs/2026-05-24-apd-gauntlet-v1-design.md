# APD Gauntlet v1.0 — Design Spec

**Date:** 2026-05-24
**Status:** Approved (brainstorming complete; ready for implementation planning)
**Scope:** Complete v1.0 production release of the APD Gauntlet — a multi-agent security architecture review framework built on the APD model (Assure Trustworthiness, Provide Scalability, Demonstrate Auditability).

---

## 1. Context

The starting point is the content in `9-agent-apd-framework/` — twelve agent markdown files (1 orchestrator, 1 intake, 1 synthesizer, 9 specialists), three skill files (in a partial nested duplicate), four YAML/markdown templates, and a README. The content is well-designed: rigorous lens-vs-scope discipline, block-on-ambiguity defaults, schema contracts for findings and capabilities, a PBM-specific impact-to-severity rubric. What's missing is the *package* — proper layout, machine-readable schemas, a validator, examples, distribution mechanism, and the genericization seams that let it ship as open-source software.

This spec describes the v1.0 release that turns the framework content into a production-ready open-source project.

## 2. Design Decisions (locked)

| Dimension | Decision |
|---|---|
| Distribution | Canonical Git repository + Claude Code plugin published from it |
| Audience | Open source, PBM as the bundled starting domain, genericization documented |
| License | Apache-2.0 |
| Validation | JSON Schema files + Python validator CLI (`apd-gauntlet`) |
| Domain model | Pluggable domain packs; `domains/pbm/` ships in v1 |
| v1 scope | Complete release (schemas, validator, agent refactor, domain pack, sample run, plugin manifest, CI, docs) |
| Build strategy | Layered foundation-first, mono-repo, single source of truth |

## 3. Goals & non-goals

**Goals.**

- Move from flat content layout to a Claude Code-native plugin layout (`.claude/agents/`, `.claude/skills/`).
- Make the finding and capability schemas machine-enforced via JSON Schema + a Python validator.
- Extract PBM-specific content from agents and skills into a pluggable `domains/pbm/` pack.
- Ship a CI-validated synthetic sample run that exercises the full pipeline.
- Fix the contract inconsistencies identified during analysis (see §7).
- Provide a documentation set sufficient for an external contributor to (a) operate the gauntlet and (b) build a new domain pack.
- Tag v1.0.0 with a published Python package, a stable plugin manifest, and a credible README.

**Non-goals (v1).**

- A second domain pack (e.g. `domains/saas/`). Mechanism ships; second pack proves the abstraction in v1.1.
- LLM-driven clustering as a separate runnable script. The synthesizer's merge/link/separate logic remains LLM-driven; the validator only enforces structure.
- Runtime telemetry or usage analytics.
- A GUI or web report renderer. The advisory report stays markdown.
- Backwards compatibility with the pre-v1.0 flat layout. v1.0 is the first stable release; nothing prior is supported.

## 4. Repository structure

```
apd-gauntlet/
├── README.md                       # what it is, install, 60-second quickstart
├── LICENSE                         # Apache-2.0
├── CONTRIBUTING.md                 # PR conventions, DCO sign-off, testing
├── CHANGELOG.md                    # Keep-a-Changelog
├── CODE_OF_CONDUCT.md              # Contributor Covenant 2.1
├── plugin.json                     # Claude Code plugin manifest
├── pyproject.toml                  # Python package + entry point
├── .gitignore
│
├── .claude/                        # Plugin payload
│   ├── agents/
│   │   ├── apd-orchestrator.md
│   │   ├── apd-intake.md
│   │   ├── apd-synthesizer.md
│   │   └── apd-<goal>.md           # 9 specialist files
│   └── skills/
│       ├── apd-framework/SKILL.md
│       ├── apd-finding-schema/SKILL.md
│       ├── apd-evidence-discipline/SKILL.md
│       ├── apd-control-mappings/SKILL.md
│       └── apd-domain/SKILL.md     # GENERATED from active domain pack
│
├── domains/
│   └── pbm/
│       ├── domain.yaml
│       ├── severity-rubric.md
│       ├── consequential-actions.md
│       ├── immutability-classes.md
│       ├── data-taxonomy.md
│       └── common-patterns/
│           ├── confidentiality.md
│           ├── integrity.md
│           └── ... (9 files total)
│
├── schemas/                        # JSON Schema draft 2020-12
│   ├── finding.schema.json
│   ├── capability.schema.json
│   ├── contradiction.schema.json
│   ├── severity-disagreement.schema.json
│   ├── coverage-matrix.schema.json
│   ├── nist-coverage.schema.json
│   ├── attack-exposure.schema.json
│   └── domain.schema.json
│
├── templates/
│   ├── finding.template.yaml
│   ├── capability.template.yaml
│   ├── context-brief.template.md
│   └── advisory-report.template.md
│
├── tools/
│   ├── apd_gauntlet/
│   │   ├── __init__.py
│   │   ├── cli.py
│   │   ├── validate.py
│   │   ├── init_run.py
│   │   ├── build_domain_skill.py
│   │   ├── summary.py
│   │   ├── linters.py
│   │   └── data/
│   │       └── mitre-mitigations.json    # cached MITRE crosswalk
│   └── requirements.txt
│
├── tests/
│   ├── test_validate.py
│   ├── test_init_run.py
│   ├── test_build_domain_skill.py
│   ├── test_id_determinism.py
│   ├── test_examples.py
│   ├── fixtures/
│   │   ├── valid/
│   │   └── invalid/
│   └── conftest.py
│
├── examples/
│   └── apd-20260601-claim-event-bus/
│       ├── README.md
│       ├── inputs/
│       └── expected/
│
├── docs/
│   ├── architecture.md
│   ├── running-the-gauntlet.md
│   ├── adapting-to-other-domains.md
│   ├── extending-agents.md
│   ├── schema-evolution.md
│   └── adrs/
│       ├── 0001-three-tier-structure.md
│       ├── 0002-block-on-ambiguity-default.md
│       ├── 0003-pluggable-domain-packs.md
│       ├── 0004-json-schema-validation.md
│       ├── 0005-deterministic-finding-ids.md
│       └── 0006-llm-driven-clustering.md
│
└── .github/
    ├── workflows/
    │   ├── validate.yml
    │   ├── python-tests.yml
    │   ├── markdown-lint.yml
    │   └── release.yml
    ├── ISSUE_TEMPLATE/
    │   ├── bug_report.yml
    │   └── domain_pack_proposal.yml
    └── PULL_REQUEST_TEMPLATE.md
```

### File migration map (from current state to v1)

| Current location | New location |
|---|---|
| Root `apd-*.md` (12 agent files) | `.claude/agents/` |
| Root `SKILL.md` (the apd-framework skill) | `.claude/skills/apd-framework/SKILL.md` |
| `mnt/.../apd-evidence-discipline/SKILL.md` | `.claude/skills/apd-evidence-discipline/SKILL.md` (rubric removed) |
| `mnt/.../apd-finding-schema/SKILL.md` | `.claude/skills/apd-finding-schema/SKILL.md` |
| `mnt/.../apd-control-mappings/SKILL.md` | `.claude/skills/apd-control-mappings/SKILL.md` |
| Root `*.template.{yaml,md}` (4 files) | `templates/` |
| PBM severity rubric (inside evidence-discipline) | `domains/pbm/severity-rubric.md` |
| "Common finding patterns" sections in each specialist | `domains/pbm/common-patterns/<goal>.md` |
| `mnt/` directory | **deleted** (partial duplicate) |

## 5. JSON Schemas

All schemas use JSON Schema draft 2020-12. Each ships with positive and negative fixtures under `tests/fixtures/`.

| Schema | What it enforces |
|---|---|
| `finding.schema.json` | Required: `schema_version` (integer), `id`, `agent`, `apd_tier`, `apd_goal`, `disposition`, `severity`, `confidence`, `title`, `summary`, `detail`, `evidence` (minItems=1), `control_mappings.nist_800_53r5`, `recommendation`. ID pattern: `^(conf\|intg\|avail\|dist\|resil\|ephem\|auth\|nonrep\|immut\|merged)-[0-9a-f]{8}$`. Enums for agent, tier, goal, disposition, severity, confidence, recommendation.posture. Each evidence entry has `{artifact, locator, excerpt}`. Conditional: `disposition=blocked` ⇒ `prerequisite_evidence` populated. Conditional: `recommendation.posture ∈ {required, recommended}` ⇒ `recommendation.detail` populated. `mitre_attack[].rationale` required and minLength enforced. |
| `capability.schema.json` | Required: `schema_version`, `id`, `agent`, `apd_tier`, `apd_goal`, `title`, `description`, `maturity`, `scope`, `evidence` (minItems=1), `control_mappings.nist_800_53r5`. ID pattern: `^…-cap-[0-9a-f]{8}$`. Maturity enum. The "maturity ≥ implemented requires non-tech-plan evidence" rule is enforced in the Python validator (cross-references intake artifact index, which JSON Schema can't reach). |
| `contradiction.schema.json` | `id`, `finding_id`, `capability_id`, `finding_assertion`, `capability_assertion`, `evidence_comparison`, `recommended_resolution` |
| `severity-disagreement.schema.json` | `finding_id`, `agent_severities` map (agent → severity enum, minProperties=2), `chosen_severity`, `rationale` |
| `coverage-matrix.schema.json` | APD 9×N matrix: per component, nine cells each with `{findings: [ids], capabilities: [ids], posture: enum(silent\|covered\|gapped\|gapped_and_covered)}` |
| `nist-coverage.schema.json` | Per control: `id`, `family`, `title`, `finding_count`, `finding_ids`, `capability_count`, `capability_ids`, `posture` |
| `attack-exposure.schema.json` | Per technique: `id`, `sub_technique` (nullable), `tactic`, `name`, `exposure_finding_count`, `exposure_finding_ids`, `mitigated_by_capabilities` array |
| `domain.schema.json` | Validates `domains/<pack>/domain.yaml`: `name`, `display_name`, `version`, `framework_compat`, `description`, `includes`, `regulatory_anchors` |

**Schema-vs-validator split.** JSON Schema enforces structure that can be expressed declaratively. The Python validator enforces everything else: cross-file ID resolution, deterministic-ID regeneration, 25-word excerpt counting, hedge-word detection in ATT&CK rationales, maturity-vs-evidence cross-checking against the intake artifact index.

## 6. Python validator (`tools/apd_gauntlet/`)

Installed as a console script `apd-gauntlet` via `pyproject.toml` entry point. Dependencies: `jsonschema`, `pyyaml`, `click` (CLI), `rich` (output formatting). Python ≥ 3.10.

### 6.1 Subcommands

```
apd-gauntlet validate <run-dir> [--strict] [--schema-only] [--json]
apd-gauntlet init-run <run-id> --inputs <path> --domain pbm
apd-gauntlet build-domain-skill <domain-name> [--out .claude/skills/apd-domain/]
apd-gauntlet summarize <run-dir>
apd-gauntlet lint-agents [--agent-dir .claude/agents/]
apd-gauntlet check-ids <yaml-file>
apd-gauntlet refresh-mitre                          # regenerate cached crosswalk
apd-gauntlet validate-domain <domain-name>          # structural check on a pack
```

### 6.2 The `validate` command — three passes

**Pass 1: Per-record JSON Schema validation** (using `jsonschema`).

- Reads every YAML file under the run directory.
- Validates each record against its schema.
- Collects violations per record with JSON Pointer paths.

**Pass 2: Custom semantic lints** (cannot be expressed declaratively in JSON Schema).

- `evidence[].excerpt` token count ≤ 25 (whitespace-split).
- ID matches the deterministic derivation: first 8 hex characters of SHA-256 over `title + "|" + first_evidence_locator`. (Capability IDs use the same derivation with the `-cap-` infix per `apd-finding-schema`.)
- Capability `maturity ≥ implemented` ⇒ at least one `evidence[].artifact` is not in the run's tech_plan set (resolved by parsing the intake artifact index).
- `mitre_attack[].rationale` does not contain unjustified hedge words (`could`, `may`, `potentially`) — heuristic warning, not error.
- `recommendation.posture: required` ⇒ severity ∈ {critical, high} — warning, not error (legitimate exceptions exist).

**Pass 3: Cross-file resolution.**

- `cross_references[]` IDs exist in lower-tier files.
- `merged_from[]` IDs exist in pre-synthesis files.
- `evidence[].artifact` appears in the intake artifact index.
- `contradictions[]` reference real finding and capability IDs.

### 6.3 Exit codes & output

- Exit 0: clean.
- Exit 1: schema or semantic violations.
- Exit 2: internal validator failure (file not found, parse error).
- Default output: human-readable summary with file:line citations.
- `--json`: machine-parseable for CI.
- `--strict`: warnings become errors.

### 6.4 Test coverage targets

- Line coverage ≥ 85% across `tools/apd_gauntlet/`.
- Line coverage 100% on `validate.py`.
- Every error class has at least one positive and one negative fixture.
- Determinism test: `check-ids` round-trips correctly for 100 generated titles.

## 7. Agent refactor and contract fixes

The current agent and skill content carries inconsistencies that v1 resolves. Each fix is small but load-bearing.

### 7.1 Schema-driven fixes

| Issue | Fix | Files touched |
|---|---|---|
| `rejected-records.yaml` absent from synthesizer outputs list | Add to the official "Outputs" list | `apd-synthesizer.md` |
| `disposition: strength` underspecified (no advisory-report section, severity nonsensical) | **Drop `strength` from the disposition enum.** Schema already notes capabilities are the right vehicle for affirmations. | `apd-finding-schema/SKILL.md`, `finding.schema.json`, finding template |
| "Skip Distributed" scope hint produces missing tier-2 file for tier-3 readers | Orchestrator emits stub `<goal>.findings.yaml` and `<goal>.capabilities.yaml` containing empty lists plus a `_meta: { skipped: true, reason: <hint>, emitted_by: orchestrator }` header. Tier 3 reads normally; synthesizer records the skip in run metadata. | `apd-orchestrator.md` |
| ATT&CK mitigation→technique crosswalk source unnamed | Cite MITRE STIX bundle URL + ship cached crosswalk at `tools/apd_gauntlet/data/mitre-mitigations.json`. Add `refresh-mitre` subcommand. | `apd-control-mappings/SKILL.md`, validator |
| `gap` vs `risk` differentiation thin | Add three worked examples per disposition + decision flowchart text | `apd-finding-schema/SKILL.md` |
| "Validator" referent ambiguous | Make explicit: **orchestrator** invokes `apd-gauntlet validate` after each tier; **synthesizer's Step 1** runs validation again over the full set including merged records. | `apd-orchestrator.md`, `apd-synthesizer.md` |
| No `schema_version` on records | Add `schema_version: 1` (integer) as required top-level field on finding and capability schemas. Add a YAML frontmatter block to `context-brief.md` and to `advisory-report.md` carrying `framework_version`, `domain_pack: { name, version }`, and `run_id`. (The brief and report remain primarily markdown; the frontmatter is the machine-readable header.) | All schemas, templates, intake/synthesizer agents |

### 7.2 Domain-pack refactor

For each specialist agent file (`apd-<goal>.md`):

- "Common finding patterns" section is **removed**; content moves to `domains/pbm/common-patterns/<goal>.md`.
- "Common capability patterns" section is **removed**; content also moves.
- New "Required reading" entry added: `.claude/skills/apd-domain/SKILL.md` — for active-domain severity rubric, consequential actions, and pattern library.

For `apd-evidence-discipline/SKILL.md`:

- The impact-to-PBM severity rubric is **removed**; content moves to `domains/pbm/severity-rubric.md`.
- The five rules + severity-calibration discipline + maturity discipline + self-check **stay** (all domain-neutral).
- Add: "Cite the matching clause from the active domain's severity-rubric.md in your finding's `detail`."

For `apd-orchestrator.md`:

- New Phase 0 step: `apd-gauntlet build-domain-skill <name>` materializes `apd-domain/SKILL.md` before intake.
- New step at end of Phase 2, 3, 4: `apd-gauntlet validate <run-dir>` over tier outputs before proceeding.
- Explicit skip-specialist handling (emit stub file).
- Records active domain pack version in run metadata.

For `apd-synthesizer.md`:

- Step 1 explicitly invokes the validator (or LLM fallback if unavailable).
- `rejected-records.yaml` added to canonical outputs list.
- Advisory report header records `framework_version` and `domain_pack: { name, version }`.

For `apd-finding-schema/SKILL.md`:

- Points at `schemas/finding.schema.json` as the canonical contract; the skill is its documentation.
- Drops `disposition: strength` from documented enum.
- Adds `schema_version` field documentation.
- Adds expanded `gap`/`risk`/`uncertainty`/`blocked` decision examples.

## 8. Domain pack mechanism

### 8.1 Pack structure

```
domains/<name>/
├── domain.yaml                     # metadata
├── severity-rubric.md              # critical/high/medium/low/informational thresholds for this domain
├── consequential-actions.md        # what counts as an audit-worthy action (for Non-Repudiation)
├── immutability-classes.md         # what data classes must not change (for Immutability)
├── data-taxonomy.md                # field-level data classification with regulatory citations
└── common-patterns/
    ├── confidentiality.md          # finding + capability pattern templates
    ├── integrity.md
    ├── availability.md
    ├── distributed.md
    ├── resilient.md
    ├── ephemeral.md
    ├── authenticity.md
    ├── non-repudiation.md
    └── immutability.md
```

### 8.2 `domain.yaml`

```yaml
name: pbm
display_name: "Pharmacy Benefit Management"
version: 1.0.0
framework_compat: ">=1.0.0,<2.0.0"
description: "PBM-specialized severity rubric and pattern library. Anchored to HIPAA breach-notification thresholds, CMS Part D submission integrity, URAC accreditation requirements, and SOC 2."
includes:
  - severity-rubric.md
  - consequential-actions.md
  - immutability-classes.md
  - data-taxonomy.md
  - common-patterns/confidentiality.md
  - common-patterns/integrity.md
  - common-patterns/availability.md
  - common-patterns/distributed.md
  - common-patterns/resilient.md
  - common-patterns/ephemeral.md
  - common-patterns/authenticity.md
  - common-patterns/non-repudiation.md
  - common-patterns/immutability.md
regulatory_anchors:
  - HIPAA
  - "CMS Part D"
  - URAC
  - "SOC 2"
```

### 8.3 The build step

`apd-gauntlet build-domain-skill pbm` produces `.claude/skills/apd-domain/SKILL.md`:

1. Validate `domain.yaml` against `domain.schema.json`.
2. Verify all `includes` files exist.
3. Check `framework_compat` against current framework version; refuse if outside range.
4. Concatenate file contents with section headers reflecting the source path.
5. Write generated skill with frontmatter:

   ```yaml
   ---
   name: apd-domain
   description: Active domain pack content — severity rubric, consequential actions, common patterns. Generated from a domain pack at build time; do not edit by hand.
   metadata:
     pack: pbm
     pack_version: 1.0.0
     framework_version: 1.0.0
     generated: <ISO-8601 timestamp>
   ---
   ```

The orchestrator runs this build in Phase 0. The intake brief records which pack was active.

### 8.4 Adding a new domain

Documented in `docs/adapting-to-other-domains.md`:

1. `cp -r domains/pbm domains/<new>`
2. Edit `domain.yaml` (name, version, description, regulatory_anchors).
3. Rewrite the four narrative files (rubric, consequential-actions, immutability-classes, data-taxonomy) for the new domain.
4. Rewrite each `common-patterns/<goal>.md` with domain-relevant examples.
5. `apd-gauntlet validate-domain <new>` runs structural and link checks.
6. PR with the pack plus a sample run in `examples/` that uses it.

## 9. Sample run (`examples/apd-20260601-claim-event-bus/`)

A synthetic PBM tech plan tight enough to exercise every interesting framework feature without leaking real PHI or proprietary architecture.

### 9.1 Inputs

| File | Content |
|---|---|
| `inputs/tech_plan.md` | Kafka-based claim event bus design: PHI in payloads, broker encryption only, multi-region active-passive, KMS hierarchy described but rotation not specified, audit log to mutable RDS table |
| `inputs/claim-events.proto` | Protobuf schema declaring `member_id`, `drug_ndc`, `prescriber_npi`, `pharmacy_id`, claim status fields |
| `inputs/threat-model.md` | Abbreviated STRIDE on the change |
| `inputs/adr-001-cap-positioning.md` | Explains active-passive choice and rationale |
| `inputs/iac/kafka.tf` | Terraform stub for the Kafka cluster (gives some capabilities `implemented` maturity) |

### 9.2 Expected outputs

Author-curated (not LLM-generated). Frozen reference set under `expected/`. Realistic counts:

- ~15-20 findings across all severities; ~5 blocked-on-evidence
- ~10 capabilities, most at `designed`, two at `implemented` (via Terraform evidence)
- 1-2 contradictions (e.g. capability claims at-rest encryption; finding disputes Kafka audit-log scope)
- 2-3 severity disagreements at synthesis

Must exercise: `disposition: blocked` with populated `prerequisite_evidence`, `cross_references` (tier 2 citing tier 1), synthesizer `merge` (e.g. Confidentiality + Non-Repudiation on Kafka audit topic), `link` (Availability + Distributed on single-region SLO), contradictions, passing-bar ATT&CK rationales.

### 9.3 CI integration

`tests/test_examples.py` runs `apd-gauntlet validate examples/apd-20260601-claim-event-bus/expected/`. The test fails if schemas drift from the canonical example, providing a regression guard.

## 10. Plugin packaging

### 10.1 Manifest

```json
{
  "name": "apd-gauntlet",
  "version": "1.0.0",
  "description": "APD security architecture review framework — 9 specialist agents plus intake, orchestrator, and synthesizer.",
  "author": "<author>",
  "license": "Apache-2.0",
  "repository": "https://github.com/<owner>/apd-gauntlet",
  "agents": "./.claude/agents/",
  "skills": "./.claude/skills/"
}
```

The `<author>` and `<owner>` placeholders are intentional — filled at M7 once GitHub org and author identity are confirmed.

### 10.2 Known-unstable surface

The Claude Code plugin manifest format is moving. M7 starts with a `context7` docs check to confirm current field names. If per-agent enumeration is required, a `Makefile` target generates the list from `.claude/agents/`. Plugin publishing to a marketplace is stubbed for v1.0; will be wired in v1.1 once the marketplace process is documented.

## 11. CI and quality gates (`.github/workflows/`)

| Workflow | Trigger | Steps |
|---|---|---|
| `validate.yml` | PR + push to main | (1) `apd-gauntlet validate examples/apd-20260601-claim-event-bus/expected/`; (2) meta-validate all `schemas/*.schema.json` against JSON Schema draft 2020-12 meta-schema; (3) validate `domains/pbm/domain.yaml` against `domain.schema.json` |
| `python-tests.yml` | PR + push to main | `pytest --cov`; `ruff check tools/`; `mypy tools/`. Fail if coverage < 85% on `tools/apd_gauntlet/` |
| `markdown-lint.yml` | PR | `markdownlint` on `docs/`, `.claude/`, `domains/`. Custom: verify every agent frontmatter parses; verify "Required reading" paths resolve. |
| `release.yml` | Tag push (`v*`) | Runs all of the above; builds Python package; publishes to PyPI; creates GitHub Release with auto-generated notes from `CHANGELOG.md`. Plugin marketplace publish stubbed. |

## 12. Documentation set

| File | Purpose | Approx size |
|---|---|---|
| `README.md` | What it is, install, 60-second quickstart, links to docs | ~5 KB |
| `docs/architecture.md` | How the gauntlet works under the hood (current README's lifecycle + discipline content lands here) | ~15 KB |
| `docs/running-the-gauntlet.md` | Operator guide: invoke, interpret outputs, scope hints, troubleshooting | ~10 KB |
| `docs/adapting-to-other-domains.md` | Domain pack authoring guide (codifies §8) | ~8 KB |
| `docs/extending-agents.md` | For contributors: how to modify agents/skills | ~5 KB |
| `docs/schema-evolution.md` | Versioning + breaking-change policy (codifies §13) | ~3 KB |
| `docs/adrs/0001…0006.md` | Architecture decision records | ~1-2 KB each |
| `CONTRIBUTING.md` | PR conventions, DCO sign-off, testing requirements | ~3 KB |
| `CHANGELOG.md` | Keep-a-Changelog format, starts with v1.0.0 entry | grows |
| `CODE_OF_CONDUCT.md` | Contributor Covenant 2.1, unchanged stock text | ~3 KB |

### ADRs to author

1. **Three-tier structure** — why Trustworthiness → Scalability → Auditability ordering is load-bearing.
2. **Block-on-ambiguity as default** — why this discipline anchors the framework's credibility.
3. **Pluggable domain packs** — decision and mechanism from this design.
4. **JSON Schema as canonical validation** — decision and rationale (chosen over pure LLM).
5. **Deterministic finding IDs** — SHA8 derivation; what it enables and breaks.
6. **LLM-driven clustering in the synthesizer** — why merge/link/separate is not codified as a script.

## 13. Versioning policy

Three independent semvers:

| Thing | Where it lives | Bump when |
|---|---|---|
| Framework version | `pyproject.toml`, git tags, `framework_version` field on context brief and advisory report | `.claude/` content or schemas change in a way users notice |
| Schema version | `schema_version` integer field on each finding and capability record | Schema gets a breaking change (rename, new required field, tightened constraint) |
| Domain pack version | `version` in each pack's `domain.yaml` | Rubric thresholds, consequential-action surface, or common patterns shift |

**Schema breaking-change semantics** (in `docs/schema-evolution.md`):

- Renaming a required field → major bump.
- Adding a required field → major bump.
- Adding an optional field → minor bump.
- Tightening a constraint (e.g. shorter `maxLength`) → minor bump.
- Removing a field → major bump.
- Loosening a constraint → patch bump.

**Domain pack compatibility:** each pack declares `framework_compat` as a semver range. The validator refuses to build the skill if the active framework is outside that range.

## 14. Implementation phasing

Seven milestones, dependency-ordered. Estimates assume single-engineer focused work.

| # | Milestone | Estimate | Depends on |
|---|---|---|---|
| **M1** | Scaffolding: git init, LICENSE, README skeleton, layout established, file moves from current flat state, `mnt/` deletion, `pyproject.toml`, `.gitignore` | ~2 days | — |
| **M2** | Schemas: 8 JSON Schema files authored, positive + negative fixtures, meta-validation against draft 2020-12 | ~3 days | M1 |
| **M3** | Validator: Python CLI package, three-pass validation, pytest suite at 85%+ coverage, MITRE crosswalk cached | ~4 days | M2 |
| **M4** | Agent refactor: apply all contract fixes from §7 (drop `strength`, add `schema_version`, fix `rejected-records`, skip-specialist stubs, validator integration in orchestrator and synthesizer); extract PBM content out of agents and skills | ~3 days | M2 |
| **M5** | Domain pack: assemble `domains/pbm/`, write `apd-domain/SKILL.md` build logic, end-to-end validator pass | ~2 days | M3, M4 |
| **M6** | Sample run: author synthetic inputs and curated expected outputs, wire into integration test | ~3 days | M5 |
| **M7** | Plugin and CI: `plugin.json` (after current spec docs check), four GitHub Actions workflows, six ADRs, all doc pages, README rewrite, `CHANGELOG.md`, tag v1.0.0, PyPI publish | ~4 days | M6 |

**Total**: ~3-4 weeks single-engineer. M2 and the early steps of M4 can overlap once schemas stabilize.

## 15. Risk register

| # | Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| 1 | Claude Code plugin manifest spec changes between design and M7 | Medium | Low (manifest is small, late-stage) | M7 first step is a `context7` docs check; manifest authoring is last |
| 2 | Sample-run authoring exceeds 3-day budget | High | Medium | Accept "good enough" first draft at M6; refine after v1.0 ships; treat as the longest unbounded task |
| 3 | Domain pack abstraction over-engineered for a single pack | Medium | Medium | Defer second pack to v1.1; design but don't over-invest; v1.1's `domains/saas/` is the real test |
| 4 | Validator scope creep ("lint everything") | High | Medium | Cap v1 at the lints specified in §6; treat anything more as v1.1 RFC |
| 5 | MITRE / NIST data freshness | Low | Low | `refresh-mitre` subcommand; quarterly cron CI job post-v1.0; version-pin cached snapshot |
| 6 | Cross-file validation order (validator needs intake brief before checking artifact references) | Low | Low | Validator parses intake first as a precondition; documented in CLI help |
| 7 | Agent refactor breaks subtle in-prompt assumptions | Medium | High | The sample run exercises the full pipeline; CI catches drift; manual review of every agent diff before M4 lands |

## 16. Open questions deferred to implementation

- Exact `pyproject.toml` package name on PyPI (`apd-gauntlet` likely free; will confirm at M3).
- Whether to ship the MITRE crosswalk as JSON or STIX 2.1 (likely JSON for size and parse speed; will confirm at M3).
- Plugin marketplace process (deferred to v1.1 per §10.2).
- Whether `apd-gauntlet init-run` should support copying inputs into the run directory or only scaffolding empty subdirs (likely scaffold-only; user `cp` their own artifacts).

## 17. Out of scope (v1)

Explicitly not addressed in v1.0 and not implied to come in any specific later version:

- A web UI or report renderer beyond markdown.
- LLM-as-a-service abstractions (Claude Code is the only target).
- Multi-language SDK for the validator (Python only).
- Real-time / streaming gauntlet runs.
- Persistent storage of run history beyond filesystem.
- User authentication, authorization, or multi-tenant concerns.
- Integration with ticketing systems (Jira, Linear) for finding follow-up.
- Automated remediation suggestions beyond the agent-emitted `recommendation` field.
