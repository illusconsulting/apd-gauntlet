# APD Gauntlet 1.7.1 and 2.x Program — Master Implementation Plan

> **For agentic workers:** This plan sequences the program; it does not contain code. Each workstream has its own detailed plan, executed with superpowers:subagent-driven-development (recommended) or superpowers:executing-plans. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship everything agreed on 2026-10-10:

- the audit's defect fixes as 1.7.1;
- a measured evaluation harness;
- the cost and token waves;
- local apps and optional decision models;
- Terraform, OpenTofu and Atmos evaluation;
- decision-model checks;
- the threat catalog as an enrichment layer (agreed 2026-10-11);

all on the 2.0 line, then the code-flow layer on 2.1. Every change lands behind a measured before-and-after comparison.

**Architecture:** Two release lines (RELEASING.md): fixes land on `main` and merge forward; everything else lands on `next`. Each milestone ends in a tagged pre-release that passes the comparison gates against the 1.7.1 baseline (A15.1). Shared names and interfaces are fixed once, in the registry below, and every detailed plan uses them.

**Tech Stack:** Python 3.10–3.12 engine (`tools/apd_gauntlet`), the Claude Code workflow (`.claude/workflows/apd-gauntlet.js`), the Claude Agent SDK runner (2.0), and external tools: Atmos, OpenTofu, Trivy, Checkov, ShellCheck, Joern, OpenGrep.

**Specs:**

