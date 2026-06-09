# Changelog

All notable changes to this project will be documented in this file. Format based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versioning per [SemVer](https://semver.org/).

## [Unreleased]

## v1.7.0 — 2026-06-09

### Added

- **OWASP MASVS / MASWE as first-class mobile taxonomies** — the `mobile-applications` pack declares `taxonomies: [masvs, maswe]` in `domain.yaml`, auto-seeded into a run's `taxonomies:` at `init-run`. Specialists emit `masvs` control IDs (`MASVS-<CATEGORY>-<n>`, on findings **and** capabilities) and `maswe` weakness IDs (`MASWE-####`, findings-only) in `control_mappings`, feeding two new gated synthesis rollups (`masvs-coverage.yaml`, `maswe-coverage.yaml` + their single-file schemas) and two new Coverage sub-tabs in the HTML report. New `apd-gauntlet refresh-mas` verb + bundled `masvs.json` (v2.1.0, 24 controls) and `maswe.json` (Beta, pinned per-refresh to an upstream commit). `data.meta.active_taxonomies` now lifts the run's taxonomy scope; `audit-report` gains `id_coverage_masvs` / `id_coverage_maswe` structural checks and `coverage_rollups_nonempty` extends to the MAS rollups.
- **Optional `taxonomies` field on `domain.yaml`** — any pack can declare default taxonomies that `init-run` unions into the run config (pack -> run auto-seed). Packs that omit the field are unaffected.
- **ADR 0014** — OWASP MAS (MASVS + MASWE) as mobile finding/capability taxonomies.
- HTML report: a new "Start here" reading-guide tab (`✦`, leftmost) that orients first-time readers with an orientation map, a vocabulary glossary, a reading workflow, and per-role focus paths, reading the run's live data for contextual guidance. Overview remains the default tab.
- **Threat-model report scene** — a dedicated report tab (after Coverage, before Attack paths) detailing the threat model: STRIDE×asset matrix, entries table, coverage-by-surface, an interactive trust-boundary surface map, and a supplied-vs-authored comparator. Gracefully omitted when no threat model exists (no user-supplied TM and none authored). Renders in the existing report design language (shared interactive `GraphView`, `apd-matrix`/`coverage-bar`/`contradiction` classes).
- **HTML report — Attack-paths "Enumerated paths" link to findings.** Each enumerated path whose edges traverse a finding now shows a `⚑ N finding(s)` indicator in its header (titled with the finding ids). Clicking a finding/capability id pill copies the id to the clipboard (with a toast); clicking the red "finding" chip immediately left of the id opens that finding in the Findings view (the same `onOpenFinding` navigation Overview/Annexes already use).

### Changed

- **Threat-model-evaluator (`tmeval-*`) findings are now first-class downstream** (data-model audit F1). The decomposed pipeline previously unioned only `apath-*` tier-4 findings into the rollups/metrics/report, silently dropping `tmeval-*` from NIST/ATT&CK/9×N coverage, the severity distribution, and the report findings list (they surfaced only as `finding_id` references and in the threat-model scene). `rollup._load_deduped` now unions both `apath-*` and `tmeval-*`; `RunArtifacts` gains a `threat_model_findings` field (loaded from `40-threat-model/threat-model.findings.yaml`); the report `findings_array`, 9×N matrix, and taxonomy sweep include them; and `audit-report`'s `id_coverage_findings` widens to `deduped ∪ apath ∪ tmeval`. Report finding counts grow accordingly (the example golden moved from 90 → 93 findings).
- **Completeness gate distinguishes structural from editorial failures** (data-model audit F3). The agent receipt gains an optional `report_audit: {structural_failed, editorial_failed}` block that the `audit-report` worker lifts from the CLI's per-class counts; the workflow's synthesis-audit loop now blocks on **structural** completeness only (or an unverifiable report) and surfaces residual **editorial** completeness gaps non-blocking after the remediation cap (matching the LLM semantic-residual policy), rather than hard-blocking on any audit failure.
- **Report graphs are now interactive (Cytoscape.js).** The Attack-paths asset graph and the Threat-model surface map render with Cytoscape (dagre/fcose layouts) instead of static Mermaid — pan/zoom/drag, hover tooltips with provenance, and click-to-highlight-paths with two-way Attack-paths list↔graph cross-highlight. Mermaid was removed from the bundle (smaller `app.js`); the report stays self-contained/offline.
- **`runs/` is now fully gitignored and no longer ships pre-built runs.** The three shipped example runs (crAPI, authentik, caldera) were removed from version control and `runs/` (the gauntlet's output directory) is ignored in its entirety, so a tool user cannot accidentally commit a sensitive security review. The single canonical fixture is now the synthetic `examples/apd-20260601-claim-event-bus/expected/` run; all tests, the report golden, and the dev-template demo data (`report-template/data.js`) were repointed to it, and the README quickstart now validates the example. The report transforms' divergent-shape regression coverage is preserved by the in-memory synthetic-shape unit tests in `test_transform_new_shapes.py` (no real-run fixtures required).
- **Specialist agent guardrails hardened** against recurring output friction seen in multi-pack runs. The `apd-finding-schema` skill now stresses the 200-character `title` cap, mandatory YAML-quoting of colon/em-dash/leading-special scalars (an unquoted colon also aborts canonicalization), and writing findings only to the canonical tier path (no invented nested directories). The `apd-control-mappings` skill now stresses that every taxonomy mapping lives under `control_mappings` (never at the finding root) with the MITRE ATLAS key spelled `atlas` (not `mitre_atlas`), and that only concrete CWEs that resolve in the bundled catalog may be cited (no pillar/category CWEs such as CWE-320).
- **Documentation: foreground-execution requirement made consistent + preflight checklist added.** `running-the-gauntlet.md` gains a "Preflight: confirm scaffolding is in place" section and lists `plan-run` in the CLI reference; its Step 2 foreground statement is now the canonical source that the README, `architecture.md`, `extending-agents.md`, the workflow `meta.description`, and the `apd-orchestrator` shim all point to (run the gauntlet in-session — a background or headless launch can interrupt the subagent dispatches and leave an empty run directory). The operator install path now recommends an isolated install (venv / `pipx`), mirroring `CONTRIBUTING.md`. Docs and descriptions only — no runtime, CLI, schema, or report-template change.

### Fixed

- **Attack-path analysis wires declared crown jewels to inventory assets** (#84). Run-config `crown_jewels[]` are abstract pattern tokens (`pii_profile_store`, `tool_execution_capability`); `attack_path/build.py` previously realized a jewel only when an asset's `data_classifications` contained a naive `_store`-stripped token or an asset name case-insensitively equalled the pattern, so real inventories left every declared jewel an orphan sink and the deterministic floor enumerated zero paths. `_add_crown_jewels` now also matches a jewel's classification-alias tokens (the full pattern plus its generic-suffix-stripped head, exact-matched against the controlled `data_classifications` vocabulary) and honors an optional per-asset `realizes_crown_jewels: [pattern]` inventory field; any declared jewel that still wires to zero inbound edges is surfaced as a non-fatal `orphan_crown_jewels` build diagnostic rather than silently producing no paths.
- **`asset-graph.schema.json` accepts `threat_model_inferred` edge provenance** (#85). The always-on authored-baseline threat-model path emits `provenance.source: "threat_model_inferred"`, which was absent from the schema's `source` enum and failed validation for every such edge.
- **`validate` no longer rejects tier-4 analyzers' own derived evidence** (#86). The attack-path analyzer and threat-model evaluator legitimately cite their synthesis outputs (`40-synthesis/asset-graph.yaml`, `attack-paths.yaml`, `defense-graph.yaml`, `deduped-findings.yaml`, `deduped-capabilities.yaml`) as evidence; these are now auto-exempted from the "not in intake brief" check via `ANALYZER_DERIVED_ARTIFACTS`, the way `code-evidence-index.yaml` already is. Genuinely unknown artifacts still fail.
- **`canonicalize` is resilient to a single unparseable file.** A lone malformed YAML record (e.g. an unquoted colon-bearing scalar a specialist emitted) raised `yaml.YAMLError` and aborted the entire canonicalize pass, so no file was canonicalized and the tier gate could not run. Per-file parse failures are now caught, skipped, collected on `CanonicalizeResult.parse_errors`, and reported by the CLI, while the remaining files canonicalize normally.
- **Rollup last-resort fallback now writes `metrics.yaml`** (data-model audit F2). When the deterministic `rollup` failed twice, the synthesizer last-resort was told to write "ONLY" `nist-coverage`/`attack-exposure`/`apd-coverage-matrix` — but `load_run` requires `metrics.yaml`, so `build-report` would `MissingArtifactError` and the completeness gate would throw, making the deepest fallback unable to ship any report. The last-resort prompt now also (re)writes `metrics.yaml` and pulls the tier-4 (`apath-*`/`tmeval-*`) findings.
- **`apply-clusters` no longer folds tier-4 findings into `deduped-findings.yaml`** (data-model audit F4). It ran with `include_attack_path=True` despite executing *before* attack-path/threat-model analysis; on a corruption-recovery re-run where a stale `attack-path.findings.yaml`/`threat-model.findings.yaml` already existed, `apath-*`/`tmeval-*` could be folded into the deduped corpus and double-rendered in the report. It now loads the corpus with `include_attack_path=False`; the tier-4 findings are unioned downstream where they belong.
- **Single shared severity normalizer** (data-model audit F6). The schema-token (`informational`) → template-token (`info`) mapping lived duplicated in `synthesis/metrics.py` and `report/transform.py`; it now lives once in `apd_gauntlet.severity` and both layers import it, so they can never drift.
- **Workflow `outputs` advisory label fixed** (data-model audit F5) — the `rollup` step's idempotency-guard label now lists `metrics.yaml` (which `build_rollups` writes).
- **Workflow no longer passes `--framework-version undefined`** — the `apd-gauntlet.js` setup phase built the `build-domain-skill` flag by blind string concatenation (`'--framework-version ' + args.framework_version`); when a run's `.apd-run.yaml` omitted `framework_version`, JS stringified `undefined` into the literal arg `--framework-version undefined`, which crashed `build_domain_skill` at `int('undefined')` in `_version_in_range`. The flag is now emitted only when `args.framework_version` is present; otherwise it is omitted and the CLI's own `default=__version__` applies.
- **`scaffold_run` stamps the live framework version** — `init-run`/`scaffold_run` hardcoded `framework_version: 1.1.0` in every generated `.apd-run.yaml`, recording a stale version and risking a spurious `framework_compat` failure in `build_domain_skill` if a pack floor ever rose above `1.1.0`. It now writes the live package `__version__`.

## v1.6.0 — 2026-06-03

### Added

- **`agentic-ai` domain pack** — security-architecture calibration for autonomous LLM-agent systems (tool-use agents, multi-agent topologies, self-improving loops), grounded in the OWASP LLM Top 10, MITRE ATLAS, and CSA MAESTRO.
- **`mobile-applications` domain pack** — OWASP MASVS/MASWE/MASTG + MAS Checklist + NIST SP 800-163r1 app-vetting, calibrated for the adversary-controlled-client surface (on-device storage, keystore/TEE, pinning, WebView/JS bridges, deep-link/IPC, in-process SDKs, reverse-engineering resilience, hardware attestation), anchored to the MITRE ATT&CK Mobile matrix.
- **MITRE ATLAS as a first-class finding taxonomy** — declare `mitre_atlas` in `.apd-run.yaml`; specialists emit `atlas` technique IDs (`AML.T####[.###]`) in structured finding fields, feeding the new `atlas-coverage` synthesis rollup and the report's taxonomy tooltips. New `apd-gauntlet refresh-atlas` verb + bundled `atlas-techniques.json`.
- **CSA MAESTRO as a recognized threat-model methodology** — `methodology_hint: maestro` routes supplied threat models through the free-form envelope with an L1–L7 → APD-goal mapping in the `apd-threat-model-methodologies` skill.
- **Per-goal domain-skill sidecars** — `build-domain-skill` emits `.claude/skills/apd-domain/by-goal/<goal>.md` (calibration files + merged surfaces + only that goal's common-patterns, with a `pruned` manifest) so each lens agent loads a goal-scoped slice; the full cross-goal `SKILL.md` is retained for intake / attack-path / domain-auditor. `--full-only` suppresses sidecars.
- **Report completeness gate** (#71) — `audit-report` now enforces 8 completeness checks on the built `data.js`, each classified `klass: structural` or `klass: editorial`. Structural checks (`attack_paths_present`, `d3fend_overlay_present`, `apd_matrix_nonempty`, `coverage_rollups_nonempty`, `taxonomy_titles_resolve`, `section_errors_empty`) and editorial checks (`exec_summary_present`, `editorial_sections_present`) each exempt legitimately-empty states. The workflow's synthesis-audit phase blocks a run (throws) when a structural failure is unresolved after the two-attempt remediation cap — a degraded HTML report (placeholder exec summary, mismatched counts, empty attack-paths or D3FEND) can no longer ship silently. `report-audit.yaml` gains a per-check `klass` field; `audit-report` prints `structural_failed`/`editorial_failed` counts.
- **`refresh-cwe` `<Category>` projection** (#71) — `refresh-cwe` now also projects CWE `<Category>` entries (e.g. CWE-840 "Business Logic Errors") into the bundled reference data so cited categories resolve in report tooltips and survive a refresh.
- **ADR 0011** — Report completeness gate — block on degraded HTML reports.
- **ADR 0012** — MITRE ATLAS as a first-class finding taxonomy.

### Changed

- ATT&CK Mobile technique titles and mitigation→technique crosswalk merged additively into the bundled catalogs so Mobile-pack runs render names rather than bare IDs.
- HTML report now renders `data.meta` diagnostics and informational-severity findings that the template previously dropped.

### Fixed

- Golden-run framework defects (F1–F5): new `apd-gauntlet canonicalize`, non-vacuous record/ID validators, loader capability-id guard, deduped-union resolver, and attack-path crown-jewel↔asset name-collision handling.

## v1.5.1 — 2026-05-27

### Added

- **`api-security` domain pack** under `domains/api-security/` — 14 files (878 lines) anchored to OWASP API Top 10 (2023), PCI-DSS 4.0, GDPR, NIST 800-63B, SOC 2. Ships 8 crown jewels and 9 attacker positions covering authenticated/unauthenticated/compromised attacker scenarios common to API-style production systems. Severity rubric calibrates to API1-API10 categories + breach-notification thresholds.
- **Canonical example fixture run** at `runs/apd-20260527-crapi-owasp-api-top10/` — full APD gauntlet output against OWASP crAPI v1.1.5 (Apache-2.0, intentionally vulnerable multi-service automotive B2C demo). 63 deduped findings + 22 capabilities + complete 40-synthesis output including `report-data.yaml`. Used by Phase D HTML report integration tests as the golden fixture.

### Changed

- Phase D tests now reference `example_run` fixture (was `legacy_example_run`); pointed at the crAPI run.
- `report-template/data.js` (dev template demo data) regenerated from the crAPI run.
- `tests/fixtures/report-html/crapi-golden-data.js` replaces `legacy_example-golden-data.js` as the golden-output regression check.

### Known limitations

- 5 transform tests skip cleanly because crAPI's synthesizer-emitted YAML files use shape variants (`techniques:` dict vs `technique:` list in attack-exposure.yaml; goal-keyed vs component-keyed apd-coverage-matrix; missing family_summary in nist-coverage) that the v1.5.0 transforms don't yet normalize. Tracked as a polish item — transforms should be made tolerant of both shapes in a follow-up.

## v1.5.0 — 2026-05-27

### Added

- **Interactive HTML advisory report** at `runs/<run_id>/40-synthesis/report-html/`.
  Auto-generated by the synthesizer's trailing `apd-gauntlet build-report` step.
  Self-contained, offline-openable, no network or Node toolchain on the
  consumer side. Six tabs: Overview, Findings, Capabilities, Coverage,
  Attack paths (v1.4 enumeration + D3FEND overlay), Annexes.
- **`apd-gauntlet build-report <run_dir>`** CLI verb. Idempotent;
  re-runnable without re-running the gauntlet itself.
- **`40-synthesis/report-data.yaml`** — new optional synthesizer emission
  carrying the editorial prose blocks the HTML report cannot derive
  algorithmically (exec_summary, headline_findings, strengths caveats,
  next_steps, posture_summary). Schema-validated like the other 40-synthesis
  files; cross-file validator checks that ids resolve.

### Changed

- `apd-synthesizer` agent now emits `report-data.yaml` and invokes
  `apd-gauntlet build-report` at the end of every run.
- `tools/apd_gauntlet/data/` gains a precompiled React 18 + Mermaid bundle
  under `report-template/`. Rebuilt by contributors via
  `python tools/build_report_template.py` (Node 20+ + esbuild required).
- CI runs `tools/check_report_template_freshness.py` to ensure the
  precompiled bundle matches the JSX source under `report-template/`.

### Compatibility

This release is fully additive. v1.4 outputs (markdown, all existing YAMLs,
attack-paths, D3FEND coverage) are byte-identical. Runs without
`report-data.yaml` produce a degraded-but-complete HTML report.

## [1.4.0] - 2026-05-26

### Added

- **`apd-attack-path-analyzer` tier-4 agent** — activation-gated BloodHound-style bounded enumeration over a partial provenance-and-confidence-aware graph from declared attacker positions to declared crown jewels. Findings use `agent: attack_path_analyzer` and id prefix `apath-`.
- **Asset graph, attack-paths, defense-graph schemas** capturing nodes, edges, paths, and the D3FEND defensive overlay on bottleneck edges. Each edge carries `provenance.source` and `confidence`; the analyzer never invents nodes or edges.
- **Asset inventory** machine-readable artifact emitted by intake at `00-context/asset-inventory.yaml` when crown jewels are declared.
- **D3FEND defensive overlay** on bottleneck edges with capability-backing-vs-net-new partitioning. The D3FEND-must-counter-ATT&CK discipline rule (per `tools/apd_gauntlet/data/d3fend.json`) prevents name-similarity mappings.
- **Inline Mermaid attack-path diagrams** in the advisory report (≤50 nodes per diagram; partitioned by `attacker_position` for larger graphs).
- **Domain pack additions** for `crown_jewels[]`, `attacker_positions[]`, `default_trust_boundaries[]`. PBM domain pack ships 3 crown jewels, 5 attacker positions, and 3 default trust boundaries.
- **Run-config additions** for `crown_jewels[]` / `attacker_positions[]` overrides plus the `attack_path_analysis` tuning block (`max_hop`, `max_paths_per_pair`, `bottleneck_threshold`).
- **CLI subcommand `apd-gauntlet analyze-attack-paths <run_dir>`** for deterministic, headless graph build + path enumeration + D3FEND overlay + finding emission.
- **`apd-attack-path-discipline` skill** codifying never-invent rules for nodes and edges, confidence-floors-severity rule, bounded-enumeration discipline, and the block-on-missing-crown-jewels rule.
- **New schemas**: `asset-inventory.schema.json`, `asset-graph.schema.json`, `attack-path.schema.json`, `defense-graph.schema.json`.
- **ADR 0010** — Attack-path analysis on partial graphs.
- **`docs/attack-path-analysis.md`** — operator guide for declaring crown jewels and attacker positions, tuning enumeration bounds, reading the outputs.
- **Bundled example** `examples/apd-20260601-claim-event-bus/` exercises the full v1.4 pipeline end-to-end (3 attacker positions × 2 crown jewels yields 75 paths, 24 bottleneck edges).

### Changed

- `finding.schema.json` — `agent` enum gains `attack_path_analyzer`; `id` / `cross_references` / `merged_from` patterns accept `apath-[0-9a-f]{8}`.
- `run-config.schema.json` — new optional `crown_jewels`, `attacker_positions`, `attack_path_analysis` blocks (all additive).
- `domain.schema.json` — new optional `crown_jewels`, `attacker_positions`, `default_trust_boundaries` arrays (all additive).
- `defense-graph.schema.json` — `capability_ids` pattern corrected to accept the prefix-cap form (e.g., `auth-cap-7c2a4f91`) per `capability.schema.json`.
- `asset-graph.schema.json` — `provenance.source` enum extended to include `asset_inventory`.
- `apd-intake` — gains `00-context/asset-inventory.yaml` emission when crown jewels are declared.
- `apd-orchestrator` — topology now describes 16 agents; Phase 5.6 dispatches the analyzer.
- `apd-synthesizer` — 9×N coverage matrix scan now includes `tmeval-` and `apath-` findings from tier-4 sources.
- Validator picks up `asset-inventory.yaml`, `asset-graph.yaml`, `attack-paths.yaml`, `defense-graph.yaml`, and `attack-path.findings.yaml`; new cross-file pass checks edge endpoints reference real `nodes[].node_id`, real findings, and real capabilities.
- Finding/capability YAML root keys standardized on singular form (`finding:` / `capability:`) per the validator's `RECORD_KINDS` convention; loaders tolerate both forms for forgiveness.

### Backward compatibility

All changes additive within v1.x; `framework_compat: ">=1.0.0,<2.0.0"` continues to accept v1.4.0. A v1.1-style run with no `crown_jewels` and no `attacker_positions` produces identical output to v1.3 (analyzer skips silently and writes `40-synthesis/attack-path-analyzer-skipped.txt`).

## [1.3.0] - 2026-05-26

### Added

- **`apd-threat-model-recon` tier-0 agent** — parses user-supplied threat models into a normalized graph at `00-context/threat-model-normalized.yaml`. Activation-gated on `.apd-run.yaml` declaring `threat_model: <path>` (or intake auto-detecting a TM-like artifact).
- **`apd-threat-model-evaluator` tier-4 agent** — evaluates the normalized TM against specialist findings/capabilities; emits three finding flavors: coverage gap (`disposition: gap`), contradiction (`disposition: risk`), silence (`disposition: uncertainty`). Findings use `agent: threat_model_evaluator` and id prefix `tmeval-`.
- **Native methodology support**: STRIDE (OWASP Threat Dragon JSON, Microsoft TMT .tm7, STRIDE-per-element Markdown/CSV), LINDDUN (Markdown/CSV tables), attack trees (indented prose, ADTool XML, JSON). PASTA / VAST / Trike / free-form prose accepted with reduced extraction confidence.
- **CLI subcommand `parse-threat-model`** — standalone parser dispatcher; auto-detects format from extension or honors `--methodology-hint`.
- **CLI flags on `init-run`**: `--threat-model <path>` and `--methodology-hint <name>` pre-populate the run-config.
- **New skill `apd-threat-model-methodologies`** — canonical STRIDE/LINDDUN→APD-goal mapping tables (single source of truth shared with Python mapping module) + discipline rules.
- **New schemas**: `threat-model-normalized.schema.json`, `threat-model-coverage.schema.json`.
- **Validator extensions**: `tmeval-` findings must cite the normalized TM (or source artifact) in evidence; contradiction findings must cross-reference the contradicting specialist finding ID.
- **New dependency**: `lxml>=4.9` (used by Microsoft TMT and ADTool XML parsers with XXE-safe flags).
- **ADR 0009** — Methodology-aware threat-model evaluator.
- **`docs/threat-modeling.md`** operator guide.

### Changed

- `finding.schema.json` — `agent` enum gains `threat_model_evaluator`; `id` pattern extended to accept `tmeval-` prefix.
- `run-config.schema.json` — accepts optional `threat_model: <path>` and `methodology_hint: <name>` fields.
- **Shared `$defs` extraction** (carry-forward from Phase A): ATT&CK / D3FEND / CWE patterns now defined once in `schemas/_defs.schema.json` and `$ref`'d by record schemas. Behavior unchanged.
- **`owasp_llm_top10` pattern tightened** (carry-forward from Phase A): now `^LLM(0[1-9]|10)$` (was `^LLM[0-9]{2}$` which accepted non-existent codes).
- **`refresh_mitre.py` aligned** (carry-forward from Phase A): constants renamed to `MAX_RESPONSE_BYTES` / `DEFAULT_TIMEOUT_SECONDS` matching the v1.2 triad; Content-Length pre-check added.
- **CLI `validate` now scans coverage rollups** (carry-forward from Phase A): cwe-coverage / owasp-coverage / d3fend-coverage in `40-synthesis/` are now validated by `apd-gauntlet validate` (previously only by tests).
- **ADR 0007 reformatted** (carry-forward from Phase A): now matches the canonical 0001-0008 hyphen+colon style.

### Backward compatibility

- All schema changes additive. v1.2-format runs (and v1.1, v1.0) validate unchanged.
- Minimum-viable run with no `threat_model:` declaration produces identical output to v1.2.
- PBM domain pack (`framework_compat: ">=1.0.0,<2.0.0"`) consumes v1.3.0 with no changes.

## [1.2.0] - 2026-XX-XX

### Added

- **Multi-framework taxonomy mappings** on findings: CWE, OWASP Top 10 (web), OWASP API Top 10, OWASP LLM Top 10 (all optional, declared per run via `taxonomies:` in `.apd-run.yaml`).
- **MITRE D3FEND mappings on capabilities**, with required `counters_attack` cross-reference to ATT&CK techniques the capability defends against. Sub-technique parent matching: `T1110.001` is satisfied by `T1110` declared in `mitre_attack[]`.
- **`mitre_attack` field on capabilities** (parallel to the one on findings) — documents which ATT&CK techniques the capability defends against. Enables the D3FEND `counters_attack` cross-reference rule.
- **Per-run taxonomy scoping** via `taxonomies:` field in `.apd-run.yaml`. CWE/ATT&CK/D3FEND default-on; OWASP variants opt-in.
- **Intake `taxonomy_suggestions` block** auto-detects relevant surfaces (web routes, OpenAPI specs, LLM SDK imports) and writes advisory suggestions to the context brief.
- **Three new synthesizer coverage rollups**: `cwe-coverage.yaml`, `owasp-coverage.yaml`, `d3fend-coverage.yaml` (the last includes a `counter_coverage` view showing which exposed ATT&CK techniques have D3FEND-backed capabilities countering them).
- **Three new schemas**: `cwe-coverage.schema.json`, `owasp-coverage.schema.json`, `d3fend-coverage.schema.json`.
- **Three new CLI subcommands**: `refresh-cwe`, `refresh-owasp`, `refresh-d3fend` (each applies the v1.0 security-review hardening: 60s timeout, 200 MiB cap, `source_sha256` in projected payload).
- **Seeded reference data** at `tools/apd_gauntlet/data/`: 969 CWEs (live-fetched v4.20), 30 OWASP categories (3 lists × 10, seed-only), 149 D3FEND techniques with 3234 counter relations (live-fetched).
- **`apd-control-mappings` skill** gains per-taxonomy discipline sections (CWE, OWASP Top 10 web/API/LLM, D3FEND).
- **`apd-intake` agent** gains taxonomy auto-detection step.
- **`apd-synthesizer` agent** documents the three new rollup outputs.
- **All 9 specialist agents** reference the v1.2 taxonomy scope.
- **`init-run --taxonomies`** CLI flag pre-populates the run-config.
- **Cross-reference validation**: D3FEND `counters_attack` must intersect the capability's `mitre_attack[].technique` list (with sub-technique parent matching).
- **ADR 0008** — Multi-framework taxonomy mappings.
- **`docs/taxonomy-mappings.md`** operator guide.

### Changed

- `finding.schema.json` — `control_mappings` accepts optional `cwe`, `owasp_top10`, `owasp_api_top10`, `owasp_llm_top10` arrays.
- `capability.schema.json` — `control_mappings` accepts optional `mitre_attack` (parallel to finding's) and `d3fend` arrays.
- `run-config.schema.json` — accepts optional `taxonomies` array.
- D3FEND ID pattern widened from `^D3-[A-Z]{2,5}$` to `^D3-[A-Z]{2,7}$` (real MITRE D3FEND data contains 6- and 7-letter codes like `D3-PHDURA`, `D3-DNSTA`).
- `docs/architecture.md`, `docs/running-the-gauntlet.md`, `docs/schema-evolution.md`, `README.md` — refreshed for v1.2 additions.

### Backward compatibility

- All schema changes additive. v1.1-format runs validate unchanged against v1.2 schemas.
- Minimum-viable run with no `taxonomies:` declaration produces identical output to v1.1.
- PBM domain pack (`framework_compat: ">=1.0.0,<2.0.0"`) consumes v1.2.0 with no changes.

## [1.1.0] - 2026-05-XX

### Added

- Optional `apd-code-recon` intake-tier agent that uses the DeusData [codebase-memory-mcp](https://github.com/DeusData/codebase-memory-mcp) graph to produce a code-grounded view of the system under review. Gated by `code_recon` setting in `.apd-run.yaml` (`enabled` / `auto` / `disabled`). See [ADR 0007](docs/adrs/0007-optional-code-reconnaissance-via-cbm.md).
- New schemas: `schemas/run-config.schema.json` (validates `.apd-run.yaml`) and `schemas/code-evidence-index.schema.json` (validates the code-evidence index).
- New template: `templates/code-architecture-brief.template.md`.
- CLI: `apd-gauntlet validate-run-config <path>` for operator parity with `validate-domain`.
- Validator now schema-validates `00-context/code-evidence-index.yaml` when present and treats it as a known artifact source for specialist evidence pointers.

### Changed

- `scaffold_run` emits `code_recon: auto` and `framework_version: 1.1.0` in the generated `.apd-run.yaml`.
- `apd-evidence-discipline` skill documents code-evidence pointer format and restates the input-trust boundary for CBM-returned content.
- `apd-orchestrator` agent gains a conditional Phase 1.5 dispatching `apd-code-recon`.

### Compatibility

- Backwards-compatible with v1.0 run directories: runs without a `.apd-run.yaml` skip Phase 1.5 entirely.
- Domain packs declaring `framework_compat: ">=1.0.0,<2.0.0"` (e.g. PBM) continue to work unchanged.

## [1.0.0] - 2026-05-XX

First public release.

### Added

- Twelve agents (orchestrator, intake, synthesizer, nine specialists) for APD security architecture reviews.
- Five skills providing framework discipline, schemas, evidence rules, control mappings, and (generated) domain content.
- JSON Schemas for finding, capability, contradiction, severity-disagreement, coverage-matrix, NIST coverage, ATT&CK exposure, and domain pack records.
- `apd-gauntlet` Python CLI with `validate`, `init-run`, `build-domain-skill`, `summarize`, `lint-agents`, `check-ids`, `validate-domain`, and `refresh-mitre` subcommands.
- Pluggable domain pack mechanism with PBM (Pharmacy Benefit Management) shipped as the first pack.
- Curated synthetic claim-event-bus example with CI-validated expected outputs.
- Claude Code plugin manifest.
- CI workflows for validation, Python tests, markdown lint, and release.