- `docs/superpowers/specs/2026-10-10-local-apps-and-decision-models-design.md` (PR #29)
- `docs/superpowers/specs/2026-10-10-iac-terraform-opentofu-atmos-design.md`
- `docs/superpowers/specs/2026-10-10-code-flow-layer-design.md` (draft, awaiting review)
- `docs/superpowers/specs/2026-10-11-threat-catalog-integration-design.md` (approved 2026-10-11)
- The cost and token audit (Claude Doc "APD Gauntlet cost and token audit", 2026-10-10), the source for WS1, WS3, WS5 and WS6.

**Amended 2026-10-17 per the amendments register** (A7.18, A7.19, A7.20, A7.21, A7.22, A7.23, A7.24, A8.1, A8.4, A8.6, A9.2, A9.13, A10.5, A10.10, A12.6, A14.3, A14.5, A14.6, A15.4, A15.5, A15.7, A15.11, A15.12, A15.13).

## Global Constraints

- **Release lines:** per RELEASING.md. Bug fixes go to `main` by PR, then `main` merges into `next`. Features go to `next` by PR. Tags pass `tools/check_release_tag.py`.
- **Versions:** pyproject and `__init__` use PEP 440 (`2.0.0aN`); the plugin manifests use SemVer (`2.0.0-alpha.N`). The test literal moves with each pre-release.
- **CI never touches the network** (ADR-0017). Real-run accuracy is judged locally, and real runs are never committed.
- **Every behaviour-changing task ships behind `compare-runs`,** run twice per configuration. Each task or PR group gates against the previous accepted state (the last configuration whose gates passed). Each milestone exit gates against the 1.7.1 baseline (Task 1). A run that exercises a changed runner runs it by path, `Workflow({scriptPath: "<checkout>/.claude/workflows/apd-gauntlet.js", args: <the run's parsed .apd-run.yaml>})`, as `/apd-gauntlet:run` does, or in a new session, because `Workflow({name: "apd-gauntlet"})` runs the copy of the script registered when the Claude Code session started (A15.12).
- **Gates that a baseline cannot measure.** 1.7 runs record no retries, first-pass validation or audit iterations, so `compare-runs` reports gates 4–5 as `not_available` against the 1.7.1 baseline. It still exits 0 (`pass_with_gaps`); `--strict` turns that into a failure. A second baseline captured on `next` after WS2 Task 7 makes those gates measurable for WS3 onward.
- **The comparison gates.** These comparison gates are proposals, recorded in `eval/gates.yaml`:
  - no critical or high finding lost unless the loss traces to evidence;
  - severity agrees on at least 90% of matched findings;
  - blocked rate moves by no more than 5 points;
  - first-pass schema validity and retry count no worse than baseline;
  - report audit passes in no more iterations than baseline.
- **Ids are minted by Python only** (ADR-0020); agents emit content.
- **Nothing from a client repository executes.** Every external tool runs through `apd_gauntlet.sandbox.run_tool` (registry §R2).
- **Decision models default to `none`.** Their flags are advisory. Thresholds come from `calibrate` on development labels, frozen before held-out runs.
- **Quality gates:** `ruff check tools/ tests/`, `mypy tools/` (strict on `tools/apd_gauntlet`), `pytest`, and `markdownlint-cli2` on the linted globs all pass on every PR. CI excludes `docs/superpowers/plans/**`, so a PR that edits a plan file lints it explicitly: `npx --yes markdownlint-cli2 <plan files>`.
- **External tool floors:** OpenTofu ≥ 1.12.6 (tested 1.13.1), Trivy ≥ 0.71.1 (tested 0.75.0), Atmos ≥ 1.231.0 (tested 1.232.0), Checkov ≥ 3.3.26 (tested 3.3.29), ShellCheck ≥ 0.9 (tested 0.11.0), python-hcl2 `>=7,<8`.
- **Python dependency pins:** `claude-agent-sdk>=0.2.167,<0.3`, `textual>=8.2,<9`, `starlette>=1.0,<2`, `httpx>=0.27,<1`, `keyring>=25.7,<26`, dev `pytest-asyncio>=1.0` with `asyncio_mode = "auto"`.

## Review Focus

- **A 1.7 run resumed by a 2.0 runner, or a 2.0 run resumed by 1.7.1.** Both should refuse with a clear message rather than mix formats: `resume-plan` and the ledger record the engine version.
- **A workflow step added in one channel but not the other** (Claude Code workflow versus Agent SDK runner). The parity test must fail. Every plan that adds a phase or CLI step updates both and extends `test_plan_run_phase_names_consistent_with_workflow` (`tests/test_cli_plan_run.py`).
- **An operator who never runs the baseline.** `compare-runs` must refuse to call a candidate "passing" without a baseline directory, rather than compare against nothing.
- **Decision thresholds shipped uncalibrated.** Records must say `calibrated: false`, and flags from uncalibrated thresholds must be labelled as such in the report header.
- **Two consent subjects** (decision model, IaC module fetch). Granting one must not imply the other: `consent.json` is keyed by subject (§R6).

---

## Workstreams

| Id | Workstream | Line | Detailed plan | Depends on |
|---|---|---|---|---|
| WS0 | Release lines | both | Done: PRs #27, #28 | — |
| WS1 | Audit defect fixes → 1.7.1 | `main` | `2026-10-10-ws1-defect-fixes-1.7.1.md` (12 tasks) | — |
| WS2 | Measurement and evaluation harness | `next` | `2026-10-10-ws2-measurement-and-evaluation.md` (14 tasks) | — |
| WS3 | Cost wave 1 (quick wins) | `next` | `2026-10-10-ws3-cost-wave1-quick-wins.md` (9 tasks) | WS1 merged forward, WS2 |
| WS4 | Local apps and decision models | `next` | `2026-10-10-local-apps-plan{1,2,3}-*.md` (PR #29; 9, 9 and 8 tasks), amended per §A | WS3 (LA2, LA3) |
| WS5 | Cost waves 2–3 (context, determinism, tiering) | `next` | `2026-10-10-ws5-cost-waves2-3-context-and-tiering.md` (23 tasks) | WS3, WS2, LA2; Wave 3 runs in M6 |
| WS6 | Decision tasks beyond finding QA (audit wave 4) | `next` | `2026-10-10-ws6-decision-tasks.md` (13 tasks) | LA1, WS2 (`calibrate`), WS5 (`tm-candidates`, `edge-review`), IAC3 (`iac-triage`) |
| WS7 | IaC: Terraform, OpenTofu, Atmos | `next` | `2026-10-10-iac-plan{1,2,3,4}-*.md` (14, 8, 10 and 6 tasks) | LA1 (consent), LA2 (runner phases), LA3 (doctor hook), WS2 (IAC4) |
| WS8 | Code-flow layer, plus infrastructure-to-code join | `next` (2.1) | CF1–CF4, written after spec approval | WS7, WS2 |
| WS9 | 2.0.0 GA | both | RELEASING.md "2.0.0 GA" | M6 |
| WS10 | Threat catalog integration | `next` | `2026-10-11-cat1-catalog-data-loader-editions.md`, `-cat2-scope-and-tm-author.md`, `-cat3-lenses-evaluator-paths-report.md`, `-cat4-evaluation.md` (14, 10, 15 and 12 tasks) | WS2 (CAT1, CAT4), WS1 and LA2 (CAT2), WS5 Task 8 (CAT3) |

## Milestones and releases

| Milestone | Tag | Contents | Exit gate |
|---|---|---|---|
| M1 | `v1.7.1` (`main`) | WS1 (released as v1.7.1) | WS1 tests green; the 1.7.1 substitute gate (A8.1): offline regression passed (consolidated Task 1.4), live run clean (consolidated Task 1.5 Steps 1–4), metrics comparison inconclusive against the 1.4.0-era example (A15.9); 1.7.1 released on that basis (consolidated DEC-1) |
| M2 | `v2.0.0a1` | Docs PRs merged; WS2; second baseline captured on `next`; WS3 | Gates pass (gates 4–5 against the second baseline); `usage` shows lower cost per run |
| M3 | `v2.0.0a2` | LA1, LA2 (amended) | Runner completes the committed examples with parity; finding QA in shadow |
| M4 | `v2.0.0a3` | LA3; WS5 Wave 2; CAT1 | Gates pass after each Wave 2 item; catalog load, no-HITRUST, KB-alignment and KB-edition tests green |
| M5 | `v2.0.0a4` | IAC1–IAC3; WS6 tasks in shadow mode; CAT2 and CAT3 with `threat_catalog: off` as the default | IaC probe-regression and security tests green: `!exec` and template canaries, outside and remote includes, `.tofu` precedence, override files, argument allowlist, suppressions surfaced; catalog metamorphic suite C1–C6 green |
| M6 | `v2.0.0b1` | IAC4; calibration; WS5 Wave 3, one tier at a time; WS6 tasks enabled one at a time; CAT4 | Held-out IaC recall ≥ 1.7.1 baseline; gates pass per tier; catalog gates decide the `threat_catalog` default; feature freeze |
| M7 | `v2.0.0rc1` → `v2.0.0` | Fixes only; WS9 | RELEASING.md GA checklist |
| M8 | `v2.1.0aN` | WS8 (CF1–CF4) after spec approval | CF4 evaluation vs the 1.7.1 CBM-only baseline |

**Parallel-safe pairs**, run in separate worktrees:

- WS1 with WS2;
- LA1 with WS3, once WS3 Task 1 (the runner agent) has merged;
- IAC1 with WS5 data-only items (digests and renders);
- CAT1 with LA1 (CAT1 edits no workflow or runner file).

Everything that edits `.claude/workflows/apd-gauntlet.js` or `runner/flow.py` merges one PR at a time. CAT2 and CAT3 are on that list.

---

## Registry: names and interfaces shared across plans

Every detailed plan uses these exact names. A plan that needs a new shared name adds it here in the same PR.

### R1. New CLI commands

| Command | Owner | Contract |
|---|---|---|
| `resume-plan <run-dir> --json` | WS1 | Prints `{"engine_version": str, "steps": [{"label": str, "complete": bool, "reason": str}]}`. Exits 0 and writes nothing. The workflow and runner skip steps marked complete; LLM prompts carry no guard text. |
| `prepare-run <run-dir> [--domain …]` | WS3 | Composite of scaffold `validate`, `build-domain-skill` and `validate-domain`, keeping their exit codes. Named `prepare-run`, not the audit's `setup`, because LA3 owns `apd-gauntlet setup`. |
| `tier-gate <run-dir> --tier <dir>` | WS3 | Composite: canonicalize the tier, then `validate --tier`. Exit 0 clean, 1 schema errors. |
| `post-tier4 <run-dir>` | WS3 | Composite: `assemble-c4`, tmeval canonicalize, `rollup`. |
| `closeout <run-dir>` | WS3 | Composite: dimpr canonicalize, `summarize`, final `validate`. |
| `compare-runs <baseline> <candidate> [--json] [--gates eval/gates.yaml]` | WS2 | A deterministic delta. Exits 0 when every gate passes, 1 when any fails, 2 on usage errors or a missing baseline. |
| `usage <run-dir> --otel <file>` | WS2 | Summarises tokens and cost per agent and phase from OpenTelemetry `claude_code.api_request` events into `<run-dir>/.apd-state/usage.yaml`. |
| `usage <run-dir> --otel <file> --expect-model <agent-glob>=<model-prefix>` | WS5 Task 15a (N10) | Repeatable. Exits 1 and prints `expect-model: <agent> ran <model>, expected <prefix>*` on any mismatch; `usage.yaml` `by_agent.<agent>` gains `models` and `efforts`. |
| `eval run <corpus.yaml> --set dev\|heldout --evaluator <name>` | WS2 | Runs a registered evaluator and writes `eval/results/<evaluator>/<set>-<timestamp>.yaml`. |
| `calibrate <task> --labels <file> --target-precision <p>` | WS2 | Writes or updates `tools/apd_gauntlet/data/decide/thresholds.yaml` entry `<task>: {threshold, precision, recall, n, labels_sha256, calibrated: true, provider, model, weights_revision}`; exits 2 if the labelled records mix models (A12.6). |
| `metamorphic run --suite <name>` | WS2 | Generic invariance harness. Suites register transformations (IAC4: T1–T8; CF4 adds its own). |
| `xref-digest <run-dir> --before <tier-dir>` | WS5 | Writes `40-synthesis/digests/xref-<tier>.yaml`. |
| `report-digest <run-dir>` | WS5 | Writes `40-synthesis/digests/report.yaml`. |
| `edge-review <run-dir>` | WS5 | Writes `40-synthesis/edge-review.yaml` (heuristic edges only). |
| `tm-candidates <run-dir>` | WS5 | Writes `40-synthesis/tm-candidates.yaml` (the Python join of TM entries and findings). |
| `render <run-dir> --artifact <name>` | WS5 | Renders markdown from YAML for `threat-model-authored`, `attack-path-report`, `threat-model-coverage-report` and `advisory-report`. |
| `build-lens-skills <run-dir>` | WS5 | One compiled skill packet per lens, under `.claude/skills/apd-domain/lens/<goal>.md`. |
| `decide <task> <run-dir>` | LA1 | Task registry `apd_gauntlet.decide.tasks`. LA1 owns `finding-qa`. WS6 adds `cluster-pairs`, `report-claims`, `tm-screen`, `asset-match`, `intake-score`, `input-screen`, `iac-triage` and `diagram-check` (N7, WS6 Task 14). |
| `iac run <run-dir>` / `iac consent <run-dir>` | IAC1 | Per the IaC spec. |
| `code-flow run <run-dir>` | CF1 | Per the code-flow spec. |
| `refresh-threat-catalog [--version X.Y.Z] [--dry-run] [--out-dir DIR] [--token-env NAME]` | CAT1 | Refreshes `data/threat-catalog/open.json` and its schema from a catalog release; verifies, validates and checks `compat.yaml`. |
| `catalog scope <run-dir>` | CAT2 | Writes `00-context/threat-scope.yaml`. Exits 0 and writes nothing when `threat_catalog` is `off`; exits 1 without an inventory. |
| `catalog shortlists <run-dir>` | CAT3 | Writes `00-context/threat-shortlists/<goal>.md` for the nine goals. |
| `catalog export-gaps <run-dir>… --out <file>` | CAT3 | Merges `catalog-gaps.yaml` across runs, stripping evidence, names and paths. Local only. |
| `catalog gates <corpus.yaml> --set dev\|heldout [--gates eval/gates.yaml] [--record <file>] [--strict] [--json]` | CAT4 | Evaluates the catalog gates across `off` and `open` run sets; `--record` writes the default decision. `eval label-template` gains `--kind findings\|threats`, `--sample N` and `--merge`. |

### R2. Shared Python modules

- **`apd_gauntlet.sandbox.tools`** (created by IAC1; refines the IaC spec's `iac/tools.py` location so CF1 can reuse it):
  - `run_tool(tool: str, args: list[str], *, cwd: Path, network: bool = False, timeout_s: int) -> ToolResult`, where `ToolResult` is `(returncode: int, stdout: str, stderr: str, duration_s: float)`;
  - `register_invocation(tool: str, validator: Callable[[list[str]], None]) -> None`;
  - `ToolNotAllowed(Exception)`.
- **`apd_gauntlet.context.select`** (created by IAC3; reused by CF3): `select_packet(graph: TypedGraph, seeds: dict[str, float], params: ContextParams) -> Packet`, with `ContextParams` loaded from `data/<domain>/context-params.yaml`.
- **`apd_gauntlet.validate` evidence-index registry** (created by IAC2): `EVIDENCE_INDEXES: dict[str, EvidenceIndexSpec]`, keyed by filename (`code-evidence-index.yaml`, `iac-evidence-index.yaml`, `iac-graph.yaml`, later `code-flow-index.yaml`), with `EvidenceIndexSpec(schema: str, locator_re: str, id_field: str)`. The existing code-evidence handling moves behind it unchanged.
- **`apd_gauntlet.eval.evaluators`** (created by WS2): `register(name: str, fn: Callable[[CorpusEntry, Labels], EvalResult])`.
- **`apd_gauntlet.catalog`** (created by CAT1): `catalog_config_from_run_config(run_cfg: Mapping[str, Any]) -> CatalogConfig | None`, `load_selection_params(path: Path | None = None) -> SelectionParams`, `load_catalog(cfg: CatalogConfig, *, data_dir: Path | None = None) -> Catalog | None` and the frozen `Threat`/`Catalog` model. CAT2 adds `goals`, `scope` and `candidates`; CAT3 adds `shortlists`, `derive`, `coverage` and `gaps`. The CAT brief fixes every signature.

### R3. Phases

The workflow's `meta.phases` and `runner.flow.PHASES` stay equal at every commit. Phases are added in this order:

- `iac`, after `setup` and before `intake` (IAC1);
- `code-flow`, after `code-recon` and before `threat-model-author` (CF1).

WS3 renames no phase. The `setup` phase runs `prepare-run`. WS10 adds no phase: `catalog-scope` is the first step of `threat-model-author`, and `catalog-shortlists` runs in the `canonicalize` phase right after WS1's `canonicalize-threat-model`, before tier 1. The workflow mirrors the Python default as `CATALOG_DEFAULT_EDITION` with `catalogEdition()`; a parity test keeps the two equal.

### R4. Run-config keys (all optional, additive)

| Key | Owner |
|---|---|
| `decision_model` | LA1 |
| `decision_model.provider: selfhosted` | LA1 Task 10 (N5) |
| `decision_model.tasks.finding-qa` (`off \| shadow`; default `shadow` when a provider is set) | LA1 Task 8 (A12.3) |
| `decision_model.task_models` (`{<task>: <model id>}`, ids validated against the catalog) | WS6 Task 3 (A12.9) |
| `decision_model.tasks.diagram-check` | WS6 Task 14 (N7) |
| `decision_model.cache` (`run \| workspace`, default `run`) | WS6 Task 15 (N8, optional) |
| `domain_improvement_capture: false` | WS3 |
| `infrastructure.static.atmos`, the object form of `infrastructure.static.terraform`, `infrastructure.modules`, `infrastructure.plans`, `infrastructure.require_tools` | IAC1 |
| `code_flow`, `repos[].deploys_as` | CF1 |
| `threat_catalog` (`off \| open \| full`, or an object with `edition`, `path`, `system_types`, `exclude_system_types`). `full` is an operator-supplied local catalog file in the release schema (A7). | CAT1 |

User-config keys (`user-config.schema.json`, not the run config): `decision_model.base_url`, `decision_model.context_window`, `decision_model.images`, `decision_model.ca_bundle` (LA1 Task 10, N5); `decision_model.cloudflare_gateway_id`, `decision_model.gateway_log_payloads` (LA1 Task 11, N6).

### R5. Agent frontmatter

- Every agent sets `model` and `effort`. WS3 adds `effort` everywhere and keeps today's models; WS5 Wave 3 changes models one tier at a time. Every agent also sets `omitClaudeMd: true` (N15, WS5 Task 0b).
- New agent `apd-cli-runner` (WS3): tools `Bash` only, `model: haiku`, `effort: low`. `pyStep()` dispatches with `agentType: 'apd-cli-runner'`.

### R6. State files under `runs/<id>/.apd-state/`

`consent.json` is a JSON object keyed by subject:

```json
{
  "decision_model": {"provider": "…", "model": "…", "granted_at": "…", "method": "…"},
  "iac_module_fetch": {"sources": ["…"], "sources_sha256": "…", "granted_at": "…", "method": "…"}
}
```

LA1's `has_consent` and `record_consent` read and write the `decision_model` subject (§A1). IAC1 adds `has_fetch_consent(run_dir, sources)` and `record_fetch_consent(run_dir, sources, method)`.

### R7. Schemas (new or changed, all additive)

| Schema | Change | Owner |
|---|---|---|
| `decision-record` | New | LA1 |
| `iac-evidence-index` | New | IAC1 creates the skeleton; IAC2 completes it |
| `iac-graph` | New | IAC3 |
| `finding` | Gains `alternatives_considered` | IAC3 |
| `asset-graph` | Provenance gains `iac_evidence` | IAC3 |
| `asset-graph` | Provenance gains `code_flow` | CF3 |
| `domain` | Gains `consumers` per calibration file | WS5 |
| `eval-labels`, `eval-corpus` | New | WS2 |
| `code-flow-index` | New | CF1 |
| `run-config` | Gains `threat_catalog` | CAT1 |
| `finding` | `owasp_llm_top10` items also accept `LLMnn:2025` | CAT1 |
| `domain` | Gains `threat_profile` | CAT2 |
| `threat-scope` | New | CAT2 |
| `threat-model-normalized` | Entries gain `catalog_refs` and `catalog_gap_reason` | CAT2 |
| `finding` | Gains `threat_refs` and `catalog_mappings`; `tmeval_key` gains flavor `catalog_silence` and `threat_id` | CAT3 |
| `capability` | Gains `threat_refs` | CAT3 |
| `tm-candidates` | Gains `catalog_silence` | CAT3 |
| `asset-graph`, `attack-path` | Edges gain `threat_refs`; paths gain `tactic_sequence` | CAT3 |
| `catalog-coverage`, `catalog-gaps`, `catalog-silence-dismissals` | New | CAT3 |
| `eval-labels` | Gains kind `threats` | CAT4 |
| `_defs` | Gains `catalog_threat_id` (CAT1), `catalog_system_type` and `catalog_family_code` (CAT2) | CAT1, CAT2 |
| `threat-model-normalized` | Skeleton-only optional `catalog_candidates`; the validator warns if it appears in the authored TM | CAT2 |
| `owasp-coverage`; `owasp_*.json` KBs | Entries gain `edition`, `edition_names`, `crosswalked`, `crosswalked_from`; KBs gain `edition` and `seed_source` | CAT1 |
| `defense-graph`, `metrics` | `candidate_d3fend[].source`; `catalogThreatsByStatus` | CAT3 |
| `decision-record` | Gains required `calibrated`, `endpoint` (host only), per-item `state_sha256` and `possibly_truncated` | LA1 (A1.3, A12.2, A12.7; `endpoint` from N5) |
| `thresholds.yaml` entries (`data/decide/`) | Gain `provider`, `model` and `weights_revision` | WS2 (A12.6) |
| `run-attempts` | Gains required `tier_repairs` and `lens_reruns`; optional `llm_first_pass_invalid`, `repairs` and `python_repairs` | WS2 (A9.4); WS5 Task 15b (N11) |
| `routing` | New file `40-synthesis/routing.yaml`, outside `decisions/` | WS6 Task 16 (N9, optional) |
| `code-evidence-index` | Gains optional `repos[].coverage` | WS5 Tasks 13–14 (N21) |
| `metrics` | Gains real `findings_pre_dedup` and `capabilities_pre_dedup` counts | WS2 (N20) |

Each change gets a dated entry in `docs/schema-evolution.md`.

### R8. Data files

- `tools/apd_gauntlet/data/decide/thresholds.yaml` (WS2 writes; LA1, WS6 read). Entries carry `provider`, `model` and `weights_revision`; a client whose provider or model differs from the entry's escalates every item, with a warning (A12.6).
- `tools/apd_gauntlet/data/iac/` (WS7)
- `tools/apd_gauntlet/data/codeflow/` (WS8)
- `tools/apd_gauntlet/data/threat-catalog/` (WS10): `open.json`, `open.schema.json`, `open.provenance.json`, `compat.yaml`, `selection.yaml`, `system-types.yaml`, `apd-goals.yaml`, `taxonomy-map.yaml`, `owasp-crosswalks.yaml`. `open.json` and `open.schema.json` are the release's `threat-catalog-<v>.json` and `threat-catalog.schema.json`, byte-identical. A local catalog file (`threat_catalog: full`) is never committed or vendored; the loader warns when it sits in an unignored git tree. Also `00-context/threat-scope.yaml`, `00-context/threat-candidates.md`, `00-context/threat-shortlists/<goal-stem>.md`, `40-synthesis/catalog-coverage.yaml`, `40-synthesis/catalog-gaps.yaml`, `40-threat-model/catalog-silence-dismissals.yaml`, `eval/catalog/decision.yaml` (committed aggregates, ADR-0028) and `eval/local/catalog/` (gitignored). WS2's `TUNABLE_GLOBS` gains `data/threat-catalog/selection.yaml` and `data/threat-catalog/system-types.yaml`.
- `eval/` at the repo root, not packaged: corpora manifests, labels, gates and local results (results are gitignored)
- `eval/gates-wave3.yaml` (WS5 Task 15c, N12): the Wave 3 artifact-level gates, holding the A10.11 thresholds
- `docs/superpowers/ledgers/<plan-slug>.md`: each executed plan's controller ledger of rulings, committed with its PR (new files there need `git add -f`)

### R9. Additions settled by the detailed plans

The detailed plans fixed these names. They are binding in the same way as R1–R8.

**CLI (R1):**

- **`resume-plan`:** exits 2 when `.apd-run.yaml` is missing or invalid, and 3 when the run's `framework_version` major differs from the engine's. 2.0 applies the mirror rule. `steps` lists the agent steps with `code-recon` expanded per `recon_shards(cfg)` plus `code-recon-cross-repo`, by first-attempt label (WS1).
- **Composites** (WS3):
  - each constituent always runs;
  - status lines `<composite>: <step> exit=<N>` go to stderr, then `ok` or `failed <steps>`;
  - the exit code is `validate`'s for `tier-gate` and the first failure for the others;
  - `tier-gate` canonicalizes the whole run, because `canonicalize` has no per-tier mode;
  - `tier-gate --json` returns errors keyed by file for WS1's repair loop;
  - `closeout` forwards `--record-attempts`.
- **Excerpt check:** `--strict-excerpts` (WS1, opt-in on 1.7.1). WS3 makes it the default on `next`, with `--no-strict-excerpts`, on `validate`, `tier-gate` and `closeout`. The check applies only to citations of files under `inputs/`, and `...` splits an excerpt into fragments that must appear in order.
- **`compare-runs`:** results are `pass`, `pass_with_gaps` (exit 0) or `fail` (exit 1). `--strict` treats gaps as failures. `--excuse <gate>:<reason>` records a known, accepted deviation (WS2).
- **WS2:**
  - new subcommands: `eval freeze [--root] [--new-heldout-set]` and `eval label-template <run-dir> --entry <id> --out <file>`;
  - new options: `summarize --record-attempts <json>`, `usage --workflow-run --json`, `eval run --root --results-dir --json`, `calibrate --min-support --thresholds` and `metamorphic run --root --json`.
- **WS6:** `decide-labels sheet|annotate|export`, and `decide` task `output-screen`.

**Modules (R2):**

- **WS1:**
  - `resume_plan.{RESUMABLE_STEPS, ResumeStep, build_resume_plan, step_status, check_engine_compat, EngineMismatch}`;
  - `resources.read_prompt`;
  - `validate.{schema_errors_for_file, check_excerpts_verbatim}` and `run_cross_file_pass(strict_excerpts=)`;
  - `linters.{compute_cev_id, compute_tm_entry_id}`.
- **WS2:**
  - `measure.attempts.write_attempts` (the LA2 runner calls it at closeout);
  - `measure.usage.AGENT_PHASES` (WS2 lists `apd-tier-repair`; WS3 adds `apd-cli-runner`);
  - `eval.calibrate.{register_value, ValueSpec}`;
  - `eval.metamorphic.{register_suite, BUILTIN_SUITE_MODULES}`.

  `tests/conftest.py` is created by WS2; later plans add to it.
- **WS3:** `apd_gauntlet.composite.{SubStep, invoke, run_composite}` and the four step builders, which LA2 reuses. Shared workflow test harness: `tests/js/workflow_dispatch_trace.mjs` (`trace`, `CLI_LABELS`, `HA_SHAPED`).
- **WS5:** `code_recon.shards.{recon_shards, RECON_SHARD_SIZE}` (6, mirrored in the workflow) and `attack_path.edge_review.REVIEWED_EDGE_TYPES`.
- **WS6:**
  - `decide.tasks.{TASKS, register, get_task, task_names, TASK_EGRESS}`;
  - `decide.policy.{WS6_TASKS, task_mode, load_threshold, policy_for, TaskPolicy}`;
  - `decide.batch.{TaskSpec, run_task}`;
  - `runner.instructions.ESCALATION_NOTES`;
  - `attack_path.build.is_heuristic_edge`, which WS5's `edge-review` uses.
- **IAC:**
  - `register_invocation` takes keyword-only `helpers`, `env` and `allow_network`;
  - a `ToolRunner` protocol;
  - `run_tool` return codes 124 (timeout), 125 (output cap) and 127 (tool not found);
  - `context.select` also exports `TypedGraph`, `TypedEdge`, `ContextParams`, `Packet` and `load_context_params(domain)`.

**Run-config (R4):**

- `decision_model.tasks: {<task>: off|shadow|active}`, default `off` for every WS6 task even when a provider is set;
- `decision_model.weights_revision`;
- `decision_model.allow_full_inputs: false`, which `intake-score`, `input-screen` and `output-screen` require to be true.

**Agents (R5), replacing R5's first line:**

- Every agent sets `effort` after WS3, and `model` after WS5 Task 23, when the linter starts requiring it. Every agent also sets `omitClaudeMd: true` (N15, WS5 Task 0b).
- Descriptions are one line: at most 160 characters for agents, 200 for skills, and 4,096 bytes in total.
- New agent `apd-tier-repair` (WS1; WS3 adds `effort: low`): tools Read and Edit, `sonnet`, `low`, usage phase `canonicalize`. WS1's `repairTierGate` dispatches it.
- `apd-orchestrator` is deleted by WS3.

**State (R6):**

- `consent.json["decision_model"].tasks` (WS6).
- IaC consent functions live in `apd_gauntlet.iac.consent`, with methods `flag | prompt | tui | web`.
- New state files `.apd-state/attempts.yaml` and `.apd-state/usage.yaml` (WS2).

**Schemas (R7):**

- **WS1:** `agent-receipt` gains `resume_plan`. Agent-emitted `code-evidence-index` `id` and `threat-model-normalized` `entry_id`/`inferred_apd_goals` become optional.
- **WS2:** new `run-attempts` schema. `eval-labels` kinds are `findings`, `decisions` and `iac` (IAC4 adds the last).
- **WS5:** new schemas `xref-digest`, `report-digest`, `edge-review`, `tm-candidates` and `code-recon-shard`. `domain.consumers` maps a calibration include path to hyphenated goal stems.
- **WS6:**
  - `decision-record` gains WS6 fields, plus an item-level `where`;
  - new `decision-escalations` schema;
  - `severity-disagreement` gains an optional `decision`;
  - `asset-graph` provenance gains `decision`.
- **IAC:**
  - id patterns `iev-`, `n-` and `e-`, each followed by 8 hex characters;
  - index entries gain `suppressed_in_repo` and `suppression`;
  - `asset-graph` `build_summary.sources_used` gains `iac_graph`.

**Paths (R8):**

- **WS2:** `eval/frozen.yaml` and `eval/findings/`; `eval/local/` and `eval/results/` are gitignored. Threshold keys are `<task>` or `<task>.<flag>`, for example `finding-qa.unsupported`.
- **WS5:**
  - `40-synthesis/digests/`;
  - `00-context/code-recon/*.yaml` and `merge-report.yaml`;
  - `.claude/skills/apd-domain/attack-path-defaults.md`;
  - `.claude/skills/apd-domain/lens/<goal>.md`.
- **WS6:** decision records at `40-synthesis/decisions/<task>.all.yaml`, escalations at `40-synthesis/escalations/<task>.yaml`, labels under `eval/local/decide/`.
- **IAC:** `data/iac/{tools,check-goal-map,control-allowlist,security-vars,aws-graph-map,context-params,internet-aliases}.yaml` and `eval/local/iac/`. IaC packets with more seeds than the cap write overflow ids to `<goal>.overflow.md`.

**Workflow labels:** each plan lists the labels it adds. These are shared because later plans edit around them:

- `resume-plan`, `canonicalize-code-evidence`, `canonicalize-threat-model`, `repair-*`, `*-rerun`, `*-after-repair` and `*-after-rerun` (WS1);
- `prepare-run`, `tier-gate-<tier>`, `post-tier4`, `post-tier4-retry-1` and `closeout` (WS3);
- `xref-digest-<tier>`, `report-digest`, `render-*`, `analyze-attack-paths`, `edge-review`, `tm-candidates`, `build-lens-skills`, `code-recon-<shard>` and `code-recon-cross-repo` (WS5);
- `iac-run` (IAC1);
- `catalog-scope` and `catalog-shortlists` (WS10).

### R10. ADR numbers

| ADR | Owner |
|---|---|
| 0016, 0018 | Unused (reserved 2026-06; never landed) |
| 0024–0026 | LA1–LA3 |
| 0027 | IAC1 (IaC evaluation, including template-driven execution) |
| 0028 | WS2 (measurement, and the narrow ADR-0017 exception for aggregate calibration statistics) |
| 0029 | WS6 |
| 0030 | CAT1 (threat catalog as an enrichment layer) |
| 0031–0039 | Code-flow (CF1–CF4) |
| 0040 | Healthcare / clinical-FHIR pack (N22) |

N5 and N6 amend ADR-0024; N7–N9 amend ADR-0029; N1 needs no ADR.

---

## §A. Amendments to existing plans (make before executing the affected plan)

- **A1. LA1 Tasks 5–6.**
  - `record_consent`/`has_consent` read and write `consent.json["decision_model"]` (R6).
  - Finding-QA thresholds load through WS6's `decide.policy.load_threshold` from `data/decide/thresholds.yaml`, under keys `finding-qa.<flag>`. The proposal values ship as `calibrated: false` entries, and every decision record copies `calibrated`.
  - The `severity` score scale is fixed at five levels, 0 to 4 (informational, low, medium, high, critical), so `calibrate` can register `finding-qa.severity_delta`.
  - LA1 adds its fixtures to `tests/conftest.py` (created by WS2) rather than creating that file.
  - Finding QA counts toward the per-run decision spend that WS6 computes from all decision records.
- **A2. LA2 Tasks 3, 6 and 7.**
  - The step table uses WS3's composite commands (`prepare-run`, `tier-gate`, `post-tier4`, `closeout`) and WS1's `resume-plan` semantics.
  - The repair dispatch reuses WS1's repair prompt template (`tools/apd_gauntlet/data/prompts/repair.md`).
  - Agent specs read `model` and `effort` from frontmatter (R5).
  - CLI steps call WS3's `apd_gauntlet.composite` builders rather than re-implementing the composites.
  - The repair dispatch uses the `apd-tier-repair` agent.
  - The runner calls `measure.attempts.write_attempts` at closeout.
  - The runner refuses to resume a 1.7 run, mirroring `resume-plan`'s exit 3.
- **A3. LA3 Task 3.** In `tools/apd_gauntlet/app/services.py`, add `register_doctor_check(name: str, fn: Callable[[UserConfig], Check]) -> None`. `doctor()` appends the registered checks, in registration order, after the built-in ones. IAC1 and CF1 call it. `Check` is LA3's existing dataclass (`name`, `status`, `detail`, `fix`).
- **A4. IaC spec.** Done in this branch:
  - raw-read fallback for unresolved roots (§9);
  - 1.7 baseline in the evaluation (§13.2);
  - infrastructure-to-code join noted as an open item (§16).
- **A6. WS3 Task 4 (from WS1 execution, 2026-10-12).** `.claude/agents/apd-tier-repair.md` already exists on the 1.7 line (tools Read and Edit, `model: sonnet`, no `effort`), and WS1's `repairTierGate` already dispatches it, because the tier-gate repair prompt embeds client text and the 1.7 line must not run it on a Bash-capable agent. WS3 Task 4 becomes: add `effort: low`, the usage phase and WS3's tests; keep the existing file and dispatch. `repair.md` carries a data-not-instructions line that LA2 reuses.
- **A5. Declined 2026-10-11: the OWASP LLM fix is 2.0 only (CAT1); WS1 is unchanged.** For the record: The bundled `owasp_llm_top10.json` and the `apd-control-mappings` skill use the 2023 list (`LLM06 Sensitive Information Disclosure`, `LLM07 Insecure Plugin Design`), while the `agentic-ai` pack's prose uses 2025 meanings (`LLM06 Excessive Agency`) under the same bare ids. In an `agentic-ai` run a bare `LLM06` can mean either, and rollups print the 2023 name. The 1.7.1 fix changes the seed list, its golden fixture, `refresh_owasp`'s LLM source and the skill's LLM section. The finding pattern does not change on 1.7.1; CAT1 adds year-qualified ids on 2.0 (threat catalog spec §10).

---

## Task 1: Capture the 1.7.1 baseline (operator)

**Files:** none committed. Run directories stay local, under `runs/` (gitignored).

- [ ] **Step 1: Configure telemetry.** Claude Code has no default OTLP protocol, and `usage` does not parse the console exporter, so:
  - Run a local OpenTelemetry Collector with an OTLP HTTP receiver and a `file` exporter writing `telemetry/<run-id>.otlp.jsonl`. WS2 Task 4's runbook has the config.
  - In the shell that launches Claude Code (2.1.273 or later, so agents report real names), export:
    - `CLAUDE_CODE_ENABLE_TELEMETRY=1`
    - `OTEL_LOGS_EXPORTER=otlp`
    - `OTEL_EXPORTER_OTLP_PROTOCOL=http/json`
    - `OTEL_EXPORTER_OTLP_ENDPOINT=http://127.0.0.1:4318`
    - `OTEL_LOG_TOOL_DETAILS=1`
- [ ] **Step 2: Run the baseline set twice each on 1.7.1 (`pip install apd-gauntlet==1.7.1` and the 1.7.1 plugin from `main`):** the three committed examples (`examples/apd-20260601-claim-event-bus`, `examples/apd-20260602-acme-mobile-banking`, `examples/apd-20260612-home-assistant`), plus one private PBM run. Keep each run directory and its telemetry export under a name ending `-baseline-r1` or `-baseline-r2`.
- [ ] **Step 3: Verify.** Each run directory passes `apd-gauntlet validate <run-dir>`, and each telemetry file contains `claude_code.api_request` events. Expected: "Clean." for every run; a non-empty event count for every file.

## Task 2: Execute WS1 and release 1.7.1

- [x] **Step 1:** Execute `2026-10-10-ws1-defect-fixes-1.7.1.md` on a branch from `main`, one PR per task group the plan names. **Done:** one branch and PR #49 (A8.3).
- [x] **Step 2:** Pass the 1.7.1 substitute gate (A8.1; `compare-runs` exists on neither line): the offline example regression (consolidated plan Task 1.4, Appendix 1: `validate`, `canonicalize`, `build-report`, `audit-report`, `resume-plan` on the three committed examples, each identical to the 1.7.0 engine's output) plus one live run of `examples/apd-20260601-claim-event-bus/inputs` with the `metrics.yaml` comparison (consolidated Task 1.5). Keep the 1.7.1 run directory `runs/apd-20261016-ws1-gate` for WS2 (it has no telemetry); no 1.7.0 live run exists (A15.1). A 1.7.1 defect found later ships as 1.7.2. **Done:** substitute gate (A8.1).
- [x] **Step 3:** Bump to 1.7.1 per RELEASING.md "Cutting a stable 1.7.x release". Tag and push. Expected: the release gate prints `prerelease=false, make_latest=true`. **Done:** tag `v1.7.1`.
- [x] **Step 4:** Merge `main` into `next` with `git merge --no-ff main`. While `next` has no 2.0 pre-release, the merge is conflict-free and takes 1.7.1 in all five version places; keep them ("keep `next`'s values" applies only once `2.0.0aN` is on `next`). In the same merge commit, reword next's CHANGELOG bullet "Version stays `1.7.0` for now" to "Version tracks the stable line (1.7.1) until the first 2.0 pre-release", and delete the empty `## [Unreleased]` heading that comes from `main`. Expected: CI green on `next`. **Done:** merge-forward #52 (A8.4).

## Task 3: Merge pending docs and release-line PRs

- [ ] **Step 1:** Merge #27 into `main`, then `main` into `next`, then #28 into `next`.
- [ ] **Step 2:** Merge #29 into `next`, then this branch (IaC spec, code-flow draft, program plans).
- [ ] **Step 3:** Apply amendments A1–A3 to the LA plan files in one docs PR. Expected: `markdownlint-cli2` clean.
- [ ] **Step 4 (administrator):** Protect `next`, and add the `v*` tag ruleset. (2026-10-17: `next` is protected by ruleset `next-protection-rules`; the `v*` tag ruleset is still open, consolidated Task 0.2 Step 1.)

## Task 4: M2 — WS2 and WS3, then `v2.0.0a1`

- [ ] **Step 1:** Execute the WS2 plan. Expected: `compare-runs` and `usage` work on the Task 1 baselines; WS2 Task 14's noise-floor check passes.
- [ ] **Step 1a: Capture the second baseline.** After WS2 Task 7 (attempts recorded), rerun the Task 1 set twice on `next` with the names ending `-next-baseline-r1` and `-next-baseline-r2`. Expected: each run has `.apd-state/attempts.yaml`, so gates 4–5 are measurable from WS3 onward.
- [ ] **Step 2:** Execute the WS3 plan, one PR per task. After each behaviour-changing task, run the Task 1 set twice and `compare-runs`. Expected: every gate passes, and `usage` shows per-run cost at or below baseline.
- [ ] **Step 3:** Cut `v2.0.0a1` per RELEASING.md "Cutting a 2.0 pre-release". The version-bump PR also changes the workflow's older-engine halt (`pip install --upgrade "apd-gauntlet>=1.7.1,<2"` and "upgrade apd-gauntlet to 1.7.1"), its two assertions in `tests/test_workflow_apd_gauntlet.py` and the copy of the command in `docs/running-the-gauntlet.md` to `pip install --upgrade --pre "apd-gauntlet>=2.0.0a1,<3"` and "upgrade apd-gauntlet to 2.0.0a1"; the CHANGELOG's v1.7.1 entry stays as history (A8.6). Expected: the gate prints `prerelease=true, make_latest=false`.

## Task 5: M3 — LA1 and LA2, then `v2.0.0a2`

- [ ] **Step 1:** Execute LA1, as amended by A1. Turn finding QA on in shadow mode (decision records written, nothing acted on).
- [ ] **Step 2:** Execute LA2, as amended by A2. Expected: `apd-gauntlet run` completes each committed example. The parity test asserts `runner.flow.PHASES == meta.phases`.
- [ ] **Step 3:** Run `compare-runs` on the workflow and runner outputs for the same example. Expected: gates pass, so runner output is equivalent.
- [ ] **Step 4:** Cut `v2.0.0a2`.

## Task 6: M4 — LA3 and WS5 Wave 2, then `v2.0.0a3`

- [ ] **Step 1:** Execute LA3, as amended by A3.
- [ ] **Step 2:** Execute the Wave 2 part of WS5 in the plan's order (digests and renders first), with `compare-runs` after each item. Expected: gates pass; `usage` shows the per-item saving.
- [ ] **Step 2a:** Execute CAT1 (`2026-10-11-cat1-catalog-data-loader-editions.md`). Expected: the vendored open catalog passes the load, no-HITRUST, KB-alignment and KB-edition tests; `compare-runs` passes with `threat_catalog: off` (CAT1 changes OWASP editions, so crosswalked comparisons are part of this check).
- [ ] **Step 3:** Cut `v2.0.0a3`.

## Task 7: M5 — IAC1–IAC3 and WS6 shadow mode, then `v2.0.0a4`

- [ ] **Step 1:** Execute IAC1, IAC2 and IAC3 in order. Expected:
  - the transformation suite and the security tests (`!exec` canary, outside include, argument allowlist) pass in CI;
  - a manual run on one private Atmos repository completes.
- [ ] **Step 2:** Execute WS6 with every task in shadow mode.
- [ ] **Step 2a:** Execute CAT2, then CAT3, with `threat_catalog: off` as the default. Run `compare-runs` with `off` (Expected: gates pass, outputs unchanged) and record a first `open` comparison for information.
- [ ] **Step 3:** Cut `v2.0.0a4`.

## Task 8: M6 — evaluation, calibration, tiering; `v2.0.0b1` and feature freeze

- [ ] **Step 0: One shared freeze.** IAC4 context parameters, CAT4 selection parameters and the WS2 `calibrate` thresholds are all tuned on development data first; then a single `eval freeze`; then every held-out run. Tuning after the freeze needs `eval freeze --new-heldout-set`.
- [ ] **Step 1:** Execute IAC4. Label the development and held-out corpora, run the 1.7.1 raw-read baseline and the new path, then tune the context parameters (frozen in Step 0's shared freeze). Expected: held-out recall of labelled issues ≥ baseline.
- [ ] **Step 2:** Run `calibrate` for `finding-qa` and each WS6 task on the development labels, with target precision 0.98. Then enable tasks one at a time: finding QA first, then `cluster-pairs`, `report-claims`, `asset-match`, `tm-screen`, `intake-score`, `input-screen`, `iac-triage`. Run `compare-runs` after each. Expected: gates pass.
- [ ] **Step 3:** Execute the Wave 3 part of WS5, one tier of lenses at a time, report writer last, with `compare-runs` after each. Expected: gates pass, or the tier reverts to its previous model.
- [ ] **Step 3a:** Execute CAT4: label threats, tune selection on development data before the shared freeze, measure once on held-out. Expected: every catalog gate passes and `threat_catalog` defaults to `open`; otherwise the default stays `off` for 2.0.
- [ ] **Step 4:** Cut `v2.0.0b1`. Feature freeze on `next` until GA.

## Task 9: M7 — release candidate and 2.0.0 GA

- [ ] **Step 1:** Fix-only PRs on `next`; cut `v2.0.0rc1`; test the plugin and engine installed from it.
- [ ] **Step 2:** Follow RELEASING.md "2.0.0 GA":
  - `release/1.7`;
  - the marketplace renames;
  - remove the pre-release notices;
  - merge `next` into `main`;
  - tag `v2.0.0`.

  Expected: the gate prints `make_latest=true`; `pip install apd-gauntlet` resolves 2.0.0.

## Task 10: M8 — code-flow layer (2.1)

- [ ] **Step 1:** Review and approve `2026-10-10-code-flow-layer-design.md`, resolving its §13 open questions.
- [ ] **Step 2:** Write CF1–CF4 with superpowers:writing-plans, using registry R2 (`run_tool`, `select_packet`, `EVIDENCE_INDEXES`) and R3 (the `code-flow` phase). Add each new plan file with `git add -f`.
- [ ] **Step 3:** Execute CF1–CF4. Gate on CF4's evaluation against the 1.7.1 CBM-only baseline.

---

## Decisions taken while planning

These were settled while writing the detailed plans. Each plan's Global Constraints repeat the ones it depends on.

1. **Composite naming.** The setup composite is `prepare-run`, not `setup`, because LA3 owns `apd-gauntlet setup`.
2. **Shared module locations.** `run_tool` lives in `apd_gauntlet.sandbox` and the packet selector in `apd_gauntlet.context`, so the code-flow layer reuses both.
3. **Excerpt check.**
   - It checks only citations of files under `inputs/`.
   - An excerpt containing `...` must match as fragments, in order.
   - It runs at tier gates, so the repair loop can fix it.
   - It warns on 1.7.1 (opt-in `--strict-excerpts`) and errors by default on `next`.
4. **Read-only gates always run on 1.7.1.** A schema-only guard check could otherwise skip a gate whose only errors are semantic.
5. **Id minting.** `cev-` and `tm-` ids are minted only when absent, so ids in committed examples keep resolving. ADR-0020 gets an amendment note.
6. **Agents.** Repairs go to a narrow `apd-tier-repair` agent, and `apd-orchestrator` is deleted.
7. **Comparison policy.**
   - Each step compares against the previous accepted state; milestones compare against the 1.7.1 baseline (A15.1).
   - WS1 runs comparisons once per PR group.
   - A second baseline on `next` makes gates 4–5 measurable.
   - WS3 Task 8 (strict excerpts by default) records `--excuse` for the first-pass validity gate, because it introduces a new error class on purpose.
8. **IaC.**
   - Client suppressions are surfaced as `suppressed_in_repo` entries, never honoured silently.
   - `atmos.*` template calls are rewritten to literals.
   - The CI job downloads pinned tools in its setup step only; the tests stay offline.
   - Internet attacker positions map through `data/iac/internet-aliases.yaml`.
9. **Decision tasks.**
   - Every WS6 task defaults to `off`.
   - `output-screen` is added (audit Wave 4).
   - `iac-triage` escalations go to the severity-disagreements annex and never change severity.
   - Whole-file tasks require `allow_full_inputs: true`.
   - Finding QA shares the per-run spend.
10. **Threat-model join.** The `tm-candidates` join matches on APD goal plus shared code evidence or a cited `tm-` id. Matching on asset names finds no pairs on the Home Assistant example; this join recovers its one known contradiction.
11. **Context trimming.**
    - Domain sidecar consumers come from each pack's stated consumers, defaulting to all nine lenses.
    - Code-recon shards hold 6 repositories each.
    - Render failures are advisory.
    - `build-lens-skills` stays a separate step.
12. **Evaluation corpora.** The committed examples form the development findings corpus. The held-out findings corpus is private PBM runs under `eval/local/`.
13. **Execution method** (2026-10-11): every detailed plan runs with superpowers:subagent-driven-development — a fresh implementer per task, spec and quality review before the next task, and a whole-branch review at the end.
14. **Threat catalog** (2026-10-11): spec approved. The OWASP LLM fix is 2.0 only (A5 declined). Catalog 1.1.0 (2026-10-13) removed all HITRUST content. The whole release is vendored as `open`; `full` is an operator-supplied local file; the loader and CI refuse any `hitrust` key or text (A7).

## Decisions still needed (defaults apply if no answer)

| Decision | Default | Blocks |
|---|---|---|
| Where Clef runs for reviews of PHI-handling systems (Workers AI only if the client's Cloudflare agreements cover it, otherwise self-hosted) | No decision model on reviews of PHI-handling systems until confirmed | WS6 and finding QA on reviews of PHI-handling systems |
| Approve the code-flow spec and its release target | 2.1, after GA | M8 |
| IaC held-out repositories (a public OpenTofu repository plus Atmos repositories), with licences checked at pinned commits | Chosen during IAC4 Task 1 | M6 |
| How aggressive the domain consumer map is (pbm drops 55% against the audit's 45%) | Packs' stated consumers | WS5 Task 9 |
| Match parameters (title similarity 0.5; at least 10 predicted positives for `calibrate`) | Confirmed or adjusted by WS2 Task 14's noise check | M2 |
| Catalog repository visibility and licence (consolidated DEC-7) | Repository public; data CC BY-SA 4.0, code Apache-2.0; CIS ids only; CSA ids plus short attributed titles | Consolidated Task 5.3 |
| Catalog compat floor and asset names (consolidated DEC-8) | `>=1.1.0,<2.0.0`; `threat-catalog-<v>.json`, `threat-catalog.schema.json`, `SHA256SUMS`; vendored names stay `open.*` | CAT1 Tasks 6 and 10 |
| ATT&CK v20.0 follow-up versus the catalog's v19.2 (consolidated DEC-9) | Vendor 1.1.0; refresh ATT&CK only if an id check fails; plan catalog 1.2.0 on v20 | CAT1 Task 14 |
| CAT4 held-out systems | Two private systems: one with PHI-classified assets, one using the `agentic-ai` pack | M6 |

## Size

| Plan | Tasks |
|---|---|
| WS1 | 12 |
| WS2 | 14 |
| WS3 | 9 |
| LA1, LA2, LA3 | 26 |
| WS5 | 23 |
| WS6 | 13 |
| IAC1–IAC4 | 38 |
| CAT1–CAT4 | 51 |
| **Total for 1.7.1 and 2.0** | **186** |
| CF1–CF4 (2.1, after spec approval) | To be planned |

Each behaviour-changing PR group also needs about 8 gauntlet runs (4 configurations × 2) for its comparison. That operator time, not coding, is the long pole.

## Operator work outside the code

- **Baseline capture** (Task 1), the second baseline on `next` (Task 4 Step 1a), and every `compare-runs` rerun: about 8 gauntlet runs per behaviour-changing PR group.
- **Telemetry collector:** a local OpenTelemetry Collector during every measured run (Task 1 Step 1).
- **Labelling:**
  - about 200 cluster pairs (WS6);
  - finding goal and severity labels from the committed examples (WS2);
  - IaC corpus labels (IAC4);
  - code-flow labels (CF4);
  - applicable catalog threats per corpus system, and mapping labels for a finding sample (CAT4).

  All local, per ADR-0017.
- **Live fixture recording** for decision providers (LA1 Task 9) needs real keys.
- **Hosting decision for Clef** on reviews of PHI-handling systems: Workers AI only if the client's Cloudflare agreements cover it, otherwise self-hosted. Needed before any decision task runs on a PHI review.
- **Repository administration:** branch protection and the tag ruleset (Task 3).
- **Threat catalog release:** create `illusconsulting/threat-catalog` (public by default), push the 1.1.0 sources, and add `LICENSE` and `NOTICE`. Tag `v1.1.0` and publish `threat-catalog-1.1.0.json`, `threat-catalog.schema.json` and `SHA256SUMS`. Do this before CAT1 Task 7, which copies the release schema. CAT1 Task 14 vendors the file.

## Risks

- **Workflow merge conflicts.** WS3, WS5, LA2, IAC1 and CF1 all edit the workflow and runner flow. Mitigation: one PR at a time on those files, with the parity test as the tripwire.
- **Measurement noise.** Two runs per configuration may not separate noise from regressions on small effects. If gates flap, raise to three runs and gate on the median.
- **Labelling effort** is the long pole for M6. Start IaC and cluster-pair labelling during M4.
- **Tier-3 model moves** may raise audit iterations. Wave 3 reverts per tier on gate failure.
- **External tool churn** (Trivy and Checkov rules, Atmos flags). Versions are pinned, and evaluations rerun on every upgrade.
- **Catalog mapping error** (about 1–2%) flowing into findings. Derived mappings stay in `catalog_mappings`, are counted apart from lens mappings, and are gated on precision (threat catalog spec §14).
